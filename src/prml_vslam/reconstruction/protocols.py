"""Package-local execution seams for reconstruction backends.

Reconstruction is the dense-geometry analogue of the SLAM method layer: it owns
backend ids, backend configs, and thin adapters around external libraries such
as Open3D. Pipeline stages call these protocols but do not interpret
reconstruction-native state or log directly to Rerun.
"""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Iterable
from pathlib import Path
from typing import Protocol, runtime_checkable

from prml_vslam.interfaces import Observation

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

    @abstractmethod
    def run_sequence(
        self,
        observations: Iterable[Observation],
        *,
        artifact_root: Path,
    ) -> ReconstructionArtifacts:
        """Reconstruct one scene from an offline sequence of RGB-D observations.

        Args:
            observations: Ordered normalized RGB-D observations in the repo pose
                convention.
            artifact_root: Directory where normalized outputs should be written.

        Returns:
            Durable reconstruction artifacts and side metadata.
        """
        ...


__all__ = ["OfflineReconstructionBackend"]
