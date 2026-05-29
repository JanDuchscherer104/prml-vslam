"""Canonical MASt3R-SLAM backend public surface.

This package contains the thin adapter and runtime helpers that adapt the
upstream MASt3R-SLAM checkout under ``external/mast3r-slam`` to the repository's
method contract. Heavy upstream imports (torch, lietorch, mast3r_slam) are
deferred to attribute access so that simply importing this package never
crashes when the upstream stack is missing.
"""

from typing import Any

__all__ = ["Mast3rSlamBackend", "Mast3rSlamSession"]


def __getattr__(name: str) -> Any:
    if name == "Mast3rSlamBackend":
        from .adapter import Mast3rSlamBackend

        return Mast3rSlamBackend
    if name == "Mast3rSlamSession":
        from .adapter import Mast3rSlamSession

        return Mast3rSlamSession
    raise AttributeError(name)
