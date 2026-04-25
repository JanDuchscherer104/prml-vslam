"""Trajectory-evaluation stage runtime input contracts."""

from __future__ import annotations

from pathlib import Path

from prml_vslam.interfaces.slam import SlamArtifacts
from prml_vslam.methods.stage.backend_config import MethodId
from prml_vslam.sources.contracts import PreparedBenchmarkInputs, ReferenceSource, SequenceManifest
from prml_vslam.utils import BaseData


class TrajectoryEvaluationStageInput(BaseData):
    """Inputs required to compute repository trajectory metrics."""

    artifact_root: Path
    baseline_source: ReferenceSource = ReferenceSource.GROUND_TRUTH
    method_id: MethodId | None = None
    method_label: str = "unknown"
    sequence_manifest: SequenceManifest
    benchmark_inputs: PreparedBenchmarkInputs | None = None
    slam: SlamArtifacts


__all__ = ["TrajectoryEvaluationStageInput"]
