"""Streaming pipeline runner."""

from __future__ import annotations

from threading import Event

from prml_vslam.interfaces import FrameTransform
from prml_vslam.methods.contracts import MethodId
from prml_vslam.methods.protocols import StreamingSlamBackend
from prml_vslam.methods.updates import SlamUpdate
from prml_vslam.pipeline.contracts.plan import RunPlan
from prml_vslam.pipeline.contracts.request import RunRequest
from prml_vslam.pipeline.state import RunState, StreamingRunSnapshot
from prml_vslam.protocols.source import StreamingSequenceSource
from prml_vslam.utils import Console, load_point_cloud_ply
from prml_vslam.visualization.rerun import (
    attach_recording_sinks as _attach_recording_sinks,
)
from prml_vslam.visualization.rerun import (
    collect_native_visualization_artifacts as _collect_native_visualization_artifacts,
)
from prml_vslam.visualization.rerun import (
    create_recording_stream as _create_recording_stream,
)
from prml_vslam.visualization.rerun import log_pinhole as _log_pinhole
from prml_vslam.visualization.rerun import log_pointcloud as _log_pointcloud
from prml_vslam.visualization.rerun import log_points3d as _log_points3d
from prml_vslam.visualization.rerun import log_transform as _log_transform

from .runner_runtime import RunnerRuntime
from .streaming_coordinator import StreamingCoordinator

_STOP_JOIN_TIMEOUT_SECONDS = 10.0


def _viewer_pose_from_update(update: SlamUpdate, *, method_id: MethodId) -> FrameTransform:
    """Return one repo pose unchanged for viewer logging."""
    if update.pose is None:
        raise ValueError("Viewer pose conversion requires an update with a pose.")
    del method_id
    return update.pose


class _StreamingViewerHooks:
    """Patchable viewer-hook namespace passed into the coordinator."""

    create_recording_stream = staticmethod(_create_recording_stream)
    attach_recording_sinks = staticmethod(_attach_recording_sinks)
    collect_native_visualization_artifacts = staticmethod(_collect_native_visualization_artifacts)
    log_pinhole = staticmethod(_log_pinhole)
    log_transform = staticmethod(_log_transform)
    log_pointcloud = staticmethod(_log_pointcloud)
    log_points3d = staticmethod(_log_points3d)
    load_point_cloud_ply = staticmethod(load_point_cloud_ply)
    viewer_pose_from_update = staticmethod(_viewer_pose_from_update)


VIEWER_HOOKS = _StreamingViewerHooks()


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
        StreamingCoordinator(
            runtime=self._runtime,
            console=self._console,
            frame_timeout_seconds=self.frame_timeout_seconds,
            fps_window_size=self.fps_window_size,
            trajectory_window_size=self.trajectory_window_size,
            viewer_hooks=VIEWER_HOOKS,
        ).run(
            stop_event=stop_event,
            request=request,
            plan=plan,
            source=source,
            slam_backend=slam_backend,
        )


def _to_stopped_snapshot(snapshot: StreamingRunSnapshot) -> StreamingRunSnapshot:
    if snapshot.state not in {RunState.PREPARING, RunState.RUNNING}:
        return snapshot
    return snapshot.model_copy(update={"state": RunState.STOPPED})


__all__ = ["StreamingRunner", "_viewer_pose_from_update"]
