"""Explicit frame-labelled transform contracts shared across the repository.

This module owns :class:`FrameTransform`, the canonical rigid-transform DTO
used for runtime poses, dataset calibration, alignment outputs, and viewer
placement metadata. It centralizes transform semantics so packages can exchange
poses without inventing parallel matrix or quaternion formats.
"""

from __future__ import annotations

from typing import Self

import numpy as np
from numpy.typing import NDArray
from pydantic import ConfigDict
from pytransform3d.rotations import (
    check_matrix,
    matrix_from_quaternion,
    quaternion_from_matrix,
    robust_polar_decomposition,
)
from pytransform3d.transformations import transform_from

from prml_vslam.utils import BaseData


class FrameTransform(BaseData):
    """Serializable rigid transform with explicit frame direction.

    The transform maps coordinates from :attr:`source_frame` into
    :attr:`target_frame`. When frame labels are omitted, the repository default
    is the canonical runtime camera pose convention ``world <- camera``:
    translation is the camera origin expressed in world coordinates, and
    rotation maps camera-frame vectors into the named world frame. Cross-system
    alignment transforms should use explicit frame names such as
    ``viewer_world`` or ``tango_world`` rather than assuming all ``world``
    labels are interchangeable.
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
        """Build the shared transform DTO from XYZW quaternion and XYZ translation arrays."""
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
        """Return the normalized unit quaternion in XYZW order."""
        quaternion = np.array([self.qx, self.qy, self.qz, self.qw], dtype=np.float64)
        norm = np.linalg.norm(quaternion)
        if norm == 0.0:
            raise ValueError("FrameTransform quaternion must be non-zero.")
        return quaternion / norm

    def translation_xyz(self) -> NDArray[np.float64]:
        """Return the translation component in XYZ order."""
        return np.array([self.tx, self.ty, self.tz], dtype=np.float64)

    def as_matrix(self) -> NDArray[np.float64]:
        """Return the transform as a 4x4 homogeneous matrix."""
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
        """Build the shared transform DTO from a 4x4 homogeneous matrix."""
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
        """Return translation and quaternion fields in canonical TUM trajectory order."""
        qx, qy, qz, qw = self.quaternion_xyzw()
        return (self.tx, self.ty, self.tz, float(qx), float(qy), float(qz), float(qw))


def project_rotation_to_so3(rotation: NDArray[np.float64], *, max_frobenius_error: float = 2e-3) -> NDArray[np.float64]:
    """Project one near-rotation matrix into a validated SO(3) rotation.

    Use this helper when an upstream system or numeric procedure yields a
    slightly non-orthonormal 3x3 matrix that still belongs on a
    :class:`FrameTransform`. It is intentionally strict so invalid geometry does
    not silently cross package boundaries.
    """
    rotation_array = np.asarray(rotation, dtype=np.float64)
    if rotation_array.shape != (3, 3):
        raise ValueError(f"Expected a 3x3 rotation matrix, got shape {rotation_array.shape}.")
    if not np.all(np.isfinite(rotation_array)):
        raise ValueError("Rotation matrices must contain only finite values.")
    projected = robust_polar_decomposition(rotation_array)
    projection_error = np.linalg.norm(rotation_array - projected, ord="fro")
    if not np.isfinite(projection_error) or projection_error > max_frobenius_error:
        raise ValueError(
            f"Rotation matrix is too far from SO(3) to normalize safely. Frobenius error: {projection_error:.6f}."
        )
    return check_matrix(projected)


__all__ = ["FrameTransform", "project_rotation_to_so3"]
