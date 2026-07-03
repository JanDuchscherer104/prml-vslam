from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import ConfigDict, Field

from prml_vslam.sources.contracts import Record3DTransportId
from prml_vslam.sources.datasets.advio import AdvioDatasetService, AdvioServingConfig
from prml_vslam.sources.datasets.contracts import (
    ADVIO_FIXEDPOINT_COMMON_START_TRAJECTORY_CONVENTION,
    AdvioPoseFrameMode,
    DatasetId,
    FrameSelectionConfig,
    ReferenceCloudConfig,
)
from prml_vslam.sources.datasets.normalized_source import NormalizedDatasetRuntimeSource
from prml_vslam.sources.datasets.normalized_store import (
    NormalizedDatasetProfile,
    normalized_dataset_profile,
    normalized_store_for_path_config,
)
from prml_vslam.sources.datasets.record3d import Record3DMaterializationConfig, record3d_layout
from prml_vslam.sources.datasets.tum_rgbd import TumRgbdDatasetService
from prml_vslam.sources.materialization import VideoOfflineSequenceSource
from prml_vslam.sources.protocols import OfflineSequenceSource, StreamingSequenceSource
from prml_vslam.sources.record3d.source import Record3DStreamingSourceConfig
from prml_vslam.sources.replay import ReplayMode
from prml_vslam.sources.streaming import SampledStreamingSource
from prml_vslam.utils import FactoryConfig, PathConfig, get_path_config


class VideoSourceConfig(FrameSelectionConfig, FactoryConfig[OfflineSequenceSource]):
    model_config = ConfigDict(extra="ignore")

    source_id: Literal["video"] = "video"
    video_path: Path

    def setup_target(self, path_config: PathConfig | None = None, **_kwargs: Any) -> OfflineSequenceSource:
        path_config = get_path_config() if path_config is None else path_config
        return VideoOfflineSequenceSource(
            path_config=path_config,
            video_path=path_config.resolve_video_path(self.video_path, must_exist=True),
        )


class TumRgbdSourceConfig(FrameSelectionConfig, FactoryConfig[NormalizedDatasetRuntimeSource]):
    model_config = ConfigDict(extra="ignore")

    source_id: Literal["tum_rgbd"] = "tum_rgbd"
    sequence_id: str
    replay_mode: ReplayMode = ReplayMode.REALTIME
    reference_cloud: ReferenceCloudConfig = Field(default_factory=ReferenceCloudConfig)
    rgb_max_width_px: int = Field(default=392, ge=1)
    rgb_dimension_multiple: int = Field(default=14, ge=1)

    def setup_target(self, path_config: PathConfig | None = None, **_kwargs: Any) -> NormalizedDatasetRuntimeSource:
        path_config = get_path_config() if path_config is None else path_config
        service = TumRgbdDatasetService(path_config)
        sequence_id = str(service.resolve_sequence_id(self.sequence_id))
        profile = normalized_runtime_profile_for_source_config(
            dataset_id=DatasetId.TUM_RGBD,
            sequence_id=sequence_id,
            source_config=self,
        )
        return NormalizedDatasetRuntimeSource(
            label=sequence_id,
            store=normalized_store_for_path_config(DatasetId.TUM_RGBD, path_config),
            profile=profile,
            frame_selection=runtime_frame_selection_for_source_config(self),
            replay_mode=self.replay_mode,
        )


class AdvioSourceConfig(FrameSelectionConfig, FactoryConfig[NormalizedDatasetRuntimeSource]):
    model_config = ConfigDict(extra="ignore")

    source_id: Literal["advio"] = "advio"
    sequence_id: str
    dataset_serving: AdvioServingConfig = Field(default_factory=AdvioServingConfig)
    replay_mode: ReplayMode = ReplayMode.REALTIME
    rgb_max_width_px: int = Field(default=392, ge=1)
    rgb_dimension_multiple: int = Field(default=14, ge=1)

    def setup_target(self, path_config: PathConfig | None = None, **_kwargs: Any) -> NormalizedDatasetRuntimeSource:
        path_config = get_path_config() if path_config is None else path_config
        service = AdvioDatasetService(path_config)
        sequence_id = service.resolve_sequence_id(self.sequence_id)
        canonical_sequence_id = f"advio-{sequence_id:02d}"
        profile = normalized_runtime_profile_for_source_config(
            dataset_id=DatasetId.ADVIO,
            sequence_id=canonical_sequence_id,
            source_config=self,
        )
        return NormalizedDatasetRuntimeSource(
            label=canonical_sequence_id,
            store=normalized_store_for_path_config(DatasetId.ADVIO, path_config),
            profile=profile,
            frame_selection=runtime_frame_selection_for_source_config(self),
            replay_mode=self.replay_mode,
        )


class Record3DDatasetSourceConfig(FrameSelectionConfig, FactoryConfig[NormalizedDatasetRuntimeSource]):
    model_config = ConfigDict(extra="forbid")

    source_id: Literal["record3d_dataset"] = "record3d_dataset"
    sequence_id: str
    replay_mode: ReplayMode = ReplayMode.REALTIME
    materialization: Record3DMaterializationConfig = Field(default_factory=Record3DMaterializationConfig)
    reference_cloud: ReferenceCloudConfig = Field(default_factory=lambda: ReferenceCloudConfig(min_confidence=1))
    rgb_max_width_px: int = Field(default=392, ge=1)
    rgb_dimension_multiple: int = Field(default=14, ge=1)

    def setup_target(self, path_config: PathConfig | None = None, **_kwargs: Any) -> NormalizedDatasetRuntimeSource:
        path_config = get_path_config() if path_config is None else path_config
        sequence_id = record3d_layout.normalize_sequence_id(self.sequence_id)
        profile = normalized_runtime_profile_for_source_config(
            dataset_id=DatasetId.RECORD3D,
            sequence_id=sequence_id,
            source_config=self,
        )
        return NormalizedDatasetRuntimeSource(
            label=sequence_id,
            store=normalized_store_for_path_config(DatasetId.RECORD3D, path_config),
            profile=profile,
            frame_selection=runtime_frame_selection_for_source_config(self),
            replay_mode=self.replay_mode,
        )


class Record3DSourceConfig(FrameSelectionConfig, FactoryConfig[StreamingSequenceSource]):
    model_config = ConfigDict(extra="ignore")

    source_id: Literal["record3d"] = "record3d"
    transport: Record3DTransportId = Record3DTransportId.USB
    device_index: int = 0
    device_address: str = ""
    frame_timeout_seconds: float = 5.0

    def setup_target(self, path_config: PathConfig | None = None, **_kwargs: Any) -> StreamingSequenceSource:
        del path_config
        source = Record3DStreamingSourceConfig(
            transport=self.transport,
            device_index=self.device_index,
            device_address=self.device_address,
            frame_timeout_seconds=self.frame_timeout_seconds,
        ).setup_target()
        if self.frame_stride == 1 and self.target_fps is None:
            return source
        return SampledStreamingSource(
            source,
            frame_selection=FrameSelectionConfig(frame_stride=self.frame_stride, target_fps=self.target_fps),
        )


SourceBackendConfig = Annotated[
    VideoSourceConfig | TumRgbdSourceConfig | AdvioSourceConfig | Record3DDatasetSourceConfig | Record3DSourceConfig,
    Field(discriminator="source_id"),
]


def normalized_profile_for_source_config(
    *,
    dataset_id: DatasetId,
    sequence_id: str,
    source_id: str,
    payload: dict[str, Any],
) -> NormalizedDatasetProfile:
    excluded_keys = {"replay_mode"}
    source_profile = {key: value for key, value in payload.items() if key not in excluded_keys}
    if dataset_id is DatasetId.ADVIO:
        serving = source_profile.get("dataset_serving")
        if isinstance(serving, dict):
            source_profile["dataset_serving"] = serving | {"pose_frame_mode": AdvioPoseFrameMode.LOCAL_FIRST_POSE.value}
        source_profile["trajectory_convention"] = ADVIO_FIXEDPOINT_COMMON_START_TRAJECTORY_CONVENTION
    return normalized_dataset_profile(
        dataset_id=dataset_id,
        sequence_id=sequence_id,
        source_id=source_id,
        payload=source_profile,
    )


DatasetBackedSourceConfig = AdvioSourceConfig | TumRgbdSourceConfig | Record3DDatasetSourceConfig


def default_normalized_profile_frame_selection(dataset_id: DatasetId) -> FrameSelectionConfig:
    """Return the stored-entry cadence used by default normalized dataset builds."""
    return FrameSelectionConfig(target_fps=15.0 if dataset_id is DatasetId.ADVIO else 30.0)


def runtime_frame_selection_for_source_config(source_config: DatasetBackedSourceConfig) -> FrameSelectionConfig:
    """Return read-time sampling requested by one dataset-backed runtime config."""
    return FrameSelectionConfig(frame_stride=source_config.frame_stride, target_fps=source_config.target_fps)


def normalized_runtime_profile_for_source_config(
    *,
    dataset_id: DatasetId,
    sequence_id: str,
    source_config: DatasetBackedSourceConfig,
) -> NormalizedDatasetProfile:
    """Return the normalized profile for the stored entry replayed at runtime."""
    return normalized_profile_for_source_config(
        dataset_id=dataset_id,
        sequence_id=sequence_id,
        source_id=source_config.source_id,
        payload=source_config.model_dump(mode="json"),
    )
