"""Pipeline planning contracts."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import Field

from prml_vslam.methods.contracts import MethodId
from prml_vslam.utils import BaseData

from .request import PipelineMode, SourceSpec


class RunPlanStageId(StrEnum):
    """Canonical stage identifiers in the benchmark planner."""

    INGEST = "ingest"
    SLAM = "slam"
    REFERENCE_RECONSTRUCTION = "reference_reconstruction"
    TRAJECTORY_EVALUATION = "trajectory_evaluation"
    CLOUD_EVALUATION = "cloud_evaluation"
    EFFICIENCY_EVALUATION = "efficiency_evaluation"
    SUMMARY = "summary"


class RunPlanStage(BaseData):
    """One typed stage in a benchmark run plan."""

    id: RunPlanStageId
    """Stable identifier for the stage."""

    title: str
    """Short human-readable stage title."""

    summary: str
    """Short description of the stage intent."""

    outputs: list[Path] = Field(default_factory=list)
    """Expected artifact paths for the stage."""


class RunPlan(BaseData):
    """Planner output returned to the CLI or UI layer."""

    run_id: str
    """Stable filesystem-safe run identifier."""

    mode: PipelineMode
    """Selected pipeline mode."""

    method: MethodId
    """External backend chosen for the run."""

    artifact_root: Path
    """Root directory for all run artifacts."""

    source: SourceSpec
    """Source definition that the run plan was built from."""

    stages: list[RunPlanStage] = Field(default_factory=list)
    """Ordered execution stages for the benchmark run."""

    def stage_rows(self) -> list[dict[str, str]]:
        """Return compact tabular rows for plan summaries."""
        return [
            {
                "Stage": stage.title,
                "Id": stage.id.value,
                "Outputs": ", ".join(path.name for path in stage.outputs),
            }
            for stage in self.stages
        ]


__all__ = ["RunPlan", "RunPlanStage", "RunPlanStageId"]
