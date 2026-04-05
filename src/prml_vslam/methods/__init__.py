"""Mock method surfaces used to satisfy shared repository interfaces."""

from .contracts import MethodId
from .mstr import MSTRMethodConfig
from .vista import VISTAMethodConfig

__all__ = [
    "MSTRMethodConfig",
    "MethodId",
    "VISTAMethodConfig",
]
