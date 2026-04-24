"""Generic stage binding contracts.

Bindings are the stage-owned bridge between declarative config, deterministic
planning, runtime construction, input DTO construction, and failure
fingerprints. Pipeline orchestration iterates bindings; it does not switch on
stage keys for stage-specific behavior.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from prml_vslam.methods.descriptors import BackendDescriptor
from prml_vslam.pipeline.contracts.mode import PipelineMode
from prml_vslam.pipeline.contracts.plan import RunPlan
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.runner import StageResultStore
from prml_vslam.pipeline.stages.base.config import StageConfig
from prml_vslam.pipeline.stages.base.protocols import BaseStageRuntime
from prml_vslam.pipeline.stages.base.proxy import DeploymentKind, RuntimeCapability
from prml_vslam.protocols.source import OfflineSequenceSource
from prml_vslam.utils import BaseConfig, BaseData, PathConfig, RunArtifactPaths


@dataclass(frozen=True, slots=True)
class PlanContext:
    """Inputs available while compiling a deterministic run plan."""

    run_config: BaseConfig
    path_config: PathConfig
    run_paths: RunArtifactPaths
    backend: BackendDescriptor | None = None


@dataclass(frozen=True, slots=True)
class RuntimeBuildContext:
    """Inputs available while lazily constructing one stage runtime."""

    run_config: BaseConfig
    plan: RunPlan
    path_config: PathConfig
    source: OfflineSequenceSource | None = None


@dataclass(frozen=True, slots=True)
class StageInputContext:
    """Inputs available while constructing one runtime-boundary DTO."""

    run_config: BaseConfig
    plan: RunPlan
    path_config: PathConfig
    run_paths: RunArtifactPaths
    backend_descriptor: BackendDescriptor
    results: StageResultStore


@dataclass(frozen=True, slots=True)
class FailureFingerprint:
    """Stable hash inputs for generic stage failure provenance."""

    config_payload: BaseConfig | BaseData | dict[str, str | int | float | bool | None] | list[BaseData] | None
    input_payload: BaseConfig | BaseData | dict[str, str | int | float | bool | None] | list[BaseData] | None


class StageBinding:
    """Base class for one statically ordered stage binding."""

    key: StageKey
    section_name: str
    deployment_default: DeploymentKind = "in_process"

    def stage_config(self, run_config: BaseConfig) -> StageConfig:
        """Return this binding's stage section from a run config."""
        stages = run_config.stages
        return getattr(stages, self.section_name)

    def enabled(self, run_config: BaseConfig) -> bool:
        """Return whether the stage is requested by its config section."""
        return self.stage_config(run_config).enabled

    def planned_outputs(self, context: PlanContext) -> list[Path]:
        """Return deterministic output paths declared by this stage."""
        del context
        return []

    def availability(self, context: PlanContext) -> tuple[bool, str | None]:
        """Return whether the configured stage can run."""
        del context
        return True, None

    def runtime_factory(self, context: RuntimeBuildContext) -> Callable[[], BaseStageRuntime] | None:
        """Return a lazy runtime factory for this stage, or ``None`` for diagnostics."""
        del context
        return None

    def runtime_capabilities(self, mode: PipelineMode) -> frozenset[RuntimeCapability]:
        """Return runtime capabilities advertised by this stage runtime."""
        del mode
        return frozenset({RuntimeCapability.OFFLINE})

    def build_offline_input(self, context: StageInputContext) -> BaseData:
        """Build the narrow DTO consumed by this stage runtime."""
        raise RuntimeError(f"No offline input builder for stage '{self.key.value}'.")

    def build_streaming_start_input(self, context: StageInputContext) -> BaseData:
        """Build the narrow DTO used to start a streaming runtime."""
        del context
        raise RuntimeError(f"No streaming input builder for stage '{self.key.value}'.")

    def failure_fingerprint(self, context: StageInputContext) -> FailureFingerprint:
        """Return stable config and input payloads for failure provenance."""
        return FailureFingerprint(
            config_payload={"stage_key": self.key.value},
            input_payload={"run_id": context.plan.run_id, "stage_key": self.key.value},
        )


__all__ = [
    "FailureFingerprint",
    "PlanContext",
    "RuntimeBuildContext",
    "StageBinding",
    "StageInputContext",
]
