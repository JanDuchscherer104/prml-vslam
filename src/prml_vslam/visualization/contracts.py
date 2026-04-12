"""Thin visualization-policy contracts."""

from __future__ import annotations

from pydantic import Field

from prml_vslam.pipeline.contracts.artifacts import ArtifactRef
from prml_vslam.utils import BaseConfig, BaseData


class VisualizationConfig(BaseConfig):
    """Viewer-export policy attached to one run request."""

    connect_live_viewer: bool = False
    """Whether streaming runs should attach a live gRPC viewer sink."""

    grpc_url: str = "rerun+http://127.0.0.1:9876/proxy"
    """Rerun gRPC endpoint used when `connect_live_viewer` is enabled."""

    preserve_native_rerun: bool = True
    """Whether native upstream `.rrd` recordings should be preserved as method artifacts."""


class VisualizationArtifacts(BaseData):
    """Viewer artifacts associated with one run."""

    native_rerun_rrd: ArtifactRef | None = None
    """Optional preserved recorded-session `.rrd` from an upstream backend."""

    native_output_dir: ArtifactRef | None = None
    """Optional preserved backend-native output directory."""

    extras: dict[str, ArtifactRef] = Field(default_factory=dict)
    """Optional additional viewer artifacts owned by the visualization layer."""


__all__ = ["VisualizationArtifacts", "VisualizationConfig"]
