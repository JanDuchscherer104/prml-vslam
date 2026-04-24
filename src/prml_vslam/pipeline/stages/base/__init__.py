"""Generic stage runtime contract package."""

from __future__ import annotations

from typing import Any

__all__ = [
    "FailureFingerprint",
    "LifecycleStageRuntimeMixin",
    "PlanContext",
    "RuntimeBuildContext",
    "StageBinding",
    "StageInputContext",
    "StageResult",
    "StageRuntimeStatus",
    "StageRuntimeUpdate",
    "VisualizationItem",
]


def __getattr__(name: str) -> Any:
    if name in {"FailureFingerprint", "PlanContext", "RuntimeBuildContext", "StageBinding", "StageInputContext"}:
        from . import binding

        return getattr(binding, name)
    if name in {"StageResult", "StageRuntimeStatus", "StageRuntimeUpdate", "VisualizationItem"}:
        from . import contracts

        return getattr(contracts, name)
    if name == "LifecycleStageRuntimeMixin":
        from .runtime import LifecycleStageRuntimeMixin

        return LifecycleStageRuntimeMixin
    raise AttributeError(name)
