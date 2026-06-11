"""Shared helpers for the bounded dataset pipeline demo."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from prml_vslam.methods.stage.backend_config import MethodId
from prml_vslam.pipeline import PipelineMode
from prml_vslam.pipeline.backend import PipelineRuntimeSource
from prml_vslam.pipeline.config import RunConfig, build_run_config
from prml_vslam.sources.config import AdvioSourceConfig
from prml_vslam.sources.datasets.advio import AdvioPoseFrameMode, AdvioPoseSource, AdvioServingConfig
from prml_vslam.sources.protocols import BenchmarkInputSource, StreamingSequenceSource
from prml_vslam.sources.replay import ObservationStream
from prml_vslam.utils import PathConfig


class _CappedPacketStream(ObservationStream):
    def __init__(self, stream: ObservationStream, *, max_frames: int) -> None:
        self._stream = stream
        self._max_frames = max_frames
        self._seen_frames = 0

    def connect(self) -> Any:
        return self._stream.connect()

    def disconnect(self) -> None:
        self._stream.disconnect()

    def wait_for_observation(self, timeout_seconds: float | None = None):
        if self._seen_frames >= self._max_frames:
            raise EOFError
        packet = self._stream.wait_for_observation(timeout_seconds=timeout_seconds)
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

    def open_stream(self, *, loop: bool) -> ObservationStream:
        return _CappedPacketStream(self._source.open_stream(loop=loop), max_frames=self._max_frames)


def build_advio_demo_run_config(
    *,
    path_config: PathConfig,
    sequence_id: str,
    mode: PipelineMode,
    method: MethodId,
    pose_source: AdvioPoseSource = AdvioPoseSource.GROUND_TRUTH,
    pose_frame_mode: AdvioPoseFrameMode = AdvioPoseFrameMode.PROVIDER_WORLD,
    normalize_video_orientation: bool = True,
    dataset_frame_stride: int = 1,
    dataset_target_fps: float | None = None,
) -> RunConfig:
    """Build the canonical bounded ADVIO demo run config shared by app and CLI."""
    return build_run_config(
        experiment_name=f"{sequence_id}-{mode.value}-{method.value}",
        mode=mode,
        output_dir=path_config.artifacts_dir,
        source_backend=AdvioSourceConfig(
            sequence_id=sequence_id,
            frame_stride=dataset_frame_stride,
            target_fps=dataset_target_fps,
            dataset_serving=AdvioServingConfig(
                pose_source=pose_source,
                pose_frame_mode=pose_frame_mode,
            ),
            normalize_video_orientation=normalize_video_orientation,
        ),
        method=method,
        connect_live_viewer=True,
    )


def load_run_config_toml(*, path_config: PathConfig, config_path: str | Path) -> RunConfig:
    """Load one launchable pipeline config through the target RunConfig contract."""
    resolved_config_path = path_config.resolve_pipeline_config_path(config_path, must_exist=True)
    payload = tomllib.loads(resolved_config_path.read_text(encoding="utf-8"))
    legacy_sections = [section for section in ("source", "slam") if section in payload]
    if legacy_sections:
        legacy = ", ".join(f"`[{section}]`" for section in legacy_sections)
        raise RuntimeError(
            "Legacy top-level launch sections are no longer supported for app/CLI launch: "
            f"{legacy}. Use `[stages.source.backend]` and `[stages.slam.backend]`."
        )
    if "stages" not in payload:
        raise RuntimeError("RunConfig launch requires a `[stages]` section bundle.")
    return RunConfig.from_toml(resolved_config_path)


def build_runtime_source_from_run_config(
    *,
    run_config: RunConfig,
    path_config: PathConfig,
) -> PipelineRuntimeSource:
    """Build the runtime source required by one target run config."""
    if run_config.mode is PipelineMode.OFFLINE:
        return None
    if run_config.stages.source.backend is None:
        raise ValueError("RunConfig launch requires `[stages.source.backend]` for runtime source construction.")
    if run_config.stages.slam.backend is None:
        raise ValueError("RunConfig launch requires `[stages.slam.backend]` for runtime source construction.")
    source = run_config.stages.source.backend.setup_target(path_config=path_config)
    return (
        source
        if run_config.stages.slam.backend.max_frames is None
        else _CappedStreamingSource(source, max_frames=run_config.stages.slam.backend.max_frames)
    )


def save_run_config_toml(
    *,
    path_config: PathConfig,
    run_config: RunConfig,
    config_path: str | Path,
) -> Path:
    """Persist a pipeline run config TOML through the repo-owned config path helper."""
    resolved_config_path = path_config.resolve_pipeline_config_path(config_path, create_parent=True)
    run_config.save_toml(resolved_config_path)
    return resolved_config_path


def persist_advio_demo_run_config(
    *,
    path_config: PathConfig,
    sequence_id: str,
    mode: PipelineMode,
    method: MethodId,
    dataset_frame_stride: int = 1,
    dataset_target_fps: float | None = None,
    config_path: str | Path | None = None,
) -> Path:
    """Persist the canonical ADVIO demo run config under `.configs/pipelines/` by default."""
    run_config = build_advio_demo_run_config(
        path_config=path_config,
        sequence_id=sequence_id,
        mode=mode,
        method=method,
        dataset_frame_stride=dataset_frame_stride,
        dataset_target_fps=dataset_target_fps,
    )
    return save_run_config_toml(
        path_config=path_config,
        run_config=run_config,
        config_path=(config_path or f"{run_config.experiment_name}.toml"),
    )


__all__ = [
    "build_advio_demo_run_config",
    "build_runtime_source_from_run_config",
    "load_run_config_toml",
    "persist_advio_demo_run_config",
    "save_run_config_toml",
]
