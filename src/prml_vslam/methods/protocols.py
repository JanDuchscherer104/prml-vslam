"""Package-local protocol seams for SLAM backends and sessions.

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
from prml_vslam.interfaces.slam import SlamArtifacts, SlamSessionInit, SlamUpdate
from prml_vslam.methods.config_contracts import MethodId, SlamBackendConfig, SlamOutputPolicy


#  TODO: Why do we need both SlamSession and SlamBackend?
@runtime_checkable
class SlamSession(Protocol):
    """Consume streaming frames and buffer method-owned live updates.

    The lifecycle is ``start_session() -> step(...) -> try_get_updates() ->
    close()``. The returned :class:`prml_vslam.interfaces.slam.SlamUpdate`
    values are method-owned live telemetry and may include arrays or backend
    diagnostics; :class:`prml_vslam.interfaces.slam.SlamArtifacts` remains the
    durable output boundary. A session owns run-specific mutable algorithm
    state, while the pipeline SLAM stage owns when that session is created,
    driven, drained, and finalized.
    """

    @abstractmethod
    def step(self, frame: FramePacket) -> None:
        """Consume one frame and prepare an incremental SLAM update."""

    @abstractmethod
    def try_get_updates(self) -> list[SlamUpdate]:
        """Retrieve any pending incremental SLAM updates non-blockingly."""

    @abstractmethod
    def close(self) -> SlamArtifacts:
        """Finalize the session and return the persisted SLAM artifacts."""


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
    """Start one incremental session over normalized repository inputs.

    Streaming backends receive the same run context as offline execution before
    frame packets arrive. This lets dataset-backed replay inputs and benchmark
    references remain explicit while the hot path consumes only
    :class:`prml_vslam.interfaces.runtime.FramePacket` values.
    """

    method_id: MethodId

    @abstractmethod
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
    """Backend that supports both bounded offline runs and streaming sessions."""


__all__ = [
    "OfflineSlamBackend",
    "SlamBackend",
    "SlamSession",
    "StreamingSlamBackend",
]
