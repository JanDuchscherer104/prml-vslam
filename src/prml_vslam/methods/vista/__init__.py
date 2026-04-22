"""Canonical ViSTA backend public surface.

This package contains the thin adapter and runtime/bootstrap helpers that adapt
the upstream ViSTA checkout to the repository's method contract.
"""

from typing import Any

__all__ = ["VistaSlamBackend", "VistaSlamBackendConfig", "VistaSlamRuntime"]


def __getattr__(name: str) -> Any:
    if name == "VistaSlamBackend":
        from .adapter import VistaSlamBackend

        return VistaSlamBackend
    if name == "VistaSlamBackendConfig":
        from ..configs import VistaSlamBackendConfig

        return VistaSlamBackendConfig
    if name == "VistaSlamRuntime":
        from .session import VistaSlamRuntime

        return VistaSlamRuntime
    raise AttributeError(name)
