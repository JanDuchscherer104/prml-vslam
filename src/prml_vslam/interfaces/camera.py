"""Canonical shared camera and pose models."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Self

import numpy as np
from numpy.typing import NDArray
from pydantic import ConfigDict
from pytransform3d.rotations import matrix_from_quaternion, quaternion_from_matrix
from pytransform3d.transformations import transform_from

from prml_vslam.utils.base_data import BaseData


class CameraIntrinsics(BaseData):
    """Canonical pinhole intrinsics with optional image and distortion metadata."""

    model_config = ConfigDict(frozen=True)

    fx: float
    fy: float
    cx: float
    cy: float
    width_px: int | None = None
    height_px: int | None = None
    distortion_model: str | None = None
    distortion_coefficients: tuple[float, ...] = ()

    def as_matrix(self) -> NDArray[np.float64]:
        """Return the intrinsics as a 3x3 camera matrix."""
        return np.array(
            [
                [self.fx, 0.0, self.cx],
                [0.0, self.fy, self.cy],
                [0.0, 0.0, 1.0],
            ],
            dtype=np.float64,
        )

    def to_latex(self) -> str:
        """Return the canonical LaTeX camera-intrinsics matrix display."""
        return (
            "K = \\begin{bmatrix}"
            f"{self.fx:.3f} & 0.000 & {self.cx:.3f} \\\\ "
            f"0.000 & {self.fy:.3f} & {self.cy:.3f} \\\\ "
            "0.000 & 0.000 & 1.000"
            "\\end{bmatrix}"
        )

    @classmethod
    def from_matrix(
        cls,
        matrix: NDArray[np.float64] | list[list[float]],
        *,
        width_px: int | None = None,
        height_px: int | None = None,
        distortion_model: str | None = None,
        distortion_coefficients: Sequence[float] = (),
    ) -> Self:
        """Build intrinsics from a 3x3 row-major camera matrix."""
        matrix_array = np.asarray(matrix, dtype=np.float64)
        if matrix_array.shape != (3, 3):
            raise ValueError(f"Expected a 3x3 intrinsic matrix, got shape {matrix_array.shape}.")
        return cls(
            fx=float(matrix_array[0, 0]),
            fy=float(matrix_array[1, 1]),
            cx=float(matrix_array[0, 2]),
            cy=float(matrix_array[1, 2]),
            width_px=width_px,
            height_px=height_px,
            distortion_model=distortion_model,
            distortion_coefficients=tuple(float(value) for value in distortion_coefficients),
        )

    @classmethod
    def from_column_major_flat_k(
        cls,
        values: Sequence[float],
        **kwargs: int | str | Sequence[float] | None,
    ) -> Self:
        """Build intrinsics from a flat 9-value column-major matrix payload."""
        if len(values) != 9:
            raise ValueError(f"Expected 9 values for a flat intrinsic matrix, got {len(values)}.")
        matrix = np.asarray(values, dtype=np.float64).reshape((3, 3), order="F")
        return cls.from_matrix(matrix, **kwargs)

    @classmethod
    def from_row_major_flat_k(
        cls,
        values: Sequence[float],
        **kwargs: int | str | Sequence[float] | None,
    ) -> Self:
        """Build intrinsics from a flat 9-value row-major matrix payload."""
        if len(values) != 9:
            raise ValueError(f"Expected 9 values for a flat intrinsic matrix, got {len(values)}.")
        matrix = np.asarray(values, dtype=np.float64).reshape((3, 3))
        return cls.from_matrix(matrix, **kwargs)


class SE3Pose(BaseData):
    """Rigid camera pose with camera-to-world semantics."""

    model_config = ConfigDict(frozen=True)

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
    ) -> Self:
        """Build a pose from XYZW quaternion and XYZ translation arrays."""
        return cls(
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
            raise ValueError("SE3 quaternion must be non-zero.")
        return quaternion / norm

    def translation_xyz(self) -> NDArray[np.float64]:
        """Return the translation vector in XYZ order."""
        return np.array([self.tx, self.ty, self.tz], dtype=np.float64)

    def as_matrix(self) -> NDArray[np.float64]:
        """Return the camera-to-world transform as a 4x4 matrix."""
        quaternion_wxyz = self.quaternion_xyzw()[[3, 0, 1, 2]]
        rotation = matrix_from_quaternion(quaternion_wxyz)
        return transform_from(rotation, self.translation_xyz(), strict_check=False)

    @classmethod
    def from_matrix(cls, matrix: NDArray[np.float64]) -> Self:
        """Build a camera-to-world pose from a 4x4 homogeneous transform."""
        matrix_array = np.asarray(matrix, dtype=np.float64)
        if matrix_array.shape != (4, 4):
            raise ValueError(f"Expected a 4x4 pose matrix, got shape {matrix_array.shape}.")
        if not np.allclose(matrix_array[3], np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float64)):
            raise ValueError("SE3 matrices must have a final row of [0, 0, 0, 1].")
        quaternion_wxyz = quaternion_from_matrix(matrix_array[:3, :3])
        return cls.from_quaternion_translation(quaternion_wxyz[[1, 2, 3, 0]], matrix_array[:3, 3])

    def to_tum_fields(self) -> tuple[float, float, float, float, float, float, float]:
        """Return the pose fields in TUM trajectory order."""
        qx, qy, qz, qw = self.quaternion_xyzw()
        return (self.tx, self.ty, self.tz, float(qx), float(qy), float(qz), float(qw))
