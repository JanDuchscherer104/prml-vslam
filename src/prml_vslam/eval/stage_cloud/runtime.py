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
    """Compute Open3D point-cloud metrics for benchmark clouds."""

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
                update={"lifecycle_state": StageStatus.FAILED, "last_error": str(exc)}
            )
            raise
        self._status = result.final_runtime_status
        return result

    def _run(self, input_payload: CloudEvaluationStageInput) -> StageResult:
        artifact = DenseCloudEvaluationService().compute_dense_evaluations(
            artifact_root=input_payload.artifact_root,
            reference_cloud_path=input_payload.reference_cloud.path,
            estimates=[(estimate.estimate_kind, estimate.cloud.path) for estimate in input_payload.estimates],
            f1_threshold_m=input_payload.f1_threshold_m,
            cloud_alignment_path=input_payload.cloud_alignment.path
            if input_payload.cloud_alignment is not None
            else None,
        )
        outcome = StageOutcome(
            stage_key=StageKey.CLOUD_EVALUATION,
            status=StageStatus.COMPLETED,
            config_hash=stable_hash({"f1_threshold_m": input_payload.f1_threshold_m}),
            input_fingerprint=stable_hash(
                {
                    "reference_cloud": input_payload.reference_cloud,
                    "estimates": input_payload.estimates,
                    "cloud_alignment": input_payload.cloud_alignment,
                }
            ),
            artifacts=_artifact_map(artifact),
            metrics=_summary_metrics(artifact),
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
                processed_items=len(input_payload.estimates),
            ),
        )


def _artifact_map(artifact: DenseCloudEvaluationArtifact) -> dict[str, ArtifactRef]:
    artifacts = {
        "cloud_metrics": artifact_ref(artifact.path, kind="json"),
        "reference_cloud": artifact_ref(artifact.reference_cloud_path, kind="ply"),
    }
    if artifact.cloud_alignment_path is not None:
        artifacts["cloud_alignment"] = artifact_ref(artifact.cloud_alignment_path, kind="json")
    for estimate in artifact.estimates:
        artifacts[f"{estimate.estimate_kind.value}_point_cloud_ply"] = artifact_ref(
            estimate.estimate_cloud_path, kind="ply"
        )
    return artifacts


def _summary_metrics(artifact: DenseCloudEvaluationArtifact) -> dict[str, float]:
    return {
        f"{estimate.estimate_kind.value}.{metric_id.value}": value
        for estimate in artifact.estimates
        for metric_id, value in estimate.metrics.items()
    }


__all__ = ["CloudEvaluationRuntime"]
