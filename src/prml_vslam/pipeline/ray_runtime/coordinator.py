"""Authoritative per-run coordinator for event-first execution.

The coordinator owns the runtime truth for one run: it records
:class:`RunEvent` values, projects the live snapshot, manages bounded transient
payload handles, fans events out to sinks, and coordinates the streaming credit
loop. Stage helpers and stage actors do work, but this actor decides how that
work is sequenced and observed.
"""

from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import ray
from ray.actor import ActorHandle

from prml_vslam.interfaces import CameraIntrinsics, FramePacket, FramePacketProvenance, FrameTransform
from prml_vslam.interfaces.alignment import GroundAlignmentMetadata
from prml_vslam.interfaces.ingest import SourceStageOutput
from prml_vslam.methods.descriptors import BackendDescriptor
from prml_vslam.pipeline.backend import PipelineRuntimeSource
from prml_vslam.pipeline.config import RunConfig
from prml_vslam.pipeline.contracts.events import (
    ArtifactRegistered,
    RunCompleted,
    RunEvent,
    RunFailed,
    RunStarted,
    RunStopped,
    RunStopRequested,
    RunSubmitted,
    StageCompleted,
    StageFailed,
    StageOutcome,
    StageQueued,
    StageStarted,
    StageStatus,
)
from prml_vslam.pipeline.contracts.mode import PipelineMode
from prml_vslam.pipeline.contracts.plan import RunPlan
from prml_vslam.pipeline.contracts.provenance import ArtifactRef, StageCacheInfo
from prml_vslam.pipeline.contracts.runtime import RunSnapshot, RunState
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.execution_context import StageExecutionContext
from prml_vslam.pipeline.finalization import stable_hash
from prml_vslam.pipeline.ray_runtime.common import (
    DEFAULT_MAX_FRAMES_IN_FLIGHT,
    EVENT_RING_LIMIT,
    HANDLE_LIMIT,
    HandlePayload,
    clean_actor_options,
    coordinator_actor_name,
    ts_ns,
)
from prml_vslam.pipeline.ray_runtime.stage_actors import PacketSourceActor
from prml_vslam.pipeline.runner import StageResultStore, StageRunner
from prml_vslam.pipeline.runtime_manager import RuntimeManager
from prml_vslam.pipeline.sinks import JsonlEventSink
from prml_vslam.pipeline.snapshot_projector import SnapshotProjector
from prml_vslam.pipeline.stage_cache import ContentFingerprinter, StageCacheKey, StageCacheStore
from prml_vslam.pipeline.stages.base.binding import RuntimeBuildContext, StageInputContext
from prml_vslam.pipeline.stages.base.config import StageCacheMode, StageConfig
from prml_vslam.pipeline.stages.base.contracts import (
    StageResult,
    StageRuntimeStatus,
    StageRuntimeUpdate,
    VisualizationIntent,
    VisualizationItem,
)
from prml_vslam.pipeline.stages.base.handles import TransientPayloadRef
from prml_vslam.pipeline.stages.base.proxy import RuntimeCapability, StageRuntimeProxy
from prml_vslam.pipeline.stages.bindings import stage_binding_for
from prml_vslam.pipeline.stages.reconstruction.visualization import (
    MESH_ARTIFACT,
    POINT_CLOUD_ARTIFACT,
    ROLE_RECONSTRUCTION_MESH,
    ROLE_RECONSTRUCTION_POINT_CLOUD,
)
from prml_vslam.pipeline.stages.slam import SlamFrameInput, SlamStageRuntime
from prml_vslam.pipeline.stages.source.visualization import SourceVisualizationAdapter
from prml_vslam.protocols.source import OfflineSequenceSource, StreamingSequenceSource
from prml_vslam.utils import Console, PathConfig, RunArtifactPaths

_TERMINAL_STATES = {RunState.COMPLETED, RunState.FAILED, RunState.STOPPED}


@dataclass(frozen=True, slots=True)
class _StageCacheRuntimeContext:
    """Resolved cache state for one stage execution attempt."""

    store: StageCacheStore
    key: StageCacheKey
    can_read: bool
    can_write: bool


def _artifact_visualizations(artifacts: dict[str, ArtifactRef]) -> list[VisualizationItem]:
    visualizations: list[VisualizationItem] = []
    dense_points = artifacts.get("dense_points_ply")
    if dense_points is not None:
        visualizations.append(
            VisualizationItem(
                intent=VisualizationIntent.POINT_CLOUD,
                role=ROLE_RECONSTRUCTION_POINT_CLOUD,
                artifact_refs={POINT_CLOUD_ARTIFACT: dense_points},
                space="world",
                metadata={"reconstruction_id": "slam"},
            )
        )
    reference_cloud = artifacts.get("reference_cloud")
    if reference_cloud is not None:
        visualizations.append(
            VisualizationItem(
                intent=VisualizationIntent.POINT_CLOUD,
                role=ROLE_RECONSTRUCTION_POINT_CLOUD,
                artifact_refs={POINT_CLOUD_ARTIFACT: reference_cloud},
                space="world",
                metadata={"reconstruction_id": "reference"},
            )
        )
    reference_mesh = artifacts.get("reference_mesh")
    if reference_mesh is not None:
        visualizations.append(
            VisualizationItem(
                intent=VisualizationIntent.MESH,
                role=ROLE_RECONSTRUCTION_MESH,
                artifact_refs={MESH_ARTIFACT: reference_mesh},
                space="world",
                metadata={"reconstruction_id": "reference"},
            )
        )
    return visualizations


@ray.remote(num_cpus=1, max_restarts=0, max_task_retries=0)
class RunCoordinatorActor:
    """Own one run's state, event log, and live execution coordination."""

    def __init__(self, *, run_id: str, namespace: str) -> None:
        self._console = Console(__name__).child(self.__class__.__name__).child(run_id)
        self._run_id = run_id
        self._namespace = namespace
        self._snapshot: RunSnapshot = RunSnapshot(run_id=run_id)
        self._projector = SnapshotProjector()
        self._event_counter = 0
        self._events: list[RunEvent] = []
        self._handle_refs: dict[str, HandlePayload] = {}
        self._handle_order: deque[str] = deque()
        self._lock = threading.Lock()
        self._stop_requested = False
        self._source_finished = False
        self._streaming_finalized = False
        self._in_flight_frames = 0
        self._streaming_done = threading.Event()
        self._jsonl_sink: JsonlEventSink | None = None
        self._rerun_sink: ActorHandle | None = None
        self._rerun_sink_last_call: ray.ObjectRef[None] | None = None
        self._rerun_sink_submission_count = 0
        self._rerun_sink_pending_count = 0
        self._worker: threading.Thread | None = None
        self._source_actor: ActorHandle | None = None
        self._streaming_runtime_manager: RuntimeManager | None = None
        self._slam_runtime_proxy: StageRuntimeProxy | None = None
        self._run_config: RunConfig | None = None
        self._plan: RunPlan | None = None
        self._backend_descriptor: BackendDescriptor | None = None
        self._result_store = StageResultStore()
        self._stage_runner = StageRunner(self._result_store)
        self._source_visualization_adapter = SourceVisualizationAdapter()
        self._streaming_error: str | None = None
        self._path_config: PathConfig | None = None

    def start(
        self, *, run_config: RunConfig, plan: RunPlan, path_config: PathConfig, runtime_source: PipelineRuntimeSource
    ) -> None:
        """Initialize run-scoped state and spawn the worker thread."""
        if self._worker is not None and self._worker.is_alive():
            raise RuntimeError(f"Run '{self._run_id}' is already active.")
        self._console.info(
            "Starting run '%s' in %s mode with %d planned stages.",
            plan.run_id,
            plan.mode.value,
            len(plan.stages),
        )
        self._run_config = run_config
        self._plan = plan
        self._path_config = path_config
        self._stop_requested = False
        self._source_finished = False
        self._streaming_finalized = False
        self._in_flight_frames = 0
        self._streaming_done = threading.Event()
        self._source_actor = None
        self._streaming_runtime_manager = None
        self._slam_runtime_proxy = None
        self._streaming_error = None
        self._result_store = StageResultStore()
        self._stage_runner = StageRunner(self._result_store)
        self._source_visualization_adapter = SourceVisualizationAdapter()
        self._snapshot = RunSnapshot(run_id=plan.run_id, plan=plan, active_executor="ray")
        run_paths = RunArtifactPaths.build(plan.artifact_root)
        self._jsonl_sink = JsonlEventSink(run_paths.summary_path.parent / "run-events.jsonl")
        self._console.info("Writing durable run events to '%s'.", self._jsonl_sink.path)
        self._rerun_sink = self._build_rerun_sink(run_config=run_config, run_paths=run_paths)
        self._record_event(RunSubmitted(event_id=self._next_event_id(), run_id=plan.run_id, ts_ns=ts_ns()))
        self._worker = threading.Thread(
            target=self._run,
            args=(run_config, plan, path_config, runtime_source),
            daemon=True,
            name=f"run-coordinator-{plan.run_id}",
        )
        self._worker.start()

    def stop(self) -> None:
        """Request graceful stop for the active run."""
        if self._snapshot.state in _TERMINAL_STATES:
            self._console.debug(
                "Ignoring stop request for terminal run '%s' with state '%s'.",
                self._run_id,
                self._snapshot.state.value,
            )
            return
        self._console.warning("Stop requested for run '%s'.", self._run_id)
        self._stop_requested = True
        self._record_event(RunStopRequested(event_id=self._next_event_id(), run_id=self._run_id, ts_ns=ts_ns()))
        if self._source_actor is not None:
            self._source_actor.stop.remote()
        if self._slam_runtime_proxy is not None:
            self._slam_runtime_proxy.stop()
        if self._streaming_done.is_set() and self._snapshot.state not in {RunState.COMPLETED, RunState.FAILED}:
            self._record_event(RunStopped(event_id=self._next_event_id(), run_id=self._run_id, ts_ns=ts_ns()))

    def snapshot(self) -> RunSnapshot:
        """Return a deep-copied projected snapshot for external readers."""
        with self._lock:
            return self._snapshot.model_copy(deep=True)

    def events(self, after_event_id: str | None = None, limit: int = 200) -> list[RunEvent]:
        """Return a bounded trailing slice of the in-memory event ring."""
        with self._lock:
            events = list(self._events)
        if after_event_id is not None:
            ids = [event.event_id for event in events]
            if after_event_id in ids:
                events = events[ids.index(after_event_id) + 1 :]
        return events[-limit:]

    def read_payload(self, handle_id: str) -> np.ndarray | None:
        """Resolve one coordinator-owned target transient payload ref locally."""
        return self._resolve_handle_payload(self._handle_refs.get(handle_id))

    def shutdown(self) -> None:
        """Stop worker-owned activity and close observer sidecars."""
        self._console.info("Shutting down run '%s'.", self._run_id)
        self._stop_requested = True
        if self._source_actor is not None:
            try:
                self._source_actor.stop.remote()
                ray.kill(self._source_actor)
            except Exception:
                pass
        if self._slam_runtime_proxy is not None:
            self._slam_runtime_proxy.stop()
        if self._worker is not None:
            self._worker.join(timeout=5.0)
        self._close_rerun_sink()

    def on_packet(
        self,
        *,
        packet: FramePacket,
        frame_ref: HandlePayload | None,
        depth_ref: HandlePayload | None,
        confidence_ref: HandlePayload | None,
        pointmap_ref: HandlePayload | None,
        intrinsics: CameraIntrinsics | None,
        pose: FrameTransform | None,
        provenance: FramePacketProvenance,
        processed_frame_count: int,
        measured_fps: float,
        frame_payload_ref: TransientPayloadRef | None = None,
        depth_payload_ref: TransientPayloadRef | None = None,
        pointmap_payload_ref: TransientPayloadRef | None = None,
    ) -> None:
        """Record one observed packet and forward it to streaming SLAM.

        Packet observation is live state only. Durable packet telemetry was
        retired with the WP-09C event cutover, while payloads remain behind
        coordinator-owned transient refs.
        """
        for payload_ref, handle in (
            (frame_payload_ref, frame_ref),
            (depth_payload_ref, depth_ref),
            (pointmap_payload_ref, pointmap_ref),
        ):
            if payload_ref is not None and handle is not None:
                self._remember_handle(payload_ref.handle_id, handle)
        source_status = StageRuntimeStatus(
            stage_key=StageKey.SOURCE,
            lifecycle_state=StageStatus.RUNNING,
            progress_message=f"received {processed_frame_count} frames",
            completed_steps=processed_frame_count,
            progress_unit="frames",
            processed_items=processed_frame_count,
            fps=measured_fps,
            updated_at_ns=ts_ns(),
        )
        with self._lock:
            self._snapshot = self._projector.apply_runtime_update(
                self._snapshot,
                StageRuntimeUpdate(
                    stage_key=StageKey.SOURCE,
                    timestamp_ns=ts_ns(),
                    runtime_status=source_status,
                ),
            )
        self._emit_source_visualization_update(
            packet=packet,
            frame_payload_ref=frame_payload_ref,
            depth_payload_ref=depth_payload_ref,
            pointmap_payload_ref=pointmap_payload_ref,
        )
        if self._stop_requested or self._slam_runtime_proxy is None:
            return
        self._in_flight_frames += 1
        frame_accepted = False
        try:
            self._submit_frame_to_slam_runtime(
                packet=packet,
                frame_ref=frame_ref,
                depth_ref=depth_ref,
                confidence_ref=confidence_ref,
                pointmap_ref=pointmap_ref,
                intrinsics=intrinsics,
                pose=pose,
                provenance=provenance,
            )
            frame_accepted = True
        except Exception as exc:
            self._console.error("Streaming SLAM frame submission failed for run '%s': %s", self._run_id, exc)
            self._streaming_error = str(exc)
            self._source_finished = True
            if self._source_actor is not None:
                self._source_actor.stop.remote()
        finally:
            self._in_flight_frames = max(0, self._in_flight_frames - 1)
            if frame_accepted and self._source_actor is not None and not self._stop_requested:
                self._source_actor.grant_credit.remote(1)
        if frame_accepted:
            self._publish_slam_runtime_updates(self._drain_slam_runtime_updates())
        if self._source_finished and self._in_flight_frames == 0:
            self._finalize_streaming()

    def grant_slam_source_credit(self, *, credit_count: int = 1) -> None:
        """Release source credits after SLAM accepts a frame without finalizing.

        Streaming finalization is now gated by live runtime-update draining and
        the coordinator's in-flight frame count rather than legacy durable
        backend-notice events.
        """
        if self._source_actor is not None and not self._stop_requested:
            self._source_actor.grant_credit.remote(credit_count)

    def on_slam_runtime_updates(
        self,
        *,
        updates: list[StageRuntimeUpdate],
    ) -> None:
        """Forward live SLAM runtime updates to observer sinks."""
        self._cache_slam_runtime_payloads(updates)
        with self._lock:
            for update in updates:
                self._snapshot = self._projector.apply_runtime_update(self._snapshot, update)
        if self._rerun_sink is None:
            return
        payload_resolver = self._self_actor_handle()
        for update in updates:
            self._submit_rerun_update(update=update, payload_resolver=payload_resolver)

    def _submit_frame_to_slam_runtime(
        self,
        *,
        packet: FramePacket,
        frame_ref: HandlePayload | None,
        depth_ref: HandlePayload | None,
        confidence_ref: HandlePayload | None,
        pointmap_ref: HandlePayload | None,
        intrinsics: CameraIntrinsics | None,
        pose: FrameTransform | None,
        provenance: FramePacketProvenance,
    ) -> None:
        if self._slam_runtime_proxy is None:
            raise RuntimeError("Streaming SLAM runtime has not been started.")
        self._stage_runner.submit_stream_item(
            runtime=self._slam_runtime_proxy.streaming(),
            item=SlamFrameInput(
                frame=FramePacket(
                    seq=packet.seq,
                    timestamp_ns=packet.timestamp_ns,
                    rgb=self._resolve_handle_payload(frame_ref),
                    depth=self._resolve_handle_payload(depth_ref),
                    confidence=self._resolve_handle_payload(confidence_ref),
                    pointmap=self._resolve_handle_payload(pointmap_ref),
                    point_cloud=packet.point_cloud,
                    intrinsics=intrinsics,
                    pose=pose,
                    provenance=provenance,
                )
            ),
        )

    def _drain_slam_runtime_updates(self) -> list[StageRuntimeUpdate]:
        if self._slam_runtime_proxy is None:
            return []
        return self._slam_runtime_proxy.live_updates().drain_runtime_updates(max_items=None)

    def _publish_slam_runtime_updates(self, updates: list[StageRuntimeUpdate]) -> None:
        if not updates:
            return
        try:
            self.on_slam_runtime_updates(updates=updates)
        except Exception as exc:  # pragma: no cover - best-effort observer routing
            self._console.warning("Failed to route live SLAM runtime updates for run '%s': %s", self._run_id, exc)

    def _cache_slam_runtime_payloads(self, updates: list[StageRuntimeUpdate]) -> None:
        runtime = self._active_slam_runtime()
        if runtime is None:
            return
        for update in updates:
            for item in update.visualizations:
                for ref in item.payload_refs.values():
                    payload = runtime.read_payload(ref)
                    if payload is not None:
                        self._remember_handle(ref.handle_id, payload)

    def _active_slam_runtime(self) -> SlamStageRuntime | None:
        if self._slam_runtime_proxy is None:
            return None
        runtime = self._slam_runtime_proxy.runtime
        if not isinstance(runtime, SlamStageRuntime):
            return None
        return runtime

    def on_source_eof(self) -> None:
        """Mark the streaming source as exhausted and finalize if drained."""
        self._console.info("Streaming source reached EOF for run '%s'.", self._run_id)
        self._source_finished = True
        if self._in_flight_frames == 0:
            self._finalize_streaming()

    def on_source_error(self, error_message: str) -> None:
        """Record a streaming-source failure and finalize once in-flight work drains."""
        self._console.error("Streaming source failed for run '%s': %s", self._run_id, error_message)
        self._streaming_error = error_message
        self._source_finished = True
        if self._in_flight_frames == 0:
            self._finalize_streaming()

    def _run(
        self,
        run_config: RunConfig,
        plan: RunPlan,
        path_config: PathConfig,
        runtime_source: PipelineRuntimeSource,
    ) -> None:
        try:
            self._record_event(RunStarted(event_id=self._next_event_id(), run_id=plan.run_id, ts_ns=ts_ns()))
            unavailable = [stage for stage in plan.stages if not stage.available]
            if unavailable:
                reason = unavailable[0].availability_reason or f"Stage '{unavailable[0].key.value}' is unavailable."
                raise RuntimeError(reason)
            slam_backend = run_config.stages.slam.backend
            if slam_backend is None:
                raise RuntimeError("RunConfig execution requires `[stages.slam.backend]`.")
            self._backend_descriptor = slam_backend.describe()
            if plan.mode is PipelineMode.OFFLINE:
                self._run_offline(
                    run_config=run_config,
                    plan=plan,
                    path_config=path_config,
                    runtime_source=runtime_source,
                )
            else:
                self._run_streaming(
                    run_config=run_config,
                    plan=plan,
                    path_config=path_config,
                    runtime_source=runtime_source,
                )
                self._streaming_done.wait()
        except Exception as exc:
            self._record_event(
                RunFailed(event_id=self._next_event_id(), run_id=self._run_id, ts_ns=ts_ns(), error_message=str(exc))
            )
            try:
                self._console.exception("Run '%s' failed: %s", self._run_id, exc)
            except Exception:
                pass
        finally:
            self._close_rerun_sink()

    def _run_offline(
        self,
        *,
        run_config: RunConfig,
        plan: RunPlan,
        path_config: PathConfig,
        runtime_source: OfflineSequenceSource | None,
    ) -> None:
        if runtime_source is None:
            if run_config.stages.source.backend is None:
                raise RuntimeError("RunConfig execution requires `[stages.source.backend]`.")
            source = run_config.stages.source.backend.setup_target(path_config=path_config)
        else:
            source = runtime_source
        self._console.info(
            "Offline source prepared via %s path.",
            "injected runtime source" if runtime_source is not None else "run-config source backend",
        )
        context = self._stage_execution_context(
            run_config=run_config,
            plan=plan,
            path_config=path_config,
        )
        runtime_manager = self._build_runtime_manager(plan=plan, source=source)
        runtime_manager.preflight(plan).raise_for_errors()
        self._result_store = StageResultStore()
        self._stage_runner = StageRunner(self._result_store)
        for stage in plan.stages:
            if not stage.available:
                continue
            stage_key = stage.key
            if stage_key is StageKey.TRAJECTORY_EVALUATION and self._stop_requested:
                continue
            runtime_proxy = runtime_manager.runtime_for(stage_key)
            stage_config = runtime_manager.stage_config(stage_key)
            input_payload = self._build_offline_stage_input(stage_key=stage_key, context=context)
            config_hash, input_fingerprint = self._failure_hash_inputs(stage_key=stage_key, context=context)
            stage_cache = self._stage_cache_context(stage_key=stage_key, stage_config=stage_config, context=context)
            if stage_cache is not None and stage_cache.can_read:
                cached_result = stage_cache.store.read(stage_cache.key, artifact_root=plan.artifact_root)
                if cached_result is not None:
                    self._emit_stage_started(stage_key)
                    self._result_store.put(cached_result)
                    self._record_stage_result(stage_key, cached_result)
                    continue
            self._stage_runner.run_offline_stage(
                stage_key=stage_key,
                runtime=runtime_proxy.offline(),
                input_payload=input_payload,
                stage_config=stage_config,
                config_hash=config_hash,
                input_fingerprint=input_fingerprint,
                on_stage_started=self._emit_stage_started,
                on_stage_completed=lambda completed_stage_key, result: self._record_stage_result(
                    completed_stage_key, result
                ),
                on_stage_failed=self._record_stage_failure,
                transform_result=(
                    None
                    if stage_cache is None
                    else lambda result, cache=stage_cache: self._apply_stage_cache_result(
                        cache=cache,
                        result=result,
                        artifact_root=plan.artifact_root,
                    )
                ),
            )
            self._publish_runtime_updates_from_proxy(runtime_proxy)
        terminal_state = "stopped" if self._stop_requested else "completed"
        self._console.info("Offline run '%s' %s.", self._run_id, terminal_state)
        self._record_event(
            RunStopped(event_id=self._next_event_id(), run_id=self._run_id, ts_ns=ts_ns())
            if self._stop_requested
            else RunCompleted(event_id=self._next_event_id(), run_id=self._run_id, ts_ns=ts_ns())
        )

    def _build_runtime_manager(self, *, plan: RunPlan, source: OfflineSequenceSource) -> RuntimeManager:
        manager = RuntimeManager()
        for stage in plan.stages:
            if not stage.available:
                continue
            binding = stage_binding_for(stage.key)
            factory = binding.runtime_factory(
                RuntimeBuildContext(
                    run_config=self._require_run_config(),
                    plan=plan,
                    path_config=self._require_path_config(),
                    source=source,
                )
            )
            if factory is None:
                continue
            manager.register(
                stage.key,
                factory=factory,
                capabilities=binding.runtime_capabilities(plan.mode),
                deployment_kind=binding.deployment_default,
                stage_config=binding.stage_config(self._require_run_config()),
            )
        return manager

    def _build_offline_stage_input(self, *, stage_key: StageKey, context: StageExecutionContext):
        return stage_binding_for(stage_key).build_offline_input(self._stage_input_context(context))

    def _failure_hash_inputs(self, *, stage_key: StageKey, context: StageExecutionContext) -> tuple[str, str]:
        fingerprint = stage_binding_for(stage_key).failure_fingerprint(self._stage_input_context(context))
        config_payload = fingerprint.config_payload
        input_payload = fingerprint.input_payload
        return stable_hash(config_payload), stable_hash(input_payload)

    def _content_hash_inputs(self, *, stage_key: StageKey, context: StageExecutionContext) -> tuple[str, str]:
        fingerprint = stage_binding_for(stage_key).failure_fingerprint(self._stage_input_context(context))
        fingerprinter = ContentFingerprinter()
        return fingerprinter.hash_value(fingerprint.config_payload), fingerprinter.hash_value(fingerprint.input_payload)

    def _stage_cache_context(
        self,
        *,
        stage_key: StageKey,
        stage_config: StageConfig,
        context: StageExecutionContext,
    ) -> _StageCacheRuntimeContext | None:
        if stage_key is StageKey.SUMMARY or not stage_config.cache.enabled:
            return None
        config_hash, input_fingerprint = self._content_hash_inputs(stage_key=stage_key, context=context)
        cache_root = (
            stage_config.cache.cache_root
            if stage_config.cache.cache_root is not None
            else context.path_config.artifacts_dir / "_stage_cache"
        )
        mode = stage_config.cache.mode
        return _StageCacheRuntimeContext(
            store=StageCacheStore(cache_root),
            key=StageCacheKey.build(
                stage_key=stage_key,
                config_hash=config_hash,
                input_fingerprint=input_fingerprint,
            ),
            can_read=mode in {StageCacheMode.READ_WRITE, StageCacheMode.READ_ONLY},
            can_write=mode in {StageCacheMode.READ_WRITE, StageCacheMode.WRITE_ONLY},
        )

    def _apply_stage_cache_result(
        self,
        *,
        cache: _StageCacheRuntimeContext,
        result: StageResult,
        artifact_root: Path,
    ) -> StageResult:
        cache_info = StageCacheInfo(cache_key=cache.key.cache_key, cache_root=cache.store.cache_root, hit=False)
        updated = result.model_copy(
            update={
                "outcome": result.outcome.model_copy(
                    update={
                        "config_hash": cache.key.config_hash,
                        "input_fingerprint": cache.key.input_fingerprint,
                        "cache": cache_info,
                    }
                )
            }
        )
        if not cache.can_write:
            return updated
        try:
            entry_path = cache.store.write(cache.key, result=updated, artifact_root=artifact_root)
        except Exception as exc:
            self._console.warning(
                "Failed to write stage cache entry for '%s' in run '%s': %s",
                cache.key.stage_key.value,
                self._run_id,
                exc,
            )
            return updated
        if entry_path is None:
            return updated
        return updated.model_copy(
            update={
                "outcome": updated.outcome.model_copy(
                    update={"cache": cache_info.model_copy(update={"entry_path": entry_path})}
                )
            }
        )

    def _record_stage_result(self, stage_key: StageKey, result: StageResult) -> None:
        payload = result.payload
        for artifact_key, artifact in result.outcome.artifacts.items():
            self._record_event(
                ArtifactRegistered(
                    event_id=self._next_event_id(),
                    run_id=self._run_id,
                    ts_ns=ts_ns(),
                    stage_key=stage_key,
                    artifact_key=artifact_key,
                    artifact=artifact,
                )
            )
        self._console.info(
            "Stage '%s' finished for run '%s' with status '%s' and %d artifacts.",
            stage_key.value,
            self._run_id,
            result.outcome.status.value,
            len(result.outcome.artifacts),
        )
        self._record_event(
            StageCompleted(
                event_id=self._next_event_id(),
                run_id=self._run_id,
                ts_ns=ts_ns(),
                stage_key=stage_key,
                outcome=result.outcome,
            )
        )
        if stage_key is StageKey.GRAVITY_ALIGNMENT and isinstance(payload, GroundAlignmentMetadata):
            self._submit_rerun_update(
                update=StageRuntimeUpdate(
                    stage_key=StageKey.GRAVITY_ALIGNMENT,
                    timestamp_ns=ts_ns(),
                    semantic_events=[payload],
                ),
                payload_resolver=None,
            )
        if stage_key is StageKey.SOURCE and isinstance(payload, SourceStageOutput):
            self._submit_source_reference_visualization_update(output=payload, artifacts=result.outcome.artifacts)
        self._submit_artifact_visualization_update(stage_key=stage_key, outcome=result.outcome)

    def _submit_artifact_visualization_update(self, *, stage_key: StageKey, outcome: StageOutcome) -> None:
        visualizations = _artifact_visualizations(outcome.artifacts)
        if not visualizations:
            return
        self._submit_rerun_update(
            update=StageRuntimeUpdate(stage_key=stage_key, timestamp_ns=ts_ns(), visualizations=visualizations),
            payload_resolver=None,
        )

    def _run_streaming(
        self,
        *,
        run_config: RunConfig,
        plan: RunPlan,
        path_config: PathConfig,
        runtime_source: StreamingSequenceSource | None,
    ) -> None:
        if runtime_source is None:
            raise RuntimeError("Streaming runs require an explicit runtime source.")
        context = self._stage_execution_context(
            run_config=run_config,
            plan=plan,
            path_config=path_config,
        )
        runtime_manager = self._build_runtime_manager(plan=plan, source=runtime_source)
        runtime_manager.preflight(plan).raise_for_errors()
        self._streaming_runtime_manager = runtime_manager
        self._result_store = StageResultStore()
        self._stage_runner = StageRunner(self._result_store)
        self._run_streaming_prepare(context=context, runtime_manager=runtime_manager)
        self._source_actor = PacketSourceActor.options(
            **clean_actor_options(
                {
                    "num_cpus": 1.0,
                    "num_gpus": 0.0,
                    "max_restarts": 0,
                    "max_task_retries": 0,
                }
            )
        ).remote(
            coordinator_name=coordinator_actor_name(plan.run_id),
            namespace=self._namespace,
        )
        self._console.info(
            "Streaming run '%s' started with %d in-flight frame credits.",
            self._run_id,
            DEFAULT_MAX_FRAMES_IN_FLIGHT,
        )
        self._source_actor.start_stream.remote(
            source=runtime_source,
            initial_credits=DEFAULT_MAX_FRAMES_IN_FLIGHT,
            loop=False,
        )

    def _run_streaming_prepare(self, *, context: StageExecutionContext, runtime_manager: RuntimeManager) -> None:
        for stage in context.plan.stages:
            if not stage.available:
                continue
            stage_key = stage.key
            if stage_key is StageKey.SOURCE:
                runtime_proxy = runtime_manager.runtime_for(stage_key)
                stage_config = runtime_manager.stage_config(stage_key)
                input_payload = self._build_offline_stage_input(stage_key=stage_key, context=context)
                config_hash, input_fingerprint = self._failure_hash_inputs(stage_key=stage_key, context=context)
                self._stage_runner.run_offline_stage(
                    stage_key=stage_key,
                    runtime=runtime_proxy.offline(),
                    input_payload=input_payload,
                    stage_config=stage_config,
                    config_hash=config_hash,
                    input_fingerprint=input_fingerprint,
                    on_stage_started=self._emit_stage_started,
                    on_stage_completed=lambda completed_stage_key, result: self._record_stage_result(
                        completed_stage_key, result
                    ),
                    on_stage_failed=self._record_stage_failure,
                )
                continue
            if stage_key is StageKey.SLAM:
                self._start_streaming_slam_runtime(context=context, runtime_manager=runtime_manager)
        if self._slam_runtime_proxy is None:
            raise RuntimeError("Streaming run requires an available SLAM runtime stage.")

    def _start_streaming_slam_runtime(
        self,
        *,
        context: StageExecutionContext,
        runtime_manager: RuntimeManager,
    ) -> None:
        stage_key = StageKey.SLAM
        runtime_proxy = runtime_manager.runtime_for(stage_key)
        stage_config = runtime_manager.stage_config(stage_key)
        config_hash, input_fingerprint = self._failure_hash_inputs(stage_key=stage_key, context=context)
        try:
            self._stage_runner.start_streaming_stage(
                stage_key=stage_key,
                runtime=runtime_proxy.streaming(),
                input_payload=stage_binding_for(stage_key).build_streaming_start_input(
                    self._stage_input_context(context)
                ),
                on_stage_started=self._emit_stage_started,
            )
        except Exception as exc:
            self._record_stage_failure(
                stage_key,
                stage_config.failure_outcome(
                    error_message=str(exc),
                    config_hash=config_hash,
                    input_fingerprint=input_fingerprint,
                ),
            )
            raise
        self._slam_runtime_proxy = runtime_proxy

    def _finalize_streaming(self) -> None:
        if self._streaming_finalized:
            return
        self._streaming_finalized = True
        finalize_reason = (
            "streaming error"
            if self._streaming_error is not None
            else "stop request"
            if self._stop_requested
            else "source finished and in-flight frames drained"
        )
        self._console.debug("Finalizing streaming run '%s' because %s.", self._run_id, finalize_reason)
        try:
            run_config = self._require_run_config()
            plan = self._require_plan()
            context = self._stage_execution_context(run_config=run_config, plan=plan)
            self._publish_slam_runtime_updates(self._drain_slam_runtime_updates())
            self._finalize_slam_streaming_stage(context=context)
            self._run_streaming_finalize_stages(context=context)
            if self._streaming_error is not None:
                self._console.error("Streaming run '%s' failed: %s", self._run_id, self._streaming_error)
                self._record_event(
                    RunFailed(
                        event_id=self._next_event_id(),
                        run_id=self._run_id,
                        ts_ns=ts_ns(),
                        error_message=self._streaming_error,
                    )
                )
            elif self._stop_requested:
                self._console.warning("Streaming run '%s' stopped.", self._run_id)
                self._record_event(RunStopped(event_id=self._next_event_id(), run_id=self._run_id, ts_ns=ts_ns()))
            else:
                self._console.info("Streaming run '%s' completed.", self._run_id)
                self._record_event(RunCompleted(event_id=self._next_event_id(), run_id=self._run_id, ts_ns=ts_ns()))
        finally:
            self._streaming_done.set()

    def _finalize_slam_streaming_stage(self, *, context: StageExecutionContext) -> None:
        if self._slam_runtime_proxy is None:
            return
        runtime_manager = self._require_streaming_runtime_manager()
        stage_key = StageKey.SLAM
        stage_config = runtime_manager.stage_config(stage_key)
        config_hash, input_fingerprint = self._failure_hash_inputs(stage_key=stage_key, context=context)
        try:
            slam_result = self._stage_runner.finish_streaming_stage(
                stage_key=stage_key,
                runtime=self._slam_runtime_proxy.streaming(),
            )
        except Exception as exc:
            error_message = str(exc)
            self._streaming_error = error_message
            outcome = stage_config.failure_outcome(
                error_message=error_message,
                config_hash=config_hash,
                input_fingerprint=input_fingerprint,
            )
            self._result_store.put(
                StageResult(
                    stage_key=stage_key,
                    payload=None,
                    outcome=outcome,
                    final_runtime_status=self._slam_runtime_proxy.status().model_copy(
                        update={"lifecycle_state": StageStatus.FAILED, "last_error": error_message}
                    ),
                )
            )
            self._record_stage_failure(stage_key, outcome)
            return

        if self._streaming_error is not None:
            failed_outcome = stage_config.failure_outcome(
                error_message=self._streaming_error,
                config_hash=config_hash,
                input_fingerprint=input_fingerprint,
                artifacts=slam_result.outcome.artifacts,
            )
            failed_result = slam_result.model_copy(
                update={
                    "outcome": failed_outcome,
                    "final_runtime_status": slam_result.final_runtime_status.model_copy(
                        update={
                            "lifecycle_state": StageStatus.FAILED,
                            "last_error": self._streaming_error,
                        }
                    ),
                }
            )
            self._result_store.put(failed_result)
            self._record_stage_failure(stage_key, failed_outcome)
            return

        if self._stop_requested and slam_result.outcome.status is not StageStatus.STOPPED:
            slam_result = slam_result.model_copy(
                update={
                    "outcome": slam_result.outcome.model_copy(update={"status": StageStatus.STOPPED}),
                    "final_runtime_status": slam_result.final_runtime_status.model_copy(
                        update={"lifecycle_state": StageStatus.STOPPED}
                    ),
                }
            )
            self._result_store.put(slam_result)
        self._record_stage_result(stage_key, slam_result)

    def _run_streaming_finalize_stages(self, *, context: StageExecutionContext) -> None:
        runtime_manager = self._require_streaming_runtime_manager()
        for stage in context.plan.stages:
            if not stage.available:
                continue
            stage_key = stage.key
            if stage_key in {StageKey.SOURCE, StageKey.SLAM}:
                continue
            if stage_key is StageKey.TRAJECTORY_EVALUATION and (
                self._streaming_error is not None or self._stop_requested
            ):
                continue
            runtime_proxy = runtime_manager.runtime_for(stage_key)
            stage_config = runtime_manager.stage_config(stage_key)
            input_payload = self._build_offline_stage_input(stage_key=stage_key, context=context)
            config_hash, input_fingerprint = self._failure_hash_inputs(stage_key=stage_key, context=context)
            self._stage_runner.run_offline_stage(
                stage_key=stage_key,
                runtime=runtime_proxy.offline(),
                input_payload=input_payload,
                stage_config=stage_config,
                config_hash=config_hash,
                input_fingerprint=input_fingerprint,
                on_stage_started=self._emit_stage_started,
                on_stage_completed=lambda completed_stage_key, result: self._record_stage_result(
                    completed_stage_key, result
                ),
                on_stage_failed=self._record_stage_failure,
            )
            self._publish_runtime_updates_from_proxy(runtime_proxy)

    def _build_rerun_sink(self, *, run_config: RunConfig, run_paths: RunArtifactPaths) -> ActorHandle | None:
        if not (run_config.visualization.connect_live_viewer or run_config.visualization.export_viewer_rrd):
            self._console.info("Rerun sink disabled for run '%s'.", self._run_id)
            return None
        from prml_vslam.pipeline.sinks.rerun import RerunSinkActor

        self._console.info("Rerun sink enabled for run '%s'.", self._run_id)
        return RerunSinkActor.remote(
            grpc_url=run_config.visualization.grpc_url if run_config.visualization.connect_live_viewer else None,
            target_path=run_paths.viewer_rrd_path if run_config.visualization.export_viewer_rrd else None,
            recording_id=self._run_id,
            frusta_history_window_streaming=run_config.visualization.frusta_history_window_streaming,
            show_tracking_trajectory=run_config.visualization.show_tracking_trajectory,
            log_source_rgb=run_config.visualization.log_source_rgb,
            log_diagnostic_preview=run_config.visualization.log_diagnostic_preview,
            log_camera_image_rgb=run_config.visualization.log_camera_image_rgb,
        )

    def _emit_stage_started(self, stage_key: StageKey) -> None:
        self._console.info("Stage '%s' started for run '%s'.", stage_key.value, self._run_id)
        self._record_event(
            StageQueued(event_id=self._next_event_id(), run_id=self._run_id, ts_ns=ts_ns(), stage_key=stage_key)
        )
        self._record_event(
            StageStarted(event_id=self._next_event_id(), run_id=self._run_id, ts_ns=ts_ns(), stage_key=stage_key)
        )

    def _record_stage_failure(self, stage_key: StageKey, outcome: StageOutcome) -> None:
        if self._snapshot.stage_outcomes.get(stage_key, None) is not None and self._snapshot.stage_outcomes[
            stage_key
        ].status in {
            StageStatus.COMPLETED,
            StageStatus.FAILED,
            StageStatus.STOPPED,
        }:
            return
        for artifact_key, artifact in outcome.artifacts.items():
            self._record_event(
                ArtifactRegistered(
                    event_id=self._next_event_id(),
                    run_id=self._run_id,
                    ts_ns=ts_ns(),
                    stage_key=stage_key,
                    artifact_key=artifact_key,
                    artifact=artifact,
                )
            )
        self._console.error(
            "Stage '%s' failed for run '%s': %s",
            stage_key.value,
            self._run_id,
            outcome.error_message or "unknown error",
        )
        self._record_event(
            StageFailed(
                event_id=self._next_event_id(),
                run_id=self._run_id,
                ts_ns=ts_ns(),
                stage_key=stage_key,
                outcome=outcome,
            )
        )

    def _record_event(
        self,
        event: RunEvent,
        *,
        project_to_snapshot: bool = True,
    ) -> None:
        with self._lock:
            if project_to_snapshot:
                self._snapshot = self._projector.apply(self._snapshot, event)
            self._events.append(event)
            if len(self._events) > EVENT_RING_LIMIT:
                self._console.debug("Trimming in-memory event ring to last %d events.", EVENT_RING_LIMIT)
                self._events = self._events[-EVENT_RING_LIMIT:]
        if self._jsonl_sink is not None:
            self._jsonl_sink.observe(event)

    def _emit_source_visualization_update(
        self,
        *,
        packet: FramePacket,
        frame_payload_ref: TransientPayloadRef | None,
        depth_payload_ref: TransientPayloadRef | None,
        pointmap_payload_ref: TransientPayloadRef | None,
    ) -> None:
        visualization_owner = self._run_config
        if visualization_owner is None or not visualization_owner.visualization.log_source_rgb:
            return
        visualizations = self._source_visualization_adapter.build_packet_items(
            packet=packet,
            frame_payload_ref=frame_payload_ref,
            depth_payload_ref=depth_payload_ref,
            pointmap_payload_ref=pointmap_payload_ref,
        )
        if not visualizations:
            return
        update = StageRuntimeUpdate(
            stage_key=StageKey.SOURCE,
            timestamp_ns=ts_ns(),
            visualizations=visualizations,
        )
        with self._lock:
            self._snapshot = self._projector.apply_runtime_update(self._snapshot, update)
        self._submit_rerun_update(update=update, payload_resolver=self._self_actor_handle())

    def _submit_source_reference_visualization_update(
        self,
        *,
        output: SourceStageOutput,
        artifacts: dict[str, ArtifactRef],
    ) -> None:
        visualizations = self._source_visualization_adapter.build_reference_items(
            output=output,
            artifact_refs=artifacts,
        )
        if not visualizations:
            return
        update = StageRuntimeUpdate(
            stage_key=StageKey.SOURCE,
            timestamp_ns=ts_ns(),
            visualizations=visualizations,
        )
        with self._lock:
            self._snapshot = self._projector.apply_runtime_update(self._snapshot, update)
        self._submit_rerun_update(update=update, payload_resolver=None)

    def _submit_rerun_update(
        self,
        *,
        update: StageRuntimeUpdate,
        payload_resolver: ActorHandle | None,
    ) -> None:
        if self._rerun_sink is None:
            return
        try:
            self._log_rerun_update_backlog(update)
            self._rerun_sink_last_call = self._rerun_sink.observe_update.remote(
                update=update,
                payload_resolver=payload_resolver,
            )
        except Exception as exc:  # pragma: no cover - best-effort sidecar submission
            self._console.warning(
                "Failed to submit Rerun sink runtime update for stage '%s': %s", update.stage_key.value, exc
            )

    def _publish_runtime_updates_from_proxy(self, runtime_proxy: StageRuntimeProxy) -> None:
        if RuntimeCapability.LIVE_UPDATES not in runtime_proxy.supported_capabilities:
            return
        updates = runtime_proxy.live_updates().drain_runtime_updates(max_items=None)
        if not updates:
            return
        with self._lock:
            for update in updates:
                self._snapshot = self._projector.apply_runtime_update(self._snapshot, update)
        for update in updates:
            self._submit_rerun_update(update=update, payload_resolver=None)

    def _self_actor_handle(self) -> ActorHandle:
        return ray.get_actor(coordinator_actor_name(self._run_id), namespace=self._namespace)

    def _log_rerun_update_backlog(self, update: StageRuntimeUpdate) -> None:
        self._rerun_sink_submission_count += 1
        if self._rerun_sink_last_call is None:
            return
        ready, _ = ray.wait([self._rerun_sink_last_call], timeout=0.0)
        if ready:
            self._rerun_sink_pending_count = 0
            return
        self._rerun_sink_pending_count += 1
        if self._rerun_sink_pending_count == 1 or self._rerun_sink_pending_count % 100 == 0:
            payload_refs = [
                (item.role, slot, ref.payload_kind, ref.shape, ref.dtype)
                for item in update.visualizations
                for slot, ref in item.payload_refs.items()
            ]
            self._console.warning(
                "Rerun sink sidecar is lagging: previous runtime update still pending for stage '%s' "
                "(submitted=%d, consecutive_pending=%d, refs=%s). Live viewer may lag behind the exported RRD.",
                update.stage_key.value,
                self._rerun_sink_submission_count,
                self._rerun_sink_pending_count,
                payload_refs,
            )

    def _remember_handle(self, handle_id: str, payload: HandlePayload) -> None:
        self._handle_refs[handle_id] = payload
        self._handle_order.append(handle_id)
        while len(self._handle_order) > HANDLE_LIMIT:
            stale_id = self._handle_order.popleft()
            self._console.debug("Evicting stale handle '%s' due to handle limit %d.", stale_id, HANDLE_LIMIT)
            self._handle_refs.pop(stale_id, None)

    def _resolve_handle_local(self, handle_id: str) -> np.ndarray | None:
        return self._resolve_handle_payload(self._handle_refs.get(handle_id))

    @staticmethod
    def _resolve_handle_payload(payload: HandlePayload | None) -> np.ndarray | None:
        if payload is None:
            return None
        if isinstance(payload, np.ndarray):
            return np.asarray(payload)
        return np.asarray(ray.get(payload))

    def _next_event_id(self) -> str:
        self._event_counter += 1
        return str(self._event_counter)

    def _close_rerun_sink(self) -> None:
        if self._rerun_sink is None:
            return
        try:
            self._submit_final_artifact_rerun_update()
            if self._rerun_sink_last_call is not None:
                ray.get(self._rerun_sink_last_call)
            self._rerun_sink_last_call = self._rerun_sink.close.remote()
            ray.get(self._rerun_sink_last_call)
        except Exception as exc:  # pragma: no cover - best-effort sidecar cleanup
            self._console.warning("Failed to close Rerun sink actor for run '%s': %s", self._run_id, exc)
        finally:
            try:
                ray.kill(self._rerun_sink, no_restart=True)
            except Exception:
                pass
            self._rerun_sink = None
            self._rerun_sink_last_call = None

    def _submit_final_artifact_rerun_update(self) -> None:
        visualizations = _artifact_visualizations(self._snapshot.artifacts)
        if not visualizations:
            return
        self._submit_rerun_update(
            update=StageRuntimeUpdate(stage_key=StageKey.SUMMARY, timestamp_ns=ts_ns(), visualizations=visualizations),
            payload_resolver=None,
        )

    def _require_run_config(self) -> RunConfig:
        if self._run_config is not None:
            return self._run_config
        raise RuntimeError("Run config is not initialized.")

    def _require_plan(self) -> RunPlan:
        if self._plan is None:
            raise RuntimeError("Run plan is not initialized.")
        return self._plan

    def _require_backend_descriptor(self) -> BackendDescriptor:
        if self._backend_descriptor is None:
            raise RuntimeError("Backend descriptor is not initialized.")
        return self._backend_descriptor

    def _require_path_config(self) -> PathConfig:
        if self._path_config is None:
            raise RuntimeError("Path config is not initialized.")
        return self._path_config

    def _require_streaming_runtime_manager(self) -> RuntimeManager:
        if self._streaming_runtime_manager is None:
            raise RuntimeError("Streaming runtime manager is not initialized.")
        return self._streaming_runtime_manager

    def _stage_execution_context(
        self,
        *,
        run_config: RunConfig,
        plan: RunPlan,
        path_config: PathConfig | None = None,
    ) -> StageExecutionContext:
        return StageExecutionContext(
            run_config=run_config,
            plan=plan,
            path_config=self._require_path_config() if path_config is None else path_config,
            run_paths=RunArtifactPaths.build(plan.artifact_root),
            backend_descriptor=self._require_backend_descriptor(),
        )

    def _stage_input_context(self, context: StageExecutionContext) -> StageInputContext:
        return StageInputContext(
            run_config=context.run_config,
            plan=context.plan,
            path_config=context.path_config,
            run_paths=context.run_paths,
            backend_descriptor=context.backend_descriptor,
            results=self._result_store,
        )


__all__ = ["RunCoordinatorActor"]
