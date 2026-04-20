"""ADVIO app- and pipeline-facing service layer.

This module owns the high-level ADVIO service surface used by launch code. It
turns the lower-level sequence owner into summaries, normalized source adapters,
and preview streams without duplicating ADVIO-specific path or replay logic.
"""

from __future__ import annotations

from pathlib import Path

from prml_vslam.datasets.contracts import DatasetServingConfig, FrameSelectionConfig
from prml_vslam.io import Cv2ReplayMode
from prml_vslam.utils import BaseConfig

from ..sources import DatasetSequenceSource, DatasetServiceBase, open_dataset_sequence_stream
from .advio_download import AdvioDownloadManager
from .advio_layout import load_advio_catalog
from .advio_loading import load_advio_frame_timestamps_ns
from .advio_models import (
    AdvioDatasetSummary,
    AdvioSequenceConfig,
)
from .advio_sequence import AdvioSequence


class AdvioStreamingSourceConfig(FrameSelectionConfig, BaseConfig):
    """Configure a process-backed ADVIO streaming source adapter."""

    dataset_root: Path
    sequence_id: int
    dataset_serving: DatasetServingConfig
    respect_video_rotation: bool = False

    def setup_target(self) -> DatasetSequenceSource:
        """Build the normalized ADVIO streaming source adapter."""

        def sequence(sequence_id: int) -> AdvioSequence:
            return AdvioSequenceConfig(dataset_root=self.dataset_root, sequence_id=sequence_id).setup_target()

        def stream(
            sequence_id: int,
            loop: bool,
            replay_mode: Cv2ReplayMode,
            frame_selection: FrameSelectionConfig,
        ):
            advio_sequence = sequence(sequence_id)
            return open_dataset_sequence_stream(
                sequence=advio_sequence,
                timestamps_ns=load_advio_frame_timestamps_ns(advio_sequence.paths.frame_timestamps_path).tolist(),
                frame_selection=frame_selection,
                loop=loop,
                replay_mode=replay_mode,
                dataset_serving=self.dataset_serving,
                respect_video_rotation=self.respect_video_rotation,
            )

        return DatasetSequenceSource(
            sequence_id=self.sequence_id,
            frame_selection=FrameSelectionConfig(frame_stride=self.frame_stride, target_fps=self.target_fps),
            label=lambda sequence_id: sequence(sequence_id).scene.display_name,
            manifest=lambda sequence_id, output_dir, frame_selection: sequence(sequence_id).to_sequence_manifest(
                output_dir=output_dir,
                frame_selection=frame_selection,
                dataset_serving=self.dataset_serving,
            ),
            benchmark=lambda sequence_id, output_dir: sequence(sequence_id).to_benchmark_inputs(output_dir=output_dir),
            stream=stream,
        )


class AdvioDatasetService(DatasetServiceBase, AdvioDownloadManager):
    """Provide the main ADVIO service surface for app and pipeline code."""

    catalog_loader = staticmethod(load_advio_catalog)
    summary_model = AdvioDatasetSummary
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
        dataset_serving: DatasetServingConfig | None = None,
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
            benchmark=lambda _value, output_dir: sequence.to_benchmark_inputs(output_dir=output_dir),
        )

    def build_streaming_source(
        self,
        *,
        sequence_id: int,
        frame_selection: FrameSelectionConfig | None = None,
        dataset_serving: DatasetServingConfig,
        respect_video_rotation: bool = False,
    ) -> DatasetSequenceSource:
        """Build the ADVIO-backed streaming source adapter for one sequence."""
        selection = frame_selection or FrameSelectionConfig()
        return AdvioStreamingSourceConfig(
            dataset_root=self.dataset_root,
            sequence_id=sequence_id,
            dataset_serving=dataset_serving,
            respect_video_rotation=respect_video_rotation,
            frame_stride=selection.frame_stride,
            target_fps=selection.target_fps,
        ).setup_target()

    def open_preview_stream(
        self,
        *,
        sequence_id: int,
        frame_selection: FrameSelectionConfig | None = None,
        dataset_serving: DatasetServingConfig,
        loop: bool = True,
        replay_mode: Cv2ReplayMode = Cv2ReplayMode.REALTIME,
        respect_video_rotation: bool = False,
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
            respect_video_rotation=respect_video_rotation,
        )
