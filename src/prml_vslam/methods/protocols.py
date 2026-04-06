"""Package-local protocol seams for SLAM backends and sessions."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from prml_vslam.interfaces import FramePacket
from prml_vslam.methods.contracts import MethodId
from prml_vslam.pipeline.contracts import SequenceManifest, SlamArtifacts, SlamConfig, SlamUpdate


@runtime_checkable
class SlamSession(Protocol):
    """Protocol for a live SLAM session that consumes incremental frames."""

    def step(self, frame: FramePacket) -> SlamUpdate:
        """Consume one frame and return an incremental SLAM update."""

    def close(self) -> SlamArtifacts:
        """Finalize the session and return the persisted SLAM artifacts."""


@runtime_checkable
class OfflineSlamBackend(Protocol):
    """Protocol for SLAM backends that operate on materialized sequences."""

    method_id: MethodId

    def run_sequence(
        self,
        sequence: SequenceManifest,
        cfg: SlamConfig,
        artifact_root: Path,
    ) -> SlamArtifacts:
        """Run the backend over a materialized sequence and persist artifacts."""


@runtime_checkable
class StreamingSlamBackend(Protocol):
    """Protocol for SLAM backends that support incremental streaming execution."""

    method_id: MethodId

    def start_session(self, cfg: SlamConfig, artifact_root: Path) -> SlamSession:
        """Prepare a streaming-capable session for incremental frame updates."""


@runtime_checkable
class SlamBackend(OfflineSlamBackend, StreamingSlamBackend, Protocol):
    """Protocol for backends that implement both offline and streaming SLAM."""


__all__ = [
    "OfflineSlamBackend",
    "SlamBackend",
    "SlamSession",
    "StreamingSlamBackend",
]
