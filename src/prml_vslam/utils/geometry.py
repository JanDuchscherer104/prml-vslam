"""Shared geometry helpers used across repository-owned interfaces."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Self

from pydantic import ConfigDict

from prml_vslam.interfaces import SE3Pose

from .base_data import BaseData


class ImageSize(BaseData):
    """Integer image resolution in pixels."""

    model_config = ConfigDict(frozen=True)

    width: int
    """Image width in pixels."""

    height: int
    """Image height in pixels."""

    @classmethod
    def from_payload(cls, payload: object) -> Self:
        """Normalize a width/height payload into an image-size model.

        Args:
            payload: Upstream payload encoded as either a mapping with
                ``width``/``height`` keys or a 2-value sequence.

        Returns:
            Normalized image size.
        """
        if isinstance(payload, dict):
            width = payload.get("width")
            height = payload.get("height")
            if isinstance(width, int) and isinstance(height, int):
                return cls(width=width, height=height)

        if isinstance(payload, list | tuple) and len(payload) == 2 and all(isinstance(value, int) for value in payload):
            return cls(width=int(payload[0]), height=int(payload[1]))

        raise TypeError("Image size must be encoded as {'width': int, 'height': int} or [width, height].")


def write_tum_trajectory(
    trajectory_path: Path,
    poses: Sequence[SE3Pose],
    timestamps: Sequence[float],
    *,
    include_header: bool = False,
    decimal_places: int = 6,
) -> Path:
    """Write a TUM trajectory file from canonical SE(3) poses and timestamps."""
    if len(poses) != len(timestamps):
        raise ValueError(f"Expected one timestamp per pose, got {len(timestamps)} timestamps for {len(poses)} poses.")

    trajectory_path.parent.mkdir(parents=True, exist_ok=True)
    format_spec = f".{decimal_places}f"
    lines = ["# timestamp tx ty tz qx qy qz qw"] if include_header else []

    for timestamp, pose in zip(timestamps, poses, strict=True):
        tx, ty, tz, qx, qy, qz, qw = pose.to_tum_fields()
        lines.append(" ".join(format(value, format_spec) for value in (timestamp, tx, ty, tz, qx, qy, qz, qw)))

    trajectory_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return trajectory_path.resolve()


__all__ = [
    "ImageSize",
    "write_tum_trajectory",
]
