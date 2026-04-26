"""Public reconstruction entry surface for reference-scene builders.

The :mod:`prml_vslam.reconstruction` package owns reconstruction-method ids,
artifact DTOs, minimal config-as-factory surfaces, and thin library-backed
reconstruction adapters. Shared posed observation DTOs live in
:mod:`prml_vslam.interfaces.observation`. This package is intentionally smaller than
``prml_vslam.methods`` today because the repository currently targets one
minimal offline reconstruction implementation.
"""

from .config import Open3dTsdfBackendConfig, ReconstructionBackendConfig
from .contracts import (
    ReconstructionArtifacts,
    ReconstructionMetadata,
    ReconstructionMethodId,
)
from .open3d_tsdf import Open3dTsdfBackend
from .protocols import OfflineReconstructionBackend

__all__ = [
    "Open3dTsdfBackend",
    "Open3dTsdfBackendConfig",
    "OfflineReconstructionBackend",
    "ReconstructionArtifacts",
    "ReconstructionBackendConfig",
    "ReconstructionMetadata",
    "ReconstructionMethodId",
]
