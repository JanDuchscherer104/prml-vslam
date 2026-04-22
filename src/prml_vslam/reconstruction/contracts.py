"""Typed contracts for reconstruction adapters.

This module owns the method ids and package-local DTOs used by the
reconstruction package. The contracts stay independent from pipeline planning
and from viewer logging so reconstruction code can remain a thin geometry
adapter around external libraries such as Open3D.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import ConfigDict, Field

from prml_vslam.interfaces import RgbdObservation
from prml_vslam.utils import BaseData


class ReconstructionMethodId(StrEnum):
    """Name reconstruction backends supported by package-owned configs."""

    OPEN3D_TSDF = "open3d_tsdf"

    @property
    def display_name(self) -> str:
        """Return the user-facing method label."""
        match self:
            case ReconstructionMethodId.OPEN3D_TSDF:
                return "Open3D TSDF"


ReconstructionObservation = RgbdObservation
"""Temporary compatibility alias for the shared RGB-D observation DTO."""


class ReconstructionMetadata(BaseData):
    """Persist side metadata for one normalized reconstruction output.

    PLY geometry alone cannot explain which backend produced the cloud, how
    many RGB-D observations were fused, or what metric TSDF parameters shaped
    the result. Keep those values here so later evaluation and visualization
    can reason about the artifact without inspecting Open3D internals.
    """

    model_config = ConfigDict(frozen=True)

    method_id: ReconstructionMethodId
    """Reconstruction backend that produced the artifact."""

    observation_count: int
    """Number of RGB-D observations integrated into the reconstruction."""

    point_count: int
    """Number of extracted points written to the normalized output cloud."""

    target_frame: str
    """Frame represented by the exported point coordinates."""

    voxel_length_m: float
    """Open3D TSDF voxel length in meters."""

    sdf_trunc_m: float
    """Open3D TSDF signed-distance truncation in meters."""

    depth_trunc_m: float
    """Maximum depth integrated into the TSDF volume in meters."""

    depth_scale: float
    """Scale factor passed to Open3D when normalizing depth values."""

    integrate_color: bool
    """Whether the reconstruction fused RGB values alongside geometry."""


class ReconstructionArtifacts(BaseData):
    """Describe normalized durable outputs from one reconstruction run.

    The minimal public contract is one world-space reference cloud plus typed
    metadata. Meshes and backend diagnostics may be preserved as optional extras
    but must not replace the point-cloud contract consumed by pipeline and
    evaluation stages.
    """

    reference_cloud_path: Path
    """Filesystem path to the normalized world-space reference cloud."""

    metadata_path: Path
    """Filesystem path to the typed side metadata for the reconstruction."""

    mesh_path: Path | None = None
    """Optional filesystem path to a preserved extracted mesh artifact."""

    extras: dict[str, Path] = Field(default_factory=dict)
    """Additional backend-owned artifacts kept outside the minimal public contract."""


__all__ = [
    "ReconstructionArtifacts",
    "ReconstructionMetadata",
    "ReconstructionMethodId",
    "ReconstructionObservation",
]
