"""Dense-cloud evaluation stage runtime input contracts."""

from __future__ import annotations

from prml_vslam.eval.contracts import DenseCloudEvaluationSelection
from prml_vslam.utils import BaseData


class CloudEvaluationStageInput(BaseData):
    """Inputs required to compare aligned metric-world dense point clouds."""

    selection: DenseCloudEvaluationSelection


__all__ = ["CloudEvaluationStageInput"]
