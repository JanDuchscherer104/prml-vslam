"""Tests for the typed pipeline planning surfaces."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from prml_vslam.pipeline import (
    CaptureManifest,
    CaptureMetadataConfig,
    MethodId,
    PipelineMode,
    PipelinePlannerService,
    RunPlanRequest,
    RunPlanStageId,
    TimestampSource,
    WorkspaceMaterializerService,
)


def test_pipeline_planner_builds_expected_stage_sequence() -> None:
    planner = PipelinePlannerService()
    request = RunPlanRequest(
        experiment_name="Lobby Sweep 01",
        video_path=Path("captures/lobby.mp4"),
        output_dir=Path("artifacts"),
        mode=PipelineMode.BATCH,
        method=MethodId.VISTA_SLAM,
        frame_stride=2,
        enable_dense_mapping=True,
        compare_to_arcore=True,
        build_ground_truth_cloud=True,
        capture=CaptureMetadataConfig(
            device_label="Pixel 8 Pro",
            frame_rate_hz=29.97,
            timestamp_source=TimestampSource.CAPTURE,
            arcore_log_path=Path("captures/lobby-arcore.json"),
        ),
    )

    plan = planner.build_plan(request)

    assert plan.artifact_root == Path("artifacts/lobby-sweep-01/batch/vista_slam")
    assert [stage.id for stage in plan.stages] == [
        RunPlanStageId.CAPTURE_MANIFEST,
        RunPlanStageId.VIDEO_DECODE,
        RunPlanStageId.METHOD_PREPARE,
        RunPlanStageId.SLAM_RUN,
        RunPlanStageId.TRAJECTORY_NORMALIZATION,
        RunPlanStageId.DENSE_NORMALIZATION,
        RunPlanStageId.ARCORE_ALIGNMENT,
        RunPlanStageId.REFERENCE_RECONSTRUCTION,
        RunPlanStageId.VISUALIZATION_EXPORT,
    ]
    assert plan.stages[0].outputs == [Path("artifacts/lobby-sweep-01/batch/vista_slam/input/capture_manifest.json")]


def test_pipeline_planner_omits_optional_stages_when_disabled() -> None:
    planner = PipelinePlannerService()
    request = RunPlanRequest(
        experiment_name="Quick Check",
        video_path=Path("captures/quick-check.mp4"),
        output_dir=Path("artifacts"),
        mode=PipelineMode.BATCH,
        method=MethodId.MAST3R_SLAM,
        enable_dense_mapping=False,
        compare_to_arcore=False,
        build_ground_truth_cloud=False,
    )

    plan = planner.build_plan(request)

    assert [stage.id for stage in plan.stages] == [
        RunPlanStageId.CAPTURE_MANIFEST,
        RunPlanStageId.VIDEO_DECODE,
        RunPlanStageId.METHOD_PREPARE,
        RunPlanStageId.SLAM_RUN,
        RunPlanStageId.TRAJECTORY_NORMALIZATION,
        RunPlanStageId.VISUALIZATION_EXPORT,
    ]


def test_workspace_materializer_creates_manifest_plan_and_stub_outputs(tmp_path: Path) -> None:
    materializer = WorkspaceMaterializerService()
    request = RunPlanRequest(
        experiment_name="Atrium Run",
        video_path=Path("captures/atrium.mp4"),
        output_dir=tmp_path / "artifacts",
        mode=PipelineMode.BATCH,
        method=MethodId.VISTA_SLAM,
        compare_to_arcore=True,
        build_ground_truth_cloud=True,
        capture=CaptureMetadataConfig(
            device_label="Pixel 8 Pro",
            frame_rate_hz=30.0,
            timestamp_source=TimestampSource.CAPTURE,
            arcore_log_path=Path("captures/atrium-arcore.json"),
            notes="Daylight walkthrough",
        ),
    )

    workspace = materializer.materialize(request)

    artifact_root = tmp_path / "artifacts" / "atrium-run" / "batch" / "vista_slam"
    assert workspace.artifact_root == artifact_root
    assert workspace.capture_manifest_path.exists()
    assert workspace.run_request_path.exists()
    assert workspace.run_plan_path.exists()
    assert (artifact_root / "slam" / "trajectory.tum").exists()
    assert (artifact_root / "slam" / "trajectory.metadata.json").exists()
    assert (artifact_root / "dense" / "dense_points.ply").exists()
    assert (artifact_root / "dense" / "dense_points.metadata.json").exists()
    assert (artifact_root / "evaluation" / "arcore_alignment.json").exists()

    manifest = CaptureManifest.model_validate_json(workspace.capture_manifest_path.read_text(encoding="utf-8"))
    assert manifest.experiment_name == "Atrium Run"
    assert manifest.capture.device_label == "Pixel 8 Pro"
    assert manifest.capture.timestamp_source is TimestampSource.CAPTURE

    trajectory_sidecar = json.loads((artifact_root / "slam" / "trajectory.metadata.json").read_text(encoding="utf-8"))
    assert trajectory_sidecar["transform_convention"] == "T_world_camera"
    assert trajectory_sidecar["timestamp_source"] == TimestampSource.CAPTURE.value


def test_workspace_materializer_refuses_to_overwrite_existing_artifacts(tmp_path: Path) -> None:
    materializer = WorkspaceMaterializerService()
    request = RunPlanRequest(
        experiment_name="Quick Check",
        video_path=Path("captures/quick-check.mp4"),
        output_dir=tmp_path / "artifacts",
        mode=PipelineMode.BATCH,
        method=MethodId.MAST3R_SLAM,
    )

    artifact_root = tmp_path / "artifacts" / "quick-check" / "batch" / "mast3r_slam"
    existing_path = artifact_root / "planning" / "run_plan.toml"
    existing_path.parent.mkdir(parents=True, exist_ok=True)
    existing_path.write_text("existing", encoding="utf-8")

    with pytest.raises(FileExistsError, match="run_plan.toml"):
        materializer.materialize(request)
