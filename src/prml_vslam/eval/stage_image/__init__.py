"""The ``evaluate.image`` pipeline stage.

This stage renders the SLAM dense cloud from the estimated trajectory and scores
the synthetic views against the input frames, producing
``evaluation/image_metrics.json``. It is a thin pipeline adapter over the shared
engine in :mod:`prml_vslam.eval.render_eval`; the renderer lives in
:mod:`prml_vslam.rendering` and the metrics in :mod:`prml_vslam.eval.image_metrics`.
"""

from .config import ImageEvaluationPolicy, ImageEvaluationStageConfig
from .spec import IMAGE_EVALUATION_STAGE_SPEC

__all__ = [
    "IMAGE_EVALUATION_STAGE_SPEC",
    "ImageEvaluationPolicy",
    "ImageEvaluationStageConfig",
]
