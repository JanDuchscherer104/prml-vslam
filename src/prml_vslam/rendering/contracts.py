"""Typed contracts for point-cloud view rendering.

These DTOs are the inputs and outputs of
:mod:`prml_vslam.rendering.point_cloud_renderer`. A :class:`RenderedView` is the
generated-image side of an image-quality comparison: it carries the rendered RGB
frame, its metric depth, the coverage mask of which pixels a (sparse) cloud
actually filled, and the camera the view was rendered from.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from pydantic import ConfigDict, Field

from prml_vslam.interfaces.camera import CameraIntrinsics
from prml_vslam.interfaces.transforms import FrameTransform
from prml_vslam.utils import BaseData


class RenderConfig(BaseData):
    """Configure point-cloud rasterization into an RGB-D view."""

    model_config = ConfigDict(frozen=True)

    depth_scale: float = Field(default=1000.0, gt=0.0)
    """Open3D depth encoding factor; metric depth is recovered as ``depth / depth_scale``."""

    depth_max_m: float = Field(default=50.0, gt=0.0)
    """Maximum rendered depth in meters; points farther than this are dropped."""

    dilation_px: int = Field(default=0, ge=0)
    """Optional morphological hole-fill radius for sparse projections (``0`` = raw projection)."""

    background_rgb: tuple[int, int, int] = (0, 0, 0)
    """RGB color written to pixels no point projected onto."""

    default_point_color_rgb: tuple[int, int, int] = (128, 128, 128)
    """Fallback per-point color used when the cloud carries no colors."""


class RenderedView(BaseData):
    """One rendered point-cloud view paired with its coverage and camera."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    rgb: NDArray[np.uint8]
    """Rendered RGB image, shape ``(H, W, 3)`` uint8."""

    depth_m: NDArray[np.float32]
    """Rendered metric depth in meters, shape ``(H, W)``; ``0`` where no point projected."""

    coverage: NDArray[np.bool_]
    """Boolean mask, shape ``(H, W)``, ``True`` where a point filled the pixel."""

    intrinsics: CameraIntrinsics
    """Camera model the view was rendered with."""

    pose: FrameTransform
    """``world <- camera`` pose the view was rendered from."""

    def coverage_fraction(self) -> float:
        """Return the fraction of pixels a point projected onto."""
        return float(np.count_nonzero(self.coverage) / self.coverage.size)


__all__ = ["RenderConfig", "RenderedView"]
