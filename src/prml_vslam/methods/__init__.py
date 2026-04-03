"""Mock method surfaces used to satisfy shared repository interfaces."""

from .install import MethodInstallationService
from .interfaces import MethodId, MethodRunRequest, ViewerId
from .mstr import MSTRMethodConfig
from .vista import VISTAMethodConfig

__all__ = [
    "MSTRMethodConfig",
    "MethodId",
    "MethodInstallationService",
    "MethodRunRequest",
    "VISTAMethodConfig",
    "ViewerId",
]
