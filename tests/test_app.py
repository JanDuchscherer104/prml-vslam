"""Tests for the packaged Streamlit app and Record3D runtime."""

from __future__ import annotations

import time
import warnings
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from prml_vslam.app import bootstrap
from prml_vslam.app.models import AdvioPageState, AppState, Record3DPageState
from prml_vslam.app.services import (
    AdvioPreviewRuntimeController,
    AdvioPreviewSnapshot,
    AdvioPreviewStreamState,
    Record3DStreamRuntimeController,
)
from prml_vslam.app.state import SessionStateStore
from prml_vslam.datasets.advio import AdvioPoseSource
from prml_vslam.datasets.advio_layout import resolve_existing_reference_tum
from prml_vslam.datasets.interfaces import DatasetId
from prml_vslam.eval import TrajectoryEvaluationService
from prml_vslam.eval.interfaces import EvaluationControls, SelectionSnapshot
from prml_vslam.interfaces import CameraIntrinsics, FramePacket, SE3Pose
from prml_vslam.io.record3d import (
    Record3DDevice,
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
    run_root = tmp_path / "artifacts" / "advio-15" / "vista" / "slam"
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
            state=AdvioPreviewStreamState.CONNECTING,
            sequence_id=sequence_id,
            sequence_label=sequence_label,
            pose_source=pose_source,
        )


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


def _usb_snapshot(*, uncertainty: bool) -> Record3DStreamSnapshot:
    uncertainty_frame = np.array([[0.0, 0.5], [0.75, 1.0]], dtype=np.float32) if uncertainty else None
    return Record3DStreamSnapshot(
        transport=Record3DTransportId.USB,
        state=Record3DStreamState.STREAMING,
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
            uncertainty=uncertainty_frame,
            metadata={"original_size": [960, 720], "transport": Record3DTransportId.USB.value},
        ),
    )


def _wifi_snapshot() -> Record3DStreamSnapshot:
    return Record3DStreamSnapshot(
        transport=Record3DTransportId.WIFI,
        state=Record3DStreamState.STREAMING,
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
            uncertainty=None,
            metadata={"device_address": "http://myiPhone.local", "transport": Record3DTransportId.WIFI.value},
        ),
    )


def _advio_preview_snapshot() -> AdvioPreviewSnapshot:
    return AdvioPreviewSnapshot(
        state=AdvioPreviewStreamState.STREAMING,
        sequence_id=15,
        sequence_label="advio-15 · Office 03",
        pose_source=AdvioPoseSource.GROUND_TRUTH,
        received_frames=9,
        measured_fps=9.8,
        trajectory_positions_xyz=np.array(
            [
                [1.0, 2.0, 3.0],
                [1.5, 2.5, 3.5],
                [2.0, 3.0, 4.0],
            ],
            dtype=np.float64,
        ),
        trajectory_timestamps_s=np.array([0.0, 0.1, 0.2], dtype=np.float64),
        latest_packet=FramePacket(
            seq=2,
            timestamp_ns=200_000_000,
            rgb=np.ones((4, 6, 3), dtype=np.uint8) * 7,
            intrinsics=CameraIntrinsics(
                width_px=64,
                height_px=48,
                fx=100.0,
                fy=101.0,
                cx=32.0,
                cy=24.0,
            ),
            pose=SE3Pose(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=2.0, ty=3.0, tz=4.0),
            metadata={
                "loop_index": 1,
                "source_frame_index": 2,
                "video_rotation_degrees": 90,
            },
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


def _render_record3d_page_script_with_runtime(runtime, transport, devices) -> None:
    from types import SimpleNamespace

    from prml_vslam.app.models import AppState, Record3DPageState
    from prml_vslam.app.pages.record3d import render as render_record3d_page

    class _Store:
        def save(self, state: AppState) -> None:
            self.last_state = state.model_copy(deep=True)

    class _Service:
        def __init__(self, current_devices) -> None:
            self.current_devices = current_devices

        def list_usb_devices(self):
            return list(self.current_devices)

    context = SimpleNamespace(
        state=AppState(record3d=Record3DPageState(transport=transport, is_running=False)),
        store=_Store(),
        record3d_runtime=runtime,
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


def _plotly_specs(at: AppTest) -> list[str]:
    return [element.proto.spec for element in at.main if getattr(element, "type", None) == "plotly_chart"]


def test_metrics_service_discovers_and_persists_mock_results(tmp_path: Path) -> None:
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

    result = service.compute_evaluation(
        selection=selection,
        controls=EvaluationControls(),
    )

    assert result.path.exists()
    assert result.matched_pairs == 3
    assert result.stats.rmse > 0.0
    assert len(result.trajectories) == 2


def test_compute_evaluation_loads_each_trajectory_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path_config = _build_path_config(tmp_path)
    service = TrajectoryEvaluationService(path_config)
    selection = SelectionSnapshot(
        sequence_slug="advio-15",
        reference_path=resolve_existing_reference_tum(
            path_config.resolve_dataset_dir(DatasetId.ADVIO.value), "advio-15"
        ),
        run=service.discover_runs("advio-15")[0],
    )
    assert selection.reference_path is not None

    import prml_vslam.eval.mock_metrics as mock_metrics

    counts: Counter[Path] = Counter()
    original = mock_metrics._load_tum_trajectory

    def counted_load(path: Path) -> tuple[np.ndarray, np.ndarray]:
        counts[path] += 1
        return original(path)

    monkeypatch.setattr(mock_metrics, "_load_tum_trajectory", counted_load)

    service.compute_evaluation(selection=selection, controls=EvaluationControls())

    assert counts[selection.reference_path] == 1
    assert counts[selection.run.estimate_path] == 1


def test_run_app_defaults_to_record3d_page(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path_config = _build_path_config(tmp_path)
    monkeypatch.setattr(bootstrap, "get_path_config", lambda: path_config)

    app_path = Path(__file__).resolve().parents[1] / "streamlit_app.py"
    at = AppTest.from_file(str(app_path))
    at.run()

    assert at.title[0].value == "Record3D Stream"
    assert not at.radio
    assert at.sidebar.button_group[0].label == "Transport"
    assert at.sidebar.selectbox[0].label == "USB Device"
    assert {metric.label for metric in at.metric} >= {"Status", "Received Frames", "Frame Rate", "Transport"}


def test_render_metrics_page_entry_shows_metrics_content(
    tmp_path: Path,
) -> None:
    def _render_metrics_page_entry_script(root_path: str) -> None:
        from pathlib import Path
        from types import SimpleNamespace

        from prml_vslam.app import bootstrap
        from prml_vslam.app.models import AppState
        from prml_vslam.datasets.advio_layout import resolve_existing_reference_tum
        from prml_vslam.datasets.interfaces import DatasetId
        from prml_vslam.eval import TrajectoryEvaluationService
        from prml_vslam.eval.interfaces import EvaluationControls, SelectionSnapshot
        from prml_vslam.utils.path_config import PathConfig

        def _write_tum(path: Path, rows: list[tuple[float, float, float, float]]) -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "\n".join(f"{t:.1f} {x:.3f} {y:.3f} {z:.3f} 0 0 0 1" for t, x, y, z in rows) + "\n",
                encoding="utf-8",
            )

        class _Store:
            def save(self, state: AppState) -> None:
                self.last_state = state.model_copy(deep=True)

        class _Runtime:
            def stop(self) -> None:
                return None

        class _AdvioRuntime:
            def snapshot(self):
                from prml_vslam.app.services import AdvioPreviewSnapshot

                return AdvioPreviewSnapshot()

            def stop(self) -> None:
                return None

            def start(self, *, sequence_id: int, sequence_label: str, pose_source, stream) -> None:
                del sequence_id, sequence_label, pose_source, stream
                return None

        root = Path(root_path)
        _write_tum(
            root / "data" / "advio" / "advio-15" / "ground-truth" / "ground_truth.tum",
            [(0.0, 0.0, 0.0, 0.0), (0.1, 1.0, 0.0, 0.0), (0.2, 2.0, 1.0, 0.0)],
        )
        _write_tum(
            root / "artifacts" / "advio-15" / "vista" / "slam" / "trajectory.tum",
            [(0.0, 0.0, 0.0, 0.0), (0.1, 1.1, 0.0, 0.0), (0.2, 2.2, 0.9, 0.0)],
        )

        path_config = PathConfig(
            root=root,
            artifacts_dir=root / "artifacts",
            captures_dir=root / "captures",
        )
        service = TrajectoryEvaluationService(path_config)
        selection = SelectionSnapshot(
            sequence_slug="advio-15",
            reference_path=resolve_existing_reference_tum(
                path_config.resolve_dataset_dir(DatasetId.ADVIO.value), "advio-15"
            ),
            run=service.discover_runs("advio-15")[0],
        )
        result = service.compute_evaluation(selection=selection, controls=EvaluationControls())
        context = SimpleNamespace(
            path_config=path_config,
            evaluation_service=service,
            record3d_runtime=_Runtime(),
            advio_runtime=_AdvioRuntime(),
            store=_Store(),
            state=AppState(
                metrics={
                    "dataset": DatasetId.ADVIO,
                    "sequence_slug": "advio-15",
                    "run_root": selection.run.artifact_root,
                    "evaluation": EvaluationControls(),
                    "result_path": result.path,
                },
            ),
        )
        bootstrap._render_metrics_page_entry(context)

    at = AppTest.from_function(_render_metrics_page_entry_script, args=(str(tmp_path),))
    at.run()

    assert at.title[0].value == "Trajectory Metrics"
    assert {metric.label for metric in at.metric} >= {"RMSE", "Mean", "Median", "Max"}


def test_render_pipeline_page_entry_shows_builder_guidance(tmp_path: Path) -> None:
    def _render_pipeline_page_entry_script(root_path: str) -> None:
        from pathlib import Path
        from types import SimpleNamespace

        from prml_vslam.app import bootstrap
        from prml_vslam.app.models import AppState
        from prml_vslam.utils.path_config import PathConfig

        class _Store:
            def save(self, state: AppState) -> None:
                self.last_state = state.model_copy(deep=True)

        class _Runtime:
            def stop(self) -> None:
                return None

        class _AdvioRuntime:
            def snapshot(self):
                from prml_vslam.app.services import AdvioPreviewSnapshot

                return AdvioPreviewSnapshot()

            def stop(self) -> None:
                return None

            def start(self, *, sequence_id: int, sequence_label: str, pose_source, stream) -> None:
                del sequence_id, sequence_label, pose_source, stream
                return None

        root = Path(root_path)
        context = SimpleNamespace(
            path_config=PathConfig(
                root=root,
                artifacts_dir=root / "artifacts",
                captures_dir=root / "captures",
            ),
            state=AppState(),
            store=_Store(),
            record3d_runtime=_Runtime(),
            advio_runtime=_AdvioRuntime(),
        )
        bootstrap._render_pipeline_page_entry(context)

    at = AppTest.from_function(_render_pipeline_page_entry_script, args=(str(tmp_path),))
    at.run()

    assert at.title[0].value == "Pipeline Planning"
    assert {item.value for item in at.subheader} >= {
        "Example Pipelines",
        "Design Pattern",
        "How To Use It",
        "Request Shape",
        "Generated Plan",
        "Mock Run",
    }
    assert any("never executes a backend" in item.value.lower() for item in at.info)
    assert len(at.dataframe) >= 3
    assert {metric.label for metric in at.metric} >= {"Run Id", "Method", "Stages", "Artifact Root"}


def test_pipeline_mock_stage_statuses_follow_stage_ids(tmp_path: Path) -> None:
    from prml_vslam.app.pages import pipeline as pipeline_page
    from prml_vslam.methods import MethodId
    from prml_vslam.pipeline import (
        BenchmarkEvaluationConfig,
        DenseConfig,
        ReferenceConfig,
        RunRequest,
        TrackingConfig,
        VideoSourceSpec,
    )
    from prml_vslam.pipeline.contracts import RunPlanStageId, StageExecutionStatus

    path_config = PathConfig(
        root=tmp_path,
        artifacts_dir=tmp_path / "artifacts",
        captures_dir=tmp_path / "captures",
    )
    plan = RunRequest(
        experiment_name="tracking-only-demo",
        output_dir=path_config.artifacts_dir,
        source=VideoSourceSpec(video_path=path_config.captures_dir / "tracking-only.mp4"),
        tracking=TrackingConfig(method=MethodId.VISTA, max_frames=300),
        dense=DenseConfig(enabled=False),
        reference=ReferenceConfig(enabled=False),
        evaluation=BenchmarkEvaluationConfig(
            compare_to_arcore=False,
            evaluate_cloud=False,
            evaluate_efficiency=True,
        ),
    ).build(path_config)

    stage_status = pipeline_page._mock_stage_statuses(plan)

    assert set(stage_status) == {stage.id for stage in plan.stages}
    assert stage_status[RunPlanStageId.INGEST] is StageExecutionStatus.HIT
    assert RunPlanStageId.REFERENCE_RECONSTRUCTION not in stage_status
    assert stage_status[RunPlanStageId.SLAM] is StageExecutionStatus.RAN
    assert stage_status[RunPlanStageId.EFFICIENCY_EVALUATION] is StageExecutionStatus.RAN
    assert stage_status[RunPlanStageId.SUMMARY] is StageExecutionStatus.RAN


def test_record3d_page_renders_usb_controls_and_frames() -> None:
    devices = [Record3DDevice(product_id=101, udid="device-101")]
    at = AppTest.from_function(
        _render_record3d_page_script,
        args=(_usb_snapshot(uncertainty=True), Record3DTransportId.USB, devices),
    )
    at.run()

    assert at.title[0].value == "Record3D Stream"
    assert at.sidebar.button_group[0].label == "Transport"
    assert at.sidebar.selectbox[0].label == "USB Device"
    assert not any(item.value == "Connection" for item in at.subheader)
    assert {metric.label for metric in at.metric} >= {"Status", "Received Frames", "Frame Rate", "Transport"}
    assert {tab.label for tab in at.tabs} >= {"Frames", "Trajectory", "Camera"}
    assert not any("not available for this transport" in item.value.lower() for item in at.info)
    assert len(_plotly_specs(at)) == 1
    assert '"scatter3d"' in _plotly_specs(at)[0]
    assert "Ego Trajectory" in _plotly_specs(at)[0]


def test_record3d_page_renders_wifi_info_when_uncertainty_is_missing() -> None:
    at = AppTest.from_function(
        _render_record3d_page_script,
        args=(_wifi_snapshot(), Record3DTransportId.WIFI, []),
    )
    at.run()

    assert at.sidebar.text_input[0].label == "Wi-Fi Device Address"
    assert at.sidebar.button_group[0].label == "Transport"
    assert {metric.label for metric in at.metric} >= {"Status", "Received Frames", "Frame Rate", "Transport"}
    assert any("not available for this transport" in item.value.lower() for item in at.info)
    assert any("ego trajectory is not available" in item.value.lower() for item in at.info)


def test_advio_page_renders_summary_and_download_controls(tmp_path: Path) -> None:
    def _render_advio_page_script(root_path: str) -> None:
        from pathlib import Path
        from types import SimpleNamespace

        from prml_vslam.app.models import AdvioPageState, AppState
        from prml_vslam.app.pages.advio import render as render_advio_page
        from prml_vslam.datasets import AdvioCatalog, AdvioDatasetService, AdvioSceneMetadata
        from prml_vslam.datasets.advio import (
            AdvioDownloadPreset,
            AdvioEnvironment,
            AdvioPeopleLevel,
            AdvioUpstreamMetadata,
        )
        from prml_vslam.utils import PathConfig

        class _Store:
            def save(self, state: AppState) -> None:
                self.last_state = state.model_copy(deep=True)

        class _AdvioRuntime:
            def snapshot(self):
                from prml_vslam.app.services import AdvioPreviewSnapshot

                return AdvioPreviewSnapshot()

            def stop(self) -> None:
                return None

            def start(self, *, sequence_id: int, sequence_label: str, pose_source, stream) -> None:
                del sequence_id, sequence_label, pose_source, stream
                return None

        advio_service = AdvioDatasetService(
            PathConfig(root=Path(root_path)),
            catalog=AdvioCatalog(
                dataset_id="advio",
                dataset_label="ADVIO",
                upstream=AdvioUpstreamMetadata(
                    repo_url="https://github.com/AaltoVision/ADVIO",
                    zenodo_record_url="https://zenodo.org/records/1476931",
                    doi="10.5281/zenodo.1320824",
                    license="CC BY-NC 4.0",
                    calibration_base_url="https://raw.githubusercontent.com/AaltoVision/ADVIO/master/calibration/",
                ),
                scenes=[
                    AdvioSceneMetadata(
                        sequence_id=15,
                        sequence_slug="advio-15",
                        venue="Office",
                        dataset_code="03",
                        environment=AdvioEnvironment.INDOOR,
                        has_stairs=False,
                        has_escalator=False,
                        has_elevator=False,
                        people_level=AdvioPeopleLevel.NONE,
                        has_vehicles=False,
                        calibration_name="iphone-03.yaml",
                        archive_url="https://zenodo.org/api/records/1476931/files/advio-15.zip/content",
                        archive_size_bytes=54_845_329,
                        archive_md5="f5febcd087acd90531aea98efff71c7c",
                    )
                ],
            ),
        )

        context = SimpleNamespace(
            state=AppState(advio=AdvioPageState(download_preset=AdvioDownloadPreset.OFFLINE)),
            store=_Store(),
            advio_service=advio_service,
            advio_runtime=_AdvioRuntime(),
        )
        render_advio_page(context)

    at = AppTest.from_function(_render_advio_page_script, args=(str(tmp_path),))
    at.run()

    assert at.title[0].value == "ADVIO Dataset"
    assert {metric.label for metric in at.metric} >= {
        "Total Scenes",
        "Local Scenes",
        "Replay Ready",
        "Offline Ready",
        "Cached Archives",
    }
    assert any(button.label == "Download selected scenes" and button.disabled is False for button in at.button)
    assert any(item.value == "Loop Preview" for item in at.subheader)
    assert any(selectbox.label == "Bundle" for selectbox in at.selectbox)
    assert at.multiselect[0].label == "Scenes"
    assert at.multiselect[1].label == "Modalities Override"
    assert len(_plotly_specs(at)) == 4
    specs = "\n".join(_plotly_specs(at))
    assert "Scene Mix by Venue" in specs
    assert "Local Readiness" in specs
    assert "Crowd Density" in specs
    assert "Scene Attributes" in specs


def test_advio_page_renders_local_sequence_explorer(tmp_path: Path) -> None:
    dataset_root = tmp_path / "data" / "advio"
    _write_advio_local_sequence(dataset_root)

    def _render_advio_page_script(root_path: str) -> None:
        from pathlib import Path
        from types import SimpleNamespace

        from prml_vslam.app.models import AppState
        from prml_vslam.app.pages.advio import render as render_advio_page
        from prml_vslam.datasets import AdvioDatasetService
        from prml_vslam.utils import PathConfig

        class _Store:
            def save(self, state: AppState) -> None:
                self.last_state = state.model_copy(deep=True)

        class _AdvioRuntime:
            def snapshot(self):
                from prml_vslam.app.services import AdvioPreviewSnapshot

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
    assert any(selectbox.label == "Local Scene" for selectbox in at.selectbox)
    assert any(selectbox.label == "Preview Scene" for selectbox in at.selectbox)
    assert any(selectbox.label == "Pose Source" for selectbox in at.selectbox)
    specs = "\n".join(_plotly_specs(at))
    assert "BEV Trajectory Overlay" in specs
    assert "3D Trajectory Overlay" in specs
    assert "Translational Speed" in specs
    assert "Height Profile" in specs
    assert "Sampling Intervals" in specs
    assert "Trajectory Cadence" in specs


def test_advio_page_renders_loop_preview_snapshot(tmp_path: Path) -> None:
    dataset_root = tmp_path / "data" / "advio"
    _write_advio_local_sequence(dataset_root)

    def _render_advio_page_script(root_path: str) -> None:
        from pathlib import Path
        from types import SimpleNamespace

        import numpy as np

        from prml_vslam.app.models import AdvioPageState, AppState
        from prml_vslam.app.pages.advio import render as render_advio_page
        from prml_vslam.app.services import AdvioPreviewSnapshot, AdvioPreviewStreamState
        from prml_vslam.datasets import AdvioDatasetService
        from prml_vslam.datasets.advio import AdvioPoseSource
        from prml_vslam.interfaces import CameraIntrinsics, FramePacket, SE3Pose
        from prml_vslam.utils import PathConfig

        class _Store:
            def save(self, state: AppState) -> None:
                self.last_state = state.model_copy(deep=True)

        class _AdvioRuntime:
            def snapshot(self) -> AdvioPreviewSnapshot:
                return AdvioPreviewSnapshot(
                    state=AdvioPreviewStreamState.STREAMING,
                    sequence_id=15,
                    sequence_label="advio-15 · Office 03",
                    pose_source=AdvioPoseSource.GROUND_TRUTH,
                    received_frames=9,
                    measured_fps=9.8,
                    trajectory_positions_xyz=np.array(
                        [[1.0, 2.0, 3.0], [1.5, 2.5, 3.5], [2.0, 3.0, 4.0]],
                        dtype=np.float64,
                    ),
                    trajectory_timestamps_s=np.array([0.0, 0.1, 0.2], dtype=np.float64),
                    latest_packet=FramePacket(
                        seq=2,
                        timestamp_ns=200_000_000,
                        rgb=np.ones((4, 6, 3), dtype=np.uint8) * 7,
                        intrinsics=CameraIntrinsics(
                            width_px=64,
                            height_px=48,
                            fx=100.0,
                            fy=101.0,
                            cx=32.0,
                            cy=24.0,
                        ),
                        pose=SE3Pose(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=2.0, ty=3.0, tz=4.0),
                        metadata={"loop_index": 1, "source_frame_index": 2, "video_rotation_degrees": 90},
                    ),
                )

            def stop(self) -> None:
                return None

            def start(self, *, sequence_id: int, sequence_label: str, pose_source, stream) -> None:
                del sequence_id, sequence_label, pose_source, stream
                return None

        context = SimpleNamespace(
            state=AppState(advio=AdvioPageState(preview_is_running=True)),
            store=_Store(),
            advio_service=AdvioDatasetService(PathConfig(root=Path(root_path))),
            advio_runtime=_AdvioRuntime(),
        )
        render_advio_page(context)

    at = AppTest.from_function(_render_advio_page_script, args=(str(tmp_path),))
    at.run()

    assert {metric.label for metric in at.metric} >= {"Status", "Received Frames", "Frame Rate", "Loop Index"}
    assert {tab.label for tab in at.tabs} >= {"Frames", "Trajectory", "Camera"}
    specs = "\n".join(_plotly_specs(at))
    assert "Ego Trajectory" in specs


def test_advio_download_form_returns_typed_request_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from prml_vslam.app.advio_controller import AdvioDownloadFormData
    from prml_vslam.app.pages import advio as advio_page
    from prml_vslam.datasets import AdvioDatasetService
    from prml_vslam.datasets.advio import AdvioDownloadPreset, AdvioModality

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


def test_advio_page_controller_handles_download_and_refreshes_once() -> None:
    from prml_vslam.app.advio_controller import AdvioDownloadFormData, build_advio_page_data
    from prml_vslam.datasets import (
        AdvioDatasetSummary,
        AdvioDownloadRequest,
        AdvioDownloadResult,
        AdvioEnvironment,
        AdvioLocalSceneStatus,
        AdvioPeopleLevel,
        AdvioSceneMetadata,
    )
    from prml_vslam.datasets.advio import AdvioDownloadPreset

    summary = AdvioDatasetSummary(
        total_scene_count=1,
        local_scene_count=1,
        replay_ready_scene_count=1,
        offline_ready_scene_count=1,
        full_scene_count=1,
        cached_archive_count=1,
        total_remote_archive_bytes=10,
    )
    statuses = [
        AdvioLocalSceneStatus(
            scene=AdvioSceneMetadata(
                sequence_id=15,
                sequence_slug="advio-15",
                venue="Office",
                dataset_code="03",
                environment=AdvioEnvironment.INDOOR,
                has_stairs=False,
                has_escalator=False,
                has_elevator=False,
                people_level=AdvioPeopleLevel.NONE,
                has_vehicles=False,
                calibration_name="iphone-03.yaml",
                archive_url="https://example.com/advio-15.zip",
                archive_size_bytes=10_000_000,
                archive_md5="abc123",
            ),
            replay_ready=True,
            offline_ready=True,
            full_ready=True,
        )
    ]

    class ServiceSpy:
        def __init__(self) -> None:
            self.calls = {"download": 0, "summarize": 0, "local_scene_statuses": 0}
            self.summary_statuses: list[AdvioLocalSceneStatus] | None = None

        def download(self, request: AdvioDownloadRequest) -> AdvioDownloadResult:
            self.calls["download"] += 1
            return AdvioDownloadResult(
                sequence_ids=request.sequence_ids,
                modalities=list(request.resolved_modalities()),
                downloaded_archives=[Path("advio-15.zip")],
                written_paths=[Path("data/advio/advio-15")],
            )

        def summarize(self, statuses: list[AdvioLocalSceneStatus] | None = None) -> AdvioDatasetSummary:
            self.calls["summarize"] += 1
            self.summary_statuses = statuses
            return summary

        def local_scene_statuses(self) -> list[object]:
            self.calls["local_scene_statuses"] += 1
            return statuses

    service = ServiceSpy()
    page_data = build_advio_page_data(
        SimpleNamespace(advio_service=service),
        AdvioDownloadFormData(
            request=AdvioDownloadRequest(sequence_ids=[15], preset=AdvioDownloadPreset.OFFLINE),
            submitted=True,
        ),
    )

    assert service.calls == {"download": 1, "summarize": 1, "local_scene_statuses": 1}
    assert service.summary_statuses is statuses
    assert page_data.summary == summary
    assert page_data.rows == [
        {
            "Scene": "advio-15",
            "Venue": "Office",
            "Dataset": "03",
            "Environment": "Indoor",
            "Packed Size (MB)": 10.0,
            "Local": False,
            "Replay Ready": True,
            "Offline Ready": True,
            "Local Modalities": "",
        }
    ]
    assert page_data.notice_level == "success"
    assert "Prepared 1 scene(s)" in page_data.notice_message


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


def test_advio_sequence_explorer_only_loads_selected_sample(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from prml_vslam.app.pages import advio as advio_page
    from prml_vslam.datasets import (
        AdvioEnvironment,
        AdvioLocalSceneStatus,
        AdvioPeopleLevel,
        AdvioSceneMetadata,
    )

    rendered_samples: list[int] = []
    loaded_ids: list[int] = []

    class DummyContext:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

    class ServiceSpy:
        def scene(self, sequence_id: int) -> SimpleNamespace:
            return SimpleNamespace(display_name=f"advio-{sequence_id:02d}")

        def load_local_sample(self, sequence_id: int) -> SimpleNamespace:
            loaded_ids.append(sequence_id)
            return SimpleNamespace(sequence_id=sequence_id)

    def _status(sequence_id: int) -> AdvioLocalSceneStatus:
        return AdvioLocalSceneStatus(
            scene=AdvioSceneMetadata(
                sequence_id=sequence_id,
                sequence_slug=f"advio-{sequence_id:02d}",
                venue="Office",
                dataset_code="03",
                environment=AdvioEnvironment.INDOOR,
                has_stairs=False,
                has_escalator=False,
                has_elevator=False,
                people_level=AdvioPeopleLevel.NONE,
                has_vehicles=False,
                calibration_name="iphone-03.yaml",
                archive_url=f"https://example.com/advio-{sequence_id:02d}.zip",
                archive_size_bytes=10_000_000,
                archive_md5="abc123",
            ),
            sequence_dir=Path(f"/tmp/advio-{sequence_id:02d}"),
            replay_ready=True,
            offline_ready=True,
        )

    monkeypatch.setattr(advio_page.st, "container", lambda *args, **kwargs: DummyContext())
    monkeypatch.setattr(advio_page.st, "subheader", lambda *args, **kwargs: None)
    monkeypatch.setattr(advio_page.st, "selectbox", lambda *args, **kwargs: 16)
    monkeypatch.setattr(advio_page.st, "warning", lambda *args, **kwargs: None)
    monkeypatch.setattr(advio_page.st, "info", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        advio_page, "_render_sequence_details", lambda sample: rendered_samples.append(sample.sequence_id)
    )

    advio_page._render_sequence_explorer(
        SimpleNamespace(
            state=AppState(advio=AdvioPageState(explorer_sequence_id=16)),
            store=FakeStore(),
            advio_service=ServiceSpy(),
        ),
        [_status(15), _status(16)],
    )

    assert loaded_ids == [16]
    assert rendered_samples == [16]


def test_advio_page_warns_when_local_scene_is_not_offline_ready(tmp_path: Path) -> None:
    dataset_root = tmp_path / "data" / "advio"
    sequence_dir = dataset_root / "advio-15" / "iphone"
    sequence_dir.mkdir(parents=True, exist_ok=True)
    (sequence_dir / "frames.mov").write_bytes(b"")
    (sequence_dir / "frames.csv").write_text("0.0,0\n0.1,1\n", encoding="utf-8")

    def _render_advio_page_script(root_path: str) -> None:
        from pathlib import Path
        from types import SimpleNamespace

        from prml_vslam.app.models import AppState
        from prml_vslam.app.pages.advio import render as render_advio_page
        from prml_vslam.datasets import AdvioDatasetService
        from prml_vslam.utils import PathConfig

        class _Store:
            def save(self, state: AppState) -> None:
                self.last_state = state.model_copy(deep=True)

        class _AdvioRuntime:
            def snapshot(self):
                from prml_vslam.app.services import AdvioPreviewSnapshot

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
    from prml_vslam.app.pages import record3d as record3d_page
    from prml_vslam.app.record3d_controller import handle_record3d_page_action

    class RuntimeSpy:
        def __init__(self) -> None:
            self.start_usb_calls = 0
            self.start_wifi_calls = 0

        def snapshot(self) -> Record3DStreamSnapshot:
            return Record3DStreamSnapshot()

        def stop(self) -> None:
            return None

        def start_usb(self, *, device_index: int) -> None:
            self.start_usb_calls += 1

        def start_wifi(self, *, device_address: str) -> None:
            self.start_wifi_calls += 1

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
        record3d_service=FakeRecord3DService([Record3DDevice(product_id=101, udid="device-101")]),
    )

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(record3d_page.st, "sidebar", DummyContext())
    monkeypatch.setattr(record3d_page.st, "subheader", lambda *args, **kwargs: None)
    monkeypatch.setattr(record3d_page.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(record3d_page.st, "segmented_control", lambda *args, **kwargs: Record3DTransportId.WIFI)
    monkeypatch.setattr(record3d_page.st, "form", lambda *args, **kwargs: DummyContext())
    monkeypatch.setattr(record3d_page.st, "text_input", lambda *args, **kwargs: "192.168.159.24")
    monkeypatch.setattr(record3d_page.st, "form_submit_button", lambda *args, **kwargs: False)
    monkeypatch.setattr(record3d_page.st, "button", lambda *args, **kwargs: False)
    monkeypatch.setattr(record3d_page.st, "expander", lambda *args, **kwargs: DummyContext())
    monkeypatch.setattr(record3d_page.st, "write", lambda *args, **kwargs: None)
    monkeypatch.setattr(record3d_page.st, "warning", lambda *args, **kwargs: None)
    monkeypatch.setattr(record3d_page.st, "info", lambda *args, **kwargs: None)

    action = record3d_page._render_sidebar_controls(context)
    monkeypatch.undo()

    assert runtime.start_usb_calls == 0
    assert runtime.start_wifi_calls == 0
    assert action.transport is Record3DTransportId.WIFI
    assert action.start_requested is False
    assert action.stop_requested is False
    assert context.state.record3d.transport is Record3DTransportId.USB

    handle_record3d_page_action(context, action)

    assert runtime.start_usb_calls == 0
    assert runtime.start_wifi_calls == 0
    assert context.state.record3d.transport is Record3DTransportId.WIFI


def test_record3d_page_dispatches_exactly_one_controller_action(monkeypatch: pytest.MonkeyPatch) -> None:
    from prml_vslam.app.pages import record3d as record3d_page

    dispatched_actions = []

    def _fake_render_sidebar_controls(context):
        del context
        return SimpleNamespace()

    def _fake_handle_action(context, action):
        del context
        dispatched_actions.append(action)
        return Record3DStreamSnapshot()

    monkeypatch.setattr(record3d_page, "render_page_intro", lambda **kwargs: None)
    monkeypatch.setattr(record3d_page, "_render_sidebar_controls", _fake_render_sidebar_controls)
    monkeypatch.setattr(record3d_page, "handle_record3d_page_action", _fake_handle_action)
    monkeypatch.setattr(record3d_page, "_render_live_snapshot", lambda context: None)

    context = SimpleNamespace(
        state=AppState(record3d=Record3DPageState()),
        store=FakeStore(),
        record3d_runtime=FakeRecord3DRuntime(),
        record3d_service=FakeRecord3DService([]),
    )
    record3d_page.render(context)

    assert len(dispatched_actions) == 1


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
                    state=Record3DStreamState.STREAMING,
                )
            return Record3DStreamSnapshot(
                transport=Record3DTransportId.USB,
                state=Record3DStreamState.CONNECTING,
                source_label=f"USB device #{self.start_usb_calls[-1]}",
            )

        def stop(self) -> None:
            self.stop_calls += 1

        def start_usb(self, *, device_index: int) -> None:
            self.start_usb_calls.append(device_index)

        def start_wifi(self, *, device_address: str) -> None:
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
    assert snapshot.state is Record3DStreamState.CONNECTING


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
                pose=SE3Pose(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
                uncertainty=np.ones((2, 2), dtype=np.float32),
                metadata={"transport": Record3DTransportId.USB.value},
            ),
            FramePacket(
                seq=1,
                timestamp_ns=1_100_000_000,
                arrival_timestamp_s=1.1,
                rgb=np.ones((2, 2, 3), dtype=np.uint8),
                depth=np.ones((2, 2), dtype=np.float32),
                intrinsics=CameraIntrinsics(fx=100.0, fy=200.0, cx=10.0, cy=20.0),
                pose=SE3Pose(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=0.5, tz=0.25),
                uncertainty=np.ones((2, 2), dtype=np.float32),
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
    assert snapshot.latest_packet.uncertainty is not None
    assert snapshot.measured_fps > 0.0
    assert snapshot.trajectory_positions_xyz.shape[1] == 3
    assert snapshot.trajectory_positions_xyz.shape[0] >= 2
    np.testing.assert_allclose(snapshot.trajectory_positions_xyz[-1], np.array([1.0, 0.5, 0.25]))

    controller.stop()

    assert usb_stream.disconnected is True
    assert controller.snapshot().state is Record3DStreamState.IDLE
    assert controller.snapshot().latest_packet is None
    assert controller.snapshot().trajectory_positions_xyz.shape == (0, 3)


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
                pose=SE3Pose(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
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
                pose=SE3Pose(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=0.5, tz=0.25),
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

    assert snapshot.state is AdvioPreviewStreamState.STREAMING
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
    assert controller.snapshot().state is AdvioPreviewStreamState.IDLE
    assert controller.snapshot().latest_packet is None
    assert controller.snapshot().trajectory_positions_xyz.shape == (0, 3)


def test_run_app_uses_streamlit_navigation(monkeypatch: pytest.MonkeyPatch) -> None:
    navigation_calls: list[tuple[str, bool, list[str], list[bool]]] = []

    class FakePage:
        def __init__(self, *, title: str, default: bool) -> None:
            self.title = title
            self.default = default

        def run(self) -> None:
            return None

    fake_context = SimpleNamespace(
        state=AppState(),
        record3d_runtime=FakeRecord3DRuntime(),
        advio_runtime=FakeAdvioRuntime(),
        store=FakeStore(),
    )

    monkeypatch.setattr(bootstrap, "build_context", lambda: fake_context)
    monkeypatch.setattr(bootstrap, "inject_styles", lambda: None)
    monkeypatch.setattr(bootstrap.st, "set_page_config", lambda **kwargs: None)

    def fake_page(page, *, title: str, icon: str | None = None, url_path: str | None = None, default: bool = False):
        del page, icon, url_path
        return FakePage(title=title, default=default)

    def fake_navigation(pages, *, position: str = "sidebar", expanded: bool = False):
        navigation_calls.append((position, expanded, [page.title for page in pages], [page.default for page in pages]))
        return pages[0]

    monkeypatch.setattr(bootstrap.st, "Page", fake_page)
    monkeypatch.setattr(bootstrap.st, "navigation", fake_navigation)

    bootstrap.run_app()

    assert navigation_calls == [
        ("sidebar", True, ["Record3D", "ADVIO", "Pipeline", "Metrics"], [True, False, False, False])
    ]


def test_metrics_page_entry_stops_record3d_runtime_when_switching(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = FakeRecord3DRuntime()
    context = SimpleNamespace(
        state=AppState(record3d=Record3DPageState(is_running=True)),
        store=FakeStore(),
        record3d_runtime=runtime,
        advio_runtime=FakeAdvioRuntime(),
    )
    monkeypatch.setattr(bootstrap, "render_metrics_page", lambda ctx: None)

    bootstrap._render_metrics_page_entry(context)

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
    monkeypatch.setattr(bootstrap, "render_pipeline_page", lambda ctx: None)

    bootstrap._render_pipeline_page_entry(context)

    assert context.state.advio.preview_is_running is False
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


def test_session_state_store_accepts_hot_reloaded_advio_runtime_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    class HotReloadedRuntime:
        def snapshot(self) -> AdvioPreviewSnapshot:
            return AdvioPreviewSnapshot()

        def stop(self) -> None:
            return None

        def start(self, *, sequence_id: int, sequence_label: str, pose_source: AdvioPoseSource, stream) -> None:
            del sequence_id, sequence_label, pose_source, stream
            return None

    fake_session_state = {"_prml_vslam_advio_runtime": HotReloadedRuntime()}
    monkeypatch.setattr("prml_vslam.app.state.st.session_state", fake_session_state)

    runtime = SessionStateStore().load_advio_runtime()

    assert runtime is fake_session_state["_prml_vslam_advio_runtime"]


def test_normalize_grayscale_ignores_non_finite_depth_values() -> None:
    from prml_vslam.app.image_utils import normalize_grayscale_image

    image = np.array([[np.nan, 1.0], [np.inf, 3.0]], dtype=np.float32)

    with warnings.catch_warnings(record=True) as captured_warnings:
        warnings.simplefilter("always")
        normalized = normalize_grayscale_image(image)

    assert normalized.dtype == np.uint8
    assert normalized.shape == image.shape
    assert not captured_warnings
    assert normalized[0, 0] == 0
    assert normalized[1, 0] == 0


def test_format_camera_intrinsics_latex_preserves_existing_output() -> None:
    from prml_vslam.app.camera_display import format_camera_intrinsics_latex

    assert format_camera_intrinsics_latex(fx=100.0, fy=101.0, cx=32.0, cy=24.0) == (
        "K = \\begin{bmatrix}"
        "100.000 & 0.000 & 32.000 \\\\ "
        "0.000 & 101.000 & 24.000 \\\\ "
        "0.000 & 0.000 & 1.000"
        "\\end{bmatrix}"
    )
