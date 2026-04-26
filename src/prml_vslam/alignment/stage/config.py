"""Persisted config for the ``gravity.align`` stage."""

from __future__ import annotations

from pathlib import Path

from pydantic import ConfigDict, Field

from prml_vslam.alignment.contracts import GroundAlignmentConfig
from prml_vslam.pipeline.contracts.context import PipelinePlanContext
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.config import StageConfig


class GroundAlignmentStageConfig(StageConfig):
    """Stage-owned policy for derived ground-plane alignment."""

    model_config = ConfigDict(extra="ignore")

    stage_key: StageKey | None = StageKey.GRAVITY_ALIGNMENT
    ground: GroundAlignmentConfig = Field(default_factory=GroundAlignmentConfig)
    """Alignment-owned ground-plane policy consumed by the runtime."""

    def planned_outputs(self, context: PipelinePlanContext) -> list[Path]:
        return [context.run_paths.ground_alignment_path]

    def availability(self, context: PipelinePlanContext) -> tuple[bool, str | None]:
        slam_backend = context.run_config.stages.slam.backend
        if slam_backend is None:
            return False, "Ground alignment requires `[stages.slam.backend]`."
        backend = context.slam_backend if context.slam_backend is not None else slam_backend
        if not backend.supports_dense_points:
            return False, f"{backend.display_name} does not expose point-cloud outputs for ground alignment."
        outputs = context.run_config.stages.slam.outputs
        if not (outputs.emit_dense_points or outputs.emit_sparse_points):
            return False, "Ground alignment requires sparse or dense point-cloud outputs from the SLAM stage."
        return True, None


__all__ = ["GroundAlignmentStageConfig"]
