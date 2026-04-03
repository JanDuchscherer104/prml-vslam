"""MASt3R-SLAM mock config."""

from __future__ import annotations

from pathlib import Path

from prml_vslam.methods.base import MockMethodConfig
from prml_vslam.methods.interfaces import MethodId


class MSTRMethodConfig(MockMethodConfig):
    """Config that builds the repository-local MASt3R mock runtime."""

    calibration_path: Path | None = None
    """Optional calibration path kept only to satisfy the shared config shape."""

    @property
    def method_id(self) -> MethodId:
        return MethodId.MSTR


__all__ = ["MSTRMethodConfig"]
