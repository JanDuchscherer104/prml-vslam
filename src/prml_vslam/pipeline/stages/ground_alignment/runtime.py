"""Bounded runtime adapter for the ground-alignment stage."""

from __future__ import annotations

from prml_vslam.alignment import GroundAlignmentService
from prml_vslam.pipeline.contracts.events import StageOutcome
from prml_vslam.pipeline.contracts.provenance import StageStatus
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.finalization import stable_hash, write_json
from prml_vslam.pipeline.ray_runtime.common import artifact_ref
from prml_vslam.pipeline.stages.base.contracts import StageResult, StageRuntimeStatus
from prml_vslam.pipeline.stages.ground_alignment.contracts import GroundAlignmentRuntimeInput


# TODO: why is this class not derived from common StageRuntime base class?
class GroundAlignmentRuntime:
    """Adapt :class:`GroundAlignmentService` to the generic bounded runtime API."""

    def __init__(self, *, service_type: type[GroundAlignmentService] | None = None) -> None:
        # TODO(pipeline-refactor/WP-10): Remove this injectable service seam
        # after legacy stage_execution monkeypatch tests migrate to runtime tests.
        self._service_type = GroundAlignmentService if service_type is None else service_type
        self._status = StageRuntimeStatus(stage_key=StageKey.GROUND_ALIGNMENT)

    def status(self) -> StageRuntimeStatus:
        """Return the latest ground-alignment runtime status."""
        return self._status

    def stop(self) -> None:
        """Mark the bounded runtime as stopped."""
        self._status = self._status.model_copy(update={"lifecycle_state": StageStatus.STOPPED})

    def run_offline(self, input_payload: GroundAlignmentRuntimeInput) -> StageResult:
        """Detect and persist the derived ground-alignment artifact."""
        self._status = self._status.model_copy(
            update={
                "lifecycle_state": StageStatus.RUNNING,
                "progress_message": "Estimating ground alignment.",
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

    def _run(self, input_payload: GroundAlignmentRuntimeInput) -> StageResult:
        metadata = self._service_type(config=input_payload.request.alignment.ground).estimate_from_slam_artifacts(
            slam=input_payload.slam
        )
        write_json(input_payload.run_paths.ground_alignment_path, metadata)
        outcome_status = StageStatus.COMPLETED if metadata.applied else StageStatus.SKIPPED
        outcome = StageOutcome(
            stage_key=StageKey.GROUND_ALIGNMENT,
            status=outcome_status,
            config_hash=stable_hash(input_payload.request.alignment.ground),
            input_fingerprint=stable_hash(
                {
                    "trajectory_tum": input_payload.slam.trajectory_tum,
                    "dense_points_ply": input_payload.slam.dense_points_ply,
                    "sparse_points_ply": input_payload.slam.sparse_points_ply,
                }
            ),
            artifacts={
                "ground_alignment": artifact_ref(input_payload.run_paths.ground_alignment_path, kind="json"),
            },
            metrics={
                "confidence": metadata.confidence,
                "candidate_count": metadata.candidate_count,
            },
        )
        return StageResult(
            stage_key=StageKey.GROUND_ALIGNMENT,
            payload=metadata,
            outcome=outcome,
            final_runtime_status=_final_status(
                stage_key=StageKey.GROUND_ALIGNMENT,
                status=outcome_status,
                processed_items=1,
                progress_message="Ground alignment complete.",
            ),
        )


def _final_status(
    *,
    stage_key: StageKey,
    status: StageStatus,
    processed_items: int,
    progress_message: str,
) -> StageRuntimeStatus:
    return StageRuntimeStatus(
        stage_key=stage_key,
        lifecycle_state=status,
        progress_message=progress_message,
        completed_steps=processed_items,
        total_steps=processed_items,
        progress_unit="artifacts",
        processed_items=processed_items,
    )


__all__ = ["GroundAlignmentRuntime", "GroundAlignmentRuntimeInput"]
