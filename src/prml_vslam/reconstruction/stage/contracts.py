"""Reconstruction stage runtime input contracts."""

from __future__ import annotations

from prml_vslam.reconstruction.stage.config import ReconstructionBackend
from prml_vslam.sources.contracts import PreparedBenchmarkInputs
from prml_vslam.utils import BaseData, RunArtifactPaths


class ReconstructionStageInput(BaseData):
    """Inputs required to build one offline reference reconstruction."""

    backend: ReconstructionBackend
    run_paths: RunArtifactPaths
    benchmark_inputs: PreparedBenchmarkInputs | None = None


__all__ = ["ReconstructionStageInput"]
