"""Tests for the typed pipeline planning surfaces."""

from __future__ import annotations

from pathlib import Path

from prml_vslam.methods import MethodId
from prml_vslam.pipeline import (
    BenchmarkEvaluationConfig,
    DenseConfig,
    PipelineMode,
    PipelinePlannerService,
    ReferenceConfig,
    RunPlanStageId,
    RunRequest,
    TrackingConfig,
    VideoSourceSpec,
)


def test_pipeline_planner_builds_expected_stage_sequence() -> None:
    planner = PipelinePlannerService()
    request = RunRequest(
        experiment_name="Lobby Sweep 01",
        mode=PipelineMode.OFFLINE,
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

    plan = planner.build_plan(request)
    run_paths = planner.path_config.plan_run_paths(
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


def test_pipeline_planner_omits_optional_stages_when_disabled() -> None:
    planner = PipelinePlannerService()
    request = RunRequest(
        experiment_name="Quick Check",
        mode=PipelineMode.OFFLINE,
        output_dir=Path("artifacts"),
        source=VideoSourceSpec(video_path=Path("captures/quick-check.mp4")),
        tracking=TrackingConfig(method=MethodId.MSTR),
        dense=DenseConfig(enabled=False),
        reference=ReferenceConfig(enabled=False),
        evaluation=BenchmarkEvaluationConfig(
            compare_to_arcore=False,
            evaluate_cloud=False,
            evaluate_efficiency=False,
        ),
    )

    plan = planner.build_plan(request)

    assert [stage.id for stage in plan.stages] == [
        RunPlanStageId.INGEST,
        RunPlanStageId.SLAM,
        RunPlanStageId.SUMMARY,
    ]
