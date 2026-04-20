"""Durable artifact contracts produced by the pipeline.

This module contains the normalized artifact references that stage outputs use
to cross package boundaries. These objects are durable and file-backed, unlike
the transient array handles used in runtime snapshots.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field

from prml_vslam.utils import BaseData


#  TODO: this is a pipeline general dto
class ArtifactRef(BaseData):
    """Describe one durable artifact materialized under the run artifact root."""

    path: Path
    """Filesystem path to the materialized artifact."""

    kind: str
    """Short artifact kind identifier."""

    fingerprint: str
    """Content or provenance fingerprint for cache decisions."""


# TODO: this is a dto / data model that should be defined in a shared model module! This belongs to methods!
class SlamArtifacts(BaseData):
    """Bundle the normalized durable outputs of the SLAM stage.

    Method wrappers normalize backend-native exports into this DTO so the rest
    of the repository can reason about trajectories and point clouds without
    learning each backend's private file layout.
    """

    trajectory_tum: ArtifactRef
    """Normalized TUM trajectory artifact."""

    sparse_points_ply: ArtifactRef | None = None
    """Optional sparse point cloud artifact."""

    dense_points_ply: ArtifactRef | None = None
    """Optional dense point cloud artifact."""

    extras: dict[str, ArtifactRef] = Field(default_factory=dict)
    """Optional backend-specific artifacts preserved without widening the core contract."""


__all__ = ["ArtifactRef", "SlamArtifacts"]
