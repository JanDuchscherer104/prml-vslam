"""Persisted config for the ``evaluate.image`` stage."""

from __future__ import annotations

from pathlib import Path

from pydantic import ConfigDict, Field

from prml_vslam.eval.perceptual import LpipsNet
from prml_vslam.pipeline.contracts.context import PipelinePlanContext
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.config import StageConfig
from prml_vslam.utils import BaseConfig


class ImageEvaluationPolicy(BaseConfig):
    """Stage-owned image-evaluation rendering policy.

    Mirrors :class:`prml_vslam.eval.render_eval.RenderEvalConfig`; the runtime
    spec translates this persisted policy into the engine config so this module
    stays free of the rendering/Open3D import.
    """

    model_config = ConfigDict(extra="ignore")

    depth_max_m: float = Field(default=1e6, gt=0.0)
    """Render depth clip in cloud units (huge by default; monocular SLAM is up-to-scale)."""

    dilation_px: int = Field(default=0, ge=0)
    """Optional morphological hole-fill radius for sparse clouds (0 = raw)."""

    save_gallery: bool = True
    """Write a GT/rendered/side-by-side gallery under ``evaluation/render_eval/``."""

    gallery_every: int = Field(default=10, ge=1)
    """Save every Nth scored pair to the gallery (1 = all)."""

    compute_lpips: bool = False
    """Also score the learned perceptual LPIPS distance (loads a torch backbone; off by default)."""

    lpips_net: LpipsNet = "alex"
    """LPIPS backbone when ``compute_lpips`` is set (``alex`` = fast, ``vgg`` = slower paper variant)."""


class ImageEvaluationStageConfig(StageConfig):
    """Stage-owned image-quality evaluation policy."""

    model_config = ConfigDict(extra="ignore")

    stage_key: StageKey | None = StageKey.IMAGE_EVALUATION
    rendering: ImageEvaluationPolicy = Field(default_factory=ImageEvaluationPolicy)
    """Render-and-score policy consumed by the runtime."""

    def planned_outputs(self, context: PipelinePlanContext) -> list[Path]:
        return [context.run_paths.image_metrics_path]

    def availability(self, context: PipelinePlanContext) -> tuple[bool, str | None]:
        slam = context.run_config.stages.slam
        if not slam.enabled:
            return False, "Image evaluation requires the SLAM stage to be enabled."
        if not slam.outputs.emit_dense_points:
            return (
                False,
                "Image evaluation requires SLAM dense points (`[stages.slam.outputs] emit_dense_points = true`).",
            )
        return True, None


__all__ = ["ImageEvaluationPolicy", "ImageEvaluationStageConfig"]
