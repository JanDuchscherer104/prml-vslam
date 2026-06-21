"""Bounded runtime adapter for offline point-cloud alignment."""

from __future__ import annotations

from prml_vslam.align.icp._algorithm import CloudAlignmentService
from prml_vslam.align.icp.stage_contracts import CloudAlignmentStageInput
from prml_vslam.eval.contracts import CloudAlignmentArtifact, CloudAlignmentSelection
from prml_vslam.interfaces.artifacts import ArtifactRef, artifact_ref
from prml_vslam.pipeline.contracts.events import StageOutcome
from prml_vslam.pipeline.contracts.provenance import StageStatus
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.contracts import StageResult, StageRuntimeStatus
from prml_vslam.pipeline.stages.base.protocols import OfflineStageRuntime
from prml_vslam.utils.serialization import stable_hash


class CloudAlignmentRuntime(OfflineStageRuntime[CloudAlignmentStageInput]):
    """Refine a trajectory-Sim(3)-aligned SLAM cloud before dense-cloud metrics."""

    def __init__(self) -> None:
        self._status = StageRuntimeStatus(stage_key=StageKey.CLOUD_ALIGNMENT)

    def status(self) -> StageRuntimeStatus:
        return self._status

    def stop(self) -> None:
        self._status = self._status.model_copy(update={"lifecycle_state": StageStatus.STOPPED})

    def run_offline(self, input_payload: CloudAlignmentStageInput) -> StageResult:
        self._status = self._status.model_copy(
            update={
                "lifecycle_state": StageStatus.RUNNING,
                "progress_message": "Refining Sim(3)-aligned point cloud with ICP.",
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

    def _run(self, input_payload: CloudAlignmentStageInput) -> StageResult:
        artifact = CloudAlignmentService().compute_cloud_alignment(
            selection=CloudAlignmentSelection(
                artifact_root=input_payload.artifact_root,
                reference_cloud_path=input_payload.reference_cloud.path,
                sim3_cloud_path=input_payload.sim3_point_cloud.path,
                target_frame=input_payload.target_frame,
                max_correspondence_distance_m=input_payload.max_correspondence_distance_m,
            )
        )
        artifacts = _artifact_map(artifact)
        outcome = StageOutcome(
            stage_key=StageKey.CLOUD_ALIGNMENT,
            status=StageStatus.COMPLETED,
            config_hash=stable_hash({"max_correspondence_distance_m": input_payload.max_correspondence_distance_m}),
            input_fingerprint=stable_hash(
                {
                    "reference_cloud": input_payload.reference_cloud,
                    "sim3_point_cloud": input_payload.sim3_point_cloud,
                    "target_frame": input_payload.target_frame,
                }
            ),
            artifacts=artifacts,
            metrics={"fitness": artifact.fitness, "inlier_rmse_m": artifact.inlier_rmse_m},
        )
        return StageResult(
            stage_key=StageKey.CLOUD_ALIGNMENT,
            payload=artifact,
            outcome=outcome,
            final_runtime_status=StageRuntimeStatus(
                stage_key=StageKey.CLOUD_ALIGNMENT,
                lifecycle_state=StageStatus.COMPLETED,
                progress_message="Point-cloud alignment complete.",
                completed_steps=1,
                total_steps=1,
                progress_unit="alignment",
                processed_items=1,
            ),
        )


def _artifact_map(artifact: CloudAlignmentArtifact) -> dict[str, ArtifactRef]:
    return {
        "cloud_alignment": artifact_ref(artifact.path, kind="json"),
        "reference_cloud": artifact_ref(artifact.reference_cloud_path, kind="ply"),
        "sim3_aligned_point_cloud_ply": artifact_ref(artifact.sim3_point_cloud_path, kind="ply"),
        "icp_aligned_point_cloud_ply": artifact_ref(artifact.icp_point_cloud_path, kind="ply"),
    }


__all__ = ["CloudAlignmentRuntime"]
