"""Camera-intrinsics comparison utilities."""

from __future__ import annotations

import numpy as np

from prml_vslam.eval.contracts import IntrinsicsComparisonDiagnostics
from prml_vslam.interfaces.camera import CameraIntrinsics, CameraIntrinsicsSeries


def compare_camera_intrinsics_series(
    *,
    estimated_intrinsics: CameraIntrinsicsSeries,
    reference: CameraIntrinsics,
) -> IntrinsicsComparisonDiagnostics:
    """Compare one estimated intrinsics series against a reference camera model."""
    if not estimated_intrinsics.samples:
        raise ValueError("Cannot compare an empty estimated intrinsics series.")
    estimates = np.asarray([sample.intrinsics.as_matrix() for sample in estimated_intrinsics.samples], dtype=np.float64)
    fx = estimates[:, 0, 0]
    fy = estimates[:, 1, 1]
    cx = estimates[:, 0, 2]
    cy = estimates[:, 1, 2]
    return IntrinsicsComparisonDiagnostics(
        raster_space=estimated_intrinsics.raster_space,
        reference=reference,
        mean_estimate=CameraIntrinsics(
            fx=float(fx.mean()),
            fy=float(fy.mean()),
            cx=float(cx.mean()),
            cy=float(cy.mean()),
            width_px=estimated_intrinsics.width_px,
            height_px=estimated_intrinsics.height_px,
        ),
        fx_residual_px=(fx - reference.fx).tolist(),
        fy_residual_px=(fy - reference.fy).tolist(),
        cx_residual_px=(cx - reference.cx).tolist(),
        cy_residual_px=(cy - reference.cy).tolist(),
    )


__all__ = ["compare_camera_intrinsics_series"]
