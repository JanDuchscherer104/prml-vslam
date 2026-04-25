"""Bounded runtime adapter for the ground-alignment stage."""

from __future__ import annotations

from prml_vslam.alignment.contracts import GroundAlignmentConfig
from prml_vslam.alignment.services import GroundAlignmentService
from prml_vslam.interfaces.artifacts import artifact_ref
from prml_vslam.interfaces.slam import SlamArtifacts
from prml_vslam.pipeline.contracts.events import StageOutcome
from prml_vslam.pipeline.contracts.provenance import StageStatus
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.contracts import StageResult, StageRuntimeStatus
from prml_vslam.pipeline.stages.base.protocols import OfflineStageRuntime
from prml_vslam.utils import BaseData, RunArtifactPaths
from prml_vslam.utils.serialization import stable_hash, write_json


class GroundAlignmentStageInput(BaseData):
    """Inputs required to derive ground-alignment metadata from SLAM outputs."""

    config: GroundAlignmentConfig
    run_paths: RunArtifactPaths
    slam: SlamArtifacts


class GroundAlignmentRuntime(OfflineStageRuntime[GroundAlignmentStageInput]):
    """Adapt :class:`GroundAlignmentService` to the generic bounded runtime API.

    The runtime owns stage-result construction, artifact registration, and live
    status for the pipeline. Plane fitting and frame semantics remain
    alignment-owned in :mod:`prml_vslam.alignment.services`.
    """

    def __init__(self, *, service_type: type[GroundAlignmentService] | None = None) -> None:
        self._service_type = GroundAlignmentService if service_type is None else service_type
        self._status = StageRuntimeStatus(stage_key=StageKey.GRAVITY_ALIGNMENT)

    def status(self) -> StageRuntimeStatus:
        """Return the latest ground-alignment runtime status."""
        return self._status

    def stop(self) -> None:
        """Mark the bounded runtime as stopped."""
        self._status = self._status.model_copy(update={"lifecycle_state": StageStatus.STOPPED})

    def run_offline(self, input_payload: GroundAlignmentStageInput) -> StageResult:
        """Detect and persist the derived ground-alignment artifact.

        Returns a skipped stage outcome when the alignment service explicitly
        declines to apply a transform, preserving a durable diagnostic record
        without failing the run.
        """
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

    def _run(self, input_payload: GroundAlignmentStageInput) -> StageResult:
        metadata = self._service_type(config=input_payload.config).estimate_from_slam_artifacts(slam=input_payload.slam)
        write_json(input_payload.run_paths.ground_alignment_path, metadata)
        outcome_status = StageStatus.COMPLETED if metadata.applied else StageStatus.SKIPPED
        outcome = StageOutcome(
            stage_key=StageKey.GRAVITY_ALIGNMENT,
            status=outcome_status,
            config_hash=stable_hash(input_payload.config),
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
            stage_key=StageKey.GRAVITY_ALIGNMENT,
            payload=metadata,
            outcome=outcome,
            final_runtime_status=_final_status(
                stage_key=StageKey.GRAVITY_ALIGNMENT,
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


__all__ = ["GroundAlignmentRuntime", "GroundAlignmentStageInput"]
