"""Pipeline provenance contracts."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import Field

from prml_vslam.utils import BaseData

from .plan import RunPlanStageId


class StageExecutionStatus(StrEnum):
    """Execution status stored in one stage manifest."""

    HIT = "hit"
    RAN = "ran"
    FAILED = "failed"


class StageManifest(BaseData):
    """Cache and provenance record for one executed stage."""

    stage_id: RunPlanStageId
    """Stage identity."""

    config_hash: str
    """Fingerprint of the relevant stage configuration."""

    input_fingerprint: str
    """Fingerprint of the stage inputs."""

    output_paths: dict[str, Path] = Field(default_factory=dict)
    """Named materialized outputs produced or reused by the stage."""

    status: StageExecutionStatus
    """Whether the stage was reused, executed, or failed."""

    @staticmethod
    def table_rows(stage_manifests: list[StageManifest]) -> list[dict[str, str]]:
        """Return compact tabular rows for manifest summaries."""
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
    """Final persisted outcome for one benchmark run."""

    run_id: str
    """Stable run identifier."""

    artifact_root: Path
    """Root directory that owns all run artifacts."""

    stage_status: dict[RunPlanStageId, StageExecutionStatus] = Field(default_factory=dict)
    """Final status per stage."""


__all__ = ["RunSummary", "StageExecutionStatus", "StageManifest"]
