from __future__ import annotations

import json
from dataclasses import dataclass
from fnmatch import fnmatch
from functools import lru_cache
from pathlib import Path, PurePosixPath

from .advio_models import AdvioCatalog, AdvioModality, AdvioSceneMetadata

_CATALOG_PATH = Path(__file__).with_name("advio_catalog.json")


@dataclass(frozen=True)
class _RelativePathSpec:
    parent_parts: tuple[str, ...]
    names: tuple[str, ...] = ()
    glob_pattern: str | None = None
    scene_attr: str | None = None
    recurse: bool = False

    def resolve(self, root: Path, scene: AdvioSceneMetadata) -> Path | None:
        directory = root.joinpath(*self.parent_parts)
        if self.glob_pattern is not None:
            return next(directory.glob(self.glob_pattern), None)
        names = self.names or (str(getattr(scene, self.scene_attr or "")),)
        return next((path for name in names if (path := directory / name).exists()), None)

    def matches(self, relative_path: PurePosixPath, scene: AdvioSceneMetadata) -> bool:
        if relative_path.parts[: len(self.parent_parts)] != self.parent_parts:
            return False
        if self.recurse:
            return True
        remainder = relative_path.parts[len(self.parent_parts) :]
        if len(remainder) != 1:
            return False
        if self.glob_pattern is not None:
            return fnmatch(remainder[0], self.glob_pattern)
        names = self.names or (str(getattr(scene, self.scene_attr or "")),)
        return remainder[0] in names


@dataclass(frozen=True)
class _ModalitySpec:
    sequence_specs: tuple[_RelativePathSpec, ...] = ()
    dataset_specs: tuple[_RelativePathSpec, ...] = ()
    archive_specs: tuple[_RelativePathSpec, ...] = ()


_CALIBRATION = _RelativePathSpec(("calibration",), scene_attr="calibration_name")
_GROUND_TRUTH_POSE = _RelativePathSpec(("ground-truth",), names=("poses.csv", "pose.csv"))
_GROUND_TRUTH_FIXPOINTS = _RelativePathSpec(("ground-truth",), names=("fixpoints.csv",))
_IPHONE_FRAMES_MOV = _RelativePathSpec(("iphone",), names=("frames.mov",))
_IPHONE_FRAMES_CSV = _RelativePathSpec(("iphone",), names=("frames.csv",))
_IPHONE_PLATFORM_LOCATION = _RelativePathSpec(("iphone",), names=("platform-location.csv", "platform-locations.csv"))
_IPHONE_ACCELEROMETER = _RelativePathSpec(("iphone",), names=("accelerometer.csv",))
_IPHONE_GYROSCOPE = _RelativePathSpec(("iphone",), names=("gyroscope.csv", "gyro.csv"))
_IPHONE_MAGNETOMETER = _RelativePathSpec(("iphone",), names=("magnetometer.csv",))
_IPHONE_BAROMETER = _RelativePathSpec(("iphone",), names=("barometer.csv",))
_IPHONE_ARKIT = _RelativePathSpec(("iphone",), names=("arkit.csv",))
_PIXEL_ARCORE = _RelativePathSpec(("pixel",), names=("arcore.csv",))
_TANGO_FRAMES_MOV = _RelativePathSpec(("tango",), names=("frames.mov",))
_TANGO_FRAMES_CSV = _RelativePathSpec(("tango",), names=("frames.csv",))
_TANGO_RAW = _RelativePathSpec(("tango",), names=("raw.csv",))
_TANGO_AREA_LEARNING = _RelativePathSpec(("tango",), names=("area-learning.csv",))
_TANGO_POINT_CLOUD = _RelativePathSpec(("tango",), glob_pattern="point-cloud*.csv")
_TANGO_ARCHIVE = _RelativePathSpec(("tango",), recurse=True)

_MODALITY_SPECS = {
    AdvioModality.CALIBRATION: _ModalitySpec(dataset_specs=(_CALIBRATION,)),
    AdvioModality.GROUND_TRUTH: _ModalitySpec(
        sequence_specs=(_GROUND_TRUTH_POSE, _GROUND_TRUTH_FIXPOINTS),
        archive_specs=(_GROUND_TRUTH_POSE, _GROUND_TRUTH_FIXPOINTS),
    ),
    AdvioModality.IPHONE_VIDEO: _ModalitySpec(
        sequence_specs=(_IPHONE_FRAMES_MOV, _IPHONE_FRAMES_CSV),
        archive_specs=(_IPHONE_FRAMES_MOV, _IPHONE_FRAMES_CSV),
    ),
    AdvioModality.IPHONE_SENSORS: _ModalitySpec(
        sequence_specs=(
            _IPHONE_PLATFORM_LOCATION,
            _IPHONE_ACCELEROMETER,
            _IPHONE_GYROSCOPE,
            _IPHONE_MAGNETOMETER,
            _IPHONE_BAROMETER,
        ),
        archive_specs=(
            _IPHONE_PLATFORM_LOCATION,
            _IPHONE_ACCELEROMETER,
            _IPHONE_GYROSCOPE,
            _IPHONE_MAGNETOMETER,
            _IPHONE_BAROMETER,
        ),
    ),
    AdvioModality.IPHONE_ARKIT: _ModalitySpec(sequence_specs=(_IPHONE_ARKIT,), archive_specs=(_IPHONE_ARKIT,)),
    AdvioModality.PIXEL_ARCORE: _ModalitySpec(sequence_specs=(_PIXEL_ARCORE,), archive_specs=(_PIXEL_ARCORE,)),
    AdvioModality.TANGO: _ModalitySpec(
        sequence_specs=(
            _TANGO_FRAMES_MOV,
            _TANGO_FRAMES_CSV,
            _TANGO_RAW,
            _TANGO_AREA_LEARNING,
            _TANGO_POINT_CLOUD,
        ),
        archive_specs=(_TANGO_ARCHIVE,),
    ),
}


@lru_cache(maxsize=1)
def load_advio_catalog() -> AdvioCatalog:
    return AdvioCatalog.model_validate(json.loads(_CATALOG_PATH.read_text(encoding="utf-8")))


def scene_for_sequence_id(catalog: AdvioCatalog, sequence_id: int) -> AdvioSceneMetadata:
    try:
        return next(scene for scene in catalog.scenes if scene.sequence_id == sequence_id)
    except StopIteration as exc:
        raise KeyError(f"Unknown ADVIO scene id: {sequence_id}") from exc


def resolve_existing_sequence_dir(dataset_root: Path, sequence_slug: str) -> Path | None:
    for candidate in (dataset_root / sequence_slug, dataset_root / "data" / sequence_slug):
        if candidate.is_dir():
            return candidate
    return None


def resolve_sequence_dir(dataset_root: Path, scene: AdvioSceneMetadata) -> Path:
    sequence_dir = resolve_existing_sequence_dir(dataset_root, scene.sequence_slug)
    if sequence_dir is None:
        raise FileNotFoundError(f"ADVIO sequence {scene.sequence_slug} is not available under {dataset_root}")
    return sequence_dir


def resolve_existing_reference_tum(dataset_root: Path, sequence_slug: str) -> Path | None:
    sequence_dir = resolve_existing_sequence_dir(dataset_root, sequence_slug)
    if sequence_dir is None:
        return None
    for candidate in (
        sequence_dir / "ground-truth" / "ground_truth.tum",
        sequence_dir / "ground_truth.tum",
        sequence_dir / "evaluation" / "ground_truth.tum",
    ):
        if candidate.exists():
            return candidate
    return None


def list_local_sequence_ids(dataset_root: Path) -> list[int]:
    sequence_ids: set[int] = set()
    for root in (dataset_root, dataset_root / "data"):
        if not root.exists():
            continue
        for candidate in root.iterdir():
            if not candidate.is_dir() or not candidate.name.startswith("advio-"):
                continue
            try:
                sequence_ids.add(int(candidate.name.split("-")[1]))
            except (IndexError, ValueError):
                continue
    return sorted(sequence_ids)


def resolve_calibration_path(dataset_root: Path, scene: AdvioSceneMetadata) -> Path:
    return dataset_root / "calibration" / scene.calibration_name


def resolve_ground_truth_csv(sequence_dir: Path, scene: AdvioSceneMetadata) -> Path:
    return _require_path(sequence_dir, scene, _GROUND_TRUTH_POSE, "ground-truth pose CSV")


def resolve_optional_arkit_csv(sequence_dir: Path, scene: AdvioSceneMetadata) -> Path | None:
    return _IPHONE_ARKIT.resolve(sequence_dir, scene)


def resolve_optional_gyroscope_csv(sequence_dir: Path, scene: AdvioSceneMetadata) -> Path | None:
    return _IPHONE_GYROSCOPE.resolve(sequence_dir, scene)


def local_modalities(dataset_root: Path, scene: AdvioSceneMetadata) -> list[AdvioModality]:
    sequence_dir = resolve_existing_sequence_dir(dataset_root, scene.sequence_slug)
    return [
        modality
        for modality in AdvioModality
        if _modality_present(_MODALITY_SPECS[modality], dataset_root, sequence_dir, scene)
    ]


def archive_member_matches(
    relative_path: PurePosixPath, scene: AdvioSceneMetadata, modalities: tuple[AdvioModality, ...]
) -> bool:
    return any(
        requirement.matches(relative_path, scene)
        for modality in modalities
        for requirement in _MODALITY_SPECS[modality].archive_specs
    )


def _modality_present(
    spec: _ModalitySpec,
    dataset_root: Path,
    sequence_dir: Path | None,
    scene: AdvioSceneMetadata,
) -> bool:
    if any(requirement.resolve(dataset_root, scene) is None for requirement in spec.dataset_specs):
        return False
    if not spec.sequence_specs:
        return True
    return sequence_dir is not None and all(
        requirement.resolve(sequence_dir, scene) is not None for requirement in spec.sequence_specs
    )


def _require_path(root: Path, scene: AdvioSceneMetadata, spec: _RelativePathSpec, label: str) -> Path:
    path = spec.resolve(root, scene)
    if path is None:
        raise FileNotFoundError(f"Required ADVIO {label} is missing under {root}")
    return path
