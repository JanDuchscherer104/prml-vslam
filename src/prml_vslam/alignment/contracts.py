"""Typed contracts for derived ground-plane alignment."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from prml_vslam.utils import BaseConfig


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


__all__ = [
    "AlignmentConfig",
    "GroundAlignmentConfig",
]
