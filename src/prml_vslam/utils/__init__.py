"""Shared utility surfaces for the project."""

from __future__ import annotations

from .base_config import BaseConfig, FactoryConfig
from .base_data import BaseData
from .console import Console, caller_namespace, get_console
from .geometry import load_point_cloud_ply
from .json_types import JsonObject, JsonScalar, JsonValue
from .path_config import PathConfig, RunArtifactPaths, get_path_config
from .serialization import hash_path, stable_hash, write_json
from .telemetry import FPS_WINDOW, rolling_fps

__all__ = [
    "BaseConfig",
    "BaseData",
    "Console",
    "FactoryConfig",
    "FPS_WINDOW",
    "hash_path",
    "JsonObject",
    "JsonScalar",
    "JsonValue",
    "load_point_cloud_ply",
    "PathConfig",
    "RunArtifactPaths",
    "caller_namespace",
    "get_console",
    "get_path_config",
    "rolling_fps",
    "stable_hash",
    "write_json",
]
