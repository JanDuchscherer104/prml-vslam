from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from prml_vslam.io import Cv2ReplayMode
from prml_vslam.protocols import FramePacketStream
from prml_vslam.utils import Console, PathConfig

from .advio_download import AdvioDownloadManager
from .advio_layout import load_advio_catalog
from .advio_models import (
    AdvioCatalog,
    AdvioDatasetSummary,
    AdvioDownloadRequest,
    AdvioDownloadResult,
    AdvioLocalSceneStatus,
    AdvioPoseSource,
    AdvioSceneMetadata,
    AdvioSequenceConfig,
)
from .advio_sequence import AdvioOfflineSample, AdvioSequence

if TYPE_CHECKING:
    from prml_vslam.pipeline.contracts import SequenceManifest
    from prml_vslam.pipeline.protocols import StreamingSequenceSource


class AdvioStreamingSequenceSource:
    """ADVIO-backed streaming source used by pipeline-owned replay sessions."""

    def __init__(
        self,
        *,
        service: AdvioDatasetService,
        sequence_id: int,
        pose_source: AdvioPoseSource,
        respect_video_rotation: bool,
    ) -> None:
        self._service = service
        self._sequence_id = sequence_id
        self._pose_source = pose_source
        self._respect_video_rotation = respect_video_rotation

    @property
    def label(self) -> str:
        """Return the human-readable ADVIO scene label."""
        return self._service.scene(self._sequence_id).display_name

    def prepare_sequence_manifest(self, output_dir: Path) -> SequenceManifest:
        """Materialize the normalized sequence boundary for one replay run."""
        return self._service.build_sequence_manifest(sequence_id=self._sequence_id, output_dir=output_dir)

    def open_stream(self, *, loop: bool) -> FramePacketStream:
        """Open the replay stream consumed by the pipeline session."""
        return self._service.open_preview_stream(
            sequence_id=self._sequence_id,
            pose_source=self._pose_source,
            respect_video_rotation=self._respect_video_rotation,
            loop=loop,
            replay_mode=Cv2ReplayMode.REALTIME,
        )


class AdvioDatasetService:
    """Dataset service for ADVIO catalog access, download, and replay helpers."""

    def __init__(self, path_config: PathConfig, *, catalog: AdvioCatalog | None = None) -> None:
        self.path_config = path_config
        self.catalog = load_advio_catalog() if catalog is None else catalog
        self._download_manager = AdvioDownloadManager(
            self.dataset_root, catalog=self.catalog, console=Console(__name__).child(self.__class__.__name__)
        )

    @property
    def dataset_root(self) -> Path:
        return self.path_config.resolve_dataset_dir(self.catalog.dataset_id)

    @property
    def archive_root(self) -> Path:
        return self._download_manager.archive_root

    def list_scenes(self) -> list[AdvioSceneMetadata]:
        return list(self.catalog.scenes)

    def scene(self, sequence_id: int) -> AdvioSceneMetadata:
        return self._download_manager.scene(sequence_id)

    def summarize(self, statuses: list[AdvioLocalSceneStatus] | None = None) -> AdvioDatasetSummary:
        statuses = self.local_scene_statuses() if statuses is None else statuses
        return AdvioDatasetSummary(
            total_scene_count=len(statuses),
            local_scene_count=sum(status.sequence_dir is not None for status in statuses),
            replay_ready_scene_count=sum(status.replay_ready for status in statuses),
            offline_ready_scene_count=sum(status.offline_ready for status in statuses),
            full_scene_count=sum(status.full_ready for status in statuses),
            cached_archive_count=sum(status.archive_path is not None for status in statuses),
            total_remote_archive_bytes=sum(scene.archive_size_bytes for scene in self.catalog.scenes),
        )

    def local_scene_statuses(self) -> list[AdvioLocalSceneStatus]:
        return self._download_manager.local_scene_statuses()

    def list_local_sequence_ids(self) -> list[int]:
        return [status.scene.sequence_id for status in self.local_scene_statuses() if status.offline_ready]

    def load_local_sample(self, sequence_id: int) -> AdvioOfflineSample:
        return self._sequence(sequence_id).load_offline_sample()

    def build_sequence_manifest(self, *, sequence_id: int, output_dir: Path | None = None) -> SequenceManifest:
        return self._sequence(sequence_id).to_sequence_manifest(output_dir=output_dir)

    def build_streaming_source(
        self,
        *,
        sequence_id: int,
        pose_source: AdvioPoseSource,
        respect_video_rotation: bool,
    ) -> StreamingSequenceSource:
        """Return a replay source compatible with pipeline-owned streaming sessions."""
        return AdvioStreamingSequenceSource(
            service=self,
            sequence_id=sequence_id,
            pose_source=pose_source,
            respect_video_rotation=respect_video_rotation,
        )

    def open_preview_stream(
        self,
        *,
        sequence_id: int,
        pose_source: AdvioPoseSource,
        respect_video_rotation: bool,
        loop: bool = True,
        replay_mode: Cv2ReplayMode = Cv2ReplayMode.REALTIME,
    ) -> FramePacketStream:
        return self._sequence(sequence_id).open_stream(
            pose_source=pose_source,
            loop=loop,
            replay_mode=replay_mode,
            respect_video_rotation=respect_video_rotation,
        )

    def download(self, request: AdvioDownloadRequest) -> AdvioDownloadResult:
        return self._download_manager.download(request)

    def _sequence(self, sequence_id: int) -> AdvioSequence:
        return AdvioSequence(
            config=AdvioSequenceConfig(dataset_root=self.dataset_root, sequence_id=sequence_id), catalog=self.catalog
        )
