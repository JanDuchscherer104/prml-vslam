"""TUM RGB-D app- and pipeline-facing service layer.

This module contains the high-level TUM RGB-D service surface that owns catalog
summaries, normalized source adapters, and preview timing helpers for the rest
of the package.
"""

from __future__ import annotations

from ...replay import ReplayMode
from ..contracts import DatasetSummary, FrameSelectionConfig, ReferenceCloudConfig, SequenceKey
from ..normalized_store import NormalizedDatasetProfile, NormalizedDatasetStore
from ..sources import DatasetSequenceSource, DatasetServiceBase, open_dataset_sequence_stream
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
        config = TumRgbdSequenceConfig(
            dataset_root=self.dataset_root,
            sequence_id=str(sequence_id),
            reference_cloud=reference_cloud or ReferenceCloudConfig(),
        )

        def sequence() -> TumRgbdSequence:
            return TumRgbdSequence(config=config, catalog=self.catalog)

        return DatasetSequenceSource(
            sequence_id=sequence_id,
            frame_selection=frame_selection or FrameSelectionConfig(),
            label=lambda value: self.scene(value).display_name,
            manifest=lambda _value, output_dir, selection: sequence().to_sequence_manifest(
                output_dir=output_dir,
                frame_selection=selection,
            ),
            benchmark=lambda _value, output_dir, selection: sequence().to_benchmark_inputs(
                output_dir=output_dir,
                frame_selection=selection,
            ),
            replay_mode=replay_mode,
            normalized_store=normalized_store,
            normalized_profile=normalized_profile,
            stream=lambda _value, loop, mode, selection: self._open_sequence_stream(
                sequence=sequence(),
                frame_selection=selection,
                loop=loop,
                replay_mode=mode,
                **stream_kwargs,
            ),
        )

    def _preview_timestamps_ns(self, sequence: TumRgbdSequence) -> list[int]:
        """Return preview timestamps derived from the RGB association rows."""
        return [
            int(round(association.rgb_timestamp_s * 1e9))
            for association in load_tum_rgbd_associations(sequence.paths.sequence_dir)
        ]

    def _open_sequence_stream(
        self,
        *,
        sequence: TumRgbdSequence,
        frame_selection: FrameSelectionConfig,
        loop: bool,
        replay_mode: ReplayMode,
        **stream_kwargs,
    ):
        return open_dataset_sequence_stream(
            sequence=sequence,
            timestamps_ns=self._preview_timestamps_ns(sequence),
            frame_selection=frame_selection,
            loop=loop,
            replay_mode=replay_mode,
            **stream_kwargs,
        )
