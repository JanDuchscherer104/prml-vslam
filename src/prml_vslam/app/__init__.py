"""Packaged Streamlit entrypoint for the PRML VSLAM workbench."""

from importlib import import_module

__all__ = ["run_app"]


def __getattr__(name: str) -> object:
    if name == "run_app":
        return import_module(".bootstrap", __name__).run_app
    if name in {"bootstrap", "plotting"}:
        return import_module(f".{name}", __name__)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
