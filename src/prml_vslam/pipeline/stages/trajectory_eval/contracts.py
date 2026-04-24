"""Stage-local contracts for bounded trajectory-evaluation execution."""

from __future__ import annotations

from pathlib import Path

from prml_vslam.benchmark.contracts import ReferenceSource
from prml_vslam.interfaces.ingest import PreparedBenchmarkInputs, SequenceManifest
from prml_vslam.interfaces.slam import SlamArtifacts
from prml_vslam.pipeline.stages.slam.config import MethodId
from prml_vslam.utils import BaseData


class TrajectoryEvaluationRuntimeInput(BaseData):
    """Inputs required to compute repository trajectory metrics.

    The evaluation stage is downstream of source preparation and SLAM
    completion. It needs the normalized sequence, optional prepared references,
    and the estimated trajectory artifact; it must not discover references by
    walking dataset folders independently.
    """

    artifact_root: Path
    """Run-owned artifact root where evaluation outputs are written."""

    baseline_source: ReferenceSource = ReferenceSource.GROUND_TRUTH
    """Prepared reference trajectory selected for evaluation."""

    method_id: MethodId | None = None
    """Selected SLAM backend id, when available for labels."""

    method_label: str = "unknown"
    """Human-readable SLAM backend label used in loaded evaluation artifacts."""

    sequence_manifest: SequenceManifest
    """Normalized source sequence manifest."""

    benchmark_inputs: PreparedBenchmarkInputs | None = None
    """Prepared benchmark references, when the source provides them."""

    slam: SlamArtifacts
    """Normalized SLAM artifact bundle with the estimated trajectory."""


__all__ = ["TrajectoryEvaluationRuntimeInput"]
