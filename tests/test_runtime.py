"""Tests for the pipeline runtime: messages, backends, session manager."""

from __future__ import annotations

import json
import math
from pathlib import Path

import cv2
import numpy as np
import pytest
from pydantic import ValidationError

from prml_vslam.pipeline import (
    Envelope,
    FramePayload,
    MessageKind,
    MethodId,
    PosePayload,
    PreviewPayload,
    SessionManager,
    TrajectoryArtifactMetadata,
    make_envelope,
    pose_from_matrix,
    pose_to_matrix,
)
from prml_vslam.pipeline.methods.base import SlamBackend, SlamOutput
from prml_vslam.pipeline.methods.mast3r import MockMast3rBackend
from prml_vslam.pipeline.methods.vista import MockVistaBackend

# ---------------------------------------------------------------------------
# Message model tests
# ---------------------------------------------------------------------------


def test_envelope_roundtrip() -> None:
    env = make_envelope(session_id="s1", seq=0, kind=MessageKind.FRAME, payload={"w": 640})
    data = env.model_dump(mode="json")
    restored = Envelope.model_validate(data)
    assert restored.session_id == "s1"
    assert restored.payload["w"] == 640


def test_envelope_toml_roundtrip() -> None:
    env = make_envelope(session_id="s1", seq=7, kind=MessageKind.POSE_UPDATE, ts_ns=123)
    toml_text = env.to_toml()
    restored = Envelope.from_toml(toml_text)
    assert restored.seq == 7
    assert restored.kind is MessageKind.POSE_UPDATE


# ---------------------------------------------------------------------------
# pytransform3d round-trip helpers
# ---------------------------------------------------------------------------


def test_pose_matrix_roundtrip() -> None:
    """pose_from_matrix → pose_to_matrix is identity for valid SE(3)."""
    from pytransform3d import transformations as pt

    mat = pt.transform_from(np.eye(3), np.array([1.0, 2.0, 3.0]))
    nested = pose_from_matrix(mat)
    recovered = pose_to_matrix(nested)
    np.testing.assert_allclose(recovered, mat, atol=1e-14)


def test_pose_payload_from_matrix() -> None:
    from pytransform3d import transformations as pt

    mat = pt.transform_from(np.eye(3), np.array([4.0, 5.0, 6.0]))
    pp = PosePayload.from_matrix(mat, timestamp_s=1.5, is_keyframe=True)
    assert pp.timestamp_s == 1.5
    assert pp.is_keyframe is True
    np.testing.assert_allclose(pp.matrix, mat, atol=1e-14)


def test_pose_payload_rejects_invalid_se3() -> None:
    with pytest.raises(ValidationError, match="transform"):
        PosePayload(
            t_world_camera=[
                [1.0, 0.0, 0.0, 0.0],
                [0.0, 1.0, 0.0, 0.0],
                [0.0, 0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0, 2.0],
            ]
        )


def test_preview_payload_rejects_non_xyz_points() -> None:
    with pytest.raises(ValidationError, match="trajectory_so_far"):
        PreviewPayload(trajectory_so_far=[[0.0, 1.0]])


def test_slam_output_rejects_invalid_pose() -> None:
    with pytest.raises(ValidationError, match="rotation matrix"):
        SlamOutput(pose=np.zeros((4, 4), dtype=np.float64))


def test_trajectory_metadata_enforces_canonical_units() -> None:
    with pytest.raises(ValidationError, match="units"):
        TrajectoryArtifactMetadata(
            artifact_path=Path("slam/trajectory.tum"),
            method=MethodId.VISTA_SLAM,
            units="feet",
        )


# ---------------------------------------------------------------------------
# Backend protocol conformance
# ---------------------------------------------------------------------------


def test_backends_satisfy_protocol() -> None:
    assert isinstance(MockVistaBackend(), SlamBackend)
    assert isinstance(MockMast3rBackend(), SlamBackend)


# ---------------------------------------------------------------------------
# Mock backend tests
# ---------------------------------------------------------------------------


def test_mock_vista_produces_circular_trajectory(tmp_path: Path) -> None:
    backend = MockVistaBackend(radius=1.0, angular_speed=0.5)

    outputs = [backend.step(i, ts_ns=int(i * 33e6)) for i in range(20)]

    for out in outputs:
        assert out.pose is not None
        dist = math.sqrt(float(out.pose[0, 3]) ** 2 + float(out.pose[2, 3]) ** 2)
        assert abs(dist - 1.0) < 0.01

    backend.export_artifacts(tmp_path)
    assert (tmp_path / "slam" / "trajectory.tum").exists()
    assert (tmp_path / "slam" / "sparse_points.ply").exists()


def test_mock_mast3r_produces_linear_trajectory(tmp_path: Path) -> None:
    backend = MockMast3rBackend(step_size=0.1, dense_update_interval=3)

    outputs = [backend.step(i, ts_ns=int(i * 33e6)) for i in range(15)]

    for out in outputs:
        assert out.pose is not None
        assert abs(float(out.pose[0, 3])) < 0.001  # x ≈ 0
        assert abs(float(out.pose[1, 3])) < 0.001  # y ≈ 0

    map_steps = [o for o in outputs if o.map_points is not None]
    assert len(map_steps) > 0

    backend.export_artifacts(tmp_path)
    assert (tmp_path / "slam" / "trajectory.tum").exists()


# ---------------------------------------------------------------------------
# Session manager tests
# ---------------------------------------------------------------------------


def test_session_manager_streaming_demo(tmp_path: Path) -> None:
    mgr = SessionManager()
    sess = mgr.create_session(
        mode="streaming",
        method=MethodId.VISTA_SLAM,
        artifact_root=tmp_path / "streaming",
    )
    assert sess.session_id in mgr.active_sessions

    all_outputs: list[Envelope] = []
    for i in range(10):
        env = make_envelope(
            session_id=sess.session_id,
            seq=i,
            kind=MessageKind.FRAME,
            payload={"width": 640, "height": 480, "frame_index": i},
            ts_ns=int(i * 33e6),
        )
        all_outputs.extend(mgr.push(sess.session_id, [env]))

    final = mgr.close_session(sess.session_id)
    all_outputs.extend(final)

    pose_count = sum(1 for o in all_outputs if o.kind is MessageKind.POSE_UPDATE)
    assert pose_count == 10
    assert sess.session_id not in mgr.active_sessions


def test_frame_payload_requires_materialisable_source() -> None:
    with pytest.raises(ValidationError, match="FramePayload requires"):
        FramePayload()


def test_session_manager_rejects_invalid_stream_frame(tmp_path: Path) -> None:
    mgr = SessionManager()
    sess = mgr.create_session(
        mode="streaming",
        method=MethodId.VISTA_SLAM,
        artifact_root=tmp_path / "streaming",
    )
    env = make_envelope(
        session_id=sess.session_id,
        seq=0,
        kind=MessageKind.FRAME,
        payload={"width": 640},
        ts_ns=1,
    )

    with pytest.raises(ValidationError, match="width and height"):
        mgr.push(sess.session_id, [env])


def test_streaming_session_persists_replay_inputs(tmp_path: Path) -> None:
    mgr = SessionManager()
    artifact_root = tmp_path / "streaming"
    sess = mgr.create_session(
        mode="streaming",
        method=MethodId.VISTA_SLAM,
        artifact_root=artifact_root,
    )

    frame = np.full((18, 24, 3), 127, dtype=np.uint8)
    ok, encoded = cv2.imencode(".jpg", frame)
    assert ok

    env = make_envelope(
        session_id=sess.session_id,
        seq=3,
        kind=MessageKind.FRAME,
        payload={
            "jpeg_bytes": encoded.tobytes(),
            "width": 24,
            "height": 18,
            "frame_index": 42,
        },
        ts_ns=123456789,
    )

    mgr.push(sess.session_id, [env])
    mgr.close_session(sess.session_id)

    manifest_path = artifact_root / "input" / "capture_manifest.json"
    assert manifest_path.exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["mode"] == "streaming"
    assert manifest["method"] == MethodId.VISTA_SLAM.value
    assert manifest["num_frames"] == 1
    assert manifest["entries"][0]["frame_index"] == 42

    persisted_frame = artifact_root / manifest["entries"][0]["image_path"]
    assert persisted_frame.exists()


def test_session_manager_offline_requires_video_path() -> None:
    mgr = SessionManager()
    with pytest.raises(ValueError, match="video_path"):
        mgr.create_session(
            mode="offline",
            method=MethodId.VISTA_SLAM,
            artifact_root=Path("/tmp/test"),
        )


def test_deterministic_replay(tmp_path: Path) -> None:
    """Running the streaming pipeline twice with identical inputs produces
    identical pose sequences."""
    results: list[list[list[list[float]]]] = []

    for run in range(2):
        mgr = SessionManager()
        sess = mgr.create_session(
            mode="streaming",
            method=MethodId.VISTA_SLAM,
            artifact_root=tmp_path / f"run-{run}",
            session_id=f"replay-{run}",
        )
        outputs: list[Envelope] = []
        for i in range(30):
            env = make_envelope(
                session_id=sess.session_id,
                seq=i,
                kind=MessageKind.FRAME,
                payload={"width": 2, "height": 2},
                ts_ns=int(i * 33e6),
            )
            outputs.extend(mgr.push(sess.session_id, [env]))
        mgr.close_session(sess.session_id)

        poses = [o.payload["t_world_camera"] for o in outputs if o.kind is MessageKind.POSE_UPDATE]
        results.append(poses)

    assert len(results[0]) == len(results[1])
    for p1, p2 in zip(results[0], results[1], strict=True):
        for r1, r2 in zip(p1, p2, strict=True):
            for v1, v2 in zip(r1, r2, strict=True):
                assert abs(v1 - v2) < 1e-12
