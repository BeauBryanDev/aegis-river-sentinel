from collections import deque
from typing import Optional
import numpy as np

from app.core.config import settings


class DetectionsService:
    """
    Sliding window anomaly detector over water flow metrics.

    Maintains a rolling history of the last N frames
    and computes multivariable Z-Score against that baseline.

    Emits anomaly flags with graded severity.
    """

    METRIC_KEYS = ("vel_mean", "vel_std", "water_ratio", "flow_entropy")

    def __init__(self, window_size: Optional[int] = None) -> None:
        self.window_size = window_size or settings.SLIDING_WINDOW_SIZE
        self.history: dict[str, deque] = {
            key: deque(maxlen=self.window_size) for key in self.METRIC_KEYS
        }

    def reset(self) -> None:
        """
        Clear the sliding window.
        Called between videos or when starting a new stream.
        """
        for key in self.METRIC_KEYS:
            self.history[key].clear()

    def is_warm(self) -> bool:
        """
        Returns True when the sliding window has enough samples
        to compute statistically meaningful Z-Scores.
        """
        return len(self.history["vel_mean"]) >= max(30, self.window_size // 5)

    def update_and_score(self, metrics: dict) -> dict:
        """
        Add new frame metrics to the sliding window and compute
        the anomaly score against the historical baseline.

        Args:
            metrics: dict from WaterFlowService.compute_metrics()

        Returns:
            dict with:
                z_scores        per-metric Z-Score values
                anomaly_score   max absolute Z-Score across metrics
                anomaly_flag    True if score exceeds threshold
                severity        LOW / MEDIUM / HIGH or None
                is_warm         whether baseline is ready
        """
        z_scores = {key: 0.0 for key in self.METRIC_KEYS}

        if not self.is_warm():
            for key in self.METRIC_KEYS:
                self.history[key].append(metrics[key])

            return {
                "z_scores":      z_scores,
                "anomaly_score": 0.0,
                "anomaly_flag":  False,
                "severity":      None,
                "is_warm":       False,
            }

        for key in self.METRIC_KEYS:
            baseline    = np.array(self.history[key], dtype=np.float64)
            mean        = float(np.mean(baseline))
            std         = float(np.std(baseline))

            if std < 1e-6:
                z_scores[key] = 0.0
            else:
                z_scores[key] = (metrics[key] - mean) / std

        for key in self.METRIC_KEYS:
            self.history[key].append(metrics[key])

        abs_scores    = {k: abs(v) for k, v in z_scores.items()}
        anomaly_score = max(abs_scores.values())

        threshold     = settings.ANOMALY_Z_THRESHOLD
        anomaly_flag  = anomaly_score >= threshold
        severity      = self._classify_severity(anomaly_score) if anomaly_flag else None

        return {
            "z_scores":      z_scores,
            "anomaly_score": float(anomaly_score),
            "anomaly_flag":  bool(anomaly_flag),
            "severity":      severity,
            "is_warm":       True,
        }

    def _classify_severity(self, anomaly_score: float) -> str:
        """
        Map anomaly score magnitude to a severity level.

        2.0 - 3.0   LOW      minor perturbation
        3.0 - 4.5   MEDIUM   significant event
        4.5+        HIGH     probable flood or major turbulence
        """
        if anomaly_score >= 4.5:
            return "HIGH"
        if anomaly_score >= 3.0:
            return "MEDIUM"
        return "LOW"

    def classify_alert_type(self, metrics: dict, z_scores: dict) -> Optional[str]:
        """
        Infer the type of anomaly based on which metric
        dominates the Z-Score.

        Returns None if no clear signature is detected.
        """
        abs_z = {k: abs(v) for k, v in z_scores.items()}
        dominant = max(abs_z, key=abs_z.get)

        if abs_z[dominant] < settings.ANOMALY_Z_THRESHOLD:
            return None

        if dominant == "water_ratio" and z_scores["water_ratio"] > 0:
            return "water_level_rise"

        if dominant == "vel_mean" and z_scores["vel_mean"] > 0:
            return "velocity_spike"

        if dominant == "flow_entropy":
            return "flow_disturbance"

        if dominant == "vel_std":
            return "turbulence"

        return "generic_anomaly"


detections_service = DetectionsService()