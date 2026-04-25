"""Canonical ViSTA-SLAM backend adapter (offline + streaming)."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from prml_vslam.interfaces import Observation
from prml_vslam.interfaces.slam import SlamArtifacts
from prml_vslam.methods.contracts import SlamUpdate
from prml_vslam.methods.protocols import SlamBackend
from prml_vslam.methods.stage.backend_config import (
    MethodId,
    SlamBackendConfig,
    SlamOutputPolicy,
    VistaSlamBackendConfig,
)
from prml_vslam.sources.contracts import PreparedBenchmarkInputs, ReferenceSource, SequenceManifest
from prml_vslam.utils import Console, PathConfig

from .session import VistaSlamRuntime, create_vista_runtime


class VistaSlamBackend(SlamBackend):
    """ViSTA-SLAM backend implementing offline and streaming contracts."""

    method_id: MethodId = MethodId.VISTA

    def __init__(
        self,
        config: VistaSlamBackendConfig,
        path_config: PathConfig | None = None,
    ) -> None:
        self._cfg = config
        self._path_config = path_config or PathConfig()
        self._console = Console(__name__).child(self.__class__.__name__)
        self._streaming_runtime: VistaSlamRuntime | None = None

    def start_streaming(
        self,
        sequence_manifest: SequenceManifest,
        benchmark_inputs: PreparedBenchmarkInputs | None,
        baseline_source: ReferenceSource,
        backend_config: SlamBackendConfig,
        output_policy: SlamOutputPolicy,
        artifact_root: Path,
    ) -> None:
        """Load upstream OnlineSLAM and retain backend-owned streaming state."""
        del sequence_manifest, benchmark_inputs, baseline_source, backend_config
        self._streaming_runtime = create_vista_runtime(
            config=self._cfg,
            path_config=self._path_config,
            console=self._console,
            output_policy=output_policy,
            artifact_root=artifact_root,
            live_mode=True,
        )

    def step_streaming(self, frame: Observation) -> None:
        """Consume one streaming frame through the active ViSTA runtime."""
        self._require_streaming_runtime().step(frame)

    def drain_streaming_updates(self) -> list[SlamUpdate]:
        """Retrieve pending ViSTA live updates without exposing runtime state."""
        return self._require_streaming_runtime().drain_updates()

    def finish_streaming(self) -> SlamArtifacts:
        """Finalize the active ViSTA streaming runtime and clear it."""
        runtime = self._require_streaming_runtime()
        artifacts = runtime.finish()
        self._streaming_runtime = None
        return artifacts

    def run_observations(
        self,
        observations: Iterable[Observation],
        benchmark_inputs: PreparedBenchmarkInputs | None,
        baseline_source: ReferenceSource,
        backend_config: SlamBackendConfig,
        output_policy: SlamOutputPolicy,
        artifact_root: Path,
    ) -> SlamArtifacts:
        """Run ViSTA-SLAM over normalized offline observations and persist artifacts."""
        del benchmark_inputs, baseline_source
        runtime = create_vista_runtime(
            config=self._cfg,
            path_config=self._path_config,
            console=self._console,
            artifact_root=artifact_root,
            output_policy=output_policy,
            live_mode=False,
        )
        max_frames = backend_config.max_frames
        self._console.info(
            "Running ViSTA-SLAM on normalized offline observations%s.",
            "" if max_frames is None else f" with max_frames={max_frames}",
        )
        for frame_count, observation in enumerate(observations, start=1):
            if max_frames is not None and frame_count > max_frames:
                break
            runtime.step(observation)
        return runtime.finish()

    def _require_streaming_runtime(self) -> VistaSlamRuntime:
        if self._streaming_runtime is None:
            raise RuntimeError("ViSTA-SLAM streaming backend has not been started.")
        return self._streaming_runtime


__all__ = ["VistaSlamBackend"]
