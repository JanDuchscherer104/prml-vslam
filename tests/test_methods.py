"""Tests for the repository-local method mocks."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np

from prml_vslam.interfaces import CameraIntrinsics, FramePacket, SE3Pose
from prml_vslam.methods import MethodId, MockSlamBackendConfig, VistaSlamBackend, VistaSlamBackendConfig
from prml_vslam.methods.contracts import SlamBackendConfig, SlamOutputPolicy
from prml_vslam.methods.vista.adapter import VistaSlamSession
from prml_vslam.pipeline import SequenceManifest
from prml_vslam.utils import Console
from prml_vslam.utils.geometry import load_tum_trajectory, write_tum_trajectory


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
        SlamBackendConfig(),
        SlamOutputPolicy(),
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
        SlamBackendConfig(),
        SlamOutputPolicy(),
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
    assert artifacts.dense_points_ply is not None
    assert artifacts.dense_points_ply.path.exists()
    assert "element vertex 32" in dense_lines


def test_mock_slam_session_emits_incremental_updates_and_artifacts(tmp_path: Path) -> None:
    backend = MockSlamBackendConfig().setup_target()
    assert backend is not None

    session = backend.start_session(
        SlamBackendConfig(),
        SlamOutputPolicy(),
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
    assert update0.pose is not None
    assert update0.pointmap is not None
    assert update1.num_sparse_points >= update0.num_sparse_points
    assert update1.num_dense_points >= update0.num_dense_points
    assert update1.pose is not None
    assert artifacts.sparse_points_ply is not None
    assert artifacts.sparse_points_ply.path.exists()
    assert artifacts.dense_points_ply is not None
    assert artifacts.dense_points_ply.path.exists()
    assert timestamps_s[1] > timestamps_s[0]


def test_methods_package_exports_vista_backend_surfaces() -> None:
    backend_config = VistaSlamBackendConfig()
    backend = backend_config.setup_target()

    assert isinstance(backend, VistaSlamBackend)
    assert backend.method_id is MethodId.VISTA


def test_vista_session_extracts_live_pose_and_pointmap_from_upstream_view(tmp_path: Path) -> None:
    class FakeFlowTracker:
        def __init__(self) -> None:
            self.calls = 0

        def compute_disparity(self, image: np.ndarray, visualize: bool = False) -> bool:
            del image, visualize
            self.calls += 1
            return True

    class FakeSlam:
        def __init__(self) -> None:
            self.device = "cpu"
            self.step_calls: list[dict[str, object]] = []

        def step(self, value: dict[str, object]) -> None:
            self.step_calls.append(value)

        def get_view(self, view_index: int, **kwargs: object) -> object:
            del kwargs
            assert view_index == 0
            return SimpleNamespace(
                pose=np.array(
                    [
                        [1.0, 0.0, 0.0, 1.5],
                        [0.0, 1.0, 0.0, 0.0],
                        [0.0, 0.0, 1.0, 2.5],
                        [0.0, 0.0, 0.0, 1.0],
                    ],
                    dtype=np.float64,
                ),
                depth=np.array([[1.0, 0.0], [2.0, 3.0]], dtype=np.float32),
                intri=np.array(
                    [
                        [2.0, 0.0, 0.5],
                        [0.0, 4.0, 0.5],
                        [0.0, 0.0, 1.0],
                    ],
                    dtype=np.float64,
                ),
            )

        def get_pointmap_vis(self, view_index: int) -> tuple[np.ndarray, np.ndarray]:
            assert view_index == 0
            pointmap = np.array(
                [
                    [[0.0, 0.0, 1.0], [0.5, 0.0, 0.0]],
                    [[0.0, 0.5, 2.0], [0.5, 0.5, 3.0]],
                ],
                dtype=np.float32,
            )
            preview = np.zeros((2, 2, 3), dtype=np.uint8)
            return preview, pointmap

    session = VistaSlamSession(
        slam=FakeSlam(),
        flow_tracker=FakeFlowTracker(),
        artifact_root=tmp_path / "vista-stream",
        output_policy=SlamOutputPolicy(),
        console=Console(__name__).child("vista-test"),
    )

    update = session.step(FramePacket(seq=0, timestamp_ns=123, rgb=np.zeros((8, 8, 3), dtype=np.uint8)))

    assert update.pose is not None
    assert update.pose.tx == 1.5
    assert update.pose.tz == 2.5
    assert update.is_keyframe is True
    assert update.keyframe_index == 0
    assert update.pose_updated is True
    assert update.preview_rgb is not None
    assert update.preview_rgb.shape == (2, 2, 3)
    assert update.pointmap is not None
    assert update.pointmap.shape == (2, 2, 3)
    assert np.allclose(update.pointmap[..., 2], np.array([[1.0, 0.0], [2.0, 3.0]], dtype=np.float32))
    assert update.num_dense_points == 3


def test_vista_session_omits_dense_pointmap_when_policy_disables_it(tmp_path: Path) -> None:
    class FakeSlam:
        def get_view(self, *args: object, **kwargs: object) -> object:
            return SimpleNamespace(pose=np.eye(4), depth=np.ones((2, 2)), intri=np.eye(3))

        def get_pointmap_vis(self, view_index: int) -> tuple[np.ndarray, np.ndarray]:
            return np.zeros((2, 2, 3), dtype=np.uint8), np.zeros((2, 2, 3), dtype=np.float32)

        @property
        def device(self) -> str:
            return "cpu"

        def step(self, value: object) -> None:
            pass

    session = VistaSlamSession(
        slam=FakeSlam(),
        flow_tracker=SimpleNamespace(compute_disparity=lambda *args, **kwargs: True),
        artifact_root=tmp_path / "vista-stream",
        output_policy=SlamOutputPolicy(emit_dense_points=False),
        console=Console(__name__).child("vista-test"),
    )

    update = session.step(FramePacket(seq=0, timestamp_ns=123, rgb=np.zeros((8, 8, 3), dtype=np.uint8)))

    assert update.is_keyframe is True
    assert update.pointmap is None
    assert update.preview_rgb is not None


def test_vista_session_keyframe_gates_streaming_updates_before_step(tmp_path: Path) -> None:
    class FakeFlowTracker:
        def __init__(self) -> None:
            self._outcomes = iter([True, False, True])

        def compute_disparity(self, image: np.ndarray, visualize: bool = False) -> bool:
            del image, visualize
            return next(self._outcomes)

    class FakeSlam:
        def __init__(self) -> None:
            self.device = "cpu"
            self.step_calls: list[dict[str, object]] = []
            self.get_view_calls: list[int] = []
            self.get_pointmap_vis_calls: list[int] = []

        def step(self, value: dict[str, object]) -> None:
            self.step_calls.append(value)

        def get_view(self, view_index: int, **kwargs: object) -> object:
            del kwargs
            self.get_view_calls.append(view_index)
            return SimpleNamespace(
                pose=np.array(
                    [
                        [1.0, 0.0, 0.0, float(view_index)],
                        [0.0, 1.0, 0.0, 0.0],
                        [0.0, 0.0, 1.0, 0.0],
                        [0.0, 0.0, 0.0, 1.0],
                    ],
                    dtype=np.float64,
                ),
                depth=np.ones((2, 2), dtype=np.float32),
                intri=np.eye(3, dtype=np.float64),
            )

        def get_pointmap_vis(self, view_index: int) -> tuple[np.ndarray, np.ndarray]:
            self.get_pointmap_vis_calls.append(view_index)
            preview = np.zeros((2, 2, 3), dtype=np.uint8)
            pointmap = np.array(
                [
                    [[0.0, 0.0, 1.0], [0.0, 0.0, 2.0]],
                    [[0.0, 0.0, 3.0], [0.0, 0.0, 4.0]],
                ],
                dtype=np.float32,
            )
            return preview, pointmap

    slam = FakeSlam()
    session = VistaSlamSession(
        slam=slam,
        flow_tracker=FakeFlowTracker(),
        artifact_root=tmp_path / "vista-stream",
        output_policy=SlamOutputPolicy(),
        console=Console(__name__).child("vista-test"),
    )

    update0 = session.step(FramePacket(seq=0, timestamp_ns=100, rgb=np.zeros((8, 8, 3), dtype=np.uint8)))
    update1 = session.step(FramePacket(seq=1, timestamp_ns=200, rgb=np.zeros((8, 8, 3), dtype=np.uint8)))
    update2 = session.step(FramePacket(seq=2, timestamp_ns=300, rgb=np.zeros((8, 8, 3), dtype=np.uint8)))

    assert update0.is_keyframe is True
    assert update0.keyframe_index == 0
    assert update1.is_keyframe is False
    assert update1.keyframe_index is None
    assert update1.pose is None
    assert update1.pointmap is None
    assert update2.is_keyframe is True
    assert update2.keyframe_index == 1
    assert len(slam.step_calls) == 2
    assert slam.get_view_calls == [0, 1]
    assert slam.get_pointmap_vis_calls == [0, 1]


def test_vista_session_tolerates_unavailable_live_preview_until_pose_graph_populates(tmp_path: Path) -> None:
    class FakeFlowTracker:
        def compute_disparity(self, image: np.ndarray, visualize: bool = False) -> bool:
            del image, visualize
            return True

    class FakeSlam:
        def __init__(self) -> None:
            self.device = "cpu"

        def step(self, value: dict[str, object]) -> None:
            del value

        def get_view(self, view_index: int, **kwargs: object) -> object:
            del view_index, kwargs
            raise IndexError("pose graph not ready")

        def get_pointmap_vis(self, view_index: int) -> tuple[np.ndarray, np.ndarray]:
            del view_index
            return np.zeros((2, 2, 3), dtype=np.uint8), np.zeros((2, 2, 3), dtype=np.float32)

    session = VistaSlamSession(
        slam=FakeSlam(),
        flow_tracker=FakeFlowTracker(),
        artifact_root=tmp_path / "vista-stream",
        output_policy=SlamOutputPolicy(),
        console=Console(__name__).child("vista-test"),
    )

    update = session.step(FramePacket(seq=0, timestamp_ns=123, rgb=np.zeros((8, 8, 3), dtype=np.uint8)))

    assert update.pose is None
    assert update.pointmap is None
    assert update.num_dense_points == 0
    assert update.is_keyframe is True
    assert update.keyframe_index == 0
