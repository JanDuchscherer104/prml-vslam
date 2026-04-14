"""Streaming pipeline runner."""

from __future__ import annotations

import time
from threading import Event

import numpy as np

from prml_vslam.benchmark import PreparedBenchmarkInputs
from prml_vslam.methods.protocols import SlamSession, StreamingSlamBackend
from prml_vslam.methods.updates import SlamUpdate
from prml_vslam.pipeline.contracts.artifacts import ArtifactRef
from prml_vslam.pipeline.contracts.plan import RunPlan
from prml_vslam.pipeline.contracts.request import RunRequest
from prml_vslam.pipeline.state import RunState, StreamingRunSnapshot
from prml_vslam.protocols.source import BenchmarkInputSource, StreamingSequenceSource
from prml_vslam.utils import Console, RunArtifactPaths
from prml_vslam.utils.packet_session import (
    PacketSessionMetrics,
    extract_pose_position,
)
from prml_vslam.visualization import VisualizationArtifacts
from prml_vslam.visualization.rerun import (
    attach_file_sink,
    attach_grpc_sink,
    collect_native_visualization_artifacts,
    create_recording_stream,
    log_pointcloud,
    log_preview_image,
    log_transform,
)

from .finalization import compute_trajectory_evaluation, finalize_run_outputs, write_json
from .runner_runtime import RunnerRuntime

_STOP_JOIN_TIMEOUT_SECONDS = 10.0


class StreamingRunner:
    """Own one threaded streaming run over a live or replayed packet stream."""

    def __init__(
        self,
        *,
        frame_timeout_seconds: float = 5.0,
        fps_window_size: int = 20,
        trajectory_window_size: int = 100,
    ) -> None:
        self.frame_timeout_seconds = frame_timeout_seconds
        self.fps_window_size = fps_window_size
        self.trajectory_window_size = trajectory_window_size
        self._console = Console(__name__).child(self.__class__.__name__)
        self._runtime = RunnerRuntime(
            empty_snapshot=StreamingRunSnapshot,
            stop_timeout_message="Streaming worker thread did not stop within the timeout.",
        )

    def start(
        self,
        *,
        request: RunRequest,
        plan: RunPlan,
        source: StreamingSequenceSource,
        slam_backend: StreamingSlamBackend,
    ) -> None:
        """Launch the streaming pipeline in a dedicated worker thread."""
        self._runtime.launch(
            starting_snapshot=StreamingRunSnapshot(state=RunState.PREPARING, plan=plan),
            thread_name=f"Pipeline-streaming-{plan.run_id}",
            worker_target=lambda stop_event: self._run_worker(
                stop_event=stop_event,
                request=request,
                plan=plan,
                source=source,
                slam_backend=slam_backend,
            ),
        )

    def stop(self) -> None:
        """Stop the active streaming run."""
        self._runtime.stop(snapshot_update=_to_stopped_snapshot, join_timeout_seconds=_STOP_JOIN_TIMEOUT_SECONDS)

    def snapshot(self) -> StreamingRunSnapshot:
        """Return the latest streaming runtime snapshot."""
        return self._runtime.snapshot()

    def set_failed_start(self, *, plan: RunPlan, error_message: str) -> None:
        """Set the initial snapshot state for a run that failed to start."""
        self.stop()
        self._runtime.replace_snapshot(
            StreamingRunSnapshot(state=RunState.FAILED, plan=plan, error_message=error_message)
        )

    def _run_worker(
        self,
        *,
        stop_event: Event,
        request: RunRequest,
        plan: RunPlan,
        source: StreamingSequenceSource,
        slam_backend: StreamingSlamBackend,
    ) -> None:
        metrics = PacketSessionMetrics(
            fps_window_size=self.fps_window_size,
            trajectory_window_size=self.trajectory_window_size,
        )
        run_paths = RunArtifactPaths.build(plan.artifact_root)
        slam_session: SlamSession | None = None
        ingest_started = False
        slam_started = False
        pipeline_failed = False
        error_message = ""
        sequence_manifest = None
        benchmark_inputs: PreparedBenchmarkInputs | None = None
        slam_artifacts = None
        visualization_artifacts = None
        latest_preview_update = None
        trajectory_evaluation = None

        start_timestamp_ns: int | None = None
        live_recording = None
        final_state = RunState.COMPLETED

        def _record_runtime_error(exc: Exception) -> None:
            nonlocal final_state, pipeline_failed, error_message
            if isinstance(exc, EOFError):
                final_state = RunState.COMPLETED
                return
            final_state = RunState.FAILED
            pipeline_failed = True
            error_message = str(exc)
            self._console.error(error_message)

        try:
            self._console.info(f"Preparing streaming run '{plan.run_id}' from source '{source.label}'.")
            ingest_started = True
            sequence_manifest = source.prepare_sequence_manifest(run_paths.sequence_manifest_path.parent)
            if isinstance(source, BenchmarkInputSource):
                benchmark_inputs = source.prepare_benchmark_inputs(run_paths.benchmark_inputs_path.parent)
                if benchmark_inputs is not None:
                    write_json(run_paths.benchmark_inputs_path, benchmark_inputs)
            write_json(run_paths.sequence_manifest_path, sequence_manifest)
            self._runtime.update_fields(
                state=RunState.PREPARING,
                plan=plan,
                sequence_manifest=sequence_manifest,
                benchmark_inputs=benchmark_inputs,
                error_message="",
            )
            stream = source.open_stream(loop=True)
            self._runtime.register_cleanup(stop_event=stop_event, cleanup=stream.disconnect)
            connected_target = stream.connect()
            del connected_target
            if request.visualization.connect_live_viewer or request.visualization.export_viewer_rrd:
                live_recording = create_recording_stream(app_id="prml-vslam", recording_id=plan.run_id)
                if request.visualization.connect_live_viewer:
                    attach_grpc_sink(live_recording, grpc_url=request.visualization.grpc_url)
                if request.visualization.export_viewer_rrd:
                    attach_file_sink(live_recording, target_path=run_paths.viewer_rrd_path)
            slam_session = slam_backend.start_session(
                request.slam.backend,
                request.slam.outputs,
                plan.artifact_root,
            )
            slam_started = True
            self._runtime.update_fields(state=RunState.RUNNING, error_message="")

            max_frames = request.slam.backend.max_frames
            frames_pushed = 0

            while not stop_event.is_set():
                if max_frames is not None and frames_pushed >= max_frames:
                    self._console.info("Reached configured SLAM max frames limit (%d); stopping stream.", max_frames)
                    break

                packet = stream.wait_for_packet(timeout_seconds=self.frame_timeout_seconds)
                frames_pushed += 1

                arrival_time_s = time.monotonic()
                if start_timestamp_ns is None:
                    start_timestamp_ns = packet.timestamp_ns

                metrics.record_packet(arrival_time_s=arrival_time_s)
                self._runtime.update_fields(
                    state=RunState.RUNNING,
                    latest_packet=packet,
                    error_message="",
                    **metrics.packet_snapshot_fields(),
                )
                slam_session.step(packet)

                for update in slam_session.try_get_updates():
                    if _has_renderable_preview(update):
                        latest_preview_update = update
                    if update.is_keyframe:
                        keyframe_position_xyz = extract_pose_position(update)
                        update_timestamp_ns = update.source_timestamp_ns or update.timestamp_ns
                        metrics.record_keyframe(
                            arrival_time_s=arrival_time_s,
                            position_xyz=keyframe_position_xyz,
                            trajectory_time_s=(update_timestamp_ns - start_timestamp_ns) / 1e9
                            if update.pose is not None and start_timestamp_ns is not None
                            else None,
                        )
                        if live_recording is not None and update.pose is not None:
                            log_transform(
                                live_recording,
                                entity_path="camera",
                                transform=update.pose,
                            )
                            if update.pointmap is not None:
                                log_pointcloud(
                                    live_recording,
                                    entity_path="camera/pointcloud",
                                    pointmap=update.pointmap,
                                    colors=update.preview_rgb,
                                )
                            if update.preview_rgb is not None:
                                log_preview_image(
                                    live_recording,
                                    entity_path="camera/preview",
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
        except Exception as exc:
            _record_runtime_error(exc)
        finally:
            try:
                if slam_session is not None:
                    slam_artifacts = slam_session.close()
            except Exception as exc:
                if final_state is RunState.FAILED or stop_event.is_set():
                    self._console.warning(str(exc))
                else:
                    final_state = RunState.FAILED
                    pipeline_failed = True
                    error_message = str(exc)
                    self._console.error(error_message)
            if stop_event.is_set() and final_state is not RunState.FAILED:
                final_state = RunState.STOPPED
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
            trajectory_evaluation = compute_trajectory_evaluation(
                request=request,
                plan=plan,
                sequence_manifest=sequence_manifest,
                benchmark_inputs=benchmark_inputs,
                slam=slam_artifacts,
            )
            try:
                summary, stage_manifests = finalize_run_outputs(
                    request=request,
                    plan=plan,
                    run_paths=run_paths,
                    sequence_manifest=sequence_manifest,
                    benchmark_inputs=benchmark_inputs,
                    slam=slam_artifacts,
                    visualization=visualization_artifacts,
                    trajectory_evaluation=trajectory_evaluation,
                    ingest_started=ingest_started,
                    slam_started=slam_started,
                    pipeline_failed=pipeline_failed,
                    error_message=error_message,
                )
            except Exception as exc:
                final_state = RunState.FAILED
                error_message = str(exc)
                self._console.error(f"Finalization failed: {exc}")
                summary = None
                stage_manifests = []
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


def _has_renderable_preview(update: SlamUpdate) -> bool:
    """Return whether one backend update exposes a non-empty preview payload."""
    if update.preview_rgb is not None and np.asarray(update.preview_rgb).size > 0:
        return True
    if update.pointmap is None:
        return False
    pointmap = np.asarray(update.pointmap)
    return pointmap.size > 0 and pointmap.ndim in {2, 3}


def _to_stopped_snapshot(snapshot: StreamingRunSnapshot) -> StreamingRunSnapshot:
    if snapshot.state not in {RunState.PREPARING, RunState.RUNNING}:
        return snapshot
    return snapshot.model_copy(update={"state": RunState.STOPPED})


__all__ = ["StreamingRunner"]
