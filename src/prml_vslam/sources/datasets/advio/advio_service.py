from __future__ import annotations

from typing import Any

from prml_vslam.sources.datasets.contracts import AdvioServingConfig, FrameSelectionConfig

from ..sources import DatasetSequenceSource, DatasetServiceBase
from .advio_download import AdvioDownloadManager
from .advio_layout import load_advio_catalog
from .advio_loading import load_advio_frame_timestamps_ns
from .advio_models import AdvioSequenceConfig
from .advio_sequence import AdvioSequence


class AdvioDatasetService(DatasetServiceBase, AdvioDownloadManager):
    catalog_loader = staticmethod(load_advio_catalog)

    def resolve_sequence_id(self, sequence_slug: str) -> int:
        """Resolve an ``advio-XX`` slug into the numeric ADVIO sequence id."""
        if sequence_slug.startswith("advio-"):
            _, suffix = sequence_slug.split("-", maxsplit=1)
            if suffix.isdigit():
                return int(suffix)
        raise RuntimeError(f"ADVIO sequence slug '{sequence_slug}' could not be resolved to a numeric scene id.")

    def _preview_timestamps_ns(self, sequence: AdvioSequence) -> list[int]:
        return load_advio_frame_timestamps_ns(sequence.paths.frame_timestamps_path).tolist()

    def _sequence(self, sequence_id: int, **config_kwargs: Any) -> AdvioSequence:
        return AdvioSequence(
            config=AdvioSequenceConfig(dataset_root=self.dataset_root, sequence_id=sequence_id, **config_kwargs),
            catalog=self.catalog,
        )

    def _build_raw_source(
        self,
        *,
        sequence_id: int,
        frame_selection: FrameSelectionConfig | None = None,
        dataset_serving: AdvioServingConfig | None = None,
    ) -> DatasetSequenceSource:
        """Build the raw ADVIO source used only for normalized-store ingestion."""
        selection = frame_selection or FrameSelectionConfig()
        sequence = self._sequence(sequence_id)
        return DatasetSequenceSource(
            sequence_id=sequence_id,
            frame_selection=selection,
            label=lambda value: self.scene(value).display_name,
            manifest=lambda _value, output_dir, manifest_selection: sequence.to_sequence_manifest(
                output_dir=output_dir,
                frame_selection=manifest_selection,
                dataset_serving=dataset_serving,
            ),
            benchmark=lambda _value, output_dir, _selection: sequence.to_benchmark_inputs(
                output_dir=output_dir,
                frame_selection=_selection,
                dataset_serving=dataset_serving,
            ),
        )

    def _build_normalization_materializer(
        self,
        *,
        sequence_id: int,
        frame_selection: FrameSelectionConfig | None = None,
        dataset_serving: AdvioServingConfig,
        normalize_video_orientation: bool = True,
        rgb_max_width_px: int = 392,
        rgb_dimension_multiple: int = 14,
    ) -> DatasetSequenceSource:
        """Build the raw ADVIO materializer used only for normalized-store ingestion."""
        selection = frame_selection or FrameSelectionConfig()

        return DatasetSequenceSource(
            sequence_id=sequence_id,
            frame_selection=selection,
            label=lambda value: self.scene(value).display_name,
            manifest=lambda _value, output_dir, manifest_selection: self._sequence(sequence_id).to_sequence_manifest(
                output_dir=output_dir,
                frame_selection=manifest_selection,
                dataset_serving=dataset_serving,
            ),
            benchmark=lambda _value, output_dir, _selection: self._sequence(sequence_id).to_benchmark_inputs(
                output_dir=output_dir,
                frame_selection=_selection,
                dataset_serving=dataset_serving,
                rgb_max_width_px=rgb_max_width_px,
                rgb_dimension_multiple=rgb_dimension_multiple,
            ),
        )
