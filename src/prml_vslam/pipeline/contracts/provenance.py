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


class RunSummary(BaseData):
    """Persist the final run-level status view derived from executed stages."""

    run_id: str
    """Stable run identifier."""

    artifact_root: Path
    """Root directory that owns all run artifacts."""

    stage_status: dict[StageKey, StageStatus] = Field(default_factory=dict)
    """Final status per stage."""


__all__ = ["RunSummary", "StageManifest", "StageStatus"]
