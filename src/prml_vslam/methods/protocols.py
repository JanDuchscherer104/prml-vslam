"""Package-local protocol seams for SLAM backends and sessions.

These protocols define the method-owned behavior boundary between pipeline
orchestration and concrete backend wrappers. They explain how a backend consumes
normalized inputs and returns normalized durable artifacts without exposing
upstream-private runtime APIs to the rest of the repository.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from prml_vslam.benchmark import PreparedBenchmarkInputs, ReferenceSource
from prml_vslam.interfaces import FramePacket
from prml_vslam.methods.contracts import MethodId, SlamBackendConfig, SlamOutputPolicy
from prml_vslam.methods.session_init import SlamSessionInit
from prml_vslam.methods.updates import SlamUpdate
from prml_vslam.pipeline.contracts.artifacts import SlamArtifacts
from prml_vslam.pipeline.contracts.sequence import SequenceManifest


@runtime_checkable
class SlamSession(Protocol):
    """Consume streaming frames and buffer method-owned live updates.

    The lifecycle is ``start_session() -> step(...) -> try_get_updates() ->
    close()``. The returned :class:`SlamUpdate` values are live telemetry,
    while :class:`prml_vslam.pipeline.SlamArtifacts` remains the durable output
    boundary.
    """

    def step(self, frame: FramePacket) -> None:
        """Consume one frame and prepare an incremental SLAM update."""

    def try_get_updates(self) -> list[SlamUpdate]:
        """Retrieve any pending incremental SLAM updates non-blockingly."""

    def close(self) -> SlamArtifacts:
        """Finalize the session and return the persisted SLAM artifacts."""


@runtime_checkable
class OfflineSlamBackend(Protocol):
    """Execute over a normalized offline sequence manifest."""

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
    """Start one incremental session over normalized repository inputs."""

    method_id: MethodId

    def start_session(
        self,
        session_init: SlamSessionInit,
        backend_config: SlamBackendConfig,
        output_policy: SlamOutputPolicy,
        artifact_root: Path,
    ) -> SlamSession:
        """Prepare a streaming-capable session for incremental frame updates."""


@runtime_checkable
class SlamBackend(OfflineSlamBackend, StreamingSlamBackend, Protocol):
    """Combine the offline and streaming method seams into one backend contract."""


__all__ = [
    "OfflineSlamBackend",
    "SlamBackend",
    "SlamSession",
    "StreamingSlamBackend",
]
