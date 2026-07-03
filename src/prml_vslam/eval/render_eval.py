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
from collections.abc import Sequence
from pathlib import Path

import numpy as np
from pydantic import ConfigDict, Field

from prml_vslam.eval.contracts import ImageQualitySummary
from prml_vslam.eval.image_metrics import compute_image_metrics
from prml_vslam.eval.image_service import ImageQualityEvaluationService, load_image_rgb
from prml_vslam.eval.perceptual import LpipsNet, LpipsScorerProtocol
from prml_vslam.interfaces.camera import CameraIntrinsics, load_camera_intrinsics_yaml
from prml_vslam.rendering import PointCloudRenderer, RenderConfig, poses_from_tum_trajectory, write_image_rgb
from prml_vslam.sources.contracts import SequenceManifest
from prml_vslam.utils import BaseData
from prml_vslam.utils.path_config import RunArtifactPaths

_FRAME_SUFFIXES: tuple[str, ...] = (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff")

__all__ = [
    "RenderEvalConfig",
    "RenderEvalResult",
    "evaluate_rendered_run",
    "evaluate_run_from_artifact_root",
]


class RenderEvalConfig(BaseData):
    """Configure run-level render-and-score evaluation."""

    model_config = ConfigDict(frozen=True)

    depth_max_m: float = Field(default=1e6, gt=0.0)
    """Render depth clip. Defaults huge because monocular SLAM clouds are up-to-scale."""

    depth_scale: float = Field(default=1000.0, gt=0.0)
    """Open3D depth encoding factor passed through to the renderer (divides depth, so must be positive)."""

    dilation_px: int = Field(default=0, ge=0)
    """Optional morphological hole-fill radius for sparse clouds (0 = raw)."""

    save_gallery: bool = True
    """Write GT / rendered / side-by-side PNGs under ``evaluation/render_eval/``."""

    gallery_every: int = Field(default=10, ge=1)
    """Save every Nth scored pair to the gallery (1 = all); used as a modulo divisor, so must be >= 1."""

    max_pair_dt_ms: float | None = Field(default=None, gt=0.0)
    """Drop a pose when no input frame is within this timestamp tolerance (None = always pair nearest)."""

    compute_lpips: bool = False
    """Also score the learned perceptual LPIPS distance (loads a torch backbone; off by default)."""

    lpips_net: LpipsNet = "alex"
    """LPIPS backbone when ``compute_lpips`` is set (``alex`` = fast, ``vgg`` = slower paper variant)."""


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
    frame_paths: Sequence[Path],
    timestamps_ns: list[int] | np.ndarray,
    output_root: Path,
    config: RenderEvalConfig | None = None,
) -> RenderEvalResult:
    """Render the cloud along the trajectory and score it against the input frames.

    ``frame_paths`` is the per-input-frame path series, index-aligned with
    ``timestamps_ns`` (entry ``i`` is the frame captured at ``timestamps_ns[i]``);
    each estimated pose is paired with the input frame nearest in time. A frame
    path that does not exist (e.g. a partially materialized streaming run) is
    skipped rather than failing the whole evaluation.
    """
    config = config or RenderEvalConfig()
    lpips_scorer = _build_lpips_scorer(config)
    poses = poses_from_tum_trajectory(trajectory_path)
    if not poses:
        raise ValueError(f"Trajectory '{trajectory_path}' contains no poses to render.")

    timestamps = np.asarray(timestamps_ns, dtype=np.int64)
    if timestamps.size == 0:
        raise ValueError("Input frame timestamps are empty; cannot pair rendered views.")
    if len(frame_paths) != timestamps.size:
        raise ValueError(
            f"Input frame count ({len(frame_paths)}) does not match the timestamp count "
            f"({timestamps.size}); frames and timestamps must be index-aligned."
        )

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
        target_ns = int(round(timestamp_s * 1e9))
        frame_index = int(np.argmin(np.abs(timestamps - target_ns)))
        if (
            config.max_pair_dt_ms is not None
            and abs(int(timestamps[frame_index]) - target_ns) / 1e6 > config.max_pair_dt_ms
        ):
            continue
        frame_path = frame_paths[frame_index]
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
        frames.append(compute_image_metrics(reference, view.rgb, mask=view.coverage, lpips_scorer=lpips_scorer))
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

    Input resolution is manifest-first: when ``input/sequence_manifest.json`` is
    present its source-owned ``rgb_dir`` / ``timestamps_path`` / ``intrinsics_path``
    win, so runs whose RGB frames, timestamps, or intrinsics live outside the
    canonical ``input/*`` layout still score correctly. The canonical
    ``input/frames``, ``input/timestamps.json``, and ``input/intrinsics.yaml``
    paths remain the fallback for older artifacts. The cloud is the dense cloud
    (``slam/dense_points.ply`` or ``slam/point_cloud.ply``) along
    ``slam/trajectory.tum``.
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

    intrinsics_path, timestamps_ns, frame_paths = _resolve_run_inputs(paths)
    return evaluate_rendered_run(
        cloud_path=cloud_path,
        trajectory_path=paths.trajectory_path,
        intrinsics=load_camera_intrinsics_yaml(intrinsics_path),
        frame_paths=frame_paths,
        timestamps_ns=timestamps_ns,
        output_root=paths.artifact_root,
        config=config,
    )


def _build_lpips_scorer(config: RenderEvalConfig) -> LpipsScorerProtocol | None:
    """Build the LPIPS scorer once per run when enabled, else ``None``.

    Kept as a tiny seam so the torch-backed backbone is constructed lazily (only when
    ``compute_lpips`` is set) and so tests can substitute a lightweight dummy scorer.
    """
    if not config.compute_lpips:
        return None
    from prml_vslam.eval.perceptual import LpipsScorer

    return LpipsScorer(net=config.lpips_net)


def _resolve_run_inputs(paths: RunArtifactPaths) -> tuple[Path, list[int], list[Path]]:
    """Resolve (intrinsics path, per-frame timestamps, frame paths) manifest-first.

    Prefers the source-owned paths declared in ``input/sequence_manifest.json``
    when they exist, falling back to the canonical ``input/*`` layout otherwise.
    Resolved files are validated so a misconfigured run fails loudly instead of
    silently scoring the wrong inputs.
    """
    manifest = _load_sequence_manifest(paths.sequence_manifest_path)
    intrinsics_path = _prefer_existing(
        manifest.intrinsics_path if manifest is not None else None,
        paths.input_intrinsics_path,
        what="camera intrinsics",
    )
    timestamps_path = _prefer_existing(
        manifest.timestamps_path if manifest is not None else None,
        paths.input_timestamps_path,
        what="frame timestamps",
    )
    timestamps_ns = _load_timestamps_ns(timestamps_path)
    frame_paths = _resolve_frame_paths(manifest, paths, frame_count=len(timestamps_ns))
    return intrinsics_path, timestamps_ns, frame_paths


def _load_sequence_manifest(path: Path) -> SequenceManifest | None:
    """Load the persisted sequence manifest, tolerating absence only."""
    if not path.exists():
        return None
    try:
        return SequenceManifest.model_validate_json(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise RuntimeError(f"Could not read sequence manifest '{path}'.") from exc
    except ValueError as exc:
        raise ValueError(f"Invalid sequence manifest '{path}'.") from exc


def _prefer_existing(candidate: Path | None, canonical: Path, *, what: str) -> Path:
    """Return the manifest-declared ``candidate`` when it exists, else the canonical path."""
    if candidate is not None and Path(candidate).exists():
        return Path(candidate)
    if not canonical.exists():
        raise FileNotFoundError(
            f"No {what} found for this run (looked at the sequence manifest and canonical '{canonical}')."
        )
    return canonical


def _resolve_frame_paths(manifest: SequenceManifest | None, paths: RunArtifactPaths, *, frame_count: int) -> list[Path]:
    """Resolve the index-aligned input-frame paths, preferring a manifest ``rgb_dir``.

    A source-owned ``rgb_dir`` (one that resolves outside the canonical
    ``input/frames``) is read by sorted filename and must contain exactly
    ``frame_count`` frames so it stays index-aligned with the timestamps. The
    canonical fallback derives ``{index:06d}.png`` names directly, which keeps the
    existing tolerance for partially materialized runs (missing frames are skipped).
    """
    manifest_rgb = manifest.rgb_dir if manifest is not None else None
    if (
        manifest_rgb is not None
        and manifest_rgb.is_dir()
        and manifest_rgb.resolve() != paths.input_frames_dir.resolve()
    ):
        frame_paths = sorted(
            entry for entry in manifest_rgb.iterdir() if entry.is_file() and entry.suffix.lower() in _FRAME_SUFFIXES
        )
        if not frame_paths:
            raise FileNotFoundError(f"Sequence manifest rgb_dir '{manifest_rgb}' contains no input frames.")
        if len(frame_paths) != frame_count:
            raise ValueError(
                f"Sequence manifest rgb_dir '{manifest_rgb}' holds {len(frame_paths)} frames but the run has "
                f"{frame_count} timestamps; frames and timestamps must be index-aligned."
            )
        return frame_paths
    return [paths.input_frames_dir / f"{index:06d}.png" for index in range(frame_count)]


def _load_timestamps_ns(path: Path) -> list[int]:
    """Load per-frame nanosecond timestamps from normalized JSON or a numeric stamp file."""
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or not isinstance(payload.get("timestamps_ns"), list):
            raise ValueError(f"Timestamps JSON '{path}' must contain a 'timestamps_ns' list.")
        return [int(value) for value in payload["timestamps_ns"]]
    values: list[int] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        first_field = stripped.split(",", maxsplit=1)[0].split()[0]
        values.append(int(round(float(first_field) * 1e9)))
    if not values:
        raise ValueError(f"No per-frame timestamps could be parsed from '{path}'.")
    return values
