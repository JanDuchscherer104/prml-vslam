from __future__ import annotations

from pathlib import Path

from prml_vslam.datasets.contracts import FrameSelectionConfig
from prml_vslam.io import Cv2ReplayMode
from prml_vslam.utils import BaseConfig

from ..sources import DatasetSequenceSource, DatasetServiceBase, open_dataset_sequence_stream
from .advio_download import AdvioDownloadManager
from .advio_layout import load_advio_catalog
from .advio_loading import load_advio_frame_timestamps_ns
from .advio_models import (
    AdvioDatasetSummary,
    AdvioPoseSource,
    AdvioSequenceConfig,
)
from .advio_sequence import AdvioSequence


class AdvioStreamingSourceConfig(FrameSelectionConfig, BaseConfig):
    """Config-backed ADVIO streaming source for process-backed execution."""

    dataset_root: Path
    sequence_id: int
    pose_source: AdvioPoseSource = AdvioPoseSource.GROUND_TRUTH
    respect_video_rotation: bool = False

    def setup_target(self) -> DatasetSequenceSource:
        """Build the minimal config-backed ADVIO streaming adapter."""

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
                pose_source=self.pose_source,
                respect_video_rotation=self.respect_video_rotation,
            )

        return DatasetSequenceSource(
            sequence_id=self.sequence_id,
            frame_selection=FrameSelectionConfig(frame_stride=self.frame_stride, target_fps=self.target_fps),
            label=lambda sequence_id: sequence(sequence_id).scene.display_name,
            manifest=lambda sequence_id, output_dir, frame_selection: sequence(sequence_id).to_sequence_manifest(
                output_dir=output_dir,
                frame_selection=frame_selection,
            ),
            benchmark=lambda sequence_id, output_dir: sequence(sequence_id).to_benchmark_inputs(output_dir=output_dir),
            stream=stream,
        )


class AdvioDatasetService(DatasetServiceBase, AdvioDownloadManager):
    """Dataset service for ADVIO catalog access, download, and replay helpers."""

    catalog_loader = staticmethod(load_advio_catalog)
    summary_model = AdvioDatasetSummary
    sequence_config_model = AdvioSequenceConfig
    sequence_model = AdvioSequence

    def resolve_sequence_id(self, sequence_slug: str) -> int:
        if sequence_slug.startswith("advio-"):
            _, suffix = sequence_slug.split("-", maxsplit=1)
            if suffix.isdigit():
                return int(suffix)
        raise RuntimeError(f"ADVIO sequence slug '{sequence_slug}' could not be resolved to a numeric scene id.")

    def _preview_timestamps_ns(self, sequence: AdvioSequence) -> list[int]:
        return load_advio_frame_timestamps_ns(sequence.paths.frame_timestamps_path).tolist()
