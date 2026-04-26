"""Public TUM RGB-D dataset surface for app, tests, and pipeline integration.

This package owns the TUM RGB-D-specific models, sequence owner, service
helpers, and replay/normalization entry points that plug into the broader
:mod:`prml_vslam.sources.datasets` and :mod:`prml_vslam.pipeline` architecture.
"""

from __future__ import annotations

from .tum_rgbd_loading import TumRgbdOfflineSample
from .tum_rgbd_models import (
    TumRgbdCatalog,
    TumRgbdDownloadPreset,
    TumRgbdDownloadRequest,
    TumRgbdLocalSceneStatus,
    TumRgbdModality,
    TumRgbdPoseSource,
    TumRgbdSceneMetadata,
    TumRgbdSequenceConfig,
)
from .tum_rgbd_sequence import TumRgbdSequence
from .tum_rgbd_service import TumRgbdDatasetService

__all__ = [
    "TumRgbdCatalog",
    "TumRgbdDatasetService",
    "TumRgbdDownloadPreset",
    "TumRgbdDownloadRequest",
    "TumRgbdLocalSceneStatus",
    "TumRgbdModality",
    "TumRgbdOfflineSample",
    "TumRgbdPoseSource",
    "TumRgbdSceneMetadata",
    "TumRgbdSequence",
    "TumRgbdSequenceConfig",
]
