"""MASt3R-SLAM mock config."""

from __future__ import annotations

from prml_vslam.methods.base import MockMethodConfig
from prml_vslam.methods.contracts import MethodId


class MSTRMethodConfig(MockMethodConfig):
    """Config that builds the repository-local MASt3R mock runtime."""

    @property
    def method_id(self) -> MethodId:
        return MethodId.MSTR


__all__ = ["MSTRMethodConfig"]
