"""Tests for the target pipeline runtime skeleton."""

from __future__ import annotations

from pathlib import Path

import pytest

from prml_vslam.interfaces.ingest import PreparedBenchmarkInputs, SequenceManifest, SourceStageOutput
from prml_vslam.interfaces.slam import ArtifactRef, SlamArtifacts
from prml_vslam.pipeline.contracts.events import StageOutcome
from prml_vslam.pipeline.contracts.plan import RunPlan, RunPlanStage
from prml_vslam.pipeline.contracts.provenance import StageStatus
from prml_vslam.pipeline.contracts.request import PipelineMode, VideoSourceSpec
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.runner import StageResultStore, StageRunner
from prml_vslam.pipeline.runtime_manager import RuntimeManager
from prml_vslam.pipeline.stages.base.config import StageConfig
from prml_vslam.pipeline.stages.base.contracts import StageResult, StageRuntimeStatus, StageRuntimeUpdate
from prml_vslam.pipeline.stages.base.proxy import RuntimeCapability
from prml_vslam.utils import BaseData


class _RuntimeInput(BaseData):
    label: str


class _StreamItem(BaseData):
    seq: int


class _FakeOfflineRuntime:
    def __init__(self, *, stage_key: StageKey = StageKey.INGEST, fail: bool = False) -> None:
        self.stage_key = stage_key
        self.fail = fail
        self.stopped = False

    def status(self) -> StageRuntimeStatus:
        return StageRuntimeStatus(stage_key=self.stage_key, lifecycle_state=StageStatus.RUNNING)

    def stop(self) -> None:
        self.stopped = True

    def run_offline(self, input_payload: _RuntimeInput) -> StageResult:
        if self.fail:
            raise ValueError("runtime boom")
        outcome = StageOutcome(
            stage_key=self.stage_key,
            status=StageStatus.COMPLETED,
            config_hash="config",
            input_fingerprint=input_payload.label,
        )
        return StageResult(
            stage_key=self.stage_key,
            payload=SequenceManifest(sequence_id=input_payload.label),
            outcome=outcome,
            final_runtime_status=StageRuntimeStatus(
                stage_key=self.stage_key,
                lifecycle_state=StageStatus.COMPLETED,
            ),
        )


class _FakeStreamingRuntime(_FakeOfflineRuntime):
    def __init__(self) -> None:
        super().__init__(stage_key=StageKey.SLAM)
        self.items: list[_StreamItem] = []

    def start_streaming(self, input_payload: _RuntimeInput) -> None:
        self.items.append(_StreamItem(seq=len(input_payload.label)))

    def submit_stream_item(self, item: _StreamItem) -> None:
        self.items.append(item)

    def drain_runtime_updates(self, max_items: int | None = None) -> list[StageRuntimeUpdate]:
        del max_items
        return []

    def finish_streaming(self) -> StageResult:
        outcome = StageOutcome(
            stage_key=StageKey.SLAM,
            status=StageStatus.COMPLETED,
            config_hash="config",
            input_fingerprint="stream",
        )
        return StageResult(
            stage_key=StageKey.SLAM,
            payload=None,
            outcome=outcome,
            final_runtime_status=StageRuntimeStatus(
                stage_key=StageKey.SLAM,
                lifecycle_state=StageStatus.COMPLETED,
                processed_items=len(self.items),
            ),
        )


def _plan(mode: PipelineMode = PipelineMode.OFFLINE) -> RunPlan:
    return RunPlan(
        run_id="runtime-skeleton",
        mode=mode,
        artifact_root=Path(".artifacts/runtime-skeleton"),
        source=VideoSourceSpec(video_path=Path("captures/demo.mp4")),
        stages=[
            RunPlanStage(key=StageKey.INGEST),
            RunPlanStage(key=StageKey.SLAM),
            RunPlanStage(key=StageKey.SUMMARY, available=False, availability_reason="placeholder"),
        ],
    )


def _completed_outcome(stage_key: StageKey) -> StageOutcome:
    return StageOutcome(
        stage_key=stage_key,
        status=StageStatus.COMPLETED,
        config_hash="config",
        input_fingerprint="input",
    )


def test_result_store_reads_target_source_and_slam_payloads() -> None:
    store = StageResultStore()
    manifest = SequenceManifest(sequence_id="seq-1")
    benchmark_inputs = PreparedBenchmarkInputs()
    slam_artifacts = SlamArtifacts(
        trajectory_tum=ArtifactRef(path=Path("slam/trajectory.tum"), kind="tum", fingerprint="traj"),
    )
    ingest_result = StageResult(
        stage_key=StageKey.INGEST,
        payload=SourceStageOutput(sequence_manifest=manifest, benchmark_inputs=benchmark_inputs),
        outcome=_completed_outcome(StageKey.INGEST),
        final_runtime_status=StageRuntimeStatus(stage_key=StageKey.INGEST, lifecycle_state=StageStatus.COMPLETED),
    )
    slam_result = StageResult(
        stage_key=StageKey.SLAM,
        payload=slam_artifacts,
        outcome=_completed_outcome(StageKey.SLAM),
        final_runtime_status=StageRuntimeStatus(stage_key=StageKey.SLAM, lifecycle_state=StageStatus.COMPLETED),
    )

    store.put(ingest_result)
    store.put(slam_result)

    assert ingest_result.payload == SourceStageOutput(sequence_manifest=manifest, benchmark_inputs=benchmark_inputs)
    assert store.require_sequence_manifest() == manifest
    assert store.require_benchmark_inputs() == benchmark_inputs
    assert store.require_slam_artifacts() == slam_artifacts
    assert [outcome.stage_key for outcome in store.ordered_outcomes()] == [StageKey.INGEST, StageKey.SLAM]


def test_result_store_reads_target_source_output_payload() -> None:
    store = StageResultStore()
    manifest = SequenceManifest(sequence_id="seq-1")
    benchmark_inputs = PreparedBenchmarkInputs()
    store.put(
        StageResult(
            stage_key=StageKey.INGEST,
            payload=SourceStageOutput(sequence_manifest=manifest, benchmark_inputs=benchmark_inputs),
            outcome=_completed_outcome(StageKey.INGEST),
            final_runtime_status=StageRuntimeStatus(
                stage_key=StageKey.INGEST,
                lifecycle_state=StageStatus.COMPLETED,
            ),
        )
    )

    assert store.require_sequence_manifest() == manifest
    assert store.require_benchmark_inputs() == benchmark_inputs


def test_result_store_reports_missing_dependencies() -> None:
    store = StageResultStore()

    with pytest.raises(RuntimeError, match="SequenceManifest"):
        store.require_sequence_manifest()
    with pytest.raises(RuntimeError, match="slam"):
        store.require_result(StageKey.SLAM)


def test_stage_runner_records_success_and_failure_callbacks() -> None:
    store = StageResultStore()
    runner = StageRunner(store)
    started: list[StageKey] = []
    completed: list[StageKey] = []
    failed: list[StageKey] = []

    result = runner.run_offline_stage(
        stage_key=StageKey.INGEST,
        runtime=_FakeOfflineRuntime(),
        input_payload=_RuntimeInput(label="seq-1"),
        stage_config=StageConfig(stage_key=StageKey.INGEST),
        config_hash="config",
        input_fingerprint="seq-1",
        on_stage_started=started.append,
        on_stage_completed=lambda stage_key, _result: completed.append(stage_key),
        on_stage_failed=lambda stage_key, _outcome: failed.append(stage_key),
    )

    assert result.stage_key is StageKey.INGEST
    assert store.require_sequence_manifest().sequence_id == "seq-1"
    assert started == [StageKey.INGEST]
    assert completed == [StageKey.INGEST]
    assert failed == []

    with pytest.raises(ValueError, match="runtime boom"):
        runner.run_offline_stage(
            stage_key=StageKey.SLAM,
            runtime=_FakeOfflineRuntime(stage_key=StageKey.SLAM, fail=True),
            input_payload=_RuntimeInput(label="slam"),
            stage_config=StageConfig(stage_key=StageKey.SLAM),
            config_hash="config",
            input_fingerprint="slam",
            on_stage_failed=lambda stage_key, _outcome: failed.append(stage_key),
        )
    assert failed == [StageKey.SLAM]


def test_runtime_manager_preflight_is_lazy_and_checks_capabilities() -> None:
    allocations: list[StageKey] = []
    manager = RuntimeManager()
    manager.register(
        StageKey.INGEST,
        factory=lambda: allocations.append(StageKey.INGEST) or _FakeOfflineRuntime(),
        capabilities=frozenset({RuntimeCapability.OFFLINE}),
    )
    manager.register(
        StageKey.SLAM,
        factory=lambda: allocations.append(StageKey.SLAM) or _FakeOfflineRuntime(stage_key=StageKey.SLAM),
        capabilities=frozenset({RuntimeCapability.OFFLINE}),
    )

    result = manager.preflight(_plan(mode=PipelineMode.STREAMING))

    assert allocations == []
    assert result.missing_runtime_keys == []
    assert result.unsupported_capabilities == {
        StageKey.SLAM: [RuntimeCapability.LIVE_UPDATES, RuntimeCapability.STREAMING]
    }
    with pytest.raises(RuntimeError, match="No runtime registered"):
        manager.runtime_for(StageKey.SUMMARY)


def test_runtime_manager_accepts_streaming_slam_with_live_updates() -> None:
    manager = RuntimeManager()
    manager.register(
        StageKey.INGEST,
        factory=_FakeOfflineRuntime,
        capabilities=frozenset({RuntimeCapability.OFFLINE}),
    )
    manager.register(
        StageKey.SLAM,
        factory=_FakeStreamingRuntime,
        capabilities=frozenset({RuntimeCapability.LIVE_UPDATES, RuntimeCapability.STREAMING}),
    )

    result = manager.preflight(_plan(mode=PipelineMode.STREAMING))

    assert result.ok
    assert result.unsupported_capabilities == {}


def test_runtime_manager_constructs_proxy_lazily() -> None:
    allocations: list[StageKey] = []
    manager = RuntimeManager()
    manager.register(
        StageKey.INGEST,
        factory=lambda: allocations.append(StageKey.INGEST) or _FakeOfflineRuntime(),
        capabilities=frozenset({RuntimeCapability.OFFLINE}),
        executor_id="local-ingest",
        resource_assignment={"CPU": 1.0},
    )

    proxy = manager.runtime_for(StageKey.INGEST)
    same_proxy = manager.runtime_for(StageKey.INGEST)

    assert proxy is same_proxy
    assert allocations == [StageKey.INGEST]
    assert proxy.offline().run_offline(_RuntimeInput(label="seq-1")).stage_key is StageKey.INGEST
    status = proxy.status()
    assert status.executor_id == "local-ingest"
    assert status.submitted_count == 1
    assert status.completed_count == 1
    assert status.in_flight_count == 0


def test_runtime_manager_rejects_unimplemented_ray_proxy_deployment() -> None:
    manager = RuntimeManager()
    manager.register(
        StageKey.INGEST,
        factory=_FakeOfflineRuntime,
        capabilities=frozenset({RuntimeCapability.OFFLINE}),
        deployment_kind="ray",
    )

    preflight = manager.preflight(_plan())
    assert preflight.unsupported_deployments == {StageKey.INGEST: "ray"}
    with pytest.raises(RuntimeError, match="unsupported deployment kinds"):
        preflight.raise_for_errors()

    with pytest.raises(NotImplementedError, match="requested deployment_kind='ray'"):
        manager.runtime_for(StageKey.INGEST)


def test_stage_runtime_proxy_exposes_only_supported_views() -> None:
    manager = RuntimeManager()
    manager.register(
        StageKey.SLAM,
        factory=_FakeStreamingRuntime,
        capabilities=frozenset({RuntimeCapability.STREAMING}),
    )
    proxy = manager.runtime_for(StageKey.SLAM)

    with pytest.raises(RuntimeError, match="does not support 'offline'"):
        proxy.offline()

    streaming = proxy.streaming()
    streaming.start_streaming(_RuntimeInput(label="run"))
    streaming.submit_stream_item(_StreamItem(seq=7))
    result = streaming.finish_streaming()

    assert result.stage_key is StageKey.SLAM
    assert proxy.status().submitted_count == 3
    assert proxy.status().completed_count == 3
