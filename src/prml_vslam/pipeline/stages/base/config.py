"""Declarative base config contracts for pipeline stage planning.

This module owns generic stage policy config only. These models validate and
describe planning, telemetry, placement, cleanup, and failure-provenance policy;
they do not construct runtimes, open sources, allocate Ray resources, or create
observer sinks.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import ConfigDict, Field, field_validator

from prml_vslam.interfaces.artifacts import ArtifactRef
from prml_vslam.pipeline.contracts.events import StageOutcome
from prml_vslam.pipeline.contracts.plan import RunPlan
from prml_vslam.pipeline.contracts.provenance import StageStatus
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.protocols.source import OfflineSequenceSource
from prml_vslam.utils import BaseConfig, BaseData, JsonScalar, PathConfig, RunArtifactPaths

if TYPE_CHECKING:
    from collections.abc import Callable

    from prml_vslam.methods.stage.config import SlamBackendConfig
    from prml_vslam.pipeline.config import RunConfig
    from prml_vslam.pipeline.runner import StageResultStore
    from prml_vslam.pipeline.stages.base.protocols import BaseStageRuntime


# TODO: streamline (collapse ?) handling of all context classes! This also includes StageExecutionContext from src/prml_vslam/pipeline/execution_context.py. (from this file StagePlanContext, StageRuntimeBuildContext, StageInputContext! How many different context types do we really need?)
@dataclass(frozen=True, slots=True)
class StagePlanContext:
    """Inputs available while compiling a deterministic run plan."""

    run_config: RunConfig
    path_config: PathConfig
    run_paths: RunArtifactPaths
    backend: SlamBackendConfig | None = None


@dataclass(frozen=True, slots=True)
class StageRuntimeBuildContext:
    """Inputs available while lazily constructing one stage runtime."""

    run_config: RunConfig
    plan: RunPlan
    path_config: PathConfig
    source: OfflineSequenceSource | None = None


@dataclass(frozen=True, slots=True)
class StageInputContext:
    """Inputs available while constructing one runtime-boundary DTO."""

    run_config: RunConfig
    plan: RunPlan
    path_config: PathConfig
    run_paths: RunArtifactPaths
    results: StageResultStore


@dataclass(frozen=True, slots=True)
class FailureFingerprint:
    """Stable hash inputs for generic stage failure provenance."""

    config_payload: BaseConfig | BaseData | dict[str, JsonScalar] | list[BaseData] | None
    input_payload: BaseConfig | BaseData | dict[str, JsonScalar] | list[BaseData] | None


class StageConfig(BaseConfig):
    """Base declarative policy shared by target stage config sections."""

    model_config = ConfigDict(extra="ignore")

    stage_key: StageKey | None = None
    """Canonical stage key represented by this section."""

    enabled: bool = True
    """Whether this stage section is requested by the target config."""

    num_cpus: float | None = Field(default=None, ge=0.0)
    """Requested CPU count, when explicitly constrained."""

    num_gpus: float | None = Field(default=None, ge=0.0)
    """Requested GPU count, when explicitly constrained."""

    memory_bytes: int | None = Field(default=None, ge=0)
    """Requested memory in bytes, when explicitly constrained."""

    custom_resources: dict[str, float] = Field(default_factory=dict)
    """Substrate-specific custom resource quantities keyed by resource name."""

    node_ip_address: str | None = None
    """Preferred node IP address, when a stage needs node locality."""

    node_labels: dict[str, str] = Field(default_factory=dict)
    """Preferred node labels for schedulers that support label matching."""

    affinity: str | None = None
    """Optional affinity label interpreted only by runtime placement adapters."""

    runtime_env: dict[str, JsonScalar] = Field(default_factory=dict)
    """Small runtime-environment hints kept below runtime construction."""

    emit_progress: bool = True
    """Whether the runtime should emit coarse progress status when available."""

    emit_queue_metrics: bool = False
    """Whether runtime-owned queue or backlog metrics should be emitted."""

    emit_latency_metrics: bool = False
    """Whether runtime-measured latency metrics should be emitted."""

    emit_throughput_metrics: bool = False
    """Whether runtime throughput or FPS metrics should be emitted."""

    sampling_interval_ms: int = Field(default=1000, ge=1)
    """Minimum status sampling interval in milliseconds."""

    cleanup_artifact_keys: list[str] = Field(default_factory=list)
    """Stage artifact-key selectors to prune after the run epilogue."""

    cleanup_on_completed: bool = True
    """Whether cleanup applies after a completed run."""

    cleanup_on_failed: bool = False
    """Whether cleanup applies after a failed run."""

    cleanup_on_stopped: bool = False
    """Whether cleanup applies after a stopped run."""

    cache_enabled: bool = False
    """Reserved cache switch; active content-addressed cache execution is deferred."""

    @field_validator("custom_resources")
    @classmethod
    def validate_custom_resources(cls, value: dict[str, float]) -> dict[str, float]:
        """Reject negative custom resource quantities."""
        negative = [name for name, quantity in value.items() if quantity < 0.0]
        if negative:
            raise ValueError(f"Custom resource quantities must be non-negative: {', '.join(sorted(negative))}.")
        return value

    @field_validator("cleanup_artifact_keys")
    @classmethod
    def validate_artifact_key_selectors(cls, value: list[str]) -> list[str]:
        """Allow only exact artifact keys or safe ``prefix:*`` selectors."""
        invalid = [selector for selector in value if not _valid_artifact_selector(selector)]
        if invalid:
            raise ValueError(f"Invalid cleanup artifact selector(s): {', '.join(invalid)}.")
        return value

    def declared_outputs(self, output_paths: Sequence[Path] = ()) -> list[Path]:
        """Return the declared output paths for a generic stage section."""
        return list(output_paths)

    def planned_outputs(self, context: StagePlanContext) -> list[Path]:
        """Return deterministic output paths declared by this stage."""
        del context
        return []

    def availability(self, context: StagePlanContext) -> tuple[bool, str | None]:
        """Return whether the configured stage can run."""
        del context
        return True, None

    def runtime_factory(self, context: StageRuntimeBuildContext) -> Callable[[], BaseStageRuntime] | None:
        """Return a lazy runtime factory for this stage, or ``None`` for diagnostics."""
        del context
        return None

    def build_offline_input(self, context: StageInputContext) -> BaseData:
        """Build the narrow DTO consumed by this stage runtime."""
        raise RuntimeError(f"No offline input builder for stage '{self.stage_key}'.")

    def build_streaming_start_input(self, context: StageInputContext) -> BaseData:
        """Build the narrow DTO used to start a streaming runtime."""
        del context
        raise RuntimeError(f"No streaming input builder for stage '{self.stage_key}'.")

    def failure_fingerprint(self, context: StageInputContext) -> FailureFingerprint:
        """Return stable config and input payloads for failure provenance."""
        stage_key = self.stage_key.value if self.stage_key is not None else "unknown"
        return FailureFingerprint(
            config_payload={"stage_key": stage_key},
            input_payload={"run_id": context.plan.run_id, "stage_key": stage_key},
        )

    def failure_outcome(
        self,
        *,
        error_message: str,
        config_hash: str,
        input_fingerprint: str,
        artifacts: dict[str, ArtifactRef] | None = None,
    ) -> StageOutcome:
        """Build a failed :class:`StageOutcome` using this stage's identity."""
        if self.stage_key is None:
            raise ValueError("StageConfig.failure_outcome() requires `stage_key`.")
        return StageOutcome(
            stage_key=self.stage_key,
            status=StageStatus.FAILED,
            config_hash=config_hash,
            input_fingerprint=input_fingerprint,
            artifacts={} if artifacts is None else artifacts,
            error_message=error_message,
        )


def _valid_artifact_selector(selector: str) -> bool:
    if not selector:
        return False
    if selector in {".", ".."} or "/" in selector or "\\" in selector:
        return False
    if any(token in selector for token in ("?", "[", "]")):
        return False
    if "*" not in selector:
        return ":" not in selector
    if not selector.endswith(":*") or selector.count("*") != 1:
        return False
    prefix = selector[:-2]
    return bool(prefix) and ":" not in prefix


__all__ = [
    "FailureFingerprint",
    "StageConfig",
    "StageInputContext",
    "StagePlanContext",
    "StageRuntimeBuildContext",
]
