"""Shared helpers for launching the bounded ADVIO pipeline demo run."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from prml_vslam.datasets.advio import AdvioPoseSource
from prml_vslam.datasets.contracts import DatasetId
from prml_vslam.methods import MethodId
from prml_vslam.pipeline import PipelineMode, RunRequest
from prml_vslam.pipeline.contracts import (
    BenchmarkEvaluationConfig,
    DatasetSourceSpec,
    ReferenceConfig,
    SlamConfig,
)

if TYPE_CHECKING:
    from .bootstrap import AppContext


def start_advio_demo_run(
    context: AppContext,
    *,
    sequence_id: int,
    mode: PipelineMode,
    method: MethodId,
    pose_source: AdvioPoseSource,
    respect_video_rotation: bool,
) -> None:
    """Start one bounded ADVIO benchmark-demo run via the shared pipeline runtime."""
    scene = context.advio_service.scene(sequence_id)
    request = build_demo_request(
        output_dir=context.path_config.artifacts_dir,
        sequence_slug=scene.sequence_slug,
        mode=mode,
        method=method,
    )
    source = context.advio_service.build_streaming_source(
        sequence_id=sequence_id,
        pose_source=pose_source,
        respect_video_rotation=respect_video_rotation,
    )
    context.pipeline_runtime.start(request=request, source=source)


def build_demo_request(
    *,
    output_dir: Path,
    sequence_slug: str,
    mode: PipelineMode,
    method: MethodId,
) -> RunRequest:
    """Build the bounded run request used by Streamlit demo run launchers."""
    return RunRequest(
        experiment_name=f"advio-{mode.value}-{sequence_slug}-{method.value}",
        mode=mode,
        output_dir=output_dir,
        source=DatasetSourceSpec(dataset_id=DatasetId.ADVIO, sequence_id=sequence_slug),
        slam=SlamConfig(method=method, emit_dense_points=True),
        reference=ReferenceConfig(enabled=False),
        evaluation=BenchmarkEvaluationConfig(
            compare_to_arcore=False,
            evaluate_cloud=False,
            evaluate_efficiency=False,
        ),
    )


__all__ = ["build_demo_request", "start_advio_demo_run"]
