"""Package-local protocol seams for SLAM backends and sessions."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol, runtime_checkable

from prml_vslam.benchmark import PreparedBenchmarkInputs, ReferenceSource
from prml_vslam.interfaces import FramePacket
from prml_vslam.methods.contracts import MethodId, SlamBackendConfig, SlamOutputPolicy
from prml_vslam.methods.updates import SlamUpdate
from prml_vslam.pipeline.contracts.artifacts import SlamArtifacts
from prml_vslam.pipeline.contracts.sequence import SequenceManifest


@runtime_checkable
class SlamSession(Protocol):
    """Protocol for a live SLAM session that consumes incremental frames."""

    def step(self, frame: FramePacket) -> None:
        """Consume one frame and prepare an incremental SLAM update."""

    def try_get_updates(self) -> list[SlamUpdate]:
        """Retrieve any pending incremental SLAM updates non-blockingly."""

    def close(self) -> SlamArtifacts:
        """Finalize the session and return the persisted SLAM artifacts."""


@runtime_checkable
class OfflineSlamBackend(Protocol):
    """Protocol for SLAM backends that operate on materialized sequences."""

    method_id: MethodId

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
    """Protocol for SLAM backends that support incremental streaming execution."""

    method_id: MethodId

    def start_session(
        self,
        backend_config: SlamBackendConfig,
        output_policy: SlamOutputPolicy,
        artifact_root: Path,
    ) -> SlamSession:
        """Prepare a streaming-capable session for incremental frame updates."""


@runtime_checkable
class ProcessStreamingSlamBackend(StreamingSlamBackend, Protocol):
    """Protocol for backends that can provide a picklable streaming-session factory."""

    def streaming_session_factory(
        self,
        backend_config: SlamBackendConfig,
        output_policy: SlamOutputPolicy,
        artifact_root: Path,
    ) -> Callable[[], SlamSession]:
        """Return a picklable factory that builds one streaming SLAM session."""


@runtime_checkable
class SlamBackend(OfflineSlamBackend, StreamingSlamBackend, Protocol):
    """Protocol for backends that implement both offline and streaming SLAM."""


__all__ = [
    "OfflineSlamBackend",
    "ProcessStreamingSlamBackend",
    "SlamBackend",
    "SlamSession",
    "StreamingSlamBackend",
]
