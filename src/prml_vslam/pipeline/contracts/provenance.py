"""Persisted provenance contracts for completed pipeline runs.

This module owns the durable, post-execution view of what happened during a
run. In pipeline terms, provenance means the stable record of stage status,
input and config fingerprints, and named outputs that survived beyond the live
:class:`prml_vslam.pipeline.contracts.events.RunEvent` stream.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import Field

from prml_vslam.interfaces.artifacts import ArtifactRef
from prml_vslam.utils import BaseData

from .stages import StageKey


class StageStatus(StrEnum):
    """Shared stage-status vocabulary used in runtime and persisted views."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


class StageManifest(BaseData):
    """Persist the durable record for one executed or skipped stage.

    Each manifest ties one :class:`prml_vslam.pipeline.contracts.stages.StageKey`
    to the configuration and input fingerprints that produced its named output
    artifacts. This is the stage-level durable counterpart to transient runtime
    events such as :class:`prml_vslam.pipeline.contracts.events.StageCompleted`.
    """

    stage_id: StageKey
    """Stage identity."""

    config_hash: str
    """Fingerprint of the relevant stage configuration."""

    input_fingerprint: str
    """Fingerprint of the stage inputs."""

    output_paths: dict[str, Path] = Field(default_factory=dict)
    """Named materialized outputs produced or reused by the stage."""

    status: StageStatus
    """Final stage status for this manifest."""

    @staticmethod
    def table_rows(stage_manifests: list[StageManifest]) -> list[dict[str, str]]:
        """Return compact rows suitable for run summaries and review surfaces."""
        return [
            {
                "Stage": manifest.stage_id.value,
                "Status": manifest.status.value,
                "Config Hash": manifest.config_hash,
                "Outputs": ", ".join(path.name for path in manifest.output_paths.values()),
            }
            for manifest in stage_manifests
        ]


class StageRuntimeSummary(BaseData):
    """Persist a compact terminal runtime snapshot for one stage.

    The summary is a provenance-owned projection of the final runtime status.
    It intentionally duplicates only scalar fields that are useful after a run
    completes, avoiding a dependency from provenance contracts back to live
    stage-runtime DTOs.
    """

    stage_key: StageKey
    """Stage whose runtime produced this terminal status."""

    lifecycle_state: StageStatus
    """Final lifecycle state reported by the runtime."""

    progress_message: str = ""
    """Human-readable terminal progress detail."""

    completed_steps: int | None = Field(default=None, ge=0)
    """Completed progress units when the runtime measured bounded work."""

    total_steps: int | None = Field(default=None, ge=0)
    """Total progress units when the runtime measured bounded work."""

    progress_unit: str | None = None
    """Name of the progress unit."""

    submitted_count: int = Field(default=0, ge=0)
    """Number of work items submitted to the runtime or proxy."""

    completed_count: int = Field(default=0, ge=0)
    """Number of submitted work items completed by the runtime or proxy."""

    failed_count: int = Field(default=0, ge=0)
    """Number of submitted work items that failed."""

    processed_items: int = Field(default=0, ge=0)
    """Domain-neutral count of items processed by the runtime."""

    accepted_keyframes: int = Field(default=0, ge=0)
    """SLAM keyframes accepted into the pose graph."""

    fps: float | None = Field(default=None, ge=0.0)
    """Frame rate when measured by the runtime."""

    throughput: float | None = Field(default=None, ge=0.0)
    """Generic non-frame throughput when measured by the runtime."""

    throughput_unit: str | None = None
    """Unit label for :attr:`throughput`."""

    latency_ms: float | None = Field(default=None, ge=0.0)
    """Runtime-measured latency in milliseconds."""

    last_warning: str | None = None
    """Most recent non-fatal warning reported by the runtime."""

    last_error: str | None = None
    """Most recent error reported by the runtime."""

    updated_at_ns: int = Field(default=0, ge=0)
    """Terminal status update timestamp in nanoseconds."""


class RunSummary(BaseData):
    """Persist the final run-level status view derived from executed stages."""

    run_id: str
    """Stable run identifier."""

    artifact_root: Path
    """Root directory that owns all run artifacts."""

    stage_status: dict[StageKey, StageStatus] = Field(default_factory=dict)
    """Final status per stage."""

    stage_runtime_summaries: dict[StageKey, StageRuntimeSummary] = Field(default_factory=dict)
    """Final runtime metrics per stage when available."""


__all__ = ["ArtifactRef", "RunSummary", "StageManifest", "StageRuntimeSummary", "StageStatus"]
