"""Bounded runtime adapter for trajectory evaluation."""

from __future__ import annotations

from prml_vslam.eval.contracts import EvaluationArtifact
from prml_vslam.eval.services import TrajectoryEvaluationService
from prml_vslam.interfaces.slam import ArtifactRef
from prml_vslam.pipeline.contracts.events import StageOutcome
from prml_vslam.pipeline.contracts.provenance import StageStatus
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.finalization import stable_hash
from prml_vslam.pipeline.ray_runtime.common import artifact_ref
from prml_vslam.pipeline.stages.base.contracts import StageResult, StageRuntimeStatus
from prml_vslam.pipeline.stages.trajectory_eval.contracts import TrajectoryEvaluationRuntimeInput
from prml_vslam.utils import PathConfig


class TrajectoryEvaluationRuntime:
    """Adapt eval-owned trajectory metric computation to the bounded runtime API."""

    def __init__(self) -> None:
        self._status = StageRuntimeStatus(stage_key=StageKey.TRAJECTORY_EVALUATION)

    def status(self) -> StageRuntimeStatus:
        """Return the latest trajectory-evaluation runtime status."""
        return self._status

    def stop(self) -> None:
        """Mark the bounded runtime as stopped."""
        self._status = self._status.model_copy(update={"lifecycle_state": StageStatus.STOPPED})

    def run_offline(self, input_payload: TrajectoryEvaluationRuntimeInput) -> StageResult:
        """Compute trajectory metrics and return a canonical stage result."""
        self._status = self._status.model_copy(
            update={
                "lifecycle_state": StageStatus.RUNNING,
                "progress_message": "Computing trajectory evaluation.",
            }
        )
        try:
            result = self._run(input_payload)
        except Exception as exc:
            self._status = self._status.model_copy(
                update={
                    "lifecycle_state": StageStatus.FAILED,
                    "last_error": str(exc),
                }
            )
            raise
        self._status = result.final_runtime_status
        return result

    def _run(self, input_payload: TrajectoryEvaluationRuntimeInput) -> StageResult:
        artifact = TrajectoryEvaluationService(
            PathConfig(artifacts_dir=input_payload.request.output_dir)
        ).compute_pipeline_evaluation(
            request=input_payload.request,
            plan=input_payload.plan,
            sequence_manifest=input_payload.sequence_manifest,
            benchmark_inputs=input_payload.benchmark_inputs,
            slam=input_payload.slam,
        )
        artifacts = _artifact_map(artifact)
        outcome = StageOutcome(
            stage_key=StageKey.TRAJECTORY_EVALUATION,
            status=StageStatus.COMPLETED,
            config_hash=stable_hash(input_payload.request.benchmark.trajectory),
            input_fingerprint=stable_hash(
                {
                    "benchmark_inputs": input_payload.benchmark_inputs,
                    "slam_trajectory": input_payload.slam.trajectory_tum,
                }
            ),
            artifacts=artifacts,
        )
        return StageResult(
            stage_key=StageKey.TRAJECTORY_EVALUATION,
            payload=artifact,
            outcome=outcome,
            final_runtime_status=StageRuntimeStatus(
                stage_key=StageKey.TRAJECTORY_EVALUATION,
                lifecycle_state=StageStatus.COMPLETED,
                progress_message="Trajectory evaluation complete.",
                completed_steps=1,
                total_steps=1,
                progress_unit="evaluation",
                processed_items=1,
            ),
        )


def _artifact_map(artifact: EvaluationArtifact | None) -> dict[str, ArtifactRef]:
    if artifact is None:
        return {}
    return {
        "trajectory_metrics": artifact_ref(artifact.path, kind="json"),
        "reference_tum": artifact_ref(artifact.reference_path, kind="tum"),
        "estimate_tum": artifact_ref(artifact.estimate_path, kind="tum"),
    }


__all__ = ["TrajectoryEvaluationRuntime", "TrajectoryEvaluationRuntimeInput"]
