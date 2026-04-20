"""Tests for the repository-local method mocks."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from pydantic import ValidationError

from prml_vslam.benchmark import ReferenceCloudCoordinateStatus, ReferenceCloudSource, ReferenceSource
from prml_vslam.interfaces import CameraIntrinsics, FramePacket, FrameTransform
from prml_vslam.interfaces.ingest import (
    PreparedBenchmarkInputs,
    ReferenceCloudRef,
    ReferencePointCloudSequenceRef,
    ReferenceTrajectoryRef,
    SequenceManifest,
)
from prml_vslam.interfaces.slam import SlamSessionInit
from prml_vslam.methods import MethodId, MockSlamBackendConfig, VistaSlamBackend, VistaSlamBackendConfig
from prml_vslam.methods.config_contracts import SlamBackendConfig, SlamOutputPolicy
from prml_vslam.pipeline.finalization import stable_hash
from prml_vslam.utils import Console
from prml_vslam.utils.geometry import load_tum_trajectory, write_point_cloud_ply, write_tum_trajectory


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


def _write_normalized_timestamps(path: Path, timestamps_ns: list[int]) -> Path:
    path.write_text(json.dumps({"timestamps_ns": timestamps_ns}), encoding="utf-8")
    return path


def _pose(tx: float, *, ty: float = 0.0, tz: float = 0.0) -> FrameTransform:
    return FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=tx, ty=ty, tz=tz)


def _write_reference_bundle(tmp_path: Path) -> PreparedBenchmarkInputs:
    reference_dir = tmp_path / "references"
    reference_dir.mkdir(parents=True, exist_ok=True)

    ground_truth_path = write_tum_trajectory(
        reference_dir / "ground_truth.tum",
        [_pose(0.0), _pose(1.0), _pose(2.0)],
        [0.0, 0.1, 0.2],
    )
    arcore_path = write_tum_trajectory(
        reference_dir / "arcore.tum",
        [_pose(10.0), _pose(11.0), _pose(12.0)],
        [0.0, 0.1, 0.2],
    )
    tango_trajectory_path = write_tum_trajectory(
        reference_dir / "tango_area_learning.tum",
        [_pose(0.0), _pose(1.0), _pose(2.0)],
        [0.0, 0.1, 0.2],
    )
    payload_root = reference_dir / "tango"
    payload_root.mkdir(parents=True, exist_ok=True)
    index_path = payload_root / "point-cloud.csv"
    index_path.write_text("0.0,1\n0.1,2\n0.2,3\n", encoding="utf-8")
    for index, depth in ((1, 1.0), (2, 1.1), (3, 1.2)):
        (payload_root / f"point-cloud-{index:05d}.csv").write_text(
            f"0.0,0.0,{depth}\n0.1,0.0,{depth}\n0.0,0.1,{depth}\n",
            encoding="utf-8",
        )
    aligned_cloud_path = write_point_cloud_ply(
        reference_dir / "tango_area_learning_aligned.ply",
        np.asarray([[0.0, 0.0, 1.0], [0.2, 0.0, 1.0], [0.0, 0.2, 1.0]], dtype=np.float64),
    )
    metadata_path = reference_dir / "tango_area_learning_aligned.metadata.json"
    metadata_path.write_text("{}", encoding="utf-8")
    return PreparedBenchmarkInputs(
        reference_trajectories=[
            ReferenceTrajectoryRef(source=ReferenceSource.GROUND_TRUTH, path=ground_truth_path),
            ReferenceTrajectoryRef(source=ReferenceSource.ARCORE, path=arcore_path),
        ],
        reference_clouds=[
            ReferenceCloudRef(
                source=ReferenceCloudSource.TANGO_AREA_LEARNING,
                path=aligned_cloud_path,
                metadata_path=metadata_path,
                target_frame="advio_gt_world",
                coordinate_status=ReferenceCloudCoordinateStatus.ALIGNED,
            )
        ],
        reference_point_cloud_sequences=[
            ReferencePointCloudSequenceRef(
                source=ReferenceCloudSource.TANGO_AREA_LEARNING,
                index_path=index_path,
                payload_root=payload_root,
                trajectory_path=tango_trajectory_path,
                target_frame="advio_tango_area_learning_world",
                native_frame="advio_tango_area_learning_world",
                coordinate_status=ReferenceCloudCoordinateStatus.SOURCE_NATIVE,
            )
        ],
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


def test_mock_slam_backend_materializes_placeholder_outputs_without_reference(tmp_path: Path) -> None:
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
    backend = MockSlamBackendConfig().setup_target()
    assert backend is not None
    (tmp_path / "frames").mkdir()
    benchmark_inputs = _write_reference_bundle(tmp_path)
    sequence = SequenceManifest(
        sequence_id="advio-15",
        rgb_dir=tmp_path / "frames",
        timestamps_path=_write_normalized_timestamps(tmp_path / "timestamps.json", [0, 100_000_000, 200_000_000]),
    )
    artifacts = backend.run_sequence(
        sequence=sequence,
        benchmark_inputs=benchmark_inputs,
        baseline_source=ReferenceSource.ARCORE,
        backend_config=VistaSlamBackendConfig(),
        output_policy=SlamOutputPolicy(),
        artifact_root=tmp_path / "mock-run",
    )

    trajectory = load_tum_trajectory(artifacts.trajectory_tum.path)
    assert trajectory.positions_xyz[:, 0].tolist() == [10.0, 11.0, 12.0]


def test_mock_slam_session_emits_incremental_updates_and_artifacts(tmp_path: Path) -> None:
    benchmark_inputs = _write_reference_bundle(tmp_path)
    session = (
        MockSlamBackendConfig()
        .setup_target()
        .start_session(
            session_init=SlamSessionInit(
                sequence_manifest=SequenceManifest(sequence_id="advio-15"),
                benchmark_inputs=benchmark_inputs,
                baseline_source=ReferenceSource.GROUND_TRUTH,
            ),
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
            intrinsics=CameraIntrinsics(fx=100.0, fy=100.0, cx=4.0, cy=4.0, width_px=8, height_px=8),
            pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=0.0, tz=0.0),
        )
    )
    updates = session.try_get_updates()

    assert len(updates) == 2
    assert updates[0].is_keyframe is True
    assert updates[1].pose is not None
    assert updates[1].pose.tx == 1.0
    assert updates[1].pointmap is not None
    assert updates[1].num_dense_points > 0

    artifacts = session.close()
    assert artifacts.trajectory_tum.path.exists()


def test_mock_slam_session_uses_reference_pose_instead_of_stream_packet_pose(tmp_path: Path) -> None:
    benchmark_inputs = _write_reference_bundle(tmp_path)
    session = (
        MockSlamBackendConfig()
        .setup_target()
        .start_session(
            session_init=SlamSessionInit(
                sequence_manifest=SequenceManifest(sequence_id="advio-15"),
                benchmark_inputs=benchmark_inputs,
                baseline_source=ReferenceSource.ARCORE,
            ),
            backend_config=SlamBackendConfig(),
            output_policy=SlamOutputPolicy(),
            artifact_root=tmp_path / "mock-stream-ref-pose",
        )
    )

    session.step(
        FramePacket(
            seq=0,
            timestamp_ns=100_000_000,
            rgb=np.zeros((8, 8, 3), dtype=np.uint8),
            intrinsics=CameraIntrinsics(fx=100.0, fy=100.0, cx=4.0, cy=4.0, width_px=8, height_px=8),
            pose=_pose(999.0),
        )
    )

    update = session.try_get_updates()[0]
    assert update.pose is not None
    assert update.pose.tx == 11.0
    assert update.pointmap is not None


def test_mock_slam_backend_zero_variance_awgn_preserves_reference_outputs(tmp_path: Path) -> None:
    benchmark_inputs = _write_reference_bundle(tmp_path)
    backend = MockSlamBackendConfig(
        trajectory_position_noise_variance_m2=0.0,
        point_noise_variance_m2=0.0,
        random_seed=7,
    ).setup_target()
    sequence = SequenceManifest(
        sequence_id="advio-15",
        timestamps_path=_write_normalized_timestamps(tmp_path / "timestamps.json", [0, 100_000_000, 200_000_000]),
    )

    artifacts = backend.run_sequence(
        sequence=sequence,
        benchmark_inputs=benchmark_inputs,
        baseline_source=ReferenceSource.GROUND_TRUTH,
        backend_config=SlamBackendConfig(),
        output_policy=SlamOutputPolicy(),
        artifact_root=tmp_path / "mock-offline-zero-noise",
    )

    trajectory = load_tum_trajectory(artifacts.trajectory_tum.path)
    assert trajectory.positions_xyz[:, 0].tolist() == [0.0, 1.0, 2.0]


def test_mock_slam_backend_nonzero_awgn_is_deterministic_with_fixed_seed(tmp_path: Path) -> None:
    benchmark_inputs = _write_reference_bundle(tmp_path)
    config = MockSlamBackendConfig(
        trajectory_position_noise_variance_m2=0.01,
        point_noise_variance_m2=0.01,
        random_seed=13,
    )
    session1 = config.setup_target().start_session(
        session_init=SlamSessionInit(
            sequence_manifest=SequenceManifest(sequence_id="advio-15"),
            benchmark_inputs=benchmark_inputs,
            baseline_source=ReferenceSource.GROUND_TRUTH,
        ),
        backend_config=SlamBackendConfig(),
        output_policy=SlamOutputPolicy(),
        artifact_root=tmp_path / "mock-noise-1",
    )
    session2 = config.setup_target().start_session(
        session_init=SlamSessionInit(
            sequence_manifest=SequenceManifest(sequence_id="advio-15"),
            benchmark_inputs=benchmark_inputs,
            baseline_source=ReferenceSource.GROUND_TRUTH,
        ),
        backend_config=SlamBackendConfig(),
        output_policy=SlamOutputPolicy(),
        artifact_root=tmp_path / "mock-noise-2",
    )
    frame = FramePacket(
        seq=0,
        timestamp_ns=100_000_000,
        rgb=np.zeros((8, 8, 3), dtype=np.uint8),
        intrinsics=CameraIntrinsics(fx=100.0, fy=100.0, cx=4.0, cy=4.0, width_px=8, height_px=8),
    )

    session1.step(frame)
    session2.step(frame)
    update1 = session1.try_get_updates()[0]
    update2 = session2.try_get_updates()[0]

    assert update1.pose is not None and update2.pose is not None
    assert update1.pose.tx == pytest.approx(update2.pose.tx)
    assert update1.pose.ty == pytest.approx(update2.pose.ty)
    assert update1.pose.tz == pytest.approx(update2.pose.tz)
    assert update1.pointmap is not None and update2.pointmap is not None
    assert np.array_equal(np.nan_to_num(update1.pointmap, nan=-1.0), np.nan_to_num(update2.pointmap, nan=-1.0))


def test_mock_slam_session_warns_and_falls_back_when_reference_payload_is_missing(tmp_path: Path) -> None:
    benchmark_inputs = _write_reference_bundle(tmp_path)
    session = (
        MockSlamBackendConfig()
        .setup_target()
        .start_session(
            session_init=SlamSessionInit(
                sequence_manifest=SequenceManifest(sequence_id="advio-15"),
                benchmark_inputs=benchmark_inputs,
                baseline_source=ReferenceSource.GROUND_TRUTH,
            ),
            backend_config=SlamBackendConfig(),
            output_policy=SlamOutputPolicy(),
            artifact_root=tmp_path / "mock-stream-missing-payload",
        )
    )

    session.step(
        FramePacket(
            seq=0,
            timestamp_ns=10_000_000_000,
            rgb=np.zeros((8, 8, 3), dtype=np.uint8),
            intrinsics=CameraIntrinsics(fx=100.0, fy=100.0, cx=4.0, cy=4.0, width_px=8, height_px=8),
        )
    )

    update = session.try_get_updates()[0]
    assert update.pointmap is not None
    assert any("falling back to synthetic pointmap generation" in warning for warning in update.backend_warnings)


def test_methods_package_exports_vista_backend_surfaces() -> None:
    assert VistaSlamBackend is not None


def test_vista_backend_starts_direct_streaming_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import prml_vslam.methods.vista.adapter as vista_adapter

    backend = VistaSlamBackendConfig().setup_target()
    assert backend is not None
    monkeypatch.setattr(
        vista_adapter,
        "create_vista_session",
        lambda **_: SimpleNamespace(
            step=lambda *_args, **_kwargs: None,
            try_get_updates=lambda: [],
            close=lambda: None,
        ),
    )

    session = backend.start_session(
        session_init=SlamSessionInit(sequence_manifest=SequenceManifest(sequence_id="vista-stream")),
        backend_config=SlamBackendConfig(),
        output_policy=SlamOutputPolicy(),
        artifact_root=tmp_path / "vista-stream",
    )

    assert callable(session.step)
    assert callable(session.try_get_updates)
    assert callable(session.close)


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
    from prml_vslam.methods.vista.session import VistaSlamSession

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
        frame_preprocessor=_make_fake_frame_preprocessor(),
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


def test_vista_session_uses_injected_frame_preprocessor_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from prml_vslam.methods.vista.preprocess import PreparedVistaFrame
    from prml_vslam.methods.vista.session import VistaSlamSession

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


def test_vista_session_live_outputs_follow_model_raster_not_source_raster(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from prml_vslam.methods.vista.preprocess import PreparedVistaFrame
    from prml_vslam.methods.vista.session import VistaSlamSession

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

    session = VistaSlamSession(
        slam=FakeSlam(),
        flow_tracker=SimpleNamespace(compute_disparity=lambda *args, **kwargs: True),
        frame_preprocessor=FakePreprocessor(),
        artifact_root=tmp_path / "vista-stream",
        output_policy=SlamOutputPolicy(),
        console=Console(__name__).child("vista-test"),
    )

    source_rgb = np.zeros((11, 13, 3), dtype=np.uint8)
    session.step(FramePacket(seq=0, timestamp_ns=123, rgb=source_rgb))
    update = session.try_get_updates()[0]

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
    from prml_vslam.methods.vista.session import VistaSlamSession

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
        frame_preprocessor=_make_fake_frame_preprocessor(image_rgb=np.zeros((2, 2, 3), dtype=np.uint8)),
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
    from prml_vslam.methods.vista.session import VistaSlamSession

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
        frame_preprocessor=_make_fake_frame_preprocessor(image_rgb=np.zeros((2, 2, 3), dtype=np.uint8)),
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
    assert update.backend_warnings == []


def test_vista_session_warns_when_dense_pointmap_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from prml_vslam.methods.vista.session import VistaSlamSession

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

    session = VistaSlamSession(
        slam=FakeSlam(),
        flow_tracker=SimpleNamespace(compute_disparity=lambda *args, **kwargs: True),
        frame_preprocessor=_make_fake_frame_preprocessor(image_rgb=np.zeros((2, 2, 3), dtype=np.uint8)),
        artifact_root=tmp_path / "vista-stream",
        output_policy=SlamOutputPolicy(),
        console=Console(__name__).child("vista-test"),
    )

    session.step(FramePacket(seq=11, timestamp_ns=123, rgb=np.zeros((8, 8, 3), dtype=np.uint8)))
    update = session.try_get_updates()[0]

    assert update.pointmap is None
    assert update.backend_warnings == [
        "ViSTA-SLAM accepted a keyframe without a dense pointmap for source_seq=11, keyframe_index=0."
    ]


def test_vista_session_warns_when_dense_pointmap_has_no_valid_points(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from prml_vslam.methods.vista.session import VistaSlamSession

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

    session = VistaSlamSession(
        slam=FakeSlam(),
        flow_tracker=SimpleNamespace(compute_disparity=lambda *args, **kwargs: True),
        frame_preprocessor=_make_fake_frame_preprocessor(image_rgb=np.zeros((2, 2, 3), dtype=np.uint8)),
        artifact_root=tmp_path / "vista-stream",
        output_policy=SlamOutputPolicy(),
        console=Console(__name__).child("vista-test"),
    )

    session.step(FramePacket(seq=13, timestamp_ns=123, rgb=np.zeros((8, 8, 3), dtype=np.uint8)))
    update = session.try_get_updates()[0]

    assert update.pointmap is not None
    assert update.backend_warnings == [
        "ViSTA-SLAM accepted a keyframe whose dense pointmap contained no valid finite z>0 points for source_seq=13, keyframe_index=0."
    ]


def test_vista_session_accepts_tensor_backed_live_pointmap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from prml_vslam.methods.vista.session import VistaSlamSession

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

    session = VistaSlamSession(
        slam=FakeSlam(),
        flow_tracker=SimpleNamespace(compute_disparity=lambda *args, **kwargs: True),
        frame_preprocessor=_make_fake_frame_preprocessor(image_rgb=np.zeros((2, 2, 3), dtype=np.uint8)),
        artifact_root=tmp_path / "vista-stream",
        output_policy=SlamOutputPolicy(),
        console=Console(__name__).child("vista-test"),
    )

    session.step(FramePacket(seq=17, timestamp_ns=123, rgb=np.zeros((8, 8, 3), dtype=np.uint8)))
    update = session.try_get_updates()[0]

    assert update.pointmap is not None
    assert update.pointmap.dtype == np.float32
    assert np.allclose(update.pointmap[..., 2], np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32))


def test_vista_session_keyframe_gates_streaming_updates_before_step(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from prml_vslam.methods.vista.session import VistaSlamSession

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
        frame_preprocessor=_make_fake_frame_preprocessor(image_rgb=np.zeros((2, 2, 3), dtype=np.uint8)),
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
    from prml_vslam.methods.vista.session import VistaSlamSession

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
        frame_preprocessor=_make_fake_frame_preprocessor(image_rgb=np.zeros((2, 2, 3), dtype=np.uint8)),
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


def test_vista_session_close_exports_accepted_keyframe_source_timestamps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from prml_vslam.methods.vista.session import VistaSlamSession
    from prml_vslam.utils.geometry import load_tum_trajectory

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

    session = VistaSlamSession(
        slam=FakeSlam(),
        flow_tracker=FakeFlowTracker(),
        frame_preprocessor=_make_fake_frame_preprocessor(image_rgb=np.zeros((2, 2, 3), dtype=np.uint8)),
        artifact_root=tmp_path / "vista-stream",
        output_policy=SlamOutputPolicy(),
        console=Console(__name__).child("vista-test"),
    )

    session.step(FramePacket(seq=0, timestamp_ns=100_000_000, rgb=np.zeros((8, 8, 3), dtype=np.uint8)))
    session.step(FramePacket(seq=1, timestamp_ns=250_000_000, rgb=np.zeros((8, 8, 3), dtype=np.uint8)))
    session.step(FramePacket(seq=2, timestamp_ns=400_000_000, rgb=np.zeros((8, 8, 3), dtype=np.uint8)))
    artifacts = session.close()

    trajectory = load_tum_trajectory(artifacts.trajectory_tum.path)
    assert trajectory.timestamps.tolist() == [0.1, 0.4]


def test_vista_backend_offline_run_requires_normalized_rgb_dir(tmp_path: Path) -> None:
    from prml_vslam.benchmark import ReferenceSource

    backend = VistaSlamBackendConfig().setup_target()
    assert backend is not None
    timestamps_path = _write_normalized_timestamps(tmp_path / "timestamps.json", [100_000_000])

    with pytest.raises(RuntimeError, match="SequenceManifest\\.rgb_dir"):
        backend.run_sequence(
            sequence=SequenceManifest(sequence_id="advio-15", timestamps_path=timestamps_path),
            benchmark_inputs=None,
            baseline_source=ReferenceSource.GROUND_TRUTH,
            backend_config=VistaSlamBackendConfig(),
            output_policy=SlamOutputPolicy(),
            artifact_root=tmp_path / "vista-offline",
        )


def test_vista_backend_offline_run_requires_normalized_timestamps_path(tmp_path: Path) -> None:
    from prml_vslam.benchmark import ReferenceSource

    backend = VistaSlamBackendConfig().setup_target()
    assert backend is not None
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir(parents=True)

    with pytest.raises(RuntimeError, match="SequenceManifest\\.timestamps_path"):
        backend.run_sequence(
            sequence=SequenceManifest(sequence_id="advio-15", rgb_dir=frames_dir),
            benchmark_inputs=None,
            baseline_source=ReferenceSource.GROUND_TRUTH,
            backend_config=VistaSlamBackendConfig(),
            output_policy=SlamOutputPolicy(),
            artifact_root=tmp_path / "vista-offline",
        )


def test_vista_artifact_builder_projects_near_orthonormal_trajectory_rotations(tmp_path: Path) -> None:
    from prml_vslam.methods.vista.artifacts import build_vista_artifacts
    from prml_vslam.utils.geometry import load_tum_trajectory

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


def test_vista_config_models_reject_removed_dead_knobs() -> None:
    for payload in (
        {"device": "cpu"},
        {"stride": 5},
        {"keyframe_detection": "stride"},
    ):
        with pytest.raises(ValidationError):
            VistaSlamBackendConfig.model_validate(payload)
