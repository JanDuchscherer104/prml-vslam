"""MASt3R-SLAM backend public surfaces."""

from importlib import import_module

__all__ = ["Mast3rSlamBackend", "Mast3rSlamBackendConfig"]


def __getattr__(name: str) -> object:
    if name == "Mast3rSlamBackend":
        return getattr(import_module(".adapter", __name__), name)
    if name == "Mast3rSlamBackendConfig":
        return getattr(import_module(".config", __name__), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")