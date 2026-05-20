"""Bounded runtime adapter for dense-cloud evaluation."""

from __future__ import annotations

from prml_vslam.eval.contracts import DenseCloudEvaluationArtifact
from prml_vslam.eval.services import DenseCloudEvaluationService
from prml_vslam.eval.stage_cloud.contracts import CloudEvaluationStageInput
from prml_vslam.interfaces.artifacts import ArtifactRef, artifact_ref
from prml_vslam.pipeline.contracts.events import StageOutcome
from prml_vslam.pipeline.contracts.provenance import StageStatus
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.contracts import StageResult, StageRuntimeStatus
from prml_vslam.pipeline.stages.base.protocols import OfflineStageRuntime
from prml_vslam.utils.serialization import stable_hash


class CloudEvaluationRuntime(OfflineStageRuntime[CloudEvaluationStageInput]):
    """Adapt Open3D dense-cloud metrics to the bounded runtime API.

    The runtime assumes input selection has already resolved clouds into one
    shared metric world frame. It owns pipeline outcome/status construction;
    metric computation and persisted result schema stay in
    :class:`prml_vslam.eval.services.DenseCloudEvaluationService`.
    """

    def __init__(self) -> None:
        self._status = StageRuntimeStatus(stage_key=StageKey.CLOUD_EVALUATION)

    def status(self) -> StageRuntimeStatus:
        """Return the latest dense-cloud evaluation runtime status."""
        return self._status

    def stop(self) -> None:
        """Mark the bounded runtime as stopped."""
        self._status = self._status.model_copy(update={"lifecycle_state": StageStatus.STOPPED})

    def run_offline(self, input_payload: CloudEvaluationStageInput) -> StageResult:
        """Compute dense-cloud metrics and return a canonical stage result."""
        self._status = self._status.model_copy(
            update={
                "lifecycle_state": StageStatus.RUNNING,
                "progress_message": "Computing dense-cloud evaluation.",
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

    def _run(self, input_payload: CloudEvaluationStageInput) -> StageResult:
        selection = input_payload.selection
        artifact = DenseCloudEvaluationService().compute_dense_evaluation(selection=selection)
        artifact_map = _artifact_map(artifact)
        outcome = StageOutcome(
            stage_key=StageKey.CLOUD_EVALUATION,
            status=StageStatus.COMPLETED,
            config_hash=stable_hash({"f_score_threshold_m": selection.f_score_threshold_m}),
            input_fingerprint=stable_hash(
                {
                    "reference_cloud_path": selection.reference_cloud_path,
                    "estimate_cloud_path": selection.estimate_cloud_path,
                }
            ),
            artifacts=artifact_map,
            metrics=artifact.metrics,
        )
        return StageResult(
            stage_key=StageKey.CLOUD_EVALUATION,
            payload=artifact,
            outcome=outcome,
            final_runtime_status=StageRuntimeStatus(
                stage_key=StageKey.CLOUD_EVALUATION,
                lifecycle_state=StageStatus.COMPLETED,
                progress_message="Dense-cloud evaluation complete.",
                completed_steps=1,
                total_steps=1,
                progress_unit="evaluation",
                processed_items=1,
            ),
        )


def _artifact_map(artifact: DenseCloudEvaluationArtifact) -> dict[str, ArtifactRef]:
    return {
        "cloud_metrics": artifact_ref(artifact.path, kind="json"),
        "reference_cloud": artifact_ref(artifact.reference_cloud_path, kind="ply"),
        "estimate_cloud": artifact_ref(artifact.estimate_cloud_path, kind="ply"),
    }


__all__ = ["CloudEvaluationRuntime"]
