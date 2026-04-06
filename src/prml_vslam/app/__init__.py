"""Packaged Streamlit entrypoint for the PRML VSLAM workbench."""

from importlib import import_module

__all__ = ["launch_app", "run_app"]


def __getattr__(name: str) -> object:
    if name in {"launch_app", "run_app"}:
        return getattr(import_module(".bootstrap", __name__), name)
    if name in {"bootstrap", "plotting"}:
        return import_module(f".{name}", __name__)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
