"""MASt3R-SLAM backend adapter for the current stage runtime.

The adapter wraps the upstream checkout under ``external/mast3r-slam`` while
keeping the repository boundary narrow: offline and streaming paths consume
normalized :class:`prml_vslam.interfaces.observation.Observation` frames and
return normalized :class:`prml_vslam.methods.contracts.SlamArtifacts`.

Live pointmaps emitted in :class:`prml_vslam.methods.contracts.SlamUpdate`
remain camera-local RDF. Camera placement crosses the boundary separately as
``T_world_camera``.
"""

from __future__ import annotations

import importlib.util
import sys
import threading
from collections.abc import Iterable
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np

from prml_vslam.interfaces import CAMERA_RDF_FRAME, Observation
from prml_vslam.interfaces.artifacts import artifact_ref
from prml_vslam.interfaces.transforms import FrameTransform
from prml_vslam.methods.contracts import SlamArtifacts, SlamUpdate
from prml_vslam.methods.protocols import SlamBackend
from prml_vslam.methods.stage.backend_config import (
    Mast3rSlamBackendConfig,
    MethodId,
    SlamBackendConfig,
    SlamOutputPolicy,
)
from prml_vslam.sources.contracts import PreparedBenchmarkInputs, ReferenceSource, SequenceManifest
from prml_vslam.utils import Console, PathConfig, RunArtifactPaths

_BACKEND_JOIN_TIMEOUT_S = 30.0


class _InProcessValue:
    """Stand-in for ``mp.Manager().Value`` without a helper process."""

    __slots__ = ("value",)

    def __init__(self, typecode: str, initial: Any) -> None:
        del typecode
        self.value = initial


class _InProcessManager:
    """Small manager shim for upstream shared keyframe/state containers."""

    def RLock(self):  # noqa: N802
        """Return a reentrant lock using the upstream Manager naming."""
        return threading.RLock()

    def Value(self, typecode: str, initial: Any):  # noqa: N802
        """Return a mutable value using the upstream Manager naming."""
        return _InProcessValue(typecode, initial)

    def list(self):  # noqa: A003
        """Return a mutable list using the upstream Manager naming."""
        return []


class _Mast3rSlamSession:
    """Backend-private session over one upstream MASt3R-SLAM runtime."""

    def __init__(
        self,
        *,
        cfg: Mast3rSlamBackendConfig,
        output_policy: SlamOutputPolicy,
        artifact_root: Path,
        path_config: PathConfig,
        console: Console,
    ) -> None:
        self._cfg = cfg
        self._output_policy = output_policy
        self._artifact_root = artifact_root
        self._path_config = path_config
        self._console = console.child("Mast3rSlamSession")

        self._device: str = cfg.device
        self._img_size: int = cfg.img_size
        self._model: Any = None
        self._keyframes: Any = None
        self._states: Any = None
        self._tracker: Any = None
        self._manager: Any = None
        self._K: Any = None
        self._h = 0
        self._w = 0

        self._torch: Any = None
        self._mast3r_cfg: dict[str, Any] = {}
        self._lietorch: Any = None
        self._Mode: Any = None
        self._create_frame: Any = None
        self._resize_img: Any = None
        self._SharedKeyframes: Any = None
        self._SharedStates: Any = None
        self._FrameTracker: Any = None
        self._Intrinsics: Any = None
        self._as_SE3: Any = None
        self._mast3r_inference_mono: Any = None
        self._upstream_main: ModuleType | None = None

        self._source_frame_count = 0
        self._accepted_keyframe_count = 0
        self._num_dense_points = 0
        self._timestamps_s: list[float] = []
        self._pending_updates: list[SlamUpdate] = []
        self._backend_error: Exception | None = None

        self._backend_thread: threading.Thread | None = None

        self._initialize()

    def _initialize(self) -> None:
        """Load upstream modules, config, model, and cached runtime symbols."""
        import torch

        self._inject_sys_path()
        self._validate_prerequisites()

        from mast3r_slam.config import load_config

        load_config(str(self._resolve_path(self._cfg.yaml_config_path)))
        from mast3r_slam.config import config as mast3r_cfg

        if self._cfg.use_calib is not None:
            mast3r_cfg["use_calib"] = bool(self._cfg.use_calib)
        self._mast3r_cfg = mast3r_cfg

        torch.backends.cuda.matmul.allow_tf32 = True
        torch.set_grad_enabled(False)
        self._torch = torch

        import lietorch
        from mast3r_slam.dataloader import Intrinsics
        from mast3r_slam.frame import Mode, SharedKeyframes, SharedStates, create_frame
        from mast3r_slam.lietorch_utils import as_SE3
        from mast3r_slam.mast3r_utils import load_mast3r, mast3r_inference_mono, resize_img
        from mast3r_slam.tracker import FrameTracker

        checkpoint = str(self._resolve_path(self._cfg.checkpoint_path))
        self._console.info("Loading MASt3R model from '%s'.", checkpoint)
        self._model = load_mast3r(path=checkpoint, device=self._device)
        self._model.share_memory()

        self._lietorch = lietorch
        self._Mode = Mode
        self._create_frame = create_frame
        self._resize_img = resize_img
        self._SharedKeyframes = SharedKeyframes
        self._SharedStates = SharedStates
        self._FrameTracker = FrameTracker
        self._Intrinsics = Intrinsics
        self._as_SE3 = as_SE3
        self._mast3r_inference_mono = mast3r_inference_mono
        self._upstream_main = _load_upstream_main_module(self._resolve_path(self._cfg.mast3r_slam_dir))

    def step(self, frame: Observation) -> None:
        """Feed one normalized observation to MASt3R and queue a live update."""
        self._raise_if_backend_failed()
        if frame.rgb is None:
            raise RuntimeError("MASt3R-SLAM requires RGB observations.")

        if self._keyframes is None:
            img_f32_dummy = frame.rgb.astype(np.float32) / 255.0
            probe = self._resize_img(img_f32_dummy, self._img_size)
            self._h, self._w = int(probe["img"].shape[2]), int(probe["img"].shape[3])
            self._manager = _InProcessManager()
            self._keyframes = self._SharedKeyframes(self._manager, self._h, self._w, device=self._device)
            self._states = self._SharedStates(self._manager, self._h, self._w, device=self._device)
            self._tracker = self._FrameTracker(self._model, self._keyframes, self._device)
            self._console.info("MASt3R initialized with dynamic size %dx%d.", self._w, self._h)

        internal_idx = self._source_frame_count
        self._timestamps_s.append(frame.timestamp_ns / 1e9)
        self._maybe_set_intrinsics(frame)
        if self._backend_thread is None:
            self._start_backend_thread()

        img_f32 = frame.rgb.astype(np.float32) / 255.0
        if internal_idx == 0:
            T_world_camera = self._lietorch.Sim3.Identity(1, device=self._device)
        else:
            previous_frame = self._states.get_frame()
            T_world_camera = previous_frame.T_WC

        mast3r_frame = self._create_frame(
            internal_idx,
            img_f32,
            T_world_camera,
            img_size=self._img_size,
            device=self._device,
        )

        mode = self._states.get_mode()
        is_keyframe = False
        keyframe_index: int | None = None
        pose_updated = False

        if mode == self._Mode.INIT:
            points_init, confidence_init = self._mast3r_inference_mono(self._model, mast3r_frame)
            mast3r_frame.update_pointmap(points_init, confidence_init)
            self._keyframes.append(mast3r_frame)
            self._states.queue_global_optimization(len(self._keyframes) - 1)
            self._states.set_mode(self._Mode.TRACKING)
            self._states.set_frame(mast3r_frame)
            is_keyframe = True
            keyframe_index = len(self._keyframes) - 1
            self._accepted_keyframe_count = 1
            pose_updated = True
        elif mode == self._Mode.TRACKING:
            add_new_keyframe, _match_info, try_relocalization = self._tracker.track(mast3r_frame)
            if try_relocalization:
                self._states.set_mode(self._Mode.RELOC)
            self._states.set_frame(mast3r_frame)
            pose_updated = True
            if add_new_keyframe:
                self._keyframes.append(mast3r_frame)
                self._states.queue_global_optimization(len(self._keyframes) - 1)
                is_keyframe = True
                keyframe_index = len(self._keyframes) - 1
                self._accepted_keyframe_count += 1
        elif mode == self._Mode.RELOC:
            points, confidence = self._mast3r_inference_mono(self._model, mast3r_frame)
            mast3r_frame.update_pointmap(points, confidence)
            self._states.set_frame(mast3r_frame)
            self._states.queue_reloc()
        else:
            raise RuntimeError(f"Unexpected MASt3R mode: {mode}")

        self._source_frame_count += 1
        self._emit_update(
            frame=frame,
            mast3r_frame=mast3r_frame,
            is_keyframe=is_keyframe,
            keyframe_index=keyframe_index,
            pose_updated=pose_updated,
        )

    def try_get_updates(self) -> list[SlamUpdate]:
        """Return and clear pending updates while surfacing backend failures."""
        self._raise_if_backend_failed()
        updates = self._pending_updates
        self._pending_updates = []
        return updates

    def close(self) -> SlamArtifacts:
        """Stop backend optimization, export native outputs, and return artifacts."""
        if self._states is None or self._keyframes is None:
            raise RuntimeError("MASt3R-SLAM close() called before processing any RGB frames.")
        self._raise_if_backend_failed()
        self._states.set_mode(self._Mode.TERMINATED)
        self._join_backend_thread()
        self._raise_if_backend_failed()

        run_paths = RunArtifactPaths.build(self._artifact_root)
        native_output_dir = run_paths.native_output_dir
        native_output_dir.mkdir(parents=True, exist_ok=True)
        seq_name = "mast3r"
        traj_native = native_output_dir / f"{seq_name}.txt"
        ply_native = native_output_dir / f"{seq_name}.ply"

        from mast3r_slam.evaluate import save_reconstruction, save_traj

        try:
            save_traj(
                native_output_dir,
                traj_native.name,
                self._timestamps_s,
                self._keyframes,
                intrinsics=None,
            )
        except Exception as exc:
            raise RuntimeError(
                "MASt3R-SLAM failed to export trajectory for "
                f"{self._source_frame_count} frames and {self._accepted_keyframe_count} keyframes."
            ) from exc

        ply_written = False
        if self._output_policy.emit_dense_points:
            try:
                save_reconstruction(
                    native_output_dir,
                    ply_native.name,
                    self._keyframes,
                    self._cfg.c_conf_threshold,
                )
                ply_written = ply_native.exists()
            except Exception as exc:
                self._console.warning("MASt3R-SLAM reconstruction export failed: %s", exc)

        self._console.info(
            "MASt3R-SLAM session closed after %d frames and %d keyframes. Native outputs: '%s'.",
            self._source_frame_count,
            self._accepted_keyframe_count,
            native_output_dir,
        )
        return _build_artifacts(
            native_output_dir=native_output_dir,
            artifact_root=self._artifact_root,
            output_policy=self._output_policy,
            traj_native=traj_native,
            ply_native=ply_native if ply_written else None,
        )

    def abort(self) -> None:
        """Best-effort stop used when a run fails before normal close."""
        try:
            if self._states is not None and self._Mode is not None:
                self._states.set_mode(self._Mode.TERMINATED)
        except Exception as exc:
            self._console.warning("MASt3R-SLAM abort could not set terminal state: %s", exc)
        self._join_backend_thread()

    def _maybe_set_intrinsics(self, frame: Observation) -> None:
        """Populate first-frame intrinsics before the backend thread starts."""
        if not self._mast3r_cfg.get("use_calib", False):
            return
        if self._K is not None:
            return
        if frame.rgb is None:
            raise RuntimeError("MASt3R use_calib=True requires RGB frames.")
        if frame.intrinsics is None:
            raise RuntimeError(
                "MASt3R use_calib=True but Observation.intrinsics is None. "
                "Provide calibrated observations or set Mast3rSlamBackendConfig.use_calib=False."
            )
        width_raw = frame.intrinsics.width_px or frame.rgb.shape[1]
        height_raw = frame.intrinsics.height_px or frame.rgb.shape[0]
        intrinsics_obj = self._Intrinsics.from_calib(
            self._img_size,
            width_raw,
            height_raw,
            [
                frame.intrinsics.fx,
                frame.intrinsics.fy,
                frame.intrinsics.cx,
                frame.intrinsics.cy,
                *frame.intrinsics.distortion_coefficients,
            ],
        )
        if intrinsics_obj is None:
            return
        self._K = self._torch.from_numpy(intrinsics_obj.K_frame).to(self._device, dtype=self._torch.float32)
        self._keyframes.set_intrinsics(self._K)

    def _emit_update(
        self,
        *,
        frame: Observation,
        mast3r_frame: Any,
        is_keyframe: bool,
        keyframe_index: int | None,
        pose_updated: bool,
    ) -> None:
        pose = self._frame_transform_from_sim3(mast3r_frame.T_WC) if pose_updated else None
        pointmap: np.ndarray | None = None
        preview_rgb: np.ndarray | None = None
        added_points = 0

        if is_keyframe and self._output_policy.emit_dense_points:
            pointmap, preview_rgb, added_points = self._extract_keyframe_visuals(mast3r_frame)
            self._num_dense_points += added_points

        self._pending_updates.append(
            SlamUpdate(
                seq=frame.seq,
                timestamp_ns=frame.timestamp_ns,
                source_seq=frame.seq,
                source_timestamp_ns=frame.timestamp_ns,
                is_keyframe=is_keyframe,
                keyframe_index=keyframe_index,
                pose=pose,
                pose_updated=pose_updated,
                num_sparse_points=0,
                num_dense_points=self._num_dense_points,
                pointmap=pointmap,
                camera_intrinsics=frame.intrinsics,
                image_rgb=frame.rgb,
                preview_rgb=preview_rgb,
            )
        )

    def _extract_keyframe_visuals(self, mast3r_frame: Any) -> tuple[np.ndarray | None, np.ndarray | None, int]:
        """Return camera-local RDF pointmap, preview image, and valid point count."""
        try:
            x_canon = mast3r_frame.X_canon
            confidence_avg = mast3r_frame.get_average_conf()
            if x_canon is None or confidence_avg is None or mast3r_frame.img_shape is None:
                return None, None, 0
            shape_values = mast3r_frame.img_shape.flatten().tolist()
            if len(shape_values) < 2:
                return None, None, 0
            height_px, width_px = int(shape_values[0]), int(shape_values[1])
            points_camera = x_canon.detach().cpu().numpy().astype(np.float32).reshape(height_px, width_px, 3)
            preview_rgb = None if mast3r_frame.uimg is None else _normalize_preview_rgb(mast3r_frame.uimg)
            confidence = confidence_avg.detach().cpu().numpy().reshape(-1)
            valid_count = int(np.count_nonzero(confidence > self._cfg.c_conf_threshold))
            return points_camera, preview_rgb, valid_count
        except Exception as exc:
            self._console.warning("MASt3R keyframe visualization extraction failed: %s", exc)
            return None, None, 0

    def _frame_transform_from_sim3(self, T_world_camera: Any) -> FrameTransform:
        """Convert upstream Sim3 pose to repo ``world <- camera_rdf`` semantics."""
        se3 = self._as_SE3(T_world_camera)
        matrix = se3.matrix()[0].detach().cpu().numpy().astype(np.float64)
        return FrameTransform.from_matrix(matrix, target_frame="world", source_frame=CAMERA_RDF_FRAME)

    def _resolve_path(self, path: Path) -> Path:
        """Resolve a repo-relative MASt3R path against the injected path config."""
        return self._path_config.resolve_repo_path(path)

    def _start_backend_thread(self) -> None:
        """Start upstream backend optimization after shared state is ready."""
        self._backend_thread = threading.Thread(
            target=self._run_upstream_backend,
            name="mast3r-backend",
            daemon=True,
        )
        self._backend_thread.start()

    def _run_upstream_backend(self) -> None:
        """Run upstream ``main.run_backend`` while adapting the retriever path."""
        upstream_main: ModuleType | None = None
        original_load_retriever: Any | None = None

        try:
            if self._upstream_main is None:
                raise RuntimeError("MASt3R upstream main module was not loaded.")
            upstream_main = self._upstream_main
            original_load_retriever = upstream_main.load_retriever

            def _load_retriever(model: Any) -> Any:
                return original_load_retriever(
                    model,
                    retriever_path=str(self._resolve_path(self._cfg.retrieval_checkpoint_path)),
                    device=self._device,
                )

            upstream_main.load_retriever = _load_retriever
            upstream_main.run_backend(self._mast3r_cfg, self._model, self._states, self._keyframes, self._K)
        except Exception as exc:
            backend_error = RuntimeError(f"MASt3R backend loop failed: {exc}")
            backend_error.__cause__ = exc
            self._backend_error = backend_error
            self._console.error("MASt3R backend loop error: %s", exc)
        finally:
            if upstream_main is not None and original_load_retriever is not None:
                upstream_main.load_retriever = original_load_retriever

    def _raise_if_backend_failed(self) -> None:
        if self._backend_error is not None:
            raise self._backend_error

    def _join_backend_thread(self) -> None:
        if self._backend_thread is None:
            return
        self._backend_thread.join(timeout=_BACKEND_JOIN_TIMEOUT_S)
        if self._backend_thread.is_alive():
            self._console.error("MASt3R backend thread did not stop within timeout.")

    def _inject_sys_path(self) -> None:
        """Make upstream MASt3R and embedded third-party packages importable."""
        mast3r_root = self._resolve_path(self._cfg.mast3r_slam_dir)
        import_roots = [
            mast3r_root,
            mast3r_root / "thirdparty" / "mast3r",
            mast3r_root / "thirdparty" / "mast3r" / "dust3r",
            mast3r_root / "thirdparty" / "in3d",
        ]
        for import_root in reversed(import_roots):
            import_path = str(import_root)
            if import_path not in sys.path:
                sys.path.insert(0, import_path)

    def _validate_prerequisites(self) -> None:
        """Fail early with actionable diagnostics for missing external assets."""
        missing: list[str] = []
        mast3r_dir = self._resolve_path(self._cfg.mast3r_slam_dir)
        if not (mast3r_dir / "mast3r_slam").exists():
            missing.append(
                f"MASt3R-SLAM submodule not populated at '{mast3r_dir}'. Run: git submodule update --init --recursive"
            )
        for label, path in (
            ("MASt3R backbone checkpoint", self._cfg.checkpoint_path),
            ("MASt3R retrieval checkpoint", self._cfg.retrieval_checkpoint_path),
            ("MASt3R YAML config", self._cfg.yaml_config_path),
        ):
            resolved = self._resolve_path(path)
            if not resolved.exists():
                missing.append(f"{label} missing at '{resolved}'.")

        try:
            import mast3r_slam
            import mast3r_slam_backends

            del mast3r_slam, mast3r_slam_backends
        except ImportError as exc:
            missing.append(
                "MASt3R-SLAM Python package or C++/CUDA extension is not importable. "
                "Install the upstream checkout editable with: "
                "`uv pip install --no-build-isolation -e external/mast3r-slam/thirdparty/mast3r "
                "-e external/mast3r-slam/thirdparty/in3d -e external/mast3r-slam`; "
                "the embedded Dust3R package must also be importable from "
                "`external/mast3r-slam/thirdparty/mast3r/dust3r`. "
                f"Inner error: {exc}"
            )

        if missing:
            raise RuntimeError(
                "MASt3R-SLAM prerequisites not satisfied:\n" + "\n".join(f"  - {item}" for item in missing)
            )


class Mast3rSlamBackend(SlamBackend):
    """MASt3R-SLAM backend implementing current offline and streaming contracts."""

    method_id: MethodId = MethodId.MAST3R

    def __init__(
        self,
        config: Mast3rSlamBackendConfig,
        path_config: PathConfig | None = None,
    ) -> None:
        self._cfg = config
        self._path_config = PathConfig() if path_config is None else path_config
        self._console = Console(__name__).child(self.__class__.__name__)
        self._streaming_session: _Mast3rSlamSession | None = None

    def start_streaming(
        self,
        sequence_manifest: SequenceManifest,
        benchmark_inputs: PreparedBenchmarkInputs | None,
        baseline_source: ReferenceSource,
        backend_config: SlamBackendConfig,
        output_policy: SlamOutputPolicy,
        artifact_root: Path,
    ) -> None:
        """Create backend-owned streaming state before observations arrive."""
        del sequence_manifest, benchmark_inputs, baseline_source, backend_config
        self._streaming_session = _Mast3rSlamSession(
            cfg=self._cfg,
            output_policy=output_policy,
            artifact_root=artifact_root,
            path_config=self._path_config,
            console=self._console,
        )

    def step_streaming(self, frame: Observation) -> None:
        """Consume one streaming observation through the active session."""
        self._require_streaming_session().step(frame)

    def drain_streaming_updates(self) -> list[SlamUpdate]:
        """Return pending MASt3R live updates without exposing session state."""
        return self._require_streaming_session().try_get_updates()

    def finish_streaming(self) -> SlamArtifacts:
        """Finalize the active streaming session and return durable artifacts."""
        session = self._require_streaming_session()
        try:
            return session.close()
        finally:
            self._streaming_session = None

    def run_observations(
        self,
        observations: Iterable[Observation],
        benchmark_inputs: PreparedBenchmarkInputs | None,
        baseline_source: ReferenceSource,
        backend_config: SlamBackendConfig,
        output_policy: SlamOutputPolicy,
        artifact_root: Path,
    ) -> SlamArtifacts:
        """Run MASt3R-SLAM over normalized offline observations."""
        del benchmark_inputs, baseline_source
        session = _Mast3rSlamSession(
            cfg=self._cfg,
            output_policy=output_policy,
            artifact_root=artifact_root,
            path_config=self._path_config,
            console=self._console,
        )
        try:
            for frame_count, observation in enumerate(observations, start=1):
                if backend_config.max_frames is not None and frame_count > backend_config.max_frames:
                    break
                session.step(observation)
            return session.close()
        except Exception:
            session.abort()
            raise

    def _require_streaming_session(self) -> _Mast3rSlamSession:
        if self._streaming_session is None:
            raise RuntimeError("MASt3R-SLAM streaming backend has not been started.")
        return self._streaming_session


def _load_upstream_main_module(mast3r_root: Path) -> ModuleType:
    """Load upstream ``main.py`` as an internal module so its entry points are reusable."""
    module_name = "_prml_vslam_mast3r_slam_upstream_main"
    cached = sys.modules.get(module_name)
    if isinstance(cached, ModuleType):
        return cached
    main_path = mast3r_root / "main.py"
    if not main_path.exists():
        raise RuntimeError(f"MASt3R-SLAM upstream main.py is missing at '{main_path}'.")
    spec = importlib.util.spec_from_file_location(module_name, main_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load MASt3R-SLAM upstream main.py from '{main_path}'.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _normalize_preview_rgb(payload: Any) -> np.ndarray:
    """Normalize upstream preview payloads to ``H x W x 3`` uint8 RGB."""
    if isinstance(payload, np.ndarray):
        preview = np.asarray(payload)
    else:
        preview = payload.detach().cpu().numpy()
    while preview.ndim > 3 and preview.shape[0] == 1:
        preview = preview[0]
    if preview.ndim != 3:
        raise ValueError(f"Expected preview RGB shape HxWx3 or 3xHxW, got {preview.shape}.")
    if preview.shape[0] == 3 and preview.shape[-1] != 3:
        preview = np.transpose(preview, (1, 2, 0))
    if preview.shape[-1] != 3:
        raise ValueError(f"Expected preview RGB to have 3 channels, got shape {preview.shape}.")
    if np.issubdtype(preview.dtype, np.floating):
        finite_preview = np.nan_to_num(preview, nan=0.0, posinf=255.0, neginf=0.0)
        if finite_preview.size and float(np.nanmax(finite_preview)) <= 1.0:
            finite_preview = finite_preview * 255.0
        return np.clip(finite_preview, 0.0, 255.0).astype(np.uint8)
    return np.clip(preview, 0, 255).astype(np.uint8)


def _build_artifacts(
    *,
    native_output_dir: Path,
    artifact_root: Path,
    output_policy: SlamOutputPolicy,
    traj_native: Path,
    ply_native: Path | None,
) -> SlamArtifacts:
    """Normalize native MASt3R outputs into repository-owned artifacts."""
    if not traj_native.exists():
        raise RuntimeError(f"Expected MASt3R trajectory file not found: '{traj_native}'.")

    run_paths = RunArtifactPaths.build(artifact_root)
    canonical_traj = run_paths.trajectory_path
    canonical_traj.parent.mkdir(parents=True, exist_ok=True)
    if canonical_traj.resolve() != traj_native.resolve():
        canonical_traj.write_bytes(traj_native.read_bytes())

    dense_ref = None
    if output_policy.emit_dense_points and ply_native is not None and ply_native.exists():
        canonical_ply = run_paths.dense_points_path
        canonical_ply.parent.mkdir(parents=True, exist_ok=True)
        if canonical_ply.resolve() != ply_native.resolve():
            canonical_ply.write_bytes(ply_native.read_bytes())
        dense_ref = artifact_ref(canonical_ply, kind="ply")

    extras = {
        path.name: artifact_ref(path, kind=path.suffix.lstrip(".") or "file")
        for path in sorted(native_output_dir.iterdir())
        if path.is_file() and path not in {traj_native, ply_native}
    }
    return SlamArtifacts(
        trajectory_tum=artifact_ref(canonical_traj, kind="tum"),
        sparse_points_ply=None,
        dense_points_ply=dense_ref,
        extras=extras,
    )


__all__ = ["Mast3rSlamBackend"]
