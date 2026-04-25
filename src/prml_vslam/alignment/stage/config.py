"""Persisted config for the ``gravity.align`` stage."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from pydantic import ConfigDict, Field

from prml_vslam.alignment.contracts import GroundAlignmentConfig
from prml_vslam.pipeline.contracts.context import PipelineExecutionContext, PipelinePlanContext
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.config import FailureFingerprint, StageConfig
from prml_vslam.pipeline.stages.base.protocols import BaseStageRuntime


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

    def runtime_factory(self, context: PipelineExecutionContext) -> Callable[[], BaseStageRuntime]:
        del context
        from prml_vslam.alignment.stage.runtime import GroundAlignmentRuntime

        return GroundAlignmentRuntime

    def build_offline_input(self, context: PipelineExecutionContext):
        from prml_vslam.alignment.stage.contracts import GroundAlignmentStageInput

        return GroundAlignmentStageInput(
            config=self.ground,
            run_paths=context.run_paths,
            slam=context.results.require_slam_artifacts(),
        )

    def failure_fingerprint(self, context: PipelineExecutionContext) -> FailureFingerprint:
        slam = context.results.require_slam_artifacts()
        return FailureFingerprint(
            config_payload=self.ground,
            input_payload={
                "trajectory_tum": slam.trajectory_tum,
                "dense_points_ply": slam.dense_points_ply,
                "sparse_points_ply": slam.sparse_points_ply,
            },
        )


__all__ = ["GroundAlignmentStageConfig"]
