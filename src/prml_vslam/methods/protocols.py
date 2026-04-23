"""Package-local protocol seams for SLAM backends.

These protocols define the method-owned behavior boundary between pipeline
orchestration and concrete backend wrappers. They explain how a backend consumes
normalized inputs and returns normalized durable artifacts without exposing
upstream-private runtime APIs to the rest of the repository.
"""

from __future__ import annotations

from abc import abstractmethod
from pathlib import Path
from typing import Protocol, runtime_checkable

from prml_vslam.benchmark.contracts import ReferenceSource
from prml_vslam.interfaces import FramePacket
from prml_vslam.interfaces.ingest import PreparedBenchmarkInputs, SequenceManifest
from prml_vslam.interfaces.slam import SlamArtifacts
from prml_vslam.methods.config_contracts import MethodId, SlamBackendConfig, SlamOutputPolicy
from prml_vslam.methods.contracts import SlamUpdate


@runtime_checkable
class OfflineSlamBackend(Protocol):
    """Execute a backend over a normalized offline sequence manifest.

    Implementations adapt upstream systems such as ViSTA-SLAM or MASt3R-SLAM
    into repository contracts. They may create backend-native workspaces, but
    they must return normalized :class:`prml_vslam.interfaces.slam.SlamArtifacts`
    and keep evaluation, alignment, and viewer policy outside the method
    wrapper.
    """

    method_id: MethodId

    @abstractmethod
    def run_sequence(
        self,
        sequence: SequenceManifest,
        benchmark_inputs: PreparedBenchmarkInputs | None,
        baseline_source: ReferenceSource,
        backend_config: SlamBackendConfig,
        output_policy: SlamOutputPolicy,
        artifact_root: Path,
    ) -> SlamArtifacts:
        """Run the backend over a materialized sequence and persist artifacts."""


@runtime_checkable
class StreamingSlamBackend(Protocol):
    """Expose streaming SLAM lifecycle directly on the backend.

    :class:`prml_vslam.pipeline.stages.slam.runtime.SlamStageRuntime` owns the
    pipeline lifecycle. Backend implementations own method-private mutable
    state behind this protocol and do not expose a separate public session
    object.
    """

    method_id: MethodId

    @abstractmethod
    def start_streaming(
        self,
        sequence_manifest: SequenceManifest,
        benchmark_inputs: PreparedBenchmarkInputs | None,
        baseline_source: ReferenceSource,
        backend_config: SlamBackendConfig,
        output_policy: SlamOutputPolicy,
        artifact_root: Path,
    ) -> None:
        """Prepare backend-owned streaming state before frames arrive."""

    @abstractmethod
    def step_streaming(self, frame: FramePacket) -> None:
        """Consume one streaming frame through backend-owned state."""

    @abstractmethod
    def drain_streaming_updates(self) -> list[SlamUpdate]:
        """Retrieve pending method-owned live updates without blocking."""

    @abstractmethod
    def finish_streaming(self) -> SlamArtifacts:
        """Finalize backend-owned streaming state and persist artifacts."""


@runtime_checkable
class SlamBackend(OfflineSlamBackend, StreamingSlamBackend, Protocol):
    """Backend that supports both bounded offline runs and streaming sessions."""


__all__ = [
    "OfflineSlamBackend",
    "SlamBackend",
    "StreamingSlamBackend",
]
