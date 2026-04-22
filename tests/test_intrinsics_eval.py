"""Tests for camera-intrinsics comparison utilities."""

from __future__ import annotations

import numpy as np

from prml_vslam.eval.intrinsics import compare_camera_intrinsics_series
from prml_vslam.interfaces import CameraIntrinsics, CameraIntrinsicsSeries


def test_compare_camera_intrinsics_series_reports_residuals_and_mean() -> None:
    estimated = CameraIntrinsicsSeries.from_matrices(
        np.asarray(
            [
                [[10.0, 0.0, 5.0], [0.0, 11.0, 6.0], [0.0, 0.0, 1.0]],
                [[12.0, 0.0, 6.0], [0.0, 15.0, 8.0], [0.0, 0.0, 1.0]],
            ],
            dtype=np.float64,
        ),
        raster_space="model",
        source="test",
        width_px=224,
        height_px=224,
    )
    reference = CameraIntrinsics(fx=9.0, fy=10.0, cx=4.0, cy=5.0, width_px=224, height_px=224)

    comparison = compare_camera_intrinsics_series(estimated_intrinsics=estimated, reference=reference)

    assert comparison.raster_space == "model"
    assert comparison.reference == reference
    assert comparison.mean_estimate == CameraIntrinsics(
        fx=11.0,
        fy=13.0,
        cx=5.5,
        cy=7.0,
        width_px=224,
        height_px=224,
    )
    assert comparison.fx_residual_px == [1.0, 3.0]
    assert comparison.fy_residual_px == [1.0, 5.0]
    assert comparison.cx_residual_px == [1.0, 2.0]
    assert comparison.cy_residual_px == [1.0, 3.0]
