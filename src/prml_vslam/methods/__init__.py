"""Mock method surfaces used to satisfy shared repository interfaces."""

from .contracts import MethodId


def __getattr__(name: str) -> object:
    """Lazily expose heavier mock-backend helpers without eager import cycles."""
    if name == "MockSlamBackendConfig":
        from .mock_vslam import MockSlamBackendConfig

        return MockSlamBackendConfig
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "MethodId",
    "MockSlamBackendConfig",
]
