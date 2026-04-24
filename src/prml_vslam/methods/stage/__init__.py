"""SLAM pipeline stage integration owned by the methods package."""

from __future__ import annotations

from typing import Any

from prml_vslam.methods.stage.config import (
    BackendConfig,
    BackendConfigValue,
    Mast3rSlamBackendConfig,
    MethodId,
    SlamBackendConfig,
    SlamOutputPolicy,
    SlamStageConfig,
    VistaSlamBackendConfig,
    build_slam_backend_config,
)
from prml_vslam.methods.stage.contracts import SlamOfflineInput, SlamStreamingStartInput

__all__ = [
    "BackendConfig",
    "BackendConfigValue",
    "Mast3rSlamBackendConfig",
    "MethodId",
    "SlamBackendConfig",
    "SlamOfflineInput",
    "SlamOutputPolicy",
    "SlamStageConfig",
    "SlamStageRuntime",
    "SlamStreamingStartInput",
    "VistaSlamBackendConfig",
    "build_slam_backend_config",
]


def __getattr__(name: str) -> Any:
    if name == "SlamStageRuntime":
        from prml_vslam.methods.stage.runtime import SlamStageRuntime

        return SlamStageRuntime
    raise AttributeError(name)
