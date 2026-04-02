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
    AppPageId,
    AppState,
    DatasetId,
    EvaluationControls,
    Record3DPageState,
)
from prml_vslam.app.services import MetricsAppService, Record3DStreamRuntimeController
from prml_vslam.app.state import SessionStateStore
from prml_vslam.io.record3d import (
    Record3DDevice,
    Record3DFramePacket,
    Record3DIntrinsicMatrix,
    Record3DStreamSnapshot,
    Record3DStreamState,
    Record3DTransportId,
)
from prml_vslam.utils.path_config import PathConfig


def _write_tum(path: Path, rows: list[tuple[float, float, float, float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(f"{t:.1f} {x:.3f} {y:.3f} {z:.3f} 0 0 0 1" for t, x, y, z in rows) + "\n",
        encoding="utf-8",
    )


def _build_path_config(tmp_path: Path) -> PathConfig:
    sequence_root = tmp_path / "data" / "advio" / "advio-15" / "ground-truth"
    run_root = tmp_path / "artifacts" / "advio-15" / "vista_slam" / "slam"
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
        artifacts_dir=tmp_path / "artifacts",
        captures_dir=tmp_path / "captures",
    )


class FakeStore:
    """Minimal store stand-in for direct page-render tests."""

    def save(self, state: AppState) -> None:
        self.last_state = state.model_copy(deep=True)


class FakeRecord3DService:
    """Minimal Record3D service stand-in for direct page-render tests."""

    def __init__(self, devices: list[Record3DDevice], error_message: str = "") -> None:
        self.devices = devices
        self.error_message = error_message

    def list_usb_devices(self) -> list[Record3DDevice]:
        if self.error_message:
            raise RuntimeError(self.error_message)
        return list(self.devices)


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
            state=Record3DStreamState.CONNECTING,
            source_label=f"USB device #{device_index}",
        )

    def start_wifi(self, *, device_address: str) -> None:
        self._snapshot = Record3DStreamSnapshot(
            transport=Record3DTransportId.WIFI,
            state=Record3DStreamState.CONNECTING,
            source_label=device_address,
        )


class FakePacketStream:
    """Tiny packet-stream stand-in for runtime-controller tests."""

    def __init__(self, *, packets: list[Record3DFramePacket], connected_target: object) -> None:
        self.packets = packets
        self.connected_target = connected_target
        self.disconnected = False
        self.wait_calls = 0

    def connect(self) -> object:
        return self.connected_target

    def disconnect(self) -> None:
        self.disconnected = True

    def wait_for_packet(self, timeout_seconds: float | None = None) -> Record3DFramePacket:
        index = min(self.wait_calls, len(self.packets) - 1)
        self.wait_calls += 1
        time.sleep(0.01)
        return self.packets[index]


def _usb_snapshot(*, uncertainty: bool) -> Record3DStreamSnapshot:
    uncertainty_frame = np.array([[0.0, 0.5], [0.75, 1.0]], dtype=np.float32) if uncertainty else None
    return Record3DStreamSnapshot(
        transport=Record3DTransportId.USB,
        state=Record3DStreamState.STREAMING,
        source_label="device-101",
        received_frames=12,
        measured_fps=29.7,
        latest_packet=Record3DFramePacket(
            transport=Record3DTransportId.USB,
            rgb=np.ones((2, 2, 3), dtype=np.uint8),
            depth=np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32),
            intrinsic_matrix=Record3DIntrinsicMatrix(fx=100.0, fy=200.0, tx=10.0, ty=20.0),
            uncertainty=uncertainty_frame,
            metadata={"original_size": [960, 720]},
            arrival_timestamp_s=42.0,
        ),
    )


def _wifi_snapshot() -> Record3DStreamSnapshot:
    return Record3DStreamSnapshot(
        transport=Record3DTransportId.WIFI,
        state=Record3DStreamState.STREAMING,
        source_label="http://myiPhone.local",
        received_frames=8,
        measured_fps=15.5,
        latest_packet=Record3DFramePacket(
            transport=Record3DTransportId.WIFI,
            rgb=np.ones((2, 2, 3), dtype=np.uint8) * 3,
            depth=np.ones((2, 2), dtype=np.float32),
            intrinsic_matrix=Record3DIntrinsicMatrix(fx=50.0, fy=60.0, tx=5.0, ty=6.0),
            uncertainty=None,
            metadata={"device_address": "http://myiPhone.local"},
            arrival_timestamp_s=24.0,
        ),
    )


def _render_record3d_page_script(snapshot, transport, devices) -> None:
    from types import SimpleNamespace

    from prml_vslam.app.models import AppState, Record3DPageState
    from prml_vslam.app.pages.record3d import render as render_record3d_page

    class _Store:
        def save(self, state: AppState) -> None:
            self.last_state = state.model_copy(deep=True)

    class _Runtime:
        def __init__(self, current_snapshot) -> None:
            self.current_snapshot = current_snapshot

        def snapshot(self):
            return self.current_snapshot

        def stop(self) -> None:
            self.current_snapshot = type(snapshot)()

        def start_usb(self, *, device_index: int) -> None:
            return None

        def start_wifi(self, *, device_address: str) -> None:
            return None

    class _Service:
        def __init__(self, current_devices) -> None:
            self.current_devices = current_devices

        def list_usb_devices(self):
            return list(self.current_devices)

    context = SimpleNamespace(
        state=AppState(record3d=Record3DPageState(transport=transport, is_running=False)),
        store=_Store(),
        record3d_runtime=_Runtime(snapshot),
        record3d_service=_Service(devices),
    )
    render_record3d_page(context)


def _wait_for(predicate, *, timeout_seconds: float = 1.0) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if predicate():
            return
        time.sleep(0.02)
    raise AssertionError("Timed out waiting for the expected runtime state.")


def test_metrics_service_discovers_and_persists_evo_results(tmp_path: Path) -> None:
    pytest.importorskip("evo")
    path_config = _build_path_config(tmp_path)
    service = MetricsAppService(path_config)

    runs = service.discover_runs(DatasetId.ADVIO, "advio-15")

    assert len(runs) == 1
    selection = service.resolve_selection(
        dataset=DatasetId.ADVIO,
        sequence_slug="advio-15",
        run_root=runs[0].artifact_root,
    )
    assert selection is not None

    result = service.compute_evaluation(
        selection=selection,
        controls=EvaluationControls(),
    )

    assert result.path.exists()
    assert result.matched_pairs == 3
    assert result.stats.rmse > 0.0
    assert len(result.trajectories) == 2


def test_run_app_defaults_to_record3d_page(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path_config = _build_path_config(tmp_path)
    monkeypatch.setattr(bootstrap, "get_path_config", lambda: path_config)

    app_path = Path(__file__).resolve().parents[1] / "streamlit_app.py"
    at = AppTest.from_file(str(app_path))
    at.run()

    assert at.title[0].value == "Record3D Stream"
    assert at.text_input[0].value == "192.168.159.24"
    assert {metric.label for metric in at.metric} >= {"Status", "Received Frames", "Frame Rate", "Transport"}


def test_run_app_renders_metrics_page_when_state_selects_metrics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("evo")
    path_config = _build_path_config(tmp_path)
    service = MetricsAppService(path_config)
    selection = service.resolve_selection(
        dataset=DatasetId.ADVIO,
        sequence_slug="advio-15",
        run_root=service.discover_runs(DatasetId.ADVIO, "advio-15")[0].artifact_root,
    )
    assert selection is not None
    result = service.compute_evaluation(selection=selection, controls=EvaluationControls())

    monkeypatch.setattr(bootstrap, "get_path_config", lambda: path_config)

    app_path = Path(__file__).resolve().parents[1] / "streamlit_app.py"
    at = AppTest.from_file(str(app_path))
    at.session_state["_prml_vslam_app_state"] = AppState(
        current_page=AppPageId.METRICS,
        metrics={
            "dataset": DatasetId.ADVIO,
            "sequence_slug": "advio-15",
            "run_root": selection.run.artifact_root,
            "evaluation": EvaluationControls(),
            "result_path": result.path,
        },
    ).model_dump(mode="json")
    at.run()

    assert at.title[0].value == "Trajectory Metrics"
    assert {metric.label for metric in at.metric} >= {"RMSE", "Mean", "Median", "Max"}


def test_record3d_page_renders_usb_controls_and_frames() -> None:
    devices = [Record3DDevice(product_id=101, udid="device-101")]
    at = AppTest.from_function(
        _render_record3d_page_script,
        args=(_usb_snapshot(uncertainty=True), Record3DTransportId.USB, devices),
    )
    at.run()

    assert at.title[0].value == "Record3D Stream"
    assert at.selectbox[0].label == "USB Device"
    assert at.text_input[0].label == "Wi-Fi Device Address"
    assert {metric.label for metric in at.metric} >= {"Status", "Received Frames", "Frame Rate", "Transport"}
    assert {item.value for item in at.subheader} >= {"Camera Intrinsics", "Packet Metadata"}
    assert not any("not available for this transport" in item.value.lower() for item in at.info)


def test_record3d_page_renders_wifi_info_when_uncertainty_is_missing() -> None:
    at = AppTest.from_function(
        _render_record3d_page_script,
        args=(_wifi_snapshot(), Record3DTransportId.WIFI, []),
    )
    at.run()

    assert at.text_input[0].label == "Wi-Fi Device Address"
    assert {metric.label for metric in at.metric} >= {"Status", "Received Frames", "Frame Rate", "Transport"}
    assert any("not available for this transport" in item.value.lower() for item in at.info)


def test_record3d_runtime_controller_updates_stats_and_clears_on_stop() -> None:
    usb_stream = FakePacketStream(
        packets=[
            Record3DFramePacket(
                transport=Record3DTransportId.USB,
                rgb=np.ones((2, 2, 3), dtype=np.uint8),
                depth=np.ones((2, 2), dtype=np.float32),
                intrinsic_matrix=Record3DIntrinsicMatrix(fx=100.0, fy=200.0, tx=10.0, ty=20.0),
                uncertainty=np.ones((2, 2), dtype=np.float32),
                metadata={},
                arrival_timestamp_s=1.0,
            ),
            Record3DFramePacket(
                transport=Record3DTransportId.USB,
                rgb=np.ones((2, 2, 3), dtype=np.uint8),
                depth=np.ones((2, 2), dtype=np.float32),
                intrinsic_matrix=Record3DIntrinsicMatrix(fx=100.0, fy=200.0, tx=10.0, ty=20.0),
                uncertainty=np.ones((2, 2), dtype=np.float32),
                metadata={},
                arrival_timestamp_s=1.1,
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
    assert snapshot.latest_packet.uncertainty is not None
    assert snapshot.measured_fps > 0.0

    controller.stop()

    assert usb_stream.disconnected is True
    assert controller.snapshot().state is Record3DStreamState.IDLE
    assert controller.snapshot().latest_packet is None


def test_record3d_runtime_controller_stops_previous_stream_when_switching_transport() -> None:
    usb_stream = FakePacketStream(
        packets=[_usb_snapshot(uncertainty=True).latest_packet],
        connected_target=Record3DDevice(product_id=101, udid="device-101"),
    )
    wifi_stream = FakePacketStream(
        packets=[_wifi_snapshot().latest_packet],
        connected_target=SimpleNamespace(device_address="http://myiPhone.local"),
    )
    controller = Record3DStreamRuntimeController(
        usb_stream_factory=lambda device_index, timeout_seconds: usb_stream,
        wifi_stream_factory=lambda device_address, timeout_seconds: wifi_stream,
    )

    controller.start_usb(device_index=0)
    _wait_for(lambda: controller.snapshot().transport is Record3DTransportId.USB)
    controller.start_wifi(device_address="myiPhone.local")
    _wait_for(lambda: controller.snapshot().transport is Record3DTransportId.WIFI)

    assert usb_stream.disconnected is True
    controller.stop()
    assert wifi_stream.disconnected is True


def test_navigation_stops_record3d_runtime_when_switching_to_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = FakeRecord3DRuntime()
    context = SimpleNamespace(
        state=AppState(current_page=AppPageId.RECORD3D, record3d=Record3DPageState(is_running=True)),
        store=FakeStore(),
        record3d_runtime=runtime,
    )
    monkeypatch.setattr(bootstrap.st, "segmented_control", lambda *args, **kwargs: AppPageId.METRICS)

    bootstrap._render_top_level_navigation(context)

    assert context.state.current_page is AppPageId.METRICS
    assert context.state.record3d.is_running is False
    assert runtime.stop_calls == 1


def test_session_state_store_accepts_hot_reloaded_runtime_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    class HotReloadedRuntime:
        def snapshot(self) -> Record3DStreamSnapshot:
            return Record3DStreamSnapshot()

        def stop(self) -> None:
            return None

        def start_usb(self, *, device_index: int) -> None:
            return None

        def start_wifi(self, *, device_address: str) -> None:
            return None

    fake_session_state = {"_prml_vslam_record3d_runtime": HotReloadedRuntime()}
    monkeypatch.setattr("prml_vslam.app.state.st.session_state", fake_session_state)

    runtime = SessionStateStore().load_record3d_runtime()

    assert runtime is fake_session_state["_prml_vslam_record3d_runtime"]


def test_normalize_grayscale_ignores_non_finite_depth_values() -> None:
    from prml_vslam.app.pages.record3d import _normalize_grayscale

    image = np.array([[np.nan, 1.0], [np.inf, 3.0]], dtype=np.float32)

    with warnings.catch_warnings(record=True) as captured_warnings:
        warnings.simplefilter("always")
        normalized = _normalize_grayscale(image)

    assert normalized.dtype == np.uint8
    assert normalized.shape == image.shape
    assert not captured_warnings
    assert normalized[0, 0] == 0
    assert normalized[1, 0] == 0
