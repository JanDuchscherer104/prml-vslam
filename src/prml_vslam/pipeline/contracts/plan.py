"""Pipeline planning contracts."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field

from prml_vslam.methods.contracts import MethodId
from prml_vslam.utils import BaseData

from .request import PipelineMode, SourceSpec
from .stages import StageExecutorKind, StageKey


class RunPlanStage(BaseData):
    """One typed stage in a benchmark run plan."""

    key: StageKey
    """Stable identifier for the stage."""

    title: str
    """Short human-readable stage title."""

    summary: str
    """Short description of the stage intent."""

    outputs: list[Path] = Field(default_factory=list)
    """Expected artifact paths for the stage."""

    executor_kind: StageExecutorKind
    """Executor kind used by the active backend/runtime."""

    available: bool = True
    """Whether the selected backend can execute the stage."""

    availability_reason: str | None = None
    """Why the stage is unavailable, when it is merely a placeholder."""

    failure_modes: list[str] = Field(default_factory=list)
    """Declared terminal failure modes for the stage."""


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
                "Id": stage.key.value,
                "Available": "yes" if stage.available else "no",
                "Outputs": ", ".join(path.name for path in stage.outputs),
            }
            for stage in self.stages
        ]


__all__ = ["RunPlan", "RunPlanStage"]
