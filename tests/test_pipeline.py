"""Tests for the typed pipeline planning surfaces."""

from __future__ import annotations

from pathlib import Path

from prml_vslam.pipeline import MethodId, PipelinePlannerService, RunPlanRequest, RunPlanStageId


def test_pipeline_planner_builds_expected_stage_sequence() -> None:
    planner = PipelinePlannerService()
    request = RunPlanRequest(
        experiment_name="Lobby Sweep 01",
        video_path=Path("captures/lobby.mp4"),
        output_dir=Path("artifacts"),
        method=MethodId.VISTA_SLAM,
        frame_stride=2,
        enable_dense_mapping=True,
        compare_to_arcore=True,
        build_ground_truth_cloud=True,
    )

    plan = planner.build_plan(request)

    assert plan.artifact_root == Path("artifacts/lobby-sweep-01/vista_slam")
    assert [stage.id for stage in plan.stages] == [
        RunPlanStageId.INGEST,
        RunPlanStageId.SLAM,
        RunPlanStageId.DENSE_MAPPING,
        RunPlanStageId.ARCORE_COMPARISON,
        RunPlanStageId.REFERENCE_RECONSTRUCTION,
    ]


def test_pipeline_planner_omits_optional_stages_when_disabled() -> None:
    planner = PipelinePlannerService()
    request = RunPlanRequest(
        experiment_name="Quick Check",
        video_path=Path("captures/quick-check.mp4"),
        output_dir=Path("artifacts"),
        method=MethodId.MAST3R_SLAM,
        enable_dense_mapping=False,
        compare_to_arcore=False,
        build_ground_truth_cloud=False,
    )

    plan = planner.build_plan(request)

    assert [stage.id for stage in plan.stages] == [
        RunPlanStageId.INGEST,
        RunPlanStageId.SLAM,
    ]
