"""Mock and real method surfaces used to satisfy shared repository interfaces."""

from importlib import import_module

from .contracts import MethodId


def __getattr__(name: str) -> object:
    """Lazily expose heavier backend helpers without eager import cycles."""
    if name == "MockSlamBackendConfig":
        from .mock_vslam import MockSlamBackendConfig

        return MockSlamBackendConfig
    if name in {"VistaSlamBackend", "VistaSlamBackendConfig"}:
        return getattr(import_module(".vista", __name__), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "MethodId",
    "MockSlamBackendConfig",
    "VistaSlamBackend",
    "VistaSlamBackendConfig",
]
