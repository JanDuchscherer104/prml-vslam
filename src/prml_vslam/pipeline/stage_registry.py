"""Stage registry and registry-backed execution-plan compiler."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
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
from prml_vslam.utils import PathConfig, RunArtifactPaths

AvailabilityFn = Callable[[RunRequest, BackendDescriptor], StageAvailability]


@dataclass(slots=True)
class _RegistryEntry:
    definition: StageDefinition
    availability_fn: AvailabilityFn


class StageRegistry:
    """Single source of truth for the linear pipeline vocabulary."""

    def __init__(self) -> None:
        self._entries: dict[StageKey, _RegistryEntry] = {}

    def register(self, definition: StageDefinition, availability_fn: AvailabilityFn) -> None:
        """Register one stage definition and its availability function."""
        self._entries[definition.key] = _RegistryEntry(definition=definition, availability_fn=availability_fn)

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
        planned_keys = [StageKey.INGEST, StageKey.SLAM]
        if request.benchmark.reference.enabled:
            planned_keys.append(StageKey.REFERENCE_RECONSTRUCTION)
        if request.benchmark.trajectory.enabled:
            planned_keys.append(StageKey.TRAJECTORY_EVALUATION)
        if request.benchmark.cloud.enabled:
            planned_keys.append(StageKey.CLOUD_EVALUATION)
        if request.benchmark.efficiency.enabled:
            planned_keys.append(StageKey.EFFICIENCY_EVALUATION)
        planned_keys.append(StageKey.SUMMARY)

        return RunPlan(
            run_id=path_config.slugify_experiment_name(request.experiment_name),
            mode=request.mode,
            method=MethodId(request.slam.backend.kind),
            artifact_root=run_paths.artifact_root,
            source=request.source,
            stages=[
                self._stage_for_key(
                    key=key,
                    request=request,
                    backend=backend,
                    run_paths=RunArtifactPaths.build(run_paths.artifact_root),
                )
                for key in planned_keys
            ],
        )

    def _stage_for_key(
        self,
        *,
        key: StageKey,
        request: RunRequest,
        backend: BackendDescriptor,
        run_paths: RunArtifactPaths,
    ) -> RunPlanStage:
        definition = self.get(key)
        availability = self.availability(key, request, backend)
        return RunPlanStage(
            key=definition.key,
            title=definition.title,
            summary=_stage_summary(key=key, request=request),
            outputs=_stage_outputs(key=key, request=request, run_paths=run_paths),
            executor_kind=_executor_kind_for_stage(key=key, request=request),
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


def _executor_kind_for_stage(*, key: StageKey, request: RunRequest) -> StageExecutorKind:
    if key is StageKey.SLAM and request.mode.value == "streaming":
        return StageExecutorKind.STREAMING
    if key is StageKey.SUMMARY:
        return StageExecutorKind.PROJECTION
    return StageExecutorKind.BATCH


def _stage_outputs(*, key: StageKey, request: RunRequest, run_paths: RunArtifactPaths) -> list[Path]:
    match key:
        case StageKey.INGEST:
            return [run_paths.sequence_manifest_path, run_paths.benchmark_inputs_path]
        case StageKey.SLAM:
            outputs = [run_paths.trajectory_path]
            if request.slam.backend.kind == MethodId.VISTA.value:
                if request.slam.outputs.emit_sparse_points or request.slam.outputs.emit_dense_points:
                    outputs.append(run_paths.point_cloud_path)
            else:
                if request.slam.outputs.emit_sparse_points:
                    outputs.append(run_paths.sparse_points_path)
                if request.slam.outputs.emit_dense_points:
                    outputs.append(run_paths.dense_points_path)
            return outputs
        case StageKey.TRAJECTORY_EVALUATION:
            return [run_paths.trajectory_metrics_path]
        case StageKey.REFERENCE_RECONSTRUCTION:
            return [run_paths.reference_cloud_path]
        case StageKey.CLOUD_EVALUATION:
            return [run_paths.cloud_metrics_path]
        case StageKey.EFFICIENCY_EVALUATION:
            return [run_paths.efficiency_metrics_path]
        case StageKey.SUMMARY:
            return [run_paths.summary_path, run_paths.stage_manifests_path]


def _stage_summary(*, key: StageKey, request: RunRequest) -> str:
    match key:
        case StageKey.INGEST:
            match request.source:
                case VideoSourceSpec(video_path=video_path, frame_stride=frame_stride):
                    return (
                        f"Decode '{video_path}' at stride {frame_stride} and materialize a normalized sequence "
                        "manifest."
                    )
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
        case StageKey.SLAM:
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
        case StageKey.TRAJECTORY_EVALUATION:
            baseline_label = {
                ReferenceSource.GROUND_TRUTH: "ground-truth trajectory",
                ReferenceSource.ARCORE: "ARCore baseline",
                ReferenceSource.ARKIT: "ARKit baseline",
            }[request.benchmark.trajectory.baseline_source]
            return f"Evaluate the estimated trajectory against the selected {baseline_label}."
        case StageKey.REFERENCE_RECONSTRUCTION:
            return "Placeholder reference reconstruction stage retained in the vocabulary."
        case StageKey.CLOUD_EVALUATION:
            return "Placeholder dense-cloud evaluation stage retained in the vocabulary."
        case StageKey.EFFICIENCY_EVALUATION:
            return "Placeholder efficiency-evaluation stage retained in the vocabulary."
        case StageKey.SUMMARY:
            return "Persist run summary and stage manifests from the executed stage outcomes."


__all__ = ["StageRegistry"]
