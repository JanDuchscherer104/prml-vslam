"""Registry-backed compiler for the linear pipeline stage vocabulary.

The registry is the planning-time source of truth for stage order, request
gating, backend availability, and canonical output ownership. Runtime
execution should consume the resulting :class:`RunPlan` rather than re-derive
stage order independently.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from prml_vslam.methods.contracts import MethodId
from prml_vslam.methods.descriptors import BackendDescriptor
from prml_vslam.pipeline.contracts.plan import RunPlan, RunPlanStage
from prml_vslam.pipeline.contracts.request import RunRequest
from prml_vslam.pipeline.contracts.stages import StageAvailability, StageDefinition, StageKey
from prml_vslam.utils import BaseData, PathConfig, RunArtifactPaths

EnabledFn = Callable[[RunRequest], bool]
AvailabilityFn = Callable[[RunRequest, BackendDescriptor], StageAvailability]
OutputsFn = Callable[[RunRequest, RunArtifactPaths], list[Path]]


class _RegistryEntry(BaseData):
    definition: StageDefinition
    enabled_fn: EnabledFn | None = None
    availability_fn: AvailabilityFn
    outputs_fn: OutputsFn | None = None


class StageRegistry:
    """Collect stage metadata and compile deterministic run plans."""

    def __init__(self) -> None:
        self._entries: dict[StageKey, _RegistryEntry] = {}

    def register(
        self,
        definition: StageDefinition,
        availability_fn: AvailabilityFn,
        *,
        enabled_fn: EnabledFn | None = None,
        outputs_fn: OutputsFn | None = None,
    ) -> None:
        """Register one stage and the rules that make it plan-visible.

        Args:
            definition: Stable stage identity.
            availability_fn: Backend-aware availability decision.
            enabled_fn: Optional request gate that removes the stage entirely
                from the compiled plan when it evaluates to ``False``.
            outputs_fn: Optional canonical output-path builder used for plan
                previews and artifact ownership.
        """
        self._entries[definition.key] = _RegistryEntry(
            definition=definition,
            enabled_fn=enabled_fn,
            availability_fn=availability_fn,
            outputs_fn=outputs_fn,
        )

    def get(self, key: StageKey) -> StageDefinition:
        """Return the registered definition for one stage key."""
        return self._entries[key].definition

    def availability(self, key: StageKey, request: RunRequest, backend: BackendDescriptor) -> StageAvailability:
        """Return whether the stage is executable for one request/backend pair."""
        return self._entries[key].availability_fn(request, backend)

    def compile(self, *, request: RunRequest, backend: BackendDescriptor, path_config: PathConfig) -> RunPlan:
        """Compile one deterministic :class:`RunPlan` from registry entries.

        Planning is intentionally side-effect free: the registry decides stage
        order, availability, and expected outputs without opening sources or
        booting runtime actors.
        """
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
            outputs=[] if entry.outputs_fn is None else entry.outputs_fn(request, run_paths),
            available=availability.available,
            availability_reason=availability.reason,
        )

    @classmethod
    def default(cls) -> StageRegistry:
        """Build the repository-owned default stage vocabulary."""
        registry = cls()
        registry.register(
            StageDefinition(key=StageKey.INGEST),
            lambda _request, _backend: StageAvailability(available=True),
            outputs_fn=_ingest_outputs,
        )
        registry.register(
            StageDefinition(key=StageKey.SLAM),
            _slam_stage_availability,
            outputs_fn=_slam_outputs,
        )
        registry.register(
            StageDefinition(key=StageKey.TRAJECTORY_EVALUATION),
            _trajectory_stage_availability,
            enabled_fn=lambda request: request.benchmark.trajectory.enabled,
            outputs_fn=lambda _request, run_paths: [run_paths.trajectory_metrics_path],
        )
        registry.register(
            StageDefinition(key=StageKey.REFERENCE_RECONSTRUCTION),
            lambda _request, _backend: StageAvailability(
                available=False,
                reason="Reference reconstruction remains a planned placeholder in this refactor.",
            ),
            enabled_fn=lambda request: request.benchmark.reference.enabled,
            outputs_fn=lambda _request, run_paths: [run_paths.reference_cloud_path],
        )
        registry.register(
            StageDefinition(key=StageKey.CLOUD_EVALUATION),
            lambda _request, _backend: StageAvailability(
                available=False,
                reason="Dense-cloud evaluation remains a planned placeholder in this refactor.",
            ),
            enabled_fn=lambda request: request.benchmark.cloud.enabled,
            outputs_fn=lambda _request, run_paths: [run_paths.cloud_metrics_path],
        )
        registry.register(
            StageDefinition(key=StageKey.EFFICIENCY_EVALUATION),
            lambda _request, _backend: StageAvailability(
                available=False,
                reason="Efficiency evaluation remains a planned placeholder in this refactor.",
            ),
            enabled_fn=lambda request: request.benchmark.efficiency.enabled,
            outputs_fn=lambda _request, run_paths: [run_paths.efficiency_metrics_path],
        )
        registry.register(
            StageDefinition(key=StageKey.SUMMARY),
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


__all__ = ["StageRegistry"]
