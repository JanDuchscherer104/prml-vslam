"""Public method-wrapper entry surface for PRML VSLAM backends."""

from __future__ import annotations

from typing import Any

from .contracts import SlamUpdate

__all__ = [
    "MockSlamBackend",
    "SlamUpdate",
    "VistaSlamBackend",
]


def __getattr__(name: str) -> Any:
    """Provide lazy access to concrete backend wrappers."""
    if name == "MockSlamBackend":
        from .mock_vslam import MockSlamBackend

        return MockSlamBackend
    if name == "VistaSlamBackend":
        from .vista.adapter import VistaSlamBackend

        return VistaSlamBackend
    raise AttributeError(name)
