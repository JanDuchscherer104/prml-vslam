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
    AdvioPreviewStreamState,
    AppState,
    Record3DPageState,
    Record3DStreamSnapshot,
    Record3DStreamState,
)
from prml_vslam.app.services import (
    AdvioPreviewRuntimeController,
    Record3DStreamRuntimeController,
)
from prml_vslam.app.state import SessionStateStore
from prml_vslam.datasets.advio import AdvioPoseSource
from prml_vslam.datasets.advio.advio_layout import resolve_existing_reference_tum
from prml_vslam.datasets.contracts import DatasetId
from prml_vslam.eval import TrajectoryEvaluationService
from prml_vslam.eval.contracts import SelectionSnapshot
from prml_vslam.interfaces import CameraIntrinsics, FramePacket, SE3Pose
from prml_vslam.io.record3d import Record3DDevice, Record3DTransportId
from prml_vslam.methods import MethodId
from prml_vslam.pipeline.session import PipelineSessionSnapshot, PipelineSessionState
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


class FakePipelineRuntime:
    """Minimal pipeline runtime stand-in for direct page-render and navigation tests."""

    def __init__(self, snapshot: PipelineSessionSnapshot | None = None) -> None:
        self._snapshot = snapshot or PipelineSessionSnapshot()
        self.stop_calls = 0
        self.start_calls: list[dict[str, object]] = []

    def snapshot(self) -> PipelineSessionSnapshot:
        return self._snapshot

    def stop(self) -> None:
        self.stop_calls += 1
        self._snapshot = PipelineSessionSnapshot(state=PipelineSessionState.STOPPED)

    def start(self, **kwargs: object) -> None:
        self.start_calls.append(kwargs)
        self._snapshot = PipelineSessionSnapshot(state=PipelineSessionState.CONNECTING)


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
    reference_path = tmp_path / "data" / "advio" / "advio-15" / "ground-truth" / "ground_truth.tum"
    estimate_path = tmp_path / "artifacts" / "advio-15" / "vista" / "slam" / "trajectory.tum"
    _write_tum(reference_path, [(0.0, 0.0, 0.0, 0.0), (0.1, 1.0, 0.0, 0.0)])
    _write_tum(estimate_path, [(10.0, 0.0, 0.0, 0.0), (10.1, 1.0, 0.0, 0.0)])

    path_config = PathConfig(
        root=tmp_path,
        artifacts_dir=tmp_path / "artifacts",
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
    from prml_vslam.pipeline.contracts import ArtifactRef, SequenceManifest, SlamArtifacts

    pipeline_page._compute_evo_preview.cache_clear()
    reference_path = tmp_path / "reference.tum"
    estimate_path = tmp_path / "estimate.tum"
    _write_tum(reference_path, [(0.0, 0.0, 0.0, 0.0), (0.1, 1.0, 0.0, 0.0), (0.2, 2.0, 1.0, 0.0)])
    _write_tum(estimate_path, [(0.0, 0.0, 0.0, 0.0), (0.1, 1.1, 0.1, 0.0), (0.2, 2.2, 1.2, 0.0)])

    snapshot = PipelineSessionSnapshot(
        sequence_manifest=SequenceManifest(sequence_id="advio-15", reference_tum_path=reference_path),
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


def test_pipeline_page_action_starts_pipeline_session_once_without_app_manifest_writes(tmp_path: Path) -> None:
    from prml_vslam.app.pages import pipeline as pipeline_page

    source = object()

    class AdvioServiceSpy:
        def __init__(self) -> None:
            self.source_calls: list[tuple[int, AdvioPoseSource, bool]] = []

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

    runtime = FakePipelineRuntime()
    context = SimpleNamespace(
        path_config=PathConfig(root=tmp_path, artifacts_dir=tmp_path / "artifacts", captures_dir=tmp_path / "captures"),
        advio_service=AdvioServiceSpy(),
        pipeline_runtime=runtime,
        state=AppState(),
        store=FakeStore(),
    )

    error_message = pipeline_page._handle_pipeline_page_action(
        context,
        pipeline_page.PipelinePageAction(
            sequence_id=15,
            mode=pipeline_page.PipelineMode.OFFLINE,
            method=MethodId.VISTA,
            pose_source=AdvioPoseSource.GROUND_TRUTH,
            respect_video_rotation=True,
            start_requested=True,
        ),
    )

    assert error_message is None
    assert context.advio_service.source_calls == [(15, AdvioPoseSource.GROUND_TRUTH, True)]
    assert len(runtime.start_calls) == 1
    assert runtime.start_calls[0]["source"] is source
    request = runtime.start_calls[0]["request"]
    assert request.source.dataset_id is DatasetId.ADVIO
    assert request.slam.method is MethodId.VISTA
    assert request.evaluation.compare_to_arcore is False
    assert request.evaluation.evaluate_cloud is False
    assert request.evaluation.evaluate_efficiency is False


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
    )

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        record3d_page,
        "list_record3d_usb_devices",
        lambda: [Record3DDevice(product_id=101, udid="device-101")],
    )
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
    assert context.state.record3d.wifi_device_address == ""
    assert action.transport is Record3DTransportId.WIFI
    assert action.start_requested is False
    assert action.stop_requested is False
    assert context.state.record3d.transport is Record3DTransportId.USB

    handle_record3d_page_action(context, action)

    assert runtime.start_usb_calls == 0
    assert runtime.start_wifi_calls == 0
    assert context.state.record3d.transport is Record3DTransportId.WIFI


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


def test_metrics_page_entry_stops_record3d_runtime_when_switching(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = FakeRecord3DRuntime()
    context = SimpleNamespace(
        state=AppState(record3d=Record3DPageState(is_running=True)),
        store=FakeStore(),
        record3d_runtime=runtime,
        advio_runtime=FakeAdvioRuntime(),
        pipeline_runtime=FakePipelineRuntime(),
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


def test_metrics_page_entry_keeps_pipeline_runtime_when_switching(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime = FakePipelineRuntime(snapshot=PipelineSessionSnapshot(state=PipelineSessionState.RUNNING))
    context = SimpleNamespace(
        state=AppState(),
        store=FakeStore(),
        record3d_runtime=FakeRecord3DRuntime(),
        advio_runtime=FakeAdvioRuntime(),
        pipeline_runtime=runtime,
    )
    monkeypatch.setattr(bootstrap, "render_metrics_page", lambda ctx: None)

    bootstrap._render_metrics_page_entry(context)

    assert runtime.stop_calls == 0


def test_session_state_store_round_trips_pipeline_session_service(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_session_state: dict[str, object] = {}
    monkeypatch.setattr("prml_vslam.app.state.st.session_state", fake_session_state)
    store = SessionStateStore()

    runtime = store.load_pipeline_runtime()

    assert fake_session_state["_prml_vslam_pipeline_runtime"] is runtime
    assert store.load_pipeline_runtime() is runtime


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
