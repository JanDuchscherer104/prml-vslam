"""Tests for the packaged Streamlit app and Record3D runtime."""

from __future__ import annotations

import time
import warnings
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from prml_vslam.app import bootstrap
from prml_vslam.app.models import (
    AdvioPageState,
    AdvioPreviewSnapshot,
    AppPageId,
    AppState,
    PipelineSourceId,
    PreviewStreamState,
    Record3DPageState,
    Record3DStreamSnapshot,
)
from prml_vslam.app.services import (
    AdvioPreviewRuntimeController,
    Record3DStreamRuntimeController,
)
from prml_vslam.app.state import SessionStateStore
from prml_vslam.benchmark import (
    BenchmarkConfig,
    CloudBenchmarkConfig,
    EfficiencyBenchmarkConfig,
    TrajectoryBenchmarkConfig,
)
from prml_vslam.datasets.advio import AdvioPoseSource
from prml_vslam.datasets.advio.advio_layout import resolve_existing_reference_tum
from prml_vslam.datasets.contracts import DatasetId
from prml_vslam.eval import TrajectoryEvaluationService
from prml_vslam.eval.contracts import SelectionSnapshot
from prml_vslam.interfaces import (
    CameraIntrinsics,
    FramePacket,
    FrameTransform,
)
from prml_vslam.io.record3d import (
    Record3DDevice,
    Record3DTransportId,
)
from prml_vslam.methods import MethodId
from prml_vslam.methods.updates import SlamUpdate
from prml_vslam.pipeline import PipelineMode, RunRequest
from prml_vslam.pipeline.contracts.artifacts import ArtifactRef, SlamArtifacts
from prml_vslam.pipeline.contracts.plan import RunPlan
from prml_vslam.pipeline.contracts.request import (
    DatasetSourceSpec,
    LiveTransportId,
    Record3DLiveSourceSpec,
    SlamStageConfig,
)
from prml_vslam.pipeline.contracts.sequence import SequenceManifest
from prml_vslam.pipeline.run_service import RunService
from prml_vslam.pipeline.state import RunSnapshot, RunState, StreamingRunSnapshot
from prml_vslam.pipeline.streaming import (
    _is_keyframe_like_update,
)
from prml_vslam.utils.path_config import PathConfig
from prml_vslam.visualization import VisualizationConfig


def _write_tum(path: Path, rows: list[tuple[float, float, float, float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(f"{t:.1f} {x:.3f} {y:.3f} {z:.3f} 0 0 0 1" for t, x, y, z in rows) + "\n",
        encoding="utf-8",
    )


def _build_path_config(tmp_path: Path) -> PathConfig:
    sequence_root = tmp_path / ".data" / "advio" / "advio-15" / "ground-truth"
    run_root = tmp_path / ".artifacts" / "advio-15" / "vista" / "slam"
    _write_tum(
        sequence_root / "ground_truth.tum",
        [(0.0, 0.0, 0.0, 0.0), (0.1, 1.0, 0.0, 0.0), (0.2, 2.0, 1.0, 0.0)],
    )
    _write_tum(
        run_root / "trajectory.tum",
        [(0.0, 0.0, 0.0, 0.0), (0.1, 1.1, 0.0, 0.0), (0.2, 2.2, 0.9, 0.0)],
    )
    return PathConfig(
        root=tmp_path,
        artifacts_dir=tmp_path / ".artifacts",
        captures_dir=tmp_path / "captures",
    )


def _write_pipeline_config(
    path_config: PathConfig,
    *,
    name: str = "advio-offline-advio-15-vista.toml",
    source_block: str = 'dataset_id = "advio"\nsequence_id = "advio-15"',
) -> Path:
    config_path = path_config.resolve_pipeline_config_path(name, create_parent=True)
    config_path.write_text(
        f"""
experiment_name = "advio-offline-advio-15-vista"
mode = "offline"
output_dir = ".artifacts"

[source]
{source_block}

[slam]
method = "vista"

[slam.outputs]
emit_dense_points = true
emit_sparse_points = true

[benchmark.reference]
enabled = false

[benchmark.trajectory]
enabled = false
baseline_id = "reference"

[benchmark.cloud]
enabled = false

[benchmark.efficiency]
enabled = false
""".strip(),
        encoding="utf-8",
    )
    return config_path


def _load_pipeline_request_fixture() -> RunRequest:
    return RunRequest(
        experiment_name="advio-offline-advio-15-vista",
        mode=PipelineMode.OFFLINE,
        output_dir=Path(".artifacts"),
        source=DatasetSourceSpec(dataset_id=DatasetId.ADVIO, sequence_id="advio-15"),
        slam=SlamStageConfig(
            method=MethodId.VISTA,
            backend={"config_path": None, "max_frames": None},
            outputs={"emit_dense_points": True, "emit_sparse_points": True},
        ),
        benchmark=BenchmarkConfig(
            reference={"enabled": False},
            trajectory=TrajectoryBenchmarkConfig(enabled=False),
            cloud=CloudBenchmarkConfig(enabled=False),
            efficiency=EfficiencyBenchmarkConfig(enabled=False),
        ),
        visualization=VisualizationConfig(export_viewer_rrd=False, connect_live_viewer=False),
    )


def _record3d_pipeline_action(
    *,
    transport: Record3DTransportId,
    persist_capture: bool = True,
    usb_device_index: int = 0,
    wifi_device_address: str = "",
) -> dict[str, object]:
    return {
        "source_kind": PipelineSourceId.RECORD3D,
        "record3d_transport": transport,
        "record3d_usb_device_index": usb_device_index,
        "record3d_wifi_device_address": wifi_device_address,
        "record3d_persist_capture": persist_capture,
        "mode": PipelineMode.STREAMING,
        "method": MethodId.VISTA,
    }


def _record3d_pipeline_request(
    *,
    transport: Record3DTransportId,
    output_dir: Path,
    persist_capture: bool = True,
    device_index: int | None = None,
    device_address: str = "",
) -> RunRequest:
    return RunRequest(
        experiment_name=f"record3d-{transport.value}-demo",
        mode=PipelineMode.STREAMING,
        output_dir=output_dir,
        source=Record3DLiveSourceSpec(
            transport=transport,
            persist_capture=persist_capture,
            device_index=device_index,
            device_address=device_address,
        ),
        slam=SlamStageConfig(method=MethodId.VISTA),
        benchmark=BenchmarkConfig(
            reference={"enabled": False},
            trajectory=TrajectoryBenchmarkConfig(enabled=False),
            cloud=CloudBenchmarkConfig(enabled=False),
            efficiency=EfficiencyBenchmarkConfig(enabled=False),
        ),
        visualization=VisualizationConfig(export_viewer_rrd=False, connect_live_viewer=False),
    )


def _write_advio_local_sequence(dataset_root: Path, *, sequence_id: int = 15) -> Path:
    sequence_dir = dataset_root / f"advio-{sequence_id:02d}"
    (sequence_dir / "iphone").mkdir(parents=True, exist_ok=True)
    (sequence_dir / "pixel").mkdir(parents=True, exist_ok=True)
    (sequence_dir / "ground-truth").mkdir(parents=True, exist_ok=True)
    (dataset_root / "calibration").mkdir(parents=True, exist_ok=True)

    (sequence_dir / "iphone" / "frames.mov").write_bytes(b"")
    (sequence_dir / "iphone" / "frames.csv").write_text("0.0,0\n0.1,1\n0.2,2\n", encoding="utf-8")
    for name in (
        "platform-location.csv",
        "accelerometer.csv",
        "gyroscope.csv",
        "magnetometer.csv",
        "barometer.csv",
    ):
        (sequence_dir / "iphone" / name).write_text("0.0,0.0,0.0,0.0\n", encoding="utf-8")
    (sequence_dir / "iphone" / "arkit.csv").write_text(
        "0.0,1.0,2.0,3.0,1.0,0.0,0.0,0.0\n0.1,1.5,2.5,3.5,1.0,0.0,0.0,0.0\n",
        encoding="utf-8",
    )
    (sequence_dir / "pixel" / "arcore.csv").write_text(
        "0.0,1.0,2.0,3.0,1.0,0.0,0.0,0.0\n0.1,1.4,2.3,3.3,1.0,0.0,0.0,0.0\n",
        encoding="utf-8",
    )
    (sequence_dir / "ground-truth" / "poses.csv").write_text(
        "0.0,1.0,2.0,3.0,1.0,0.0,0.0,0.0\n0.1,1.5,2.5,3.5,1.0,0.0,0.0,0.0\n0.2,2.0,3.0,4.0,1.0,0.0,0.0,0.0\n",
        encoding="utf-8",
    )
    (dataset_root / "calibration" / "iphone-03.yaml").write_text(
        """
cameras:
- camera:
    image_height: 48
    image_width: 64
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
    return sequence_dir


class FakeStore:
    """Minimal store stand-in for direct page-render tests."""

    def save(self, state: AppState) -> None:
        self.last_state = state.model_copy(deep=True)


class FakeRecord3DRuntime:
    """Minimal runtime stand-in for direct page-render and navigation tests."""

    def __init__(self, snapshot: Record3DStreamSnapshot | None = None) -> None:
        self._snapshot = snapshot or Record3DStreamSnapshot()
        self.stop_calls = 0

    def snapshot(self) -> Record3DStreamSnapshot:
        return self._snapshot

    def stop(self) -> None:
        self.stop_calls += 1
        self._snapshot = Record3DStreamSnapshot()

    def start_usb(self, *, device_index: int) -> None:
        self._snapshot = Record3DStreamSnapshot(
            transport=Record3DTransportId.USB,
            state=PreviewStreamState.CONNECTING,
            source_label=f"USB device #{device_index}",
        )

    def start_wifi_preview(self, *, device_address: str) -> None:
        self._snapshot = Record3DStreamSnapshot(
            transport=Record3DTransportId.WIFI,
            state=PreviewStreamState.CONNECTING,
            source_label=device_address,
        )


class FakeAdvioRuntime:
    """Minimal ADVIO preview runtime stand-in for direct page-render and navigation tests."""

    def __init__(self, snapshot: AdvioPreviewSnapshot | None = None) -> None:
        self._snapshot = snapshot or AdvioPreviewSnapshot()
        self.stop_calls = 0

    def snapshot(self) -> AdvioPreviewSnapshot:
        return self._snapshot

    def stop(self) -> None:
        self.stop_calls += 1
        self._snapshot = AdvioPreviewSnapshot()

    def start(
        self,
        *,
        sequence_id: int,
        sequence_label: str,
        pose_source: AdvioPoseSource,
        stream,
    ) -> None:
        del stream
        self._snapshot = AdvioPreviewSnapshot(
            state=PreviewStreamState.CONNECTING,
            sequence_id=sequence_id,
            sequence_label=sequence_label,
            pose_source=pose_source,
        )


class FakeRunService:
    """Minimal run-service stand-in for direct page-render and navigation tests."""

    def __init__(self, snapshot: RunSnapshot | None = None) -> None:
        self._snapshot = snapshot or RunSnapshot()
        self.stop_calls = 0
        self.start_calls: list[dict[str, object]] = []

    def snapshot(self) -> RunSnapshot:
        return self._snapshot

    def stop_run(self) -> None:
        self.stop_calls += 1
        self._snapshot = RunSnapshot(state=RunState.STOPPED)

    def start_run(self, **kwargs: object) -> None:
        self.start_calls.append(kwargs)
        self._snapshot = RunSnapshot(state=RunState.PREPARING)


class FakePacketStream:
    """Tiny packet-stream stand-in for runtime-controller tests."""

    def __init__(self, *, packets: list[FramePacket], connected_target: object) -> None:
        self.packets = packets
        self.connected_target = connected_target
        self.disconnected = False
        self.wait_calls = 0

    def connect(self) -> object:
        return self.connected_target

    def disconnect(self) -> None:
        self.disconnected = True

    def wait_for_packet(self, timeout_seconds: float | None = None) -> FramePacket:
        index = min(self.wait_calls, len(self.packets) - 1)
        self.wait_calls += 1
        time.sleep(0.01)
        return self.packets[index]


class FakeFramePacketStream:
    """Tiny frame-packet stream stand-in for ADVIO preview runtime tests."""

    def __init__(self, *, packets: list[FramePacket]) -> None:
        self.packets = packets
        self.disconnected = False
        self.wait_calls = 0

    def connect(self) -> str:
        return "connected"

    def disconnect(self) -> None:
        self.disconnected = True

    def wait_for_packet(self, timeout_seconds: float | None = None) -> FramePacket:
        del timeout_seconds
        index = min(self.wait_calls, len(self.packets) - 1)
        self.wait_calls += 1
        time.sleep(0.01)
        return self.packets[index]


def _usb_snapshot(*, confidence: bool) -> Record3DStreamSnapshot:
    confidence_frame = np.array([[0.0, 0.5], [0.75, 1.0]], dtype=np.float32) if confidence else None
    return Record3DStreamSnapshot(
        transport=Record3DTransportId.USB,
        state=PreviewStreamState.STREAMING,
        source_label="device-101",
        received_frames=12,
        measured_fps=29.7,
        trajectory_positions_xyz=np.array(
            [
                [0.0, 0.0, 0.0],
                [0.5, 0.2, 0.1],
                [1.0, 0.4, 0.2],
            ],
            dtype=np.float64,
        ),
        trajectory_timestamps_s=np.array([1.0, 1.1, 1.2], dtype=np.float64),
        latest_packet=FramePacket(
            seq=0,
            timestamp_ns=42_000_000_000,
            arrival_timestamp_s=42.0,
            rgb=np.ones((2, 2, 3), dtype=np.uint8),
            depth=np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32),
            intrinsics=CameraIntrinsics(fx=100.0, fy=200.0, cx=10.0, cy=20.0),
            confidence=confidence_frame,
            metadata={"original_size": [960, 720], "transport": Record3DTransportId.USB.value},
        ),
    )


def _wifi_snapshot() -> Record3DStreamSnapshot:
    return Record3DStreamSnapshot(
        transport=Record3DTransportId.WIFI,
        state=PreviewStreamState.STREAMING,
        source_label="http://myiPhone.local",
        received_frames=8,
        measured_fps=15.5,
        latest_packet=FramePacket(
            seq=0,
            timestamp_ns=24_000_000_000,
            arrival_timestamp_s=24.0,
            rgb=np.ones((2, 2, 3), dtype=np.uint8) * 3,
            depth=np.ones((2, 2), dtype=np.float32),
            intrinsics=CameraIntrinsics(fx=50.0, fy=60.0, cx=5.0, cy=6.0),
            confidence=None,
            metadata={"device_address": "http://myiPhone.local", "transport": Record3DTransportId.WIFI.value},
        ),
    )


def _wait_for(predicate, *, timeout_seconds: float = 1.0) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if predicate():
            return
        time.sleep(0.02)
    raise AssertionError("Timed out waiting for the expected runtime state.")


def test_metrics_service_discovers_and_persists_evo_results(tmp_path: Path) -> None:
    path_config = _build_path_config(tmp_path)
    service = TrajectoryEvaluationService(path_config)

    runs = service.discover_runs("advio-15")

    assert len(runs) == 1
    selection = SelectionSnapshot(
        sequence_slug="advio-15",
        reference_path=resolve_existing_reference_tum(
            path_config.resolve_dataset_dir(DatasetId.ADVIO.value), "advio-15"
        ),
        run=runs[0],
    )

    result = service.compute_evaluation(selection=selection)

    assert result.path.exists()
    assert result.path.name == "trajectory_metrics.json"
    assert result.matched_pairs == 3
    assert result.stats.rmse > 0.0
    assert len(result.trajectories) == 2

    reloaded = service.load_evaluation(selection=selection)

    assert reloaded is not None
    assert reloaded.path == result.path
    assert len(reloaded.trajectories) == 2
    assert reloaded.error_series is not None


def test_metrics_service_fails_when_timestamps_do_not_match(tmp_path: Path) -> None:
    reference_path = tmp_path / ".data" / "advio" / "advio-15" / "ground-truth" / "ground_truth.tum"
    estimate_path = tmp_path / ".artifacts" / "advio-15" / "vista" / "slam" / "trajectory.tum"
    _write_tum(reference_path, [(0.0, 0.0, 0.0, 0.0), (0.1, 1.0, 0.0, 0.0)])
    _write_tum(estimate_path, [(10.0, 0.0, 0.0, 0.0), (10.1, 1.0, 0.0, 0.0)])

    path_config = PathConfig(
        root=tmp_path,
        artifacts_dir=tmp_path / ".artifacts",
        captures_dir=tmp_path / "captures",
    )
    service = TrajectoryEvaluationService(path_config)
    runs = service.discover_runs("advio-15")
    selection = SelectionSnapshot(
        sequence_slug="advio-15",
        reference_path=reference_path,
        run=runs[0],
    )

    with pytest.raises(ValueError, match="No matching trajectory timestamps"):
        service.compute_evaluation(selection=selection)


def test_pipeline_page_computes_evo_preview_from_artifacts(tmp_path: Path) -> None:
    from prml_vslam.app.pages import pipeline as pipeline_page

    pipeline_page._compute_evo_preview.cache_clear()
    from prml_vslam.benchmark import PreparedBenchmarkInputs, ReferenceSource, ReferenceTrajectoryRef

    reference_path = tmp_path / "reference.tum"
    estimate_path = tmp_path / "estimate.tum"
    _write_tum(reference_path, [(0.0, 0.0, 0.0, 0.0), (0.1, 1.0, 0.0, 0.0), (0.2, 2.0, 1.0, 0.0)])
    _write_tum(estimate_path, [(0.0, 0.0, 0.0, 0.0), (0.1, 1.1, 0.1, 0.0), (0.2, 2.2, 1.2, 0.0)])

    snapshot = RunSnapshot(
        sequence_manifest=SequenceManifest(sequence_id="advio-15"),
        benchmark_inputs=PreparedBenchmarkInputs(
            reference_trajectories=[
                ReferenceTrajectoryRef(path=reference_path, source=ReferenceSource.GROUND_TRUTH),
            ]
        ),
        slam=SlamArtifacts(
            trajectory_tum=ArtifactRef(path=estimate_path, kind="tum", fingerprint="trajectory"),
        ),
    )

    evo_preview, evo_error = pipeline_page._resolve_evo_preview(snapshot)

    assert evo_error is None
    assert evo_preview is not None
    assert len(evo_preview.error_series.values) == 3
    assert evo_preview.stats.rmse > 0.0


def test_pipeline_page_evo_preview_fails_when_timestamps_do_not_match(tmp_path: Path) -> None:
    from prml_vslam.app.pages import pipeline as pipeline_page

    pipeline_page._compute_evo_preview.cache_clear()
    reference_path = tmp_path / "reference.tum"
    estimate_path = tmp_path / "estimate.tum"
    _write_tum(reference_path, [(0.0, 0.0, 0.0, 0.0), (0.1, 1.0, 0.0, 0.0)])
    _write_tum(estimate_path, [(10.0, 0.0, 0.0, 0.0), (10.1, 1.0, 0.0, 0.0)])

    with pytest.raises(ValueError, match="No matching timestamps"):
        pipeline_page._compute_evo_preview(
            reference_path=reference_path,
            estimate_path=estimate_path,
            reference_mtime_ns=reference_path.stat().st_mtime_ns,
            estimate_mtime_ns=estimate_path.stat().st_mtime_ns,
        )


def test_pipeline_page_formats_mstr_as_mock_preview() -> None:
    from prml_vslam.app.pages import pipeline as pipeline_page

    assert pipeline_page._pipeline_method_label(MethodId.MSTR) == "Mock Preview"


def test_pipeline_page_metrics_distinguish_packet_and_backend_rates(tmp_path: Path) -> None:
    from prml_vslam.app.pages import pipeline as pipeline_page

    snapshot = StreamingRunSnapshot(
        state=RunState.RUNNING,
        plan=RunPlan(
            run_id="vista-stream",
            mode=PipelineMode.STREAMING,
            method=MethodId.VISTA,
            artifact_root=tmp_path / ".artifacts" / "vista-stream" / "vista",
            source=DatasetSourceSpec(dataset_id=DatasetId.ADVIO, sequence_id="advio-15"),
        ),
        received_frames=12,
        measured_fps=18.5,
        accepted_keyframes=3,
        backend_fps=4.25,
        num_sparse_points=7,
        num_dense_points=41,
    )

    metrics = pipeline_page._pipeline_metrics(snapshot)

    assert metrics[2] == ("Received Frames", "12")
    assert metrics[3] == ("Packet FPS", "18.50 fps")
    assert metrics[4] == ("Accepted Keyframes", "3")
    assert metrics[5] == ("Keyframe FPS", "4.25 fps")


def test_pipeline_page_streaming_tabs_surface_strict_vista_preview_limits(tmp_path: Path) -> None:
    from prml_vslam.app.pages import pipeline as pipeline_page

    class DummyContext:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

    info_messages: list[str] = []
    trajectory_call: dict[str, object] = {}
    snapshot = StreamingRunSnapshot(
        plan=RunPlan(
            run_id="vista-stream",
            mode=PipelineMode.STREAMING,
            method=MethodId.VISTA,
            artifact_root=tmp_path / ".artifacts" / "vista-stream" / "vista",
            source=DatasetSourceSpec(dataset_id=DatasetId.ADVIO, sequence_id="advio-15"),
        ),
        latest_packet=FramePacket(
            seq=0,
            timestamp_ns=0,
            rgb=np.zeros((2, 2, 3), dtype=np.uint8),
            intrinsics=CameraIntrinsics(fx=100.0, fy=100.0, cx=1.0, cy=1.0, width_px=2, height_px=2),
        ),
        latest_slam_update=SlamUpdate(seq=0, timestamp_ns=0, is_keyframe=True),
    )
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(pipeline_page.st, "tabs", lambda *_args, **_kwargs: [DummyContext() for _ in range(4)])
    monkeypatch.setattr(pipeline_page.st, "columns", lambda *args, **kwargs: (DummyContext(), DummyContext()))
    monkeypatch.setattr(pipeline_page.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(pipeline_page.st, "image", lambda *args, **kwargs: None)
    monkeypatch.setattr(pipeline_page.st, "json", lambda *args, **kwargs: None)
    monkeypatch.setattr(pipeline_page.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(pipeline_page.st, "toggle", lambda *args, **kwargs: False)
    monkeypatch.setattr(pipeline_page.st, "info", lambda message, *args, **kwargs: info_messages.append(message))
    monkeypatch.setattr(
        pipeline_page,
        "render_live_trajectory",
        lambda **kwargs: trajectory_call.update(kwargs),
    )
    monkeypatch.setattr(
        pipeline_page,
        "render_camera_intrinsics",
        lambda *args, **kwargs: None,
    )

    pipeline_page._render_pipeline_tabs(snapshot)
    monkeypatch.undo()

    assert pipeline_page._VISTA_POINTMAP_EMPTY_MESSAGE in info_messages
    assert trajectory_call["empty_message"] == pipeline_page._VISTA_TRAJECTORY_EMPTY_MESSAGE


def test_pipeline_page_streaming_tabs_retain_last_valid_vista_preview(tmp_path: Path) -> None:
    from prml_vslam.app.pages import pipeline as pipeline_page

    class DummyContext:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

    image_payloads: list[np.ndarray] = []
    caption_messages: list[str] = []
    info_messages: list[str] = []
    retained_preview = np.full((2, 2, 3), fill_value=17, dtype=np.uint8)
    snapshot = StreamingRunSnapshot(
        plan=RunPlan(
            run_id="vista-stream",
            mode=PipelineMode.STREAMING,
            method=MethodId.VISTA,
            artifact_root=tmp_path / ".artifacts" / "vista-stream" / "vista",
            source=DatasetSourceSpec(dataset_id=DatasetId.ADVIO, sequence_id="advio-15"),
        ),
        latest_packet=FramePacket(
            seq=4,
            timestamp_ns=4,
            rgb=np.ones((2, 2, 3), dtype=np.uint8),
            intrinsics=CameraIntrinsics(fx=100.0, fy=100.0, cx=1.0, cy=1.0, width_px=2, height_px=2),
        ),
        latest_slam_update=SlamUpdate(
            seq=4,
            timestamp_ns=4,
            is_keyframe=False,
            keyframe_index=None,
        ),
        latest_preview_update=SlamUpdate(
            seq=3,
            timestamp_ns=3,
            is_keyframe=True,
            keyframe_index=7,
            preview_rgb=retained_preview,
        ),
        accepted_keyframes=8,
    )

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(pipeline_page.st, "tabs", lambda *_args, **_kwargs: [DummyContext() for _ in range(4)])
    monkeypatch.setattr(pipeline_page.st, "columns", lambda *args, **kwargs: (DummyContext(), DummyContext()))
    monkeypatch.setattr(pipeline_page.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(pipeline_page.st, "image", lambda image, *args, **kwargs: image_payloads.append(image))
    monkeypatch.setattr(pipeline_page.st, "json", lambda *args, **kwargs: None)
    monkeypatch.setattr(pipeline_page.st, "caption", lambda message, *args, **kwargs: caption_messages.append(message))
    monkeypatch.setattr(pipeline_page.st, "toggle", lambda *args, **kwargs: False)
    monkeypatch.setattr(pipeline_page.st, "info", lambda message, *args, **kwargs: info_messages.append(message))
    monkeypatch.setattr(
        pipeline_page,
        "render_live_trajectory",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        pipeline_page,
        "render_camera_intrinsics",
        lambda *args, **kwargs: None,
    )

    pipeline_page._render_pipeline_tabs(snapshot)
    monkeypatch.undo()

    assert any(image is retained_preview for image in image_payloads)
    assert "Showing last valid keyframe artifact from keyframe 7." in caption_messages
    assert pipeline_page._VISTA_POINTMAP_EMPTY_MESSAGE not in info_messages


def test_pipeline_page_streaming_tabs_render_mock_preview_outputs(tmp_path: Path) -> None:
    from prml_vslam.app.pages import pipeline as pipeline_page

    class DummyContext:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

    preview_image = np.full((2, 2), fill_value=7.0, dtype=np.float32)
    image_payloads: list[np.ndarray] = []
    trajectory_call: dict[str, object] = {}
    snapshot = StreamingRunSnapshot(
        plan=RunPlan(
            run_id="mock-stream",
            mode=PipelineMode.STREAMING,
            method=MethodId.MSTR,
            artifact_root=tmp_path / ".artifacts" / "mock-stream" / "mstr",
            source=DatasetSourceSpec(dataset_id=DatasetId.ADVIO, sequence_id="advio-15"),
        ),
        latest_packet=FramePacket(
            seq=1,
            timestamp_ns=1,
            rgb=np.ones((2, 2, 3), dtype=np.uint8),
            intrinsics=CameraIntrinsics(fx=100.0, fy=100.0, cx=1.0, cy=1.0, width_px=2, height_px=2),
        ),
        latest_slam_update=SlamUpdate(
            seq=1,
            timestamp_ns=1,
            pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=0.0, tz=0.0),
            num_sparse_points=12,
            num_dense_points=4,
            pointmap=np.zeros((2, 2, 3), dtype=np.float32),
            preview_rgb=None,
        ),
        latest_preview_update=SlamUpdate(
            seq=1,
            timestamp_ns=1,
            pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=0.0, tz=0.0),
            num_sparse_points=12,
            num_dense_points=4,
            pointmap=np.zeros((2, 2, 3), dtype=np.float32),
            preview_rgb=None,
        ),
        accepted_keyframes=1,
        backend_fps=9.0,
        trajectory_positions_xyz=np.asarray([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]], dtype=np.float64),
        trajectory_timestamps_s=np.asarray([0.0, 1.0], dtype=np.float64),
    )

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(pipeline_page.st, "tabs", lambda *_args, **_kwargs: [DummyContext() for _ in range(4)])
    monkeypatch.setattr(pipeline_page.st, "columns", lambda *args, **kwargs: (DummyContext(), DummyContext()))
    monkeypatch.setattr(pipeline_page.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(pipeline_page.st, "image", lambda image, *args, **kwargs: image_payloads.append(image))
    monkeypatch.setattr(pipeline_page.st, "json", lambda *args, **kwargs: None)
    monkeypatch.setattr(pipeline_page.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(pipeline_page.st, "toggle", lambda *args, **kwargs: False)
    monkeypatch.setattr(pipeline_page.st, "info", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        pipeline_page,
        "render_live_trajectory",
        lambda **kwargs: trajectory_call.update(kwargs),
    )
    monkeypatch.setattr(
        pipeline_page,
        "render_camera_intrinsics",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(pipeline_page, "_pointmap_preview_image", lambda pointmap: preview_image)

    pipeline_page._render_pipeline_tabs(snapshot)
    monkeypatch.undo()

    assert any(image is preview_image for image in image_payloads)
    assert np.array_equal(trajectory_call["positions_xyz"], snapshot.trajectory_positions_xyz)
    assert np.array_equal(trajectory_call["timestamps_s"], snapshot.trajectory_timestamps_s)


def test_pipeline_page_preview_status_message_marks_current_keyframe() -> None:
    from prml_vslam.app.pages import pipeline as pipeline_page

    update = SlamUpdate(
        seq=3,
        timestamp_ns=3,
        is_keyframe=True,
        keyframe_index=5,
        preview_rgb=np.ones((2, 2, 3), dtype=np.uint8),
    )
    snapshot = StreamingRunSnapshot(
        latest_slam_update=update,
        latest_preview_update=update,
    )

    assert pipeline_page._preview_status_message(snapshot) == pipeline_page._VISTA_PREVIEW_CURRENT_MESSAGE


def test_pipeline_page_pointmap_preview_image_uses_generic_projection() -> None:
    from prml_vslam.app.pages import pipeline as pipeline_page

    pointmap = np.array(
        [
            [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]],
            [[7.0, 8.0, 9.0], [10.0, 11.0, 12.0]],
        ],
        dtype=np.float32,
    )

    preview = pipeline_page._pointmap_preview_image(pointmap)

    assert preview is not None
    assert preview.shape == (2, 2)
    assert not np.array_equal(preview, pointmap[..., 2])


def test_packet_session_metrics_separate_packet_and_keyframe_history() -> None:
    from prml_vslam.utils.packet_session import PacketSessionMetrics

    metrics = PacketSessionMetrics(fps_window_size=4, trajectory_window_size=4)
    metrics.record_packet(arrival_time_s=0.0)
    metrics.record_packet(arrival_time_s=1.0)
    metrics.record_keyframe(
        arrival_time_s=1.0,
        position_xyz=np.array([1.0, 0.0, 0.0], dtype=np.float64),
        trajectory_time_s=0.5,
    )
    fields = metrics.snapshot_fields()

    assert fields["received_frames"] == 2
    assert fields["accepted_keyframes"] == 1
    assert fields["trajectory_positions_xyz"].shape == (1, 3)
    assert fields["trajectory_timestamps_s"].shape == (1,)
    assert fields["backend_fps"] == 0.0


def test_streaming_keyframe_gate_rejects_small_pose_jitter() -> None:
    update_jitter = SlamUpdate(seq=1, timestamp_ns=1, is_keyframe=False)
    update_keyframe = SlamUpdate(seq=2, timestamp_ns=2, is_keyframe=True)

    assert _is_keyframe_like_update(update_jitter) is False
    assert _is_keyframe_like_update(update_keyframe) is True


def test_pipeline_page_action_starts_pipeline_session_once_from_selected_toml(tmp_path: Path) -> None:
    from prml_vslam.app.pages import pipeline as pipeline_page

    source = object()
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts", captures_dir=tmp_path / "captures")
    config_path = _write_pipeline_config(path_config)

    class AdvioServiceSpy:
        def __init__(self) -> None:
            self.source_calls: list[tuple[int, AdvioPoseSource, bool]] = []

        def local_scene_statuses(self) -> list[SimpleNamespace]:
            return [
                SimpleNamespace(
                    replay_ready=True,
                    scene=SimpleNamespace(sequence_id=15, sequence_slug="advio-15", display_name="advio-15"),
                )
            ]

        def scene(self, sequence_id: int) -> SimpleNamespace:
            return SimpleNamespace(sequence_slug=f"advio-{sequence_id:02d}", display_name=f"advio-{sequence_id:02d}")

        def build_streaming_source(
            self,
            *,
            sequence_id: int,
            pose_source: AdvioPoseSource,
            respect_video_rotation: bool,
        ) -> object:
            self.source_calls.append((sequence_id, pose_source, respect_video_rotation))
            return source

        def build_sequence_manifest(self, **_: object) -> object:
            raise AssertionError("Pipeline page should not materialize the sequence manifest directly.")

    runtime = FakeRunService()
    context = SimpleNamespace(
        path_config=path_config,
        advio_service=AdvioServiceSpy(),
        run_service=runtime,
        state=AppState(),
        store=FakeStore(),
    )

    error_message = pipeline_page._handle_pipeline_page_action(
        context,
        pipeline_page.PipelinePageAction(
            config_path=config_path,
            source_kind=PipelineSourceId.ADVIO,
            advio_sequence_id=15,
            mode=PipelineMode.OFFLINE,
            method=MethodId.VISTA,
            pose_source=AdvioPoseSource.GROUND_TRUTH,
            respect_video_rotation=True,
            start_requested=True,
        ),
    )

    assert error_message is None
    assert context.advio_service.source_calls == []
    assert context.state.pipeline.config_path == config_path
    assert len(runtime.start_calls) == 1
    assert runtime.start_calls[0]["runtime_source"] is None
    request = runtime.start_calls[0]["request"]
    assert request.source.dataset_id is DatasetId.ADVIO
    assert request.slam.method is MethodId.VISTA
    assert request.benchmark.trajectory.enabled is False
    assert request.benchmark.cloud.enabled is False
    assert request.benchmark.efficiency.enabled is False


def test_pipeline_request_builds_record3d_usb_source_from_action(tmp_path: Path) -> None:
    from prml_vslam.app.pages import pipeline as pipeline_page

    context = SimpleNamespace(path_config=PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts"))

    request, error_message = pipeline_page._build_request_from_action(
        context,
        pipeline_page.PipelinePageAction(
            **_record3d_pipeline_action(
                transport=Record3DTransportId.USB,
                usb_device_index=2,
                persist_capture=False,
            )
        ),
    )

    assert error_message is None
    assert request is not None
    assert isinstance(request.source, Record3DLiveSourceSpec)
    assert request.source.transport is LiveTransportId.USB

    assert request.source.device_index == 2
    assert request.source.device_address == ""
    assert request.source.persist_capture is False


def test_pipeline_request_builds_record3d_wifi_source_from_action(tmp_path: Path) -> None:
    from prml_vslam.app.pages import pipeline as pipeline_page

    context = SimpleNamespace(path_config=PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts"))

    request, error_message = pipeline_page._build_request_from_action(
        context,
        pipeline_page.PipelinePageAction(
            **_record3d_pipeline_action(
                transport=Record3DTransportId.WIFI,
                wifi_device_address="myiPhone.local",
            )
        ),
    )

    assert error_message is None
    assert request is not None
    assert isinstance(request.source, Record3DLiveSourceSpec)
    assert request.source.transport is LiveTransportId.WIFI
    assert request.source.device_index is None
    assert request.source.device_address == "myiPhone.local"
    assert request.source.persist_capture is True


def test_pipeline_source_input_error_requires_wifi_device_address() -> None:
    from prml_vslam.app.pages import pipeline as pipeline_page

    error_message = pipeline_page._source_input_error(
        pipeline_page.PipelinePageAction(**_record3d_pipeline_action(transport=Record3DTransportId.WIFI))
    )

    assert error_message == "Enter a Record3D Wi-Fi preview device address."


def test_pipeline_streaming_source_supports_record3d_wifi() -> None:
    from prml_vslam.app.pages import pipeline as pipeline_page

    context = SimpleNamespace()
    source = pipeline_page._build_streaming_source_from_action(
        context,
        pipeline_page.PipelinePageAction(
            **_record3d_pipeline_action(
                transport=Record3DTransportId.WIFI,
                wifi_device_address="myiPhone.local",
            )
        ),
    )

    assert source.config.transport is Record3DTransportId.WIFI
    assert source.config.device_address == "myiPhone.local"


def test_pipeline_streaming_source_requires_wifi_device_address() -> None:
    from prml_vslam.app.pages import pipeline as pipeline_page

    context = SimpleNamespace()

    with pytest.raises(ValueError, match="Enter a Record3D Wi-Fi preview device address."):
        pipeline_page._build_streaming_source_from_action(
            context,
            pipeline_page.PipelinePageAction(**_record3d_pipeline_action(transport=Record3DTransportId.WIFI)),
        )


def test_parse_optional_int_rejects_invalid_input() -> None:
    from prml_vslam.app.pages import pipeline as pipeline_page

    value, error_message = pipeline_page._parse_optional_int(raw_value="not-a-number", field_label="SLAM Max Frames")

    assert value is None
    assert error_message == "Enter a whole number for `SLAM Max Frames` or leave the field blank."


def test_pipeline_page_state_sync_hydrates_record3d_usb_template(tmp_path: Path) -> None:
    from prml_vslam.app.pages import pipeline as pipeline_page

    context = SimpleNamespace(
        state=AppState(),
        store=FakeStore(),
    )
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts")
    request = _record3d_pipeline_request(
        transport=Record3DTransportId.USB,
        output_dir=path_config.artifacts_dir,
        persist_capture=False,
        device_index=3,
    )

    pipeline_page._sync_pipeline_page_state_from_template(
        context=context,
        config_path=tmp_path / "record3d-usb.toml",
        request=request,
        statuses=[],
    )

    assert context.state.pipeline.source_kind is PipelineSourceId.RECORD3D
    assert context.state.pipeline.record3d_transport is Record3DTransportId.USB
    assert context.state.pipeline.record3d_usb_device_index == 3
    assert context.state.pipeline.record3d_persist_capture is False


def test_pipeline_page_state_sync_hydrates_record3d_wifi_template(tmp_path: Path) -> None:
    from prml_vslam.app.pages import pipeline as pipeline_page

    context = SimpleNamespace(
        state=AppState(),
        store=FakeStore(),
    )
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts")
    request = _record3d_pipeline_request(
        transport=Record3DTransportId.WIFI,
        output_dir=path_config.artifacts_dir,
        device_address="myiPhone.local",
    )

    pipeline_page._sync_pipeline_page_state_from_template(
        context=context,
        config_path=tmp_path / "record3d-wifi.toml",
        request=request,
        statuses=[],
    )

    assert context.state.pipeline.source_kind is PipelineSourceId.RECORD3D
    assert context.state.pipeline.record3d_transport is Record3DTransportId.WIFI
    assert context.state.pipeline.record3d_wifi_device_address == "myiPhone.local"
    assert context.state.pipeline.record3d_persist_capture is True


def test_load_pipeline_request_toml_parses_record3d_wifi_source(tmp_path: Path) -> None:
    from prml_vslam.pipeline.demo import load_run_request_toml

    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts")
    config_path = _write_pipeline_config(
        path_config,
        name="record3d-wifi.toml",
        source_block=(
            'source_id = "record3d"\ntransport = "wifi"\npersist_capture = false\ndevice_address = "myiPhone.local"'
        ),
    )

    request = load_run_request_toml(path_config=path_config, config_path=config_path)

    assert isinstance(request.source, Record3DLiveSourceSpec)
    assert request.source.transport is LiveTransportId.WIFI
    assert request.source.persist_capture is False
    assert request.source.device_address == "myiPhone.local"


def test_pipeline_demo_controls_show_only_stop_button_while_run_is_active() -> None:
    from prml_vslam.app.pages import pipeline as pipeline_page

    class DummyContext:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

    class AdvioServiceSpy:
        def local_scene_statuses(self) -> list[SimpleNamespace]:
            return [SimpleNamespace(scene=SimpleNamespace(sequence_id=15), replay_ready=True)]

        def scene(self, sequence_id: int) -> SimpleNamespace:
            return SimpleNamespace(display_name=f"advio-{sequence_id:02d} · Mall 01")

    seen_labels: list[str] = []
    config_path = Path("/tmp/advio-offline-advio-15-vista.toml")
    context = SimpleNamespace(
        path_config=SimpleNamespace(),
        advio_service=AdvioServiceSpy(),
        run_service=FakeRunService(snapshot=RunSnapshot(state=RunState.RUNNING)),
        state=AppState(),
        store=FakeStore(),
    )

    def fake_button(label: str, *args, **kwargs) -> bool:
        seen_labels.append(label)
        return False

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(pipeline_page, "render_page_intro", lambda *args, **kwargs: None)
    monkeypatch.setattr(pipeline_page.st, "container", lambda *args, **kwargs: DummyContext())
    monkeypatch.setattr(pipeline_page.st, "subheader", lambda *args, **kwargs: None)
    monkeypatch.setattr(pipeline_page.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(pipeline_page.st, "selectbox", lambda *args, **kwargs: config_path)
    monkeypatch.setattr(pipeline_page.st, "columns", lambda *args, **kwargs: (DummyContext(), DummyContext()))
    monkeypatch.setattr(pipeline_page.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(pipeline_page.st, "json", lambda *args, **kwargs: None)
    monkeypatch.setattr(pipeline_page.st, "warning", lambda *args, **kwargs: None)
    monkeypatch.setattr(pipeline_page.st, "dataframe", lambda *args, **kwargs: None)
    monkeypatch.setattr(pipeline_page, "_discover_pipeline_config_paths", lambda *_args, **_kwargs: [config_path])
    monkeypatch.setattr(
        pipeline_page,
        "_load_pipeline_request",
        lambda *_args, **_kwargs: (_load_pipeline_request_fixture(), None),
    )
    monkeypatch.setattr(
        pipeline_page,
        "_render_request_editor",
        lambda **kwargs: (
            pipeline_page.PipelinePageAction(
                config_path=config_path,
                source_kind=PipelineSourceId.ADVIO,
                advio_sequence_id=15,
                mode=PipelineMode.OFFLINE,
                method=MethodId.VISTA,
                pose_source=AdvioPoseSource.GROUND_TRUTH,
            ),
            None,
            None,
        ),
    )
    monkeypatch.setattr(
        pipeline_page, "_build_request_from_action", lambda *_args, **_kwargs: (_load_pipeline_request_fixture(), None)
    )
    monkeypatch.setattr(
        pipeline_page,
        "_build_preview_plan",
        lambda *_args, **_kwargs: (SimpleNamespace(stages=[], stage_rows=lambda: []), None),
    )
    monkeypatch.setattr(pipeline_page.st, "button", fake_button)
    monkeypatch.setattr(pipeline_page, "_handle_pipeline_page_action", lambda **kwargs: None)
    monkeypatch.setattr(pipeline_page, "render_live_fragment", lambda *args, **kwargs: None)

    pipeline_page.render(context)
    monkeypatch.undo()

    assert seen_labels == ["Stop run"]


def test_pipeline_page_reruns_after_successful_start_action() -> None:
    from prml_vslam.app.pages import pipeline as pipeline_page

    class DummyContext:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

    rerun_calls: list[bool] = []
    config_path = Path("/tmp/advio-offline-advio-15-vista.toml")
    context = SimpleNamespace(
        path_config=SimpleNamespace(),
        advio_service=SimpleNamespace(
            local_scene_statuses=lambda: [
                SimpleNamespace(
                    replay_ready=True,
                    scene=SimpleNamespace(sequence_id=15, sequence_slug="advio-15", display_name="advio-15"),
                )
            ],
            scene=lambda sequence_id: SimpleNamespace(display_name=f"advio-{sequence_id:02d} · Mall 01"),
        ),
        run_service=FakeRunService(),
        state=AppState(),
        store=FakeStore(),
    )

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(pipeline_page, "render_page_intro", lambda *args, **kwargs: None)
    monkeypatch.setattr(pipeline_page.st, "container", lambda *args, **kwargs: DummyContext())
    monkeypatch.setattr(pipeline_page.st, "subheader", lambda *args, **kwargs: None)
    monkeypatch.setattr(pipeline_page.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(pipeline_page.st, "selectbox", lambda *args, **kwargs: config_path)
    monkeypatch.setattr(pipeline_page.st, "columns", lambda *args, **kwargs: (DummyContext(), DummyContext()))
    monkeypatch.setattr(pipeline_page.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(pipeline_page.st, "json", lambda *args, **kwargs: None)
    monkeypatch.setattr(pipeline_page.st, "warning", lambda *args, **kwargs: None)
    monkeypatch.setattr(pipeline_page.st, "dataframe", lambda *args, **kwargs: None)
    monkeypatch.setattr(pipeline_page, "_discover_pipeline_config_paths", lambda *_args, **_kwargs: [config_path])
    monkeypatch.setattr(
        pipeline_page,
        "_load_pipeline_request",
        lambda *_args, **_kwargs: (_load_pipeline_request_fixture(), None),
    )
    monkeypatch.setattr(
        pipeline_page,
        "_render_request_editor",
        lambda **kwargs: (
            pipeline_page.PipelinePageAction(
                config_path=config_path,
                source_kind=PipelineSourceId.ADVIO,
                advio_sequence_id=15,
                mode=PipelineMode.OFFLINE,
                method=MethodId.VISTA,
                pose_source=AdvioPoseSource.GROUND_TRUTH,
            ),
            None,
            None,
        ),
    )
    monkeypatch.setattr(
        pipeline_page, "_build_request_from_action", lambda *_args, **_kwargs: (_load_pipeline_request_fixture(), None)
    )
    monkeypatch.setattr(
        pipeline_page,
        "_build_preview_plan",
        lambda *_args, **_kwargs: (SimpleNamespace(stages=[], stage_rows=lambda: []), None),
    )
    monkeypatch.setattr(
        pipeline_page.st,
        "button",
        lambda label, *args, **kwargs: label == "Start run",
    )
    monkeypatch.setattr(pipeline_page, "_handle_pipeline_page_action", lambda **kwargs: None)
    monkeypatch.setattr(pipeline_page.st, "rerun", lambda: rerun_calls.append(True))
    monkeypatch.setattr(pipeline_page, "render_live_fragment", lambda *args, **kwargs: None)

    pipeline_page.render(context)
    monkeypatch.undo()

    assert rerun_calls == [True]


def test_advio_download_form_returns_typed_request_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from prml_vslam.app.advio_controller import AdvioDownloadFormData
    from prml_vslam.app.pages import advio as advio_page
    from prml_vslam.datasets.advio import AdvioDatasetService, AdvioDownloadPreset, AdvioModality

    class DummyContext:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

    selections = iter([[15], [AdvioModality.CALIBRATION]])
    monkeypatch.setattr(advio_page.st, "form", lambda *args, **kwargs: DummyContext())
    monkeypatch.setattr(advio_page.st, "multiselect", lambda *args, **kwargs: next(selections))
    monkeypatch.setattr(advio_page.st, "selectbox", lambda *args, **kwargs: AdvioDownloadPreset.FULL)
    monkeypatch.setattr(advio_page.st, "toggle", lambda *args, **kwargs: True)
    monkeypatch.setattr(advio_page.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(advio_page.st, "form_submit_button", lambda *args, **kwargs: True)

    context = SimpleNamespace(
        state=AppState(),
        store=FakeStore(),
        advio_service=AdvioDatasetService(PathConfig(root=tmp_path)),
        advio_runtime=FakeAdvioRuntime(),
    )
    form = advio_page._render_download_form(context)

    assert isinstance(form, AdvioDownloadFormData)
    assert form.submitted is True
    assert form.request.sequence_ids == [15]
    assert form.request.preset is AdvioDownloadPreset.FULL
    assert form.request.modalities == [AdvioModality.CALIBRATION]
    assert form.request.overwrite is True
    assert context.state.advio.selected_sequence_ids == [15]
    assert context.state.advio.download_preset is AdvioDownloadPreset.FULL
    assert context.state.advio.selected_modalities == [AdvioModality.CALIBRATION]
    assert context.state.advio.overwrite_existing is True


def test_advio_page_data_treats_empty_download_selection_as_full_catalog() -> None:
    from prml_vslam.app.advio_controller import AdvioDownloadFormData, build_advio_page_data
    from prml_vslam.datasets.advio import AdvioDatasetSummary, AdvioDownloadRequest

    class ServiceSpy:
        def __init__(self) -> None:
            self.requests: list[AdvioDownloadRequest] = []

        def download(self, request: AdvioDownloadRequest) -> SimpleNamespace:
            self.requests.append(request)
            return SimpleNamespace(
                sequence_ids=[15, 16],
                downloaded_archive_count=1,
                written_path_count=2,
            )

        def local_scene_statuses(self) -> list[object]:
            return []

        def summarize(self, statuses: list[object]) -> AdvioDatasetSummary:
            return AdvioDatasetSummary(
                total_scene_count=0,
                local_scene_count=0,
                replay_ready_scene_count=0,
                offline_ready_scene_count=0,
                full_scene_count=0,
                cached_archive_count=0,
                total_remote_archive_bytes=0,
            )

    service = ServiceSpy()
    page_data = build_advio_page_data(
        SimpleNamespace(advio_service=service),
        AdvioDownloadFormData(request=AdvioDownloadRequest(sequence_ids=[]), submitted=True),
    )

    assert page_data.notice_level == "success"
    assert "Prepared 2 scene(s)" in page_data.notice_message
    assert len(service.requests) == 1
    assert service.requests[0].sequence_ids == []


def test_advio_controller_handles_preview_start_and_stop() -> None:
    from prml_vslam.app.advio_controller import AdvioPreviewFormData, handle_advio_preview_action

    stream = object()

    class ServiceSpy:
        def __init__(self) -> None:
            self.preview_calls: list[tuple[int, AdvioPoseSource, bool]] = []

        def scene(self, sequence_id: int) -> SimpleNamespace:
            return SimpleNamespace(display_name=f"advio-{sequence_id:02d} · Office 03")

        def open_preview_stream(
            self,
            *,
            sequence_id: int,
            pose_source: AdvioPoseSource,
            respect_video_rotation: bool,
        ) -> object:
            self.preview_calls.append((sequence_id, pose_source, respect_video_rotation))
            return stream

    class RuntimeSpy:
        def __init__(self) -> None:
            self.start_calls: list[dict[str, object]] = []
            self.stop_calls = 0

        def start(self, **kwargs: object) -> None:
            self.start_calls.append(kwargs)

        def stop(self) -> None:
            self.stop_calls += 1

    service = ServiceSpy()
    runtime = RuntimeSpy()
    context = SimpleNamespace(
        state=AppState(),
        store=FakeStore(),
        advio_service=service,
        advio_runtime=runtime,
    )

    error_message = handle_advio_preview_action(
        context,
        AdvioPreviewFormData(
            sequence_id=15,
            pose_source=AdvioPoseSource.GROUND_TRUTH,
            respect_video_rotation=True,
            start_requested=True,
        ),
    )

    assert error_message is None
    assert context.state.advio.preview_is_running is True
    assert service.preview_calls == [(15, AdvioPoseSource.GROUND_TRUTH, True)]
    assert runtime.start_calls == [
        {
            "sequence_id": 15,
            "sequence_label": "advio-15 · Office 03",
            "pose_source": AdvioPoseSource.GROUND_TRUTH,
            "stream": stream,
        }
    ]

    error_message = handle_advio_preview_action(
        context,
        AdvioPreviewFormData(
            sequence_id=15,
            pose_source=AdvioPoseSource.GROUND_TRUTH,
            stop_requested=True,
        ),
    )

    assert error_message is None
    assert context.state.advio.preview_is_running is False
    assert runtime.stop_calls == 1


def test_advio_loop_preview_shows_only_stop_button_while_preview_is_running() -> None:
    from prml_vslam.app.pages import advio as advio_page

    class DummyContext:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

    seen_labels: list[str] = []
    context = SimpleNamespace(
        state=AppState(advio=AdvioPageState(preview_is_running=True)),
        store=FakeStore(),
        advio_service=SimpleNamespace(
            scene=lambda sequence_id: SimpleNamespace(display_name=f"advio-{sequence_id:02d} · Mall 01")
        ),
        advio_runtime=FakeAdvioRuntime(),
    )
    statuses = [SimpleNamespace(scene=SimpleNamespace(sequence_id=15), replay_ready=True)]

    def fake_selectbox(label: str, *args, **kwargs):
        return {
            "Preview Scene": 15,
            "Pose Source": AdvioPoseSource.GROUND_TRUTH,
        }[label]

    def fake_button(label: str, *args, **kwargs) -> bool:
        seen_labels.append(label)
        return False

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(advio_page.st, "container", lambda *args, **kwargs: DummyContext())
    monkeypatch.setattr(advio_page.st, "subheader", lambda *args, **kwargs: None)
    monkeypatch.setattr(advio_page.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(advio_page.st, "selectbox", fake_selectbox)
    monkeypatch.setattr(advio_page.st, "toggle", lambda *args, **kwargs: False)
    monkeypatch.setattr(advio_page.st, "button", fake_button)
    monkeypatch.setattr(advio_page, "handle_advio_preview_action", lambda *args, **kwargs: None)
    monkeypatch.setattr(advio_page, "render_live_fragment", lambda *args, **kwargs: None)

    advio_page._render_loop_preview(context, statuses)
    monkeypatch.undo()

    assert seen_labels == ["Stop preview"]


def test_advio_loop_preview_reruns_after_successful_start_action() -> None:
    from prml_vslam.app.pages import advio as advio_page

    class DummyContext:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

    rerun_calls: list[bool] = []
    context = SimpleNamespace(
        state=AppState(),
        store=FakeStore(),
        advio_service=SimpleNamespace(
            scene=lambda sequence_id: SimpleNamespace(display_name=f"advio-{sequence_id:02d} · Mall 01")
        ),
        advio_runtime=FakeAdvioRuntime(),
    )
    statuses = [SimpleNamespace(scene=SimpleNamespace(sequence_id=15), replay_ready=True)]

    def fake_selectbox(label: str, *args, **kwargs):
        return {
            "Preview Scene": 15,
            "Pose Source": AdvioPoseSource.GROUND_TRUTH,
        }[label]

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(advio_page.st, "container", lambda *args, **kwargs: DummyContext())
    monkeypatch.setattr(advio_page.st, "subheader", lambda *args, **kwargs: None)
    monkeypatch.setattr(advio_page.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(advio_page.st, "selectbox", fake_selectbox)
    monkeypatch.setattr(advio_page.st, "toggle", lambda *args, **kwargs: False)
    monkeypatch.setattr(
        advio_page.st,
        "button",
        lambda label, *args, **kwargs: label == "Start preview",
    )
    monkeypatch.setattr(advio_page, "handle_advio_preview_action", lambda *args, **kwargs: None)
    monkeypatch.setattr(advio_page.st, "rerun", lambda: rerun_calls.append(True))
    monkeypatch.setattr(advio_page, "render_live_fragment", lambda *args, **kwargs: None)

    advio_page._render_loop_preview(context, statuses)
    monkeypatch.undo()

    assert rerun_calls == [True]


def test_advio_page_warns_when_local_scene_is_not_offline_ready(tmp_path: Path) -> None:
    dataset_root = tmp_path / ".data" / "advio"
    sequence_dir = dataset_root / "advio-15" / "iphone"
    sequence_dir.mkdir(parents=True, exist_ok=True)
    (sequence_dir / "frames.mov").write_bytes(b"")
    (sequence_dir / "frames.csv").write_text("0.0,0\n0.1,1\n", encoding="utf-8")

    def _render_advio_page_script(root_path: str) -> None:
        from pathlib import Path
        from types import SimpleNamespace

        from prml_vslam.app.models import AppState
        from prml_vslam.app.pages.advio import render as render_advio_page
        from prml_vslam.datasets.advio import AdvioDatasetService
        from prml_vslam.utils import PathConfig

        class _Store:
            def save(self, state: AppState) -> None:
                self.last_state = state.model_copy(deep=True)

        class _AdvioRuntime:
            def snapshot(self):
                from prml_vslam.app.models import AdvioPreviewSnapshot

                return AdvioPreviewSnapshot()

            def stop(self) -> None:
                return None

            def start(self, *, sequence_id: int, sequence_label: str, pose_source, stream) -> None:
                del sequence_id, sequence_label, pose_source, stream
                return None

        context = SimpleNamespace(
            state=AppState(),
            store=_Store(),
            advio_service=AdvioDatasetService(PathConfig(root=Path(root_path))),
            advio_runtime=_AdvioRuntime(),
        )
        render_advio_page(context)

    at = AppTest.from_function(_render_advio_page_script, args=(str(tmp_path),))
    at.run()

    assert any(item.value == "Sequence Explorer" for item in at.subheader)
    assert any(item.value == "Loop Preview" for item in at.subheader)
    assert any("none are offline-ready yet" in item.value.lower() for item in at.warning)


def test_record3d_transport_change_does_not_start_stream_until_submit() -> None:
    from prml_vslam.app import record3d_controls
    from prml_vslam.app.pages import record3d as record3d_page
    from prml_vslam.app.record3d_controller import handle_record3d_page_action

    class RuntimeSpy:
        def __init__(self) -> None:
            self.start_usb_calls = 0
            self.start_wifi_preview_calls = 0

        def snapshot(self) -> Record3DStreamSnapshot:
            return Record3DStreamSnapshot()

        def stop(self) -> None:
            return None

        def start_usb(self, *, device_index: int) -> None:
            self.start_usb_calls += 1

        def start_wifi_preview(self, *, device_address: str) -> None:
            self.start_wifi_preview_calls += 1

    class DummyContext:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

    runtime = RuntimeSpy()
    context = SimpleNamespace(
        state=AppState(record3d=Record3DPageState(transport=Record3DTransportId.USB, is_running=False)),
        store=FakeStore(),
        record3d_runtime=runtime,
    )

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        record3d_controls,
        "list_record3d_usb_devices",
        lambda: [Record3DDevice(product_id=101, udid="device-101")],
    )
    monkeypatch.setattr(record3d_page.st, "sidebar", DummyContext())
    monkeypatch.setattr(record3d_page.st, "subheader", lambda *args, **kwargs: None)
    monkeypatch.setattr(record3d_page.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(record3d_page.st, "segmented_control", lambda *args, **kwargs: Record3DTransportId.WIFI)
    monkeypatch.setattr(record3d_page.st, "text_input", lambda *args, **kwargs: "192.168.159.24")
    monkeypatch.setattr(record3d_page.st, "button", lambda *args, **kwargs: False)
    monkeypatch.setattr(record3d_page.st, "expander", lambda *args, **kwargs: DummyContext())
    monkeypatch.setattr(record3d_page.st, "write", lambda *args, **kwargs: None)
    monkeypatch.setattr(record3d_page.st, "warning", lambda *args, **kwargs: None)
    monkeypatch.setattr(record3d_page.st, "info", lambda *args, **kwargs: None)

    action = record3d_page._render_sidebar_controls(context)
    monkeypatch.undo()

    assert runtime.start_usb_calls == 0
    assert runtime.start_wifi_preview_calls == 0
    assert context.state.record3d.wifi_device_address == "192.168.159.24"
    assert action.transport is Record3DTransportId.WIFI
    assert action.start_requested is False
    assert action.stop_requested is False
    assert context.state.record3d.transport is Record3DTransportId.USB

    handle_record3d_page_action(context, action)

    assert runtime.start_usb_calls == 0
    assert runtime.start_wifi_preview_calls == 0
    assert context.state.record3d.transport is Record3DTransportId.WIFI


def test_record3d_wifi_start_button_enables_when_user_enters_address() -> None:
    from prml_vslam.app.pages import record3d as record3d_page

    class DummyContext:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

    captured_start_disabled: list[bool] = []
    context = SimpleNamespace(
        state=AppState(record3d=Record3DPageState(transport=Record3DTransportId.WIFI, is_running=False)),
        store=FakeStore(),
        record3d_runtime=FakeRecord3DRuntime(),
    )

    def fake_button(label: str, *args, **kwargs) -> bool:
        if label == "Start stream":
            captured_start_disabled.append(bool(kwargs.get("disabled", False)))
        return False

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(record3d_page.st, "sidebar", DummyContext())
    monkeypatch.setattr(record3d_page.st, "subheader", lambda *args, **kwargs: None)
    monkeypatch.setattr(record3d_page.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(record3d_page.st, "segmented_control", lambda *args, **kwargs: Record3DTransportId.WIFI)
    monkeypatch.setattr(record3d_page.st, "text_input", lambda *args, **kwargs: "192.168.159.24")
    monkeypatch.setattr(record3d_page.st, "button", fake_button)
    monkeypatch.setattr(record3d_page.st, "expander", lambda *args, **kwargs: DummyContext())
    monkeypatch.setattr(record3d_page.st, "write", lambda *args, **kwargs: None)
    monkeypatch.setattr(record3d_page.st, "warning", lambda *args, **kwargs: None)
    monkeypatch.setattr(record3d_page.st, "info", lambda *args, **kwargs: None)

    action = record3d_page._render_sidebar_controls(context)
    monkeypatch.undo()

    assert captured_start_disabled == [False]
    assert action.wifi_device_address == "192.168.159.24"
    assert action.start_requested is False


def test_record3d_sidebar_shows_only_stop_button_while_stream_is_running() -> None:
    from prml_vslam.app import record3d_controls
    from prml_vslam.app.pages import record3d as record3d_page

    class DummyContext:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

    seen_labels: list[str] = []
    context = SimpleNamespace(
        state=AppState(record3d=Record3DPageState(is_running=True)),
        store=FakeStore(),
        record3d_runtime=FakeRecord3DRuntime(),
    )

    def fake_button(label: str, *args, **kwargs) -> bool:
        seen_labels.append(label)
        return False

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        record3d_controls,
        "list_record3d_usb_devices",
        lambda: [Record3DDevice(product_id=101, udid="device-101")],
    )
    monkeypatch.setattr(record3d_page.st, "sidebar", DummyContext())
    monkeypatch.setattr(record3d_page.st, "subheader", lambda *args, **kwargs: None)
    monkeypatch.setattr(record3d_page.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(record3d_page.st, "segmented_control", lambda *args, **kwargs: Record3DTransportId.USB)
    monkeypatch.setattr(
        record3d_page.st, "selectbox", lambda *args, **kwargs: Record3DDevice(product_id=101, udid="device-101")
    )
    monkeypatch.setattr(record3d_page.st, "button", fake_button)
    monkeypatch.setattr(record3d_page.st, "expander", lambda *args, **kwargs: DummyContext())
    monkeypatch.setattr(record3d_page.st, "write", lambda *args, **kwargs: None)
    monkeypatch.setattr(record3d_page.st, "warning", lambda *args, **kwargs: None)
    monkeypatch.setattr(record3d_page.st, "info", lambda *args, **kwargs: None)

    action = record3d_page._render_sidebar_controls(context)
    monkeypatch.undo()

    assert seen_labels == ["Stop stream"]
    assert action.start_requested is False
    assert action.stop_requested is False


def test_record3d_page_reruns_after_start_action() -> None:
    from prml_vslam.app.pages import record3d as record3d_page
    from prml_vslam.app.record3d_controller import Record3DPageAction

    rerun_calls: list[bool] = []
    context = SimpleNamespace(
        state=AppState(record3d=Record3DPageState(is_running=False)),
        store=FakeStore(),
        record3d_runtime=FakeRecord3DRuntime(),
    )

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        record3d_page,
        "render_page_intro",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        record3d_page,
        "_render_sidebar_controls",
        lambda _context: Record3DPageAction(
            transport=Record3DTransportId.USB,
            start_requested=True,
            usb_device_index=0,
        ),
    )
    monkeypatch.setattr(record3d_page, "_render_live_snapshot", lambda _context: None)
    monkeypatch.setattr(record3d_page.st, "rerun", lambda: rerun_calls.append(True))

    record3d_page.render(context)
    monkeypatch.undo()

    assert rerun_calls == [True]
    assert context.state.record3d.is_running is True


def test_record3d_page_controller_restarts_running_usb_stream_with_new_selector() -> None:
    from prml_vslam.app.record3d_controller import Record3DPageAction, handle_record3d_page_action

    class RuntimeSpy:
        def __init__(self) -> None:
            self.stop_calls = 0
            self.start_usb_calls: list[int] = []

        def snapshot(self) -> Record3DStreamSnapshot:
            if not self.start_usb_calls:
                return Record3DStreamSnapshot(
                    transport=Record3DTransportId.USB,
                    state=PreviewStreamState.STREAMING,
                )
            return Record3DStreamSnapshot(
                transport=Record3DTransportId.USB,
                state=PreviewStreamState.CONNECTING,
                source_label=f"USB device #{self.start_usb_calls[-1]}",
            )

        def stop(self) -> None:
            self.stop_calls += 1

        def start_usb(self, *, device_index: int) -> None:
            self.start_usb_calls.append(device_index)

        def start_wifi_preview(self, *, device_address: str) -> None:
            raise AssertionError(f"Unexpected Wi-Fi start for {device_address}")

    context = SimpleNamespace(
        state=AppState(
            record3d=Record3DPageState(transport=Record3DTransportId.USB, usb_device_index=0, is_running=True)
        ),
        store=FakeStore(),
        record3d_runtime=RuntimeSpy(),
    )

    snapshot = handle_record3d_page_action(
        context,
        Record3DPageAction(
            transport=Record3DTransportId.USB,
            usb_device_index=1,
            start_requested=True,
        ),
    )

    assert context.record3d_runtime.stop_calls == 1
    assert context.record3d_runtime.start_usb_calls == [1]
    assert context.state.record3d.usb_device_index == 1
    assert context.state.record3d.is_running is True
    assert snapshot.transport is Record3DTransportId.USB

    assert snapshot.state is PreviewStreamState.CONNECTING


def test_record3d_runtime_controller_updates_stats_and_clears_on_stop() -> None:
    usb_stream = FakePacketStream(
        packets=[
            FramePacket(
                seq=0,
                timestamp_ns=1_000_000_000,
                arrival_timestamp_s=1.0,
                rgb=np.ones((2, 2, 3), dtype=np.uint8),
                depth=np.ones((2, 2), dtype=np.float32),
                intrinsics=CameraIntrinsics(fx=100.0, fy=200.0, cx=10.0, cy=20.0),
                pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
                confidence=np.ones((2, 2), dtype=np.float32),
                metadata={"transport": Record3DTransportId.USB.value},
            ),
            FramePacket(
                seq=1,
                timestamp_ns=1_100_000_000,
                arrival_timestamp_s=1.1,
                rgb=np.ones((2, 2, 3), dtype=np.uint8),
                depth=np.ones((2, 2), dtype=np.float32),
                intrinsics=CameraIntrinsics(fx=100.0, fy=200.0, cx=10.0, cy=20.0),
                pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=0.5, tz=0.25),
                confidence=np.ones((2, 2), dtype=np.float32),
                metadata={"transport": Record3DTransportId.USB.value},
            ),
        ],
        connected_target=Record3DDevice(product_id=101, udid="device-101"),
    )
    controller = Record3DStreamRuntimeController(
        usb_stream_factory=lambda device_index, timeout_seconds: usb_stream,
    )

    controller.start_usb(device_index=0)
    _wait_for(lambda: controller.snapshot().received_frames >= 2)
    snapshot = controller.snapshot()

    assert snapshot.transport is Record3DTransportId.USB
    assert snapshot.latest_packet is not None
    assert snapshot.latest_packet.confidence is not None
    assert snapshot.measured_fps > 0.0
    assert snapshot.trajectory_positions_xyz.shape[1] == 3
    assert snapshot.trajectory_positions_xyz.shape[0] >= 2
    np.testing.assert_allclose(snapshot.trajectory_positions_xyz[-1], np.array([1.0, 0.5, 0.25]))

    controller.stop()

    assert usb_stream.disconnected is True
    assert controller.snapshot().state is PreviewStreamState.IDLE
    assert controller.snapshot().latest_packet is None
    assert controller.snapshot().trajectory_positions_xyz.shape == (0, 3)


def test_record3d_runtime_controller_stops_previous_stream_when_switching_transport() -> None:
    usb_stream = FakePacketStream(
        packets=[_usb_snapshot(confidence=True).latest_packet],
        connected_target=Record3DDevice(product_id=101, udid="device-101"),
    )
    wifi_stream = FakePacketStream(
        packets=[_wifi_snapshot().latest_packet],
        connected_target=SimpleNamespace(device_address="http://myiPhone.local"),
    )
    controller = Record3DStreamRuntimeController(
        usb_stream_factory=lambda device_index, timeout_seconds: usb_stream,
        wifi_preview_stream_factory=lambda device_address, timeout_seconds: wifi_stream,
    )

    controller.start_usb(device_index=0)
    _wait_for(lambda: controller.snapshot().transport is Record3DTransportId.USB)
    controller.start_wifi_preview(device_address="myiPhone.local")
    _wait_for(lambda: controller.snapshot().transport is Record3DTransportId.WIFI)

    assert usb_stream.disconnected is True
    controller.stop()
    assert wifi_stream.disconnected is True


def test_advio_preview_runtime_controller_updates_stats_and_clears_on_stop() -> None:
    stream = FakeFramePacketStream(
        packets=[
            FramePacket(
                seq=0,
                timestamp_ns=0,
                rgb=np.ones((2, 2, 3), dtype=np.uint8),
                intrinsics=CameraIntrinsics(
                    width_px=64,
                    height_px=48,
                    fx=100.0,
                    fy=101.0,
                    cx=32.0,
                    cy=24.0,
                ),
                pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
                metadata={"loop_index": 0, "source_frame_index": 0},
            ),
            FramePacket(
                seq=1,
                timestamp_ns=100_000_000,
                rgb=np.ones((2, 2, 3), dtype=np.uint8) * 2,
                intrinsics=CameraIntrinsics(
                    width_px=64,
                    height_px=48,
                    fx=100.0,
                    fy=101.0,
                    cx=32.0,
                    cy=24.0,
                ),
                pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=0.5, tz=0.25),
                metadata={"loop_index": 0, "source_frame_index": 1},
            ),
        ]
    )
    controller = AdvioPreviewRuntimeController()

    controller.start(
        sequence_id=15,
        sequence_label="advio-15 · Office 03",
        pose_source=AdvioPoseSource.GROUND_TRUTH,
        stream=stream,
    )
    _wait_for(lambda: controller.snapshot().received_frames >= 2)
    snapshot = controller.snapshot()

    assert snapshot.state is PreviewStreamState.STREAMING
    assert snapshot.sequence_id == 15
    assert snapshot.pose_source is AdvioPoseSource.GROUND_TRUTH
    assert snapshot.latest_packet is not None
    assert snapshot.measured_fps > 0.0
    assert snapshot.trajectory_positions_xyz.shape[1] == 3
    assert snapshot.trajectory_positions_xyz.shape[0] >= 2
    np.testing.assert_allclose(snapshot.trajectory_positions_xyz[-1], np.array([1.0, 0.5, 0.25]))
    np.testing.assert_allclose(snapshot.trajectory_timestamps_s[-1], 0.1)

    controller.stop()

    assert stream.disconnected is True
    assert controller.snapshot().state is PreviewStreamState.IDLE
    assert controller.snapshot().latest_packet is None
    assert controller.snapshot().trajectory_positions_xyz.shape == (0, 3)


def test_metrics_page_entry_stops_record3d_runtime_when_switching(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = FakeRecord3DRuntime()
    context = SimpleNamespace(
        state=AppState(record3d=Record3DPageState(is_running=True)),
        store=FakeStore(),
        record3d_runtime=runtime,
        advio_runtime=FakeAdvioRuntime(),
        run_service=FakeRunService(),
    )
    bootstrap._render_page_entry(context, AppPageId.METRICS, lambda ctx: None)

    assert context.state.record3d.is_running is False
    assert runtime.stop_calls == 1


def test_pipeline_page_entry_stops_advio_runtime_when_switching(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = FakeAdvioRuntime()
    context = SimpleNamespace(
        state=AppState(advio=AdvioPageState(preview_is_running=True)),
        store=FakeStore(),
        record3d_runtime=FakeRecord3DRuntime(),
        advio_runtime=runtime,
    )
    bootstrap._render_page_entry(context, AppPageId.PIPELINE, lambda ctx: None)

    assert context.state.advio.preview_is_running is False
    assert runtime.stop_calls == 1


def test_metrics_page_entry_keeps_run_service_when_switching(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = FakeRunService(snapshot=RunSnapshot(state=RunState.RUNNING))
    context = SimpleNamespace(
        state=AppState(),
        store=FakeStore(),
        record3d_runtime=FakeRecord3DRuntime(),
        advio_runtime=FakeAdvioRuntime(),
        run_service=runtime,
    )
    bootstrap._render_page_entry(context, AppPageId.METRICS, lambda ctx: None)

    assert runtime.stop_calls == 0


def test_session_state_store_round_trips_run_service(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_session_state: dict[str, object] = {}
    monkeypatch.setattr("prml_vslam.app.state.st.session_state", fake_session_state)
    store = SessionStateStore()

    runtime = store.load_run_service()

    assert fake_session_state["_prml_vslam_pipeline_runtime"] is runtime
    assert store.load_run_service() is runtime
    assert isinstance(runtime, RunService)


def test_normalize_grayscale_ignores_non_finite_depth_values() -> None:
    from prml_vslam.utils.image_utils import normalize_grayscale_image

    image = np.array([[np.nan, 1.0], [np.inf, 3.0]], dtype=np.float32)

    with warnings.catch_warnings(record=True) as captured_warnings:
        warnings.simplefilter("always")
        normalized = normalize_grayscale_image(image)

    assert normalized.dtype == np.uint8
    assert normalized.shape == image.shape
    assert not captured_warnings
    assert normalized[0, 0] == 0
    assert normalized[1, 0] == 0
