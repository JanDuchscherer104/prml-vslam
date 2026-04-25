"""Dataset lookup helpers kept outside dataset identifier contracts."""

from __future__ import annotations

from pathlib import Path

from .advio.advio_layout import list_local_sequence_ids, resolve_existing_reference_tum
from .contracts import DatasetId
from .tum_rgbd.tum_rgbd_layout import (
    list_local_sequence_ids as list_local_tum_rgbd_sequence_ids,
)
from .tum_rgbd.tum_rgbd_layout import (
    resolve_existing_reference_tum as resolve_existing_tum_rgbd_reference_tum,
)


def list_sequence_slugs(dataset_id: DatasetId, dataset_root: Path) -> list[str]:
    """Return local sequence slugs available for one dataset family."""
    match dataset_id:
        case DatasetId.ADVIO:
            return [f"{dataset_id.value}-{sequence_id:02d}" for sequence_id in list_local_sequence_ids(dataset_root)]
        case DatasetId.TUM_RGBD:
            return list_local_tum_rgbd_sequence_ids(dataset_root)


def resolve_reference_path(dataset_id: DatasetId, dataset_root: Path, sequence_slug: str) -> Path | None:
    """Return the canonical default reference trajectory for one dataset sequence."""
    match dataset_id:
        case DatasetId.ADVIO:
            return resolve_existing_reference_tum(dataset_root, sequence_slug)
        case DatasetId.TUM_RGBD:
            return resolve_existing_tum_rgbd_reference_tum(dataset_root, sequence_slug)
