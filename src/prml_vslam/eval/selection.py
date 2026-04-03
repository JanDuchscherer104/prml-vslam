from __future__ import annotations

from pathlib import Path

from prml_vslam.datasets.interfaces import DatasetId
from prml_vslam.eval.interfaces import DiscoveredRun, SelectionSnapshot
from prml_vslam.utils.path_config import PathConfig


def resolve_dataset_root(path_config: PathConfig, dataset: DatasetId) -> Path:
    """Return the repo-owned root for one dataset."""
    match dataset:
        case DatasetId.ADVIO:
            return path_config.resolve_dataset_dir(dataset.value)
        case _:
            raise NotImplementedError(f"Unsupported dataset: {dataset!r}")


def list_sequences(*, dataset: DatasetId, dataset_root: Path) -> list[str]:
    """List locally available sequence slugs for a resolved dataset root."""
    prefix = f"{dataset.value}-"
    return sorted(
        {
            path.name
            for candidate_root in (dataset_root, dataset_root / "data")
            if candidate_root.exists()
            for path in candidate_root.iterdir()
            if path.is_dir() and path.name.startswith(prefix)
        }
    )


def resolve_reference_path(*, dataset_root: Path, sequence_slug: str) -> Path | None:
    """Return the local TUM reference trajectory when it already exists."""
    sequence_root = dataset_root / sequence_slug
    for candidate in (
        sequence_root / "ground-truth" / "ground_truth.tum",
        sequence_root / "ground_truth.tum",
        sequence_root / "evaluation" / "ground_truth.tum",
    ):
        if candidate.exists():
            return candidate
    return None


def build_selection(
    *,
    dataset: DatasetId,
    dataset_root: Path,
    sequence_slug: str,
    run: DiscoveredRun,
) -> SelectionSnapshot:
    """Build the selection snapshot used by the metrics page and tests."""
    return SelectionSnapshot(
        dataset=dataset,
        sequence_slug=sequence_slug,
        dataset_root=dataset_root,
        reference_path=resolve_reference_path(dataset_root=dataset_root, sequence_slug=sequence_slug),
        run=run,
    )


__all__ = [
    "build_selection",
    "list_sequences",
    "resolve_dataset_root",
    "resolve_reference_path",
]
