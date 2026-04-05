from __future__ import annotations

import hashlib
import tempfile
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

from prml_vslam.utils import Console

from .advio_layout import (
    archive_member_matches,
    local_modalities,
    resolve_calibration_path,
    resolve_existing_sequence_dir,
    scene_for_sequence_id,
)
from .advio_models import (
    AdvioCatalog,
    AdvioDownloadPreset,
    AdvioDownloadRequest,
    AdvioDownloadResult,
    AdvioLocalSceneStatus,
    AdvioModality,
    AdvioSceneMetadata,
)

_DOWNLOAD_CHUNK_SIZE_BYTES = 1024 * 1024


class AdvioDownloadManager:
    def __init__(self, dataset_root: Path, *, catalog: AdvioCatalog, console: Console) -> None:
        self.dataset_root = dataset_root
        self.catalog = catalog
        self.console = console

    @property
    def archive_root(self) -> Path:
        """Return the cache directory used for downloaded scene archives."""
        return self.dataset_root / ".archives"

    def scene(self, sequence_id: int) -> AdvioSceneMetadata:
        """Return one catalog scene by id."""
        return scene_for_sequence_id(self.catalog, sequence_id)

    def local_scene_statuses(self) -> list[AdvioLocalSceneStatus]:
        """Return local availability status for every catalog scene."""
        return [
            AdvioLocalSceneStatus(
                scene=scene,
                sequence_dir=resolve_existing_sequence_dir(self.dataset_root, scene.sequence_slug),
                local_modalities=(local_modalities := self._local_modalities(scene)),
                archive_path=self._existing_archive_path(scene),
                replay_ready=_modalities_present(local_modalities, AdvioDownloadPreset.STREAMING.modalities),
                offline_ready=_modalities_present(local_modalities, AdvioDownloadPreset.OFFLINE.modalities),
                full_ready=_modalities_present(local_modalities, AdvioDownloadPreset.FULL.modalities),
            )
            for scene in self.catalog.scenes
        ]

    def download(self, request: AdvioDownloadRequest) -> AdvioDownloadResult:
        """Download selected ADVIO scenes and extract the requested modalities."""
        self.dataset_root.mkdir(parents=True, exist_ok=True)
        self.archive_root.mkdir(parents=True, exist_ok=True)

        sequence_ids = request.sequence_ids or [scene.sequence_id for scene in self.catalog.scenes]
        modalities = request.resolved_modalities()
        downloaded_archives: list[Path] = []
        reused_archives: list[Path] = []
        written_paths: list[Path] = []

        for sequence_id in sequence_ids:
            scene = self.scene(sequence_id)
            if AdvioModality.CALIBRATION in modalities:
                calibration_path = self._ensure_calibration(scene, overwrite=request.overwrite)
                if calibration_path not in written_paths:
                    written_paths.append(calibration_path)

            archive_modalities = tuple(modality for modality in modalities if modality is not AdvioModality.CALIBRATION)
            if not archive_modalities:
                continue

            archive_path, downloaded = self._ensure_archive(scene, overwrite=request.overwrite)
            (downloaded_archives if downloaded else reused_archives).append(archive_path)
            written_paths.extend(
                self._extract_modalities(
                    scene=scene,
                    archive_path=archive_path,
                    modalities=archive_modalities,
                    overwrite=request.overwrite,
                )
            )
            archive_path.unlink()

        return AdvioDownloadResult(
            sequence_ids=sequence_ids,
            modalities=list(modalities),
            downloaded_archives=downloaded_archives,
            reused_archives=reused_archives,
            written_paths=list(dict.fromkeys(written_paths)),
        )

    def _local_modalities(self, scene: AdvioSceneMetadata) -> list[AdvioModality]:
        return local_modalities(self.dataset_root, scene)

    def _ensure_archive(self, scene: AdvioSceneMetadata, *, overwrite: bool) -> tuple[Path, bool]:
        archive_path = self.archive_root / f"{scene.sequence_slug}.zip"
        if archive_path.exists() and not overwrite:
            self._validate_archive_checksum(archive_path, scene.archive_md5)
            return archive_path, False
        self.console.info(f"Downloading {scene.sequence_slug} from {scene.archive_url}.")
        _download_binary_to_path(scene.archive_url, archive_path)
        self._validate_archive_checksum(archive_path, scene.archive_md5)
        return archive_path, True

    def _ensure_calibration(self, scene: AdvioSceneMetadata, *, overwrite: bool) -> Path:
        calibration_path = resolve_calibration_path(self.dataset_root, scene)
        calibration_path.parent.mkdir(parents=True, exist_ok=True)
        if calibration_path.exists() and not overwrite:
            return calibration_path
        calibration_url = f"{self.catalog.upstream.calibration_base_url}{scene.calibration_name}"
        self.console.info(f"Downloading calibration {scene.calibration_name} from {calibration_url}.")
        calibration_path.write_text(_download_text(calibration_url), encoding="utf-8")
        return calibration_path

    def _existing_archive_path(self, scene: AdvioSceneMetadata) -> Path | None:
        archive_path = self.archive_root / f"{scene.sequence_slug}.zip"
        return archive_path if archive_path.exists() else None

    def _validate_archive_checksum(self, archive_path: Path, expected_md5: str) -> None:
        actual_md5 = _md5_for_file(archive_path)
        if actual_md5 != expected_md5:
            msg = (
                f"Checksum mismatch for {archive_path}. Expected {expected_md5}, got {actual_md5}. "
                "Remove the corrupted archive and retry the download."
            )
            raise ValueError(msg)

    def _extract_modalities(
        self,
        *,
        scene: AdvioSceneMetadata,
        archive_path: Path,
        modalities: tuple[AdvioModality, ...],
        overwrite: bool,
    ) -> list[Path]:
        written_paths: list[Path] = []
        matched_members = 0
        with zipfile.ZipFile(archive_path) as archive:
            for member in archive.infolist():
                if member.is_dir():
                    continue
                normalized = _normalize_archive_member(member.filename)
                if normalized is None:
                    continue
                relative_sequence_path = _relative_sequence_path(normalized, scene.sequence_slug)
                if relative_sequence_path is None or not archive_member_matches(
                    relative_sequence_path, scene, modalities
                ):
                    continue
                matched_members += 1
                target_path = self.dataset_root / Path(*normalized)
                if target_path.exists() and not overwrite:
                    written_paths.append(target_path)
                    continue
                _ensure_directory_parent(target_path)
                with archive.open(member, "r") as source, target_path.open("wb") as sink:
                    sink.write(source.read())
                written_paths.append(target_path)

        if matched_members == 0:
            requested = ", ".join(modality.value for modality in modalities)
            msg = f"Archive {archive_path} did not contain any members for requested modalities: {requested}"
            raise ValueError(msg)
        return written_paths


def _modalities_present(local_modalities: list[AdvioModality], required_modalities: tuple[AdvioModality, ...]) -> bool:
    available = set(local_modalities)
    return all(modality in available for modality in required_modalities)


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


def _normalize_archive_member(member_name: str) -> tuple[str, ...] | None:
    parts = tuple(part for part in PurePosixPath(member_name).parts if part not in {"", "."})
    return None if not parts or any(part == ".." for part in parts) else parts


def _relative_sequence_path(normalized_parts: tuple[str, ...], sequence_slug: str) -> PurePosixPath | None:
    root_parts = (
        normalized_parts[1:] if len(normalized_parts) >= 2 and normalized_parts[0] == "data" else normalized_parts
    )
    if not root_parts or root_parts[0] != sequence_slug:
        return None
    return PurePosixPath(*root_parts[1:])


def _download_binary_to_path(url: str, target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "prml-vslam"})
    with tempfile.NamedTemporaryFile(dir=target_path.parent, delete=False) as temp_file:
        temp_path = Path(temp_file.name)
        with urllib.request.urlopen(request, timeout=60) as response:
            while chunk := response.read(_DOWNLOAD_CHUNK_SIZE_BYTES):
                temp_file.write(chunk)
    temp_path.replace(target_path)


def _download_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "prml-vslam"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def _md5_for_file(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        while chunk := handle.read(_DOWNLOAD_CHUNK_SIZE_BYTES):
            digest.update(chunk)
    return digest.hexdigest()
