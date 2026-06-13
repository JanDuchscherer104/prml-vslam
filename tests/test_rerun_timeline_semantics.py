"""Focused tests for explicit Rerun timeline semantics."""

from __future__ import annotations

import numpy as np

from prml_vslam.interfaces import CameraIntrinsics, FrameTransform
from prml_vslam.methods.contracts import SlamUpdate
from prml_vslam.methods.stage.visualization import (
    DEPTH_REF,
    IMAGE_REF,
    POINTMAP_REF,
    ROLE_SOURCE_RGB,
    SlamVisualizationAdapter,
)
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.contracts import StageRuntimeUpdate, VisualizationIntent, VisualizationItem
from prml_vslam.pipeline.stages.base.handles import TransientPayloadRef
from prml_vslam.visualization import rerun as rerun_helpers
from prml_vslam.visualization.rerun_policy import RerunLoggingPolicy


class _StrictFakeRecordingStream:
    def __init__(self) -> None:
        self.timelines: dict[str, int] = {}

    def set_time(self, timeline: str, *, sequence: int) -> None:
        self.timelines[timeline] = sequence

    def reset_time(self) -> None:
        self.timelines.clear()

    def disable_timeline(self, timeline: str) -> None:  # pragma: no cover - should never be called
        raise AssertionError(f"disable_timeline must not be used: {timeline}")

    def current_timeline(self, timeline: str) -> int | None:
        return self.timelines.get(timeline)


def _timeline_state(stream: _StrictFakeRecordingStream) -> tuple[int | None, int | None]:
    return stream.current_timeline("frame"), stream.current_timeline("keyframe")


def _payload_ref(handle_id: str, *, payload_kind: str, shape: tuple[int, ...], dtype: str) -> TransientPayloadRef:
    return TransientPayloadRef(handle_id=handle_id, payload_kind=payload_kind, shape=shape, dtype=dtype)


def _source_update(frame_index: int) -> StageRuntimeUpdate:
    return StageRuntimeUpdate(
        stage_key=StageKey.SOURCE,
        timestamp_ns=1,
        visualizations=[
            VisualizationItem(
                intent=VisualizationIntent.RGB_IMAGE,
                role=ROLE_SOURCE_RGB,
                payload_refs={IMAGE_REF: _payload_ref("frame", payload_kind="image", shape=(2, 2, 3), dtype="uint8")},
                frame_index=frame_index,
            )
        ],
    )


def _pose_update(source_seq: int) -> StageRuntimeUpdate:
    return StageRuntimeUpdate(
        stage_key=StageKey.SLAM,
        timestamp_ns=2,
        visualizations=SlamVisualizationAdapter().build_items(
            SlamUpdate(
                seq=source_seq - 1,
                timestamp_ns=2,
                source_seq=source_seq,
                pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
            ),
            {},
        ),
    )


def _keyframe_update(source_seq: int) -> StageRuntimeUpdate:
    return StageRuntimeUpdate(
        stage_key=StageKey.SLAM,
        timestamp_ns=3,
        visualizations=SlamVisualizationAdapter().build_items(
            SlamUpdate(
                seq=8,
                timestamp_ns=3,
                source_seq=source_seq,
                source_timestamp_ns=3,
                is_keyframe=True,
                keyframe_index=2,
                pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
                camera_intrinsics=CameraIntrinsics(fx=2.0, fy=2.0, cx=1.0, cy=1.0, width_px=4, height_px=3),
            ),
            {
                IMAGE_REF: _payload_ref("rgb", payload_kind="image", shape=(3, 4, 3), dtype="uint8"),
                DEPTH_REF: _payload_ref("depth", payload_kind="depth", shape=(3, 4), dtype="float32"),
                POINTMAP_REF: _payload_ref("pointmap", payload_kind="point_cloud", shape=(3, 4, 3), dtype="float32"),
            },
        ),
    )


def test_policy_uses_explicit_frame_timeline_for_source_and_tracking_updates(monkeypatch) -> None:
    stream = _StrictFakeRecordingStream()
    calls: list[tuple[str, str, int | None, int | None]] = []
    monkeypatch.setattr(rerun_helpers, "log_pinhole", lambda *args, **kwargs: None)
    monkeypatch.setattr(rerun_helpers, "log_pointcloud", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        rerun_helpers,
        "log_points3d",
        lambda stream, *, entity_path, points_xyz, **kwargs: calls.append(
            ("point", entity_path, *_timeline_state(stream))
        ),
    )
    monkeypatch.setattr(
        rerun_helpers,
        "log_line_strip3d",
        lambda stream, *, entity_path, positions_xyz, **kwargs: calls.append(
            ("trajectory", entity_path, *_timeline_state(stream))
        ),
    )
    monkeypatch.setattr(
        rerun_helpers,
        "log_rgb_image",
        lambda stream, *, entity_path, image_rgb: calls.append(("rgb", entity_path, *_timeline_state(stream))),
    )
    monkeypatch.setattr(
        rerun_helpers,
        "log_transform",
        lambda stream, *, entity_path, transform, axis_length=None, static=False: calls.append(
            ("pose", entity_path, *_timeline_state(stream))
        ),
    )
    policy = RerunLoggingPolicy(
        log_source_rgb=True,
    )

    stream.set_time("keyframe", sequence=99)
    policy.observe_update(stream, _source_update(5), payloads={"frame": np.zeros((2, 2, 3), dtype=np.uint8)})
    policy.observe_update(stream, _pose_update(7), payloads={})

    assert calls == [
        ("rgb", "world/live/source/rgb", 5, None),
        ("pose", "world/slam/live/tracking/camera", 7, None),
        ("pose", "world/slam/live/tracking_smoothed/camera", 7, None),
        ("point", "world/slam/trajectory/raw/start", 7, None),
        ("trajectory", "world/slam/trajectory/raw", 7, None),
        ("point", "world/slam/trajectory/smoothed/start", 7, None),
        ("trajectory", "world/slam/trajectory/smoothed", 7, None),
    ]


def test_policy_logs_live_model_and_keyed_history_on_frame_timeline(monkeypatch) -> None:
    stream = _StrictFakeRecordingStream()
    calls: list[tuple[str, str, int | None, int | None]] = []
    monkeypatch.setattr(
        rerun_helpers,
        "log_pinhole",
        lambda stream, *, entity_path, intrinsics, image_plane_distance=None: calls.append(
            ("pinhole", entity_path, *_timeline_state(stream))
        ),
    )
    monkeypatch.setattr(
        rerun_helpers,
        "log_pointcloud",
        lambda stream, *, entity_path, pointmap, colors=None, **kwargs: calls.append(
            ("points", entity_path, *_timeline_state(stream))
        ),
    )
    monkeypatch.setattr(
        rerun_helpers,
        "log_points3d",
        lambda stream, *, entity_path, points_xyz, **kwargs: calls.append(
            ("point", entity_path, *_timeline_state(stream))
        ),
    )
    monkeypatch.setattr(
        rerun_helpers,
        "log_line_strip3d",
        lambda stream, *, entity_path, positions_xyz, **kwargs: calls.append(
            ("trajectory", entity_path, *_timeline_state(stream))
        ),
    )
    monkeypatch.setattr(
        rerun_helpers,
        "log_depth_image",
        lambda stream, *, entity_path, depth_m: calls.append(("depth", entity_path, *_timeline_state(stream))),
    )
    monkeypatch.setattr(
        rerun_helpers,
        "log_rgb_image",
        lambda stream, *, entity_path, image_rgb: calls.append(("rgb", entity_path, *_timeline_state(stream))),
    )
    monkeypatch.setattr(
        rerun_helpers,
        "log_transform",
        lambda stream, *, entity_path, transform, axis_length=None, static=False: calls.append(
            ("pose", entity_path, *_timeline_state(stream))
        ),
    )
    policy = RerunLoggingPolicy()

    policy.observe_update(
        stream,
        _keyframe_update(13),
        payloads={
            "rgb": np.zeros((3, 4, 3), dtype=np.uint8),
            "depth": np.ones((3, 4), dtype=np.float32),
            "pointmap": np.ones((3, 4, 3), dtype=np.float32),
        },
    )

    live_calls = [call for call in calls if call[1].startswith("world/slam/live/model")]
    history_calls = [call for call in calls if call[1].startswith("world/slam/keyframes/")]

    assert all(frame == 13 and keyframe is None for _, _, frame, keyframe in live_calls)
    assert all(frame == 13 and keyframe is None for _, _, frame, keyframe in history_calls)
