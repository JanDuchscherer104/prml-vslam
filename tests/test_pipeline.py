"""Tests for the runnable pipeline core."""

from __future__ import annotations

import json
import time
from pathlib import Path
from threading import Event
from typing import TYPE_CHECKING

import numpy as np
import pytest
from pydantic import Field

import prml_vslam.pipeline.streaming_coordinator as streaming_coordinator_module
from prml_vslam.benchmark import BenchmarkConfig, PreparedBenchmarkInputs, ReferenceSource, ReferenceTrajectoryRef
from prml_vslam.datasets import DatasetId
from prml_vslam.interfaces import CameraIntrinsics, FramePacket, FrameTransform
from prml_vslam.methods import MethodId, MockSlamBackendConfig, VistaSlamBackend
from prml_vslam.methods.contracts import SlamBackendConfig, SlamOutputPolicy
from prml_vslam.methods.multiprocess import (
    MultiprocessSlamSession,
)
from prml_vslam.methods.protocols import OfflineSlamBackend, SlamSession, StreamingSlamBackend
from prml_vslam.methods.updates import SlamUpdate
from prml_vslam.methods.vista.config import VistaSlamBackendConfig
from prml_vslam.pipeline import PipelineMode, RunRequest, SequenceManifest
from prml_vslam.pipeline.contracts.artifacts import ArtifactRef, SlamArtifacts
from prml_vslam.pipeline.contracts.execution import StageExecutionKey, StageExecutionMode, StageResult
from prml_vslam.pipeline.contracts.plan import RunPlanStageId
from prml_vslam.pipeline.contracts.provenance import StageExecutionStatus
from prml_vslam.pipeline.contracts.request import (
    DatasetSourceSpec,
    SlamStageConfig,
    VideoSourceSpec,
)
from prml_vslam.pipeline.finalization import build_stage_manifest_from_result
from prml_vslam.pipeline.offline import OfflineRunner
from prml_vslam.pipeline.packet_codec import (
    deserialize_frame_packet,
    serialize_frame_packet,
)
from prml_vslam.pipeline.run_service import RunService, _default_slam_backend_factory
from prml_vslam.pipeline.state import RunSnapshot, RunState, StreamingRunSnapshot
from prml_vslam.pipeline.streaming import StreamingRunner
from prml_vslam.protocols.source import BenchmarkInputSource, OfflineSequenceSource, StreamingSequenceSource
from prml_vslam.utils import BaseConfig, Console, PathConfig

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
    request = _build_request(path_config, method=MethodId.MOCK)

    plan = request.build(path_config)

    assert plan.method is MethodId.MOCK
    assert len(plan.stages) == 3


def test_run_request_build_respects_disabled_optional_stage_toggles(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts", captures_dir=tmp_path / "captures")
    request = _build_request(path_config, method=MethodId.MOCK)
    request.benchmark.trajectory.enabled = False

    plan = request.build(path_config)

    assert RunPlanStageId.BENCHMARK not in [stage.id for stage in plan.stages]


def test_run_request_from_toml_parses_nested_vista_backend_config(tmp_path: Path) -> None:
    config_path = tmp_path / "vista-full.toml"
    config_path.write_text(
        """
experiment_name = "Vista Full"
mode = "streaming"
output_dir = ".artifacts"

[source]
dataset_id = "advio"
sequence_id = "advio-15"

[slam]
method = "vista"

[slam.backend]
max_frames = 12

[slam.backend.slam]
flow_thres = 2.5
max_view_num = 128
""".strip(),
        encoding="utf-8",
    )

    request = RunRequest.from_toml(config_path)

    assert isinstance(request.slam.backend, VistaSlamBackendConfig)
    assert request.slam.backend.max_frames == 12
    assert request.slam.backend.slam.flow_thres == 2.5
    assert request.slam.backend.slam.max_view_num == 128


def test_run_request_parses_vista_specific_backend_overrides_from_toml() -> None:
    request = RunRequest.from_toml(
        """
experiment_name = "vista-config"
mode = "streaming"
output_dir = ".artifacts"

[source]
dataset_id = "advio"
sequence_id = "advio-15"

[slam]
method = "vista"

[slam.backend.slam]
flow_thres = 3.5
max_view_num = 123
"""
    )

    assert isinstance(request.slam.backend, VistaSlamBackendConfig)
    assert request.slam.backend.slam.flow_thres == 3.5
    assert request.slam.backend.slam.max_view_num == 123


def test_run_request_execution_config_defaults_to_local() -> None:
    request = RunRequest.from_toml(
        """
experiment_name = "execution-defaults"
mode = "streaming"
output_dir = ".artifacts"

[source]
dataset_id = "advio"
sequence_id = "advio-15"

[slam]
method = "mock"
"""
    )

    assert request.execution.streaming.ingest is StageExecutionMode.LOCAL
    assert request.execution.streaming.packet_source is StageExecutionMode.LOCAL
    assert request.execution.streaming.slam is StageExecutionMode.LOCAL
    assert request.execution.streaming.trajectory_evaluation is StageExecutionMode.LOCAL
    assert request.execution.streaming.summary is StageExecutionMode.LOCAL


def test_run_request_parses_streaming_execution_modes_from_toml() -> None:
    request = RunRequest.from_toml(
        """
experiment_name = "execution-process"
mode = "streaming"
output_dir = ".artifacts"

[source]
dataset_id = "advio"
sequence_id = "advio-15"

[slam]
method = "mock"

[execution.streaming]
ingest = "process"
packet_source = "process"
slam = "process"
trajectory_evaluation = "process"
summary = "process"
"""
    )

    assert request.execution.streaming.ingest is StageExecutionMode.PROCESS
    assert request.execution.streaming.packet_source is StageExecutionMode.PROCESS
    assert request.execution.streaming.slam is StageExecutionMode.PROCESS
    assert request.execution.streaming.trajectory_evaluation is StageExecutionMode.PROCESS
    assert request.execution.streaming.summary is StageExecutionMode.PROCESS


def test_run_request_rejects_unknown_vista_backend_fields(tmp_path: Path) -> None:
    config_path = tmp_path / "vista-invalid.toml"
    config_path.write_text(
        """
experiment_name = "Vista Invalid"
mode = "streaming"
output_dir = ".artifacts"

[source]
dataset_id = "advio"
sequence_id = "advio-15"

[slam]
method = "vista"

[slam.backend]
max_frames = 12
unsupported = true
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unsupported"):
        RunRequest.from_toml(config_path)


def test_method_id_keeps_mock_and_mast3r_without_mstr_alias() -> None:
    assert MethodId("mock") is MethodId.MOCK
    assert MethodId("mast3r") is MethodId.MAST3R
    assert not hasattr(MethodId, "MSTR")

    with pytest.raises(ValueError, match="mstr"):
        MethodId("mstr")


def test_run_request_from_toml_accepts_mock_method(tmp_path: Path) -> None:
    config_path = tmp_path / "mock.toml"
    config_path.write_text(
        """
experiment_name = "Mock"
mode = "streaming"
output_dir = ".artifacts"

[source]
dataset_id = "advio"
sequence_id = "advio-15"

[slam]
method = "mock"
""".strip(),
        encoding="utf-8",
    )

    request = RunRequest.from_toml(config_path)

    assert request.slam.method is MethodId.MOCK


def test_run_request_from_toml_rejects_mstr_method(tmp_path: Path) -> None:
    config_path = tmp_path / "mstr.toml"
    config_path.write_text(
        """
experiment_name = "MSTR"
mode = "streaming"
output_dir = ".artifacts"

[source]
dataset_id = "advio"
sequence_id = "advio-15"

[slam]
method = "mstr"
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="mstr"):
        RunRequest.from_toml(config_path)


def test_slam_stage_config_normalizes_generic_vista_backend_config() -> None:
    config = SlamStageConfig(method=MethodId.VISTA, backend=SlamBackendConfig(max_frames=7))

    assert isinstance(config.backend, VistaSlamBackendConfig)
    assert config.backend.max_frames == 7


def test_pipeline_protocols_accept_current_structural_implementations(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts", captures_dir=tmp_path / "captures")
    request = _build_request(path_config)
    request.build(path_config)

    assert isinstance(OfflineRunner(), OfflineRunner)
    assert isinstance(StreamingRunner(), StreamingRunner)
    assert isinstance(MockSlamBackendConfig().setup_target(), OfflineSlamBackend)
    assert isinstance(MockSlamBackendConfig().setup_target(), StreamingSlamBackend)


def test_stage_result_converts_to_stage_manifest() -> None:
    result = StageResult(
        stage_id=RunPlanStageId.INGEST,
        execution_key=StageExecutionKey.INGEST,
        status=StageExecutionStatus.RAN,
        config_hash="config",
        input_fingerprint="input",
        output_paths={"sequence_manifest": Path("sequence_manifest.json")},
    )

    manifest = build_stage_manifest_from_result(result)

    assert manifest.stage_id is RunPlanStageId.INGEST
    assert manifest.status is StageExecutionStatus.RAN
    assert manifest.output_paths["sequence_manifest"] == Path("sequence_manifest.json")


def test_materialize_offline_manifest_reuses_cached_frames(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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


def test_materialize_offline_manifest_reuses_cached_timestamps(tmp_path: Path) -> None:
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
    (run_paths.rgb_dir / "000000.png").write_text("fake frame", encoding="utf-8")
    (run_paths.rgb_dir / ".ingest_metadata.json").write_text(
        json.dumps({"video_path": str(video_path.resolve()), "frame_stride": 1}),
        encoding="utf-8",
    )
    run_paths.input_timestamps_path.parent.mkdir(parents=True, exist_ok=True)
    run_paths.input_timestamps_path.write_text(
        json.dumps({"timestamps_ns": [10, 20, 30], "frame_stride": 1}),
        encoding="utf-8",
    )

    request = RunRequest(
        experiment_name="Cached Video Offline",
        output_dir=path_config.artifacts_dir,
        source=VideoSourceSpec(video_path=Path("video.mp4"), frame_stride=1),
        slam=SlamStageConfig(method=MethodId.VISTA),
        benchmark=BenchmarkConfig(trajectory={"enabled": False}, efficiency={"enabled": False}),
    )

    manifest = materialize_offline_manifest(
        request=request,
        prepared_manifest=SequenceManifest(sequence_id="video", video_path=video_path),
        run_paths=run_paths,
    )

    assert manifest.timestamps_path == run_paths.input_timestamps_path.resolve()
    payload = json.loads(run_paths.input_timestamps_path.read_text(encoding="utf-8"))
    assert payload["timestamps_ns"] == [10, 20, 30]


def test_offline_runner_completes_and_persists_outputs(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts", captures_dir=tmp_path / "captures")
    request = _build_request(path_config, mode=PipelineMode.OFFLINE)
    plan = request.build(path_config)
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


def test_streaming_runner_process_packet_source_and_slam_complete(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts", captures_dir=tmp_path / "captures")
    request = _build_request(path_config, mode=PipelineMode.STREAMING)
    request.execution.streaming.packet_source = StageExecutionMode.PROCESS
    request.execution.streaming.slam = StageExecutionMode.PROCESS
    plan = request.build(path_config)
    source = FakeStreamingSourceConfig(
        sequence_manifest=SequenceManifest(sequence_id="advio-15"),
        packets=[
            _make_packet(seq=0, timestamp_ns=1_000_000_000, tx=0.0),
            _make_packet(seq=1, timestamp_ns=2_000_000_000, tx=0.1),
            _make_packet(seq=2, timestamp_ns=3_000_000_000, tx=0.2),
        ],
    ).setup_target()
    assert source is not None
    runner = StreamingRunner(frame_timeout_seconds=0.01)

    runner.start(request=request, plan=plan, source=source, slam_backend=KeyframeStreamingBackend())
    snapshot = _wait_for_terminal_snapshot(runner, timeout_seconds=10.0)

    assert snapshot.state is RunState.COMPLETED
    assert snapshot.received_frames == 3
    assert snapshot.accepted_keyframes == 2
    assert snapshot.summary is not None
    assert snapshot.summary.stage_status[RunPlanStageId.SLAM] is StageExecutionStatus.RAN


def test_streaming_runner_process_finite_stages_complete_trajectory_evaluation(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts", captures_dir=tmp_path / "captures")
    request = _build_request(path_config, mode=PipelineMode.STREAMING)
    request.benchmark.trajectory.enabled = True
    request.execution.streaming.ingest = StageExecutionMode.PROCESS
    request.execution.streaming.trajectory_evaluation = StageExecutionMode.PROCESS
    request.execution.streaming.summary = StageExecutionMode.PROCESS
    plan = request.build(path_config)
    reference_path = tmp_path / "ground_truth.tum"
    reference_path.write_text("0 0 0 0 0 0 0 1\n", encoding="utf-8")
    source = BenchmarkStreamingSource(
        sequence_manifest=SequenceManifest(sequence_id="advio-15"),
        stream=FinitePacketStream([_make_packet(seq=0, timestamp_ns=1_000_000_000, tx=0.0)]),
        benchmark_inputs=PreparedBenchmarkInputs(
            reference_trajectories=[ReferenceTrajectoryRef(path=reference_path, source=ReferenceSource.GROUND_TRUTH)]
        ),
    )
    runner = StreamingRunner(frame_timeout_seconds=0.01)

    runner.start(request=request, plan=plan, source=source, slam_backend=KeyframeStreamingBackend())
    snapshot = _wait_for_terminal_snapshot(runner, timeout_seconds=10.0)

    assert snapshot.state is RunState.COMPLETED
    assert snapshot.summary is not None
    assert snapshot.summary.stage_status[RunPlanStageId.INGEST] is StageExecutionStatus.RAN
    assert snapshot.summary.stage_status[RunPlanStageId.TRAJECTORY_EVALUATION] is StageExecutionStatus.RAN
    assert snapshot.summary.stage_status[RunPlanStageId.SUMMARY] is StageExecutionStatus.RAN


def test_execute_finite_stage_process_timeout_returns_failed_stage_result() -> None:
    result = streaming_coordinator_module.execute_finite_stage(
        stage_id=RunPlanStageId.INGEST,
        mode=StageExecutionMode.PROCESS,
        target=_sleeping_stage_result,
        kwargs={"sleep_seconds": 0.1},
        timeout_seconds=0.01,
        config_hash="config",
        input_fingerprint="input",
    )

    assert result.status is StageExecutionStatus.FAILED
    assert "ingest stage exceeded process timeout" in result.error_message


def test_streaming_runner_process_ingest_timeout_terminalizes_with_failed_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts", captures_dir=tmp_path / "captures")
    request = _build_request(path_config, mode=PipelineMode.STREAMING)
    request.execution.streaming.ingest = StageExecutionMode.PROCESS
    plan = request.build(path_config)
    source = FakeStreamingSourceConfig(
        sequence_manifest=SequenceManifest(sequence_id="advio-15"),
        prepare_delay_seconds=0.1,
        fail_on_open=True,
    ).setup_target()
    assert source is not None
    monkeypatch.setattr(
        streaming_coordinator_module,
        "_stage_process_timeout_seconds",
        lambda stage_id: 0.01 if stage_id is RunPlanStageId.INGEST else 5.0,
    )
    runner = StreamingRunner(frame_timeout_seconds=0.01)

    runner.start(request=request, plan=plan, source=source, slam_backend=KeyframeStreamingBackend())
    snapshot = _wait_for_terminal_snapshot(runner, timeout_seconds=5.0)

    assert snapshot.state is RunState.FAILED
    assert "ingest stage exceeded process timeout" in snapshot.error_message


def test_streaming_runner_stop_preserves_last_preview_snapshot(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts", captures_dir=tmp_path / "captures")
    request = _build_request(path_config, mode=PipelineMode.STREAMING)
    plan = request.build(path_config)
    source = FakeStreamingSource(
        sequence_manifest=SequenceManifest(sequence_id="advio-15"),
        stream=LoopingPacketStream(_make_packet(seq=0, timestamp_ns=1_000_000_000, tx=0.0)),
    )
    runner = StreamingRunner(frame_timeout_seconds=0.01)

    runner.start(request=request, plan=plan, source=source, slam_backend=StickyPreviewBackend())
    _wait_for(lambda: runner.snapshot().latest_preview_update is not None)

    runner.stop()
    snapshot = runner.snapshot()

    assert snapshot.state is RunState.STOPPED
    assert snapshot.latest_packet is not None
    assert snapshot.latest_preview_update is not None
    assert snapshot.latest_preview_update.preview_rgb is not None


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
    assert snapshot.latest_preview_update is not None
    assert snapshot.latest_preview_update.keyframe_index == 1
    assert snapshot.trajectory_positions_xyz.shape == (2, 3)
    np.testing.assert_allclose(snapshot.trajectory_positions_xyz[-1], np.array([0.2, 0.0, 0.0]))
    assert source.prepare_calls == 1
    assert source.open_calls == [True]


def test_streaming_runner_prepares_benchmark_inputs_for_streaming_sources(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts", captures_dir=tmp_path / "captures")
    request = _build_request(path_config, mode=PipelineMode.STREAMING)
    request.benchmark.trajectory.enabled = True
    plan = request.build(path_config)
    reference_path = tmp_path / "ground_truth.tum"
    reference_path.write_text("0 0 0 0 0 0 0 1\n", encoding="utf-8")
    source = BenchmarkStreamingSource(
        sequence_manifest=SequenceManifest(sequence_id="advio-15"),
        stream=FinitePacketStream([_make_packet(seq=0, timestamp_ns=1_000_000_000, tx=0.0)]),
        benchmark_inputs=PreparedBenchmarkInputs(
            reference_trajectories=[ReferenceTrajectoryRef(path=reference_path, source=ReferenceSource.GROUND_TRUTH)]
        ),
    )
    runner = StreamingRunner(frame_timeout_seconds=0.01)

    runner.start(request=request, plan=plan, source=source, slam_backend=KeyframeStreamingBackend())
    snapshot = _wait_for_terminal_snapshot(runner)
    run_paths = PathConfig(
        root=tmp_path, artifacts_dir=tmp_path / ".artifacts", captures_dir=tmp_path / "captures"
    ).plan_run_paths(
        experiment_name=request.experiment_name,
        method_slug=request.slam.method.value,
        output_dir=request.output_dir,
    )

    assert snapshot.benchmark_inputs is not None
    assert run_paths.benchmark_inputs_path.exists()
    assert run_paths.trajectory_metrics_path.exists()
    assert snapshot.summary is not None
    assert snapshot.summary.stage_status[RunPlanStageId.TRAJECTORY_EVALUATION].value == "ran"


def test_streaming_runner_terminalizes_when_trajectory_evaluation_inputs_are_missing(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts", captures_dir=tmp_path / "captures")
    request = _build_request(path_config, mode=PipelineMode.STREAMING)
    request.benchmark.trajectory.enabled = True
    plan = request.build(path_config)
    source = FakeStreamingSource(
        sequence_manifest=SequenceManifest(sequence_id="advio-15"),
        stream=FinitePacketStream([_make_packet(seq=0, timestamp_ns=1_000_000_000, tx=0.0)]),
    )
    runner = StreamingRunner(frame_timeout_seconds=0.01)

    runner.start(request=request, plan=plan, source=source, slam_backend=KeyframeStreamingBackend())
    snapshot = _wait_for_terminal_snapshot(runner)
    run_paths = path_config.plan_run_paths(
        experiment_name=request.experiment_name,
        method_slug=request.slam.method.value,
        output_dir=request.output_dir,
    )

    assert snapshot.state is RunState.FAILED
    assert "Trajectory evaluation requires" in snapshot.error_message
    assert snapshot.summary is not None
    assert snapshot.summary.stage_status[RunPlanStageId.SLAM].value == "ran"
    assert snapshot.summary.stage_status[RunPlanStageId.TRAJECTORY_EVALUATION].value == "failed"
    assert run_paths.summary_path.exists()
    assert run_paths.stage_manifests_path.exists()


def test_multiprocess_frame_packet_serialization_round_trips_contract(tmp_path: Path) -> None:
    packet = FramePacket(
        seq=7,
        timestamp_ns=123_000,
        arrival_timestamp_s=4.5,
        rgb=np.full((2, 3, 3), fill_value=17, dtype=np.uint8),
        depth=np.full((2, 3), fill_value=2.5, dtype=np.float32),
        confidence=np.ones((2, 3), dtype=np.float32),
        intrinsics=CameraIntrinsics(fx=200.0, fy=201.0, cx=1.0, cy=1.5, width_px=3, height_px=2),
        pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=2.0, tz=3.0),
        metadata={"method": MethodId.VISTA, "source_path": tmp_path, "nested": ("frame", 7)},
    )

    restored = deserialize_frame_packet(serialize_frame_packet(packet))

    assert isinstance(restored, FramePacket)
    assert restored.seq == packet.seq
    assert restored.timestamp_ns == packet.timestamp_ns
    assert restored.arrival_timestamp_s == packet.arrival_timestamp_s
    assert restored.intrinsics == packet.intrinsics
    assert restored.pose == packet.pose
    np.testing.assert_array_equal(restored.rgb, packet.rgb)
    np.testing.assert_array_equal(restored.depth, packet.depth)
    np.testing.assert_array_equal(restored.confidence, packet.confidence)
    assert restored.metadata == {
        "method": MethodId.VISTA.value,
        "source_path": str(tmp_path),
        "nested": ["frame", 7],
    }


def test_streaming_runner_applies_update_emitted_during_session_close(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts", captures_dir=tmp_path / "captures")
    request = _build_request(path_config, mode=PipelineMode.STREAMING)
    plan = request.build(path_config)
    source = FakeStreamingSource(
        sequence_manifest=SequenceManifest(sequence_id="advio-15"),
        stream=FinitePacketStream([_make_packet(seq=0, timestamp_ns=1_000_000_000, tx=0.0)]),
    )
    runner = StreamingRunner(frame_timeout_seconds=0.01)

    runner.start(request=request, plan=plan, source=source, slam_backend=CloseUpdateStreamingBackend())
    snapshot = _wait_for_terminal_snapshot(runner)

    assert isinstance(snapshot, StreamingRunSnapshot)
    assert snapshot.state is RunState.COMPLETED
    assert snapshot.accepted_keyframes == 1
    assert snapshot.latest_slam_update is not None
    assert snapshot.latest_slam_update.keyframe_index == 0
    assert snapshot.latest_preview_update is not None
    np.testing.assert_allclose(snapshot.trajectory_positions_xyz[-1], np.array([0.4, 0.0, 0.0]))


def test_streaming_runner_retains_last_renderable_preview_update(tmp_path: Path) -> None:
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
            ]
        ),
    )
    backend = PreviewRetentionStreamingBackend()
    runner = StreamingRunner(frame_timeout_seconds=0.01)

    runner.start(request=request, plan=plan, source=source, slam_backend=backend)
    snapshot = _wait_for_terminal_snapshot(runner)

    assert isinstance(snapshot, StreamingRunSnapshot)
    assert snapshot.state is RunState.COMPLETED
    assert snapshot.latest_slam_update is not None
    assert snapshot.latest_slam_update.is_keyframe is False
    assert snapshot.latest_preview_update is not None
    assert snapshot.latest_preview_update.is_keyframe is True
    assert snapshot.latest_preview_update.keyframe_index == 0
    assert snapshot.latest_preview_update.preview_rgb is not None


def test_streaming_runner_stop_preserves_last_preview_and_trajectory_via_run_service(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts", captures_dir=tmp_path / "captures")
    request = _build_request(path_config, mode=PipelineMode.STREAMING)
    service = RunService(
        path_config=path_config,
        slam_backend_factory=lambda _method: PreviewRetentionStreamingBackend(),
    )
    source = FakeStreamingSource(
        sequence_manifest=SequenceManifest(sequence_id="advio-15"),
        stream=BlockingPacketStream(first_packet=_make_packet(seq=0, timestamp_ns=1_000_000_000, tx=0.0)),
    )

    service.start_run(request=request, runtime_source=source)
    _wait_for(
        lambda: isinstance(service.snapshot(), StreamingRunSnapshot) and service.snapshot().received_frames >= 1,
        timeout_seconds=5.0,
    )
    service.stop_run()
    snapshot = service.snapshot()

    assert isinstance(snapshot, StreamingRunSnapshot)
    assert snapshot.state is RunState.STOPPED
    assert snapshot.latest_preview_update is not None
    assert snapshot.latest_preview_update.preview_rgb is not None
    assert snapshot.trajectory_positions_xyz.shape[0] == 1


def test_streaming_runner_attributes_delayed_updates_by_update_timestamp(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts", captures_dir=tmp_path / "captures")
    request = _build_request(path_config, mode=PipelineMode.STREAMING)
    plan = request.build(path_config)
    source = FakeStreamingSource(
        sequence_manifest=SequenceManifest(sequence_id="advio-15"),
        stream=FinitePacketStream(
            [
                _make_packet(seq=0, timestamp_ns=1_000_000_000, tx=0.0),
                _make_packet(seq=1, timestamp_ns=2_000_000_000, tx=0.1),
            ]
        ),
    )
    runner = StreamingRunner(frame_timeout_seconds=0.01)

    runner.start(
        request=request,
        plan=plan,
        source=source,
        slam_backend=DelayedUpdateStreamingBackend(),
    )
    snapshot = _wait_for_terminal_snapshot(runner)

    assert isinstance(snapshot, StreamingRunSnapshot)
    assert snapshot.state is RunState.COMPLETED
    assert snapshot.accepted_keyframes == 1
    np.testing.assert_allclose(snapshot.trajectory_timestamps_s, np.array([0.0]))


def test_streaming_runner_failed_start_surfaces_startup_error_without_unboundlocal(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts", captures_dir=tmp_path / "captures")
    request = _build_request(path_config, mode=PipelineMode.STREAMING)
    plan = request.build(path_config)
    source = FakeStreamingSource(
        sequence_manifest=SequenceManifest(sequence_id="advio-15"),
        stream=FinitePacketStream([_make_packet(seq=0, timestamp_ns=1_000_000_000, tx=0.0)]),
    )
    runner = StreamingRunner(frame_timeout_seconds=0.01)

    runner.start(
        request=request,
        plan=plan,
        source=source,
        slam_backend=StartFailureStreamingBackend(),
    )
    snapshot = _wait_for_terminal_snapshot(runner)

    assert isinstance(snapshot, StreamingRunSnapshot)
    assert snapshot.state is RunState.FAILED
    assert "start session failed" in snapshot.error_message


def test_streaming_runner_finalize_runs_registered_cleanup_on_completion_and_failure(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts", captures_dir=tmp_path / "captures")
    request = _build_request(path_config, mode=PipelineMode.STREAMING)
    plan = request.build(path_config)

    completion_stream = DisconnectSpyPacketStream(packets=[_make_packet(seq=0, timestamp_ns=1_000_000_000, tx=0.0)])
    completion_runner = StreamingRunner(frame_timeout_seconds=0.01)
    completion_runner.start(
        request=request,
        plan=plan,
        source=FakeStreamingSource(
            sequence_manifest=SequenceManifest(sequence_id="advio-15"), stream=completion_stream
        ),
        slam_backend=PreviewRetentionStreamingBackend(),
    )
    completion_snapshot = _wait_for_terminal_snapshot(completion_runner)

    failure_stream = DisconnectSpyPacketStream(packets=[_make_packet(seq=0, timestamp_ns=1_000_000_000, tx=0.0)])
    failure_runner = StreamingRunner(frame_timeout_seconds=0.01)
    failure_runner.start(
        request=request,
        plan=plan,
        source=FakeStreamingSource(sequence_manifest=SequenceManifest(sequence_id="advio-15"), stream=failure_stream),
        slam_backend=FailingStepStreamingBackend(),
    )
    failure_snapshot = _wait_for_terminal_snapshot(failure_runner)

    assert completion_snapshot.state is RunState.COMPLETED
    assert failure_snapshot.state is RunState.FAILED
    assert completion_stream.disconnect_calls >= 1
    assert failure_stream.disconnect_calls >= 1


def test_streaming_runner_preserves_native_rerun_without_repo_export(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts", captures_dir=tmp_path / "captures")
    request = _build_request(path_config, mode=PipelineMode.STREAMING)
    request.visualization.preserve_native_rerun = True
    request.visualization.export_viewer_rrd = False
    plan = request.build(path_config)
    source = FakeStreamingSource(
        sequence_manifest=SequenceManifest(sequence_id="advio-15"),
        stream=FinitePacketStream([_make_packet(seq=0, timestamp_ns=1_000_000_000, tx=0.0)]),
    )
    runner = StreamingRunner(frame_timeout_seconds=0.01)

    runner.start(request=request, plan=plan, source=source, slam_backend=NativeRerunStreamingBackend())
    snapshot = _wait_for_terminal_snapshot(runner)

    assert snapshot.visualization is not None
    assert snapshot.visualization.native_rerun_rrd is not None
    assert snapshot.visualization.native_rerun_rrd.path.exists()


def test_streaming_runner_fails_when_multiprocess_worker_raises(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts", captures_dir=tmp_path / "captures")
    request = _build_request(path_config, mode=PipelineMode.STREAMING)
    plan = request.build(path_config)
    source = FakeStreamingSource(
        sequence_manifest=SequenceManifest(sequence_id="advio-15"),
        stream=FinitePacketStream([_make_packet(seq=0, timestamp_ns=1_000_000_000, tx=0.0)]),
    )
    runner = StreamingRunner(frame_timeout_seconds=0.01)

    runner.start(request=request, plan=plan, source=source, slam_backend=FailingWorkerBackend())
    snapshot = _wait_for_terminal_snapshot(runner, timeout_seconds=10.0)

    assert snapshot.state is RunState.FAILED
    assert "synthetic worker failure" in snapshot.error_message


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
                    preview_rgb=np.zeros((2, 2, 3), dtype=np.uint8),
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
                    preview_rgb=np.ones((2, 2, 3), dtype=np.uint8),
                    pointmap=np.zeros((2, 2, 3), dtype=np.float32),
                ),
            ]
        )
        self.steps = 0
        self._pending: list[SlamUpdate] = []

    def step(self, frame: FramePacket) -> None:
        del frame
        self.steps += 1
        self._pending.append(next(self._updates))

    def try_get_updates(self) -> list[SlamUpdate]:
        updates = self._pending
        self._pending = []
        return updates

    def close(self) -> SlamArtifacts:
        trajectory_path = self._artifact_root / "slam" / "trajectory.tum"
        trajectory_path.parent.mkdir(parents=True, exist_ok=True)
        trajectory_path.write_text("0 0 0 0 0 0 0 1\n", encoding="utf-8")
        return SlamArtifacts(
            trajectory_tum=ArtifactRef(path=trajectory_path, kind="tum", fingerprint="keyframe-streaming"),
        )


class PreviewRetentionStreamingBackend:
    """Streaming backend double that stops emitting preview payloads after the first keyframe."""

    method_id = MethodId.VISTA

    def start_session(
        self,
        backend_config: SlamBackendConfig,
        output_policy: SlamOutputPolicy,
        artifact_root: Path,
    ) -> SlamSession:
        del backend_config, output_policy
        return PreviewRetentionStreamingSession(artifact_root=artifact_root)


class PreviewRetentionStreamingSession:
    """Streaming session double that keeps a prior preview valid across non-keyframe updates."""

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
                    preview_rgb=np.full((2, 2, 3), fill_value=9, dtype=np.uint8),
                    pointmap=np.zeros((2, 2, 3), dtype=np.float32),
                ),
                SlamUpdate(
                    seq=1,
                    timestamp_ns=2_000_000_000,
                    is_keyframe=False,
                    keyframe_index=None,
                ),
            ]
        )
        self._pending: list[SlamUpdate] = []

    def step(self, frame: FramePacket) -> None:
        del frame
        self._pending.append(next(self._updates))

    def try_get_updates(self) -> list[SlamUpdate]:
        updates = self._pending
        self._pending = []
        return updates

    def close(self) -> SlamArtifacts:
        trajectory_path = self._artifact_root / "slam" / "trajectory.tum"
        trajectory_path.parent.mkdir(parents=True, exist_ok=True)
        trajectory_path.write_text("0 0 0 0 0 0 0 1\n", encoding="utf-8")
        return SlamArtifacts(
            trajectory_tum=ArtifactRef(path=trajectory_path, kind="tum", fingerprint="preview-retention-streaming"),
        )


class DelayedUpdateStreamingBackend:
    method_id = MethodId.VISTA

    def start_session(
        self,
        backend_config: SlamBackendConfig,
        output_policy: SlamOutputPolicy,
        artifact_root: Path,
    ) -> SlamSession:
        del backend_config, output_policy
        return DelayedUpdateStreamingSession(artifact_root=artifact_root)


class DelayedUpdateStreamingSession:
    def __init__(self, *, artifact_root: Path) -> None:
        self._artifact_root = artifact_root
        self._pending: list[SlamUpdate] = []
        self._frames: list[FramePacket] = []

    def step(self, frame: FramePacket) -> None:
        self._frames.append(frame)
        if len(self._frames) == 2:
            self._pending.append(
                SlamUpdate(
                    seq=self._frames[0].seq,
                    timestamp_ns=self._frames[0].timestamp_ns,
                    pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
                    is_keyframe=True,
                    keyframe_index=0,
                )
            )

    def try_get_updates(self) -> list[SlamUpdate]:
        updates = self._pending
        self._pending = []
        return updates

    def close(self) -> SlamArtifacts:
        trajectory_path = self._artifact_root / "slam" / "trajectory.tum"
        trajectory_path.parent.mkdir(parents=True, exist_ok=True)
        trajectory_path.write_text("0 0 0 0 0 0 0 1\n", encoding="utf-8")
        return SlamArtifacts(trajectory_tum=ArtifactRef(path=trajectory_path, kind="tum", fingerprint="delayed"))


class StartFailureStreamingBackend:
    method_id = MethodId.VISTA

    def start_session(
        self,
        backend_config: SlamBackendConfig,
        output_policy: SlamOutputPolicy,
        artifact_root: Path,
    ) -> SlamSession:
        del backend_config, output_policy, artifact_root
        raise RuntimeError("start session failed")


class FailingStepStreamingBackend:
    method_id = MethodId.VISTA

    def start_session(
        self,
        backend_config: SlamBackendConfig,
        output_policy: SlamOutputPolicy,
        artifact_root: Path,
    ) -> SlamSession:
        del backend_config, output_policy
        return FailingStepStreamingSession(artifact_root=artifact_root)


class FailingStepStreamingSession:
    def __init__(self, *, artifact_root: Path) -> None:
        self._artifact_root = artifact_root

    def step(self, frame: FramePacket) -> None:
        del frame
        raise RuntimeError("frame step failed")

    def try_get_updates(self) -> list[SlamUpdate]:
        return []

    def close(self) -> SlamArtifacts:
        trajectory_path = self._artifact_root / "slam" / "trajectory.tum"
        trajectory_path.parent.mkdir(parents=True, exist_ok=True)
        trajectory_path.write_text("0 0 0 0 0 0 0 1\n", encoding="utf-8")
        return SlamArtifacts(trajectory_tum=ArtifactRef(path=trajectory_path, kind="tum", fingerprint="failing-step"))


class StickyPreviewBackend:
    method_id = MethodId.VISTA

    def start_session(
        self,
        backend_config: SlamBackendConfig,
        output_policy: SlamOutputPolicy,
        artifact_root: Path,
    ) -> SlamSession:
        del backend_config, output_policy
        return StickyPreviewSession(artifact_root=artifact_root)


class StickyPreviewSession:
    def __init__(self, *, artifact_root: Path) -> None:
        self._artifact_root = artifact_root
        self._emitted_preview = False
        self._pending: list[SlamUpdate] = []

    def step(self, frame: FramePacket) -> None:
        if self._emitted_preview:
            return
        self._pending.append(
            SlamUpdate(
                seq=frame.seq,
                timestamp_ns=frame.timestamp_ns,
                source_seq=frame.seq,
                source_timestamp_ns=frame.timestamp_ns,
                is_keyframe=True,
                keyframe_index=0,
                pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
                preview_rgb=np.ones((2, 2, 3), dtype=np.uint8),
            )
        )
        self._emitted_preview = True

    def try_get_updates(self) -> list[SlamUpdate]:
        updates = self._pending
        self._pending = []
        return updates

    def close(self) -> SlamArtifacts:
        trajectory_path = self._artifact_root / "slam" / "trajectory.tum"
        trajectory_path.parent.mkdir(parents=True, exist_ok=True)
        trajectory_path.write_text("0 0 0 0 0 0 0 1\n", encoding="utf-8")
        return SlamArtifacts(
            trajectory_tum=ArtifactRef(path=trajectory_path, kind="tum", fingerprint="sticky-preview-streaming"),
        )


class BenchmarkStreamingSource(StreamingSequenceSource, BenchmarkInputSource):
    def __init__(
        self,
        *,
        sequence_manifest: SequenceManifest,
        stream: object,
        benchmark_inputs: PreparedBenchmarkInputs,
    ) -> None:
        self.sequence_manifest = sequence_manifest
        self.stream = stream
        self.prepare_calls = 0
        self.open_calls: list[bool] = []
        self._benchmark_inputs = benchmark_inputs

    @property
    def label(self) -> str:
        return "benchmark-streaming"

    def prepare_sequence_manifest(self, _output_dir: Path) -> SequenceManifest:
        self.prepare_calls += 1
        return self.sequence_manifest

    def open_stream(self, *, loop: bool = False) -> object:
        self.open_calls.append(loop)
        return self.stream

    def prepare_benchmark_inputs(self, _output_dir: Path) -> PreparedBenchmarkInputs:
        return self._benchmark_inputs


class NativeRerunStreamingBackend:
    method_id = MethodId.VISTA

    def start_session(
        self,
        backend_config: SlamBackendConfig,
        output_policy: SlamOutputPolicy,
        artifact_root: Path,
    ) -> SlamSession:
        del backend_config, output_policy
        return NativeRerunStreamingSession(artifact_root=artifact_root)


class NativeRerunStreamingSession:
    def __init__(self, *, artifact_root: Path) -> None:
        self._artifact_root = artifact_root

    def step(self, frame: FramePacket) -> None:
        del frame

    def try_get_updates(self) -> list[SlamUpdate]:
        return []

    def close(self) -> SlamArtifacts:
        native_dir = self._artifact_root / "native"
        native_dir.mkdir(parents=True, exist_ok=True)
        (native_dir / "rerun_recording.rrd").write_bytes(b"native-rerun")
        trajectory_path = self._artifact_root / "slam" / "trajectory.tum"
        trajectory_path.parent.mkdir(parents=True, exist_ok=True)
        trajectory_path.write_text("0 0 0 0 0 0 0 1\n", encoding="utf-8")
        return SlamArtifacts(
            trajectory_tum=ArtifactRef(path=trajectory_path, kind="tum", fingerprint="native-rerun-streaming"),
        )


class CloseUpdateStreamingBackend:
    method_id = MethodId.VISTA

    def start_session(
        self,
        backend_config: SlamBackendConfig,
        output_policy: SlamOutputPolicy,
        artifact_root: Path,
    ) -> SlamSession:
        del backend_config, output_policy
        return CloseUpdateStreamingSession(artifact_root=artifact_root)


class CloseUpdateStreamingSession:
    def __init__(self, *, artifact_root: Path) -> None:
        self._artifact_root = artifact_root
        self._pending: list[SlamUpdate] = []
        self._last_frame: FramePacket | None = None

    def step(self, frame: FramePacket) -> None:
        self._last_frame = frame

    def try_get_updates(self) -> list[SlamUpdate]:
        updates = self._pending
        self._pending = []
        return updates

    def close(self) -> SlamArtifacts:
        if self._last_frame is not None:
            self._pending.append(
                SlamUpdate(
                    seq=self._last_frame.seq,
                    timestamp_ns=self._last_frame.timestamp_ns,
                    source_seq=self._last_frame.seq,
                    source_timestamp_ns=self._last_frame.timestamp_ns,
                    is_keyframe=True,
                    keyframe_index=0,
                    pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.4, ty=0.0, tz=0.0),
                    preview_rgb=np.ones((2, 2, 3), dtype=np.uint8),
                )
            )
        trajectory_path = self._artifact_root / "slam" / "trajectory.tum"
        trajectory_path.parent.mkdir(parents=True, exist_ok=True)
        trajectory_path.write_text("0 0 0 0 0 0 0 1\n", encoding="utf-8")
        return SlamArtifacts(
            trajectory_tum=ArtifactRef(path=trajectory_path, kind="tum", fingerprint="close-update-streaming"),
        )


class FailingWorkerBackend:
    method_id = MethodId.VISTA

    def start_session(
        self,
        backend_config: SlamBackendConfig,
        output_policy: SlamOutputPolicy,
        artifact_root: Path,
    ) -> SlamSession:
        del backend_config, output_policy, artifact_root
        return MultiprocessSlamSession(session_factory=FailingWorkerSessionFactory(), console=Console(__name__))


class FailingWorkerSessionFactory:
    def __call__(self) -> SlamSession:
        return FailingWorkerSession()


class FailingWorkerSession:
    def step(self, frame: FramePacket) -> None:
        del frame
        raise RuntimeError("synthetic worker failure")

    def try_get_updates(self) -> list[SlamUpdate]:
        return []

    def close(self) -> SlamArtifacts:
        raise RuntimeError("close should not be called after a worker failure")


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


def test_run_service_rejects_non_executable_optional_stages(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts", captures_dir=tmp_path / "captures")
    request = _build_request(path_config, mode=PipelineMode.OFFLINE)
    request.benchmark.reference.enabled = True
    service = RunService(
        path_config=path_config,
        slam_backend_factory=lambda _method: MockSlamBackendConfig().setup_target(),
    )

    with pytest.raises(RuntimeError, match="Unsupported stages"):
        service.start_run(request=request)

    assert service.snapshot().state is RunState.FAILED


def test_default_slam_backend_factory_maps_vista_to_real_backend(tmp_path: Path) -> None:
    # _default_slam_backend_factory no longer takes path_config in main.
    backend = _default_slam_backend_factory(MethodId.VISTA)
    assert isinstance(backend, VistaSlamBackend)


def test_default_slam_backend_factory_maps_mock_to_mock_backend(tmp_path: Path) -> None:
    backend = _default_slam_backend_factory(MethodId.MOCK)
    assert isinstance(backend, MockSlamBackendConfig().target_type)


def test_default_slam_backend_factory_rejects_mast3r_until_backend_exists(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="mast3r.*support execution"):
        _default_slam_backend_factory(MethodId.MAST3R)


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


def _wait_for(predicate, *, timeout_seconds: float = 1.0) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if predicate():
            return
        time.sleep(0.02)
    raise AssertionError("Timed out waiting for the expected runtime state.")


def _wait_for_terminal_snapshot(
    runner: OfflineRunner | StreamingRunner, *, timeout_seconds: float = 2.5
) -> RunSnapshot:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        snapshot = runner.snapshot()
        if snapshot.state in (RunState.COMPLETED, RunState.FAILED, RunState.STOPPED):
            return snapshot
        time.sleep(0.05)
    raise TimeoutError("Pipeline runner did not reach a terminal state.")


def _sleeping_stage_result(sleep_seconds: float) -> StageResult:
    time.sleep(sleep_seconds)
    return StageResult(
        stage_id=RunPlanStageId.INGEST,
        execution_key=StageExecutionKey.INGEST,
        status=StageExecutionStatus.RAN,
        config_hash="config",
        input_fingerprint="input",
    )


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


class FakeStreamingSourceConfig(BaseConfig):
    sequence_manifest: SequenceManifest
    packets: list[FramePacket] = Field(default_factory=list)
    prepare_delay_seconds: float = 0.0
    fail_on_open: bool = False

    @property
    def target_type(self) -> type[ConfigBackedFakeStreamingSource]:
        return ConfigBackedFakeStreamingSource


class ConfigBackedFakeStreamingSource(FakeStreamingSource):
    def __init__(self, config: FakeStreamingSourceConfig) -> None:
        self.config = config
        self._prepare_delay_seconds = config.prepare_delay_seconds
        self._fail_on_open = config.fail_on_open
        super().__init__(
            sequence_manifest=config.sequence_manifest,
            stream=FinitePacketStream(list(config.packets)),
        )

    def prepare_sequence_manifest(self, _output_dir: Path) -> SequenceManifest:
        time.sleep(self._prepare_delay_seconds)
        return self.sequence_manifest

    def open_stream(self, *, loop: bool = False) -> object:
        if self._fail_on_open:
            del loop
            raise AssertionError("stream should not open when ingest times out")
        return super().open_stream(loop=loop)


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


class DisconnectSpyPacketStream(FinitePacketStream):
    def __init__(self, packets: list[FramePacket]) -> None:
        super().__init__(packets)
        self.disconnect_calls = 0

    def disconnect(self) -> None:
        self.disconnect_calls += 1


class BlockingPacketStream:
    def __init__(self, *, first_packet: FramePacket) -> None:
        self._first_packet = first_packet
        self._served = False
        self._unblock = Event()

    def connect(self) -> None:
        return None

    def wait_for_packet(self, timeout_seconds: float) -> FramePacket:
        if not self._served:
            self._served = True
            return self._first_packet
        if not self._unblock.wait(timeout_seconds):
            raise TimeoutError("waiting for stop")
        raise EOFError

    def disconnect(self) -> None:
        self._unblock.set()


class LoopingPacketStream:
    def __init__(self, packet: FramePacket) -> None:
        self.packet = packet
        self.disconnected = False

    def connect(self) -> None:
        return None

    def wait_for_packet(self, timeout_seconds: float) -> FramePacket:
        del timeout_seconds
        if self.disconnected:
            raise EOFError
        time.sleep(0.01)
        return self.packet

    def disconnect(self) -> None:
        self.disconnected = True


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
