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
    """Serializable rigid transform with explicit frame direction.

    When frame labels are omitted, the repository default is the canonical
    runtime camera pose convention: `camera -> world`.
    """

    model_config = ConfigDict(frozen=True)

    target_frame: str = "world"
    """Frame whose coordinates the transform maps into."""

    source_frame: str = "camera"
    """Frame whose coordinates the transform maps from."""

    qx: float
    qy: float
    qz: float
    qw: float
    tx: float
    ty: float
    tz: float

    @classmethod
    def from_quaternion_translation(
        cls,
        quaternion_xyzw: NDArray[np.float64],
        translation_xyz: NDArray[np.float64],
        *,
        target_frame: str = "world",
        source_frame: str = "camera",
    ) -> Self:
        """Build a transform from XYZW quaternion and XYZ translation arrays."""
        return cls(
            target_frame=target_frame,
            source_frame=source_frame,
            qx=float(quaternion_xyzw[0]),
            qy=float(quaternion_xyzw[1]),
            qz=float(quaternion_xyzw[2]),
            qw=float(quaternion_xyzw[3]),
            tx=float(translation_xyz[0]),
            ty=float(translation_xyz[1]),
            tz=float(translation_xyz[2]),
        )

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
        target_frame: str = "world",
        source_frame: str = "camera",
    ) -> Self:
        """Build a transform from a 4x4 homogeneous matrix."""
        matrix_array = np.asarray(matrix, dtype=np.float64)
        if matrix_array.shape != (4, 4):
            raise ValueError(f"Expected a 4x4 pose matrix, got shape {matrix_array.shape}.")
        if not np.allclose(matrix_array[3], np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float64)):
            raise ValueError("FrameTransform matrices must have a final row of [0, 0, 0, 1].")
        quaternion_wxyz = quaternion_from_matrix(matrix_array[:3, :3])
        return cls.from_quaternion_translation(
            quaternion_wxyz[[1, 2, 3, 0]],
            matrix_array[:3, 3],
            target_frame=target_frame,
            source_frame=source_frame,
        )

    def to_tum_fields(self) -> tuple[float, float, float, float, float, float, float]:
        """Return the transform fields in TUM trajectory order."""
        qx, qy, qz, qw = self.quaternion_xyzw()
        return (self.tx, self.ty, self.tz, float(qx), float(qy), float(qz), float(qw))


__all__ = ["FrameTransform"]
