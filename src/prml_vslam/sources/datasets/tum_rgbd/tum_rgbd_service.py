"""TUM RGB-D app- and pipeline-facing service layer.

This module contains the high-level TUM RGB-D service surface that owns catalog
summaries, normalized source adapters, and preview timing helpers for the rest
of the package.
"""

from __future__ import annotations

from ...replay import ReplayMode
from ..contracts import DatasetSummary, FrameSelectionConfig, ReferenceCloudConfig, SequenceKey
from ..normalized_store import NormalizedDatasetProfile, NormalizedDatasetStore
from ..sources import DatasetSequenceSource, DatasetServiceBase
from .tum_rgbd_download import TumRgbdDownloadManager
from .tum_rgbd_layout import load_tum_rgbd_catalog
from .tum_rgbd_loading import load_tum_rgbd_associations
from .tum_rgbd_models import TumRgbdSequenceConfig
from .tum_rgbd_sequence import TumRgbdSequence


class TumRgbdDatasetService(DatasetServiceBase, TumRgbdDownloadManager):
    """Provide the main TUM RGB-D service surface for app and pipeline code."""

    catalog_loader = staticmethod(load_tum_rgbd_catalog)
    summary_model = DatasetSummary
    sequence_config_model = TumRgbdSequenceConfig
    sequence_model = TumRgbdSequence

    def build_streaming_source(
        self,
        *,
        sequence_id: SequenceKey,
        frame_selection: FrameSelectionConfig | None = None,
        replay_mode: ReplayMode = ReplayMode.REALTIME,
        reference_cloud: ReferenceCloudConfig | None = None,
        normalized_store: NormalizedDatasetStore | None = None,
        normalized_profile: NormalizedDatasetProfile | None = None,
        **stream_kwargs,
    ) -> DatasetSequenceSource:
        return self._build_streaming_source(
            sequence_id=sequence_id,
            frame_selection=frame_selection or FrameSelectionConfig(),
            replay_mode=replay_mode,
            sequence_kwargs={"reference_cloud": reference_cloud or ReferenceCloudConfig()},
            normalized_store=normalized_store,
            normalized_profile=normalized_profile,
            **stream_kwargs,
        )

    def _preview_timestamps_ns(self, sequence: TumRgbdSequence) -> list[int]:
        """Return preview timestamps derived from the RGB association rows."""
        return [
            int(round(association.rgb_timestamp_s * 1e9))
            for association in load_tum_rgbd_associations(sequence.paths.sequence_dir)
        ]
