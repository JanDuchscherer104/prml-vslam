"""Shared utility surfaces for the project."""

from __future__ import annotations

from importlib import import_module

from .base_config import BaseConfig
from .base_data import BaseData
from .console import Console, caller_namespace, get_console
from .path_config import PathConfig, RunArtifactPaths, get_path_config

__all__ = [
    "BaseConfig",
    "BaseData",
    "Console",
    "ImageSize",
    "load_point_cloud_ply",
    "PathConfig",
    "RunArtifactPaths",
    "caller_namespace",
    "get_console",
    "get_path_config",
]


def __getattr__(name: str) -> object:
    if name not in {"ImageSize", "load_point_cloud_ply"}:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(import_module(".geometry", __name__), name)
