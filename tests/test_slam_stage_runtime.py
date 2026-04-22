"""Tests for the target SLAM stage runtime."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from prml_vslam.benchmark.contracts import ReferenceSource
from prml_vslam.interfaces import FramePacket, FrameTransform
from prml_vslam.interfaces.ingest import PreparedBenchmarkInputs, SequenceManifest
from prml_vslam.interfaces.slam import ArtifactRef, SlamArtifacts, SlamSessionInit, SlamUpdate
from prml_vslam.methods.config_contracts import MethodId
from prml_vslam.pipeline.contracts.plan import RunPlan, RunPlanStage
from prml_vslam.pipeline.contracts.provenance import StageStatus
from prml_vslam.pipeline.contracts.request import PipelineMode, RunRequest, SlamStageConfig, VideoSourceSpec
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.contracts import VisualizationIntent
from prml_vslam.pipeline.stages.slam import SlamFrameInput, SlamOfflineInput, SlamStageRuntime, SlamStreamingStartInput
from prml_vslam.utils import PathConfig


class _FakeBackendFactory:
    def __init__(self, backend: _FakeBackend) -> None:
        self.backend = backend

    def build(self, backend_config, *, path_config: PathConfig | None = None) -> _FakeBackend:
        del backend_config, path_config
        return self.backend


class _FakeBackend:
    method_id = MethodId.MOCK

    def __init__(self, artifact_root: Path) -> None:
        self.artifact_root = artifact_root
        self.session = _FakeSession(artifact_root)

    def run_sequence(
        self,
        sequence: SequenceManifest,
        benchmark_inputs: PreparedBenchmarkInputs | None,
        baseline_source: ReferenceSource,
        *,
        backend_config,
        output_policy,
        artifact_root: Path,
    ) -> SlamArtifacts:
        del sequence, benchmark_inputs, baseline_source, backend_config, output_policy
        return _slam_artifacts(artifact_root)

    def start_session(self, **kwargs) -> _FakeSession:
        del kwargs
        return self.session


class _FakeSession:
    def __init__(self, artifact_root: Path) -> None:
        self.artifact_root = artifact_root
        self.pending: list[SlamUpdate] = []
        self.closed = False

    def step(self, frame: FramePacket) -> None:
        self.pending.append(
            SlamUpdate(
                seq=frame.seq,
                timestamp_ns=frame.timestamp_ns,
                source_seq=frame.seq,
                source_timestamp_ns=frame.timestamp_ns,
                is_keyframe=True,
                keyframe_index=frame.seq,
                pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=2.0, tz=3.0),
                image_rgb=np.zeros((2, 3, 3), dtype=np.uint8),
                depth_map=np.ones((2, 3), dtype=np.float32),
                preview_rgb=np.full((2, 3, 3), 127, dtype=np.uint8),
                pointmap=np.ones((2, 3, 3), dtype=np.float32),
                pose_updated=True,
                backend_warnings=["first warning"],
            )
        )

    def try_get_updates(self) -> list[SlamUpdate]:
        updates = self.pending
        self.pending = []
        return updates

    def close(self) -> SlamArtifacts:
        self.closed = True
        return _slam_artifacts(self.artifact_root)


def _request(tmp_path: Path) -> RunRequest:
    return RunRequest(
        experiment_name="slam-runtime",
        mode=PipelineMode.STREAMING,
        output_dir=tmp_path / ".artifacts",
        source=VideoSourceSpec(video_path=Path("captures/demo.mp4")),
        slam=SlamStageConfig(backend={"method_id": "mock"}),
    )


def _plan(tmp_path: Path, request: RunRequest) -> RunPlan:
    return RunPlan(
        run_id=request.experiment_name,
        mode=request.mode,
        artifact_root=tmp_path / ".artifacts" / request.experiment_name,
        source=request.source,
        stages=[RunPlanStage(key=StageKey.SLAM)],
    )


def _slam_artifacts(artifact_root: Path) -> SlamArtifacts:
    return SlamArtifacts(
        trajectory_tum=ArtifactRef(path=artifact_root / "slam" / "trajectory.tum", kind="tum", fingerprint="traj")
    )


def test_slam_runtime_offline_returns_stage_result(tmp_path: Path) -> None:
    request = _request(tmp_path).model_copy(update={"mode": PipelineMode.OFFLINE})
    plan = _plan(tmp_path, request)
    runtime = SlamStageRuntime(backend_factory=_FakeBackendFactory(_FakeBackend(plan.artifact_root)))

    result = runtime.run_offline(
        SlamOfflineInput(
            request=request,
            plan=plan,
            path_config=PathConfig(root=Path(__file__).resolve().parents[1], artifacts_dir=tmp_path / ".artifacts"),
            sequence_manifest=SequenceManifest(sequence_id="seq-1"),
            benchmark_inputs=None,
        )
    )

    assert result.stage_key is StageKey.SLAM
    assert result.outcome.status is StageStatus.COMPLETED
    assert isinstance(result.payload, SlamArtifacts)
    assert result.final_runtime_status.lifecycle_state is StageStatus.COMPLETED


def test_slam_runtime_streaming_emits_updates_and_transient_refs(tmp_path: Path) -> None:
    request = _request(tmp_path)
    plan = _plan(tmp_path, request)
    backend = _FakeBackend(plan.artifact_root)
    runtime = SlamStageRuntime(backend_factory=_FakeBackendFactory(backend))
    sequence_manifest = SequenceManifest(sequence_id="seq-1")

    runtime.start_streaming(
        SlamStreamingStartInput(
            request=request,
            plan=plan,
            path_config=PathConfig(root=Path(__file__).resolve().parents[1], artifacts_dir=tmp_path / ".artifacts"),
            session_init=SlamSessionInit(sequence_manifest=sequence_manifest),
        )
    )
    runtime.submit_stream_item(SlamFrameInput(frame=FramePacket(seq=1, timestamp_ns=10, rgb=np.zeros((2, 3, 3)))))
    updates = runtime.drain_runtime_updates()

    assert len(updates) == 1
    update = updates[0]
    semantic_update = update.semantic_events[0]
    assert isinstance(semantic_update, SlamUpdate)
    assert semantic_update.image_rgb is None
    assert semantic_update.depth_map is None
    assert semantic_update.preview_rgb is None
    assert semantic_update.pointmap is None
    assert update.runtime_status is not None
    assert update.runtime_status.processed_items == 1
    assert update.runtime_status.last_warning == "first warning"
    assert any(item.intent is VisualizationIntent.POINT_CLOUD for item in update.visualizations)

    refs = [ref for item in update.visualizations for ref in item.payload_refs.values()]
    assert refs
    assert all(runtime.read_payload(ref) is not None for ref in refs)
    assert not any("TransientPayloadRef" in repr(field.annotation) for field in SlamUpdate.model_fields.values())

    result = runtime.finish_streaming()
    assert result.outcome.status is StageStatus.COMPLETED
    assert isinstance(result.payload, SlamArtifacts)
    assert backend.session.closed is True
