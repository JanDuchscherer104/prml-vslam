"""Shared video-frame materialization helpers."""

from __future__ import annotations

import shutil
from pathlib import Path

import cv2

from .base_data import BaseData


class ExtractedVideoFrames(BaseData):
    """Materialized RGB frames plus their derived timestamps."""

    rgb_dir: Path
    timestamps_ns: list[int]


def extract_video_frames(
    *,
    video_path: Path,
    output_dir: Path,
    frame_stride: int = 1,
    max_frames: int | None = None,
    clear_output: bool = True,
) -> ExtractedVideoFrames:
    """Extract PNG frames from one video with deterministic timestamps."""
    if clear_output and output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise FileNotFoundError(f"Cannot open video: {video_path}")

    timestamps_ns: list[int] = []
    frame_index = 0
    written_index = 0
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    try:
        while True:
            ok, frame_bgr = capture.read()
            if not ok:
                break
            if frame_index % frame_stride != 0:
                frame_index += 1
                continue
            if max_frames is not None and written_index >= max_frames:
                break
            timestamp_ns = int(round(frame_index / fps * 1e9)) if fps > 0.0 else int(frame_index * 1e9 / 30.0)
            frame_path = output_dir / f"{written_index:06d}.png"
            if not cv2.imwrite(str(frame_path), frame_bgr):
                raise RuntimeError(f"Failed to write extracted frame to '{frame_path}'.")
            timestamps_ns.append(timestamp_ns)
            written_index += 1
            frame_index += 1
    finally:
        capture.release()
    return ExtractedVideoFrames(rgb_dir=output_dir.resolve(), timestamps_ns=timestamps_ns)


__all__ = ["ExtractedVideoFrames", "extract_video_frames"]
