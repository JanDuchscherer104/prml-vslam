"""Package-local execution seams for reconstruction backends."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol, runtime_checkable

from .configs import ReconstructionBackendConfig
from .contracts import ReconstructionArtifacts, ReconstructionMethodId, ReconstructionObservation


@runtime_checkable
class OfflineReconstructionBackend(Protocol):
    """Consume typed RGB-D observations and write normalized reconstruction artifacts."""

    method_id: ReconstructionMethodId

    def run_sequence(
        self,
        observations: Sequence[ReconstructionObservation],
        *,
        backend_config: ReconstructionBackendConfig,
        artifact_root: Path,
    ) -> ReconstructionArtifacts:
        """Reconstruct one scene from an offline sequence of RGB-D observations."""


__all__ = ["OfflineReconstructionBackend"]
