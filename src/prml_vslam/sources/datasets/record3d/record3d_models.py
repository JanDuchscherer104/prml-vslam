"""Typed models for offline Record3D dataset archives."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import ConfigDict, Field, field_validator

from prml_vslam.sources.datasets.contracts import ReferenceCloudConfig
from prml_vslam.utils import BaseConfig, BaseData


class Record3DPoseFrameMode(StrEnum):
    """Pose-frame conversion policy for Record3D metadata poses."""

    METADATA = "record3d_metadata"
    METADATA_P_YZ_FLIP = "record3d_metadata_p_yz_flip"


class Record3DMaterializationConfig(BaseConfig):
    """Policy for deriving metric artifacts from one Record3D archive."""

    model_config = ConfigDict(extra="forbid")

    depth_unit_scale: float = Field(default=1.0, gt=0.0)
    pose_frame_mode: Record3DPoseFrameMode = Record3DPoseFrameMode.METADATA_P_YZ_FLIP


class Record3DSequenceConfig(BaseConfig):
    """Configure one local `.r3d` archive sequence."""

    dataset_root: Path = Path(".data/record3d")
    sequence_id: str
    materialization: Record3DMaterializationConfig = Field(default_factory=Record3DMaterializationConfig)
    reference_cloud: ReferenceCloudConfig = Field(default_factory=lambda: ReferenceCloudConfig(min_confidence=1))


class Record3DSceneMetadata(BaseData):
    """Local metadata for one Record3D archive."""

    sequence_id: str
    archive_name: str
    display_name: str
    sequence_index: int | None = None
    archive_url: str | None = None
    archive_sha256: str | None = None
    archive_size_bytes: int = 0


class Record3DCatalog(BaseData):
    """Small catalog wrapper used by the shared dataset service base."""

    dataset_id: Literal["record3d_dataset"] = "record3d_dataset"
    dataset_label: str = "Record3D"
    scenes: list[Record3DSceneMetadata] = Field(default_factory=list)


class Record3DDownloadRequest(BaseConfig):
    """Explicit Record3D archive download selection used by the CLI."""

    sequence_ids: list[int] = Field(default_factory=list)
    """Selected zero-based sequence indices. An empty selection means all scenes."""

    overwrite: bool = False
    """Whether existing `.r3d` archives should be re-downloaded."""

    @field_validator("sequence_ids")
    @classmethod
    def validate_sequence_ids(cls, value: list[int]) -> list[int]:
        """Normalize explicit scene selections and reject negative indices."""
        normalized = sorted(set(value))
        for sequence_id in normalized:
            if sequence_id < 0:
                msg = f"Record3D sequence id must be non-negative, got {sequence_id}"
                raise ValueError(msg)
        return normalized


__all__ = [
    "Record3DCatalog",
    "Record3DDownloadRequest",
    "Record3DMaterializationConfig",
    "Record3DPoseFrameMode",
    "Record3DSceneMetadata",
    "Record3DSequenceConfig",
]
