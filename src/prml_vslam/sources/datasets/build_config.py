"""TOML contracts for normalized datastore batch builds."""

from __future__ import annotations

from typing import Annotated, Literal, Self

from pydantic import ConfigDict, Field, model_validator

from prml_vslam.sources.config import AdvioSourceConfig, Record3DDatasetSourceConfig, TumRgbdSourceConfig
from prml_vslam.sources.datasets.contracts import ReferenceCloudConfig
from prml_vslam.utils import BaseConfig


class NormalizedCadenceConfig(BaseConfig):
    """Normalize-time frame selection that contributes to datastore identity."""

    normalized_frame_stride: int | None = Field(default=None, ge=1)
    normalized_target_fps: float | None = Field(default=None, gt=0.0)

    @model_validator(mode="after")
    def validate_single_normalized_sampling_mode(self) -> Self:
        if self.normalized_target_fps is not None and self.normalized_frame_stride not in (None, 1):
            raise ValueError("Configure either `normalized_frame_stride` or `normalized_target_fps`, not both.")
        return self


class AdvioNormalizedDatasetBuildSource(NormalizedCadenceConfig):
    """Grouped ADVIO normalized-store build settings."""

    model_config = ConfigDict(extra="forbid")

    source_id: Literal["advio"] = "advio"
    sequence_ids: list[str] = Field(min_length=1)
    rgb_max_width_px: int = Field(default=392, ge=1)
    rgb_dimension_multiple: int = Field(default=14, ge=1)

    def source_configs(self) -> list[AdvioSourceConfig]:
        """Expand this dataset group into concrete per-sequence source configs."""
        return [
            AdvioSourceConfig(
                sequence_id=sequence_id,
                normalized_frame_stride=self.normalized_frame_stride,
                normalized_target_fps=self.normalized_target_fps,
                rgb_max_width_px=self.rgb_max_width_px,
                rgb_dimension_multiple=self.rgb_dimension_multiple,
            )
            for sequence_id in self.sequence_ids
        ]


class TumRgbdNormalizedDatasetBuildSource(NormalizedCadenceConfig):
    """Grouped TUM RGB-D normalized-store build settings."""

    model_config = ConfigDict(extra="forbid")

    source_id: Literal["tum_rgbd"] = "tum_rgbd"
    sequence_ids: list[str] = Field(min_length=1)
    reference_cloud: ReferenceCloudConfig = Field(default_factory=ReferenceCloudConfig)
    rgb_max_width_px: int = Field(default=392, ge=1)
    rgb_dimension_multiple: int = Field(default=14, ge=1)

    def source_configs(self) -> list[TumRgbdSourceConfig]:
        """Expand this dataset group into concrete per-sequence source configs."""
        return [
            TumRgbdSourceConfig(
                sequence_id=sequence_id,
                normalized_frame_stride=self.normalized_frame_stride,
                normalized_target_fps=self.normalized_target_fps,
                reference_cloud=self.reference_cloud.model_copy(deep=True),
                rgb_max_width_px=self.rgb_max_width_px,
                rgb_dimension_multiple=self.rgb_dimension_multiple,
            )
            for sequence_id in self.sequence_ids
        ]


class Record3DNormalizedDatasetBuildSource(NormalizedCadenceConfig):
    """Grouped Record3D normalized-store build settings."""

    model_config = ConfigDict(extra="forbid")

    source_id: Literal["record3d_dataset"] = "record3d_dataset"
    sequence_ids: list[str] = Field(min_length=1)
    reference_cloud: ReferenceCloudConfig = Field(default_factory=lambda: ReferenceCloudConfig(min_confidence=1))
    rgb_max_width_px: int = Field(default=392, ge=1)
    rgb_dimension_multiple: int = Field(default=14, ge=1)

    def source_configs(self) -> list[Record3DDatasetSourceConfig]:
        """Expand this dataset group into concrete per-sequence source configs."""
        return [
            Record3DDatasetSourceConfig(
                sequence_id=sequence_id,
                normalized_frame_stride=self.normalized_frame_stride,
                normalized_target_fps=self.normalized_target_fps,
                reference_cloud=self.reference_cloud.model_copy(deep=True),
                rgb_max_width_px=self.rgb_max_width_px,
                rgb_dimension_multiple=self.rgb_dimension_multiple,
            )
            for sequence_id in self.sequence_ids
        ]


NormalizedDatasetBuildSource = Annotated[
    AdvioNormalizedDatasetBuildSource | TumRgbdNormalizedDatasetBuildSource | Record3DNormalizedDatasetBuildSource,
    Field(discriminator="source_id"),
]


class NormalizedDatasetBuildConfig(BaseConfig):
    """TOML-owned dataset groups for generating normalized datastore entries."""

    workers: int | None = Field(default=None, ge=1)
    sources: list[NormalizedDatasetBuildSource] = Field(min_length=1)

    def source_configs(self) -> list[AdvioSourceConfig | TumRgbdSourceConfig | Record3DDatasetSourceConfig]:
        """Expand grouped dataset settings into per-sequence source configs."""
        return [source_config for source in self.sources for source_config in source.source_configs()]
