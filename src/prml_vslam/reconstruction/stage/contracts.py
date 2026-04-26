"""Reconstruction stage runtime input contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, TypeAlias

from pydantic import Field

from prml_vslam.interfaces.artifacts import ArtifactRef
from prml_vslam.methods.stage.contracts import SlamStageOutput
from prml_vslam.reconstruction.config import Open3dTsdfBackendConfig
from prml_vslam.sources.contracts import PreparedBenchmarkInputs
from prml_vslam.sources.stage.contracts import SourceStageOutput
from prml_vslam.utils import BaseConfig, BaseData, RunArtifactPaths

ReconstructionBackend: TypeAlias = Annotated[
    Open3dTsdfBackendConfig,
    Field(discriminator="method_id"),
]


class ReconstructionInputSourceKind(StrEnum):
    """Name the upstream payload selected for reconstruction."""

    RGBD_OBSERVATION_SEQUENCE = "rgbd_observation_sequence"
    SLAM_DENSE_POINT_CLOUD = "slam_dense_point_cloud"
    SLAM_SPARSE_POINT_CLOUD = "slam_sparse_point_cloud"
    SLAM_PREDICTED_GEOMETRY_SEQUENCE = "slam_predicted_geometry_sequence"


class ReconstructionInputSelection(BaseConfig):
    """Persisted policy for selecting a reconstruction input source."""

    source_kind: ReconstructionInputSourceKind = ReconstructionInputSourceKind.RGBD_OBSERVATION_SEQUENCE
    """Preferred upstream payload used to build reconstruction input."""

    require_metric_scale: bool = True
    """Whether SLAM-derived geometry must be metric before reconstruction."""

    allow_native_monocular: bool = False
    """Whether native monocular scale may be consumed when metric scale is unavailable."""

    prefer_dense: bool = True
    """Whether automatic SLAM point-cloud selection should prefer dense outputs."""


class ReconstructionStageInput(BaseData):
    """Inputs required to build one reconstruction artifact."""

    backend: ReconstructionBackend
    run_paths: RunArtifactPaths
    source: SourceStageOutput | None = None
    slam: SlamStageOutput | None = None
    input_source: ReconstructionInputSourceKind = ReconstructionInputSourceKind.RGBD_OBSERVATION_SEQUENCE
    benchmark_inputs: PreparedBenchmarkInputs | None = None
    point_cloud: ArtifactRef | None = None


__all__ = [
    "ReconstructionBackend",
    "ReconstructionInputSelection",
    "ReconstructionInputSourceKind",
    "ReconstructionStageInput",
]
