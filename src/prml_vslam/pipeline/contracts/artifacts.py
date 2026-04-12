"""Pipeline artifact contracts."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field

from prml_vslam.utils import BaseData


class ArtifactRef(BaseData):
    """Reference to one materialized artifact owned by the repository."""

    path: Path
    """Filesystem path to the materialized artifact."""

    kind: str
    """Short artifact kind identifier."""

    fingerprint: str
    """Content or provenance fingerprint for cache decisions."""


class SlamArtifacts(BaseData):
    """Materialized outputs produced by the SLAM stage."""

    trajectory_tum: ArtifactRef
    """Normalized TUM trajectory artifact."""

    sparse_points_ply: ArtifactRef | None = None
    """Optional sparse point cloud artifact."""

    dense_points_ply: ArtifactRef | None = None
    """Optional dense point cloud artifact."""

    extras: dict[str, ArtifactRef] = Field(default_factory=dict)
    """Optional backend-specific artifacts preserved without widening the core contract."""


__all__ = ["ArtifactRef", "SlamArtifacts"]
