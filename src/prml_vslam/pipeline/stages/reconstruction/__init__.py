"""Reconstruction stage runtime package."""

from __future__ import annotations

from typing import Any

__all__ = [
    "Open3dTsdfReconstructionConfig",
    "ReconstructionBackend",
    "ReconstructionBackendConfig",
    "ReconstructionId",
    "ReconstructionRuntime",
    "ReconstructionRuntimeInput",
    "ReconstructionStageBinding",
    "ReconstructionStageConfig",
    "ReconstructionVisualizationAdapter",
]


def __getattr__(name: str) -> Any:
    if name in {
        "Open3dTsdfReconstructionConfig",
        "ReconstructionBackend",
        "ReconstructionBackendConfig",
        "ReconstructionId",
        "ReconstructionStageConfig",
    }:
        from . import config

        return getattr(config, name)
    if name == "ReconstructionStageBinding":
        from .binding import ReconstructionStageBinding

        return ReconstructionStageBinding
    if name == "ReconstructionRuntimeInput":
        from .contracts import ReconstructionRuntimeInput

        return ReconstructionRuntimeInput
    if name == "ReconstructionRuntime":
        from .runtime import ReconstructionRuntime

        return ReconstructionRuntime
    if name == "ReconstructionVisualizationAdapter":
        from .visualization import ReconstructionVisualizationAdapter

        return ReconstructionVisualizationAdapter
    raise AttributeError(name)
