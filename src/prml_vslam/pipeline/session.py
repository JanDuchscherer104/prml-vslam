"""Pipeline-owned streaming session service for the bounded ADVIO replay demo."""

from __future__ import annotations

import hashlib
import json
import time
from collections import deque
from enum import StrEnum
from pathlib import Path
from threading import Event, Lock, Thread
from typing import TYPE_CHECKING

import numpy as np
from pydantic import Field

from prml_vslam.interfaces import FramePacket
from prml_vslam.methods.contracts import MethodId
from prml_vslam.methods.mock_vslam import MockTrackingRuntimeConfig
from prml_vslam.pipeline.contracts import (
    PipelineMode,
    RunPlan,
    RunPlanStageId,
    RunRequest,
    RunSummary,
    SequenceManifest,
    StageExecutionStatus,
    StageManifest,
    TrackingArtifacts,
    TrackingUpdate,
)
from prml_vslam.pipeline.protocols import StreamingSequenceSource, StreamingTrackerBackend
from prml_vslam.protocols import FramePacketStream
from prml_vslam.utils import BaseConfig, BaseData, Console, PathConfig, RunArtifactPaths

if TYPE_CHECKING:
    from collections.abc import Callable


_ACTIVE_SESSION_STATES = frozenset({"connecting", "running"})
_SUPPORTED_STAGE_IDS = frozenset(
    {
        RunPlanStageId.INGEST,
        RunPlanStageId.SLAM,
        RunPlanStageId.DENSE_MAPPING,
        RunPlanStageId.SUMMARY,
    }
)


def _empty_positions_xyz() -> np.ndarray:
    return np.empty((0, 3), dtype=np.float64)


def _empty_timestamps_s() -> np.ndarray:
    return np.empty((0,), dtype=np.float64)


class _RollingRuntimeMetrics:
    """Small rolling metrics helper for live session snapshots."""

    def __init__(self, *, fps_window_size: int, trajectory_window_size: int) -> None:
        self._arrival_times: deque[float] = deque(maxlen=fps_window_size)
        self._trajectory_positions: deque[np.ndarray] = deque(maxlen=trajectory_window_size)
        self._trajectory_timestamps: deque[float] = deque(maxlen=trajectory_window_size)
        self._received_frames = 0

    def record(
        self,
        *,
        arrival_time_s: float,
        position_xyz: np.ndarray | None,
        trajectory_time_s: float | None,
    ) -> None:
        """Append one frame arrival and optional trajectory sample."""
        self._received_frames += 1
        self._arrival_times.append(arrival_time_s)
        if position_xyz is not None and trajectory_time_s is not None:
            self._trajectory_positions.append(position_xyz)
            self._trajectory_timestamps.append(trajectory_time_s)

    def snapshot_fields(self) -> dict[str, int | float | np.ndarray]:
        """Return the current metrics in snapshot-ready form."""
        return {
            "received_frames": self._received_frames,
            "measured_fps": self._measure_fps(self._arrival_times),
            "trajectory_positions_xyz": self._positions_to_array(self._trajectory_positions),
            "trajectory_timestamps_s": np.asarray(tuple(self._trajectory_timestamps), dtype=np.float64),
        }

    @staticmethod
    def _measure_fps(arrival_times: deque[float]) -> float:
        if len(arrival_times) < 2:
            return 0.0
        elapsed = arrival_times[-1] - arrival_times[0]
        return 0.0 if elapsed <= 0.0 else float((len(arrival_times) - 1) / elapsed)

    @staticmethod
    def _positions_to_array(positions: deque[np.ndarray]) -> np.ndarray:
        return np.vstack(tuple(positions)).astype(np.float64, copy=False) if positions else _empty_positions_xyz()


class PipelineSessionState(StrEnum):
    """Lifecycle states exposed by the pipeline-owned session service."""

    IDLE = "idle"
    CONNECTING = "connecting"
    RUNNING = "running"
    COMPLETED = "completed"
    STOPPED = "stopped"
    FAILED = "failed"


class PipelineSessionSnapshot(BaseData):
    """Current session state rendered by the Streamlit Pipeline page."""

    state: PipelineSessionState = PipelineSessionState.IDLE
    """Current lifecycle state."""

    plan: RunPlan | None = None
    """Resolved run plan for the current or most recent session."""

    sequence_manifest: SequenceManifest | None = None
    """Normalized sequence manifest prepared by the ingest stage."""

    latest_packet: FramePacket | None = None
    """Most recent frame packet seen by the tracker."""

    latest_update: TrackingUpdate | None = None
    """Most recent incremental tracking update."""

    tracking: TrackingArtifacts | None = None
    """Persisted tracking artifacts returned by the backend."""

    summary: RunSummary | None = None
    """Final persisted run summary."""

    stage_manifests: list[StageManifest] = Field(default_factory=list)
    """Executed stage manifests owned by this slice."""

    received_frames: int = 0
    """Number of processed frames for the current session."""

    measured_fps: float = 0.0
    """Rolling measured frame rate."""

    trajectory_positions_xyz: np.ndarray = Field(default_factory=_empty_positions_xyz)
    """Current sparse trajectory positions in world coordinates."""

    trajectory_timestamps_s: np.ndarray = Field(default_factory=_empty_timestamps_s)
    """Current trajectory timestamps in seconds."""

    num_map_points: int = 0
    """Latest sparse-map size reported by the backend."""

    num_dense_points: int = 0
    """Latest dense-point count reported by the backend."""

    error_message: str = ""
    """Last surfaced error message."""


class PipelineSessionService:
    """Own the bounded streaming session flow for the current pipeline slice."""

    def __init__(
        self,
        *,
        path_config: PathConfig | None = None,
        frame_timeout_seconds: float = 0.5,
        fps_window_size: int = 30,
        trajectory_window_size: int = 1024,
        tracker_factory: Callable[[MethodId], StreamingTrackerBackend] | None = None,
    ) -> None:
        self.path_config = PathConfig() if path_config is None else path_config
        self.frame_timeout_seconds = frame_timeout_seconds
        self.fps_window_size = fps_window_size
        self.trajectory_window_size = trajectory_window_size
        self._tracker_factory = _default_tracker_factory if tracker_factory is None else tracker_factory
        self._console = Console(__name__).child(self.__class__.__name__)
        self._lock = Lock()
        self._snapshot = PipelineSessionSnapshot()
        self._active_stream: FramePacketStream | None = None
        self._active_stop_event: Event | None = None
        self._worker_thread: Thread | None = None

    def start(self, *, request: RunRequest, source: StreamingSequenceSource) -> None:
        """Start a new pipeline session for one run request and replay source."""
        self.stop()
        plan = request.build(self.path_config)
        unsupported_stage_ids = [stage.id for stage in plan.stages if stage.id not in _SUPPORTED_STAGE_IDS]
        if unsupported_stage_ids:
            error_message = "Unsupported stages for the current streaming slice: " + ", ".join(
                stage_id.value for stage_id in unsupported_stage_ids
            )
            self._console.error(error_message)
            with self._lock:
                self._snapshot = PipelineSessionSnapshot(
                    state=PipelineSessionState.FAILED,
                    plan=plan,
                    error_message=error_message,
                )
            raise RuntimeError(error_message)

        stop_event = Event()
        worker = Thread(
            target=self._run_worker,
            kwargs={
                "request": request,
                "plan": plan,
                "source": source,
                "stop_event": stop_event,
            },
            name=f"Pipeline-session-{plan.run_id}",
            daemon=True,
        )
        with self._lock:
            self._active_stop_event = stop_event
            self._worker_thread = worker
            self._snapshot = PipelineSessionSnapshot(
                state=PipelineSessionState.CONNECTING,
                plan=plan,
            )
        worker.start()

    def stop(self) -> None:
        """Stop the active session and preserve the last rendered snapshot."""
        with self._lock:
            worker = self._worker_thread
            stop_event = self._active_stop_event
            stream = self._active_stream
        if stop_event is not None:
            stop_event.set()
        if stream is not None:
            stream.disconnect()
        if worker is not None:
            worker.join(timeout=2.0)
            if worker.is_alive():
                raise RuntimeError("Timed out stopping the pipeline session worker thread.")
        with self._lock:
            if self._snapshot.state.value in _ACTIVE_SESSION_STATES:
                self._snapshot = self._snapshot.model_copy(update={"state": PipelineSessionState.STOPPED})
            self._active_stream = None
            self._active_stop_event = None
            self._worker_thread = None

    def snapshot(self) -> PipelineSessionSnapshot:
        """Return a deep copy of the latest session snapshot."""
        with self._lock:
            return self._snapshot.model_copy(deep=True)

    def _run_worker(
        self,
        *,
        request: RunRequest,
        plan: RunPlan,
        source: StreamingSequenceSource,
        stop_event: Event,
    ) -> None:
        run_paths = RunArtifactPaths.build(plan.artifact_root)
        metrics = _RollingRuntimeMetrics(
            fps_window_size=self.fps_window_size,
            trajectory_window_size=self.trajectory_window_size,
        )
        tracker: StreamingTrackerBackend | None = None
        stream: FramePacketStream | None = None
        sequence_manifest: SequenceManifest | None = None
        tracking_artifacts: TrackingArtifacts | None = None
        summary: RunSummary | None = None
        stage_manifests: list[StageManifest] = []
        ingest_started = False
        slam_started = False
        tracker_opened = False
        final_state = PipelineSessionState.COMPLETED
        pipeline_failed = False
        error_message = ""
        start_monotonic = time.monotonic()

        try:
            self._console.info(f"Preparing streaming run '{plan.run_id}' from source '{source.label}'.")
            ingest_started = True
            sequence_manifest = source.prepare_sequence_manifest(run_paths.sequence_manifest_path.parent)
            _write_json(run_paths.sequence_manifest_path, sequence_manifest)
            self._set_snapshot(
                state=PipelineSessionState.CONNECTING,
                plan=plan,
                sequence_manifest=sequence_manifest,
                error_message="",
            )

            tracker = self._tracker_factory(request.tracking.method)
            stream = source.open_stream(loop=request.mode is PipelineMode.STREAMING)
            with self._lock:
                if self._active_stop_event is stop_event:
                    self._active_stream = stream

            stream.connect()
            slam_started = True
            tracker.open(request.tracking, plan.artifact_root)
            tracker_opened = True
            self._set_snapshot(
                state=PipelineSessionState.RUNNING,
                plan=plan,
                sequence_manifest=sequence_manifest,
                error_message="",
            )

            while not stop_event.is_set():
                packet = stream.wait_for_packet(timeout_seconds=self.frame_timeout_seconds)
                update = tracker.step(packet)
                arrival_time_s = time.monotonic()
                metrics.record(
                    arrival_time_s=arrival_time_s,
                    position_xyz=_extract_position(update),
                    trajectory_time_s=arrival_time_s - start_monotonic if update.pose is not None else None,
                )
                self._set_snapshot(
                    state=PipelineSessionState.RUNNING,
                    latest_packet=packet,
                    latest_update=update,
                    num_map_points=update.num_map_points,
                    num_dense_points=update.num_dense_points,
                    error_message="",
                    **metrics.snapshot_fields(),
                )
        except EOFError:
            final_state = PipelineSessionState.COMPLETED
        except Exception as exc:
            final_state = PipelineSessionState.FAILED
            pipeline_failed = True
            error_message = str(exc)
            self._console.error(error_message)
        finally:
            if tracker is not None and tracker_opened:
                try:
                    tracking_artifacts = tracker.close()
                except Exception as exc:
                    final_state = PipelineSessionState.FAILED
                    pipeline_failed = True
                    error_message = str(exc)
                    self._console.error(error_message)
            if stop_event.is_set() and final_state is not PipelineSessionState.FAILED:
                final_state = PipelineSessionState.STOPPED
            try:
                summary, stage_manifests = self._finalize_outputs(
                    request=request,
                    plan=plan,
                    run_paths=run_paths,
                    sequence_manifest=sequence_manifest,
                    tracking=tracking_artifacts,
                    ingest_started=ingest_started,
                    slam_started=slam_started,
                    pipeline_failed=pipeline_failed,
                    error_message=error_message,
                )
            except Exception as exc:
                final_state = PipelineSessionState.FAILED
                error_message = str(exc)
                self._console.error(error_message)
                summary = None
                stage_manifests = []
            if stream is not None:
                stream.disconnect()
            with self._lock:
                if self._active_stop_event is stop_event:
                    self._active_stream = None
                    self._active_stop_event = None
                    self._worker_thread = None
                self._snapshot = self._snapshot.model_copy(
                    update={
                        "state": final_state,
                        "plan": plan,
                        "sequence_manifest": sequence_manifest,
                        "tracking": tracking_artifacts,
                        "summary": summary,
                        "stage_manifests": stage_manifests,
                        "error_message": error_message,
                    }
                )

    def _finalize_outputs(
        self,
        *,
        request: RunRequest,
        plan: RunPlan,
        run_paths: RunArtifactPaths,
        sequence_manifest: SequenceManifest | None,
        tracking: TrackingArtifacts | None,
        ingest_started: bool,
        slam_started: bool,
        pipeline_failed: bool,
        error_message: str,
    ) -> tuple[RunSummary, list[StageManifest]]:
        """Persist the run summary plus truthful stage manifests for executed work."""
        stage_status = self._build_stage_status(
            plan=plan,
            sequence_manifest=sequence_manifest,
            tracking=tracking,
            ingest_started=ingest_started,
            slam_started=slam_started,
            pipeline_failed=pipeline_failed,
        )
        non_summary_manifests = self._build_stage_manifests(
            request=request,
            plan=plan,
            run_paths=run_paths,
            sequence_manifest=sequence_manifest,
            tracking=tracking,
            stage_status=stage_status,
        )
        summary_manifest = self._build_summary_manifest(
            request=request,
            run_paths=run_paths,
            sequence_manifest=sequence_manifest,
            tracking=tracking,
            stage_status=stage_status,
            existing_stage_manifests=non_summary_manifests,
            error_message=error_message,
        )
        stage_manifests = [*non_summary_manifests, summary_manifest]
        summary = RunSummary(
            run_id=plan.run_id,
            artifact_root=plan.artifact_root,
            stage_status={**stage_status, RunPlanStageId.SUMMARY: StageExecutionStatus.RAN},
        )
        _write_json(run_paths.summary_path, summary)
        _write_json(run_paths.stage_manifests_path, stage_manifests)
        if pipeline_failed:
            self._console.warning(f"Persisted failed run summary for '{plan.run_id}'.")
        return summary, stage_manifests

    @staticmethod
    def _build_stage_status(
        *,
        plan: RunPlan,
        sequence_manifest: SequenceManifest | None,
        tracking: TrackingArtifacts | None,
        ingest_started: bool,
        slam_started: bool,
        pipeline_failed: bool,
    ) -> dict[RunPlanStageId, StageExecutionStatus]:
        """Compute truthful statuses for the stages owned by this slice."""
        planned_ids = {stage.id for stage in plan.stages}
        stage_status: dict[RunPlanStageId, StageExecutionStatus] = {}
        if RunPlanStageId.INGEST in planned_ids and ingest_started:
            stage_status[RunPlanStageId.INGEST] = (
                StageExecutionStatus.RAN if sequence_manifest is not None else StageExecutionStatus.FAILED
            )
        if RunPlanStageId.SLAM in planned_ids and slam_started:
            stage_status[RunPlanStageId.SLAM] = (
                StageExecutionStatus.RAN
                if tracking is not None and not pipeline_failed
                else StageExecutionStatus.FAILED
            )
        if RunPlanStageId.DENSE_MAPPING in planned_ids and slam_started:
            stage_status[RunPlanStageId.DENSE_MAPPING] = (
                StageExecutionStatus.RAN
                if tracking is not None and tracking.dense is not None and not pipeline_failed
                else StageExecutionStatus.FAILED
            )
        return stage_status

    def _build_stage_manifests(
        self,
        *,
        request: RunRequest,
        plan: RunPlan,
        run_paths: RunArtifactPaths,
        sequence_manifest: SequenceManifest | None,
        tracking: TrackingArtifacts | None,
        stage_status: dict[RunPlanStageId, StageExecutionStatus],
    ) -> list[StageManifest]:
        """Build non-summary stage manifests for the executed pipeline slice."""
        manifests: list[StageManifest] = []
        if RunPlanStageId.INGEST in stage_status:
            output_paths = (
                {"sequence_manifest": run_paths.sequence_manifest_path} if sequence_manifest is not None else {}
            )
            if sequence_manifest is not None and sequence_manifest.reference_tum_path is not None:
                output_paths["reference_tum"] = sequence_manifest.reference_tum_path
            manifests.append(
                StageManifest(
                    stage_id=RunPlanStageId.INGEST,
                    config_hash=_stable_hash(request.source),
                    input_fingerprint=_stable_hash(request.source),
                    output_paths=output_paths,
                    status=stage_status[RunPlanStageId.INGEST],
                )
            )
        if RunPlanStageId.SLAM in stage_status:
            output_paths: dict[str, Path] = {}
            if tracking is not None:
                output_paths["trajectory_tum"] = tracking.trajectory_tum.path
                if tracking.sparse_points_ply is not None:
                    output_paths["sparse_points_ply"] = tracking.sparse_points_ply.path
                if tracking.preview_log_jsonl is not None:
                    output_paths["preview_log_jsonl"] = tracking.preview_log_jsonl.path
            manifests.append(
                StageManifest(
                    stage_id=RunPlanStageId.SLAM,
                    config_hash=_stable_hash(request.tracking),
                    input_fingerprint=_stable_hash(sequence_manifest or {"missing": "sequence_manifest"}),
                    output_paths=output_paths,
                    status=stage_status[RunPlanStageId.SLAM],
                )
            )
        if RunPlanStageId.DENSE_MAPPING in stage_status:
            output_paths = (
                {"dense_points_ply": tracking.dense.dense_points_ply.path}
                if tracking is not None and tracking.dense is not None
                else {}
            )
            manifests.append(
                StageManifest(
                    stage_id=RunPlanStageId.DENSE_MAPPING,
                    config_hash=_stable_hash(request.dense),
                    input_fingerprint=_stable_hash(tracking or {"missing": "tracking"}),
                    output_paths=output_paths,
                    status=stage_status[RunPlanStageId.DENSE_MAPPING],
                )
            )
        planned_ids = {stage.id for stage in plan.stages}
        return [manifest for manifest in manifests if manifest.stage_id in planned_ids]

    def _build_summary_manifest(
        self,
        *,
        request: RunRequest,
        run_paths: RunArtifactPaths,
        sequence_manifest: SequenceManifest | None,
        tracking: TrackingArtifacts | None,
        stage_status: dict[RunPlanStageId, StageExecutionStatus],
        existing_stage_manifests: list[StageManifest],
        error_message: str,
    ) -> StageManifest:
        """Build the summary-stage manifest before persisting summary outputs."""
        return StageManifest(
            stage_id=RunPlanStageId.SUMMARY,
            config_hash=_stable_hash({"experiment_name": request.experiment_name, "mode": request.mode}),
            input_fingerprint=_stable_hash(
                {
                    "sequence_manifest": sequence_manifest,
                    "tracking": tracking,
                    "stage_status": stage_status,
                    "stage_manifests": existing_stage_manifests,
                    "error_message": error_message,
                }
            ),
            output_paths={
                "run_summary": run_paths.summary_path,
                "stage_manifests": run_paths.stage_manifests_path,
            },
            status=StageExecutionStatus.RAN,
        )

    def _set_snapshot(self, **fields: object) -> None:
        """Update the session snapshot under the internal lock."""
        with self._lock:
            self._snapshot = self._snapshot.model_copy(update=fields)


def _default_tracker_factory(method_id: MethodId) -> StreamingTrackerBackend:
    """Build the streaming-capable mock backend for one method id."""
    tracker = MockTrackingRuntimeConfig(method_id=method_id).setup_target()
    if tracker is None:
        raise RuntimeError(f"Failed to initialize the mock tracker for method '{method_id.value}'.")
    return tracker


def _extract_position(update: TrackingUpdate) -> np.ndarray | None:
    """Extract a finite world-space translation from one tracking update."""
    if update.pose is None:
        return None
    position = np.array([update.pose.tx, update.pose.ty, update.pose.tz], dtype=np.float64)
    return position if np.all(np.isfinite(position)) else None


def _stable_hash(payload: object) -> str:
    """Compute a stable SHA-256 hash for repo-owned JSON-friendly payloads."""
    normalized_payload = BaseConfig.to_jsonable(payload)
    encoded = json.dumps(normalized_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _write_json(path: Path, payload: object) -> None:
    """Persist one JSON artifact with stable formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(BaseConfig.to_jsonable(payload), indent=2, sort_keys=True), encoding="utf-8")


__all__ = ["PipelineSessionService", "PipelineSessionSnapshot", "PipelineSessionState"]
