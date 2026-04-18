"""Focused tests for the Ray-backed pipeline core."""

from __future__ import annotations

import os
import sys
import time
import uuid
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import ray
from pydantic import ValidationError

from prml_vslam.benchmark import (
    BenchmarkConfig,
    CloudBenchmarkConfig,
    EfficiencyBenchmarkConfig,
    TrajectoryBenchmarkConfig,
)
from prml_vslam.interfaces import FramePacketProvenance, FrameTransform
from prml_vslam.methods.descriptors import BackendCapabilities, BackendDescriptor
from prml_vslam.methods.events import KeyframeVisualizationReady, translate_slam_update
from prml_vslam.methods.factory import BackendFactory
from prml_vslam.methods.updates import SlamUpdate
from prml_vslam.pipeline import PipelineMode, RunRequest
from prml_vslam.pipeline.backend_ray import RayPipelineBackend
from prml_vslam.pipeline.contracts.events import (
    FramePacketSummary,
    PacketObserved,
    RunStopped,
    StageFailed,
    StageOutcome,
    StageStatus,
)
from prml_vslam.pipeline.contracts.handles import ArrayHandle, PreviewHandle
from prml_vslam.pipeline.contracts.request import DatasetSourceSpec, SlamStageConfig, VideoSourceSpec
from prml_vslam.pipeline.contracts.runtime import RunSnapshot, RunState, StreamingRunSnapshot
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.ingest import _max_frames_for_request
from prml_vslam.pipeline.placement import actor_options_for_stage
from prml_vslam.pipeline.ray_runtime.common import backend_config_payload, clean_actor_options
from prml_vslam.pipeline.ray_runtime.coordinator import RunCoordinatorActor
from prml_vslam.pipeline.ray_runtime.stage_actors import StreamingSlamStageActor
from prml_vslam.pipeline.run_service import RunService
from prml_vslam.pipeline.snapshot_projector import SnapshotProjector
from prml_vslam.pipeline.stage_registry import StageRegistry
from prml_vslam.utils import PathConfig
from tests.pipeline_testing_support import FakeOfflineSource, FakeStreamingSource


@pytest.fixture(autouse=True)
def _isolated_ray_namespace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PRML_VSLAM_RAY_NAMESPACE", f"pytest-{uuid.uuid4().hex}")
    yield
    if ray.is_initialized():
        ray.shutdown()


def test_run_request_requires_explicit_backend_spec() -> None:
    with pytest.raises(ValidationError):
        RunRequest.model_validate(
            {
                "experiment_name": "demo",
                "mode": "offline",
                "output_dir": ".artifacts",
                "source": {"video_path": "captures/demo.mp4"},
                "slam": {"method": "vista", "backend": {"max_frames": 9}},
            }
        )


def test_run_request_accepts_explicit_backend_spec() -> None:
    request = RunRequest.model_validate(
        {
            "experiment_name": "demo",
            "mode": "offline",
            "output_dir": ".artifacts",
            "source": {"video_path": "captures/demo.mp4"},
            "slam": {"backend": {"kind": "vista", "max_frames": 9}},
        }
    )

    assert request.slam.backend.kind == "vista"
    assert request.slam.backend.max_frames == 9


def test_stage_registry_marks_placeholder_stages_unavailable(tmp_path: Path) -> None:
    path_config = PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts")
    request = RunRequest(
        experiment_name="placeholder",
        mode=PipelineMode.OFFLINE,
        output_dir=path_config.artifacts_dir,
        source=DatasetSourceSpec(dataset_id="advio", sequence_id="advio-01"),
        slam=SlamStageConfig(backend={"kind": "mock"}),
        benchmark=BenchmarkConfig(
            reference={"enabled": False},
            trajectory=TrajectoryBenchmarkConfig(enabled=False),
            cloud=CloudBenchmarkConfig(enabled=True),
            efficiency=EfficiencyBenchmarkConfig(enabled=False),
        ),
    )

    plan = StageRegistry.default().compile(
        request=request,
        backend=BackendFactory().describe(request.slam.backend),
        path_config=path_config,
    )

    unavailable = [stage for stage in plan.stages if not stage.available]
    assert len(unavailable) == 1
    assert unavailable[0].key.value == "cloud.evaluate"
    assert "placeholder" in unavailable[0].availability_reason


def test_snapshot_projector_preserves_stopped_preview_handle() -> None:
    projector = SnapshotProjector()
    preview = PreviewHandle(handle_id="preview", width=16, height=12, channels=3, dtype="uint8")
    snapshot = StreamingRunSnapshot(run_id="run-1", state=RunState.STOPPED, latest_preview=preview)

    updated = projector.apply(
        snapshot,
        PacketObserved(
            event_id="1",
            run_id="run-1",
            ts_ns=1,
            packet=FramePacketSummary(seq=1, timestamp_ns=1, provenance=FramePacketProvenance()),
            frame=ArrayHandle(handle_id="frame", shape=(4, 4, 3), dtype="uint8"),
            received_frames=1,
            measured_fps=12.0,
        ),
    )

    assert updated.state is RunState.STOPPED
    assert isinstance(updated, StreamingRunSnapshot)
    assert updated.latest_preview == preview


def test_snapshot_projector_preserves_completed_state_on_run_stopped() -> None:
    projector = SnapshotProjector()
    snapshot = StreamingRunSnapshot(run_id="run-1", state=RunState.COMPLETED)

    updated = projector.apply(
        snapshot,
        RunStopped(event_id="2", run_id="run-1", ts_ns=2),
    )

    assert updated.state is RunState.COMPLETED


def test_snapshot_projector_clears_current_stage_on_stage_failed() -> None:
    projector = SnapshotProjector()
    snapshot = RunSnapshot(
        run_id="run-1",
        state=RunState.RUNNING,
        current_stage_key=StageKey.SLAM,
        stage_status={StageKey.SLAM: StageStatus.RUNNING},
    )

    updated = projector.apply(
        snapshot,
        StageFailed(
            event_id="3",
            run_id="run-1",
            ts_ns=3,
            stage_key=StageKey.SLAM,
            outcome=StageOutcome(
                stage_key=StageKey.SLAM,
                status=StageStatus.FAILED,
                config_hash="cfg",
                input_fingerprint="inp",
                error_message="boom",
            ),
        ),
    )

    assert updated.current_stage_key is None
    assert updated.stage_status[StageKey.SLAM] is StageStatus.FAILED
    assert updated.error_message == "boom"


def test_translate_slam_update_emits_explicit_backend_events() -> None:
    update = SlamUpdate(
        seq=4,
        timestamp_ns=8,
        source_seq=4,
        source_timestamp_ns=8,
        is_keyframe=True,
        keyframe_index=2,
        pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=2.0, tz=3.0),
        num_sparse_points=5,
        num_dense_points=9,
        pose_updated=True,
    )
    pointmap_handle = ArrayHandle(handle_id="pointmap", shape=(2, 2, 3), dtype="float32")

    events = translate_slam_update(
        update=update,
        accepted_keyframes=3,
        backend_fps=7.5,
        pointmap_handle=pointmap_handle,
    )
    kinds = [event.kind for event in events]

    assert "pose.estimated" in kinds
    assert "keyframe.accepted" in kinds
    assert "keyframe.visualization_ready" in kinds
    assert "map.stats" in kinds
    visualization_event = next(event for event in events if isinstance(event, KeyframeVisualizationReady))
    assert visualization_event.pointmap == pointmap_handle
    assert visualization_event.pose.tx == 1.0


def test_actor_options_preserve_defaults_without_placement() -> None:
    request = _placement_request()
    backend = _test_backend_descriptor(default_cpu=4.0, default_gpu=1.0)

    ingest_options = actor_options_for_stage(
        stage_key=StageKey.INGEST,
        request=request,
        backend=backend,
        default_num_cpus=1.0,
        default_num_gpus=0.0,
        restartable=True,
    )
    slam_options = actor_options_for_stage(
        stage_key=StageKey.SLAM,
        request=request,
        backend=backend,
        default_num_cpus=2.0,
        default_num_gpus=0.0,
        inherit_backend_defaults=True,
    )

    assert ingest_options["num_cpus"] == 1.0
    assert ingest_options["num_gpus"] == 0.0
    assert ingest_options["max_restarts"] == -1
    assert slam_options["num_cpus"] == 4.0
    assert slam_options["num_gpus"] == 1.0


def test_actor_options_explicit_slam_placement_overrides_resources() -> None:
    request = _placement_request(placement={"slam": {"resources": {"CPU": 4, "GPU": 1}}})
    backend = _test_backend_descriptor(default_cpu=2.0, default_gpu=0.0)

    options = actor_options_for_stage(
        stage_key=StageKey.SLAM,
        request=request,
        backend=backend,
        default_num_cpus=2.0,
        default_num_gpus=0.0,
        inherit_backend_defaults=True,
    )

    assert options["num_cpus"] == 4.0
    assert options["num_gpus"] == 1.0


def test_actor_options_explicit_ingest_placement_overrides_resources() -> None:
    request = _placement_request(placement={"ingest": {"resources": {"CPU": 3}}})
    backend = _test_backend_descriptor(default_cpu=8.0, default_gpu=1.0)

    options = actor_options_for_stage(
        stage_key=StageKey.INGEST,
        request=request,
        backend=backend,
        default_num_cpus=1.0,
        default_num_gpus=0.0,
        restartable=True,
    )

    assert options["num_cpus"] == 3.0
    assert options["num_gpus"] == 0.0
    assert options["max_restarts"] == -1


def test_clean_actor_options_keeps_nonempty_resources_dict() -> None:
    cleaned = clean_actor_options(
        {
            "num_cpus": 1.0,
            "resources": {"capture": 1.0},
            "empty_resources": {},
            "none_value": None,
        }
    )

    assert cleaned == {"num_cpus": 1.0, "resources": {"capture": 1.0}}


def test_run_coordinator_resolves_materialized_handle_payloads_without_ray_get() -> None:
    coordinator_cls = RunCoordinatorActor.__ray_metadata__.modified_class
    coordinator = coordinator_cls(run_id="demo", namespace="pytest-unit")
    payload = np.zeros((2, 2, 3), dtype=np.uint8)

    coordinator._remember_handle("frame-1", payload)

    resolved = coordinator._resolve_handle_local("frame-1")

    assert resolved is not None
    assert np.array_equal(resolved, payload)


def test_run_coordinator_read_array_accepts_materialized_handle_payloads() -> None:
    coordinator_cls = RunCoordinatorActor.__ray_metadata__.modified_class
    coordinator = coordinator_cls(run_id="demo", namespace="pytest-unit")
    payload = np.zeros((2, 2, 3), dtype=np.uint8)

    coordinator._remember_handle("frame-1", payload)

    resolved = coordinator.read_array("frame-1")

    assert resolved is not None
    assert np.array_equal(resolved, payload)


def test_run_coordinator_submits_rerun_bindings_without_hot_path_ray_get(monkeypatch: pytest.MonkeyPatch) -> None:
    coordinator_cls = RunCoordinatorActor.__ray_metadata__.modified_class
    coordinator = coordinator_cls(run_id="demo", namespace="pytest-unit")
    submitted: list[tuple[object, list[tuple[str, object]]]] = []

    class FakeObserveEventRemote:
        def remote(self, *, event: object, bindings: list[tuple[str, object]]) -> str:
            submitted.append((event, bindings))
            return "rerun-call-1"

    coordinator._rerun_sink = SimpleNamespace(observe_event=FakeObserveEventRemote())
    monkeypatch.setattr(
        "prml_vslam.pipeline.ray_runtime.coordinator.ray.get",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("coordinator hot path must not call ray.get")),
    )

    coordinator.on_packet(
        packet=FramePacketSummary(seq=1, timestamp_ns=1, provenance=FramePacketProvenance()),
        frame_handle=ArrayHandle(handle_id="frame-1", shape=(2, 2, 3), dtype="uint8"),
        frame_ref=np.zeros((2, 2, 3), dtype=np.uint8),
        depth_ref=None,
        confidence_ref=None,
        intrinsics=None,
        pose=None,
        provenance=FramePacketProvenance(),
        received_frames=1,
        measured_fps=30.0,
    )

    assert len(submitted) == 1
    assert submitted[0][1][0][0] == "frame-1"
    assert coordinator._rerun_sink_last_call == "rerun-call-1"


def test_run_coordinator_records_stage_failed_events() -> None:
    coordinator_cls = RunCoordinatorActor.__ray_metadata__.modified_class
    coordinator = coordinator_cls(run_id="demo", namespace="pytest-unit")

    coordinator._record_stage_failure(
        stage_key=StageKey.SLAM,
        outcome=StageOutcome(
            stage_key=StageKey.SLAM,
            status=StageStatus.FAILED,
            config_hash="cfg",
            input_fingerprint="inp",
            error_message="backend boom",
        ),
    )

    snapshot = coordinator.snapshot()

    assert snapshot.stage_status[StageKey.SLAM] is StageStatus.FAILED
    assert snapshot.error_message == "backend boom"
    assert any(getattr(event, "kind", None) == "stage.failed" for event in coordinator.events())


def test_streaming_slam_stage_resolves_materialized_payloads_without_ray_get() -> None:
    payload = np.zeros((2, 2, 3), dtype=np.uint8)

    resolved = StreamingSlamStageActor.__ray_metadata__.modified_class._resolve_payload(payload)

    assert resolved is not None
    assert np.array_equal(resolved, payload)


def test_backend_config_payload_strips_backend_kind_for_vista() -> None:
    request = RunRequest.model_validate(
        {
            "experiment_name": "vista",
            "mode": "offline",
            "output_dir": ".artifacts",
            "source": {"video_path": "captures/demo.mp4"},
            "slam": {"backend": {"kind": "vista", "max_frames": 9}},
        }
    )

    payload = backend_config_payload(request)

    assert payload.max_frames == 9


def test_streaming_requests_cap_ingest_by_backend_max_frames() -> None:
    request = RunRequest.model_validate(
        {
            "experiment_name": "vista-stream",
            "mode": "streaming",
            "output_dir": ".artifacts",
            "source": {"dataset_id": "advio", "sequence_id": "advio-01"},
            "slam": {"backend": {"kind": "vista", "max_frames": 42}},
        }
    )

    assert _max_frames_for_request(request) == 42


def test_ray_backend_uses_current_python_for_local_runtime_env() -> None:
    runtime_env = RayPipelineBackend._build_runtime_env(address=None)

    assert runtime_env["py_executable"] == sys.executable
    assert "excludes" in runtime_env
    assert runtime_env["env_vars"]["OMP_NUM_THREADS"] == "1"
    assert runtime_env["env_vars"]["MKL_NUM_THREADS"] == "1"
    assert runtime_env["env_vars"]["OPENBLAS_NUM_THREADS"] == "1"
    assert runtime_env["env_vars"]["UV_NUM_THREADS"] == "1"


def test_ray_backend_does_not_force_local_python_for_remote_address() -> None:
    runtime_env = RayPipelineBackend._build_runtime_env(address="ray://10.0.0.5:10001")

    assert "py_executable" not in runtime_env
    assert "excludes" in runtime_env
    assert runtime_env["env_vars"]["OMP_NUM_THREADS"] == "1"


def test_ray_backend_disables_uv_runtime_env_replication_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("RAY_ENABLE_UV_RUN_RUNTIME_ENV", raising=False)

    RayPipelineBackend._prepare_ray_environment()

    assert os.environ["RAY_ENABLE_UV_RUN_RUNTIME_ENV"] == "0"


def test_ray_backend_prefers_persistent_local_head_outside_pytest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = RayPipelineBackend(namespace="prml_vslam.local")
    captured: dict[str, object] = {}

    monkeypatch.setattr("prml_vslam.pipeline.backend_ray.ray.is_initialized", lambda: False)
    monkeypatch.setattr(
        backend,
        "_ensure_local_head_address",
        lambda: "127.0.0.1:25001",
    )

    def fake_init(**kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setattr("prml_vslam.pipeline.backend_ray.ray.init", fake_init)

    backend._ensure_ray()

    assert captured["address"] == "127.0.0.1:25001"
    assert captured["_skip_env_hook"] is True


def test_ray_backend_keeps_inprocess_init_for_pytest_namespaces(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = RayPipelineBackend(namespace="pytest-unit")
    captured: dict[str, object] = {}

    monkeypatch.setattr("prml_vslam.pipeline.backend_ray.ray.is_initialized", lambda: False)
    monkeypatch.setattr(
        backend,
        "_ensure_local_head_address",
        lambda: (_ for _ in ()).throw(AssertionError("should not be called")),
    )

    def fake_init(**kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setattr("prml_vslam.pipeline.backend_ray.ray.init", fake_init)

    backend._ensure_ray()

    assert "address" not in captured
    assert captured["_skip_env_hook"] is True


def test_ray_backend_submits_via_coordinator_and_reads_via_backend(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path_config = PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts")
    backend = RayPipelineBackend(path_config=path_config, namespace="pytest-unit")
    request = RunRequest(
        experiment_name="backend-unit",
        mode=PipelineMode.OFFLINE,
        output_dir=path_config.artifacts_dir,
        source=VideoSourceSpec(video_path=Path("captures/dummy.mp4")),
        slam=SlamStageConfig(backend={"kind": "mock"}),
    )
    snapshot = RunSnapshot(run_id="backend-unit", state=RunState.COMPLETED)
    submitted: list[tuple[str, object]] = []
    stopped: list[str] = []

    class _Remote:
        def __init__(self, fn):
            self.remote = fn

    fake_coordinator = type(
        "Coordinator",
        (),
        {
            "start": _Remote(
                lambda **kwargs: submitted.append((kwargs["plan"].run_id, kwargs.get("runtime_source"))) or None
            ),
            "stop": _Remote(lambda: stopped.append("backend-unit")),
            "snapshot": _Remote(lambda: snapshot),
            "events": _Remote(lambda after_event_id, limit: []),
            "read_array": _Remote(lambda handle_id: np.ones((2, 2, 3), dtype=np.uint8)),
            "shutdown": _Remote(lambda: None),
        },
    )()

    monkeypatch.setattr("prml_vslam.pipeline.backend_ray.ray.get", lambda value: value)
    monkeypatch.setattr(backend, "_ensure_ray", lambda: None)
    monkeypatch.setattr(backend, "_create_coordinator", lambda run_id: fake_coordinator)
    monkeypatch.setattr(backend, "_coordinator_for", lambda run_id: fake_coordinator)

    run_id = backend.submit_run(request=request, runtime_source="runtime")

    assert run_id == "backend-unit"
    assert submitted == [("backend-unit", "runtime")]
    assert backend.get_snapshot(run_id).state is RunState.COMPLETED
    assert backend.get_events(run_id) == []
    assert backend.read_array(run_id, ArrayHandle(handle_id="frame", shape=(2, 2, 3), dtype="uint8")) is not None
    backend.stop_run(run_id)
    assert stopped == ["backend-unit"]


@pytest.mark.skipif(
    os.getenv("PRML_VSLAM_RUN_RAY_SMOKE") != "1",
    reason="Ray end-to-end smoke tests remain opt-in while the real cluster startup path is environment-sensitive.",
)
def test_run_service_offline_mock_smoke(tmp_path: Path) -> None:
    path_config = PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts")
    service = RunService(path_config=path_config)
    request = RunRequest(
        experiment_name="offline-smoke",
        mode=PipelineMode.OFFLINE,
        output_dir=path_config.artifacts_dir,
        source=VideoSourceSpec(video_path=Path("captures/dummy.mp4")),
        slam=SlamStageConfig(backend={"kind": "mock"}),
    )

    service.start_run(request=request, runtime_source=FakeOfflineSource())
    snapshot = _wait_for_terminal_snapshot(service)

    assert snapshot.state is RunState.COMPLETED
    assert snapshot.sequence_manifest is not None
    assert snapshot.slam is not None
    assert "trajectory_tum" in snapshot.artifacts
    service.shutdown()


@pytest.mark.skipif(
    os.getenv("PRML_VSLAM_RUN_RAY_SMOKE") != "1",
    reason="Ray end-to-end smoke tests remain opt-in while the real cluster startup path is environment-sensitive.",
)
def test_run_service_streaming_mock_smoke(tmp_path: Path) -> None:
    path_config = PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts")
    service = RunService(path_config=path_config)
    request = RunRequest(
        experiment_name="streaming-smoke",
        mode=PipelineMode.STREAMING,
        output_dir=path_config.artifacts_dir,
        source=VideoSourceSpec(video_path=Path("captures/dummy.mp4")),
        slam=SlamStageConfig(backend={"kind": "mock"}),
    )

    service.start_run(request=request, runtime_source=FakeStreamingSource())
    snapshot = _wait_for_terminal_snapshot(service)

    assert snapshot.state is RunState.COMPLETED
    assert isinstance(snapshot, StreamingRunSnapshot)
    assert snapshot.received_frames >= 3
    assert len(snapshot.trajectory_positions_xyz) >= 1
    assert snapshot.latest_packet is not None
    assert snapshot.latest_frame is not None
    assert service.read_array(snapshot.latest_frame) is not None
    service.shutdown()


def _wait_for_terminal_snapshot(service: RunService, *, timeout_seconds: float = 20.0) -> RunSnapshot:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        snapshot = service.snapshot()
        if snapshot.state not in {RunState.IDLE, RunState.PREPARING, RunState.RUNNING}:
            return snapshot
        time.sleep(0.2)
    raise AssertionError("Pipeline run did not reach a terminal state.")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _placement_request(*, placement: dict[str, object] | None = None) -> RunRequest:
    by_stage = (
        {}
        if placement is None
        else {StageKey(stage_key): stage_placement for stage_key, stage_placement in placement.items()}
    )
    return RunRequest(
        experiment_name="placement-demo",
        mode=PipelineMode.OFFLINE,
        output_dir=Path(".artifacts"),
        source=VideoSourceSpec(video_path=Path("captures/demo.mp4")),
        slam=SlamStageConfig(backend={"kind": "mock"}),
        placement={"by_stage": by_stage},
    )


def _test_backend_descriptor(*, default_cpu: float, default_gpu: float) -> BackendDescriptor:
    return BackendDescriptor(
        key="test",
        display_name="Test Backend",
        capabilities=BackendCapabilities(
            offline=True,
            streaming=True,
            dense_points=True,
            live_preview=True,
            native_visualization=False,
            trajectory_benchmark_support=True,
        ),
        default_resources={"CPU": default_cpu, "GPU": default_gpu},
    )
