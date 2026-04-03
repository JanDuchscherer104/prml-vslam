"""Shared image helpers for Streamlit app pages."""

from __future__ import annotations

import numpy as np


def normalize_grayscale_image(image: np.ndarray) -> np.ndarray:
    """Scale a grayscale image into an 8-bit displayable range."""
    if image.size == 0:
        return np.zeros((1, 1), dtype=np.uint8)
    finite = np.asarray(image, dtype=np.float32)
    finite_mask = np.isfinite(finite)
    if not np.any(finite_mask):
        return np.zeros_like(finite, dtype=np.uint8)
    minimum = float(np.min(finite[finite_mask]))
    maximum = float(np.max(finite[finite_mask]))
    if maximum <= minimum:
        return np.zeros_like(finite, dtype=np.uint8)
    scaled = np.zeros_like(finite, dtype=np.float32)
    scaled[finite_mask] = (finite[finite_mask] - minimum) / (maximum - minimum)
    return np.clip(scaled * 255.0, 0.0, 255.0).astype(np.uint8)


__all__ = ["normalize_grayscale_image"]
