"""Shared artifact reference contracts."""

from __future__ import annotations

from pathlib import Path

from prml_vslam.utils import BaseData
from prml_vslam.utils.serialization import stable_hash


class ArtifactRef(BaseData):
    """Reference one materialized repository artifact by path and fingerprint."""

    path: Path
    kind: str
    fingerprint: str


def artifact_ref(path: Path, *, kind: str) -> ArtifactRef:
    """Build one stable artifact reference for a materialized path."""
    resolved_path = path.resolve()
    return ArtifactRef(
        path=resolved_path,
        kind=kind,
        fingerprint=stable_hash({"path": str(resolved_path), "kind": kind}),
    )


__all__ = ["ArtifactRef", "artifact_ref"]
