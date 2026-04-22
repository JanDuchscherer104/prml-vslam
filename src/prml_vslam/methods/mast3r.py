"""Placeholder MASt3R backend config and runtime stub."""

from __future__ import annotations

from pathlib import Path

from prml_vslam.benchmark import ReferenceSource
from prml_vslam.interfaces import FramePacket
from prml_vslam.interfaces.ingest import PreparedBenchmarkInputs, SequenceManifest
from prml_vslam.interfaces.slam import SlamArtifacts, SlamUpdate
from prml_vslam.methods.config_contracts import MethodId, SlamBackendConfig, SlamOutputPolicy
from prml_vslam.methods.configs import Mast3rSlamBackendConfig
from prml_vslam.methods.protocols import SlamBackend


class Mast3rSlamBackend(SlamBackend):
    """Runtime stub that fails fast when the placeholder backend is selected."""

    method_id: MethodId = MethodId.MAST3R

    def __init__(self, config: Mast3rSlamBackendConfig) -> None:
        self._config = config

    def start_streaming(
        self,
        sequence_manifest: SequenceManifest,
        benchmark_inputs: PreparedBenchmarkInputs | None,
        baseline_source: ReferenceSource,
        backend_config: SlamBackendConfig,
        output_policy: SlamOutputPolicy,
        artifact_root: Path,
    ) -> None:
        """Fail because MASt3R streaming execution is not implemented."""
        del sequence_manifest, benchmark_inputs, baseline_source, backend_config, output_policy, artifact_root
        raise RuntimeError("MASt3R-SLAM is not executable in this repository yet.")

    def step_streaming(self, frame: FramePacket) -> None:
        """Fail because MASt3R streaming execution is not implemented."""
        del frame
        raise RuntimeError("MASt3R-SLAM is not executable in this repository yet.")

    def drain_streaming_updates(self) -> list[SlamUpdate]:
        """Fail because MASt3R streaming execution is not implemented."""
        raise RuntimeError("MASt3R-SLAM is not executable in this repository yet.")

    def finish_streaming(self) -> SlamArtifacts:
        """Fail because MASt3R streaming execution is not implemented."""
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
