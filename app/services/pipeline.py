import traceback
from pathlib import Path
from typing import Optional

import cv2
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.analysis import Analysis
from app.models.alerts import Alert
from app.services.segformer import segformer_service
from app.services.raft import raft_service
from app.services.water_flow_services import water_flow_service
from app.services.detections_service import DetectionsService
from app.services.video_service import video_service
from app.utils.video_utils import iter_video_frames
from app.utils.flow_heatmap_utils import (
    flow_to_heatmap,
    flow_to_hsv,
    compose_visualization_panel,
)


class PipelineService:
    """
    Orchestrates the full RiverWatch analysis pipeline for a single video.

    Sequence per frame pair:
    i. heartbeat filter (frame diff)
    ii. water mask (SegFormer, cached with interval + histogram trigger)
    iii. optical flow (RAFT-Small) masked to water ROI
    iv. physical metrics (WaterFlowService)
    v. anomaly detection (DetectionsService, sliding window)
    vi. persistence (Analysis + Alert rows when relevant)
    A visualization video is written to disk for review.
    """

    ANALYSIS_BATCH_SIZE = 30

    def __init__(self) -> None:
        self.detector = DetectionsService()

    def ensure_models_loaded(self) -> None:
        
        if not segformer_service.is_loaded():
            segformer_service.load()
            
        if not raft_service.is_loaded():
            raft_service.load()

    def process_video(
        self,
        video_id: int,
        db: Session,
        write_visualization: bool = True,
    ) -> dict:
        """
        Run the full pipeline over a single video.

        Args:
            video_id:  id of the Video row to process
            db:   active SQLAlchemy session
            write_visualization: whether to render an output video

        Returns:
            dict with processing summary:
            frames_processed, frames_skipped, analyses_created,
            alerts_created, output_path
        """
        video = video_service.get(video_id, db)
        
        if video is None:
            raise ValueError(f"Video id={video_id} not found")

        video_service.mark_processing(video_id, db)

        try:
            self.ensure_models_loaded()
            self.detector.reset()

            summary = self._run(video, db, write_visualization)

            video_service.mark_completed(video_id, db)
            return summary

        except Exception as e:
            
            tb = traceback.format_exc()
            video_service.mark_failed(video_id, tb, db)
            
            raise

    def _run(
        self,
        video,
        db: Session,
        write_visualization: bool,
    ) -> dict:

        filepath = Path(video.filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"Video file not found: {filepath}")

        cap = cv2.VideoCapture(str(filepath))
        
        if not cap.isOpened():
            raise IOError(f"Cannot open video: {filepath}")

        fps  = cap.get(cv2.CAP_PROP_FPS) or 30.0
        width   = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height  = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        writer  = None
        output_path: Optional[str] = None

        if write_visualization:
            output_path = str(filepath.with_suffix(".viz.mp4"))
            fourcc      = cv2.VideoWriter_fourcc(*"mp4v")
            writer      = cv2.VideoWriter(
                output_path, fourcc, fps, (width * 3, height)
            )

        ret, frame_prev = cap.read()
        if not ret:
            cap.release()
            if writer is not None:
                writer.release()
            raise IOError("Video is empty or unreadable")

        water_mask = segformer_service.predict_mask(frame_prev)

        frame_idx        = 0
        frames_processed = 0
        frames_skipped   = 0
        analyses_batch: list[dict] = []
        analyses_created = 0
        alerts_created   = 0
        analysis_start   = 0

        try:
            while True:
                ret, frame_curr = cap.read()
                if not ret:
                    break

                frame_idx += 1

                diff = raft_service.frame_diff(frame_prev, frame_curr)
                if diff < settings.FRAME_DIFF_THRESHOLD:
                    frames_skipped += 1
                    frame_prev      = frame_curr
                    continue

                refresh_mask = (
                    frame_idx % settings.SEGFORMER_INTERVAL == 0
                    or segformer_service.histogram_changed(frame_prev, frame_curr)
                )
                if refresh_mask:
                    water_mask = segformer_service.predict_mask(frame_curr)

                flow_roi = raft_service.compute_flow(
                    frame_prev, frame_curr, water_mask
                )

                metrics = water_flow_service.compute_metrics(flow_roi, water_mask)

                detection = self.detector.update_and_score(metrics)

                analyses_batch.append({
                    "frame":     frame_idx,
                    "metrics":   metrics,
                    "detection": detection,
                })

                if writer is not None:
                    heatmap  = flow_to_heatmap(flow_roi, mask=water_mask)
                    hsv_flow = flow_to_hsv(flow_roi,    mask=water_mask)
                    panel    = compose_visualization_panel(
                        frame_curr,
                        heatmap,
                        hsv_flow,
                        metrics,
                        anomaly_info=detection,
                    )
                    writer.write(panel)

                if detection["anomaly_flag"]:
                    alert_type = self.detector.classify_alert_type(
                        metrics,
                        detection["z_scores"],
                    )
                    if alert_type is not None:
                        self._persist_alert(
                            db,
                            video_id     = video.id,
                            analysis_id  = None,
                            frame_num    = frame_idx,
                            alert_type   = alert_type,
                            severity     = detection["severity"],
                            score        = detection["anomaly_score"],
                        )
                        alerts_created += 1

                if len(analyses_batch) >= self.ANALYSIS_BATCH_SIZE:
                    analysis_start = self._flush_analyses(
                        db, video.id, analyses_batch, analysis_start
                    )
                    analyses_created += len(analyses_batch)
                    analyses_batch.clear()

                frame_prev        = frame_curr
                frames_processed += 1

            if analyses_batch:
                self._flush_analyses(
                    db, video.id, analyses_batch, analysis_start
                )
                analyses_created += len(analyses_batch)

        finally:
            cap.release()
            if writer is not None:
                writer.release()

        return {
            "frames_processed": frames_processed,
            "frames_skipped":   frames_skipped,
            "analyses_created": analyses_created,
            "alerts_created":   alerts_created,
            "output_path":      output_path,
        }

    def _flush_analyses(
        self,
        db: Session,
        video_id: int,
        batch: list[dict],
        frame_start_offset: int,
    ) -> int:
        """
        Aggregate a batch of per-frame metrics into a single
        Analysis row spanning the batch's frame range.
        """
        frames        = [b["frame"] for b in batch]
        metrics_list  = [b["metrics"] for b in batch]
        detections    = [b["detection"] for b in batch]

        avg = lambda key: sum(m[key] for m in metrics_list) / len(metrics_list)

        max_score = max(d["anomaly_score"] for d in detections)
        any_flag  = any(d["anomaly_flag"] for d in detections)

        analysis = Analysis(
            video_id      = video_id,
            frame_start   = min(frames),
            frame_end     = max(frames),
            water_ratio   = avg("water_ratio"),
            vel_mean      = avg("vel_mean"),
            vel_std       = avg("vel_std"),
            vel_max       = max(m["vel_max"] for m in metrics_list),
            anomaly_score = max_score,
            anomaly_flag  = any_flag,
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)

        return max(frames) + 1

    def _persist_alert(
        self,
        db: Session,
        video_id: int,
        analysis_id: Optional[int],
        frame_num: int,
        alert_type: str,
        severity: str,
        score: float,
    ) -> None:
        """
        Insert an Alert row.

        Note: analysis_id may be None if the alert is emitted before
        the current batch of analyses is flushed. In that case, the
        FK is written as -1 as a placeholder and a background reconcile
        task can link it later. For the PoC we insert directly.
        """
        if analysis_id is None:
            last_analysis = (
                db.query(Analysis)
                .filter(Analysis.video_id == video_id)
                .order_by(Analysis.id.desc())
                .first()
            )
            analysis_id = last_analysis.id if last_analysis else None

        if analysis_id is None:
            return

        alert = Alert(
            video_id     = video_id,
            analysis_id  = analysis_id,
            frame_num    = frame_num,
            alert_type   = alert_type,
            severity     = severity,
            description  = f"Anomaly score {score:.2f} at frame {frame_num}",
        )
        db.add(alert)
        db.commit()


pipeline_service = PipelineService()