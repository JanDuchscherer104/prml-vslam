"""Typed contracts for reconstruction adapters.

This module owns the method ids and package-local DTOs used by the
reconstruction package. The contracts stay independent from pipeline planning
and from viewer logging so reconstruction code can remain a thin geometry
adapter around external libraries such as Open3D.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from typing import Any

from pydantic import ConfigDict, Field

from prml_vslam.utils import BaseData


class ReconstructionMethodId(StrEnum):
    """Name reconstruction backends supported by package-owned configs."""

    NKSR = "nksr"
    POISSON = "poisson"

    @property
    def display_name(self) -> str:
        """Return the user-facing method label."""
        match self:
            case ReconstructionMethodId.NKSR:
                return "Neural Kernel Surface Reconstruction"
            case ReconstructionMethodId.POISSON:
                return "Screened Poisson Surface Reconstruction"


class ReconstructionMetadata(BaseData):
    """Persist side metadata for one normalized reconstruction output.

    PLY geometry alone cannot explain which backend produced the cloud, how
    many source points were processed, or what parameters shaped the result.
    Keep those values here so later evaluation and visualization can reason
    about the artifact.
    """

    model_config = ConfigDict(frozen=True)

    method_id: ReconstructionMethodId
    """Reconstruction backend that produced the artifact."""

    point_count: int
    """Number of extracted points/vertices in the output."""

    target_frame: str
    """Frame represented by the exported point coordinates."""

    config_dump: dict[str, Any] = Field(default_factory=dict)
    """Complete serialized configuration of the backend that produced this."""


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
]
