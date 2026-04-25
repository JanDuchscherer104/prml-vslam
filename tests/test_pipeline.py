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

from prml_vslam.interfaces import (
    CAMERA_RDF_FRAME,
    FrameTransform,
    Observation,
    ObservationIndexEntry,
    ObservationProvenance,
    ObservationSequenceIndex,
    ObservationSequenceRef,
)
from prml_vslam.interfaces.artifacts import ArtifactRef
from prml_vslam.interfaces.slam import SlamArtifacts
from prml_vslam.methods.contracts import SlamUpdate
from prml_vslam.methods.stage.config import MethodId, VistaSlamBackendConfig
from prml_vslam.pipeline import PipelineMode
from prml_vslam.pipeline.backend_ray import RayPipelineBackend
from prml_vslam.pipeline.config import RunConfig, build_run_config
from prml_vslam.pipeline.contracts.context import PipelineExecutionContext
from prml_vslam.pipeline.contracts.events import (
    RunStopped,
    StageCompleted,
    StageFailed,
    StageOutcome,
    StageStatus,
)
from prml_vslam.pipeline.contracts.plan import PlannedSource, RunPlan, RunPlanStage
from prml_vslam.pipeline.contracts.provenance import RunSummary
from prml_vslam.pipeline.contracts.runtime import RunSnapshot, RunState
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.placement import actor_options_for_stage
from prml_vslam.pipeline.ray_runtime.common import clean_actor_options
from prml_vslam.pipeline.ray_runtime.coordinator import RunCoordinatorActor
from prml_vslam.pipeline.ray_runtime.stage_actors import PacketSourceActor
from prml_vslam.pipeline.ray_runtime.substrate import build_runtime_env, prepare_ray_environment
from prml_vslam.pipeline.run_service import RunService
from prml_vslam.pipeline.runner import StageResultStore, StageRunner
from prml_vslam.pipeline.runtime_manager import RuntimeManager
from prml_vslam.pipeline.snapshot_projector import SnapshotProjector
from prml_vslam.pipeline.stages.base.contracts import (
    StageResult,
    StageRuntimeStatus,
    StageRuntimeUpdate,
    VisualizationIntent,
    VisualizationItem,
)
from prml_vslam.pipeline.stages.base.handles import TransientPayloadRef
from prml_vslam.reconstruction.stage import ReconstructionRuntime, ReconstructionStageInput
from prml_vslam.sources.config import AdvioSourceConfig, TumRgbdSourceConfig, VideoSourceConfig
from prml_vslam.sources.contracts import (
    PreparedBenchmarkInputs,
    ReferenceSource,
    SequenceManifest,
    SourceStageOutput,
)
from prml_vslam.sources.runtime import SourceStageInput
from prml_vslam.utils import Console, PathConfig, RunArtifactPaths
from prml_vslam.utils.serialization import stable_hash
from tests.pipeline_testing_support import FakeOfflineSource, FakeStreamingSource


@pytest.fixture(autouse=True)
def _isolated_ray_namespace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PRML_VSLAM_RAY_NAMESPACE", f"pytest-{uuid.uuid4().hex}")
    yield
    if ray.is_initialized():
        ray.shutdown()


def _fake_slam_artifacts(artifact_root: Path, *, emit_sparse_points: bool, emit_dense_points: bool) -> SlamArtifacts:
    run_paths = RunArtifactPaths.build(artifact_root)
    run_paths.trajectory_path.parent.mkdir(parents=True, exist_ok=True)
    run_paths.trajectory_path.write_text("0.0 0.0 0.0 0.0 0.0 0.0 0.0 1.0\n", encoding="utf-8")
    point_cloud_ref: ArtifactRef | None = None
    if emit_sparse_points or emit_dense_points:
        run_paths.point_cloud_path.parent.mkdir(parents=True, exist_ok=True)
        run_paths.point_cloud_path.write_text("ply\n", encoding="utf-8")
        point_cloud_ref = ArtifactRef(path=run_paths.point_cloud_path, kind="ply", fingerprint="cloud")
    return SlamArtifacts(
        trajectory_tum=ArtifactRef(path=run_paths.trajectory_path, kind="tum", fingerprint="traj"),
        sparse_points_ply=point_cloud_ref if emit_sparse_points else None,
        dense_points_ply=point_cloud_ref if emit_dense_points else None,
    )


class _FakeVistaBackend:
    method_id = MethodId.VISTA

    def __init__(self) -> None:
        self._output_policy = None
        self._artifact_root: Path | None = None
        self._pending_updates: list[SlamUpdate] = []

    def run_sequence(
        self,
        sequence: SequenceManifest,
        benchmark_inputs: PreparedBenchmarkInputs | None,
        baseline_source: ReferenceSource,
        backend_config,
        output_policy,
        artifact_root: Path,
    ) -> SlamArtifacts:
        del sequence, benchmark_inputs, baseline_source, backend_config
        return _fake_slam_artifacts(
            artifact_root,
            emit_sparse_points=output_policy.emit_sparse_points,
            emit_dense_points=output_policy.emit_dense_points,
        )

    def start_streaming(
        self,
        sequence_manifest: SequenceManifest,
        benchmark_inputs: PreparedBenchmarkInputs | None,
        baseline_source: ReferenceSource,
        backend_config,
        output_policy,
        artifact_root: Path,
    ) -> None:
        del sequence_manifest, benchmark_inputs, baseline_source, backend_config
        self._output_policy = output_policy
        self._artifact_root = artifact_root

    def step_streaming(self, frame: Observation) -> None:
        pose = frame.T_world_camera or FrameTransform(
            qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=float(frame.seq), ty=0.0, tz=0.0
        )
        self._pending_updates.append(
            SlamUpdate(
                seq=frame.seq,
                source_seq=frame.seq,
                timestamp_ns=frame.timestamp_ns,
                source_timestamp_ns=frame.timestamp_ns,
                is_keyframe=True,
                keyframe_index=frame.seq,
                pose=pose,
                pose_updated=True,
                num_sparse_points=1,
                num_dense_points=1,
                pointmap=np.ones((2, 2, 3), dtype=np.float32),
                image_rgb=frame.rgb,
                preview_rgb=frame.rgb,
            )
        )

    def drain_streaming_updates(self) -> list[SlamUpdate]:
        updates = self._pending_updates
        self._pending_updates = []
        return updates

    def finish_streaming(self) -> SlamArtifacts:
        assert self._artifact_root is not None
        assert self._output_policy is not None
        return _fake_slam_artifacts(
            self._artifact_root,
            emit_sparse_points=self._output_policy.emit_sparse_points,
            emit_dense_points=self._output_policy.emit_dense_points,
        )


@pytest.fixture(autouse=True)
def _fake_vista_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "prml_vslam.methods.stage.config.VistaSlamBackendConfig.setup_target",
        lambda self, *, path_config=None, **_kwargs: _FakeVistaBackend(),
    )


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


def test_run_config_requires_explicit_stage_backend_discriminator() -> None:
    with pytest.raises(ValidationError):
        RunConfig.model_validate(
            {
                "experiment_name": "demo",
                "mode": "offline",
                "output_dir": ".artifacts",
                "stages": {
                    "source": {"backend": {"source_id": "video", "video_path": "captures/demo.mp4"}},
                    "slam": {"backend": {"max_frames": 9}},
                },
            }
        )


def test_run_config_accepts_explicit_stage_backend_spec() -> None:
    run_config = RunConfig.model_validate(
        {
            "experiment_name": "demo",
            "mode": "offline",
            "output_dir": ".artifacts",
            "stages": {
                "source": {"backend": {"source_id": "video", "video_path": "captures/demo.mp4"}},
                "slam": {"backend": {"method_id": "vista", "max_frames": 9}},
            },
        }
    )

    assert run_config.stages.slam.backend.method_id is MethodId.VISTA
    assert run_config.stages.slam.backend.max_frames == 9


def test_run_config_defaults_to_ephemeral_local_head_lifecycle() -> None:
    run_config = RunConfig.model_validate(
        {
            "experiment_name": "demo",
            "mode": "offline",
            "output_dir": ".artifacts",
            "stages": {
                "source": {"backend": {"source_id": "video", "video_path": "captures/demo.mp4"}},
                "slam": {"backend": {"method_id": "vista"}},
            },
        }
    )

    assert run_config.ray_local_head_lifecycle == "ephemeral"


def test_run_config_from_toml_accepts_inline_ray_policy(tmp_path: Path) -> None:
    config_path = tmp_path / "run.toml"
    config_path.write_text(
        """
experiment_name = "demo"
mode = "streaming"
output_dir = ".artifacts"
ray_local_head_lifecycle = "reusable"

[stages.source.backend]
source_id = "advio"
sequence_id = "advio-01"

[stages.source.backend.dataset_serving]
pose_source = "ground_truth"
pose_frame_mode = "provider_world"

[stages.slam.backend]
method_id = "vista"

""".strip(),
        encoding="utf-8",
    )

    run_config = RunConfig.from_toml(config_path)

    assert run_config.ray_local_head_lifecycle == "reusable"


def test_run_config_from_toml_accepts_viewer_blueprint_path(tmp_path: Path) -> None:
    config_path = tmp_path / "run.toml"
    config_path.write_text(
        """
experiment_name = "demo"
mode = "streaming"
output_dir = ".artifacts"

[stages.source.backend]
source_id = "advio"
sequence_id = "advio-01"

[stages.source.backend.dataset_serving]
pose_source = "ground_truth"
pose_frame_mode = "provider_world"

[stages.slam.backend]
method_id = "vista"

[visualization]
connect_live_viewer = true
viewer_blueprint_path = ".configs/visualization/vista_blueprint.rbl"
""".strip(),
        encoding="utf-8",
    )

    run_config = RunConfig.from_toml(config_path)

    assert run_config.visualization.connect_live_viewer is True
    assert run_config.visualization.viewer_blueprint_path == Path(".configs/visualization/vista_blueprint.rbl")


def test_run_config_marks_cloud_eval_placeholder_unavailable(tmp_path: Path) -> None:
    path_config = PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts")
    run_config = _run_config(
        experiment_name="cloud-validation",
        mode=PipelineMode.OFFLINE,
        output_dir=path_config.artifacts_dir,
        source_backend=VideoSourceConfig(video_path=Path("captures/demo.mp4")),
        method=MethodId.VISTA,
        emit_dense_points=False,
        evaluate_cloud=True,
    )

    plan = run_config.compile_plan(path_config)
    cloud_stage = next(stage for stage in plan.stages if stage.key is StageKey.CLOUD_EVALUATION)

    assert cloud_stage.available is False
    assert cloud_stage.availability_reason == "Dense-cloud evaluation is planned but no runtime is registered yet."


def test_run_config_compile_plan_uses_supplied_path_config(tmp_path: Path) -> None:
    path_config = PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts")
    run_config = _run_config(
        experiment_name="request-build",
        mode=PipelineMode.OFFLINE,
        output_dir=path_config.artifacts_dir,
        source_backend=VideoSourceConfig(video_path=Path("captures/demo.mp4")),
        method=MethodId.VISTA,
    )

    plan = run_config.compile_plan(path_config)

    assert plan.run_id == "request-build"
    assert (
        plan.artifact_root
        == path_config.plan_run_paths(
            experiment_name=run_config.experiment_name,
            method_slug=run_config.stages.slam.backend.method_id.value,
            output_dir=run_config.output_dir,
        ).artifact_root
    )
    assert [stage.key for stage in plan.stages] == [StageKey.SOURCE, StageKey.SLAM, StageKey.SUMMARY]


def test_build_run_config_copies_backend_policy_and_visualization_fields(tmp_path: Path) -> None:
    run_config = build_run_config(
        experiment_name="builder-demo",
        mode=PipelineMode.OFFLINE,
        output_dir=tmp_path / ".artifacts",
        source_backend=VideoSourceConfig(video_path=Path("captures/demo.mp4"), frame_stride=3),
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
        connect_live_viewer=True,
        export_viewer_rrd=True,
    )

    assert run_config.stages.slam.backend.method_id is MethodId.VISTA
    assert run_config.stages.slam.backend.max_frames == 12
    assert run_config.stages.slam.backend.vista_slam_dir == Path("external/vista-slam")
    assert run_config.stages.slam.outputs.emit_dense_points is False
    assert run_config.stages.slam.outputs.emit_sparse_points is True
    assert run_config.stages.reconstruction.enabled is True
    assert run_config.stages.evaluate_trajectory.enabled is True
    assert run_config.stages.evaluate_trajectory.evaluation.baseline_source is ReferenceSource.ARCORE
    assert run_config.stages.evaluate_cloud.enabled is False
    assert run_config.visualization.connect_live_viewer is True
    assert run_config.visualization.export_viewer_rrd is True


def test_stage_registry_marks_placeholder_stages_unavailable(tmp_path: Path) -> None:
    path_config = PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts")
    run_config = _run_config(
        experiment_name="placeholder",
        mode=PipelineMode.OFFLINE,
        output_dir=path_config.artifacts_dir,
        source_backend=AdvioSourceConfig(
            sequence_id="advio-01",
            dataset_serving={
                "pose_source": "ground_truth",
                "pose_frame_mode": "provider_world",
            },
        ),
        method=MethodId.VISTA,
        reference_enabled=False,
        trajectory_eval_enabled=False,
        evaluate_cloud=True,
    )

    plan = run_config.compile_plan(path_config=path_config)

    unavailable = [stage for stage in plan.stages if not stage.available]
    assert len(unavailable) == 1
    assert unavailable[0].key.value == "evaluate.cloud"
    assert "no runtime is registered yet" in unavailable[0].availability_reason


def test_stage_registry_allows_tum_rgbd_reference_reconstruction(tmp_path: Path) -> None:
    path_config = PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts")
    run_config = _run_config(
        experiment_name="tum-reference",
        mode=PipelineMode.OFFLINE,
        output_dir=path_config.artifacts_dir,
        source_backend=TumRgbdSourceConfig(sequence_id="freiburg1_desk"),
        method=MethodId.VISTA,
        reference_enabled=True,
    )

    plan = run_config.compile_plan(path_config=path_config)

    reference_stage = next(stage for stage in plan.stages if stage.key is StageKey.RECONSTRUCTION)
    assert reference_stage.available is True
    assert reference_stage.outputs == [RunArtifactPaths.build(plan.artifact_root).reference_cloud_path]


def test_stage_registry_rejects_non_rgbd_reference_reconstruction(tmp_path: Path) -> None:
    path_config = PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts")
    run_config = _run_config(
        experiment_name="video-reference",
        mode=PipelineMode.OFFLINE,
        output_dir=path_config.artifacts_dir,
        source_backend=VideoSourceConfig(video_path=Path("captures/demo.mp4")),
        method=MethodId.VISTA,
        reference_enabled=True,
    )

    plan = run_config.compile_plan(path_config=path_config)

    reference_stage = next(stage for stage in plan.stages if stage.key is StageKey.RECONSTRUCTION)
    assert reference_stage.available is False
    assert reference_stage.availability_reason == "Reconstruction currently requires a TUM RGB-D dataset source."


def test_reference_reconstruction_stage_writes_cloud_and_metadata(tmp_path: Path) -> None:
    pytest.importorskip("open3d")
    run_config = _run_config(
        experiment_name="reference-stage",
        mode=PipelineMode.OFFLINE,
        output_dir=tmp_path / ".artifacts",
        source_backend=TumRgbdSourceConfig(sequence_id="freiburg1_desk"),
        method=MethodId.VISTA,
        reference_enabled=True,
    )
    run_config.stages.reconstruction.backend.extract_mesh = True
    plan = _plan_with_stages(
        tmp_path=tmp_path,
        run_config=run_config,
        stage_keys=[StageKey.RECONSTRUCTION],
    )
    context = PipelineExecutionContext(
        run_config=run_config,
        plan=plan,
        path_config=PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts"),
        run_paths=RunArtifactPaths.build(plan.artifact_root),
        results=StageResultStore(),
        slam_backend=run_config.stages.slam.backend,
    )
    benchmark_inputs = _rgbd_benchmark_inputs(tmp_path)

    result = ReconstructionRuntime().run_offline(
        ReconstructionStageInput(
            backend=run_config.stages.reconstruction.backend,
            run_paths=context.run_paths,
            benchmark_inputs=benchmark_inputs,
        )
    )

    assert result.outcome.stage_key is StageKey.RECONSTRUCTION
    assert result.outcome.status is StageStatus.COMPLETED
    assert result.outcome.artifacts["reference_cloud"].path.exists()
    assert result.outcome.artifacts["reconstruction_metadata"].path.exists()
    assert result.outcome.artifacts["reference_mesh"].path.exists()
    assert result.outcome.metrics["observation_count"] == 1


def test_snapshot_projector_preserves_stopped_preview_handle() -> None:
    projector = SnapshotProjector()
    snapshot = RunSnapshot(run_id="run-1", state=RunState.STOPPED)
    ref = TransientPayloadRef(handle_id="frame", payload_kind="image", shape=(4, 4, 3), dtype="uint8")

    updated = projector.apply_runtime_update(
        snapshot,
        StageRuntimeUpdate(
            stage_key=StageKey.SOURCE,
            timestamp_ns=1,
            visualizations=[
                VisualizationItem(
                    intent=VisualizationIntent.RGB_IMAGE,
                    role="source_rgb",
                    payload_refs={"image": ref},
                    frame_index=1,
                )
            ],
            runtime_status=StageRuntimeStatus(
                stage_key=StageKey.SOURCE,
                lifecycle_state=StageStatus.RUNNING,
                processed_items=1,
                fps=12.0,
            ),
        ),
    )

    assert updated.state is RunState.STOPPED
    assert updated.stage_runtime_status[StageKey.SOURCE].processed_items == 1
    assert updated.stage_runtime_status[StageKey.SOURCE].fps == 12.0
    assert updated.live_refs[StageKey.SOURCE]["source_rgb:image"] == ref


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
            StageKey.SOURCE: StageRuntimeStatus(
                stage_key=StageKey.SOURCE,
                lifecycle_state=StageStatus.RUNNING,
                progress_message="streaming",
            )
        },
        artifacts={"before": ArtifactRef(path=Path("/tmp/before"), kind="txt", fingerprint="before")},
    )

    updated = projector.apply_runtime_update(
        snapshot,
        StageRuntimeUpdate(
            stage_key=StageKey.SLAM,
            timestamp_ns=2,
            semantic_events=[
                SlamUpdate(
                    seq=1,
                    source_seq=1,
                    source_timestamp_ns=2,
                    timestamp_ns=2,
                    pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=2.0, tz=3.0),
                    pose_updated=True,
                )
            ],
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


def test_snapshot_projector_runtime_update_replaces_runtime_status() -> None:
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

    assert updated.stage_runtime_status[StageKey.SLAM] == update.runtime_status
    assert snapshot.stage_runtime_status[StageKey.SLAM].progress_message == "old"


def test_actor_options_preserve_defaults_without_placement() -> None:
    run_config = _placement_run_config()
    backend = _test_backend_config(default_cpu=4.0, default_gpu=1.0)

    source_options = actor_options_for_stage(
        stage_key=StageKey.SOURCE,
        run_config=run_config,
        backend=backend,
        default_num_cpus=1.0,
        default_num_gpus=0.0,
        restartable=True,
    )
    slam_options = actor_options_for_stage(
        stage_key=StageKey.SLAM,
        run_config=run_config,
        backend=backend,
        default_num_cpus=2.0,
        default_num_gpus=0.0,
        inherit_backend_defaults=True,
    )

    assert source_options["num_cpus"] == 1.0
    assert source_options["num_gpus"] == 0.0
    assert source_options["max_restarts"] == -1
    assert slam_options["num_cpus"] == 4.0
    assert slam_options["num_gpus"] == 1.0


def test_actor_options_explicit_slam_placement_overrides_resources() -> None:
    run_config = _placement_run_config(placement={"slam": {"resources": {"CPU": 4, "GPU": 1}}})
    backend = _test_backend_config(default_cpu=2.0, default_gpu=0.0)

    options = actor_options_for_stage(
        stage_key=StageKey.SLAM,
        run_config=run_config,
        backend=backend,
        default_num_cpus=2.0,
        default_num_gpus=0.0,
        inherit_backend_defaults=True,
    )

    assert options["num_cpus"] == 4.0
    assert options["num_gpus"] == 1.0


def test_actor_options_explicit_source_placement_overrides_resources() -> None:
    run_config = _placement_run_config(placement={"source": {"resources": {"CPU": 3}}})
    backend = _test_backend_config(default_cpu=8.0, default_gpu=1.0)

    options = actor_options_for_stage(
        stage_key=StageKey.SOURCE,
        run_config=run_config,
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


def test_run_coordinator_read_payload_accepts_materialized_payloads() -> None:
    coordinator_cls = RunCoordinatorActor.__ray_metadata__.modified_class
    coordinator = coordinator_cls(run_id="demo", namespace="pytest-unit")
    payload = np.zeros((2, 2, 3), dtype=np.uint8)

    coordinator._remember_handle("frame-1", payload)

    resolved = coordinator.read_payload("frame-1")

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
    assert snapshot.live_refs[StageKey.SLAM]["model_rgb:image"] == ref


def test_run_coordinator_runtime_updates_do_not_create_durable_backend_events() -> None:
    coordinator_cls = RunCoordinatorActor.__ray_metadata__.modified_class
    coordinator = coordinator_cls(run_id="run-1", namespace="pytest-unit")
    coordinator._snapshot = RunSnapshot(run_id="run-1")

    coordinator.on_slam_runtime_updates(
        updates=[
            StageRuntimeUpdate(
                stage_key=StageKey.SLAM,
                timestamp_ns=10,
                semantic_events=[
                    SlamUpdate(
                        seq=1,
                        timestamp_ns=10,
                        pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=2.0, tz=3.0),
                        pose_updated=True,
                    )
                ],
            )
        ]
    )

    snapshot = coordinator.snapshot()
    assert snapshot.stage_runtime_status == {}
    assert coordinator.events() == []


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
    coordinator._run_config = SimpleNamespace(visualization=SimpleNamespace(log_source_rgb=True))
    monkeypatch.setattr(coordinator, "_self_actor_handle", lambda: "resolver")
    monkeypatch.setattr(
        "prml_vslam.pipeline.ray_runtime.coordinator.ray.get",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("coordinator hot path must not call ray.get")),
    )

    coordinator.on_packet(
        packet=Observation(seq=1, timestamp_ns=1, provenance=ObservationProvenance()),
        frame_ref=np.zeros((2, 2, 3), dtype=np.uint8),
        depth_ref=None,
        confidence_ref=None,
        pointmap_ref=None,
        intrinsics=None,
        pose=None,
        provenance=ObservationProvenance(),
        processed_frame_count=1,
        measured_fps=30.0,
        frame_payload_ref=TransientPayloadRef(
            handle_id="frame-1",
            payload_kind="image",
            media_type="image/rgb",
            shape=(2, 2, 3),
            dtype="uint8",
        ),
    )

    assert len(submitted) == 1
    assert submitted[0][0].stage_key is StageKey.SOURCE
    assert submitted[0][1] == "resolver"
    assert coordinator._rerun_sink_last_call == "rerun-call-1"


def test_run_coordinator_routes_reconstruction_runtime_updates_without_payload_resolver() -> None:
    coordinator_cls = RunCoordinatorActor.__ray_metadata__.modified_class
    coordinator = coordinator_cls(run_id="demo", namespace="pytest-unit")
    submitted: list[tuple[StageRuntimeUpdate, Any]] = []
    update = StageRuntimeUpdate(
        stage_key=StageKey.RECONSTRUCTION,
        timestamp_ns=1,
        runtime_status=StageRuntimeStatus(
            stage_key=StageKey.RECONSTRUCTION,
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
            return StageRuntimeStatus(stage_key=StageKey.RECONSTRUCTION)

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
        StageKey.RECONSTRUCTION,
        factory=FakeReconstructionRuntime,
    )
    runtime_proxy = runtime_manager.runtime_for(StageKey.RECONSTRUCTION)
    coordinator._rerun_sink = SimpleNamespace(observe_update=FakeObserveUpdateRemote())

    coordinator._publish_runtime_updates_from_proxy(runtime_proxy)

    assert submitted == [(update, None)]
    assert coordinator._rerun_sink_last_call == "rerun-call-1"
    assert coordinator.snapshot().stage_runtime_status[StageKey.RECONSTRUCTION].lifecycle_state is StageStatus.COMPLETED
    assert runtime_proxy.drain_runtime_updates() == []


def test_run_coordinator_runtime_manager_registers_reconstruction_live_updates(tmp_path: Path) -> None:
    coordinator_cls = RunCoordinatorActor.__ray_metadata__.modified_class
    coordinator = coordinator_cls(run_id="demo", namespace="pytest-unit")
    run_config = _run_config(
        experiment_name="demo",
        mode=PipelineMode.OFFLINE,
        output_dir=tmp_path / ".artifacts",
        source_backend=VideoSourceConfig(video_path=Path("captures/demo.mp4")),
        method=MethodId.VISTA,
    )
    plan = _plan_with_stages(
        tmp_path=tmp_path,
        run_config=run_config,
        stage_keys=[StageKey.RECONSTRUCTION],
    )
    coordinator._run_config = run_config
    coordinator._path_config = PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts")
    coordinator._slam_backend = run_config.stages.slam.backend
    context = coordinator._stage_execution_context(run_config=run_config, plan=plan, source=FakeOfflineSource())

    runtime_manager = coordinator._build_runtime_manager(plan=plan, context=context)
    runtime_proxy = runtime_manager.runtime_for(StageKey.RECONSTRUCTION)

    assert isinstance(runtime_proxy.runtime, ReconstructionRuntime)


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
        packet=Observation(seq=1, timestamp_ns=1, provenance=ObservationProvenance()),
        frame_ref=np.zeros((2, 2, 3), dtype=np.uint8),
        depth_ref=None,
        confidence_ref=None,
        pointmap_ref=None,
        intrinsics=None,
        pose=None,
        provenance=ObservationProvenance(),
        processed_frame_count=1,
        measured_fps=30.0,
        frame_payload_ref=TransientPayloadRef(
            handle_id="frame-1",
            payload_kind="image",
            media_type="image/rgb",
            shape=(2, 2, 3),
            dtype="uint8",
        ),
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

    assert snapshot.stage_outcomes[StageKey.SLAM].status is StageStatus.FAILED
    assert snapshot.error_message == "backend boom"
    assert any(event.kind == "stage.failed" for event in coordinator.events())


def test_run_coordinator_emits_source_stage_failure_before_run_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path_config = PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts")
    run_config = _run_config(
        experiment_name="source-failure",
        mode=PipelineMode.OFFLINE,
        output_dir=path_config.artifacts_dir,
        source_backend=VideoSourceConfig(video_path=Path("captures/demo.mp4")),
        method=MethodId.VISTA,
        trajectory_eval_enabled=False,
    )
    coordinator_cls = RunCoordinatorActor.__ray_metadata__.modified_class
    coordinator = coordinator_cls(run_id=run_config.experiment_name, namespace="pytest-unit")
    plan = _plan_with_stages(
        tmp_path=tmp_path,
        run_config=run_config,
        stage_keys=[StageKey.SOURCE, StageKey.SLAM, StageKey.SUMMARY],
    )

    coordinator._run_config = run_config
    coordinator._plan = plan
    coordinator._path_config = path_config
    coordinator._slam_backend = run_config.stages.slam.backend
    monkeypatch.setattr(coordinator._console, "exception", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "prml_vslam.sources.runtime.SourceRuntime.run_offline",
        lambda self, input_payload: (_ for _ in ()).throw(RuntimeError("source boom")),
    )

    coordinator._run(
        run_config=run_config,
        plan=plan,
        path_config=path_config,
        runtime_source=FakeOfflineSource(),
    )

    events = coordinator.events()
    assert [event.kind for event in events] == [
        "run.started",
        "stage.queued",
        "stage.started",
        "stage.failed",
        "run.failed",
    ]
    failed_event = next(event for event in events if isinstance(event, StageFailed))
    assert failed_event.stage_key is StageKey.SOURCE
    assert failed_event.outcome.config_hash == stable_hash(run_config.stages.source.backend)
    assert failed_event.outcome.input_fingerprint == stable_hash(run_config.stages.source.backend)
    assert failed_event.outcome.error_message == "source boom"


def test_run_coordinator_fails_fast_for_available_stage_without_runtime_spec(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_config = _run_config(
        experiment_name="missing-runtime-stage",
        mode=PipelineMode.OFFLINE,
        output_dir=tmp_path / ".artifacts",
        source_backend=VideoSourceConfig(video_path=Path("captures/demo.mp4")),
        method=MethodId.VISTA,
    )
    coordinator_cls = RunCoordinatorActor.__ray_metadata__.modified_class
    coordinator = coordinator_cls(run_id=run_config.experiment_name, namespace="pytest-unit")
    path_config = PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts")
    plan = _plan_with_stages(
        tmp_path=tmp_path,
        run_config=run_config,
        stage_keys=[StageKey.SOURCE, StageKey.CLOUD_EVALUATION, StageKey.SUMMARY],
    )
    coordinator._run_config = run_config
    coordinator._path_config = path_config
    coordinator._slam_backend = run_config.stages.slam.backend
    monkeypatch.setattr(coordinator._console, "exception", lambda *args, **kwargs: None)

    coordinator._run(
        run_config=run_config,
        plan=plan,
        path_config=path_config,
        runtime_source=FakeOfflineSource(),
    )

    failed_event = next(event for event in coordinator.events() if event.kind == "run.failed")
    assert "evaluate.cloud" in failed_event.error_message


def test_run_coordinator_offline_dispatches_batch_stage_executors(tmp_path: Path) -> None:
    coordinator_cls = RunCoordinatorActor.__ray_metadata__.modified_class
    coordinator = coordinator_cls(run_id="demo", namespace="pytest-unit")
    path_config = PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts")
    run_config = _run_config(
        experiment_name="dispatch-demo",
        mode=PipelineMode.OFFLINE,
        output_dir=path_config.artifacts_dir,
        source_backend=VideoSourceConfig(video_path=Path("captures/demo.mp4")),
        method=MethodId.VISTA,
        trajectory_eval_enabled=False,
    )
    plan = _plan_with_stages(
        tmp_path=tmp_path,
        run_config=run_config,
        stage_keys=[StageKey.SOURCE, StageKey.SLAM, StageKey.SUMMARY],
    )
    coordinator._run_config = run_config
    coordinator._path_config = path_config
    coordinator._slam_backend = _test_backend_config(default_cpu=1.0, default_gpu=0.0)

    coordinator._run_offline(
        run_config=run_config,
        plan=plan,
        path_config=path_config,
        runtime_source=FakeOfflineSource(),
    )

    snapshot = coordinator.snapshot()
    assert snapshot.stage_outcomes[StageKey.SOURCE].status is StageStatus.COMPLETED
    assert snapshot.stage_outcomes[StageKey.SLAM].status is StageStatus.COMPLETED
    assert snapshot.stage_outcomes[StageKey.SUMMARY].status is StageStatus.COMPLETED
    assert "trajectory_tum" in snapshot.artifacts
    assert "run_summary" in snapshot.artifacts
    assert snapshot.state is RunState.COMPLETED


def test_run_coordinator_finalize_streaming_dispatches_batch_executors(tmp_path: Path) -> None:
    coordinator_cls = RunCoordinatorActor.__ray_metadata__.modified_class
    coordinator = coordinator_cls(run_id="streaming-dispatch", namespace="pytest-unit")
    path_config = PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts")
    run_config = _run_config(
        experiment_name="streaming-dispatch",
        mode=PipelineMode.STREAMING,
        output_dir=path_config.artifacts_dir,
        source_backend=VideoSourceConfig(video_path=Path("captures/demo.mp4")),
        method=MethodId.VISTA,
        trajectory_eval_enabled=True,
    )
    plan = _plan_with_stages(
        tmp_path=tmp_path,
        run_config=run_config,
        stage_keys=[
            StageKey.SOURCE,
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
                StageKey.SOURCE,
                StageKey.SLAM,
                StageKey.TRAJECTORY_EVALUATION,
            ]
            return StageResult(
                stage_key=StageKey.SUMMARY,
                payload=RunSummary(
                    run_id=input_payload.plan.run_id,
                    artifact_root=input_payload.plan.artifact_root,
                    stage_status={
                        StageKey.SOURCE: StageStatus.COMPLETED,
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
    )
    runtime_manager.register(
        StageKey.TRAJECTORY_EVALUATION,
        factory=_FakeTrajectoryRuntime,
    )
    runtime_manager.register(
        StageKey.SUMMARY,
        factory=_FakeSummaryRuntime,
    )
    coordinator._run_config = run_config
    coordinator._plan = plan
    coordinator._path_config = path_config
    coordinator._slam_backend = _test_backend_config(default_cpu=1.0, default_gpu=0.0)
    coordinator._snapshot = RunSnapshot(run_id=plan.run_id, plan=plan, active_executor="ray")
    coordinator._streaming_runtime_manager = runtime_manager
    coordinator._slam_runtime_proxy = runtime_manager.runtime_for(StageKey.SLAM)
    coordinator._result_store.put(
        StageResult(
            stage_key=StageKey.SOURCE,
            payload=SourceStageOutput(sequence_manifest=sequence_manifest, benchmark_inputs=None),
            outcome=StageOutcome(
                stage_key=StageKey.SOURCE,
                status=StageStatus.COMPLETED,
                config_hash="source",
                input_fingerprint="source",
            ),
            final_runtime_status=StageRuntimeStatus(
                stage_key=StageKey.SOURCE,
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


def test_slam_backend_config_uses_stage_owned_method_id_for_vista() -> None:
    run_config = RunConfig.model_validate(
        {
            "experiment_name": "vista",
            "mode": "offline",
            "output_dir": ".artifacts",
            "stages": {
                "source": {"backend": {"source_id": "video", "video_path": "captures/demo.mp4"}},
                "slam": {"backend": {"method_id": "vista", "max_frames": 9}},
            },
        }
    )

    assert run_config.stages.slam.backend.method_id is MethodId.VISTA
    assert run_config.stages.slam.backend.max_frames == 9


def test_streaming_source_config_input_caps_video_extraction_by_backend_max_frames() -> None:
    input_payload = SourceStageInput(
        artifact_root=Path("/tmp/source"),
        mode=PipelineMode.STREAMING,
        frame_stride=1,
        streaming_max_frames=42,
    )

    assert input_payload.streaming_max_frames == 42


def test_ray_backend_uses_current_python_for_local_runtime_env() -> None:
    runtime_env = build_runtime_env(address=None)

    assert runtime_env["py_executable"] == sys.executable
    assert "excludes" in runtime_env
    assert runtime_env["env_vars"]["OMP_NUM_THREADS"] == "1"
    assert runtime_env["env_vars"]["MKL_NUM_THREADS"] == "1"
    assert runtime_env["env_vars"]["OPENBLAS_NUM_THREADS"] == "1"
    assert runtime_env["env_vars"]["UV_NUM_THREADS"] == "1"


def test_ray_backend_does_not_force_local_python_for_remote_address() -> None:
    runtime_env = build_runtime_env(address="ray://10.0.0.5:10001")

    assert "py_executable" not in runtime_env
    assert "excludes" in runtime_env
    assert runtime_env["env_vars"]["OMP_NUM_THREADS"] == "1"


def test_ray_backend_disables_uv_runtime_env_replication_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("RAY_ENABLE_UV_RUN_RUNTIME_ENV", raising=False)

    prepare_ray_environment()

    assert os.environ["RAY_ENABLE_UV_RUN_RUNTIME_ENV"] == "0"


def test_ray_backend_prefers_persistent_local_head_outside_pytest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = RayPipelineBackend(namespace="prml_vslam.local")
    captured: dict[str, Any] = {}

    monkeypatch.setattr("prml_vslam.pipeline.backend_ray.ray.is_initialized", lambda: False)
    monkeypatch.setattr(backend._local_head, "ensure_address", lambda *, reuse: "127.0.0.1:25001")

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
        backend._local_head,
        "ensure_address",
        lambda *, reuse: (_ for _ in ()).throw(AssertionError("should not be called")),
    )

    def fake_init(**kwargs: Any) -> None:
        captured.update(kwargs)

    monkeypatch.setattr("prml_vslam.pipeline.backend_ray.ray.init", fake_init)

    backend._ensure_ray()

    assert "address" not in captured
    assert captured["_skip_env_hook"] is True


def test_ray_backend_coordinator_placement_is_backend_owned(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = RayPipelineBackend(namespace="pytest-unit")
    captured: dict[str, Any] = {}

    class FakeCoordinatorOptions:
        def remote(self, *, run_id: str, namespace: str) -> object:
            return SimpleNamespace(run_id=run_id, namespace=namespace)

    def fake_options(**options: Any) -> FakeCoordinatorOptions:
        captured.update(options)
        return FakeCoordinatorOptions()

    monkeypatch.setattr(backend, "_shutdown_run", lambda run_id: None)
    monkeypatch.setattr("prml_vslam.pipeline.backend_ray.RunCoordinatorActor.options", fake_options)

    backend._create_coordinator("coordinator-placement")

    assert captured == {
        "name": "prml-vslam-run-coordinator-placement",
        "namespace": "pytest-unit",
        "num_cpus": 1.0,
        "num_gpus": 0.0,
        "max_restarts": 0,
        "max_task_retries": 0,
    }


def test_ray_backend_logs_pytest_init_path(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    backend = RayPipelineBackend(namespace="pytest-unit")
    captured: dict[str, Any] = {}

    monkeypatch.setattr("prml_vslam.pipeline.backend_ray.ray.is_initialized", lambda: False)
    monkeypatch.setattr(
        backend._local_head,
        "ensure_address",
        lambda *, reuse: (_ for _ in ()).throw(AssertionError("should not be called")),
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
    metadata_path = backend._local_head._metadata_path()
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text('{"address": "127.0.0.1:25001", "pid": 123}', encoding="utf-8")
    backend._local_head._can_connect = lambda address: address == "127.0.0.1:25001"  # type: ignore[method-assign]

    assert backend._local_head.ensure_address(reuse=True) == "127.0.0.1:25001"


def test_ray_backend_replaces_stale_local_head_metadata(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    backend = RayPipelineBackend(
        path_config=PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts", logs_dir=tmp_path / ".logs"),
        namespace="prml_vslam.local",
    )
    backend._reuse_local_head = True
    metadata_path = backend._local_head._metadata_path()
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text('{"address": "127.0.0.1:25001", "pid": 123}', encoding="utf-8")
    backend._local_head._can_connect = lambda address: address == "127.0.0.1:25002"  # type: ignore[method-assign]
    monkeypatch.setattr(backend._local_head, "_pick_address", lambda: "127.0.0.1:25002")
    monkeypatch.setattr(
        backend._local_head,
        "_wait_until_connectable",
        lambda address: address == "127.0.0.1:25002",
    )

    class FakePopen:
        pid = 456

        def poll(self) -> None:
            return None

    monkeypatch.setattr(
        "prml_vslam.pipeline.ray_runtime.substrate.subprocess.Popen", lambda *args, **kwargs: FakePopen()
    )

    assert backend._local_head.ensure_address(reuse=True) == "127.0.0.1:25002"
    assert backend._local_head._read_metadata() == {"address": "127.0.0.1:25002", "pid": 456}


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
    metadata_path = backend._local_head._metadata_path()
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text('{"address": "127.0.0.1:25001", "pid": 123}', encoding="utf-8")
    backend._local_head._can_connect = lambda address: address == "127.0.0.1:25002"  # type: ignore[method-assign]
    monkeypatch.setattr(backend._local_head, "_pick_address", lambda: "127.0.0.1:25002")
    monkeypatch.setattr(
        backend._local_head,
        "_wait_until_connectable",
        lambda address: address == "127.0.0.1:25002",
    )

    class FakePopen:
        pid = 456

        def poll(self) -> None:
            return None

    monkeypatch.setattr(
        "prml_vslam.pipeline.ray_runtime.substrate.subprocess.Popen", lambda *args, **kwargs: FakePopen()
    )

    with _capture_logger(
        caplog,
        monkeypatch,
        "prml_vslam.pipeline.backend_ray.RayPipelineBackend.prml_vslam.local",
    ):
        assert backend._local_head.ensure_address(reuse=True) == "127.0.0.1:25002"

    assert any("Discarding stale local Ray head metadata." in r.message for r in caplog.records)
    assert any("Starting local Ray head on '127.0.0.1:25002'." in r.message for r in caplog.records)


def test_ray_backend_closes_parent_log_handle_after_spawn(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    backend = RayPipelineBackend(
        path_config=PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts", logs_dir=tmp_path / ".logs"),
        namespace="prml_vslam.local",
    )
    backend._reuse_local_head = True
    monkeypatch.setattr(backend._local_head, "_pick_address", lambda: "127.0.0.1:25002")
    monkeypatch.setattr(
        backend._local_head,
        "_wait_until_connectable",
        lambda address: address == "127.0.0.1:25002",
    )

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
    monkeypatch.setattr("prml_vslam.pipeline.ray_runtime.substrate.subprocess.Popen", fake_popen)

    assert backend._local_head.ensure_address(reuse=True) == "127.0.0.1:25002"
    assert captured["stdout"] is fake_log_handle
    assert fake_log_handle.closed
    assert backend._local_head._read_metadata() == {"address": "127.0.0.1:25002", "pid": 789}


def test_ray_backend_preserve_shutdown_skips_local_head_termination(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = RayPipelineBackend(namespace="prml_vslam.local")
    backend._coordinators = {"run-1": object()}  # type: ignore[assignment]
    shutdowns: list[str] = []

    monkeypatch.setattr("prml_vslam.pipeline.backend_ray.ray.is_initialized", lambda: True)
    monkeypatch.setattr(backend, "_shutdown_run", lambda run_id: shutdowns.append(run_id))
    monkeypatch.setattr("prml_vslam.pipeline.backend_ray.ray.shutdown", lambda: shutdowns.append("ray"))
    monkeypatch.setattr(backend._local_head, "shutdown", lambda: shutdowns.append("head"))

    backend.shutdown(preserve_local_head=True)

    assert shutdowns == ["run-1", "ray"]


def test_ray_backend_submits_via_coordinator_and_reads_via_backend(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path_config = PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts")
    backend = RayPipelineBackend(path_config=path_config, namespace="pytest-unit")
    run_config = _run_config(
        experiment_name="backend-unit",
        mode=PipelineMode.OFFLINE,
        output_dir=path_config.artifacts_dir,
        source_backend=VideoSourceConfig(video_path=Path("captures/dummy.mp4")),
        method=MethodId.VISTA,
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
            "read_payload": _Remote(lambda handle_id: np.full((2, 2, 3), 2, dtype=np.uint8)),
            "shutdown": _Remote(lambda: None),
        },
    )()

    monkeypatch.setattr("prml_vslam.pipeline.backend_ray.ray.get", lambda value: value)
    monkeypatch.setattr(backend, "_ensure_ray", lambda: None)
    monkeypatch.setattr(backend, "_create_coordinator", lambda run_id: fake_coordinator)
    monkeypatch.setattr(backend, "_coordinator_for", lambda run_id: fake_coordinator)

    run_id = backend.submit_run(run_config=run_config, runtime_source="runtime")

    assert run_id == "backend-unit"
    assert submitted == [("backend-unit", "runtime")]
    assert backend.get_snapshot(run_id).state is RunState.COMPLETED
    assert backend.get_events(run_id) == []
    assert backend.read_payload(run_id, TransientPayloadRef(handle_id="payload", payload_kind="image")) is not None
    backend.stop_run(run_id)
    assert stopped == ["backend-unit"]


def test_ray_backend_submit_run_rejects_unavailable_stage_after_planning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path_config = PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts")
    backend = RayPipelineBackend(path_config=path_config, namespace="pytest-unit")
    run_config = _run_config(
        experiment_name="placeholder",
        mode=PipelineMode.OFFLINE,
        output_dir=path_config.artifacts_dir,
        source_backend=AdvioSourceConfig(
            sequence_id="advio-01",
            dataset_serving={
                "pose_source": "ground_truth",
                "pose_frame_mode": "provider_world",
            },
        ),
        method=MethodId.VISTA,
        emit_dense_points=True,
        evaluate_cloud=True,
    )
    created_runs: list[str] = []

    monkeypatch.setattr(backend, "_ensure_ray", lambda: None)
    monkeypatch.setattr(backend, "_create_coordinator", lambda run_id: created_runs.append(run_id))

    with pytest.raises(RuntimeError, match="no runtime is registered yet"):
        backend.submit_run(run_config=run_config)

    assert created_runs == []


def test_source_backend_config_delegates_video_resolution(tmp_path: Path) -> None:
    path_config = PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts")
    video_path = tmp_path / "resolver-demo.mp4"
    video_path.write_bytes(b"")

    resolved = VideoSourceConfig(video_path=video_path).setup_target(path_config=path_config)

    assert resolved.label == "Video 'resolver-demo.mp4'"


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
    actor._processed_frame_count = 0
    actor._packet_timestamps = deque(maxlen=20)
    monkeypatch.setattr(
        "prml_vslam.pipeline.ray_runtime.stage_actors.put_transient_payload",
        lambda array, **kwargs: (
            TransientPayloadRef(handle_id="frame", payload_kind=kwargs["payload_kind"], shape=np.asarray(array).shape),
            np.asarray(array),
        ),
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
def test_run_service_offline_vista_smoke(tmp_path: Path) -> None:
    path_config = PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts")
    service = RunService(path_config=path_config)
    run_config = _run_config(
        experiment_name="offline-smoke",
        mode=PipelineMode.OFFLINE,
        output_dir=path_config.artifacts_dir,
        source_backend=VideoSourceConfig(video_path=Path("captures/dummy.mp4")),
        method=MethodId.VISTA,
    )

    service.start_run(run_config=run_config, runtime_source=FakeOfflineSource())
    snapshot = _wait_for_terminal_snapshot(service)

    assert snapshot.state is RunState.COMPLETED
    assert snapshot.stage_outcomes[StageKey.SOURCE].status is StageStatus.COMPLETED
    assert snapshot.stage_outcomes[StageKey.SLAM].status is StageStatus.COMPLETED
    assert "trajectory_tum" in snapshot.artifacts
    service.shutdown()


@pytest.mark.skipif(
    os.getenv("PRML_VSLAM_RUN_RAY_SMOKE") != "1",
    reason="Ray end-to-end smoke tests remain opt-in while the real cluster startup path is environment-sensitive.",
)
def test_run_service_streaming_vista_smoke(tmp_path: Path) -> None:
    path_config = PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts")
    service = RunService(path_config=path_config)
    run_config = _run_config(
        experiment_name="streaming-smoke",
        mode=PipelineMode.STREAMING,
        output_dir=path_config.artifacts_dir,
        source_backend=VideoSourceConfig(video_path=Path("captures/dummy.mp4")),
        method=MethodId.VISTA,
    )

    service.start_run(run_config=run_config, runtime_source=FakeStreamingSource())
    snapshot = _wait_for_terminal_snapshot(service)

    assert snapshot.state is RunState.COMPLETED
    assert snapshot.stage_runtime_status[StageKey.SLAM].processed_items >= 3
    source_ref = snapshot.live_refs[StageKey.SOURCE]["source_rgb:image"]
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


def _run_config(
    *,
    experiment_name: str,
    mode: PipelineMode = PipelineMode.OFFLINE,
    output_dir: Path,
    source_backend,
    method: MethodId = MethodId.VISTA,
    max_frames: int | None = None,
    emit_dense_points: bool = True,
    emit_sparse_points: bool = True,
    reference_enabled: bool = False,
    trajectory_eval_enabled: bool = False,
    trajectory_baseline: ReferenceSource = ReferenceSource.GROUND_TRUTH,
    evaluate_cloud: bool = False,
) -> RunConfig:
    return build_run_config(
        experiment_name=experiment_name,
        mode=mode,
        output_dir=output_dir,
        source_backend=source_backend,
        method=method,
        max_frames=max_frames,
        emit_dense_points=emit_dense_points,
        emit_sparse_points=emit_sparse_points,
        reference_enabled=reference_enabled,
        trajectory_eval_enabled=trajectory_eval_enabled,
        trajectory_baseline=trajectory_baseline,
        evaluate_cloud=evaluate_cloud,
    )


def _plan_with_stages(
    *,
    tmp_path: Path,
    run_config: RunConfig,
    stage_keys: list[StageKey],
) -> RunPlan:
    return RunPlan(
        run_id=run_config.experiment_name,
        mode=run_config.mode,
        artifact_root=tmp_path / run_config.experiment_name,
        source=PlannedSource(source_id="video", video_path=Path("captures/demo.mp4")),
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
    index = ObservationSequenceIndex(
        source_id="test",
        sequence_id="test-sequence",
        observation_count=1,
        rows=[
            ObservationIndexEntry(
                seq=0,
                timestamp_ns=0,
                rgb_path=Path("rgb.npy"),
                depth_path=Path("depth.npy"),
                T_world_camera=FrameTransform(
                    qx=0.0,
                    qy=0.0,
                    qz=0.0,
                    qw=1.0,
                    tx=0.0,
                    ty=0.0,
                    tz=0.0,
                    source_frame=CAMERA_RDF_FRAME,
                ),
                intrinsics={
                    "fx": 32.0,
                    "fy": 32.0,
                    "cx": 15.5,
                    "cy": 15.5,
                    "width_px": 32,
                    "height_px": 32,
                },
                provenance=ObservationProvenance(source_id="test", sequence_id="test-sequence"),
            )
        ],
    )
    index_path = payload_root / "observations.json"
    index_path.write_text(json.dumps(index.model_dump(mode="json"), indent=2), encoding="utf-8")
    return PreparedBenchmarkInputs(
        observation_sequences=[
            ObservationSequenceRef(
                source_id="test",
                sequence_id="test-sequence",
                index_path=index_path,
                payload_root=payload_root,
                observation_count=1,
            )
        ]
    )


def _placement_run_config(*, placement: dict[str, dict[str, dict[str, float]]] | None = None) -> RunConfig:
    run_config = _run_config(
        experiment_name="placement-demo",
        mode=PipelineMode.OFFLINE,
        output_dir=Path(".artifacts"),
        source_backend=VideoSourceConfig(video_path=Path("captures/demo.mp4")),
        method=MethodId.VISTA,
    )
    if placement is None:
        return run_config
    stages = run_config.stages
    updates = {}
    for stage_name, stage_placement in placement.items():
        resources = stage_placement.get("resources", {})
        updates[stage_name] = getattr(stages, stage_name).model_copy(
            update={
                "num_cpus": resources.get("CPU"),
                "num_gpus": resources.get("GPU"),
            }
        )
    return run_config.model_copy(update={"stages": stages.model_copy(update=updates)})


def _test_backend_config(*, default_cpu: float, default_gpu: float) -> VistaSlamBackendConfig:
    class TestVistaBackendConfig(VistaSlamBackendConfig):
        @property
        def default_resources(self) -> dict[str, float]:
            return {"CPU": default_cpu, "GPU": default_gpu}

    return TestVistaBackendConfig()
