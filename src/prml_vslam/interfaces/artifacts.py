"""Shared artifact reference contracts."""

from __future__ import annotations

from pathlib import Path

from prml_vslam.utils import BaseData


class ArtifactRef(BaseData):
    """Reference one materialized repository artifact by path and fingerprint."""

    path: Path
    kind: str
    fingerprint: str


__all__ = ["ArtifactRef"]
