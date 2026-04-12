"""Config classes for the canonical ViSTA backend."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import Field

from prml_vslam.utils import BaseConfig

if TYPE_CHECKING:
    from .adapter import VistaSlamBackend


class VistaSlamConfig(BaseConfig):
    """Algorithm-level hyperparameters forwarded to upstream OnlineSLAM."""

    device: str = "cuda"
    """Torch device string used for model inference."""

    max_view_num: int = 400
    """Maximum number of keyframes the pose graph may hold."""

    stride: int = 25
    """Keyframe stride fallback used by upstream keyframe selection."""

    flow_thres: float = 5.0
    """Optical-flow magnitude threshold that triggers a new keyframe."""

    keyframe_detection: str = "flow_stride"
    """Keyframe-selection strategy passed to the upstream frontend."""

    neighbor_edge_num: int = 3
    """Number of temporal-neighbor edges per keyframe in the pose graph."""

    loop_edge_num: int = 3
    """Maximum number of loop-closure edges added per keyframe."""

    loop_dist_min: int = 40
    """Minimum frame distance for a valid loop-closure candidate."""

    loop_nms: int = 40
    """Non-maximum suppression window for loop-closure candidates."""

    loop_cand_thresh_neighbor: int = 5
    """Loop candidate must share more neighbours than this threshold."""

    point_conf_thres: float = 4.2
    """Minimum point-confidence score retained in the reconstruction."""

    rel_pose_thres: float = 0.75
    """Maximum relative-pose uncertainty accepted for an edge."""

    pgo_every: int = 500
    """Pose-graph optimisation interval in keyframes."""

    random_seed: int = 43
    """Random seed set before model initialisation for reproducibility."""


class VistaSlamBackendConfig(BaseConfig):
    """Factory config that builds the canonical ViSTA backend."""

    vista_slam_dir: Path = Path("external/vista-slam")
    """Path to the ViSTA repository (submodule root)."""

    checkpoint_path: Path = Path("external/vista-slam/pretrains/frontend_sta_weights.pth")
    """Path to the STA frontend pretrained weights."""

    vocab_path: Path = Path("external/vista-slam/pretrains/ORBvoc.txt")
    """Path to the ORB vocabulary file used by loop detection."""

    slam: VistaSlamConfig = Field(default_factory=VistaSlamConfig)
    """Algorithm-level hyperparameters forwarded to upstream OnlineSLAM."""

    @property
    def target_type(self) -> type[VistaSlamBackend]:
        """Return the backend type instantiated by :meth:`setup_target`."""
        from .adapter import VistaSlamBackend

        return VistaSlamBackend


__all__ = ["VistaSlamBackendConfig", "VistaSlamConfig"]
