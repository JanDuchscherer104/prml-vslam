"""Runtime spec for the trajectory-alignment stage."""

from __future__ import annotations

from prml_vslam.align.trajectory_sim3.runtime import TrajectoryAlignmentRuntime
from prml_vslam.align.trajectory_sim3.stage_contracts import TrajectoryAlignmentStageInput
from prml_vslam.pipeline.contracts.context import PipelineExecutionContext
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.config import FailureFingerprint
from prml_vslam.pipeline.stages.base.spec import StageRuntimeSpec


def _build_offline_input(context: PipelineExecutionContext) -> TrajectoryAlignmentStageInput:
    config = context.run_config.stages.align_trajectory
    slam_backend = context.run_config.stages.slam.backend
    return TrajectoryAlignmentStageInput(
        artifact_root=context.plan.artifact_root,
        path_config=context.path_config,
        baseline_source=config.baseline_source,
        method_id=None if slam_backend is None else slam_backend.method_id,
        sequence_manifest=context.results.require_sequence_manifest(),
        benchmark_inputs=context.results.require_benchmark_inputs(),
        slam=context.results.require_slam_artifacts(),
    )


def _failure_fingerprint(context: PipelineExecutionContext) -> FailureFingerprint:
    slam = context.results.require_slam_artifacts()
    benchmark_inputs = context.results.require_benchmark_inputs()
    return FailureFingerprint(
        config_payload={"baseline_source": context.run_config.stages.align_trajectory.baseline_source.value},
        input_payload={
            "benchmark_inputs": benchmark_inputs.model_dump_json() if benchmark_inputs is not None else None,
            "slam_trajectory": slam.trajectory_tum.path.as_posix(),
            "slam_dense_points": None if slam.dense_points_ply is None else slam.dense_points_ply.path.as_posix(),
        },
    )


TRAJECTORY_ALIGNMENT_STAGE_SPEC = StageRuntimeSpec(
    stage_key=StageKey.TRAJECTORY_ALIGNMENT,
    runtime_factory=lambda _context: TrajectoryAlignmentRuntime,
    build_offline_input=_build_offline_input,
    failure_fingerprint=_failure_fingerprint,
)

__all__ = ["TRAJECTORY_ALIGNMENT_STAGE_SPEC"]
