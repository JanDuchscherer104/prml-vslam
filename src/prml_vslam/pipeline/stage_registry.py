"""Stage registry and registry-backed execution-plan compiler."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from prml_vslam.benchmark import ReferenceSource
from prml_vslam.datasets.contracts import DatasetId
from prml_vslam.methods.contracts import MethodId
from prml_vslam.methods.descriptors import BackendDescriptor
from prml_vslam.pipeline.contracts.plan import RunPlan, RunPlanStage
from prml_vslam.pipeline.contracts.request import (
    DatasetSourceSpec,
    Record3DLiveSourceSpec,
    RunRequest,
    VideoSourceSpec,
)
from prml_vslam.pipeline.contracts.stages import (
    StageAvailability,
    StageDefinition,
    StageExecutorKind,
    StageKey,
)
from prml_vslam.utils import BaseData, PathConfig, RunArtifactPaths

EnabledFn = Callable[[RunRequest], bool]
AvailabilityFn = Callable[[RunRequest, BackendDescriptor], StageAvailability]
SummaryFn = Callable[[RunRequest], str]
OutputsFn = Callable[[RunRequest, RunArtifactPaths], list[Path]]
ExecutorKindFn = Callable[[RunRequest], StageExecutorKind]


class _RegistryEntry(BaseData):
    definition: StageDefinition
    enabled_fn: EnabledFn | None = None
    availability_fn: AvailabilityFn
    summary_fn: SummaryFn | None = None
    outputs_fn: OutputsFn | None = None
    executor_kind_fn: ExecutorKindFn | None = None


class StageRegistry:
    """Single source of truth for the linear pipeline vocabulary."""

    def __init__(self) -> None:
        self._entries: dict[StageKey, _RegistryEntry] = {}

    def register(
        self,
        definition: StageDefinition,
        availability_fn: AvailabilityFn,
        *,
        enabled_fn: EnabledFn | None = None,
        summary_fn: SummaryFn | None = None,
        outputs_fn: OutputsFn | None = None,
        executor_kind_fn: ExecutorKindFn | None = None,
    ) -> None:
        """Register one stage definition and its availability function."""
        self._entries[definition.key] = _RegistryEntry(
            definition=definition,
            enabled_fn=enabled_fn,
            availability_fn=availability_fn,
            summary_fn=summary_fn,
            outputs_fn=outputs_fn,
            executor_kind_fn=executor_kind_fn,
        )

    def get(self, key: StageKey) -> StageDefinition:
        """Return one registered stage definition."""
        return self._entries[key].definition

    def availability(self, key: StageKey, request: RunRequest, backend: BackendDescriptor) -> StageAvailability:
        """Return whether one stage is executable for the request/backend pair."""
        return self._entries[key].availability_fn(request, backend)

    def compile(self, *, request: RunRequest, backend: BackendDescriptor, path_config: PathConfig) -> RunPlan:
        """Compile one deterministic run plan from the stage registry."""
        run_paths = path_config.plan_run_paths(
            experiment_name=request.experiment_name,
            method_slug=request.slam.backend.kind,
            output_dir=request.output_dir,
        )
        resolved_run_paths = RunArtifactPaths.build(run_paths.artifact_root)
        active_entries = [
            entry for entry in self._entries.values() if entry.enabled_fn is None or entry.enabled_fn(request)
        ]

        return RunPlan(
            run_id=path_config.slugify_experiment_name(request.experiment_name),
            mode=request.mode,
            artifact_root=run_paths.artifact_root,
            source=request.source,
            stages=[
                self._stage_for_entry(
                    entry=entry,
                    request=request,
                    backend=backend,
                    run_paths=resolved_run_paths,
                )
                for entry in active_entries
            ],
        )

    def _stage_for_entry(
        self,
        *,
        entry: _RegistryEntry,
        request: RunRequest,
        backend: BackendDescriptor,
        run_paths: RunArtifactPaths,
    ) -> RunPlanStage:
        definition = entry.definition
        availability = entry.availability_fn(request, backend)
        return RunPlanStage(
            key=definition.key,
            title=definition.title,
            summary=definition.description if entry.summary_fn is None else entry.summary_fn(request),
            outputs=[] if entry.outputs_fn is None else entry.outputs_fn(request, run_paths),
            executor_kind=(
                definition.executor_kind if entry.executor_kind_fn is None else entry.executor_kind_fn(request)
            ),
            available=availability.available,
            availability_reason=availability.reason,
            failure_modes=definition.failure_modes,
        )

    @classmethod
    def default(cls) -> StageRegistry:
        """Build the repository default stage registry."""
        registry = cls()
        registry.register(
            StageDefinition(
                key=StageKey.INGEST,
                title="Normalize Input Sequence",
                depends_on=[],
                output_keys=["sequence_manifest", "benchmark_inputs"],
                executor_kind=StageExecutorKind.BATCH,
                description="Resolve the normalized sequence manifest and benchmark inputs.",
                failure_modes=["source_open_failed", "normalization_failed"],
            ),
            lambda _request, _backend: StageAvailability(available=True),
            summary_fn=_ingest_summary,
            outputs_fn=_ingest_outputs,
        )
        registry.register(
            StageDefinition(
                key=StageKey.SLAM,
                title="Run SLAM Backend",
                depends_on=[StageKey.INGEST],
                output_keys=["trajectory_tum", "sparse_points", "dense_points"],
                executor_kind=StageExecutorKind.BATCH,
                description="Execute the selected backend over the normalized input.",
                failure_modes=["backend_init_failed", "backend_execution_failed"],
            ),
            _slam_stage_availability,
            summary_fn=_slam_summary,
            outputs_fn=_slam_outputs,
            executor_kind_fn=_slam_executor_kind,
        )
        registry.register(
            StageDefinition(
                key=StageKey.TRAJECTORY_EVALUATION,
                title="Evaluate Trajectory",
                depends_on=[StageKey.INGEST, StageKey.SLAM],
                output_keys=["trajectory_metrics"],
                executor_kind=StageExecutorKind.BATCH,
                description="Compare the estimated trajectory against the selected reference.",
                failure_modes=["missing_reference", "evaluation_failed"],
            ),
            _trajectory_stage_availability,
            enabled_fn=lambda request: request.benchmark.trajectory.enabled,
            summary_fn=_trajectory_stage_summary,
            outputs_fn=lambda _request, run_paths: [run_paths.trajectory_metrics_path],
        )
        registry.register(
            StageDefinition(
                key=StageKey.REFERENCE_RECONSTRUCTION,
                title="Build Reference Reconstruction",
                depends_on=[StageKey.INGEST],
                output_keys=["reference_cloud"],
                executor_kind=StageExecutorKind.BATCH,
                description="Placeholder reference reconstruction stage.",
                failure_modes=["not_implemented"],
            ),
            lambda _request, _backend: StageAvailability(
                available=False,
                reason="Reference reconstruction remains a planned placeholder in this refactor.",
            ),
            enabled_fn=lambda request: request.benchmark.reference.enabled,
            outputs_fn=lambda _request, run_paths: [run_paths.reference_cloud_path],
        )
        registry.register(
            StageDefinition(
                key=StageKey.CLOUD_EVALUATION,
                title="Evaluate Dense Cloud",
                depends_on=[StageKey.SLAM],
                output_keys=["cloud_metrics"],
                executor_kind=StageExecutorKind.BATCH,
                description="Placeholder dense-cloud evaluation stage.",
                failure_modes=["not_implemented"],
            ),
            lambda _request, _backend: StageAvailability(
                available=False,
                reason="Dense-cloud evaluation remains a planned placeholder in this refactor.",
            ),
            enabled_fn=lambda request: request.benchmark.cloud.enabled,
            outputs_fn=lambda _request, run_paths: [run_paths.cloud_metrics_path],
        )
        registry.register(
            StageDefinition(
                key=StageKey.EFFICIENCY_EVALUATION,
                title="Measure Efficiency",
                depends_on=[StageKey.SLAM],
                output_keys=["efficiency_metrics"],
                executor_kind=StageExecutorKind.BATCH,
                description="Placeholder efficiency-evaluation stage.",
                failure_modes=["not_implemented"],
            ),
            lambda _request, _backend: StageAvailability(
                available=False,
                reason="Efficiency evaluation remains a planned placeholder in this refactor.",
            ),
            enabled_fn=lambda request: request.benchmark.efficiency.enabled,
            outputs_fn=lambda _request, run_paths: [run_paths.efficiency_metrics_path],
        )
        registry.register(
            StageDefinition(
                key=StageKey.SUMMARY,
                title="Write Run Summary",
                depends_on=[StageKey.INGEST, StageKey.SLAM],
                output_keys=["run_summary", "stage_manifests"],
                executor_kind=StageExecutorKind.PROJECTION,
                description="Project stage outcomes into persisted run summary and manifests.",
                failure_modes=["summary_projection_failed"],
            ),
            lambda _request, _backend: StageAvailability(available=True),
            outputs_fn=lambda _request, run_paths: [run_paths.summary_path, run_paths.stage_manifests_path],
        )
        return registry


def _slam_stage_availability(request: RunRequest, backend: BackendDescriptor) -> StageAvailability:
    if request.mode.value == "offline" and not backend.capabilities.offline:
        return StageAvailability(available=False, reason=f"{backend.display_name} does not support offline execution.")
    if request.mode.value == "streaming" and not backend.capabilities.streaming:
        return StageAvailability(
            available=False,
            reason=f"{backend.display_name} does not support streaming execution.",
        )
    return StageAvailability(available=True)


def _trajectory_stage_availability(_request: RunRequest, backend: BackendDescriptor) -> StageAvailability:
    if not backend.capabilities.trajectory_benchmark_support:
        return StageAvailability(
            available=False,
            reason=f"{backend.display_name} does not support repository trajectory evaluation.",
        )
    return StageAvailability(available=True)


def _slam_executor_kind(request: RunRequest) -> StageExecutorKind:
    if request.mode.value == "streaming":
        return StageExecutorKind.STREAMING
    return StageExecutorKind.BATCH


def _ingest_outputs(_request: RunRequest, run_paths: RunArtifactPaths) -> list[Path]:
    return [run_paths.sequence_manifest_path, run_paths.benchmark_inputs_path]


def _slam_outputs(request: RunRequest, run_paths: RunArtifactPaths) -> list[Path]:
    outputs = [run_paths.trajectory_path]
    if request.slam.backend.kind == MethodId.VISTA.value:
        if request.slam.outputs.emit_sparse_points or request.slam.outputs.emit_dense_points:
            outputs.append(run_paths.point_cloud_path)
        return outputs
    if request.slam.outputs.emit_sparse_points:
        outputs.append(run_paths.sparse_points_path)
    if request.slam.outputs.emit_dense_points:
        outputs.append(run_paths.dense_points_path)
    return outputs


def _ingest_summary(request: RunRequest) -> str:
    match request.source:
        case VideoSourceSpec(video_path=video_path, frame_stride=frame_stride):
            return f"Decode '{video_path}' at stride {frame_stride} and materialize a normalized sequence manifest."
        case DatasetSourceSpec(dataset_id=DatasetId.ADVIO, sequence_id=sequence_id):
            return f"Normalize ADVIO sequence '{sequence_id}' into the shared sequence-manifest boundary."
        case Record3DLiveSourceSpec(
            transport=transport,
            persist_capture=persist_capture,
            device_index=device_index,
            device_address=device_address,
        ):
            persistence = "with persistence" if persist_capture else "without persistence"
            source_label = (
                f"USB device #{device_index}"
                if transport.value == "usb" and device_index is not None
                else device_address or transport.value
            )
            return f"Capture the Record3D source '{source_label}' {persistence} into the shared boundary."


def _slam_summary(request: RunRequest) -> str:
    artifact_names = ["trajectory"]
    if request.slam.backend.kind == MethodId.VISTA.value:
        if request.slam.outputs.emit_sparse_points or request.slam.outputs.emit_dense_points:
            artifact_names.append("point-cloud geometry")
    else:
        if request.slam.outputs.emit_sparse_points:
            artifact_names.append("sparse geometry")
        if request.slam.outputs.emit_dense_points:
            artifact_names.append("dense geometry")
    return f"Run the {MethodId(request.slam.backend.kind).display_name} backend and export {', '.join(artifact_names)} artifacts."


def _trajectory_stage_summary(request: RunRequest) -> str:
    baseline_label = {
        ReferenceSource.GROUND_TRUTH: "ground-truth trajectory",
        ReferenceSource.ARCORE: "ARCore baseline",
        ReferenceSource.ARKIT: "ARKit baseline",
    }[request.benchmark.trajectory.baseline_source]
    return f"Evaluate the estimated trajectory against the selected {baseline_label}."


__all__ = ["StageRegistry"]
