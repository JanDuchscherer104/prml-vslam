"""SLAM stage runtime adapters and stage-local helpers."""

from __future__ import annotations

from typing import Any

__all__ = [
    "BackendConfig",
    "Mast3rSlamBackendConfig",
    "MethodId",
    "MockSlamBackendConfig",
    "SlamBackendConfig",
    "SlamFrameInput",
    "SlamOfflineInput",
    "SlamOutputPolicy",
    "SlamStageBinding",
    "SlamStageConfig",
    "SlamStageRuntime",
    "SlamStreamingStartInput",
    "SlamVisualizationAdapter",
    "VistaSlamBackendConfig",
]


def __getattr__(name: str) -> Any:
    if name in {
        "BackendConfig",
        "Mast3rSlamBackendConfig",
        "MethodId",
        "MockSlamBackendConfig",
        "SlamBackendConfig",
        "SlamOutputPolicy",
        "SlamStageConfig",
        "VistaSlamBackendConfig",
    }:
        from . import config

        return getattr(config, name)
    if name == "SlamStageBinding":
        from .binding import SlamStageBinding

        return SlamStageBinding
    if name in {"SlamFrameInput", "SlamOfflineInput", "SlamStreamingStartInput"}:
        from . import contracts

        return getattr(contracts, name)
    if name == "SlamStageRuntime":
        from .runtime import SlamStageRuntime

        return SlamStageRuntime
    if name == "SlamVisualizationAdapter":
        from .visualization import SlamVisualizationAdapter

        return SlamVisualizationAdapter
    raise AttributeError(name)
