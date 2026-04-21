"""Public reconstruction entry surface for reference-scene builders.

The :mod:`prml_vslam.reconstruction` package owns reconstruction-method ids,
artifact DTOs, minimal config-as-factory surfaces, and thin library-backed
reconstruction adapters. Shared posed RGB-D observation DTOs live in
:mod:`prml_vslam.interfaces.rgbd`. This package is intentionally smaller than
``prml_vslam.methods`` today because the repository currently targets one
minimal offline reconstruction implementation.
"""

from .config import Open3dTsdfBackendConfig, ReconstructionBackendConfig
from .contracts import (
    ReconstructionArtifacts,
    ReconstructionMetadata,
    ReconstructionMethodId,
    ReconstructionObservation,
)
from .open3d_tsdf import Open3dTsdfBackend
from .protocols import OfflineReconstructionBackend, ReconstructionSession, StreamingReconstructionBackend
from .rgbd_source import FileRgbdObservationSource

__all__ = [
    "Open3dTsdfBackend",
    "Open3dTsdfBackendConfig",
    "FileRgbdObservationSource",
    "OfflineReconstructionBackend",
    "ReconstructionArtifacts",
    "ReconstructionBackendConfig",
    "ReconstructionMetadata",
    "ReconstructionMethodId",
    "ReconstructionObservation",
    "ReconstructionSession",
    "StreamingReconstructionBackend",
]
