"""Placeholder MASt3R backend config and runtime stub."""

from __future__ import annotations

from pathlib import Path

from prml_vslam.benchmark import PreparedBenchmarkInputs, ReferenceSource
from prml_vslam.methods.config_contracts import MethodId, SlamBackendConfig, SlamOutputPolicy
from prml_vslam.methods.configs import Mast3rSlamBackendConfig
from prml_vslam.methods.protocols import SlamBackend, SlamSession
from prml_vslam.methods.session_init import SlamSessionInit
from prml_vslam.pipeline.contracts.artifacts import SlamArtifacts
from prml_vslam.pipeline.contracts.sequence import SequenceManifest


class Mast3rSlamBackend(SlamBackend):
    """Runtime stub that fails fast when the placeholder backend is selected."""

    method_id: MethodId = MethodId.MAST3R

    def __init__(self, config: Mast3rSlamBackendConfig) -> None:
        self._config = config

    def start_session(
        self,
        session_init: SlamSessionInit,
        backend_config: SlamBackendConfig,
        output_policy: SlamOutputPolicy,
        artifact_root: Path,
    ) -> SlamSession:
        """Fail because MASt3R streaming execution is not implemented."""
        del session_init, backend_config, output_policy, artifact_root
        raise RuntimeError("MASt3R-SLAM is not executable in this repository yet.")

    def run_sequence(
        self,
        sequence: SequenceManifest,
        benchmark_inputs: PreparedBenchmarkInputs | None,
        baseline_source: ReferenceSource,
        backend_config: SlamBackendConfig,
        output_policy: SlamOutputPolicy,
        artifact_root: Path,
    ) -> SlamArtifacts:
        """Fail because MASt3R offline execution is not implemented."""
        del sequence, benchmark_inputs, baseline_source, backend_config, output_policy, artifact_root
        raise RuntimeError("MASt3R-SLAM is not executable in this repository yet.")


__all__ = ["Mast3rSlamBackend", "Mast3rSlamBackendConfig"]
