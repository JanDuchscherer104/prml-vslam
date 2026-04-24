"""Ground-alignment pipeline stage integration."""

from __future__ import annotations

from typing import Any

from prml_vslam.alignment.stage.config import GroundAlignmentStageConfig
from prml_vslam.alignment.stage.contracts import GroundAlignmentRuntimeInput

__all__ = ["GroundAlignmentRuntime", "GroundAlignmentRuntimeInput", "GroundAlignmentStageConfig"]


def __getattr__(name: str) -> Any:
    if name == "GroundAlignmentRuntime":
        from prml_vslam.alignment.stage.runtime import GroundAlignmentRuntime

        return GroundAlignmentRuntime
    raise AttributeError(name)
