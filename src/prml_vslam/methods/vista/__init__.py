"""Canonical ViSTA backend public surface.

This package contains the thin adapter, runtime/bootstrap helpers, and session
wrapper that adapt the upstream ViSTA checkout to the repository's method
contract.
"""

from typing import Any

__all__ = ["VistaSlamBackend", "VistaSlamBackendConfig", "VistaSlamSession"]


def __getattr__(name: str) -> Any:
    if name == "VistaSlamBackend":
        from .adapter import VistaSlamBackend

        return VistaSlamBackend
    if name == "VistaSlamBackendConfig":
        from ..configs import VistaSlamBackendConfig

        return VistaSlamBackendConfig
    if name == "VistaSlamSession":
        from .session import VistaSlamSession

        return VistaSlamSession
    raise AttributeError(name)
