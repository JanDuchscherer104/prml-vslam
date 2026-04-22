"""Stage-local contracts for bounded reconstruction execution."""

from __future__ import annotations

from prml_vslam.interfaces.ingest import PreparedBenchmarkInputs
from prml_vslam.pipeline.contracts.request import RunRequest
from prml_vslam.utils import BaseData, RunArtifactPaths


class ReconstructionRuntimeInput(BaseData):
    """Inputs required to build one offline reference reconstruction."""

    # TODO(pipeline-refactor/WP-09): Replace RunRequest with target
    # ReconstructionStageConfig once `[stages.reconstruction]` owns backend
    # and reference-mode policy.
    request: RunRequest
    """Current run request carrying reference-reconstruction policy."""

    run_paths: RunArtifactPaths
    """Canonical artifact paths for the current run."""

    benchmark_inputs: PreparedBenchmarkInputs | None = None
    """Prepared benchmark inputs containing one RGB-D observation sequence."""


__all__ = ["ReconstructionRuntimeInput"]
