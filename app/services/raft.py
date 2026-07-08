import cv2
import numpy as np
import torch
import torchvision.transforms.functional as TVF
from torchvision.models.optical_flow import raft_small, Raft_Small_Weights

from app.core.config import settings


class RAFTService:

    def __init__(self) -> None:
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model  = None

    def load(self) -> None:
        """
        Load RAFT-Small weights.
        Called once at application startup.
        """
        self.model = raft_small(weights=Raft_Small_Weights.DEFAULT)

        state_dict = torch.load(
            settings.MODEL_RAFT_PATH,
            map_location=self.device,
            weights_only=True,
        )
        self.model.load_state_dict(state_dict)
        self.model.to(self.device)
        self.model.eval()

    def is_loaded(self) -> bool:
        return self.model is not None

    def _to_tensor(self, frame_bgr: np.ndarray) -> torch.Tensor:
        """
        Convert BGR numpy frame to RAFT input tensor.
        torchvision RAFT-Small expects values in [0, 1].
        """
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        tensor    = TVF.to_tensor(frame_rgb).unsqueeze(0).to(self.device)
        return tensor

    def _resize_to_raft(
        self,
        frame_bgr: np.ndarray,
    ) -> tuple[np.ndarray, tuple[int, int]]:
        """
        Resize frame so both dimensions are multiples of 8.
        RAFT-Small requires this constraint.
        Preserves aspect ratio. Returns resized frame and original (h, w).
        """
        h_orig, w_orig = frame_bgr.shape[:2]

        scale   = settings.TARGET_WIDTH / w_orig
        h_new   = int(h_orig * scale)
        w_new   = settings.TARGET_WIDTH

        h_new = (h_new // 8) * 8
        w_new = (w_new // 8) * 8

        resized = cv2.resize(
            frame_bgr,
            (w_new, h_new),
            interpolation=cv2.INTER_LINEAR,
        )
        return resized, (h_orig, w_orig)

    def compute_flow(
        self,
        frame1_bgr: np.ndarray,
        frame2_bgr: np.ndarray,
        water_mask: np.ndarray,
    ) -> np.ndarray:
        """
        Compute optical flow between two BGR frames.
        Flow is masked to water ROI only.
        Background pixels are zeroed out.

        Args:
            frame1_bgr:  previous frame, BGR uint8
            frame2_bgr:  current frame, BGR uint8
            water_mask:  binary uint8 mask (H, W), 1=water 0=background

        Returns:
            flow_roi: float32 array (H, W, 2) with flow vectors.
                      dx = flow[..., 0], dy = flow[..., 1]
                      Zero outside water ROI.
        """
        if not self.is_loaded():
            raise RuntimeError("RAFTService.load() has not been called.")

        h_orig, w_orig = frame1_bgr.shape[:2]

        f1_resized, _ = self._resize_to_raft(frame1_bgr)
        f2_resized, _ = self._resize_to_raft(frame2_bgr)

        t1 = self._to_tensor(f1_resized)
        t2 = self._to_tensor(f2_resized)

        with torch.no_grad():
            flow_list = self.model(t1, t2)

        flow = flow_list[-1][0]

        flow_np = flow.cpu().numpy().transpose(1, 2, 0)

        # resize flow back to original frame dimensions
        flow_np = cv2.resize(
            flow_np,
            (w_orig, h_orig),
            interpolation=cv2.INTER_LINEAR,
        )

        # scale flow vectors to compensate for resize
        scale_x = w_orig / f1_resized.shape[1]
        scale_y = h_orig / f1_resized.shape[0]
        flow_np[..., 0] *= scale_x
        flow_np[..., 1] *= scale_y

        # apply water mask: zero out background pixels
        mask_2ch         = np.stack([water_mask, water_mask], axis=2)
        flow_roi         = flow_np * mask_2ch

        return flow_roi.astype(np.float32)

    def frame_diff(
        self,
        frame1_bgr: np.ndarray,
        frame2_bgr: np.ndarray,
    ) -> float:
        """
        Heartbeat filter.
        Compute mean absolute difference in brightness between two frames.
        Returns a scalar. If below FRAME_DIFF_THRESHOLD, discard the frame.
        """
        gray1 = cv2.cvtColor(frame1_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
        gray2 = cv2.cvtColor(frame2_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
        return float(np.mean(np.abs(gray1 - gray2)))


raft_service = RAFTService()

