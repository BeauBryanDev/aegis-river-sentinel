import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.videos import Video
from app.utils.video_utils import probe_video, read_frame_at


class VideoService:
    """
    Business logic for video lifecycle:
    - persist uploaded files to disk
    - extract metadata via ffprobe
    - register videos in the database
    - update processing status during pipeline execution
    """

    def __init__(self) -> None:
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def save_upload(
        self,
        upload_file: UploadFile,
        location_id: int,
        db: Session,
    ) -> Video:
        """
        Save uploaded video to disk and register it in the database.

        Returns the created Video row with status='pending'.
        """
        if not upload_file.filename:
            raise ValueError("Uploaded file has no filename.")

        suffix    = Path(upload_file.filename).suffix.lower()
        if suffix not in (".mp4", ".avi", ".mov", ".mkv"):
            raise ValueError(f"Unsupported video format: {suffix}")

        unique_id = uuid4().hex[:12]
        safe_name = f"{unique_id}{suffix}"
        filepath  = self.upload_dir / safe_name

        max_bytes = settings.MAX_VIDEO_MB * 1024 * 1024
        written   = 0

        with filepath.open("wb") as f:
            while chunk := await upload_file.read(1024 * 1024):
                written += len(chunk)
                if written > max_bytes:
                    f.close()
                    filepath.unlink(missing_ok=True)
                    raise ValueError(
                        f"Video exceeds maximum size of {settings.MAX_VIDEO_MB} MB"
                    )
                f.write(chunk)

        try:
            metadata = probe_video(filepath)
        except Exception as e:
            filepath.unlink(missing_ok=True)
            raise ValueError(f"Cannot probe video: {e}") from e

        video = Video(
            location_id  = location_id,
            filename     = upload_file.filename,
            filepath     = str(filepath),
            fps          = metadata["fps"],
            duration_s   = metadata["duration_s"],
            width        = metadata["width"],
            height       = metadata["height"],
            total_frames = metadata["total_frames"],
            status       = "pending",
        )

        db.add(video)
        db.commit()
        db.refresh(video)
        
        return video

    def get(self, video_id: int, db: Session) -> Optional[Video]:
        return db.query(Video).filter(Video.id == video_id).first()

    def list_by_location(self, location_id: int, db: Session) -> list[Video]:
        
        return (
            db.query(Video)
            .filter(Video.location_id == location_id)
            .order_by(Video.created_at.desc())
            .all()
        )

    def mark_processing(self, video_id: int, db: Session) -> Optional[Video]:
        video = self.get(video_id, db)
        if video is None:
            return None
        video.status = "processing"
        db.commit()
        db.refresh(video)
        
        return video

    def mark_completed(self, video_id: int, db: Session) -> Optional[Video]:
        video = self.get(video_id, db)
        if video is None:
            return None
        video.status       = "completed"
        video.processed_at = datetime.now(timezone.utc)
        video.error_msg    = None
        db.commit()
        db.refresh(video)
        
        return video

    def mark_failed(
        self,
        video_id: int,
        error_msg: str,
        db: Session,
    ) -> Optional[Video]:
        video = self.get(video_id, db)
        
        if video is None:
            
            return None
        
        video.status       = "failed"
        video.processed_at = datetime.now(timezone.utc)
        video.error_msg    = error_msg[:2000]
        db.commit()
        db.refresh(video)
        
        return video

    def delete(self, video_id: int, db: Session) -> bool:
        """
        Delete video row and remove file from disk.
        Cascade deletes analyses and alerts via ORM configuration.
        """
        video = self.get(video_id, db)
        if video is None:
            
            return False

        filepath = Path(video.filepath)
        if filepath.exists():
            try:
                filepath.unlink()
            except OSError:
                pass

        db.delete(video)
        db.commit()
        
        return True


video_service = VideoService()

