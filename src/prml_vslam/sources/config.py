"""Declarative source backend factories.

Concrete source backend config variants construct dataset, video, or live-source
adapters through ``setup_target(...)``. Stage policy lives in
``prml_vslam.sources.stage.config``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Literal, TypeAlias

from pydantic import ConfigDict, Field

from prml_vslam.sources.contracts import Record3DTransportId
from prml_vslam.sources.datasets.advio import AdvioDatasetService, AdvioServingConfig
from prml_vslam.sources.datasets.contracts import FrameSelectionConfig
from prml_vslam.sources.datasets.tum_rgbd import TumRgbdDatasetService, TumRgbdPoseSource
from prml_vslam.sources.materialization import VideoOfflineSequenceSource
from prml_vslam.sources.protocols import OfflineSequenceSource, StreamingSequenceSource
from prml_vslam.sources.record3d.source import Record3DStreamingSourceConfig
from prml_vslam.sources.replay import ReplayMode
from prml_vslam.sources.streaming import SampledStreamingSource
from prml_vslam.utils import FactoryConfig, PathConfig


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

    def setup_target(self, *, path_config: PathConfig, **_kwargs: Any) -> OfflineSequenceSource:
        """Build the normalized raw-video source adapter."""
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

    def setup_target(self, *, path_config: PathConfig, **_kwargs: Any) -> StreamingSequenceSource:
        """Build the normalized TUM RGB-D source adapter."""
        service = TumRgbdDatasetService(path_config)
        return service.build_streaming_source(
            sequence_id=service.resolve_sequence_id(self.sequence_id),
            frame_selection=FrameSelectionConfig(frame_stride=self.frame_stride, target_fps=self.target_fps),
            replay_mode=self.replay_mode,
            pose_source=TumRgbdPoseSource.GROUND_TRUTH,
            include_depth=True,
        )


class AdvioSourceConfig(FrameSelectionConfig, FactoryConfig[StreamingSequenceSource]):
    """Configure one ADVIO dataset source adapter.

    ADVIO adds dataset-serving policy for pose source, video orientation, and
    optional Tango reference payloads. Those semantics stay ADVIO-owned rather
    than being promoted into the generic source backend base.
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

    tango_reference_point_stride: int = Field(default=1, ge=1)
    """Stride for prepared static ADVIO Tango reference clouds; ``1`` keeps every payload point."""

    def setup_target(self, *, path_config: PathConfig, **_kwargs: Any) -> StreamingSequenceSource:
        """Build the normalized ADVIO source adapter."""
        service = AdvioDatasetService(path_config)
        return service.build_streaming_source(
            sequence_id=service.resolve_sequence_id(self.sequence_id),
            frame_selection=FrameSelectionConfig(frame_stride=self.frame_stride, target_fps=self.target_fps),
            dataset_serving=self.dataset_serving,
            replay_mode=self.replay_mode,
            normalize_video_orientation=self.normalize_video_orientation,
            tango_reference_point_stride=self.tango_reference_point_stride,
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

    def setup_target(self, *, path_config: PathConfig | None = None, **_kwargs: Any) -> StreamingSequenceSource:
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


__all__ = [
    "AdvioSourceConfig",
    "Record3DSourceConfig",
    "SourceBackendConfig",
    "TumRgbdSourceConfig",
    "VideoSourceConfig",
]
