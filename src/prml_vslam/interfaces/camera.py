"""Canonical camera-intrinsics DTO shared across the package.

This module owns :class:`CameraIntrinsics`, the repo-wide representation of a
pinhole camera model plus optional raster and distortion metadata. Dataset
loaders, IO transports, method wrappers, visualization helpers, and the
pipeline all use this DTO when they need a shared description of one camera
raster. It does not own frame transforms or runtime packets; see
:mod:`prml_vslam.interfaces.transforms` and :mod:`prml_vslam.interfaces.runtime`
for those boundaries.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Self

import numpy as np
from numpy.typing import NDArray
from pydantic import ConfigDict

from prml_vslam.utils.base_data import BaseData


class CameraIntrinsics(BaseData):
    """Describe one camera raster in a backend- and dataset-neutral way.

    Use this DTO whenever a package boundary needs stable focal lengths,
    principal point, optional raster size, and optional distortion metadata
    without depending on an upstream-specific calibration format. The object is
    shared by :class:`prml_vslam.interfaces.FramePacket`,
    :class:`prml_vslam.datasets.contracts.AdvioManifestAssets`, and method live
    updates such as :class:`prml_vslam.methods.updates.SlamUpdate`.
    """

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
        """Return the canonical 3x3 pinhole matrix for downstream math."""
        return np.array(
            [
                [self.fx, 0.0, self.cx],
                [0.0, self.fy, self.cy],
                [0.0, 0.0, 1.0],
            ],
            dtype=np.float64,
        )

    def to_latex(self) -> str:
        """Render the shared intrinsics matrix in the compact LaTeX form used by UI surfaces."""
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
        """Build the shared DTO from a conventional 3x3 row-major camera matrix."""
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
        """Build the shared DTO from a flat 9-value column-major payload."""
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
        """Build the shared DTO from a flat 9-value row-major payload."""
        if len(values) != 9:
            raise ValueError(f"Expected 9 values for a flat intrinsic matrix, got {len(values)}.")
        matrix = np.asarray(values, dtype=np.float64).reshape((3, 3))
        return cls.from_matrix(matrix, **kwargs)
