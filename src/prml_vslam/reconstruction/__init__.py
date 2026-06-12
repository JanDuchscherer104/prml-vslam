"""Public reconstruction entry surface for reference-scene builders.

The :mod:`prml_vslam.reconstruction` package owns reconstruction-method ids,
artifact DTOs, minimal config-as-factory surfaces, and thin library-backed
reconstruction adapters. Shared posed observation DTOs live in
:mod:`prml_vslam.interfaces.observation`.
"""

from .config import (
    NksrBackendConfig,
    PoissonBackendConfig,
    ReconstructionBackendConfig,
)
from .contracts import (
    ReconstructionArtifacts,
    ReconstructionMetadata,
    ReconstructionMethodId,
)
from .nksr import NksrBackend
from .poisson import PoissonBackend
from .protocols import OfflineReconstructionBackend

__all__ = [
    "NksrBackend",
    "NksrBackendConfig",
    "PoissonBackend",
    "PoissonBackendConfig",
    "OfflineReconstructionBackend",
    "ReconstructionArtifacts",
    "ReconstructionBackendConfig",
    "ReconstructionMetadata",
    "ReconstructionMethodId",
]
