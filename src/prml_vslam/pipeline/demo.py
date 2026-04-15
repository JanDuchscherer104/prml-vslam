"""Shared helpers for the bounded dataset pipeline demo."""

from __future__ import annotations

from pathlib import Path

from prml_vslam.datasets.advio import AdvioDatasetService, AdvioPoseSource
from prml_vslam.datasets.contracts import DatasetId
from prml_vslam.datasets.tum_rgbd import TumRgbdDatasetService, TumRgbdPoseSource
from prml_vslam.io.record3d_source import Record3DStreamingSourceConfig
from prml_vslam.methods import MethodId
from prml_vslam.pipeline import PipelineMode, RunRequest
from prml_vslam.pipeline.backend import PipelineRuntimeSource
from prml_vslam.pipeline.contracts.request import (
    DatasetSourceSpec,
    Record3DLiveSourceSpec,
    build_run_request,
)
from prml_vslam.protocols.runtime import FramePacketStream
from prml_vslam.protocols.source import BenchmarkInputSource, StreamingSequenceSource
from prml_vslam.utils import PathConfig


class _CappedPacketStream(FramePacketStream):
    def __init__(self, stream: FramePacketStream, *, max_frames: int) -> None:
        self._stream = stream
        self._max_frames = max_frames
        self._seen_frames = 0

    def connect(self) -> object:
        return self._stream.connect()

    def disconnect(self) -> None:
        self._stream.disconnect()

    def wait_for_packet(self, timeout_seconds: float | None = None):
        if self._seen_frames >= self._max_frames:
            raise EOFError
        packet = self._stream.wait_for_packet(timeout_seconds=timeout_seconds)
        self._seen_frames += 1
        return packet


class _CappedStreamingSource(StreamingSequenceSource):
    def __init__(self, source: StreamingSequenceSource, *, max_frames: int) -> None:
        self._source = source
        self._max_frames = max_frames
        self.label = source.label

    def prepare_sequence_manifest(self, output_dir: Path):
        return self._source.prepare_sequence_manifest(output_dir)

    def prepare_benchmark_inputs(self, output_dir: Path):
        if not isinstance(self._source, BenchmarkInputSource):
            return None
        return self._source.prepare_benchmark_inputs(output_dir)

    def open_stream(self, *, loop: bool) -> FramePacketStream:
        return _CappedPacketStream(self._source.open_stream(loop=loop), max_frames=self._max_frames)


def build_advio_demo_request(
    *,
    path_config: PathConfig,
    sequence_id: str,
    mode: PipelineMode,
    method: MethodId,
    pose_source: AdvioPoseSource = AdvioPoseSource.GROUND_TRUTH,
    respect_video_rotation: bool = False,
    dataset_frame_stride: int = 1,
    dataset_target_fps: float | None = None,
) -> RunRequest:
    """Build the canonical bounded ADVIO demo request shared by app and CLI."""
    return build_run_request(
        experiment_name=f"{sequence_id}-{mode.value}-{method.value}",
        mode=mode,
        output_dir=path_config.artifacts_dir,
        source=DatasetSourceSpec(
            dataset_id=DatasetId.ADVIO,
            sequence_id=sequence_id,
            frame_stride=dataset_frame_stride,
            target_fps=dataset_target_fps,
            pose_source=pose_source,
            respect_video_rotation=respect_video_rotation,
        ),
        method=method,
        connect_live_viewer=True,
    )


def load_run_request_toml(*, path_config: PathConfig, config_path: str | Path) -> RunRequest:
    """Load a pipeline request TOML through the repo-owned config path helper."""
    resolved_config_path = path_config.resolve_pipeline_config_path(config_path, must_exist=True)
    return RunRequest.from_toml(resolved_config_path)


def build_runtime_source_from_request(
    *,
    request: RunRequest,
    path_config: PathConfig,
) -> PipelineRuntimeSource:
    """Build the runtime source required by one persisted run request.

    Offline requests return `None`. Streaming requests are executed from the
    persisted request contract directly, so CLI and Streamlit share the same
    replay controls, capture settings, and backend frame cap.
    """
    if request.mode is PipelineMode.OFFLINE:
        return None
    match request.source:
        case DatasetSourceSpec(dataset_id=DatasetId.ADVIO, sequence_id=sequence_id):
            service = AdvioDatasetService(path_config)
            source = service.build_streaming_source(
                sequence_id=service.resolve_sequence_id(sequence_id),
                frame_selection=request.source,
                pose_source=request.source.pose_source,
                respect_video_rotation=request.source.respect_video_rotation,
            )
            return (
                source
                if request.slam.backend.max_frames is None
                else _CappedStreamingSource(source, max_frames=request.slam.backend.max_frames)
            )
        case DatasetSourceSpec(dataset_id=DatasetId.TUM_RGBD, sequence_id=sequence_id):
            service = TumRgbdDatasetService(path_config)
            source = service.build_streaming_source(
                sequence_id=service.resolve_sequence_id(sequence_id),
                frame_selection=request.source,
                pose_source=TumRgbdPoseSource(request.source.pose_source.value),
                include_depth=True,
            )
            return (
                source
                if request.slam.backend.max_frames is None
                else _CappedStreamingSource(source, max_frames=request.slam.backend.max_frames)
            )
        case Record3DLiveSourceSpec(
            transport=transport,
            device_index=device_index,
            device_address=device_address,
        ):
            source = Record3DStreamingSourceConfig(
                transport=transport,
                device_index=0 if device_index is None else device_index,
                device_address=device_address,
            ).setup_target()
            if source is None:
                raise RuntimeError("Failed to initialize the Record3D streaming source.")
            return (
                source
                if request.slam.backend.max_frames is None
                else _CappedStreamingSource(source, max_frames=request.slam.backend.max_frames)
            )
        case _:
            raise RuntimeError(f"Unsupported streaming source spec: {request.source!r}")


def save_run_request_toml(
    *,
    path_config: PathConfig,
    request: RunRequest,
    config_path: str | Path,
) -> Path:
    """Persist a pipeline request TOML through the repo-owned config path helper."""
    resolved_config_path = path_config.resolve_pipeline_config_path(config_path, create_parent=True)
    request.save_toml(resolved_config_path)
    return resolved_config_path


def persist_advio_demo_request(
    *,
    path_config: PathConfig,
    sequence_id: str,
    mode: PipelineMode,
    method: MethodId,
    dataset_frame_stride: int = 1,
    dataset_target_fps: float | None = None,
    config_path: str | Path | None = None,
) -> Path:
    """Persist the canonical ADVIO demo request under `.configs/pipelines/` by default."""
    request = build_advio_demo_request(
        path_config=path_config,
        sequence_id=sequence_id,
        mode=mode,
        method=method,
        dataset_frame_stride=dataset_frame_stride,
        dataset_target_fps=dataset_target_fps,
    )
    return save_run_request_toml(
        path_config=path_config,
        request=request,
        config_path=(config_path or f"{request.experiment_name}.toml"),
    )


__all__ = [
    "build_advio_demo_request",
    "build_runtime_source_from_request",
    "load_run_request_toml",
    "persist_advio_demo_request",
    "save_run_request_toml",
]
