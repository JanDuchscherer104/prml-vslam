"""Tests for the repository-local method mocks."""

from __future__ import annotations

import pickle
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from prml_vslam.interfaces import CameraIntrinsics, FramePacket, FrameTransform
from prml_vslam.methods import MethodId, MockSlamBackendConfig, VistaSlamBackend, VistaSlamBackendConfig
from prml_vslam.methods.contracts import SlamBackendConfig, SlamOutputPolicy
from prml_vslam.methods.protocols import ProcessStreamingSlamBackend
from prml_vslam.pipeline import SequenceManifest
from prml_vslam.utils import Console


def _install_fake_torch(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeTensor:
        def __init__(self, value: np.ndarray) -> None:
            self._value = np.asarray(value)

        @property
        def shape(self) -> tuple[int, ...]:
            return self._value.shape

        def permute(self, *axes: int) -> FakeTensor:
            self._value = np.transpose(self._value, axes)
            return self

        def float(self) -> FakeTensor:
            self._value = self._value.astype(np.float32)
            return self

        def unsqueeze(self, axis: int) -> FakeTensor:
            self._value = np.expand_dims(self._value, axis)
            return self

        def to(self, device: str) -> FakeTensor:
            del device
            return self

        def __truediv__(self, scalar: float) -> FakeTensor:
            self._value = self._value / scalar
            return self

    monkeypatch.setitem(
        sys.modules,
        "torch",
        SimpleNamespace(
            from_numpy=lambda value: FakeTensor(np.asarray(value)),
            tensor=lambda value: FakeTensor(np.asarray(value)),
            manual_seed=lambda seed: None,
        ),
    )


def test_mock_slam_backend_materializes_placeholder_outputs_without_reference(tmp_path: Path) -> None:
    from prml_vslam.benchmark import ReferenceSource

    backend = MockSlamBackendConfig().setup_target()
    assert backend is not None
    sequence = SequenceManifest(sequence_id="test-seq")
    artifacts = backend.run_sequence(
        sequence=sequence,
        benchmark_inputs=None,
        baseline_source=ReferenceSource.GROUND_TRUTH,
        backend_config=VistaSlamBackendConfig(),
        output_policy=SlamOutputPolicy(),
        artifact_root=tmp_path / "mock-run",
    )

    assert artifacts.trajectory_tum.path.exists()
    assert artifacts.trajectory_tum.kind == "tum"
    assert artifacts.sparse_points_ply is not None
    assert artifacts.sparse_points_ply.path.exists()


def test_mock_slam_backend_config_defaults_to_mock_method() -> None:
    assert MockSlamBackendConfig().method_id is MethodId.MOCK


def test_mock_slam_backend_runs_sequence_manifest_offline(tmp_path: Path) -> None:
    from prml_vslam.benchmark import ReferenceSource

    backend = MockSlamBackendConfig().setup_target()
    assert backend is not None
    sequence = SequenceManifest(
        sequence_id="advio-15",
        rgb_dir=tmp_path / "frames",
        timestamps_path=tmp_path / "timestamps.json",
    )
    # reference_tum_path was removed from SequenceManifest in main.
    # The mock now just emits a placeholder update.
    artifacts = backend.run_sequence(
        sequence=sequence,
        benchmark_inputs=None,
        baseline_source=ReferenceSource.GROUND_TRUTH,
        backend_config=VistaSlamBackendConfig(),
        output_policy=SlamOutputPolicy(),
        artifact_root=tmp_path / "mock-run",
    )

    assert artifacts.trajectory_tum.path.exists()


def test_mock_slam_session_emits_incremental_updates_and_artifacts(tmp_path: Path) -> None:
    session = (
        MockSlamBackendConfig()
        .setup_target()
        .start_session(
            backend_config=VistaSlamBackendConfig(),
            output_policy=SlamOutputPolicy(),
            artifact_root=tmp_path / "mock-stream",
        )
    )

    session.step(FramePacket(seq=0, timestamp_ns=0, rgb=np.zeros((8, 8, 3), dtype=np.uint8)))
    session.step(
        FramePacket(
            seq=1,
            timestamp_ns=100_000_000,
            rgb=np.zeros((8, 8, 3), dtype=np.uint8),
            pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=0.0, tz=0.0),
        )
    )
    updates = session.try_get_updates()

    assert len(updates) == 2
    assert updates[0].is_keyframe is True
    assert updates[1].pose is not None
    assert updates[1].pose.tx == 1.0

    artifacts = session.close()
    assert artifacts.trajectory_tum.path.exists()


def test_methods_package_exports_vista_backend_surfaces() -> None:
    assert VistaSlamBackend is not None


def test_vista_backend_exposes_picklable_streaming_session_factory(tmp_path: Path) -> None:
    backend = VistaSlamBackendConfig().setup_target()
    assert backend is not None

    factory = backend.streaming_session_factory(
        SlamBackendConfig(),
        SlamOutputPolicy(),
        tmp_path / "vista-stream",
    )

    assert isinstance(backend, ProcessStreamingSlamBackend)
    assert callable(factory)
    pickle.dumps(factory)
    assert VistaSlamBackendConfig is not None


def test_vista_session_extracts_live_pose_and_pointmap_from_upstream_view(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from prml_vslam.methods.vista.adapter import VistaSlamSession

    _install_fake_torch(monkeypatch)

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
                depth=np.ones((224, 224), dtype=np.float32),
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
            pointmap = np.zeros((224, 224, 3), dtype=np.float32)
            pointmap[:2, :2, :] = np.array(
                [
                    [[0.0, 0.0, 1.0], [0.5, 0.0, 0.0]],
                    [[0.0, 0.5, 2.0], [0.5, 0.5, 3.0]],
                ],
                dtype=np.float32,
            )
            preview = np.zeros((224, 224, 3), dtype=np.uint8)
            return preview, pointmap

    session = VistaSlamSession(
        slam=FakeSlam(),
        flow_tracker=FakeFlowTracker(),
        artifact_root=tmp_path / "vista-stream",
        output_policy=SlamOutputPolicy(),
        console=Console(__name__).child("vista-test"),
    )

    session.step(FramePacket(seq=0, timestamp_ns=123, rgb=np.zeros((8, 8, 3), dtype=np.uint8)))
    updates = session.try_get_updates()
    assert len(updates) == 1
    update = updates[0]

    assert update.pose is not None
    assert update.pose.tx == 1.5
    assert update.pose.tz == 2.5
    assert update.is_keyframe is True
    assert update.keyframe_index == 0
    assert update.pose_updated is True
    assert update.camera_intrinsics == CameraIntrinsics(
        fx=2.0,
        fy=4.0,
        cx=0.5,
        cy=0.5,
        width_px=224,
        height_px=224,
    )
    assert update.image_rgb is not None
    assert update.image_rgb.shape == (224, 224, 3)
    assert update.depth_map is not None
    assert update.depth_map.shape == (224, 224)
    assert update.preview_rgb is not None
    assert update.preview_rgb.shape == (224, 224, 3)
    assert update.pointmap is not None
    assert update.pointmap.shape == (224, 224, 3)
    assert np.allclose(update.pointmap[:2, :2, 2], np.array([[1.0, 0.0], [2.0, 3.0]], dtype=np.float32))
    assert update.num_dense_points == 3


def test_mast3r_session_starts_backend_after_intrinsics_are_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from prml_vslam.methods.mast3r.adapter import Mast3rSlamSession

    class FakeTensor:
        def __init__(self, value: np.ndarray) -> None:
            self._value = np.asarray(value)

        def to(self, *_args, **_kwargs) -> FakeTensor:
            return self

        def detach(self) -> FakeTensor:
            return self

        def cpu(self) -> FakeTensor:
            return self

        def numpy(self) -> np.ndarray:
            return self._value

    class FakeSharedKeyframes:
        def __init__(self, *_args, **_kwargs) -> None:
            self.frames = []
            self.intrinsics: FakeTensor | None = None

        def append(self, frame) -> None:
            self.frames.append(frame)

        def set_intrinsics(self, intrinsics: FakeTensor) -> None:
            self.intrinsics = intrinsics

        def __len__(self) -> int:
            return len(self.frames)

    class FakeSharedStates:
        def __init__(self, *_args, **_kwargs) -> None:
            self.mode = FakeMode.INIT
            self.frame = None

        def get_mode(self) -> str:
            return self.mode

        def queue_global_optimization(self, _index: int) -> None:
            return

        def set_mode(self, mode: str) -> None:
            self.mode = mode

        def set_frame(self, frame) -> None:
            self.frame = frame

    class FakeFrameTracker:
        pass

    class FakeFrame:
        def __init__(self, T_WC: str) -> None:
            self.T_WC = T_WC

        def update_pointmap(self, _X: FakeTensor, _C: FakeTensor) -> None:
            return

    class FakeMode:
        INIT = "init"
        TRACKING = "tracking"
        RELOC = "reloc"

    class FakeIntrinsics:
        @staticmethod
        def from_calib(*_args, **_kwargs) -> SimpleNamespace:
            return SimpleNamespace(K_frame=np.eye(3, dtype=np.float32))

    monkeypatch.setitem(sys.modules, "mast3r_slam.config", SimpleNamespace(config={"use_calib": True}))
    monkeypatch.setitem(sys.modules, "mast3r_slam.dataloader", SimpleNamespace(Intrinsics=FakeIntrinsics))
    monkeypatch.setitem(
        sys.modules,
        "torch",
        SimpleNamespace(float32="float32", from_numpy=lambda value: FakeTensor(np.asarray(value))),
    )

    session = Mast3rSlamSession.__new__(Mast3rSlamSession)
    session._cfg = SimpleNamespace(c_conf_threshold=1.5)
    session._output_policy = SlamOutputPolicy()
    session._artifact_root = Path("/tmp/mast3r-test")
    session._console = SimpleNamespace(info=lambda *_args, **_kwargs: None)
    session._device = "cpu"
    session._img_size = 512
    session._model = object()
    session._keyframes = None
    session._states = None
    session._tracker = None
    session._manager = None
    session._K = None
    session._h = 0
    session._w = 0
    session._source_frame_count = 0
    session._accepted_keyframe_count = 0
    session._num_dense_points = 0
    session._timestamps_s = []
    session._pending_updates = []
    session._backend_error = None
    session._backend_thread = None
    session._backend_stop = SimpleNamespace(clear=lambda: None)
    session._resize_img = lambda _img, _size: {"img": np.zeros((1, 3, 4, 4), dtype=np.float32)}
    session._SharedKeyframes = FakeSharedKeyframes
    session._SharedStates = FakeSharedStates
    session._FrameTracker = FakeFrameTracker
    session._Mode = FakeMode
    session._create_frame = lambda _idx, _img, T_WC, **_kwargs: FakeFrame(T_WC)
    session._mast3r_inference_mono = lambda _model, _frame: (
        FakeTensor(np.zeros((4, 3), dtype=np.float32)),
        FakeTensor(np.ones((4,), dtype=np.float32)),
    )
    session._lietorch = SimpleNamespace(Sim3=SimpleNamespace(Identity=lambda *_args, **_kwargs: "identity"))
    session._emit_update = lambda **_kwargs: None
    session._raise_if_backend_failed = lambda: None

    observed_k_ready: list[bool] = []

    def _start_backend_thread() -> None:
        observed_k_ready.append(session._K is not None)
        session._backend_thread = SimpleNamespace(is_alive=lambda: False)

    session._start_backend_thread = _start_backend_thread

    session.step(
        FramePacket(
            seq=0,
            timestamp_ns=123,
            rgb=np.zeros((4, 4, 3), dtype=np.uint8),
            intrinsics=CameraIntrinsics(
                fx=100.0,
                fy=100.0,
                cx=2.0,
                cy=2.0,
                width_px=4,
                height_px=4,
            ),
        )
    )

    assert observed_k_ready == [True]
    assert session._K is not None
    assert session._keyframes is not None
    assert session._keyframes.intrinsics is not None


def test_mast3r_session_extracts_camera_local_pointmap() -> None:
    from prml_vslam.methods.mast3r.adapter import Mast3rSlamSession

    class FakeTensor:
        def __init__(self, value: np.ndarray) -> None:
            self._value = np.asarray(value)

        def detach(self) -> FakeTensor:
            return self

        def cpu(self) -> FakeTensor:
            return self

        def numpy(self) -> np.ndarray:
            return self._value

        def flatten(self) -> FakeTensor:
            return FakeTensor(self._value.flatten())

        def tolist(self) -> list[int]:
            return self._value.tolist()

    class FakeTransform:
        def act(self, value: FakeTensor) -> FakeTensor:
            return FakeTensor(value.numpy() + np.array([10.0, 20.0, 30.0], dtype=np.float32))

    session = Mast3rSlamSession.__new__(Mast3rSlamSession)
    session._cfg = SimpleNamespace(c_conf_threshold=0.5)

    x_canon = np.array(
        [
            [0.0, 0.0, 1.0],
            [1.0, 0.0, 2.0],
            [0.0, 1.0, 3.0],
            [1.0, 1.0, 4.0],
        ],
        dtype=np.float32,
    )
    fake_frame = SimpleNamespace(
        X_canon=FakeTensor(x_canon),
        get_average_conf=lambda: FakeTensor(np.array([1.0, 0.25, 0.75, 1.0], dtype=np.float32)),
        img_shape=FakeTensor(np.array([2, 2], dtype=np.int64)),
        uimg=FakeTensor(np.zeros((2, 2, 3), dtype=np.float32)),
        T_WC=FakeTransform(),
    )

    pointmap, _preview_rgb, valid = session._extract_keyframe_visuals(fake_frame)

    assert valid == 3
    assert pointmap is not None
    assert pointmap.shape == (2, 2, 3)
    np.testing.assert_allclose(pointmap.reshape(-1, 3), x_canon)


def test_vista_session_uses_injected_frame_preprocessor_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from prml_vslam.methods.vista.adapter import VistaSlamSession, _PreparedVistaFrame

    _install_fake_torch(monkeypatch)

    class FakeSlam:
        def __init__(self) -> None:
            self.device = "cpu"
            self.step_calls: list[dict[str, object]] = []

        def step(self, value: dict[str, object]) -> None:
            self.step_calls.append(value)

        def get_view(self, view_index: int, **kwargs: object) -> object:
            del view_index, kwargs
            return SimpleNamespace(
                pose=np.eye(4, dtype=np.float64),
                depth=np.ones((4, 6), dtype=np.float32),
                intri=np.eye(3, dtype=np.float64),
            )

        def get_pointmap_vis(self, view_index: int) -> tuple[np.ndarray, np.ndarray]:
            del view_index
            return np.zeros((4, 6, 3), dtype=np.uint8), np.ones((4, 6, 3), dtype=np.float32)

    class FakePreprocessor:
        def __init__(self) -> None:
            self.calls: list[tuple[tuple[int, ...], str]] = []

        def prepare(self, rgb_image: np.ndarray, *, view_name: str) -> _PreparedVistaFrame:
            self.calls.append((rgb_image.shape, view_name))
            torch = sys.modules["torch"]
            image_rgb = np.full((4, 6, 3), fill_value=7, dtype=np.uint8)
            gray_u8 = np.full((4, 6), fill_value=11, dtype=np.uint8)
            rgb_tensor = torch.from_numpy(image_rgb).permute(2, 0, 1).float() / 255.0
            return _PreparedVistaFrame(image_rgb=image_rgb, gray_u8=gray_u8, rgb_tensor=rgb_tensor)

    fake_preprocessor = FakePreprocessor()
    slam = FakeSlam()
    session = VistaSlamSession(
        slam=slam,
        flow_tracker=SimpleNamespace(compute_disparity=lambda *args, **kwargs: True),
        frame_preprocessor=fake_preprocessor,
        artifact_root=tmp_path / "vista-stream",
        output_policy=SlamOutputPolicy(),
        console=Console(__name__).child("vista-test"),
    )

    session.step(FramePacket(seq=0, timestamp_ns=123, rgb=np.zeros((8, 8, 3), dtype=np.uint8)))
    updates = session.try_get_updates()
    assert len(updates) == 1
    update = updates[0]

    assert fake_preprocessor.calls == [((8, 8, 3), "frame_000000")]
    assert len(slam.step_calls) == 1
    assert slam.step_calls[0]["shape"].shape == (1, 2)
    assert update.image_rgb is not None
    assert update.image_rgb.shape == (4, 6, 3)
    assert update.depth_map is not None
    assert update.depth_map.shape == (4, 6)


def test_vista_session_projects_near_orthonormal_live_pose_before_quaternion_conversion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from prml_vslam.methods.vista.adapter import VistaSlamSession

    _install_fake_torch(monkeypatch)

    class FakeSlam:
        def __init__(self) -> None:
            self.device = "cpu"

        def step(self, value: dict[str, object]) -> None:
            del value

        def get_view(self, view_index: int, **kwargs: object) -> object:
            del view_index, kwargs
            pose = np.eye(4, dtype=np.float64)
            pose[:3, :3] = np.array(
                [
                    [1.0 + 2e-6, 1e-6, 0.0],
                    [-1e-6, 1.0 - 1e-6, 0.0],
                    [0.0, 0.0, 1.0 + 1e-6],
                ],
                dtype=np.float64,
            )
            pose[:3, 3] = np.array([1.0, 2.0, 3.0], dtype=np.float64)
            return SimpleNamespace(pose=pose, depth=np.ones((2, 2), dtype=np.float32), intri=np.eye(3))

        def get_pointmap_vis(self, view_index: int) -> tuple[np.ndarray, np.ndarray]:
            del view_index
            return np.zeros((2, 2, 3), dtype=np.uint8), np.ones((2, 2, 3), dtype=np.float32)

    session = VistaSlamSession(
        slam=FakeSlam(),
        flow_tracker=SimpleNamespace(compute_disparity=lambda *args, **kwargs: True),
        artifact_root=tmp_path / "vista-stream",
        output_policy=SlamOutputPolicy(),
        console=Console(__name__).child("vista-test"),
    )

    session.step(FramePacket(seq=0, timestamp_ns=123, rgb=np.zeros((8, 8, 3), dtype=np.uint8)))
    updates = session.try_get_updates()
    assert len(updates) == 1
    update = updates[0]

    assert update.pose is not None
    assert np.isclose(np.linalg.norm(update.pose.quaternion_xyzw()), 1.0)
    assert update.pose.translation_xyz().tolist() == [1.0, 2.0, 3.0]


def test_vista_session_omits_dense_pointmap_when_policy_disables_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from prml_vslam.methods.vista.adapter import VistaSlamSession

    _install_fake_torch(monkeypatch)

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

    session.step(FramePacket(seq=0, timestamp_ns=123, rgb=np.zeros((8, 8, 3), dtype=np.uint8)))
    updates = session.try_get_updates()
    assert len(updates) == 1
    update = updates[0]

    assert update.is_keyframe is True
    assert update.pointmap is None
    assert update.preview_rgb is not None


def test_vista_session_keyframe_gates_streaming_updates_before_step(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from prml_vslam.methods.vista.adapter import VistaSlamSession

    _install_fake_torch(monkeypatch)

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

    session.step(FramePacket(seq=0, timestamp_ns=100, rgb=np.zeros((8, 8, 3), dtype=np.uint8)))
    session.step(FramePacket(seq=1, timestamp_ns=200, rgb=np.zeros((8, 8, 3), dtype=np.uint8)))
    session.step(FramePacket(seq=2, timestamp_ns=300, rgb=np.zeros((8, 8, 3), dtype=np.uint8)))
    updates = session.try_get_updates()

    assert len(updates) == 3
    update0, update1, update2 = updates

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


def test_vista_session_tolerates_unavailable_live_preview_until_pose_graph_populates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from prml_vslam.methods.vista.adapter import VistaSlamSession

    _install_fake_torch(monkeypatch)

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

    session.step(FramePacket(seq=0, timestamp_ns=123, rgb=np.zeros((8, 8, 3), dtype=np.uint8)))
    updates = session.try_get_updates()
    assert len(updates) == 1
    update = updates[0]

    assert update.pose is None
    assert update.pointmap is None
    assert update.num_dense_points == 0
    assert update.is_keyframe is True
    assert update.keyframe_index == 0


def test_vista_artifact_builder_projects_near_orthonormal_trajectory_rotations(tmp_path: Path) -> None:
    from prml_vslam.methods.vista.adapter import _build_artifacts

    native_output_dir = tmp_path / "native"
    native_output_dir.mkdir(parents=True, exist_ok=True)
    trajectory = np.repeat(np.eye(4, dtype=np.float64)[None, :, :], repeats=2, axis=0)
    trajectory[1, :3, :3] = np.array(
        [
            [1.0 + 3e-6, 0.0, 0.0],
            [0.0, 1.0 - 2e-6, 1e-6],
            [0.0, -1e-6, 1.0 + 1e-6],
        ],
        dtype=np.float64,
    )
    trajectory[1, :3, 3] = np.array([0.5, 0.0, 0.0], dtype=np.float64)
    np.save(native_output_dir / "trajectory.npy", trajectory)

    artifacts = _build_artifacts(
        native_output_dir=native_output_dir,
        artifact_root=tmp_path / "artifacts",
        output_policy=SlamOutputPolicy(),
    )

    assert artifacts.trajectory_tum.path.exists()


def test_vista_artifact_builder_aliases_sparse_and_dense_to_one_canonical_cloud(tmp_path: Path) -> None:
    from prml_vslam.methods.vista.adapter import _build_artifacts

    native_output_dir = tmp_path / "native"
    native_output_dir.mkdir(parents=True, exist_ok=True)
    np.save(native_output_dir / "trajectory.npy", np.eye(4, dtype=np.float64)[None, :, :])
    (native_output_dir / "rerun_recording.rrd").write_bytes(b"native-rerun")
    (native_output_dir / "pointcloud.ply").write_text(
        "\n".join(
            [
                "ply",
                "format ascii 1.0",
                "element vertex 1",
                "property float x",
                "property float y",
                "property float z",
                "end_header",
                "0 0 1",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    artifacts = _build_artifacts(
        native_output_dir=native_output_dir,
        artifact_root=tmp_path / "artifacts",
        output_policy=SlamOutputPolicy(),
    )

    assert artifacts.sparse_points_ply is not None
    assert artifacts.dense_points_ply is not None
    assert artifacts.sparse_points_ply.path == artifacts.dense_points_ply.path
    assert artifacts.sparse_points_ply.path.name == "point_cloud.ply"
    assert not hasattr(artifacts, "native_rerun_rrd")
    assert not hasattr(artifacts, "native_output_dir")
    assert "rerun_recording.rrd" not in artifacts.extras


def test_vista_pose_normalization_rejects_clearly_invalid_rotations() -> None:
    from prml_vslam.methods.vista.adapter import _frame_transform_from_vista_pose

    pose = np.eye(4, dtype=np.float64)
    pose[:3, :3] = np.array(
        [
            [2.0, 0.0, 0.0],
            [0.0, 0.5, 0.0],
            [0.0, 0.0, 0.25],
        ],
        dtype=np.float64,
    )

    with pytest.raises(ValueError, match="too far from SO\\(3\\)"):
        _frame_transform_from_vista_pose(pose)
