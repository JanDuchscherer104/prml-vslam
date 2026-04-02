"""IO helpers shared by external VSLAM method adapters."""

from __future__ import annotations

import json
import shutil
from collections.abc import Sequence
from pathlib import Path

import cv2

from prml_vslam.pipeline.workspace import CaptureManifest, FrameSample
from prml_vslam.utils.geometry import SE3Pose
from prml_vslam.utils.geometry import write_tum_trajectory as write_shared_tum_trajectory

IMAGE_SUFFIXES = {".bmp", ".jpeg", ".jpg", ".png", ".tif", ".tiff"}
VIDEO_SUFFIXES = {".avi", ".m4v", ".mov", ".mp4", ".mpeg", ".mpg"}


def is_video_path(path: Path) -> bool:
    """Return whether a path looks like a supported video capture."""
    return path.suffix.lower() in VIDEO_SUFFIXES


def ensure_directory(path: Path) -> Path:
    """Create a directory if needed and return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def list_image_files(input_dir: Path) -> list[Path]:
    """Return supported RGB image files in deterministic order."""
    image_paths = sorted(
        path for path in input_dir.iterdir() if path.suffix.lower() in IMAGE_SUFFIXES and path.is_file()
    )
    if not image_paths:
        raise FileNotFoundError(f"No RGB images found in '{input_dir}'.")
    return image_paths


def extract_video_frames(
    source_path: Path,
    *,
    frames_dir: Path,
    manifest_path: Path,
    frame_stride: int,
) -> CaptureManifest:
    """Decode a video into a stride-sampled PNG frame sequence.

    Args:
        source_path: Video file to decode.
        frames_dir: Output directory for stride-sampled PNG frames.
        manifest_path: JSON manifest path that records decoded timestamps.
        frame_stride: Sampling stride applied to the video stream.

    Returns:
        Persisted capture manifest describing the sampled frame sequence.
    """
    ensure_directory(frames_dir)
    ensure_directory(manifest_path.parent)

    capture = cv2.VideoCapture(source_path.as_posix())
    if not capture.isOpened():
        raise RuntimeError(f"Could not open video capture '{source_path}'.")

    fps_value = capture.get(cv2.CAP_PROP_FPS)
    fps = float(fps_value) if fps_value and fps_value > 0 else None
    frame_records: list[FrameSample] = []
    source_index = 0

    try:
        while True:
            success, frame_bgr = capture.read()
            if not success:
                break

            if source_index % frame_stride != 0:
                source_index += 1
                continue

            frame_index = len(frame_records)
            frame_path = frames_dir / f"frame_{frame_index:06d}.png"
            if not cv2.imwrite(frame_path.as_posix(), frame_bgr):
                raise RuntimeError(f"Failed to write decoded frame to '{frame_path}'.")

            timestamp_msec = float(capture.get(cv2.CAP_PROP_POS_MSEC))
            if timestamp_msec > 0:
                timestamp_seconds = timestamp_msec / 1000.0
            elif fps is not None:
                timestamp_seconds = source_index / fps
            else:
                timestamp_seconds = float(source_index)

            frame_records.append(
                FrameSample(
                    index=frame_index,
                    source_index=source_index,
                    timestamp_seconds=timestamp_seconds,
                    image_path=frame_path.resolve(),
                )
            )
            source_index += 1
    finally:
        capture.release()

    if not frame_records:
        raise RuntimeError(f"No frames were decoded from '{source_path}'.")

    manifest = CaptureManifest(
        source_path=source_path.resolve(),
        source_kind="video",
        frame_stride=frame_stride,
        fps=fps,
        frames=frame_records,
    )
    write_capture_manifest(manifest, manifest_path)
    return manifest


def materialize_image_directory(
    source_dir: Path,
    *,
    frames_dir: Path,
    manifest_path: Path,
    frame_stride: int,
) -> CaptureManifest:
    """Copy a stride-sampled image directory into a method-owned frame folder."""
    ensure_directory(frames_dir)
    ensure_directory(manifest_path.parent)

    source_images = list_image_files(source_dir)
    frame_records: list[FrameSample] = []

    for source_index, source_image in enumerate(source_images):
        if source_index % frame_stride != 0:
            continue

        frame_index = len(frame_records)
        destination = frames_dir / f"frame_{frame_index:06d}{source_image.suffix.lower()}"
        shutil.copy2(source_image, destination)
        frame_records.append(
            FrameSample(
                index=frame_index,
                source_index=source_index,
                timestamp_seconds=float(frame_index),
                image_path=destination.resolve(),
            )
        )

    if not frame_records:
        raise RuntimeError(f"No frames were materialized from '{source_dir}'.")

    manifest = CaptureManifest(
        source_path=source_dir.resolve(),
        source_kind="image_dir",
        frame_stride=frame_stride,
        frames=frame_records,
    )
    write_capture_manifest(manifest, manifest_path)
    return manifest


def write_capture_manifest(manifest: CaptureManifest, path: Path) -> Path:
    """Persist a capture manifest as JSON."""
    ensure_directory(path.parent)
    path.write_text(json.dumps(manifest.model_dump(mode="json"), indent=2), encoding="utf-8")
    return path.resolve()


def timestamps_for_view_names(manifest: CaptureManifest | None, view_names: list[str] | None) -> list[float]:
    """Resolve per-view timestamps from a capture manifest.

    Args:
        manifest: Capture manifest that maps materialized image names to times.
        view_names: Upstream view names that should map back to materialized
            image names.

    Returns:
        Timestamps aligned to the provided view names or a simple sequential
        fallback if the mapping is unavailable.
    """
    if manifest is None:
        if view_names is None:
            return []
        return [float(index) for index, _ in enumerate(view_names)]

    if view_names is None:
        return [frame.timestamp_seconds for frame in manifest.frames]

    timestamp_lookup = {frame.image_path.name: frame.timestamp_seconds for frame in manifest.frames}
    timestamps: list[float] = []
    missing_name = False
    for view_name in view_names:
        timestamp = timestamp_lookup.get(Path(view_name).name)
        if timestamp is None:
            missing_name = True
            break
        timestamps.append(timestamp)

    if missing_name:
        return [float(index) for index, _ in enumerate(view_names)]
    return timestamps


def write_tum_trajectory(trajectory_path: Path, poses: Sequence[SE3Pose], timestamps: Sequence[float]) -> Path:
    """Write a TUM-format trajectory from canonical SE(3) poses and timestamps."""
    return write_shared_tum_trajectory(trajectory_path, poses, timestamps)


__all__ = [
    "IMAGE_SUFFIXES",
    "VIDEO_SUFFIXES",
    "ensure_directory",
    "extract_video_frames",
    "is_video_path",
    "list_image_files",
    "materialize_image_directory",
    "timestamps_for_view_names",
    "write_capture_manifest",
    "write_tum_trajectory",
]
