"""Pure image-pair quality metrics (L1, L2, PSNR, SSIM).

This module owns the reference-vs-generated image comparison math consumed by
:mod:`prml_vslam.eval.image_service`. It is deliberately free of file IO and
pipeline concerns: every function takes two raster-aligned image arrays and
returns scalar metrics, so it can score any ``(ground_truth, generated)`` pair
regardless of how the generated image was produced.

Conventions
-----------
- Inputs may be ``uint8`` in ``[0, 255]`` or floating point in ``[0, 1]``. Both
  are normalized to ``float64`` in ``[0, 1]`` via ``data_range`` (inferred from
  the dtype when not given) so results are comparable across sources.
- Images are 2D ``(H, W)`` grayscale or 3D ``(H, W, C)`` colour and must share
  the same shape.
- An optional boolean ``mask`` of shape ``(H, W)`` restricts scoring to covered
  pixels, which keeps sparse renders (e.g. point-cloud projections that leave
  holes) from being penalised on unfilled background.

The module does not resample or align: callers must pass images that already
correspond pixel-for-pixel.
"""

from __future__ import annotations

import numpy as np
from skimage.metrics import structural_similarity as _structural_similarity

from prml_vslam.eval.contracts import ImageQualityMetrics

__all__ = [
    "compute_image_metrics",
    "l1_error",
    "l2_error",
    "peak_signal_noise_ratio",
    "structural_similarity_index",
]


def compute_image_metrics(
    reference: np.ndarray,
    generated: np.ndarray,
    *,
    data_range: float | None = None,
    mask: np.ndarray | None = None,
) -> ImageQualityMetrics:
    """Compute the full image-quality metric set for one image pair.

    Normalizes both images once and evaluates L1 (MAE), L2 (RMSE), MSE, PSNR,
    and SSIM. Returns an :class:`ImageQualityMetrics` payload carrying the scored
    coverage fraction and the resolved ``data_range`` for reproducibility.
    """
    reference01, generated01, mask_bool, resolved_range = _prepare(
        reference, generated, data_range=data_range, mask=mask
    )
    mse = _mean_squared_error(reference01, generated01, mask_bool)
    coverage = 1.0 if mask_bool is None else float(np.count_nonzero(mask_bool) / mask_bool.size)
    return ImageQualityMetrics(
        l1=_mean_absolute_error(reference01, generated01, mask_bool),
        l2=float(np.sqrt(mse)),
        mse=mse,
        psnr=_psnr_from_mse(mse),
        ssim=_ssim(reference01, generated01, mask_bool),
        coverage=coverage,
        data_range=resolved_range,
    )


def l1_error(
    reference: np.ndarray,
    generated: np.ndarray,
    *,
    data_range: float | None = None,
    mask: np.ndarray | None = None,
) -> float:
    """Return the mean absolute error (MAE) on the normalized ``[0, 1]`` scale."""
    reference01, generated01, mask_bool, _ = _prepare(reference, generated, data_range=data_range, mask=mask)
    return _mean_absolute_error(reference01, generated01, mask_bool)


def l2_error(
    reference: np.ndarray,
    generated: np.ndarray,
    *,
    data_range: float | None = None,
    mask: np.ndarray | None = None,
) -> float:
    """Return the root mean squared error (RMSE) on the normalized ``[0, 1]`` scale."""
    reference01, generated01, mask_bool, _ = _prepare(reference, generated, data_range=data_range, mask=mask)
    return float(np.sqrt(_mean_squared_error(reference01, generated01, mask_bool)))


def peak_signal_noise_ratio(
    reference: np.ndarray,
    generated: np.ndarray,
    *,
    data_range: float | None = None,
    mask: np.ndarray | None = None,
) -> float:
    """Return PSNR in decibels; ``+inf`` when the images are identical."""
    reference01, generated01, mask_bool, _ = _prepare(reference, generated, data_range=data_range, mask=mask)
    return _psnr_from_mse(_mean_squared_error(reference01, generated01, mask_bool))


def structural_similarity_index(
    reference: np.ndarray,
    generated: np.ndarray,
    *,
    data_range: float | None = None,
    mask: np.ndarray | None = None,
) -> float:
    """Return the mean structural similarity index (SSIM) for the image pair."""
    reference01, generated01, mask_bool, _ = _prepare(reference, generated, data_range=data_range, mask=mask)
    return _ssim(reference01, generated01, mask_bool)


def _prepare(
    reference: np.ndarray,
    generated: np.ndarray,
    *,
    data_range: float | None,
    mask: np.ndarray | None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None, float]:
    """Validate inputs and return normalized images, a boolean mask, and the range."""
    reference = np.asarray(reference)
    generated = np.asarray(generated)
    if reference.shape != generated.shape:
        raise ValueError(
            f"Reference and generated images must share a shape, got {reference.shape} vs {generated.shape}."
        )
    if reference.ndim not in (2, 3):
        raise ValueError(f"Images must be 2D grayscale or 3D colour, got {reference.ndim}D.")
    resolved_range = _resolve_data_range(reference, generated, data_range)
    if resolved_range <= 0.0:
        raise ValueError(f"data_range must be positive, got {resolved_range}.")
    reference01 = reference.astype(np.float64) / resolved_range
    generated01 = generated.astype(np.float64) / resolved_range

    mask_bool: np.ndarray | None = None
    if mask is not None:
        mask_bool = np.asarray(mask, dtype=bool)
        spatial_shape = reference.shape[:2]
        if mask_bool.shape != spatial_shape:
            raise ValueError(f"Mask shape {mask_bool.shape} must match the image spatial shape {spatial_shape}.")
        if not mask_bool.any():
            raise ValueError("Mask selects zero pixels; nothing to score.")
    return reference01, generated01, mask_bool, resolved_range


def _resolve_data_range(reference: np.ndarray, generated: np.ndarray, data_range: float | None) -> float:
    """Infer the value range, failing fast on dtype combinations that cannot be inferred.

    A consistent ``uint8`` pair implies ``[0, 255]`` and a consistent floating pair
    implies ``[0, 1]``. Mixed integer/float inputs (e.g. ``float[0, 1]`` vs
    ``uint8[0, 255]``) or non-``uint8`` integers are ambiguous and would silently
    produce wrong metrics, so they require an explicit ``data_range`` instead.
    """
    if data_range is not None:
        return float(data_range)
    reference_is_integer = np.issubdtype(reference.dtype, np.integer)
    generated_is_integer = np.issubdtype(generated.dtype, np.integer)
    if reference_is_integer != generated_is_integer:
        raise ValueError(
            f"Cannot infer data_range for mixed integer/floating images ({reference.dtype} vs {generated.dtype}); "
            "pass an explicit data_range."
        )
    if reference_is_integer:
        if reference.dtype != np.uint8 or generated.dtype != np.uint8:
            raise ValueError(
                f"Cannot infer data_range for non-uint8 integer images ({reference.dtype}, {generated.dtype}); "
                "pass an explicit data_range."
            )
        return 255.0
    return 1.0


def _valid_differences(reference01: np.ndarray, generated01: np.ndarray, mask: np.ndarray | None) -> np.ndarray:
    difference = reference01 - generated01
    if mask is None:
        return difference.reshape(-1)
    return difference[mask].reshape(-1)


def _mean_absolute_error(reference01: np.ndarray, generated01: np.ndarray, mask: np.ndarray | None) -> float:
    return float(np.mean(np.abs(_valid_differences(reference01, generated01, mask))))


def _mean_squared_error(reference01: np.ndarray, generated01: np.ndarray, mask: np.ndarray | None) -> float:
    return float(np.mean(np.square(_valid_differences(reference01, generated01, mask))))


def _psnr_from_mse(mse: float) -> float:
    if mse <= 0.0:
        return float("inf")
    return float(10.0 * np.log10(1.0 / mse))


def _ssim(reference01: np.ndarray, generated01: np.ndarray, mask: np.ndarray | None) -> float:
    channel_axis = -1 if reference01.ndim == 3 else None
    score, ssim_map = _structural_similarity(
        reference01,
        generated01,
        data_range=1.0,
        channel_axis=channel_axis,
        full=True,
    )
    if mask is None:
        return float(score)
    if channel_axis is not None:
        ssim_map = ssim_map.mean(axis=-1)
    return float(ssim_map[mask].mean())
