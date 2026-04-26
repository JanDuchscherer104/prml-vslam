"""Public method-wrapper entry surface for PRML VSLAM backends."""

from __future__ import annotations

from typing import Any

from .contracts import SlamUpdate

__all__ = [
    "SlamUpdate",
    "VistaSlamBackend",
]


def __getattr__(name: str) -> Any:
    """Provide lazy access to concrete backend wrappers."""
    if name == "VistaSlamBackend":
        from .vista.adapter import VistaSlamBackend

        return VistaSlamBackend
    raise AttributeError(name)
