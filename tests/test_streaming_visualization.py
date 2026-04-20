"""Tests for repo-owned streaming Rerun sink behavior."""

from __future__ import annotations

import uuid
import warnings
from pathlib import Path

import numpy as np
import rerun.dataframe as rdf

from prml_vslam.interfaces import CameraIntrinsics, FramePacketProvenance, FrameTransform
from prml_vslam.interfaces.alignment import GroundAlignmentMetadata
from prml_vslam.interfaces.slam import KeyframeVisualizationReady, PoseEstimated
from prml_vslam.pipeline.contracts.events import (
    BackendNoticeReceived,
    FramePacketSummary,
    PacketObserved,
    StageCompleted,
    StageOutcome,
)
from prml_vslam.pipeline.contracts.handles import ArrayHandle, PreviewHandle
from prml_vslam.pipeline.contracts.provenance import StageStatus
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

    def reset_time(self) -> None:
        self.timelines.clear()

    def flush(self, blocking: bool = True) -> None:
        assert blocking is True

    def disconnect(self) -> None:
        return None

    def disable_timeline(self, timeline: str) -> None:  # pragma: no cover - should never be called
        raise AssertionError(f"disable_timeline must not be used in ordinary logging paths: {timeline}")

    def current_timeline(self, timeline: str) -> int | None:
        return self.timelines.get(timeline)


def _timeline_state(stream: _FakeRecordingStream) -> tuple[int | None, int | None]:
    return stream.current_timeline("frame"), stream.current_timeline("keyframe")


def _ground_alignment_metadata() -> GroundAlignmentMetadata:
    return GroundAlignmentMetadata(
        applied=True,
        confidence=0.9,
        point_cloud_source="dense_points_ply",
        ground_plane_world={
            "normal_xyz_world": (0.0, 1.0, 0.0),
            "offset_world": 0.0,
            "inlier_count": 16,
            "inlier_ratio": 0.8,
        },
        visualization={
            "corners_xyz_world": [
                (0.0, 0.0, 0.0),
                (0.0, 0.0, 1.0),
                (1.0, 0.0, 1.0),
                (1.0, 0.0, 0.0),
            ]
        },
    )


def _ground_alignment_event(*, event_id: str = "ground", run_id: str | None = None) -> StageCompleted:
    return StageCompleted(
        event_id=event_id,
        run_id=f"run-{uuid.uuid4().hex}" if run_id is None else run_id,
        ts_ns=1,
        stage_key=StageKey.GROUND_ALIGNMENT,
        outcome=StageOutcome(
            stage_key=StageKey.GROUND_ALIGNMENT,
            status=StageStatus.COMPLETED,
            config_hash="cfg",
            input_fingerprint="inp",
        ),
        ground_alignment=_ground_alignment_metadata(),
    )


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

    sink.observe(event, payloads={})


def test_rerun_sink_logs_ground_alignment_live_and_augments_export_on_close(tmp_path: Path, monkeypatch) -> None:
    viewer_path = tmp_path / "viewer.rrd"
    viewer_path.write_bytes(b"rrd")
    ground_calls: list[str] = []
    augment_calls: list[tuple[GroundAlignmentMetadata, Path, str]] = []
    stream_names = iter(["live", "export"])

    class FakeRecordingStream(_FakeRecordingStream):
        def __init__(self, *, name: str) -> None:
            super().__init__()
            self.name = name
            self.flushed = False
            self.disconnected = False

        def flush(self, blocking: bool = True) -> None:
            assert blocking is True
            self.flushed = True

        def disconnect(self) -> None:
            self.disconnected = True

    monkeypatch.setattr(
        rerun_sink_module,
        "create_recording_stream",
        lambda **_: FakeRecordingStream(name=next(stream_names)),
    )
    monkeypatch.setattr(rerun_sink_module, "attach_recording_sinks", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        rerun_sink_module,
        "log_ground_plane_patch",
        lambda stream, *, metadata, static=True: ground_calls.append(stream.name),
    )
    monkeypatch.setattr(
        rerun_sink_module,
        "augment_viewer_recording_with_ground_plane",
        lambda *, metadata, viewer_recording_path, recording_id: augment_calls.append(
            (metadata, viewer_recording_path, recording_id)
        ),
    )

    sink = RerunEventSink(
        grpc_url="rerun+http://127.0.0.1:9876/proxy",
        target_path=viewer_path,
        recording_id="demo-run",
    )

    sink.observe(_ground_alignment_event(run_id="demo-run"), payloads={})

    assert ground_calls == ["live"]

    sink.close()

    assert augment_calls == [(_ground_alignment_metadata(), viewer_path, "demo-run")]


def test_rerun_sink_close_stamps_ground_plane_overlay_as_static_in_exported_rrd(tmp_path: Path) -> None:
    viewer_path = tmp_path / "viewer.rrd"
    sink = RerunEventSink(grpc_url=None, target_path=viewer_path, recording_id="static-ground-plane")

    sink.observe(_ground_alignment_event(run_id="static-ground-plane"), payloads={})
    sink.close()

    recording = rdf.load_recording(viewer_path)
    fill_view = recording.view(index="log_tick", contents="/world/alignment/ground_plane/fill")
    outline_view = recording.view(index="log_tick", contents="/world/alignment/ground_plane/outline")

    fill_static_rows = [batch.to_pydict() for batch in fill_view.select_static()]
    outline_static_rows = [batch.to_pydict() for batch in outline_view.select_static()]

    assert len(fill_static_rows) == 1
    assert len(outline_static_rows) == 1

    np.testing.assert_allclose(
        np.asarray(fill_static_rows[0]["/world/alignment/ground_plane/fill:Mesh3D:vertex_positions"]).reshape(-1, 3),
        np.asarray(_ground_alignment_metadata().visualization.corners_xyz_world, dtype=np.float32),
    )
    np.testing.assert_array_equal(
        np.asarray(fill_static_rows[0]["/world/alignment/ground_plane/fill:Mesh3D:triangle_indices"]).reshape(-1, 3),
        np.asarray([[0, 1, 2], [0, 2, 3]], dtype=np.uint32),
    )
    np.testing.assert_allclose(
        np.asarray(outline_static_rows[0]["/world/alignment/ground_plane/outline:LineStrips3D:strips"]).reshape(-1, 3),
        np.asarray(
            [
                (0.0, 0.0, 0.0),
                (0.0, 0.0, 1.0),
                (1.0, 0.0, 1.0),
                (1.0, 0.0, 0.0),
                (0.0, 0.0, 0.0),
            ],
            dtype=np.float32,
        ),
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        assert [batch.to_pydict() for batch in fill_view.select()] == []
        assert [batch.to_pydict() for batch in outline_view.select()] == []


def test_rerun_sink_logs_live_model_and_keyframe_branches(tmp_path: Path, monkeypatch) -> None:
    calls: list[tuple[str, str, int | None, int | None]] = []
    transform_axis_lengths: dict[str, float | None] = {}

    monkeypatch.setattr(rerun_sink_module, "create_recording_stream", lambda **_: _FakeRecordingStream())
    monkeypatch.setattr(rerun_sink_module, "attach_recording_sinks", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        rerun_sink_module,
        "log_pinhole",
        lambda stream, *, entity_path, intrinsics: calls.append(("pinhole", entity_path, *_timeline_state(stream))),
    )
    monkeypatch.setattr(
        rerun_sink_module,
        "log_rgb_image",
        lambda stream, *, entity_path, image_rgb: calls.append(("rgb", entity_path, *_timeline_state(stream))),
    )
    monkeypatch.setattr(
        rerun_sink_module,
        "log_depth_image",
        lambda stream, *, entity_path, depth_m: calls.append(("depth", entity_path, *_timeline_state(stream))),
    )
    monkeypatch.setattr(
        rerun_sink_module,
        "log_transform",
        lambda stream, *, entity_path, transform, axis_length=None: (
            calls.append(("pose", entity_path, *_timeline_state(stream))),
            transform_axis_lengths.__setitem__(entity_path, axis_length),
        ),
    )
    monkeypatch.setattr(
        rerun_sink_module,
        "log_pointcloud",
        lambda stream, *, entity_path, pointmap, colors=None: calls.append(
            ("points", entity_path, *_timeline_state(stream))
        ),
    )
    monkeypatch.setattr(
        rerun_sink_module,
        "log_line_strip3d",
        lambda stream, *, entity_path, positions_xyz: calls.append(
            ("trajectory", entity_path, *_timeline_state(stream))
        ),
    )
    monkeypatch.setattr(rerun_sink_module, "log_clear", lambda *args, **kwargs: None)

    sink = RerunEventSink(grpc_url=None, target_path=tmp_path / "viewer.rrd")

    event = BackendNoticeReceived(
        event_id="1",
        run_id=f"run-{uuid.uuid4().hex}",
        ts_ns=1,
        stage_key=StageKey.SLAM,
        notice=KeyframeVisualizationReady(
            seq=5,
            timestamp_ns=1,
            source_seq=8,
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
        payloads={
            "preview": np.zeros((3, 4, 3), dtype=np.uint8),
            "rgb": np.zeros((3, 4, 3), dtype=np.uint8),
            "depth": np.ones((3, 4), dtype=np.float32),
            "pointmap": np.ones((3, 4, 3), dtype=np.float32),
        },
    )

    assert calls == [
        ("pose", "world/live/model", 8, None),
        ("rgb", rerun_sink_module.MODEL_RGB_2D_ENTITY_PATH, 8, None),
        ("pinhole", "world/live/model/camera/image", 8, None),
        ("rgb", "world/live/model/camera/image", 8, None),
        ("depth", "world/live/model/camera/image/depth", 8, None),
        ("rgb", "world/live/model/diag/preview", 8, None),
        ("points", "world/live/model/points", 8, None),
        ("pose", "world/keyframes/cameras/000003", 8, None),
        ("pose", "world/keyframes/points/000003", 8, None),
        ("pinhole", "world/keyframes/cameras/000003/image", 8, None),
        ("rgb", "world/keyframes/cameras/000003/image", 8, None),
        ("depth", "world/keyframes/cameras/000003/image/depth", 8, None),
        ("rgb", "world/keyframes/cameras/000003/diag/preview", 8, None),
        ("points", "world/keyframes/points/000003/points", 8, None),
    ]
    assert transform_axis_lengths["world/live/model"] == 0.0
    assert transform_axis_lengths["world/keyframes/cameras/000003"] == 0.0
    assert transform_axis_lengths["world/keyframes/points/000003"] == 0.0


def test_rerun_sink_logs_pointmaps_under_shared_model_and_keyframe_transforms(tmp_path: Path, monkeypatch) -> None:
    calls: list[tuple[str, str, int | None, int | None]] = []
    captured_transforms: dict[str, FrameTransform] = {}
    captured_pointmaps: dict[str, np.ndarray] = {}

    monkeypatch.setattr(rerun_sink_module, "create_recording_stream", lambda **_: _FakeRecordingStream())
    monkeypatch.setattr(rerun_sink_module, "attach_recording_sinks", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        rerun_sink_module,
        "log_transform",
        lambda stream, *, entity_path, transform, axis_length=None: (
            calls.append(("pose", entity_path, *_timeline_state(stream))),
            captured_transforms.__setitem__(entity_path, transform),
        ),
    )
    monkeypatch.setattr(
        rerun_sink_module,
        "log_pointcloud",
        lambda stream, *, entity_path, pointmap, colors=None: (
            calls.append(("points", entity_path, *_timeline_state(stream))),
            captured_pointmaps.__setitem__(entity_path, np.asarray(pointmap)),
        ),
    )
    monkeypatch.setattr(rerun_sink_module, "log_line_strip3d", lambda *args, **kwargs: None)
    monkeypatch.setattr(rerun_sink_module, "log_clear", lambda *args, **kwargs: None)

    sink = RerunEventSink(grpc_url=None, target_path=tmp_path / "viewer.rrd")

    event = BackendNoticeReceived(
        event_id="1",
        run_id=f"run-{uuid.uuid4().hex}",
        ts_ns=1,
        stage_key=StageKey.SLAM,
        notice=KeyframeVisualizationReady(
            seq=1,
            timestamp_ns=1,
            source_seq=4,
            source_timestamp_ns=1,
            keyframe_index=0,
            pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=2.0, tz=1.0),
            pointmap=ArrayHandle(handle_id="pointmap", shape=(1, 1, 3), dtype="float32"),
        ),
    )

    sink.observe(
        event,
        payloads={"pointmap": np.array([[[0.5, 0.0, 2.0]]], dtype=np.float32)},
    )

    assert calls == [
        ("pose", "world/live/model", 4, None),
        ("points", "world/live/model/points", 4, None),
        ("pose", "world/keyframes/cameras/000000", 4, None),
        ("pose", "world/keyframes/points/000000", 4, None),
        ("points", "world/keyframes/points/000000/points", 4, None),
    ]

    live_world_points = transform_points_world_camera(
        captured_pointmaps["world/live/model/points"].reshape(-1, 3),
        captured_transforms["world/live/model"],
    )
    keyframe_world_points = transform_points_world_camera(
        captured_pointmaps["world/keyframes/points/000000/points"].reshape(-1, 3),
        captured_transforms["world/keyframes/points/000000"],
    )

    np.testing.assert_allclose(live_world_points[0], np.array([1.5, 2.0, 3.0]))
    np.testing.assert_allclose(keyframe_world_points[0], np.array([1.5, 2.0, 3.0]))


def test_rerun_sink_logs_source_rgb_and_tracking_pose(tmp_path: Path, monkeypatch) -> None:
    calls: list[tuple[str, str, int | None, int | None]] = []
    tracking_axis_lengths: dict[str, float | None] = {}

    monkeypatch.setattr(rerun_sink_module, "create_recording_stream", lambda **_: _FakeRecordingStream())
    monkeypatch.setattr(rerun_sink_module, "attach_recording_sinks", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        rerun_sink_module,
        "log_rgb_image",
        lambda stream, *, entity_path, image_rgb: calls.append(("rgb", entity_path, *_timeline_state(stream))),
    )
    monkeypatch.setattr(
        rerun_sink_module,
        "log_transform",
        lambda stream, *, entity_path, transform, axis_length=None: (
            calls.append(("pose", entity_path, *_timeline_state(stream))),
            tracking_axis_lengths.__setitem__(entity_path, axis_length),
        ),
    )
    monkeypatch.setattr(
        rerun_sink_module,
        "log_line_strip3d",
        lambda stream, *, entity_path, positions_xyz: calls.append(
            ("trajectory", entity_path, *_timeline_state(stream))
        ),
    )
    monkeypatch.setattr(rerun_sink_module, "log_clear", lambda *args, **kwargs: None)

    sink = RerunEventSink(grpc_url=None, target_path=tmp_path / "viewer.rrd")

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
            source_seq=7,
            pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
        ),
    )

    sink.observe(packet_event, payloads={"frame": np.zeros((2, 2, 3), dtype=np.uint8)})
    sink.observe(pose_event, payloads={})

    assert calls == [
        ("rgb", "world/live/source/rgb", 1, None),
        ("pose", "world/live/tracking/camera", 7, None),
        ("trajectory", "world/trajectory/tracking", 7, None),
    ]
    assert tracking_axis_lengths["world/live/tracking/camera"] == 0.0


def test_rerun_sink_keeps_source_rgb_separate_from_model_raster_payloads(tmp_path: Path, monkeypatch) -> None:
    calls: list[tuple[str, str, tuple[int, ...], int | None, int | None]] = []

    monkeypatch.setattr(rerun_sink_module, "create_recording_stream", lambda **_: _FakeRecordingStream())
    monkeypatch.setattr(rerun_sink_module, "attach_recording_sinks", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        rerun_sink_module,
        "log_rgb_image",
        lambda stream, *, entity_path, image_rgb: calls.append(
            ("rgb", entity_path, tuple(np.asarray(image_rgb).shape), *_timeline_state(stream))
        ),
    )
    monkeypatch.setattr(
        rerun_sink_module,
        "log_pinhole",
        lambda stream, *, entity_path, intrinsics: calls.append(
            ("pinhole", entity_path, (intrinsics.height_px, intrinsics.width_px), *_timeline_state(stream))
        ),
    )
    monkeypatch.setattr(
        rerun_sink_module,
        "log_depth_image",
        lambda stream, *, entity_path, depth_m: calls.append(
            ("depth", entity_path, tuple(np.asarray(depth_m).shape), *_timeline_state(stream))
        ),
    )
    monkeypatch.setattr(rerun_sink_module, "log_transform", lambda *args, **kwargs: None)
    monkeypatch.setattr(rerun_sink_module, "log_pointcloud", lambda *args, **kwargs: None)
    monkeypatch.setattr(rerun_sink_module, "log_line_strip3d", lambda *args, **kwargs: None)
    monkeypatch.setattr(rerun_sink_module, "log_clear", lambda *args, **kwargs: None)

    sink = RerunEventSink(grpc_url=None, target_path=tmp_path / "viewer.rrd")
    sink.observe(
        PacketObserved(
            event_id="packet",
            run_id=f"run-{uuid.uuid4().hex}",
            ts_ns=1,
            packet=FramePacketSummary(seq=1, timestamp_ns=1, provenance=FramePacketProvenance(source_id="fake")),
            frame=ArrayHandle(handle_id="source-frame", shape=(11, 13, 3), dtype="uint8"),
            received_frames=1,
            measured_fps=30.0,
        ),
        payloads={"source-frame": np.zeros((11, 13, 3), dtype=np.uint8)},
    )
    sink.observe(
        BackendNoticeReceived(
            event_id="notice",
            run_id=f"run-{uuid.uuid4().hex}",
            ts_ns=2,
            stage_key=StageKey.SLAM,
            notice=KeyframeVisualizationReady(
                seq=2,
                timestamp_ns=2,
                source_seq=1,
                source_timestamp_ns=1,
                keyframe_index=0,
                pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
                image=ArrayHandle(handle_id="model-rgb", shape=(5, 7, 3), dtype="uint8"),
                depth=ArrayHandle(handle_id="model-depth", shape=(5, 7), dtype="float32"),
                preview=PreviewHandle(handle_id="preview", width=7, height=5, channels=3, dtype="uint8"),
                camera_intrinsics=CameraIntrinsics(fx=3.0, fy=4.0, cx=1.5, cy=2.0, width_px=7, height_px=5),
            ),
        ),
        payloads={
            "model-rgb": np.zeros((5, 7, 3), dtype=np.uint8),
            "model-depth": np.ones((5, 7), dtype=np.float32),
            "preview": np.zeros((5, 7, 3), dtype=np.uint8),
        },
    )

    assert calls == [
        ("rgb", "world/live/source/rgb", (11, 13, 3), 1, None),
        ("rgb", rerun_sink_module.MODEL_RGB_2D_ENTITY_PATH, (5, 7, 3), 1, None),
        ("pinhole", "world/live/model/camera/image", (5, 7), 1, None),
        ("rgb", "world/live/model/camera/image", (5, 7, 3), 1, None),
        ("depth", "world/live/model/camera/image/depth", (5, 7), 1, None),
        ("rgb", "world/live/model/diag/preview", (5, 7, 3), 1, None),
        ("pinhole", "world/keyframes/cameras/000000/image", (5, 7), 1, None),
        ("rgb", "world/keyframes/cameras/000000/image", (5, 7, 3), 1, None),
        ("depth", "world/keyframes/cameras/000000/image/depth", (5, 7), 1, None),
        ("rgb", "world/keyframes/cameras/000000/diag/preview", (5, 7, 3), 1, None),
    ]


def test_rerun_sink_does_not_log_root_world_coordinates(tmp_path: Path, monkeypatch) -> None:
    paths: list[tuple[str, int | None, int | None]] = []

    monkeypatch.setattr(rerun_sink_module, "create_recording_stream", lambda **_: _FakeRecordingStream())
    monkeypatch.setattr(rerun_sink_module, "attach_recording_sinks", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        rerun_sink_module,
        "log_transform",
        lambda stream, *, entity_path, transform, axis_length=None: paths.append(
            (entity_path, *_timeline_state(stream))
        ),
    )
    monkeypatch.setattr(rerun_sink_module, "log_line_strip3d", lambda *args, **kwargs: None)
    monkeypatch.setattr(rerun_sink_module, "log_clear", lambda *args, **kwargs: None)

    sink = RerunEventSink(grpc_url=None, target_path=tmp_path / "viewer.rrd")
    sink.observe(
        BackendNoticeReceived(
            event_id="1",
            run_id=f"run-{uuid.uuid4().hex}",
            ts_ns=1,
            stage_key=StageKey.SLAM,
            notice=PoseEstimated(
                seq=1,
                timestamp_ns=1,
                source_seq=2,
                pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
            ),
        ),
        payloads={},
    )

    assert paths == [("world/live/tracking/camera", 2, None)]
    assert "world" not in [path for path, _, _ in paths]


def test_rerun_sink_actor_forwards_materialized_rerun_bindings_without_ray_get(tmp_path: Path, monkeypatch) -> None:
    observed: dict[str, object] = {}

    class FakeLocalSink:
        def __init__(self, **kwargs: object) -> None:
            observed["init"] = kwargs

        def observe(self, event, *, payloads) -> None:
            observed["event"] = event
            observed["payload"] = payloads["frame"]

        def close(self) -> None:
            observed["closed"] = True

    monkeypatch.setattr(rerun_sink_module, "RerunEventSink", FakeLocalSink)
    monkeypatch.setattr(
        rerun_sink_module.ray,
        "get",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("sink actor must not call ray.get")),
    )

    actor_cls = RerunSinkActor.__ray_metadata__.modified_class
    actor = actor_cls(
        grpc_url=None,
        target_path=tmp_path / "viewer.rrd",
        recording_id="demo",
        frusta_history_window_streaming=5,
        show_tracking_trajectory=False,
    )
    actor.observe_event(
        event=PacketObserved(
            event_id="1",
            run_id="demo",
            ts_ns=1,
            packet=FramePacketSummary(seq=1, timestamp_ns=1, provenance=FramePacketProvenance()),
            frame=ArrayHandle(handle_id="frame", shape=(2, 2, 3), dtype="uint8"),
        ),
        rerun_bindings=[("frame", np.ones((2, 2, 3), dtype=np.uint8))],
    )
    actor.close()

    assert observed["init"]["recording_id"] == "demo"
    assert observed["init"]["frusta_history_window_streaming"] == 5
    assert observed["init"]["show_tracking_trajectory"] is False
    assert np.array_equal(observed["payload"], np.ones((2, 2, 3), dtype=np.uint8))
    assert observed["closed"] is True


def test_rerun_sink_keeps_camera_branch_when_keyframe_pointmap_is_missing(tmp_path: Path, monkeypatch) -> None:
    calls: list[tuple[str, str, int | None, int | None]] = []

    monkeypatch.setattr(rerun_sink_module, "create_recording_stream", lambda **_: _FakeRecordingStream())
    monkeypatch.setattr(rerun_sink_module, "attach_recording_sinks", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        rerun_sink_module,
        "log_pinhole",
        lambda stream, *, entity_path, intrinsics: calls.append(("pinhole", entity_path, *_timeline_state(stream))),
    )
    monkeypatch.setattr(
        rerun_sink_module,
        "log_rgb_image",
        lambda stream, *, entity_path, image_rgb: calls.append(("rgb", entity_path, *_timeline_state(stream))),
    )
    monkeypatch.setattr(
        rerun_sink_module,
        "log_transform",
        lambda stream, *, entity_path, transform, axis_length=None: calls.append(
            ("pose", entity_path, *_timeline_state(stream))
        ),
    )
    monkeypatch.setattr(rerun_sink_module, "log_line_strip3d", lambda *args, **kwargs: None)
    monkeypatch.setattr(rerun_sink_module, "log_clear", lambda *args, **kwargs: None)

    sink = RerunEventSink(grpc_url=None, target_path=tmp_path / "viewer.rrd")
    sink.observe(
        BackendNoticeReceived(
            event_id="1",
            run_id=f"run-{uuid.uuid4().hex}",
            ts_ns=1,
            stage_key=StageKey.SLAM,
            notice=KeyframeVisualizationReady(
                seq=5,
                timestamp_ns=1,
                source_seq=8,
                source_timestamp_ns=1,
                keyframe_index=3,
                pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
                image=ArrayHandle(handle_id="rgb", shape=(3, 4, 3), dtype="uint8"),
                camera_intrinsics=CameraIntrinsics(fx=2.0, fy=2.0, cx=1.0, cy=1.0, width_px=4, height_px=3),
            ),
        ),
        payloads={"rgb": np.zeros((3, 4, 3), dtype=np.uint8)},
    )

    assert calls == [
        ("pose", "world/live/model", 8, None),
        ("rgb", rerun_sink_module.MODEL_RGB_2D_ENTITY_PATH, 8, None),
        ("pinhole", "world/live/model/camera/image", 8, None),
        ("rgb", "world/live/model/camera/image", 8, None),
        ("pose", "world/keyframes/cameras/000003", 8, None),
        ("pose", "world/keyframes/points/000003", 8, None),
        ("pinhole", "world/keyframes/cameras/000003/image", 8, None),
        ("rgb", "world/keyframes/cameras/000003/image", 8, None),
    ]


def test_rerun_sink_clears_stale_keyframe_camera_subtrees_without_clearing_points(tmp_path: Path, monkeypatch) -> None:
    clears: list[str] = []

    monkeypatch.setattr(rerun_sink_module, "create_recording_stream", lambda **_: _FakeRecordingStream())
    monkeypatch.setattr(rerun_sink_module, "attach_recording_sinks", lambda *args, **kwargs: None)
    monkeypatch.setattr(rerun_sink_module, "log_transform", lambda *args, **kwargs: None)
    monkeypatch.setattr(rerun_sink_module, "log_pointcloud", lambda *args, **kwargs: None)
    monkeypatch.setattr(rerun_sink_module, "log_pinhole", lambda *args, **kwargs: None)
    monkeypatch.setattr(rerun_sink_module, "log_rgb_image", lambda *args, **kwargs: None)
    monkeypatch.setattr(rerun_sink_module, "log_depth_image", lambda *args, **kwargs: None)
    monkeypatch.setattr(rerun_sink_module, "log_line_strip3d", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        rerun_sink_module,
        "log_clear",
        lambda stream, *, entity_path, recursive: clears.append(f"{entity_path}:{recursive}"),
    )

    sink = RerunEventSink(
        grpc_url=None,
        target_path=tmp_path / "viewer.rrd",
        frusta_history_window_streaming=2,
    )

    for keyframe_index in range(3):
        sink.observe(
            BackendNoticeReceived(
                event_id=str(keyframe_index),
                run_id=f"run-{uuid.uuid4().hex}",
                ts_ns=keyframe_index,
                stage_key=StageKey.SLAM,
                notice=KeyframeVisualizationReady(
                    seq=keyframe_index,
                    timestamp_ns=keyframe_index,
                    source_seq=keyframe_index,
                    source_timestamp_ns=keyframe_index,
                    keyframe_index=keyframe_index,
                    pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
                ),
            ),
            payloads={},
        )

    assert clears == ["world/keyframes/cameras/000000:True"]
