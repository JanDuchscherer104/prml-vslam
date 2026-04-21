"""Config classes for the canonical MASt3R-SLAM backend."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import ConfigDict

from prml_vslam.methods.contracts import SlamBackendConfig
from prml_vslam.utils import FactoryConfig


if TYPE_CHECKING:
    from .adapter import Mast3rSlamBackend


class Mast3rSlamBackendConfig(SlamBackendConfig, FactoryConfig["Mast3rSlamBackend"]):
    """Factory config that builds the MASt3R-SLAM backend.

    Hyperparameters for tracking / retrieval / local-opt / reloc are
    loaded from the upstream ``yaml_config_path``. If you need to deviate
    from upstream defaults, edit ``config/base.yaml`` in the submodule or
    point ``yaml_config_path`` at a repo-local override.
    """

    model_config = ConfigDict(extra="forbid")

    mast3r_slam_dir: Path = Path("external/mast3r-slam")
    """Path to the MASt3R-SLAM submodule root."""

    checkpoint_path: Path = Path(
        "external/mast3r-slam/checkpoints/MASt3R_ViTLarge_BaseDecoder_512_catmlpdpt_metric.pth"
    )
    """Path to the MASt3R backbone weights."""

    retrieval_checkpoint_path: Path = Path(
        "external/mast3r-slam/checkpoints/MASt3R_ViTLarge_BaseDecoder_512_catmlpdpt_metric_retrieval_trainingfree.pth"
    )
    """Path to the retrieval weights used for loop closure."""

    yaml_config_path: Path = Path("external/mast3r-slam/config/base.yaml")
    """Path to the upstream YAML hyperparameter config (use ``calib.yaml`` for use_calib=True presets)."""

    c_conf_threshold: float = 1.5
    """Confidence threshold applied when exporting the dense point cloud."""

    device: str = "cuda:0"
    """Torch device used for model inference and CUDA kernels."""

    img_size: int = 512
    """Image long-edge size for the MASt3R encoder (512 is upstream default; 224 also supported)."""

    use_calib: bool | None = None
    """Override the YAML 'use_calib' flag. None = respect YAML; True/False = force it."""

    backend_poll_interval_s: float = 0.01
    """Sleep between iterations of the backend optimisation thread when idle."""

    backend_join_timeout_s: float = 30.0
    """Max seconds to wait for the backend thread to exit on close()."""

    @property
    def target_type(self) -> type[Mast3rSlamBackend]:
        """Return the backend type instantiated by :meth:`setup_target`."""
        from .adapter import Mast3rSlamBackend

        return Mast3rSlamBackend


__all__ = ["Mast3rSlamBackendConfig"]
