from pathlib import Path
from typing import Iterator, Optional
import subprocess
import json
import cv2
import numpy as np


def probe_video(video_path: str | Path) -> dict:
    """
    Extract video metadata using ffprobe.

    Returns a dict with:
        fps, duration_s, width, height, total_frames, codec
    """
    video_path = str(video_path)

    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries",
        "stream=width,height,r_frame_rate,nb_frames,codec_name,duration",
        "-of", "json",
        video_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data   = json.loads(result.stdout)

    if not data.get("streams"):
        raise ValueError(f"No video stream found in {video_path}")

    stream = data["streams"][0]

    # r_frame_rate "30000/1001" o "30/1"
    num, den = stream["r_frame_rate"].split("/")
    fps      = float(num) / float(den) if float(den) > 0 else 0.0

    total_frames = int(stream.get("nb_frames", 0)) if stream.get("nb_frames") else None
    duration_s   = float(stream.get("duration", 0.0)) if stream.get("duration") else None

    return {
        "fps":          fps,
        "duration_s":   duration_s,
        "width":        int(stream["width"]),
        "height":       int(stream["height"]),
        "total_frames": total_frames,
        "codec":        stream.get("codec_name", "unknown"),
    }


def iter_video_frames(
    video_path: str | Path,
    start_frame: int = 0,
    max_frames: Optional[int] = None,
) -> Iterator[tuple[int, np.ndarray]]:
    """
    Iterate over frames of a video.

    Yields (frame_index, frame_bgr) tuples.
    frame_bgr is a numpy uint8 array in BGR format (OpenCV native).

    Args:
        video_path:   path to video file
        start_frame:  index of first frame to yield
        max_frames:   optional cap on number of frames to yield
    """
    video_path = str(video_path)
    cap        = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        raise IOError(f"Cannot open video: {video_path}")

    if start_frame > 0:
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    frame_idx = start_frame
    yielded   = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            yield frame_idx, frame

            frame_idx += 1
            yielded   += 1

            if max_frames is not None and yielded >= max_frames:
                break
    finally:
        cap.release()


def read_frame_at(video_path: str | Path, frame_index: int) -> np.ndarray:
    """
    Read a single frame at a specific index.
    Useful for thumbnails and one-off inspections.
    """
    video_path = str(video_path)
    cap        = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        raise IOError(f"Cannot open video: {video_path}")

    try:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ret, frame = cap.read()

        if not ret:
            raise ValueError(f"Cannot read frame {frame_index} from {video_path}")

        return frame
    finally:
        cap.release()


def resize_preserving_aspect(
    frame_bgr: np.ndarray,
    target_width: int,
    multiple_of: int = 8,
) -> np.ndarray:
    """
    Resize frame so width equals target_width and both
    dimensions are multiples of `multiple_of`.

    Preserves aspect ratio. Required for RAFT  and SegFormer models.
    """
    h_orig, w_orig = frame_bgr.shape[:2]

    scale  = target_width / w_orig
    w_new  = target_width
    h_new  = int(h_orig * scale)

    w_new  = (w_new // multiple_of) * multiple_of
    h_new  = (h_new // multiple_of) * multiple_of

    return cv2.resize(frame_bgr, (w_new, h_new), interpolation=cv2.INTER_LINEAR)


def frame_pair_iterator(
    video_path: str | Path,
    max_frames: Optional[int] = None,
) -> Iterator[tuple[int, np.ndarray, np.ndarray]]:
    """
    Iterate over consecutive frame pairs.

    Yields (frame_index, prev_frame, curr_frame) for each pair.
    Used by the pipeline for optical flow computation.
    """
    iterator = iter_video_frames(video_path, max_frames=max_frames)

    try:
        _, prev_frame = next(iterator)
    except StopIteration:
        return

    for idx, curr_frame in iterator:
        
        yield idx, prev_frame, curr_frame
        prev_frame = curr_frame