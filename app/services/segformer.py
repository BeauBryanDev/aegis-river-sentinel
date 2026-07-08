import numpy as np
import torch
import torch.nn.functional as TF
from PIL import Image
from transformers import SegformerForSemanticSegmentation, SegformerImageProcessor

from app.core.config import settings


CLASS_NAMES = {
    0: "background",
    1: "water",
    2: "sky",
    3: "vegetation",
    4: "building",
    5: "vehicle",
    6: "person",
}


class SegFormerService:

    def __init__(self) -> None:
        self.device    = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model     = None
        self.processor = None

    def load(self) -> None:
        """
        Load SegFormer checkpoint and processor.
        Called once at application startup.
        """
        checkpoint = "nvidia/mit-b2"

        self.processor = SegformerImageProcessor.from_pretrained(
            checkpoint,
            do_resize=True,
            size={"height": 512, "width": 512},
            do_normalize=True,
        )

        self.model = SegformerForSemanticSegmentation.from_pretrained(
            checkpoint,
            num_labels=settings.NUM_CLASSES,
            ignore_mismatched_sizes=True,
            id2label={str(k): v for k, v in CLASS_NAMES.items()},
            label2id={v: str(k) for k, v in CLASS_NAMES.items()},
        )

        state_dict = torch.load(
            settings.MODEL_SEGFORMER_PATH,
            map_location=self.device,
            weights_only=True,
        )
        self.model.load_state_dict(state_dict)
        self.model.to(self.device)
        self.model.eval()

    def is_loaded(self) -> bool:
        return self.model is not None and self.processor is not None

    def predict_mask(self, frame_bgr: np.ndarray) -> np.ndarray:
        """
        Run semantic segmentation on a BGR frame.

        Returns a binary uint8 mask (H, W):
            1 = water
            0 = everything else
        """
        if not self.is_loaded():
            raise RuntimeError("SegFormerService.load() has not been called.")

        h_orig, w_orig = frame_bgr.shape[:2]

        import cv2
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(frame_rgb)

        inputs = self.processor(images=pil_image, return_tensors="pt")
        pixel_values = inputs["pixel_values"].to(self.device)

        with torch.no_grad():
            with torch.autocast(
                device_type=self.device.type,
                dtype=torch.float16,
                enabled=self.device.type == "cuda",
            ):
                outputs   = self.model(pixel_values=pixel_values)
                logits    = outputs.logits
                logits_up = TF.interpolate(
                    logits,
                    size=(h_orig, w_orig),
                    mode="bilinear",
                    align_corners=False,
                )
                pred = logits_up.argmax(dim=1).squeeze(0).cpu().numpy()

        water_mask = (pred == settings.WATER_CLASS_INDEX).astype(np.uint8)
        return water_mask

    def histogram_changed(
        self,
        prev_frame_bgr: np.ndarray,
        curr_frame_bgr: np.ndarray,
        threshold: float = 0.15,
    ) -> bool:
        """
        Compare HSV value-channel histograms between two frames.
        Returns True if illumination or scene changed significantly,
        triggering a SegFormer re-run outside the normal interval.
        """
        import cv2

        def hist(frame: np.ndarray) -> np.ndarray:
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            h   = cv2.calcHist([hsv], [2], None, [64], [0, 256])
            cv2.normalize(h, h)
            return h

        prev_h = hist(prev_frame_bgr)
        curr_h = hist(curr_frame_bgr)

        correlation = cv2.compareHist(prev_h, curr_h, cv2.HISTCMP_CORREL)
        return correlation < (1.0 - threshold)


segformer_service = SegFormerService()

