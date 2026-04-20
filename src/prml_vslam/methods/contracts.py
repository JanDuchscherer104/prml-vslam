"""Typed contracts for external VSLAM method adapters.

This module owns the backend identifiers and method-owned runtime/output policy
that wrapper implementations share. It does not define pipeline planning or
artifact layout; instead it describes the knobs and capabilities that
:mod:`prml_vslam.pipeline` can rely on when selecting and executing a method.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import ConfigDict

from prml_vslam.utils import BaseConfig


class MethodId(StrEnum):
    """Name the external or repository-local backends supported by the package."""

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
    """Describe which optional geometry surfaces a backend should materialize.

    These flags shape the contents of :class:`prml_vslam.pipeline.SlamArtifacts`
    without changing stage order or pipeline semantics.
    """

    emit_dense_points: bool = True
    """Whether the backend should materialize a dense point cloud artifact."""

    emit_sparse_points: bool = True
    """Whether the backend should materialize sparse geometry artifacts."""


class SlamBackendConfig(BaseConfig):
    """Provide the method-owned runtime contract shared by backend configs.

    Concrete configs implement the capabilities and factory behavior that the
    rest of the package queries before runtime execution begins.
    """

    model_config = ConfigDict(extra="forbid")

    max_frames: int | None = None
    """Optional frame cap used for debugging or short smoke runs."""

    @property
    def display_name(self) -> str:
        """Return the user-facing backend label used across planning and UI surfaces."""
        return self.method_id.display_name

    @property
    def supports_offline(self) -> bool:
        """Whether the backend supports offline execution."""
        raise NotImplementedError

    @property
    def supports_streaming(self) -> bool:
        """Whether the backend supports streaming execution."""
        raise NotImplementedError

    @property
    def supports_dense_points(self) -> bool:
        """Whether the backend can expose point-cloud outputs."""
        raise NotImplementedError

    @property
    def supports_live_preview(self) -> bool:
        """Whether the backend can emit live preview payloads."""
        raise NotImplementedError

    @property
    def supports_native_visualization(self) -> bool:
        """Whether the backend may emit native visualization artifacts."""
        raise NotImplementedError

    @property
    def supports_trajectory_benchmark(self) -> bool:
        """Whether the backend supports repository trajectory evaluation."""
        raise NotImplementedError

    @property
    def default_resources(self) -> dict[str, float]:
        """Return backend-owned default Ray resource hints."""
        return {}

    @property
    def notes(self) -> list[str]:
        """Return backend-specific planning notes surfaced to callers when relevant."""
        return []


__all__ = ["MethodId", "SlamBackendConfig", "SlamOutputPolicy"]
