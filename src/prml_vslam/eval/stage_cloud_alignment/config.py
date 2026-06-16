"""Persisted config for the ``align.cloud`` stage."""

from __future__ import annotations

from pathlib import Path

from pydantic import ConfigDict, Field

from prml_vslam.pipeline.contracts.context import PipelinePlanContext
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.config import StageConfig
from prml_vslam.sources.config import (
    AdvioSourceConfig,
    Record3DDatasetSourceConfig,
    SourceBackendConfig,
    TumRgbdSourceConfig,
)
from prml_vslam.sources.contracts import PreparedBenchmarkInputs, ReferenceCloudSource
from prml_vslam.sources.datasets.contracts import DatasetId
from prml_vslam.sources.datasets.normalization import (
    dataset_service,
    normalized_profile_for_dataset,
    normalized_store_for_service,
)
from prml_vslam.utils import PathConfig


class CloudAlignmentStageConfig(StageConfig):
    """Offline policy for aligning SLAM clouds before dense-cloud metrics."""

    model_config = ConfigDict(extra="ignore")

    stage_key: StageKey | None = StageKey.CLOUD_ALIGNMENT
    enabled: bool = False
    reference_source: ReferenceCloudSource | None = None
    """Preferred source-prepared reference cloud, when available."""

    max_correspondence_distance_m: float = Field(default=0.05, gt=0.0)
    """Maximum ICP correspondence distance in meters."""

    def availability(self, context: PipelinePlanContext) -> tuple[bool, str | None]:
        if not context.run_config.stages.align_trajectory.enabled:
            return False, "Cloud alignment requires `align.trajectory`."
        slam_backend = context.run_config.stages.slam.backend
        if slam_backend is None:
            return False, "Cloud alignment requires `[stages.slam.backend]`."
        backend = context.slam_backend if context.slam_backend is not None else slam_backend
        if not backend.supports_dense_points:
            return False, f"{backend.display_name} does not support dense point-cloud outputs."
        if (
            not context.run_config.stages.slam.outputs.emit_dense_points
            and context.run_config.reuse_artifact_root is None
        ):
            return False, "Cloud alignment requires dense SLAM point-cloud outputs."
        source_backend = context.run_config.stages.source.backend
        if context.run_config.reuse_artifact_root is None and not _source_reference_cloud_available(
            source_backend,
            preferred_source=self.reference_source,
            path_config=context.path_config,
        ):
            if not context.run_config.stages.reconstruction.enabled:
                return False, "Cloud alignment requires a source-prepared reference cloud or reference reconstruction."
            reconstruction_available, reconstruction_reason = context.run_config.stages.reconstruction.availability(
                context
            )
            if not reconstruction_available:
                return False, f"Cloud alignment requires available reference reconstruction: {reconstruction_reason}"
        return True, None

    def planned_outputs(self, context: PipelinePlanContext) -> list[Path]:
        return [
            context.run_paths.artifact_root / "evaluation" / "cloud_alignment.json",
            context.run_paths.artifact_root / "evaluation" / "point_cloud_sim3_icp_aligned.ply",
        ]


def _source_reference_cloud_available(
    source_backend: SourceBackendConfig | None,
    *,
    preferred_source: ReferenceCloudSource | None,
    path_config: PathConfig,
) -> bool:
    if isinstance(source_backend, AdvioSourceConfig):
        return False
    if isinstance(source_backend, Record3DDatasetSourceConfig):
        return preferred_source in {None, ReferenceCloudSource.RECORD3D_LIDAR}
    if isinstance(source_backend, TumRgbdSourceConfig):
        return preferred_source in {None, ReferenceCloudSource.TUM_RGBD} and _tum_rgbd_reference_cloud_inputs_available(
            sequence_id=source_backend.sequence_id,
            path_config=path_config,
        )
    return False


def _tum_rgbd_reference_cloud_inputs_available(*, sequence_id: str, path_config: PathConfig) -> bool:
    source_backend = TumRgbdSourceConfig(sequence_id=sequence_id)
    service = dataset_service(DatasetId.TUM_RGBD, path_config)
    profile = normalized_profile_for_dataset(
        dataset_id=DatasetId.TUM_RGBD,
        service=service,
        source_config=source_backend,
    )
    try:
        entry = normalized_store_for_service(DatasetId.TUM_RGBD, path_config).load_entry(profile)
        benchmark_inputs = PreparedBenchmarkInputs.model_validate_json(
            entry.benchmark_inputs_path.read_text(encoding="utf-8")
        )
    except (FileNotFoundError, OSError, RuntimeError, ValueError):
        return False
    return any(ref.path.exists() and ref.metadata_path.exists() for ref in benchmark_inputs.reference_clouds)


__all__ = ["CloudAlignmentStageConfig"]
