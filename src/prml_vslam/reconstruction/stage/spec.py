"""Runtime spec for the reconstruction stage."""

from __future__ import annotations

from prml_vslam.interfaces.artifacts import ArtifactRef
from prml_vslam.pipeline.contracts.context import PipelineExecutionContext
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.runner import StageDependencyError
from prml_vslam.pipeline.stages.base.config import FailureFingerprint
from prml_vslam.pipeline.stages.base.spec import StageRuntimeSpec
from prml_vslam.reconstruction.stage.contracts import (
    ReconstructionInputSourceKind,
    ReconstructionStageInput,
)
from prml_vslam.reconstruction.stage.runtime import ReconstructionRuntime
from prml_vslam.sources.contracts import PreparedBenchmarkInputs
from prml_vslam.utils import BaseData


class _ReconstructionFailureInputFingerprint(BaseData):
    """Typed reconstruction input fingerprint payload."""

    input_source: ReconstructionInputSourceKind
    benchmark_inputs: PreparedBenchmarkInputs | None = None
    point_cloud: ArtifactRef | None = None


def _build_offline_input(context: PipelineExecutionContext) -> ReconstructionStageInput:
    config = context.run_config.stages.reconstruction
    input_source = config.input_selection.source_kind
    source = context.results.require_source_output()
    slam = None
    point_cloud = None

    match input_source:
        case ReconstructionInputSourceKind.RGBD_OBSERVATION_SEQUENCE:
            benchmark_inputs = context.results.require_benchmark_inputs()
        case ReconstructionInputSourceKind.SLAM_DENSE_POINT_CLOUD:
            slam = context.results.require_slam_output()
            if slam.artifacts.dense_points_ply is None:
                raise StageDependencyError(
                    "Reconstruction requested a dense SLAM point cloud, but SLAM did not produce one."
                )
            benchmark_inputs = context.results.require_benchmark_inputs()
            point_cloud = slam.artifacts.dense_points_ply
        case ReconstructionInputSourceKind.SLAM_SPARSE_POINT_CLOUD:
            slam = context.results.require_slam_output()
            if slam.artifacts.sparse_points_ply is None:
                raise StageDependencyError(
                    "Reconstruction requested a sparse SLAM point cloud, but SLAM did not produce one."
                )
            benchmark_inputs = context.results.require_benchmark_inputs()
            point_cloud = slam.artifacts.sparse_points_ply
        case ReconstructionInputSourceKind.SLAM_PREDICTED_GEOMETRY_SEQUENCE:
            raise StageDependencyError(
                "Reconstruction predicted-geometry input is declared but no PredictedGeometrySequenceRef "
                "contract is implemented yet."
            )

    return ReconstructionStageInput(
        backend=config.backend,
        run_paths=context.run_paths,
        source=source,
        slam=slam,
        input_source=input_source,
        benchmark_inputs=benchmark_inputs,
        point_cloud=point_cloud,
    )


def _failure_fingerprint(context: PipelineExecutionContext) -> FailureFingerprint:
    config = context.run_config.stages.reconstruction
    input_source = config.input_selection.source_kind
    input_payload = _ReconstructionFailureInputFingerprint(input_source=input_source)
    match input_source:
        case ReconstructionInputSourceKind.RGBD_OBSERVATION_SEQUENCE:
            input_payload.benchmark_inputs = context.results.require_benchmark_inputs()
        case ReconstructionInputSourceKind.SLAM_DENSE_POINT_CLOUD:
            input_payload.point_cloud = context.results.require_slam_artifacts().dense_points_ply
        case ReconstructionInputSourceKind.SLAM_SPARSE_POINT_CLOUD:
            input_payload.point_cloud = context.results.require_slam_artifacts().sparse_points_ply
        case ReconstructionInputSourceKind.SLAM_PREDICTED_GEOMETRY_SEQUENCE:
            pass
    return FailureFingerprint(
        config_payload=config,
        input_payload=input_payload,
    )


RECONSTRUCTION_STAGE_SPEC = StageRuntimeSpec(
    stage_key=StageKey.RECONSTRUCTION,
    runtime_factory=lambda _context: ReconstructionRuntime,
    build_offline_input=_build_offline_input,
    failure_fingerprint=_failure_fingerprint,
)

__all__ = ["RECONSTRUCTION_STAGE_SPEC"]
