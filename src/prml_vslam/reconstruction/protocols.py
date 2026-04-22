"""Package-local execution seams for reconstruction backends.

Reconstruction is the dense-geometry analogue of the SLAM method layer: it owns
backend ids, backend configs, and thin adapters around external libraries such
as Open3D. Pipeline stages call these protocols but do not interpret
reconstruction-native state or log directly to Rerun.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Protocol, runtime_checkable

from prml_vslam.interfaces import RgbdObservation

from .config import ReconstructionBackendConfig
from .contracts import ReconstructionArtifacts, ReconstructionMethodId


@runtime_checkable
class OfflineReconstructionBackend(Protocol):
    """Consume typed RGB-D observations and write normalized artifacts.

    Implementations must assume each observation carries coherent
    ``camera_intrinsics``, RGB, metric depth in meters, and ``T_world_camera``
    pose semantics. The returned artifact bundle owns durable outputs, not live
    visualization payloads.
    """

    method_id: ReconstructionMethodId

    def run_sequence(
        self,
        observations: Iterable[RgbdObservation],
        *,
        backend_config: ReconstructionBackendConfig,
        artifact_root: Path,
    ) -> ReconstructionArtifacts:
        """Reconstruct one scene from an offline sequence of RGB-D observations.

        Args:
            observations: Ordered normalized RGB-D observations in the repo pose
                convention.
            backend_config: Method-private reconstruction config used for this
                backend.
            artifact_root: Directory where normalized outputs should be written.

        Returns:
            Durable reconstruction artifacts and side metadata.
        """


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
    """Start stateful streaming reconstruction over normalized RGB-D observations.

    This is reserved for future online reconstruction methods. The current
    Open3D TSDF target remains offline-first until a concrete streaming use
    case needs a live session.
    """

    method_id: ReconstructionMethodId

    def start_session(
        self,
        *,
        backend_config: ReconstructionBackendConfig,
        artifact_root: Path,
    ) -> ReconstructionSession:
        """Start one streaming reconstruction session."""


__all__ = ["OfflineReconstructionBackend", "ReconstructionSession", "StreamingReconstructionBackend"]
