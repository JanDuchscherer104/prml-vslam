"""Workspace-owned manifests for prepared inputs and materialized captures."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field

from prml_vslam.utils import BaseData


class FrameSample(BaseData):
    """One decoded or materialized RGB frame in a capture manifest."""

    index: int
    """Zero-based frame index within the materialized sequence."""

    source_index: int
    """Zero-based source frame index before stride-based subsampling."""

    timestamp_seconds: float
    """Source timestamp in seconds, if known or approximated."""

    image_path: Path
    """Absolute path to the materialized RGB image file."""


class CaptureManifest(BaseData):
    """Persistent metadata for a materialized SLAM-ready image sequence."""

    source_path: Path
    """Original capture path used to create the materialized sequence."""

    source_kind: Literal["video", "image_dir"]
    """Type of the original capture source."""

    frame_stride: int = 1
    """Stride used when sampling frames from the source."""

    fps: float | None = None
    """Detected source frame rate when the source is a video."""

    frames: list[FrameSample] = Field(default_factory=list)
    """Sampled frames written for downstream backends."""


class PreparedInput(BaseData):
    """Method-ready input description derived from a shared capture source."""

    source_path: Path
    """Original input path passed by the caller."""

    resolved_input_path: Path
    """Concrete input path that the upstream backend should consume."""

    frames_dir: Path | None = None
    """Directory containing materialized RGB frames when one was created."""

    image_glob: str | None = None
    """Glob pattern suitable for backends that consume image sequences."""

    manifest_path: Path | None = None
    """JSON manifest path describing the materialized frame sequence."""

    manifest: CaptureManifest | None = None
    """Loaded manifest object for timestamp lookup and debugging."""


__all__ = [
    "CaptureManifest",
    "FrameSample",
    "PreparedInput",
]
