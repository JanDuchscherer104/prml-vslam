"""Deterministic planning contracts for the pipeline.

This module owns the side-effect-free plan representation returned from
:meth:`prml_vslam.pipeline.config.RunConfig.compile_plan`. It captures what the
pipeline intends to execute before any runtime actor, backend wrapper, or
source stream is started.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field

from prml_vslam.utils import BaseData

from .mode import PipelineMode
from .stages import StageKey

SourceMetadataValue = str | int | float | bool | None


class PlannedSource(BaseData):
    """Compact source selection snapshot captured in the deterministic plan."""

    source_id: str
    frame_stride: int = 1
    target_fps: float | None = None
    expected_fps: float | None = None
    replay_mode: str | None = None
    sequence_id: str | None = None
    video_path: Path | None = None
    transport: str | None = None
    device_index: int | None = None
    device_address: str = ""
    normalize_video_orientation: bool = True
    metadata: dict[str, SourceMetadataValue] = Field(default_factory=dict)


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
    """Represent the deterministic plan compiled from one launch config.

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

    source: PlannedSource
    """Target source selection snapshot that the run plan was built from."""

    stages: list[RunPlanStage] = Field(default_factory=list)
    """Ordered execution stages for the benchmark run."""

    config_warnings: list[str] = Field(default_factory=list)
    """Lenient config diagnostics collected while loading TOML."""

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


__all__ = ["PlannedSource", "RunPlan", "RunPlanStage"]
