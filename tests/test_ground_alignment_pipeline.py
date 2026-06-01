"""Focused tests for pipeline integration of the `gravity.align` stage."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from prml_vslam.alignment.contracts import GroundAlignmentConfig
from prml_vslam.alignment.stage import (
    GroundAlignmentKeyframeSample,
    GroundAlignmentRuntime,
    GroundAlignmentStageInput,
    GroundAlignmentStreamingStartInput,
)
from prml_vslam.interfaces import FrameTransform
from prml_vslam.interfaces.alignment import GroundAlignmentMetadata
from prml_vslam.interfaces.artifacts import ArtifactRef
from prml_vslam.interfaces.slam import SlamArtifacts
from prml_vslam.methods.stage.backend_config import MethodId, VistaSlamBackendConfig
from prml_vslam.pipeline import PipelineMode
from prml_vslam.pipeline.config import build_run_config
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.sources.config import VideoSourceConfig
from prml_vslam.utils import PathConfig, RunArtifactPaths


def test_run_config_build_rejects_ground_alignment_without_point_cloud_outputs(tmp_path: Path) -> None:
    path_config = PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts")
    run_config = build_run_config(
        experiment_name="ground-align-validation",
        mode=PipelineMode.OFFLINE,
        output_dir=path_config.artifacts_dir,
        source_backend=VideoSourceConfig(video_path=Path("captures/demo.mp4")),
        method=MethodId.VISTA,
        emit_dense_points=False,
        emit_sparse_points=False,
        ground_alignment_enabled=True,
    )

    with pytest.raises(ValueError, match="Ground alignment requires sparse or dense point-cloud outputs"):
        run_config.compile_plan(path_config, fail_on_unavailable=True)


def test_streaming_ground_alignment_requires_dense_keyframe_pointmaps(tmp_path: Path) -> None:
    path_config = PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts")
    run_config = build_run_config(
        experiment_name="ground-align-streaming-validation",
        mode=PipelineMode.STREAMING,
        output_dir=path_config.artifacts_dir,
        source_backend=VideoSourceConfig(video_path=Path("captures/demo.mp4")),
        method=MethodId.VISTA,
        emit_dense_points=False,
        emit_sparse_points=True,
        ground_alignment_enabled=True,
    )

    with pytest.raises(ValueError, match="Streaming ground alignment requires dense keyframe pointmaps"):
        run_config.compile_plan(path_config, fail_on_unavailable=True)


def test_stage_registry_places_ground_alignment_between_slam_and_trajectory(tmp_path: Path) -> None:
    path_config = PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts")
    run_config = build_run_config(
        experiment_name="ground-align-order",
        mode=PipelineMode.OFFLINE,
        output_dir=path_config.artifacts_dir,
        source_backend=VideoSourceConfig(video_path=Path("captures/demo.mp4")),
        method=MethodId.VISTA,
        trajectory_eval_enabled=True,
        ground_alignment_enabled=True,
    )

    plan = run_config.compile_plan(path_config)

    assert [stage.key for stage in plan.stages] == [
        StageKey.SOURCE,
        StageKey.SLAM,
        StageKey.GRAVITY_ALIGNMENT,
        StageKey.TRAJECTORY_EVALUATION,
        StageKey.SUMMARY,
    ]


def test_stage_registry_marks_ground_alignment_unavailable_without_backend_point_cloud_support(tmp_path: Path) -> None:
    class NoPointCloudVistaBackendConfig(VistaSlamBackendConfig):
        @property
        def supports_dense_points(self) -> bool:
            return False

    path_config = PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts")
    run_config = build_run_config(
        experiment_name="ground-align-unavailable",
        mode=PipelineMode.OFFLINE,
        output_dir=path_config.artifacts_dir,
        source_backend=VideoSourceConfig(video_path=Path("captures/demo.mp4")),
        method=MethodId.VISTA,
        ground_alignment_enabled=True,
    )
    backend = NoPointCloudVistaBackendConfig()

    plan = run_config.compile_plan(path_config=path_config, backend=backend)
    ground_stage = next(stage for stage in plan.stages if stage.key is StageKey.GRAVITY_ALIGNMENT)

    assert ground_stage.available is False
    assert "point-cloud" in (ground_stage.availability_reason or "")


def test_run_artifact_paths_include_ground_alignment_json(tmp_path: Path) -> None:
    run_paths = RunArtifactPaths.build(tmp_path / "run")

    assert run_paths.ground_alignment_path == (tmp_path / "run" / "alignment" / "ground_alignment.json").resolve()


def test_run_ground_alignment_stage_writes_metadata_and_returns_skipped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path_config = PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts")
    run_config = build_run_config(
        experiment_name="ground-align-stage",
        mode=PipelineMode.OFFLINE,
        output_dir=path_config.artifacts_dir,
        source_backend=VideoSourceConfig(video_path=Path("captures/demo.mp4")),
        method=MethodId.VISTA,
        ground_alignment_enabled=True,
    )
    plan = run_config.compile_plan(path_config)
    run_paths = RunArtifactPaths.build(plan.artifact_root)
    slam = SlamArtifacts(
        trajectory_tum=ArtifactRef(path=tmp_path / "trajectory.tum", kind="tum", fingerprint="traj"),
        dense_points_ply=ArtifactRef(path=tmp_path / "cloud.ply", kind="ply", fingerprint="cloud"),
    )

    class FakeGroundAlignmentService:
        def __init__(self, *, config) -> None:
            self.config = config

        def estimate_from_slam_artifacts(self, *, slam: SlamArtifacts) -> GroundAlignmentMetadata:
            assert slam.dense_points_ply is not None
            return GroundAlignmentMetadata(
                applied=False,
                confidence=0.2,
                point_cloud_source="dense_points_ply",
                candidate_count=2,
                skip_reason="No reliable dominant ground plane found.",
            )

    del monkeypatch, plan

    result = GroundAlignmentRuntime(service_type=FakeGroundAlignmentService).run_offline(
        GroundAlignmentStageInput(config=run_config.stages.align_ground.ground, run_paths=run_paths, slam=slam)
    )

    assert result.outcome.stage_key is StageKey.GRAVITY_ALIGNMENT
    assert result.outcome.status.value == "skipped"
    assert run_paths.ground_alignment_path.exists()
    payload = json.loads(run_paths.ground_alignment_path.read_text(encoding="utf-8"))
    assert payload["applied"] is False
    assert payload["skip_reason"] == "No reliable dominant ground plane found."


def test_run_ground_alignment_stage_writes_applied_metadata_when_export_enabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path_config = PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts")
    run_config = build_run_config(
        experiment_name="ground-align-viewer",
        mode=PipelineMode.OFFLINE,
        output_dir=path_config.artifacts_dir,
        source_backend=VideoSourceConfig(video_path=Path("captures/demo.mp4")),
        method=MethodId.VISTA,
        ground_alignment_enabled=True,
        export_viewer_rrd=True,
    )
    plan = run_config.compile_plan(path_config)
    run_paths = RunArtifactPaths.build(plan.artifact_root)
    slam = SlamArtifacts(
        trajectory_tum=ArtifactRef(path=tmp_path / "trajectory.tum", kind="tum", fingerprint="traj"),
        dense_points_ply=ArtifactRef(path=tmp_path / "cloud.ply", kind="ply", fingerprint="cloud"),
    )

    class FakeGroundAlignmentService:
        def __init__(self, *, config) -> None:
            self.config = config

        def estimate_from_slam_artifacts(self, *, slam: SlamArtifacts) -> GroundAlignmentMetadata:
            return GroundAlignmentMetadata(
                applied=True,
                confidence=0.9,
                point_cloud_source="dense_points_ply",
                visualization={"corners_xyz_world": [(0.0, 0.0, 0.0)] * 4},
            )

    del monkeypatch, plan

    result = GroundAlignmentRuntime(service_type=FakeGroundAlignmentService).run_offline(
        GroundAlignmentStageInput(config=run_config.stages.align_ground.ground, run_paths=run_paths, slam=slam)
    )

    assert result.outcome.status.value == "completed"
    assert isinstance(result.payload, GroundAlignmentMetadata)
    assert result.payload.applied is True
    payload = json.loads(run_paths.ground_alignment_path.read_text(encoding="utf-8"))
    assert payload["applied"] is True


def test_streaming_ground_alignment_runtime_runs_ransac_on_configured_keyframe_interval(tmp_path: Path) -> None:
    run_paths = RunArtifactPaths.build(tmp_path / "run")
    calls: list[tuple[int, str]] = []

    class FakeGroundAlignmentService:
        def __init__(self, *, config: GroundAlignmentConfig) -> None:
            self.config = config

        def estimate_from_world_points(
            self,
            *,
            points_xyz_world: np.ndarray,
            poses_world_camera: np.ndarray,
            point_cloud_source: str,
        ) -> GroundAlignmentMetadata:
            calls.append((len(points_xyz_world), point_cloud_source))
            assert poses_world_camera.shape == (2, 4, 4)
            return GroundAlignmentMetadata(
                applied=True,
                confidence=0.9,
                point_cloud_source="streaming_pointmaps",
                T_viewer_world_world=FrameTransform(
                    target_frame="viewer_world",
                    source_frame="world",
                    qx=0.0,
                    qy=0.0,
                    qz=0.0,
                    qw=1.0,
                    tx=0.0,
                    ty=0.0,
                    tz=0.0,
                ),
                visualization={"corners_xyz_world": [(0.0, 0.0, 0.0)] * 4},
            )

    runtime = GroundAlignmentRuntime(service_type=FakeGroundAlignmentService)
    runtime.start_streaming(
        GroundAlignmentStreamingStartInput(
            config=GroundAlignmentConfig(ransac_interval_keyframes=2),
            run_paths=run_paths,
        )
    )
    sample = GroundAlignmentKeyframeSample(
        keyframe_index=0,
        T_world_camera=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=2.0, tz=3.0),
        pointmap_xyz_camera=np.asarray(
            [
                [[0.0, 0.0, 1.0], [1.0, 0.0, 2.0]],
                [[0.0, 0.0, 0.0], [0.0, 1.0, -1.0]],
            ],
            dtype=np.float32,
        ),
    )

    runtime.submit_stream_item(sample)

    assert calls == []
    assert runtime.drain_runtime_updates() == []

    runtime.submit_stream_item(sample.model_copy(update={"keyframe_index": 1}))
    updates = runtime.drain_runtime_updates()

    assert calls == [(4, "streaming_pointmaps")]
    assert len(updates) == 1
    assert updates[0].stage_key is StageKey.GRAVITY_ALIGNMENT
    assert isinstance(updates[0].semantic_events[0], GroundAlignmentMetadata)
    assert updates[0].semantic_events[0].point_cloud_source == "streaming_pointmaps"

    result = runtime.finish_streaming()

    assert result.outcome.status.value == "completed"
    assert run_paths.ground_alignment_path.exists()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]
