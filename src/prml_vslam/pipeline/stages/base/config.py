"""Declarative base config contracts for pipeline stage planning.

This module owns generic stage policy config only. These models validate and
describe planning, telemetry, placement, cleanup, and failure-provenance policy;
they do not construct runtimes, open sources, allocate Ray resources, or create
observer sinks.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from pydantic import ConfigDict, Field, field_validator

from prml_vslam.interfaces.slam import ArtifactRef
from prml_vslam.pipeline.contracts.events import StageOutcome
from prml_vslam.pipeline.contracts.provenance import StageStatus
from prml_vslam.pipeline.contracts.stages import StageAvailability, StageKey
from prml_vslam.utils import BaseConfig

JsonScalar = str | int | float | bool | None


class ResourceSpec(BaseConfig):
    """Describe substrate-neutral resources requested by one stage."""

    model_config = ConfigDict(extra="forbid")

    num_cpus: float | None = Field(default=None, ge=0.0)
    """Requested CPU count, when explicitly constrained."""

    num_gpus: float | None = Field(default=None, ge=0.0)
    """Requested GPU count, when explicitly constrained."""

    memory_bytes: int | None = Field(default=None, ge=0)
    """Requested memory in bytes, when explicitly constrained."""

    custom_resources: dict[str, float] = Field(default_factory=dict)
    """Substrate-specific custom resource quantities keyed by resource name."""

    @field_validator("custom_resources")
    @classmethod
    def validate_custom_resources(cls, value: dict[str, float]) -> dict[str, float]:
        """Reject negative custom resource quantities."""
        negative = [name for name, quantity in value.items() if quantity < 0.0]
        if negative:
            raise ValueError(f"Custom resource quantities must be non-negative: {', '.join(sorted(negative))}.")
        return value


class PlacementConstraint(BaseConfig):
    """Describe optional substrate-neutral placement preferences."""

    model_config = ConfigDict(extra="forbid")

    node_ip_address: str | None = None
    """Preferred node IP address, when a stage needs node locality."""

    node_labels: dict[str, str] = Field(default_factory=dict)
    """Preferred node labels for schedulers that support label matching."""

    affinity: str | None = None
    """Optional affinity label interpreted only by runtime placement adapters."""


class StageExecutionConfig(BaseConfig):
    """Collect stage execution policy without constructing runtime targets."""

    model_config = ConfigDict(extra="forbid")

    resources: ResourceSpec = Field(default_factory=ResourceSpec)
    """Substrate-neutral resource request for this stage."""

    placement: PlacementConstraint = Field(default_factory=PlacementConstraint)
    """Optional placement preference for this stage."""

    runtime_env: dict[str, JsonScalar] = Field(default_factory=dict)
    """Small runtime-environment hints kept below runtime construction."""


class StageTelemetryConfig(BaseConfig):
    """Configure which live status metrics a stage should emit."""

    model_config = ConfigDict(extra="forbid")

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


class StageCleanupPolicy(BaseConfig):
    """Describe stage artifact cleanup policy by artifact key."""

    model_config = ConfigDict(extra="forbid")

    artifact_keys: list[str] = Field(default_factory=list)
    """Stage artifact-key selectors to prune after the run epilogue."""

    on_completed: bool = True
    """Whether cleanup applies after a completed run."""

    on_failed: bool = False
    """Whether cleanup applies after a failed run."""

    on_stopped: bool = False
    """Whether cleanup applies after a stopped run."""

    @field_validator("artifact_keys")
    @classmethod
    def validate_artifact_key_selectors(cls, value: list[str]) -> list[str]:
        """Allow only exact artifact keys or safe ``prefix:*`` selectors."""
        invalid = [selector for selector in value if not _valid_artifact_selector(selector)]
        if invalid:
            raise ValueError(f"Invalid cleanup artifact selector(s): {', '.join(invalid)}.")
        return value


class StageConfig(BaseConfig):
    """Base declarative policy shared by target stage config sections."""

    model_config = ConfigDict(extra="forbid")

    # TODO(pipeline-refactor/WP-10): Switch this field to the target stage-key
    # vocabulary after current-key aliases are removed.
    stage_key: StageKey | None = None
    """Current executable stage key represented by this section during migration."""

    enabled: bool = True
    """Whether this stage section is requested by the target config."""

    execution: StageExecutionConfig = Field(default_factory=StageExecutionConfig)
    """Execution and placement policy for the stage."""

    telemetry: StageTelemetryConfig = Field(default_factory=StageTelemetryConfig)
    """Live status and telemetry emission policy for the stage."""

    cleanup: StageCleanupPolicy = Field(default_factory=StageCleanupPolicy)
    """Artifact cleanup policy keyed by stage artifact names."""

    def availability(self, reason: str | None = None) -> StageAvailability:
        """Return a planning availability view for this stage policy."""
        if reason is not None:
            return StageAvailability(available=False, reason=reason)
        if not self.enabled:
            return StageAvailability(available=False, reason="Stage is disabled.")
        return StageAvailability(available=True)

    def declared_outputs(self, output_paths: Sequence[Path] = ()) -> list[Path]:
        """Return the declared output paths for a generic stage section."""
        return list(output_paths)

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
    "PlacementConstraint",
    "ResourceSpec",
    "StageCleanupPolicy",
    "StageConfig",
    "StageExecutionConfig",
    "StageTelemetryConfig",
]
