"""Filesystem layout helpers for local Record3D `.r3d` archives."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import parse_qsl, quote, urlencode, urlparse

from .record3d_models import Record3DCatalog, Record3DSceneMetadata

_ZENODO_RECORD_ID = "20591352"
_ZENODO_RECORD_URL_ENV = "PRML_VSLAM_RECORD3D_ZENODO_RECORD_URL"
_ZENODO_RECORD_BASE_URL = f"https://zenodo.org/records/{_ZENODO_RECORD_ID}"
_RECORD3D_SCENES: tuple[tuple[str, str], ...] = (
    ("2026-06-03--18-17-10.r3d", "b281dd4c65a98c5957608f3ef156428a1f52177304c2c354355e58652313814c"),
    ("2026-06-03--18-20-22.r3d", "c08b45dbfa51fe41a14939fa391fae60af5ad6f24a284c90ad5ddbc2efbe0ae4"),
    ("2026-06-03--18-24-27.r3d", "0ef088ed96515655a642b692a6193443dc78bd76196ccf14d1b6b28d0e338b64"),
    ("2026-06-03--18-26-32.r3d", "d76050f5edac45644dd3aafa20e1b73336959a4282c5494ff30c748c86288fc5"),
    ("2026-06-03--18-27-25.r3d", "dc7f97ff84c7437ca7a0cee9f0aa88653c83453ca0a58b612851e04389581993"),
    ("2026-06-03--18-29-08.r3d", "19d8f70a01db18515a93d2642d65fda04cd559a46406d5ee5a4d2f360e96c9d8"),
    ("2026-06-03--18-32-27.r3d", "e2718ce2b78411351eafec517d1b4882201d2f7c521251ec6ed608569f5efd73"),
    ("2026-06-03--18-35-44.r3d", "e2b0edb31426885e8cdf548ec441d717ed3a572d5c2a67d2cd51588cdf749fa3"),
)


def load_record3d_catalog() -> Record3DCatalog:
    """Return the static catalog of downloadable Record3D archives."""
    return Record3DCatalog(
        scenes=[
            Record3DSceneMetadata(
                sequence_index=index,
                sequence_id=Path(archive_name).stem,
                archive_name=archive_name,
                display_name=Path(archive_name).stem,
                archive_url=archive_url(archive_name),
                archive_sha256=archive_sha256,
            )
            for index, (archive_name, archive_sha256) in enumerate(_RECORD3D_SCENES)
        ]
    )


def archive_url(archive_name: str) -> str:
    """Return the default Zenodo file URL for one Record3D archive."""
    record_url = os.environ.get(_ZENODO_RECORD_URL_ENV, _ZENODO_RECORD_BASE_URL)
    parsed = urlparse(record_url)
    base_url = record_url.split("?", maxsplit=1)[0].rstrip("/")
    query_items = [(key, value) for key, value in parse_qsl(parsed.query) if key in {"preview", "token"}]
    query_items.append(("download", "1"))
    return f"{base_url}/files/{quote(archive_name)}?{urlencode(query_items)}"


def normalize_sequence_id(sequence_id: str) -> str:
    """Normalize UI and path-ish sequence names into archive stems."""
    value = Path(sequence_id).name
    return value.removesuffix(".r3d")


def archive_path_for_sequence(dataset_root: Path, sequence_id: str) -> Path:
    """Return the expected archive path for one sequence id."""
    normalized = normalize_sequence_id(sequence_id)
    direct = dataset_root / f"{normalized}.r3d"
    if direct.exists():
        return direct
    nested = dataset_root / normalized / f"{normalized}.r3d"
    return nested if nested.exists() else direct


def cache_dir_for_sequence(dataset_root: Path, sequence_id: str) -> Path:
    """Return the default local materialization cache for one archive."""
    return dataset_root / ".record3d_cache" / normalize_sequence_id(sequence_id)


def list_local_sequence_ids(dataset_root: Path) -> list[str]:
    """Return local `.r3d` archive stems under the dataset root."""
    if not dataset_root.exists():
        return []
    archive_paths = list(dataset_root.glob("*.r3d")) + list(dataset_root.glob("*/*.r3d"))
    return sorted({normalize_sequence_id(path.name) for path in archive_paths if path.is_file()})


def scene_for_sequence_id(catalog: Record3DCatalog, dataset_root: Path, sequence_id: str) -> Record3DSceneMetadata:
    """Resolve one sequence id from the static catalog or local disk."""
    normalized = normalize_sequence_id(sequence_id)
    for scene in catalog.scenes:
        if (
            str(scene.sequence_index) == sequence_id
            or scene.sequence_id == normalized
            or scene.archive_name == f"{normalized}.r3d"
        ):
            return scene
    archive_path = archive_path_for_sequence(dataset_root, normalized)
    if not archive_path.exists():
        raise FileNotFoundError(f"Record3D archive is missing: {archive_path}")
    return Record3DSceneMetadata(
        sequence_id=normalized,
        archive_name=archive_path.name,
        display_name=normalized,
        archive_size_bytes=archive_path.stat().st_size,
    )


def resolve_existing_reference_tum(dataset_root: Path, sequence_slug: str) -> Path | None:
    """Return the materialized ARKit TUM trajectory path when it exists."""
    sequence_id = normalize_sequence_id(sequence_slug)
    path = cache_dir_for_sequence(dataset_root, sequence_id) / "evaluation" / "record3d_arkit.tum"
    return path if path.exists() else None


__all__ = [
    "archive_url",
    "archive_path_for_sequence",
    "cache_dir_for_sequence",
    "list_local_sequence_ids",
    "load_record3d_catalog",
    "normalize_sequence_id",
    "resolve_existing_reference_tum",
    "scene_for_sequence_id",
]
