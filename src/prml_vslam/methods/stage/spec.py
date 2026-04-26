"""Runtime spec for the SLAM stage."""

from __future__ import annotations

from prml_vslam.methods.stage.contracts import SlamOfflineStageInput, SlamStreamingStartStageInput
from prml_vslam.methods.stage.runtime import SlamStageRuntime
from prml_vslam.pipeline.contracts.context import PipelineExecutionContext
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.config import FailureFingerprint
from prml_vslam.pipeline.stages.base.spec import StageRuntimeSpec


def _build_offline_input(context: PipelineExecutionContext) -> SlamOfflineStageInput:
    slam_config = context.run_config.stages.slam
    if slam_config.backend is None:
        raise RuntimeError("SLAM runtime requires `[stages.slam.backend]`.")
    return SlamOfflineStageInput(
        backend=slam_config.backend,
        outputs=slam_config.outputs,
        artifact_root=context.plan.artifact_root,
        path_config=context.path_config,
        baseline_source=context.run_config.stages.evaluate_trajectory.evaluation.baseline_source,
        sequence_manifest=context.results.require_sequence_manifest(),
        benchmark_inputs=context.results.require_benchmark_inputs(),
        preserve_native_rerun=context.run_config.visualization.preserve_native_rerun,
    )


def _build_streaming_start_input(context: PipelineExecutionContext) -> SlamStreamingStartStageInput:
    slam_config = context.run_config.stages.slam
    if slam_config.backend is None:
        raise RuntimeError("SLAM runtime requires `[stages.slam.backend]`.")
    return SlamStreamingStartStageInput(
        backend=slam_config.backend,
        outputs=slam_config.outputs,
        artifact_root=context.plan.artifact_root,
        path_config=context.path_config,
        sequence_manifest=context.results.require_sequence_manifest(),
        benchmark_inputs=context.results.require_benchmark_inputs(),
        baseline_source=context.run_config.stages.evaluate_trajectory.evaluation.baseline_source,
        log_diagnostic_preview=context.run_config.visualization.log_diagnostic_preview,
        preserve_native_rerun=context.run_config.visualization.preserve_native_rerun,
    )


def _failure_fingerprint(context: PipelineExecutionContext) -> FailureFingerprint:
    return FailureFingerprint(
        config_payload=context.run_config.stages.slam,
        input_payload=context.results.require_sequence_manifest(),
    )


SLAM_STAGE_SPEC = StageRuntimeSpec(
    stage_key=StageKey.SLAM,
    runtime_factory=lambda _context: SlamStageRuntime,
    build_offline_input=_build_offline_input,
    build_streaming_start_input=_build_streaming_start_input,
    failure_fingerprint=_failure_fingerprint,
)

__all__ = ["SLAM_STAGE_SPEC"]
