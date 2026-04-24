"""Benchmark reference identifiers shared by datasets, methods, and eval.

The benchmark package owns reusable semantic identifiers for prepared
reference trajectories and clouds. Persisted pipeline stage policy lives under
``prml_vslam.pipeline.stages.*`` so run configuration stays stage-local.
"""

from __future__ import annotations

from enum import StrEnum


class ReferenceSource(StrEnum):
    """Typed source identifier for one available reference trajectory.

    Dataset ingest can expose several trajectories, but evaluation must choose
    one explicitly. ARCore and ARKit are optional external baselines, while
    ``GROUND_TRUTH`` is the preferred benchmark reference when available.
    """

    GROUND_TRUTH = "ground_truth"
    ARCORE = "arcore"
    ARKIT = "arkit"

    @property
    def label(self) -> str:
        """Return the human-readable source label."""
        return {
            ReferenceSource.GROUND_TRUTH: "ground truth",
            ReferenceSource.ARCORE: "ARCore",
            ReferenceSource.ARKIT: "ARKit",
        }[self]


class ReferenceCloudSource(StrEnum):
    """Typed source identifier for one available reference cloud."""

    TANGO_RAW = "tango_raw"
    TANGO_AREA_LEARNING = "tango_area_learning"


class ReferenceCloudCoordinateStatus(StrEnum):
    """Coordinate status for one prepared reference cloud."""

    SOURCE_NATIVE = "source_native"
    ALIGNED = "aligned"


__all__ = [
    "ReferenceCloudCoordinateStatus",
    "ReferenceCloudSource",
    "ReferenceSource",
]
