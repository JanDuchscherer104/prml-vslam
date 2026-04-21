"""Public method-wrapper entry surface for PRML VSLAM backends.

The :mod:`prml_vslam.methods` package owns backend identifiers, backend-private
config, method-owned live updates, and thin wrappers that adapt external SLAM
systems to the normalized artifact boundaries in :mod:`prml_vslam.pipeline`.
This root module exposes the backend configs and canonical wrappers that other
packages import directly.
"""

from __future__ import annotations

from typing import Any

from .config_contracts import MethodId
from .configs import MockSlamBackendConfig, VistaSlamBackendConfig
from .vista.adapter import VistaSlamBackend

__all__ = [
    "MethodId",
    "MockSlamBackendConfig",
    "VistaSlamBackend",
    "VistaSlamBackendConfig",
]


def __getattr__(name: str) -> Any:
    """Provide lazy access to non-exported compatibility symbols."""
    if name == "BackendConfig":
        from .configs import BackendConfig

        return BackendConfig
    raise AttributeError(name)
