from __future__ import annotations

import zipfile
from pathlib import Path

from prml_vslam.sources.datasets.contracts import DatasetDownloadResult
from prml_vslam.sources.datasets.download_helpers import (
    normalize_archive_member,
    relative_sequence_path,
)
from prml_vslam.sources.datasets.fetch import DatasetFetchHelper
from prml_vslam.utils import Console

from .advio_layout import (
    arcore_ready,
    arkit_ready,
    offline_ready,
    replay_ready,
    resolve_calibration_path,
    resolve_existing_sequence_dir,
    scene_for_sequence_id,
)
from .advio_models import (
    AdvioCatalog,
    AdvioDownloadRequest,
    AdvioLocalSceneStatus,
    AdvioSceneMetadata,
)

_DOWNLOAD_CHUNK_SIZE_BYTES = 1024 * 1024


class AdvioDownloadManager:
    def __init__(self, dataset_root: Path, *, catalog: AdvioCatalog, console: Console) -> None:
        self.dataset_root = dataset_root
        self.catalog = catalog
        self.console = console
        self._fetch_helper = DatasetFetchHelper()

    @property
    def archive_root(self) -> Path:
        """Return the cache directory used for downloaded scene archives."""
        return self.dataset_root / ".archives"

    def scene(self, sequence_id: int) -> AdvioSceneMetadata:
        """Return one catalog scene by id."""
        return scene_for_sequence_id(self.catalog, sequence_id)

    def local_scene_statuses(self) -> list[AdvioLocalSceneStatus]:
        """Return local availability status for every catalog scene."""
        statuses: list[AdvioLocalSceneStatus] = []
        for scene in self.catalog.scenes:
            sequence_dir = resolve_existing_sequence_dir(self.dataset_root, scene.sequence_slug)
            statuses.append(
                AdvioLocalSceneStatus(
                    scene=scene,
                    sequence_dir=sequence_dir,
                    archive_path=self._existing_archive_path(scene),
                    replay_ready=replay_ready(self.dataset_root, scene),
                    offline_ready=offline_ready(self.dataset_root, scene),
                    arcore_ready=arcore_ready(sequence_dir, scene),
                    arkit_ready=arkit_ready(sequence_dir, scene),
                )
            )
        return statuses

    def download(self, request: AdvioDownloadRequest) -> DatasetDownloadResult[int]:
        """Download selected ADVIO scenes and extract complete scene payloads."""
        self.dataset_root.mkdir(parents=True, exist_ok=True)
        self.archive_root.mkdir(parents=True, exist_ok=True)

        sequence_ids = request.sequence_ids or [scene.sequence_id for scene in self.catalog.scenes]
        downloaded_archive_count = 0
        reused_archive_count = 0
        written_paths: set[Path] = set()

        for sequence_id in sequence_ids:
            scene = self.scene(sequence_id)
            written_paths.add(self._ensure_calibration(scene, overwrite=request.overwrite))
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

        return DatasetDownloadResult[int](
            sequence_ids=sequence_ids,
            downloaded_archive_count=downloaded_archive_count,
            reused_archive_count=reused_archive_count,
            written_path_count=len(written_paths),
        )

    def _ensure_archive(self, scene: AdvioSceneMetadata, *, overwrite: bool) -> tuple[Path, bool]:
        archive_path = self.archive_root / f"{scene.sequence_slug}.zip"
        self.console.info(f"Resolving archive {scene.sequence_slug} from {scene.archive_url}.")
        return self._fetch_helper.fetch_to_path(
            scene.archive_url,
            archive_path,
            known_hash=f"md5:{scene.archive_md5}",
            overwrite=overwrite,
        )

    def _ensure_calibration(self, scene: AdvioSceneMetadata, *, overwrite: bool) -> Path:
        calibration_path = resolve_calibration_path(self.dataset_root, scene)
        calibration_path.parent.mkdir(parents=True, exist_ok=True)
        if calibration_path.exists() and not overwrite:
            return calibration_path
        calibration_url = f"{self.catalog.upstream.calibration_base_url}{scene.calibration_name}"
        self.console.info(f"Resolving calibration {scene.calibration_name} from {calibration_url}.")
        fetched_path, _ = self._fetch_helper.fetch_to_path(calibration_url, calibration_path, overwrite=overwrite)
        return fetched_path

    def _existing_archive_path(self, scene: AdvioSceneMetadata) -> Path | None:
        archive_path = self.archive_root / f"{scene.sequence_slug}.zip"
        return archive_path if archive_path.exists() else None

    def _extract_full_scene(
        self,
        *,
        scene: AdvioSceneMetadata,
        archive_path: Path,
        overwrite: bool,
    ) -> set[Path]:
        written_paths: set[Path] = set()
        matched_members = 0
        with zipfile.ZipFile(archive_path) as archive:
            for member in archive.infolist():
                if member.is_dir():
                    continue
                normalized = normalize_archive_member(member.filename)
                if normalized is None:
                    continue
                relative_path = relative_sequence_path(normalized, scene.sequence_slug)
                if relative_path is None or not relative_path.parts:
                    continue
                matched_members += 1
                target_path = self.dataset_root / Path(*normalized)
                if not target_path.exists() or overwrite:
                    _ensure_directory_parent(target_path)
                    with archive.open(member, "r") as source, target_path.open("wb") as sink:
                        sink.write(source.read())
                written_paths.add(target_path)

        if matched_members == 0:
            msg = f"Archive {archive_path} did not contain any members for scene {scene.sequence_slug}."
            raise ValueError(msg)
        return written_paths


def _ensure_directory_parent(target_path: Path) -> None:
    for ancestor in reversed(target_path.parent.parents):
        if ancestor.exists() and ancestor.is_file():
            if ancestor.stat().st_size == 0:
                ancestor.unlink()
                continue
            msg = f"Expected directory path but found file at {ancestor}. Remove it and retry the ADVIO download."
            raise ValueError(msg)
    if target_path.parent.exists() and target_path.parent.is_file():
        if target_path.parent.stat().st_size == 0:
            target_path.parent.unlink()
        else:
            msg = f"Expected directory path but found file at {target_path.parent}. Remove it and retry the ADVIO download."
            raise ValueError(msg)
    target_path.parent.mkdir(parents=True, exist_ok=True)
