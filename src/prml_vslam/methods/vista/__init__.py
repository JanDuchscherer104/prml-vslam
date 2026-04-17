"""Canonical ViSTA backend public surfaces."""

from importlib import import_module

__all__ = ["VistaSlamBackend", "VistaSlamBackendConfig", "VistaSlamConfig", "VistaSlamSession"]


def __getattr__(name: str) -> object:
    if name in {"VistaSlamBackend", "VistaSlamSession"}:
        return getattr(import_module(".adapter", __name__), name)
    if name in {"VistaSlamBackendConfig", "VistaSlamConfig"}:
        return getattr(import_module(".config", __name__), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
