"""Config-driven method selection for reconstruction backends."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from prml_vslam.interfaces import RgbdObservation

from .configs import ReconstructionBackendConfig
from .contracts import ReconstructionArtifacts
from .protocols import OfflineReconstructionBackend


class ReconstructionHarness:
    """Build and run the selected reconstruction backend in one place.

    The harness keeps backend switching local to the reconstruction package so
    pipeline code can depend on typed config and one protocol seam rather than
    importing concrete backend modules directly.
    """

    def __init__(self, backend_config: ReconstructionBackendConfig) -> None:
        self._backend_config = backend_config

    @property
    def backend_config(self) -> ReconstructionBackendConfig:
        """Return the typed config that selected the active backend."""
        return self._backend_config

    def build_backend(self) -> OfflineReconstructionBackend:
        """Construct the configured backend through the repo config-as-factory pattern."""
        backend = self._backend_config.setup_target()
        return backend

    def run_sequence(
        self,
        observations: Iterable[RgbdObservation],
        *,
        artifact_root: Path,
    ) -> ReconstructionArtifacts:
        """Execute the configured backend over one offline observation sequence."""
        backend = self.build_backend()
        return backend.run_sequence(
            observations,
            backend_config=self._backend_config,
            artifact_root=artifact_root,
        )


__all__ = ["ReconstructionHarness"]
