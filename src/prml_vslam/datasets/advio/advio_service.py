from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from prml_vslam.benchmark import PreparedBenchmarkInputs
from prml_vslam.datasets.contracts import FrameSelectionConfig
from prml_vslam.io import Cv2ReplayMode
from prml_vslam.protocols import FramePacketStream
from prml_vslam.protocols.source import BenchmarkInputSource, StreamingSequenceSource
from prml_vslam.utils import BaseConfig, FactoryConfig

from ..sources import DatasetServiceBase
from .advio_download import AdvioDownloadManager
from .advio_layout import load_advio_catalog
from .advio_loading import load_advio_frame_timestamps_ns
from .advio_models import (
    AdvioDatasetSummary,
    AdvioPoseSource,
    AdvioSequenceConfig,
)
from .advio_sequence import AdvioSequence

if TYPE_CHECKING:
    from prml_vslam.pipeline.contracts.sequence import SequenceManifest


class AdvioStreamingSourceConfig(FrameSelectionConfig, BaseConfig, FactoryConfig["AdvioStreamingSequenceSource"]):
    """Config-backed ADVIO streaming source for process-backed execution."""

    dataset_root: Path
    sequence_id: int
    pose_source: AdvioPoseSource = AdvioPoseSource.GROUND_TRUTH
    respect_video_rotation: bool = False

    @property
    def target_type(self) -> type[AdvioStreamingSequenceSource]:
        return AdvioStreamingSequenceSource


class AdvioStreamingSequenceSource(StreamingSequenceSource, BenchmarkInputSource):
    """ADVIO-backed streaming source used by pipeline-owned replay sessions."""

    def __init__(self, config: AdvioStreamingSourceConfig) -> None:
        self.config = config

    @property
    def label(self) -> str:
        return self._sequence().scene.display_name

    def prepare_sequence_manifest(self, output_dir: Path) -> SequenceManifest:
        return self._sequence().to_sequence_manifest(output_dir=output_dir, frame_selection=self.config)

    def prepare_benchmark_inputs(self, output_dir: Path) -> PreparedBenchmarkInputs:
        return self._sequence().to_benchmark_inputs(output_dir=output_dir)

    def open_stream(self, *, loop: bool) -> FramePacketStream:
        sequence = self._sequence()
        timestamps_ns = load_advio_frame_timestamps_ns(sequence.paths.frame_timestamps_path)
        stride = self.config.stride_for_timestamps_ns(timestamps_ns.tolist())
        return sequence.open_stream(
            pose_source=self.config.pose_source,
            stride=stride,
            respect_video_rotation=self.config.respect_video_rotation,
            loop=loop,
            replay_mode=Cv2ReplayMode.REALTIME,
        )

    def _sequence(self) -> AdvioSequence:
        return AdvioSequenceConfig(
            dataset_root=self.config.dataset_root,
            sequence_id=self.config.sequence_id,
        ).setup_target()


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

    def build_streaming_source(
        self,
        *,
        sequence_id: int,
        pose_source: AdvioPoseSource,
        respect_video_rotation: bool,
        frame_selection: FrameSelectionConfig | None = None,
    ) -> StreamingSequenceSource:
        selection = frame_selection or FrameSelectionConfig()
        return AdvioStreamingSourceConfig(
            dataset_root=self.dataset_root,
            sequence_id=sequence_id,
            pose_source=pose_source,
            respect_video_rotation=respect_video_rotation,
            frame_stride=selection.frame_stride,
            target_fps=selection.target_fps,
        ).setup_target()

    def open_preview_stream(
        self,
        *,
        sequence_id: int,
        pose_source: AdvioPoseSource,
        respect_video_rotation: bool,
        frame_selection: FrameSelectionConfig | None = None,
        loop: bool = True,
        replay_mode: Cv2ReplayMode = Cv2ReplayMode.REALTIME,
    ) -> FramePacketStream:
        sequence = self._sequence(sequence_id)
        timestamps_ns = load_advio_frame_timestamps_ns(sequence.paths.frame_timestamps_path)
        stride = (frame_selection or FrameSelectionConfig()).stride_for_timestamps_ns(timestamps_ns.tolist())
        return sequence.open_stream(
            pose_source=pose_source,
            stride=stride,
            loop=loop,
            replay_mode=replay_mode,
            respect_video_rotation=respect_video_rotation,
        )

    def _preview_timestamps_ns(self, sequence: AdvioSequence) -> list[int]:
        return load_advio_frame_timestamps_ns(sequence.paths.frame_timestamps_path).tolist()
