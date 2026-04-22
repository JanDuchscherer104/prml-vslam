"""Focused tests for the Ray-backed pipeline core."""

from __future__ import annotations

import json
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
from prml_vslam.interfaces import (
    FramePacketProvenance,
    FrameTransform,
    RgbdObservationIndexEntry,
    RgbdObservationProvenance,
    RgbdObservationSequenceIndex,
    RgbdObservationSequenceRef,
)
from prml_vslam.interfaces.ingest import PreparedBenchmarkInputs, SequenceManifest, SourceStageOutput
from prml_vslam.interfaces.slam import (
    ArtifactRef,
    BackendWarning,
    KeyframeVisualizationReady,
    PoseEstimated,
    SlamArtifacts,
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
    RunStopped,
    StageCompleted,
    StageFailed,
    StageOutcome,
    StageStatus,
)
from prml_vslam.pipeline.contracts.handles import ArrayHandle
from prml_vslam.pipeline.contracts.plan import RunPlan, RunPlanStage
from prml_vslam.pipeline.contracts.provenance import RunSummary
from prml_vslam.pipeline.contracts.request import (
    DatasetSourceSpec,
    SlamStageConfig,
    VideoSourceSpec,
    build_run_request,
)
from prml_vslam.pipeline.contracts.runtime import RunSnapshot, RunState
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.execution_context import StageExecutionContext
from prml_vslam.pipeline.finalization import stable_hash
from prml_vslam.pipeline.ingest import _max_frames_for_request, materialize_offline_manifest
from prml_vslam.pipeline.placement import actor_options_for_stage
from prml_vslam.pipeline.ray_runtime.common import backend_config_payload, clean_actor_options
from prml_vslam.pipeline.ray_runtime.coordinator import RunCoordinatorActor
from prml_vslam.pipeline.ray_runtime.stage_actors import PacketSourceActor
from prml_vslam.pipeline.run_service import RunService
from prml_vslam.pipeline.runner import StageRunner
from prml_vslam.pipeline.runtime_manager import RuntimeManager
from prml_vslam.pipeline.snapshot_projector import SnapshotProjector
from prml_vslam.pipeline.source_resolver import OfflineSourceResolver
from prml_vslam.pipeline.stage_registry import StageRegistry
from prml_vslam.pipeline.stages.base.contracts import (
    StageResult,
    StageRuntimeStatus,
    StageRuntimeUpdate,
    VisualizationIntent,
    VisualizationItem,
)
from prml_vslam.pipeline.stages.base.handles import TransientPayloadRef
from prml_vslam.pipeline.stages.base.proxy import RuntimeCapability
from prml_vslam.pipeline.stages.reconstruction import ReconstructionRuntime, ReconstructionRuntimeInput
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

[source.dataset_serving]
dataset_id = "advio"
pose_source = "ground_truth"
pose_frame_mode = "provider_world"

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

[source.dataset_serving]
dataset_id = "advio"
pose_source = "ground_truth"
pose_frame_mode = "provider_world"

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


def test_stage_registry_allows_tum_rgbd_reference_reconstruction(tmp_path: Path) -> None:
    path_config = PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts")
    request = RunRequest(
        experiment_name="tum-reference",
        mode=PipelineMode.OFFLINE,
        output_dir=path_config.artifacts_dir,
        source=DatasetSourceSpec(dataset_id="tum_rgbd", sequence_id="freiburg1_desk"),
        slam=SlamStageConfig(backend={"kind": "mock"}),
        benchmark=BenchmarkConfig(reference={"enabled": True}),
    )

    plan = StageRegistry.default().compile(
        request=request,
        backend=BackendFactory().describe(request.slam.backend),
        path_config=path_config,
    )

    reference_stage = next(stage for stage in plan.stages if stage.key is StageKey.REFERENCE_RECONSTRUCTION)
    assert reference_stage.available is True
    assert reference_stage.outputs == [RunArtifactPaths.build(plan.artifact_root).reference_cloud_path]


def test_stage_registry_rejects_non_rgbd_reference_reconstruction(tmp_path: Path) -> None:
    path_config = PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts")
    request = RunRequest(
        experiment_name="video-reference",
        mode=PipelineMode.OFFLINE,
        output_dir=path_config.artifacts_dir,
        source=VideoSourceSpec(video_path=Path("captures/demo.mp4")),
        slam=SlamStageConfig(backend={"kind": "mock"}),
        benchmark=BenchmarkConfig(reference={"enabled": True}),
    )

    plan = StageRegistry.default().compile(
        request=request,
        backend=BackendFactory().describe(request.slam.backend),
        path_config=path_config,
    )

    reference_stage = next(stage for stage in plan.stages if stage.key is StageKey.REFERENCE_RECONSTRUCTION)
    assert reference_stage.available is False
    assert (
        reference_stage.availability_reason == "Reference reconstruction currently requires a TUM RGB-D dataset source."
    )


def test_reference_reconstruction_stage_writes_cloud_and_metadata(tmp_path: Path) -> None:
    pytest.importorskip("open3d")
    request = RunRequest(
        experiment_name="reference-stage",
        mode=PipelineMode.OFFLINE,
        output_dir=tmp_path / ".artifacts",
        source=DatasetSourceSpec(dataset_id="tum_rgbd", sequence_id="freiburg1_desk"),
        slam=SlamStageConfig(backend={"kind": "mock"}),
        benchmark=BenchmarkConfig(reference={"enabled": True, "extract_mesh": True}),
    )
    plan = _plan_with_stages(
        tmp_path=tmp_path,
        request=request,
        stage_keys=[StageKey.REFERENCE_RECONSTRUCTION],
    )
    context = StageExecutionContext(
        request=request,
        plan=plan,
        path_config=PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts"),
        run_paths=RunArtifactPaths.build(plan.artifact_root),
        backend_descriptor=BackendFactory().describe(request.slam.backend),
    )
    benchmark_inputs = _rgbd_benchmark_inputs(tmp_path)

    result = ReconstructionRuntime().run_offline(
        ReconstructionRuntimeInput(
            request=request,
            run_paths=context.run_paths,
            benchmark_inputs=benchmark_inputs,
        )
    )

    assert result.outcome.stage_key is StageKey.REFERENCE_RECONSTRUCTION
    assert result.outcome.status is StageStatus.COMPLETED
    assert result.outcome.artifacts["reference_cloud"].path.exists()
    assert result.outcome.artifacts["reconstruction_metadata"].path.exists()
    assert result.outcome.artifacts["reference_mesh"].path.exists()
    assert result.outcome.metrics["observation_count"] == 1


def test_snapshot_projector_preserves_stopped_preview_handle() -> None:
    projector = SnapshotProjector()
    snapshot = RunSnapshot(run_id="run-1", state=RunState.STOPPED)

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
    assert updated.stage_runtime_status[StageKey.INGEST].processed_items == 1
    assert updated.stage_runtime_status[StageKey.INGEST].fps == 12.0


def test_snapshot_projector_preserves_completed_state_on_run_stopped() -> None:
    projector = SnapshotProjector()
    snapshot = RunSnapshot(run_id="run-1", state=RunState.COMPLETED)

    updated = projector.apply(
        snapshot,
        RunStopped(event_id="2", run_id="run-1", ts_ns=2),
    )

    assert updated.state is RunState.COMPLETED


def test_snapshot_projector_copies_only_mutated_runtime_containers() -> None:
    projector = SnapshotProjector()
    snapshot = RunSnapshot(
        run_id="run-1",
        state=RunState.RUNNING,
        stage_runtime_status={
            StageKey.INGEST: StageRuntimeStatus(
                stage_key=StageKey.INGEST,
                lifecycle_state=StageStatus.RUNNING,
                progress_message="streaming",
            )
        },
        artifacts={"before": ArtifactRef(path=Path("/tmp/before"), kind="txt", fingerprint="before")},
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

    assert updated.stage_runtime_status == snapshot.stage_runtime_status
    assert updated.artifacts == snapshot.artifacts
    assert updated.stage_runtime_status is not snapshot.stage_runtime_status
    assert updated.artifacts is not snapshot.artifacts


def test_snapshot_projector_clears_current_stage_on_stage_failed() -> None:
    projector = SnapshotProjector()
    snapshot = RunSnapshot(
        run_id="run-1",
        state=RunState.RUNNING,
        current_stage_key=StageKey.SLAM,
        stage_runtime_status={
            StageKey.SLAM: StageRuntimeStatus(stage_key=StageKey.SLAM, lifecycle_state=StageStatus.RUNNING)
        },
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
    assert StageKey.SLAM not in updated.stage_runtime_status
    assert updated.error_message == "boom"
    assert updated.stage_outcomes[StageKey.SLAM].status is StageStatus.FAILED


def test_snapshot_projector_projects_stage_completed_into_target_keyed_fields() -> None:
    projector = SnapshotProjector()
    outcome = StageOutcome(
        stage_key=StageKey.SLAM,
        status=StageStatus.COMPLETED,
        config_hash="cfg",
        input_fingerprint="inp",
        artifacts={"trajectory": ArtifactRef(path=Path("/tmp/traj.tum"), kind="tum", fingerprint="traj")},
    )

    updated = projector.apply(
        RunSnapshot(run_id="run-1"),
        StageCompleted(event_id="4", run_id="run-1", ts_ns=4, stage_key=StageKey.SLAM, outcome=outcome),
    )

    assert updated.stage_outcomes[StageKey.SLAM] == outcome
    assert updated.stage_status[StageKey.SLAM] is StageStatus.COMPLETED
    assert updated.artifacts["trajectory"] == outcome.artifacts["trajectory"]


def test_snapshot_projector_applies_runtime_update_to_target_and_compat_fields() -> None:
    projector = SnapshotProjector()
    ref = TransientPayloadRef(handle_id="payload-1", payload_kind="image", shape=(2, 2, 3), dtype="uint8")
    update = StageRuntimeUpdate(
        stage_key=StageKey.SLAM,
        timestamp_ns=10,
        semantic_events=[
            SlamUpdate(
                seq=1,
                timestamp_ns=10,
                source_seq=1,
                is_keyframe=True,
                keyframe_index=2,
                pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=2.0, tz=3.0),
                num_sparse_points=4,
                num_dense_points=5,
            )
        ],
        visualizations=[
            VisualizationItem(
                intent=VisualizationIntent.RGB_IMAGE,
                role="model_rgb",
                payload_refs={"image": ref},
                frame_index=1,
                keyframe_index=2,
            )
        ],
        runtime_status=StageRuntimeStatus(
            stage_key=StageKey.SLAM,
            lifecycle_state=StageStatus.RUNNING,
            progress_message="running",
            completed_steps=1,
            progress_unit="frames",
        ),
    )

    updated = projector.apply_runtime_update(RunSnapshot(run_id="run-1"), update)

    assert updated.stage_runtime_status[StageKey.SLAM] == update.runtime_status
    assert updated.stage_status[StageKey.SLAM] is StageStatus.RUNNING
    assert updated.stage_progress[StageKey.SLAM].message == "running"
    assert updated.live_refs[StageKey.SLAM]["model_rgb:image"] == ref


def test_snapshot_projector_runtime_update_preserves_terminal_states() -> None:
    projector = SnapshotProjector()
    update = StageRuntimeUpdate(
        stage_key=StageKey.SLAM,
        timestamp_ns=10,
        runtime_status=StageRuntimeStatus(stage_key=StageKey.SLAM, lifecycle_state=StageStatus.RUNNING),
    )

    completed = projector.apply_runtime_update(RunSnapshot(run_id="run-1", state=RunState.COMPLETED), update)
    failed = projector.apply_runtime_update(RunSnapshot(run_id="run-1", state=RunState.FAILED), update)
    stopped = projector.apply_runtime_update(RunSnapshot(run_id="run-1", state=RunState.STOPPED), update)

    assert completed.state is RunState.COMPLETED
    assert failed.state is RunState.FAILED
    assert stopped.state is RunState.STOPPED


def test_snapshot_projector_runtime_update_skips_empty_progress_projection() -> None:
    projector = SnapshotProjector()
    snapshot = RunSnapshot(
        run_id="run-1",
        stage_runtime_status={
            StageKey.SLAM: StageRuntimeStatus(
                stage_key=StageKey.SLAM,
                lifecycle_state=StageStatus.RUNNING,
                progress_message="old",
            )
        },
    )
    update = StageRuntimeUpdate(
        stage_key=StageKey.SLAM,
        timestamp_ns=10,
        runtime_status=StageRuntimeStatus(stage_key=StageKey.SLAM, lifecycle_state=StageStatus.RUNNING),
    )

    updated = projector.apply_runtime_update(snapshot, update)

    assert StageKey.SLAM not in updated.stage_progress
    assert snapshot.stage_progress[StageKey.SLAM].message == "old"


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


def test_run_coordinator_applies_slam_runtime_updates_to_snapshot() -> None:
    coordinator_cls = RunCoordinatorActor.__ray_metadata__.modified_class
    coordinator = coordinator_cls(run_id="run-1", namespace="pytest-unit")
    coordinator._snapshot = RunSnapshot(run_id="run-1")
    ref = TransientPayloadRef(handle_id="payload-1", payload_kind="image", shape=(2, 2, 3), dtype="uint8")
    update = StageRuntimeUpdate(
        stage_key=StageKey.SLAM,
        timestamp_ns=1,
        visualizations=[
            VisualizationItem(
                intent=VisualizationIntent.RGB_IMAGE,
                role="model_rgb",
                payload_refs={"image": ref},
                frame_index=1,
            )
        ],
        runtime_status=StageRuntimeStatus(stage_key=StageKey.SLAM, lifecycle_state=StageStatus.RUNNING),
    )

    coordinator.on_slam_runtime_updates(updates=[update])

    snapshot = coordinator.snapshot()
    assert snapshot.stage_runtime_status[StageKey.SLAM] == update.runtime_status
    assert snapshot.stage_status[StageKey.SLAM] is StageStatus.RUNNING
    assert snapshot.live_refs[StageKey.SLAM]["model_rgb:image"] == ref


def test_run_coordinator_can_record_backend_notices_without_snapshot_projection() -> None:
    coordinator_cls = RunCoordinatorActor.__ray_metadata__.modified_class
    coordinator = coordinator_cls(run_id="run-1", namespace="pytest-unit")
    coordinator._snapshot = RunSnapshot(run_id="run-1")

    coordinator.on_slam_notices(
        notices=[
            PoseEstimated(
                seq=1,
                timestamp_ns=10,
                pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=2.0, tz=3.0),
            )
        ],
        bindings=[],
        released_credits=0,
        project_to_snapshot=False,
    )

    snapshot = coordinator.snapshot()
    assert snapshot.stage_runtime_status == {}
    assert any(isinstance(event, BackendNoticeReceived) for event in coordinator.events())


def test_run_coordinator_submits_source_rgb_runtime_update_without_hot_path_ray_get(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coordinator_cls = RunCoordinatorActor.__ray_metadata__.modified_class
    coordinator = coordinator_cls(run_id="demo", namespace="pytest-unit")
    submitted: list[tuple[StageRuntimeUpdate, object]] = []

    class FakeObserveUpdateRemote:
        def remote(self, *, update: StageRuntimeUpdate, payload_resolver: object) -> str:
            submitted.append((update, payload_resolver))
            return "rerun-call-1"

    coordinator._rerun_sink = SimpleNamespace(observe_update=FakeObserveUpdateRemote())
    coordinator._request = SimpleNamespace(visualization=SimpleNamespace(log_source_rgb=True))
    monkeypatch.setattr(coordinator, "_self_actor_handle", lambda: "resolver")
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
    assert submitted[0][0].stage_key is StageKey.INGEST
    assert submitted[0][1] == "resolver"
    assert coordinator._rerun_sink_last_call == "rerun-call-1"


def test_run_coordinator_routes_reconstruction_runtime_updates_without_payload_resolver() -> None:
    coordinator_cls = RunCoordinatorActor.__ray_metadata__.modified_class
    coordinator = coordinator_cls(run_id="demo", namespace="pytest-unit")
    submitted: list[tuple[StageRuntimeUpdate, Any]] = []
    update = StageRuntimeUpdate(
        stage_key=StageKey.REFERENCE_RECONSTRUCTION,
        timestamp_ns=1,
        runtime_status=StageRuntimeStatus(
            stage_key=StageKey.REFERENCE_RECONSTRUCTION,
            lifecycle_state=StageStatus.COMPLETED,
        ),
        visualizations=[
            VisualizationItem(
                intent=VisualizationIntent.POINT_CLOUD,
                role="reconstruction_point_cloud",
            )
        ],
    )

    class FakeObserveUpdateRemote:
        def remote(self, *, update: StageRuntimeUpdate, payload_resolver: Any) -> str:
            submitted.append((update, payload_resolver))
            return "rerun-call-1"

    class FakeReconstructionRuntime:
        def __init__(self) -> None:
            self.drained = False

        def status(self) -> StageRuntimeStatus:
            return StageRuntimeStatus(stage_key=StageKey.REFERENCE_RECONSTRUCTION)

        def stop(self) -> None:
            return None

        def run_offline(self, input_payload) -> StageResult:
            del input_payload
            raise AssertionError("routing test should not run the stage")

        def drain_runtime_updates(self, max_items: int | None = None) -> list[StageRuntimeUpdate]:
            del max_items
            if self.drained:
                return []
            self.drained = True
            return [update]

    runtime_manager = RuntimeManager()
    runtime_manager.register(
        StageKey.REFERENCE_RECONSTRUCTION,
        factory=FakeReconstructionRuntime,
        capabilities=frozenset({RuntimeCapability.OFFLINE, RuntimeCapability.LIVE_UPDATES}),
    )
    runtime_proxy = runtime_manager.runtime_for(StageKey.REFERENCE_RECONSTRUCTION)
    coordinator._rerun_sink = SimpleNamespace(observe_update=FakeObserveUpdateRemote())

    coordinator._publish_runtime_updates_from_proxy(runtime_proxy)

    assert submitted == [(update, None)]
    assert coordinator._rerun_sink_last_call == "rerun-call-1"
    assert (
        coordinator.snapshot().stage_runtime_status[StageKey.REFERENCE_RECONSTRUCTION].lifecycle_state
        is StageStatus.COMPLETED
    )
    assert runtime_proxy.live_updates().drain_runtime_updates() == []


def test_run_coordinator_runtime_manager_registers_reconstruction_live_updates(tmp_path: Path) -> None:
    coordinator_cls = RunCoordinatorActor.__ray_metadata__.modified_class
    coordinator = coordinator_cls(run_id="demo", namespace="pytest-unit")
    request = RunRequest(
        experiment_name="demo",
        mode=PipelineMode.OFFLINE,
        output_dir=tmp_path / ".artifacts",
        source=VideoSourceSpec(video_path=Path("captures/demo.mp4")),
        slam=SlamStageConfig(backend={"kind": "mock"}),
    )
    plan = _plan_with_stages(
        tmp_path=tmp_path,
        request=request,
        stage_keys=[StageKey.REFERENCE_RECONSTRUCTION],
    )

    runtime_manager = coordinator._build_runtime_manager(plan=plan, source=FakeOfflineSource())
    runtime_proxy = runtime_manager.runtime_for(StageKey.REFERENCE_RECONSTRUCTION)

    assert RuntimeCapability.OFFLINE in runtime_proxy.supported_capabilities
    assert RuntimeCapability.LIVE_UPDATES in runtime_proxy.supported_capabilities


def test_run_coordinator_releases_streaming_credit_before_update_observer_routing() -> None:
    coordinator_cls = RunCoordinatorActor.__ray_metadata__.modified_class
    coordinator = coordinator_cls(run_id="demo", namespace="pytest-unit")
    call_order: list[str] = []
    credits: list[int] = []

    class _FakeStreamingRuntime:
        def status(self) -> StageRuntimeStatus:
            return StageRuntimeStatus(stage_key=StageKey.SLAM, lifecycle_state=StageStatus.RUNNING)

        def stop(self) -> None:
            return None

        def start_streaming(self, input_payload) -> None:
            del input_payload

        def submit_stream_item(self, item) -> None:
            del item

        def drain_runtime_updates(self, max_items: int | None = None) -> list[StageRuntimeUpdate]:
            del max_items
            return [
                StageRuntimeUpdate(
                    stage_key=StageKey.SLAM,
                    timestamp_ns=1,
                    runtime_status=StageRuntimeStatus(stage_key=StageKey.SLAM, lifecycle_state=StageStatus.RUNNING),
                )
            ]

        def finish_streaming(self) -> StageResult:
            raise AssertionError("finish_streaming should not be called in this test")

    runtime_manager = RuntimeManager()
    runtime_manager.register(
        StageKey.SLAM,
        factory=_FakeStreamingRuntime,
        capabilities=frozenset({RuntimeCapability.LIVE_UPDATES, RuntimeCapability.STREAMING}),
    )
    coordinator._slam_runtime_proxy = runtime_manager.runtime_for(StageKey.SLAM)
    coordinator._source_actor = SimpleNamespace(
        grant_credit=SimpleNamespace(remote=lambda count: call_order.append("credit") or credits.append(count)),
    )

    def _fail_update_routing(*, updates: list[StageRuntimeUpdate]) -> None:
        del updates
        call_order.append("updates")
        raise RuntimeError("observer routing failed")

    coordinator.on_slam_runtime_updates = _fail_update_routing

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

    assert credits == [1]
    assert call_order == ["credit", "updates"]
    assert coordinator._in_flight_frames == 0
    assert coordinator._streaming_error is None


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
        "prml_vslam.pipeline.ray_runtime.coordinator.SourceRuntime.run_offline",
        lambda self, input_payload: (_ for _ in ()).throw(RuntimeError("ingest boom")),
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


def test_run_coordinator_offline_dispatches_batch_stage_executors(tmp_path: Path) -> None:
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
    coordinator._backend_descriptor = _test_backend_descriptor(default_cpu=1.0, default_gpu=0.0)

    coordinator._run_offline(
        request=request,
        plan=plan,
        path_config=path_config,
        runtime_source=FakeOfflineSource(),
    )

    snapshot = coordinator.snapshot()
    assert snapshot.stage_outcomes[StageKey.INGEST].status is StageStatus.COMPLETED
    assert snapshot.stage_outcomes[StageKey.SLAM].status is StageStatus.COMPLETED
    assert snapshot.stage_outcomes[StageKey.SUMMARY].status is StageStatus.COMPLETED
    assert "trajectory_tum" in snapshot.artifacts
    assert "run_summary" in snapshot.artifacts
    assert snapshot.state is RunState.COMPLETED


def test_run_coordinator_finalize_streaming_dispatches_batch_executors(tmp_path: Path) -> None:
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
    calls: list[str] = []

    class _FakeSlamRuntime:
        def status(self) -> StageRuntimeStatus:
            return StageRuntimeStatus(stage_key=StageKey.SLAM, lifecycle_state=StageStatus.RUNNING)

        def stop(self) -> None:
            return None

        def start_streaming(self, input_payload) -> None:
            del input_payload

        def submit_stream_item(self, item) -> None:
            del item

        def drain_runtime_updates(self, max_items: int | None = None) -> list[StageRuntimeUpdate]:
            del max_items
            return []

        def finish_streaming(self) -> StageResult:
            calls.append("slam.finish")
            return StageResult(
                stage_key=StageKey.SLAM,
                payload=slam_artifacts,
                outcome=StageOutcome(
                    stage_key=StageKey.SLAM,
                    status=StageStatus.COMPLETED,
                    config_hash="slam",
                    input_fingerprint="slam",
                    artifacts={"trajectory_tum": slam_artifacts.trajectory_tum},
                ),
                final_runtime_status=StageRuntimeStatus(
                    stage_key=StageKey.SLAM,
                    lifecycle_state=StageStatus.COMPLETED,
                ),
            )

    class _FakeTrajectoryRuntime:
        def status(self) -> StageRuntimeStatus:
            return StageRuntimeStatus(stage_key=StageKey.TRAJECTORY_EVALUATION, lifecycle_state=StageStatus.RUNNING)

        def stop(self) -> None:
            return None

        def run_offline(self, input_payload) -> StageResult:
            assert input_payload.sequence_manifest == sequence_manifest
            assert input_payload.benchmark_inputs is None
            assert input_payload.slam == slam_artifacts
            calls.append("trajectory")
            return StageResult(
                stage_key=StageKey.TRAJECTORY_EVALUATION,
                payload=None,
                outcome=StageOutcome(
                    stage_key=StageKey.TRAJECTORY_EVALUATION,
                    status=StageStatus.COMPLETED,
                    config_hash="trajectory",
                    input_fingerprint="trajectory",
                ),
                final_runtime_status=StageRuntimeStatus(
                    stage_key=StageKey.TRAJECTORY_EVALUATION,
                    lifecycle_state=StageStatus.COMPLETED,
                ),
            )

    class _FakeSummaryRuntime:
        def status(self) -> StageRuntimeStatus:
            return StageRuntimeStatus(stage_key=StageKey.SUMMARY, lifecycle_state=StageStatus.RUNNING)

        def stop(self) -> None:
            return None

        def run_offline(self, input_payload) -> StageResult:
            calls.append("summary")
            assert [outcome.stage_key for outcome in input_payload.stage_outcomes] == [
                StageKey.INGEST,
                StageKey.SLAM,
                StageKey.TRAJECTORY_EVALUATION,
            ]
            return StageResult(
                stage_key=StageKey.SUMMARY,
                payload=RunSummary(
                    run_id=input_payload.plan.run_id,
                    artifact_root=input_payload.plan.artifact_root,
                    stage_status={
                        StageKey.INGEST: StageStatus.COMPLETED,
                        StageKey.SLAM: StageStatus.COMPLETED,
                        StageKey.TRAJECTORY_EVALUATION: StageStatus.COMPLETED,
                    },
                ),
                outcome=StageOutcome(
                    stage_key=StageKey.SUMMARY,
                    status=StageStatus.COMPLETED,
                    config_hash="summary",
                    input_fingerprint="summary",
                ),
                final_runtime_status=StageRuntimeStatus(
                    stage_key=StageKey.SUMMARY,
                    lifecycle_state=StageStatus.COMPLETED,
                ),
            )

    runtime_manager = RuntimeManager()
    slam_runtime = _FakeSlamRuntime()
    runtime_manager.register(
        StageKey.SLAM,
        factory=lambda: slam_runtime,
        capabilities=frozenset({RuntimeCapability.LIVE_UPDATES, RuntimeCapability.STREAMING}),
    )
    runtime_manager.register(
        StageKey.TRAJECTORY_EVALUATION,
        factory=_FakeTrajectoryRuntime,
        capabilities=frozenset({RuntimeCapability.OFFLINE}),
    )
    runtime_manager.register(
        StageKey.SUMMARY,
        factory=_FakeSummaryRuntime,
        capabilities=frozenset({RuntimeCapability.OFFLINE}),
    )
    coordinator._request = request
    coordinator._plan = plan
    coordinator._path_config = path_config
    coordinator._backend_descriptor = _test_backend_descriptor(default_cpu=1.0, default_gpu=0.0)
    coordinator._snapshot = RunSnapshot(run_id=plan.run_id, plan=plan, active_executor="ray")
    coordinator._streaming_runtime_manager = runtime_manager
    coordinator._slam_runtime_proxy = runtime_manager.runtime_for(StageKey.SLAM)
    coordinator._result_store.put(
        StageResult(
            stage_key=StageKey.INGEST,
            payload=SourceStageOutput(sequence_manifest=sequence_manifest, benchmark_inputs=None),
            outcome=StageOutcome(
                stage_key=StageKey.INGEST,
                status=StageStatus.COMPLETED,
                config_hash="ingest",
                input_fingerprint="ingest",
            ),
            final_runtime_status=StageRuntimeStatus(
                stage_key=StageKey.INGEST,
                lifecycle_state=StageStatus.COMPLETED,
            ),
        )
    )
    coordinator._stage_runner = StageRunner(coordinator._result_store)

    coordinator._finalize_streaming()

    assert calls == ["slam.finish", "trajectory", "summary"]
    snapshot = coordinator.snapshot()
    assert snapshot.stage_outcomes[StageKey.SLAM].artifacts["trajectory_tum"] == slam_artifacts.trajectory_tum
    assert snapshot.artifacts["trajectory_tum"] == slam_artifacts.trajectory_tum
    assert snapshot.state is RunState.COMPLETED


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
            "source": {
                "dataset_id": "advio",
                "sequence_id": "advio-01",
                "dataset_serving": {
                    "dataset_id": "advio",
                    "pose_source": "ground_truth",
                    "pose_frame_mode": "provider_world",
                },
            },
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
            "read_payload": _Remote(lambda handle_id: np.full((2, 2, 3), 2, dtype=np.uint8)),
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
    assert backend.read_payload(run_id, TransientPayloadRef(handle_id="payload", payload_kind="image")) is not None
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


def test_source_resolver_delegates_video_resolution(tmp_path: Path) -> None:
    path_config = PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts")
    video_path = tmp_path / "resolver-demo.mp4"
    video_path.write_bytes(b"")
    resolver = OfflineSourceResolver(path_config)

    resolved = resolver.resolve(VideoSourceSpec(video_path=video_path))

    assert resolved.label == "Video 'resolver-demo.mp4'"


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


def test_materialize_offline_manifest_normalizes_tum_rgbd_timestamps(tmp_path: Path) -> None:
    artifact_root = tmp_path / "artifacts"
    run_paths = RunArtifactPaths.build(artifact_root)
    rgb_dir = tmp_path / "rgb"
    rgb_dir.mkdir(parents=True)
    timestamps_path = tmp_path / "rgb.txt"
    timestamps_path.write_text(
        "\n".join(
            [
                "# color images",
                "# timestamp filename",
                "0.000000000 rgb/000000.png",
                "0.200000000 rgb/000001.png",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    request = RunRequest(
        experiment_name="tum-ingest",
        mode=PipelineMode.OFFLINE,
        output_dir=tmp_path / ".artifacts",
        source=DatasetSourceSpec(dataset_id="tum_rgbd", sequence_id="freiburg1_room"),
        slam=SlamStageConfig(backend={"kind": "mock"}),
    )
    prepared_manifest = SequenceManifest(
        sequence_id="freiburg1_room",
        rgb_dir=rgb_dir,
        timestamps_path=timestamps_path,
    )

    manifest = materialize_offline_manifest(
        request=request,
        prepared_manifest=prepared_manifest,
        run_paths=run_paths,
    )

    assert manifest.timestamps_path == run_paths.input_timestamps_path.resolve()
    payload = json.loads(manifest.timestamps_path.read_text(encoding="utf-8"))
    assert payload == {"frame_stride": 1, "timestamps_ns": [0, 200_000_000]}


def test_materialize_offline_manifest_normalizes_advio_csv_timestamps(tmp_path: Path) -> None:
    artifact_root = tmp_path / "artifacts"
    run_paths = RunArtifactPaths.build(artifact_root)
    rgb_dir = tmp_path / "rgb"
    rgb_dir.mkdir(parents=True)
    timestamps_path = tmp_path / "frames.csv"
    timestamps_path.write_text("0.000000000,1\n0.100000000,2\n", encoding="utf-8")
    request = RunRequest(
        experiment_name="advio-ingest",
        mode=PipelineMode.OFFLINE,
        output_dir=tmp_path / ".artifacts",
        source=DatasetSourceSpec(
            dataset_id="advio",
            sequence_id="advio-15",
            dataset_serving={
                "dataset_id": "advio",
                "pose_source": "ground_truth",
                "pose_frame_mode": "provider_world",
            },
        ),
        slam=SlamStageConfig(backend={"kind": "mock"}),
    )
    prepared_manifest = SequenceManifest(
        sequence_id="advio-15",
        rgb_dir=rgb_dir,
        timestamps_path=timestamps_path,
    )

    manifest = materialize_offline_manifest(
        request=request,
        prepared_manifest=prepared_manifest,
        run_paths=run_paths,
    )

    assert manifest.timestamps_path == run_paths.input_timestamps_path.resolve()
    payload = json.loads(manifest.timestamps_path.read_text(encoding="utf-8"))
    assert payload == {"frame_stride": 1, "timestamps_ns": [0, 100_000_000]}


def test_materialize_offline_manifest_does_not_double_sample_dataset_timestamps(tmp_path: Path) -> None:
    artifact_root = tmp_path / "artifacts"
    run_paths = RunArtifactPaths.build(artifact_root)
    rgb_dir = tmp_path / "rgb"
    rgb_dir.mkdir(parents=True)
    timestamps_path = tmp_path / "sampled-rgb.txt"
    timestamps_path.write_text("0.000000000 rgb/000000.png\n0.200000000 rgb/000001.png\n", encoding="utf-8")
    request = RunRequest(
        experiment_name="sampled-dataset-ingest",
        mode=PipelineMode.OFFLINE,
        output_dir=tmp_path / ".artifacts",
        source=DatasetSourceSpec(dataset_id="tum_rgbd", sequence_id="freiburg1_room", frame_stride=2),
        slam=SlamStageConfig(backend={"kind": "mock"}),
    )
    prepared_manifest = SequenceManifest(
        sequence_id="freiburg1_room",
        rgb_dir=rgb_dir,
        timestamps_path=timestamps_path,
    )

    manifest = materialize_offline_manifest(
        request=request,
        prepared_manifest=prepared_manifest,
        run_paths=run_paths,
    )

    payload = json.loads(manifest.timestamps_path.read_text(encoding="utf-8"))
    assert payload == {"frame_stride": 1, "timestamps_ns": [0, 200_000_000]}


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
        coordinator._record_stage_result(
            StageKey.SLAM,
            StageResult(
                stage_key=StageKey.SLAM,
                payload=None,
                outcome=outcome,
                final_runtime_status=StageRuntimeStatus(
                    stage_key=StageKey.SLAM,
                    lifecycle_state=StageStatus.COMPLETED,
                ),
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
        lambda array: (ArrayHandle(handle_id="frame", shape=(2, 2, 3), dtype="uint8"), np.asarray(array)),
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
    assert snapshot.stage_outcomes[StageKey.INGEST].status is StageStatus.COMPLETED
    assert snapshot.stage_outcomes[StageKey.SLAM].status is StageStatus.COMPLETED
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
    assert snapshot.stage_runtime_status[StageKey.SLAM].processed_items >= 3
    source_ref = snapshot.live_refs[StageKey.INGEST]["source_rgb:image"]
    assert service.read_payload(source_ref) is not None
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


def _rgbd_benchmark_inputs(tmp_path: Path) -> PreparedBenchmarkInputs:
    payload_root = tmp_path / "rgbd-payload"
    payload_root.mkdir(parents=True, exist_ok=True)
    np.save(payload_root / "rgb.npy", np.full((32, 32, 3), 127, dtype=np.uint8))
    np.save(payload_root / "depth.npy", np.ones((32, 32), dtype=np.float32))
    index = RgbdObservationSequenceIndex(
        source_id="test",
        sequence_id="test-sequence",
        observation_count=1,
        rows=[
            RgbdObservationIndexEntry(
                seq=0,
                timestamp_ns=0,
                rgb_path=Path("rgb.npy"),
                depth_path=Path("depth.npy"),
                T_world_camera=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
                camera_intrinsics={
                    "fx": 32.0,
                    "fy": 32.0,
                    "cx": 15.5,
                    "cy": 15.5,
                    "width_px": 32,
                    "height_px": 32,
                },
                provenance=RgbdObservationProvenance(source_id="test", sequence_id="test-sequence"),
            )
        ],
    )
    index_path = payload_root / "rgbd_observations.json"
    index_path.write_text(json.dumps(index.model_dump(mode="json"), indent=2), encoding="utf-8")
    return PreparedBenchmarkInputs(
        rgbd_observation_sequences=[
            RgbdObservationSequenceRef(
                source_id="test",
                sequence_id="test-sequence",
                index_path=index_path,
                payload_root=payload_root,
                observation_count=1,
            )
        ]
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
