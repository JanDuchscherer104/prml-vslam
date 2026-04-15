"""Typed contracts for external VSLAM method adapters."""

from __future__ import annotations

from enum import StrEnum

from pydantic import ConfigDict

from prml_vslam.utils import BaseConfig


class MethodId(StrEnum):
    """Supported external VSLAM backends."""

    VISTA = "vista"
    MAST3R = "mast3r"
    MOCK = "mock"

    @property
    def display_name(self) -> str:
        """Return the upstream method name shown to users."""
        match self:
            case MethodId.VISTA:
                return "ViSTA-SLAM"
            case MethodId.MAST3R:
                return "MASt3R-SLAM"
            case MethodId.MOCK:
                return "Mock Preview"


class SlamOutputPolicy(BaseConfig):
    """Method-owned output policy controls."""

    emit_dense_points: bool = True
    """Whether the backend should materialize a dense point cloud artifact."""

    emit_sparse_points: bool = True
    """Whether the backend should materialize sparse geometry artifacts."""


class SlamBackendConfig(BaseConfig):
    """Method-owned backend controls."""

    model_config = ConfigDict(extra="forbid")

    max_frames: int | None = None
    """Optional frame cap used for debugging or short smoke runs."""


__all__ = ["MethodId", "SlamBackendConfig", "SlamOutputPolicy"]
