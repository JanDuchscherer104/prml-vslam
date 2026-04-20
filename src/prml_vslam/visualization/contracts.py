"""Thin visualization-policy contracts."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field

from prml_vslam.pipeline.contracts.artifacts import ArtifactRef
from prml_vslam.utils import BaseConfig, BaseData


class VisualizationConfig(BaseConfig):
    """Viewer-export policy attached to one run request."""

    connect_live_viewer: bool = False
    """Whether streaming runs should attach a live gRPC viewer sink."""

    export_viewer_rrd: bool = False
    """Whether one canonical repo-owned `.rrd` recording should be exported."""

    grpc_url: str = "rerun+http://127.0.0.1:9876/proxy"
    """Rerun gRPC endpoint used when `connect_live_viewer` is enabled."""

    viewer_blueprint_path: Path | None = None
    """Optional blueprint loaded by the CLI-owned live viewer subprocess."""

    preserve_native_rerun: bool = True
    """Whether native upstream `.rrd` recordings should be preserved as method artifacts."""

    frusta_history_window_streaming: int = Field(default=20, gt=0)
    """Bounded keyed-camera/frusta window applied by the streaming sink."""

    frusta_history_window_offline: int | None = Field(default=None, gt=0)
    """Future offline frusta-history window; `None` keeps full history."""

    show_tracking_trajectory: bool = True
    """Whether the repo-owned sink should log the full tracking trajectory polyline."""


class VisualizationArtifacts(BaseData):
    """Viewer artifacts associated with one run."""

    native_rerun_rrd: ArtifactRef | None = None
    """Optional preserved recorded-session `.rrd` from an upstream backend."""

    native_output_dir: ArtifactRef | None = None
    """Optional preserved backend-native output directory."""

    extras: dict[str, ArtifactRef] = Field(default_factory=dict)
    """Optional additional viewer artifacts owned by the visualization layer."""


__all__ = [
    "VisualizationArtifacts",
    "VisualizationConfig",
]
