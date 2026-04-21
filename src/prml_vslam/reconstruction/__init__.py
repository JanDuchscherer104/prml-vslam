"""Public reconstruction entry surface for reference-scene builders.

The :mod:`prml_vslam.reconstruction` package owns reconstruction-method ids,
typed RGB-D observation DTOs, minimal config-as-factory surfaces, and thin
library-backed reconstruction adapters. It is intentionally smaller than
``prml_vslam.methods`` today because the repository currently targets one
minimal offline reconstruction implementation.
"""

from .configs import Open3dTsdfBackendConfig, ReconstructionBackendConfig
from .contracts import (
    ReconstructionArtifacts,
    ReconstructionMetadata,
    ReconstructionMethodId,
    ReconstructionObservation,
)
from .harness import ReconstructionHarness
from .open3d_tsdf import Open3dTsdfBackend

__all__ = [
    "Open3dTsdfBackend",
    "Open3dTsdfBackendConfig",
    "ReconstructionArtifacts",
    "ReconstructionBackendConfig",
    "ReconstructionHarness",
    "ReconstructionMetadata",
    "ReconstructionMethodId",
    "ReconstructionObservation",
]
