"""Streaming pipeline runner."""

from __future__ import annotations

import time
from threading import Event

from prml_vslam.interfaces import FrameTransform
from prml_vslam.methods.protocols import SlamSession, StreamingSlamBackend
from prml_vslam.pipeline.contracts.plan import RunPlan
from prml_vslam.pipeline.contracts.request import RunRequest
from prml_vslam.pipeline.contracts.runtime import RunState, StreamingRunSnapshot
from prml_vslam.protocols.source import StreamingSequenceSource
from prml_vslam.utils import Console, RunArtifactPaths
from prml_vslam.utils.packet_session import PacketSessionMetrics, extract_pose_position
from prml_vslam.visualization.rerun import (
    attach_file_sink,
    attach_grpc_sink,
    create_recording_stream,
    export_viewer_recording,
    log_transform,
)

from .finalization import finalize_run_outputs, write_json
from .runner_runtime import RunnerRuntime

_STOP_JOIN_TIMEOUT_SECONDS = 10.0


class StreamingRunner:
    """Own the bounded streaming session flow for the current pipeline slice."""

    def __init__(
        self,
        *,
        frame_timeout_seconds: float = 0.5,
        fps_window_size: int = 30,
        trajectory_window_size: int = 1024,
    ) -> None:
        self.frame_timeout_seconds = frame_timeout_seconds
        self.fps_window_size = fps_window_size
        self.trajectory_window_size = trajectory_window_size
        self._console = Console(__name__).child(self.__class__.__name__)
        self._runtime = RunnerRuntime(
            empty_snapshot=StreamingRunSnapshot,
            stop_timeout_message="Timed out stopping the streaming pipeline worker thread.",
        )

    def start(
        self,
        *,
        request: RunRequest,
        plan: RunPlan,
        source: StreamingSequenceSource,
        slam_backend: StreamingSlamBackend,
    ) -> None:
        """Start a new pipeline session for one already-planned run."""
        self.stop()
        self._runtime.launch(
            starting_snapshot=StreamingRunSnapshot(state=RunState.PREPARING, plan=plan),
            thread_name=f"Pipeline-streaming-{plan.run_id}",
            worker_target=lambda stop_event: self._run_worker(
                request=request,
                plan=plan,
                source=source,
                slam_backend=slam_backend,
                stop_event=stop_event,
            ),
        )

    def stop(self) -> None:
        """Stop the active session and preserve the last rendered snapshot."""
        self._runtime.stop(snapshot_update=_to_stopped_snapshot, join_timeout_seconds=_STOP_JOIN_TIMEOUT_SECONDS)

    def snapshot(self) -> StreamingRunSnapshot:
        """Return a deep copy of the latest session snapshot."""
        return self._runtime.snapshot()

    def set_failed_start(self, *, plan: RunPlan, error_message: str) -> None:
        """Persist a pre-launch failure without starting a worker."""
        self.stop()
        self._runtime.replace_snapshot(
            StreamingRunSnapshot(state=RunState.FAILED, plan=plan, error_message=error_message)
        )

    def _run_worker(
        self,
        *,
        request: RunRequest,
        plan: RunPlan,
        source: StreamingSequenceSource,
        slam_backend: StreamingSlamBackend,
        stop_event: Event,
    ) -> None:
        run_paths = RunArtifactPaths.build(plan.artifact_root)
        metrics = PacketSessionMetrics(
            fps_window_size=self.fps_window_size,
            trajectory_window_size=self.trajectory_window_size,
        )
        slam_session: SlamSession | None = None
        sequence_manifest = None
        slam_artifacts = None
        summary = None
        stage_manifests = []
        ingest_started = False
        slam_started = False
        final_state = RunState.COMPLETED
        pipeline_failed = False
        error_message = ""
        start_monotonic = time.monotonic()
        live_recording = None

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
            write_json(run_paths.sequence_manifest_path, sequence_manifest)
            self._runtime.update_fields(
                state=RunState.PREPARING,
                plan=plan,
                sequence_manifest=sequence_manifest,
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
            slam_started = True
            slam_session = slam_backend.start_session(
                request.slam.backend,
                request.slam.outputs,
                plan.artifact_root,
            )
            self._runtime.update_fields(state=RunState.RUNNING, error_message="")
            while not stop_event.is_set():
                packet = stream.wait_for_packet(timeout_seconds=self.frame_timeout_seconds)
                update = slam_session.step(packet)
                arrival_time_s = time.monotonic()
                metrics.record(
                    arrival_time_s=arrival_time_s,
                    position_xyz=extract_pose_position(update),
                    trajectory_time_s=arrival_time_s - start_monotonic if update.pose is not None else None,
                )
                self._runtime.update_fields(
                    state=RunState.RUNNING,
                    latest_packet=packet,
                    latest_slam_update=update,
                    num_sparse_points=update.num_sparse_points,
                    num_dense_points=update.num_dense_points,
                    error_message="",
                    **metrics.snapshot_fields(),
                )
                if live_recording is not None and update.pose is not None:
                    log_transform(
                        live_recording,
                        entity_path=f"/run/{plan.run_id}/camera/current",
                        transform=FrameTransform.from_matrix(
                            update.pose.as_matrix(),
                            target_frame="world",
                            source_frame="camera",
                            timestamp_ns=update.timestamp_ns,
                        ),
                    )
        except EOFError:
            final_state = RunState.COMPLETED
        except Exception as exc:
            _record_runtime_error(exc)
        finally:
            if slam_session is not None:
                try:
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
            if request.visualization.export_viewer_rrd and sequence_manifest is not None and slam_artifacts is not None:
                slam_artifacts = slam_artifacts.model_copy(
                    update={
                        "viewer_rrd": export_viewer_recording(
                            sequence_manifest=sequence_manifest,
                            slam_artifacts=slam_artifacts,
                            output_path=run_paths.viewer_rrd_path,
                            run_id=plan.run_id,
                        )
                    }
                )
            try:
                summary, stage_manifests = finalize_run_outputs(
                    request=request,
                    plan=plan,
                    run_paths=run_paths,
                    sequence_manifest=sequence_manifest,
                    slam=slam_artifacts,
                    ingest_started=ingest_started,
                    slam_started=slam_started,
                    pipeline_failed=pipeline_failed,
                    error_message=error_message,
                )
            except Exception as exc:
                final_state = RunState.FAILED
                error_message = str(exc)
                self._console.error(error_message)
                summary = None
                stage_manifests = []
            self._runtime.finalize(
                stop_event=stop_event,
                snapshot_update=lambda snapshot: snapshot.model_copy(
                    update={
                        "state": final_state,
                        "plan": plan,
                        "sequence_manifest": sequence_manifest,
                        "slam": slam_artifacts,
                        "summary": summary,
                        "stage_manifests": stage_manifests,
                        "error_message": error_message,
                    }
                ),
            )


def _to_stopped_snapshot(snapshot: StreamingRunSnapshot) -> StreamingRunSnapshot:
    if snapshot.state not in {RunState.PREPARING, RunState.RUNNING}:
        return snapshot
    return snapshot.model_copy(update={"state": RunState.STOPPED})


__all__ = ["StreamingRunner"]
