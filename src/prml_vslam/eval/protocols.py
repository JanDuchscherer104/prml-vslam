"""Protocol seams for repository-local evaluation stages.

These protocols describe the service boundaries that review surfaces and
pipeline stages use when they compute or load persisted evaluation artifacts.
They sit above normalized pipeline outputs and below app or CLI rendering code.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Protocol, runtime_checkable

from prml_vslam.eval.contracts import (
    DenseCloudEvaluationArtifact,
    DenseCloudEvaluationSelection,
)


@runtime_checkable
class DenseCloudEvaluator(Protocol):
    """Load or compute dense-cloud evaluation over normalized run artifacts.

    The protocol is a future-stage seam. Concrete implementations should use
    normalized PLY artifacts and typed coordinate-status metadata rather than
    inferring frame semantics from filenames.
    """

    @abstractmethod
    def load_dense_evaluation(
        self,
        *,
        selection: DenseCloudEvaluationSelection,
    ) -> DenseCloudEvaluationArtifact | None:
        """Load a persisted dense-cloud evaluation when it exists."""
        ...

    @abstractmethod
    def compute_dense_evaluation(
        self,
        *,
        selection: DenseCloudEvaluationSelection,
    ) -> DenseCloudEvaluationArtifact:
        """Compute and persist one dense-cloud evaluation result."""
        ...


__all__ = [
    "DenseCloudEvaluator",
]
