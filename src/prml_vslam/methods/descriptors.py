"""Explicit backend descriptors and capability contracts."""

from __future__ import annotations

from pydantic import Field

from prml_vslam.pipeline.contracts.transport import TransportModel


class BackendCapabilities(TransportModel):
    """Capability surface exposed by one backend."""

    offline: bool
    streaming: bool
    dense_points: bool
    live_preview: bool
    native_visualization: bool
    trajectory_benchmark_support: bool


class BackendDescriptor(TransportModel):
    """Descriptive metadata for one backend kind."""

    key: str
    display_name: str
    capabilities: BackendCapabilities
    default_resources: dict[str, float] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


__all__ = ["BackendCapabilities", "BackendDescriptor"]
