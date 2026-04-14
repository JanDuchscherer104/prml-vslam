"""Offline pipeline runner."""

from __future__ import annotations

from threading import Event

from prml_vslam.methods.protocols import OfflineSlamBackend
from prml_vslam.pipeline.contracts.plan import RunPlan
from prml_vslam.pipeline.contracts.request import RunRequest
from prml_vslam.pipeline.state import RunSnapshot, RunState
from prml_vslam.protocols.source import BenchmarkInputSource, OfflineSequenceSource
from prml_vslam.utils import Console, RunArtifactPaths
from prml_vslam.visualization.rerun import collect_native_visualization_artifacts

from .finalization import compute_trajectory_evaluation, finalize_run_outputs, write_json
from .ingest import materialize_offline_manifest
from .runner_runtime import RunnerRuntime

_STOP_JOIN_TIMEOUT_SECONDS = 10.0


class OfflineRunner:
    """Own one threaded offline run over a materialized sequence boundary."""

    def __init__(self) -> None:
        self._console = Console(__name__).child(self.__class__.__name__)
        self._runtime = RunnerRuntime(
            empty_snapshot=RunSnapshot,
            stop_timeout_message="Offline worker thread did not stop within the timeout.",
        )

    def start(
        self,
        *,
        request: RunRequest,
        plan: RunPlan,
        source: OfflineSequenceSource,
        slam_backend: OfflineSlamBackend,
    ) -> None:
        """Start a new offline run for one already-planned request."""
        self.stop()
        self._runtime.launch(
            starting_snapshot=RunSnapshot(state=RunState.PREPARING, plan=plan),
            thread_name=f"Pipeline-offline-{plan.run_id}",
            worker_target=lambda stop_event: self._run_worker(
                request=request,
                plan=plan,
                source=source,
                slam_backend=slam_backend,
                stop_event=stop_event,
            ),
        )

    def stop(self) -> None:
        """Stop the active offline run."""
        self._runtime.stop(join_timeout_seconds=_STOP_JOIN_TIMEOUT_SECONDS)

    def snapshot(self) -> RunSnapshot:
        """Return the latest offline runtime snapshot."""
        return self._runtime.snapshot()

    def set_failed_start(self, *, plan: RunPlan, error_message: str) -> None:
        """Set the initial snapshot state for a run that failed to start."""
        self._runtime.update_fields(
            state=RunState.FAILED,
            plan=plan,
            error_message=error_message,
        )

    def _run_worker(
        self,
        *,
        request: RunRequest,
        plan: RunPlan,
        source: OfflineSequenceSource,
        slam_backend: OfflineSlamBackend,
        stop_event: Event,
    ) -> None:
        run_paths = RunArtifactPaths.build(plan.artifact_root)
        ingest_started = False
        slam_started = False
        pipeline_failed = False
        error_message = ""
        sequence_manifest = None
        benchmark_inputs = None
        slam_artifacts = None
        visualization_artifacts = None
        trajectory_evaluation = None

        final_state = RunState.COMPLETED

        try:
            self._console.info(f"Preparing offline run '{plan.run_id}' from source '{source.label}'.")
            ingest_started = True
            prepared_manifest = source.prepare_sequence_manifest(run_paths.sequence_manifest_path.parent)
            if isinstance(source, BenchmarkInputSource):
                benchmark_inputs = source.prepare_benchmark_inputs(run_paths.benchmark_inputs_path.parent)
                if benchmark_inputs is not None:
                    write_json(run_paths.benchmark_inputs_path, benchmark_inputs)

            sequence_manifest = materialize_offline_manifest(
                request=request,
                prepared_manifest=prepared_manifest,
                run_paths=run_paths,
            )
            write_json(run_paths.sequence_manifest_path, sequence_manifest)
            self._runtime.update_fields(
                state=RunState.RUNNING,
                plan=plan,
                sequence_manifest=sequence_manifest,
                benchmark_inputs=benchmark_inputs,
                error_message="",
            )
            if stop_event.is_set():
                final_state = RunState.STOPPED
            else:
                slam_started = True
                slam_artifacts = slam_backend.run_sequence(
                    sequence_manifest,
                    benchmark_inputs,
                    request.benchmark.trajectory.baseline_source,
                    backend_config=request.slam.backend,
                    output_policy=request.slam.outputs,
                    artifact_root=plan.artifact_root,
                )
                visualization_artifacts = collect_native_visualization_artifacts(
                    native_output_dir=run_paths.native_output_dir,
                    preserve_native_rerun=request.visualization.preserve_native_rerun,
                )
                trajectory_evaluation = compute_trajectory_evaluation(
                    request=request,
                    plan=plan,
                    sequence_manifest=sequence_manifest,
                    benchmark_inputs=benchmark_inputs,
                    slam=slam_artifacts,
                )
        except Exception as exc:
            final_state = RunState.FAILED
            pipeline_failed = True
            error_message = str(exc)
            self._console.error(error_message)
        finally:
            if stop_event.is_set() and final_state is not RunState.FAILED:
                final_state = RunState.STOPPED
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
                self._runtime.update_fields(
                    state=final_state,
                    summary=summary,
                    stage_manifests=stage_manifests,
                    error_message=error_message,
                )
            except Exception as exc:
                final_state = RunState.FAILED
                self._console.error(f"Finalization failed: {exc}")
                self._runtime.update_fields(state=RunState.FAILED, error_message=str(exc))


__all__ = ["OfflineRunner"]
