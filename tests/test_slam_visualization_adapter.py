"""Tests for the SLAM stage visualization adapter."""

from __future__ import annotations

from prml_vslam.interfaces import CameraIntrinsics, FrameTransform
from prml_vslam.methods.contracts import SlamUpdate
from prml_vslam.pipeline.stages.base.contracts import VisualizationIntent
from prml_vslam.pipeline.stages.base.handles import TransientPayloadRef
from prml_vslam.pipeline.stages.slam.visualization import (
    DEPTH_REF,
    IMAGE_REF,
    POINTMAP_REF,
    PREVIEW_REF,
    ROLE_KEYFRAME_CAMERA_WINDOW,
    ROLE_KEYFRAME_DEPTH,
    ROLE_KEYFRAME_PINHOLE,
    ROLE_KEYFRAME_POINTMAP,
    ROLE_KEYFRAME_RGB,
    ROLE_MODEL_DEPTH,
    ROLE_MODEL_PINHOLE,
    ROLE_MODEL_POINTMAP,
    ROLE_MODEL_PREVIEW,
    ROLE_MODEL_RGB,
    ROLE_TRACKING_POSE,
    ROLE_TRACKING_TRAJECTORY,
    SlamVisualizationAdapter,
)


def _pose() -> FrameTransform:
    return FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=2.0, tz=3.0)


def _ref(handle_id: str, *, payload_kind: str, shape: tuple[int, ...], dtype: str) -> TransientPayloadRef:
    return TransientPayloadRef(handle_id=handle_id, payload_kind=payload_kind, shape=shape, dtype=dtype)


def test_pose_only_update_produces_pose_and_trajectory_items() -> None:
    update = SlamUpdate(seq=4, timestamp_ns=10, source_seq=9, pose=_pose(), pose_updated=True)

    items = SlamVisualizationAdapter().build_items(update, {})

    assert [(item.intent, item.role, item.frame_index) for item in items] == [
        (VisualizationIntent.POSE_TRANSFORM, ROLE_TRACKING_POSE, 9),
        (VisualizationIntent.TRAJECTORY, ROLE_TRACKING_TRAJECTORY, 9),
    ]
    assert all(item.pose == update.pose for item in items)


def test_keyframe_update_produces_model_and_keyframe_visualization_items() -> None:
    update = SlamUpdate(
        seq=5,
        timestamp_ns=10,
        source_seq=8,
        is_keyframe=True,
        keyframe_index=3,
        pose=_pose(),
        camera_intrinsics=CameraIntrinsics(fx=2.0, fy=2.0, cx=1.0, cy=1.0, width_px=4, height_px=3),
    )
    refs = {
        IMAGE_REF: _ref("rgb", payload_kind="image", shape=(3, 4, 3), dtype="uint8"),
        DEPTH_REF: _ref("depth", payload_kind="depth", shape=(3, 4), dtype="float32"),
        PREVIEW_REF: _ref("preview", payload_kind="image", shape=(3, 4, 3), dtype="uint8"),
        POINTMAP_REF: _ref("pointmap", payload_kind="point_cloud", shape=(3, 4, 3), dtype="float32"),
    }

    items = SlamVisualizationAdapter().build_items(update, refs)
    roles = [item.role for item in items]

    assert ROLE_MODEL_RGB in roles
    assert ROLE_MODEL_DEPTH in roles
    assert ROLE_MODEL_PREVIEW in roles
    assert ROLE_MODEL_POINTMAP in roles
    assert ROLE_MODEL_PINHOLE in roles
    assert ROLE_KEYFRAME_RGB in roles
    assert ROLE_KEYFRAME_DEPTH in roles
    assert ROLE_KEYFRAME_POINTMAP in roles
    assert ROLE_KEYFRAME_PINHOLE in roles
    assert ROLE_KEYFRAME_CAMERA_WINDOW in roles
    assert all(item.frame_index == 8 for item in items)
    assert all(item.keyframe_index in {None, 3} for item in items)
    assert next(item for item in items if item.role == ROLE_MODEL_POINTMAP).payload_refs["colors"] == refs[IMAGE_REF]


def test_slam_update_remains_free_of_transient_payload_refs() -> None:
    field_annotations = [repr(field.annotation) for field in SlamUpdate.model_fields.values()]

    assert not any("TransientPayloadRef" in annotation for annotation in field_annotations)
