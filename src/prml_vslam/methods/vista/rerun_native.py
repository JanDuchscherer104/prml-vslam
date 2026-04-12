"""Helpers for preserved native ViSTA Rerun recordings."""

from __future__ import annotations

from pathlib import Path

from prml_vslam.pipeline.contracts.artifacts import ArtifactRef


def native_rerun_artifact(path: Path | None) -> ArtifactRef | None:
    """Return a preserved native `.rrd` artifact when one exists."""
    if path is None or not path.exists():
        return None
    return ArtifactRef(path=path.resolve(), kind="rrd", fingerprint=f"{path.name}-native")


__all__ = ["native_rerun_artifact"]
