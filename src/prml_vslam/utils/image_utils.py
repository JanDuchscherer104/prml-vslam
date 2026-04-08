"""Shared image normalization helpers."""

import cv2
import numpy as np


def normalize_grayscale_image(image: np.ndarray) -> np.ndarray:
    """Scale a grayscale image into an 8-bit displayable range."""
    finite = np.asarray(image, dtype=np.float32)
    if finite.size == 0:
        return np.zeros((1, 1), dtype=np.uint8)

    if not np.any(finite_mask := np.isfinite(finite)):
        return np.zeros_like(finite, dtype=np.uint8)

    mask = finite_mask.astype(np.uint8)
    minimum, maximum, _, _ = cv2.minMaxLoc(finite, mask=mask)
    if maximum <= minimum:
        return np.zeros_like(finite, dtype=np.uint8)

    normalized = np.zeros(finite.shape, dtype=np.uint8)
    cv2.normalize(
        src=finite,
        dst=normalized,
        alpha=0,
        beta=255,
        norm_type=cv2.NORM_MINMAX,
        dtype=cv2.CV_8U,
        mask=mask,
    )
    return normalized


__all__ = ["normalize_grayscale_image"]
