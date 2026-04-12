"""Shared helpers for the bounded ADVIO pipeline demo."""

from __future__ import annotations

from pathlib import Path

from prml_vslam.benchmark import (
    BenchmarkConfig,
    CloudBenchmarkConfig,
    EfficiencyBenchmarkConfig,
    TrajectoryBenchmarkConfig,
)
from prml_vslam.datasets.contracts import DatasetId
from prml_vslam.methods import MethodId
from prml_vslam.pipeline import PipelineMode, RunRequest
from prml_vslam.pipeline.contracts.request import DatasetSourceSpec, SlamStageConfig
from prml_vslam.utils import PathConfig
from prml_vslam.visualization import VisualizationConfig


def build_advio_demo_request(
    *,
    path_config: PathConfig,
    sequence_id: str,
    mode: PipelineMode,
    method: MethodId,
) -> RunRequest:
    """Build the canonical bounded ADVIO demo request shared by app and CLI."""
    return RunRequest(
        experiment_name=f"advio-{mode.value}-{sequence_id}-{method.value}",
        mode=mode,
        output_dir=path_config.artifacts_dir,
        source=DatasetSourceSpec(dataset_id=DatasetId.ADVIO, sequence_id=sequence_id),
        slam=SlamStageConfig(method=method),
        benchmark=BenchmarkConfig(
            reference={"enabled": False},
            trajectory=TrajectoryBenchmarkConfig(enabled=False),
            cloud=CloudBenchmarkConfig(enabled=False),
            efficiency=EfficiencyBenchmarkConfig(enabled=False),
        ),
        visualization=VisualizationConfig(connect_live_viewer=False),
    )


def load_run_request_toml(*, path_config: PathConfig, config_path: str | Path) -> RunRequest:
    """Load a pipeline request TOML through the repo-owned config path helper."""
    resolved_config_path = path_config.resolve_pipeline_config_path(config_path, must_exist=True)
    return RunRequest.from_toml(resolved_config_path)


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
    config_path: str | Path | None = None,
) -> Path:
    """Persist the canonical ADVIO demo request under `.configs/pipelines/` by default."""
    request = build_advio_demo_request(
        path_config=path_config,
        sequence_id=sequence_id,
        mode=mode,
        method=method,
    )
    return save_run_request_toml(
        path_config=path_config,
        request=request,
        config_path=(config_path or f"{request.experiment_name}.toml"),
    )


__all__ = [
    "build_advio_demo_request",
    "load_run_request_toml",
    "persist_advio_demo_request",
    "save_run_request_toml",
]
