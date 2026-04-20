"""Canonical shared camera intrinsics."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Self

import numpy as np
from numpy.typing import NDArray
from pydantic import ConfigDict

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
