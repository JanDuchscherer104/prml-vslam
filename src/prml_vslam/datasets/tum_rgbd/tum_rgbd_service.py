"""TUM RGB-D app- and pipeline-facing service layer.

This module contains the high-level TUM RGB-D service surface that owns catalog
summaries, normalized source adapters, and preview timing helpers for the rest
of the package.
"""

from __future__ import annotations

from ..sources import DatasetServiceBase
from .tum_rgbd_download import TumRgbdDownloadManager
from .tum_rgbd_layout import load_tum_rgbd_catalog
from .tum_rgbd_loading import load_tum_rgbd_associations
from .tum_rgbd_models import (
    TumRgbdDatasetSummary,
    TumRgbdSequenceConfig,
)
from .tum_rgbd_sequence import TumRgbdSequence


class TumRgbdDatasetService(DatasetServiceBase, TumRgbdDownloadManager):
    """Provide the main TUM RGB-D service surface for app and pipeline code."""

    catalog_loader = staticmethod(load_tum_rgbd_catalog)
    summary_model = TumRgbdDatasetSummary
    sequence_config_model = TumRgbdSequenceConfig
    sequence_model = TumRgbdSequence

    def _preview_timestamps_ns(self, sequence: TumRgbdSequence) -> list[int]:
        """Return preview timestamps derived from the RGB association rows."""
        return [
            int(round(association.rgb_timestamp_s * 1e9))
            for association in load_tum_rgbd_associations(sequence.paths.sequence_dir)
        ]
