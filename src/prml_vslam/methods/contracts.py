"""Typed contracts for external VSLAM method adapters."""

from __future__ import annotations

from enum import StrEnum


class MethodId(StrEnum):
    """Supported external VSLAM backends."""

    VISTA = "vista"
    MSTR = "mstr"

    @property
    def display_name(self) -> str:
        """Return the upstream method name shown to users."""
        match self:
            case MethodId.VISTA:
                return "ViSTA-SLAM"
            case MethodId.MSTR:
                return "MASt3R-SLAM"


__all__ = ["MethodId"]
