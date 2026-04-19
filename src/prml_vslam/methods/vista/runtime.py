"""Upstream ViSTA runtime/bootstrap helpers."""

from __future__ import annotations

import importlib
import sys
from dataclasses import dataclass
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Any, Protocol

from prml_vslam.utils import Console, PathConfig

from .config import VistaSlamBackendConfig
from .preprocess import UpstreamVistaFramePreprocessor, VistaFramePreprocessor

if TYPE_CHECKING:
    import torch

_VISTA_INPUT_RESOLUTION = (224, 224)


class VistaFlowTracker(Protocol):
    """Subset of the upstream flow tracker API used by the session wrapper."""

    def compute_disparity(self, image: Any, visualize: bool = False) -> bool:
        """Return whether the current frame should become a new keyframe."""


class VistaOnlineSlam(Protocol):
    """Subset of the upstream OnlineSLAM API used by the session wrapper."""

    device: torch.device | str

    def step(self, value: dict[str, Any]) -> None:
        """Consume one prepared keyframe."""

    def save_data_all(self, output_dir: str, *, save_images: bool, save_depths: bool) -> None:
        """Persist native ViSTA outputs for later normalization."""

    def get_view(self, view_index: int, **kwargs: Any) -> Any:
        """Return one live view payload from the upstream pose graph."""

    def get_pointmap_vis(self, view_index: int) -> tuple[Any | None, Any | None]:
        """Return preview RGB and dense pointmap payloads for one live view."""


class _DbowVocabulary(Protocol):
    """Subset of the DBoW vocabulary API used for binary cache generation."""

    def load(self, path: str) -> None:
        """Load the text vocabulary from disk."""

    def save(self, path: str, binary: bool) -> None:
        """Write the vocabulary back to disk in the requested format."""


class _DbowModule(Protocol):
    """Subset of the imported DBoW module used by this wrapper."""

    def Vocabulary(self) -> _DbowVocabulary:
        """Construct one vocabulary instance."""


@dataclass(slots=True)
class VistaRuntimeComponents:
    """Concrete upstream runtime components consumed by the session wrapper."""

    slam: VistaOnlineSlam
    flow_tracker: VistaFlowTracker
    frame_preprocessor: VistaFramePreprocessor


def build_vista_runtime_components(
    *,
    config: VistaSlamBackendConfig,
    path_config: PathConfig,
    console: Console,
    live_mode: bool,
) -> VistaRuntimeComponents:
    """Instantiate one configured upstream ViSTA runtime bundle."""
    vista_dir = path_config.resolve_repo_path(config.vista_slam_dir)
    checkpoint_path = path_config.resolve_repo_path(config.checkpoint_path)
    vocab_path = path_config.resolve_repo_path(config.vocab_path)
    vocab_cache_path = path_config.resolve_repo_path(Path(".artifacts/cache/vista") / f"{vocab_path.stem}.dbow3.bin")
    missing: list[str] = []
    if not vista_dir.exists():
        missing.append(f"vista-slam repo not found at '{vista_dir}'")
    if not checkpoint_path.exists():
        missing.append(f"STA checkpoint missing at '{checkpoint_path}' — download it from the upstream release.")
    if not vocab_path.exists():
        missing.append(f"ORB vocabulary missing at '{vocab_path}' — download it from the upstream release.")
    if missing:
        raise RuntimeError("ViSTA-SLAM prerequisites not satisfied:\n" + "\n".join(f"  • {item}" for item in missing))
    _ensure_vista_namespace_package(vista_dir)
    dbow = _require_dbow_module()
    import torch  # noqa: PLC0415

    SLAM_image_only = importlib.import_module("vista_slam.datasets.slam_images_only").SLAM_image_only
    FlowTracker = importlib.import_module("vista_slam.flow_tracker").FlowTracker
    vista_slam_module = importlib.import_module("vista_slam.slam")
    STA = vista_slam_module.STA
    OnlineSLAM = vista_slam_module.OnlineSLAM

    torch.manual_seed(config.random_seed)
    resolved_vocab_path = resolve_vocab_path(
        dbow=dbow,
        vocab_path=vocab_path,
        vocab_cache_path=vocab_cache_path,
        console=console,
    )
    if live_mode:
        console.info(
            "Forcing upstream live defaults: max_view_num=1000, neighbor_edge_num=2, loop_edge_num=2, pgo_every=50."
        )

    class _FastOnlineSLAM(OnlineSLAM):
        def load_frontend(self, ckpt_path: str):  # type: ignore[override]
            with torch.device("meta"):
                frontend = STA()
            checkpoint = torch.load(ckpt_path, map_location="cpu", weights_only=True, mmap=True)
            frontend.load_state_dict(checkpoint["model"], strict=True, assign=True)
            del checkpoint
            frontend.to(self.device)
            frontend.eval()
            return frontend

    slam = _FastOnlineSLAM(
        ckpt_path=str(checkpoint_path),
        vocab_path=str(resolved_vocab_path),
        max_view_num=1000 if live_mode else config.max_view_num,
        neighbor_edge_num=2 if live_mode else config.neighbor_edge_num,
        loop_edge_num=2 if live_mode else config.loop_edge_num,
        loop_dist_min=config.loop_dist_min,
        loop_nms=config.loop_nms,
        loop_cand_thresh_neighbor=config.loop_cand_thresh_neighbor,
        conf_thres=config.point_conf_thres,
        rel_pose_thres=config.rel_pose_thres,
        flow_thres=config.flow_thres,
        pgo_every=50 if live_mode else config.pgo_every,
        live_mode=live_mode,
    )
    image_dataset = SLAM_image_only([], resolution=_VISTA_INPUT_RESOLUTION)
    return VistaRuntimeComponents(
        slam=slam,
        flow_tracker=FlowTracker(config.flow_thres),
        frame_preprocessor=UpstreamVistaFramePreprocessor(image_dataset=image_dataset),
    )


def resolve_vocab_path(
    *,
    dbow: _DbowModule,
    vocab_path: Path,
    vocab_cache_path: Path,
    console: Console,
) -> Path:
    """Return the effective vocabulary path, building the binary cache when needed."""
    if vocab_path.suffix != ".txt":
        return vocab_path
    if vocab_cache_path.exists():
        return vocab_cache_path
    console.info(
        "Building binary DBoW3 vocabulary cache at '%s'. This is a one-time startup cost.",
        vocab_cache_path,
    )
    vocabulary = dbow.Vocabulary()
    vocabulary.load(str(vocab_path))
    vocab_cache_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = vocab_cache_path.with_suffix(f"{vocab_cache_path.suffix}.tmp")
    vocabulary.save(str(tmp_path), True)
    tmp_path.replace(vocab_cache_path)
    return vocab_cache_path


def _ensure_vista_namespace_package(vista_dir: Path) -> None:
    """Register the upstream `vista_slam` checkout as an explicit namespace package."""
    package_name = "vista_slam"
    package_root = vista_dir / package_name
    if not package_root.exists():
        raise RuntimeError(f"ViSTA package root not found at '{package_root}'.")
    existing = sys.modules.get(package_name)
    if existing is not None:
        existing_paths = [str(path) for path in getattr(existing, "__path__", [])]
        if str(package_root) not in existing_paths:
            raise RuntimeError(f"`{package_name}` is already imported from a different location: {existing_paths!r}.")
        return
    package = ModuleType(package_name)
    spec = ModuleSpec(name=package_name, loader=None, is_package=True)
    spec.submodule_search_locations = [str(package_root)]
    package.__spec__ = spec
    package.__package__ = package_name
    package.__path__ = [str(package_root)]  # type: ignore[attr-defined]
    sys.modules[package_name] = package


def _require_dbow_module() -> _DbowModule:
    """Import the installed `DBoW3Py` dependency with an actionable error."""
    try:
        return importlib.import_module("DBoW3Py")
    except ImportError as exc:
        raise RuntimeError(
            "DBoW3Py is not importable. Install the declared vista extra or fix the local dependency build."
        ) from exc


__all__ = [
    "VistaFlowTracker",
    "VistaOnlineSlam",
    "VistaRuntimeComponents",
    "build_vista_runtime_components",
    "resolve_vocab_path",
]
