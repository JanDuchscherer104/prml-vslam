"""Pipeline-owned streaming session service for the bounded ADVIO replay demo."""

from __future__ import annotations

import hashlib
import json
import time
from enum import StrEnum
from pathlib import Path
from threading import Event
from typing import TYPE_CHECKING

from pydantic import Field

from prml_vslam.methods.contracts import MethodId
from prml_vslam.methods.mock_vslam import MockSlamBackendConfig
from prml_vslam.pipeline.contracts import (
    PipelineMode,
    RunPlan,
    RunPlanStageId,
    RunRequest,
    RunSummary,
    SequenceManifest,
    SlamArtifacts,
    SlamUpdate,
    StageExecutionStatus,
    StageManifest,
)
from prml_vslam.pipeline.protocols import SlamBackend, SlamSession, StreamingSequenceSource
from prml_vslam.protocols import FramePacketStream
from prml_vslam.utils import BaseConfig, Console, PathConfig, RunArtifactPaths
from prml_vslam.utils.packet_session import (
    PacketSessionMetrics,
    PacketSessionRuntime,
    PacketSessionSnapshot,
    extract_pose_position,
)

if TYPE_CHECKING:
    from collections.abc import Callable


_ACTIVE_SESSION_STATES = frozenset({"connecting", "running"})
_SUPPORTED_STAGE_IDS = frozenset(
    {
        RunPlanStageId.INGEST,
        RunPlanStageId.SLAM,
        RunPlanStageId.SUMMARY,
    }
)


class PipelineSessionState(StrEnum):
    """Lifecycle states exposed by the pipeline-owned session service."""

    IDLE = "idle"
    CONNECTING = "connecting"
    RUNNING = "running"
    COMPLETED = "completed"
    STOPPED = "stopped"
    FAILED = "failed"


class PipelineSessionSnapshot(PacketSessionSnapshot):
    """Current session state rendered by the Streamlit Pipeline page."""

    state: PipelineSessionState = PipelineSessionState.IDLE
    """Current lifecycle state."""

    plan: RunPlan | None = None
    """Resolved run plan for the current or most recent session."""

    sequence_manifest: SequenceManifest | None = None
    """Normalized sequence manifest prepared by the ingest stage."""

    latest_slam_update: SlamUpdate | None = None
    """Most recent incremental SLAM update."""

    slam: SlamArtifacts | None = None
    """Persisted SLAM artifacts returned by the backend."""

    summary: RunSummary | None = None
    """Final persisted run summary."""

    stage_manifests: list[StageManifest] = Field(default_factory=list)
    """Executed stage manifests owned by this slice."""

    num_sparse_points: int = 0
    """Latest sparse-point count reported by the backend."""

    num_dense_points: int = 0
    """Latest dense-point count reported by the backend."""


class PipelineSessionService:
    """Own the bounded streaming session flow for the current pipeline slice."""

    def __init__(
        self,
        *,
        path_config: PathConfig | None = None,
        frame_timeout_seconds: float = 0.5,
        fps_window_size: int = 30,
        trajectory_window_size: int = 1024,
        slam_backend_factory: Callable[[MethodId], SlamBackend] | None = None,
    ) -> None:
        self.path_config = PathConfig() if path_config is None else path_config
        self.frame_timeout_seconds = frame_timeout_seconds
        self.fps_window_size = fps_window_size
        self.trajectory_window_size = trajectory_window_size
        self._slam_backend_factory = (
            _default_slam_backend_factory if slam_backend_factory is None else slam_backend_factory
        )
        self._console = Console(__name__).child(self.__class__.__name__)
        self._runtime = PacketSessionRuntime(
            empty_snapshot=PipelineSessionSnapshot,
            stop_timeout_message="Timed out stopping the pipeline session worker thread.",
        )

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
            self._runtime.replace_snapshot(
                PipelineSessionSnapshot(
                    state=PipelineSessionState.FAILED,
                    plan=plan,
                    error_message=error_message,
                )
            )
            raise RuntimeError(error_message)

        self._runtime.launch(
            connecting_snapshot=PipelineSessionSnapshot(
                state=PipelineSessionState.CONNECTING,
                plan=plan,
            ),
            thread_name=f"Pipeline-session-{plan.run_id}",
            worker_target=lambda stop_event: self._run_worker(
                request=request,
                plan=plan,
                source=source,
                stop_event=stop_event,
            ),
        )

    def stop(self) -> None:
        """Stop the active session and preserve the last rendered snapshot."""
        self._runtime.stop(snapshot_update=self._to_stopped_snapshot)

    def snapshot(self) -> PipelineSessionSnapshot:
        """Return a deep copy of the latest session snapshot."""
        return self._runtime.snapshot()

    def _run_worker(
        self,
        *,
        request: RunRequest,
        plan: RunPlan,
        source: StreamingSequenceSource,
        stop_event: Event,
    ) -> None:
        run_paths = RunArtifactPaths.build(plan.artifact_root)
        metrics = PacketSessionMetrics(
            fps_window_size=self.fps_window_size,
            trajectory_window_size=self.trajectory_window_size,
        )
        slam_backend: SlamBackend | None = None
        slam_session: SlamSession | None = None
        sequence_manifest: SequenceManifest | None = None
        slam_artifacts: SlamArtifacts | None = None
        summary: RunSummary | None = None
        stage_manifests: list[StageManifest] = []
        ingest_started = False
        slam_started = False
        final_state = PipelineSessionState.COMPLETED
        pipeline_failed = False
        error_message = ""
        start_monotonic = time.monotonic()

        def _record_runtime_error(exc: Exception) -> None:
            nonlocal final_state, pipeline_failed, error_message
            if isinstance(exc, EOFError):
                final_state = PipelineSessionState.COMPLETED
                return
            final_state = PipelineSessionState.FAILED
            pipeline_failed = True
            error_message = str(exc)
            self._console.error(error_message)

        def _build_terminal_snapshot(
            snapshot: PipelineSessionSnapshot,
            stop_requested: bool,
        ) -> PipelineSessionSnapshot:
            nonlocal slam_artifacts, summary, stage_manifests, final_state, pipeline_failed, error_message
            preserve_terminal_outcome = stop_requested or final_state is PipelineSessionState.FAILED
            if slam_session is not None:
                try:
                    slam_artifacts = slam_session.close()
                except Exception as exc:
                    if preserve_terminal_outcome:
                        self._console.warning(str(exc))
                    else:
                        final_state = PipelineSessionState.FAILED
                        pipeline_failed = True
                        error_message = str(exc)
                        self._console.error(error_message)
            if stop_requested and final_state is not PipelineSessionState.FAILED:
                final_state = PipelineSessionState.STOPPED
            try:
                summary, stage_manifests = self._finalize_outputs(
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
                final_state = PipelineSessionState.FAILED
                error_message = str(exc)
                self._console.error(error_message)
                summary = None
                stage_manifests = []
            return snapshot.model_copy(
                update={
                    "state": final_state,
                    "plan": plan,
                    "sequence_manifest": sequence_manifest,
                    "slam": slam_artifacts,
                    "summary": summary,
                    "stage_manifests": stage_manifests,
                    "error_message": error_message,
                }
            )

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

            slam_backend = self._slam_backend_factory(request.slam.method)

            def _start_streaming_slam(_connected_target: object) -> None:
                nonlocal slam_started, slam_session
                slam_started = True
                slam_session = slam_backend.start_session(request.slam, plan.artifact_root)
                self._set_snapshot(
                    state=PipelineSessionState.RUNNING,
                    plan=plan,
                    sequence_manifest=sequence_manifest,
                    error_message="",
                )

            def _consume_packet(stream: FramePacketStream) -> None:
                packet = stream.wait_for_packet(timeout_seconds=self.frame_timeout_seconds)
                update = slam_session.step(packet)
                arrival_time_s = time.monotonic()
                metrics.record(
                    arrival_time_s=arrival_time_s,
                    position_xyz=extract_pose_position(update),
                    trajectory_time_s=arrival_time_s - start_monotonic if update.pose is not None else None,
                )
                self._set_snapshot(
                    state=PipelineSessionState.RUNNING,
                    latest_packet=packet,
                    latest_slam_update=update,
                    num_sparse_points=update.num_sparse_points,
                    num_dense_points=update.num_dense_points,
                    error_message="",
                    **metrics.snapshot_fields(),
                )

            stream = source.open_stream(loop=request.mode is PipelineMode.STREAMING)
            self._runtime.register_stream(stop_event=stop_event, stream=stream)
            _start_streaming_slam(stream.connect())
            while not stop_event.is_set():
                _consume_packet(stream)
        except EOFError:
            final_state = PipelineSessionState.COMPLETED
        except Exception as exc:
            _record_runtime_error(exc)
        finally:
            self._runtime.finalize(
                stop_event=stop_event,
                snapshot_update=lambda snapshot: _build_terminal_snapshot(snapshot, stop_event.is_set()),
            )

    def _finalize_outputs(
        self,
        *,
        request: RunRequest,
        plan: RunPlan,
        run_paths: RunArtifactPaths,
        sequence_manifest: SequenceManifest | None,
        slam: SlamArtifacts | None,
        ingest_started: bool,
        slam_started: bool,
        pipeline_failed: bool,
        error_message: str,
    ) -> tuple[RunSummary, list[StageManifest]]:
        """Persist the run summary plus truthful stage manifests for executed work."""
        stage_status = self._build_stage_status(
            plan=plan,
            sequence_manifest=sequence_manifest,
            slam=slam,
            ingest_started=ingest_started,
            slam_started=slam_started,
            pipeline_failed=pipeline_failed,
        )
        non_summary_manifests = self._build_stage_manifests(
            request=request,
            plan=plan,
            run_paths=run_paths,
            sequence_manifest=sequence_manifest,
            slam=slam,
            stage_status=stage_status,
        )
        summary_manifest = self._build_summary_manifest(
            request=request,
            run_paths=run_paths,
            sequence_manifest=sequence_manifest,
            slam=slam,
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
        slam: SlamArtifacts | None,
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
                StageExecutionStatus.RAN if slam is not None and not pipeline_failed else StageExecutionStatus.FAILED
            )
        return stage_status

    def _build_stage_manifests(
        self,
        *,
        request: RunRequest,
        plan: RunPlan,
        run_paths: RunArtifactPaths,
        sequence_manifest: SequenceManifest | None,
        slam: SlamArtifacts | None,
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
            if slam is not None:
                output_paths["trajectory_tum"] = slam.trajectory_tum.path
                if slam.sparse_points_ply is not None:
                    output_paths["sparse_points_ply"] = slam.sparse_points_ply.path
                if slam.dense_points_ply is not None:
                    output_paths["dense_points_ply"] = slam.dense_points_ply.path
                if slam.preview_log_jsonl is not None:
                    output_paths["preview_log_jsonl"] = slam.preview_log_jsonl.path
            manifests.append(
                StageManifest(
                    stage_id=RunPlanStageId.SLAM,
                    config_hash=_stable_hash(request.slam),
                    input_fingerprint=_stable_hash(sequence_manifest or {"missing": "sequence_manifest"}),
                    output_paths=output_paths,
                    status=stage_status[RunPlanStageId.SLAM],
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
        slam: SlamArtifacts | None,
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
                    "slam": slam,
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
        self._runtime.update_fields(**fields)

    @staticmethod
    def _to_stopped_snapshot(snapshot: PipelineSessionSnapshot) -> PipelineSessionSnapshot:
        """Mark one active session snapshot as stopped without discarding outputs."""
        if snapshot.state.value not in _ACTIVE_SESSION_STATES:
            return snapshot
        return snapshot.model_copy(update={"state": PipelineSessionState.STOPPED})


def _default_slam_backend_factory(method_id: MethodId) -> SlamBackend:
    """Build the mock SLAM backend for one method id."""
    backend = MockSlamBackendConfig().setup_target()
    if backend is None:
        raise RuntimeError(f"Failed to initialize the mock SLAM backend for method '{method_id.value}'.")
    return backend


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
