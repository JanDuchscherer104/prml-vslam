"""Canonical method-owned backend configs and discriminated union.

This module gives request and pipeline code one discriminated backend-config
surface that still preserves method ownership. It sits between generic run
requests and the concrete wrapper configs implemented in the backend-owning
modules.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, Literal, TypeAlias

from pydantic import ConfigDict, Field

from prml_vslam.utils import FactoryConfig

from .config_contracts import MethodId, SlamBackendConfig

if TYPE_CHECKING:
    from .mast3r import Mast3rSlamBackend
    from .mock_vslam import MockSlamBackend
    from .vista.adapter import VistaSlamBackend


class MockSlamBackendConfig(SlamBackendConfig, FactoryConfig["MockSlamBackend"]):
    """Configure the repository-local mock backend used for smoke runs and demos."""

    method_id: Literal[MethodId.MOCK] = MethodId.MOCK
    """Selected mock backend label."""

    trajectory_position_noise_mean_m: float = 0.0
    """Mean of the i.i.d. position noise applied to replayed trajectory translations."""

    trajectory_position_noise_variance_m2: float = Field(default=0.0, ge=0.0)
    """Variance of the i.i.d. position noise applied to replayed trajectory translations."""

    point_noise_mean_m: float = 0.0
    """Mean of the i.i.d. point noise applied to replayed reference geometry."""

    point_noise_variance_m2: float = Field(default=0.0, ge=0.0)
    """Variance of the i.i.d. point noise applied to replayed reference geometry."""

    random_seed: int = 43
    """Deterministic seed used for replay noise generation."""

    @property
    def supports_offline(self) -> bool:
        """Whether the backend supports offline execution."""
        return True

    @property
    def supports_streaming(self) -> bool:
        """Whether the backend supports streaming execution."""
        return True

    @property
    def supports_dense_points(self) -> bool:
        """Whether the backend can expose point-cloud outputs."""
        return True

    @property
    def supports_live_preview(self) -> bool:
        """Whether the backend can emit live preview payloads."""
        return True

    @property
    def supports_native_visualization(self) -> bool:
        """Whether the backend may emit native visualization artifacts."""
        return False

    @property
    def supports_trajectory_benchmark(self) -> bool:
        """Whether the backend supports repository trajectory evaluation."""
        return True

    @property
    def default_resources(self) -> dict[str, float]:
        """Return backend-owned default Ray resource hints."""
        return {"CPU": 1.0}

    @property
    def target_type(self) -> type[MockSlamBackend]:
        """Return the mock backend type used for the pipeline demo."""
        from .mock_vslam import MockSlamBackend

        return MockSlamBackend

    def setup_target(self, **kwargs: Any) -> MockSlamBackend:
        """Instantiate the mock backend while ignoring unrelated runtime kwargs."""
        kwargs.pop("path_config", None)
        from .mock_vslam import MockSlamBackend

        return MockSlamBackend(self)


class Mast3rSlamBackendConfig(SlamBackendConfig, FactoryConfig["Mast3rSlamBackend"]):
    """Configure the placeholder MASt3R wrapper used for planning-only selection."""

    method_id: Literal[MethodId.MAST3R] = MethodId.MAST3R
    """Stable backend discriminator."""

    @property
    def supports_offline(self) -> bool:
        """Whether the backend supports offline execution."""
        return False

    @property
    def supports_streaming(self) -> bool:
        """Whether the backend supports streaming execution."""
        return False

    @property
    def supports_dense_points(self) -> bool:
        """Whether the backend can expose point-cloud outputs."""
        return False

    @property
    def supports_live_preview(self) -> bool:
        """Whether the backend can emit live preview payloads."""
        return False

    @property
    def supports_native_visualization(self) -> bool:
        """Whether the backend may emit native visualization artifacts."""
        return False

    @property
    def supports_trajectory_benchmark(self) -> bool:
        """Whether the backend supports repository trajectory evaluation."""
        return False

    @property
    def target_type(self) -> type[Mast3rSlamBackend]:
        """Return the placeholder backend type."""
        from .mast3r import Mast3rSlamBackend

        return Mast3rSlamBackend

    @property
    def notes(self) -> list[str]:
        """Return backend-specific planning notes."""
        return ["MASt3R remains a placeholder backend in this repository."]

    def setup_target(self, **kwargs: Any) -> Mast3rSlamBackend:
        """Instantiate the placeholder backend while ignoring runtime kwargs."""
        kwargs.pop("path_config", None)
        from .mast3r import Mast3rSlamBackend

        return Mast3rSlamBackend(self)


class VistaSlamBackendConfig(SlamBackendConfig, FactoryConfig["VistaSlamBackend"]):
    """Factory config that builds the canonical ViSTA backend."""

    model_config = ConfigDict(extra="forbid")

    method_id: Literal[MethodId.VISTA] = MethodId.VISTA
    """Stable backend discriminator."""

    vista_slam_dir: Path = Path("external/vista-slam")
    """Path to the ViSTA repository (submodule root)."""

    checkpoint_path: Path = Path("external/vista-slam/pretrains/frontend_sta_weights.pth")
    """Path to the STA frontend pretrained weights."""

    vocab_path: Path = Path("external/vista-slam/pretrains/ORBvoc.txt")
    """Path to the ORB vocabulary file used by loop detection."""

    max_view_num: int = 400
    """Maximum number of keyframes the pose graph may hold."""

    flow_thres: float = 5.0
    """Optical-flow magnitude threshold that triggers a new keyframe."""

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

    device: Literal["auto", "cuda", "cpu"] = "auto"
    """Torch device policy for the upstream ViSTA runtime."""

    @property
    def supports_offline(self) -> bool:
        """Whether the backend supports offline execution."""
        return True

    @property
    def supports_streaming(self) -> bool:
        """Whether the backend supports streaming execution."""
        return True

    @property
    def supports_dense_points(self) -> bool:
        """Whether the backend can expose point-cloud outputs."""
        return True

    @property
    def supports_live_preview(self) -> bool:
        """Whether the backend can emit live preview payloads."""
        return True

    @property
    def supports_native_visualization(self) -> bool:
        """Whether the backend may emit native visualization artifacts."""
        return True

    @property
    def supports_trajectory_benchmark(self) -> bool:
        """Whether the backend supports repository trajectory evaluation."""
        return True

    @property
    def default_resources(self) -> dict[str, float]:
        """Return backend-owned default Ray resource hints."""
        return {"CPU": 2.0, "GPU": 1.0}

    @property
    def notes(self) -> list[str]:
        """Return backend-specific planning notes."""
        return ["GPU acceleration is recommended for real ViSTA runs."]

    @property
    def target_type(self) -> type[VistaSlamBackend]:
        """Return the backend type instantiated by :meth:`setup_target`."""
        from .vista.adapter import VistaSlamBackend

        return VistaSlamBackend


BackendConfig: TypeAlias = Annotated[
    MockSlamBackendConfig | VistaSlamBackendConfig | Mast3rSlamBackendConfig,
    Field(discriminator="method_id"),
]

__all__ = [
    "BackendConfig",
    "Mast3rSlamBackendConfig",
    "MockSlamBackendConfig",
    "SlamBackendConfig",
    "VistaSlamBackendConfig",
]
