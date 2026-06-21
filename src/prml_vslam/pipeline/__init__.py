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
    "SweepConfig",
    "SweepRunItem",
    "build_run_config_from_sweep_item",
    "expand_sweep",
    "load_sweep_config",
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
    if name == "ArtifactRef":
        from prml_vslam.interfaces.artifacts import ArtifactRef

        return ArtifactRef
    if name == "RunSummary":
        from .contracts import provenance

        return getattr(provenance, name)
    if name == "RunSnapshot":
        from .contracts.runtime import RunSnapshot

        return RunSnapshot
    if name == "StageKey":
        from .contracts.stages import StageKey

        return StageKey
    if name in {"SweepConfig", "SweepRunItem", "build_run_config_from_sweep_item", "expand_sweep", "load_sweep_config"}:
        from . import sweep as _sweep

        return getattr(_sweep, name)
    raise AttributeError(name)
