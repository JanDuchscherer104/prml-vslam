"""Pipeline manifest contracts."""

from __future__ import annotations

from pathlib import Path

from prml_vslam.datasets.contracts import AdvioManifestAssets, DatasetId, DatasetServingConfig
from prml_vslam.utils import BaseData


class SequenceManifest(BaseData):
    """Normalized artifact boundary between input ingestion and benchmark execution."""

    sequence_id: str
    """Stable sequence identifier used across artifact stages."""

    dataset_id: DatasetId | None = None
    """Dataset family when the sequence originated from a repository-owned dataset."""

    dataset_serving: DatasetServingConfig | None = None
    """Typed dataset-serving semantics preserved from the request surface."""

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

    advio: AdvioManifestAssets | None = None
    """ADVIO-specific assets preserved for downstream consumers."""


__all__ = ["SequenceManifest"]
