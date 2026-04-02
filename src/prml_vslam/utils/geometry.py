"""Shared geometry primitives used across repository-owned interfaces."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Self

import numpy as np
from numpy.typing import NDArray
from pydantic import ConfigDict
from pytransform3d.rotations import matrix_from_quaternion, quaternion_from_matrix
from pytransform3d.transformations import transform_from

from .base_config import BaseConfig


class ImageSize(BaseConfig):
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


class CameraIntrinsics(BaseConfig):
    """Pinhole camera intrinsics without distortion parameters."""

    model_config = ConfigDict(frozen=True)

    fx: float
    """Focal length in pixels along the x axis."""

    fy: float
    """Focal length in pixels along the y axis."""

    cx: float
    """Principal-point x coordinate in pixels."""

    cy: float
    """Principal-point y coordinate in pixels."""

    def as_matrix(self) -> NDArray[np.float64]:
        """Return the intrinsic coefficients as a 3x3 camera matrix.

        Returns:
            Matrix ``K`` in row-major form.
        """
        return np.array(
            [
                [self.fx, 0.0, self.cx],
                [0.0, self.fy, self.cy],
                [0.0, 0.0, 1.0],
            ],
            dtype=np.float64,
        )

    @classmethod
    def from_matrix(cls, matrix: NDArray[np.float64] | list[list[float]]) -> Self:
        """Build intrinsics from a 3x3 row-major camera matrix.

        Args:
            matrix: Camera matrix in row-major layout.

        Returns:
            Normalized camera-intrinsics model.
        """
        matrix_array = np.asarray(matrix, dtype=np.float64)
        if matrix_array.shape != (3, 3):
            raise ValueError(f"Expected a 3x3 intrinsic matrix, got shape {matrix_array.shape}.")
        return cls(
            fx=float(matrix_array[0, 0]),
            fy=float(matrix_array[1, 1]),
            cx=float(matrix_array[0, 2]),
            cy=float(matrix_array[1, 2]),
        )

    @classmethod
    def from_column_major_flat_k(cls, values: Sequence[float]) -> Self:
        """Build intrinsics from a flat 9-value column-major matrix payload.

        Args:
            values: Flat 9-value sequence encoded in column-major order.

        Returns:
            Normalized camera-intrinsics model.
        """
        if len(values) != 9:
            raise ValueError(f"Expected 9 values for a flat intrinsic matrix, got {len(values)}.")
        matrix = np.asarray(values, dtype=np.float64).reshape((3, 3), order="F")
        return cls.from_matrix(matrix)

    @classmethod
    def from_row_major_flat_k(cls, values: Sequence[float]) -> Self:
        """Build intrinsics from a flat 9-value row-major matrix payload.

        Args:
            values: Flat 9-value sequence encoded in row-major order.

        Returns:
            Normalized camera-intrinsics model.
        """
        if len(values) != 9:
            raise ValueError(f"Expected 9 values for a flat intrinsic matrix, got {len(values)}.")
        matrix = np.asarray(values, dtype=np.float64).reshape((3, 3))
        return cls.from_matrix(matrix)


class SE3Pose(BaseConfig):
    """Rigid camera pose with camera-to-world semantics.

    The stored transform represents ``camera_in_world``. Translation is the
    camera origin expressed in world coordinates, and the quaternion rotates
    camera-frame vectors into world coordinates.
    """

    model_config = ConfigDict(frozen=True)

    qx: float
    """Quaternion x component in XYZW order."""

    qy: float
    """Quaternion y component in XYZW order."""

    qz: float
    """Quaternion z component in XYZW order."""

    qw: float
    """Quaternion w component in XYZW order."""

    tx: float
    """Camera x position in world coordinates."""

    ty: float
    """Camera y position in world coordinates."""

    tz: float
    """Camera z position in world coordinates."""

    def quaternion_xyzw(self) -> NDArray[np.float64]:
        """Return the normalized quaternion in XYZW order.

        Returns:
            Unit quaternion in XYZW order.
        """
        quaternion = np.array([self.qx, self.qy, self.qz, self.qw], dtype=np.float64)
        norm = np.linalg.norm(quaternion)
        if norm == 0.0:
            raise ValueError("SE3 quaternion must be non-zero.")
        return quaternion / norm

    def translation_xyz(self) -> NDArray[np.float64]:
        """Return the translation vector in XYZ order.

        Returns:
            Translation vector in world coordinates.
        """
        return np.array([self.tx, self.ty, self.tz], dtype=np.float64)

    def as_matrix(self) -> NDArray[np.float64]:
        """Return the camera-to-world transform as a 4x4 matrix.

        Returns:
            Homogeneous transform matrix with camera-to-world semantics.
        """
        quaternion_xyzw = self.quaternion_xyzw()
        quaternion_wxyz = quaternion_xyzw[[3, 0, 1, 2]]
        rotation = matrix_from_quaternion(quaternion_wxyz)
        return transform_from(rotation, self.translation_xyz(), strict_check=False)

    @classmethod
    def from_matrix(cls, matrix: NDArray[np.float64]) -> Self:
        """Build a camera-to-world pose from a 4x4 homogeneous transform.

        Args:
            matrix: Homogeneous transform with camera-to-world semantics.

        Returns:
            Normalized pose model in quaternion-plus-translation form.
        """
        matrix_array = np.asarray(matrix, dtype=np.float64)
        if matrix_array.shape != (4, 4):
            raise ValueError(f"Expected a 4x4 pose matrix, got shape {matrix_array.shape}.")
        if not np.allclose(matrix_array[3], np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float64)):
            raise ValueError("SE3 matrices must have a final row of [0, 0, 0, 1].")

        quaternion_wxyz = quaternion_from_matrix(matrix_array[:3, :3])
        translation = matrix_array[:3, 3]
        return cls(
            qx=float(quaternion_wxyz[1]),
            qy=float(quaternion_wxyz[2]),
            qz=float(quaternion_wxyz[3]),
            qw=float(quaternion_wxyz[0]),
            tx=float(translation[0]),
            ty=float(translation[1]),
            tz=float(translation[2]),
        )

    def to_tum_fields(self) -> tuple[float, float, float, float, float, float, float]:
        """Return the pose fields in TUM trajectory order.

        Returns:
            Tuple ``(tx, ty, tz, qx, qy, qz, qw)``.
        """
        qx, qy, qz, qw = self.quaternion_xyzw()
        return (self.tx, self.ty, self.tz, float(qx), float(qy), float(qz), float(qw))


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
    "CameraIntrinsics",
    "ImageSize",
    "SE3Pose",
    "write_tum_trajectory",
]
