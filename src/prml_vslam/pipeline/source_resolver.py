"""Pipeline-local offline source adapters used by orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from prml_vslam.datasets.advio import AdvioDatasetService
from prml_vslam.datasets.contracts import DatasetId
from prml_vslam.pipeline.contracts.request import DatasetSourceSpec, Record3DLiveSourceSpec, SourceSpec, VideoSourceSpec
from prml_vslam.pipeline.contracts.sequence import SequenceManifest
from prml_vslam.protocols.source import OfflineSequenceSource
from prml_vslam.utils import PathConfig


class VideoOfflineSequenceSource:
    """Video-backed offline source adapter owned by pipeline orchestration."""

    def __init__(self, *, path_config: PathConfig, video_path: Path, frame_stride: int) -> None:
        self._path_config = path_config
        self._video_path = video_path
        self._frame_stride = frame_stride

    @property
    def label(self) -> str:
        return f"Video '{self._video_path.name}'"

    def prepare_sequence_manifest(self, output_dir: Path) -> SequenceManifest:
        del output_dir
        resolved_video_path = self._path_config.resolve_video_path(self._video_path, must_exist=True)
        return SequenceManifest(
            sequence_id=resolved_video_path.stem,
            video_path=resolved_video_path,
        )


@dataclass(slots=True)
class OfflineSourceResolver:
    """Resolve offline-capable source adapters for pipeline orchestration."""

    path_config: PathConfig

    def resolve(self, source_spec: SourceSpec) -> OfflineSequenceSource:
        match source_spec:
            case DatasetSourceSpec(dataset_id=DatasetId.ADVIO, sequence_id=sequence_id):
                service = AdvioDatasetService(self.path_config)
                numeric_sequence_id = service.resolve_sequence_id(sequence_id)
                return service.build_offline_source(sequence_id=numeric_sequence_id)
            case VideoSourceSpec(video_path=video_path, frame_stride=frame_stride):
                return VideoOfflineSequenceSource(
                    path_config=self.path_config,
                    video_path=video_path,
                    frame_stride=frame_stride,
                )
            case Record3DLiveSourceSpec():
                raise RuntimeError("Record3D live sources require `streaming` mode.")
            case _:
                raise RuntimeError(f"Unsupported offline source spec: {source_spec!r}")


__all__ = ["OfflineSourceResolver", "VideoOfflineSequenceSource"]
