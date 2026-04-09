"""Tests for the repository-local method backends."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from prml_vslam.interfaces import CameraIntrinsics, FramePacket, SE3Pose
from prml_vslam.methods import MethodId, MockSlamBackendConfig, VistaSlamBackendConfig
from prml_vslam.pipeline.contracts import SequenceManifest, SlamConfig
from prml_vslam.utils.geometry import load_tum_trajectory, write_tum_trajectory

_VISTA_WEIGHTS = Path("external/vista-slam/pretrains/frontend_sta_weights.pth")
_VISTA_DEMO_VIDEO = Path("external/vista-slam/media/tumrgbd_room.mp4")


def _has_cuda() -> bool:
    try:
        import torch  # noqa: PLC0415

        return torch.cuda.is_available()
    except ImportError:
        return False


_skip_no_vista_assets = pytest.mark.skipif(
    not (_VISTA_WEIGHTS.exists() and _VISTA_DEMO_VIDEO.exists()),
    reason="ViSTA-SLAM weights or demo video not available",
)


def _write_calibration(path: Path, *, width_px: int = 64, height_px: int = 64) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""
cameras:
- camera:
    image_height: {height_px}
    image_width: {width_px}
    type: pinhole
    intrinsics:
      data: [100.0, 101.0, 32.0, 24.0]
    distortion:
      type: radial-tangential
      parameters:
        data: [0.1, 0.01, 0.0, 0.0]
    T_cam_imu:
      data:
      - [1.0, 0.0, 0.0, 0.01]
      - [0.0, 1.0, 0.0, 0.02]
      - [0.0, 0.0, 1.0, 0.03]
      - [0.0, 0.0, 0.0, 1.0]
""".strip(),
        encoding="utf-8",
    )


def test_mock_slam_backend_materializes_placeholder_outputs_without_reference(tmp_path: Path) -> None:
    backend = MockSlamBackendConfig(method_id=MethodId.MSTR).setup_target()
    assert backend is not None

    result = backend.run_sequence(
        SequenceManifest(sequence_id="demo-sequence"),
        SlamConfig(method=MethodId.MSTR),
        tmp_path / "artifacts" / "demo" / "mstr",
    )

    assert result.trajectory_tum.path.exists()
    assert result.dense_points_ply is not None
    assert result.dense_points_ply.path.exists()


def test_mock_slam_backend_runs_sequence_manifest_offline(tmp_path: Path) -> None:
    backend = MockSlamBackendConfig().setup_target()
    assert backend is not None

    reference_path = tmp_path / "reference.tum"
    calibration_path = tmp_path / "iphone-03.yaml"
    _write_calibration(calibration_path)
    write_tum_trajectory(
        reference_path,
        [
            SE3Pose(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
            SE3Pose(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=0.5, tz=0.0),
        ],
        [0.0, 1.0],
    )

    artifacts = backend.run_sequence(
        SequenceManifest(
            sequence_id="advio-15",
            reference_tum_path=reference_path,
            intrinsics_path=calibration_path,
        ),
        SlamConfig(method=MethodId.VISTA),
        tmp_path / "offline-artifacts",
    )

    trajectory = load_tum_trajectory(artifacts.trajectory_tum.path)
    dense_lines = (
        artifacts.dense_points_ply.path.read_text(encoding="utf-8").splitlines() if artifacts.dense_points_ply else []
    )

    assert trajectory.timestamps.shape == (2,)
    assert np.allclose(trajectory.positions_xyz[0], np.array([0.0, 0.0, 0.0], dtype=np.float64))
    assert np.allclose(trajectory.positions_xyz[1], np.array([1.0, 0.5, 0.0], dtype=np.float64))
    assert artifacts.sparse_points_ply is not None
    assert artifacts.sparse_points_ply.path.exists()
    assert artifacts.preview_log_jsonl is not None
    assert artifacts.preview_log_jsonl.path.exists()
    assert artifacts.dense_points_ply is not None
    assert artifacts.dense_points_ply.path.exists()
    assert "element vertex 32" in dense_lines


def test_mock_slam_session_emits_incremental_updates_and_artifacts(tmp_path: Path) -> None:
    backend = MockSlamBackendConfig().setup_target()
    assert backend is not None

    session = backend.start_session(
        SlamConfig(method=MethodId.VISTA),
        tmp_path / "streaming-artifacts",
    )
    update0 = session.step(
        FramePacket(
            seq=0,
            timestamp_ns=2_000_000_000,
            rgb=np.zeros((8, 8, 3), dtype=np.uint8),
            intrinsics=CameraIntrinsics(fx=400.0, fy=400.0, cx=3.5, cy=3.5, width_px=8, height_px=8),
            pose=SE3Pose(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
        )
    )
    update1 = session.step(
        FramePacket(
            seq=1,
            timestamp_ns=1_500_000_000,
            rgb=np.zeros((8, 8, 3), dtype=np.uint8),
            intrinsics=CameraIntrinsics(fx=400.0, fy=400.0, cx=3.5, cy=3.5, width_px=8, height_px=8),
            pose=SE3Pose(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=0.0, tz=0.0),
        )
    )
    artifacts = session.close()

    trajectory_lines = artifacts.trajectory_tum.path.read_text(encoding="utf-8").splitlines()
    timestamps_s = [float(line.split()[0]) for line in trajectory_lines]

    assert update0.num_sparse_points > 0
    assert update0.num_dense_points > 0
    assert update0.pointmap is not None
    assert update1.num_sparse_points >= update0.num_sparse_points
    assert update1.num_dense_points >= update0.num_dense_points
    assert artifacts.sparse_points_ply is not None
    assert artifacts.sparse_points_ply.path.exists()
    assert artifacts.dense_points_ply is not None
    assert artifacts.dense_points_ply.path.exists()
    assert timestamps_s[1] > timestamps_s[0]


# ------------------------------------------------------------------
# ViSTA-SLAM streaming session
# ------------------------------------------------------------------

_NUM_VISTA_TEST_FRAMES = 10


def _extract_test_frames(video_path: Path, max_frames: int) -> list[np.ndarray]:
    """Read up to *max_frames* RGB frames from a video file."""
    cap = cv2.VideoCapture(str(video_path))
    frames: list[np.ndarray] = []
    while len(frames) < max_frames:
        ok, bgr = cap.read()
        if not ok:
            break
        frames.append(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
    cap.release()
    return frames


@_skip_no_vista_assets
def test_vista_slam_session_processes_frames_and_produces_artifacts(tmp_path: Path) -> None:
    """start_session → step(frame) × N → close() produces a valid trajectory."""
    backend = VistaSlamBackendConfig().setup_target()
    assert backend is not None

    session = backend.start_session(
        SlamConfig(method=MethodId.VISTA),
        tmp_path / "vista-streaming",
    )

    frames = _extract_test_frames(_VISTA_DEMO_VIDEO, _NUM_VISTA_TEST_FRAMES)
    assert len(frames) == _NUM_VISTA_TEST_FRAMES, "Demo video too short for test"

    updates = []
    for seq, rgb in enumerate(frames):
        update = session.step(
            FramePacket(seq=seq, timestamp_ns=seq * 33_000_000, rgb=rgb)
        )
        updates.append(update)
        assert update.seq == seq

    artifacts = session.close()

    # Trajectory must exist and contain poses
    assert artifacts.trajectory_tum.path.exists()
    trajectory = load_tum_trajectory(artifacts.trajectory_tum.path)
    assert len(trajectory.timestamps) > 0

    # Point cloud artifacts
    assert artifacts.sparse_points_ply is not None
    assert artifacts.sparse_points_ply.path.exists()
