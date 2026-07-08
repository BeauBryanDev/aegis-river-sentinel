import cv2 
import numpy as np
from typing import Optional

def flow_to_heatmap( 
                    flow: np.ndarray,
                    mask: Optional[np.ndarray] = None,
                    colormap: int = cv2.COLORMAP_JET,
) -> np.ndarray:
    """
    Convert an optical flow field to a heatmap image
    encoding velocity magnitude.

    Cold colors (blue) indicate low velocity.
    Warm colors (red) indicate high velocity.

    Args:
        flow:     float32 array (H, W, 2) with dx, dy per pixel
        mask:     optional uint8 binary mask (H, W).
                  Pixels where mask==0 are rendered black.
        colormap: OpenCV colormap constant (default JET)

    Returns:
        BGR uint8 image (H, W, 3)
    """
    dx = flow[..., 0]
    dy = flow[..., 1]

    magnitude = np.sqrt(dx * dx + dy * dy).astype(np.float32)
    normalized = cv2.normalize(magnitude, None, 0, 255, cv2.NORM_MINMAX)
    normalized = normalized.astype(np.uint8)

    heatmap = cv2.applyColorMap(normalized, colormap)

    if mask is not None:
        heatmap[mask == 0] = 0

    return heatmap


def flow_to_hsv(
    flow: np.ndarray,
    mask: Optional[np.ndarray] = None,
) -> np.ndarray:
    """
    Convert an optical flow field to an HSV visualization
    encoding both direction and magnitude.

    Hue     -> flow direction (angle)
    Value   -> flow magnitude (speed)
    Saturation is fixed at maximum.

    Args:
        flow: float32 array (H, W, 2) with dx, dy per pixel
        mask: optional uint8 binary mask. mask==0 rendered black.

    Returns:
        BGR uint8 image (H, W, 3)
    """
    dx = flow[..., 0] # dx, dy
    dy = flow[..., 1] # dx, dy
 
    h, w = flow.shape[:2]  # height, width
    hsv  = np.zeros((h, w, 3), dtype=np.uint8)  # hsv image
    hsv[..., 1] = 255  # saturation

    magnitude, angle = cv2.cartToPolar(dx, dy)
    # convert angle to hue
    hsv[..., 0] = (angle * 180 / np.pi / 2).astype(np.uint8)
    hsv[..., 2] = cv2.normalize(
        magnitude, None, 0, 255, cv2.NORM_MINMAX
    ).astype(np.uint8)

    bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

    if mask is not None:
        bgr[mask == 0] = 0

    return bgr


def overlay_metrics(
    frame_bgr: np.ndarray,
    metrics: dict,
    anomaly_info: Optional[dict] = None,
) -> np.ndarray:
    """
    Draw metric values and anomaly status on top of a frame.

    Args:
        frame_bgr:    the frame to annotate
        metrics:      dict from WaterFlowService.compute_metrics()
        anomaly_info: optional dict from DetectionsService with
                      keys anomaly_score, anomaly_flag, severity

    Returns:
        annotated BGR frame (copy, does not modify input)
    """
    out = frame_bgr.copy()

    line1 = (
        f"water: {metrics['water_ratio'] * 100:.1f}%  "
        f"vel_mean: {metrics['vel_mean']:.2f} px/f  "
        f"vel_std: {metrics['vel_std']:.2f}  "
        f"entropy: {metrics['flow_entropy']:.2f}"
    )
    cv2.putText(
        out,
        line1,
        (10, 25),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )

    if anomaly_info is not None:
        severity = anomaly_info.get("severity")
        score    = anomaly_info.get("anomaly_score", 0.0)

        color, label = _severity_color(severity)
        line2        = f"{label}  score: {score:.2f}"

        cv2.putText(
            out,
            line2,
            (10, 55),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            color,
            2,
            cv2.LINE_AA,
        )

    return out


def _severity_color(severity: Optional[str]) -> tuple[tuple[int, int, int], str]:
    """
    Map severity string to BGR color and label
    for on-screen overlay.
    """
    if severity == "HIGH":
        return (0, 0, 255), "ANOMALY: HIGH"
    if severity == "MEDIUM":
        return (0, 165, 255), "ANOMALY: MEDIUM"
    if severity == "LOW":
        return (0, 255, 255), "ANOMALY: LOW"
    return (0, 255, 0), "NORMAL"


def compose_visualization_panel(
    frame_bgr: np.ndarray,
    heatmap:   np.ndarray,
    hsv_flow:  np.ndarray,
    metrics:   dict,
    anomaly_info: Optional[dict] = None,
) -> np.ndarray:
    """
    Build a horizontal 3-panel visualization:
    [annotated frame] [velocity heatmap] [direction hsv flow]

    All three panels are stacked side by side into a single
    BGR image, ready for writing to output video.
    """
    annotated = overlay_metrics(frame_bgr, metrics, anomaly_info)

    if heatmap.shape[:2] != annotated.shape[:2]:
        heatmap = cv2.resize(heatmap, (annotated.shape[1], annotated.shape[0]))

    if hsv_flow.shape[:2] != annotated.shape[:2]:
        hsv_flow = cv2.resize(hsv_flow, (annotated.shape[1], annotated.shape[0]))

    return np.hstack([annotated, heatmap, hsv_flow])