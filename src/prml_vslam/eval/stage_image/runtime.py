"""Bounded runtime adapter for image-quality evaluation."""

from __future__ import annotations

from prml_vslam.eval.image_service import ImageQualityEvaluationService
from prml_vslam.eval.render_eval import RenderEvalResult
from prml_vslam.eval.stage_image.contracts import ImageEvaluationStageInput, image_evaluation_input_fingerprint_payload
from prml_vslam.interfaces.artifacts import ArtifactRef, artifact_ref
from prml_vslam.pipeline.contracts.events import StageOutcome
from prml_vslam.pipeline.contracts.provenance import StageStatus
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.contracts import StageResult, StageRuntimeStatus
from prml_vslam.pipeline.stages.base.protocols import OfflineStageRuntime
from prml_vslam.utils.serialization import stable_hash


class ImageEvaluationRuntime(OfflineStageRuntime[ImageEvaluationStageInput]):
    """Adapt the eval-owned render-and-score engine to the bounded runtime API.

    The runtime builds pipeline outcomes and status, while
    :meth:`prml_vslam.eval.image_service.ImageQualityEvaluationService.evaluate_run`
    owns rendering, timestamp pairing, masked metric computation, and persistence.
    """

    def __init__(self) -> None:
        self._status = StageRuntimeStatus(stage_key=StageKey.IMAGE_EVALUATION)

    def status(self) -> StageRuntimeStatus:
        """Return the latest image-evaluation runtime status."""
        return self._status

    def stop(self) -> None:
        """Mark the bounded runtime as stopped."""
        self._status = self._status.model_copy(update={"lifecycle_state": StageStatus.STOPPED})

    def run_offline(self, input_payload: ImageEvaluationStageInput) -> StageResult:
        """Render the dense cloud, score it against input frames, and return the result."""
        self._status = self._status.model_copy(
            update={
                "lifecycle_state": StageStatus.RUNNING,
                "progress_message": "Rendering dense cloud and scoring image quality.",
            }
        )
        try:
            result = ImageQualityEvaluationService().evaluate_run(
                input_payload.artifact_root,
                config=input_payload.render_config,
            )
        except Exception as exc:
            self._status = self._status.model_copy(
                update={"lifecycle_state": StageStatus.FAILED, "last_error": str(exc)}
            )
            raise
        stage_result = self._build_result(input_payload, result)
        self._status = stage_result.final_runtime_status
        return stage_result

    def _build_result(self, input_payload: ImageEvaluationStageInput, result: RenderEvalResult) -> StageResult:
        outcome = StageOutcome(
            stage_key=StageKey.IMAGE_EVALUATION,
            status=StageStatus.COMPLETED,
            config_hash=stable_hash(input_payload.render_config),
            input_fingerprint=stable_hash(image_evaluation_input_fingerprint_payload(input_payload)),
            artifacts=_artifact_map(result),
            metrics=_headline_metrics(result),
        )
        return StageResult(
            stage_key=StageKey.IMAGE_EVALUATION,
            payload=result.summary,
            outcome=outcome,
            final_runtime_status=StageRuntimeStatus(
                stage_key=StageKey.IMAGE_EVALUATION,
                lifecycle_state=StageStatus.COMPLETED,
                progress_message="Image evaluation complete.",
                completed_steps=result.scored_pairs,
                total_steps=result.scored_pairs,
                progress_unit="frame",
                processed_items=result.scored_pairs,
            ),
        )


def _artifact_map(result: RenderEvalResult) -> dict[str, ArtifactRef]:
    return {"image_metrics": artifact_ref(result.metrics_path, kind="json")}


def _headline_metrics(result: RenderEvalResult) -> dict[str, float | int | str]:
    metrics: dict[str, float | int | str] = {"scored_pairs": result.scored_pairs}
    for metric_id, stats in result.summary.stats.items():
        metrics[f"{metric_id}.mean"] = stats.mean
    return metrics


__all__ = ["ImageEvaluationRuntime"]
