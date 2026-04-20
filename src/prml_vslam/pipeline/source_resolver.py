"""Pipeline-local source resolution for offline-capable requests.

This module adapts request-layer source specs into concrete
:class:`prml_vslam.protocols.source.OfflineSequenceSource` owners. It belongs to
the pipeline because it translates request contracts into source adapters, but
the actual dataset and IO logic still stays in their owning packages.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from prml_vslam.datasets.advio import AdvioDatasetService
from prml_vslam.datasets.contracts import DatasetId
from prml_vslam.pipeline.contracts.request import DatasetSourceSpec, Record3DLiveSourceSpec, SourceSpec, VideoSourceSpec
from prml_vslam.pipeline.contracts.sequence import SequenceManifest
from prml_vslam.protocols.source import OfflineSequenceSource
from prml_vslam.utils import Console, PathConfig


class VideoOfflineSequenceSource:
    """Adapt a raw video path into the normalized offline source seam."""

    def __init__(self, *, path_config: PathConfig, video_path: Path, frame_stride: int) -> None:
        self._path_config = path_config
        self._video_path = video_path
        self._frame_stride = frame_stride

    @property
    def label(self) -> str:
        """Return the compact user-facing label for this source."""
        return f"Video '{self._video_path.name}'"

    def prepare_sequence_manifest(self, output_dir: Path) -> SequenceManifest:
        """Resolve the video path and return the minimal normalized manifest."""
        del output_dir
        resolved_video_path = self._path_config.resolve_video_path(self._video_path, must_exist=True)
        return SequenceManifest(
            sequence_id=resolved_video_path.stem,
            video_path=resolved_video_path,
        )


@dataclass(slots=True)
class OfflineSourceResolver:
    """Resolve request-layer source specs into offline-capable source adapters."""

    path_config: PathConfig

    def resolve(self, source_spec: SourceSpec) -> OfflineSequenceSource:
        """Resolve one request source spec into the owning offline source adapter."""
        console = Console(__name__).child(self.__class__.__name__)
        match source_spec:
            case DatasetSourceSpec(dataset_id=DatasetId.ADVIO, sequence_id=sequence_id):
                service = AdvioDatasetService(self.path_config)
                numeric_sequence_id = service.resolve_sequence_id(sequence_id)
                console.info(
                    "Resolved ADVIO offline source '%s' to normalized sequence id '%s'.",
                    sequence_id,
                    numeric_sequence_id,
                )
                return service.build_offline_source(
                    sequence_id=numeric_sequence_id,
                    dataset_serving=source_spec.dataset_serving,
                )
            case VideoSourceSpec(video_path=video_path, frame_stride=frame_stride):
                resolved_video_path = self.path_config.resolve_video_path(video_path, must_exist=True)
                console.info("Resolved video offline source '%s'.", video_path)
                console.debug("Resolved video path to '%s'.", resolved_video_path)
                return VideoOfflineSequenceSource(
                    path_config=self.path_config,
                    video_path=resolved_video_path,
                    frame_stride=frame_stride,
                )
            case Record3DLiveSourceSpec():
                raise RuntimeError("Record3D live sources require `streaming` mode.")
            case _:
                raise RuntimeError(f"Unsupported offline source spec: {source_spec!r}")


__all__ = ["OfflineSourceResolver", "VideoOfflineSequenceSource"]
