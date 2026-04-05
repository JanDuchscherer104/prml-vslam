"""Typed contracts for external VSLAM method adapters."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

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


class MethodRunRequest(BaseData):
    """Minimal inference request accepted by the repository-local method mocks."""

    input_path: Path
    """Video file or image-directory input that should be processed."""

    artifact_root: Path
    """Repository-owned output root where normalized artifacts belong."""


class MethodRunResult(BaseData):
    """Normalized artifact paths produced by one mock method run."""

    method: MethodId
    """Backend that produced the artifacts."""

    normalized_trajectory_path: Path
    """Normalized TUM trajectory path owned by this repository."""

    normalized_point_cloud_path: Path
    """Normalized dense point cloud path owned by this repository."""

    executed: bool = False
    """Whether the mock runtime materialized the paths during this call."""


__all__ = [
    "MethodId",
    "MethodRunRequest",
    "MethodRunResult",
]
