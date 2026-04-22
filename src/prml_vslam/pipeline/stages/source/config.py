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
from prml_vslam.datasets.contracts import DatasetId, FrameSelectionConfig
from prml_vslam.datasets.tum_rgbd import TumRgbdDatasetService, TumRgbdPoseSource
from prml_vslam.interfaces.runtime import Record3DTransportId
from prml_vslam.io.record3d_source import Record3DStreamingSourceConfig
from prml_vslam.pipeline.contracts.request import (
    DatasetSourceSpec,
    Record3DLiveSourceSpec,
    SourceSpec,
    VideoSourceSpec,
)
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.config import StageConfig
from prml_vslam.pipeline.stages.source.runtime import SampledStreamingSource, VideoOfflineSequenceSource
from prml_vslam.protocols.source import OfflineSequenceSource, StreamingSequenceSource
from prml_vslam.utils import FactoryConfig, PathConfig


class VideoSourceConfig(FrameSelectionConfig, FactoryConfig[OfflineSequenceSource]):
    """Configure one raw-video source adapter."""

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
    """Configure one TUM RGB-D dataset source adapter."""

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
    """Configure one ADVIO dataset source adapter."""

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
    """Configure one live Record3D source adapter."""

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
    """Target source stage policy plus source backend selection."""

    model_config = ConfigDict(extra="forbid")

    stage_key: StageKey | None = StageKey.INGEST
    """Current executable stage key used during migration."""

    backend: SourceBackendConfig
    """Concrete source backend config that constructs the source adapter."""


def source_backend_config_from_source_spec(source_spec: SourceSpec) -> SourceBackendConfig:
    """Project one legacy request source spec into the target source backend config."""
    # TODO(pipeline-refactor/WP-09): Delete this compatibility projection after
    # launch paths submit SourceStageConfig directly.
    match source_spec:
        case VideoSourceSpec(video_path=video_path, frame_stride=frame_stride, target_fps=target_fps):
            return VideoSourceConfig(video_path=video_path, frame_stride=frame_stride, target_fps=target_fps)
        case DatasetSourceSpec(
            dataset_id=DatasetId.ADVIO,
            sequence_id=sequence_id,
            frame_stride=frame_stride,
            target_fps=target_fps,
            dataset_serving=dataset_serving,
            respect_video_rotation=respect_video_rotation,
        ):
            return AdvioSourceConfig(
                sequence_id=sequence_id,
                frame_stride=frame_stride,
                target_fps=target_fps,
                dataset_serving=AdvioServingConfig() if dataset_serving is None else dataset_serving,
                respect_video_rotation=respect_video_rotation,
            )
        case DatasetSourceSpec(
            dataset_id=DatasetId.TUM_RGBD,
            sequence_id=sequence_id,
            frame_stride=frame_stride,
            target_fps=target_fps,
        ):
            return TumRgbdSourceConfig(sequence_id=sequence_id, frame_stride=frame_stride, target_fps=target_fps)
        case Record3DLiveSourceSpec(transport=transport, device_index=device_index, device_address=device_address):
            return Record3DSourceConfig(
                transport=transport,
                device_index=0 if device_index is None else device_index,
                device_address=device_address,
            )
        case _:
            raise RuntimeError(f"Unsupported legacy source spec: {source_spec!r}")


def source_stage_config_from_source_spec(source_spec: SourceSpec) -> SourceStageConfig:
    """Project one legacy source spec into the target source stage config."""
    # TODO(pipeline-refactor/WP-09): Delete this compatibility projection after
    # launch paths submit SourceStageConfig directly.
    return SourceStageConfig(backend=source_backend_config_from_source_spec(source_spec))


__all__ = [
    "AdvioSourceConfig",
    "Record3DSourceConfig",
    "SourceBackendConfig",
    "SourceStageConfig",
    "TumRgbdSourceConfig",
    "VideoSourceConfig",
    "source_backend_config_from_source_spec",
    "source_stage_config_from_source_spec",
]
