"""Normalized SLAM artifact DTOs shared across packages."""

from __future__ import annotations

from pydantic import Field

from prml_vslam.pipeline.contracts.provenance import ArtifactRef
from prml_vslam.utils import BaseData


class SlamArtifacts(BaseData):
    """Normalize durable outputs produced by a SLAM backend.

    The bundle is the scientific handoff from method execution into evaluation,
    alignment, reconstruction, artifact inspection, and reporting.
    """

    trajectory_tum: ArtifactRef
    sparse_points_ply: ArtifactRef | None = None
    dense_points_ply: ArtifactRef | None = None
    extras: dict[str, ArtifactRef] = Field(default_factory=dict)


__all__ = ["SlamArtifacts"]
