"""Download manager for static Record3D `.r3d` archive scenes."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from prml_vslam.sources.datasets.contracts import DatasetDownloadResult
from prml_vslam.sources.datasets.fetch import DatasetFetchHelper
from prml_vslam.utils import Console

from .record3d_models import (
    Record3DCatalog,
    Record3DDownloadRequest,
    Record3DSceneMetadata,
)

_SENSITIVE_QUERY_KEYS = {"access_token", "auth", "key", "signature", "token"}


class Record3DDownloadManager:
    """Resolve and download Record3D archive scenes into the dataset root."""

    def __init__(self, dataset_root: Path, *, catalog: Record3DCatalog, console: Console) -> None:
        self.dataset_root = dataset_root
        self.catalog = catalog
        self.console = console
        self._fetch_helper = DatasetFetchHelper()

    def download(self, request: Record3DDownloadRequest) -> DatasetDownloadResult[int]:
        """Download selected Record3D `.r3d` archives with SHA-256 verification."""
        self.dataset_root.mkdir(parents=True, exist_ok=True)
        scenes = self._selected_scenes(request.sequence_ids)
        downloaded_archive_count = 0
        reused_archive_count = 0
        written_paths: set[Path] = set()

        for scene in scenes:
            archive_path, downloaded = self._ensure_archive(scene, overwrite=request.overwrite)
            downloaded_archive_count += int(downloaded)
            reused_archive_count += int(not downloaded)
            written_paths.add(archive_path)

        return DatasetDownloadResult[int](
            sequence_ids=[scene.sequence_index for scene in scenes if scene.sequence_index is not None],
            downloaded_archive_count=downloaded_archive_count,
            reused_archive_count=reused_archive_count,
            written_path_count=len(written_paths),
        )

    def _selected_scenes(self, sequence_ids: list[int]) -> list[Record3DSceneMetadata]:
        if not sequence_ids:
            return list(self.catalog.scenes)
        scenes_by_index = {
            scene.sequence_index: scene for scene in self.catalog.scenes if scene.sequence_index is not None
        }
        missing_sequence_ids = [sequence_id for sequence_id in sequence_ids if sequence_id not in scenes_by_index]
        if missing_sequence_ids:
            upper_bound = max(scenes_by_index) if scenes_by_index else -1
            msg = f"Record3D sequence id must be in [0, {upper_bound}], got {missing_sequence_ids[0]}"
            raise ValueError(msg)
        return [scenes_by_index[sequence_id] for sequence_id in sequence_ids]

    def _ensure_archive(self, scene: Record3DSceneMetadata, *, overwrite: bool) -> tuple[Path, bool]:
        if scene.archive_url is None or scene.archive_sha256 is None:
            raise ValueError(f"Record3D scene is not downloadable: {scene.sequence_id}")
        self._validate_archive_name(scene.archive_name)
        archive_path = self.dataset_root / scene.archive_name
        self.console.info(
            "Resolving Record3D archive %s from %s.",
            scene.archive_name,
            _redact_url_for_log(scene.archive_url),
        )
        return self._fetch_helper.fetch_to_path(
            scene.archive_url,
            archive_path,
            known_hash=f"sha256:{scene.archive_sha256}",
            overwrite=overwrite,
        )

    @staticmethod
    def _validate_archive_name(archive_name: str) -> None:
        path = Path(archive_name)
        if path.name != archive_name or path.suffix != ".r3d":
            raise ValueError(f"Record3D archive name must be a simple `.r3d` filename: {archive_name}")


def _redact_url_for_log(url: str) -> str:
    split = urlsplit(url)
    query = urlencode(
        [
            (key, "<redacted>" if key.lower() in _SENSITIVE_QUERY_KEYS else value)
            for key, value in parse_qsl(split.query, keep_blank_values=True)
        ]
    )
    return urlunsplit((split.scheme, split.netloc, split.path, query, split.fragment))
