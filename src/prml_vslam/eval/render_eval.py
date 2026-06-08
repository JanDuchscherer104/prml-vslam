"""Run-level image-quality evaluation by rendering a SLAM dense cloud.

This module is the shared compute engine behind the ``render-run`` CLI command,
the (planned) ``evaluate.image`` pipeline stage, and the Streamlit review page.
Given a run's dense point cloud, estimated trajectory, source intrinsics, and the
decoded input frames, it:

1. renders one synthetic view per estimated (keyframe) pose,
2. pairs each rendered view with the input frame nearest in time,
3. scores the pair with masked L1/L2/PSNR/SSIM (holes excluded via the
   coverage mask), and
4. persists ``evaluation/image_metrics.json`` plus an optional GT/rendered
   side-by-side gallery for visual inspection.

It deliberately compares the *raw* cloud at *source* intrinsics: that is the
fair, reproducible cross-method comparison (ViSTA vs. MASt3R) the project wants.
Source<->model raster reconciliation and cloud cleanup are explicit follow-ups,
not silent behavior here.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from pydantic import ConfigDict

from prml_vslam.eval.contracts import ImageQualitySummary
from prml_vslam.eval.image_metrics import compute_image_metrics
from prml_vslam.eval.image_service import ImageQualityEvaluationService, load_image_rgb
from prml_vslam.interfaces.camera import CameraIntrinsics, load_camera_intrinsics_yaml
from prml_vslam.rendering import PointCloudRenderer, RenderConfig, poses_from_tum_trajectory, write_image_rgb
from prml_vslam.utils import BaseData
from prml_vslam.utils.path_config import RunArtifactPaths

__all__ = [
    "RenderEvalConfig",
    "RenderEvalResult",
    "evaluate_rendered_run",
    "evaluate_run_from_artifact_root",
]


class RenderEvalConfig(BaseData):
    """Configure run-level render-and-score evaluation."""

    model_config = ConfigDict(frozen=True)

    depth_max_m: float = 1e6
    """Render depth clip. Defaults huge because monocular SLAM clouds are up-to-scale."""

    depth_scale: float = 1000.0
    """Open3D depth encoding factor passed through to the renderer."""

    dilation_px: int = 0
    """Optional morphological hole-fill radius for sparse clouds (0 = raw)."""

    save_gallery: bool = True
    """Write GT / rendered / side-by-side PNGs under ``evaluation/render_eval/``."""

    gallery_every: int = 10
    """Save every Nth scored pair to the gallery (1 = all)."""

    max_pair_dt_ms: float | None = None
    """Drop a pose when no input frame is within this timestamp tolerance (None = always pair nearest)."""


class RenderEvalResult(BaseData):
    """Outcome of one run-level render-and-score evaluation."""

    model_config = ConfigDict(frozen=True)

    summary: ImageQualitySummary
    """Aggregated image-quality metrics across all scored pairs."""

    metrics_path: Path
    """Path to the persisted ``image_metrics.json``."""

    gallery_dir: Path | None = None
    """Directory holding the GT/rendered/side-by-side gallery, when written."""

    scored_pairs: int = 0
    """Number of (input frame, rendered view) pairs actually scored."""


def evaluate_rendered_run(
    *,
    cloud_path: Path,
    trajectory_path: Path,
    intrinsics: CameraIntrinsics,
    frames_dir: Path,
    timestamps_ns: list[int] | np.ndarray,
    output_root: Path,
    config: RenderEvalConfig | None = None,
) -> RenderEvalResult:
    """Render the cloud along the trajectory and score it against the input frames.

    ``timestamps_ns`` is the per-input-frame timestamp series (index ``i`` maps to
    ``frames_dir/{i:06d}.png``); each estimated pose is paired with the input
    frame nearest in time.
    """
    config = config or RenderEvalConfig()
    poses = poses_from_tum_trajectory(trajectory_path)
    if not poses:
        raise ValueError(f"Trajectory '{trajectory_path}' contains no poses to render.")

    timestamps = np.asarray(timestamps_ns, dtype=np.int64)
    if timestamps.size == 0:
        raise ValueError("Input frame timestamps are empty; cannot pair rendered views.")

    renderer = PointCloudRenderer.from_ply(
        cloud_path,
        config=RenderConfig(
            depth_max_m=config.depth_max_m,
            depth_scale=config.depth_scale,
            dilation_px=config.dilation_px,
        ),
    )

    gallery_dir = (output_root / "evaluation" / "render_eval") if config.save_gallery else None
    frames = []
    for keyframe_index, (timestamp_s, pose) in enumerate(poses):
        target_ns = timestamp_s * 1e9
        frame_index = int(np.argmin(np.abs(timestamps - target_ns)))
        if config.max_pair_dt_ms is not None and abs(timestamps[frame_index] - target_ns) / 1e6 > config.max_pair_dt_ms:
            continue
        frame_path = frames_dir / f"{frame_index:06d}.png"
        if not frame_path.exists():
            # The paired input frame was not materialized to disk (e.g. a partially
            # materialized streaming run); skip rather than fail the whole evaluation.
            continue
        reference = load_image_rgb(frame_path)
        view = renderer.render(intrinsics=intrinsics, pose=pose)
        if reference.shape != view.rgb.shape:
            raise ValueError(
                f"Input frame shape {reference.shape} does not match the rendered shape {view.rgb.shape}. "
                "The render intrinsics raster must match the input-frame raster (check rotation/crop)."
            )
        if not view.coverage.any():
            # No point projected into this view (pose looks away / fully clipped); skip rather
            # than score an all-background frame (which masked metrics would reject anyway).
            continue
        frames.append(compute_image_metrics(reference, view.rgb, mask=view.coverage))
        if gallery_dir is not None and keyframe_index % config.gallery_every == 0:
            name = f"{keyframe_index:06d}_src{frame_index:06d}.png"
            write_image_rgb(gallery_dir / "gt" / name, reference)
            write_image_rgb(gallery_dir / "rendered" / name, view.rgb)
            write_image_rgb(gallery_dir / "side_by_side" / name, np.hstack([reference, view.rgb]))

    if not frames:
        raise ValueError("No (frame, render) pairs were scored; check the timestamp tolerance and inputs.")

    summary = ImageQualitySummary.from_frames(frames)
    metrics_path = ImageQualityEvaluationService().persist(summary, output_root)
    return RenderEvalResult(
        summary=summary,
        metrics_path=metrics_path,
        gallery_dir=gallery_dir,
        scored_pairs=len(frames),
    )


def evaluate_run_from_artifact_root(
    artifact_root: Path,
    *,
    config: RenderEvalConfig | None = None,
) -> RenderEvalResult:
    """Resolve all inputs from a finished run's artifact root and evaluate it.

    Uses the dense cloud (``slam/dense_points.ply`` or ``slam/point_cloud.ply``),
    ``slam/trajectory.tum``, source intrinsics from ``input/intrinsics.yaml``, and
    per-frame timestamps from ``input/timestamps.json``.
    """
    paths = RunArtifactPaths.build(Path(artifact_root))
    cloud_path = paths.dense_points_path if paths.dense_points_path.exists() else paths.point_cloud_path
    if not cloud_path.exists():
        raise FileNotFoundError(
            f"No dense cloud found at '{paths.dense_points_path}' or '{paths.point_cloud_path}'. "
            "Run SLAM with dense-point output enabled first."
        )
    if not paths.trajectory_path.exists():
        raise FileNotFoundError(f"No trajectory found at '{paths.trajectory_path}'.")

    intrinsics = load_camera_intrinsics_yaml(paths.input_intrinsics_path)
    timestamps_ns = json.loads(paths.input_timestamps_path.read_text(encoding="utf-8"))["timestamps_ns"]
    return evaluate_rendered_run(
        cloud_path=cloud_path,
        trajectory_path=paths.trajectory_path,
        intrinsics=intrinsics,
        frames_dir=paths.input_frames_dir,
        timestamps_ns=timestamps_ns,
        output_root=paths.artifact_root,
        config=config,
    )
