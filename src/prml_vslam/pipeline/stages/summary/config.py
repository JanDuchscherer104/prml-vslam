"""Persisted config for the projection-only ``summary`` stage."""

from __future__ import annotations

from pydantic import ConfigDict

from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.config import StageConfig


class SummaryStageConfig(StageConfig):
    """Summary-stage policy without metric or runtime interpretation."""

    model_config = ConfigDict(extra="ignore")

    stage_key: StageKey | None = StageKey.SUMMARY


__all__ = ["SummaryStageConfig"]
