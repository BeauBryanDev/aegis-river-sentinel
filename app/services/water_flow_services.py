import numpy as np


class WaterFlowService:
    """
    Extracts physical metrics from an optical flow field
    computed over a water ROI mask.
    No temporal state is kept here. Temporal analysis lives
    in detections_service.
    """

    ENTROPY_BINS = 16

    def compute_metrics(
        self,
        flow_roi: np.ndarray,
        water_mask: np.ndarray,
    ) -> dict:
        """
        Compute all four physical metrics for a single frame.

        Args:
            flow_roi:   float32 array (H, W, 2) from RAFTService.
                        Already masked to water ROI, zero outside.
            water_mask: uint8 binary array (H, W). 1=water, 0=background.

        Returns:
            dict with keys: vel_mean, vel_std, vel_max,
                            water_ratio, flow_entropy
        """
        water_pixels = water_mask.astype(bool)
        total_water  = int(water_pixels.sum())
        total_frame  = int(water_mask.size)
        water_ratio  = total_water / total_frame if total_frame > 0 else 0.0

        if total_water == 0:
            return {
                "vel_mean":     0.0,
                "vel_std":      0.0,
                "vel_max":      0.0,
                "water_ratio":  0.0,
                "flow_entropy": 0.0,
            }

        dx = flow_roi[..., 0]
        dy = flow_roi[..., 1]

        magnitude = np.sqrt(dx * dx + dy * dy)
        mag_water = magnitude[water_pixels]

        vel_mean = float(np.mean(mag_water))
        vel_std  = float(np.std(mag_water))
        vel_max  = float(np.max(mag_water))

        flow_entropy = self._compute_direction_entropy(
            dx[water_pixels],
            dy[water_pixels],
            mag_water,
        )

        return {
            "vel_mean":     vel_mean,
            "vel_std":      vel_std,
            "vel_max":      vel_max,
            "water_ratio":  water_ratio,
            "flow_entropy": flow_entropy,
        }

    def _compute_direction_entropy(
        self,
        dx_water: np.ndarray,
        dy_water: np.ndarray,
        mag_water: np.ndarray,
    ) -> float:
        """
        Compute Shannon entropy over the distribution
        of flow direction angles.

        Low entropy  -> flow is coherent, all vectors point
                        in similar direction (laminar flow)
        High entropy -> flow is chaotic, vectors point in many
                        directions (turbulence, stone impact,
                        object drag)

        Only pixels with meaningful magnitude contribute
        to avoid noise from near-zero vectors.
        """
        min_magnitude = 0.5
        valid         = mag_water >= min_magnitude

        if valid.sum() < 10:
            return 0.0

        angles = np.arctan2(dy_water[valid], dx_water[valid])

        hist, _ = np.histogram(
            angles,
            bins=self.ENTROPY_BINS,
            range=(-np.pi, np.pi),
        )

        prob = hist.astype(np.float64) / hist.sum()
        prob = prob[prob > 0]

        entropy     = -np.sum(prob * np.log2(prob))
        max_entropy = np.log2(self.ENTROPY_BINS)

        return float(entropy / max_entropy)


water_flow_service = WaterFlowService()