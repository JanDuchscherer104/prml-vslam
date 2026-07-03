"""Runtime input contracts for dense-cloud evaluation."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field

from prml_vslam.eval.contracts import CloudEstimateKind
from prml_vslam.interfaces.artifacts import ArtifactRef
from prml_vslam.utils import BaseData


class CloudEvaluationEstimateInput(BaseData):
    """One dense-cloud estimate selected for evaluation."""

    estimate_kind: CloudEstimateKind
    """Semantic role of the estimate cloud."""

    cloud: ArtifactRef
    """PLY artifact containing estimate points in the reference target frame."""


class CloudEvaluationStageInput(BaseData):
    """Bounded runtime input for Open3D dense-cloud evaluation."""

    artifact_root: Path
    """Run artifact root that owns the resulting metrics JSON."""

    reference_cloud: ArtifactRef
    """Reference PLY cloud in the benchmark target frame."""

    estimates: list[CloudEvaluationEstimateInput]
    """Estimate PLY clouds to compare against the reference."""

    f1_threshold_m: float = Field(default=0.05, gt=0.0)
    """Distance threshold used for precision, recall, and F1, in meters."""

    cloud_alignment: ArtifactRef | None = None
    """Optional cloud-alignment metadata used for ICP diagnostics."""


__all__ = ["CloudEvaluationEstimateInput", "CloudEvaluationStageInput"]
