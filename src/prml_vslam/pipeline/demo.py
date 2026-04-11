"""Shared helpers for the bounded ADVIO pipeline demo."""

from __future__ import annotations

from pathlib import Path

from prml_vslam.datasets.contracts import DatasetId
from prml_vslam.io.record3d import Record3DTransportId
from prml_vslam.methods import MethodId
from prml_vslam.pipeline import PipelineMode, RunRequest
from prml_vslam.pipeline.contracts import (
    BenchmarkEvaluationConfig,
    DatasetSourceSpec,
    LiveSourceSpec,
    Record3DLiveSourceSpec,
    ReferenceConfig,
    SlamConfig,
)
from prml_vslam.utils import PathConfig


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
        slam=SlamConfig(method=method, emit_dense_points=True),
        reference=ReferenceConfig(enabled=False),
        evaluation=BenchmarkEvaluationConfig(
            evaluate_trajectory=False,
            compare_to_arcore=False,
            evaluate_cloud=False,
            evaluate_efficiency=False,
        ),
    )


def load_run_request_toml(*, path_config: PathConfig, config_path: str | Path) -> RunRequest:
    """Load a pipeline request TOML through the repo-owned config path helper."""
    resolved_config_path = path_config.resolve_pipeline_config_path(config_path, must_exist=True)
    request = RunRequest.from_toml(resolved_config_path)
    return _normalize_legacy_record3d_source(request)


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


def _normalize_legacy_record3d_source(request: RunRequest) -> RunRequest:
    """Convert legacy Record3D live-source TOML payloads into the typed source contract."""
    match request.source:
        case LiveSourceSpec(source_id="record3d_usb", persist_capture=persist_capture):
            normalized_source = Record3DLiveSourceSpec(
                transport=Record3DTransportId.USB,
                persist_capture=persist_capture,
            )
        case LiveSourceSpec(source_id="record3d_wifi", persist_capture=persist_capture):
            normalized_source = Record3DLiveSourceSpec(
                transport=Record3DTransportId.WIFI,
                persist_capture=persist_capture,
            )
        case _:
            return request
    return request.model_copy(update={"source": normalized_source})
