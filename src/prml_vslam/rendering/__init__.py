"""Headless rendering of VSLAM geometry into images for evaluation.

The :mod:`prml_vslam.rendering` package produces the *generated* image side of an
image-quality comparison. :class:`PointCloudRenderer` rasterizes a colored
world-space point cloud (such as a SLAM dense cloud) from a camera pose and
intrinsics into an RGB-D :class:`RenderedView`, using Open3D's GL-free tensor
projection so it runs headless. The rendered RGB pairs directly with
:mod:`prml_vslam.eval.image_metrics`; the view's coverage mask lets metrics
ignore pixels a sparse cloud never filled.
"""

from .contracts import RenderConfig, RenderedView
from .point_cloud_renderer import (
    PointCloudRenderer,
    poses_from_tum_trajectory,
    render_trajectory_views,
    write_image_rgb,
)

__all__ = [
    "PointCloudRenderer",
    "RenderConfig",
    "RenderedView",
    "poses_from_tum_trajectory",
    "render_trajectory_views",
    "write_image_rgb",
]
