"""Focused tests for explicit Rerun timeline semantics."""

from __future__ import annotations

import numpy as np

from prml_vslam.interfaces import CameraIntrinsics, FramePacketProvenance, FrameTransform
from prml_vslam.methods.events import KeyframeVisualizationReady, PoseEstimated
from prml_vslam.pipeline.contracts.events import BackendNoticeReceived, FramePacketSummary, PacketObserved
from prml_vslam.pipeline.contracts.handles import ArrayHandle
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.sinks.rerun_policy import RerunLoggingPolicy


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


def test_policy_uses_explicit_frame_timeline_for_source_and_tracking_events() -> None:
    stream = _StrictFakeRecordingStream()
    calls: list[tuple[str, str, int | None, int | None]] = []
    policy = RerunLoggingPolicy(
        log_pinhole=lambda *args, **kwargs: None,
        log_pointcloud=lambda *args, **kwargs: None,
        log_line_strip3d=lambda stream, *, entity_path, positions_xyz: calls.append(
            ("trajectory", entity_path, *_timeline_state(stream))
        ),
        log_clear=lambda *args, **kwargs: None,
        log_depth_image=lambda *args, **kwargs: None,
        log_rgb_image=lambda stream, *, entity_path, image_rgb: calls.append(
            ("rgb", entity_path, *_timeline_state(stream))
        ),
        log_transform=lambda stream, *, entity_path, transform, axis_length=None: calls.append(
            ("pose", entity_path, *_timeline_state(stream))
        ),
    )

    stream.set_time("keyframe", sequence=99)
    policy.observe(
        stream,
        PacketObserved(
            event_id="1",
            run_id="run-1",
            ts_ns=1,
            packet=FramePacketSummary(seq=5, timestamp_ns=1, provenance=FramePacketProvenance()),
            frame=ArrayHandle(handle_id="frame", shape=(2, 2, 3), dtype="uint8"),
        ),
        payloads={"frame": np.zeros((2, 2, 3), dtype=np.uint8)},
    )
    policy.observe(
        stream,
        BackendNoticeReceived(
            event_id="2",
            run_id="run-1",
            ts_ns=2,
            stage_key=StageKey.SLAM,
            notice=PoseEstimated(
                seq=6,
                timestamp_ns=2,
                source_seq=7,
                pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
            ),
        ),
        payloads={},
    )

    assert calls == [
        ("rgb", "world/live/source/rgb", 5, None),
        ("pose", "world/live/tracking/camera", 7, None),
        ("trajectory", "world/trajectory/tracking", 7, None),
    ]


def test_policy_logs_live_model_on_frame_timeline_and_history_on_stable_untimed_paths() -> None:
    stream = _StrictFakeRecordingStream()
    calls: list[tuple[str, str, int | None, int | None]] = []
    policy = RerunLoggingPolicy(
        log_pinhole=lambda stream, *, entity_path, intrinsics: calls.append(
            ("pinhole", entity_path, *_timeline_state(stream))
        ),
        log_pointcloud=lambda stream, *, entity_path, pointmap, colors=None: calls.append(
            ("points", entity_path, *_timeline_state(stream))
        ),
        log_line_strip3d=lambda stream, *, entity_path, positions_xyz: calls.append(
            ("trajectory", entity_path, *_timeline_state(stream))
        ),
        log_clear=lambda *args, **kwargs: None,
        log_depth_image=lambda stream, *, entity_path, depth_m: calls.append(
            ("depth", entity_path, *_timeline_state(stream))
        ),
        log_rgb_image=lambda stream, *, entity_path, image_rgb: calls.append(
            ("rgb", entity_path, *_timeline_state(stream))
        ),
        log_transform=lambda stream, *, entity_path, transform, axis_length=None: calls.append(
            ("pose", entity_path, *_timeline_state(stream))
        ),
    )

    policy.observe(
        stream,
        BackendNoticeReceived(
            event_id="3",
            run_id="run-1",
            ts_ns=3,
            stage_key=StageKey.SLAM,
            notice=KeyframeVisualizationReady(
                seq=8,
                timestamp_ns=3,
                source_seq=13,
                source_timestamp_ns=3,
                keyframe_index=2,
                pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
                image=ArrayHandle(handle_id="rgb", shape=(3, 4, 3), dtype="uint8"),
                depth=ArrayHandle(handle_id="depth", shape=(3, 4), dtype="float32"),
                pointmap=ArrayHandle(handle_id="pointmap", shape=(3, 4, 3), dtype="float32"),
                camera_intrinsics=CameraIntrinsics(fx=2.0, fy=2.0, cx=1.0, cy=1.0, width_px=4, height_px=3),
            ),
        ),
        payloads={
            "rgb": np.zeros((3, 4, 3), dtype=np.uint8),
            "depth": np.ones((3, 4), dtype=np.float32),
            "pointmap": np.ones((3, 4, 3), dtype=np.float32),
        },
    )

    live_calls = [call for call in calls if call[1].startswith("world/live/model")]
    history_calls = [call for call in calls if call[1].startswith("world/keyframes/")]

    assert all(frame == 13 and keyframe is None for _, _, frame, keyframe in live_calls)
    assert all(frame is None and keyframe is None for _, _, frame, keyframe in history_calls)
