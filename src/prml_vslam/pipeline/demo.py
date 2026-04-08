"""Shared helpers for the bounded ADVIO pipeline demo."""

from __future__ import annotations

from prml_vslam.datasets.contracts import DatasetId
from prml_vslam.methods import MethodId
from prml_vslam.pipeline import PipelineMode, RunRequest
from prml_vslam.pipeline.contracts import (
    BenchmarkEvaluationConfig,
    DatasetSourceSpec,
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
            compare_to_arcore=False,
            evaluate_cloud=False,
            evaluate_efficiency=False,
        ),
    )


__all__ = ["build_advio_demo_request"]
