from __future__ import annotations

from functools import lru_cache
from pathlib import Path, PurePosixPath

from .tum_rgbd_models import (
    TumRgbdCatalog,
    TumRgbdModality,
    TumRgbdSceneMetadata,
)

_BASE_DATASET_URL = "https://cvg.cit.tum.de/data/datasets/rgbd-dataset"
_ARCHIVE_BASE_URL = "https://cvg.cit.tum.de/rgbd/dataset"

_VISTA_FREIBURG1_SCENES = (
    ("freiburg1_360", "fr1/360", "Handheld SLAM", 450_000_000),
    ("freiburg1_floor", "fr1/floor", "Handheld SLAM", 820_000_000),
    ("freiburg1_desk", "fr1/desk", "Handheld SLAM", 360_000_000),
    ("freiburg1_desk2", "fr1/desk2", "Handheld SLAM", 370_000_000),
    ("freiburg1_room", "fr1/room", "Handheld SLAM", 830_000_000),
    ("freiburg1_plant", "fr1/plant", "3D Object Reconstruction", 740_000_000),
    ("freiburg1_teddy", "fr1/teddy", "3D Object Reconstruction", 930_000_000),
    ("freiburg1_xyz", "fr1/xyz", "Testing and Debugging", 470_000_000),
    ("freiburg1_rpy", "fr1/rpy", "Testing and Debugging", 420_000_000),
)
_VISTA_FREIBURG2_3_SCENES = (
    ("freiburg2_360_hemisphere", "fr2/360_hemisphere", "Handheld SLAM", 1_500_000_000),
    ("freiburg2_360_kidnap", "fr2/360_kidnap", "Handheld SLAM", 740_000_000),
    ("freiburg2_desk", "fr2/desk", "Handheld SLAM", 2_010_000_000),
    ("freiburg2_large_with_loop", "fr2/large_with_loop", "Handheld SLAM", 2_830_000_000),
    ("freiburg2_rpy", "fr2/rpy", "Testing and Debugging", 2_130_000_000),
    ("freiburg2_xyz", "fr2/xyz", "Testing and Debugging", 2_390_000_000),
    ("freiburg3_cabinet", "fr3/cabinet", "3D Object Reconstruction", 520_000_000),
    ("freiburg3_large_cabinet", "fr3/large_cabinet", "3D Object Reconstruction", 480_000_000),
    ("freiburg3_long_office_household", "fr3/long_office_household", "Handheld SLAM", 1_580_000_000),
    ("freiburg3_teddy", "fr3/teddy", "3D Object Reconstruction", 1_300_000_000),
)
_CATALOG_SCENES = _VISTA_FREIBURG1_SCENES + _VISTA_FREIBURG2_3_SCENES


@lru_cache(maxsize=1)
def load_tum_rgbd_catalog() -> TumRgbdCatalog:
    return TumRgbdCatalog(
        dataset_id="tum_rgbd",
        dataset_label="TUM RGB-D",
        upstream={"dataset_url": _BASE_DATASET_URL, "file_formats_url": f"{_BASE_DATASET_URL}/file_formats"},
        scenes=[
            TumRgbdSceneMetadata(
                sequence_id=sequence_id,
                folder_name=f"rgbd_dataset_{sequence_id}",
                display_name=display_name,
                category=category,
                archive_url=_archive_url(sequence_id),
                archive_size_bytes=archive_size_bytes,
            )
            for sequence_id, display_name, category, archive_size_bytes in _CATALOG_SCENES
        ],
    )


def scene_for_sequence_id(catalog: TumRgbdCatalog, sequence_id: str) -> TumRgbdSceneMetadata:
    normalized = _normalize_sequence_id(sequence_id)
    try:
        return next(
            scene
            for scene in catalog.scenes
            if scene.sequence_id == normalized or scene.folder_name == sequence_id or scene.display_name == sequence_id
        )
    except StopIteration as exc:
        raise KeyError(f"Unknown TUM RGB-D scene id: {sequence_id}") from exc


def resolve_existing_sequence_dir(dataset_root: Path, sequence_id: str) -> Path | None:
    normalized = _normalize_sequence_id(sequence_id)
    folder_name = f"rgbd_dataset_{normalized}"
    for root in (dataset_root, dataset_root / "data"):
        for candidate_name in (folder_name, normalized, sequence_id):
            candidate = root / candidate_name
            if candidate.is_dir():
                return candidate
    return None


def resolve_sequence_dir(dataset_root: Path, scene: TumRgbdSceneMetadata) -> Path:
    sequence_dir = resolve_existing_sequence_dir(dataset_root, scene.sequence_id)
    if sequence_dir is None:
        raise FileNotFoundError(f"TUM RGB-D sequence {scene.sequence_id} is not available under {dataset_root}")
    return sequence_dir


def resolve_existing_reference_tum(dataset_root: Path, sequence_slug: str) -> Path | None:
    sequence_dir = resolve_existing_sequence_dir(dataset_root, sequence_slug)
    if sequence_dir is None:
        return None
    for candidate in (
        sequence_dir / "evaluation" / "ground_truth.tum",
        sequence_dir / "groundtruth.txt",
        sequence_dir / "pose.txt",
    ):
        if candidate.exists():
            return candidate
    return None


def list_local_sequence_ids(dataset_root: Path) -> list[str]:
    sequence_ids: set[str] = set()
    for root in (dataset_root, dataset_root / "data"):
        if not root.exists():
            continue
        for candidate in root.iterdir():
            if not candidate.is_dir():
                continue
            sequence_id = _normalize_sequence_id(candidate.name)
            if sequence_id.startswith("freiburg"):
                sequence_ids.add(sequence_id)
    return sorted(sequence_ids)


def local_modalities(dataset_root: Path, scene: TumRgbdSceneMetadata) -> list[TumRgbdModality]:
    sequence_dir = resolve_existing_sequence_dir(dataset_root, scene.sequence_id)
    if sequence_dir is None:
        return []
    return [modality for modality in TumRgbdModality if _modality_present(sequence_dir=sequence_dir, modality=modality)]


def archive_member_matches(relative_path: PurePosixPath, modalities: tuple[TumRgbdModality, ...]) -> bool:
    if not relative_path.parts:
        return False
    name = relative_path.name
    first_part = relative_path.parts[0]
    return any(
        (modality is TumRgbdModality.RGB and (first_part == "rgb" or name == "rgb.txt"))
        or (modality is TumRgbdModality.DEPTH and (first_part == "depth" or name == "depth.txt"))
        or (modality is TumRgbdModality.GROUND_TRUTH and name in {"groundtruth.txt", "pose.txt"})
        for modality in modalities
    )


def _modality_present(*, sequence_dir: Path, modality: TumRgbdModality) -> bool:
    match modality:
        case TumRgbdModality.RGB:
            return (sequence_dir / "rgb.txt").exists() and (sequence_dir / "rgb").is_dir()
        case TumRgbdModality.DEPTH:
            return (sequence_dir / "depth.txt").exists() and (sequence_dir / "depth").is_dir()
        case TumRgbdModality.GROUND_TRUTH:
            return (sequence_dir / "groundtruth.txt").exists() or (sequence_dir / "pose.txt").exists()


def _archive_url(sequence_id: str) -> str:
    freiburg, _ = sequence_id.split("_", maxsplit=1)
    return f"{_ARCHIVE_BASE_URL}/{freiburg.replace('freiburg', 'freiburg')}/rgbd_dataset_{sequence_id}.tgz"


def _normalize_sequence_id(sequence_id: str) -> str:
    return sequence_id.removeprefix("rgbd_dataset_").replace("/", "_")
