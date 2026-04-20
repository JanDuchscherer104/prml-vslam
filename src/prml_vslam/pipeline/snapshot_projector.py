"""Project append-only runtime events into live metadata snapshots.

This module contains the projector that turns the append-only event stream into
inspection-oriented :class:`RunSnapshot` values. It is intentionally pure and
deterministic: it does not own runtime state, it only applies
:class:`RunEvent` values to a previous snapshot.
"""

from __future__ import annotations

from collections.abc import Iterable

from prml_vslam.methods.events import (
    KeyframeAccepted,
    KeyframeVisualizationReady,
    MapStatsUpdated,
    PoseEstimated,
)
from prml_vslam.pipeline.contracts.events import (
    ArtifactRegistered,
    BackendNoticeReceived,
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
    StageProgressed,
    StageQueued,
    StageStarted,
    StageStatus,
)
from prml_vslam.pipeline.contracts.runtime import RunSnapshot, RunState, StreamingRunSnapshot
from prml_vslam.pipeline.contracts.stages import StageKey

_TRAJECTORY_HISTORY_LIMIT = 100


class SnapshotProjector:
    """Derive :class:`RunSnapshot` values from append-only runtime events.

    This projector is the bridge from event-first runtime truth to the
    inspection-oriented snapshot model consumed by app and CLI polling loops.
    """

    def project(self, snapshot: RunSnapshot, events: Iterable[RunEvent]) -> RunSnapshot:
        """Apply a sequence of events in order and return the final projected snapshot."""
        current = snapshot
        for event in events:
            current = self.apply(current, event)
        return current

    def apply(self, snapshot: RunSnapshot, event: RunEvent) -> RunSnapshot:
        """Apply one event to one snapshot.

        Args:
            snapshot: Previous projected state for one run.
            event: New event emitted for that same run.

        Returns:
            An updated snapshot. The input snapshot is never mutated.
        """
        if snapshot.run_id and event.run_id != snapshot.run_id:
            raise ValueError(f"Event run id mismatch: {event.run_id} != {snapshot.run_id}")

        updated = self._copy_for_update(snapshot)
        updated.run_id = event.run_id
        updated.last_event_id = event.event_id
        updated.last_event_kind = event.kind

        match event:
            case RunSubmitted() | RunStarted():
                if isinstance(event, RunStarted):
                    updated.state = RunState.PREPARING
            case StageQueued(stage_key=stage_key):
                updated.stage_status[stage_key] = StageStatus.QUEUED
            case StageStarted(stage_key=stage_key):
                updated.current_stage_key = stage_key
                updated.stage_status[stage_key] = StageStatus.RUNNING
                if updated.state is not RunState.STOPPED:
                    updated.state = RunState.PREPARING if stage_key is StageKey.INGEST else RunState.RUNNING
            case StageProgressed(stage_key=stage_key, progress=progress):
                updated.stage_progress[stage_key] = progress
            case ArtifactRegistered(artifact_key=artifact_key, artifact=artifact):
                updated.artifacts[artifact_key] = artifact
            case PacketObserved(packet=packet, frame=frame, received_frames=received_frames, measured_fps=measured_fps):
                if isinstance(updated, StreamingRunSnapshot):
                    updated.latest_packet = packet
                    updated.latest_frame = frame
                    updated.received_frames = received_frames
                    updated.measured_fps = measured_fps
                    if updated.state is not RunState.STOPPED:
                        updated.state = RunState.RUNNING
            case BackendNoticeReceived(notice=notice):
                if isinstance(updated, StreamingRunSnapshot):
                    match notice:
                        case PoseEstimated(pose=pose, timestamp_ns=timestamp_ns):
                            updated.trajectory_positions_xyz.append((pose.tx, pose.ty, pose.tz))
                            updated.trajectory_positions_xyz = updated.trajectory_positions_xyz[
                                -_TRAJECTORY_HISTORY_LIMIT:
                            ]
                            updated.trajectory_timestamps_s.append(timestamp_ns / 1e9)
                            updated.trajectory_timestamps_s = updated.trajectory_timestamps_s[
                                -_TRAJECTORY_HISTORY_LIMIT:
                            ]
                        case KeyframeAccepted(accepted_keyframes=accepted_keyframes, backend_fps=backend_fps):
                            if accepted_keyframes is not None:
                                updated.accepted_keyframes = accepted_keyframes
                            if backend_fps is not None:
                                updated.backend_fps = backend_fps
                        case KeyframeVisualizationReady(preview=preview):
                            updated.latest_preview = preview
                        case MapStatsUpdated(
                            num_sparse_points=num_sparse_points,
                            num_dense_points=num_dense_points,
                        ):
                            updated.num_sparse_points = num_sparse_points
                            updated.num_dense_points = num_dense_points
                        case _:
                            pass
            case StageCompleted(
                stage_key=stage_key,
                outcome=outcome,
                sequence_manifest=sequence_manifest,
                benchmark_inputs=benchmark_inputs,
                slam=slam,
                ground_alignment=ground_alignment,
                visualization=visualization,
                summary=summary,
                stage_manifests=stage_manifests,
            ):
                updated.stage_status[stage_key] = StageStatus.COMPLETED
                updated.stage_progress.pop(stage_key, None)
                if updated.current_stage_key is stage_key:
                    updated.current_stage_key = None
                updated.artifacts.update(outcome.artifacts)
                if sequence_manifest is not None:
                    updated.sequence_manifest = sequence_manifest
                if benchmark_inputs is not None:
                    updated.benchmark_inputs = benchmark_inputs
                if slam is not None:
                    updated.slam = slam
                if ground_alignment is not None:
                    updated.ground_alignment = ground_alignment
                if visualization is not None:
                    updated.visualization = visualization
                if summary is not None:
                    updated.summary = summary
                if stage_manifests:
                    updated.stage_manifests = stage_manifests
            case StageFailed(stage_key=stage_key, outcome=outcome):
                updated.stage_status[stage_key] = StageStatus.FAILED
                updated.stage_progress.pop(stage_key, None)
                if updated.current_stage_key is stage_key:
                    updated.current_stage_key = None
                updated.error_message = outcome.error_message
            case RunStopRequested():
                if updated.state not in {RunState.COMPLETED, RunState.FAILED}:
                    updated.state = RunState.STOPPED
            case RunStopped():
                if updated.state not in {RunState.COMPLETED, RunState.FAILED}:
                    updated.state = RunState.STOPPED
                updated.current_stage_key = None
            case RunCompleted():
                if updated.state is not RunState.STOPPED:
                    updated.state = RunState.COMPLETED
                updated.current_stage_key = None
            case RunFailed(error_message=error_message):
                updated.state = RunState.FAILED
                updated.error_message = error_message
                updated.current_stage_key = None
            case _:
                raise ValueError(f"Unsupported run event: {event!r}")
        return updated

    @staticmethod
    def _copy_for_update(snapshot: RunSnapshot) -> RunSnapshot:
        """Copy only the mutable containers that projection mutates."""
        updated = snapshot.model_copy()
        updated.stage_status = dict(snapshot.stage_status)
        updated.stage_progress = dict(snapshot.stage_progress)
        updated.artifacts = dict(snapshot.artifacts)
        if isinstance(snapshot, StreamingRunSnapshot):
            updated.trajectory_positions_xyz = list(snapshot.trajectory_positions_xyz)
            updated.trajectory_timestamps_s = list(snapshot.trajectory_timestamps_s)
        return updated


__all__ = ["SnapshotProjector"]
