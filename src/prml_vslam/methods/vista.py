"""ViSTA-SLAM mock config."""

from __future__ import annotations

from prml_vslam.methods.base import MockMethodConfig
from prml_vslam.methods.contracts import MethodId


class VISTAMethodConfig(MockMethodConfig):
    """Config that builds the repository-local ViSTA mock runtime."""

    @property
    def method_id(self) -> MethodId:
        return MethodId.VISTA


__all__ = ["VISTAMethodConfig"]
