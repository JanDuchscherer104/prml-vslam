"""Tests for the refactored pipeline planning and execution surfaces."""

from __future__ import annotations

import json
import time
from pathlib import Path

import cv2
import numpy as np
import pytest
from pydantic import ValidationError

import prml_vslam.pipeline.ingest as ingest_module
from prml_vslam.benchmark import BenchmarkConfig
from prml_vslam.datasets.contracts import DatasetId
from prml_vslam.interfaces import CameraIntrinsics, FramePacket, SE3Pose
from prml_vslam.io.record3d import Record3DTransportId
from prml_vslam.methods import MethodId, MockSlamBackendConfig
from prml_vslam.methods.contracts import SlamBackendConfig, SlamOutputPolicy
from prml_vslam.methods.protocols import OfflineSlamBackend, SlamBackend, SlamSession, StreamingSlamBackend
from prml_vslam.methods.vista.adapter import VistaSlamBackend
from prml_vslam.pipeline import PipelineMode, RunRequest, SequenceManifest
from prml_vslam.pipeline.contracts.plan import RunPlan, RunPlanStage, RunPlanStageId
from prml_vslam.pipeline.contracts.provenance import StageExecutionStatus, StageManifest
from prml_vslam.pipeline.contracts.request import (
    DatasetSourceSpec,
    Record3DLiveSourceSpec,
    SlamStageConfig,
    VideoSourceSpec,
)
from prml_vslam.pipeline.contracts.runtime import RunSnapshot, RunState, StreamingRunSnapshot
from prml_vslam.pipeline.ingest import materialize_offline_manifest
from prml_vslam.pipeline.offline import OfflineRunner
from prml_vslam.pipeline.run_service import RunService, _default_slam_backend_factory
from prml_vslam.pipeline.streaming import StreamingRunner
from prml_vslam.protocols.source import OfflineSequenceSource, StreamingSequenceSource
from prml_vslam.utils import PathConfig
from prml_vslam.utils.geometry import write_tum_trajectory


def test_run_request_builds_expected_stage_sequence_from_direct_config() -> None:
    path_config = PathConfig()
    request = RunRequest(
        experiment_name="Lobby Sweep 01",
        output_dir=Path(".artifacts"),
        source=VideoSourceSpec(video_path=Path("captures/lobby.mp4"), frame_stride=2),
        slam=SlamStageConfig(
            method=MethodId.VISTA,
            outputs=SlamOutputPolicy(emit_dense_points=True, emit_sparse_points=True),
        ),
        benchmark=BenchmarkConfig(
            reference={"enabled": True},
            trajectory={"enabled": True},
            cloud={"enabled": True},
            efficiency={"enabled": True},
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


def test_run_request_build_keeps_default_stage_selection() -> None:
    request = RunRequest(
        experiment_name="Default Check",
        output_dir=Path(".artifacts"),
        source=VideoSourceSpec(video_path=Path("captures/default-check.mp4")),
        slam=SlamStageConfig(method=MethodId.MSTR),
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
        slam=SlamStageConfig(method=MethodId.VISTA),
        benchmark=BenchmarkConfig(trajectory={"enabled": False}, efficiency={"enabled": False}),
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
        slam=SlamStageConfig(
            method=MethodId.MSTR,
            outputs=SlamOutputPolicy(emit_dense_points=False, emit_sparse_points=False),
        ),
        benchmark=BenchmarkConfig(
            reference={"enabled": False},
            trajectory={"enabled": False},
            cloud={"enabled": False},
            efficiency={"enabled": False},
        ),
    )

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
        slam=SlamStageConfig(
            method=MethodId.VISTA,
            outputs=SlamOutputPolicy(emit_dense_points=False),
        ),
        benchmark=BenchmarkConfig(cloud={"enabled": True}),
    )

    with pytest.raises(ValueError, match="slam.outputs.emit_dense_points=True"):
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
        SlamBackendConfig(),
        SlamOutputPolicy(),
        tmp_path / "streaming-artifacts",
    )

    assert isinstance(source, OfflineSequenceSource)
    assert isinstance(source, StreamingSequenceSource)
    assert isinstance(backend, OfflineSlamBackend)
    assert isinstance(backend, StreamingSlamBackend)
    assert isinstance(backend, SlamBackend)
    assert isinstance(session, SlamSession)
    assert backend.method_id is MethodId.MSTR


def test_materialize_offline_manifest_extracts_frames_and_sidecars(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts", captures_dir=tmp_path / "captures")
    run_paths = path_config.plan_run_paths(experiment_name="Video Offline", method_slug="vista")
    video_path = path_config.resolve_video_path("video.mp4")
    video_path.parent.mkdir(parents=True, exist_ok=True)
    _write_demo_video(video_path)
    calibration_path = tmp_path / "iphone-03.yaml"
    calibration_path.write_text("camera: demo\n", encoding="utf-8")
    timestamps_path = tmp_path / "frames.csv"
    timestamps_path.write_text("0.0,0\n0.1,1\n0.2,2\n", encoding="utf-8")
    request = RunRequest(
        experiment_name="Video Offline",
        output_dir=path_config.artifacts_dir,
        source=VideoSourceSpec(video_path=Path("video.mp4"), frame_stride=2),
        slam=SlamStageConfig(method=MethodId.VISTA),
        benchmark=BenchmarkConfig(trajectory={"enabled": False}, efficiency={"enabled": False}),
    )

    manifest = materialize_offline_manifest(
        request=request,
        prepared_manifest=SequenceManifest(
            sequence_id="video",
            video_path=video_path,
            timestamps_path=timestamps_path,
            intrinsics_path=calibration_path,
        ),
        run_paths=run_paths,
    )

    assert manifest.rgb_dir == run_paths.input_frames_dir
    assert sorted(path.name for path in manifest.rgb_dir.glob("*.png")) == ["000000.png", "000001.png"]
    assert manifest.timestamps_path == run_paths.input_timestamps_path
    assert json.loads(manifest.timestamps_path.read_text(encoding="utf-8"))["timestamps_ns"] == [0, 200_000_000]
    assert manifest.intrinsics_path == run_paths.input_intrinsics_path
    assert manifest.intrinsics_path.read_text(encoding="utf-8") == "camera: demo\n"
    assert manifest.rotation_metadata_path == run_paths.input_rotation_metadata_path


def test_materialize_offline_manifest_reuses_cached_frames(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts", captures_dir=tmp_path / "captures")
    run_paths = path_config.plan_run_paths(experiment_name="Cached Video Offline", method_slug="vista")
    video_path = path_config.resolve_video_path("video.mp4")
    video_path.parent.mkdir(parents=True, exist_ok=True)
    _write_demo_video(video_path)

    run_paths.input_frames_dir.mkdir(parents=True, exist_ok=True)
    for frame_index in range(2):
        frame = np.full((4, 4, 3), frame_index * 80, dtype=np.uint8)
        assert cv2.imwrite(str(run_paths.input_frames_dir / f"{frame_index:06d}.png"), frame)
    run_paths.input_timestamps_path.parent.mkdir(parents=True, exist_ok=True)
    run_paths.input_timestamps_path.write_text(
        json.dumps({"timestamps_ns": [0, 100_000_000], "frame_stride": 1}),
        encoding="utf-8",
    )

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

    manifest = materialize_offline_manifest(
        request=request,
        prepared_manifest=SequenceManifest(sequence_id="video", video_path=video_path),
        run_paths=run_paths,
    )

    assert manifest.rgb_dir == run_paths.input_frames_dir
    assert manifest.timestamps_path == run_paths.input_timestamps_path
    assert sorted(path.name for path in manifest.rgb_dir.glob("*.png")) == ["000000.png", "000001.png"]


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
    assert source.prepare_calls == 1
    assert snapshot.sequence_manifest is not None
    assert snapshot.sequence_manifest.rgb_dir == sequence_manifest.rgb_dir
    assert snapshot.slam is not None
    assert snapshot.summary is not None
    assert snapshot.summary.stage_status == {
        RunPlanStageId.INGEST: StageExecutionStatus.RAN,
        RunPlanStageId.SLAM: StageExecutionStatus.RAN,
        RunPlanStageId.SUMMARY: StageExecutionStatus.RAN,
    }
    assert run_paths.summary_path.exists()
    assert snapshot.slam.trajectory_tum.path.exists()


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
    assert source.prepare_calls == 1
    assert source.open_calls == [True]
    assert snapshot.received_frames == 2
    assert snapshot.slam is not None
    assert snapshot.summary is not None


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

    assert len(offline_runner.start_calls) == 1
    assert streaming_runner.start_calls == []


def test_run_service_requires_runtime_source_for_streaming(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts", captures_dir=tmp_path / "captures")
    request = _build_request(path_config, mode=PipelineMode.STREAMING)
    service = RunService(
        path_config=path_config,
        slam_backend_factory=lambda _method: MockSlamBackendConfig().setup_target(),
    )

    with pytest.raises(RuntimeError, match="runtime_source"):
        service.start_run(request=request)


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

    assert offline_runner.start_calls == []
    assert len(streaming_runner.start_calls) == 1


def test_default_slam_backend_factory_maps_vista_to_real_backend(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts", captures_dir=tmp_path / "captures")

    backend = _default_slam_backend_factory(MethodId.VISTA, path_config=path_config)

    assert isinstance(backend, VistaSlamBackend)
    assert backend.method_id is MethodId.VISTA


def test_default_slam_backend_factory_maps_mstr_to_mock_backend(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts", captures_dir=tmp_path / "captures")

    backend = _default_slam_backend_factory(MethodId.MSTR, path_config=path_config)

    assert backend.method_id is MethodId.MSTR


class FakeOfflineSource:
    """Small offline source stand-in for pipeline runner tests."""

    def __init__(self, *, sequence_manifest: SequenceManifest, label: str = "advio-15 · Office 03") -> None:
        self.label = label
        self._sequence_manifest = sequence_manifest
        self.prepare_calls = 0

    def prepare_sequence_manifest(self, output_dir: Path) -> SequenceManifest:
        self.prepare_calls += 1
        del output_dir
        return self._sequence_manifest


class FakeStreamingSource(FakeOfflineSource):
    """Small streaming source stand-in for pipeline runner tests."""

    def __init__(self, *, sequence_manifest: SequenceManifest, stream, label: str = "advio-15 · Office 03") -> None:
        super().__init__(sequence_manifest=sequence_manifest, label=label)
        self._stream = stream
        self.open_calls: list[bool] = []

    def open_stream(self, *, loop: bool):
        self.open_calls.append(loop)
        return self._stream


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


class OfflineRunnerSpy:
    """Small offline-runner double for RunService tests."""

    def __init__(self) -> None:
        self.start_calls: list[dict[str, object]] = []
        self.failed_start_calls: list[dict[str, object]] = []
        self.stop_calls = 0

    def start(self, **kwargs: object) -> None:
        self.start_calls.append(kwargs)

    def stop(self) -> None:
        self.stop_calls += 1

    def snapshot(self) -> RunSnapshot:
        return RunSnapshot()

    def set_failed_start(self, *, plan, error_message: str) -> None:
        self.failed_start_calls.append({"plan": plan, "error_message": error_message})


class StreamingRunnerSpy:
    """Small streaming-runner double for RunService tests."""

    def __init__(self) -> None:
        self.start_calls: list[dict[str, object]] = []
        self.failed_start_calls: list[dict[str, object]] = []
        self.stop_calls = 0

    def start(self, **kwargs: object) -> None:
        self.start_calls.append(kwargs)

    def stop(self) -> None:
        self.stop_calls += 1

    def snapshot(self) -> StreamingRunSnapshot:
        return StreamingRunSnapshot()

    def set_failed_start(self, *, plan, error_message: str) -> None:
        self.failed_start_calls.append({"plan": plan, "error_message": error_message})


def _wait_for_terminal_snapshot(runner, *, timeout_seconds: float = 2.0):
    deadline = time.time() + timeout_seconds
    snapshot = runner.snapshot()
    while snapshot.state in {RunState.PREPARING, RunState.RUNNING} and time.time() < deadline:
        time.sleep(0.01)
        snapshot = runner.snapshot()
    return snapshot


def _make_packet(*, seq: int, timestamp_ns: int, tx: float) -> FramePacket:
    return FramePacket(
        seq=seq,
        timestamp_ns=timestamp_ns,
        rgb=np.zeros((4, 4, 3), dtype=np.uint8),
        intrinsics=CameraIntrinsics(fx=200.0, fy=200.0, cx=1.5, cy=1.5, width_px=4, height_px=4),
        pose=SE3Pose(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=tx, ty=0.0, tz=0.0),
    )


def _build_request(path_config: PathConfig, *, mode: PipelineMode) -> RunRequest:
    return RunRequest(
        experiment_name=f"advio-{mode.value}-demo-vista",
        mode=mode,
        output_dir=path_config.artifacts_dir,
        source=DatasetSourceSpec(dataset_id=DatasetId.ADVIO, sequence_id="advio-15"),
        slam=SlamStageConfig(method=MethodId.VISTA),
        benchmark=BenchmarkConfig(
            reference={"enabled": False},
            trajectory={"enabled": False},
            cloud={"enabled": False},
            efficiency={"enabled": False},
        ),
    )


def _prepared_offline_manifest(tmp_path: Path) -> SequenceManifest:
    rgb_dir = tmp_path / "frames"
    rgb_dir.mkdir(parents=True, exist_ok=True)
    for index in range(2):
        (rgb_dir / f"{index:06d}.png").write_bytes(b"demo")
    timestamps_path = tmp_path / "timestamps.json"
    timestamps_path.write_text(json.dumps({"timestamps_ns": [0, 1_000_000_000]}), encoding="utf-8")
    intrinsics_path = tmp_path / "iphone-03.yaml"
    intrinsics_path.write_text(
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
    reference_path = tmp_path / "reference.tum"
    write_tum_trajectory(
        reference_path,
        [
            SE3Pose(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
            SE3Pose(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=0.5, tz=0.0),
        ],
        [0.0, 1.0],
    )
    return SequenceManifest(
        sequence_id="advio-15",
        rgb_dir=rgb_dir,
        timestamps_path=timestamps_path,
        intrinsics_path=intrinsics_path,
        reference_tum_path=reference_path,
    )


def _write_demo_video(path: Path) -> None:
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, 10.0, (4, 4))
    if not writer.isOpened():
        raise RuntimeError("Failed to create demo video for pipeline ingest test.")
    for index in range(3):
        frame = np.full((4, 4, 3), fill_value=index * 40, dtype=np.uint8)
        writer.write(frame)
    writer.release()
