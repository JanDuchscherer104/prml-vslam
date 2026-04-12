"""Dataset-owned contracts."""

from __future__ import annotations

from enum import StrEnum


class DatasetId(StrEnum):
    """Datasets exposed through evaluation surfaces."""

    ADVIO = "advio"

    @property
    def label(self) -> str:
        """Return the short user-facing dataset label."""
        return self.value.upper()


__all__ = ["DatasetId"]
