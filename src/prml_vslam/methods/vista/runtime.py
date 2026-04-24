"""Upstream ViSTA runtime and bootstrap helpers.

This module owns the heavy lifting required to turn repository config and local
paths into an initialized upstream ViSTA runtime bundle. It stays below the
top-level adapter in :mod:`prml_vslam.methods.vista.adapter` and above the
session wrapper in :mod:`prml_vslam.methods.vista.session`.
"""

from __future__ import annotations

import importlib
import sys
from abc import abstractmethod
from dataclasses import dataclass
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Any, Protocol

from prml_vslam.methods.options import VistaSlamBackendOptions
from prml_vslam.utils import Console, PathConfig

from .preprocess import UpstreamVistaFramePreprocessor, VistaFramePreprocessor

if TYPE_CHECKING:
    import torch

_VISTA_INPUT_RESOLUTION = (224, 224)


class VistaFlowTracker(Protocol):
    """Subset of the upstream flow-tracker API consumed by the session wrapper."""

    @abstractmethod
    def compute_disparity(self, image: Any, visualize: bool = False) -> bool:
        """Return whether the current frame should become a new keyframe."""


class VistaOnlineSlam(Protocol):
    """Subset of the upstream OnlineSLAM API consumed by the wrapper."""

    device: torch.device | str

    @abstractmethod
    def step(self, value: dict[str, Any]) -> None:
        """Consume one prepared keyframe payload through the upstream runtime API."""

    @abstractmethod
    def save_data_all(self, output_dir: str, *, save_images: bool, save_depths: bool) -> None:
        """Persist native ViSTA outputs for later normalization."""

    @abstractmethod
    def get_view(self, view_index: int, **kwargs: Any) -> Any:
        """Return one live view payload from the upstream pose graph."""

    @abstractmethod
    def get_pointmap_vis(self, view_index: int) -> tuple[Any | None, Any | None]:
        """Return preview RGB and dense pointmap payloads for one live view."""


class _DbowVocabulary(Protocol):
    """Subset of the DBoW vocabulary API used for binary cache generation."""

    @abstractmethod
    def load(self, path: str) -> None:
        """Load the text vocabulary from disk."""

    @abstractmethod
    def save(self, path: str, binary: bool) -> None:
        """Write the vocabulary back to disk in the requested format."""


class _DbowModule(Protocol):
    """Subset of the imported DBoW module used by this wrapper."""

    @abstractmethod
    def Vocabulary(self) -> _DbowVocabulary:
        """Construct one vocabulary instance."""


@dataclass(slots=True)
class VistaRuntimeComponents:
    """Bundle the concrete upstream runtime objects consumed by the session wrapper."""

    slam: VistaOnlineSlam
    flow_tracker: VistaFlowTracker
    frame_preprocessor: VistaFramePreprocessor


def build_vista_runtime_components(
    *,
    config: VistaSlamBackendOptions,
    path_config: PathConfig,
    console: Console,
    live_mode: bool,
) -> VistaRuntimeComponents:
    """Instantiate one configured upstream ViSTA runtime bundle.

    This is the main assembly boundary between repo-owned config/path policy and
    the imported upstream ViSTA runtime components.
    """
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

    device = _resolve_torch_device(torch, config=config)
    if device.type == "cpu":
        _patch_xformers_attention_for_cpu(torch)

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
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            self.device = device

        def load_frontend(self, ckpt_path: str):  # type: ignore[override]
            with torch.device("meta"):
                frontend = STA()
            checkpoint = torch.load(ckpt_path, map_location="cpu", weights_only=True, mmap=True)
            frontend.load_state_dict(checkpoint["model"], strict=True, assign=True)
            del checkpoint
            frontend.to(device)
            frontend.eval()
            return frontend

    with _patch_online_slam_default_device(torch, device=device):
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


def _resolve_torch_device(torch_module: Any, *, config: VistaSlamBackendOptions):
    if config.device == "cuda":
        if not torch_module.cuda.is_available():
            raise RuntimeError("ViSTA-SLAM was configured with device='cuda', but no CUDA GPU is available.")
        return torch_module.device("cuda")
    if config.device == "cpu":
        return torch_module.device("cpu")
    return torch_module.device("cuda" if torch_module.cuda.is_available() else "cpu")


def _patch_xformers_attention_for_cpu(torch_module: Any) -> None:
    sta_blocks = importlib.import_module("vista_slam.sta_model.blocks.sta_blocks")
    attention_cls = sta_blocks.XFormer_Attention
    if getattr(attention_cls, "_prml_cpu_patch", False):
        return

    def forward(self: Any, x: Any, xpos: Any) -> Any:
        batch_size, token_count, channel_count = x.shape
        qkv = self.qkv(x).reshape(
            batch_size,
            token_count,
            3,
            self.num_heads,
            channel_count // self.num_heads,
        )
        qkv = qkv.transpose(1, 3)
        q, k, v = [qkv[:, :, index] for index in range(3)]

        if self.rope is not None:
            q = self.rope(q, xpos)
            k = self.rope(k, xpos)

        drop_prob = self.attn_drop_prob if self.training else 0.0
        attended = torch_module.nn.functional.scaled_dot_product_attention(
            q,
            k,
            v,
            dropout_p=drop_prob,
            scale=self.scale,
        )
        output = attended.transpose(1, 2).reshape(batch_size, token_count, channel_count)
        output = self.proj(output)
        return self.proj_drop(output)

    attention_cls.forward = forward
    attention_cls._prml_cpu_patch = True


class _patch_online_slam_default_device:
    def __init__(self, torch_module: Any, *, device: Any) -> None:
        self._torch = torch_module
        self._device = device
        self._original_device = torch_module.device

    def __enter__(self) -> None:
        def patched_device(value: Any = None, *args: Any, **kwargs: Any):
            if value == "cuda":
                return self._device
            return self._original_device(value, *args, **kwargs)

        self._torch.device = patched_device

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self._torch.device = self._original_device


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
