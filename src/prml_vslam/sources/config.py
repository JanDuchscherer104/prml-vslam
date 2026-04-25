"""Declarative source stage config and source backend factories.

This module owns the target source-stage config shape. ``SourceStageConfig``
describes stage policy, while concrete source backend config variants construct
dataset, video, or live-source adapters through ``setup_target(...)``.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any, Literal, TypeAlias

from pydantic import ConfigDict, Field

from prml_vslam.pipeline.contracts.context import PipelineExecutionContext, PipelinePlanContext
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.config import FailureFingerprint, StageConfig
from prml_vslam.pipeline.stages.base.protocols import BaseStageRuntime
from prml_vslam.protocols.source import OfflineSequenceSource, StreamingSequenceSource
from prml_vslam.sources.contracts import Record3DTransportId
from prml_vslam.sources.datasets.advio import AdvioDatasetService, AdvioServingConfig
from prml_vslam.sources.datasets.contracts import FrameSelectionConfig
from prml_vslam.sources.datasets.tum_rgbd import TumRgbdDatasetService, TumRgbdPoseSource
from prml_vslam.sources.materialization import VideoOfflineSequenceSource
from prml_vslam.sources.record3d.source import Record3DStreamingSourceConfig
from prml_vslam.sources.runtime import SourceRuntime, SourceStageInput
from prml_vslam.sources.streaming import SampledStreamingSource
from prml_vslam.utils import FactoryConfig, PathConfig
from prml_vslam.utils.serialization import stable_hash


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

    def setup_target(self, *, path_config: PathConfig, **_kwargs: Any) -> StreamingSequenceSource:
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

    model_config = ConfigDict(extra="ignore")

    source_id: Literal["advio"] = "advio"
    """Typed source discriminator for ADVIO inputs."""

    sequence_id: str
    """ADVIO sequence slug such as ``advio-20``."""

    dataset_serving: AdvioServingConfig = Field(default_factory=AdvioServingConfig)
    """ADVIO-only pose provider and frame semantics."""

    respect_video_rotation: bool = False
    """Whether replay should honor ADVIO video rotation metadata."""

    tango_reference_point_stride: int = Field(default=1, ge=1)
    """Stride for prepared static ADVIO Tango reference clouds; ``1`` keeps every payload point."""

    def setup_target(self, *, path_config: PathConfig, **_kwargs: Any) -> StreamingSequenceSource:
        """Build the normalized ADVIO source adapter."""
        service = AdvioDatasetService(path_config)
        return service.build_streaming_source(
            sequence_id=service.resolve_sequence_id(self.sequence_id),
            frame_selection=FrameSelectionConfig(frame_stride=self.frame_stride, target_fps=self.target_fps),
            dataset_serving=self.dataset_serving,
            respect_video_rotation=self.respect_video_rotation,
            tango_reference_point_stride=self.tango_reference_point_stride,
        )


class Record3DSourceConfig(FrameSelectionConfig, FactoryConfig[StreamingSequenceSource]):
    """Configure one live Record3D source adapter.

    The source owns transport-level capture for USB or Wi-Fi Preview and emits
    normalized :class:`prml_vslam.sources.contracts.Observation` values. It
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


class SourceStageConfig(StageConfig):
    """Target source stage policy plus source backend selection.

    Stage policy such as enablement, telemetry, cleanup, and resources lives on
    the inherited :class:`prml_vslam.pipeline.stages.base.config.StageConfig`.
    Concrete source construction lives in :attr:`backend` so adding a new source
    follows the same config-as-factory pattern as methods and reconstruction.
    """

    model_config = ConfigDict(extra="ignore")

    stage_key: StageKey | None = StageKey.SOURCE
    """Canonical source stage key."""

    backend: SourceBackendConfig | None = None
    """Concrete source backend config that constructs the source adapter."""

    def planned_outputs(self, context: PipelinePlanContext) -> list[Path]:
        """Return source-owned normalized input artifacts."""
        return [context.run_paths.sequence_manifest_path, context.run_paths.benchmark_inputs_path]

    def runtime_factory(self, context: PipelineExecutionContext) -> Callable[[], BaseStageRuntime]:
        """Return a lazy source runtime factory bound to the prepared source."""
        if context.source is None:
            raise RuntimeError("Source stage runtime construction requires a source adapter.")

        def _factory() -> BaseStageRuntime:
            return SourceRuntime(source=context.source)

        return _factory

    def build_offline_input(self, context: PipelineExecutionContext) -> SourceStageInput:
        """Build the narrow source runtime input."""
        source_backend = self.backend
        slam_backend = context.run_config.stages.slam.backend
        return SourceStageInput(
            artifact_root=context.plan.artifact_root,
            mode=context.run_config.mode,
            frame_stride=1 if source_backend is None else source_backend.frame_stride,
            streaming_max_frames=None if slam_backend is None else slam_backend.max_frames,
            config_hash=stable_hash(source_backend),
            input_fingerprint=stable_hash(source_backend),
        )

    def failure_fingerprint(self, context: PipelineExecutionContext) -> FailureFingerprint:
        """Return source config and input fingerprint payloads."""
        del context
        return FailureFingerprint(config_payload=self.backend, input_payload=self.backend)


__all__ = [
    "AdvioSourceConfig",
    "Record3DSourceConfig",
    "SourceBackendConfig",
    "SourceStageConfig",
    "TumRgbdSourceConfig",
    "VideoSourceConfig",
]
