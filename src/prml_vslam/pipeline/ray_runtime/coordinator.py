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
from typing import Any, Literal, cast

import numpy as np
import ray
from ray.actor import ActorHandle

from prml_vslam.align.trajectory_sim3.contracts import TrajectoryAlignmentArtifact
from prml_vslam.eval.trajectory_contracts import TrajectoryEvaluationManifest
from prml_vslam.interfaces import CameraIntrinsics, FrameTransform, Observation, ObservationProvenance
from prml_vslam.interfaces.alignment import GroundAlignmentMetadata
from prml_vslam.interfaces.artifacts import ArtifactRef
from prml_vslam.methods.stage import SlamStageRuntime
from prml_vslam.methods.stage.backend_config import SlamBackendConfig
from prml_vslam.methods.stage.visualization import (
    ROLE_KEYFRAME_DEPTH,
    ROLE_KEYFRAME_PINHOLE,
    ROLE_KEYFRAME_PREVIEW,
    ROLE_KEYFRAME_RGB,
    ROLE_MODEL_CAMERA_RGB,
    ROLE_MODEL_PINHOLE,
    ROLE_MODEL_PREVIEW,
    ROLE_SOURCE_RGB,
)
from prml_vslam.pipeline.backend import PipelineRuntimeSource
from prml_vslam.pipeline.config import RunConfig
from prml_vslam.pipeline.contracts.context import PipelineExecutionContext
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
from prml_vslam.pipeline.contracts.runtime import RunSnapshot, RunState
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.placement import actor_options_for_stage
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
from prml_vslam.pipeline.reuse import load_reused_stage_results
from prml_vslam.pipeline.runner import StageResultStore, StageRunner
from prml_vslam.pipeline.runtime_manager import RuntimeManager
from prml_vslam.pipeline.sinks import JsonlEventSink
from prml_vslam.pipeline.snapshot_projector import SnapshotProjector
from prml_vslam.pipeline.stages.base.contracts import (
    StageResult,
    StageRuntimeStatus,
    StageRuntimeUpdate,
    VisualizationIntent,
    VisualizationItem,
)
from prml_vslam.pipeline.stages.base.handles import TransientPayloadRef
from prml_vslam.pipeline.stages.base.proxy import StageRuntimeHandle
from prml_vslam.pipeline.stages.base.ray import RayStageRuntimeHandle
from prml_vslam.pipeline.stages.specs import stage_runtime_spec_for
from prml_vslam.sources.protocols import OfflineSequenceSource, StreamingSequenceSource
from prml_vslam.sources.stage.contracts import SourceStageOutput
from prml_vslam.sources.stage.visualization import ROLE_SOURCE_REFERENCE_TRAJECTORY, SourceVisualizationAdapter
from prml_vslam.utils import Console, JsonScalar, PathConfig, RunArtifactPaths
from prml_vslam.visualization.artifacts import artifact_visualizations

_TERMINAL_STATES = {RunState.COMPLETED, RunState.FAILED, RunState.STOPPED}
_RerunSinkKind = Literal["live", "export"]
_RERUN_ALL_DESTINATIONS: frozenset[_RerunSinkKind] = frozenset(("live", "export"))
_RERUN_EXPORT_DESTINATION: frozenset[_RerunSinkKind] = frozenset(("export",))
_RERUN_LIVE_DESTINATION: frozenset[_RerunSinkKind] = frozenset(("live",))
_FAILED_SLAM_DEPENDENT_STREAMING_FINALIZERS = frozenset(
    {
        StageKey.GRAVITY_ALIGNMENT,
        StageKey.TRAJECTORY_ALIGNMENT,
        StageKey.TRAJECTORY_EVALUATION,
        StageKey.RECONSTRUCTION,
        StageKey.CLOUD_ALIGNMENT,
        StageKey.CLOUD_EVALUATION,
    }
)


@dataclass
class _RerunSinkSidecar:
    kind: _RerunSinkKind
    actor: ActorHandle
    last_call: ray.ObjectRef[None] | None = None
    submission_count: int = 0
    pending_count: int = 0


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
        self._slam_submission_refs: list[ray.ObjectRef[None]] = []
        self._slam_submission_lock = threading.Lock()
        self._streaming_done = threading.Event()
        self._jsonl_sink: JsonlEventSink | None = None
        self._rerun_sinks: list[_RerunSinkSidecar] = []
        self._worker: threading.Thread | None = None
        self._source_actor: ActorHandle | None = None
        self._streaming_runtime_manager: RuntimeManager | None = None
        self._slam_runtime_proxy: StageRuntimeHandle | RayStageRuntimeHandle | None = None
        self._run_config: RunConfig | None = None
        self._plan: RunPlan | None = None
        self._slam_backend: SlamBackendConfig | None = None
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
        self._slam_submission_refs = []
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
        self._rerun_sinks = self._build_rerun_sinks(run_config=run_config, run_paths=run_paths)
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
        with self._lock:
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
        self._close_rerun_sinks()

    def on_packet(
        self,
        *,
        packet: Observation,
        frame_ref: HandlePayload | None,
        depth_ref: HandlePayload | None,
        confidence_ref: HandlePayload | None,
        pointmap_ref: HandlePayload | None,
        intrinsics: CameraIntrinsics | None,
        pose: FrameTransform | None,
        provenance: ObservationProvenance,
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
        try:
            submission_ref = self._submit_frame_to_slam_runtime(
                packet=packet,
                frame_ref=frame_ref,
                depth_ref=depth_ref,
                confidence_ref=confidence_ref,
                pointmap_ref=pointmap_ref,
                intrinsics=intrinsics,
                pose=pose,
                provenance=provenance,
            )
            if submission_ref is None:
                self._complete_inline_slam_submission()
            else:
                self._track_slam_submission(submission_ref)
        except Exception as exc:
            self._console.error("Streaming SLAM frame submission failed for run '%s': %s", self._run_id, exc)
            self._streaming_error = str(exc)
            self._source_finished = True
            if self._source_actor is not None:
                self._source_actor.stop.remote()
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
        if not self._has_rerun_sinks():
            return
        payload_resolver = self._self_actor_handle()
        self._submit_rerun_updates(updates=updates, payload_resolver=payload_resolver)

    def _submit_frame_to_slam_runtime(
        self,
        *,
        packet: Observation,
        frame_ref: HandlePayload | None,
        depth_ref: HandlePayload | None,
        confidence_ref: HandlePayload | None,
        pointmap_ref: HandlePayload | None,
        intrinsics: CameraIntrinsics | None,
        pose: FrameTransform | None,
        provenance: ObservationProvenance,
    ) -> ray.ObjectRef[None] | None:
        if self._slam_runtime_proxy is None:
            raise RuntimeError("Streaming SLAM runtime has not been started.")
        item = Observation(
            seq=packet.seq,
            timestamp_ns=packet.timestamp_ns,
            rgb=self._resolve_handle_payload(frame_ref),
            depth_m=self._resolve_handle_payload(depth_ref) if pose is not None else None,
            confidence=self._resolve_handle_payload(confidence_ref),
            pointmap_xyz=self._resolve_handle_payload(pointmap_ref) if pose is not None else None,
            point_cloud_xyz=packet.point_cloud_xyz if pose is not None else None,
            point_cloud_rgb=packet.point_cloud_rgb if pose is not None else None,
            intrinsics=intrinsics,
            T_world_camera=pose,
            arrival_timestamp_s=packet.arrival_timestamp_s,
            provenance=provenance,
        )
        if isinstance(self._slam_runtime_proxy, RayStageRuntimeHandle):
            return self._slam_runtime_proxy.submit_stream_item_async(item)
        self._stage_runner.submit_stream_item(runtime=self._slam_runtime_proxy, item=item)
        return None

    def _drain_slam_runtime_updates(self) -> list[StageRuntimeUpdate]:
        if self._slam_runtime_proxy is None:
            return []
        return self._slam_runtime_proxy.drain_runtime_updates(max_items=None)

    def _track_slam_submission(self, submission_ref: ray.ObjectRef[None]) -> None:
        with self._slam_submission_lock:
            self._slam_submission_refs.append(submission_ref)
            self._in_flight_frames += 1

    def _complete_inline_slam_submission(self) -> None:
        if self._source_actor is not None and not self._stop_requested:
            self._source_actor.grant_credit.remote(1)
        self._publish_slam_runtime_updates(self._drain_slam_runtime_updates())

    def _streaming_completion_loop(self) -> None:
        while not self._streaming_done.is_set():
            completed = self._drain_completed_slam_submissions(timeout_s=0.05)
            if not completed:
                self._streaming_done.wait(timeout=0.05)
            if self._source_finished and self._in_flight_frames == 0:
                self._finalize_streaming()

    def _drain_completed_slam_submissions(self, *, timeout_s: float) -> int:
        with self._slam_submission_lock:
            pending_refs = list(self._slam_submission_refs)
        if not pending_refs:
            return 0
        ready_refs, _ = ray.wait(pending_refs, num_returns=len(pending_refs), timeout=timeout_s)
        if not ready_refs:
            return 0
        ready_set = set(ready_refs)
        with self._slam_submission_lock:
            self._slam_submission_refs = [ref for ref in self._slam_submission_refs if ref not in ready_set]
        for submission_ref in ready_refs:
            self._complete_slam_submission(submission_ref)
        return len(ready_refs)

    def _complete_slam_submission(self, submission_ref: ray.ObjectRef[None]) -> None:
        try:
            ray.get(submission_ref)
        except Exception as exc:
            if isinstance(self._slam_runtime_proxy, RayStageRuntimeHandle):
                self._slam_runtime_proxy.mark_async_item_failed()
            self._console.error("Streaming SLAM frame processing failed for run '%s': %s", self._run_id, exc)
            self._streaming_error = str(exc)
            self._source_finished = True
            if self._source_actor is not None:
                self._source_actor.stop.remote()
        else:
            if isinstance(self._slam_runtime_proxy, RayStageRuntimeHandle):
                self._slam_runtime_proxy.mark_async_item_completed()
            if self._source_actor is not None and not self._stop_requested:
                self._source_actor.grant_credit.remote(1)
            self._publish_slam_runtime_updates(self._drain_slam_runtime_updates())
        finally:
            with self._slam_submission_lock:
                self._in_flight_frames = max(0, self._in_flight_frames - 1)
        if self._source_finished and self._in_flight_frames == 0:
            self._finalize_streaming()

    def _publish_slam_runtime_updates(self, updates: list[StageRuntimeUpdate]) -> None:
        if not updates:
            return
        try:
            self.on_slam_runtime_updates(updates=updates)
        except Exception as exc:  # pragma: no cover - best-effort observer routing
            self._console.warning("Failed to route live SLAM runtime updates for run '%s': %s", self._run_id, exc)

    def _cache_slam_runtime_payloads(self, updates: list[StageRuntimeUpdate]) -> None:
        if self._slam_runtime_proxy is None or not self._rerun_sinks:
            return
        cache_export_payloads = any(sidecar.kind == "export" for sidecar in self._rerun_sinks)
        cache_live_payloads = any(sidecar.kind == "live" for sidecar in self._rerun_sinks)
        for update in updates:
            cache_update = (
                update if cache_export_payloads else self._live_rerun_update(update) if cache_live_payloads else None
            )
            if cache_update is None:
                continue
            for ref in _payload_refs_for_update(cache_update):
                payload = self._read_slam_runtime_payload(ref)
                if payload is not None:
                    self._remember_handle(ref.handle_id, payload)

    def _read_slam_runtime_payload(self, ref: TransientPayloadRef) -> np.ndarray | None:
        if isinstance(self._slam_runtime_proxy, RayStageRuntimeHandle):
            return self._slam_runtime_proxy.read_payload(ref)
        runtime = self._active_slam_runtime()
        if runtime is None:
            return None
        return runtime.read_payload(ref)

    def _active_slam_runtime(self) -> SlamStageRuntime | None:
        if self._slam_runtime_proxy is None or isinstance(self._slam_runtime_proxy, RayStageRuntimeHandle):
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
            self._slam_backend = slam_backend
            if plan.mode is PipelineMode.OFFLINE:
                self._run_offline(
                    run_config=run_config,
                    plan=plan,
                    path_config=path_config,
                    runtime_source=runtime_source,
                )
            else:
                streaming_source = cast(StreamingSequenceSource | None, runtime_source)
                self._run_streaming(
                    run_config=run_config,
                    plan=plan,
                    path_config=path_config,
                    runtime_source=streaming_source,
                )
                self._streaming_completion_loop()
        except Exception as exc:
            self._record_event(
                RunFailed(event_id=self._next_event_id(), run_id=self._run_id, ts_ns=ts_ns(), error_message=str(exc))
            )
            try:
                self._console.exception("Run '%s' failed: %s", self._run_id, exc)
            except Exception:
                pass
        finally:
            self._close_rerun_sinks()

    def _run_offline(
        self,
        *,
        run_config: RunConfig,
        plan: RunPlan,
        path_config: PathConfig,
        runtime_source: OfflineSequenceSource | None,
    ) -> None:
        source_enabled = any(stage.key is StageKey.SOURCE for stage in plan.stages)
        source: OfflineSequenceSource | None
        if runtime_source is None and source_enabled:
            if run_config.stages.source.backend is None:
                raise RuntimeError("RunConfig execution requires `[stages.source.backend]`.")
            source = run_config.stages.source.backend.setup_target(path_config=path_config)
        else:
            source = runtime_source
        self._console.info(
            "Offline source prepared via %s path.",
            "injected runtime source" if runtime_source is not None else "run-config source backend",
        )
        self._result_store = StageResultStore()
        self._stage_runner = StageRunner(self._result_store)
        context = self._stage_execution_context(
            run_config=run_config,
            plan=plan,
            path_config=path_config,
            source=source,
        )
        self._load_reused_results(run_config=run_config, plan=plan)
        runtime_manager = self._build_runtime_manager(plan=plan, context=context)
        runtime_manager.preflight(plan).raise_for_errors()
        for stage in plan.stages:
            if not stage.available:
                continue
            stage_key = stage.key
            if stage_key is StageKey.TRAJECTORY_EVALUATION and self._stop_requested:
                continue
            runtime_proxy, _ = self._run_bounded_stage(
                stage_key=stage_key,
                runtime_manager=runtime_manager,
                context=context,
            )
            self._publish_runtime_updates_from_proxy(runtime_proxy)
        terminal_state = "stopped" if self._stop_requested else "completed"
        self._console.info("Offline run '%s' %s.", self._run_id, terminal_state)
        self._record_event(
            RunStopped(event_id=self._next_event_id(), run_id=self._run_id, ts_ns=ts_ns())
            if self._stop_requested
            else RunCompleted(event_id=self._next_event_id(), run_id=self._run_id, ts_ns=ts_ns())
        )

    def _build_runtime_manager(self, *, plan: RunPlan, context: PipelineExecutionContext) -> RuntimeManager:
        manager = RuntimeManager()
        run_config = self._require_run_config()
        for stage in plan.stages:
            if not stage.available:
                continue
            stage_config = run_config.stages.section(stage.key)
            stage_spec = stage_runtime_spec_for(stage.key)
            factory = stage_spec.runtime_factory(context)
            if factory is None:
                continue
            manager.register(
                stage.key,
                factory=factory,
                stage_config=stage_config,
                stage_spec=stage_spec,
            )
        return manager

    def _run_bounded_stage(
        self,
        *,
        stage_key: StageKey,
        runtime_manager: RuntimeManager,
        context: PipelineExecutionContext,
    ) -> tuple[StageRuntimeHandle, StageResult]:
        runtime_proxy = runtime_manager.runtime_for(stage_key)
        result = self._stage_runner.run_configured_offline_stage(
            stage_key=stage_key,
            runtime=runtime_proxy,
            stage_config=context.run_config.stages.section(stage_key),
            stage_spec=runtime_manager.stage_spec(stage_key),
            context=context,
            on_stage_started=self._emit_stage_started,
            on_stage_completed=self._record_stage_result,
            on_stage_failed=self._record_stage_failure,
        )
        return runtime_proxy, result

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
        if stage_key in {StageKey.TRAJECTORY_ALIGNMENT, StageKey.TRAJECTORY_EVALUATION} and isinstance(
            payload, TrajectoryAlignmentArtifact
        ):
            self._console.info(
                "Applying post-run Sim(3) visual alignment: scale=%.6f matched_pairs=%d rms_error_m=%.6f",
                payload.scale,
                payload.matched_pairs,
                payload.rms_error_m,
            )
            self._submit_rerun_update(
                update=StageRuntimeUpdate(
                    stage_key=stage_key,
                    timestamp_ns=ts_ns(),
                    semantic_events=[payload],
                ),
                payload_resolver=None,
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
        if stage_key is StageKey.TRAJECTORY_EVALUATION and isinstance(payload, TrajectoryEvaluationManifest):
            self._submit_rerun_update(
                update=StageRuntimeUpdate(
                    stage_key=StageKey.TRAJECTORY_EVALUATION,
                    timestamp_ns=ts_ns(),
                    semantic_events=[payload],
                ),
                payload_resolver=None,
                destinations=_RERUN_EXPORT_DESTINATION,
            )
        if stage_key is StageKey.SOURCE and isinstance(payload, SourceStageOutput):
            self._submit_source_reference_visualization_update(output=payload, artifacts=result.outcome.artifacts)
        self._submit_artifact_visualization_update(stage_key=stage_key, outcome=result.outcome)

    def _submit_artifact_visualization_update(self, *, stage_key: StageKey, outcome: StageOutcome) -> None:
        visualizations = artifact_visualizations(outcome.artifacts)
        if not visualizations:
            return
        self._submit_rerun_update(
            update=StageRuntimeUpdate(stage_key=stage_key, timestamp_ns=ts_ns(), visualizations=visualizations),
            payload_resolver=None,
            destinations=_RERUN_EXPORT_DESTINATION,
        )

    def _load_reused_results(self, *, run_config: RunConfig, plan: RunPlan) -> None:
        reuse_root = run_config.reuse_artifact_root
        if reuse_root is None:
            return
        enabled_stage_keys = {stage.key for stage in plan.stages}
        for result in load_reused_stage_results(reuse_root):
            if result.stage_key not in enabled_stage_keys:
                self._result_store.put(result)
                self._record_stage_result(result.stage_key, result)

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
        self._result_store = StageResultStore()
        self._stage_runner = StageRunner(self._result_store)
        context = self._stage_execution_context(
            run_config=run_config,
            plan=plan,
            path_config=path_config,
            source=runtime_source,
        )
        runtime_manager = self._build_runtime_manager(plan=plan, context=context)
        runtime_manager.preflight(plan).raise_for_errors()
        self._streaming_runtime_manager = runtime_manager
        self._run_streaming_prepare(context=context, runtime_manager=runtime_manager)
        self._source_actor = PacketSourceActor.options(  # type: ignore[attr-defined]
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

    def _run_streaming_prepare(self, *, context: PipelineExecutionContext, runtime_manager: RuntimeManager) -> None:
        for stage in context.plan.stages:
            if not stage.available:
                continue
            stage_key = stage.key
            if stage_key is StageKey.SOURCE:
                _, source_result = self._run_bounded_stage(
                    stage_key=stage_key,
                    runtime_manager=runtime_manager,
                    context=context,
                )
                continue
            if stage_key is StageKey.SLAM:
                self._start_streaming_slam_runtime(context=context, runtime_manager=runtime_manager)
        if self._slam_runtime_proxy is None:
            raise RuntimeError("Streaming run requires an available SLAM runtime stage.")

    def _start_streaming_slam_runtime(
        self,
        *,
        context: PipelineExecutionContext,
        runtime_manager: RuntimeManager,
    ) -> None:
        stage_key = StageKey.SLAM
        stage_spec = runtime_manager.stage_spec(stage_key)
        runtime_factory = stage_spec.runtime_factory(context)
        if runtime_factory is None:
            raise RuntimeError("Streaming SLAM stage has no runtime factory.")
        if not isinstance(runtime_factory, type):
            raise RuntimeError("Ray-hosted streaming SLAM requires a class-based runtime factory.")
        actor_options = actor_options_for_stage(
            stage_key=stage_key,
            run_config=context.run_config,
            backend=context.run_config.stages.slam.backend,
            default_num_cpus=1.0,
            default_num_gpus=0.0,
            restartable=False,
            inherit_backend_defaults=True,
        )
        remote_options = cast(dict[str, Any], clean_actor_options(actor_options))
        remote_runtime_cls: Any = ray.remote(**remote_options)(runtime_factory)
        runtime_proxy = RayStageRuntimeHandle(
            stage_key=stage_key,
            actor=cast(ActorHandle, remote_runtime_cls.remote()),
            resource_assignment=_resource_assignment_for_status(actor_options),
        )
        self._stage_runner.start_configured_streaming_stage(
            stage_key=stage_key,
            runtime=runtime_proxy,
            stage_config=context.run_config.stages.section(stage_key),
            stage_spec=stage_spec,
            context=context,
            on_stage_started=self._emit_stage_started,
            on_stage_failed=self._record_stage_failure,
        )
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

    def _finalize_slam_streaming_stage(self, *, context: PipelineExecutionContext) -> None:
        if self._slam_runtime_proxy is None:
            return
        stage_key = StageKey.SLAM
        stage_config = context.run_config.stages.section(stage_key)
        stage_spec = self._require_streaming_runtime_manager().stage_spec(stage_key)
        config_hash, input_fingerprint = self._stage_runner.failure_hash_inputs(
            stage_config=stage_config,
            stage_spec=stage_spec,
            context=context,
        )
        try:
            slam_result = self._stage_runner.finish_streaming_stage(
                stage_key=stage_key,
                runtime=self._slam_runtime_proxy,
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

    def _run_streaming_finalize_stages(self, *, context: PipelineExecutionContext) -> None:
        runtime_manager = self._require_streaming_runtime_manager()
        for stage in context.plan.stages:
            if not stage.available:
                continue
            stage_key = stage.key
            if stage_key in {StageKey.SOURCE, StageKey.SLAM}:
                continue
            if stage_key in _FAILED_SLAM_DEPENDENT_STREAMING_FINALIZERS and (
                self._streaming_error is not None or self._stop_requested
            ):
                continue
            runtime_proxy, _ = self._run_bounded_stage(
                stage_key=stage_key,
                runtime_manager=runtime_manager,
                context=context,
            )
            self._publish_runtime_updates_from_proxy(runtime_proxy)

    def _build_rerun_sinks(self, *, run_config: RunConfig, run_paths: RunArtifactPaths) -> list[_RerunSinkSidecar]:
        if not (run_config.visualization.connect_live_viewer or run_config.visualization.export_viewer_rrd):
            self._console.info("Rerun sink disabled for run '%s'.", self._run_id)
            return []
        from prml_vslam.visualization.rerun_sink import ExportRerunSinkActor, LiveRerunSinkActor

        self._console.info("Rerun sink enabled for run '%s'.", self._run_id)
        common_options = {
            "recording_id": self._run_id,
            "show_tracking_trajectory": run_config.visualization.show_tracking_trajectory,
            "trajectory_pose_axis_length": run_config.visualization.trajectory_pose_axis_length,
            "log_source_rgb": run_config.visualization.log_source_rgb,
            "log_diagnostic_preview": run_config.visualization.log_diagnostic_preview,
            "log_camera_image_rgb": run_config.visualization.log_camera_image_rgb,
            "point_cloud_decimation_keep_ratio": run_config.visualization.point_cloud_decimation_keep_ratio,
            "reference_point_cloud_decimation_keep_ratio": (
                run_config.visualization.reference_point_cloud_decimation_keep_ratio
            ),
            "mesh_decimation_keep_ratio": run_config.visualization.mesh_decimation_keep_ratio,
            "decimation_random_seed": run_config.visualization.decimation_random_seed,
            "view_coordinates": run_config.visualization.view_coordinates,
        }
        sidecars: list[_RerunSinkSidecar] = []
        if run_config.visualization.connect_live_viewer:
            sidecars.append(
                _RerunSinkSidecar(
                    kind="live",
                    actor=LiveRerunSinkActor.remote(  # type: ignore[attr-defined]
                        grpc_url=run_config.visualization.grpc_url,
                        **common_options,
                    ),
                )
            )
        if run_config.visualization.export_viewer_rrd:
            sidecars.append(
                _RerunSinkSidecar(
                    kind="export",
                    actor=ExportRerunSinkActor.remote(  # type: ignore[attr-defined]
                        target_path=run_paths.viewer_rrd_path,
                        **common_options,
                    ),
                )
            )
        return sidecars

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
        packet: Observation,
        frame_payload_ref: TransientPayloadRef | None,
        depth_payload_ref: TransientPayloadRef | None,
        pointmap_payload_ref: TransientPayloadRef | None,
    ) -> None:
        visualization_owner = self._run_config
        if visualization_owner is None or not visualization_owner.visualization.log_source_rgb:
            return
        visualizations = self._source_visualization_adapter.build_observation_items(
            observation=packet,
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
        live_visualizations = [
            item
            for item in visualizations
            if item.intent is VisualizationIntent.TRAJECTORY and item.role == ROLE_SOURCE_REFERENCE_TRAJECTORY
        ]
        if self._rerun_sinks and live_visualizations:
            self._submit_rerun_update(
                update=update.model_copy(update={"visualizations": live_visualizations}),
                payload_resolver=None,
                destinations=_RERUN_LIVE_DESTINATION,
            )
        self._submit_rerun_update(
            update=update,
            payload_resolver=None,
            destinations=_RERUN_EXPORT_DESTINATION,
        )

    def _submit_rerun_update(
        self,
        *,
        update: StageRuntimeUpdate,
        payload_resolver: ActorHandle | None,
        destinations: frozenset[_RerunSinkKind] = _RERUN_ALL_DESTINATIONS,
    ) -> None:
        self._submit_rerun_updates(
            updates=[update],
            payload_resolver=payload_resolver,
            destinations=destinations,
        )

    def _submit_rerun_updates(
        self,
        *,
        updates: list[StageRuntimeUpdate],
        payload_resolver: ActorHandle | None,
        destinations: frozenset[_RerunSinkKind] = _RERUN_ALL_DESTINATIONS,
    ) -> None:
        if not self._rerun_sinks:
            return
        for sidecar in self._rerun_sinks:
            if sidecar.kind not in destinations:
                continue
            routed_updates = [
                routed_update
                for update in updates
                if (
                    routed_update := (
                        self._live_rerun_update(update) if sidecar.kind == "live" else _export_rerun_update(update)
                    )
                )
                is not None
            ]
            if not routed_updates:
                continue
            try:
                self._log_rerun_update_backlog(routed_updates[-1], sidecar=sidecar)
                if sidecar.kind == "live":
                    sidecar.last_call = sidecar.actor.observe_updates.remote(
                        updates=routed_updates,
                        payload_resolver=payload_resolver,
                    )
                else:
                    for routed_update in routed_updates:
                        sidecar.last_call = sidecar.actor.observe_update.remote(
                            update=routed_update,
                            payload_resolver=payload_resolver,
                        )
            except Exception as exc:  # pragma: no cover - best-effort sidecar submission
                self._console.warning(
                    "Failed to submit Rerun %s sink runtime update batch ending at stage '%s': %s",
                    sidecar.kind,
                    routed_updates[-1].stage_key.value,
                    exc,
                )

    def _live_rerun_update(self, update: StageRuntimeUpdate) -> StageRuntimeUpdate | None:
        run_config = self._run_config
        if run_config is None:
            return _export_rerun_update(update)
        visualizations = [
            item
            for item in (_live_rerun_item_for_policy(item, run_config=run_config) for item in update.visualizations)
            if item is not None
        ]
        semantic_events = _rerun_supported_semantic_events(update)
        if not visualizations and not semantic_events:
            return None
        return update.model_copy(update={"visualizations": visualizations, "semantic_events": semantic_events})

    def _publish_runtime_updates_from_proxy(self, runtime_proxy: StageRuntimeHandle) -> None:
        updates = runtime_proxy.drain_runtime_updates(max_items=None)
        if not updates:
            return
        with self._lock:
            for update in updates:
                self._snapshot = self._projector.apply_runtime_update(self._snapshot, update)
        self._submit_rerun_updates(updates=updates, payload_resolver=None)

    def _self_actor_handle(self) -> ActorHandle:
        return ray.get_actor(coordinator_actor_name(self._run_id), namespace=self._namespace)

    def _has_rerun_sinks(self) -> bool:
        return bool(self._rerun_sinks)

    def _log_rerun_update_backlog(self, update: StageRuntimeUpdate, *, sidecar: _RerunSinkSidecar) -> None:
        sidecar.submission_count += 1
        if sidecar.last_call is None:
            return
        ready, _ = ray.wait([sidecar.last_call], timeout=0.0)
        if ready:
            sidecar.pending_count = 0
            return
        sidecar.pending_count += 1
        if sidecar.pending_count == 1 or sidecar.pending_count % 100 == 0:
            payload_refs = [
                (item.role, slot, ref.payload_kind, ref.shape, ref.dtype)
                for item in update.visualizations
                for slot, ref in item.payload_refs.items()
            ]
            lag_detail = (
                "Live viewer may lag behind runtime updates."
                if sidecar.kind == "live"
                else "Exported RRD may lag behind runtime updates."
            )
            self._console.warning(
                "Rerun %s sidecar is lagging: previous runtime update still pending for stage '%s' "
                "(submitted=%d, consecutive_pending=%d, refs=%s). %s",
                sidecar.kind,
                update.stage_key.value,
                sidecar.submission_count,
                sidecar.pending_count,
                payload_refs,
                lag_detail,
            )

    def _remember_handle(self, handle_id: str, payload: HandlePayload) -> None:
        with self._lock:
            self._handle_refs[handle_id] = payload
            self._handle_order.append(handle_id)
            while len(self._handle_order) > HANDLE_LIMIT:
                stale_id = self._handle_order.popleft()
                self._console.debug("Evicting stale handle '%s' due to handle limit %d.", stale_id, HANDLE_LIMIT)
                self._handle_refs.pop(stale_id, None)

    def _resolve_handle_local(self, handle_id: str) -> np.ndarray | None:
        with self._lock:
            return self._resolve_handle_payload(self._handle_refs.get(handle_id))

    @staticmethod
    def _resolve_handle_payload(payload: HandlePayload | None) -> np.ndarray | None:
        if payload is None:
            return None
        if isinstance(payload, np.ndarray):
            return np.asarray(payload)
        return np.asarray(ray.get(payload))

    def _next_event_id(self) -> str:
        with self._lock:
            self._event_counter += 1
            return str(self._event_counter)

    def _close_rerun_sinks(self) -> None:
        if not self._has_rerun_sinks():
            return
        actors = [sidecar.actor for sidecar in self._rerun_sinks]
        try:
            for sidecar in self._rerun_sinks:
                if sidecar.last_call is not None:
                    ray.get(sidecar.last_call)
                sidecar.last_call = sidecar.actor.close.remote()
                ray.get(sidecar.last_call)
        except Exception as exc:  # pragma: no cover - best-effort sidecar cleanup
            self._console.warning("Failed to close Rerun sink actor for run '%s': %s", self._run_id, exc)
        finally:
            for actor in actors:
                try:
                    ray.kill(actor, no_restart=True)
                except Exception:
                    pass
            self._rerun_sinks = []

    def _require_run_config(self) -> RunConfig:
        if self._run_config is not None:
            return self._run_config
        raise RuntimeError("Run config is not initialized.")

    def _require_plan(self) -> RunPlan:
        if self._plan is None:
            raise RuntimeError("Run plan is not initialized.")
        return self._plan

    def _require_slam_backend(self) -> SlamBackendConfig:
        if self._slam_backend is None:
            raise RuntimeError("SLAM backend is not initialized.")
        return self._slam_backend

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
        source: OfflineSequenceSource | None = None,
    ) -> PipelineExecutionContext:
        return PipelineExecutionContext(
            run_config=run_config,
            plan=plan,
            path_config=self._require_path_config() if path_config is None else path_config,
            run_paths=RunArtifactPaths.build(plan.artifact_root),
            source=source,
            results=self._result_store,
            slam_backend=self._require_slam_backend(),
        )


def _resource_assignment_for_status(
    actor_options: dict[str, float | int | dict[str, float] | None],
) -> dict[str, JsonScalar]:
    assignment: dict[str, JsonScalar] = {}
    for key in ("num_cpus", "num_gpus"):
        value = actor_options.get(key)
        if isinstance(value, int | float):
            assignment[key] = float(value)
    resources = actor_options.get("resources")
    if isinstance(resources, dict):
        for resource_name, value in resources.items():
            assignment[f"resource:{resource_name}"] = float(value)
    return assignment


def _export_rerun_update(update: StageRuntimeUpdate) -> StageRuntimeUpdate | None:
    semantic_events = _rerun_supported_semantic_events(update)
    if not update.visualizations and not semantic_events:
        return None
    if len(semantic_events) == len(update.semantic_events):
        return update
    return update.model_copy(update={"semantic_events": semantic_events})


def _rerun_supported_semantic_events(
    update: StageRuntimeUpdate,
) -> list[GroundAlignmentMetadata | TrajectoryAlignmentArtifact | TrajectoryEvaluationManifest]:
    return [
        semantic_event
        for semantic_event in update.semantic_events
        if isinstance(
            semantic_event, GroundAlignmentMetadata | TrajectoryAlignmentArtifact | TrajectoryEvaluationManifest
        )
    ]


def _live_rerun_item_for_policy(item: VisualizationItem, *, run_config: RunConfig) -> VisualizationItem | None:
    visualization_config = run_config.visualization
    if item.role == ROLE_SOURCE_RGB and not visualization_config.log_source_rgb:
        return None
    if item.role == ROLE_MODEL_CAMERA_RGB and not visualization_config.log_camera_image_rgb:
        return None
    if item.role in {ROLE_MODEL_PREVIEW, ROLE_KEYFRAME_PREVIEW} and not visualization_config.log_diagnostic_preview:
        return None
    if item.role in {ROLE_KEYFRAME_RGB, ROLE_KEYFRAME_DEPTH, ROLE_KEYFRAME_PREVIEW}:
        return None
    if item.role in {ROLE_MODEL_PINHOLE, ROLE_KEYFRAME_PINHOLE} and item.intrinsics is not None:
        return item.model_copy(update={"payload_refs": {}})
    return item


def _payload_refs_for_update(update: StageRuntimeUpdate) -> list[TransientPayloadRef]:
    refs: list[TransientPayloadRef] = []
    seen_handle_ids: set[str] = set()
    for item in update.visualizations:
        for ref in item.payload_refs.values():
            if ref.handle_id in seen_handle_ids:
                continue
            seen_handle_ids.add(ref.handle_id)
            refs.append(ref)
    return refs


__all__ = ["RunCoordinatorActor"]
