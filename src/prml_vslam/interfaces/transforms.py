"""Explicit frame-labelled transform contracts."""

from __future__ import annotations

from typing import Self

import numpy as np
from numpy.typing import NDArray
from pydantic import ConfigDict
from pytransform3d.rotations import matrix_from_quaternion, quaternion_from_matrix
from pytransform3d.transformations import transform_from

from prml_vslam.utils import BaseData


class FrameTransform(BaseData):
    """Serializable rigid transform with explicit frame direction."""

    model_config = ConfigDict(frozen=True)

    target_frame: str
    """Frame whose coordinates the transform maps into."""

    source_frame: str
    """Frame whose coordinates the transform maps from."""

    qx: float
    qy: float
    qz: float
    qw: float
    tx: float
    ty: float
    tz: float
    timestamp_ns: int | None = None

    def quaternion_xyzw(self) -> NDArray[np.float64]:
        """Return the normalized quaternion in XYZW order."""
        quaternion = np.array([self.qx, self.qy, self.qz, self.qw], dtype=np.float64)
        norm = np.linalg.norm(quaternion)
        if norm == 0.0:
            raise ValueError("FrameTransform quaternion must be non-zero.")
        return quaternion / norm

    def translation_xyz(self) -> NDArray[np.float64]:
        """Return the translation vector in XYZ order."""
        return np.array([self.tx, self.ty, self.tz], dtype=np.float64)

    def as_matrix(self) -> NDArray[np.float64]:
        """Return the transform as a 4x4 matrix."""
        quaternion_wxyz = self.quaternion_xyzw()[[3, 0, 1, 2]]
        rotation = matrix_from_quaternion(quaternion_wxyz)
        return transform_from(rotation, self.translation_xyz(), strict_check=False)

    @classmethod
    def from_matrix(
        cls,
        matrix: NDArray[np.float64],
        *,
        target_frame: str,
        source_frame: str,
        timestamp_ns: int | None = None,
    ) -> Self:
        """Build a transform from a 4x4 homogeneous matrix."""
        matrix_array = np.asarray(matrix, dtype=np.float64)
        if matrix_array.shape != (4, 4):
            raise ValueError(f"Expected a 4x4 pose matrix, got shape {matrix_array.shape}.")
        if not np.allclose(matrix_array[3], np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float64)):
            raise ValueError("FrameTransform matrices must have a final row of [0, 0, 0, 1].")
        quaternion_wxyz = quaternion_from_matrix(matrix_array[:3, :3])
        return cls(
            target_frame=target_frame,
            source_frame=source_frame,
            qx=float(quaternion_wxyz[1]),
            qy=float(quaternion_wxyz[2]),
            qz=float(quaternion_wxyz[3]),
            qw=float(quaternion_wxyz[0]),
            tx=float(matrix_array[0, 3]),
            ty=float(matrix_array[1, 3]),
            tz=float(matrix_array[2, 3]),
            timestamp_ns=timestamp_ns,
        )


__all__ = ["FrameTransform"]
