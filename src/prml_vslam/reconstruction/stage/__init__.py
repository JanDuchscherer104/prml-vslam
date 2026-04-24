"""Reconstruction pipeline stage integration."""

from __future__ import annotations

from typing import Any

from prml_vslam.reconstruction.stage.config import ReconstructionBackend, ReconstructionStageConfig
from prml_vslam.reconstruction.stage.contracts import ReconstructionRuntimeInput

__all__ = [
    "ReconstructionBackend",
    "ReconstructionRuntime",
    "ReconstructionRuntimeInput",
    "ReconstructionStageConfig",
]


def __getattr__(name: str) -> Any:
    if name == "ReconstructionRuntime":
        from prml_vslam.reconstruction.stage.runtime import ReconstructionRuntime

        return ReconstructionRuntime
    raise AttributeError(name)
