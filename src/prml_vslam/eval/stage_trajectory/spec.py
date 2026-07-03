"""Runtime spec for the trajectory-evaluation stage."""

from __future__ import annotations

from prml_vslam.eval.stage_trajectory.contracts import TrajectoryEvaluationStageInput
from prml_vslam.eval.stage_trajectory.runtime import TrajectoryEvaluationRuntime
from prml_vslam.pipeline.contracts.context import PipelineExecutionContext
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.config import FailureFingerprint
from prml_vslam.pipeline.stages.base.spec import StageRuntimeSpec


def _build_offline_input(context: PipelineExecutionContext) -> TrajectoryEvaluationStageInput:
    config = context.run_config.stages.evaluate_trajectory
    slam_backend = context.run_config.stages.slam.backend
    benchmark_inputs = context.results.require_benchmark_inputs()
    reference = (
        None if benchmark_inputs is None else benchmark_inputs.trajectory_for_source(config.evaluation.baseline_source)
    )
    return TrajectoryEvaluationStageInput(
        artifact_root=context.plan.artifact_root,
        path_config=context.path_config,
        baseline_source=config.evaluation.baseline_source,
        method_id=None if slam_backend is None else slam_backend.method_id,
        method_label="unknown" if slam_backend is None else slam_backend.display_name,
        sequence_manifest=context.results.require_sequence_manifest(),
        benchmark_inputs=benchmark_inputs,
        reference_trajectory=reference,
        candidate_trajectories=[] if benchmark_inputs is None else list(benchmark_inputs.candidate_trajectories),
        slam=context.results.require_slam_artifacts(),
    )


def _failure_fingerprint(context: PipelineExecutionContext) -> FailureFingerprint:
    slam = context.results.require_slam_artifacts()
    benchmark_inputs = context.results.require_benchmark_inputs()
    return FailureFingerprint(
        config_payload=context.run_config.stages.evaluate_trajectory.evaluation,
        input_payload={
            "benchmark_inputs": benchmark_inputs.model_dump_json() if benchmark_inputs is not None else None,
            "slam_trajectory": slam.trajectory_tum.path.as_posix(),
        },
    )


TRAJECTORY_EVALUATION_STAGE_SPEC = StageRuntimeSpec(
    stage_key=StageKey.TRAJECTORY_EVALUATION,
    runtime_factory=lambda _context: TrajectoryEvaluationRuntime,
    build_offline_input=_build_offline_input,
    failure_fingerprint=_failure_fingerprint,
)

__all__ = ["TRAJECTORY_EVALUATION_STAGE_SPEC"]
