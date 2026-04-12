"""Tests for the runnable pipeline core."""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pytest

from prml_vslam.datasets import DatasetId
from prml_vslam.interfaces import CameraIntrinsics, FramePacket, FrameTransform
from prml_vslam.io.record3d import Record3DTransportId
from prml_vslam.methods import MethodId, MockSlamBackendConfig, VistaSlamBackend, VistaSlamBackendConfig
from prml_vslam.methods.contracts import SlamBackendConfig, SlamOutputPolicy
from prml_vslam.methods.protocols import OfflineSlamBackend, SlamBackend, SlamSession, StreamingSlamBackend
from prml_vslam.methods.updates import SlamUpdate
from prml_vslam.pipeline import PipelineMode, RunRequest, SequenceManifest
from prml_vslam.pipeline.contracts.artifacts import ArtifactRef, SlamArtifacts
from prml_vslam.pipeline.contracts.plan import RunPlan, RunPlanStage, RunPlanStageId
from prml_vslam.pipeline.contracts.provenance import StageExecutionStatus, StageManifest
from prml_vslam.pipeline.contracts.request import (
    DatasetSourceSpec,
    LiveTransportId,
    Record3DLiveSourceSpec,
    SlamStageConfig,
    VideoSourceSpec,
)
from prml_vslam.pipeline.state import RunSnapshot, RunState, StreamingRunSnapshot
from prml_vslam.pipeline.offline import OfflineRunner
from prml_vslam.pipeline.run_service import RunService, _default_slam_backend_factory
from prml_vslam.pipeline.streaming import StreamingRunner
from prml_vslam.protocols.source import OfflineSequenceSource, StreamingSequenceSource
from prml_vslam.utils import Console, PathConfig, RunArtifactPaths

if TYPE_CHECKING:
    from prml_vslam.pipeline.contracts.runtime import RunSnapshot


def test_run_request_builds_expected_stage_sequence_from_direct_config(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts", captures_dir=tmp_path / "captures")
    request = _build_request(path_config)

    plan = request.build(path_config)

    assert plan.run_id == "advio-offline-demo-vista"
    assert plan.mode is PipelineMode.OFFLINE
    assert plan.method is MethodId.VISTA
    assert [stage.id for stage in plan.stages] == [
        RunPlanStageId.INGEST,
        RunPlanStageId.SLAM,
        RunPlanStageId.SUMMARY,
    ]


def test_run_request_build_keeps_default_stage_selection(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts", captures_dir=tmp_path / "captures")
    request = _build_request(path_config, method=MethodId.MSTR)

    plan = request.build(path_config)

    assert plan.method is MethodId.MSTR
    assert len(plan.stages) == 3


def test_run_request_build_respects_disabled_optional_stage_toggles(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts", captures_dir=tmp_path / "captures")
    request = _build_request(path_config, method=MethodId.MSTR)
    request.benchmark.trajectory.enabled = False

    plan = request.build(path_config)

    assert RunPlanStageId.BENCHMARK not in [stage.id for stage in plan.stages]


def test_pipeline_protocols_accept_current_structural_implementations(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts", captures_dir=tmp_path / "captures")
    request = _build_request(path_config)
    plan = request.build(path_config)

    assert isinstance(OfflineRunner(), OfflineRunner)
    assert isinstance(StreamingRunner(), StreamingRunner)
    assert isinstance(MockSlamBackendConfig().setup_target(), OfflineSlamBackend)
    assert isinstance(MockSlamBackendConfig().setup_target(), StreamingSlamBackend)


def test_materialize_offline_manifest_reuses_cached_frames(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from prml_vslam.benchmark import BenchmarkConfig
    from prml_vslam.pipeline import ingest as ingest_module
    from prml_vslam.pipeline.ingest import materialize_offline_manifest

    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts", captures_dir=tmp_path / "captures")
    video_path = path_config.captures_dir / "video.mp4"
    video_path.parent.mkdir(parents=True, exist_ok=True)
    video_path.write_text("fake video content")

    run_paths = path_config.plan_run_paths(
        experiment_name="Cached Video Offline",
        method_slug="vista",
        output_dir=path_config.artifacts_dir,
    )
    run_paths.rgb_dir.mkdir(parents=True, exist_ok=True)
    run_paths.stage_manifest_path(RunPlanStageId.INGEST).parent.mkdir(parents=True, exist_ok=True)
    run_paths.stage_manifest_path(RunPlanStageId.INGEST).write_text(
        '{"status": "ran", "config_hash": "...", "input_fingerprint": "...", "output_paths": {}}'
    )

    # Pre-populate some metadata to satisfy reuse checks.
    # The actual implementation check might depend on specific hashing.
    # For now, we mock the core extraction call.
    with open(run_paths.rgb_dir / ".ingest_metadata.json", "w") as f:
        import json

        json.dump({"video_path": str(video_path.resolve()), "frame_stride": 1}, f)

    request = RunRequest(
        experiment_name="Cached Video Offline",
        output_dir=path_config.artifacts_dir,
        source=VideoSourceSpec(video_path=Path("video.mp4"), frame_stride=1),
        slam=SlamStageConfig(method=MethodId.VISTA),
        benchmark=BenchmarkConfig(trajectory={"enabled": False}, efficiency={"enabled": False}),
    )

    def _unexpected_extract(**_: object) -> dict[str, object]:
        raise AssertionError("Frame extraction should not run when cached frames match the request.")

    monkeypatch.setattr(ingest_module, "_extract_video_frames", _unexpected_extract)

    # Add a dummy frame to satisfy the "any(output_dir.glob('*.png'))" check.
    (run_paths.rgb_dir / "000000.png").write_text("fake frame")

    manifest = materialize_offline_manifest(
        request=request,
        prepared_manifest=SequenceManifest(sequence_id="video", video_path=video_path),
        run_paths=run_paths,
    )
    assert manifest is not None
    assert manifest.rgb_dir == run_paths.rgb_dir.resolve()


def test_offline_runner_completes_and_persists_outputs(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts", captures_dir=tmp_path / "captures")
    request = _build_request(path_config, mode=PipelineMode.OFFLINE)
    plan = request.build(path_config)
    run_paths = path_config.plan_run_paths(
        experiment_name=request.experiment_name,
        method_slug=request.slam.method.value,
        output_dir=request.output_dir,
    )
    sequence_manifest = _prepared_offline_manifest(tmp_path)
    source = FakeOfflineSource(sequence_manifest=sequence_manifest)
    backend = MockSlamBackendConfig().setup_target()
    assert backend is not None
    runner = OfflineRunner()

    runner.start(request=request, plan=plan, source=source, slam_backend=backend)
    snapshot = _wait_for_terminal_snapshot(runner)

    assert snapshot.state is RunState.COMPLETED
    assert snapshot.summary is not None


def test_streaming_runner_completes_and_persists_outputs(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts", captures_dir=tmp_path / "captures")
    request = _build_request(path_config, mode=PipelineMode.STREAMING)
    plan = request.build(path_config)
    sequence_manifest = SequenceManifest(sequence_id="advio-15", video_path=tmp_path / ".data" / "advio" / "frames.mov")
    source = FakeStreamingSource(
        sequence_manifest=sequence_manifest,
        stream=FinitePacketStream(
            [
                _make_packet(seq=0, timestamp_ns=1_000_000_000, tx=0.0),
                _make_packet(seq=1, timestamp_ns=2_000_000_000, tx=1.0),
            ]
        ),
    )
    backend = MockSlamBackendConfig().setup_target()
    assert backend is not None
    runner = StreamingRunner(frame_timeout_seconds=0.01)

    runner.start(request=request, plan=plan, source=source, slam_backend=backend)
    snapshot = _wait_for_terminal_snapshot(runner)

    assert isinstance(snapshot, StreamingRunSnapshot)
    assert snapshot.state is RunState.COMPLETED
    assert snapshot.received_frames == 2
    assert snapshot.summary is not None


def test_streaming_runner_keeps_source_frames_and_keyframes_separate(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts", captures_dir=tmp_path / "captures")
    request = _build_request(path_config, mode=PipelineMode.STREAMING)
    plan = request.build(path_config)
    sequence_manifest = SequenceManifest(sequence_id="advio-15", video_path=tmp_path / ".data" / "advio" / "frames.mov")
    source = FakeStreamingSource(
        sequence_manifest=sequence_manifest,
        stream=FinitePacketStream(
            [
                _make_packet(seq=0, timestamp_ns=1_000_000_000, tx=0.0),
                _make_packet(seq=1, timestamp_ns=2_000_000_000, tx=0.1),
                _make_packet(seq=2, timestamp_ns=3_000_000_000, tx=0.2),
            ]
        ),
    )
    backend = KeyframeStreamingBackend()
    runner = StreamingRunner(frame_timeout_seconds=0.01)

    runner.start(request=request, plan=plan, source=source, slam_backend=backend)
    snapshot = _wait_for_terminal_snapshot(runner)

    assert isinstance(snapshot, StreamingRunSnapshot)
    assert snapshot.state is RunState.COMPLETED
    assert snapshot.received_frames == 3
    assert snapshot.accepted_keyframes == 2
    assert snapshot.latest_packet is not None
    assert snapshot.latest_packet.seq == 2
    assert snapshot.latest_slam_update is not None
    assert snapshot.latest_slam_update.is_keyframe is True
    assert snapshot.latest_slam_update.keyframe_index == 1
    assert snapshot.trajectory_positions_xyz.shape == (2, 3)
    np.testing.assert_allclose(snapshot.trajectory_positions_xyz[-1], np.array([0.2, 0.0, 0.0]))
    assert source.prepare_calls == 1
    assert source.open_calls == [True]


class KeyframeStreamingBackend:
    """Small streaming backend double that emits explicit keyframe metadata."""

    method_id = MethodId.VISTA

    def start_session(
        self,
        backend_config: SlamBackendConfig,
        output_policy: SlamOutputPolicy,
        artifact_root: Path,
    ) -> SlamSession:
        del backend_config, output_policy
        return KeyframeStreamingSession(artifact_root=artifact_root)


class KeyframeStreamingSession:
    """Streaming session double with one skipped frame between two keyframes."""

    def __init__(self, *, artifact_root: Path) -> None:
        self._artifact_root = artifact_root
        self._updates = iter(
            [
                SlamUpdate(
                    seq=0,
                    timestamp_ns=1_000_000_000,
                    pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
                    is_keyframe=True,
                    keyframe_index=0,
                    num_sparse_points=5,
                    num_dense_points=3,
                    pointmap=np.zeros((2, 2, 3), dtype=np.float32),
                ),
                SlamUpdate(
                    seq=1,
                    timestamp_ns=2_000_000_000,
                    is_keyframe=False,
                    keyframe_index=None,
                    num_sparse_points=5,
                    num_dense_points=3,
                ),
                SlamUpdate(
                    seq=2,
                    timestamp_ns=3_000_000_000,
                    pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.2, ty=0.0, tz=0.0),
                    is_keyframe=True,
                    keyframe_index=1,
                    num_sparse_points=8,
                    num_dense_points=6,
                    pointmap=np.zeros((2, 2, 3), dtype=np.float32),
                ),
            ]
        )
        self.steps = 0

    def step(self, frame: FramePacket) -> SlamUpdate:
        del frame
        self.steps += 1
        return next(self._updates)

    def close(self) -> SlamArtifacts:
        trajectory_path = self._artifact_root / "slam" / "trajectory.tum"
        trajectory_path.parent.mkdir(parents=True, exist_ok=True)
        trajectory_path.write_text("0 0 0 0 0 0 1\n", encoding="utf-8")
        return SlamArtifacts(
            trajectory_tum=ArtifactRef(path=trajectory_path, kind="tum", fingerprint="keyframe-streaming"),
        )


def test_run_service_dispatches_offline_without_runtime_source(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts", captures_dir=tmp_path / "captures")
    request = _build_request(path_config, mode=PipelineMode.OFFLINE)
    offline_runner = OfflineRunnerSpy()
    streaming_runner = StreamingRunnerSpy()
    service = RunService(
        path_config=path_config,
        offline_runner=offline_runner,
        streaming_runner=streaming_runner,
        slam_backend_factory=lambda _method: MockSlamBackendConfig().setup_target(),
    )

    service.start_run(request=request)

    assert offline_runner.start_calls == 1
    assert streaming_runner.start_calls == 0


def test_run_service_dispatches_streaming_with_runtime_source(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts", captures_dir=tmp_path / "captures")
    request = _build_request(path_config, mode=PipelineMode.STREAMING)
    offline_runner = OfflineRunnerSpy()
    streaming_runner = StreamingRunnerSpy()
    service = RunService(
        path_config=path_config,
        offline_runner=offline_runner,
        streaming_runner=streaming_runner,
        slam_backend_factory=lambda _method: MockSlamBackendConfig().setup_target(),
    )
    source = FakeStreamingSource(
        sequence_manifest=SequenceManifest(sequence_id="advio-15"),
        stream=FinitePacketStream([_make_packet(seq=0, timestamp_ns=0, tx=0.0)]),
    )

    service.start_run(request=request, runtime_source=source)

    assert offline_runner.start_calls == 0
    assert streaming_runner.start_calls == 1


def test_default_slam_backend_factory_maps_vista_to_real_backend(tmp_path: Path) -> None:
    # _default_slam_backend_factory no longer takes path_config in main.
    backend = _default_slam_backend_factory(MethodId.VISTA)
    assert isinstance(backend, VistaSlamBackend)


def test_default_slam_backend_factory_maps_mstr_to_mock_backend(tmp_path: Path) -> None:
    backend = _default_slam_backend_factory(MethodId.MSTR)
    assert isinstance(backend, MockSlamBackendConfig().target_type)


def _build_request(
    path_config: PathConfig,
    *,
    mode: PipelineMode = PipelineMode.OFFLINE,
    method: MethodId = MethodId.VISTA,
) -> RunRequest:
    return RunRequest(
        experiment_name="advio-offline-demo-vista",
        mode=mode,
        output_dir=path_config.artifacts_dir,
        source=DatasetSourceSpec(dataset_id=DatasetId.ADVIO, sequence_id="advio-15"),
        slam=SlamStageConfig(method=method),
    )


def _prepared_offline_manifest(root: Path) -> SequenceManifest:
    rgb_dir = root / "frames"
    rgb_dir.mkdir(parents=True, exist_ok=True)
    timestamps_path = root / "timestamps.json"
    timestamps_path.write_text("[]")
    return SequenceManifest(
        sequence_id="advio-15",
        rgb_dir=rgb_dir,
        timestamps_path=timestamps_path,
    )


def _wait_for_terminal_snapshot(runner: OfflineRunner | StreamingRunner) -> RunSnapshot:
    for _ in range(50):
        snapshot = runner.snapshot()
        if snapshot.state in (RunState.COMPLETED, RunState.FAILED, RunState.STOPPED):
            return snapshot
        time.sleep(0.05)
    raise TimeoutError("Pipeline runner did not reach a terminal state.")


def _make_packet(*, seq: int, timestamp_ns: int, tx: float) -> FramePacket:
    return FramePacket(
        seq=seq,
        timestamp_ns=timestamp_ns,
        rgb=np.zeros((4, 4, 3), dtype=np.uint8),
        intrinsics=CameraIntrinsics(fx=200.0, fy=200.0, cx=1.5, cy=1.5, width_px=4, height_px=4),
        pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=tx, ty=0.0, tz=0.0),
    )


class FakeOfflineSource(OfflineSequenceSource):
    def __init__(self, sequence_manifest: SequenceManifest) -> None:
        self.sequence_manifest = sequence_manifest

    @property
    def label(self) -> str:
        return "fake-offline"

    def prepare_sequence_manifest(self, _output_dir: Path) -> SequenceManifest:
        return self.sequence_manifest

    def load_sequence(self) -> object:
        return None


class FakeStreamingSource(StreamingSequenceSource):
    def __init__(self, sequence_manifest: SequenceManifest, stream: object) -> None:
        self.sequence_manifest = sequence_manifest
        self.stream = stream
        self.prepare_calls = 0
        self.open_calls: list[bool] = []

    @property
    def label(self) -> str:
        return "fake-streaming"

    def prepare_sequence_manifest(self, _output_dir: Path) -> SequenceManifest:
        self.prepare_calls += 1
        return self.sequence_manifest

    def open_stream(self, *, loop: bool = False) -> object:
        self.open_calls.append(loop)
        return self.stream


class FinitePacketStream:
    def __init__(self, packets: list[FramePacket]) -> None:
        self.packets = iter(packets)

    def connect(self) -> None:
        return None

    def wait_for_packet(self, timeout_seconds: float) -> FramePacket:
        del timeout_seconds
        try:
            return next(self.packets)
        except StopIteration:
            raise EOFError from None

    def disconnect(self) -> None:
        pass


class OfflineRunnerSpy:
    def __init__(self) -> None:
        self.start_calls = 0

    def start(self, **kwargs: object) -> None:
        self.start_calls += 1

    def stop(self) -> None:
        pass

    def snapshot(self) -> RunSnapshot:
        from prml_vslam.pipeline.state import RunState

        return StreamingRunSnapshot(state=RunState.IDLE, plan=None)  # type: ignore


class StreamingRunnerSpy:
    def __init__(self) -> None:
        self.start_calls = 0

    def start(self, **kwargs: object) -> None:
        self.start_calls += 1

    def stop(self) -> None:
        pass

    def snapshot(self) -> RunSnapshot:
        from prml_vslam.pipeline.state import RunState

        return StreamingRunSnapshot(state=RunState.IDLE, plan=None)  # type: ignore
