"""SLAM backend adapters and shared method contracts."""

from .contracts import MethodId


def __getattr__(name: str) -> object:
    """Lazily expose heavier backend helpers without eager import cycles."""
    if name == "MockSlamBackendConfig":
        from .mock_vslam import MockSlamBackendConfig

        return MockSlamBackendConfig
    if name == "VistaSlamBackendConfig":
        from .vista_slam.config import VistaSlamBackendConfig

        return VistaSlamBackendConfig
    if name == "VistaSlamBackend":
        from .vista_slam.runner import VistaSlamBackend

        return VistaSlamBackend
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "MethodId",
    "MockSlamBackendConfig",
    "VistaSlamBackend",
    "VistaSlamBackendConfig",
]
