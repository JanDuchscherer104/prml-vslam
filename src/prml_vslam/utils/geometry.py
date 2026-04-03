"""Shared geometry helpers used across repository-owned interfaces."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Self

import numpy as np
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
    pose_array = np.asarray(
        [(pose.tx, pose.ty, pose.tz, pose.qx, pose.qy, pose.qz, pose.qw) for pose in poses],
        dtype=np.float64,
    )
    if len(pose_array):
        quaternion_norms = np.linalg.norm(pose_array[:, 3:], axis=1, keepdims=True)
        if np.any(quaternion_norms == 0.0):
            raise ValueError("SE3 quaternions must be non-zero.")
        tum_rows = np.column_stack(
            (
                np.asarray(timestamps, dtype=np.float64),
                pose_array[:, :3],
                pose_array[:, 3:] / quaternion_norms,
            )
        )
    else:
        tum_rows = np.empty((0, 8), dtype=np.float64)
    np.savetxt(
        trajectory_path,
        tum_rows,
        fmt=f"%.{decimal_places}f",
        header="timestamp tx ty tz qx qy qz qw" if include_header else "",
        comments="# ",
    )
    return trajectory_path.resolve()


__all__ = [
    "ImageSize",
    "write_tum_trajectory",
]
