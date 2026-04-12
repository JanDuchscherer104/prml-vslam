"""Pipeline manifest contracts."""

from __future__ import annotations

from pathlib import Path

from prml_vslam.utils import BaseData


class SequenceManifest(BaseData):
    """Normalized artifact boundary between input ingestion and benchmark execution."""

    sequence_id: str
    """Stable sequence identifier used across artifact stages."""

    video_path: Path | None = None
    """Original source video path kept as provenance when one exists."""

    rgb_dir: Path | None = None
    """Canonical materialized RGB frame directory."""

    timestamps_path: Path | None = None
    """Canonical path to normalized frame timestamps."""

    intrinsics_path: Path | None = None
    """Canonical path to camera intrinsics or calibration metadata."""

    rotation_metadata_path: Path | None = None
    """Canonical path to source-rotation metadata used by offline ingest."""


__all__ = ["SequenceManifest"]
