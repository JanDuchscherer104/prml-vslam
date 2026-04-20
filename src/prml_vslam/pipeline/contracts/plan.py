"""Deterministic planning contracts for the pipeline.

This module owns the side-effect-free plan representation returned from
:meth:`prml_vslam.pipeline.contracts.request.RunRequest.build`. It captures what
the pipeline intends to execute before any runtime actor, backend wrapper, or
source stream is started.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field

from prml_vslam.utils import BaseData

from .request import PipelineMode, SourceSpec
from .stages import StageKey


class RunPlanStage(BaseData):
    """Describe one planned stage in the deterministic execution order."""

    key: StageKey
    """Stable identifier for the stage."""

    outputs: list[Path] = Field(default_factory=list)
    """Expected artifact paths for the stage."""

    available: bool = True
    """Whether the selected backend can execute the stage."""

    availability_reason: str | None = None
    """Why the stage is unavailable, when it is merely a placeholder."""


class RunPlan(BaseData):
    """Represent the deterministic plan compiled from one :class:`RunRequest`.

    The plan is the bridge between request-time policy and runtime execution.
    UI code, CLI code, and the backend layer all consume this DTO instead of
    re-deriving stage order or output ownership on their own.
    """

    run_id: str
    """Stable filesystem-safe run identifier."""

    mode: PipelineMode
    """Selected pipeline mode."""

    artifact_root: Path
    """Root directory for all run artifacts."""

    source: SourceSpec
    """Source definition that the run plan was built from."""

    stages: list[RunPlanStage] = Field(default_factory=list)
    """Ordered execution stages for the benchmark run."""

    def stage_rows(self) -> list[dict[str, str]]:
        """Return compact rows suitable for CLI or UI plan previews."""
        return [
            {
                "Stage": stage.key.label,
                "Id": stage.key.value,
                "Available": "yes" if stage.available else "no",
                "Outputs": ", ".join(path.name for path in stage.outputs),
            }
            for stage in self.stages
        ]


__all__ = ["RunPlan", "RunPlanStage"]
