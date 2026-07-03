from __future__ import annotations

from typing import Any

from ..contracts import FrameSelectionConfig, ReferenceCloudConfig, SequenceKey
from ..sources import DatasetSequenceSource, DatasetServiceBase
from .tum_rgbd_download import TumRgbdDownloadManager
from .tum_rgbd_layout import load_tum_rgbd_catalog
from .tum_rgbd_loading import load_tum_rgbd_associations
from .tum_rgbd_models import TumRgbdSequenceConfig
from .tum_rgbd_sequence import TumRgbdSequence


class TumRgbdDatasetService(DatasetServiceBase, TumRgbdDownloadManager):
    catalog_loader = staticmethod(load_tum_rgbd_catalog)

    def _build_normalization_materializer(
        self,
        *,
        sequence_id: SequenceKey,
        frame_selection: FrameSelectionConfig | None = None,
        reference_cloud: ReferenceCloudConfig | None = None,
        rgb_max_width_px: int = 392,
        rgb_dimension_multiple: int = 14,
    ) -> DatasetSequenceSource:
        return self._build_source(
            sequence_id=sequence_id,
            frame_selection=frame_selection or FrameSelectionConfig(),
            sequence_kwargs={
                "reference_cloud": reference_cloud or ReferenceCloudConfig(),
                "rgb_max_width_px": rgb_max_width_px,
                "rgb_dimension_multiple": rgb_dimension_multiple,
            },
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
