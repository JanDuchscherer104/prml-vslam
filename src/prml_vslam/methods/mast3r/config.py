"""Config class for the MASt3R-SLAM backend."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import ConfigDict

from prml_vslam.methods.contracts import SlamBackendConfig

if TYPE_CHECKING:
    from .adapter import Mast3rSlamBackend


class Mast3rSlamBackendConfig(SlamBackendConfig):
    """Factory config that builds the MASt3R-SLAM backend."""

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

    yaml_config_path: Path = Path("external/mast3r-slam/config/calib.yaml")
    """Path to the upstream YAML hyperparameter config."""

    c_conf_threshold: float = 1.5
    """Confidence threshold applied when exporting the dense point cloud."""

    @property
    def target_type(self) -> type[Mast3rSlamBackend]:
        """Return the backend type instantiated by :meth:`setup_target`."""
        from .adapter import Mast3rSlamBackend

        return Mast3rSlamBackend


__all__ = ["Mast3rSlamBackendConfig"]