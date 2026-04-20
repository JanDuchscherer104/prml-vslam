"""Public method-wrapper entry surface for PRML VSLAM backends.

The :mod:`prml_vslam.methods` package owns backend identifiers, backend-private
config, method-owned live updates, and thin wrappers that adapt external SLAM
systems to the normalized artifact boundaries in :mod:`prml_vslam.pipeline`.
This root module exposes the backend configs and canonical wrappers that other
packages import directly.
"""

from .configs import BackendConfig, MockSlamBackendConfig, VistaSlamBackendConfig
from .contracts import MethodId
from .vista.adapter import VistaSlamBackend

__all__ = [
    "BackendConfig",
    "MethodId",
    "MockSlamBackendConfig",
    "VistaSlamBackend",
    "VistaSlamBackendConfig",
]
