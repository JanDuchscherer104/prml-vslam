"""Trajectory-evaluation stage binding."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.binding import (
    FailureFingerprint,
    PlanContext,
    RuntimeBuildContext,
    StageBinding,
    StageInputContext,
)
from prml_vslam.pipeline.stages.base.protocols import BaseStageRuntime
from prml_vslam.pipeline.stages.trajectory_eval.contracts import TrajectoryEvaluationRuntimeInput


class TrajectoryEvaluationStageBinding(StageBinding):
    """Bind trajectory-evaluation config to runtime execution."""

    key = StageKey.TRAJECTORY_EVALUATION
    section_name = "evaluate_trajectory"

    def planned_outputs(self, context: PlanContext) -> list[Path]:
        """Return trajectory metrics output."""
        return [context.run_paths.trajectory_metrics_path]

    def availability(self, context: PlanContext) -> tuple[bool, str | None]:
        """Return whether the selected backend supports repository evaluation."""
        slam_backend = context.run_config.stages.slam.backend
        if slam_backend is None:
            return False, "Trajectory evaluation requires `[stages.slam.backend]`."
        descriptor = context.backend if context.backend is not None else slam_backend.describe()
        if not descriptor.capabilities.trajectory_benchmark_support:
            return False, f"{descriptor.display_name} does not support repository trajectory evaluation."
        return True, None

    def runtime_factory(self, context: RuntimeBuildContext) -> Callable[[], BaseStageRuntime]:
        """Return a lazy trajectory-evaluation runtime factory."""
        del context
        from prml_vslam.pipeline.stages.trajectory_eval.runtime import TrajectoryEvaluationRuntime

        return TrajectoryEvaluationRuntime

    def build_offline_input(self, context: StageInputContext) -> TrajectoryEvaluationRuntimeInput:
        """Build the narrow trajectory-evaluation runtime input."""
        slam_backend = context.run_config.stages.slam.backend
        return TrajectoryEvaluationRuntimeInput(
            artifact_root=context.plan.artifact_root,
            baseline_source=context.run_config.stages.evaluate_trajectory.evaluation.baseline_source,
            method_id=None if slam_backend is None else slam_backend.method_id,
            method_label="unknown" if slam_backend is None else slam_backend.display_name,
            sequence_manifest=context.results.require_sequence_manifest(),
            benchmark_inputs=context.results.require_benchmark_inputs(),
            slam=context.results.require_slam_artifacts(),
        )

    def failure_fingerprint(self, context: StageInputContext) -> FailureFingerprint:
        """Return trajectory config and SLAM trajectory fingerprint payloads."""
        slam = context.results.require_slam_artifacts()
        return FailureFingerprint(
            config_payload=context.run_config.stages.evaluate_trajectory.evaluation,
            input_payload={
                "benchmark_inputs": context.results.require_benchmark_inputs(),
                "slam_trajectory": slam.trajectory_tum,
            },
        )


__all__ = ["TrajectoryEvaluationStageBinding"]
