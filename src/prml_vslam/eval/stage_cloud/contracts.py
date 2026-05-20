"""Dense-cloud evaluation stage runtime input contracts."""

from __future__ import annotations

from prml_vslam.eval.contracts import DenseCloudEvaluationSelection
from prml_vslam.utils import BaseData


class CloudEvaluationStageInput(BaseData):
    """Inputs required to compare two metric world-frame dense point clouds."""

    selection: DenseCloudEvaluationSelection
    """Resolved reference and estimated cloud paths plus metric policy."""


__all__ = ["CloudEvaluationStageInput"]
