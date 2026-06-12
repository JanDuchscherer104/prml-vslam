"""ADVIO app- and pipeline-facing service layer.

This module owns the high-level ADVIO service surface used by launch code. It
turns the lower-level sequence owner into summaries, normalized source adapters,
and preview streams without duplicating ADVIO-specific path or replay logic.
"""

from __future__ import annotations

from prml_vslam.sources.datasets.contracts import AdvioServingConfig, DatasetSummary, FrameSelectionConfig
from prml_vslam.sources.replay import ReplayMode

from ..normalized_store import NormalizedDatasetProfile, NormalizedDatasetStore
from ..sources import DatasetSequenceSource, DatasetServiceBase, open_dataset_sequence_stream
from .advio_download import AdvioDownloadManager
from .advio_layout import load_advio_catalog
from .advio_loading import load_advio_frame_timestamps_ns
from .advio_models import AdvioSequenceConfig
from .advio_sequence import AdvioSequence


class AdvioDatasetService(DatasetServiceBase, AdvioDownloadManager):
    """Provide the main ADVIO service surface for app and pipeline code."""

    catalog_loader = staticmethod(load_advio_catalog)
    summary_model = DatasetSummary
    sequence_config_model = AdvioSequenceConfig
    sequence_model = AdvioSequence

    def resolve_sequence_id(self, sequence_slug: str) -> int:
        """Resolve an ``advio-XX`` slug into the numeric ADVIO sequence id."""
        if sequence_slug.startswith("advio-"):
            _, suffix = sequence_slug.split("-", maxsplit=1)
            if suffix.isdigit():
                return int(suffix)
        raise RuntimeError(f"ADVIO sequence slug '{sequence_slug}' could not be resolved to a numeric scene id.")

    def _preview_timestamps_ns(self, sequence: AdvioSequence) -> list[int]:
        return load_advio_frame_timestamps_ns(sequence.paths.frame_timestamps_path).tolist()

    def build_offline_source(
        self,
        *,
        sequence_id: int,
        frame_selection: FrameSelectionConfig | None = None,
        dataset_serving: AdvioServingConfig | None = None,
    ) -> DatasetSequenceSource:
        """Build the ADVIO-backed offline source adapter for one sequence."""
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
            ),
        )

    def build_streaming_source(
        self,
        *,
        sequence_id: int,
        frame_selection: FrameSelectionConfig | None = None,
        dataset_serving: AdvioServingConfig,
        replay_mode: ReplayMode = ReplayMode.REALTIME,
        normalize_video_orientation: bool = True,
        normalized_store: NormalizedDatasetStore | None = None,
        normalized_profile: NormalizedDatasetProfile | None = None,
    ) -> DatasetSequenceSource:
        """Build the ADVIO-backed streaming source adapter for one sequence."""
        selection = frame_selection or FrameSelectionConfig()

        def sequence() -> AdvioSequence:
            return self._sequence(sequence_id)

        def stream(_value: int, loop: bool, mode: ReplayMode, stream_selection: FrameSelectionConfig):
            advio_sequence = sequence()
            return open_dataset_sequence_stream(
                sequence=advio_sequence,
                timestamps_ns=load_advio_frame_timestamps_ns(advio_sequence.paths.frame_timestamps_path).tolist(),
                frame_selection=stream_selection,
                loop=loop,
                replay_mode=mode,
                dataset_serving=dataset_serving,
                normalize_video_orientation=normalize_video_orientation,
            )

        return DatasetSequenceSource(
            sequence_id=sequence_id,
            frame_selection=selection,
            label=lambda _value: sequence().scene.display_name,
            manifest=lambda _value, output_dir, manifest_selection: sequence().to_sequence_manifest(
                output_dir=output_dir,
                frame_selection=manifest_selection,
                dataset_serving=dataset_serving,
            ),
            benchmark=lambda _value, output_dir, _selection: sequence().to_benchmark_inputs(output_dir=output_dir),
            stream=stream,
            replay_mode=replay_mode,
            normalized_store=normalized_store,
            normalized_profile=normalized_profile,
        )

    def open_preview_stream(
        self,
        *,
        sequence_id: int,
        frame_selection: FrameSelectionConfig | None = None,
        dataset_serving: AdvioServingConfig,
        loop: bool = True,
        replay_mode: ReplayMode = ReplayMode.REALTIME,
        normalize_video_orientation: bool = True,
    ):
        """Open the canonical ADVIO preview replay stream for one sequence."""
        sequence = self._sequence(sequence_id)
        return open_dataset_sequence_stream(
            sequence=sequence,
            timestamps_ns=load_advio_frame_timestamps_ns(sequence.paths.frame_timestamps_path).tolist(),
            frame_selection=frame_selection or FrameSelectionConfig(),
            loop=loop,
            replay_mode=replay_mode,
            dataset_serving=dataset_serving,
            normalize_video_orientation=normalize_video_orientation,
        )
