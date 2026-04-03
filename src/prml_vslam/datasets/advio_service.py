from __future__ import annotations

from pathlib import Path

from prml_vslam.utils import Console, PathConfig

from .advio_download import AdvioDownloadManager
from .advio_layout import load_advio_catalog
from .advio_models import (
    AdvioCatalog,
    AdvioDatasetSummary,
    AdvioDownloadRequest,
    AdvioDownloadResult,
    AdvioLocalSceneStatus,
    AdvioSceneMetadata,
    AdvioSequenceConfig,
)
from .advio_sequence import AdvioOfflineSample, AdvioSequence


class AdvioDatasetService:
    def __init__(self, path_config: PathConfig, *, catalog: AdvioCatalog | None = None) -> None:
        self.path_config = path_config
        self.catalog = load_advio_catalog() if catalog is None else catalog
        console = Console(__name__).child(self.__class__.__name__)
        self.console = console
        self._download_manager = AdvioDownloadManager(self.dataset_root, catalog=self.catalog, console=console)

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

    def summarize(self) -> AdvioDatasetSummary:
        statuses = self.local_scene_statuses()
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
        return AdvioSequence(
            config=AdvioSequenceConfig(dataset_root=self.dataset_root, sequence_id=sequence_id),
            catalog=self.catalog,
        ).load_offline_sample()

    def download(self, request: AdvioDownloadRequest) -> AdvioDownloadResult:
        return self._download_manager.download(request)
