"""Shared run finalization helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from prml_vslam.benchmark import PreparedBenchmarkInputs
from prml_vslam.pipeline.contracts.artifacts import SlamArtifacts
from prml_vslam.pipeline.contracts.plan import RunPlan, RunPlanStageId
from prml_vslam.pipeline.contracts.provenance import RunSummary, StageExecutionStatus, StageManifest
from prml_vslam.pipeline.contracts.request import RunRequest
from prml_vslam.pipeline.contracts.sequence import SequenceManifest
from prml_vslam.pipeline.evaluation import TrajectoryEvaluationExecution
from prml_vslam.utils import BaseConfig, RunArtifactPaths
from prml_vslam.visualization import VisualizationArtifacts


def finalize_run_outputs(
    *,
    request: RunRequest,
    plan: RunPlan,
    run_paths: RunArtifactPaths,
    sequence_manifest: SequenceManifest | None,
    benchmark_inputs: PreparedBenchmarkInputs | None,
    slam: SlamArtifacts | None,
    trajectory_evaluation: TrajectoryEvaluationExecution,
    visualization: VisualizationArtifacts | None,
    ingest_started: bool,
    slam_started: bool,
    pipeline_failed: bool,
    error_message: str,
) -> tuple[RunSummary, list[StageManifest]]:
    """Persist the run summary plus truthful stage manifests for executed work."""
    stage_status = build_stage_status(
        plan=plan,
        sequence_manifest=sequence_manifest,
        slam=slam,
        trajectory_evaluation=trajectory_evaluation,
        ingest_started=ingest_started,
        slam_started=slam_started,
        pipeline_failed=pipeline_failed,
    )
    non_summary_manifests = build_stage_manifests(
        request=request,
        plan=plan,
        run_paths=run_paths,
        sequence_manifest=sequence_manifest,
        benchmark_inputs=benchmark_inputs,
        slam=slam,
        trajectory_evaluation=trajectory_evaluation,
        visualization=visualization,
        stage_status=stage_status,
    )
    summary_manifest = build_summary_manifest(
        request=request,
        run_paths=run_paths,
        sequence_manifest=sequence_manifest,
        benchmark_inputs=benchmark_inputs,
        slam=slam,
        trajectory_evaluation=trajectory_evaluation,
        visualization=visualization,
        stage_status=stage_status,
        existing_stage_manifests=non_summary_manifests,
        error_message=error_message,
    )
    stage_manifests = [*non_summary_manifests, summary_manifest]
    summary = RunSummary(
        run_id=plan.run_id,
        artifact_root=plan.artifact_root,
        stage_status={**stage_status, RunPlanStageId.SUMMARY: StageExecutionStatus.RAN},
    )
    write_json(run_paths.summary_path, summary)
    write_json(run_paths.stage_manifests_path, stage_manifests)
    return summary, stage_manifests


def build_stage_status(
    *,
    plan: RunPlan,
    sequence_manifest: SequenceManifest | None,
    slam: SlamArtifacts | None,
    trajectory_evaluation: TrajectoryEvaluationExecution,
    ingest_started: bool,
    slam_started: bool,
    pipeline_failed: bool,
) -> dict[RunPlanStageId, StageExecutionStatus]:
    """Compute truthful statuses for the stages owned by the current executable slice."""
    planned_ids = {stage.id for stage in plan.stages}
    stage_status: dict[RunPlanStageId, StageExecutionStatus] = {}
    if RunPlanStageId.INGEST in planned_ids and ingest_started:
        stage_status[RunPlanStageId.INGEST] = (
            StageExecutionStatus.RAN if sequence_manifest is not None else StageExecutionStatus.FAILED
        )
    if RunPlanStageId.SLAM in planned_ids and slam_started:
        stage_status[RunPlanStageId.SLAM] = (
            StageExecutionStatus.RAN if slam is not None and not pipeline_failed else StageExecutionStatus.FAILED
        )
    if RunPlanStageId.TRAJECTORY_EVALUATION in planned_ids and trajectory_evaluation.started:
        stage_status[RunPlanStageId.TRAJECTORY_EVALUATION] = (
            StageExecutionStatus.RAN
            if trajectory_evaluation.artifact is not None and not trajectory_evaluation.error_message
            else StageExecutionStatus.FAILED
        )
    return stage_status


def build_stage_manifests(
    *,
    request: RunRequest,
    plan: RunPlan,
    run_paths: RunArtifactPaths,
    sequence_manifest: SequenceManifest | None,
    benchmark_inputs: PreparedBenchmarkInputs | None,
    slam: SlamArtifacts | None,
    trajectory_evaluation: TrajectoryEvaluationExecution,
    visualization: VisualizationArtifacts | None,
    stage_status: dict[RunPlanStageId, StageExecutionStatus],
) -> list[StageManifest]:
    """Build non-summary stage manifests for the executed pipeline slice."""
    manifests: list[StageManifest] = []
    if RunPlanStageId.INGEST in stage_status:
        output_paths = {"sequence_manifest": run_paths.sequence_manifest_path} if sequence_manifest is not None else {}
        if sequence_manifest is not None:
            if sequence_manifest.rgb_dir is not None:
                output_paths["rgb_dir"] = sequence_manifest.rgb_dir
            if sequence_manifest.timestamps_path is not None:
                output_paths["timestamps"] = sequence_manifest.timestamps_path
            if sequence_manifest.intrinsics_path is not None:
                output_paths["intrinsics"] = sequence_manifest.intrinsics_path
            if sequence_manifest.rotation_metadata_path is not None:
                output_paths["rotation_metadata"] = sequence_manifest.rotation_metadata_path
        if benchmark_inputs is not None:
            output_paths["benchmark_inputs"] = run_paths.benchmark_inputs_path
            for reference in benchmark_inputs.reference_trajectories:
                output_paths[f"reference_tum:{reference.source.value}"] = reference.path
        manifests.append(
            StageManifest(
                stage_id=RunPlanStageId.INGEST,
                config_hash=stable_hash(request.source),
                input_fingerprint=stable_hash(request.source),
                output_paths=output_paths,
                status=stage_status[RunPlanStageId.INGEST],
            )
        )
    if RunPlanStageId.SLAM in stage_status:
        output_paths: dict[str, Path] = {}
        if slam is not None:
            output_paths["trajectory_tum"] = slam.trajectory_tum.path
            if slam.sparse_points_ply is not None:
                output_paths["sparse_points_ply"] = slam.sparse_points_ply.path
            if slam.dense_points_ply is not None:
                output_paths["dense_points_ply"] = slam.dense_points_ply.path
            for key, artifact in slam.extras.items():
                output_paths[f"extra:{key}"] = artifact.path
        if visualization is not None:
            if visualization.native_rerun_rrd is not None:
                output_paths["native_rerun_rrd"] = visualization.native_rerun_rrd.path
            if visualization.native_output_dir is not None:
                output_paths["native_output_dir"] = visualization.native_output_dir.path
            for key, artifact in visualization.extras.items():
                output_paths[f"visualization:{key}"] = artifact.path
        manifests.append(
            StageManifest(
                stage_id=RunPlanStageId.SLAM,
                config_hash=stable_hash(request.slam),
                input_fingerprint=stable_hash(sequence_manifest or {"missing": "sequence_manifest"}),
                output_paths=output_paths,
                status=stage_status[RunPlanStageId.SLAM],
            )
        )
    if RunPlanStageId.TRAJECTORY_EVALUATION in stage_status:
        output_paths: dict[str, Path] = {}
        if trajectory_evaluation.reference_path is not None:
            output_paths["reference_tum"] = trajectory_evaluation.reference_path
        if trajectory_evaluation.estimate_path is not None:
            output_paths["estimate_tum"] = trajectory_evaluation.estimate_path
        if trajectory_evaluation.artifact is not None:
            output_paths["trajectory_metrics"] = trajectory_evaluation.artifact.path
        manifests.append(
            StageManifest(
                stage_id=RunPlanStageId.TRAJECTORY_EVALUATION,
                config_hash=stable_hash(request.benchmark.trajectory),
                input_fingerprint=stable_hash(
                    {
                        "baseline_source": request.benchmark.trajectory.baseline_source,
                        "reference_path": trajectory_evaluation.reference_path,
                        "estimate_path": trajectory_evaluation.estimate_path,
                    }
                ),
                output_paths=output_paths,
                status=stage_status[RunPlanStageId.TRAJECTORY_EVALUATION],
            )
        )
    planned_ids = {stage.id for stage in plan.stages}
    return [manifest for manifest in manifests if manifest.stage_id in planned_ids]


def build_summary_manifest(
    *,
    request: RunRequest,
    run_paths: RunArtifactPaths,
    sequence_manifest: SequenceManifest | None,
    benchmark_inputs: PreparedBenchmarkInputs | None,
    slam: SlamArtifacts | None,
    trajectory_evaluation: TrajectoryEvaluationExecution,
    visualization: VisualizationArtifacts | None,
    stage_status: dict[RunPlanStageId, StageExecutionStatus],
    existing_stage_manifests: list[StageManifest],
    error_message: str,
) -> StageManifest:
    """Build the summary-stage manifest before persisting summary outputs."""
    return StageManifest(
        stage_id=RunPlanStageId.SUMMARY,
        config_hash=stable_hash({"experiment_name": request.experiment_name, "mode": request.mode}),
        input_fingerprint=stable_hash(
            {
                "sequence_manifest": sequence_manifest,
                "benchmark_inputs": benchmark_inputs,
                "slam": slam,
                "trajectory_evaluation": trajectory_evaluation,
                "visualization": visualization,
                "stage_status": stage_status,
                "stage_manifests": existing_stage_manifests,
                "error_message": error_message,
            }
        ),
        output_paths={
            "run_summary": run_paths.summary_path,
            "stage_manifests": run_paths.stage_manifests_path,
        },
        status=StageExecutionStatus.RAN,
    )


def stable_hash(payload: object) -> str:
    """Compute a stable SHA-256 hash for repo-owned JSON-friendly payloads."""
    normalized_payload = BaseConfig.to_jsonable(payload)
    encoded = json.dumps(normalized_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def write_json(path: Path, payload: object) -> None:
    """Persist one JSON artifact with stable formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(BaseConfig.to_jsonable(payload), indent=2, sort_keys=True), encoding="utf-8")


__all__ = [
    "build_stage_manifests",
    "build_stage_status",
    "build_summary_manifest",
    "finalize_run_outputs",
    "stable_hash",
    "write_json",
]
