from __future__ import annotations

import shutil
from pathlib import Path
from urllib.parse import unquote, urlparse

import pooch


class DatasetFetchHelper:
    """Thin cache-aware fetch helper for dataset-owned assets."""

    def __init__(self, *, user_agent: str = "prml-vslam") -> None:
        self._http_downloader = pooch.HTTPDownloader(headers={"User-Agent": user_agent}, progressbar=False)

    def fetch_to_path(
        self,
        url: str,
        target_path: Path,
        *,
        known_hash: str | None = None,
        overwrite: bool = False,
    ) -> tuple[Path, bool]:
        """Fetch one asset into a stable local path and report whether it was refreshed."""
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if overwrite and target_path.exists():
            target_path.unlink()

        downloaded = _needs_refresh(target_path, known_hash=known_hash)
        local_source = _resolve_local_source(url)
        if local_source is not None:
            _copy_local_file(local_source, target_path, known_hash=known_hash, refresh=downloaded)
            return target_path, downloaded

        fetched_path = Path(
            pooch.retrieve(
                url=url,
                path=target_path.parent,
                fname=target_path.name,
                known_hash=known_hash,
                downloader=self._http_downloader,
                progressbar=False,
            )
        )
        return fetched_path, downloaded


def _copy_local_file(source_path: Path, target_path: Path, *, known_hash: str | None, refresh: bool) -> None:
    if known_hash is not None and not _hash_matches(source_path, known_hash):
        msg = f"Checksum mismatch for local dataset asset {source_path}."
        raise ValueError(msg)
    if refresh:
        shutil.copyfile(source_path, target_path)


def _needs_refresh(path: Path, *, known_hash: str | None) -> bool:
    if not path.exists():
        return True
    return known_hash is not None and not _hash_matches(path, known_hash)


def _hash_matches(path: Path, known_hash: str) -> bool:
    algorithm, expected_hash = _parse_known_hash(known_hash)
    return pooch.file_hash(path, alg=algorithm) == expected_hash


def _parse_known_hash(known_hash: str) -> tuple[str, str]:
    if ":" in known_hash:
        algorithm, expected_hash = known_hash.split(":", maxsplit=1)
        return algorithm, expected_hash
    return "md5", known_hash


def _resolve_local_source(url: str) -> Path | None:
    parsed = urlparse(url)
    if parsed.scheme != "file":
        return None
    return Path(unquote(parsed.path))
