"""Typed contracts for external VSLAM method adapters."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import Field

from prml_vslam.utils import BaseData


class MethodId(StrEnum):
    """Supported external VSLAM backends."""

    VISTA = "vista"
    MSTR = "mstr"

    @property
    def artifact_slug(self) -> str:
        """Return the filesystem token used for method-owned artifact roots."""
        return self.value

    @property
    def display_name(self) -> str:
        """Return the upstream method name shown to users."""
        match self:
            case MethodId.VISTA:
                return "ViSTA-SLAM"
            case MethodId.MSTR:
                return "MASt3R-SLAM"


class MethodCommand(BaseData):
    """One explicit external command invocation."""

    cwd: Path
    """Working directory from which the command must be executed."""

    argv: list[str]
    """Exact argv vector used to invoke the upstream backend."""


class MethodRunRequest(BaseData):
    """Shared inference request accepted by every method adapter."""

    input_path: Path
    """Video file or image-directory input that should be processed."""

    artifact_root: Path
    """Repository-owned output root where normalized artifacts belong."""

    frame_stride: int = 1
    """Stride used when materializing frames for methods that need images."""


class MethodRunResult(BaseData):
    """Planned or executed method invocation with normalized artifact paths."""

    method: MethodId
    """Backend that produced or will produce the artifacts."""

    command: MethodCommand
    """Primary upstream inference command."""

    normalized_trajectory_path: Path
    """Normalized TUM trajectory path owned by this repository."""

    normalized_point_cloud_path: Path
    """Normalized dense point cloud path owned by this repository."""

    raw_trajectory_path: Path | None = None
    """Method-native trajectory artifact path before normalization."""

    raw_point_cloud_path: Path | None = None
    """Method-native point-cloud artifact path before normalization."""

    executed: bool = False
    """Whether the upstream inference command already ran successfully."""

    notes: list[str] = Field(default_factory=list)
    """Human-readable caveats and backend-specific setup notes."""


__all__ = [
    "MethodCommand",
    "MethodId",
    "MethodRunRequest",
    "MethodRunResult",
]
