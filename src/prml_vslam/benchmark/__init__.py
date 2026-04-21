"""Benchmark policy contracts."""

from .contracts import (
    BenchmarkConfig,
    CloudBenchmarkConfig,
    EfficiencyBenchmarkConfig,
    ReferenceCloudCoordinateStatus,
    ReferenceCloudSource,
    ReferenceReconstructionConfig,
    ReferenceSource,
    TrajectoryBenchmarkConfig,
)

__all__ = [
    "BenchmarkConfig",
    "CloudBenchmarkConfig",
    "EfficiencyBenchmarkConfig",
    "ReferenceCloudCoordinateStatus",
    "ReferenceCloudSource",
    "ReferenceSource",
    "ReferenceReconstructionConfig",
    "TrajectoryBenchmarkConfig",
]

# TODO: currently there is big redundancy and responsibility conflicts between benchmark and eval modules. decide how to optimally split responsibilities and avoid redundancies!
