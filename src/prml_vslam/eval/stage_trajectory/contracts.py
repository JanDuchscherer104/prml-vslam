"""Trajectory-evaluation stage runtime input contracts."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field

from prml_vslam.interfaces.slam import SlamArtifacts
from prml_vslam.methods.stage.backend_config import MethodId
from prml_vslam.sources.contracts import (
    PreparedBenchmarkInputs,
    ReferenceSource,
    ReferenceTrajectoryRef,
    SequenceManifest,
)
from prml_vslam.utils import BaseData


class TrajectoryEvaluationStageInput(BaseData):
    """Inputs required to compute repository trajectory metrics."""

    artifact_root: Path
    baseline_source: ReferenceSource = ReferenceSource.GROUND_TRUTH
    method_id: MethodId | None = None
    method_label: str = "unknown"
    sequence_manifest: SequenceManifest
    benchmark_inputs: PreparedBenchmarkInputs | None = None
    reference_trajectory: ReferenceTrajectoryRef | None = None
    candidate_trajectories: list[ReferenceTrajectoryRef] = Field(default_factory=list)
    slam: SlamArtifacts


__all__ = ["TrajectoryEvaluationStageInput"]
