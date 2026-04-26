"""Evaluation entry surface for persisted benchmark artifacts.

The :mod:`prml_vslam.eval` package owns explicit metric computation and result
loading for normalized run outputs. It consumes artifacts planned by
:mod:`prml_vslam.pipeline`, stage-local trajectory-evaluation selections, and
source-prepared reference identifiers from :mod:`prml_vslam.sources.contracts`, but it does
not own persisted stage policy itself.
"""

from .services import TrajectoryEvaluationService

__all__ = ["TrajectoryEvaluationService"]
