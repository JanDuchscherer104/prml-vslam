"""Project append-only runtime events into live metadata snapshots.

This module contains the projector that turns durable run events plus live
runtime updates into inspection-oriented :class:`RunSnapshot` values. It is
intentionally pure and deterministic: it does not own runtime state, it only
applies :class:`RunEvent` and :class:`StageRuntimeUpdate` values to a previous
snapshot.
"""

from __future__ import annotations

from collections.abc import Iterable

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
    StageProgress,
    StageProgressed,
    StageQueued,
    StageStarted,
    StageStatus,
)
from prml_vslam.pipeline.contracts.runtime import RunSnapshot, RunState
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.contracts import StageRuntimeStatus, StageRuntimeUpdate


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
                # TODO(pipeline-refactor/WP-10): Delete this compatibility
                # branch after progress projection reads StageRuntimeUpdate.
                updated.stage_progress[stage_key] = progress
            case ArtifactRegistered(artifact_key=artifact_key, artifact=artifact):
                updated.artifacts[artifact_key] = artifact
            case PacketObserved(packet=packet, frame=frame, received_frames=received_frames, measured_fps=measured_fps):
                # TODO(pipeline-refactor/WP-10): Delete this compatibility
                # branch after packet telemetry is projected from live updates.
                del packet, frame
                updated.stage_runtime_status[StageKey.INGEST] = StageRuntimeStatus(
                    stage_key=StageKey.INGEST,
                    lifecycle_state=StageStatus.RUNNING,
                    processed_items=received_frames,
                    fps=measured_fps,
                )
                if updated.state is not RunState.STOPPED:
                    updated.state = RunState.RUNNING
            case BackendNoticeReceived(notice=notice):
                # TODO(pipeline-refactor/WP-10): Delete this compatibility
                # branch after backend telemetry is projected from
                # StageRuntimeUpdate.semantic_events and live refs.
                del notice
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
                updated.stage_outcomes[stage_key] = outcome
                updated.stage_status[stage_key] = StageStatus.COMPLETED
                updated.stage_runtime_status.pop(stage_key, None)
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
                updated.stage_outcomes[stage_key] = outcome
                updated.stage_status[stage_key] = StageStatus.FAILED
                updated.stage_runtime_status.pop(stage_key, None)
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

    def apply_runtime_update(self, snapshot: RunSnapshot, update: StageRuntimeUpdate) -> RunSnapshot:
        """Apply one live runtime update to one snapshot without durable events."""
        updated = self._copy_for_update(snapshot)
        updated.run_id = snapshot.run_id
        updated.last_event_kind = "stage.runtime_update"
        stage_key = update.stage_key
        if update.runtime_status is not None:
            updated.stage_runtime_status[stage_key] = update.runtime_status
            updated.stage_status[stage_key] = update.runtime_status.lifecycle_state
            if _has_progress_content(update.runtime_status):
                updated.stage_progress[stage_key] = StageProgress(
                    message=update.runtime_status.progress_message,
                    completed_steps=update.runtime_status.completed_steps,
                    total_steps=update.runtime_status.total_steps,
                    unit=update.runtime_status.progress_unit,
                )
            else:
                updated.stage_progress.pop(stage_key, None)
        for item in update.visualizations:
            if item.payload_refs:
                stage_refs = updated.live_refs.setdefault(stage_key, {})
                for slot, ref in item.payload_refs.items():
                    stage_refs[f"{item.role}:{slot}" if item.role else slot] = ref
        if updated.state not in {RunState.COMPLETED, RunState.FAILED, RunState.STOPPED}:
            updated.state = RunState.RUNNING
        return updated

    @staticmethod
    def _copy_for_update(snapshot: RunSnapshot) -> RunSnapshot:
        """Copy only the mutable containers that projection mutates."""
        updated = snapshot.model_copy()
        updated.stage_outcomes = dict(snapshot.stage_outcomes)
        updated.stage_runtime_status = dict(snapshot.stage_runtime_status)
        updated.live_refs = {stage_key: dict(refs) for stage_key, refs in snapshot.live_refs.items()}
        updated.stage_status = dict(snapshot.stage_status)
        updated.stage_progress = dict(snapshot.stage_progress)
        updated.artifacts = dict(snapshot.artifacts)
        return updated


def _has_progress_content(status: StageRuntimeStatus) -> bool:
    return (
        bool(status.progress_message)
        or status.completed_steps is not None
        or status.total_steps is not None
        or status.progress_unit is not None
    )


__all__ = ["SnapshotProjector"]
