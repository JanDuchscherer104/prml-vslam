"""Focused tests for Rerun layout and modality semantics."""

from __future__ import annotations

import logging
from types import SimpleNamespace

import numpy as np
import pytest

from prml_vslam.interfaces import FrameTransform
from prml_vslam.interfaces.alignment import GroundAlignmentMetadata
from prml_vslam.methods.contracts import SlamUpdate
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.sinks.rerun_policy import RerunLoggingPolicy
from prml_vslam.pipeline.stages.base.contracts import StageRuntimeUpdate
from prml_vslam.pipeline.stages.base.handles import TransientPayloadRef
from prml_vslam.pipeline.stages.slam.visualization import DEPTH_REF, IMAGE_REF, PREVIEW_REF, SlamVisualizationAdapter
from prml_vslam.visualization import rerun as rerun_helpers


class _FakeRecordingStream:
    def __init__(self) -> None:
        self.timelines: dict[str, int] = {}

    def set_time(self, timeline: str, *, sequence: int) -> None:
        self.timelines[timeline] = sequence

    def reset_time(self) -> None:
        self.timelines.clear()

    def disable_timeline(self, timeline: str) -> None:  # pragma: no cover - should never be called
        raise AssertionError(f"disable_timeline must not be used: {timeline}")


def _payload_ref(handle_id: str, *, payload_kind: str, shape: tuple[int, ...], dtype: str) -> TransientPayloadRef:
    return TransientPayloadRef(handle_id=handle_id, payload_kind=payload_kind, shape=shape, dtype=dtype)


def _keyframe_update(*, refs: dict[str, TransientPayloadRef]) -> StageRuntimeUpdate:
    return StageRuntimeUpdate(
        stage_key=StageKey.SLAM,
        timestamp_ns=1,
        visualizations=SlamVisualizationAdapter().build_items(
            SlamUpdate(
                seq=1,
                timestamp_ns=1,
                source_seq=2,
                source_timestamp_ns=1,
                is_keyframe=True,
                keyframe_index=7,
                pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
            ),
            refs,
        ),
    )


def test_policy_uses_camera_image_namespace_and_fallback_intrinsics(caplog: pytest.LogCaptureFixture) -> None:
    stream = _FakeRecordingStream()
    pinhole_calls: list[tuple[str, object]] = []
    rgb_calls: list[str] = []
    policy = RerunLoggingPolicy(
        log_pinhole=lambda stream, *, entity_path, intrinsics: pinhole_calls.append((entity_path, intrinsics)),
        log_pointcloud=lambda *args, **kwargs: None,
        log_pointcloud_ply=lambda *args, **kwargs: None,
        log_mesh_ply=lambda *args, **kwargs: None,
        log_line_strip3d=lambda *args, **kwargs: None,
        log_clear=lambda *args, **kwargs: None,
        log_depth_image=lambda *args, **kwargs: None,
        log_ground_plane_patch=lambda *args, **kwargs: None,
        log_rgb_image=lambda stream, *, entity_path, image_rgb: rgb_calls.append(entity_path),
        log_transform=lambda *args, **kwargs: None,
        log_diagnostic_preview=True,
        log_camera_image_rgb=True,
    )

    with caplog.at_level(logging.WARNING):
        policy.observe_update(
            stream,
            _keyframe_update(
                refs={
                    IMAGE_REF: _payload_ref("rgb", payload_kind="image", shape=(3, 4, 3), dtype="uint8"),
                    DEPTH_REF: _payload_ref("depth", payload_kind="depth", shape=(3, 4), dtype="float32"),
                    PREVIEW_REF: _payload_ref("preview", payload_kind="image", shape=(3, 4, 3), dtype="uint8"),
                }
            ),
            payloads={
                "rgb": np.zeros((3, 4, 3), dtype=np.uint8),
                "depth": np.ones((3, 4), dtype=np.float32),
                "preview": np.zeros((3, 4, 3), dtype=np.uint8),
            },
        )

    assert [path for path, _ in pinhole_calls] == [
        "world/live/model/camera/image",
        "world/keyframes/cameras/000007/image",
    ]
    assert "world/live/model/camera/image" in rgb_calls
    assert "world/live/model/diag/preview" in rgb_calls
    live_intrinsics = pinhole_calls[0][1]
    assert live_intrinsics.fx == 2.0
    assert live_intrinsics.fy == 1.5
    assert live_intrinsics.cx == 2.0
    assert live_intrinsics.cy == 1.5
    assert live_intrinsics.width_px == 4
    assert live_intrinsics.height_px == 3


def test_policy_rejects_mismatched_rgb_and_depth_rasters() -> None:
    stream = _FakeRecordingStream()
    policy = RerunLoggingPolicy(
        log_pinhole=lambda *args, **kwargs: None,
        log_pointcloud=lambda *args, **kwargs: None,
        log_pointcloud_ply=lambda *args, **kwargs: None,
        log_mesh_ply=lambda *args, **kwargs: None,
        log_line_strip3d=lambda *args, **kwargs: None,
        log_clear=lambda *args, **kwargs: None,
        log_depth_image=lambda *args, **kwargs: None,
        log_ground_plane_patch=lambda *args, **kwargs: None,
        log_rgb_image=lambda *args, **kwargs: None,
        log_transform=lambda *args, **kwargs: None,
    )

    with pytest.raises(ValueError, match="must share the same raster shape"):
        policy.observe_update(
            stream,
            _keyframe_update(
                refs={
                    IMAGE_REF: _payload_ref("rgb", payload_kind="image", shape=(3, 4, 3), dtype="uint8"),
                    DEPTH_REF: _payload_ref("depth", payload_kind="depth", shape=(2, 4), dtype="float32"),
                }
            ),
            payloads={
                "rgb": np.zeros((3, 4, 3), dtype=np.uint8),
                "depth": np.ones((2, 4), dtype=np.float32),
            },
        )


def test_create_recording_stream_default_3d_view_uses_keyed_history_geometry(monkeypatch) -> None:
    sent_blueprints: list[object] = []
    logged_entities: list[tuple[str, object, bool]] = []

    class FakeRecordingStream:
        def __init__(self, *, application_id: str, recording_id: str | None) -> None:
            self.application_id = application_id
            self.recording_id = recording_id

        def send_blueprint(self, blueprint: object) -> None:
            sent_blueprints.append(blueprint)

        def log(self, entity_path: str, payload: object, *extra: object, static: bool = False) -> None:
            del extra
            logged_entities.append((entity_path, payload, static))

    class FakeSpatial3DView:
        def __init__(self, *, origin: str, contents=None, name: str) -> None:
            self.origin = origin
            self.contents = contents
            self.name = name

    class FakeSpatial2DView:
        def __init__(self, *, origin: str, contents=None, name: str) -> None:
            self.origin = origin
            self.contents = contents
            self.name = name

    class FakeHorizontal:
        def __init__(self, *views: object) -> None:
            self.views = views

    class FakeTabs:
        def __init__(self, *views: object, name: str | None = None) -> None:
            self.views = views
            self.name = name

    class FakeBlueprint:
        def __init__(self, layout: object) -> None:
            self.layout = layout

    class FakeTransform3D:
        def __init__(self, *, axis_length: float) -> None:
            self.identity = True
            self.axis_length = axis_length

    class FakeViewCoordinates:
        RDF = "rdf"

    monkeypatch.setattr(
        rerun_helpers,
        "rr",
        SimpleNamespace(
            RecordingStream=FakeRecordingStream,
            Transform3D=FakeTransform3D,
            ViewCoordinates=FakeViewCoordinates,
        ),
    )
    monkeypatch.setattr(
        rerun_helpers,
        "rrb",
        SimpleNamespace(
            Blueprint=FakeBlueprint,
            Horizontal=FakeHorizontal,
            Spatial3DView=FakeSpatial3DView,
            Spatial2DView=FakeSpatial2DView,
            Tabs=FakeTabs,
        ),
    )

    rerun_helpers.create_recording_stream(app_id="prml-vslam", recording_id="demo")

    layout = sent_blueprints[0].layout
    assert layout.views[0].contents == [
        "+ world/alignment/**",
        "+ world/reconstruction/**",
        "+ world/live/tracking/**",
        "+ world/live/model",
        "- world/live/model/camera/image",
        "- world/live/model/camera/image/**",
        "- world/live/model/camera/image/depth",
        "- world/live/model/camera/image/depth/**",
        "- world/live/model/points",
        "- world/live/model/points/**",
        "- world/keyframes/cameras/**",
        "+ world/keyframes/points/**",
        "+ world/trajectory/tracking",
    ]
    assert [view.origin for view in layout.views[1].views] == [
        rerun_helpers.MODEL_RGB_2D_ENTITY_PATH,
        "world/live/model/camera/image",
    ]
    assert len(logged_entities) == 2
    assert logged_entities[0][0] == rerun_helpers.ROOT_WORLD_ENTITY_PATH
    assert isinstance(logged_entities[0][1], FakeTransform3D)
    assert logged_entities[0][1].axis_length == rerun_helpers.ROOT_WORLD_AXIS_LENGTH
    assert logged_entities[0][2] is True
    assert logged_entities[1][0] == rerun_helpers.ROOT_WORLD_ENTITY_PATH
    assert logged_entities[1][1] == FakeViewCoordinates.RDF
    assert logged_entities[1][2] is True


def test_policy_logs_ground_plane_overlay_on_ground_alignment_stage_update() -> None:
    stream = _FakeRecordingStream()
    ground_calls: list[GroundAlignmentMetadata] = []
    metadata = GroundAlignmentMetadata(
        applied=True,
        confidence=0.9,
        point_cloud_source="dense_points_ply",
        visualization={"corners_xyz_world": [(0.0, 0.0, 0.0)] * 4},
    )
    policy = RerunLoggingPolicy(
        log_pinhole=lambda *args, **kwargs: None,
        log_pointcloud=lambda *args, **kwargs: None,
        log_pointcloud_ply=lambda *args, **kwargs: None,
        log_mesh_ply=lambda *args, **kwargs: None,
        log_line_strip3d=lambda *args, **kwargs: None,
        log_clear=lambda *args, **kwargs: None,
        log_depth_image=lambda *args, **kwargs: None,
        log_ground_plane_patch=lambda stream, *, metadata: ground_calls.append(metadata),
        log_rgb_image=lambda *args, **kwargs: None,
        log_transform=lambda *args, **kwargs: None,
    )

    policy.observe_update(
        stream,
        StageRuntimeUpdate(
            stage_key=StageKey.GRAVITY_ALIGNMENT,
            timestamp_ns=1,
            semantic_events=[metadata],
        ),
    )

    assert ground_calls == [metadata]
