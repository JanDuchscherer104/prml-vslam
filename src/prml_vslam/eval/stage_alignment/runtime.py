"""Bounded runtime adapter for the Sim(3) trajectory alignment stage."""

from __future__ import annotations

from prml_vslam.eval.contracts import DiscoveredRun, SelectionSnapshot
from prml_vslam.eval.services import TrajectoryEvaluationService
from prml_vslam.eval.stage_alignment.contracts import TrajectoryAlignmentStageInput
from prml_vslam.interfaces.artifacts import ArtifactRef, artifact_ref
from prml_vslam.pipeline.contracts.events import StageOutcome
from prml_vslam.pipeline.contracts.provenance import StageStatus
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.contracts import StageResult, StageRuntimeStatus
from prml_vslam.pipeline.stages.base.protocols import OfflineStageRuntime
from prml_vslam.utils import PathConfig
from prml_vslam.utils.serialization import stable_hash


class TrajectoryAlignmentRuntime(OfflineStageRuntime[TrajectoryAlignmentStageInput]):
    """Compute and persist the Sim(3) alignment without APE metrics."""

    def __init__(self) -> None:
        self._status = StageRuntimeStatus(stage_key=StageKey.TRAJECTORY_ALIGNMENT)

    def status(self) -> StageRuntimeStatus:
        return self._status

    def stop(self) -> None:
        self._status = self._status.model_copy(update={"lifecycle_state": StageStatus.STOPPED})

    def run_offline(self, input_payload: TrajectoryAlignmentStageInput) -> StageResult:
        self._status = self._status.model_copy(
            update={
                "lifecycle_state": StageStatus.RUNNING,
                "progress_message": "Computing Sim(3) trajectory alignment.",
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

    def _run(self, input_payload: TrajectoryAlignmentStageInput) -> StageResult:
        reference = _resolve_reference(input_payload)
        service = TrajectoryEvaluationService(PathConfig(artifacts_dir=input_payload.artifact_root.parent))
        alignment_path, aligned_estimate_path, aligned_point_cloud_path = service.compute_trajectory_alignment(
            selection=SelectionSnapshot(
                sequence_slug=input_payload.sequence_manifest.sequence_id,
                reference_path=reference,
                run=DiscoveredRun(
                    artifact_root=input_payload.artifact_root,
                    estimate_path=input_payload.slam.trajectory_tum.path,
                    point_cloud_path=(
                        input_payload.slam.dense_points_ply.path
                        if input_payload.slam.dense_points_ply is not None
                        else None
                    ),
                    label="alignment",
                ),
            )
        )
        artifacts: dict[str, ArtifactRef] = {
            "trajectory_alignment": artifact_ref(alignment_path, kind="json"),
            "aligned_estimate_tum": artifact_ref(aligned_estimate_path, kind="tum"),
        }
        if aligned_point_cloud_path is not None:
            artifacts["aligned_point_cloud_ply"] = artifact_ref(aligned_point_cloud_path, kind="ply")

        outcome = StageOutcome(
            stage_key=StageKey.TRAJECTORY_ALIGNMENT,
            status=StageStatus.COMPLETED,
            config_hash=stable_hash({"baseline_source": input_payload.baseline_source.value}),
            input_fingerprint=stable_hash(
                {
                    "benchmark_inputs": input_payload.benchmark_inputs,
                    "slam_trajectory": input_payload.slam.trajectory_tum,
                }
            ),
            artifacts=artifacts,
        )
        return StageResult(
            stage_key=StageKey.TRAJECTORY_ALIGNMENT,
            payload=None,
            outcome=outcome,
            final_runtime_status=StageRuntimeStatus(
                stage_key=StageKey.TRAJECTORY_ALIGNMENT,
                lifecycle_state=StageStatus.COMPLETED,
                progress_message="Sim(3) trajectory alignment complete.",
                completed_steps=1,
                total_steps=1,
                progress_unit="alignment",
                processed_items=1,
            ),
        )


def _resolve_reference(input_payload: TrajectoryAlignmentStageInput):
    if input_payload.benchmark_inputs is None:
        raise RuntimeError("Trajectory alignment requires prepared benchmark inputs.")
    reference = input_payload.benchmark_inputs.trajectory_for_source(input_payload.baseline_source)
    if reference is None:
        raise RuntimeError(
            f"Benchmark inputs do not include the requested baseline '{input_payload.baseline_source.value}'."
        )
    return reference.path


__all__ = ["TrajectoryAlignmentRuntime"]
