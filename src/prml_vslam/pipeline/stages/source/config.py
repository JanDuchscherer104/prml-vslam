"""Declarative source stage config and source backend factories.

This module owns the target source-stage config shape. ``SourceStageConfig``
describes stage policy, while concrete source backend config variants construct
dataset, video, or live-source adapters through ``setup_target(...)``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal, TypeAlias

from pydantic import ConfigDict, Field

from prml_vslam.datasets.advio import AdvioDatasetService, AdvioServingConfig
from prml_vslam.datasets.contracts import FrameSelectionConfig
from prml_vslam.datasets.tum_rgbd import TumRgbdDatasetService, TumRgbdPoseSource
from prml_vslam.interfaces.runtime import Record3DTransportId
from prml_vslam.io.record3d_source import Record3DStreamingSourceConfig
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.config import StageConfig
from prml_vslam.pipeline.stages.source.runtime import SampledStreamingSource, VideoOfflineSequenceSource
from prml_vslam.protocols.source import OfflineSequenceSource, StreamingSequenceSource
from prml_vslam.utils import FactoryConfig, PathConfig


class VideoSourceConfig(FrameSelectionConfig, FactoryConfig[OfflineSequenceSource]):
    """Configure one raw-video source adapter.

    Raw video sources only provide the primary frame sequence. Reference
    trajectories, depth, and dataset-specific calibration must come from other
    source variants or later benchmark preparation.
    """

    model_config = ConfigDict(extra="forbid")

    source_id: Literal["video"] = "video"
    """Typed source discriminator for raw-video inputs."""

    video_path: Path
    """Repo-relative or absolute video path."""

    def setup_target(self, *, path_config: PathConfig, **_kwargs: object) -> OfflineSequenceSource:
        """Build the normalized raw-video source adapter."""
        return VideoOfflineSequenceSource(
            path_config=path_config,
            video_path=path_config.resolve_video_path(self.video_path, must_exist=True),
            frame_stride=self.frame_stride,
        )


class TumRgbdSourceConfig(FrameSelectionConfig, FactoryConfig[StreamingSequenceSource]):
    """Configure one TUM RGB-D dataset source adapter.

    TUM RGB-D sources can provide RGB, metric depth, ground-truth poses, and
    prepared RGB-D observation sequences for reconstruction. The source config
    selects sequence and sampling policy; metric/evaluation policy remains
    benchmark- or eval-owned.
    """

    model_config = ConfigDict(extra="forbid")

    source_id: Literal["tum_rgbd"] = "tum_rgbd"
    """Typed source discriminator for TUM RGB-D inputs."""

    sequence_id: str
    """TUM RGB-D sequence slug or canonical sequence id."""

    def setup_target(self, *, path_config: PathConfig, **_kwargs: object) -> StreamingSequenceSource:
        """Build the normalized TUM RGB-D source adapter."""
        service = TumRgbdDatasetService(path_config)
        return service.build_streaming_source(
            sequence_id=service.resolve_sequence_id(self.sequence_id),
            frame_selection=FrameSelectionConfig(frame_stride=self.frame_stride, target_fps=self.target_fps),
            pose_source=TumRgbdPoseSource.GROUND_TRUTH,
            include_depth=True,
        )


class AdvioSourceConfig(FrameSelectionConfig, FactoryConfig[StreamingSequenceSource]):
    """Configure one ADVIO dataset source adapter.

    ADVIO adds dataset-serving policy for pose source, video rotation, and
    optional Tango reference payloads. Those semantics stay ADVIO-owned rather
    than being promoted into the generic source backend base.
    """

    model_config = ConfigDict(extra="forbid")

    source_id: Literal["advio"] = "advio"
    """Typed source discriminator for ADVIO inputs."""

    sequence_id: str
    """ADVIO sequence slug such as ``advio-20``."""

    dataset_serving: AdvioServingConfig = Field(default_factory=AdvioServingConfig)
    """ADVIO-only pose provider and frame semantics."""

    respect_video_rotation: bool = False
    """Whether replay should honor ADVIO video rotation metadata."""

    def setup_target(self, *, path_config: PathConfig, **_kwargs: object) -> StreamingSequenceSource:
        """Build the normalized ADVIO source adapter."""
        service = AdvioDatasetService(path_config)
        return service.build_streaming_source(
            sequence_id=service.resolve_sequence_id(self.sequence_id),
            frame_selection=FrameSelectionConfig(frame_stride=self.frame_stride, target_fps=self.target_fps),
            dataset_serving=self.dataset_serving,
            respect_video_rotation=self.respect_video_rotation,
        )


class Record3DSourceConfig(FrameSelectionConfig, FactoryConfig[StreamingSequenceSource]):
    """Configure one live Record3D source adapter.

    The source owns transport-level capture for USB or Wi-Fi Preview and emits
    normalized :class:`prml_vslam.interfaces.runtime.FramePacket` values. It
    does not own app session state, pipeline stage order, or SLAM backend
    selection.
    """

    model_config = ConfigDict(extra="forbid")

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

    def setup_target(self, *, path_config: PathConfig | None = None, **_kwargs: object) -> StreamingSequenceSource:
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


SourceBackendConfig: TypeAlias = Annotated[
    VideoSourceConfig | TumRgbdSourceConfig | AdvioSourceConfig | Record3DSourceConfig,
    Field(discriminator="source_id"),
]


class SourceStageConfig(StageConfig):
    """Target source stage policy plus source backend selection.

    Stage policy such as enablement, telemetry, cleanup, and resources lives on
    the inherited :class:`prml_vslam.pipeline.stages.base.config.StageConfig`.
    Concrete source construction lives in :attr:`backend` so adding a new source
    follows the same config-as-factory pattern as methods and reconstruction.
    """

    model_config = ConfigDict(extra="forbid")

    stage_key: StageKey | None = StageKey.INGEST
    """Current executable stage key used during migration."""

    backend: SourceBackendConfig
    """Concrete source backend config that constructs the source adapter."""


__all__ = [
    "AdvioSourceConfig",
    "Record3DSourceConfig",
    "SourceBackendConfig",
    "SourceStageConfig",
    "TumRgbdSourceConfig",
    "VideoSourceConfig",
]
