"""Current protocol seams for the pipeline streaming and SLAM runtime."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from prml_vslam.interfaces import FramePacket
from prml_vslam.methods.contracts import MethodId
from prml_vslam.pipeline.contracts import SequenceManifest, SlamArtifacts, SlamConfig, SlamUpdate
from prml_vslam.protocols import FramePacketStream


class StreamingSequenceSource(Protocol):
    """Protocol for replay or live sources used by streaming pipeline sessions."""

    label: str

    def prepare_sequence_manifest(self, output_dir: Path) -> SequenceManifest:
        """Materialize or resolve the normalized sequence boundary for one run."""

    def open_stream(self, *, loop: bool) -> FramePacketStream:
        """Open the frame stream consumed by the SLAM session."""


class SlamSession(Protocol):
    """Protocol for a live SLAM session that consumes incremental frames."""

    def step(self, frame: FramePacket) -> SlamUpdate:
        """Consume one frame and return an incremental SLAM update."""

    def close(self) -> SlamArtifacts:
        """Finalize the session and return the persisted SLAM artifacts."""


class SlamBackend(Protocol):
    """Protocol for SLAM backends that support both batch and streaming execution."""

    method_id: MethodId

    def run_sequence(
        self,
        sequence: SequenceManifest,
        cfg: SlamConfig,
        artifact_root: Path,
    ) -> SlamArtifacts:
        """Run the backend over a materialized sequence and persist artifacts."""

    def start_session(self, cfg: SlamConfig, artifact_root: Path) -> SlamSession:
        """Prepare a streaming-capable session for incremental frame updates."""


__all__ = [
    "SlamBackend",
    "SlamSession",
    "StreamingSequenceSource",
]
