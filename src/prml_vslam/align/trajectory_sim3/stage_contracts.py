"""Trajectory-alignment stage runtime input contracts."""

from __future__ import annotations

from pathlib import Path

from prml_vslam.interfaces.slam import SlamArtifacts
from prml_vslam.methods.stage.backend_config import MethodId
from prml_vslam.sources.contracts import PreparedBenchmarkInputs, ReferenceSource, SequenceManifest
from prml_vslam.utils import BaseData, PathConfig


class TrajectoryAlignmentStageInput(BaseData):
    """Inputs required to compute the Sim(3) trajectory alignment."""

    artifact_root: Path
    path_config: PathConfig
    baseline_source: ReferenceSource = ReferenceSource.GROUND_TRUTH
    method_id: MethodId | None = None
    sequence_manifest: SequenceManifest
    benchmark_inputs: PreparedBenchmarkInputs | None = None
    slam: SlamArtifacts


__all__ = ["TrajectoryAlignmentStageInput"]
