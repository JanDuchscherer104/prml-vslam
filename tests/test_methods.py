"""Tests for the method wrappers."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from pydantic import ValidationError

from prml_vslam.interfaces import CameraIntrinsics, CameraIntrinsicsSeries, Observation, ObservationProvenance
from prml_vslam.interfaces.artifacts import artifact_ref
from prml_vslam.methods import VistaSlamBackend
from prml_vslam.methods.stage.backend_config import (
    Mast3rSlamBackendConfig,
    SlamBackendConfig,
    SlamOutputPolicy,
    VistaSlamBackendConfig,
)
from prml_vslam.methods.stage.backend_config import MethodId as DomainMethodId
from prml_vslam.sources.contracts import (
    ReferenceSource,
    SequenceManifest,
)
from prml_vslam.utils import Console
from prml_vslam.utils.geometry import (
    load_point_cloud_ply_with_colors,
    load_tum_trajectory,
    write_point_cloud_ply,
)
from prml_vslam.utils.serialization import stable_hash


def test_mast3r_backend_module_imports_after_refactor() -> None:
    module = importlib.import_module("prml_vslam.methods.mast3r")

    assert module.Mast3rSlamBackend.method_id is DomainMethodId.MAST3R
    assert module.__all__ == ["Mast3rSlamBackend"]


def test_mast3r_backend_config_supports_current_runtime_contracts() -> None:
    config = Mast3rSlamBackendConfig()

    assert config.supports_offline is True
    assert config.supports_streaming is True
    assert config.supports_dense_points is True
    assert config.supports_live_preview is True
    assert config.supports_trajectory_benchmark is True
    assert config.supports_native_visualization is False
    assert config.default_resources == {"CPU": 2.0, "GPU": 1.0}
    assert config.setup_target().method_id is DomainMethodId.MAST3R


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

        def detach(self) -> FakeTensor:
            return self

        def cpu(self) -> FakeTensor:
            return self

        def numpy(self) -> np.ndarray:
            return np.asarray(self._value)

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


def _make_fake_frame_preprocessor(
    *,
    image_rgb: np.ndarray | None = None,
    gray_u8: np.ndarray | None = None,
):
    from prml_vslam.methods.vista.preprocess import PreparedVistaFrame

    resolved_image_rgb = (
        np.zeros((224, 224, 3), dtype=np.uint8) if image_rgb is None else np.asarray(image_rgb, dtype=np.uint8)
    )
    resolved_gray_u8 = (
        np.zeros(resolved_image_rgb.shape[:2], dtype=np.uint8)
        if gray_u8 is None
        else np.asarray(gray_u8, dtype=np.uint8)
    )

    class FakePreprocessor:
        def __init__(self) -> None:
            self.calls: list[tuple[tuple[int, ...], str]] = []

        def prepare(self, rgb_image: np.ndarray, *, view_name: str) -> PreparedVistaFrame:
            self.calls.append((rgb_image.shape, view_name))
            torch = sys.modules["torch"]
            rgb_tensor = torch.from_numpy(resolved_image_rgb.copy()).permute(2, 0, 1).float() / 255.0
            return PreparedVistaFrame(
                image_rgb=resolved_image_rgb.copy(),
                gray_u8=resolved_gray_u8.copy(),
                rgb_tensor=rgb_tensor,
            )

    return FakePreprocessor()


def test_methods_package_exports_vista_backend_surfaces() -> None:
    assert VistaSlamBackend is not None


def test_vista_backend_starts_direct_streaming_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import prml_vslam.methods.vista.adapter as vista_adapter

    backend = VistaSlamBackendConfig().setup_target()
    assert backend is not None
    monkeypatch.setattr(
        vista_adapter,
        "create_vista_runtime",
        lambda **_: SimpleNamespace(
            step=lambda *_args, **_kwargs: None,
            drain_updates=lambda: [],
            finish=lambda: None,
        ),
    )

    backend.start_streaming(
        sequence_manifest=SequenceManifest(sequence_id="vista-stream"),
        benchmark_inputs=None,
        baseline_source=ReferenceSource.GROUND_TRUTH,
        backend_config=SlamBackendConfig(),
        output_policy=SlamOutputPolicy(),
        artifact_root=tmp_path / "vista-stream",
    )

    assert callable(backend.step_streaming)
    assert callable(backend.drain_streaming_updates)
    assert callable(backend.finish_streaming)


def test_vista_backend_builds_binary_vocab_cache_once(tmp_path: Path) -> None:
    from prml_vslam.methods.vista.runtime import resolve_vocab_path

    pretrains_dir = tmp_path / "external" / "vista-slam" / "pretrains"
    pretrains_dir.mkdir(parents=True)
    vocab_path = pretrains_dir / "ORBvoc.txt"
    vocab_path.write_text("stub vocab")
    calls: list[tuple[str, object]] = []
    cache_path = tmp_path / ".artifacts" / "cache" / "vista" / "ORBvoc.dbow3.bin"

    class FakeVocabulary:
        def load(self, path: str) -> None:
            calls.append(("load", path))

        def save(self, path: str, binary_compressed: bool = True) -> None:
            calls.append(("save", path, binary_compressed))
            Path(path).write_text("binary vocab")

    resolved = resolve_vocab_path(
        dbow=SimpleNamespace(Vocabulary=FakeVocabulary),
        vocab_path=vocab_path,
        vocab_cache_path=cache_path,
        console=Console(__name__).child("vista-test"),
    )

    assert resolved == cache_path
    assert resolved.read_text() == "binary vocab"
    assert calls == [
        ("load", str(vocab_path)),
        ("save", str(cache_path.with_suffix(".bin.tmp")), True),
    ]


def test_vista_backend_reuses_existing_binary_vocab_cache(tmp_path: Path) -> None:
    from prml_vslam.methods.vista.runtime import resolve_vocab_path

    pretrains_dir = tmp_path / "external" / "vista-slam" / "pretrains"
    pretrains_dir.mkdir(parents=True)
    (pretrains_dir / "ORBvoc.txt").write_text("stub vocab")
    cache_path = tmp_path / ".artifacts" / "cache" / "vista" / "ORBvoc.dbow3.bin"
    cache_path.parent.mkdir(parents=True)
    cache_path.write_text("cached")

    class ExplodingVocabulary:
        def __init__(self) -> None:
            raise AssertionError("existing vocab cache should prevent DBoW3 vocabulary rebuild")

    resolved = resolve_vocab_path(
        dbow=SimpleNamespace(Vocabulary=ExplodingVocabulary),
        vocab_path=pretrains_dir / "ORBvoc.txt",
        vocab_cache_path=cache_path,
        console=Console(__name__).child("vista-test"),
    )

    assert resolved == cache_path


def test_upstream_vista_frame_preprocessor_uses_crop_resize_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from prml_vslam.methods.vista.preprocess import UpstreamVistaFramePreprocessor

    _install_fake_torch(monkeypatch)
    calls: list[tuple[tuple[int, ...], tuple[int, int], int, int, str | None]] = []
    processed_image = np.full((6, 4, 3), fill_value=23, dtype=np.uint8)

    class FakeDataset:
        resolution = (224, 224)

        def _crop_resize_if_necessary_image_only(
            self,
            image: np.ndarray,
            resolution: tuple[int, int],
            *,
            h_edge: int = 0,
            w_edge: int = 0,
            rng: np.random.Generator | None = None,
            info: str | None = None,
        ) -> np.ndarray:
            del rng
            calls.append((image.shape, resolution, h_edge, w_edge, info))
            return processed_image

        def ImgGray(self, image: np.ndarray) -> np.ndarray:
            assert np.array_equal(np.asarray(image), processed_image)
            return np.ones((1, 6, 4), dtype=np.float32)

        def ImgNorm(self, image: np.ndarray):
            assert np.array_equal(np.asarray(image), processed_image)
            torch = sys.modules["torch"]
            return torch.from_numpy(np.asarray(image)).permute(2, 0, 1).float() / 255.0

    preprocessor = UpstreamVistaFramePreprocessor(image_dataset=FakeDataset())
    prepared = preprocessor.prepare(np.zeros((12, 8, 3), dtype=np.uint8), view_name="portrait_frame")

    assert calls == [((12, 8, 3), (224, 224), 10, 10, "portrait_frame")]
    assert prepared.image_rgb.shape == (6, 4, 3)
    assert prepared.gray_u8.shape == (6, 4)
    assert prepared.rgb_tensor.shape == (3, 6, 4)


def test_vista_session_extracts_live_pose_and_pointmap_from_upstream_view(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from prml_vslam.methods.vista.session import VistaSlamRuntime

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

    session = VistaSlamRuntime(
        slam=FakeSlam(),
        flow_tracker=FakeFlowTracker(),
        frame_preprocessor=_make_fake_frame_preprocessor(),
        artifact_root=tmp_path / "vista-stream",
        output_policy=SlamOutputPolicy(),
        console=Console(__name__).child("vista-test"),
    )

    session.step(
        Observation(
            seq=0,
            timestamp_ns=123,
            rgb=np.zeros((8, 8, 3), dtype=np.uint8),
            provenance=ObservationProvenance(source_id="test"),
        )
    )
    updates = session.drain_updates()
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
    from prml_vslam.methods.mast3r.adapter import _Mast3rSlamSession

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
        def __init__(self, *_args, **_kwargs) -> None:
            return

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

    session = _Mast3rSlamSession.__new__(_Mast3rSlamSession)
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
    session._torch = SimpleNamespace(float32="float32", from_numpy=lambda value: FakeTensor(np.asarray(value)))
    session._mast3r_cfg = {"use_calib": True}
    session._h = 0
    session._w = 0
    session._source_frame_count = 0
    session._accepted_keyframe_count = 0
    session._num_dense_points = 0
    session._timestamps_s = []
    session._pending_updates = []
    session._backend_error = None
    session._backend_thread = None
    session._resize_img = lambda _img, _size: {"img": np.zeros((1, 3, 4, 4), dtype=np.float32)}
    session._SharedKeyframes = FakeSharedKeyframes
    session._SharedStates = FakeSharedStates
    session._FrameTracker = FakeFrameTracker
    session._Intrinsics = FakeIntrinsics
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
        Observation(
            seq=0,
            timestamp_ns=123,
            provenance=ObservationProvenance(source_id="test"),
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
    from prml_vslam.methods.mast3r.adapter import _Mast3rSlamSession

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

    session = _Mast3rSlamSession.__new__(_Mast3rSlamSession)
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


def test_mast3r_preview_normalization_accepts_batched_chw_float() -> None:
    from prml_vslam.methods.mast3r.adapter import _normalize_preview_rgb

    class FakeTensor:
        def __init__(self, value: np.ndarray) -> None:
            self._value = np.asarray(value)

        def detach(self) -> FakeTensor:
            return self

        def cpu(self) -> FakeTensor:
            return self

        def numpy(self) -> np.ndarray:
            return self._value

    payload = FakeTensor(
        np.array(
            [
                [
                    [[0.0, 0.5], [1.0, 1.0]],
                    [[0.25, 0.5], [0.75, 1.0]],
                    [[1.0, 0.0], [0.5, 0.25]],
                ]
            ],
            dtype=np.float32,
        )
    )

    preview = _normalize_preview_rgb(payload)

    assert preview.shape == (2, 2, 3)
    assert preview.dtype == np.uint8
    assert preview[0, 1].tolist() == [127, 127, 0]
    assert preview[1, 0].tolist() == [255, 191, 127]


def test_mast3r_preview_normalization_rejects_non_rgb_payload() -> None:
    from prml_vslam.methods.mast3r.adapter import _normalize_preview_rgb

    with pytest.raises(ValueError, match="3 channels"):
        _normalize_preview_rgb(np.zeros((2, 2, 4), dtype=np.uint8))


def test_mast3r_artifact_builder_preserves_ply_colors_and_dense_only(tmp_path: Path) -> None:
    from prml_vslam.methods.mast3r.adapter import _build_artifacts

    native_output_dir = tmp_path / "native"
    artifact_root = tmp_path / "run"
    native_output_dir.mkdir(parents=True)
    traj_native = native_output_dir / "mast3r.txt"
    traj_native.write_text("0 0 0 0 0 0 0 1\n", encoding="utf-8")
    ply_native = write_point_cloud_ply(
        native_output_dir / "mast3r.ply",
        np.asarray([[0.0, 0.0, 1.0], [1.0, 0.0, 2.0]], dtype=np.float64),
        colors_rgb=np.asarray([[255, 0, 0], [0, 255, 128]], dtype=np.uint8),
    )

    artifacts = _build_artifacts(
        native_output_dir=native_output_dir,
        artifact_root=artifact_root,
        output_policy=SlamOutputPolicy(emit_dense_points=True, emit_sparse_points=True),
        traj_native=traj_native,
        ply_native=ply_native,
    )

    assert artifacts.sparse_points_ply is None
    assert artifacts.dense_points_ply is not None
    _, colors = load_point_cloud_ply_with_colors(artifacts.dense_points_ply.path)
    assert colors is not None
    np.testing.assert_allclose(
        colors,
        np.asarray([[1.0, 0.0, 0.0], [0.0, 1.0, 128.0 / 255.0]], dtype=np.float64),
        atol=1.0 / 255.0,
    )


def test_mast3r_backend_streaming_lifecycle_uses_backend_owned_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import prml_vslam.methods.mast3r.adapter as mast3r_adapter
    from prml_vslam.methods.contracts import SlamArtifacts, SlamUpdate

    class FakeSession:
        instances: list[FakeSession] = []

        def __init__(self, *, artifact_root: Path, **_kwargs) -> None:
            self.artifact_root = artifact_root
            self.frames: list[Observation] = []
            self.closed = False
            FakeSession.instances.append(self)

        def step(self, frame: Observation) -> None:
            self.frames.append(frame)

        def try_get_updates(self) -> list[SlamUpdate]:
            return [SlamUpdate(seq=0, timestamp_ns=1, is_keyframe=True)]

        def close(self) -> SlamArtifacts:
            self.closed = True
            trajectory_path = self.artifact_root / "trajectory.tum"
            trajectory_path.parent.mkdir(parents=True)
            trajectory_path.write_text("0 0 0 0 0 0 0 1\n", encoding="utf-8")
            return SlamArtifacts(trajectory_tum=artifact_ref(trajectory_path, kind="tum"))

    monkeypatch.setattr(mast3r_adapter, "_Mast3rSlamSession", FakeSession)
    backend = Mast3rSlamBackendConfig().setup_target()
    observation = Observation(
        seq=0,
        timestamp_ns=1,
        provenance=ObservationProvenance(source_id="test"),
        rgb=np.zeros((2, 2, 3), dtype=np.uint8),
    )

    backend.start_streaming(
        sequence_manifest=SequenceManifest(sequence_id="mast3r-stream"),
        benchmark_inputs=None,
        baseline_source=ReferenceSource.GROUND_TRUTH,
        backend_config=SlamBackendConfig(),
        output_policy=SlamOutputPolicy(),
        artifact_root=tmp_path / "mast3r-stream",
    )
    backend.step_streaming(observation)
    updates = backend.drain_streaming_updates()
    artifacts = backend.finish_streaming()

    assert FakeSession.instances[0].frames == [observation]
    assert updates[0].is_keyframe is True
    assert FakeSession.instances[0].closed is True
    assert artifacts.trajectory_tum.path.exists()


def test_mast3r_backend_run_observations_aborts_session_on_step_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import prml_vslam.methods.mast3r.adapter as mast3r_adapter

    class FailingSession:
        instances: list[FailingSession] = []

        def __init__(self, **_kwargs) -> None:
            self.aborted = False
            FailingSession.instances.append(self)

        def step(self, _frame: Observation) -> None:
            raise ValueError("step failed")

        def close(self):
            raise AssertionError("close should not run after step failure")

        def abort(self) -> None:
            self.aborted = True

    monkeypatch.setattr(mast3r_adapter, "_Mast3rSlamSession", FailingSession)
    backend = Mast3rSlamBackendConfig().setup_target()
    observation = Observation(
        seq=0,
        timestamp_ns=1,
        provenance=ObservationProvenance(source_id="test"),
        rgb=np.zeros((2, 2, 3), dtype=np.uint8),
    )

    with pytest.raises(ValueError, match="step failed"):
        backend.run_observations(
            [observation],
            benchmark_inputs=None,
            baseline_source=ReferenceSource.GROUND_TRUTH,
            backend_config=SlamBackendConfig(),
            output_policy=SlamOutputPolicy(),
            artifact_root=tmp_path / "mast3r-offline",
        )

    assert FailingSession.instances[0].aborted is True


def test_mast3r_session_surfaces_deferred_backend_errors() -> None:
    from prml_vslam.methods.mast3r.adapter import _Mast3rSlamSession

    session = _Mast3rSlamSession.__new__(_Mast3rSlamSession)
    session._backend_error = RuntimeError("backend failed")

    with pytest.raises(RuntimeError, match="backend failed"):
        session.try_get_updates()


def test_mast3r_session_rejects_missing_rgb_observations() -> None:
    from prml_vslam.methods.mast3r.adapter import _Mast3rSlamSession

    session = _Mast3rSlamSession.__new__(_Mast3rSlamSession)
    session._backend_error = None

    with pytest.raises(RuntimeError, match="requires RGB observations"):
        session.step(
            Observation(
                seq=0,
                timestamp_ns=1,
                provenance=ObservationProvenance(source_id="test"),
                rgb=None,
            )
        )


def test_vista_session_uses_injected_frame_preprocessor_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from prml_vslam.methods.vista.preprocess import PreparedVistaFrame
    from prml_vslam.methods.vista.session import VistaSlamRuntime

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

        def prepare(self, rgb_image: np.ndarray, *, view_name: str) -> PreparedVistaFrame:
            self.calls.append((rgb_image.shape, view_name))
            torch = sys.modules["torch"]
            image_rgb = np.full((4, 6, 3), fill_value=7, dtype=np.uint8)
            gray_u8 = np.full((4, 6), fill_value=11, dtype=np.uint8)
            rgb_tensor = torch.from_numpy(image_rgb).permute(2, 0, 1).float() / 255.0
            return PreparedVistaFrame(image_rgb=image_rgb, gray_u8=gray_u8, rgb_tensor=rgb_tensor)

    fake_preprocessor = FakePreprocessor()
    slam = FakeSlam()
    session = VistaSlamRuntime(
        slam=slam,
        flow_tracker=SimpleNamespace(compute_disparity=lambda *args, **kwargs: True),
        frame_preprocessor=fake_preprocessor,
        artifact_root=tmp_path / "vista-stream",
        output_policy=SlamOutputPolicy(),
        console=Console(__name__).child("vista-test"),
    )

    session.step(
        Observation(
            seq=0,
            timestamp_ns=123,
            rgb=np.zeros((8, 8, 3), dtype=np.uint8),
            provenance=ObservationProvenance(source_id="test"),
        )
    )
    updates = session.drain_updates()
    assert len(updates) == 1
    update = updates[0]

    assert fake_preprocessor.calls == [((8, 8, 3), "frame_000000")]
    assert len(slam.step_calls) == 1
    assert slam.step_calls[0]["shape"].shape == (1, 2)
    assert update.image_rgb is not None
    assert update.image_rgb.shape == (4, 6, 3)
    assert update.depth_map is not None
    assert update.depth_map.shape == (4, 6)


def test_vista_session_live_outputs_follow_model_raster_not_source_raster(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from prml_vslam.methods.vista.preprocess import PreparedVistaFrame
    from prml_vslam.methods.vista.session import VistaSlamRuntime

    _install_fake_torch(monkeypatch)

    class FakeSlam:
        def __init__(self) -> None:
            self.device = "cpu"

        def step(self, value: dict[str, object]) -> None:
            del value

        def get_view(self, view_index: int, **kwargs: object) -> object:
            del view_index, kwargs
            return SimpleNamespace(
                pose=np.eye(4, dtype=np.float64),
                depth=np.ones((5, 7), dtype=np.float32),
                intri=np.array(
                    [
                        [3.0, 0.0, 1.5],
                        [0.0, 4.0, 2.0],
                        [0.0, 0.0, 1.0],
                    ],
                    dtype=np.float64,
                ),
            )

        def get_pointmap_vis(self, view_index: int) -> tuple[np.ndarray, np.ndarray]:
            del view_index
            return np.zeros((5, 7, 3), dtype=np.uint8), np.ones((5, 7, 3), dtype=np.float32)

    class FakePreprocessor:
        def prepare(self, rgb_image: np.ndarray, *, view_name: str) -> PreparedVistaFrame:
            del rgb_image, view_name
            torch = sys.modules["torch"]
            image_rgb = np.full((5, 7, 3), fill_value=17, dtype=np.uint8)
            gray_u8 = np.full((5, 7), fill_value=9, dtype=np.uint8)
            rgb_tensor = torch.from_numpy(image_rgb).permute(2, 0, 1).float() / 255.0
            return PreparedVistaFrame(image_rgb=image_rgb, gray_u8=gray_u8, rgb_tensor=rgb_tensor)

    session = VistaSlamRuntime(
        slam=FakeSlam(),
        flow_tracker=SimpleNamespace(compute_disparity=lambda *args, **kwargs: True),
        frame_preprocessor=FakePreprocessor(),
        artifact_root=tmp_path / "vista-stream",
        output_policy=SlamOutputPolicy(),
        console=Console(__name__).child("vista-test"),
    )

    source_rgb = np.zeros((11, 13, 3), dtype=np.uint8)
    session.step(
        Observation(seq=0, timestamp_ns=123, rgb=source_rgb, provenance=ObservationProvenance(source_id="test"))
    )
    update = session.drain_updates()[0]

    assert update.image_rgb is not None
    assert update.image_rgb.shape == (5, 7, 3)
    assert update.image_rgb.shape != source_rgb.shape
    assert update.depth_map is not None
    assert update.depth_map.shape == (5, 7)
    assert update.pointmap is not None
    assert update.pointmap.shape == (5, 7, 3)
    assert update.camera_intrinsics == CameraIntrinsics(
        fx=3.0,
        fy=4.0,
        cx=1.5,
        cy=2.0,
        width_px=7,
        height_px=5,
    )


def test_vista_session_projects_near_orthonormal_live_pose_before_quaternion_conversion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from prml_vslam.methods.vista.session import VistaSlamRuntime

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

    session = VistaSlamRuntime(
        slam=FakeSlam(),
        flow_tracker=SimpleNamespace(compute_disparity=lambda *args, **kwargs: True),
        frame_preprocessor=_make_fake_frame_preprocessor(image_rgb=np.zeros((2, 2, 3), dtype=np.uint8)),
        artifact_root=tmp_path / "vista-stream",
        output_policy=SlamOutputPolicy(),
        console=Console(__name__).child("vista-test"),
    )

    session.step(
        Observation(
            seq=0,
            timestamp_ns=123,
            rgb=np.zeros((8, 8, 3), dtype=np.uint8),
            provenance=ObservationProvenance(source_id="test"),
        )
    )
    updates = session.drain_updates()
    assert len(updates) == 1
    update = updates[0]

    assert update.pose is not None
    assert np.isclose(np.linalg.norm(update.pose.quaternion_xyzw()), 1.0)
    assert update.pose.translation_xyz().tolist() == [1.0, 2.0, 3.0]


def test_vista_session_omits_dense_pointmap_when_policy_disables_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from prml_vslam.methods.vista.session import VistaSlamRuntime

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

    session = VistaSlamRuntime(
        slam=FakeSlam(),
        flow_tracker=SimpleNamespace(compute_disparity=lambda *args, **kwargs: True),
        frame_preprocessor=_make_fake_frame_preprocessor(image_rgb=np.zeros((2, 2, 3), dtype=np.uint8)),
        artifact_root=tmp_path / "vista-stream",
        output_policy=SlamOutputPolicy(emit_dense_points=False),
        console=Console(__name__).child("vista-test"),
    )

    session.step(
        Observation(
            seq=0,
            timestamp_ns=123,
            rgb=np.zeros((8, 8, 3), dtype=np.uint8),
            provenance=ObservationProvenance(source_id="test"),
        )
    )
    updates = session.drain_updates()
    assert len(updates) == 1
    update = updates[0]

    assert update.is_keyframe is True
    assert update.pointmap is None
    assert update.preview_rgb is not None
    assert update.backend_warnings == []


def test_vista_session_warns_when_dense_pointmap_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from prml_vslam.methods.vista.session import VistaSlamRuntime

    _install_fake_torch(monkeypatch)

    class FakeSlam:
        def get_view(self, *args: object, **kwargs: object) -> object:
            return SimpleNamespace(pose=np.eye(4), depth=np.ones((2, 2)), intri=np.eye(3))

        def get_pointmap_vis(self, view_index: int) -> tuple[np.ndarray, None]:
            del view_index
            return np.zeros((2, 2, 3), dtype=np.uint8), None

        @property
        def device(self) -> str:
            return "cpu"

        def step(self, value: object) -> None:
            del value

    session = VistaSlamRuntime(
        slam=FakeSlam(),
        flow_tracker=SimpleNamespace(compute_disparity=lambda *args, **kwargs: True),
        frame_preprocessor=_make_fake_frame_preprocessor(image_rgb=np.zeros((2, 2, 3), dtype=np.uint8)),
        artifact_root=tmp_path / "vista-stream",
        output_policy=SlamOutputPolicy(),
        console=Console(__name__).child("vista-test"),
    )

    session.step(
        Observation(
            seq=11,
            timestamp_ns=123,
            rgb=np.zeros((8, 8, 3), dtype=np.uint8),
            provenance=ObservationProvenance(source_id="test"),
        )
    )
    update = session.drain_updates()[0]

    assert update.pointmap is None
    assert update.backend_warnings == [
        "ViSTA-SLAM accepted a keyframe without a dense pointmap for source_seq=11, keyframe_index=0."
    ]


def test_vista_session_warns_when_dense_pointmap_has_no_valid_points(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from prml_vslam.methods.vista.session import VistaSlamRuntime

    _install_fake_torch(monkeypatch)

    class FakeSlam:
        def get_view(self, *args: object, **kwargs: object) -> object:
            return SimpleNamespace(pose=np.eye(4), depth=np.ones((2, 2)), intri=np.eye(3))

        def get_pointmap_vis(self, view_index: int) -> tuple[np.ndarray, np.ndarray]:
            del view_index
            return np.zeros((2, 2, 3), dtype=np.uint8), np.zeros((2, 2, 3), dtype=np.float32)

        @property
        def device(self) -> str:
            return "cpu"

        def step(self, value: object) -> None:
            del value

    session = VistaSlamRuntime(
        slam=FakeSlam(),
        flow_tracker=SimpleNamespace(compute_disparity=lambda *args, **kwargs: True),
        frame_preprocessor=_make_fake_frame_preprocessor(image_rgb=np.zeros((2, 2, 3), dtype=np.uint8)),
        artifact_root=tmp_path / "vista-stream",
        output_policy=SlamOutputPolicy(),
        console=Console(__name__).child("vista-test"),
    )

    session.step(
        Observation(
            seq=13,
            timestamp_ns=123,
            rgb=np.zeros((8, 8, 3), dtype=np.uint8),
            provenance=ObservationProvenance(source_id="test"),
        )
    )
    update = session.drain_updates()[0]

    assert update.pointmap is not None
    assert update.backend_warnings == [
        "ViSTA-SLAM accepted a keyframe whose dense pointmap contained no valid finite z>0 points for source_seq=13, keyframe_index=0."
    ]


def test_vista_session_accepts_tensor_backed_live_pointmap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from prml_vslam.methods.vista.session import VistaSlamRuntime

    _install_fake_torch(monkeypatch)
    torch = sys.modules["torch"]

    class FakeSlam:
        def get_view(self, *args: object, **kwargs: object) -> object:
            return SimpleNamespace(pose=np.eye(4), depth=np.ones((2, 2)), intri=np.eye(3))

        def get_pointmap_vis(self, view_index: int):
            del view_index
            pointmap = torch.from_numpy(
                np.array(
                    [
                        [[0.0, 0.0, 1.0], [0.0, 0.0, 2.0]],
                        [[0.0, 0.0, 3.0], [0.0, 0.0, 4.0]],
                    ],
                    dtype=np.float32,
                )
            )
            return np.zeros((2, 2, 3), dtype=np.uint8), pointmap

        @property
        def device(self) -> str:
            return "cpu"

        def step(self, value: object) -> None:
            del value

    session = VistaSlamRuntime(
        slam=FakeSlam(),
        flow_tracker=SimpleNamespace(compute_disparity=lambda *args, **kwargs: True),
        frame_preprocessor=_make_fake_frame_preprocessor(image_rgb=np.zeros((2, 2, 3), dtype=np.uint8)),
        artifact_root=tmp_path / "vista-stream",
        output_policy=SlamOutputPolicy(),
        console=Console(__name__).child("vista-test"),
    )

    session.step(
        Observation(
            seq=17,
            timestamp_ns=123,
            rgb=np.zeros((8, 8, 3), dtype=np.uint8),
            provenance=ObservationProvenance(source_id="test"),
        )
    )
    update = session.drain_updates()[0]

    assert update.pointmap is not None
    assert update.pointmap.dtype == np.float32
    assert np.allclose(update.pointmap[..., 2], np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32))


def test_vista_session_keyframe_gates_streaming_updates_before_step(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from prml_vslam.methods.vista.session import VistaSlamRuntime

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
    session = VistaSlamRuntime(
        slam=slam,
        flow_tracker=FakeFlowTracker(),
        frame_preprocessor=_make_fake_frame_preprocessor(image_rgb=np.zeros((2, 2, 3), dtype=np.uint8)),
        artifact_root=tmp_path / "vista-stream",
        output_policy=SlamOutputPolicy(),
        console=Console(__name__).child("vista-test"),
    )

    session.step(
        Observation(
            seq=0,
            timestamp_ns=100,
            rgb=np.zeros((8, 8, 3), dtype=np.uint8),
            provenance=ObservationProvenance(source_id="test"),
        )
    )
    session.step(
        Observation(
            seq=1,
            timestamp_ns=200,
            rgb=np.zeros((8, 8, 3), dtype=np.uint8),
            provenance=ObservationProvenance(source_id="test"),
        )
    )
    session.step(
        Observation(
            seq=2,
            timestamp_ns=300,
            rgb=np.zeros((8, 8, 3), dtype=np.uint8),
            provenance=ObservationProvenance(source_id="test"),
        )
    )
    updates = session.drain_updates()

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
    from prml_vslam.methods.vista.session import VistaSlamRuntime

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

    session = VistaSlamRuntime(
        slam=FakeSlam(),
        flow_tracker=FakeFlowTracker(),
        frame_preprocessor=_make_fake_frame_preprocessor(image_rgb=np.zeros((2, 2, 3), dtype=np.uint8)),
        artifact_root=tmp_path / "vista-stream",
        output_policy=SlamOutputPolicy(),
        console=Console(__name__).child("vista-test"),
    )

    session.step(
        Observation(
            seq=0,
            timestamp_ns=123,
            rgb=np.zeros((8, 8, 3), dtype=np.uint8),
            provenance=ObservationProvenance(source_id="test"),
        )
    )
    updates = session.drain_updates()
    assert len(updates) == 1
    update = updates[0]

    assert update.pose is None
    assert update.pointmap is None
    assert update.num_dense_points == 0
    assert update.is_keyframe is True
    assert update.keyframe_index == 0


def test_vista_session_close_exports_accepted_keyframe_source_timestamps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from prml_vslam.methods.vista.session import VistaSlamRuntime

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

        def step(self, value: dict[str, object]) -> None:
            del value

        def get_view(self, view_index: int, **kwargs: object) -> object:
            del kwargs
            pose = np.eye(4, dtype=np.float64)
            pose[0, 3] = float(view_index)
            return SimpleNamespace(
                pose=pose,
                depth=np.ones((2, 2), dtype=np.float32),
                intri=np.eye(3, dtype=np.float64),
            )

        def get_pointmap_vis(self, view_index: int) -> tuple[np.ndarray, np.ndarray]:
            del view_index
            return np.zeros((2, 2, 3), dtype=np.uint8), np.ones((2, 2, 3), dtype=np.float32)

        def save_data_all(self, output_dir: str, *, save_images: bool, save_depths: bool) -> None:
            del save_images, save_depths
            trajectory = np.repeat(np.eye(4, dtype=np.float64)[None, :, :], repeats=2, axis=0)
            trajectory[1, 0, 3] = 1.0
            np.save(Path(output_dir) / "trajectory.npy", trajectory)

    session = VistaSlamRuntime(
        slam=FakeSlam(),
        flow_tracker=FakeFlowTracker(),
        frame_preprocessor=_make_fake_frame_preprocessor(image_rgb=np.zeros((2, 2, 3), dtype=np.uint8)),
        artifact_root=tmp_path / "vista-stream",
        output_policy=SlamOutputPolicy(),
        console=Console(__name__).child("vista-test"),
    )

    session.step(
        Observation(
            seq=0,
            timestamp_ns=100_000_000,
            rgb=np.zeros((8, 8, 3), dtype=np.uint8),
            provenance=ObservationProvenance(source_id="test"),
        )
    )
    session.step(
        Observation(
            seq=1,
            timestamp_ns=250_000_000,
            rgb=np.zeros((8, 8, 3), dtype=np.uint8),
            provenance=ObservationProvenance(source_id="test"),
        )
    )
    session.step(
        Observation(
            seq=2,
            timestamp_ns=400_000_000,
            rgb=np.zeros((8, 8, 3), dtype=np.uint8),
            provenance=ObservationProvenance(source_id="test"),
        )
    )
    artifacts = session.finish()

    trajectory = load_tum_trajectory(artifacts.trajectory_tum.path)
    assert trajectory.timestamps.tolist() == [0.1, 0.4]


def test_vista_artifact_builder_projects_near_orthonormal_trajectory_rotations(tmp_path: Path) -> None:
    from prml_vslam.methods.vista.artifacts import build_vista_artifacts

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

    artifacts = build_vista_artifacts(
        native_output_dir=native_output_dir,
        artifact_root=tmp_path / "artifacts",
        output_policy=SlamOutputPolicy(),
        timestamps_s=[0.0, 0.25],
    )

    assert artifacts.trajectory_tum.path.exists()
    assert load_tum_trajectory(artifacts.trajectory_tum.path).timestamps.tolist() == [0.0, 0.25]
    assert artifacts.trajectory_tum.fingerprint == stable_hash(
        {"path": str(artifacts.trajectory_tum.path.resolve()), "kind": "tum"}
    )


def test_vista_artifact_builder_aliases_sparse_and_dense_to_one_canonical_cloud(tmp_path: Path) -> None:
    from prml_vslam.methods.vista.artifacts import build_vista_artifacts

    native_output_dir = tmp_path / "native"
    native_output_dir.mkdir(parents=True, exist_ok=True)
    np.save(native_output_dir / "trajectory.npy", np.eye(4, dtype=np.float64)[None, :, :])
    (native_output_dir / "rerun_recording.rrd").write_bytes(b"native-rerun")
    extra_path = native_output_dir / "session.json"
    extra_path.write_text('{"session": "vista"}', encoding="utf-8")
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

    artifacts = build_vista_artifacts(
        native_output_dir=native_output_dir,
        artifact_root=tmp_path / "artifacts",
        output_policy=SlamOutputPolicy(),
        timestamps_s=[0.0],
    )

    assert artifacts.sparse_points_ply is not None
    assert artifacts.dense_points_ply is not None
    assert artifacts.sparse_points_ply.path == artifacts.dense_points_ply.path
    assert artifacts.sparse_points_ply.path.name == "point_cloud.ply"
    assert artifacts.sparse_points_ply.fingerprint == stable_hash(
        {"path": str(artifacts.sparse_points_ply.path.resolve()), "kind": "ply"}
    )
    assert not hasattr(artifacts, "native_rerun_rrd")
    assert not hasattr(artifacts, "native_output_dir")
    assert "rerun_recording.rrd" not in artifacts.extras
    assert artifacts.extras["session.json"].fingerprint == stable_hash(
        {"path": str(extra_path.resolve()), "kind": "json"}
    )


def test_vista_artifact_builder_preserves_point_cloud_colors_and_standardizes_intrinsics(tmp_path: Path) -> None:
    from prml_vslam.methods.vista.artifacts import build_vista_artifacts

    native_output_dir = tmp_path / "native"
    native_output_dir.mkdir(parents=True, exist_ok=True)
    np.save(native_output_dir / "trajectory.npy", np.eye(4, dtype=np.float64)[None, :, :])
    np.save(
        native_output_dir / "intrinsics.npy",
        np.asarray([[[280.0, 0.0, 112.0], [0.0, 281.0, 113.0], [0.0, 0.0, 1.0]]], dtype=np.float32),
    )
    np.savez(
        native_output_dir / "view_graph.npz",
        view_graph=np.asarray({0: []}, dtype=object),
        loop_min_dist=np.asarray(40),
        view_names=np.asarray(["frame_000000"]),
    )
    point_cloud_path = write_point_cloud_ply(
        native_output_dir / "pointcloud.ply",
        np.asarray([[0.0, 0.0, 1.0], [1.0, 0.0, 2.0]], dtype=np.float64),
        colors_rgb=np.asarray([[255, 0, 0], [0, 255, 128]], dtype=np.uint8),
    )
    assert point_cloud_path.exists()

    artifacts = build_vista_artifacts(
        native_output_dir=native_output_dir,
        artifact_root=tmp_path / "artifacts",
        output_policy=SlamOutputPolicy(),
        timestamps_s=[0.0],
    )

    assert artifacts.dense_points_ply is not None
    _, colors = load_point_cloud_ply_with_colors(artifacts.dense_points_ply.path)
    assert colors is not None
    np.testing.assert_allclose(colors[0], np.asarray([1.0, 0.0, 0.0]), atol=1 / 255.0)
    estimated_ref = artifacts.extras["estimated_intrinsics.json"]
    series = CameraIntrinsicsSeries.model_validate_json(estimated_ref.path.read_text(encoding="utf-8"))
    assert series.raster_space == "vista_model"
    assert series.source == "native/intrinsics.npy"
    assert series.method_id == "vista"
    assert series.width_px == 224
    assert series.height_px == 224
    assert series.samples[0].view_name == "frame_000000"
    assert series.samples[0].intrinsics == CameraIntrinsics(
        fx=280.0,
        fy=281.0,
        cx=112.0,
        cy=113.0,
        width_px=224,
        height_px=224,
    )


def test_vista_pose_normalization_rejects_clearly_invalid_rotations() -> None:
    from prml_vslam.methods.vista.artifacts import _frame_transform_from_vista_pose

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


def test_vista_config_models_ignore_removed_dead_knobs() -> None:
    config = VistaSlamBackendConfig.model_validate({"stride": 5, "keyframe_detection": "stride"})
    assert not hasattr(config, "stride")
    assert not hasattr(config, "keyframe_detection")

    with pytest.raises(ValidationError):
        VistaSlamBackendConfig.model_validate({"device": "tpu"})
