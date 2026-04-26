"""Protocol seams for repository-local evaluation stages.

These protocols describe the service boundaries that review surfaces and
pipeline stages use when they compute or load persisted evaluation artifacts.
They sit above normalized pipeline outputs and below app or CLI rendering code.
"""

from __future__ import annotations

from abc import abstractmethod
from pathlib import Path
from typing import Protocol, runtime_checkable

from prml_vslam.eval.contracts import (
    DenseCloudEvaluationArtifact,
    DenseCloudEvaluationSelection,
    DiscoveredRun,
    EvaluationArtifact,
    EvaluationSelection,
    SelectionSnapshot,
)
from prml_vslam.sources.datasets.contracts import DatasetId


@runtime_checkable
class TrajectoryEvaluator(Protocol):
    """Load or compute trajectory evaluation over normalized run artifacts.

    Implementations resolve a dataset/run selection, read TUM trajectories, and
    persist explicit metric semantics. App pages should call these methods only
    from explicit user actions; implicit recomputation during reruns would make
    benchmark state hard to audit.
    """

    @abstractmethod
    def discover_runs(self, sequence_slug: str | None) -> list[DiscoveredRun]:
        """Return discovered benchmark runs for one optional sequence slug."""
        ...

    @abstractmethod
    def resolve_selection(
        self,
        *,
        dataset: DatasetId,
        preferred_sequence_slug: str | None,
        preferred_run_root: Path | None,
    ) -> EvaluationSelection:
        """Resolve dataset and run choices for one evaluation consumer."""
        ...

    @abstractmethod
    def load_evaluation(self, *, selection: SelectionSnapshot) -> EvaluationArtifact | None:
        """Load a persisted trajectory evaluation when it exists."""
        ...

    @abstractmethod
    def compute_evaluation(self, *, selection: SelectionSnapshot) -> EvaluationArtifact:
        """Compute and persist one trajectory evaluation result."""
        ...


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
    "TrajectoryEvaluator",
]
