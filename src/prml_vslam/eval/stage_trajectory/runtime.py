"""Bounded runtime adapter for trajectory evaluation."""

from __future__ import annotations

from prml_vslam.eval.contracts import DiscoveredRun, EvaluationArtifact, SelectionSnapshot
from prml_vslam.eval.services import TrajectoryEvaluationService
from prml_vslam.eval.stage_trajectory.contracts import TrajectoryEvaluationRuntimeInput
from prml_vslam.interfaces.artifacts import ArtifactRef
from prml_vslam.pipeline.contracts.events import StageOutcome
from prml_vslam.pipeline.contracts.provenance import StageStatus
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.finalization import stable_hash
from prml_vslam.pipeline.ray_runtime.common import artifact_ref
from prml_vslam.pipeline.stages.base.contracts import StageResult, StageRuntimeStatus
from prml_vslam.pipeline.stages.base.protocols import OfflineStageRuntime
from prml_vslam.utils import PathConfig


class TrajectoryEvaluationRuntime(OfflineStageRuntime[TrajectoryEvaluationRuntimeInput]):
    """Adapt eval-owned trajectory metric computation to the bounded runtime API.

    The runtime builds pipeline outcomes and status, while
    :class:`prml_vslam.eval.services.TrajectoryEvaluationService` owns metric
    computation, persisted evaluation schema, and the thin evo integration.
    """

    def __init__(self) -> None:
        self._status = StageRuntimeStatus(stage_key=StageKey.TRAJECTORY_EVALUATION)

    def status(self) -> StageRuntimeStatus:
        """Return the latest trajectory-evaluation runtime status."""
        return self._status

    def stop(self) -> None:
        """Mark the bounded runtime as stopped."""
        self._status = self._status.model_copy(update={"lifecycle_state": StageStatus.STOPPED})

    def run_offline(self, input_payload: TrajectoryEvaluationRuntimeInput) -> StageResult:
        """Compute trajectory metrics and return a canonical stage result.

        The result payload is an eval-owned artifact. The durable stage outcome
        records the metrics artifact and the exact source/estimate inputs used
        for provenance.
        """
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
        artifact = _compute_pipeline_evaluation(input_payload)
        artifacts = _artifact_map(artifact)
        outcome = StageOutcome(
            stage_key=StageKey.TRAJECTORY_EVALUATION,
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
    artifacts = {
        "trajectory_metrics": artifact_ref(artifact.path, kind="json"),
        "reference_tum": artifact_ref(artifact.reference_path, kind="tum"),
        "estimate_tum": artifact_ref(artifact.estimate_path, kind="tum"),
    }
    if artifact.alignment_path is not None:
        artifacts["trajectory_alignment"] = artifact_ref(artifact.alignment_path, kind="json")
    if artifact.aligned_estimate_path is not None:
        artifacts["aligned_estimate_tum"] = artifact_ref(artifact.aligned_estimate_path, kind="tum")
    if artifact.aligned_point_cloud_path is not None:
        artifacts["aligned_point_cloud_ply"] = artifact_ref(artifact.aligned_point_cloud_path, kind="ply")
    return artifacts


def _compute_pipeline_evaluation(input_payload: TrajectoryEvaluationRuntimeInput) -> EvaluationArtifact | None:
    """Compute trajectory evaluation from the narrow runtime input."""
    if input_payload.sequence_manifest is None or input_payload.benchmark_inputs is None or input_payload.slam is None:
        raise RuntimeError("Trajectory evaluation requires a sequence manifest, benchmark inputs, and SLAM artifacts.")
    reference = input_payload.benchmark_inputs.trajectory_for_source(input_payload.baseline_source)
    if reference is None:
        raise RuntimeError(
            "Prepared benchmark inputs do not include the requested trajectory baseline "
            f"'{input_payload.baseline_source.value}'."
        )
    return TrajectoryEvaluationService(path_config=_path_config_for(input_payload)).compute_evaluation(
        selection=SelectionSnapshot(
            sequence_slug=input_payload.sequence_manifest.sequence_id,
            reference_path=reference.path,
            run=DiscoveredRun(
                artifact_root=input_payload.artifact_root,
                estimate_path=input_payload.slam.trajectory_tum.path,
                point_cloud_path=(
                    input_payload.slam.dense_points_ply.path
                    if input_payload.slam.dense_points_ply is not None
                    else None
                ),
                method=input_payload.method_id,
                label=input_payload.method_label,
            ),
        )
    )


def _path_config_for(input_payload: TrajectoryEvaluationRuntimeInput) -> PathConfig:
    return PathConfig(artifacts_dir=input_payload.artifact_root.parent)


__all__ = ["TrajectoryEvaluationRuntime", "TrajectoryEvaluationRuntimeInput"]
