"""Public ADVIO dataset surface for app, tests, and pipeline integration.

This package owns the ADVIO-specific models, sequence owner, service helpers,
and replay/normalization entry points that plug into the broader
:mod:`prml_vslam.datasets` and :mod:`prml_vslam.pipeline` architecture.
"""

from __future__ import annotations

from ..contracts import AdvioPoseFrameMode, AdvioPoseSource, AdvioServingConfig
from .advio_loading import load_advio_calibration
from .advio_models import (
    AdvioCatalog,
    AdvioDatasetSummary,
    AdvioDownloadPreset,
    AdvioDownloadRequest,
    AdvioEnvironment,
    AdvioLocalSceneStatus,
    AdvioModality,
    AdvioPeopleLevel,
    AdvioSceneMetadata,
    AdvioSequenceConfig,
    AdvioUpstreamMetadata,
)
from .advio_sequence import AdvioOfflineSample, AdvioSequence
from .advio_service import AdvioDatasetService, AdvioStreamingSourceConfig

__all__ = [
    "AdvioCatalog",
    "AdvioDatasetService",
    "AdvioDatasetSummary",
    "AdvioDownloadPreset",
    "AdvioDownloadRequest",
    "AdvioEnvironment",
    "AdvioLocalSceneStatus",
    "AdvioModality",
    "AdvioOfflineSample",
    "AdvioPeopleLevel",
    "AdvioPoseFrameMode",
    "AdvioPoseSource",
    "AdvioSceneMetadata",
    "AdvioSequence",
    "AdvioSequenceConfig",
    "AdvioServingConfig",
    "AdvioStreamingSourceConfig",
    "AdvioUpstreamMetadata",
    "load_advio_calibration",
]
