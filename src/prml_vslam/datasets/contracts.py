"""Dataset-owned contracts."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path


class DatasetId(StrEnum):
    """Datasets exposed through evaluation surfaces."""

    ADVIO = "advio"

    @property
    def label(self) -> str:
        """Return the short user-facing dataset label."""
        return {
            DatasetId.ADVIO: "ADVIO",
        }[self]

    def list_sequence_slugs(self, dataset_root: Path) -> list[str]:
        """Return local sequence slugs available for this dataset."""
        match self:
            case DatasetId.ADVIO:
                from .advio_layout import list_local_sequence_ids

                return [f"{self.value}-{sequence_id:02d}" for sequence_id in list_local_sequence_ids(dataset_root)]

    def resolve_reference_path(self, dataset_root: Path, sequence_slug: str) -> Path | None:
        """Return existing reference trajectory path for one dataset sequence."""
        match self:
            case DatasetId.ADVIO:
                from .advio_layout import resolve_existing_reference_tum

                return resolve_existing_reference_tum(dataset_root, sequence_slug)


__all__ = ["DatasetId"]
