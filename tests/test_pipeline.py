"""Tests for the typed pipeline planning surfaces."""

from __future__ import annotations

from pathlib import Path

from prml_vslam.methods import MethodId
from prml_vslam.pipeline import (
    ArtifactRef,
    CloudEvaluationConfig,
    DenseArtifacts,
    DenseConfig,
    EfficiencyEvaluationConfig,
    ReferenceConfig,
    RunPlanStageId,
    RunRequest,
    TrackingConfig,
    TrajectoryEvaluationConfig,
    TrajectoryMetrics,
    VideoSourceSpec,
)
from prml_vslam.utils import PathConfig


def test_run_request_builder_builds_expected_stage_sequence() -> None:
    path_config = PathConfig()
    request = (
        RunRequest(
            experiment_name="Lobby Sweep 01",
            output_dir=Path("artifacts"),
            source=VideoSourceSpec(video_path=Path("captures/lobby.mp4"), frame_stride=2),
        )
        .add_tracking(TrackingConfig(method=MethodId.VISTA))
        .add_dense(DenseConfig())
        .add_reference(ReferenceConfig())
        .add_trajectory_evaluation(TrajectoryEvaluationConfig())
        .add_cloud_evaluation(CloudEvaluationConfig())
        .add_efficiency_evaluation(EfficiencyEvaluationConfig())
    )
    plan = request.build(path_config)
    assert request.tracking is not None
    run_paths = path_config.plan_run_paths(
        experiment_name=request.experiment_name,
        method_slug=request.tracking.method.artifact_slug,
        output_dir=request.output_dir,
    )

    assert plan.artifact_root == run_paths.artifact_root
    assert [stage.id for stage in plan.stages] == [
        RunPlanStageId.INGEST,
        RunPlanStageId.SLAM,
        RunPlanStageId.DENSE_MAPPING,
        RunPlanStageId.REFERENCE_RECONSTRUCTION,
        RunPlanStageId.TRAJECTORY_EVALUATION,
        RunPlanStageId.CLOUD_EVALUATION,
        RunPlanStageId.EFFICIENCY_EVALUATION,
        RunPlanStageId.SUMMARY,
    ]
    assert plan.stages[0].outputs == [run_paths.sequence_manifest_path]
    assert plan.stages[1].outputs == [run_paths.trajectory_path, run_paths.sparse_points_path]
    assert plan.stages[-1].outputs == [run_paths.summary_path]
    assert request.model_dump()["evaluation"] == {
        "compare_to_arcore": True,
        "evaluate_cloud": True,
        "evaluate_efficiency": True,
    }


def test_run_request_build_keeps_legacy_field_based_defaults() -> None:
    request = RunRequest(
        experiment_name="Quick Check",
        output_dir=Path("artifacts"),
        source=VideoSourceSpec(video_path=Path("captures/quick-check.mp4")),
        tracking=TrackingConfig(method=MethodId.MSTR),
        dense=DenseConfig(enabled=False),
        reference=ReferenceConfig(enabled=False),
    )
    request.evaluation.compare_to_arcore = False
    request.evaluation.evaluate_cloud = False
    request.evaluation.evaluate_efficiency = False

    plan = request.build()

    assert [stage.id for stage in plan.stages] == [
        RunPlanStageId.INGEST,
        RunPlanStageId.SLAM,
        RunPlanStageId.SUMMARY,
    ]


def test_single_artifact_bundle_preserves_public_dump_key() -> None:
    artifact = ArtifactRef(path=Path("artifacts/dense.ply"), kind="ply", fingerprint="abc123")
    dense = DenseArtifacts(dense_points_ply=artifact)

    assert dense.dense_points_ply == artifact
    assert dense.model_dump() == {"dense_points_ply": artifact.model_dump()}


def test_metrics_bundle_alias_preserves_metrics_json_dump() -> None:
    artifact = ArtifactRef(path=Path("artifacts/trajectory.json"), kind="json", fingerprint="def456")
    metrics = TrajectoryMetrics(metrics_json=artifact)

    assert metrics.metrics_json == artifact
    assert metrics.model_dump() == {"metrics_json": artifact.model_dump()}
