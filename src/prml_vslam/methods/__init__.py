"""Mock and real method surfaces used to satisfy shared repository interfaces."""

from .contracts import MethodId


def __getattr__(name: str) -> object:
    """Lazily expose heavier backend helpers without eager import cycles."""
    if name == "MockSlamBackendConfig":
        from .mock_vslam import MockSlamBackendConfig

        return MockSlamBackendConfig
    if name == "VistaSlamBackend":
        from .vista.adapter import VistaSlamBackend

        return VistaSlamBackend
    if name == "VistaSlamBackendConfig":
        from .vista.config import VistaSlamBackendConfig

        return VistaSlamBackendConfig

    if name == "Mast3rSlamBackend":
        from .mast3r.adapter import Mast3rSlamBackend
        return Mast3rSlamBackend
    if name == "Mast3rSlamBackendConfig":
        from .mast3r.config import Mast3rSlamBackendConfig
        return Mast3rSlamBackendConfig
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "MethodId",
    "MockSlamBackendConfig",
    "VistaSlamBackend",
    "VistaSlamBackendConfig",
    "Mast3rSlamBackend", 
    "Mast3rSlamBackendConfig"
]
