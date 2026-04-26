from collections.abc import Callable, Sequence

import numpy as np
import torch

class SLAM_image_only:
    resolution: tuple[int, int]
    ImgGray: Callable[[np.ndarray], np.ndarray | torch.Tensor]
    ImgNorm: Callable[[np.ndarray], torch.Tensor]

    def __init__(
        self,
        image_paths: Sequence[str],
        resolution: tuple[int, int] = (224, 224),
    ) -> None: ...
    def _crop_resize_if_necessary_image_only(
        self,
        image: np.ndarray,
        resolution: tuple[int, int],
        *,
        h_edge: int = 0,
        w_edge: int = 0,
        rng: np.random.Generator | None = None,
        info: str | None = None,
    ) -> np.ndarray: ...
