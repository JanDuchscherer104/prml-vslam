"""Thin visualization-policy contracts.

Visualization policy controls viewer attachment and `.rrd` export, not
scientific artifact semantics. Rerun recordings are observer artifacts; TUM
trajectories, PLY clouds, manifests, and stage summaries remain the benchmark
source of truth.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field

from prml_vslam.utils import BaseConfig


class VisualizationConfig(BaseConfig):
    """Viewer-export policy attached to one run request or target run config.

    The config can ask the pipeline to connect a live Rerun sink, export a
    repo-owned recording, preserve upstream-native recordings, and tune bounded
    viewer history. Stage runtimes and DTOs must not call the Rerun SDK
    directly; they emit neutral visualization items for sinks to interpret.
    """

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

    trajectory_pose_axis_length: float = Field(default=0.0, ge=0.0)
    """Axis length for per-pose trajectory transforms; ``0.0`` keeps axes hidden."""

    log_source_rgb: bool = False
    """Whether the repo-owned sink should log original source RGB frames."""

    log_diagnostic_preview: bool = False
    """Whether the repo-owned sink should log method diagnostic preview images."""

    log_camera_image_rgb: bool = False
    """Whether the 3D camera branch should also log RGB image planes."""


__all__ = ["VisualizationConfig"]
