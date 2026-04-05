"""Mock method surfaces used to satisfy shared repository interfaces."""

from .interfaces import MethodId, MethodRunRequest
from .mstr import MSTRMethodConfig
from .vista import VISTAMethodConfig

__all__ = [
    "MSTRMethodConfig",
    "MethodId",
    "MethodRunRequest",
    "VISTAMethodConfig",
]
