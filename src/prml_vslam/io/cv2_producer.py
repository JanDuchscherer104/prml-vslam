"""Small filesystem and tabular I/O helpers shared across the project."""

from __future__ import annotations

import csv
import shutil
import urllib.request
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import yaml
from pydantic import Field

from ..utils.base_config import BaseConfig


class TimestampedCsvSummary(BaseConfig):
    """Summary statistics for a time-indexed CSV stream."""

    sample_count: int = Field(default=0, ge=0)
    """Number of non-empty rows."""

    start_s: float | None = None
    """First timestamp in seconds."""

    end_s: float | None = None
    """Last timestamp in seconds."""

    duration_s: float | None = None
    """Observed temporal span in seconds."""

    approx_rate_hz: float | None = None
    """Approximate sample rate derived from count and duration."""


def iter_video_frames(
    video_path: Path,
    *,
    artifact_root: Path,
    stride: int = 1,
    max_frames: int | None = None,
    frame_timestamps_ns: list[int] | None = None,
) -> Iterator[dict[str, Any]]:
    """Decode a video and persist sampled frames into the run workspace."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        msg = f"Cannot open video: {video_path}"
        raise FileNotFoundError(msg)

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_idx = 0
    decoded = 0
    frames_dir = artifact_root / "input" / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if frame_idx % stride != 0:
                frame_idx += 1
                continue
            if max_frames is not None and decoded >= max_frames:
                break

            height, width = frame.shape[:2]
            frame_path = frames_dir / f"{decoded:06d}.png"
            if not cv2.imwrite(str(frame_path), frame):
                msg = f"Failed to persist decoded frame to {frame_path}"
                raise OSError(msg)

            yield {
                "frame_index": frame_idx,
                "width": width,
                "height": height,
                "ts_ns": (
                    frame_timestamps_ns[frame_idx]
                    if frame_timestamps_ns is not None and frame_idx < len(frame_timestamps_ns)
                    else int(frame_idx / fps * 1e9)
                ),
                "image_path": str(frame_path),
            }
            decoded += 1
            frame_idx += 1
    finally:
        cap.release()


def download_file(url: str, target_path: Path) -> Path:
    """Download ``url`` to ``target_path``."""
    with urllib.request.urlopen(url) as response, target_path.open("wb") as handle:
        shutil.copyfileobj(response, handle)
    return target_path


def load_yaml_file(path: Path) -> dict[str, Any]:
    """Load one YAML document as a dictionary."""
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = f"Expected a YAML mapping in {path}, got {type(payload).__name__}"
        raise ValueError(msg)
    return payload


def read_numeric_csv(path: Path, *, columns: int | None = None) -> list[list[float]]:
    """Read a numeric CSV file into a list of float rows."""
    rows: list[list[float]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        for row in reader:
            if not row:
                continue
            if columns is not None and len(row) < columns:
                msg = f"Expected at least {columns} columns in {path}, got {len(row)}"
                raise ValueError(msg)
            width = columns if columns is not None else len(row)
            rows.append([float(value) for value in row[:width]])
    return rows


def summarize_timestamped_csv(path: Path) -> TimestampedCsvSummary:
    """Summarize a CSV stream whose first column stores timestamps in seconds."""
    start_s: float | None = None
    end_s: float | None = None
    sample_count = 0

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        for row in reader:
            if not row:
                continue
            timestamp_s = float(row[0])
            if start_s is None:
                start_s = timestamp_s
            end_s = timestamp_s
            sample_count += 1

    duration_s = None
    approx_rate_hz = None
    if start_s is not None and end_s is not None:
        duration_s = max(end_s - start_s, 0.0)
        if duration_s > 0 and sample_count > 1:
            approx_rate_hz = (sample_count - 1) / duration_s

    return TimestampedCsvSummary(
        sample_count=sample_count,
        start_s=start_s,
        end_s=end_s,
        duration_s=duration_s,
        approx_rate_hz=approx_rate_hz,
    )


def interpolate_numeric_rows(
    target_timestamps_s: list[float],
    source_timestamps_s: list[float],
    source_values: list[list[float]],
) -> list[list[float]]:
    """Interpolate vector-valued source samples onto ``target_timestamps_s``."""
    if len(source_timestamps_s) != len(source_values):
        msg = "source_timestamps_s and source_values must have the same length"
        raise ValueError(msg)
    if not target_timestamps_s or not source_timestamps_s:
        return []

    source_timestamps = np.asarray(source_timestamps_s, dtype=float)
    if np.any(np.diff(source_timestamps) < 0):
        msg = "source_timestamps_s must be sorted in ascending order"
        raise ValueError(msg)

    values = np.asarray(source_values, dtype=float)
    if values.ndim != 2:
        msg = "source_values must be a 2D array-like structure"
        raise ValueError(msg)

    target_timestamps = np.asarray(target_timestamps_s, dtype=float)
    interpolated = np.column_stack(
        [
            np.interp(target_timestamps, source_timestamps, values[:, column_index])
            for column_index in range(values.shape[1])
        ]
    )
    return interpolated.tolist()


def resolve_first_existing(root: Path, names: tuple[str, ...]) -> Path:
    """Return the first existing child path under ``root`` from ``names``."""
    for name in names:
        candidate = root / name
        if candidate.exists():
            return candidate
    msg = f"None of the expected files exist under {root}: {', '.join(names)}"
    raise FileNotFoundError(msg)
