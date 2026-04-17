"""Authoritative per-run Ray coordinator actor."""

from __future__ import annotations

import threading
from collections import deque
from typing import Any, TypeAlias

import numpy as np
import ray

from prml_vslam.benchmark import PreparedBenchmarkInputs
from prml_vslam.interfaces import FramePacketProvenance
from prml_vslam.methods.descriptors import BackendDescriptor
from prml_vslam.methods.events import BackendError, BackendEvent
from prml_vslam.methods.factory import BackendFactory
from prml_vslam.pipeline.contracts.artifacts import SlamArtifacts
from prml_vslam.pipeline.contracts.events import (
    ArtifactRegistered,
    BackendNoticeReceived,
    FramePacketSummary,
    PacketObserved,
    RunCompleted,
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
from prml_vslam.pipeline.contracts.provenance import RunSummary, StageManifest
from prml_vslam.pipeline.contracts.request import PipelineMode, RunRequest
from prml_vslam.pipeline.contracts.runtime import RunSnapshot, RunState, StreamingRunSnapshot
from prml_vslam.pipeline.contracts.sequence import SequenceManifest
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.finalization import stable_hash
from prml_vslam.pipeline.placement import actor_options_for_stage
from prml_vslam.pipeline.ray_runtime.common import (
    DEFAULT_MAX_FRAMES_IN_FLIGHT,
    EVENT_RING_LIMIT,
    HANDLE_LIMIT,
    IngestStageResult,
    SlamStageResult,
    SummaryStageResult,
    TrajectoryEvaluationStageResult,
    clean_actor_options,
    coordinator_actor_name,
    ts_ns,
)
from prml_vslam.pipeline.ray_runtime.stage_actors import (
    IngestStageActor,
    OfflineSlamStageActor,
    PacketSourceActor,
    StreamingSlamStageActor,
    SummaryStageActor,
    TrajectoryEvaluationStageActor,
)
from prml_vslam.pipeline.sinks import JsonlEventSink
from prml_vslam.pipeline.snapshot_projector import SnapshotProjector
from prml_vslam.pipeline.source_resolver import OfflineSourceResolver
from prml_vslam.utils import Console, PathConfig, RunArtifactPaths
from prml_vslam.visualization.contracts import VisualizationArtifacts

HandlePayload: TypeAlias = ray.ObjectRef[Any] | np.ndarray
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
        self._events: list[object] = []
        self._handle_refs: dict[str, HandlePayload] = {}
        self._handle_order: deque[str] = deque()
        self._lock = threading.Lock()
        self._stop_requested = False
        self._source_finished = False
        self._streaming_finalized = False
        self._in_flight_frames = 0
        self._streaming_done = threading.Event()
        self._jsonl_sink: JsonlEventSink | None = None
        self._rerun_sink: object | None = None
        self._rerun_sink_last_call = None
        self._worker: threading.Thread | None = None
        self._source_actor = None
        self._slam_actor = None
        self._request: RunRequest | None = None
        self._plan: RunPlan | None = None
        self._backend_descriptor: BackendDescriptor | None = None
        self._stage_outcomes: list[StageOutcome] = []
        self._sequence_manifest: SequenceManifest | None = None
        self._benchmark_inputs: PreparedBenchmarkInputs | None = None
        self._slam_artifacts: SlamArtifacts | None = None
        self._streaming_error: str | None = None

    def start(
        self, *, request: RunRequest, plan: RunPlan, path_config: PathConfig, runtime_source: object | None
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

    def events(self, after_event_id: str | None = None, limit: int = 200) -> list[object]:
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
        depth_ref: HandlePayload | None,
        confidence_ref: HandlePayload | None,
        intrinsics: object,
        pose: object,
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
            bindings=bindings,
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
                bindings=bindings,
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
        runtime_source: object | None,
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
            stage_key = self._current_stage_key()
            if stage_key is not None:
                self._record_stage_failure(
                    stage_key=stage_key,
                    outcome=self._failure_outcome(stage_key=stage_key, error_message=str(exc)),
                )
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
        runtime_source: object | None,
    ) -> None:
        source = runtime_source
        if source is None:
            source = OfflineSourceResolver(path_config).resolve(request.source)
        run_paths = RunArtifactPaths.build(plan.artifact_root)
        ingest = self._run_ingest_stage(request=request, source=source, run_paths=run_paths)
        slam = self._run_offline_slam_stage(
            request=request,
            plan=plan,
            path_config=path_config,
            sequence_manifest=ingest.sequence_manifest,
            benchmark_inputs=ingest.benchmark_inputs,
        )
        if request.benchmark.trajectory.enabled and not self._stop_requested:
            self._run_trajectory_stage(
                request=request,
                plan=plan,
                sequence_manifest=ingest.sequence_manifest,
                benchmark_inputs=ingest.benchmark_inputs,
                slam=slam.slam,
            )
        self._run_summary_stage(request=request, plan=plan, run_paths=run_paths)
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
        runtime_source: object | None,
    ) -> None:
        if runtime_source is None:
            raise RuntimeError("Streaming runs require an explicit runtime source.")
        run_paths = RunArtifactPaths.build(plan.artifact_root)
        self._run_ingest_stage(request=request, source=runtime_source, run_paths=run_paths)
        self._emit_stage_started(StageKey.SLAM)
        self._slam_actor = StreamingSlamStageActor.options(
            **self._stage_actor_options(
                stage_key=StageKey.SLAM,
                request=request,
                default_num_cpus=2.0,
                default_num_gpus=0.0,
                inherit_backend_defaults=True,
            )
        ).remote(
            coordinator_name=coordinator_actor_name(plan.run_id),
            namespace=self._namespace,
        )
        ray.get(self._slam_actor.start_stage.remote(request=request, plan=plan, path_config=path_config))
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
            run_paths = RunArtifactPaths.build(plan.artifact_root)
            if self._slam_actor is not None:
                slam_result = ray.get(self._slam_actor.close_stage.remote(request=request, plan=plan))
                if self._streaming_error is not None:
                    self._slam_artifacts = slam_result.slam
                    self._record_stage_failure(
                        stage_key=StageKey.SLAM,
                        outcome=slam_result.outcome.model_copy(
                            update={
                                "status": StageStatus.FAILED,
                                "error_message": self._streaming_error,
                            }
                        ),
                    )
                else:
                    if self._stop_requested:
                        slam_result.outcome.status = StageStatus.STOPPED
                    self._slam_artifacts = slam_result.slam
                    self._record_stage_completion(
                        stage_key=StageKey.SLAM,
                        outcome=slam_result.outcome,
                        slam=slam_result.slam,
                        visualization=slam_result.visualization,
                    )
            if self._streaming_error is None and request.benchmark.trajectory.enabled and not self._stop_requested:
                self._run_trajectory_stage(
                    request=request,
                    plan=plan,
                    sequence_manifest=self._require_sequence_manifest(),
                    benchmark_inputs=self._benchmark_inputs,
                    slam=self._require_slam_artifacts(),
                )
            self._run_summary_stage(request=request, plan=plan, run_paths=run_paths)
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

    def _run_ingest_stage(
        self,
        *,
        request: RunRequest,
        source: object,
        run_paths: RunArtifactPaths,
    ) -> IngestStageResult:
        self._emit_stage_started(StageKey.INGEST)
        actor = IngestStageActor.options(
            **self._stage_actor_options(
                stage_key=StageKey.INGEST,
                request=request,
                default_num_cpus=1.0,
                default_num_gpus=0.0,
                restartable=True,
            )
        ).remote()
        result = ray.get(actor.run.remote(request=request, source=source, run_paths=run_paths))
        self._sequence_manifest = result.sequence_manifest
        self._benchmark_inputs = result.benchmark_inputs
        self._record_stage_completion(
            stage_key=StageKey.INGEST,
            outcome=result.outcome,
            sequence_manifest=result.sequence_manifest,
            benchmark_inputs=result.benchmark_inputs,
        )
        return result

    def _run_offline_slam_stage(
        self,
        *,
        request: RunRequest,
        plan: RunPlan,
        path_config: PathConfig,
        sequence_manifest: SequenceManifest,
        benchmark_inputs: PreparedBenchmarkInputs | None,
    ) -> SlamStageResult:
        self._emit_stage_started(StageKey.SLAM)
        actor = OfflineSlamStageActor.options(
            **self._stage_actor_options(
                stage_key=StageKey.SLAM,
                request=request,
                default_num_cpus=2.0,
                default_num_gpus=1.0,
            )
        ).remote()
        result = ray.get(
            actor.run.remote(
                request=request,
                plan=plan,
                sequence_manifest=sequence_manifest,
                benchmark_inputs=benchmark_inputs,
                path_config=path_config,
            )
        )
        self._slam_artifacts = result.slam
        self._record_stage_completion(
            stage_key=StageKey.SLAM,
            outcome=result.outcome,
            slam=result.slam,
            visualization=result.visualization,
        )
        return result

    def _run_trajectory_stage(
        self,
        *,
        request: RunRequest,
        plan: RunPlan,
        sequence_manifest: SequenceManifest,
        benchmark_inputs: PreparedBenchmarkInputs | None,
        slam: SlamArtifacts,
    ) -> TrajectoryEvaluationStageResult:
        self._emit_stage_started(StageKey.TRAJECTORY_EVALUATION)
        actor = TrajectoryEvaluationStageActor.options(
            **self._stage_actor_options(
                stage_key=StageKey.TRAJECTORY_EVALUATION,
                request=request,
                default_num_cpus=1.0,
                default_num_gpus=0.0,
                restartable=True,
            )
        ).remote()
        result = ray.get(
            actor.run.remote(
                request=request,
                plan=plan,
                sequence_manifest=sequence_manifest,
                benchmark_inputs=benchmark_inputs,
                slam=slam,
            )
        )
        self._record_stage_completion(stage_key=StageKey.TRAJECTORY_EVALUATION, outcome=result.outcome)
        return result

    def _run_summary_stage(
        self,
        *,
        request: RunRequest,
        plan: RunPlan,
        run_paths: RunArtifactPaths,
    ) -> SummaryStageResult:
        self._emit_stage_started(StageKey.SUMMARY)
        actor = SummaryStageActor.options(
            **self._stage_actor_options(
                stage_key=StageKey.SUMMARY,
                request=request,
                default_num_cpus=1.0,
                default_num_gpus=0.0,
                restartable=True,
            )
        ).remote()
        result = ray.get(
            actor.run.remote(
                request=request,
                plan=plan,
                run_paths=run_paths,
                stage_outcomes=self._stage_outcomes,
            )
        )
        self._record_stage_completion(
            stage_key=StageKey.SUMMARY,
            outcome=result.outcome,
            summary=result.summary,
            stage_manifests=result.stage_manifests,
        )
        return result

    def _build_rerun_sink(self, *, request: RunRequest, run_paths: RunArtifactPaths) -> object | None:
        if not (request.visualization.connect_live_viewer or request.visualization.export_viewer_rrd):
            return None
        from prml_vslam.pipeline.sinks.rerun import RerunSinkActor

        return RerunSinkActor.remote(
            grpc_url=request.visualization.grpc_url if request.visualization.connect_live_viewer else None,
            target_path=run_paths.viewer_rrd_path if request.visualization.export_viewer_rrd else None,
            modalities=list(request.visualization.rerun_modalities),
            recording_id=self._run_id,
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
    ) -> dict[str, Any]:
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

    def _record_stage_completion(
        self,
        *,
        stage_key: StageKey,
        outcome: StageOutcome,
        sequence_manifest: SequenceManifest | None = None,
        benchmark_inputs: PreparedBenchmarkInputs | None = None,
        slam: SlamArtifacts | None = None,
        visualization: VisualizationArtifacts | None = None,
        summary: RunSummary | None = None,
        stage_manifests: list[StageManifest] | None = None,
    ) -> None:
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
        self._stage_outcomes.append(outcome)
        self._console.info(
            "Stage '%s' finished for run '%s' with status '%s' and %d artifacts.",
            stage_key.value,
            self._run_id,
            outcome.status.value,
            len(outcome.artifacts),
        )
        self._record_event(
            StageCompleted(
                event_id=self._next_event_id(),
                run_id=self._run_id,
                ts_ns=ts_ns(),
                stage_key=stage_key,
                outcome=outcome,
                sequence_manifest=sequence_manifest,
                benchmark_inputs=benchmark_inputs,
                slam=slam,
                visualization=visualization,
                summary=summary,
                stage_manifests=[] if stage_manifests is None else stage_manifests,
            )
        )

    def _record_stage_failure(self, *, stage_key: StageKey, outcome: StageOutcome) -> None:
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
        self._stage_outcomes.append(outcome)
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
        event: object,
        *,
        bindings: list[tuple[str, HandlePayload]] | None = None,
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
                    bindings=[] if bindings is None else bindings,
                )
            except Exception as exc:  # pragma: no cover - best-effort sidecar submission
                self._console.warning("Failed to submit Rerun sink event '%s': %s", getattr(event, "kind", event), exc)

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

    def _require_sequence_manifest(self) -> SequenceManifest:
        if self._sequence_manifest is None:
            raise RuntimeError("Sequence manifest is not available.")
        return self._sequence_manifest

    def _require_slam_artifacts(self) -> SlamArtifacts:
        if self._slam_artifacts is None:
            raise RuntimeError("SLAM artifacts are not available.")
        return self._slam_artifacts

    def _current_stage_key(self) -> StageKey | None:
        return self._snapshot.current_stage_key

    def _failure_outcome(self, *, stage_key: StageKey, error_message: str) -> StageOutcome:
        return StageOutcome(
            stage_key=stage_key,
            status=StageStatus.FAILED,
            config_hash=self._stage_config_hash(stage_key),
            input_fingerprint=self._stage_input_fingerprint(stage_key),
            error_message=error_message,
        )

    def _stage_config_hash(self, stage_key: StageKey) -> str:
        request = self._request
        if request is None:
            return stable_hash({"run_id": self._run_id, "stage_key": stage_key.value})
        match stage_key:
            case StageKey.INGEST:
                return stable_hash(request.source)
            case StageKey.SLAM:
                return stable_hash(request.slam)
            case StageKey.TRAJECTORY_EVALUATION:
                return stable_hash(request.benchmark.trajectory)
            case StageKey.SUMMARY:
                return stable_hash({"experiment_name": request.experiment_name, "mode": request.mode.value})
            case _:
                return stable_hash({"run_id": self._run_id, "stage_key": stage_key.value})

    def _stage_input_fingerprint(self, stage_key: StageKey) -> str:
        match stage_key:
            case StageKey.INGEST:
                return stable_hash(self._request.source if self._request is not None else {"run_id": self._run_id})
            case StageKey.SLAM:
                return stable_hash(
                    self._sequence_manifest
                    if self._sequence_manifest is not None
                    else {"run_id": self._run_id, "stage_key": stage_key.value}
                )
            case StageKey.TRAJECTORY_EVALUATION:
                return stable_hash(
                    {
                        "benchmark_inputs": self._benchmark_inputs,
                        "slam_trajectory": None
                        if self._slam_artifacts is None
                        else self._slam_artifacts.trajectory_tum,
                    }
                )
            case StageKey.SUMMARY:
                return stable_hash(self._stage_outcomes)
            case _:
                return stable_hash({"run_id": self._run_id, "stage_key": stage_key.value})


__all__ = ["RunCoordinatorActor"]
