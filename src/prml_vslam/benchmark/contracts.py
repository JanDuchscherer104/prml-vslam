"""Thin benchmark-policy contracts kept outside the pipeline core.

Benchmark config answers which comparison or reference-preparation stages are
requested and which baseline source they should use. It does not compute
metrics, execute SLAM methods, or own artifact formats; those responsibilities
remain in :mod:`prml_vslam.eval`, :mod:`prml_vslam.methods`, and
:mod:`prml_vslam.pipeline`.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from prml_vslam.utils import BaseConfig


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


# TODO(pipeline-refactor/WP-02): Replace with [stages.reconstruction] reference
# mode policy once ReconstructionStageConfig covers current reference behavior.
class ReferenceReconstructionConfig(BaseConfig):
    """Migration policy toggle for optional reference reconstruction.

    The target public pipeline stage is ``reconstruction`` with backend/mode
    variants. This config remains benchmark-owned compatibility policy until
    target reconstruction stage config covers the same reference-mode behavior.
    """

    enabled: bool = False
    """Whether the run should include the corresponding stage."""

    extract_mesh: bool = False
    """Whether the reference reconstruction stage should also persist a triangle mesh."""


class TrajectoryBenchmarkConfig(BaseConfig):
    """Policy for trajectory evaluation stage enablement and baseline choice.

    Metric computation, alignment mode, and persisted result schema belong to
    :mod:`prml_vslam.eval`. This config only requests the stage and names the
    reference trajectory source prepared by ingest.
    """

    enabled: bool = False
    """Whether the run should include trajectory evaluation."""

    baseline_source: ReferenceSource = ReferenceSource.GROUND_TRUTH
    """Explicit reference source used by the trajectory evaluation stage when available."""


class CloudBenchmarkConfig(BaseConfig):
    """Policy for dense-cloud comparison."""

    enabled: bool = False
    """Whether the run should include dense-cloud comparison."""


class EfficiencyBenchmarkConfig(BaseConfig):
    """Policy for efficiency evaluation."""

    enabled: bool = False
    """Whether the run should include efficiency metrics."""


class BenchmarkConfig(BaseConfig):
    """Bundle benchmark-stage policy without becoming a runtime owner.

    Pipeline planning reads this bundle to mark evaluation/reconstruction stages
    requested or unavailable. Runtime execution and result DTOs stay in their
    owning packages so benchmark policy remains a small composition layer.
    """

    reference: ReferenceReconstructionConfig = Field(default_factory=ReferenceReconstructionConfig)
    """Reference-reconstruction policy."""

    trajectory: TrajectoryBenchmarkConfig = Field(default_factory=TrajectoryBenchmarkConfig)
    """Trajectory-evaluation policy."""

    cloud: CloudBenchmarkConfig = Field(default_factory=CloudBenchmarkConfig)
    """Dense-cloud evaluation policy."""

    efficiency: EfficiencyBenchmarkConfig = Field(default_factory=EfficiencyBenchmarkConfig)
    """Efficiency-evaluation policy."""


__all__ = [
    "BenchmarkConfig",
    "CloudBenchmarkConfig",
    "EfficiencyBenchmarkConfig",
    "ReferenceCloudCoordinateStatus",
    "ReferenceCloudSource",
    "ReferenceSource",
    "ReferenceReconstructionConfig",
    "TrajectoryBenchmarkConfig",
]
