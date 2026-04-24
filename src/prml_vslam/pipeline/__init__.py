"""Public orchestration surface for the repository pipeline."""

from __future__ import annotations

from typing import Any

__all__ = [
    "ArtifactRef",
    "PipelineMode",
    "RunConfig",
    "RunEvent",
    "RunPlan",
    "RunService",
    "RunSnapshot",
    "RunSummary",
    "StageKey",
]


def __getattr__(name: str) -> Any:
    if name == "RunConfig":
        from .config import RunConfig

        return RunConfig
    if name == "RunService":
        from .run_service import RunService

        return RunService
    if name == "RunEvent":
        from .contracts.events import RunEvent

        return RunEvent
    if name == "PipelineMode":
        from .contracts.mode import PipelineMode

        return PipelineMode
    if name == "RunPlan":
        from .contracts.plan import RunPlan

        return RunPlan
    if name in {"ArtifactRef", "RunSummary"}:
        from .contracts import provenance

        return getattr(provenance, name)
    if name == "RunSnapshot":
        from .contracts.runtime import RunSnapshot

        return RunSnapshot
    if name == "StageKey":
        from .contracts.stages import StageKey

        return StageKey
    raise AttributeError(name)
