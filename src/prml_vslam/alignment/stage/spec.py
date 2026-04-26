"""Runtime spec for the ground-alignment stage."""

from __future__ import annotations

from prml_vslam.alignment.stage.contracts import GroundAlignmentStageInput
from prml_vslam.alignment.stage.runtime import GroundAlignmentRuntime
from prml_vslam.pipeline.contracts.context import PipelineExecutionContext
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.config import FailureFingerprint
from prml_vslam.pipeline.stages.base.spec import StageRuntimeSpec


def _build_offline_input(context: PipelineExecutionContext) -> GroundAlignmentStageInput:
    config = context.run_config.stages.align_ground
    return GroundAlignmentStageInput(
        config=config.ground,
        run_paths=context.run_paths,
        slam=context.results.require_slam_artifacts(),
    )


def _failure_fingerprint(context: PipelineExecutionContext) -> FailureFingerprint:
    slam = context.results.require_slam_artifacts()
    return FailureFingerprint(
        config_payload=context.run_config.stages.align_ground.ground,
        input_payload={
            "trajectory_tum": slam.trajectory_tum,
            "dense_points_ply": slam.dense_points_ply,
            "sparse_points_ply": slam.sparse_points_ply,
        },
    )


GROUND_ALIGNMENT_STAGE_SPEC = StageRuntimeSpec(
    stage_key=StageKey.GRAVITY_ALIGNMENT,
    runtime_factory=lambda _context: GroundAlignmentRuntime,
    build_offline_input=_build_offline_input,
    failure_fingerprint=_failure_fingerprint,
)

__all__ = ["GROUND_ALIGNMENT_STAGE_SPEC"]
