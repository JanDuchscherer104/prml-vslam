"""Package-local execution seams for reconstruction backends."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Protocol, runtime_checkable

from prml_vslam.interfaces import RgbdObservation

from .config import ReconstructionBackendConfig
from .contracts import ReconstructionArtifacts, ReconstructionMethodId


@runtime_checkable
class OfflineReconstructionBackend(Protocol):
    """Consume typed RGB-D observations and write normalized reconstruction artifacts."""

    method_id: ReconstructionMethodId

    def run_sequence(
        self,
        observations: Iterable[RgbdObservation],
        *,
        backend_config: ReconstructionBackendConfig,
        artifact_root: Path,
    ) -> ReconstructionArtifacts:
        """Reconstruct one scene from an offline sequence of RGB-D observations."""


@runtime_checkable
class ReconstructionSession(Protocol):
    """Stateful streaming reconstruction session seam.

    Open3D TSDF does not implement this seam yet. It exists so future
    streaming-capable reconstruction backends can share one package-local
    lifecycle contract.
    """

    def push_observation(self, observation: RgbdObservation) -> None:
        """Integrate one normalized RGB-D observation into the live reconstruction."""

    def status(self) -> dict[str, int | float | str]:
        """Return implementation-owned lightweight status telemetry."""

    def finish(self, *, artifact_root: Path) -> ReconstructionArtifacts:
        """Finalize the streaming reconstruction and write durable artifacts."""


@runtime_checkable
class StreamingReconstructionBackend(Protocol):
    """Start stateful streaming reconstruction over normalized RGB-D observations."""

    method_id: ReconstructionMethodId

    def start_session(
        self,
        *,
        backend_config: ReconstructionBackendConfig,
        artifact_root: Path,
    ) -> ReconstructionSession:
        """Start one streaming reconstruction session."""


__all__ = ["OfflineReconstructionBackend", "ReconstructionSession", "StreamingReconstructionBackend"]
