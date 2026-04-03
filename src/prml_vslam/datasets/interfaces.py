"""Dataset-owned identifiers."""

from __future__ import annotations

from enum import StrEnum


class DatasetId(StrEnum):
    """Datasets exposed through evaluation surfaces."""

    ADVIO = "advio"

    @property
    def label(self) -> str:
        """Return the short user-facing dataset label."""
        return {
            DatasetId.ADVIO: "ADVIO",
        }[self]


__all__ = ["DatasetId"]
