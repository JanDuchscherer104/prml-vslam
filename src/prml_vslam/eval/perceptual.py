"""LPIPS perceptual image-pair scorer, injected into the pure metric layer.

LPIPS (Learned Perceptual Image Patch Similarity, Zhang et al. 2018) is a learned
perceptual distance where *lower is more similar*. Unlike the pixel/structural metrics in
:mod:`prml_vslam.eval.image_metrics`, it needs a once-loaded neural backbone, so it lives
here behind a lazy ``torch``/``lpips`` import and is *injected* into
:func:`prml_vslam.eval.image_metrics.compute_image_metrics` as a callable. That keeps the
metric math free of torch and free of model state.

It scores the **full** image pair and ignores any coverage mask: LPIPS is a whole-image
perceptual judgement and cannot honor a per-pixel mask the way SSIM can. For sparse renders
with holes this means uncovered (black) regions contribute to the distance, so methods with
lower coverage tend to score worse here — read LPIPS as an overall-impression metric, not a
masked one like SSIM/L1.
"""

from __future__ import annotations

from typing import Literal, Protocol

import numpy as np

__all__ = ["LpipsNet", "LpipsScorer", "LpipsScorerProtocol"]

LpipsNet = Literal["alex", "vgg"]


class LpipsScorerProtocol(Protocol):
    """Callable returning the LPIPS distance for one normalized ``[0, 1]`` image pair."""

    def __call__(self, reference01: np.ndarray, generated01: np.ndarray) -> float: ...


class LpipsScorer:
    """Compute LPIPS for ``[0, 1]`` float image pairs with a once-loaded torch backbone.

    The backbone (``alex`` by default — fast; ``vgg`` is the slower paper variant) and its
    weights are downloaded once via torch-hub on first construction and then cached on the
    instance, so build a single scorer per evaluation run and reuse it across frames. The
    coverage mask is intentionally ignored (see the module docstring).
    """

    def __init__(self, net: LpipsNet = "alex", *, device: str | None = None) -> None:
        import lpips as lpips_lib
        import torch

        self._torch = torch
        self._device = (
            torch.device(device) if device is not None else torch.device("cuda" if torch.cuda.is_available() else "cpu")
        )
        self._model = lpips_lib.LPIPS(net=net, verbose=False).to(self._device).eval()

    def __call__(self, reference01: np.ndarray, generated01: np.ndarray) -> float:
        """Return the LPIPS distance for one ``[0, 1]`` normalized ``(reference, generated)`` pair."""
        torch = self._torch
        reference = self._to_nchw(reference01)
        generated = self._to_nchw(generated01)
        with torch.no_grad():
            distance = self._model(reference, generated)
        return float(distance.reshape(-1)[0].item())

    def _to_nchw(self, image01: np.ndarray):
        """Convert an ``(H, W)`` or ``(H, W, 3)`` ``[0, 1]`` array to a ``[-1, 1]`` NCHW tensor."""
        array = np.asarray(image01, dtype=np.float32)
        if array.ndim == 2:
            array = np.repeat(array[:, :, None], 3, axis=2)
        if array.ndim != 3 or array.shape[2] != 3:
            raise ValueError(f"LPIPS expects an (H, W) or (H, W, 3) image, got shape {array.shape}.")
        tensor = self._torch.from_numpy(array).permute(2, 0, 1).unsqueeze(0)
        tensor = tensor * 2.0 - 1.0  # [0, 1] -> [-1, 1] as LPIPS expects.
        return tensor.to(self._device)
