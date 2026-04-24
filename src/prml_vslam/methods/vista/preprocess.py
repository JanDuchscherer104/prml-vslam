"""Frame preprocessing helpers for ViSTA-SLAM."""

from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

import numpy as np

if TYPE_CHECKING:
    import torch


# TODO: Can't we simply define "/typings" for Vista??
class _VistaImageDataset(Protocol):
    """Subset of the upstream image dataset API used by the wrapper."""

    resolution: tuple[int, int]

    @abstractmethod
    def _crop_resize_if_necessary_image_only(
        self,
        image: np.ndarray,
        resolution: tuple[int, int],
        *,
        h_edge: int = 0,
        w_edge: int = 0,
        rng: np.random.Generator | None = None,
        info: str | None = None,
    ) -> np.ndarray:
        """Apply the upstream crop-and-resize pipeline for image-only SLAM inputs."""

    @abstractmethod
    def ImgGray(self, image: np.ndarray) -> np.ndarray | torch.Tensor:
        """Return the grayscale tensor expected by upstream ViSTA."""

    @abstractmethod
    def ImgNorm(self, image: np.ndarray) -> torch.Tensor:
        """Return the normalized RGB tensor expected by upstream ViSTA."""


@dataclass(slots=True)
class PreparedVistaFrame:
    """One RGB frame prepared for upstream ViSTA ingestion."""

    image_rgb: np.ndarray
    gray_u8: np.ndarray
    rgb_tensor: torch.Tensor


class VistaFramePreprocessor(Protocol):
    """Prepare one repo RGB frame for upstream ViSTA ingestion."""

    @abstractmethod
    def prepare(self, rgb_image: np.ndarray, *, view_name: str) -> PreparedVistaFrame:
        """Return the upstream-ready frame payload."""


class UpstreamVistaFramePreprocessor:
    """Use the exact upstream ViSTA crop-and-resize helper path."""

    def __init__(self, *, image_dataset: _VistaImageDataset) -> None:
        self._image_dataset = image_dataset

    def prepare(self, rgb_image: np.ndarray, *, view_name: str) -> PreparedVistaFrame:
        processed_image = self._image_dataset._crop_resize_if_necessary_image_only(
            rgb_image,
            self._image_dataset.resolution,
            w_edge=10,
            h_edge=10,
            info=view_name,
        )
        gray_tensor = self._image_dataset.ImgGray(processed_image)
        rgb_tensor = self._image_dataset.ImgNorm(processed_image)
        gray_u8 = (vista_numpy_array(gray_tensor, dtype=np.float32).squeeze(0) * 255.0).astype(np.uint8)
        image_rgb = np.asarray(processed_image, dtype=np.uint8)
        return PreparedVistaFrame(image_rgb=image_rgb, gray_u8=gray_u8, rgb_tensor=rgb_tensor)


def vista_numpy_array(
    value: np.ndarray | torch.Tensor,
    *,
    dtype: np.dtype[np.generic] | type[np.generic],
) -> np.ndarray:
    """Convert one upstream ViSTA array-like payload into a numpy array."""
    if isinstance(value, np.ndarray):
        return np.asarray(value, dtype=dtype)
    return np.asarray(value.detach().cpu().numpy(), dtype=dtype)


__all__ = ["PreparedVistaFrame", "UpstreamVistaFramePreprocessor", "VistaFramePreprocessor", "vista_numpy_array"]
