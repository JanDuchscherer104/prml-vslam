"""Summary stage runtime package."""

from __future__ import annotations

from typing import Any

__all__ = ["SummaryRuntime", "SummaryRuntimeInput", "SummaryStageBinding", "SummaryStageConfig"]


def __getattr__(name: str) -> Any:
    if name == "SummaryStageBinding":
        from .binding import SummaryStageBinding

        return SummaryStageBinding
    if name == "SummaryStageConfig":
        from .config import SummaryStageConfig

        return SummaryStageConfig
    if name == "SummaryRuntimeInput":
        from .contracts import SummaryRuntimeInput

        return SummaryRuntimeInput
    if name == "SummaryRuntime":
        from .runtime import SummaryRuntime

        return SummaryRuntime
    raise AttributeError(name)
