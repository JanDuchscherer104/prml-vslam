"""Typed contracts for derived ground-plane alignment."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from prml_vslam.interfaces import FrameTransform
from prml_vslam.utils import BaseConfig, BaseData


class GroundAlignmentConfig(BaseConfig):
    """Policy for the optional dominant-ground alignment stage."""

    enabled: bool = False
    """Whether the `ground.align` stage should run."""

    strategy: Literal["ransac_point_cloud"] = "ransac_point_cloud"
    """Detection strategy used to estimate the dominant ground plane."""

    min_confidence: float = Field(default=0.6, ge=0.0, le=1.0)
    """Minimum confidence required before the alignment is applied."""


class AlignmentConfig(BaseConfig):
    """Top-level alignment policy bundle attached to one run request."""

    ground: GroundAlignmentConfig = Field(default_factory=GroundAlignmentConfig)
    """Ground-plane detection and viewer-alignment policy."""


class GroundPlaneModel(BaseData):
    """Dominant ground-plane hypothesis expressed in native `world` coordinates."""

    normal_xyz_world: tuple[float, float, float]
    """Unit plane normal expressed in native `world` coordinates."""

    offset_world: float
    """Signed plane offset for the equation `n . x + d = 0` in native `world`."""

    inlier_count: int
    """Number of inlier points supporting the plane."""

    inlier_ratio: float
    """Fraction of processed point-cloud samples classified as plane inliers."""


class GroundPlaneVisualizationHint(BaseData):
    """Finite plane-patch geometry ready for a future visualization consumer."""

    frame: Literal["world"] = "world"
    """Frame represented by the stored patch corners."""

    corners_xyz_world: list[tuple[float, float, float]] = Field(default_factory=list)
    """Plane-patch corners expressed in native `world` coordinates."""


class GroundAlignmentMetadata(BaseData):
    """Result of one derived ground-plane alignment attempt."""

    applied: bool
    """Whether the stage produced an alignment transform above the confidence threshold."""

    confidence: float
    """Stage confidence in the selected dominant ground plane."""

    point_cloud_source: Literal["dense_points_ply", "sparse_points_ply", "none"]
    """Point-cloud artifact surface used by the stage."""

    ground_plane_world: GroundPlaneModel | None = None
    """Selected ground-plane model in native `world`, if one was accepted."""

    T_viewer_world_world: FrameTransform | None = None
    """Derived transform from native `world` into `viewer_world`."""

    up_source: Literal["ground_plane"] = "ground_plane"
    """Source used to define viewer up in this metadata-only implementation."""

    yaw_source: Literal["trajectory_pca", "identity"] = "identity"
    """Policy used to resolve the yaw gauge after leveling the dominant plane."""

    candidate_count: int = 0
    """Number of plane candidates scored during detection."""

    support_ratio: float | None = None
    """Inlier support ratio of the selected or best candidate."""

    median_camera_height_world: float | None = None
    """Median signed camera height above the selected plane in native `world`."""

    camera_height_spread_world: float | None = None
    """Spread of signed camera heights above the selected plane in native `world`."""

    camera_down_alignment: float | None = None
    """Median alignment of the plane normal with the camera `Y` axis across the trajectory."""

    skip_reason: str | None = None
    """Human-readable reason why the stage skipped or declined to apply the alignment."""

    visualization: GroundPlaneVisualizationHint | None = None
    """Finite plane-patch geometry for a later visualization consumer."""


__all__ = [
    "AlignmentConfig",
    "GroundAlignmentConfig",
    "GroundAlignmentMetadata",
    "GroundPlaneModel",
    "GroundPlaneVisualizationHint",
]
