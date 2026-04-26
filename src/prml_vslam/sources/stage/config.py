"""Persisted source-stage config and source backend muxing."""

from __future__ import annotations

from pathlib import Path

from pydantic import ConfigDict

from prml_vslam.pipeline.contracts.context import PipelinePlanContext
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.config import StageConfig
from prml_vslam.sources.config import SourceBackendConfig


class SourceStageConfig(StageConfig):
    """Target source-stage policy plus source backend selection."""

    model_config = ConfigDict(extra="ignore")

    stage_key: StageKey | None = StageKey.SOURCE
    """Canonical source stage key."""

    backend: SourceBackendConfig | None = None
    """Concrete source backend config that constructs the source adapter."""

    def planned_outputs(self, context: PipelinePlanContext) -> list[Path]:
        """Return source-owned normalized input artifacts."""
        return [context.run_paths.sequence_manifest_path, context.run_paths.benchmark_inputs_path]


__all__ = ["SourceStageConfig"]
