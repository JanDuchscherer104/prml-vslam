"""Image-evaluation stage runtime input contracts."""

from __future__ import annotations

from pathlib import Path

from prml_vslam.eval.render_eval import RenderEvalConfig
from prml_vslam.interfaces.slam import SlamArtifacts
from prml_vslam.utils import BaseData


class ImageEvaluationStageInput(BaseData):
    """Inputs required to render and score one run's dense cloud.

    The runtime resolves the cloud, trajectory, intrinsics, and input frames from
    ``artifact_root`` (written by the source and SLAM stages). ``slam`` is carried
    for availability and provenance only.
    """

    artifact_root: Path
    render_config: RenderEvalConfig
    slam: SlamArtifacts


__all__ = ["ImageEvaluationStageInput"]
