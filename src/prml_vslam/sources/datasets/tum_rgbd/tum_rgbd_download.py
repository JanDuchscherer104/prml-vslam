from __future__ import annotations

import tarfile
from pathlib import Path

from prml_vslam.sources.datasets.contracts import DatasetDownloadResult, LocalSceneStatus
from prml_vslam.sources.datasets.download_helpers import (
    normalize_archive_member,
    relative_sequence_path,
)
from prml_vslam.sources.datasets.fetch import DatasetFetchHelper
from prml_vslam.utils import Console

from .tum_rgbd_layout import (
    offline_ready,
    replay_ready,
    resolve_existing_sequence_dir,
    scene_for_sequence_id,
)
from .tum_rgbd_models import (
    TumRgbdCatalog,
    TumRgbdDownloadRequest,
    TumRgbdSceneMetadata,
)


class TumRgbdDownloadManager:
    def __init__(self, dataset_root: Path, *, catalog: TumRgbdCatalog, console: Console) -> None:
        self.dataset_root = dataset_root
        self.catalog = catalog
        self.console = console
        self._fetch_helper = DatasetFetchHelper()

    @property
    def archive_root(self) -> Path:
        return self.dataset_root / ".archives"

    def scene(self, sequence_id: str) -> TumRgbdSceneMetadata:
        return scene_for_sequence_id(self.catalog, sequence_id)

    def local_scene_statuses(self) -> list[LocalSceneStatus[TumRgbdSceneMetadata]]:
        statuses: list[LocalSceneStatus[TumRgbdSceneMetadata]] = []
        for scene in self.catalog.scenes:
            statuses.append(
                LocalSceneStatus[TumRgbdSceneMetadata](
                    scene=scene,
                    sequence_dir=resolve_existing_sequence_dir(self.dataset_root, scene.sequence_id),
                    archive_path=self._existing_archive_path(scene),
                    replay_ready=replay_ready(self.dataset_root, scene),
                    offline_ready=offline_ready(self.dataset_root, scene),
                )
            )
        return statuses

    def download(self, request: TumRgbdDownloadRequest) -> DatasetDownloadResult[str]:
        """Download selected TUM RGB-D scenes and extract complete scene payloads."""
        self.dataset_root.mkdir(parents=True, exist_ok=True)
        self.archive_root.mkdir(parents=True, exist_ok=True)

        sequence_ids = request.sequence_ids or [scene.sequence_id for scene in self.catalog.scenes]
        downloaded_archive_count = 0
        reused_archive_count = 0
        written_paths: set[Path] = set()

        for sequence_id in sequence_ids:
            scene = self.scene(sequence_id)
            archive_path, downloaded = self._ensure_archive(scene, overwrite=request.overwrite)
            downloaded_archive_count += int(downloaded)
            reused_archive_count += int(not downloaded)
            written_paths.update(
                self._extract_full_scene(
                    scene=scene,
                    archive_path=archive_path,
                    overwrite=request.overwrite,
                )
            )

        return DatasetDownloadResult[str](
            sequence_ids=sequence_ids,
            downloaded_archive_count=downloaded_archive_count,
            reused_archive_count=reused_archive_count,
            written_path_count=len(written_paths),
        )

    def _ensure_archive(self, scene: TumRgbdSceneMetadata, *, overwrite: bool) -> tuple[Path, bool]:
        archive_path = self.archive_root / f"{scene.folder_name}.tgz"
        self.console.info(f"Resolving archive {scene.sequence_id} from {scene.archive_url}.")
        return self._fetch_helper.fetch_to_path(scene.archive_url, archive_path, overwrite=overwrite)

    def _existing_archive_path(self, scene: TumRgbdSceneMetadata) -> Path | None:
        archive_path = self.archive_root / f"{scene.folder_name}.tgz"
        return archive_path if archive_path.exists() else None

    def _extract_full_scene(
        self,
        *,
        scene: TumRgbdSceneMetadata,
        archive_path: Path,
        overwrite: bool,
    ) -> set[Path]:
        written_paths: set[Path] = set()
        matched_members = 0
        with tarfile.open(archive_path, mode="r:gz") as archive:
            for member in archive.getmembers():
                if not member.isfile():
                    continue
                normalized = normalize_archive_member(member.name, invalid_path_label="TUM RGB-D")
                if normalized is None:
                    continue
                relative_path = relative_sequence_path(normalized, scene.folder_name)
                if relative_path is None or not relative_path.parts:
                    continue
                matched_members += 1
                target_path = self.dataset_root / Path(*normalized)
                if not target_path.exists() or overwrite:
                    _safe_extract_member(archive, member, target_path)
                written_paths.add(target_path)

        if matched_members == 0:
            msg = f"Archive {archive_path} did not contain any members for scene {scene.sequence_id}."
            raise ValueError(msg)
        return written_paths


def _safe_extract_member(archive: tarfile.TarFile, member: tarfile.TarInfo, target_path: Path) -> None:
    source = archive.extractfile(member)
    if source is None:
        raise ValueError(f"Unable to read TUM RGB-D archive member: {member.name}")
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with source, target_path.open("wb") as sink:
        sink.write(source.read())
