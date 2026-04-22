"""Stage-local contracts for bounded trajectory-evaluation execution."""

from __future__ import annotations

from prml_vslam.interfaces.ingest import PreparedBenchmarkInputs, SequenceManifest
from prml_vslam.interfaces.slam import SlamArtifacts
from prml_vslam.pipeline.contracts.plan import RunPlan
from prml_vslam.pipeline.contracts.request import RunRequest
from prml_vslam.utils import BaseData


class TrajectoryEvaluationRuntimeInput(BaseData):
    """Inputs required to compute repository trajectory metrics."""

    # TODO(pipeline-refactor/WP-09): Replace RunRequest with target RunConfig
    # benchmark policy once bounded runtimes are constructed from stage configs.
    request: RunRequest
    """Current run request carrying benchmark trajectory policy."""

    plan: RunPlan
    """Compiled run plan whose artifact root owns evaluation outputs."""

    sequence_manifest: SequenceManifest
    """Normalized source sequence manifest."""

    benchmark_inputs: PreparedBenchmarkInputs | None = None
    """Prepared benchmark references, when the source provides them."""

    slam: SlamArtifacts
    """Normalized SLAM artifact bundle with the estimated trajectory."""


__all__ = ["TrajectoryEvaluationRuntimeInput"]
