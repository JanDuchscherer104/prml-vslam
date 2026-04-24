"""Structural backend option contracts for method implementations.

Persisted SLAM backend configs are owned by
``prml_vslam.pipeline.stages.slam.config``. The method package keeps only the
minimal structural contracts its wrappers need at runtime so domain code does
not import stage modules.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol


class MockSlamBackendOptions(Protocol):
    """Runtime options consumed by the repository-local mock backend."""

    method_id: Any
    max_frames: int | None
    trajectory_position_noise_mean_m: float
    trajectory_position_noise_variance_m2: float
    point_noise_mean_m: float
    point_noise_variance_m2: float
    random_seed: int


class Mast3rSlamBackendOptions(Protocol):
    """Runtime options consumed by the placeholder MASt3R backend."""

    method_id: Any
    max_frames: int | None


class VistaSlamBackendOptions(Protocol):
    """Runtime options consumed by the ViSTA-SLAM backend."""

    method_id: Any
    max_frames: int | None
    vista_slam_dir: Path
    checkpoint_path: Path
    vocab_path: Path
    max_view_num: int
    flow_thres: float
    neighbor_edge_num: int
    loop_edge_num: int
    loop_dist_min: int
    loop_nms: int
    loop_cand_thresh_neighbor: int
    point_conf_thres: float
    rel_pose_thres: float
    pgo_every: int
    random_seed: int
    device: str


__all__ = [
    "Mast3rSlamBackendOptions",
    "MockSlamBackendOptions",
    "VistaSlamBackendOptions",
]
