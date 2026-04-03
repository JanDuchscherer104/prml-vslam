"""Tests for the typed pipeline planning surfaces."""

from __future__ import annotations

from pathlib import Path

import pytest

from prml_vslam.methods import MethodId
from prml_vslam.pipeline import (
    ArtifactRef,
    BenchmarkEvaluationConfig,
    CloudEvaluationConfig,
    CloudMetrics,
    DenseArtifacts,
    DenseConfig,
    EfficiencyEvaluationConfig,
    EfficiencyMetrics,
    ReferenceArtifacts,
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


@pytest.mark.parametrize(
    ("builder_name", "field_name", "config_cls"),
    [
        ("add_dense", "dense", DenseConfig),
        ("add_reference", "reference", ReferenceConfig),
    ],
)
def test_stage_toggle_helpers_do_not_mutate_supplied_configs(
    builder_name: str,
    field_name: str,
    config_cls: type[DenseConfig] | type[ReferenceConfig],
) -> None:
    config = config_cls(enabled=False)
    request = RunRequest(
        experiment_name="Mutation Check",
        output_dir=Path("artifacts"),
        source=VideoSourceSpec(video_path=Path("captures/mutation-check.mp4")),
    )

    getattr(request, builder_name)(config)

    request_config = getattr(request, field_name)
    assert config.enabled is False
    assert request_config.enabled is True
    assert request_config is not config


@pytest.mark.parametrize(
    ("builder_name", "field_name", "config_cls"),
    [
        ("add_trajectory_evaluation", "compare_to_arcore", TrajectoryEvaluationConfig),
        ("add_cloud_evaluation", "evaluate_cloud", CloudEvaluationConfig),
        ("add_efficiency_evaluation", "evaluate_efficiency", EfficiencyEvaluationConfig),
    ],
)
def test_evaluation_helpers_do_not_mutate_supplied_config(
    builder_name: str,
    field_name: str,
    config_cls: type[TrajectoryEvaluationConfig] | type[CloudEvaluationConfig] | type[EfficiencyEvaluationConfig],
) -> None:
    evaluation = BenchmarkEvaluationConfig(
        compare_to_arcore=False,
        evaluate_cloud=False,
        evaluate_efficiency=False,
    )
    request = RunRequest(
        experiment_name="Mutation Check",
        output_dir=Path("artifacts"),
        source=VideoSourceSpec(video_path=Path("captures/mutation-check.mp4")),
        evaluation=evaluation,
    )

    getattr(request, builder_name)(config_cls())

    assert getattr(evaluation, field_name) is False
    assert request.evaluation is not evaluation
    assert getattr(request.evaluation, field_name) is True


@pytest.mark.parametrize(
    ("bundle_cls", "field_name", "artifact_path"),
    [
        (DenseArtifacts, "dense_points_ply", "artifacts/dense.ply"),
        (ReferenceArtifacts, "reference_cloud_ply", "artifacts/reference.ply"),
    ],
)
def test_artifact_bundle_preserves_public_dump_key(
    bundle_cls: type[DenseArtifacts] | type[ReferenceArtifacts],
    field_name: str,
    artifact_path: str,
) -> None:
    artifact = ArtifactRef(path=Path(artifact_path), kind="ply", fingerprint="abc123")
    bundle = bundle_cls(**{field_name: artifact})

    assert getattr(bundle, field_name) == artifact
    assert bundle.model_dump() == {field_name: artifact.model_dump()}


@pytest.mark.parametrize("metrics_cls", [TrajectoryMetrics, CloudMetrics, EfficiencyMetrics])
def test_metrics_bundle_preserves_metrics_json_dump(
    metrics_cls: type[TrajectoryMetrics] | type[CloudMetrics] | type[EfficiencyMetrics],
) -> None:
    artifact = ArtifactRef(path=Path("artifacts/trajectory.json"), kind="json", fingerprint="def456")
    metrics = metrics_cls(metrics_json=artifact)

    assert metrics.metrics_json == artifact
    assert metrics.model_dump() == {"metrics_json": artifact.model_dump()}
