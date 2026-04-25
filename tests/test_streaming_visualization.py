"""Tests for repo-owned streaming Rerun sink behavior."""

from __future__ import annotations

import logging
import warnings
from pathlib import Path

import numpy as np
import rerun.dataframe as rdf

from prml_vslam.interfaces import CameraIntrinsics, FrameTransform
from prml_vslam.interfaces.alignment import GroundAlignmentMetadata
from prml_vslam.interfaces.artifacts import artifact_ref
from prml_vslam.methods.contracts import SlamUpdate
from prml_vslam.methods.stage.visualization import (
    COLORS_REF,
    DEPTH_REF,
    IMAGE_REF,
    POINTMAP_REF,
    PREVIEW_REF,
    ROLE_SOURCE_RGB,
    SlamVisualizationAdapter,
)
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.contracts import StageRuntimeUpdate, VisualizationIntent, VisualizationItem
from prml_vslam.pipeline.stages.base.handles import TransientPayloadRef
from prml_vslam.reconstruction.stage.visualization import (
    MESH_ARTIFACT,
    POINT_CLOUD_ARTIFACT,
    ROLE_RECONSTRUCTION_MESH,
    ROLE_RECONSTRUCTION_POINT_CLOUD,
)
from prml_vslam.sources.visualization import (
    METADATA_ARTIFACT as SOURCE_METADATA_ARTIFACT,
)
from prml_vslam.sources.visualization import (
    POINT_CLOUD_ARTIFACT as SOURCE_POINT_CLOUD_ARTIFACT,
)
from prml_vslam.sources.visualization import (
    ROLE_SOURCE_CAMERA_POSE,
    ROLE_SOURCE_CAMERA_RGB,
    ROLE_SOURCE_DEPTH,
    ROLE_SOURCE_PINHOLE,
    ROLE_SOURCE_POINTMAP,
    ROLE_SOURCE_REFERENCE_POINT_CLOUD,
    ROLE_SOURCE_REFERENCE_TRAJECTORY,
    TRAJECTORY_ARTIFACT,
)
from prml_vslam.utils.geometry import transform_points_world_camera, write_point_cloud_ply
from prml_vslam.visualization import rerun_sink as rerun_sink_module
from prml_vslam.visualization.rerun_sink import RerunEventSink, RerunSinkActor
from prml_vslam.visualization.validation import load_recording_summary


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


def _ground_alignment_update() -> StageRuntimeUpdate:
    return StageRuntimeUpdate(
        stage_key=StageKey.GRAVITY_ALIGNMENT,
        timestamp_ns=1,
        semantic_events=[_ground_alignment_metadata()],
    )


def _payload_ref(
    handle_id: str,
    *,
    payload_kind: str,
    shape: tuple[int, ...],
    dtype: str,
) -> TransientPayloadRef:
    return TransientPayloadRef(handle_id=handle_id, payload_kind=payload_kind, shape=shape, dtype=dtype)


def _slam_pose_update(
    *,
    source_seq: int,
    pose: FrameTransform,
) -> StageRuntimeUpdate:
    return StageRuntimeUpdate(
        stage_key=StageKey.SLAM,
        timestamp_ns=1,
        visualizations=SlamVisualizationAdapter().build_items(
            SlamUpdate(
                seq=source_seq,
                timestamp_ns=1,
                source_seq=source_seq,
                source_timestamp_ns=1,
                pose=pose,
            ),
            {},
        ),
    )


def _slam_keyframe_update(
    *,
    source_seq: int,
    keyframe_index: int,
    pose: FrameTransform,
    refs: dict[str, TransientPayloadRef],
    intrinsics: CameraIntrinsics | None = None,
) -> StageRuntimeUpdate:
    return StageRuntimeUpdate(
        stage_key=StageKey.SLAM,
        timestamp_ns=1,
        visualizations=SlamVisualizationAdapter().build_items(
            SlamUpdate(
                seq=source_seq,
                timestamp_ns=1,
                source_seq=source_seq,
                source_timestamp_ns=1,
                is_keyframe=True,
                keyframe_index=keyframe_index,
                pose=pose,
                camera_intrinsics=intrinsics,
            ),
            refs,
        ),
    )


def _source_rgb_update(*, frame_index: int, ref: TransientPayloadRef) -> StageRuntimeUpdate:
    return StageRuntimeUpdate(
        stage_key=StageKey.SOURCE,
        timestamp_ns=1,
        visualizations=[
            VisualizationItem(
                intent=VisualizationIntent.RGB_IMAGE,
                role=ROLE_SOURCE_RGB,
                payload_refs={IMAGE_REF: ref},
                frame_index=frame_index,
                space="source_raster",
            )
        ],
    )


def test_rerun_sink_is_noop_when_handles_are_unavailable(tmp_path: Path) -> None:
    sink = RerunEventSink(
        grpc_url=None,
        target_path=tmp_path / "viewer.rrd",
        log_diagnostic_preview=True,
        log_camera_image_rgb=True,
    )
    sink.observe_update(
        _slam_pose_update(
            source_seq=1,
            pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
        ),
        payloads={},
    )


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

    sink.observe_update(_ground_alignment_update(), payloads={})

    assert ground_calls == ["live"]

    sink.close()

    assert augment_calls == [(_ground_alignment_metadata(), viewer_path, "demo-run")]


def test_rerun_sink_close_stamps_ground_plane_overlay_as_static_in_exported_rrd(tmp_path: Path) -> None:
    viewer_path = tmp_path / "viewer.rrd"
    sink = RerunEventSink(grpc_url=None, target_path=viewer_path, recording_id="static-ground-plane")

    sink.observe_update(_ground_alignment_update(), payloads={})
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

    sink = RerunEventSink(
        grpc_url=None,
        target_path=tmp_path / "viewer.rrd",
        log_diagnostic_preview=True,
        log_camera_image_rgb=True,
    )

    sink.observe_update(
        _slam_keyframe_update(
            source_seq=8,
            keyframe_index=3,
            pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
            refs={
                IMAGE_REF: _payload_ref("rgb", payload_kind="image", shape=(3, 4, 3), dtype="uint8"),
                DEPTH_REF: _payload_ref("depth", payload_kind="depth", shape=(3, 4), dtype="float32"),
                PREVIEW_REF: _payload_ref("preview", payload_kind="image", shape=(3, 4, 3), dtype="uint8"),
                POINTMAP_REF: _payload_ref("pointmap", payload_kind="point_cloud", shape=(3, 4, 3), dtype="float32"),
            },
            intrinsics=CameraIntrinsics(fx=2.0, fy=2.0, cx=1.0, cy=1.0, width_px=4, height_px=3),
        ),
        payloads={
            "preview": np.zeros((3, 4, 3), dtype=np.uint8),
            "rgb": np.zeros((3, 4, 3), dtype=np.uint8),
            "depth": np.ones((3, 4), dtype=np.float32),
            "pointmap": np.ones((3, 4, 3), dtype=np.float32),
        },
    )

    assert calls == [
        ("pose", "world/live/tracking/camera", 8, None),
        ("trajectory", "world/slam/vista_slam_world/trajectory/raw", 8, None),
        ("pose", "world/live/model", 8, None),
        ("pose", "world/keyframes/cameras/000003", 8, None),
        ("pose", "world/keyframes/points/000003", 8, None),
        ("pinhole", "world/live/model/camera/image", 8, None),
        ("pinhole", "world/keyframes/cameras/000003/image", 8, None),
        ("rgb", rerun_sink_module.MODEL_RGB_2D_ENTITY_PATH, 8, None),
        ("rgb", "world/live/model/camera/image", 8, None),
        ("rgb", "world/keyframes/cameras/000003/image", 8, None),
        ("depth", "world/live/model/camera/image/depth", 8, None),
        ("depth", "world/keyframes/cameras/000003/image/depth", 8, None),
        ("rgb", "world/live/model/diag/preview", 8, None),
        ("rgb", "world/keyframes/cameras/000003/diag/preview", 8, None),
        ("points", "world/live/model/points", 8, None),
        ("points", "world/keyframes/points/000003/points", 8, None),
    ]
    assert transform_axis_lengths["world/live/tracking/camera"] == 0.0
    assert transform_axis_lengths["world/live/model"] == 0.0
    assert transform_axis_lengths["world/keyframes/cameras/000003"] == 0.0
    assert transform_axis_lengths["world/keyframes/points/000003"] == 0.0


def test_rerun_sink_logs_stage_runtime_update_visualizations(tmp_path: Path, monkeypatch) -> None:
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

    pose = FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0)
    refs = {
        IMAGE_REF: _payload_ref("rgb", payload_kind="image", shape=(3, 4, 3), dtype="uint8"),
        DEPTH_REF: _payload_ref("depth", payload_kind="depth", shape=(3, 4), dtype="float32"),
        PREVIEW_REF: _payload_ref("preview", payload_kind="image", shape=(3, 4, 3), dtype="uint8"),
        POINTMAP_REF: _payload_ref("pointmap", payload_kind="point_cloud", shape=(3, 4, 3), dtype="float32"),
    }
    update = StageRuntimeUpdate(
        stage_key=StageKey.SLAM,
        timestamp_ns=1,
        semantic_events=[],
        visualizations=SlamVisualizationAdapter().build_items(
            SlamUpdate(
                seq=5,
                timestamp_ns=1,
                source_seq=8,
                source_timestamp_ns=1,
                is_keyframe=True,
                keyframe_index=3,
                pose=pose,
                camera_intrinsics=CameraIntrinsics(fx=2.0, fy=2.0, cx=1.0, cy=1.0, width_px=4, height_px=3),
            ),
            refs,
        ),
    )

    sink = RerunEventSink(
        grpc_url=None,
        target_path=tmp_path / "viewer.rrd",
        log_source_rgb=True,
        log_diagnostic_preview=True,
        log_camera_image_rgb=True,
    )
    sink.observe_update(
        update,
        payloads={
            "preview": np.zeros((3, 4, 3), dtype=np.uint8),
            "rgb": np.zeros((3, 4, 3), dtype=np.uint8),
            "depth": np.ones((3, 4), dtype=np.float32),
            "pointmap": np.ones((3, 4, 3), dtype=np.float32),
        },
    )

    assert calls == [
        ("pose", "world/live/tracking/camera", 8, None),
        ("trajectory", "world/slam/vista_slam_world/trajectory/raw", 8, None),
        ("pose", "world/live/model", 8, None),
        ("pose", "world/keyframes/cameras/000003", 8, None),
        ("pose", "world/keyframes/points/000003", 8, None),
        ("pinhole", "world/live/model/camera/image", 8, None),
        ("pinhole", "world/keyframes/cameras/000003/image", 8, None),
        ("rgb", rerun_sink_module.MODEL_RGB_2D_ENTITY_PATH, 8, None),
        ("rgb", "world/live/model/camera/image", 8, None),
        ("rgb", "world/keyframes/cameras/000003/image", 8, None),
        ("depth", "world/live/model/camera/image/depth", 8, None),
        ("depth", "world/keyframes/cameras/000003/image/depth", 8, None),
        ("rgb", "world/live/model/diag/preview", 8, None),
        ("rgb", "world/keyframes/cameras/000003/diag/preview", 8, None),
        ("points", "world/live/model/points", 8, None),
        ("points", "world/keyframes/points/000003/points", 8, None),
    ]
    assert transform_axis_lengths["world/live/tracking/camera"] == 0.0
    assert transform_axis_lengths["world/live/model"] == 0.0
    assert transform_axis_lengths["world/keyframes/cameras/000003"] == 0.0
    assert transform_axis_lengths["world/keyframes/points/000003"] == 0.0


def test_rerun_sink_update_skips_missing_payload_refs(tmp_path: Path, monkeypatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr(rerun_sink_module, "create_recording_stream", lambda **_: _FakeRecordingStream())
    monkeypatch.setattr(rerun_sink_module, "attach_recording_sinks", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        rerun_sink_module,
        "log_rgb_image",
        lambda stream, *, entity_path, image_rgb: calls.append(entity_path),
    )

    sink = RerunEventSink(
        grpc_url=None,
        target_path=tmp_path / "viewer.rrd",
        log_source_rgb=True,
        log_diagnostic_preview=True,
        log_camera_image_rgb=True,
    )
    sink.observe_update(
        StageRuntimeUpdate(
            stage_key=StageKey.SLAM,
            timestamp_ns=1,
            visualizations=[
                VisualizationItem(
                    intent=VisualizationIntent.RGB_IMAGE,
                    role="source_rgb",
                    payload_refs={
                        "image": _payload_ref(
                            "missing",
                            payload_kind="image",
                            shape=(2, 2, 3),
                            dtype="uint8",
                        )
                    },
                    frame_index=1,
                )
            ],
        ),
        payloads={},
    )

    assert calls == []


def test_rerun_sink_logs_reconstruction_artifacts(tmp_path: Path, monkeypatch) -> None:
    calls: list[tuple[str, str, Path]] = []
    streams: list[_FakeRecordingStream] = []
    cloud = tmp_path / "reference_cloud.ply"
    mesh = tmp_path / "reference_mesh.ply"

    def _create_stream(**_kwargs) -> _FakeRecordingStream:
        stream = _FakeRecordingStream()
        streams.append(stream)
        return stream

    monkeypatch.setattr(rerun_sink_module, "create_recording_stream", _create_stream)
    monkeypatch.setattr(rerun_sink_module, "attach_recording_sinks", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        rerun_sink_module,
        "log_pointcloud_ply",
        lambda stream, *, entity_path, path: calls.append(("points", entity_path, path)),
    )
    monkeypatch.setattr(
        rerun_sink_module,
        "log_mesh_ply",
        lambda stream, *, entity_path, path: calls.append(("mesh", entity_path, path)),
    )

    sink = RerunEventSink(grpc_url=None, target_path=tmp_path / "viewer.rrd")
    sink.observe_update(
        StageRuntimeUpdate(
            stage_key=StageKey.RECONSTRUCTION,
            timestamp_ns=1,
            visualizations=[
                VisualizationItem(
                    intent=VisualizationIntent.POINT_CLOUD,
                    role=ROLE_RECONSTRUCTION_POINT_CLOUD,
                    artifact_refs={POINT_CLOUD_ARTIFACT: artifact_ref(cloud, kind="ply")},
                    metadata={"reconstruction_id": "reference"},
                ),
                VisualizationItem(
                    intent=VisualizationIntent.MESH,
                    role=ROLE_RECONSTRUCTION_MESH,
                    artifact_refs={MESH_ARTIFACT: artifact_ref(mesh, kind="ply")},
                    metadata={"reconstruction_id": "reference"},
                ),
            ],
        ),
    )

    assert calls == [
        ("points", "world/reconstruction/reference/point_cloud", cloud),
        ("mesh", "world/reconstruction/reference/mesh", mesh),
    ]
    assert streams[0].timelines == {}


def test_rerun_sink_logs_source_reference_artifacts(tmp_path: Path, monkeypatch) -> None:
    calls: list[tuple[str, str, Path | tuple[tuple[float, float, float], ...]]] = []
    trajectory = tmp_path / "ground_truth.tum"
    trajectory.write_text("0.0 1 2 3 0 0 0 1\n1.0 2 3 4 0 0 0 1\n", encoding="utf-8")
    cloud = tmp_path / "reference_cloud.ply"
    metadata = tmp_path / "reference_cloud.metadata.json"
    metadata.write_text('{"point_count": 2, "skipped_out_of_range_payloads": 1}', encoding="utf-8")

    monkeypatch.setattr(rerun_sink_module, "create_recording_stream", lambda **_: _FakeRecordingStream())
    monkeypatch.setattr(rerun_sink_module, "attach_recording_sinks", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        rerun_sink_module,
        "log_line_strip3d",
        lambda stream, *, entity_path, positions_xyz, static=False: calls.append(
            ("trajectory", entity_path, tuple(map(tuple, np.asarray(positions_xyz, dtype=float))))
        ),
    )
    monkeypatch.setattr(
        rerun_sink_module,
        "log_pointcloud_ply",
        lambda stream, *, entity_path, path: calls.append(("points", entity_path, path)),
    )

    sink = RerunEventSink(grpc_url=None, target_path=tmp_path / "viewer.rrd")
    sink.observe_update(
        StageRuntimeUpdate(
            stage_key=StageKey.SOURCE,
            timestamp_ns=1,
            visualizations=[
                VisualizationItem(
                    intent=VisualizationIntent.TRAJECTORY,
                    role=ROLE_SOURCE_REFERENCE_TRAJECTORY,
                    artifact_refs={TRAJECTORY_ARTIFACT: artifact_ref(trajectory, kind="tum")},
                    metadata={
                        "reference_source": "ground_truth",
                        "target_frame": "advio_gt_world",
                        "coordinate_status": "aligned",
                    },
                ),
                VisualizationItem(
                    intent=VisualizationIntent.POINT_CLOUD,
                    role=ROLE_SOURCE_REFERENCE_POINT_CLOUD,
                    artifact_refs={
                        SOURCE_POINT_CLOUD_ARTIFACT: artifact_ref(cloud, kind="ply"),
                        SOURCE_METADATA_ARTIFACT: artifact_ref(metadata, kind="json"),
                    },
                    metadata={
                        "reference_source": "tango_raw",
                        "coordinate_status": "aligned",
                        "target_frame": "advio_gt_world",
                    },
                ),
                VisualizationItem(
                    intent=VisualizationIntent.POINT_CLOUD,
                    role=ROLE_SOURCE_REFERENCE_POINT_CLOUD,
                    artifact_refs={
                        SOURCE_POINT_CLOUD_ARTIFACT: artifact_ref(cloud, kind="ply"),
                        SOURCE_METADATA_ARTIFACT: artifact_ref(metadata, kind="json"),
                    },
                    metadata={
                        "reference_source": "tango_raw",
                        "coordinate_status": "source_native",
                        "target_frame": "advio_tango_raw_world",
                    },
                ),
            ],
        )
    )

    assert calls == [
        (
            "trajectory",
            "world/reference/advio_gt_world/ground_truth/aligned/trajectory",
            ((1.0, 2.0, 3.0), (2.0, 3.0, 4.0)),
        ),
        ("points", "world/reference/advio_gt_world/tango_raw/aligned/points_2_skipped_1/point_cloud", cloud),
        (
            "points",
            "world/reference/advio_tango_raw_world/tango_raw/source_native/points_2_skipped_1/point_cloud",
            cloud,
        ),
    ]


def test_rerun_reference_validation_sees_static_trajectories_and_cloud_counts(tmp_path: Path) -> None:
    trajectory = tmp_path / "ground_truth.tum"
    trajectory.write_text("0.0 1 2 3 0 0 0 1\n1.0 2 3 4 0 0 0 1\n", encoding="utf-8")
    cloud = write_point_cloud_ply(tmp_path / "reference_cloud.ply", np.asarray([[1, 2, 3], [4, 5, 6]], dtype=float))
    metadata = tmp_path / "reference_cloud.metadata.json"
    metadata.write_text('{"point_count": 2, "skipped_out_of_range_payloads": 0}', encoding="utf-8")
    viewer_path = tmp_path / "viewer.rrd"

    sink = RerunEventSink(grpc_url=None, target_path=viewer_path, recording_id="reference-validation")
    sink.observe_update(
        StageRuntimeUpdate(
            stage_key=StageKey.SOURCE,
            timestamp_ns=1,
            visualizations=[
                VisualizationItem(
                    intent=VisualizationIntent.TRAJECTORY,
                    role=ROLE_SOURCE_REFERENCE_TRAJECTORY,
                    artifact_refs={TRAJECTORY_ARTIFACT: artifact_ref(trajectory, kind="tum")},
                    metadata={
                        "reference_source": "ground_truth",
                        "target_frame": "advio_gt_world",
                        "coordinate_status": "aligned",
                    },
                ),
                VisualizationItem(
                    intent=VisualizationIntent.POINT_CLOUD,
                    role=ROLE_SOURCE_REFERENCE_POINT_CLOUD,
                    artifact_refs={
                        SOURCE_POINT_CLOUD_ARTIFACT: artifact_ref(cloud, kind="ply"),
                        SOURCE_METADATA_ARTIFACT: artifact_ref(metadata, kind="json"),
                    },
                    metadata={
                        "reference_source": "tango_raw",
                        "coordinate_status": "aligned",
                        "target_frame": "advio_gt_world",
                    },
                ),
            ],
        )
    )
    sink.close()

    summary = load_recording_summary(viewer_path)

    assert summary.reference_trajectory_entities == ["/world/reference/advio_gt_world/ground_truth/aligned/trajectory"]
    assert [(snapshot.entity_path, snapshot.point_count) for snapshot in summary.reference_point_clouds] == [
        ("/world/reference/advio_gt_world/tango_raw/aligned/points_2_skipped_0/point_cloud", 2)
    ]


def test_rerun_sink_logs_source_posed_camera_geometry(tmp_path: Path, monkeypatch) -> None:
    calls: list[tuple[str, str, int | None, int | None]] = []

    monkeypatch.setattr(rerun_sink_module, "create_recording_stream", lambda **_: _FakeRecordingStream())
    monkeypatch.setattr(rerun_sink_module, "attach_recording_sinks", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        rerun_sink_module,
        "log_transform",
        lambda stream, *, entity_path, transform, axis_length=None: calls.append(
            ("pose", entity_path, *_timeline_state(stream))
        ),
    )
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
        "log_pointcloud",
        lambda stream, *, entity_path, pointmap, colors=None: calls.append(
            ("points", entity_path, *_timeline_state(stream))
        ),
    )

    pose = FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=2.0, tz=3.0)
    intrinsics = CameraIntrinsics(fx=2.0, fy=2.0, cx=1.0, cy=1.0, width_px=4, height_px=3)
    sink = RerunEventSink(grpc_url=None, target_path=tmp_path / "viewer.rrd", log_source_rgb=True)
    sink.observe_update(
        StageRuntimeUpdate(
            stage_key=StageKey.SOURCE,
            timestamp_ns=1,
            visualizations=[
                VisualizationItem(
                    intent=VisualizationIntent.POSE_TRANSFORM,
                    role=ROLE_SOURCE_CAMERA_POSE,
                    pose=pose,
                    frame_index=2,
                ),
                VisualizationItem(
                    intent=VisualizationIntent.PINHOLE_CAMERA,
                    role=ROLE_SOURCE_PINHOLE,
                    payload_refs={
                        IMAGE_REF: _payload_ref("rgb", payload_kind="image", shape=(3, 4, 3), dtype="uint8"),
                        DEPTH_REF: _payload_ref("depth", payload_kind="depth", shape=(3, 4), dtype="float32"),
                    },
                    intrinsics=intrinsics,
                    frame_index=2,
                ),
                VisualizationItem(
                    intent=VisualizationIntent.RGB_IMAGE,
                    role=ROLE_SOURCE_CAMERA_RGB,
                    payload_refs={IMAGE_REF: _payload_ref("rgb", payload_kind="image", shape=(3, 4, 3), dtype="uint8")},
                    frame_index=2,
                ),
                VisualizationItem(
                    intent=VisualizationIntent.DEPTH_IMAGE,
                    role=ROLE_SOURCE_DEPTH,
                    payload_refs={
                        DEPTH_REF: _payload_ref("depth", payload_kind="depth", shape=(3, 4), dtype="float32")
                    },
                    frame_index=2,
                ),
                VisualizationItem(
                    intent=VisualizationIntent.POINT_CLOUD,
                    role=ROLE_SOURCE_POINTMAP,
                    payload_refs={
                        POINTMAP_REF: _payload_ref(
                            "pointmap", payload_kind="point_cloud", shape=(3, 4, 3), dtype="float32"
                        ),
                        COLORS_REF: _payload_ref("rgb", payload_kind="image", shape=(3, 4, 3), dtype="uint8"),
                    },
                    frame_index=2,
                ),
            ],
        ),
        payloads={
            "rgb": np.zeros((3, 4, 3), dtype=np.uint8),
            "depth": np.ones((3, 4), dtype=np.float32),
            "pointmap": np.ones((3, 4, 3), dtype=np.float32),
        },
    )

    assert calls == [
        ("pose", "world/live/source/camera", 2, None),
        ("pinhole", "world/live/source/camera/image", 2, None),
        ("rgb", "world/live/source/camera/image", 2, None),
        ("depth", "world/live/source/camera/image/depth", 2, None),
        ("points", "world/live/source/camera/points", 2, None),
    ]


def test_rerun_policy_skips_invalid_reconstruction_artifact(caplog, monkeypatch) -> None:
    stream = _FakeRecordingStream()
    policy = rerun_sink_module.RerunLoggingPolicy(
        log_pinhole=lambda *args, **kwargs: None,
        log_pointcloud=lambda *args, **kwargs: None,
        log_pointcloud_ply=lambda *args, **kwargs: (_ for _ in ()).throw(FileNotFoundError("missing")),
        log_mesh_ply=lambda *args, **kwargs: None,
        log_line_strip3d=lambda *args, **kwargs: None,
        log_clear=lambda *args, **kwargs: None,
        log_depth_image=lambda *args, **kwargs: None,
        log_ground_plane_patch=lambda *args, **kwargs: None,
        log_rgb_image=lambda *args, **kwargs: None,
        log_transform=lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(logging.getLogger("prml_vslam"), "propagate", True)

    with caplog.at_level(logging.WARNING):
        policy.observe_update(
            stream,
            StageRuntimeUpdate(
                stage_key=StageKey.RECONSTRUCTION,
                timestamp_ns=1,
                visualizations=[
                    VisualizationItem(
                        intent=VisualizationIntent.POINT_CLOUD,
                        role=ROLE_RECONSTRUCTION_POINT_CLOUD,
                        artifact_refs={POINT_CLOUD_ARTIFACT: artifact_ref(Path("missing.ply"), kind="ply")},
                    )
                ],
            ),
        )

    assert "Skipping reconstruction point cloud artifact" in caplog.text


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

    sink = RerunEventSink(grpc_url=None, target_path=tmp_path / "viewer.rrd", log_camera_image_rgb=True)
    sink.observe_update(
        _slam_keyframe_update(
            source_seq=4,
            keyframe_index=0,
            pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=2.0, tz=1.0),
            refs={POINTMAP_REF: _payload_ref("pointmap", payload_kind="point_cloud", shape=(1, 1, 3), dtype="float32")},
        ),
        payloads={"pointmap": np.array([[[0.5, 0.0, 2.0]]], dtype=np.float32)},
    )

    assert calls == [
        ("pose", "world/live/tracking/camera", 4, None),
        ("pose", "world/live/model", 4, None),
        ("pose", "world/keyframes/cameras/000000", 4, None),
        ("pose", "world/keyframes/points/000000", 4, None),
        ("points", "world/live/model/points", 4, None),
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

    sink = RerunEventSink(grpc_url=None, target_path=tmp_path / "viewer.rrd", log_source_rgb=True)

    sink.observe_update(
        _source_rgb_update(
            frame_index=1,
            ref=_payload_ref("frame", payload_kind="image", shape=(2, 2, 3), dtype="uint8"),
        ),
        payloads={"frame": np.zeros((2, 2, 3), dtype=np.uint8)},
    )
    sink.observe_update(
        _slam_pose_update(
            source_seq=7,
            pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
        ),
        payloads={},
    )

    assert calls == [
        ("rgb", "world/live/source/rgb", 1, None),
        ("pose", "world/live/tracking/camera", 7, None),
        ("trajectory", "world/slam/vista_slam_world/trajectory/raw", 7, None),
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

    sink = RerunEventSink(
        grpc_url=None,
        target_path=tmp_path / "viewer.rrd",
        log_source_rgb=True,
        log_diagnostic_preview=True,
        log_camera_image_rgb=True,
    )
    sink.observe_update(
        _source_rgb_update(
            frame_index=1,
            ref=_payload_ref("source-frame", payload_kind="image", shape=(11, 13, 3), dtype="uint8"),
        ),
        payloads={"source-frame": np.zeros((11, 13, 3), dtype=np.uint8)},
    )
    sink.observe_update(
        _slam_keyframe_update(
            source_seq=1,
            keyframe_index=0,
            pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
            refs={
                IMAGE_REF: _payload_ref("model-rgb", payload_kind="image", shape=(5, 7, 3), dtype="uint8"),
                DEPTH_REF: _payload_ref("model-depth", payload_kind="depth", shape=(5, 7), dtype="float32"),
                PREVIEW_REF: _payload_ref("preview", payload_kind="image", shape=(5, 7, 3), dtype="uint8"),
            },
            intrinsics=CameraIntrinsics(fx=3.0, fy=4.0, cx=1.5, cy=2.0, width_px=7, height_px=5),
        ),
        payloads={
            "model-rgb": np.zeros((5, 7, 3), dtype=np.uint8),
            "model-depth": np.ones((5, 7), dtype=np.float32),
            "preview": np.zeros((5, 7, 3), dtype=np.uint8),
        },
    )

    assert calls == [
        ("rgb", "world/live/source/rgb", (11, 13, 3), 1, None),
        ("pinhole", "world/live/model/camera/image", (5, 7), 1, None),
        ("pinhole", "world/keyframes/cameras/000000/image", (5, 7), 1, None),
        ("rgb", rerun_sink_module.MODEL_RGB_2D_ENTITY_PATH, (5, 7, 3), 1, None),
        ("rgb", "world/live/model/camera/image", (5, 7, 3), 1, None),
        ("rgb", "world/keyframes/cameras/000000/image", (5, 7, 3), 1, None),
        ("depth", "world/live/model/camera/image/depth", (5, 7), 1, None),
        ("depth", "world/keyframes/cameras/000000/image/depth", (5, 7), 1, None),
        ("rgb", "world/live/model/diag/preview", (5, 7, 3), 1, None),
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

    sink = RerunEventSink(grpc_url=None, target_path=tmp_path / "viewer.rrd", log_camera_image_rgb=True)
    sink.observe_update(
        _slam_pose_update(
            source_seq=2,
            pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
        ),
        payloads={},
    )

    assert paths == [("world/live/tracking/camera", 2, None)]
    assert "world" not in [path for path, _, _ in paths]


def test_rerun_sink_actor_forwards_stage_runtime_updates_without_payload_resolver(tmp_path: Path, monkeypatch) -> None:
    observed: dict[str, object] = {}

    class FakeLocalSink:
        def __init__(self, **kwargs: object) -> None:
            observed["init"] = kwargs

        def observe_update(self, update, *, payload_resolver=None, payloads=None) -> None:
            del payload_resolver, payloads
            observed["update"] = update

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
    update = StageRuntimeUpdate(stage_key=StageKey.SLAM, timestamp_ns=1)
    actor.observe_update(update=update, payload_resolver=None)
    actor.close()

    assert observed["init"]["recording_id"] == "demo"
    assert observed["init"]["frusta_history_window_streaming"] == 5
    assert observed["init"]["show_tracking_trajectory"] is False
    assert observed["update"] == update
    assert observed["closed"] is True


def test_rerun_sink_actor_resolves_stage_runtime_update_payloads_in_sidecar(
    tmp_path: Path,
    monkeypatch,
) -> None:
    observed: dict[str, object] = {}
    payload = np.ones((2, 2, 3), dtype=np.uint8)
    ref = TransientPayloadRef(handle_id="frame", payload_kind="image", shape=(2, 2, 3), dtype="uint8")

    class FakeLocalSink:
        def __init__(self, **kwargs: object) -> None:
            observed["init"] = kwargs

        def observe_update(self, update, *, payload_resolver=None, payloads=None) -> None:
            del payloads
            observed["update"] = update
            observed["payload"] = payload_resolver(ref)

        def close(self) -> None:
            observed["closed"] = True

    class FakeReadPayloadRemote:
        def remote(self, handle_id: str) -> np.ndarray:
            assert handle_id == "frame"
            return payload

    class FakeResolver:
        read_payload = FakeReadPayloadRemote()

    monkeypatch.setattr(rerun_sink_module, "RerunEventSink", FakeLocalSink)
    monkeypatch.setattr(rerun_sink_module.ray, "get", lambda value: value)

    update = StageRuntimeUpdate(
        stage_key=StageKey.SLAM,
        timestamp_ns=1,
        visualizations=[
            VisualizationItem(
                intent=VisualizationIntent.RGB_IMAGE,
                role="model_rgb",
                payload_refs={"image": ref},
            )
        ],
    )
    actor_cls = RerunSinkActor.__ray_metadata__.modified_class
    actor = actor_cls(
        grpc_url=None,
        target_path=tmp_path / "viewer.rrd",
        recording_id="demo",
        frusta_history_window_streaming=5,
        show_tracking_trajectory=False,
    )
    actor.observe_update(
        update=update,
        payload_resolver=FakeResolver(),
    )
    actor.close()

    assert observed["init"]["recording_id"] == "demo"
    assert observed["update"] == update
    assert np.array_equal(observed["payload"], payload)
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

    sink = RerunEventSink(grpc_url=None, target_path=tmp_path / "viewer.rrd", log_camera_image_rgb=True)
    sink.observe_update(
        _slam_keyframe_update(
            source_seq=8,
            keyframe_index=3,
            pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
            refs={IMAGE_REF: _payload_ref("rgb", payload_kind="image", shape=(3, 4, 3), dtype="uint8")},
            intrinsics=CameraIntrinsics(fx=2.0, fy=2.0, cx=1.0, cy=1.0, width_px=4, height_px=3),
        ),
        payloads={"rgb": np.zeros((3, 4, 3), dtype=np.uint8)},
    )

    assert calls == [
        ("pose", "world/live/tracking/camera", 8, None),
        ("pose", "world/live/model", 8, None),
        ("pose", "world/keyframes/cameras/000003", 8, None),
        ("pose", "world/keyframes/points/000003", 8, None),
        ("pinhole", "world/live/model/camera/image", 8, None),
        ("pinhole", "world/keyframes/cameras/000003/image", 8, None),
        ("rgb", rerun_sink_module.MODEL_RGB_2D_ENTITY_PATH, 8, None),
        ("rgb", "world/live/model/camera/image", 8, None),
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
        sink.observe_update(
            _slam_keyframe_update(
                source_seq=keyframe_index,
                keyframe_index=keyframe_index,
                pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
                refs={},
            ),
            payloads={},
        )

    assert clears == ["world/keyframes/cameras/000000:True"]
