"""Thin visualization-policy contracts."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from prml_vslam.pipeline.contracts.artifacts import ArtifactRef
from prml_vslam.utils import BaseConfig, BaseData


class RerunModality(StrEnum):
    """Selectable live payloads that the repo-owned Rerun sink may emit."""

    SOURCE_RGB = "source_rgb"
    CAMERA_POSE = "camera_pose"
    CAMERA_INTRINSICS = "camera_intrinsics"
    KEYFRAME_RGB = "keyframe_rgb"
    KEYFRAME_DEPTH = "keyframe_depth"
    POINTMAPS = "pointmaps"
    DIAGNOSTIC_PREVIEW = "diagnostic_preview"

    @property
    def label(self) -> str:
        return {
            RerunModality.SOURCE_RGB: "Source RGB",
            RerunModality.CAMERA_POSE: "Camera Pose",
            RerunModality.CAMERA_INTRINSICS: "Camera Intrinsics",
            RerunModality.KEYFRAME_RGB: "Keyframe RGB",
            RerunModality.KEYFRAME_DEPTH: "Keyframe Depth",
            RerunModality.POINTMAPS: "Pointmaps",
            RerunModality.DIAGNOSTIC_PREVIEW: "Diagnostic Preview",
        }[self]


def default_rerun_modalities() -> list[RerunModality]:
    """Return the default live payloads exported to repo-owned Rerun sinks."""
    return [
        RerunModality.SOURCE_RGB,
        RerunModality.CAMERA_POSE,
        RerunModality.CAMERA_INTRINSICS,
        RerunModality.KEYFRAME_RGB,
        RerunModality.KEYFRAME_DEPTH,
        RerunModality.POINTMAPS,
        RerunModality.DIAGNOSTIC_PREVIEW,
    ]


class VisualizationConfig(BaseConfig):
    """Viewer-export policy attached to one run request."""

    connect_live_viewer: bool = False
    """Whether streaming runs should attach a live gRPC viewer sink."""

    export_viewer_rrd: bool = False
    """Whether one canonical repo-owned `.rrd` recording should be exported."""

    grpc_url: str = "rerun+http://127.0.0.1:9876/proxy"
    """Rerun gRPC endpoint used when `connect_live_viewer` is enabled."""

    preserve_native_rerun: bool = True
    """Whether native upstream `.rrd` recordings should be preserved as method artifacts."""

    rerun_modalities: list[RerunModality] = Field(default_factory=default_rerun_modalities)
    """Live payload types emitted by the repo-owned Rerun sink."""


class VisualizationArtifacts(BaseData):
    """Viewer artifacts associated with one run."""

    native_rerun_rrd: ArtifactRef | None = None
    """Optional preserved recorded-session `.rrd` from an upstream backend."""

    native_output_dir: ArtifactRef | None = None
    """Optional preserved backend-native output directory."""

    extras: dict[str, ArtifactRef] = Field(default_factory=dict)
    """Optional additional viewer artifacts owned by the visualization layer."""


__all__ = [
    "default_rerun_modalities",
    "RerunModality",
    "VisualizationArtifacts",
    "VisualizationConfig",
]
