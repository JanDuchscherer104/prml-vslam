"""Streaming pipeline coordinator with local or process-backed worker components."""

from __future__ import annotations

import multiprocessing as mp
import pickle
import queue
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np

from prml_vslam.benchmark import PreparedBenchmarkInputs, ReferenceCloudCoordinateStatus
from prml_vslam.interfaces import FramePacket
from prml_vslam.methods.contracts import SlamBackendConfig, SlamOutputPolicy
from prml_vslam.methods.protocols import ProcessStreamingSlamBackend, SlamSession, StreamingSlamBackend
from prml_vslam.methods.updates import SlamUpdate
from prml_vslam.pipeline.contracts.artifacts import ArtifactRef, SlamArtifacts
from prml_vslam.pipeline.contracts.execution import (
    StageExecutionKey,
    StageExecutionMode,
    StageResult,
    StreamingStageEvent,
    StreamingStageEventKind,
)
from prml_vslam.pipeline.contracts.plan import RunPlan, RunPlanStageId
from prml_vslam.pipeline.contracts.provenance import StageExecutionStatus
from prml_vslam.pipeline.contracts.request import RunRequest
from prml_vslam.pipeline.contracts.sequence import SequenceManifest
from prml_vslam.pipeline.finalization import (
    compute_trajectory_evaluation,
    finalize_stage_results,
    stable_hash,
    write_json,
)
from prml_vslam.pipeline.runner_runtime import RunnerRuntime
from prml_vslam.pipeline.state import RunState, StreamingRunSnapshot
from prml_vslam.protocols.source import BenchmarkInputSource, StreamingSequenceSource
from prml_vslam.utils import Console, RunArtifactPaths
from prml_vslam.utils.packet_session import PacketSessionMetrics, extract_pose_position
from prml_vslam.visualization import VisualizationArtifacts

_EVENT_POLL_SECONDS = 0.05
_PACKET_QUEUE_SIZE = 2
_WORKER_JOIN_TIMEOUT_SECONDS = 10.0
_INGEST_STAGE_PROCESS_TIMEOUT_SECONDS = 60.0
_TRAJECTORY_EVALUATION_STAGE_PROCESS_TIMEOUT_SECONDS = 60.0
_SUMMARY_STAGE_PROCESS_TIMEOUT_SECONDS = 15.0
_FINAL_UPDATE_DRAIN_TIMEOUT_SECONDS = 0.25
_FINAL_UPDATE_DRAIN_POLL_SECONDS = 0.02
_PACKET_SENTINEL = None


class _ViewerHooks(Protocol):
    """Patchable viewer hook surface used by the streaming coordinator."""

    def create_recording_stream(self, *, app_id: str, recording_id: str | None = None) -> object: ...

    def attach_recording_sinks(
        self,
        recording_stream: object,
        *,
        grpc_url: str | None = None,
        target_path: object | None = None,
    ) -> None: ...

    def collect_native_visualization_artifacts(
        self,
        *,
        native_output_dir: Path,
        preserve_native_rerun: bool,
    ) -> VisualizationArtifacts | None: ...

    def log_transform(self, recording_stream: object, *, entity_path: str, transform: object) -> None: ...

    def log_pointcloud(
        self,
        recording_stream: object,
        *,
        entity_path: str,
        pointmap: np.ndarray,
        colors: np.ndarray | None = None,
    ) -> None: ...

    def log_points3d(
        self,
        recording_stream: object,
        *,
        entity_path: str,
        points_xyz: np.ndarray,
        colors: np.ndarray | None = None,
        radii: float = 0.05,
    ) -> None: ...

    def log_preview_image(self, recording_stream: object, *, entity_path: str, image_rgb: np.ndarray) -> None: ...

    def log_y_up_view_coordinates(self, recording_stream: object, *, entity_path: str) -> None: ...

    def set_time_sequence(self, recording_stream: object, *, timeline: str, sequence: int) -> None: ...

    def load_point_cloud_ply(self, path: Path) -> np.ndarray: ...

    def viewer_pose_from_update(self, update: SlamUpdate, *, method_id: object) -> object: ...


@dataclass(slots=True)
class _WorkerHandle:
    worker: threading.Thread | mp.Process
    mode: StageExecutionMode

    def start(self) -> None:
        self.worker.start()

    def is_alive(self) -> bool:
        return bool(self.worker.is_alive())

    def join(self, timeout: float | None = None) -> None:
        self.worker.join(timeout=timeout)

    def terminate(self) -> None:
        if self.mode is StageExecutionMode.PROCESS and self.worker.is_alive():
            assert isinstance(self.worker, mp.Process)
            self.worker.terminate()
        self.worker.join(timeout=_WORKER_JOIN_TIMEOUT_SECONDS)


@dataclass(slots=True)
class _BackendSessionFactory:
    backend: StreamingSlamBackend
    backend_config: SlamBackendConfig
    output_policy: SlamOutputPolicy
    artifact_root: Path

    def __call__(self) -> SlamSession:
        return self.backend.start_session(self.backend_config, self.output_policy, self.artifact_root)


class StreamingCoordinator:
    """Coordinate one streaming pipeline run and its optional worker processes."""

    def __init__(
        self,
        *,
        runtime: RunnerRuntime[StreamingRunSnapshot],
        console: Console,
        frame_timeout_seconds: float,
        fps_window_size: int,
        trajectory_window_size: int,
        viewer_hooks: _ViewerHooks,
    ) -> None:
        self._runtime = runtime
        self._console = console
        self._frame_timeout_seconds = frame_timeout_seconds
        self._fps_window_size = fps_window_size
        self._trajectory_window_size = trajectory_window_size
        self._viewer_hooks = viewer_hooks

    def run(
        self,
        *,
        stop_event: threading.Event,
        request: RunRequest,
        plan: RunPlan,
        source: StreamingSequenceSource,
        slam_backend: StreamingSlamBackend,
    ) -> None:
        """Run the streaming pipeline through a coordinator-owned event loop."""
        run_paths = RunArtifactPaths.build(plan.artifact_root)
        policy = request.execution.streaming
        stage_results: list[StageResult] = []
        sequence_manifest: SequenceManifest | None = None
        benchmark_inputs: PreparedBenchmarkInputs | None = None
        slam_artifacts: SlamArtifacts | None = None
        visualization_artifacts: VisualizationArtifacts | None = None
        summary = None
        stage_manifests = []
        final_state = RunState.COMPLETED
        error_message = ""

        try:
            self._console.info(f"Preparing streaming run '{plan.run_id}' from source '{source.label}'.")
            ingest_result = execute_finite_stage(
                stage_id=RunPlanStageId.INGEST,
                mode=policy.ingest,
                target=_run_streaming_ingest_stage,
                kwargs={
                    "source_payload": _source_payload(source, policy.ingest),
                    "request": request,
                    "run_paths": run_paths,
                },
                timeout_seconds=_stage_process_timeout_seconds(RunPlanStageId.INGEST),
                config_hash=stable_hash(request.source),
                input_fingerprint=stable_hash(request.source),
            )
            stage_results.append(ingest_result)
            _raise_if_failed(ingest_result)
            sequence_manifest = ingest_result.sequence_manifest
            benchmark_inputs = ingest_result.benchmark_inputs
            self._runtime.update_fields(
                state=RunState.PREPARING,
                plan=plan,
                sequence_manifest=sequence_manifest,
                benchmark_inputs=benchmark_inputs,
                error_message="",
            )

            live_recording = None
            if request.visualization.connect_live_viewer or request.visualization.export_viewer_rrd:
                live_recording = self._viewer_hooks.create_recording_stream(
                    app_id="prml-vslam", recording_id=plan.run_id
                )
                self._viewer_hooks.attach_recording_sinks(
                    live_recording,
                    grpc_url=request.visualization.grpc_url if request.visualization.connect_live_viewer else None,
                    target_path=run_paths.viewer_rrd_path if request.visualization.export_viewer_rrd else None,
                )
                self._viewer_hooks.log_y_up_view_coordinates(live_recording, entity_path="world")
                self._log_reference_clouds(live_recording, benchmark_inputs)

            slam_result = self._run_streaming_workers(
                stop_event=stop_event,
                request=request,
                plan=plan,
                source=source,
                slam_backend=slam_backend,
                sequence_manifest=sequence_manifest,
                live_recording=live_recording,
            )
            visualization_artifacts = _collect_visualization_artifacts(
                request,
                run_paths,
                plan,
                collect_native_visualization_artifacts=self._viewer_hooks.collect_native_visualization_artifacts,
            )
            slam_result = _with_slam_visualization_outputs(slam_result, visualization_artifacts)
            stage_results.append(slam_result)
            slam_artifacts = slam_result.slam
            if stop_event.is_set():
                final_state = RunState.STOPPED
            else:
                _raise_if_failed(slam_result)

            if final_state is RunState.COMPLETED and _has_stage(plan, RunPlanStageId.TRAJECTORY_EVALUATION):
                eval_result = execute_finite_stage(
                    stage_id=RunPlanStageId.TRAJECTORY_EVALUATION,
                    mode=policy.trajectory_evaluation,
                    target=_run_trajectory_evaluation_stage,
                    kwargs={
                        "request": request,
                        "plan": plan,
                        "sequence_manifest": sequence_manifest,
                        "benchmark_inputs": benchmark_inputs,
                        "slam": slam_artifacts,
                    },
                    timeout_seconds=_stage_process_timeout_seconds(RunPlanStageId.TRAJECTORY_EVALUATION),
                    config_hash=stable_hash(request.benchmark.trajectory),
                    input_fingerprint=stable_hash(
                        {
                            "benchmark_inputs": benchmark_inputs,
                            "slam_trajectory": None if slam_artifacts is None else slam_artifacts.trajectory_tum,
                        }
                    ),
                )
                stage_results.append(eval_result)
                _raise_if_failed(eval_result)
        except Exception as exc:
            if final_state is not RunState.STOPPED:
                final_state = RunState.FAILED
            error_message = str(exc)
            self._console.error(error_message)
        finally:
            try:
                summary_result = execute_finite_stage(
                    stage_id=RunPlanStageId.SUMMARY,
                    mode=policy.summary,
                    target=_run_summary_stage,
                    kwargs={
                        "request": request,
                        "plan": plan,
                        "run_paths": run_paths,
                        "stage_results": stage_results,
                        "error_message": error_message,
                    },
                    timeout_seconds=_stage_process_timeout_seconds(RunPlanStageId.SUMMARY),
                    config_hash=stable_hash({"experiment_name": request.experiment_name, "mode": request.mode}),
                    input_fingerprint=stable_hash(stage_results),
                )
                stage_results.append(summary_result)
                if summary_result.status is StageExecutionStatus.FAILED:
                    final_state = RunState.FAILED
                    error_message = summary_result.error_message
                summary = summary_result.summary
                stage_manifests = summary_result.stage_manifests
            except Exception as exc:
                final_state = RunState.FAILED
                error_message = str(exc)
                self._console.error(f"Finalization failed: {exc}")
            self._runtime.finalize(
                stop_event=stop_event,
                snapshot_update=lambda snapshot: snapshot.model_copy(
                    update={
                        "state": final_state,
                        "plan": plan,
                        "sequence_manifest": sequence_manifest,
                        "benchmark_inputs": benchmark_inputs,
                        "slam": slam_artifacts,
                        "visualization": visualization_artifacts,
                        "summary": summary,
                        "stage_manifests": stage_manifests,
                        "error_message": error_message,
                    }
                ),
            )

    def _log_reference_clouds(
        self,
        recording_stream: object,
        benchmark_inputs: PreparedBenchmarkInputs | None,
    ) -> None:
        """Log aligned reference clouds into the viewer when available."""
        if benchmark_inputs is None:
            return
        for reference_cloud in benchmark_inputs.reference_clouds:
            if reference_cloud.coordinate_status is not ReferenceCloudCoordinateStatus.ALIGNED:
                continue
            try:
                points_xyz = self._viewer_hooks.load_point_cloud_ply(reference_cloud.path)
                self._viewer_hooks.log_points3d(
                    recording_stream,
                    entity_path=f"world/reference/aligned_gt_world/{reference_cloud.source.value}",
                    points_xyz=points_xyz,
                )
            except Exception as exc:
                self._console.warning(
                    f"Skipping aligned reference cloud '{reference_cloud.source.value}' at "
                    f"'{reference_cloud.path}': {exc}"
                )

    def _run_streaming_workers(
        self,
        *,
        stop_event: threading.Event,
        request: RunRequest,
        plan: RunPlan,
        source: StreamingSequenceSource,
        slam_backend: StreamingSlamBackend,
        sequence_manifest: SequenceManifest | None,
        live_recording: object | None,
    ) -> StageResult:
        ctx = mp.get_context("spawn")
        packet_queue = ctx.Queue(maxsize=_PACKET_QUEUE_SIZE)
        event_queue = ctx.Queue()
        worker_stop = ctx.Event()
        policy = request.execution.streaming
        packet_source_error = ""
        slam_result: StageResult | None = None
        metrics = PacketSessionMetrics(
            fps_window_size=self._fps_window_size,
            trajectory_window_size=self._trajectory_window_size,
        )
        latest_preview_update: SlamUpdate | None = None
        start_timestamp_ns: int | None = None

        def apply_slam_updates(updates: list[SlamUpdate], *, arrival_time_s: float) -> None:
            nonlocal latest_preview_update, start_timestamp_ns
            for update in updates:
                if _has_renderable_preview(update):
                    latest_preview_update = update
                if update.is_keyframe:
                    keyframe_position_xyz = extract_pose_position(update)
                    update_timestamp_ns = update.source_timestamp_ns or update.timestamp_ns
                    if start_timestamp_ns is None:
                        start_timestamp_ns = update_timestamp_ns
                    metrics.record_keyframe(
                        arrival_time_s=arrival_time_s,
                        position_xyz=keyframe_position_xyz,
                        trajectory_time_s=(update_timestamp_ns - start_timestamp_ns) / 1e9
                        if update.pose is not None and start_timestamp_ns is not None
                        else None,
                    )
                    if live_recording is not None and update.pose is not None:
                        viewer_pose = self._viewer_hooks.viewer_pose_from_update(update, method_id=request.slam.method)
                        live_camera_entity = "world/live_camera"
                        self._viewer_hooks.log_transform(
                            live_recording,
                            entity_path=live_camera_entity,
                            transform=viewer_pose,
                        )
                        if update.preview_rgb is not None:
                            self._viewer_hooks.log_preview_image(
                                live_recording,
                                entity_path=f"{live_camera_entity}/preview",
                                image_rgb=update.preview_rgb,
                            )
                        if update.keyframe_index is not None:
                            self._viewer_hooks.set_time_sequence(
                                live_recording,
                                timeline="keyframe",
                                sequence=update.keyframe_index,
                            )
                            keyframe_entity = f"world/est/cam_{update.keyframe_index:06d}"
                            self._viewer_hooks.log_transform(
                                live_recording,
                                entity_path=keyframe_entity,
                                transform=viewer_pose,
                            )
                            if update.pointmap is not None:
                                self._viewer_hooks.log_pointcloud(
                                    live_recording,
                                    entity_path=f"{keyframe_entity}/points",
                                    pointmap=update.pointmap,
                                    colors=update.preview_rgb,
                                )
                            if update.preview_rgb is not None:
                                self._viewer_hooks.log_preview_image(
                                    live_recording,
                                    entity_path=f"{keyframe_entity}/preview",
                                    image_rgb=update.preview_rgb,
                                )
                self._runtime.update_fields(
                    state=RunState.RUNNING,
                    latest_slam_update=update,
                    latest_preview_update=latest_preview_update,
                    num_sparse_points=update.num_sparse_points,
                    num_dense_points=update.num_dense_points,
                    error_message="",
                    **metrics.keyframe_snapshot_fields(),
                )

        def handle_event(event: StreamingStageEvent) -> None:
            nonlocal packet_source_error, slam_result, start_timestamp_ns
            match event.kind:
                case StreamingStageEventKind.PACKET:
                    packet = event.packet
                    if packet is None:
                        return
                    if start_timestamp_ns is None:
                        start_timestamp_ns = packet.timestamp_ns
                    metrics.record_packet(arrival_time_s=time.monotonic())
                    self._runtime.update_fields(
                        state=RunState.RUNNING,
                        latest_packet=packet,
                        error_message="",
                        **metrics.packet_snapshot_fields(),
                    )
                case StreamingStageEventKind.SLAM_UPDATE:
                    if event.slam_update is not None:
                        apply_slam_updates([event.slam_update], arrival_time_s=time.monotonic())
                case StreamingStageEventKind.ERROR:
                    packet_source_error = event.error_message
                    worker_stop.set()
                case StreamingStageEventKind.STAGE_RESULT:
                    slam_result = event.stage_result
                case StreamingStageEventKind.EOF | StreamingStageEventKind.STOPPED:
                    return

        def drain_pending_events() -> None:
            while True:
                try:
                    event = event_queue.get_nowait()
                except queue.Empty:
                    return
                if isinstance(event, StreamingStageEvent):
                    handle_event(event)

        source_handle = _start_worker(
            mode=policy.packet_source,
            name=f"Pipeline-packet-source-{plan.run_id}",
            target=_packet_source_worker,
            args=(
                _source_payload(source, policy.packet_source),
                packet_queue,
                event_queue,
                worker_stop,
                self._frame_timeout_seconds,
                request.slam.backend.max_frames,
            ),
            ctx=ctx,
        )
        slam_handle = _start_worker(
            mode=policy.slam,
            name=f"Pipeline-slam-{plan.run_id}",
            target=_slam_worker,
            args=(
                _slam_session_factory(slam_backend, request, plan, policy.slam),
                packet_queue,
                event_queue,
                worker_stop,
                stable_hash(request.slam),
                stable_hash(sequence_manifest or {"missing": "sequence_manifest"}),
            ),
            ctx=ctx,
        )
        source_handle.start()
        slam_handle.start()
        self._runtime.update_fields(state=RunState.RUNNING, error_message="")

        try:
            while slam_result is None:
                if stop_event.is_set():
                    worker_stop.set()
                try:
                    event = event_queue.get(timeout=_EVENT_POLL_SECONDS)
                except queue.Empty:
                    if not slam_handle.is_alive() and not source_handle.is_alive():
                        drain_pending_events()
                        break
                    continue
                if not isinstance(event, StreamingStageEvent):
                    continue
                handle_event(event)
            if slam_result is None:
                drain_pending_events()
            if slam_result is None:
                slam_result = _failed_result(
                    RunPlanStageId.SLAM,
                    StageExecutionKey.SLAM,
                    stable_hash(request.slam),
                    stable_hash(sequence_manifest or {"missing": "sequence_manifest"}),
                    packet_source_error or "Streaming SLAM worker exited without a stage result.",
                )
            if packet_source_error and slam_result.status is not StageExecutionStatus.FAILED:
                slam_result = slam_result.model_copy(
                    update={"status": StageExecutionStatus.FAILED, "error_message": packet_source_error}
                )
            return slam_result
        finally:
            worker_stop.set()
            _stop_worker(source_handle)
            _stop_worker(slam_handle)


def execute_finite_stage(
    *,
    stage_id: RunPlanStageId,
    mode: StageExecutionMode,
    target: Callable[..., StageResult],
    kwargs: dict[str, object],
    timeout_seconds: float,
    config_hash: str,
    input_fingerprint: str,
) -> StageResult:
    """Execute a finite stage locally or in a spawned subprocess."""
    execution_key = _finite_stage_execution_key(stage_id)
    if mode is StageExecutionMode.LOCAL:
        try:
            return target(**kwargs)
        except Exception as exc:
            return _failed_result(stage_id, execution_key, config_hash, input_fingerprint, str(exc))
    _assert_pickleable(kwargs, "stage process arguments")
    ctx = mp.get_context("spawn")
    result_queue = ctx.Queue(maxsize=1)
    process = ctx.Process(target=_finite_stage_worker, args=(target, kwargs, result_queue), daemon=True)
    process.start()
    process.join(timeout=timeout_seconds)
    if process.is_alive():
        process.terminate()
        process.join(timeout=_WORKER_JOIN_TIMEOUT_SECONDS)
        return _failed_result(
            stage_id,
            execution_key,
            config_hash,
            input_fingerprint,
            _stage_process_timeout_error(stage_id, timeout_seconds),
        )
    try:
        result = result_queue.get_nowait()
    except queue.Empty:
        return _failed_result(
            stage_id,
            execution_key,
            config_hash,
            input_fingerprint,
            f"{stage_id.value} stage exited without returning a result.",
        )
    if isinstance(result, Exception):
        return _failed_result(stage_id, execution_key, config_hash, input_fingerprint, str(result))
    if process.exitcode not in {0, None} and result.status is not StageExecutionStatus.FAILED:
        return _failed_result(
            stage_id,
            execution_key,
            config_hash,
            input_fingerprint,
            f"{stage_id.value} stage worker exited with code {process.exitcode}.",
        )
    return result


def _finite_stage_execution_key(stage_id: RunPlanStageId) -> StageExecutionKey:
    """Return the execution key corresponding to one finite stage id."""
    match stage_id:
        case RunPlanStageId.INGEST:
            return StageExecutionKey.INGEST
        case RunPlanStageId.TRAJECTORY_EVALUATION:
            return StageExecutionKey.TRAJECTORY_EVALUATION
        case RunPlanStageId.SUMMARY:
            return StageExecutionKey.SUMMARY
        case _:
            raise ValueError(f"Unexpected finite stage id for execution key: {stage_id.value}")


def _stage_process_timeout_seconds(stage_id: RunPlanStageId) -> float:
    """Return the bounded process timeout for one finite streaming stage."""
    match stage_id:
        case RunPlanStageId.INGEST:
            return _INGEST_STAGE_PROCESS_TIMEOUT_SECONDS
        case RunPlanStageId.TRAJECTORY_EVALUATION:
            return _TRAJECTORY_EVALUATION_STAGE_PROCESS_TIMEOUT_SECONDS
        case RunPlanStageId.SUMMARY:
            return _SUMMARY_STAGE_PROCESS_TIMEOUT_SECONDS
        case _:
            raise ValueError(f"Unexpected finite stage id for process timeout: {stage_id.value}")


def _stage_process_timeout_error(stage_id: RunPlanStageId, timeout_seconds: float) -> str:
    """Return the operator-facing timeout error for one finite stage."""
    timeout_label = f"{timeout_seconds:.1f}" if timeout_seconds >= 1.0 else f"{timeout_seconds:.2f}"
    return f"{stage_id.value} stage exceeded process timeout ({timeout_label}s)."


def _finite_stage_worker(target: Callable[..., StageResult], kwargs: dict[str, object], result_queue: object) -> None:
    try:
        result_queue.put(target(**kwargs))
    except Exception as exc:
        result_queue.put(exc)


def _run_streaming_ingest_stage(
    source_payload: object, request: RunRequest, run_paths: RunArtifactPaths
) -> StageResult:
    source = _source_from_payload(source_payload)
    sequence_manifest = source.prepare_sequence_manifest(run_paths.sequence_manifest_path.parent)
    benchmark_inputs = None
    output_paths = {"sequence_manifest": run_paths.sequence_manifest_path}
    if isinstance(source, BenchmarkInputSource):
        benchmark_inputs = source.prepare_benchmark_inputs(run_paths.benchmark_inputs_path.parent)
        if benchmark_inputs is not None:
            write_json(run_paths.benchmark_inputs_path, benchmark_inputs)
            output_paths["benchmark_inputs"] = run_paths.benchmark_inputs_path
            for reference in benchmark_inputs.reference_trajectories:
                output_paths[f"reference_tum:{reference.source.value}"] = reference.path
    write_json(run_paths.sequence_manifest_path, sequence_manifest)
    return StageResult(
        stage_id=RunPlanStageId.INGEST,
        execution_key=StageExecutionKey.INGEST,
        status=StageExecutionStatus.RAN,
        config_hash=stable_hash(request.source),
        input_fingerprint=stable_hash(request.source),
        output_paths=output_paths,
        sequence_manifest=sequence_manifest,
        benchmark_inputs=benchmark_inputs,
    )


def _run_trajectory_evaluation_stage(
    request: RunRequest,
    plan: RunPlan,
    sequence_manifest: SequenceManifest | None,
    benchmark_inputs: PreparedBenchmarkInputs | None,
    slam: SlamArtifacts | None,
) -> StageResult:
    trajectory_evaluation = compute_trajectory_evaluation(
        request=request,
        plan=plan,
        sequence_manifest=sequence_manifest,
        benchmark_inputs=benchmark_inputs,
        slam=slam,
    )
    output_paths = {}
    if trajectory_evaluation is not None:
        output_paths = {
            "trajectory_metrics": trajectory_evaluation.path,
            "reference_tum": trajectory_evaluation.reference_path,
            "estimate_tum": trajectory_evaluation.estimate_path,
        }
    return StageResult(
        stage_id=RunPlanStageId.TRAJECTORY_EVALUATION,
        execution_key=StageExecutionKey.TRAJECTORY_EVALUATION,
        status=StageExecutionStatus.RAN,
        config_hash=stable_hash(request.benchmark.trajectory),
        input_fingerprint=stable_hash(
            {
                "benchmark_inputs": benchmark_inputs,
                "slam_trajectory": None if slam is None else slam.trajectory_tum,
            }
        ),
        output_paths=output_paths,
        trajectory_evaluation=trajectory_evaluation,
    )


def _run_summary_stage(
    request: RunRequest,
    plan: RunPlan,
    run_paths: RunArtifactPaths,
    stage_results: list[StageResult],
    error_message: str,
) -> StageResult:
    return finalize_stage_results(
        request=request,
        plan=plan,
        run_paths=run_paths,
        stage_results=stage_results,
        error_message=error_message,
    )


def _packet_source_worker(
    source_payload: object,
    packet_queue: object,
    event_queue: object,
    stop_event: object,
    frame_timeout_seconds: float,
    max_frames: int | None,
) -> None:
    source = _source_from_payload(source_payload)
    stream = None
    frames_sent = 0
    try:
        stream = source.open_stream(loop=True)
        stream.connect()
        while not stop_event.is_set():
            if max_frames is not None and frames_sent >= max_frames:
                break
            try:
                packet = stream.wait_for_packet(timeout_seconds=frame_timeout_seconds)
            except EOFError:
                event_queue.put(
                    StreamingStageEvent(kind=StreamingStageEventKind.EOF, execution_key=StageExecutionKey.PACKET_SOURCE)
                )
                break
            event_queue.put(
                StreamingStageEvent(
                    kind=StreamingStageEventKind.PACKET,
                    execution_key=StageExecutionKey.PACKET_SOURCE,
                    packet=packet,
                )
            )
            _queue_put(packet_queue, packet.to_ipc_bytes(), stop_event)
            frames_sent += 1
        event_queue.put(
            StreamingStageEvent(kind=StreamingStageEventKind.STOPPED, execution_key=StageExecutionKey.PACKET_SOURCE)
        )
    except Exception as exc:
        event_queue.put(
            StreamingStageEvent(
                kind=StreamingStageEventKind.ERROR,
                execution_key=StageExecutionKey.PACKET_SOURCE,
                error_message=str(exc),
            )
        )
    finally:
        _queue_put(packet_queue, _PACKET_SENTINEL, stop_event, force=True)
        if stream is not None:
            stream.disconnect()


def _slam_worker(
    session_factory: Callable[[], SlamSession],
    packet_queue: object,
    event_queue: object,
    stop_event: object,
    config_hash: str,
    input_fingerprint: str,
) -> None:
    session = None
    try:
        session = session_factory()
        while not stop_event.is_set():
            try:
                packet_payload = packet_queue.get(timeout=_EVENT_POLL_SECONDS)
            except queue.Empty:
                continue
            if packet_payload is _PACKET_SENTINEL:
                break
            packet = FramePacket.from_ipc_bytes(packet_payload)
            session.step(packet)
            _emit_slam_updates(session, event_queue)
        artifacts = session.close()
        _emit_slam_updates(session, event_queue, timeout_seconds=_FINAL_UPDATE_DRAIN_TIMEOUT_SECONDS)
        event_queue.put(
            StreamingStageEvent(
                kind=StreamingStageEventKind.STAGE_RESULT,
                execution_key=StageExecutionKey.SLAM,
                stage_result=_slam_stage_result(
                    status=StageExecutionStatus.RAN,
                    config_hash=config_hash,
                    input_fingerprint=input_fingerprint,
                    slam=artifacts,
                ),
            )
        )
    except Exception as exc:
        event_queue.put(
            StreamingStageEvent(
                kind=StreamingStageEventKind.STAGE_RESULT,
                execution_key=StageExecutionKey.SLAM,
                stage_result=_failed_result(
                    RunPlanStageId.SLAM,
                    StageExecutionKey.SLAM,
                    config_hash,
                    input_fingerprint,
                    str(exc),
                ),
            )
        )


def _emit_slam_updates(
    session: SlamSession,
    event_queue: object,
    *,
    timeout_seconds: float = 0.0,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    while True:
        updates = session.try_get_updates()
        for update in updates:
            event_queue.put(
                StreamingStageEvent(
                    kind=StreamingStageEventKind.SLAM_UPDATE,
                    execution_key=StageExecutionKey.SLAM,
                    slam_update=update,
                )
            )
        if updates:
            continue
        if timeout_seconds <= 0.0 or time.monotonic() >= deadline:
            return
        time.sleep(min(_FINAL_UPDATE_DRAIN_POLL_SECONDS, max(0.0, deadline - time.monotonic())))


def _start_worker(
    *,
    mode: StageExecutionMode,
    name: str,
    target: Callable[..., None],
    args: tuple[object, ...],
    ctx: mp.context.BaseContext,
) -> _WorkerHandle:
    if mode is StageExecutionMode.PROCESS:
        return _WorkerHandle(worker=ctx.Process(target=target, args=args, name=name, daemon=True), mode=mode)
    return _WorkerHandle(worker=threading.Thread(target=target, args=args, name=name, daemon=True), mode=mode)


def _stop_worker(handle: _WorkerHandle) -> None:
    handle.join(timeout=_WORKER_JOIN_TIMEOUT_SECONDS)
    if handle.is_alive():
        handle.terminate()


def _queue_put(target_queue: object, value: object, stop_event: object, *, force: bool = False) -> None:
    deadline = time.monotonic() + 1.0 if force else None
    while force or not stop_event.is_set():
        try:
            target_queue.put(value, timeout=_EVENT_POLL_SECONDS)
            return
        except queue.Full:
            if force and deadline is not None and time.monotonic() >= deadline:
                return


def _source_payload(source: StreamingSequenceSource, mode: StageExecutionMode) -> object:
    payload = getattr(source, "config", source) if mode is StageExecutionMode.PROCESS else source
    if mode is StageExecutionMode.PROCESS:
        _assert_pickleable(payload, "streaming source")
    return payload


def _source_from_payload(payload: object) -> StreamingSequenceSource:
    setup_target = getattr(payload, "setup_target", None)
    if callable(setup_target):
        source = setup_target()
        if source is None:
            raise RuntimeError("Config-backed streaming source setup returned None.")
        return source
    return payload


def _slam_session_factory(
    backend: StreamingSlamBackend,
    request: RunRequest,
    plan: RunPlan,
    mode: StageExecutionMode,
) -> Callable[[], SlamSession]:
    if mode is StageExecutionMode.PROCESS and isinstance(backend, ProcessStreamingSlamBackend):
        factory = backend.streaming_session_factory(request.slam.backend, request.slam.outputs, plan.artifact_root)
    else:
        factory = _BackendSessionFactory(
            backend=backend,
            backend_config=request.slam.backend,
            output_policy=request.slam.outputs,
            artifact_root=plan.artifact_root,
        )
    if mode is StageExecutionMode.PROCESS:
        _assert_pickleable(factory, "streaming SLAM session factory")
    return factory


def _assert_pickleable(value: object, label: str) -> None:
    try:
        pickle.dumps(value)
    except Exception as exc:
        raise RuntimeError(f"{label} is not process-safe; use local execution or a config-backed factory.") from exc


def _source_artifact_paths(slam: SlamArtifacts | None, visualization: VisualizationArtifacts | None) -> dict[str, Path]:
    output_paths: dict[str, Path] = {}
    if slam is not None:
        output_paths["trajectory_tum"] = slam.trajectory_tum.path
        if slam.sparse_points_ply is not None:
            output_paths["sparse_points_ply"] = slam.sparse_points_ply.path
        if slam.dense_points_ply is not None:
            output_paths["dense_points_ply"] = slam.dense_points_ply.path
        for key, artifact in slam.extras.items():
            output_paths[f"extra:{key}"] = artifact.path
    if visualization is not None:
        if visualization.native_rerun_rrd is not None:
            output_paths["native_rerun_rrd"] = visualization.native_rerun_rrd.path
        if visualization.native_output_dir is not None:
            output_paths["native_output_dir"] = visualization.native_output_dir.path
        for key, artifact in visualization.extras.items():
            output_paths[f"visualization:{key}"] = artifact.path
    return output_paths


def _slam_stage_result(
    *,
    status: StageExecutionStatus,
    config_hash: str,
    input_fingerprint: str,
    slam: SlamArtifacts | None = None,
    visualization: VisualizationArtifacts | None = None,
    error_message: str = "",
) -> StageResult:
    return StageResult(
        stage_id=RunPlanStageId.SLAM,
        execution_key=StageExecutionKey.SLAM,
        status=status,
        config_hash=config_hash,
        input_fingerprint=input_fingerprint,
        output_paths=_source_artifact_paths(slam, visualization),
        error_message=error_message,
        slam=slam,
        visualization=visualization,
    )


def _with_slam_visualization_outputs(
    result: StageResult,
    visualization: VisualizationArtifacts | None,
) -> StageResult:
    return _slam_stage_result(
        status=result.status,
        config_hash=result.config_hash,
        input_fingerprint=result.input_fingerprint,
        slam=result.slam,
        visualization=visualization,
        error_message=result.error_message,
    )


def _collect_visualization_artifacts(
    request: RunRequest,
    run_paths: RunArtifactPaths,
    plan: RunPlan,
    *,
    collect_native_visualization_artifacts: Callable[..., VisualizationArtifacts | None],
) -> VisualizationArtifacts | None:
    visualization_artifacts = collect_native_visualization_artifacts(
        native_output_dir=run_paths.native_output_dir,
        preserve_native_rerun=request.visualization.preserve_native_rerun,
    )
    if request.visualization.export_viewer_rrd and run_paths.viewer_rrd_path.exists():
        repo_rrd_ref = ArtifactRef(
            path=run_paths.viewer_rrd_path.resolve(),
            kind="rrd",
            fingerprint=f"viewer-rrd-{plan.run_id}",
        )
        if visualization_artifacts is None:
            visualization_artifacts = VisualizationArtifacts()
        visualization_artifacts.extras["viewer_rrd"] = repo_rrd_ref
    return visualization_artifacts


def _failed_result(
    stage_id: RunPlanStageId,
    execution_key: StageExecutionKey,
    config_hash: str,
    input_fingerprint: str,
    error_message: str,
) -> StageResult:
    return StageResult(
        stage_id=stage_id,
        execution_key=execution_key,
        status=StageExecutionStatus.FAILED,
        config_hash=config_hash,
        input_fingerprint=input_fingerprint,
        error_message=error_message,
    )


def _raise_if_failed(result: StageResult) -> None:
    if result.status is StageExecutionStatus.FAILED:
        raise RuntimeError(result.error_message or f"Stage '{result.stage_id.value}' failed.")


def _has_stage(plan: RunPlan, stage_id: RunPlanStageId) -> bool:
    return any(stage.id is stage_id for stage in plan.stages)


def _has_renderable_preview(update: SlamUpdate) -> bool:
    """Return whether one backend update exposes a non-empty preview payload."""
    if update.preview_rgb is not None and np.asarray(update.preview_rgb).size > 0:
        return True
    if update.pointmap is None:
        return False
    pointmap = np.asarray(update.pointmap)
    return pointmap.size > 0 and pointmap.ndim in {2, 3}


__all__ = ["StreamingCoordinator", "execute_finite_stage"]
