"""Persisted config for the ``evaluate.trajectory`` stage."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from pydantic import ConfigDict, Field

from prml_vslam.pipeline.contracts.context import PipelineExecutionContext, PipelinePlanContext
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.config import FailureFingerprint, StageConfig
from prml_vslam.pipeline.stages.base.protocols import BaseStageRuntime
from prml_vslam.sources.contracts import ReferenceSource
from prml_vslam.utils import BaseConfig


class TrajectoryEvaluationPolicy(BaseConfig):
    """Stage-owned trajectory-evaluation selection policy."""

    model_config = ConfigDict(extra="ignore")

    baseline_source: ReferenceSource = ReferenceSource.GROUND_TRUTH
    """Explicit reference source used by the trajectory-evaluation stage."""


class TrajectoryEvaluationStageConfig(StageConfig):
    """Stage-owned trajectory-evaluation policy."""

    model_config = ConfigDict(extra="ignore")

    stage_key: StageKey | None = StageKey.TRAJECTORY_EVALUATION
    evaluation: TrajectoryEvaluationPolicy = Field(default_factory=TrajectoryEvaluationPolicy)
    """Evaluation-owned baseline and metric policy consumed by the runtime."""

    @property
    def baseline_source(self) -> ReferenceSource:
        """Return the selected reference trajectory source."""
        return self.evaluation.baseline_source

    def planned_outputs(self, context: PipelinePlanContext) -> list[Path]:
        return [context.run_paths.trajectory_metrics_path]

    def availability(self, context: PipelinePlanContext) -> tuple[bool, str | None]:
        slam_backend = context.run_config.stages.slam.backend
        if slam_backend is None:
            return False, "Trajectory evaluation requires `[stages.slam.backend]`."
        backend = context.slam_backend if context.slam_backend is not None else slam_backend
        if not backend.supports_trajectory_benchmark:
            return False, f"{backend.display_name} does not support repository trajectory evaluation."
        return True, None

    def runtime_factory(self, context: PipelineExecutionContext) -> Callable[[], BaseStageRuntime]:
        del context
        from prml_vslam.eval.stage_trajectory.runtime import TrajectoryEvaluationRuntime

        return TrajectoryEvaluationRuntime

    def build_offline_input(self, context: PipelineExecutionContext):
        from prml_vslam.eval.stage_trajectory.runtime import TrajectoryEvaluationStageInput

        slam_backend = context.run_config.stages.slam.backend
        return TrajectoryEvaluationStageInput(
            artifact_root=context.plan.artifact_root,
            baseline_source=self.evaluation.baseline_source,
            method_id=None if slam_backend is None else slam_backend.method_id,
            method_label="unknown" if slam_backend is None else slam_backend.display_name,
            sequence_manifest=context.results.require_sequence_manifest(),
            benchmark_inputs=context.results.require_benchmark_inputs(),
            slam=context.results.require_slam_artifacts(),
        )

    def failure_fingerprint(self, context: PipelineExecutionContext) -> FailureFingerprint:
        slam = context.results.require_slam_artifacts()
        return FailureFingerprint(
            config_payload=self.evaluation,
            input_payload={
                "benchmark_inputs": context.results.require_benchmark_inputs(),
                "slam_trajectory": slam.trajectory_tum,
            },
        )


__all__ = ["TrajectoryEvaluationPolicy", "TrajectoryEvaluationStageConfig"]
