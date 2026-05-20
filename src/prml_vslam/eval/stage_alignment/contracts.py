"""Trajectory-alignment stage runtime input contracts."""

from __future__ import annotations

from pathlib import Path

from prml_vslam.interfaces.slam import SlamArtifacts
from prml_vslam.sources.contracts import PreparedBenchmarkInputs, ReferenceSource, SequenceManifest
from prml_vslam.utils import BaseData


class TrajectoryAlignmentStageInput(BaseData):
    """Inputs required to compute the Sim(3) trajectory alignment."""

    artifact_root: Path
    baseline_source: ReferenceSource = ReferenceSource.GROUND_TRUTH
    sequence_manifest: SequenceManifest
    benchmark_inputs: PreparedBenchmarkInputs | None = None
    slam: SlamArtifacts


__all__ = ["TrajectoryAlignmentStageInput"]
