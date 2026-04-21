"""Focused tests for the Ray-backed pipeline core."""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
import uuid
from collections import deque
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest
import ray
from pydantic import ValidationError

from prml_vslam.benchmark import (
    BenchmarkConfig,
    CloudBenchmarkConfig,
    EfficiencyBenchmarkConfig,
    ReferenceSource,
    TrajectoryBenchmarkConfig,
)
from prml_vslam.interfaces import FramePacketProvenance, FrameTransform
from prml_vslam.interfaces.ingest import PreparedBenchmarkInputs, SequenceManifest
from prml_vslam.interfaces.slam import (
    ArtifactRef,
    BackendWarning,
    KeyframeVisualizationReady,
    PoseEstimated,
    SlamArtifacts,
    SlamSessionInit,
    SlamUpdate,
)
from prml_vslam.methods import MethodId
from prml_vslam.methods.descriptors import BackendCapabilities, BackendDescriptor
from prml_vslam.methods.events import translate_slam_update
from prml_vslam.methods.factory import BackendFactory
from prml_vslam.pipeline import PipelineMode, RunRequest
from prml_vslam.pipeline.backend_ray import RayPipelineBackend
from prml_vslam.pipeline.contracts.events import (
    BackendNoticeReceived,
    FramePacketSummary,
    PacketObserved,
    RunEvent,
    RunStopped,
    StageFailed,
    StageOutcome,
    StageProgress,
    StageStatus,
)
from prml_vslam.pipeline.contracts.handles import ArrayHandle, PreviewHandle
from prml_vslam.pipeline.contracts.plan import RunPlan, RunPlanStage
from prml_vslam.pipeline.contracts.provenance import RunSummary
from prml_vslam.pipeline.contracts.request import (
    DatasetSourceSpec,
    SlamStageConfig,
    VideoSourceSpec,
    build_run_request,
)
from prml_vslam.pipeline.contracts.runtime import RunSnapshot, RunState, StreamingRunSnapshot
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.finalization import stable_hash
from prml_vslam.pipeline.ingest import _max_frames_for_request, materialize_offline_manifest
from prml_vslam.pipeline.placement import actor_options_for_stage
from prml_vslam.pipeline.ray_runtime.common import backend_config_payload, clean_actor_options
from prml_vslam.pipeline.ray_runtime.coordinator import RunCoordinatorActor
from prml_vslam.pipeline.ray_runtime.stage_actors import PacketSourceActor, StreamingSlamStageActor
from prml_vslam.pipeline.ray_runtime.stage_program import StageCompletionPayload
from prml_vslam.pipeline.run_service import RunService
from prml_vslam.pipeline.snapshot_projector import SnapshotProjector
from prml_vslam.pipeline.source_resolver import OfflineSourceResolver
from prml_vslam.pipeline.stage_registry import StageRegistry
from prml_vslam.utils import Console, PathConfig, RunArtifactPaths
from tests.pipeline_testing_support import FakeOfflineSource, FakeStreamingSource


@pytest.fixture(autouse=True)
def _isolated_ray_namespace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PRML_VSLAM_RAY_NAMESPACE", f"pytest-{uuid.uuid4().hex}")
    yield
    if ray.is_initialized():
        ray.shutdown()


@contextmanager
def _capture_logger(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    logger_name: str,
):
    monkeypatch.setattr("prml_vslam.utils.console.Console._logging_configured", True)
    logger = logging.getLogger(logger_name)
    old_handlers = list(logger.handlers)
    old_level = logger.level
    old_propagate = logger.propagate
    logger.handlers = [caplog.handler]
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    caplog.clear()
    try:
        yield logger
    finally:
        logger.handlers = old_handlers
        logger.setLevel(old_level)
        logger.propagate = old_propagate


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


def test_run_request_accepts_mock_backend_noise_fields() -> None:
    request = RunRequest.model_validate(
        {
            "experiment_name": "mock-noise",
            "mode": "offline",
            "output_dir": ".artifacts",
            "source": {"video_path": "captures/demo.mp4"},
            "slam": {
                "backend": {
                    "kind": "mock",
                    "max_frames": 9,
                    "trajectory_position_noise_mean_m": 0.1,
                    "trajectory_position_noise_variance_m2": 0.2,
                    "point_noise_mean_m": 0.3,
                    "point_noise_variance_m2": 0.4,
                    "random_seed": 17,
                }
            },
        }
    )

    assert request.slam.backend.kind == "mock"
    assert request.slam.backend.trajectory_position_noise_mean_m == 0.1
    assert request.slam.backend.trajectory_position_noise_variance_m2 == 0.2
    assert request.slam.backend.point_noise_mean_m == 0.3
    assert request.slam.backend.point_noise_variance_m2 == 0.4
    assert request.slam.backend.random_seed == 17


def test_run_request_defaults_to_ephemeral_local_head_lifecycle() -> None:
    request = RunRequest.model_validate(
        {
            "experiment_name": "demo",
            "mode": "offline",
            "output_dir": ".artifacts",
            "source": {"video_path": "captures/demo.mp4"},
            "slam": {"backend": {"kind": "vista"}},
        }
    )

    assert request.runtime.ray.local_head_lifecycle == "ephemeral"


def test_run_request_from_toml_accepts_runtime_ray_policy(tmp_path: Path) -> None:
    config_path = tmp_path / "run.toml"
    config_path.write_text(
        """
experiment_name = "demo"
mode = "streaming"
output_dir = ".artifacts"

[source]
dataset_id = "advio"
sequence_id = "advio-01"

[slam.backend]
kind = "mock"

[runtime.ray]
local_head_lifecycle = "reusable"
""".strip(),
        encoding="utf-8",
    )

    request = RunRequest.from_toml(config_path)

    assert request.runtime.ray.local_head_lifecycle == "reusable"


def test_run_request_from_toml_accepts_viewer_blueprint_path(tmp_path: Path) -> None:
    config_path = tmp_path / "run.toml"
    config_path.write_text(
        """
experiment_name = "demo"
mode = "streaming"
output_dir = ".artifacts"

[source]
dataset_id = "advio"
sequence_id = "advio-01"

[slam.backend]
kind = "mock"

[visualization]
connect_live_viewer = true
viewer_blueprint_path = ".configs/visualization/vista_blueprint.rbl"
""".strip(),
        encoding="utf-8",
    )

    request = RunRequest.from_toml(config_path)

    assert request.visualization.connect_live_viewer is True
    assert request.visualization.viewer_blueprint_path == Path(".configs/visualization/vista_blueprint.rbl")


def test_run_request_build_rejects_cloud_eval_without_dense_points(tmp_path: Path) -> None:
    path_config = PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts")
    request = RunRequest(
        experiment_name="cloud-validation",
        mode=PipelineMode.OFFLINE,
        output_dir=path_config.artifacts_dir,
        source=VideoSourceSpec(video_path=Path("captures/demo.mp4")),
        slam=SlamStageConfig(backend={"kind": "mock"}, outputs={"emit_dense_points": False}),
        benchmark=BenchmarkConfig(cloud=CloudBenchmarkConfig(enabled=True)),
    )

    with pytest.raises(ValueError, match=r"Cloud evaluation requires `slam\.outputs\.emit_dense_points=True`\."):
        request.build(path_config)


def test_run_request_build_uses_supplied_path_config(tmp_path: Path) -> None:
    path_config = PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts")
    request = RunRequest(
        experiment_name="request-build",
        mode=PipelineMode.OFFLINE,
        output_dir=path_config.artifacts_dir,
        source=VideoSourceSpec(video_path=Path("captures/demo.mp4")),
        slam=SlamStageConfig(backend={"kind": "mock"}),
    )

    plan = request.build(path_config)

    assert plan.run_id == "request-build"
    assert (
        plan.artifact_root
        == path_config.plan_run_paths(
            experiment_name=request.experiment_name,
            method_slug=request.slam.backend.kind,
            output_dir=request.output_dir,
        ).artifact_root
    )
    assert [stage.key for stage in plan.stages] == [StageKey.INGEST, StageKey.SLAM, StageKey.SUMMARY]


def test_build_run_request_copies_backend_policy_and_visualization_fields(tmp_path: Path) -> None:
    request = build_run_request(
        experiment_name="builder-demo",
        mode=PipelineMode.OFFLINE,
        output_dir=tmp_path / ".artifacts",
        source=VideoSourceSpec(video_path=Path("captures/demo.mp4"), frame_stride=3),
        method=MethodId.VISTA,
        max_frames=12,
        backend_overrides={
            "vista_slam_dir": Path("external/vista-slam"),
            "checkpoint_path": Path("external/vista-slam/pretrains/frontend_sta_weights.pth"),
            "vocab_path": Path("external/vista-slam/pretrains/ORBvoc.txt"),
        },
        emit_dense_points=False,
        emit_sparse_points=True,
        reference_enabled=True,
        trajectory_eval_enabled=True,
        trajectory_baseline=ReferenceSource.ARCORE,
        evaluate_cloud=False,
        evaluate_efficiency=True,
        connect_live_viewer=True,
        export_viewer_rrd=True,
    )

    assert request.slam.backend.kind == MethodId.VISTA.value
    assert request.slam.backend.max_frames == 12
    assert request.slam.backend.vista_slam_dir == Path("external/vista-slam")
    assert request.slam.outputs.emit_dense_points is False
    assert request.slam.outputs.emit_sparse_points is True
    assert request.benchmark.reference.enabled is True
    assert request.benchmark.trajectory.enabled is True
    assert request.benchmark.trajectory.baseline_source is ReferenceSource.ARCORE
    assert request.benchmark.cloud.enabled is False
    assert request.benchmark.efficiency.enabled is True
    assert request.visualization.connect_live_viewer is True
    assert request.visualization.export_viewer_rrd is True


def test_stage_registry_marks_placeholder_stages_unavailable(tmp_path: Path) -> None:
    path_config = PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts")
    request = RunRequest(
        experiment_name="placeholder",
        mode=PipelineMode.OFFLINE,
        output_dir=path_config.artifacts_dir,
        source=DatasetSourceSpec(
            dataset_id="advio",
            sequence_id="advio-01",
            dataset_serving={
                "dataset_id": "advio",
                "pose_source": "ground_truth",
                "pose_frame_mode": "provider_world",
            },
        ),
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


def test_snapshot_projector_copies_only_mutated_runtime_containers() -> None:
    projector = SnapshotProjector()
    snapshot = StreamingRunSnapshot(
        run_id="run-1",
        state=RunState.RUNNING,
        stage_status={StageKey.INGEST: StageStatus.RUNNING},
        stage_progress={StageKey.INGEST: StageProgress(message="streaming")},
        artifacts={"before": ArtifactRef(path=Path("/tmp/before"), kind="txt", fingerprint="before")},
        trajectory_positions_xyz=[(0.0, 0.0, 0.0)],
        trajectory_timestamps_s=[0.0],
    )

    updated = projector.apply(
        snapshot,
        BackendNoticeReceived(
            event_id="2a",
            run_id="run-1",
            ts_ns=2,
            stage_key=StageKey.SLAM,
            notice=PoseEstimated(
                seq=1,
                source_seq=1,
                source_timestamp_ns=2,
                timestamp_ns=2,
                pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=2.0, tz=3.0),
            ),
        ),
    )

    assert updated.trajectory_positions_xyz == [(0.0, 0.0, 0.0), (1.0, 2.0, 3.0)]
    assert updated.trajectory_timestamps_s == [0.0, 2e-9]
    assert snapshot.trajectory_positions_xyz == [(0.0, 0.0, 0.0)]
    assert snapshot.trajectory_timestamps_s == [0.0]
    assert updated.stage_status == snapshot.stage_status
    assert updated.stage_progress == snapshot.stage_progress
    assert updated.artifacts == snapshot.artifacts
    assert updated.stage_status is not snapshot.stage_status
    assert updated.stage_progress is not snapshot.stage_progress
    assert updated.artifacts is not snapshot.artifacts


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
        backend_warnings=["dense pointmap missing for source_seq=4, keyframe_index=2"],
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
    assert "backend.warning" in kinds
    assert "keyframe.accepted" in kinds
    assert "keyframe.visualization_ready" in kinds
    assert "map.stats" in kinds
    warning_event = next(event for event in events if isinstance(event, BackendWarning))
    assert "source_seq=4" in warning_event.message
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
    submitted: list[tuple[RunEvent, list[tuple[str, np.ndarray]]]] = []

    class FakeObserveEventRemote:
        def remote(self, *, event: RunEvent, rerun_bindings: list[tuple[str, np.ndarray]]) -> str:
            submitted.append((event, rerun_bindings))
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
        rerun_bindings=[("frame-1", np.zeros((2, 2, 3), dtype=np.uint8))],
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
    assert isinstance(submitted[0][1][0][1], np.ndarray)
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
    assert any(event.kind == "stage.failed" for event in coordinator.events())


def test_run_coordinator_emits_ingest_stage_failure_before_run_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path_config = PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts")
    request = RunRequest(
        experiment_name="ingest-failure",
        mode=PipelineMode.OFFLINE,
        output_dir=path_config.artifacts_dir,
        source=VideoSourceSpec(video_path=Path("captures/demo.mp4")),
        slam=SlamStageConfig(backend={"kind": "mock"}),
        benchmark={"trajectory": {"enabled": False}},
    )
    coordinator_cls = RunCoordinatorActor.__ray_metadata__.modified_class
    coordinator = coordinator_cls(run_id=request.experiment_name, namespace="pytest-unit")
    plan = _plan_with_stages(
        tmp_path=tmp_path,
        request=request,
        stage_keys=[StageKey.INGEST, StageKey.SLAM, StageKey.SUMMARY],
    )

    coordinator._request = request
    coordinator._plan = plan
    coordinator._path_config = path_config
    monkeypatch.setattr(coordinator._console, "exception", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "prml_vslam.pipeline.ray_runtime.stage_program.run_ingest_stage",
        lambda *, context, source: (_ for _ in ()).throw(RuntimeError("ingest boom")),
    )

    coordinator._run(request=request, plan=plan, path_config=path_config, runtime_source=FakeOfflineSource())

    events = coordinator.events()
    assert [event.kind for event in events] == [
        "run.started",
        "stage.queued",
        "stage.started",
        "stage.failed",
        "run.failed",
    ]
    failed_event = next(event for event in events if isinstance(event, StageFailed))
    assert failed_event.stage_key is StageKey.INGEST
    assert failed_event.outcome.config_hash == stable_hash(request.source)
    assert failed_event.outcome.input_fingerprint == stable_hash(request.source)
    assert failed_event.outcome.error_message == "ingest boom"


def test_run_coordinator_fails_fast_for_available_stage_without_runtime_spec(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = RunRequest(
        experiment_name="missing-runtime-stage",
        mode=PipelineMode.OFFLINE,
        output_dir=tmp_path / ".artifacts",
        source=VideoSourceSpec(video_path=Path("captures/demo.mp4")),
        slam=SlamStageConfig(backend={"kind": "mock"}),
    )
    coordinator_cls = RunCoordinatorActor.__ray_metadata__.modified_class
    coordinator = coordinator_cls(run_id=request.experiment_name, namespace="pytest-unit")
    path_config = PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts")
    plan = _plan_with_stages(
        tmp_path=tmp_path,
        request=request,
        stage_keys=[StageKey.INGEST, StageKey.CLOUD_EVALUATION, StageKey.SUMMARY],
    )

    monkeypatch.setattr(
        "prml_vslam.pipeline.ray_runtime.coordinator.BackendFactory.describe",
        lambda self, backend: _test_backend_descriptor(default_cpu=1.0, default_gpu=0.0),
    )
    monkeypatch.setattr(coordinator._console, "exception", lambda *args, **kwargs: None)

    coordinator._run(request=request, plan=plan, path_config=path_config, runtime_source=FakeOfflineSource())

    failed_event = next(event for event in coordinator.events() if event.kind == "run.failed")
    assert "cloud.evaluate" in failed_event.error_message


def test_run_coordinator_offline_dispatches_batch_stage_executors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    coordinator_cls = RunCoordinatorActor.__ray_metadata__.modified_class
    coordinator = coordinator_cls(run_id="demo", namespace="pytest-unit")
    path_config = PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts")
    request = RunRequest(
        experiment_name="dispatch-demo",
        mode=PipelineMode.OFFLINE,
        output_dir=path_config.artifacts_dir,
        source=VideoSourceSpec(video_path=Path("captures/demo.mp4")),
        slam=SlamStageConfig(backend={"kind": "mock"}),
        benchmark={"trajectory": {"enabled": False}},
    )
    plan = _plan_with_stages(
        tmp_path=tmp_path,
        request=request,
        stage_keys=[StageKey.INGEST, StageKey.SLAM, StageKey.SUMMARY],
    )
    calls: list[str] = []
    sequence_manifest = SequenceManifest(sequence_id="demo-sequence")
    slam_artifacts = SlamArtifacts(
        trajectory_tum=ArtifactRef(path=tmp_path / "trajectory.tum", kind="tum", fingerprint="traj"),
    )

    coordinator._backend_descriptor = _test_backend_descriptor(default_cpu=1.0, default_gpu=0.0)
    monkeypatch.setattr(
        "prml_vslam.pipeline.ray_runtime.stage_program.run_ingest_stage",
        lambda *, context, source: (
            calls.append("ingest")
            or StageCompletionPayload(
                outcome=StageOutcome(
                    stage_key=StageKey.INGEST,
                    status=StageStatus.COMPLETED,
                    config_hash="ingest",
                    input_fingerprint="ingest",
                ),
                sequence_manifest=sequence_manifest,
                benchmark_inputs=None,
            )
        ),
    )
    monkeypatch.setattr(
        "prml_vslam.pipeline.ray_runtime.stage_program.run_offline_slam_stage",
        lambda *, context, sequence_manifest, benchmark_inputs: (
            calls.append("slam")
            or StageCompletionPayload(
                outcome=StageOutcome(
                    stage_key=StageKey.SLAM,
                    status=StageStatus.COMPLETED,
                    config_hash="slam",
                    input_fingerprint="slam",
                    artifacts={"trajectory_tum": slam_artifacts.trajectory_tum},
                ),
                slam=slam_artifacts,
                visualization=None,
            )
        ),
    )
    monkeypatch.setattr(
        "prml_vslam.pipeline.ray_runtime.stage_program.run_summary_stage",
        lambda *, context, stage_outcomes: (
            len(stage_outcomes) == 2
            and calls.append("summary")
            or StageCompletionPayload(
                outcome=StageOutcome(
                    stage_key=StageKey.SUMMARY,
                    status=StageStatus.COMPLETED,
                    config_hash="summary",
                    input_fingerprint="summary",
                ),
                summary=RunSummary(
                    run_id=context.plan.run_id,
                    artifact_root=context.plan.artifact_root,
                    stage_status={StageKey.INGEST: StageStatus.COMPLETED, StageKey.SLAM: StageStatus.COMPLETED},
                ),
                stage_manifests=[],
            )
        ),
    )

    coordinator._run_offline(
        request=request,
        plan=plan,
        path_config=path_config,
        runtime_source=FakeOfflineSource(),
    )

    assert calls == ["ingest", "slam", "summary"]
    snapshot = coordinator.snapshot()
    assert snapshot.sequence_manifest == sequence_manifest
    assert snapshot.slam == slam_artifacts
    assert snapshot.state is RunState.COMPLETED


def test_run_coordinator_finalize_streaming_dispatches_batch_executors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    coordinator_cls = RunCoordinatorActor.__ray_metadata__.modified_class
    coordinator = coordinator_cls(run_id="streaming-dispatch", namespace="pytest-unit")
    path_config = PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts")
    request = RunRequest(
        experiment_name="streaming-dispatch",
        mode=PipelineMode.STREAMING,
        output_dir=path_config.artifacts_dir,
        source=VideoSourceSpec(video_path=Path("captures/demo.mp4")),
        slam=SlamStageConfig(backend={"kind": "mock"}),
        benchmark={"trajectory": {"enabled": True}},
    )
    plan = _plan_with_stages(
        tmp_path=tmp_path,
        request=request,
        stage_keys=[
            StageKey.INGEST,
            StageKey.SLAM,
            StageKey.TRAJECTORY_EVALUATION,
            StageKey.SUMMARY,
        ],
    )
    sequence_manifest = SequenceManifest(sequence_id="stream-sequence")
    slam_artifacts = SlamArtifacts(
        trajectory_tum=ArtifactRef(path=tmp_path / "trajectory.tum", kind="tum", fingerprint="traj"),
    )
    slam_result = StageCompletionPayload(
        outcome=StageOutcome(
            stage_key=StageKey.SLAM,
            status=StageStatus.COMPLETED,
            config_hash="slam",
            input_fingerprint="slam",
            artifacts={"trajectory_tum": slam_artifacts.trajectory_tum},
        ),
        slam=slam_artifacts,
        visualization=None,
    )
    calls: list[str] = []

    class _RemoteCall:
        def __init__(self, value):
            self._value = value

        def remote(self, **_kwargs):
            return self._value

    class FakeSlamActor:
        close_stage = _RemoteCall(slam_result)

    monkeypatch.setattr("prml_vslam.pipeline.ray_runtime.coordinator.ray.get", lambda value: value)
    monkeypatch.setattr(
        "prml_vslam.pipeline.ray_runtime.stage_program.run_trajectory_evaluation_stage",
        lambda *, context, sequence_manifest, benchmark_inputs, slam: (
            sequence_manifest == coordinator._runtime_state.sequence_manifest
            and benchmark_inputs is None
            and slam == slam_artifacts
            and calls.append("trajectory")
            or StageCompletionPayload(
                outcome=StageOutcome(
                    stage_key=StageKey.TRAJECTORY_EVALUATION,
                    status=StageStatus.COMPLETED,
                    config_hash="trajectory",
                    input_fingerprint="trajectory",
                )
            )
        ),
    )
    monkeypatch.setattr(
        "prml_vslam.pipeline.ray_runtime.stage_program.run_summary_stage",
        lambda *, context, stage_outcomes: (
            len(stage_outcomes) == 2
            and calls.append("summary")
            or StageCompletionPayload(
                outcome=StageOutcome(
                    stage_key=StageKey.SUMMARY,
                    status=StageStatus.COMPLETED,
                    config_hash="summary",
                    input_fingerprint="summary",
                ),
                summary=RunSummary(
                    run_id=context.plan.run_id,
                    artifact_root=context.plan.artifact_root,
                    stage_status={
                        StageKey.SLAM: StageStatus.COMPLETED,
                        StageKey.TRAJECTORY_EVALUATION: StageStatus.COMPLETED,
                    },
                ),
                stage_manifests=[],
            )
        ),
    )
    coordinator._request = request
    coordinator._plan = plan
    coordinator._path_config = path_config
    coordinator._backend_descriptor = _test_backend_descriptor(default_cpu=1.0, default_gpu=0.0)
    coordinator._snapshot = StreamingRunSnapshot(run_id=plan.run_id, plan=plan, active_executor="ray")
    coordinator._runtime_state.sequence_manifest = sequence_manifest
    coordinator._slam_actor = FakeSlamActor()

    coordinator._finalize_streaming()

    assert calls == ["trajectory", "summary"]
    snapshot = coordinator.snapshot()
    assert snapshot.slam == slam_artifacts
    assert snapshot.state is RunState.COMPLETED


def test_streaming_slam_close_stage_fingerprints_normalized_sequence_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor_cls = StreamingSlamStageActor.__ray_metadata__.modified_class
    monkeypatch.setattr("prml_vslam.pipeline.ray_runtime.stage_actors.ray.get_actor", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "prml_vslam.visualization.rerun.collect_native_visualization_artifacts",
        lambda **kwargs: None,
    )
    actor = actor_cls(coordinator_name="demo", namespace="pytest-unit")
    trajectory_artifact = ArtifactRef(path=tmp_path / "trajectory.tum", kind="tum", fingerprint="traj")
    actor._session = SimpleNamespace(
        close=lambda: SlamArtifacts(trajectory_tum=trajectory_artifact),
    )
    request = RunRequest(
        experiment_name="streaming-fingerprint",
        mode=PipelineMode.STREAMING,
        output_dir=tmp_path / ".artifacts",
        source=VideoSourceSpec(video_path=Path("captures/demo.mp4")),
        slam=SlamStageConfig(backend={"kind": "mock"}),
    )
    plan = _plan_with_stages(
        tmp_path=tmp_path,
        request=request,
        stage_keys=[StageKey.INGEST, StageKey.SLAM, StageKey.SUMMARY],
    )
    sequence_manifest = SequenceManifest(sequence_id="normalized-sequence")

    result = actor.close_stage(request=request, plan=plan, sequence_manifest=sequence_manifest)

    assert result.outcome.input_fingerprint == stable_hash(sequence_manifest)


def test_streaming_slam_stage_resolves_materialized_payloads_without_ray_get() -> None:
    payload = np.zeros((2, 2, 3), dtype=np.uint8)

    resolved = StreamingSlamStageActor.__ray_metadata__.modified_class._resolve_payload(payload)

    assert resolved is not None
    assert np.array_equal(resolved, payload)


def test_streaming_slam_stage_passes_sequence_manifest_and_benchmark_inputs_to_backend(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor_cls = StreamingSlamStageActor.__ray_metadata__.modified_class
    monkeypatch.setattr("prml_vslam.pipeline.ray_runtime.stage_actors.ray.get_actor", lambda *args, **kwargs: None)
    captured: dict[str, object] = {}

    class FakeBackend:
        method_id = MethodId.MOCK

        def start_session(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(step=lambda *_args, **_kwargs: None, try_get_updates=lambda: [], close=lambda: None)

    monkeypatch.setattr(
        "prml_vslam.pipeline.ray_runtime.stage_actors.BackendFactory.build",
        lambda self, backend_spec, path_config=None: FakeBackend(),
    )
    actor = actor_cls(coordinator_name="demo", namespace="pytest-unit")
    request = RunRequest(
        experiment_name="streaming-start",
        mode=PipelineMode.STREAMING,
        output_dir=tmp_path / ".artifacts",
        source=VideoSourceSpec(video_path=Path("captures/demo.mp4")),
        slam=SlamStageConfig(backend={"kind": "mock"}),
    )
    plan = _plan_with_stages(
        tmp_path=tmp_path,
        request=request,
        stage_keys=[StageKey.INGEST, StageKey.SLAM, StageKey.SUMMARY],
    )
    sequence_manifest = SequenceManifest(sequence_id="normalized-sequence")
    benchmark_inputs = PreparedBenchmarkInputs()

    actor.start_stage(
        request=request,
        plan=plan,
        path_config=PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts"),
        session_init=SlamSessionInit(
            sequence_manifest=sequence_manifest,
            benchmark_inputs=benchmark_inputs,
            baseline_source=ReferenceSource.GROUND_TRUTH,
        ),
    )

    session_init = captured["session_init"]
    assert isinstance(session_init, SlamSessionInit)
    assert session_init.sequence_manifest == sequence_manifest
    assert session_init.benchmark_inputs == benchmark_inputs
    assert session_init.baseline_source is ReferenceSource.GROUND_TRUTH


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
    captured: dict[str, Any] = {}

    monkeypatch.setattr("prml_vslam.pipeline.backend_ray.ray.is_initialized", lambda: False)
    monkeypatch.setattr(
        backend,
        "_ensure_local_head_address",
        lambda: "127.0.0.1:25001",
    )

    def fake_init(**kwargs: Any) -> None:
        captured.update(kwargs)

    monkeypatch.setattr("prml_vslam.pipeline.backend_ray.ray.init", fake_init)

    backend._ensure_ray()

    assert captured["address"] == "127.0.0.1:25001"
    assert captured["_skip_env_hook"] is True


def test_ray_backend_keeps_inprocess_init_for_pytest_namespaces(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = RayPipelineBackend(namespace="pytest-unit")
    captured: dict[str, Any] = {}

    monkeypatch.setattr("prml_vslam.pipeline.backend_ray.ray.is_initialized", lambda: False)
    monkeypatch.setattr(
        backend,
        "_ensure_local_head_address",
        lambda: (_ for _ in ()).throw(AssertionError("should not be called")),
    )

    def fake_init(**kwargs: Any) -> None:
        captured.update(kwargs)

    monkeypatch.setattr("prml_vslam.pipeline.backend_ray.ray.init", fake_init)

    backend._ensure_ray()

    assert "address" not in captured
    assert captured["_skip_env_hook"] is True


def test_ray_backend_logs_pytest_init_path(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    backend = RayPipelineBackend(namespace="pytest-unit")
    captured: dict[str, Any] = {}

    monkeypatch.setattr("prml_vslam.pipeline.backend_ray.ray.is_initialized", lambda: False)
    monkeypatch.setattr(
        backend,
        "_ensure_local_head_address",
        lambda: (_ for _ in ()).throw(AssertionError("should not be called")),
    )

    def fake_init(**kwargs: Any) -> None:
        captured.update(kwargs)

    monkeypatch.setattr("prml_vslam.pipeline.backend_ray.ray.init", fake_init)

    with _capture_logger(
        caplog,
        monkeypatch,
        "prml_vslam.pipeline.backend_ray.RayPipelineBackend.pytest-unit",
    ):
        backend._ensure_ray()

    assert "address" not in captured
    assert any(
        "Initializing in-process Ray runtime for pytest namespace 'pytest-unit'." in r.message for r in caplog.records
    )


def test_ray_backend_reuses_healthy_local_head_metadata(tmp_path: Path) -> None:
    backend = RayPipelineBackend(
        path_config=PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts", logs_dir=tmp_path / ".logs"),
        namespace="prml_vslam.local",
    )
    backend._reuse_local_head = True
    metadata_path = backend._local_head_metadata_path()
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text('{"address": "127.0.0.1:25001", "pid": 123}', encoding="utf-8")
    backend._can_connect = lambda address: address == "127.0.0.1:25001"  # type: ignore[method-assign]

    assert backend._ensure_local_head_address() == "127.0.0.1:25001"


def test_ray_backend_replaces_stale_local_head_metadata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    backend = RayPipelineBackend(
        path_config=PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts", logs_dir=tmp_path / ".logs"),
        namespace="prml_vslam.local",
    )
    backend._reuse_local_head = True
    metadata_path = backend._local_head_metadata_path()
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text('{"address": "127.0.0.1:25001", "pid": 123}', encoding="utf-8")
    backend._can_connect = lambda address: address == "127.0.0.1:25002"  # type: ignore[method-assign]
    monkeypatch.setattr(backend, "_pick_local_head_address", lambda: "127.0.0.1:25002")
    monkeypatch.setattr(backend, "_wait_until_connectable", lambda address: address == "127.0.0.1:25002")

    class FakePopen:
        pid = 456

        def poll(self) -> None:
            return None

    monkeypatch.setattr("prml_vslam.pipeline.backend_ray.subprocess.Popen", lambda *args, **kwargs: FakePopen())

    assert backend._ensure_local_head_address() == "127.0.0.1:25002"
    assert backend._read_local_head_metadata() == {"address": "127.0.0.1:25002", "pid": 456}


def test_ray_backend_logs_stale_local_head_metadata_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    backend = RayPipelineBackend(
        path_config=PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts", logs_dir=tmp_path / ".logs"),
        namespace="prml_vslam.local",
    )
    backend._reuse_local_head = True
    metadata_path = backend._local_head_metadata_path()
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text('{"address": "127.0.0.1:25001", "pid": 123}', encoding="utf-8")
    backend._can_connect = lambda address: address == "127.0.0.1:25002"  # type: ignore[method-assign]
    monkeypatch.setattr(backend, "_pick_local_head_address", lambda: "127.0.0.1:25002")
    monkeypatch.setattr(backend, "_wait_until_connectable", lambda address: address == "127.0.0.1:25002")

    class FakePopen:
        pid = 456

        def poll(self) -> None:
            return None

    monkeypatch.setattr("prml_vslam.pipeline.backend_ray.subprocess.Popen", lambda *args, **kwargs: FakePopen())

    with _capture_logger(
        caplog,
        monkeypatch,
        "prml_vslam.pipeline.backend_ray.RayPipelineBackend.prml_vslam.local",
    ):
        assert backend._ensure_local_head_address() == "127.0.0.1:25002"

    assert any("Discarding stale local Ray head metadata." in r.message for r in caplog.records)
    assert any("Starting local Ray head on '127.0.0.1:25002'." in r.message for r in caplog.records)


def test_ray_backend_closes_parent_log_handle_after_spawn(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    backend = RayPipelineBackend(
        path_config=PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts", logs_dir=tmp_path / ".logs"),
        namespace="prml_vslam.local",
    )
    backend._reuse_local_head = True
    monkeypatch.setattr(backend, "_pick_local_head_address", lambda: "127.0.0.1:25002")
    monkeypatch.setattr(backend, "_wait_until_connectable", lambda address: address == "127.0.0.1:25002")

    captured: dict[str, Any] = {}

    class FakeLogHandle:
        def __init__(self) -> None:
            self.closed = False

        def close(self) -> None:
            self.closed = True

    class FakePopen:
        pid = 789

        def poll(self) -> None:
            return None

    fake_log_handle = FakeLogHandle()
    original_open = Path.open

    def fake_open(path: Path, *args: Any, **kwargs: Any) -> Any:
        if path.name == "ray-local-head.log":
            return fake_log_handle
        return original_open(path, *args, **kwargs)

    def fake_popen(*args: Any, **kwargs: Any) -> FakePopen:
        captured["stdout"] = kwargs["stdout"]
        return FakePopen()

    monkeypatch.setattr(Path, "open", fake_open)
    monkeypatch.setattr("prml_vslam.pipeline.backend_ray.subprocess.Popen", fake_popen)

    assert backend._ensure_local_head_address() == "127.0.0.1:25002"
    assert captured["stdout"] is fake_log_handle
    assert fake_log_handle.closed
    assert backend._read_local_head_metadata() == {"address": "127.0.0.1:25002", "pid": 789}


def test_ray_backend_preserve_shutdown_skips_local_head_termination(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = RayPipelineBackend(namespace="prml_vslam.local")
    backend._coordinators = {"run-1": object()}  # type: ignore[assignment]
    shutdowns: list[str] = []

    monkeypatch.setattr("prml_vslam.pipeline.backend_ray.ray.is_initialized", lambda: True)
    monkeypatch.setattr(backend, "_shutdown_run", lambda run_id: shutdowns.append(run_id))
    monkeypatch.setattr("prml_vslam.pipeline.backend_ray.ray.shutdown", lambda: shutdowns.append("ray"))
    monkeypatch.setattr(backend, "_shutdown_local_head", lambda: shutdowns.append("head"))

    backend.shutdown(preserve_local_head=True)

    assert shutdowns == ["run-1", "ray"]


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
    submitted: list[tuple[str, str | None]] = []
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


def test_ray_backend_submit_run_rejects_unavailable_stage_after_planning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path_config = PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts")
    backend = RayPipelineBackend(path_config=path_config, namespace="pytest-unit")
    request = RunRequest(
        experiment_name="placeholder",
        mode=PipelineMode.OFFLINE,
        output_dir=path_config.artifacts_dir,
        source=DatasetSourceSpec(
            dataset_id="advio",
            sequence_id="advio-01",
            dataset_serving={
                "dataset_id": "advio",
                "pose_source": "ground_truth",
                "pose_frame_mode": "provider_world",
            },
        ),
        slam=SlamStageConfig(backend={"kind": "mock"}, outputs={"emit_dense_points": True}),
        benchmark=BenchmarkConfig(cloud=CloudBenchmarkConfig(enabled=True)),
    )
    created_runs: list[str] = []

    monkeypatch.setattr(backend, "_ensure_ray", lambda: None)
    monkeypatch.setattr(backend, "_create_coordinator", lambda run_id: created_runs.append(run_id))

    with pytest.raises(RuntimeError, match="placeholder"):
        backend.submit_run(request=request)

    assert created_runs == []


def test_source_resolver_logs_video_resolution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    path_config = PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts")
    video_path = tmp_path / "resolver-demo.mp4"
    video_path.write_bytes(b"")
    resolver = OfflineSourceResolver(path_config)

    with _capture_logger(
        caplog,
        monkeypatch,
        "prml_vslam.pipeline.source_resolver.OfflineSourceResolver",
    ):
        resolved = resolver.resolve(VideoSourceSpec(video_path=video_path))

    assert resolved.label == "Video 'resolver-demo.mp4'"
    assert any("Resolved video offline source" in r.message for r in caplog.records)
    assert any("Resolved video path to" in r.message for r in caplog.records)


def test_materialize_offline_manifest_logs_cache_hit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    artifact_root = tmp_path / "artifacts"
    run_paths = RunArtifactPaths.build(artifact_root)
    run_paths.input_frames_dir.mkdir(parents=True, exist_ok=True)
    video_path = tmp_path / "captures" / "demo.mp4"
    video_path.parent.mkdir(parents=True, exist_ok=True)
    video_path.write_bytes(b"")
    (run_paths.input_frames_dir / "000000.png").write_bytes(b"png")
    (run_paths.input_frames_dir / ".ingest_metadata.json").write_text(
        f'{{"video_path": "{video_path.resolve()}", "frame_stride": 1, "max_frames": null}}',
        encoding="utf-8",
    )
    request = RunRequest(
        experiment_name="ingest-cache",
        mode=PipelineMode.OFFLINE,
        output_dir=tmp_path / ".artifacts",
        source=VideoSourceSpec(video_path=video_path, frame_stride=1),
        slam=SlamStageConfig(backend={"kind": "mock"}),
    )
    prepared_manifest = SequenceManifest(sequence_id="ingest-cache", video_path=video_path)

    with _capture_logger(
        caplog,
        monkeypatch,
        "prml_vslam.pipeline.ingest.materialize_offline_manifest",
    ):
        manifest = materialize_offline_manifest(
            request=request,
            prepared_manifest=prepared_manifest,
            run_paths=run_paths,
        )

    assert manifest.rgb_dir == run_paths.input_frames_dir.resolve()
    assert any("Materializing offline manifest for sequence 'ingest-cache'." in r.message for r in caplog.records)
    assert any("Reusing extracted frames" in r.message for r in caplog.records)


def test_run_coordinator_logs_stage_start_and_completion(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    coordinator_cls = RunCoordinatorActor.__ray_metadata__.modified_class
    coordinator = coordinator_cls(run_id="demo", namespace="pytest-unit")
    outcome = StageOutcome(
        stage_key=StageKey.SLAM,
        status=StageStatus.COMPLETED,
        config_hash="cfg",
        input_fingerprint="input",
        artifacts={},
    )

    with _capture_logger(
        caplog,
        monkeypatch,
        "prml_vslam.pipeline.ray_runtime.coordinator.RunCoordinatorActor.demo",
    ):
        coordinator._emit_stage_started(StageKey.SLAM)
        coordinator._record_stage_completion(
            StageKey.SLAM,
            SimpleNamespace(
                outcome=outcome,
                sequence_manifest=None,
                benchmark_inputs=None,
                slam=None,
                ground_alignment=None,
                visualization=None,
                summary=None,
                stage_manifests=[],
            ),
        )

    assert any("Stage 'slam' started for run 'demo'." in r.message for r in caplog.records)
    assert any(
        "Stage 'slam' finished for run 'demo' with status 'completed' and 0 artifacts." in r.message
        for r in caplog.records
    )


def test_packet_source_actor_logs_start_and_eof(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    events: list[str] = []

    class _Remote:
        def __init__(self, fn):
            self.remote = fn

    fake_coordinator = SimpleNamespace(
        on_packet=_Remote(lambda **kwargs: events.append("packet")),
        on_source_eof=_Remote(lambda: events.append("eof")),
        on_source_error=_Remote(lambda message: events.append(f"error:{message}")),
    )

    actor_cls = PacketSourceActor.__ray_metadata__.modified_class
    actor = object.__new__(actor_cls)
    actor._console = Console("prml_vslam.pipeline.ray_runtime.stage_actors").child("PacketSourceActor").child("demo")
    actor._coordinator = fake_coordinator
    actor._frame_timeout_seconds = 5.0
    actor._thread = None
    actor._stop_event = threading.Event()
    actor._credits = 0
    actor._credits_cv = threading.Condition()
    actor._received_frames = 0
    actor._packet_timestamps = deque(maxlen=20)
    monkeypatch.setattr(
        "prml_vslam.pipeline.ray_runtime.stage_actors.put_array_handle",
        lambda array: (SimpleNamespace(handle_id="frame"), np.asarray(array)),
    )

    with _capture_logger(
        caplog,
        monkeypatch,
        "prml_vslam.pipeline.ray_runtime.stage_actors.PacketSourceActor.demo",
    ):
        actor.start_stream(source=FakeStreamingSource(), initial_credits=4, loop=False)
        actor._thread.join(timeout=5.0)

    assert events[-1] == "eof"
    assert any("Starting packet stream for source 'fake-stream'" in r.message for r in caplog.records)
    assert any("Streaming source reached EOF." in r.message for r in caplog.records)


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


def _plan_with_stages(
    *,
    tmp_path: Path,
    request: RunRequest,
    stage_keys: list[StageKey],
) -> RunPlan:
    return RunPlan(
        run_id=request.experiment_name,
        mode=request.mode,
        artifact_root=tmp_path / request.experiment_name,
        source=request.source,
        stages=[
            RunPlanStage(
                key=stage_key,
            )
            for stage_key in stage_keys
        ],
    )


def _placement_request(*, placement: dict[str, dict[str, dict[str, float]]] | None = None) -> RunRequest:
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
