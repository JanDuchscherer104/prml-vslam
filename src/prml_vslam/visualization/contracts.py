"""Thin visualization-policy contracts."""

from __future__ import annotations

from prml_vslam.utils import BaseConfig


class VisualizationConfig(BaseConfig):
    """Viewer-export policy attached to one run request."""

    export_viewer_rrd: bool = False
    """Whether the run should export a normalized repo-owned `.rrd` recording."""

    connect_live_viewer: bool = False
    """Whether streaming runs should attach a live gRPC viewer sink."""

    grpc_url: str = "rerun+http://127.0.0.1:9876/proxy"
    """Rerun gRPC endpoint used when `connect_live_viewer` is enabled."""

    preserve_native_rerun: bool = True
    """Whether native upstream `.rrd` recordings should be preserved as method artifacts."""


__all__ = ["VisualizationConfig"]
