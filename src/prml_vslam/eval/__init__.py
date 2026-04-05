"""Mock trajectory-evaluation surfaces used by the app and tests."""

from .interfaces import (
    DiscoveredRun,
    ErrorSeries,
    EvaluationArtifact,
    EvaluationControls,
    EvaluationSelection,
    MetricStats,
    SelectionSnapshot,
    TrajectorySeries,
)
from .services import TrajectoryEvaluationService

__all__ = [
    "DiscoveredRun",
    "ErrorSeries",
    "EvaluationArtifact",
    "EvaluationControls",
    "EvaluationSelection",
    "MetricStats",
    "SelectionSnapshot",
    "TrajectoryEvaluationService",
    "TrajectorySeries",
]
