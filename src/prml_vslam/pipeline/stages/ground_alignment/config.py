"""Persisted config for the ``gravity.align`` stage."""

from __future__ import annotations

from pydantic import ConfigDict, Field

from prml_vslam.alignment.contracts import GroundAlignmentConfig
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.config import StageConfig


class GroundAlignmentStageConfig(StageConfig):
    """Stage-owned policy for derived ground-plane alignment."""

    model_config = ConfigDict(extra="ignore")

    stage_key: StageKey | None = StageKey.GRAVITY_ALIGNMENT
    ground: GroundAlignmentConfig = Field(default_factory=GroundAlignmentConfig)
    """Alignment-owned ground-plane policy consumed by the runtime."""


__all__ = ["GroundAlignmentStageConfig"]
