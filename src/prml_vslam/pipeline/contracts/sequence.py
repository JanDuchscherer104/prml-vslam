"""Normalized offline input-manifest contracts.

This module owns :class:`SequenceManifest`, the offline boundary shared between
source preparation and stage execution. Dataset adapters and video/live source
adapters normalize source-specific details into this DTO so backend wrappers and
pipeline runtime code can consume one consistent input shape.
"""

from __future__ import annotations

from pathlib import Path

from prml_vslam.datasets.contracts import AdvioManifestAssets, DatasetId, DatasetServingConfig
from prml_vslam.utils import BaseData


# TODO: this is a dto / data model that should be defined in a shared model module!
class SequenceManifest(BaseData):
    """Describe the normalized offline input sequence for one run.

    Treat this as the durable offline counterpart to
    :class:`prml_vslam.interfaces.FramePacket`: the manifest describes the
    prepared source artifacts and preserved source metadata that offline or
    streaming sessions can rely on before frame processing begins.
    """

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
