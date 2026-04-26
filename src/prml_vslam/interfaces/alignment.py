"""Alignment result DTOs shared outside the alignment package.

These datamodels describe derived viewer/world-up alignment artifacts. They do
not replace native SLAM output frames; instead they preserve explicit
``world`` to ``viewer_world`` semantics for visualization and inspection.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from prml_vslam.interfaces.transforms import FrameTransform
from prml_vslam.utils import BaseData


class GroundPlaneModel(BaseData):
    """Dominant ground-plane hypothesis expressed in native ``world`` coordinates.

    The normal and offset use the same world frame as the source SLAM point
    cloud. Consumers must apply any derived viewer transform explicitly instead
    of relabelling this model as already aligned.
    """

    normal_xyz_world: tuple[float, float, float]
    offset_world: float
    inlier_count: int
    inlier_ratio: float


class GroundPlaneVisualizationHint(BaseData):
    """Finite plane-patch geometry ready for visualization consumers."""

    frame: Literal["world"] = "world"
    corners_xyz_world: list[tuple[float, float, float]] = Field(default_factory=list)


class GroundAlignmentMetadata(BaseData):
    """Result of one derived ground-plane alignment attempt.

    When :attr:`applied` is true, :attr:`T_viewer_world_world` maps native
    backend ``world`` coordinates into the derived ``viewer_world`` frame. When
    false, skip diagnostics explain why no transform should be used.
    """

    applied: bool
    confidence: float
    point_cloud_source: Literal["dense_points_ply", "sparse_points_ply", "none"]
    ground_plane_world: GroundPlaneModel | None = None
    T_viewer_world_world: FrameTransform | None = None
    up_source: Literal["ground_plane"] = "ground_plane"
    yaw_source: Literal["trajectory_pca", "identity"] = "identity"
    candidate_count: int = 0
    support_ratio: float | None = None
    median_camera_height_world: float | None = None
    camera_height_spread_world: float | None = None
    camera_down_alignment: float | None = None
    skip_reason: str | None = None
    visualization: GroundPlaneVisualizationHint | None = None


__all__ = [
    "GroundAlignmentMetadata",
    "GroundPlaneModel",
    "GroundPlaneVisualizationHint",
]
