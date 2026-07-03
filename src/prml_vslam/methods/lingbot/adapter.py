"""Optional LingBot-Map backend adapter."""

from __future__ import annotations

import importlib
import json
import os
import shlex
import tempfile
import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray
from PIL import Image

from prml_vslam.interfaces import CAMERA_RDF_FRAME, CameraIntrinsics, FrameTransform, Observation
from prml_vslam.interfaces.artifacts import ArtifactRef, artifact_ref
from prml_vslam.interfaces.slam import SlamArtifacts
from prml_vslam.methods.contracts import SlamUpdate
from prml_vslam.methods.protocols import SlamBackend
from prml_vslam.methods.stage.backend_config import (
    LingbotMapSlamBackendConfig,
    MethodId,
    SlamBackendConfig,
    SlamOutputPolicy,
)
from prml_vslam.sources.contracts import PreparedBenchmarkInputs, ReferenceSource, SequenceManifest
from prml_vslam.utils import Console, PathConfig, RunArtifactPaths
from prml_vslam.utils.geometry import (
    depth_map_to_world_points,
    sample_point_cloud_random,
    write_point_cloud_ply,
    write_tum_trajectory,
)

LINGBOT_WORLD_FRAME = "lingbot_world"


class LingbotMapSlamBackend(SlamBackend):
    """Run LingBot-Map over normalized repository observations."""

    method_id: MethodId = MethodId.LINGBOT_MAP

    def __init__(
        self,
        config: LingbotMapSlamBackendConfig,
        path_config: PathConfig | None = None,
    ) -> None:
        self._cfg = config
        self._path_config = path_config or PathConfig()
        self._console = Console(__name__).child(self.__class__.__name__)
        self._streaming_frames: list[Observation] | None = None
        self._streaming_backend_config: LingbotMapSlamBackendConfig | None = None
        self._streaming_output_policy: SlamOutputPolicy | None = None
        self._streaming_artifact_root: Path | None = None

    def start_streaming(
        self,
        sequence_manifest: SequenceManifest,
        benchmark_inputs: PreparedBenchmarkInputs | None,
        baseline_source: ReferenceSource,
        backend_config: SlamBackendConfig,
        output_policy: SlamOutputPolicy,
        artifact_root: Path,
    ) -> None:
        """Start a bounded LingBot-Map streaming session over incoming RGB frames."""
        del sequence_manifest, benchmark_inputs, baseline_source
        config = _expect_lingbot_config(backend_config)
        _validate_output_policy(output_policy)
        if config.max_frames is None:
            raise RuntimeError(
                "LingBot-Map terminal streaming requires `max_frames` so the adapter cannot retain an unbounded RGB "
                "sequence. Use offline path-backed execution for full finite datasets."
            )
        self._streaming_frames = []
        self._streaming_backend_config = config
        self._streaming_output_policy = output_policy
        self._streaming_artifact_root = artifact_root

    def step_streaming(self, frame: Observation) -> None:
        """Buffer one RGB streaming observation for LingBot terminal inference."""
        frames = self._require_streaming_frames()
        config = self._require_streaming_backend_config()
        if frame.rgb is None:
            return
        if config.max_frames is not None and len(frames) >= config.max_frames:
            return
        frames.append(frame)

    def drain_streaming_updates(self) -> list[SlamUpdate]:
        """LingBot-Map does not expose incremental live updates through this adapter."""
        self._require_streaming_frames()
        return []

    def finish_streaming(self) -> SlamArtifacts:
        """Run LingBot terminal inference and clear streaming state."""
        frames = self._require_streaming_frames()
        config = self._require_streaming_backend_config()
        output_policy = self._require_streaming_output_policy()
        artifact_root = self._require_streaming_artifact_root()
        try:
            return self._run_frames(
                frames,
                backend_config=config,
                output_policy=output_policy,
                artifact_root=artifact_root,
                require_rgb_path=False,
            )
        finally:
            self._streaming_frames = None
            self._streaming_backend_config = None
            self._streaming_output_policy = None
            self._streaming_artifact_root = None

    def run_observations(
        self,
        observations: Iterable[Observation],
        benchmark_inputs: PreparedBenchmarkInputs | None,
        baseline_source: ReferenceSource,
        backend_config: SlamBackendConfig,
        output_policy: SlamOutputPolicy,
        artifact_root: Path,
    ) -> SlamArtifacts:
        """Run LingBot-Map and persist normalized trajectory and dense geometry."""
        del benchmark_inputs, baseline_source
        config = _expect_lingbot_config(backend_config)
        _validate_output_policy(output_policy)

        frames: list[Observation] = []
        for frame in observations:
            if config.max_frames is not None and len(frames) >= config.max_frames:
                break
            if frame.rgb_path is None:
                raise RuntimeError("LingBot offline inference requires path-backed RGB observations.")
            frames.append(_without_heavy_payloads(frame))
        return self._run_frames(
            frames,
            backend_config=config,
            output_policy=output_policy,
            artifact_root=artifact_root,
            require_rgb_path=True,
        )

    def _run_frames(
        self,
        frames: list[Observation],
        *,
        backend_config: LingbotMapSlamBackendConfig,
        output_policy: SlamOutputPolicy,
        artifact_root: Path,
        require_rgb_path: bool,
    ) -> SlamArtifacts:
        if not frames:
            raise RuntimeError("LingBot-Map requires at least one RGB observation.")

        runtime = _LingbotRuntime(backend_config, path_config=self._path_config)
        if require_rgb_path:
            if not all(frame.rgb_path is not None for frame in frames):
                raise RuntimeError("LingBot offline inference requires path-backed RGB observations.")
            image_paths = [frame.rgb_path for frame in frames if frame.rgb_path is not None]
            predictions, processed_images = runtime.infer_paths(image_paths)
        else:
            if not all(frame.rgb is not None for frame in frames):
                raise RuntimeError("LingBot streaming inference requires RGB observations.")
            images_rgb: list[np.ndarray] = []
            for frame in frames:
                if frame.rgb is None:
                    raise RuntimeError("LingBot streaming inference requires RGB observations.")
                images_rgb.append(np.asarray(frame.rgb, dtype=np.uint8))
            predictions, processed_images = runtime.infer(images_rgb)
        return _build_lingbot_artifacts(
            predictions=predictions,
            processed_images=processed_images,
            observations=frames,
            artifact_root=artifact_root,
            output_policy=output_policy,
            config=backend_config,
        )

    def _require_streaming_frames(self) -> list[Observation]:
        if self._streaming_frames is None:
            raise RuntimeError("LingBot-Map streaming backend has not been started.")
        return self._streaming_frames

    def _require_streaming_backend_config(self) -> LingbotMapSlamBackendConfig:
        if self._streaming_backend_config is None:
            raise RuntimeError("LingBot-Map streaming backend has not been started.")
        return self._streaming_backend_config

    def _require_streaming_output_policy(self) -> SlamOutputPolicy:
        if self._streaming_output_policy is None:
            raise RuntimeError("LingBot-Map streaming backend has not been started.")
        return self._streaming_output_policy

    def _require_streaming_artifact_root(self) -> Path:
        if self._streaming_artifact_root is None:
            raise RuntimeError("LingBot-Map streaming backend has not been started.")
        return self._streaming_artifact_root


def _expect_lingbot_config(backend_config: SlamBackendConfig) -> LingbotMapSlamBackendConfig:
    if not isinstance(backend_config, LingbotMapSlamBackendConfig):
        raise TypeError(f"Expected LingbotMapSlamBackendConfig, got {type(backend_config).__name__}.")
    return backend_config


def _without_heavy_payloads(frame: Observation) -> Observation:
    return frame.model_copy(
        update={
            "rgb": None,
            "depth_m": None,
            "confidence": None,
            "pointmap_xyz": None,
            "point_cloud_xyz": None,
            "point_cloud_rgb": None,
            "intrinsics": None,
            "T_world_camera": None,
        }
    )


def _validate_output_policy(output_policy: SlamOutputPolicy) -> None:
    if output_policy.emit_sparse_points:
        raise ValueError("LingBot-Map does not expose a separate sparse point-cloud artifact.")


@dataclass(frozen=True, slots=True)
class _DensePredictionArtifacts:
    points_xyz_world: NDArray[np.float64]
    colors_rgb: NDArray[np.uint8] | None
    stats: dict[str, Any]


class _LingbotRuntime:
    def __init__(self, config: LingbotMapSlamBackendConfig, *, path_config: PathConfig) -> None:
        self._cfg = config
        self._path_config = path_config
        self._console = Console(__name__).child("_LingbotRuntime")

    def infer(self, images_rgb: list[np.ndarray]) -> tuple[dict[str, Any], Any]:
        return self._infer(image_paths=None, images_rgb=images_rgb)

    def infer_paths(self, image_paths: list[Path]) -> tuple[dict[str, Any], Any]:
        return self._infer(image_paths=image_paths, images_rgb=None)

    def _infer(
        self,
        *,
        image_paths: list[Path] | None,
        images_rgb: list[np.ndarray] | None,
    ) -> tuple[dict[str, Any], Any]:
        os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
        _prepare_lingbot_cuda_jit_env()
        torch = importlib.import_module("torch")
        checkpoint = self._resolve_checkpoint()
        model_module_name = (
            "lingbot_map.models.gct_stream_window" if self._cfg.mode == "windowed" else "lingbot_map.models.gct_stream"
        )
        try:
            gct_stream = importlib.import_module(model_module_name).GCTStream
            load_and_preprocess_images = importlib.import_module("lingbot_map.utils.load_fn").load_and_preprocess_images
        except ModuleNotFoundError as exc:
            if exc.name is not None and exc.name.startswith("lingbot_map"):
                raise RuntimeError(
                    "LingBot-Map is not installed. Clone the upstream checkout to `external/lingbot-map` "
                    "and install this project with `uv sync --extra lingbot` before running LingBot."
                ) from exc
            raise
        for device in self._candidate_devices(torch):
            try:
                self._console.info(
                    "Running LingBot-Map on %s with image_size=%d and num_scale_frames=%d.",
                    device,
                    self._cfg.image_size,
                    self._cfg.num_scale_frames,
                )
                return self._infer_on_device(
                    torch=torch,
                    gct_stream=gct_stream,
                    load_and_preprocess_images=load_and_preprocess_images,
                    checkpoint=checkpoint,
                    image_paths=image_paths,
                    images_rgb=images_rgb,
                    device=device,
                )
            except RuntimeError as exc:
                if self._cfg.device == "auto" and device == "cuda" and _is_cuda_oom(exc):
                    Console(__name__).child("_LingbotRuntime").warn(
                        "LingBot-Map CUDA inference ran out of memory; retrying on CPU."
                    )
                    torch.cuda.empty_cache()
                    continue
                raise
        raise RuntimeError("LingBot-Map could not resolve a runnable torch device.")

    def _infer_on_device(
        self,
        *,
        torch: Any,
        gct_stream: Any,
        load_and_preprocess_images: Callable[..., Any],
        checkpoint: Path,
        image_paths: list[Path] | None,
        images_rgb: list[np.ndarray] | None,
        device: str,
    ) -> tuple[dict[str, Any], Any]:
        self._console.info("Initializing LingBot-Map model; upstream checkpoint load may take tens of seconds.")
        init_started = time.monotonic()
        model = gct_stream(
            img_size=self._cfg.image_size,
            patch_size=self._cfg.patch_size,
            enable_3d_rope=self._cfg.enable_3d_rope,
            max_frame_num=self._cfg.max_frame_num,
            kv_cache_sliding_window=self._cfg.kv_cache_sliding_window,
            kv_cache_scale_frames=self._cfg.num_scale_frames,
            kv_cache_cross_frame_special=True,
            kv_cache_include_scale_frames=True,
            enable_point=self._cfg.enable_point_head,
            use_sdpa=self._cfg.use_sdpa or device == "cpu",
            camera_num_iterations=self._cfg.camera_num_iterations,
        )
        self._console.info("LingBot-Map model initialized in %.1fs.", time.monotonic() - init_started)

        self._console.info("Loading LingBot-Map checkpoint from '%s' on CPU.", checkpoint)
        load_started = time.monotonic()
        state = torch.load(str(checkpoint), map_location="cpu", weights_only=True)
        state_dict = dict(_extract_checkpoint_state_dict(state))
        _adapt_checkpoint_state_dict(
            torch,
            state_dict,
            target_state_dict=model.state_dict(),
            pos_embed_policy=self._cfg.checkpoint_pos_embed,
        )
        missing, unexpected = model.load_state_dict(state_dict, strict=False)
        del state, state_dict
        self._console.info("LingBot-Map checkpoint loaded in %.1fs.", time.monotonic() - load_started)
        if missing or unexpected:
            self._console.warn(
                "LingBot-Map checkpoint loaded with %d missing and %d unexpected keys.",
                len(missing),
                len(unexpected),
            )
        if device.startswith("cuda"):
            self._console.info("Moving LingBot-Map model to %s.", device)
            model = model.to(device=device).eval()
            _cast_aggregator_for_inference(torch, model, dtype=_resolve_model_dtype(torch, self._cfg.model_dtype))
        else:
            model = model.to(device).eval()

        if image_paths is not None:
            frame_count = len(image_paths)
            self._console.info("Preparing %d RGB frame paths for LingBot-Map inference.", frame_count)
            image_tensor = _preprocess_image_paths_with_lingbot(
                load_and_preprocess_images,
                image_paths,
                image_size=self._cfg.image_size,
                patch_size=self._cfg.patch_size,
            )
        elif images_rgb is not None:
            frame_count = len(images_rgb)
            self._console.info("Preparing %d RGB frames for LingBot-Map inference.", frame_count)
            image_tensor = _preprocess_images_with_lingbot(
                load_and_preprocess_images,
                images_rgb,
                image_size=self._cfg.image_size,
                patch_size=self._cfg.patch_size,
            )
        else:
            raise RuntimeError("LingBot-Map inference requires RGB frame paths or RGB arrays.")
        self._console.info(
            "Starting LingBot-Map inference on tensor shape %s.",
            tuple(int(dim) for dim in image_tensor.shape),
        )
        inference_started = time.monotonic()
        with torch.no_grad():
            if device.startswith("cuda") and self._cfg.use_amp:
                dtype = torch.bfloat16 if torch.cuda.get_device_capability()[0] >= 8 else torch.float16
                with torch.amp.autocast("cuda", dtype=dtype):
                    predictions = self._run_model(model, image_tensor, torch)
            else:
                predictions = self._run_model(model, image_tensor, torch)
        self._console.info("LingBot-Map inference finished in %.1fs.", time.monotonic() - inference_started)
        processed_images = predictions.get("images")
        if processed_images is None:
            processed_images = image_tensor.detach().cpu().unsqueeze(0)
        return predictions, processed_images

    def _run_model(self, model: Any, image_tensor: Any, torch: Any) -> dict[str, Any]:
        keyframe_interval = _resolve_keyframe_interval(
            self._cfg.keyframe_interval,
            num_frames=int(image_tensor.shape[0]),
            num_scale_frames=self._cfg.num_scale_frames,
        )
        if self._cfg.mode == "streaming":
            return model.inference_streaming(
                image_tensor,
                num_scale_frames=self._cfg.num_scale_frames,
                keyframe_interval=keyframe_interval,
                output_device=torch.device("cpu"),
            )
        return model.inference_windowed(
            image_tensor,
            window_size=self._cfg.window_size,
            overlap_size=self._cfg.overlap_size,
            overlap_keyframes=self._cfg.overlap_keyframes,
            num_scale_frames=self._cfg.num_scale_frames,
            keyframe_interval=keyframe_interval,
            output_device=torch.device("cpu"),
        )

    def _resolve_checkpoint(self) -> Path:
        checkpoint = self._path_config.resolve_repo_path(self._cfg.checkpoint_path)
        if not checkpoint.exists():
            raise RuntimeError(
                f"LingBot-Map checkpoint not found at '{checkpoint}'. Override `checkpoint_path` "
                "with a local checkpoint before running."
            )
        return checkpoint

    def _candidate_devices(self, torch: Any) -> list[str]:
        if self._cfg.device == "auto":
            return ["cuda", "cpu"] if torch.cuda.is_available() else ["cpu"]
        if self._cfg.device == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("LingBot-Map requested CUDA but torch.cuda.is_available() is false.")
        return [self._cfg.device]


def _is_cuda_oom(exc: RuntimeError) -> bool:
    message = str(exc).lower()
    return "cuda out of memory" in message or ("cuda" in message and "out of memory" in message)


def _prepare_lingbot_cuda_jit_env() -> None:
    """Expose active mamba CUDA build paths to FlashInfer's JIT linker."""
    cuda_home = _resolve_lingbot_cuda_home()
    if cuda_home is None:
        return

    nvcc = cuda_home / "bin" / "nvcc"
    if nvcc.exists():
        current_cuda_home = os.environ.get("CUDA_HOME")
        if current_cuda_home is None or not _has_lingbot_cuda_jit_inputs(Path(current_cuda_home)):
            os.environ["CUDA_HOME"] = str(cuda_home)

    compiler_bin = cuda_home / "bin"
    cc = compiler_bin / "x86_64-conda-linux-gnu-gcc"
    cxx = compiler_bin / "x86_64-conda-linux-gnu-g++"
    if cc.exists():
        os.environ.setdefault("CC", str(cc))
    if cxx.exists():
        os.environ.setdefault("CXX", str(cxx))
        os.environ.setdefault("CUDAHOSTCXX", str(cxx))
        os.environ.setdefault("NVCC_PREPEND_FLAGS", f"--compiler-bindir={compiler_bin}")

    _prepend_flashinfer_stub_ldflags(cuda_home)


def _resolve_lingbot_cuda_home() -> Path | None:
    for variable in ("CUDA_HOME", "CUDA_PATH", "CONDA_PREFIX"):
        value = os.environ.get(variable)
        if value and _has_lingbot_cuda_jit_inputs(Path(value)):
            return Path(value)
    return None


def _has_lingbot_cuda_jit_inputs(cuda_home: Path) -> bool:
    return (cuda_home / "bin" / "nvcc").exists() or any(
        (stub_dir / "libcuda.so").exists()
        for stub_dir in (
            cuda_home / "lib" / "stubs",
            cuda_home / "targets" / "x86_64-linux" / "lib" / "stubs",
        )
    )


def _prepend_flashinfer_stub_ldflags(cuda_home: Path) -> None:
    flags = shlex.split(os.environ.get("FLASHINFER_EXTRA_LDFLAGS", ""))
    for stub_dir in reversed(
        (
            cuda_home / "lib" / "stubs",
            cuda_home / "targets" / "x86_64-linux" / "lib" / "stubs",
        )
    ):
        if (stub_dir / "libcuda.so").exists():
            flag = f"-L{stub_dir}"
            if flag not in flags:
                flags.insert(0, flag)
    if flags:
        os.environ["FLASHINFER_EXTRA_LDFLAGS"] = " ".join(shlex.quote(flag) for flag in flags)


def _extract_checkpoint_state_dict(state: Any) -> Mapping[str, Any]:
    if not isinstance(state, Mapping):
        raise RuntimeError("LingBot-Map checkpoint did not contain a state-dict mapping.")
    if "model" in state:
        model_state = state["model"]
        if not isinstance(model_state, Mapping):
            raise RuntimeError("LingBot-Map checkpoint `model` entry did not contain a state-dict mapping.")
        return model_state
    return state


def _adapt_checkpoint_state_dict(
    torch: Any,
    state_dict: dict[str, Any],
    *,
    target_state_dict: Mapping[str, Any],
    pos_embed_policy: str,
) -> None:
    key = "aggregator.patch_embed.pos_embed"
    source = state_dict.get(key)
    target = target_state_dict.get(key)
    if source is None or target is None or tuple(source.shape) == tuple(target.shape):
        return
    if pos_embed_policy == "drop":
        del state_dict[key]
        return
    if pos_embed_policy != "interpolate":
        raise RuntimeError(
            f"LingBot-Map checkpoint key '{key}' has shape {tuple(source.shape)}, but the configured model expects "
            f'{tuple(target.shape)}. Set `checkpoint_pos_embed = "interpolate"` or `"drop"` when using '
            "a smaller `image_size` than the checkpoint."
        )
    state_dict[key] = _resize_pos_embed(torch, source, target)


def _resize_pos_embed(torch: Any, source: Any, target: Any) -> Any:
    if len(source.shape) != 3 or len(target.shape) != 3 or source.shape[0] != 1 or target.shape[0] != 1:
        raise RuntimeError(
            "LingBot-Map positional embedding interpolation requires [1, num_tokens, dim] tensors; "
            f"got {tuple(source.shape)} -> {tuple(target.shape)}."
        )
    if source.shape[-1] != target.shape[-1]:
        raise RuntimeError(
            f"LingBot-Map positional embedding dimension mismatch: {int(source.shape[-1])} -> {int(target.shape[-1])}."
        )
    source_grid_tokens = int(source.shape[1]) - 1
    target_grid_tokens = int(target.shape[1]) - 1
    source_grid = int(source_grid_tokens**0.5)
    target_grid = int(target_grid_tokens**0.5)
    if source_grid * source_grid != source_grid_tokens or target_grid * target_grid != target_grid_tokens:
        raise RuntimeError(
            "LingBot-Map positional embedding interpolation requires square patch-token grids; "
            f"got {source_grid_tokens} -> {target_grid_tokens} patch tokens."
        )
    class_token = source[:, :1]
    patch_tokens = source[:, 1:].reshape(1, source_grid, source_grid, source.shape[-1]).permute(0, 3, 1, 2)
    resized = torch.nn.functional.interpolate(
        patch_tokens.float(),
        size=(target_grid, target_grid),
        mode="bicubic",
        align_corners=False,
    )
    resized = (
        resized.to(dtype=source.dtype, device=source.device)
        .permute(0, 2, 3, 1)
        .reshape(1, target_grid_tokens, target.shape[-1])
    )
    return torch.cat([class_token, resized], dim=1)


def _resolve_model_dtype(torch: Any, value: str) -> Any:
    if value == "float32":
        return torch.float32
    if value == "float16":
        return torch.float16
    if value == "bfloat16":
        return torch.bfloat16
    capability = torch.cuda.get_device_capability()
    return torch.bfloat16 if capability[0] >= 8 else torch.float16


def _cast_aggregator_for_inference(torch: Any, model: Any, *, dtype: Any) -> None:
    if dtype == torch.float32:
        return
    aggregator = getattr(model, "aggregator", None)
    if aggregator is not None:
        model.aggregator = aggregator.to(dtype=dtype)


def _preprocess_images_with_lingbot(
    load_and_preprocess_images: Callable[..., Any],
    images_rgb: list[np.ndarray],
    *,
    image_size: int,
    patch_size: int,
) -> Any:
    with tempfile.TemporaryDirectory(prefix="prml-lingbot-frames-") as frame_dir:
        frame_paths: list[str] = []
        for index, image in enumerate(images_rgb):
            rgb = np.asarray(image, dtype=np.uint8)
            if rgb.ndim != 3 or rgb.shape[2] != 3:
                raise ValueError(f"Expected RGB image shape (H, W, 3), got {rgb.shape}.")
            frame_path = Path(frame_dir) / f"{index:06d}.png"
            Image.fromarray(rgb).save(frame_path)
            frame_paths.append(str(frame_path))
        return _preprocess_image_paths_with_lingbot(
            load_and_preprocess_images,
            [Path(frame_path) for frame_path in frame_paths],
            image_size=image_size,
            patch_size=patch_size,
        )


def _preprocess_image_paths_with_lingbot(
    load_and_preprocess_images: Callable[..., Any],
    image_paths: list[Path],
    *,
    image_size: int,
    patch_size: int,
) -> Any:
    return load_and_preprocess_images(
        [str(path) for path in image_paths],
        mode="crop",
        image_size=image_size,
        patch_size=patch_size,
    )


def _resolve_keyframe_interval(
    value: int | str,
    *,
    num_frames: int,
    num_scale_frames: int,
) -> int:
    del num_scale_frames
    if value != "auto":
        return max(int(value), 1)
    return 1 if num_frames <= 320 else (num_frames + 319) // 320


def _build_lingbot_artifacts(
    *,
    predictions: dict[str, Any],
    processed_images: Any,
    observations: list[Observation],
    artifact_root: Path,
    output_policy: SlamOutputPolicy,
    config: LingbotMapSlamBackendConfig,
) -> SlamArtifacts:
    run_paths = RunArtifactPaths.build(artifact_root)
    native_dir = run_paths.native_output_dir
    native_dir.mkdir(parents=True, exist_ok=True)

    extrinsics_camera_to_world, intrinsics = _decode_pose_predictions(predictions, processed_images=processed_images)
    observation_count = len(observations)
    if observation_count == 0:
        raise RuntimeError("LingBot-Map did not produce any pose predictions.")
    if len(extrinsics_camera_to_world) != observation_count or len(intrinsics) != observation_count:
        raise RuntimeError(
            "LingBot-Map pose prediction count did not match processed observations: "
            f"observations={observation_count}, extrinsics={len(extrinsics_camera_to_world)}, "
            f"intrinsics={len(intrinsics)}."
        )
    poses = [_pose_camera_to_world_to_frame_transform(extrinsic) for extrinsic in extrinsics_camera_to_world]
    timestamps_s = [frame.timestamp_ns / 1e9 for frame in observations]
    trajectory_path = write_tum_trajectory(run_paths.trajectory_path, poses, timestamps_s)

    dense_ref: ArtifactRef | None = None
    num_dense_points = 0
    dense_point_stats: dict[str, Any] = {}
    if output_policy.emit_dense_points:
        dense_artifacts = _extract_dense_prediction_artifacts(
            predictions=predictions,
            processed_images=processed_images,
            intrinsics=intrinsics,
            poses=poses,
            config=config,
        )
        points = dense_artifacts.points_xyz_world
        colors = dense_artifacts.colors_rgb
        dense_point_stats = dense_artifacts.stats
        dense_point_stats["num_points_before_sampling"] = len(points)
        points, colors = sample_point_cloud_random(points, colors, max_points=config.max_points, seed=17)
        dense_point_stats["num_points_after_sampling"] = len(points)
        dense_path = write_point_cloud_ply(run_paths.point_cloud_path, points, colors_rgb=colors)
        dense_ref = artifact_ref(dense_path, kind="ply")
        num_dense_points = len(points)

    npz_path = native_dir / "predictions_normalized.npz"
    np.savez_compressed(
        npz_path,
        extrinsics_camera_to_world=extrinsics_camera_to_world,
        intrinsics=intrinsics,
        timestamps_s=np.asarray(timestamps_s, dtype=np.float64),
    )
    metadata_path = native_dir / "lingbot_metadata.json"
    metadata_path.write_text(
        json.dumps(
            {
                "method_id": MethodId.LINGBOT_MAP.value,
                "pose_convention": "T_world_camera = pose_encoding_to_extri_intri extrinsic",
                "native_pose_convention": (
                    "LingBot-Map streaming/benchmark output treats pose_encoding_to_extri_intri extrinsic as "
                    "camera_to_world (C2W)."
                ),
                "camera_frame": CAMERA_RDF_FRAME,
                "num_processed_frames": len(observations),
                "num_keyframes": len(poses),
                "processed_image_shape_hw": list(_as_numpy(processed_images).shape[-2:]),
                "dense_point_source": "depth",
                "dense_point_stats": dense_point_stats,
                "confidence_threshold": config.confidence_threshold,
                "point_stride": config.point_stride,
                "max_depth_m": config.max_depth_m,
                "world_frame": LINGBOT_WORLD_FRAME,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    extras = {
        npz_path.name: artifact_ref(npz_path, kind="npz"),
        metadata_path.name: artifact_ref(metadata_path, kind="json"),
    }
    return SlamArtifacts(
        trajectory_tum=artifact_ref(trajectory_path, kind="tum"),
        sparse_points_ply=None,
        dense_points_ply=dense_ref,
        extras=extras,
        num_processed_frames=len(observations),
        num_keyframes=len(poses),
        num_sparse_points=0,
        num_dense_points=num_dense_points,
    )


def _decode_pose_predictions(predictions: dict[str, Any], *, processed_images: Any) -> tuple[np.ndarray, np.ndarray]:
    if "pose_enc" not in predictions:
        raise RuntimeError("LingBot-Map predictions did not include `pose_enc`.")
    pose_encoding_to_extri_intri = importlib.import_module("lingbot_map.utils.pose_enc").pose_encoding_to_extri_intri
    image_shape_hw = tuple(int(value) for value in _as_numpy(processed_images).shape[-2:])
    extrinsic, intrinsic = pose_encoding_to_extri_intri(predictions["pose_enc"], image_shape_hw)
    return _strip_batch(_as_numpy(extrinsic)).astype(np.float64), _strip_batch(_as_numpy(intrinsic)).astype(np.float64)


def _pose_camera_to_world_to_frame_transform(extrinsic_camera_to_world: np.ndarray) -> FrameTransform:
    matrix = np.eye(4, dtype=np.float64)
    extrinsic = np.asarray(extrinsic_camera_to_world, dtype=np.float64)
    if extrinsic.shape != (3, 4):
        raise ValueError(f"Expected LingBot extrinsic shape (3, 4), got {extrinsic.shape}.")
    matrix[:3, :] = extrinsic
    return FrameTransform.from_matrix(
        matrix,
        target_frame=LINGBOT_WORLD_FRAME,
        source_frame=CAMERA_RDF_FRAME,
    )


def _extract_dense_prediction_artifacts(
    *,
    predictions: dict[str, Any],
    processed_images: Any,
    intrinsics: np.ndarray,
    poses: list[FrameTransform],
    config: LingbotMapSlamBackendConfig,
) -> _DensePredictionArtifacts:
    images = _images_chw_to_rgb(_strip_batch(_as_numpy(processed_images)))
    if "depth" not in predictions:
        raise RuntimeError("LingBot-Map predictions did not include `depth` for dense PLY export.")
    depth = _strip_batch(_as_numpy(predictions["depth"])).astype(np.float32)
    if depth.ndim == 4 and depth.shape[-1] == 1:
        depth = depth[..., 0]
    confidence = _optional_prediction_map(
        predictions,
        "depth_conf",
        depth.shape,
        require_if_threshold=config.confidence_threshold,
    )
    points, colors, stats = _flatten_depth_points(
        depth,
        images=images,
        intrinsics=intrinsics,
        poses=poses,
        confidence=confidence,
        confidence_threshold=config.confidence_threshold,
        stride=config.point_stride,
        max_depth_m=config.max_depth_m,
    )
    return _DensePredictionArtifacts(
        points_xyz_world=points,
        colors_rgb=colors,
        stats=stats,
    )


def _flatten_depth_points(
    depth: np.ndarray,
    *,
    images: np.ndarray,
    intrinsics: np.ndarray,
    poses: list[FrameTransform],
    confidence: np.ndarray | None,
    confidence_threshold: float,
    stride: int,
    max_depth_m: float | None,
) -> tuple[np.ndarray, np.ndarray | None, dict[str, Any]]:
    all_points: list[np.ndarray] = []
    all_colors: list[np.ndarray] = []
    candidate_points = 0
    finite_points = 0
    for index, depth_map in enumerate(depth[: len(poses)]):
        valid_depth = np.asarray(depth_map, dtype=np.float32)
        valid_mask = np.isfinite(valid_depth) & (valid_depth > 0.0)
        if max_depth_m is not None:
            valid_mask &= valid_depth <= max_depth_m
        if confidence is not None:
            valid_mask &= confidence[index] >= confidence_threshold
        finite_points += int(np.count_nonzero(valid_mask))
        valid_depth = np.where(valid_mask, valid_depth, 0.0).astype(np.float32, copy=False)
        candidate_points += int(np.count_nonzero(valid_depth[::stride, ::stride]))
        frame_intrinsics = CameraIntrinsics.from_matrix(
            intrinsics[index],
            width_px=int(valid_depth.shape[1]),
            height_px=int(valid_depth.shape[0]),
        )
        rgb = images[index] if index < len(images) and images[index].shape[:2] == valid_depth.shape else None
        points, colors = depth_map_to_world_points(
            valid_depth,
            frame_intrinsics,
            poses[index],
            rgb=rgb,
            depth_stride_px=stride,
        )
        if len(points) == 0:
            continue
        all_points.append(points)
        if colors is not None:
            all_colors.append(colors)
    colors_out = np.concatenate(all_colors, axis=0) if len(all_colors) == len(all_points) else None
    return (
        np.concatenate(all_points, axis=0).astype(np.float64, copy=False)
        if all_points
        else np.empty((0, 3), dtype=np.float64),
        None if colors_out is None else colors_out.astype(np.uint8, copy=False),
        {
            "source": "depth",
            "candidate_points": candidate_points,
            "finite_points": finite_points,
            "confidence_filter_applied": confidence is not None,
            "confidence_threshold": confidence_threshold,
            "max_depth_filter": "camera_depth" if max_depth_m is not None else "none",
            "world_frame": LINGBOT_WORLD_FRAME,
        },
    )


def _optional_prediction_map(
    predictions: dict[str, Any],
    key: str,
    expected_shape: tuple[int, ...],
    *,
    require_if_threshold: float,
) -> np.ndarray | None:
    if key not in predictions:
        if require_if_threshold > 0.0:
            raise RuntimeError(
                f"LingBot-Map confidence filtering requested threshold {require_if_threshold}, "
                f"but prediction key `{key}` was not present."
            )
        return None
    values = _strip_batch(_as_numpy(predictions[key])).astype(np.float32)
    if values.shape != expected_shape:
        if require_if_threshold > 0.0:
            raise RuntimeError(
                f"LingBot-Map confidence map `{key}` shape {values.shape} did not match expected "
                f"{expected_shape} for threshold {require_if_threshold}."
            )
        return None
    return values


def _images_chw_to_rgb(images: np.ndarray) -> np.ndarray:
    arr = np.asarray(images)
    if arr.ndim == 5 and arr.shape[0] == 1:
        arr = arr[0]
    if arr.ndim == 4 and arr.shape[1] == 3:
        arr = arr.transpose(0, 2, 3, 1)
    if arr.ndim == 3 and arr.shape[0] == 3:
        arr = arr.transpose(1, 2, 0)[None, ...]
    if arr.dtype != np.uint8:
        arr = (arr * 255.0).clip(0, 255).astype(np.uint8)
    return np.ascontiguousarray(arr)


def _strip_batch(array: np.ndarray) -> np.ndarray:
    return array[0] if array.ndim >= 1 and array.shape[0] == 1 else array


def _as_numpy(value: Any) -> np.ndarray:
    torch = importlib.import_module("torch")
    if isinstance(value, torch.Tensor):
        return value.detach().cpu().numpy()
    return np.asarray(value)


__all__ = [
    "LingbotMapSlamBackend",
    "_prepare_lingbot_cuda_jit_env",
    "_build_lingbot_artifacts",
    "_pose_camera_to_world_to_frame_transform",
    "_resolve_keyframe_interval",
]
