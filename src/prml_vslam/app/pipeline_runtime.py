"""Runtime controller for the minimal ADVIO pipeline demo."""

from __future__ import annotations

import json
import time
from enum import StrEnum
from threading import Event, Lock, Thread

import numpy as np
from pydantic import Field

from prml_vslam.datasets.advio import AdvioPoseSource
from prml_vslam.interfaces import FramePacket, FramePacketStream
from prml_vslam.methods import MethodId
from prml_vslam.methods.mock_tracking import MockTrackingRuntime
from prml_vslam.pipeline.contracts import (
    PipelineMode,
    RunPlan,
    RunPlanStageId,
    RunSummary,
    SequenceManifest,
    StageExecutionStatus,
    StageManifest,
    TrackingArtifacts,
    TrackingConfig,
)
from prml_vslam.pipeline.interfaces import TrackingUpdate
from prml_vslam.utils import BaseData

from .services import RollingRuntimeMetrics, empty_positions_xyz, empty_timestamps_s


class PipelineDemoState(StrEnum):
    """Lifecycle states for the minimal pipeline demo runner."""

    IDLE = "idle"
    CONNECTING = "connecting"
    RUNNING = "running"
    COMPLETED = "completed"
    STOPPED = "stopped"
    FAILED = "failed"


class PipelineDemoSnapshot(BaseData):
    """Current runtime snapshot exposed to the Pipeline page."""

    state: PipelineDemoState = PipelineDemoState.IDLE
    """Current lifecycle state."""

    mode: PipelineMode | None = None
    """Selected run mode."""

    sequence_id: int | None = None
    """Selected ADVIO sequence id."""

    sequence_label: str = ""
    """Selected ADVIO scene label."""

    method: MethodId | None = None
    """Mock method used for the run."""

    pose_source: AdvioPoseSource | None = None
    """Pose source injected into the ADVIO replay packets."""

    plan: RunPlan | None = None
    """Planned run shown to the user."""

    sequence_manifest: SequenceManifest | None = None
    """Prepared sequence manifest written before the mock tracker starts."""

    tracking: TrackingArtifacts | None = None
    """Persisted tracking artifacts returned by the mock runtime."""

    summary: RunSummary | None = None
    """Final run summary written at the end of the session."""

    stage_manifests: list[StageManifest] = Field(default_factory=list)
    """Small execution records for the demo stages."""

    latest_packet: FramePacket | None = None
    """Most recent frame packet seen by the worker."""

    latest_update: TrackingUpdate | None = None
    """Most recent tracking update returned by the mock runtime."""

    received_frames: int = 0
    """Number of frames processed by the current run."""

    measured_fps: float = 0.0
    """Rolling frame rate measured at the worker."""

    trajectory_positions_xyz: np.ndarray = Field(default_factory=empty_positions_xyz)
    """Current tracked trajectory positions."""

    trajectory_timestamps_s: np.ndarray = Field(default_factory=empty_timestamps_s)
    """Current tracked trajectory timestamps."""

    num_map_points: int = 0
    """Latest sparse-map size reported by the mock runtime."""

    num_dense_points: int = 0
    """Latest cumulative dense-point count reported by the mock runtime."""

    error_message: str = ""
    """Last surfaced error message."""


class PipelineDemoRuntimeController:
    """Run a minimal tracked ADVIO demo in a background worker."""

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
        self._lock = Lock()
        self._snapshot = PipelineDemoSnapshot()
        self._active_stream: FramePacketStream | None = None
        self._active_stop_event: Event | None = None
        self._worker_thread: Thread | None = None

    def snapshot(self) -> PipelineDemoSnapshot:
        """Return a deep copy of the latest pipeline demo snapshot."""
        with self._lock:
            return self._snapshot.model_copy(deep=True)

    def start(
        self,
        *,
        sequence_id: int,
        sequence_label: str,
        pose_source: AdvioPoseSource,
        plan: RunPlan,
        tracking_config: TrackingConfig,
        sequence_manifest: SequenceManifest,
        stream: FramePacketStream,
        tracker: MockTrackingRuntime,
    ) -> None:
        """Start a new tracked ADVIO demo run."""
        self.stop()
        stop_event = Event()
        worker = Thread(
            target=self._run_worker,
            kwargs={
                "sequence_id": sequence_id,
                "sequence_label": sequence_label,
                "pose_source": pose_source,
                "plan": plan,
                "tracking_config": tracking_config,
                "sequence_manifest": sequence_manifest,
                "stream": stream,
                "tracker": tracker,
                "stop_event": stop_event,
            },
            name=f"Pipeline-demo-{sequence_id:02d}",
            daemon=True,
        )
        with self._lock:
            self._active_stop_event = stop_event
            self._worker_thread = worker
            self._snapshot = PipelineDemoSnapshot(
                state=PipelineDemoState.CONNECTING,
                mode=plan.mode,
                sequence_id=sequence_id,
                sequence_label=sequence_label,
                method=plan.method,
                pose_source=pose_source,
                plan=plan,
                sequence_manifest=sequence_manifest,
            )
        worker.start()

    def stop(self) -> None:
        """Stop the current run and preserve the last snapshot."""
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
                raise RuntimeError("Timed out stopping the pipeline demo worker thread.")
        with self._lock:
            if self._snapshot.state in {PipelineDemoState.CONNECTING, PipelineDemoState.RUNNING}:
                self._snapshot = self._snapshot.model_copy(update={"state": PipelineDemoState.STOPPED})
            self._active_stream = None
            self._active_stop_event = None
            self._worker_thread = None

    def _run_worker(
        self,
        *,
        sequence_id: int,
        sequence_label: str,
        pose_source: AdvioPoseSource,
        plan: RunPlan,
        tracking_config: TrackingConfig,
        sequence_manifest: SequenceManifest,
        stream: FramePacketStream,
        tracker: MockTrackingRuntime,
        stop_event: Event,
    ) -> None:
        metrics = RollingRuntimeMetrics(
            fps_window_size=self.fps_window_size,
            trajectory_window_size=self.trajectory_window_size,
        )
        tracker_opened = False
        tracking_artifacts: TrackingArtifacts | None = None
        final_state = PipelineDemoState.COMPLETED
        error_message = ""
        start_monotonic = time.monotonic()

        try:
            with self._lock:
                if self._active_stop_event is stop_event:
                    self._active_stream = stream
            stream.connect()
            tracker.open(tracking_config, plan.artifact_root)
            tracker_opened = True
            self._update_snapshot(
                state=PipelineDemoState.RUNNING,
                mode=plan.mode,
                sequence_id=sequence_id,
                sequence_label=sequence_label,
                method=plan.method,
                pose_source=pose_source,
                plan=plan,
                sequence_manifest=sequence_manifest,
                error_message="",
            )
            while not stop_event.is_set():
                packet = stream.wait_for_packet(timeout_seconds=self.frame_timeout_seconds)
                update = tracker.step(packet)
                position_xyz = _extract_position(update)
                now = time.monotonic()
                metrics.record(
                    arrival_time_s=now,
                    position_xyz=position_xyz,
                    trajectory_time_s=now - start_monotonic if position_xyz is not None else None,
                )
                self._update_snapshot(
                    state=PipelineDemoState.RUNNING,
                    latest_packet=packet,
                    latest_update=update,
                    num_map_points=update.num_map_points,
                    num_dense_points=update.num_dense_points,
                    error_message="",
                    **metrics.snapshot_fields(),
                )
        except EOFError:
            final_state = PipelineDemoState.COMPLETED
        except Exception as exc:
            final_state = PipelineDemoState.FAILED
            error_message = str(exc)
        finally:
            if tracker_opened:
                try:
                    tracking_artifacts = tracker.close()
                except Exception as exc:
                    if final_state is not PipelineDemoState.FAILED:
                        final_state = PipelineDemoState.FAILED
                    error_message = str(exc)
            final_state = PipelineDemoState.STOPPED if stop_event.is_set() else final_state
            summary, stage_manifests = self._finalize_outputs(
                plan=plan,
                sequence_manifest=sequence_manifest,
                tracking=tracking_artifacts,
                final_state=final_state,
            )
            stream.disconnect()
            with self._lock:
                if self._active_stop_event is stop_event:
                    self._active_stream = None
                    self._active_stop_event = None
                    self._worker_thread = None
                self._snapshot = self._snapshot.model_copy(
                    update={
                        "state": final_state,
                        "mode": plan.mode,
                        "sequence_id": sequence_id,
                        "sequence_label": sequence_label,
                        "method": plan.method,
                        "pose_source": pose_source,
                        "plan": plan,
                        "sequence_manifest": sequence_manifest,
                        "tracking": tracking_artifacts,
                        "summary": summary,
                        "stage_manifests": stage_manifests,
                        "error_message": error_message,
                    }
                )

    def _update_snapshot(self, **fields: object) -> None:
        with self._lock:
            self._snapshot = self._snapshot.model_copy(update=fields)

    def _finalize_outputs(
        self,
        *,
        plan: RunPlan,
        sequence_manifest: SequenceManifest,
        tracking: TrackingArtifacts | None,
        final_state: PipelineDemoState,
    ) -> tuple[RunSummary, list[StageManifest]]:
        stage_status = self._build_stage_status(plan, final_state, tracking)
        summary = RunSummary(run_id=plan.run_id, artifact_root=plan.artifact_root, stage_status=stage_status)
        summary_path = next(stage.outputs[0] for stage in plan.stages if stage.id is RunPlanStageId.SUMMARY)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(_json_dump(summary.model_dump(mode="json")), encoding="utf-8")

        stage_manifests: list[StageManifest] = []
        for stage in plan.stages:
            output_paths = {path.stem: path for path in stage.outputs}
            if stage.id is RunPlanStageId.INGEST and sequence_manifest.reference_tum_path is not None:
                output_paths["ground_truth"] = sequence_manifest.reference_tum_path
            if stage.id is RunPlanStageId.SLAM and tracking is not None and tracking.preview_log_jsonl is not None:
                output_paths["preview_log"] = tracking.preview_log_jsonl.path
            if stage.id is RunPlanStageId.DENSE_MAPPING and tracking is not None and tracking.dense is not None:
                output_paths["dense_points"] = tracking.dense.dense_points_ply.path
            stage_manifests.append(
                StageManifest(
                    stage_id=stage.id,
                    config_hash=f"cfg-{plan.method.value}-{stage.id.value}",
                    input_fingerprint=f"sequence-{sequence_manifest.sequence_id}",
                    output_paths=output_paths,
                    status=stage_status[stage.id],
                )
            )
        return summary, stage_manifests

    @staticmethod
    def _build_stage_status(
        plan: RunPlan,
        final_state: PipelineDemoState,
        tracking: TrackingArtifacts | None,
    ) -> dict[RunPlanStageId, StageExecutionStatus]:
        stage_status: dict[RunPlanStageId, StageExecutionStatus] = {}
        for stage in plan.stages:
            match stage.id:
                case RunPlanStageId.INGEST:
                    stage_status[stage.id] = StageExecutionStatus.RAN
                case RunPlanStageId.SLAM:
                    stage_status[stage.id] = (
                        StageExecutionStatus.FAILED
                        if final_state is PipelineDemoState.FAILED
                        else StageExecutionStatus.RAN
                    )
                case RunPlanStageId.DENSE_MAPPING:
                    stage_status[stage.id] = (
                        StageExecutionStatus.FAILED
                        if final_state is PipelineDemoState.FAILED or tracking is None or tracking.dense is None
                        else StageExecutionStatus.RAN
                    )
                case RunPlanStageId.SUMMARY:
                    stage_status[stage.id] = StageExecutionStatus.RAN
                case _:
                    stage_status[stage.id] = StageExecutionStatus.HIT
        return stage_status


def _extract_position(update: TrackingUpdate) -> np.ndarray | None:
    if update.pose is None:
        return None
    position = np.array([update.pose.tx, update.pose.ty, update.pose.tz], dtype=np.float64)
    return position if np.all(np.isfinite(position)) else None


def _json_dump(payload: object) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


__all__ = ["PipelineDemoRuntimeController", "PipelineDemoSnapshot", "PipelineDemoState"]
