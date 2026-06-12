from __future__ import annotations

from typing import Any

from ...replay import ReplayMode
from ..contracts import FrameSelectionConfig, ReferenceCloudConfig, SequenceKey
from ..normalized_store import NormalizedDatasetProfile, NormalizedDatasetStore
from ..sources import DatasetSequenceSource, DatasetServiceBase
from .tum_rgbd_download import TumRgbdDownloadManager
from .tum_rgbd_layout import load_tum_rgbd_catalog
from .tum_rgbd_loading import load_tum_rgbd_associations
from .tum_rgbd_models import TumRgbdSequenceConfig
from .tum_rgbd_sequence import TumRgbdSequence


class TumRgbdDatasetService(DatasetServiceBase, TumRgbdDownloadManager):
    catalog_loader = staticmethod(load_tum_rgbd_catalog)

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

    def _sequence(self, sequence_id: SequenceKey, **config_kwargs: Any) -> TumRgbdSequence:
        return TumRgbdSequence(
            config=TumRgbdSequenceConfig(dataset_root=self.dataset_root, sequence_id=sequence_id, **config_kwargs),
            catalog=self.catalog,
        )
