"""Protocol seams for repository-local evaluation stages."""

from __future__ import annotations

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
    """Protocol for trajectory-evaluation services over normalized run artifacts."""

    def discover_runs(self, sequence_slug: str | None) -> list[DiscoveredRun]:
        """Return discovered benchmark runs for one optional sequence slug."""
        ...

    def resolve_selection(
        self,
        *,
        dataset: DatasetId,
        preferred_sequence_slug: str | None,
        preferred_run_root: Path | None,
    ) -> EvaluationSelection:
        """Resolve dataset and run choices for one evaluation consumer."""
        ...

    def load_evaluation(self, *, selection: SelectionSnapshot) -> EvaluationArtifact | None:
        """Load a persisted trajectory evaluation when it exists."""
        ...

    def compute_evaluation(self, *, selection: SelectionSnapshot) -> EvaluationArtifact:
        """Compute and persist one trajectory evaluation result."""
        ...


@runtime_checkable
class DenseCloudEvaluator(Protocol):
    """Protocol for dense-cloud evaluation services."""

    def load_dense_evaluation(
        self,
        *,
        selection: DenseCloudEvaluationSelection,
    ) -> DenseCloudEvaluationArtifact | None:
        """Load a persisted dense-cloud evaluation when it exists."""
        ...

    def compute_dense_evaluation(
        self,
        *,
        selection: DenseCloudEvaluationSelection,
    ) -> DenseCloudEvaluationArtifact:
        """Compute and persist one dense-cloud evaluation result."""
        ...


@runtime_checkable
class EfficiencyEvaluator(Protocol):
    """Protocol for runtime-efficiency evaluation services."""

    def load_efficiency_evaluation(
        self,
        *,
        selection: EfficiencyEvaluationSelection,
    ) -> EfficiencyEvaluationArtifact | None:
        """Load a persisted runtime-efficiency evaluation when it exists."""
        ...

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
