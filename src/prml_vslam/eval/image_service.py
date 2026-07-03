"""Image-quality evaluation service: batch image-pair metrics and persistence.

This is the eval-owned retrieval seam for image-quality metrics, mirroring
:class:`prml_vslam.eval.services.TrajectoryEvaluationService`. It loads images
from disk, computes per-pair metrics via the pure
:mod:`prml_vslam.eval.image_metrics` module, aggregates them, and persists or
reloads the result under the canonical ``<run_root>/evaluation/`` layout.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TYPE_CHECKING

import cv2
import numpy as np

from prml_vslam.eval.contracts import ImageQualityMetrics, ImageQualitySummary
from prml_vslam.eval.image_metrics import compute_image_metrics
from prml_vslam.utils.path_config import PathConfig
from prml_vslam.utils.serialization import write_json

if TYPE_CHECKING:
    from prml_vslam.eval.render_eval import RenderEvalConfig, RenderEvalResult

__all__ = ["ImageQualityEvaluationService", "load_image_rgb", "pair_images_by_name"]

_IMAGE_SUFFIXES: tuple[str, ...] = (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff")


def load_image_rgb(path: Path) -> np.ndarray:
    """Load one image as an ``(H, W, 3)`` uint8 RGB array."""
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(f"Could not read image: '{path}'.")
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def _load_mask(path: Path) -> np.ndarray:
    mask = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if mask is None:
        raise FileNotFoundError(f"Could not read mask image: '{path}'.")
    return mask > 0


def pair_images_by_name(
    reference_dir: Path,
    generated_dir: Path,
    *,
    suffixes: tuple[str, ...] = _IMAGE_SUFFIXES,
) -> list[tuple[str, Path, Path]]:
    """Pair images present in both directories by filename stem, sorted by stem."""

    def index(directory: Path) -> dict[str, Path]:
        return {
            entry.stem: entry
            for entry in sorted(directory.iterdir())
            if entry.is_file() and entry.suffix.lower() in suffixes
        }

    reference_index = index(reference_dir)
    generated_index = index(generated_dir)
    shared_stems = sorted(set(reference_index) & set(generated_index))
    return [(stem, reference_index[stem], generated_index[stem]) for stem in shared_stems]


class ImageQualityEvaluationService:
    """Compute, persist, and reload image-quality metrics for run artifacts.

    Evaluation stays explicit: nothing is computed as a side effect of loading.
    Results are written to ``<run_root>/evaluation/image_metrics.json`` to match
    the trajectory and cloud metric layout, so any later pipeline stage or UI can
    adopt the same artifact without rework.
    """

    def __init__(self, path_config: PathConfig | None = None) -> None:
        self.path_config = path_config

    @staticmethod
    def result_path(run_root: Path) -> Path:
        """Return the deterministic persisted image-metrics path for a run root."""
        return run_root / "evaluation" / "image_metrics.json"

    def compute_pair(
        self,
        *,
        reference_path: Path,
        generated_path: Path,
        data_range: float | None = None,
        mask_path: Path | None = None,
        lpips_scorer: Callable[[np.ndarray, np.ndarray], float] | None = None,
    ) -> ImageQualityMetrics:
        """Compute image-quality metrics for one reference/generated image pair."""
        mask = _load_mask(mask_path) if mask_path is not None else None
        return compute_image_metrics(
            load_image_rgb(reference_path),
            load_image_rgb(generated_path),
            data_range=data_range,
            mask=mask,
            lpips_scorer=lpips_scorer,
        )

    def compute_set(
        self,
        pairs: Sequence[tuple[Path, Path]],
        *,
        data_range: float | None = None,
        lpips_scorer: Callable[[np.ndarray, np.ndarray], float] | None = None,
    ) -> ImageQualitySummary:
        """Compute and aggregate metrics for a sequence of ``(reference, generated)`` paths.

        Passing ``lpips_scorer`` also records the learned perceptual LPIPS distance per pair.
        """
        if not pairs:
            raise FileNotFoundError("No image pairs were provided for evaluation.")
        frames = [
            compute_image_metrics(
                load_image_rgb(reference_path),
                load_image_rgb(generated_path),
                data_range=data_range,
                lpips_scorer=lpips_scorer,
            )
            for reference_path, generated_path in pairs
        ]
        return ImageQualitySummary.from_frames(frames)

    def evaluate_directories(
        self,
        *,
        reference_dir: Path,
        generated_dir: Path,
        data_range: float | None = None,
        lpips_scorer: Callable[[np.ndarray, np.ndarray], float] | None = None,
    ) -> ImageQualitySummary:
        """Pair images by filename across two directories and aggregate their metrics."""
        pairs = [
            (reference_path, generated_path)
            for _, reference_path, generated_path in pair_images_by_name(reference_dir, generated_dir)
        ]
        if not pairs:
            raise FileNotFoundError(f"No image pairs share a filename between '{reference_dir}' and '{generated_dir}'.")
        return self.compute_set(pairs, data_range=data_range, lpips_scorer=lpips_scorer)

    def evaluate_run(
        self,
        artifact_root: Path,
        *,
        config: RenderEvalConfig | None = None,
    ) -> RenderEvalResult:
        """Render a finished run's dense cloud, score it, and persist the metrics.

        This is the eval-owned seam for run-level render-and-score evaluation: the
        CLI, the ``evaluate.image`` pipeline stage, and the Streamlit review page
        all route through it so the artifact contract and persistence stay owned by
        the service rather than being driven ad hoc from a UI or command surface.
        """
        from prml_vslam.eval.render_eval import evaluate_run_from_artifact_root

        return evaluate_run_from_artifact_root(Path(artifact_root), config=config)

    def persist(self, summary: ImageQualitySummary, run_root: Path) -> Path:
        """Persist one image-quality summary under the run's ``evaluation/`` directory."""
        result_path = self.result_path(run_root)
        write_json(result_path, summary.model_dump(mode="json"))
        return result_path

    def load(self, run_root: Path) -> ImageQualitySummary | None:
        """Reload a persisted image-quality summary, or ``None`` when absent."""
        result_path = self.result_path(run_root)
        if not result_path.exists():
            return None
        return ImageQualitySummary.model_validate(json.loads(result_path.read_text(encoding="utf-8")))
