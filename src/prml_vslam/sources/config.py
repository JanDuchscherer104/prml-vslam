"""Declarative source backend factories.

Concrete source backend config variants construct dataset, video, or live-source
adapters through ``setup_target(...)``. Stage policy lives in
``prml_vslam.sources.stage.config``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import ConfigDict, Field

from prml_vslam.sources.contracts import Record3DTransportId
from prml_vslam.sources.datasets.advio import AdvioDatasetService, AdvioServingConfig
from prml_vslam.sources.datasets.contracts import DatasetId, FrameSelectionConfig, ReferenceCloudConfig
from prml_vslam.sources.datasets.normalized_store import (
    NormalizedDatasetProfile,
    normalized_dataset_profile,
    normalized_store_for_path_config,
)
from prml_vslam.sources.datasets.record3d import Record3DDatasetService, Record3DMaterializationConfig, record3d_layout
from prml_vslam.sources.datasets.tum_rgbd import TumRgbdDatasetService, TumRgbdPoseSource
from prml_vslam.sources.materialization import VideoOfflineSequenceSource
from prml_vslam.sources.protocols import OfflineSequenceSource, StreamingSequenceSource
from prml_vslam.sources.record3d.source import Record3DStreamingSourceConfig
from prml_vslam.sources.replay import ReplayMode
from prml_vslam.sources.streaming import SampledStreamingSource
from prml_vslam.utils import FactoryConfig, PathConfig, get_path_config


class VideoSourceConfig(FrameSelectionConfig, FactoryConfig[OfflineSequenceSource]):
    """Configure one raw-video source adapter.

    Raw video sources only provide the primary frame sequence. Reference
    trajectories, depth, and dataset-specific calibration must come from other
    source variants or later benchmark preparation.
    """

    model_config = ConfigDict(extra="ignore")

    source_id: Literal["video"] = "video"
    """Typed source discriminator for raw-video inputs."""

    video_path: Path
    """Repo-relative or absolute video path."""

    def setup_target(self, path_config: PathConfig | None = None, **_kwargs: Any) -> OfflineSequenceSource:
        """Build the normalized raw-video source adapter."""
        path_config = get_path_config() if path_config is None else path_config
        return VideoOfflineSequenceSource(
            path_config=path_config,
            video_path=path_config.resolve_video_path(self.video_path, must_exist=True),
        )


class TumRgbdSourceConfig(FrameSelectionConfig, FactoryConfig[StreamingSequenceSource]):
    """Configure one TUM RGB-D dataset source adapter.

    TUM RGB-D sources can provide RGB, metric depth, ground-truth poses, and
    prepared RGB-D observation sequences for reconstruction. The source config
    selects sequence and sampling policy; metric/evaluation policy remains
    benchmark- or eval-owned.
    """

    model_config = ConfigDict(extra="ignore")

    source_id: Literal["tum_rgbd"] = "tum_rgbd"
    """Typed source discriminator for TUM RGB-D inputs."""

    sequence_id: str
    """TUM RGB-D sequence slug or canonical sequence id."""

    replay_mode: ReplayMode = ReplayMode.REALTIME
    """Replay pacing policy for streaming TUM RGB-D observations."""

    reference_cloud: ReferenceCloudConfig = Field(default_factory=ReferenceCloudConfig)
    """Shared source-prepared reference-cloud sampling policy."""

    def setup_target(self, path_config: PathConfig | None = None, **_kwargs: Any) -> StreamingSequenceSource:
        """Build the normalized-store backed TUM RGB-D source adapter."""
        path_config = get_path_config() if path_config is None else path_config
        service = TumRgbdDatasetService(path_config)
        sequence_id = str(service.resolve_sequence_id(self.sequence_id))
        profile = normalized_profile_for_source_config(
            dataset_id=DatasetId.TUM_RGBD,
            sequence_id=sequence_id,
            source_id=self.source_id,
            payload=self.model_dump(mode="json"),
        )
        return service.build_streaming_source(
            sequence_id=sequence_id,
            frame_selection=FrameSelectionConfig(frame_stride=self.frame_stride, target_fps=self.target_fps),
            replay_mode=self.replay_mode,
            pose_source=TumRgbdPoseSource.GROUND_TRUTH,
            include_depth=True,
            reference_cloud=self.reference_cloud,
            normalized_store=normalized_store_for_path_config(DatasetId.TUM_RGBD, path_config),
            normalized_profile=profile,
        )


class AdvioSourceConfig(FrameSelectionConfig, FactoryConfig[StreamingSequenceSource]):
    """Configure one ADVIO dataset source adapter.

    ADVIO adds dataset-serving policy for pose source, video orientation, and
    video orientation. Those semantics stay ADVIO-owned rather than being
    promoted into the generic source backend base.
    """

    model_config = ConfigDict(extra="ignore")

    source_id: Literal["advio"] = "advio"
    """Typed source discriminator for ADVIO inputs."""

    sequence_id: str
    """ADVIO sequence slug such as ``advio-20``."""

    dataset_serving: AdvioServingConfig = Field(default_factory=AdvioServingConfig)
    """ADVIO-only pose provider and frame semantics."""

    replay_mode: ReplayMode = ReplayMode.REALTIME
    """Replay pacing policy for streaming ADVIO observations."""

    normalize_video_orientation: bool = True
    """Whether replay should normalize video display orientation before emission."""

    def setup_target(self, path_config: PathConfig | None = None, **_kwargs: Any) -> StreamingSequenceSource:
        """Build the normalized-store backed ADVIO source adapter."""
        path_config = get_path_config() if path_config is None else path_config
        service = AdvioDatasetService(path_config)
        sequence_id = service.resolve_sequence_id(self.sequence_id)
        canonical_sequence_id = f"advio-{sequence_id:02d}"
        profile = normalized_profile_for_source_config(
            dataset_id=DatasetId.ADVIO,
            sequence_id=canonical_sequence_id,
            source_id=self.source_id,
            payload=self.model_dump(mode="json"),
        )
        return service.build_streaming_source(
            sequence_id=sequence_id,
            frame_selection=FrameSelectionConfig(frame_stride=self.frame_stride, target_fps=self.target_fps),
            dataset_serving=self.dataset_serving,
            replay_mode=self.replay_mode,
            normalize_video_orientation=self.normalize_video_orientation,
            normalized_store=normalized_store_for_path_config(DatasetId.ADVIO, path_config),
            normalized_profile=profile,
        )


class Record3DDatasetSourceConfig(FrameSelectionConfig, FactoryConfig[StreamingSequenceSource]):
    """Configure one offline Record3D `.r3d` dataset archive."""

    model_config = ConfigDict(extra="forbid")

    source_id: Literal["record3d_dataset"] = "record3d_dataset"
    """Typed source discriminator for local Record3D `.r3d` archives."""

    sequence_id: str
    """Record3D archive stem such as `2024-03-31--16-17-17`."""

    replay_mode: ReplayMode = ReplayMode.REALTIME
    """Replay pacing policy for archive-backed RGB-D observations."""

    materialization: Record3DMaterializationConfig = Field(default_factory=Record3DMaterializationConfig)
    """Record3D-owned policy for decoded depth and pose frame semantics."""

    reference_cloud: ReferenceCloudConfig = Field(default_factory=lambda: ReferenceCloudConfig(min_confidence=1))
    """Shared source-prepared reference-cloud sampling policy."""

    def setup_target(self, path_config: PathConfig | None = None, **_kwargs: Any) -> StreamingSequenceSource:
        """Build the normalized offline Record3D dataset adapter."""
        path_config = get_path_config() if path_config is None else path_config
        service = Record3DDatasetService(path_config)
        sequence_id = record3d_layout.normalize_sequence_id(self.sequence_id)
        profile = normalized_profile_for_source_config(
            dataset_id=DatasetId.RECORD3D,
            sequence_id=sequence_id,
            source_id=self.source_id,
            payload=self.model_dump(mode="json"),
        )
        return service.build_streaming_source(
            sequence_id=sequence_id,
            frame_selection=FrameSelectionConfig(frame_stride=self.frame_stride, target_fps=self.target_fps),
            replay_mode=self.replay_mode,
            materialization=self.materialization,
            reference_cloud=self.reference_cloud,
            normalized_store=normalized_store_for_path_config(DatasetId.RECORD3D, path_config),
            normalized_profile=profile,
        )


class Record3DSourceConfig(FrameSelectionConfig, FactoryConfig[StreamingSequenceSource]):
    """Configure one live Record3D source adapter.

    The source owns transport-level capture for USB or Wi-Fi Preview and emits
    normalized :class:`prml_vslam.interfaces.observation.Observation` values. It
    does not own app session state, pipeline stage order, or SLAM backend
    selection.
    """

    model_config = ConfigDict(extra="ignore")

    source_id: Literal["record3d"] = "record3d"
    """Typed source discriminator for Record3D live inputs."""

    transport: Record3DTransportId = Record3DTransportId.USB
    """Selected Record3D transport identifier."""

    device_index: int = 0
    """Zero-based USB device index."""

    device_address: str = ""
    """Wi-Fi preview device address."""

    frame_timeout_seconds: float = 5.0
    """Maximum time to wait for the next live frame."""

    def setup_target(self, path_config: PathConfig | None = None, **_kwargs: Any) -> StreamingSequenceSource:
        """Build the normalized Record3D source adapter."""
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
    *, dataset_id: DatasetId, sequence_id: str, source_id: str, payload: dict[str, Any]
) -> NormalizedDatasetProfile:
    """Build the normalized-store profile for one dataset source config."""
    source_profile = {
        key: value
        for key, value in payload.items()
        if key not in {"frame_stride", "target_fps", "replay_mode", "normalize_video_orientation"}
    }
    return normalized_dataset_profile(
        dataset_id=dataset_id,
        sequence_id=sequence_id,
        source_id=source_id,
        payload=source_profile,
    )


__all__ = [
    "AdvioSourceConfig",
    "Record3DDatasetSourceConfig",
    "Record3DSourceConfig",
    "SourceBackendConfig",
    "TumRgbdSourceConfig",
    "VideoSourceConfig",
    "normalized_profile_for_source_config",
]
