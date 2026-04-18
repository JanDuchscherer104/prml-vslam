"""Tests for repo-owned streaming Rerun sink behavior."""

from __future__ import annotations

import uuid
from pathlib import Path

import numpy as np

from prml_vslam.interfaces import CameraIntrinsics, FramePacketProvenance, FrameTransform
from prml_vslam.methods.events import KeyframeVisualizationReady, PoseEstimated
from prml_vslam.pipeline.contracts.events import BackendNoticeReceived, FramePacketSummary, PacketObserved
from prml_vslam.pipeline.contracts.handles import ArrayHandle, PreviewHandle
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.sinks import rerun as rerun_sink_module
from prml_vslam.pipeline.sinks.rerun import RerunEventSink, RerunSinkActor
from prml_vslam.utils.geometry import transform_points_world_camera


class _FakeRecordingStream:
    def __init__(self) -> None:
        self.timelines: dict[str, int] = {}

    def log(self, entity_path: str, payload: object) -> None:
        del entity_path, payload

    def set_time(self, timeline: str, *, sequence: int) -> None:
        self.timelines[timeline] = sequence

    def disable_timeline(self, timeline: str) -> None:
        self.timelines.pop(timeline, None)

    def current_timeline(self, timeline: str) -> int | None:
        return self.timelines.get(timeline)


def test_rerun_sink_is_noop_when_handles_are_unavailable(tmp_path: Path) -> None:
    sink = RerunEventSink(grpc_url=None, target_path=tmp_path / "viewer.rrd")
    event = BackendNoticeReceived(
        event_id="1",
        run_id=f"run-{uuid.uuid4().hex}",
        ts_ns=1,
        stage_key=StageKey.SLAM,
        notice=PoseEstimated(
            seq=1,
            timestamp_ns=1,
            pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
        ),
    )

    sink.observe(event, resolve_handle=lambda _handle_id: None)


def test_rerun_sink_logs_fixed_camera_complete_branches(tmp_path: Path, monkeypatch) -> None:
    calls: list[tuple[str, str, int | None]] = []

    monkeypatch.setattr(rerun_sink_module, "create_recording_stream", lambda **_: _FakeRecordingStream())
    monkeypatch.setattr(rerun_sink_module, "attach_recording_sinks", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        rerun_sink_module,
        "log_pinhole",
        lambda stream, *, entity_path, intrinsics: calls.append(
            ("pinhole", entity_path, stream.current_timeline("keyframe"))
        ),
    )
    monkeypatch.setattr(
        rerun_sink_module,
        "log_rgb_image",
        lambda stream, *, entity_path, image_rgb: calls.append(
            ("rgb", entity_path, stream.current_timeline("keyframe"))
        ),
    )
    monkeypatch.setattr(
        rerun_sink_module,
        "log_depth_image",
        lambda stream, *, entity_path, depth_m: calls.append(
            ("depth", entity_path, stream.current_timeline("keyframe"))
        ),
    )
    monkeypatch.setattr(
        rerun_sink_module,
        "log_transform",
        lambda stream, *, entity_path, transform, axis_length=None: calls.append(
            ("pose", entity_path, stream.current_timeline("keyframe"))
        ),
    )
    monkeypatch.setattr(
        rerun_sink_module,
        "log_pointcloud",
        lambda stream, *, entity_path, pointmap, colors=None: calls.append(
            ("points", entity_path, stream.current_timeline("keyframe"))
        ),
    )

    sink = RerunEventSink(
        grpc_url=None,
        target_path=tmp_path / "viewer.rrd",
    )

    event = BackendNoticeReceived(
        event_id="1",
        run_id=f"run-{uuid.uuid4().hex}",
        ts_ns=1,
        stage_key=StageKey.SLAM,
        notice=KeyframeVisualizationReady(
            seq=1,
            timestamp_ns=1,
            source_seq=1,
            source_timestamp_ns=1,
            keyframe_index=3,
            pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
            preview=PreviewHandle(handle_id="preview", width=4, height=3, channels=3, dtype="uint8"),
            image=ArrayHandle(handle_id="rgb", shape=(3, 4, 3), dtype="uint8"),
            depth=ArrayHandle(handle_id="depth", shape=(3, 4), dtype="float32"),
            pointmap=ArrayHandle(handle_id="pointmap", shape=(3, 4, 3), dtype="float32"),
            camera_intrinsics=CameraIntrinsics(fx=2.0, fy=2.0, cx=1.0, cy=1.0, width_px=4, height_px=3),
        ),
    )

    sink.observe(
        event,
        resolve_handle=lambda handle_id: {
            "preview": np.zeros((3, 4, 3), dtype=np.uint8),
            "rgb": np.zeros((3, 4, 3), dtype=np.uint8),
            "depth": np.ones((3, 4), dtype=np.float32),
            "pointmap": np.ones((3, 4, 3), dtype=np.float32),
        }[handle_id],
    )

    assert calls == [
        ("pose", "world/live/camera", None),
        ("pinhole", "world/live/camera/cam", None),
        ("rgb", "world/live/camera/cam", None),
        ("depth", "world/live/camera/cam/depth", None),
        ("rgb", "world/live/camera/preview", None),
        ("pose", "world/live/pointmap", None),
        ("points", "world/live/pointmap/points", None),
        ("pose", "world/est/cameras/cam_000003", 3),
        ("pinhole", "world/est/cameras/cam_000003/cam", 3),
        ("rgb", "world/est/cameras/cam_000003/cam", 3),
        ("depth", "world/est/cameras/cam_000003/cam/depth", 3),
        ("rgb", "world/est/cameras/cam_000003/preview", 3),
        ("pose", "world/est/pointmaps/cam_000003", 3),
        ("points", "world/est/pointmaps/cam_000003/points", 3),
    ]


def test_rerun_sink_logs_pointmaps_under_live_and_keyframe_entities(tmp_path: Path, monkeypatch) -> None:
    calls: list[tuple[str, str, int | None]] = []
    captured_transforms: dict[str, FrameTransform] = {}
    captured_pointmaps: dict[str, np.ndarray] = {}

    monkeypatch.setattr(rerun_sink_module, "create_recording_stream", lambda **_: _FakeRecordingStream())
    monkeypatch.setattr(rerun_sink_module, "attach_recording_sinks", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        rerun_sink_module,
        "log_transform",
        lambda stream, *, entity_path, transform, axis_length=None: (
            calls.append(("pose", entity_path, stream.current_timeline("keyframe"))),
            captured_transforms.__setitem__(entity_path, transform),
        ),
    )
    monkeypatch.setattr(
        rerun_sink_module,
        "log_pointcloud",
        lambda stream, *, entity_path, pointmap, colors=None: (
            calls.append(("points", entity_path, stream.current_timeline("keyframe"))),
            captured_pointmaps.__setitem__(entity_path, np.asarray(pointmap)),
        ),
    )

    sink = RerunEventSink(
        grpc_url=None,
        target_path=tmp_path / "viewer.rrd",
    )

    event = BackendNoticeReceived(
        event_id="1",
        run_id=f"run-{uuid.uuid4().hex}",
        ts_ns=1,
        stage_key=StageKey.SLAM,
        notice=KeyframeVisualizationReady(
            seq=1,
            timestamp_ns=1,
            source_seq=1,
            source_timestamp_ns=1,
            keyframe_index=0,
            pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=2.0, tz=1.0),
            pointmap=ArrayHandle(handle_id="pointmap", shape=(1, 1, 3), dtype="float32"),
        ),
    )

    sink.observe(
        event,
        resolve_handle=lambda _handle_id: np.array([[[0.5, 0.0, 2.0]]], dtype=np.float32),
    )

    assert calls == [
        ("pose", "world/live/camera", None),
        ("pose", "world/live/pointmap", None),
        ("points", "world/live/pointmap/points", None),
        ("pose", "world/est/cameras/cam_000000", 0),
        ("pose", "world/est/pointmaps/cam_000000", 0),
        ("points", "world/est/pointmaps/cam_000000/points", 0),
    ]

    live_camera_transform = captured_transforms["world/live/pointmap"]
    live_pointmap = captured_pointmaps["world/live/pointmap/points"]
    live_world_points = transform_points_world_camera(live_pointmap.reshape(-1, 3), live_camera_transform)

    camera_transform = captured_transforms["world/est/pointmaps/cam_000000"]
    pointmap = captured_pointmaps["world/est/pointmaps/cam_000000/points"]
    world_points = transform_points_world_camera(pointmap.reshape(-1, 3), camera_transform)

    np.testing.assert_allclose(live_world_points[0], np.array([1.5, 2.0, 3.0]))
    np.testing.assert_allclose(world_points[0], np.array([1.5, 2.0, 3.0]))


def test_rerun_sink_logs_source_rgb_and_live_pose(tmp_path: Path, monkeypatch) -> None:
    calls: list[tuple[str, str, int | None]] = []

    monkeypatch.setattr(rerun_sink_module, "create_recording_stream", lambda **_: _FakeRecordingStream())
    monkeypatch.setattr(rerun_sink_module, "attach_recording_sinks", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        rerun_sink_module,
        "log_rgb_image",
        lambda stream, *, entity_path, image_rgb: calls.append(
            ("rgb", entity_path, stream.current_timeline("keyframe"))
        ),
    )
    monkeypatch.setattr(
        rerun_sink_module,
        "log_transform",
        lambda stream, *, entity_path, transform, axis_length=None: calls.append(
            ("pose", entity_path, stream.current_timeline("keyframe"))
        ),
    )

    sink = RerunEventSink(
        grpc_url=None,
        target_path=tmp_path / "viewer.rrd",
    )

    packet_event = PacketObserved(
        event_id="1",
        run_id=f"run-{uuid.uuid4().hex}",
        ts_ns=1,
        packet=FramePacketSummary(seq=1, timestamp_ns=1, provenance=FramePacketProvenance(source_id="fake")),
        frame=ArrayHandle(handle_id="frame", shape=(2, 2, 3), dtype="uint8"),
        received_frames=1,
        measured_fps=30.0,
    )
    pose_event = BackendNoticeReceived(
        event_id="2",
        run_id=f"run-{uuid.uuid4().hex}",
        ts_ns=2,
        stage_key=StageKey.SLAM,
        notice=PoseEstimated(
            seq=1,
            timestamp_ns=1,
            pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
        ),
    )

    sink.observe(packet_event, resolve_handle=lambda _handle_id: np.zeros((2, 2, 3), dtype=np.uint8))
    sink.observe(pose_event, resolve_handle=lambda _handle_id: None)

    assert calls == [
        ("rgb", "world/live/source/rgb", None),
        ("pose", "world/live/camera", None),
    ]


def test_rerun_sink_does_not_log_root_world_coordinates(tmp_path: Path, monkeypatch) -> None:
    paths: list[tuple[str, int | None]] = []

    monkeypatch.setattr(rerun_sink_module, "create_recording_stream", lambda **_: _FakeRecordingStream())
    monkeypatch.setattr(rerun_sink_module, "attach_recording_sinks", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        rerun_sink_module,
        "log_transform",
        lambda stream, *, entity_path, transform, axis_length=None: paths.append(
            (entity_path, stream.current_timeline("keyframe"))
        ),
    )

    sink = RerunEventSink(
        grpc_url=None,
        target_path=tmp_path / "viewer.rrd",
    )
    sink.observe(
        BackendNoticeReceived(
            event_id="1",
            run_id=f"run-{uuid.uuid4().hex}",
            ts_ns=1,
            stage_key=StageKey.SLAM,
            notice=PoseEstimated(
                seq=1,
                timestamp_ns=1,
                pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
            ),
        ),
        resolve_handle=lambda _handle_id: None,
    )

    assert paths == [("world/live/camera", None)]
    assert "world" not in [path for path, _ in paths]


def test_rerun_sink_clears_stale_keyframe_timeline_before_pose_estimate(tmp_path: Path, monkeypatch) -> None:
    calls: list[tuple[str, str, int | None]] = []

    monkeypatch.setattr(rerun_sink_module, "create_recording_stream", lambda **_: _FakeRecordingStream())
    monkeypatch.setattr(rerun_sink_module, "attach_recording_sinks", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        rerun_sink_module,
        "log_transform",
        lambda stream, *, entity_path, transform, axis_length=None: calls.append(
            ("pose", entity_path, stream.current_timeline("keyframe"))
        ),
    )

    sink = RerunEventSink(
        grpc_url=None,
        target_path=tmp_path / "viewer.rrd",
    )
    sink._stream.set_time("keyframe", sequence=7)  # type: ignore[union-attr]

    sink.observe(
        BackendNoticeReceived(
            event_id="1",
            run_id=f"run-{uuid.uuid4().hex}",
            ts_ns=1,
            stage_key=StageKey.SLAM,
            notice=PoseEstimated(
                seq=2,
                timestamp_ns=2,
                pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=0.0, tz=0.0),
            ),
        ),
        resolve_handle=lambda _handle_id: None,
    )

    assert calls == [("pose", "world/live/camera", None)]


def test_rerun_sink_clears_stale_keyframe_timeline_after_keyframe_visualization(tmp_path: Path, monkeypatch) -> None:
    calls: list[tuple[str, str, int | None]] = []

    monkeypatch.setattr(rerun_sink_module, "create_recording_stream", lambda **_: _FakeRecordingStream())
    monkeypatch.setattr(rerun_sink_module, "attach_recording_sinks", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        rerun_sink_module,
        "log_transform",
        lambda stream, *, entity_path, transform, axis_length=None: calls.append(
            ("pose", entity_path, stream.current_timeline("keyframe"))
        ),
    )

    sink = RerunEventSink(
        grpc_url=None,
        target_path=tmp_path / "viewer.rrd",
    )
    sink.observe(
        BackendNoticeReceived(
            event_id="1",
            run_id=f"run-{uuid.uuid4().hex}",
            ts_ns=1,
            stage_key=StageKey.SLAM,
            notice=KeyframeVisualizationReady(
                seq=1,
                timestamp_ns=1,
                source_seq=1,
                source_timestamp_ns=1,
                keyframe_index=4,
                pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
                pointmap=ArrayHandle(handle_id="pointmap", shape=(1, 1, 3), dtype="float32"),
            ),
        ),
        resolve_handle=lambda _handle_id: np.array([[[0.0, 0.0, 1.0]]], dtype=np.float32),
    )
    sink.observe(
        BackendNoticeReceived(
            event_id="2",
            run_id=f"run-{uuid.uuid4().hex}",
            ts_ns=2,
            stage_key=StageKey.SLAM,
            notice=PoseEstimated(
                seq=2,
                timestamp_ns=2,
                pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=0.0, tz=0.0),
            ),
        ),
        resolve_handle=lambda _handle_id: None,
    )

    assert calls[-1] == ("pose", "world/live/camera", None)


def test_rerun_sink_actor_forwards_materialized_bindings_to_local_sink(tmp_path: Path, monkeypatch) -> None:
    observed: dict[str, object] = {}

    class FakeLocalSink:
        def __init__(self, **kwargs: object) -> None:
            observed["init"] = kwargs

        def observe(self, event, *, resolve_handle) -> None:
            observed["event"] = event
            observed["payload"] = resolve_handle("frame")

        def close(self) -> None:
            observed["closed"] = True

    monkeypatch.setattr(rerun_sink_module, "RerunEventSink", FakeLocalSink)

    actor_cls = RerunSinkActor.__ray_metadata__.modified_class
    actor = actor_cls(
        grpc_url=None,
        target_path=tmp_path / "viewer.rrd",
        recording_id="demo",
    )
    actor.observe_event(
        event=PacketObserved(
            event_id="1",
            run_id="demo",
            ts_ns=1,
            packet=FramePacketSummary(seq=1, timestamp_ns=1, provenance=FramePacketProvenance()),
            frame=ArrayHandle(handle_id="frame", shape=(2, 2, 3), dtype="uint8"),
        ),
        bindings=[("frame", np.ones((2, 2, 3), dtype=np.uint8))],
    )
    actor.close()

    assert observed["init"]["recording_id"] == "demo"
    assert np.array_equal(observed["payload"], np.ones((2, 2, 3), dtype=np.uint8))
    assert observed["closed"] is True
