"""Stage-local contracts for bounded reconstruction execution."""

from __future__ import annotations

from prml_vslam.interfaces.ingest import PreparedBenchmarkInputs
from prml_vslam.pipeline.contracts.request import RunRequest
from prml_vslam.utils import BaseData, RunArtifactPaths


class ReconstructionRuntimeInput(BaseData):
    """Inputs required to build one offline reference reconstruction.

    The current input is compatibility-shaped around benchmark reference policy.
    The target ``reconstruction`` stage should receive reconstruction stage
    config plus reconstruction-owned backend config, while continuing to consume
    prepared RGB-D observation references from source/benchmark preparation.
    """

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
