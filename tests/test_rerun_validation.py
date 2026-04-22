"""Tests for repo-owned Rerun validation helpers."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rerun.dataframe as rdf

from prml_vslam.interfaces import CameraIntrinsics, FrameTransform
from prml_vslam.interfaces.slam import KeyframeVisualizationReady, PoseEstimated
from prml_vslam.pipeline.contracts.events import BackendNoticeReceived
from prml_vslam.pipeline.contracts.handles import ArrayHandle
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.sinks.rerun_policy import RerunLoggingPolicy
from prml_vslam.visualization import rerun as rerun_helpers
from prml_vslam.visualization.validation import load_recording_summary, write_validation_bundle


def test_load_recording_summary_reports_live_keyed_and_tracking_surfaces(tmp_path: Path) -> None:
    recording_path = _write_synthetic_recording(tmp_path)

    summary = load_recording_summary(recording_path)

    assert summary.live_model_points is not None
    assert summary.live_model_points.point_count == 1
    assert len(summary.keyed_point_clouds) == 2
    assert summary.keyed_point_clouds[0].entity_path == "/world/keyframes/points/000000/points"
    assert len(summary.keyed_camera_entities) == 2
    assert summary.tracking_positions_xyz == [(0.0, 0.0, 0.0), (1.0, 0.5, 0.25)]


def test_write_validation_bundle_emits_report_and_projection_images(tmp_path: Path) -> None:
    recording_path = _write_synthetic_recording(tmp_path)
    output_dir = tmp_path / "validation"

    artifacts = write_validation_bundle(recording_path, output_dir=output_dir)

    assert artifacts.summary_json.exists()
    assert artifacts.summary_markdown.exists()
    assert artifacts.map_xy_png.exists()
    assert artifacts.map_xz_png.exists()
    assert '"keyed_point_clouds"' in artifacts.summary_json.read_text(encoding="utf-8")
    assert "# Rerun Validation Summary" in artifacts.summary_markdown.read_text(encoding="utf-8")


def test_write_validation_bundle_respects_explicit_keyed_cloud_limit(tmp_path: Path) -> None:
    recording_path = _write_synthetic_recording(tmp_path)
    output_dir = tmp_path / "validation"

    artifacts = write_validation_bundle(recording_path, output_dir=output_dir, max_keyed_clouds=1)
    summary = json.loads(artifacts.summary_json.read_text(encoding="utf-8"))

    assert len(summary["keyed_point_clouds"]) == 1
    assert summary["keyed_point_clouds"][0]["entity_path"].startswith("/world/keyframes/points/")


def _write_synthetic_recording(tmp_path: Path) -> Path:
    stream = rerun_helpers.create_recording_stream(app_id="prml-vslam-test", recording_id="validation-loop")
    policy = RerunLoggingPolicy(
        log_pinhole=rerun_helpers.log_pinhole,
        log_pointcloud=rerun_helpers.log_pointcloud,
        log_line_strip3d=rerun_helpers.log_line_strip3d,
        log_clear=rerun_helpers.log_clear,
        log_depth_image=rerun_helpers.log_depth_image,
        log_ground_plane_patch=rerun_helpers.log_ground_plane_patch,
        log_rgb_image=rerun_helpers.log_rgb_image,
        log_transform=rerun_helpers.log_transform,
        frusta_history_window_streaming=None,
        show_tracking_trajectory=True,
    )

    poses = [
        FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
        FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=0.5, tz=0.25),
    ]
    pointmaps = [
        np.array([[[0.5, 0.0, 2.0], [0.0, 0.0, 0.0]]], dtype=np.float32),
        np.array([[[-0.25, 0.1, 1.5], [0.0, 0.0, 0.0]]], dtype=np.float32),
    ]
    intrinsics = CameraIntrinsics(fx=2.0, fy=2.0, cx=1.0, cy=1.0, width_px=4, height_px=3)

    for frame_index, (pose, pointmap) in enumerate(zip(poses, pointmaps, strict=True), start=1):
        policy.observe(
            stream,
            BackendNoticeReceived(
                event_id=f"pose-{frame_index}",
                run_id="run-1",
                ts_ns=frame_index,
                stage_key=StageKey.SLAM,
                notice=PoseEstimated(
                    seq=frame_index,
                    timestamp_ns=frame_index,
                    source_seq=frame_index,
                    source_timestamp_ns=frame_index,
                    pose=pose,
                ),
            ),
            payloads={},
        )
        policy.observe(
            stream,
            BackendNoticeReceived(
                event_id=f"keyframe-{frame_index}",
                run_id="run-1",
                ts_ns=frame_index,
                stage_key=StageKey.SLAM,
                notice=KeyframeVisualizationReady(
                    seq=frame_index,
                    timestamp_ns=frame_index,
                    source_seq=frame_index,
                    source_timestamp_ns=frame_index,
                    keyframe_index=frame_index - 1,
                    pose=pose,
                    image=ArrayHandle(handle_id=f"rgb-{frame_index}", shape=(3, 4, 3), dtype="uint8"),
                    pointmap=ArrayHandle(handle_id=f"pointmap-{frame_index}", shape=pointmap.shape, dtype="float32"),
                    camera_intrinsics=intrinsics,
                ),
            ),
            payloads={
                f"rgb-{frame_index}": np.full((3, 4, 3), frame_index * 32, dtype=np.uint8),
                f"pointmap-{frame_index}": pointmap,
            },
        )

    recording_path = tmp_path / "validation-loop.rrd"
    recording_path.write_bytes(stream.memory_recording().drain_as_bytes())
    rdf.load_recording(recording_path)
    return recording_path
