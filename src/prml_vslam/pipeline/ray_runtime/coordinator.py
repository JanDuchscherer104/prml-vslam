"""Authoritative per-run Ray coordinator actor."""

from __future__ import annotations

import threading
from collections import deque

import numpy as np
import ray
from ray.actor import ActorHandle

from prml_vslam.interfaces import CameraIntrinsics, FramePacketProvenance, FrameTransform
from prml_vslam.methods.descriptors import BackendDescriptor
from prml_vslam.methods.events import BackendError, BackendEvent
from prml_vslam.methods.factory import BackendFactory
from prml_vslam.pipeline.backend import PipelineRuntimeSource
from prml_vslam.pipeline.contracts.artifacts import SlamArtifacts
from prml_vslam.pipeline.contracts.events import (
    ArtifactRegistered,
    BackendNoticeReceived,
    FramePacketSummary,
    PacketObserved,
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
from prml_vslam.pipeline.contracts.handles import ArrayHandle
from prml_vslam.pipeline.contracts.plan import RunPlan
from prml_vslam.pipeline.contracts.request import PipelineMode, RunRequest
from prml_vslam.pipeline.contracts.runtime import RunSnapshot, RunState, StreamingRunSnapshot
from prml_vslam.pipeline.contracts.sequence import SequenceManifest
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.placement import RayActorOptions, actor_options_for_stage
from prml_vslam.pipeline.ray_runtime.common import (
    DEFAULT_MAX_FRAMES_IN_FLIGHT,
    EVENT_RING_LIMIT,
    HANDLE_LIMIT,
    HandlePayload,
    clean_actor_options,
    coordinator_actor_name,
    ts_ns,
)
from prml_vslam.pipeline.ray_runtime.stage_actors import PacketSourceActor, StreamingSlamStageActor
from prml_vslam.pipeline.ray_runtime.stage_execution import StageExecutionContext
from prml_vslam.pipeline.ray_runtime.stage_program import (
    RuntimeExecutionState,
    RuntimeStageProgram,
    StageCompletionPayload,
)
from prml_vslam.pipeline.sinks import JsonlEventSink
from prml_vslam.pipeline.snapshot_projector import SnapshotProjector
from prml_vslam.pipeline.source_resolver import OfflineSourceResolver
from prml_vslam.protocols.source import OfflineSequenceSource, StreamingSequenceSource
from prml_vslam.utils import Console, PathConfig, RunArtifactPaths

_TERMINAL_STATES = {RunState.COMPLETED, RunState.FAILED, RunState.STOPPED}


@ray.remote(num_cpus=1, max_restarts=0, max_task_retries=0)
class RunCoordinatorActor:
    """Authoritative per-run state owner and event projector."""

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
        self._worker: threading.Thread | None = None
        self._source_actor = None
        self._slam_actor = None
        self._request: RunRequest | None = None
        self._plan: RunPlan | None = None
        self._backend_descriptor: BackendDescriptor | None = None
        self._runtime_state = RuntimeExecutionState()
        self._stage_program = RuntimeStageProgram.default()
        self._streaming_error: str | None = None
        self._path_config: PathConfig | None = None

    def start(
        self, *, request: RunRequest, plan: RunPlan, path_config: PathConfig, runtime_source: PipelineRuntimeSource
    ) -> None:
        if self._worker is not None and self._worker.is_alive():
            raise RuntimeError(f"Run '{self._run_id}' is already active.")
        self._console.info(
            "Starting run '%s' in %s mode with %d planned stages.",
            plan.run_id,
            plan.mode.value,
            len(plan.stages),
        )
        self._request = request
        self._plan = plan
        self._path_config = path_config
        self._runtime_state = RuntimeExecutionState()
        self._stop_requested = False
        self._source_finished = False
        self._streaming_finalized = False
        self._in_flight_frames = 0
        self._streaming_done = threading.Event()
        self._source_actor = None
        self._slam_actor = None
        self._streaming_error = None
        self._snapshot = (
            StreamingRunSnapshot(run_id=plan.run_id, plan=plan, active_executor="ray")
            if plan.mode is PipelineMode.STREAMING
            else RunSnapshot(run_id=plan.run_id, plan=plan, active_executor="ray")
        )
        run_paths = RunArtifactPaths.build(plan.artifact_root)
        self._jsonl_sink = JsonlEventSink(run_paths.summary_path.parent / "run-events.jsonl")
        self._rerun_sink = self._build_rerun_sink(request=request, run_paths=run_paths)
        self._record_event(RunSubmitted(event_id=self._next_event_id(), run_id=plan.run_id, ts_ns=ts_ns()))
        self._worker = threading.Thread(
            target=self._run,
            args=(request, plan, path_config, runtime_source),
            daemon=True,
            name=f"run-coordinator-{plan.run_id}",
        )
        self._worker.start()

    def stop(self) -> None:
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
        if self._streaming_done.is_set() and self._snapshot.state not in {RunState.COMPLETED, RunState.FAILED}:
            self._record_event(RunStopped(event_id=self._next_event_id(), run_id=self._run_id, ts_ns=ts_ns()))

    def snapshot(self) -> RunSnapshot:
        with self._lock:
            return self._snapshot.model_copy(deep=True)

    def events(self, after_event_id: str | None = None, limit: int = 200) -> list[RunEvent]:
        with self._lock:
            events = list(self._events)
        if after_event_id is not None:
            ids = [event.event_id for event in events]
            if after_event_id in ids:
                events = events[ids.index(after_event_id) + 1 :]
        return events[-limit:]

    def read_array(self, handle_id: str) -> np.ndarray | None:
        return self._resolve_handle_payload(self._handle_refs.get(handle_id))

    def shutdown(self) -> None:
        self._console.info("Shutting down run '%s'.", self._run_id)
        self._stop_requested = True
        if self._source_actor is not None:
            try:
                self._source_actor.stop.remote()
                ray.kill(self._source_actor)
            except Exception:
                pass
        if self._slam_actor is not None:
            try:
                ray.kill(self._slam_actor)
            except Exception:
                pass
        if self._worker is not None:
            self._worker.join(timeout=5.0)
        self._close_rerun_sink()

    def on_packet(
        self,
        *,
        packet: FramePacketSummary,
        frame_handle: ArrayHandle | None,
        frame_ref: HandlePayload | None,
        rerun_bindings: list[tuple[str, np.ndarray]] | None,
        depth_ref: HandlePayload | None,
        confidence_ref: HandlePayload | None,
        intrinsics: CameraIntrinsics | None,
        pose: FrameTransform | None,
        provenance: FramePacketProvenance,
        received_frames: int,
        measured_fps: float,
    ) -> None:
        bindings: list[tuple[str, HandlePayload]] = []
        if frame_handle is not None and frame_ref is not None:
            self._remember_handle(frame_handle.handle_id, frame_ref)
            bindings.append((frame_handle.handle_id, frame_ref))
        self._record_event(
            PacketObserved(
                event_id=self._next_event_id(),
                run_id=self._run_id,
                ts_ns=ts_ns(),
                packet=packet,
                frame=frame_handle,
                received_frames=received_frames,
                measured_fps=measured_fps,
            ),
            rerun_bindings=rerun_bindings,
        )
        if self._stop_requested or self._slam_actor is None:
            return
        self._in_flight_frames += 1
        self._slam_actor.push_frame.remote(
            packet=packet,
            frame_ref=frame_ref,
            depth_ref=depth_ref,
            confidence_ref=confidence_ref,
            intrinsics=intrinsics,
            pose=pose,
            provenance=provenance,
        )

    def on_slam_notices(
        self,
        *,
        notices: list[BackendEvent],
        bindings: list[tuple[str, HandlePayload]],
        rerun_bindings: list[tuple[str, np.ndarray]],
        released_credits: int,
    ) -> None:
        for handle_id, ref in bindings:
            self._remember_handle(handle_id, ref)
        for notice in notices:
            self._record_event(
                BackendNoticeReceived(
                    event_id=self._next_event_id(),
                    run_id=self._run_id,
                    ts_ns=ts_ns(),
                    stage_key=StageKey.SLAM,
                    notice=notice,
                ),
                rerun_bindings=rerun_bindings,
            )
            if isinstance(notice, BackendError):
                self._streaming_error = notice.message
        self._in_flight_frames = max(0, self._in_flight_frames - released_credits)
        if self._source_actor is not None and not self._stop_requested:
            self._source_actor.grant_credit.remote(released_credits)
        if self._source_finished and self._in_flight_frames == 0:
            self._finalize_streaming()

    def on_source_eof(self) -> None:
        self._console.info("Streaming source reached EOF for run '%s'.", self._run_id)
        self._source_finished = True
        if self._in_flight_frames == 0:
            self._finalize_streaming()

    def on_source_error(self, error_message: str) -> None:
        self._console.error("Streaming source failed for run '%s': %s", self._run_id, error_message)
        self._streaming_error = error_message
        self._source_finished = True
        if self._in_flight_frames == 0:
            self._finalize_streaming()

    def _run(
        self,
        request: RunRequest,
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
            self._backend_descriptor = BackendFactory().describe(request.slam.backend)
            if plan.mode is PipelineMode.OFFLINE:
                self._run_offline(
                    request=request,
                    plan=plan,
                    path_config=path_config,
                    runtime_source=runtime_source,
                )
            else:
                self._run_streaming(
                    request=request,
                    plan=plan,
                    path_config=path_config,
                    runtime_source=runtime_source,
                )
                self._streaming_done.wait()
        except Exception as exc:
            self._console.exception("Run '%s' failed: %s", self._run_id, exc)
            self._record_event(
                RunFailed(event_id=self._next_event_id(), run_id=self._run_id, ts_ns=ts_ns(), error_message=str(exc))
            )
        finally:
            self._close_rerun_sink()

    def _run_offline(
        self,
        *,
        request: RunRequest,
        plan: RunPlan,
        path_config: PathConfig,
        runtime_source: OfflineSequenceSource | None,
    ) -> None:
        source: OfflineSequenceSource = (
            OfflineSourceResolver(path_config).resolve(request.source) if runtime_source is None else runtime_source
        )
        context = self._stage_execution_context(request=request, plan=plan, path_config=path_config)
        self._stage_program.execute_offline(
            plan=plan,
            context=context,
            state=self._runtime_state,
            source=source,
            driver=self,
            emit_stage_started=self._emit_stage_started,
            record_stage_completion=self._record_stage_completion,
            record_stage_failure=self._record_stage_failure,
        )
        terminal_state = "stopped" if self._stop_requested else "completed"
        self._console.info("Offline run '%s' %s.", self._run_id, terminal_state)
        self._record_event(
            RunStopped(event_id=self._next_event_id(), run_id=self._run_id, ts_ns=ts_ns())
            if self._stop_requested
            else RunCompleted(event_id=self._next_event_id(), run_id=self._run_id, ts_ns=ts_ns())
        )

    def _run_streaming(
        self,
        *,
        request: RunRequest,
        plan: RunPlan,
        path_config: PathConfig,
        runtime_source: StreamingSequenceSource | None,
    ) -> None:
        if runtime_source is None:
            raise RuntimeError("Streaming runs require an explicit runtime source.")
        context = self._stage_execution_context(request=request, plan=plan, path_config=path_config)
        self._stage_program.execute_streaming_prepare(
            plan=plan,
            context=context,
            state=self._runtime_state,
            source=runtime_source,
            driver=self,
            emit_stage_started=self._emit_stage_started,
            record_stage_completion=self._record_stage_completion,
            record_stage_failure=self._record_stage_failure,
        )
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

    def _finalize_streaming(self) -> None:
        if self._streaming_finalized:
            return
        self._streaming_finalized = True
        try:
            request = self._require_request()
            plan = self._require_plan()
            context = self._stage_execution_context(request=request, plan=plan)
            self._stage_program.execute_streaming_finalize(
                plan=plan,
                context=context,
                state=self._runtime_state,
                driver=self,
                emit_stage_started=self._emit_stage_started,
                record_stage_completion=self._record_stage_completion,
                record_stage_failure=self._record_stage_failure,
            )
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

    @property
    def stop_requested(self) -> bool:
        return self._stop_requested

    @property
    def streaming_error(self) -> str | None:
        return self._streaming_error

    def start_streaming_slam_stage(self, *, context: StageExecutionContext) -> None:
        self._slam_actor = StreamingSlamStageActor.options(
            **self._stage_actor_options(
                stage_key=StageKey.SLAM,
                request=context.request,
                default_num_cpus=2.0,
                default_num_gpus=0.0,
                inherit_backend_defaults=True,
            )
        ).remote(
            coordinator_name=coordinator_actor_name(context.plan.run_id),
            namespace=self._namespace,
        )
        try:
            ray.get(
                self._slam_actor.start_stage.remote(
                    request=context.request,
                    plan=context.plan,
                    path_config=context.path_config,
                )
            )
        except Exception:
            if self._slam_actor is not None:
                try:
                    ray.kill(self._slam_actor, no_restart=True)
                except Exception:
                    pass
                self._slam_actor = None
            raise

    def close_streaming_slam_stage(
        self,
        *,
        context: StageExecutionContext,
        sequence_manifest: SequenceManifest,
    ) -> StageCompletionPayload:
        if self._slam_actor is None:
            raise RuntimeError("Streaming SLAM actor has not been started.")
        result = ray.get(
            self._slam_actor.close_stage.remote(
                request=context.request,
                plan=context.plan,
                sequence_manifest=sequence_manifest,
            )
        )
        return StageCompletionPayload(
            outcome=result.outcome,
            slam=result.slam,
            visualization=result.visualization,
        )

    def _build_rerun_sink(self, *, request: RunRequest, run_paths: RunArtifactPaths) -> ActorHandle | None:
        if not (request.visualization.connect_live_viewer or request.visualization.export_viewer_rrd):
            return None
        from prml_vslam.pipeline.sinks.rerun import RerunSinkActor

        return RerunSinkActor.remote(
            grpc_url=request.visualization.grpc_url if request.visualization.connect_live_viewer else None,
            target_path=run_paths.viewer_rrd_path if request.visualization.export_viewer_rrd else None,
            recording_id=self._run_id,
            frusta_history_window_streaming=request.visualization.frusta_history_window_streaming,
            show_tracking_trajectory=request.visualization.show_tracking_trajectory,
        )

    def _stage_actor_options(
        self,
        *,
        stage_key: StageKey,
        request: RunRequest,
        default_num_cpus: float,
        default_num_gpus: float,
        restartable: bool = False,
        inherit_backend_defaults: bool = False,
    ) -> RayActorOptions:
        return clean_actor_options(
            actor_options_for_stage(
                stage_key=stage_key,
                request=request,
                backend=self._require_backend_descriptor(),
                default_num_cpus=default_num_cpus,
                default_num_gpus=default_num_gpus,
                restartable=restartable,
                inherit_backend_defaults=inherit_backend_defaults,
            )
        )

    def _emit_stage_started(self, stage_key: StageKey) -> None:
        self._console.info("Stage '%s' started for run '%s'.", stage_key.value, self._run_id)
        self._record_event(
            StageQueued(event_id=self._next_event_id(), run_id=self._run_id, ts_ns=ts_ns(), stage_key=stage_key)
        )
        self._record_event(
            StageStarted(event_id=self._next_event_id(), run_id=self._run_id, ts_ns=ts_ns(), stage_key=stage_key)
        )

    def _record_stage_completion(self, stage_key: StageKey, payload: StageCompletionPayload) -> None:
        for artifact_key, artifact in payload.outcome.artifacts.items():
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
            payload.outcome.status.value,
            len(payload.outcome.artifacts),
        )
        self._record_event(
            StageCompleted(
                event_id=self._next_event_id(),
                run_id=self._run_id,
                ts_ns=ts_ns(),
                stage_key=stage_key,
                outcome=payload.outcome,
                sequence_manifest=payload.sequence_manifest,
                benchmark_inputs=payload.benchmark_inputs,
                slam=payload.slam,
                visualization=payload.visualization,
                summary=payload.summary,
                stage_manifests=payload.stage_manifests,
            )
        )

    def _record_stage_failure(self, stage_key: StageKey, outcome: StageOutcome) -> None:
        if self._snapshot.stage_status.get(stage_key) in {
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
        rerun_bindings: list[tuple[str, np.ndarray]] | None = None,
    ) -> None:
        with self._lock:
            self._snapshot = self._projector.apply(self._snapshot, event)
            self._events.append(event)
            if len(self._events) > EVENT_RING_LIMIT:
                self._events = self._events[-EVENT_RING_LIMIT:]
        if self._jsonl_sink is not None:
            self._jsonl_sink.observe(event)
        if self._rerun_sink is not None:
            try:
                self._rerun_sink_last_call = self._rerun_sink.observe_event.remote(
                    event=event,
                    rerun_bindings=[] if rerun_bindings is None else rerun_bindings,
                )
            except Exception as exc:  # pragma: no cover - best-effort sidecar submission
                self._console.warning("Failed to submit Rerun sink event '%s': %s", event.kind, exc)

    def _remember_handle(self, handle_id: str, payload: HandlePayload) -> None:
        self._handle_refs[handle_id] = payload
        self._handle_order.append(handle_id)
        while len(self._handle_order) > HANDLE_LIMIT:
            stale_id = self._handle_order.popleft()
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

    def _require_request(self) -> RunRequest:
        if self._request is None:
            raise RuntimeError("Run request is not initialized.")
        return self._request

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

    def _require_sequence_manifest(self) -> SequenceManifest:
        if self._runtime_state.sequence_manifest is None:
            raise RuntimeError("Sequence manifest is not available.")
        return self._runtime_state.sequence_manifest

    def _require_slam_artifacts(self) -> SlamArtifacts:
        if self._runtime_state.slam is None:
            raise RuntimeError("SLAM artifacts are not available.")
        return self._runtime_state.slam

    def _stage_execution_context(
        self,
        *,
        request: RunRequest,
        plan: RunPlan,
        path_config: PathConfig | None = None,
    ) -> StageExecutionContext:
        return StageExecutionContext(
            request=request,
            plan=plan,
            path_config=self._require_path_config() if path_config is None else path_config,
            run_paths=RunArtifactPaths.build(plan.artifact_root),
            backend_descriptor=self._require_backend_descriptor(),
        )


__all__ = ["RunCoordinatorActor"]
