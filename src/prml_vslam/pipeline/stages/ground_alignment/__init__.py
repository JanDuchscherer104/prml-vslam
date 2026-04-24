"""Ground-alignment stage runtime package."""

from __future__ import annotations

from typing import Any

__all__ = [
    "GroundAlignmentRuntime",
    "GroundAlignmentRuntimeInput",
    "GroundAlignmentStageBinding",
    "GroundAlignmentStageConfig",
]


def __getattr__(name: str) -> Any:
    if name == "GroundAlignmentStageBinding":
        from .binding import GroundAlignmentStageBinding

        return GroundAlignmentStageBinding
    if name == "GroundAlignmentStageConfig":
        from .config import GroundAlignmentStageConfig

        return GroundAlignmentStageConfig
    if name == "GroundAlignmentRuntimeInput":
        from .contracts import GroundAlignmentRuntimeInput

        return GroundAlignmentRuntimeInput
    if name == "GroundAlignmentRuntime":
        from .runtime import GroundAlignmentRuntime

        return GroundAlignmentRuntime
    raise AttributeError(name)
