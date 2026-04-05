"""Tests for the typed pipeline planning surfaces."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from prml_vslam.methods import MethodId
from prml_vslam.pipeline import (
    BenchmarkEvaluationConfig,
    CloudMetrics,
    DenseArtifacts,
    DenseConfig,
    EfficiencyMetrics,
    ReferenceArtifacts,
    ReferenceConfig,
    RunRequest,
    TrackingConfig,
    TrajectoryMetrics,
    VideoSourceSpec,
)
from prml_vslam.pipeline.contracts import ArtifactRef, RunPlanStageId
from prml_vslam.pipeline.services import RunPlannerService
from prml_vslam.utils import PathConfig


def test_run_request_builds_expected_stage_sequence_from_direct_config() -> None:
    path_config = PathConfig()
    request = RunRequest(
        experiment_name="Lobby Sweep 01",
        output_dir=Path("artifacts"),
        source=VideoSourceSpec(video_path=Path("captures/lobby.mp4"), frame_stride=2),
        tracking=TrackingConfig(method=MethodId.VISTA),
        dense=DenseConfig(enabled=True),
        reference=ReferenceConfig(enabled=True),
        evaluation=BenchmarkEvaluationConfig(
            compare_to_arcore=True,
            evaluate_cloud=True,
            evaluate_efficiency=True,
        ),
    )
    plan = request.build(path_config)
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


def test_run_request_build_delegates_to_run_planner_service() -> None:
    request = RunRequest(
        experiment_name="Delegate Check",
        output_dir=Path("artifacts"),
        source=VideoSourceSpec(video_path=Path("captures/delegate-check.mp4")),
        tracking=TrackingConfig(method=MethodId.VISTA),
    )
    service_plan = RunPlannerService().build_run_plan(request)

    assert request.build() == service_plan


def test_run_request_build_keeps_legacy_default_stage_selection() -> None:
    request = RunRequest(
        experiment_name="Default Check",
        output_dir=Path("artifacts"),
        source=VideoSourceSpec(video_path=Path("captures/default-check.mp4")),
        tracking=TrackingConfig(method=MethodId.MSTR),
    )

    plan = request.build()

    assert [stage.id for stage in plan.stages] == [
        RunPlanStageId.INGEST,
        RunPlanStageId.SLAM,
        RunPlanStageId.DENSE_MAPPING,
        RunPlanStageId.TRAJECTORY_EVALUATION,
        RunPlanStageId.EFFICIENCY_EVALUATION,
        RunPlanStageId.SUMMARY,
    ]


def test_run_request_build_respects_disabled_optional_stage_toggles() -> None:
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


def test_run_request_requires_tracking_config() -> None:
    with pytest.raises(ValidationError):
        RunRequest(
            experiment_name="Missing Tracking",
            output_dir=Path("artifacts"),
            source=VideoSourceSpec(video_path=Path("captures/missing-tracking.mp4")),
        )


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
