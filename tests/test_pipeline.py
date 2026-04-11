"""Tests for the typed pipeline planning surfaces."""

from __future__ import annotations

import string
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from pydantic import ValidationError

from prml_vslam.datasets.contracts import DatasetId
from prml_vslam.interfaces import CameraIntrinsics, FramePacket, SE3Pose
from prml_vslam.io.record3d import Record3DTransportId
from prml_vslam.methods import MethodId, MockSlamBackendConfig
from prml_vslam.methods.protocols import OfflineSlamBackend, SlamBackend, SlamSession, StreamingSlamBackend
from prml_vslam.pipeline import PipelineMode, RunRequest, SequenceManifest
from prml_vslam.pipeline.contracts import (
    BenchmarkEvaluationConfig,
    DatasetSourceSpec,
    Record3DLiveSourceSpec,
    ReferenceConfig,
    RunPlan,
    RunPlanStage,
    RunPlanStageId,
    SlamConfig,
    StageExecutionStatus,
    StageManifest,
    VideoSourceSpec,
)
from prml_vslam.pipeline.run_service import RunService
from prml_vslam.pipeline.session import PipelineSessionService, PipelineSessionSnapshot, PipelineSessionState
from prml_vslam.protocols.source import OfflineSequenceSource, StreamingSequenceSource
from prml_vslam.utils import PathConfig


def test_run_request_builds_expected_stage_sequence_from_direct_config() -> None:
    path_config = PathConfig()
    request = RunRequest(
        experiment_name="Lobby Sweep 01",
        output_dir=Path(".artifacts"),
        source=VideoSourceSpec(video_path=Path("captures/lobby.mp4"), frame_stride=2),
        slam=SlamConfig(method=MethodId.VISTA, emit_dense_points=True, emit_sparse_points=True),
        reference=ReferenceConfig(enabled=True),
        evaluation=BenchmarkEvaluationConfig(
            evaluate_trajectory=True,
            compare_to_arcore=True,
            evaluate_cloud=True,
            evaluate_efficiency=True,
        ),
    )
    plan = request.build(path_config)
    run_paths = path_config.plan_run_paths(
        experiment_name=request.experiment_name,
        method_slug=request.slam.method.value,
        output_dir=request.output_dir,
    )

    assert plan.artifact_root == run_paths.artifact_root
    assert [stage.id for stage in plan.stages] == [
        RunPlanStageId.INGEST,
        RunPlanStageId.SLAM,
        RunPlanStageId.REFERENCE_RECONSTRUCTION,
        RunPlanStageId.TRAJECTORY_EVALUATION,
        RunPlanStageId.CLOUD_EVALUATION,
        RunPlanStageId.EFFICIENCY_EVALUATION,
        RunPlanStageId.SUMMARY,
    ]
    assert plan.stages[0].outputs == [run_paths.sequence_manifest_path]
    assert plan.stages[1].outputs == [
        run_paths.trajectory_path,
        run_paths.sparse_points_path,
        run_paths.dense_points_path,
    ]
    assert plan.stages[-1].outputs == [run_paths.summary_path, run_paths.stage_manifests_path]
    assert request.model_dump()["evaluation"] == {
        "evaluate_trajectory": True,
        "compare_to_arcore": True,
        "evaluate_cloud": True,
        "evaluate_efficiency": True,
    }


def test_run_request_build_keeps_legacy_default_stage_selection() -> None:
    request = RunRequest(
        experiment_name="Default Check",
        output_dir=Path(".artifacts"),
        source=VideoSourceSpec(video_path=Path("captures/default-check.mp4")),
        slam=SlamConfig(method=MethodId.MSTR),
    )

    plan = request.build()

    assert [stage.id for stage in plan.stages] == [
        RunPlanStageId.INGEST,
        RunPlanStageId.SLAM,
        RunPlanStageId.TRAJECTORY_EVALUATION,
        RunPlanStageId.EFFICIENCY_EVALUATION,
        RunPlanStageId.SUMMARY,
    ]


def test_run_request_build_uses_default_usb_descriptor_when_index_missing() -> None:
    request = RunRequest(
        experiment_name="Record3D Default USB",
        mode=PipelineMode.STREAMING,
        output_dir=Path(".artifacts"),
        source=Record3DLiveSourceSpec(
            transport=Record3DTransportId.USB,
            device_index=None,
        ),
        slam=SlamConfig(method=MethodId.VISTA),
    )

    plan = request.build()

    assert plan.stages[0].summary == (
        "Capture the Record3D usb source 'default USB device' with persistence into a replayable sequence manifest."
    )


def test_run_request_build_respects_disabled_optional_stage_toggles() -> None:
    request = RunRequest(
        experiment_name="Quick Check",
        output_dir=Path(".artifacts"),
        source=VideoSourceSpec(video_path=Path("captures/quick-check.mp4")),
        slam=SlamConfig(method=MethodId.MSTR, emit_dense_points=False, emit_sparse_points=False),
        reference=ReferenceConfig(enabled=False),
    )
    request.evaluation.evaluate_trajectory = False
    request.evaluation.compare_to_arcore = False
    request.evaluation.evaluate_cloud = False
    request.evaluation.evaluate_efficiency = False

    plan = request.build()

    assert [stage.id for stage in plan.stages] == [
        RunPlanStageId.INGEST,
        RunPlanStageId.SLAM,
        RunPlanStageId.SUMMARY,
    ]


def test_run_request_build_rejects_cloud_evaluation_without_dense_points() -> None:
    request = RunRequest(
        experiment_name="No Dense Cloud Eval",
        output_dir=Path(".artifacts"),
        source=VideoSourceSpec(video_path=Path("captures/no-dense-cloud.mp4")),
        slam=SlamConfig(method=MethodId.VISTA, emit_dense_points=False),
        evaluation=BenchmarkEvaluationConfig(evaluate_cloud=True),
    )

    with pytest.raises(ValueError, match="slam.emit_dense_points=True"):
        request.build()


def test_run_request_requires_slam_config() -> None:
    with pytest.raises(ValidationError):
        RunRequest(
            experiment_name="Missing SLAM",
            output_dir=Path(".artifacts"),
            source=VideoSourceSpec(video_path=Path("captures/missing-slam.mp4")),
        )


def test_run_plan_stage_rows_are_owned_by_contract() -> None:
    plan = RunPlan(
        run_id="demo",
        mode=PipelineMode.OFFLINE,
        method=MethodId.VISTA,
        artifact_root=Path("/tmp/demo"),
        source=VideoSourceSpec(video_path=Path("captures/demo.mp4")),
        stages=[
            RunPlanStage(
                id=RunPlanStageId.SLAM,
                title="Run SLAM",
                summary="demo",
                outputs=[Path("/tmp/demo/slam/trajectory.tum")],
            )
        ],
    )

    assert plan.stage_rows() == [
        {
            "Stage": "Run SLAM",
            "Id": "slam",
            "Outputs": "trajectory.tum",
        }
    ]


def test_stage_manifest_table_rows_are_owned_by_contract() -> None:
    manifests = [
        StageManifest(
            stage_id=RunPlanStageId.SLAM,
            config_hash="abc",
            input_fingerprint="def",
            output_paths={"trajectory": Path("/tmp/demo/slam/trajectory.tum")},
            status=StageExecutionStatus.RAN,
        )
    ]

    assert StageManifest.table_rows(manifests) == [
        {
            "Stage": "slam",
            "Status": "ran",
            "Config Hash": "abc",
            "Outputs": "trajectory.tum",
        }
    ]


def test_pipeline_protocols_accept_current_structural_implementations(tmp_path: Path) -> None:
    sequence_manifest = SequenceManifest(sequence_id="advio-15")
    source = FakeStreamingSource(
        sequence_manifest=sequence_manifest,
        stream=FinitePacketStream([_make_packet(seq=0, timestamp_ns=0, tx=0.0)]),
    )
    backend = MockSlamBackendConfig(method_id=MethodId.MSTR).setup_target()
    assert backend is not None
    session = backend.start_session(
        SlamConfig(method=MethodId.MSTR),
        tmp_path / "streaming-artifacts",
    )

    assert isinstance(source, OfflineSequenceSource)
    assert isinstance(source, StreamingSequenceSource)
    assert isinstance(backend, OfflineSlamBackend)
    assert isinstance(backend, StreamingSlamBackend)
    assert isinstance(backend, SlamBackend)
    assert isinstance(session, SlamSession)
    assert backend.method_id is MethodId.MSTR


class FinitePacketStream:
    """Packet stream that terminates with EOF after the last packet."""

    def __init__(self, packets: list[FramePacket]) -> None:
        self._packets = packets
        self.disconnected = False
        self.wait_calls = 0

    def connect(self) -> str:
        return "finite-stream"

    def disconnect(self) -> None:
        self.disconnected = True

    def wait_for_packet(self, timeout_seconds: float | None = None) -> FramePacket:
        del timeout_seconds
        if self.wait_calls >= len(self._packets):
            raise EOFError("stream complete")
        packet = self._packets[self.wait_calls]
        self.wait_calls += 1
        return packet


class StopAwarePacketStream:
    """Packet stream that keeps producing frames until the service disconnects it."""

    def __init__(self, packet_template: FramePacket) -> None:
        self._packet_template = packet_template
        self.disconnected = False
        self.wait_calls = 0

    def connect(self) -> str:
        return "stop-aware-stream"

    def disconnect(self) -> None:
        self.disconnected = True

    def wait_for_packet(self, timeout_seconds: float | None = None) -> FramePacket:
        del timeout_seconds
        time.sleep(0.01)
        if self.disconnected:
            raise EOFError("stream disconnected")
        packet = self._packet_template.model_copy(
            update={
                "seq": self.wait_calls,
                "timestamp_ns": self._packet_template.timestamp_ns + self.wait_calls * 10_000_000,
            }
        )
        self.wait_calls += 1
        return packet


class SlowClosingMockSlamBackend:
    """Mock backend wrapper whose session close exceeds the generic worker-stop timeout."""

    def __init__(self, *, close_sleep_seconds: float) -> None:
        backend = MockSlamBackendConfig().setup_target()
        assert backend is not None
        self._backend = backend
        self._close_sleep_seconds = close_sleep_seconds
        self.method_id = backend.method_id

    def start_session(self, cfg: SlamConfig, artifact_root: Path):
        session = self._backend.start_session(cfg, artifact_root)
        close_sleep_seconds = self._close_sleep_seconds

        class _SlowClosingSession:
            def step(self, frame: FramePacket) -> object:
                return session.step(frame)

            def close(self):
                time.sleep(close_sleep_seconds)
                return session.close()

        return _SlowClosingSession()

    def run_sequence(self, sequence: SequenceManifest, cfg: SlamConfig, artifact_root: Path):
        return self._backend.run_sequence(sequence, cfg, artifact_root)


class ExplodingPacketStream:
    """Packet stream that fails during SLAM processing."""

    def __init__(self, message: str) -> None:
        self._message = message
        self.disconnected = False
        self.wait_calls = 0

    def connect(self) -> str:
        return "exploding-stream"

    def disconnect(self) -> None:
        self.disconnected = True

    def wait_for_packet(self, timeout_seconds: float | None = None) -> FramePacket:
        del timeout_seconds
        self.wait_calls += 1
        raise RuntimeError(self._message)


class FakeStreamingSource:
    """Small streaming source stand-in for pipeline session tests."""

    def __init__(self, *, sequence_manifest: SequenceManifest, stream, label: str = "advio-15 · Office 03") -> None:
        self.label = label
        self._sequence_manifest = sequence_manifest
        self._stream = stream
        self.prepare_calls = 0
        self.open_calls: list[bool] = []
        self.last_output_dir: Path | None = None

    def prepare_sequence_manifest(self, output_dir: Path) -> SequenceManifest:
        self.prepare_calls += 1
        self.last_output_dir = output_dir
        return self._sequence_manifest

    def open_stream(self, *, loop: bool):
        self.open_calls.append(loop)
        return self._stream


def _make_packet(*, seq: int, timestamp_ns: int, tx: float) -> FramePacket:
    return FramePacket(
        seq=seq,
        timestamp_ns=timestamp_ns,
        rgb=np.zeros((4, 4, 3), dtype=np.uint8),
        intrinsics=CameraIntrinsics(fx=200.0, fy=200.0, cx=1.5, cy=1.5, width_px=4, height_px=4),
        pose=SE3Pose(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=tx, ty=0.0, tz=0.0),
    )


def _build_streaming_request(
    path_config: PathConfig,
    *,
    mode: PipelineMode = PipelineMode.OFFLINE,
    evaluate_trajectory: bool = True,
    compare_to_arcore: bool = False,
    evaluate_cloud: bool = False,
    evaluate_efficiency: bool = False,
) -> RunRequest:
    return RunRequest(
        experiment_name=f"advio-{mode.value}-demo-vista",
        mode=mode,
        output_dir=path_config.artifacts_dir,
        source=DatasetSourceSpec(dataset_id=DatasetId.ADVIO, sequence_id="advio-15"),
        slam=SlamConfig(method=MethodId.VISTA, emit_dense_points=True),
        reference=ReferenceConfig(enabled=False),
        evaluation=BenchmarkEvaluationConfig(
            evaluate_trajectory=evaluate_trajectory,
            compare_to_arcore=compare_to_arcore,
            evaluate_cloud=evaluate_cloud,
            evaluate_efficiency=evaluate_efficiency,
        ),
    )


def _wait_for_terminal_snapshot(
    service,
    *,
    timeout_seconds: float = 2.0,
):
    deadline = time.time() + timeout_seconds
    snapshot = service.snapshot()
    while snapshot.state in {PipelineSessionState.CONNECTING, PipelineSessionState.RUNNING} and time.time() < deadline:
        time.sleep(0.01)
        snapshot = service.snapshot()
    return snapshot


def test_pipeline_session_service_completes_supported_run_and_persists_outputs(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts", captures_dir=tmp_path / "captures")
    request = _build_streaming_request(path_config)
    plan = request.build(path_config)
    run_paths = path_config.plan_run_paths(
        experiment_name=request.experiment_name,
        method_slug=request.slam.method.value,
        output_dir=request.output_dir,
    )
    source = FakeStreamingSource(
        sequence_manifest=SequenceManifest(
            sequence_id="advio-15", video_path=tmp_path / ".data" / "advio" / "frames.mov"
        ),
        stream=FinitePacketStream(
            [
                _make_packet(seq=0, timestamp_ns=1_000_000_000, tx=0.0),
                _make_packet(seq=1, timestamp_ns=2_000_000_000, tx=1.0),
            ]
        ),
    )
    backend = MockSlamBackendConfig().setup_target()
    assert backend is not None
    service = PipelineSessionService(frame_timeout_seconds=0.01)

    service.start(request=request, plan=plan, source=source, slam_backend=backend)
    snapshot = _wait_for_terminal_snapshot(service)

    assert snapshot.state is PipelineSessionState.COMPLETED
    assert source.prepare_calls == 1
    assert source.open_calls == [False]
    assert source.last_output_dir == run_paths.sequence_manifest_path.parent
    assert snapshot.sequence_manifest is not None
    assert snapshot.slam is not None
    assert snapshot.summary is not None
    assert snapshot.summary.stage_status == {
        RunPlanStageId.INGEST: StageExecutionStatus.RAN,
        RunPlanStageId.SLAM: StageExecutionStatus.RAN,
        RunPlanStageId.SUMMARY: StageExecutionStatus.RAN,
    }
    assert [manifest.stage_id for manifest in snapshot.stage_manifests] == [
        RunPlanStageId.INGEST,
        RunPlanStageId.SLAM,
        RunPlanStageId.SUMMARY,
    ]
    assert all(manifest.status is not StageExecutionStatus.HIT for manifest in snapshot.stage_manifests)
    assert run_paths.sequence_manifest_path.exists()
    assert run_paths.summary_path.exists()
    assert run_paths.stage_manifests_path.exists()
    assert snapshot.slam.trajectory_tum.path.exists()
    assert snapshot.slam.dense_points_ply is not None
    assert snapshot.slam.dense_points_ply.path.exists()


def test_pipeline_session_service_stop_finishes_cleanly(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts", captures_dir=tmp_path / "captures")
    request = _build_streaming_request(path_config, mode=PipelineMode.STREAMING)
    plan = request.build(path_config)
    source = FakeStreamingSource(
        sequence_manifest=SequenceManifest(
            sequence_id="advio-15", video_path=tmp_path / ".data" / "advio" / "frames.mov"
        ),
        stream=StopAwarePacketStream(_make_packet(seq=0, timestamp_ns=1_000_000_000, tx=0.0)),
    )
    backend = MockSlamBackendConfig().setup_target()
    assert backend is not None
    service = PipelineSessionService(frame_timeout_seconds=0.01)

    service.start(request=request, plan=plan, source=source, slam_backend=backend)
    deadline = time.time() + 2.0
    while service.snapshot().state is PipelineSessionState.CONNECTING and time.time() < deadline:
        time.sleep(0.01)

    service.stop()
    snapshot = service.snapshot()

    assert source.open_calls == [True]
    assert snapshot.state is PipelineSessionState.STOPPED
    assert snapshot.summary is not None
    assert snapshot.summary.stage_status[RunPlanStageId.SUMMARY] is StageExecutionStatus.RAN


def test_pipeline_session_service_stop_allows_longer_backend_shutdown(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts", captures_dir=tmp_path / "captures")
    request = _build_streaming_request(path_config, mode=PipelineMode.STREAMING)
    plan = request.build(path_config)
    source = FakeStreamingSource(
        sequence_manifest=SequenceManifest(
            sequence_id="advio-15", video_path=tmp_path / ".data" / "advio" / "frames.mov"
        ),
        stream=StopAwarePacketStream(_make_packet(seq=0, timestamp_ns=1_000_000_000, tx=0.0)),
    )
    backend = SlowClosingMockSlamBackend(close_sleep_seconds=2.2)
    service = PipelineSessionService(frame_timeout_seconds=0.01)

    service.start(request=request, plan=plan, source=source, slam_backend=backend)
    deadline = time.time() + 2.0
    while service.snapshot().state is PipelineSessionState.CONNECTING and time.time() < deadline:
        time.sleep(0.01)

    service.stop()
    snapshot = service.snapshot()

    assert snapshot.state is PipelineSessionState.STOPPED
    assert snapshot.summary is not None
    assert snapshot.summary.stage_status[RunPlanStageId.SUMMARY] is StageExecutionStatus.RAN


def test_run_service_rejects_unsupported_stages_before_start(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts", captures_dir=tmp_path / "captures")
    request = _build_streaming_request(path_config, compare_to_arcore=True)
    source = FakeStreamingSource(
        sequence_manifest=SequenceManifest(
            sequence_id="advio-15", video_path=tmp_path / ".data" / "advio" / "frames.mov"
        ),
        stream=FinitePacketStream([_make_packet(seq=0, timestamp_ns=1_000_000_000, tx=0.0)]),
    )
    service = RunService(path_config=path_config)

    with pytest.raises(RuntimeError, match="Unsupported stages"):
        service.start_run(request=request, source=source)

    snapshot = service.snapshot()

    assert snapshot.state is PipelineSessionState.FAILED
    assert source.prepare_calls == 0
    assert source.open_calls == []
    assert snapshot.summary is None
    assert snapshot.stage_manifests == []


def test_pipeline_session_service_reports_failed_runtime_errors(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts", captures_dir=tmp_path / "captures")
    request = _build_streaming_request(path_config)
    plan = request.build(path_config)
    source = FakeStreamingSource(
        sequence_manifest=SequenceManifest(
            sequence_id="advio-15", video_path=tmp_path / ".data" / "advio" / "frames.mov"
        ),
        stream=ExplodingPacketStream("synthetic tracker failure"),
    )
    backend = MockSlamBackendConfig().setup_target()
    assert backend is not None
    service = PipelineSessionService(frame_timeout_seconds=0.01)

    service.start(request=request, plan=plan, source=source, slam_backend=backend)
    snapshot = _wait_for_terminal_snapshot(service)

    assert snapshot.state is PipelineSessionState.FAILED
    assert "synthetic tracker failure" in snapshot.error_message
    assert snapshot.summary is not None
    assert snapshot.summary.stage_status == {
        RunPlanStageId.INGEST: StageExecutionStatus.RAN,
        RunPlanStageId.SLAM: StageExecutionStatus.FAILED,
        RunPlanStageId.SUMMARY: StageExecutionStatus.RAN,
    }
    assert all(manifest.status is not StageExecutionStatus.HIT for manifest in snapshot.stage_manifests)


def test_pipeline_session_service_uses_stable_non_synthetic_provenance_hashes(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts", captures_dir=tmp_path / "captures")
    request = _build_streaming_request(path_config)
    plan = request.build(path_config)
    backend = MockSlamBackendConfig().setup_target()
    assert backend is not None

    def _run_once() -> dict[RunPlanStageId, tuple[str, str]]:
        source = FakeStreamingSource(
            sequence_manifest=SequenceManifest(
                sequence_id="advio-15",
                video_path=tmp_path / ".data" / "advio" / "frames.mov",
                reference_tum_path=tmp_path / ".data" / "advio" / "advio-15" / "ground-truth" / "ground_truth.tum",
            ),
            stream=FinitePacketStream(
                [
                    _make_packet(seq=0, timestamp_ns=1_000_000_000, tx=0.0),
                    _make_packet(seq=1, timestamp_ns=2_000_000_000, tx=1.0),
                ]
            ),
        )
        service = PipelineSessionService(frame_timeout_seconds=0.01)
        service.start(request=request, plan=plan, source=source, slam_backend=backend)
        snapshot = _wait_for_terminal_snapshot(service)
        assert snapshot.state is PipelineSessionState.COMPLETED
        assert all(manifest.status is not StageExecutionStatus.HIT for manifest in snapshot.stage_manifests)
        return {
            manifest.stage_id: (manifest.config_hash, manifest.input_fingerprint)
            for manifest in snapshot.stage_manifests
        }

    first_hashes = _run_once()
    second_hashes = _run_once()

    assert first_hashes == second_hashes
    for config_hash, input_fingerprint in first_hashes.values():
        assert len(config_hash) == 64
        assert len(input_fingerprint) == 64
        assert set(config_hash) <= set(string.hexdigits.lower())
        assert set(input_fingerprint) <= set(string.hexdigits.lower())


class SessionServiceSpy:
    """Small session-service double for RunService tests."""

    def __init__(self) -> None:
        self.start_calls: list[dict[str, object]] = []
        self.failed_start_calls: list[dict[str, object]] = []
        self.stop_calls = 0
        self._snapshot = PipelineSessionSnapshot()

    def start(self, **kwargs: object) -> None:
        self.start_calls.append(kwargs)
        self._snapshot = PipelineSessionSnapshot(state=PipelineSessionState.CONNECTING, plan=kwargs["plan"])

    def stop(self) -> None:
        self.stop_calls += 1

    def snapshot(self) -> PipelineSessionSnapshot:
        return self._snapshot

    def set_failed_start(self, *, plan, error_message: str) -> None:
        self.failed_start_calls.append({"plan": plan, "error_message": error_message})
        self._snapshot = PipelineSessionSnapshot(
            state=PipelineSessionState.FAILED,
            plan=plan,
            error_message=error_message,
        )


def test_run_service_builds_plan_and_passes_resolved_dependencies_to_session(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts", captures_dir=tmp_path / "captures")
    request = _build_streaming_request(path_config, evaluate_trajectory=False)
    source = SimpleNamespace(label="advio-demo-source")
    session_service = SessionServiceSpy()
    backend = object()
    service = RunService(
        path_config=path_config,
        session_service=session_service,
        slam_backend_factory=lambda method_id: backend,
    )

    service.start_run(request=request, source=source)

    assert len(session_service.start_calls) == 1
    start_call = session_service.start_calls[0]
    assert start_call["request"] is request
    assert start_call["source"] is source
    assert start_call["slam_backend"] is backend
    assert start_call["plan"].artifact_root == request.build(path_config).artifact_root


def test_run_service_stop_and_snapshot_delegate_to_session_service() -> None:
    session_service = SessionServiceSpy()
    expected_snapshot = PipelineSessionSnapshot(state=PipelineSessionState.RUNNING)
    session_service._snapshot = expected_snapshot
    service = RunService(session_service=session_service)

    assert service.snapshot() is expected_snapshot

    service.stop_run()

    assert session_service.stop_calls == 1
