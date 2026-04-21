"""Protocol seams for repository-local evaluation stages.

These protocols describe the service boundaries that review surfaces and
pipeline stages use when they compute or load persisted evaluation artifacts.
They sit above normalized pipeline outputs and below app or CLI rendering code.
"""

from __future__ import annotations

from abc import abstractmethod
from pathlib import Path
from typing import Protocol, runtime_checkable

from prml_vslam.datasets.contracts import DatasetId
from prml_vslam.eval.contracts import (
    DenseCloudEvaluationArtifact,
    DenseCloudEvaluationSelection,
    DiscoveredRun,
    EfficiencyEvaluationArtifact,
    EfficiencyEvaluationSelection,
    EvaluationArtifact,
    EvaluationSelection,
    SelectionSnapshot,
)


@runtime_checkable
class TrajectoryEvaluator(Protocol):
    """Load or compute trajectory evaluation over normalized run artifacts."""

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
    """Load or compute dense-cloud evaluation over normalized run artifacts."""

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


@runtime_checkable
class EfficiencyEvaluator(Protocol):
    """Load or compute runtime-efficiency evaluation over normalized run artifacts."""

    @abstractmethod
    def load_efficiency_evaluation(
        self,
        *,
        selection: EfficiencyEvaluationSelection,
    ) -> EfficiencyEvaluationArtifact | None:
        """Load a persisted runtime-efficiency evaluation when it exists."""
        ...

    @abstractmethod
    def compute_efficiency_evaluation(
        self,
        *,
        selection: EfficiencyEvaluationSelection,
    ) -> EfficiencyEvaluationArtifact:
        """Compute and persist one runtime-efficiency evaluation result."""
        ...


__all__ = [
    "DenseCloudEvaluator",
    "EfficiencyEvaluator",
    "TrajectoryEvaluator",
]
