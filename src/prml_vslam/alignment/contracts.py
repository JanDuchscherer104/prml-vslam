"""Typed policy contracts for derived ground-plane alignment.

Alignment is a derived interpretation layer over normalized SLAM outputs. It
may estimate viewer-scoped transforms such as ``T_viewer_world_world``, but it
must not mutate native trajectories or point clouds in place. Runtime services
consume these configs through :mod:`prml_vslam.alignment.services`; pipeline
stage configs merely decide whether the alignment stage should run.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from prml_vslam.utils import BaseConfig


class GroundAlignmentConfig(BaseConfig):
    """Policy for optional dominant-ground detection and viewer alignment.

    The stage consumes normalized :class:`prml_vslam.interfaces.slam.SlamArtifacts`
    and emits :class:`prml_vslam.interfaces.alignment.GroundAlignmentMetadata`.
    Unsupported or low-confidence cases return explicit skip diagnostics rather
    than silently changing downstream world-frame semantics.
    """

    enabled: bool = False
    """Whether the `gravity.align` stage should run."""

    strategy: Literal["ransac_point_cloud"] = "ransac_point_cloud"
    """Detection strategy used to estimate the dominant ground plane."""

    min_confidence: float = Field(default=0.6, ge=0.0, le=1.0)
    """Minimum confidence required before the alignment is applied."""


__all__ = ["GroundAlignmentConfig"]
