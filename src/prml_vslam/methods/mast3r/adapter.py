"""Canonical MASt3R-SLAM backend adapter (offline + streaming).

This adapter wraps the upstream MASt3R-SLAM codebase located under
``external/mast3r-slam`` and exposes the :class:`SlamBackend` protocol so the
repository pipeline (offline + streaming + Streamlit) can drive it.

Architecture (mirrors :class:`prml_vslam.methods.vista.adapter.VistaSlamBackend`):

- :class:`Mast3rSlamBackend` implements both :meth:`run_observations` (offline,
  normalized observations) and the streaming lifecycle
  (:meth:`start_streaming`, :meth:`step_streaming`,
  :meth:`drain_streaming_updates`, :meth:`finish_streaming`).
- :class:`Mast3rSlamSession` runs MASt3R's front-end (FrameTracker FSM) on the
  calling thread and spawns a background *thread* that runs MASt3R's back-end
  loop (FactorGraph local optimisation + retrieval loop closure). The two
  threads share ``SharedKeyframes`` / ``SharedStates`` which already carry
  their own locks upstream.
- The runtime stays in-process; we never spawn a child process. MASt3R
  internally uses :func:`mp.Manager` for shared state, but :class:`mp.Manager`
  itself spawns a helper subprocess and is forbidden from daemonic workers
  (e.g. Ray actors). :class:`_InProcessManager` is a drop-in replacement that
  satisfies the upstream API surface without spawning anything.
"""

from __future__ import annotations

import sys
import threading
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np

from prml_vslam.interfaces import (
    CameraIntrinsics,
    CameraIntrinsicsSample,
    CameraIntrinsicsSeries,
    FrameTransform,
    Observation,
)
from prml_vslam.interfaces.artifacts import ArtifactRef
from prml_vslam.interfaces.slam import SlamArtifacts
from prml_vslam.methods.contracts import SlamUpdate
from prml_vslam.methods.protocols import SlamBackend
from prml_vslam.methods.stage.backend_config import (
    Mast3rSlamBackendConfig,
    MethodId,
    SlamBackendConfig,
    SlamOutputPolicy,
)
from prml_vslam.sources.contracts import PreparedBenchmarkInputs, ReferenceSource, SequenceManifest
from prml_vslam.utils import Console, PathConfig, RunArtifactPaths

# ---------------------------------------------------------------------------
# In-process manager shim.
#
# MASt3R upstream uses mp.Manager() for SharedKeyframes / SharedStates.
# mp.Manager() itself spawns a helper subprocess and is forbidden from any
# daemonic worker context (Ray actors etc.). We run MASt3R in-process, so
# threading primitives are sufficient. This shim matches the small subset of
# the Manager API that upstream SharedKeyframes / SharedStates actually call.
# ---------------------------------------------------------------------------


class _InProcessValue:
    """Stand-in for :class:`mp.Manager().Value` without a helper subprocess."""

    __slots__ = ("value",)

    def __init__(self, typecode: str, initial: Any) -> None:  # noqa: ARG002
        self.value = initial


class _InProcessManager:
    """Drop-in substitute for :func:`mp.Manager` usable from daemonic workers."""

    def RLock(self) -> threading.RLock:  # noqa: N802 — match mp.Manager API
        return threading.RLock()

    def Value(self, typecode: str, initial: Any) -> _InProcessValue:  # noqa: N802
        return _InProcessValue(typecode, initial)

    def list(self) -> list[Any]:  # noqa: A003
        return []


def _ensure_uint8_rgb_from_uimg(uimg: Any) -> np.ndarray | None:
    """Convert MASt3R's ``uimg`` (H×W×3 float32 in [0,1]) to canonical uint8 RGB.

    Returns None if the tensor is missing or has an unexpected shape. The
    visualization stage uses this both as the camera image AND as per-point
    colors on the camera-local pointmap; correct dtype/shape are required for
    log_pointcloud's ``len(colors) == len(positions)`` check to pass.
    """
    if uimg is None:
        return None
    try:
        arr = uimg.detach().cpu().numpy()
    except AttributeError:
        arr = np.asarray(uimg)
    if arr.ndim != 3 or arr.shape[-1] != 3:
        return None
    if arr.dtype != np.uint8:
        arr = (arr * 255.0).clip(0, 255).astype(np.uint8)
    return np.ascontiguousarray(arr)


def _silence_upstream_warnings() -> None:
    """Filter known-benign third-party warnings emitted by MASt3R-SLAM and torch.

    These originate in upstream code we do not own (legacy
    ``torch.load(weights_only=False)`` at model load and a non-writable
    NumPy->tensor view during inference) and otherwise flood the run console.
    """
    import warnings  # noqa: PLC0415

    warnings.filterwarnings("ignore", message=r".*weights_only=False.*", category=FutureWarning)
    warnings.filterwarnings("ignore", message=r".*NumPy array is not writable.*", category=UserWarning)


def _estimate_camera_intrinsics_from_frame(mast3r_frame: Any) -> CameraIntrinsics | None:
    """Estimate model-raster intrinsics from a MASt3R keyframe pointmap."""
    import torch  # noqa: PLC0415
    from dust3r.post_process import estimate_focal_knowing_depth  # noqa: PLC0415

    x_canon = getattr(mast3r_frame, "X_canon", None)
    img_shape = getattr(mast3r_frame, "img_shape", None)
    if x_canon is None or img_shape is None:
        return None
    height_px, width_px = (int(value) for value in img_shape.flatten().tolist()[:2])
    if height_px <= 0 or width_px <= 0:
        return None

    points = x_canon.detach().reshape(height_px, width_px, 3)
    principal_point = torch.tensor([width_px / 2.0, height_px / 2.0], device=points.device, dtype=points.dtype)
    focal = estimate_focal_knowing_depth(
        points[None],
        principal_point,
        focal_mode="weiszfeld",
        min_focal=0.5,
        max_focal=3.5,
    ).reshape(-1)[0]
    focal_value = float(focal.detach().cpu().item())
    if not np.isfinite(focal_value) or focal_value <= 0.0:
        return None
    return CameraIntrinsics(
        fx=focal_value,
        fy=focal_value,
        cx=width_px / 2.0,
        cy=height_px / 2.0,
        width_px=width_px,
        height_px=height_px,
    )


# ---------------------------------------------------------------------------
# Session: wraps the upstream FrameTracker FSM + background FactorGraph loop.
# ---------------------------------------------------------------------------


class Mast3rSlamSession:
    """Stateful streaming runtime over the upstream MASt3R-SLAM stack."""

    def __init__(
        self,
        *,
        cfg: Mast3rSlamBackendConfig,
        path_config: PathConfig,
        output_policy: SlamOutputPolicy,
        artifact_root: Path,
        console: Console,
    ) -> None:
        self._cfg = cfg
        self._path_config = path_config
        self._output_policy = output_policy
        self._artifact_root = artifact_root
        self._console = console.child("Mast3rSlamSession")

        # Lazy-loaded upstream handles (populated by _initialize below).
        self._device: str = cfg.device
        self._img_size: int = cfg.img_size
        self._model: Any = None
        self._keyframes: Any = None
        self._states: Any = None
        self._tracker: Any = None
        self._manager: Any = None
        self._K: Any = None  # torch.Tensor | None
        self._h: int = 0
        self._w: int = 0
        self._lietorch: Any = None
        self._Mode: Any = None
        self._create_frame: Any = None
        self._resize_img: Any = None
        self._SharedKeyframes: Any = None
        self._SharedStates: Any = None
        self._FrameTracker: Any = None
        self._mast3r_inference_mono: Any = None

        # Frontend bookkeeping.
        self._source_frame_count = 0
        self._accepted_keyframe_count = 0
        self._num_dense_points = 0
        # Indexed by internal frame_id (= step call order).
        self._timestamps_s: list[float] = []
        self._pending_updates: list[SlamUpdate] = []
        self._estimated_intrinsics_samples: list[CameraIntrinsicsSample] = []
        self._backend_error: Exception | None = None

        # Backend thread control.
        self._backend_thread: threading.Thread | None = None
        self._backend_stop = threading.Event()

        self._initialize()

    # ---- initialisation -------------------------------------------------

    def _initialize(self) -> None:
        """Load the upstream runtime and model state needed before the first frame."""
        import torch  # noqa: PLC0415

        _silence_upstream_warnings()
        self._inject_sys_path()
        self._validate_prerequisites()

        # Upstream config is a GLOBAL dict — load it in this process first so
        # every imported mast3r_slam module sees the correct values.
        from mast3r_slam.config import load_config  # noqa: PLC0415

        load_config(str(self._resolve_path(self._cfg.yaml_config_path)))
        from mast3r_slam.config import config as mast3r_cfg  # noqa: PLC0415

        # Apply optional overrides before any downstream module reads the global config.
        if self._cfg.use_calib is not None:
            mast3r_cfg["use_calib"] = bool(self._cfg.use_calib)
        if self._cfg.match_frac_thresh is not None:
            if "tracking" not in mast3r_cfg:
                raise RuntimeError(
                    "Cannot override match_frac_thresh: the MASt3R YAML config has no `tracking` section."
                )
            mast3r_cfg["tracking"]["match_frac_thresh"] = float(self._cfg.match_frac_thresh)

        torch.backends.cuda.matmul.allow_tf32 = True
        torch.set_grad_enabled(False)

        import lietorch  # noqa: PLC0415
        from mast3r_slam.frame import Mode, SharedKeyframes, SharedStates, create_frame  # noqa: PLC0415
        from mast3r_slam.mast3r_utils import load_mast3r, mast3r_inference_mono, resize_img  # noqa: PLC0415
        from mast3r_slam.tracker import FrameTracker  # noqa: PLC0415

        checkpoint = str(self._resolve_path(self._cfg.checkpoint_path))
        self._console.info("Loading MASt3R model from '%s'...", checkpoint)
        self._model = load_mast3r(path=checkpoint, device=self._device)
        # NOTE: Upstream calls self._model.share_memory() here for the subprocess
        # backend setup. We run in-process so this is unnecessary and only
        # triggers extra CPU↔GPU allocations on some torch versions.
        self._lietorch = lietorch
        self._Mode = Mode
        self._create_frame = create_frame
        self._resize_img = resize_img
        self._SharedKeyframes = SharedKeyframes
        self._SharedStates = SharedStates
        self._FrameTracker = FrameTracker
        self._mast3r_inference_mono = mast3r_inference_mono

    # ---- streaming step -------------------------------------------------

    def step(self, frame: Observation) -> None:
        """Feed one observation to MASt3R and emit an incremental SlamUpdate."""
        self._raise_if_backend_failed()
        if frame.rgb is None:
            self._emit_empty_update(frame)
            return

        if self._keyframes is None:
            # Probe the actual output size from the first frame.
            img_f32_dummy = frame.rgb.astype(np.float32) / 255.0
            probe = self._resize_img(img_f32_dummy, self._img_size)
            self._h, self._w = int(probe["img"].shape[2]), int(probe["img"].shape[3])

            # Build shared state buffers and tracker with the correct dimensions.
            self._manager = _InProcessManager()
            self._keyframes = self._SharedKeyframes(
                self._manager, self._h, self._w, buffer=self._cfg.keyframe_buffer_size, device=self._device
            )
            self._states = self._SharedStates(self._manager, self._h, self._w, device=self._device)
            self._tracker = self._FrameTracker(self._model, self._keyframes, self._device)
            self._console.info(
                "MASt3R initialized with dynamic size: %dx%d (keyframe buffer=%d)",
                self._h,
                self._w,
                self._cfg.keyframe_buffer_size,
            )

        internal_idx = self._source_frame_count
        self._timestamps_s.append(frame.timestamp_ns / 1e9)

        # If we're configured for use_calib and we haven't set K yet, grab it
        # from the observation. We compute K_frame on first use (scaled
        # intrinsics for the resized MASt3R image).
        self._maybe_set_intrinsics(frame)
        if self._backend_thread is None:
            self._start_backend_thread()

        # uint8 RGB H×W×3 → float32 [0,1] (what mast3r_slam.frame.create_frame expects).
        img_f32 = frame.rgb.astype(np.float32) / 255.0

        # Prior pose for this frame: last tracked frame's pose, or identity for the very first.
        if internal_idx == 0:
            T_WC = self._lietorch.Sim3.Identity(1, device=self._device)
        else:
            prev = self._states.get_frame()
            T_WC = prev.T_WC

        mast3r_frame = self._create_frame(internal_idx, img_f32, T_WC, img_size=self._img_size, device=self._device)

        mode = self._states.get_mode()
        is_keyframe = False
        keyframe_index: int | None = None
        pose_updated = False

        if mode == self._Mode.INIT:
            X_init, C_init = self._mast3r_inference_mono(self._model, mast3r_frame)
            mast3r_frame.update_pointmap(X_init, C_init)
            self._keyframes.append(mast3r_frame)
            self._states.queue_global_optimization(len(self._keyframes) - 1)
            self._states.set_mode(self._Mode.TRACKING)
            self._states.set_frame(mast3r_frame)
            is_keyframe = True
            keyframe_index = len(self._keyframes) - 1
            self._accepted_keyframe_count = 1
            pose_updated = True

        elif mode == self._Mode.TRACKING:
            add_new_kf, _match_info, try_reloc = self._tracker.track(mast3r_frame)
            if try_reloc:
                self._states.set_mode(self._Mode.RELOC)
            self._states.set_frame(mast3r_frame)
            pose_updated = True  # tracker.track updates mast3r_frame.T_WC in place
            if add_new_kf:
                self._keyframes.append(mast3r_frame)
                self._states.queue_global_optimization(len(self._keyframes) - 1)
                is_keyframe = True
                keyframe_index = len(self._keyframes) - 1
                self._accepted_keyframe_count += 1

        elif mode == self._Mode.RELOC:
            X, C = self._mast3r_inference_mono(self._model, mast3r_frame)
            mast3r_frame.update_pointmap(X, C)
            self._states.set_frame(mast3r_frame)
            self._states.queue_reloc()
            pose_updated = False  # reloc handled async by backend thread

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

    def drain_updates(self) -> list[SlamUpdate]:
        """Return and clear any pending SLAM updates."""
        self._raise_if_backend_failed()
        updates = self._pending_updates
        self._pending_updates = []
        return updates

    def finish(self) -> SlamArtifacts:
        """Stop the backend thread, persist artifacts, and return them canonical."""
        from mast3r_slam.frame import Mode  # noqa: PLC0415

        if self._states is None or self._keyframes is None:
            raise RuntimeError("MASt3R-SLAM finish() called before processing any RGB frames.")
        self._raise_if_backend_failed()

        # Signal backend to stop and drain any in-flight optimisation.
        self._states.set_mode(Mode.TERMINATED)
        self._backend_stop.set()
        self._join_backend_thread()

        # Write native artifacts + return canonical SlamArtifacts.
        run_paths = RunArtifactPaths.build(self._artifact_root)
        native_output_dir = run_paths.native_output_dir
        native_output_dir.mkdir(parents=True, exist_ok=True)

        seq_name = "mast3r"
        traj_native = native_output_dir / f"{seq_name}.txt"
        ply_native = native_output_dir / f"{seq_name}.ply"

        from mast3r_slam.evaluate import save_reconstruction, save_traj  # noqa: PLC0415

        try:
            save_traj(
                native_output_dir,
                f"{seq_name}.txt",
                self._timestamps_s,
                self._keyframes,
                intrinsics=None,  # upstream Intrinsics object; we skip refine-with-calib for now
            )
        except Exception as exc:
            raise RuntimeError(
                f"MASt3R-SLAM failed to export trajectory. "
                f"The sequence ({self._source_frame_count} frames, "
                f"{self._accepted_keyframe_count} keyframes) may have been too short."
            ) from exc

        ply_written = False
        if self._output_policy.emit_dense_points or self._output_policy.emit_sparse_points:
            try:
                save_reconstruction(
                    native_output_dir,
                    f"{seq_name}.ply",
                    self._keyframes,
                    self._cfg.c_conf_threshold,
                )
                ply_written = ply_native.exists()
            except Exception as exc:
                if self._output_policy.emit_dense_points:
                    raise RuntimeError("MASt3R-SLAM failed to export the requested dense point cloud.") from exc
                self._console.warn("MASt3R-SLAM reconstruction export failed: %s (trajectory still saved).", exc)
            if self._output_policy.emit_dense_points and not ply_written:
                raise RuntimeError(f"MASt3R-SLAM did not create the requested dense point cloud: '{ply_native}'.")

        self._console.info(
            "MASt3R-SLAM session closed after %d frames, %d keyframes. Native outputs in '%s'.",
            self._source_frame_count,
            self._accepted_keyframe_count,
            native_output_dir,
        )
        estimated_intrinsics = self._build_estimated_intrinsics_series()
        return _build_artifacts(
            native_output_dir=native_output_dir,
            artifact_root=self._artifact_root,
            output_policy=self._output_policy,
            traj_native=traj_native,
            ply_native=ply_native if ply_written else None,
            n_keyframes=self._accepted_keyframe_count,
            n_processed_frames=self._source_frame_count,
            n_dense_points=self._num_dense_points,
            estimated_intrinsics=estimated_intrinsics,
        )

    def stop_backend_thread(self) -> None:
        """Best-effort stop of the backend optimisation thread."""
        if self._states is None:
            return
        self._backend_stop.set()
        self._join_backend_thread()

    # ---- backend thread -------------------------------------------------

    def _backend_loop(self) -> None:
        """Run upstream ``run_backend`` logic inside this process as a thread."""
        from mast3r_slam.config import config as mast3r_cfg  # noqa: PLC0415
        from mast3r_slam.frame import Mode  # noqa: PLC0415
        from mast3r_slam.global_opt import FactorGraph  # noqa: PLC0415
        from mast3r_slam.mast3r_utils import load_retriever  # noqa: PLC0415

        factor_graph = FactorGraph(self._model, self._keyframes, self._K, self._device)
        retriever_path = str(self._resolve_path(self._cfg.retrieval_checkpoint_path))
        retrieval_database = load_retriever(self._model, retriever_path=retriever_path, device=self._device)

        use_calib = bool(mast3r_cfg.get("use_calib", False))
        poll = self._cfg.backend_poll_interval_s

        while not self._backend_stop.is_set():
            try:
                mode = self._states.get_mode()
                if mode == Mode.TERMINATED:
                    break
                if mode == Mode.INIT or self._states.is_paused():
                    time.sleep(poll)
                    continue

                if mode == Mode.RELOC:
                    frame = self._states.get_frame()
                    success = self._relocalization(frame, factor_graph, retrieval_database, use_calib)
                    if success:
                        self._states.set_mode(Mode.TRACKING)
                    self._states.dequeue_reloc()
                    continue

                # Pick up a pending global-optimisation task.
                idx = -1
                with self._states.lock:
                    if len(self._states.global_optimizer_tasks) > 0:
                        idx = self._states.global_optimizer_tasks[0]
                if idx == -1:
                    time.sleep(poll)
                    continue

                # Build local graph: link to previous keyframe + retrieval candidates.
                kf_idx: list[int] = []
                n_consec = 1
                for j in range(min(n_consec, idx)):
                    kf_idx.append(idx - 1 - j)
                frame = self._keyframes[idx]
                retrieval_inds = retrieval_database.update(
                    frame,
                    add_after_query=True,
                    k=mast3r_cfg["retrieval"]["k"],
                    min_thresh=mast3r_cfg["retrieval"]["min_thresh"],
                )
                kf_idx += retrieval_inds

                kf_idx_set = set(kf_idx)
                kf_idx_set.discard(idx)
                kf_idx_list = list(kf_idx_set)
                frame_idx = [idx] * len(kf_idx_list)
                if kf_idx_list:
                    factor_graph.add_factors(kf_idx_list, frame_idx, mast3r_cfg["local_opt"]["min_match_frac"])

                with self._states.lock:
                    self._states.edges_ii[:] = factor_graph.ii.cpu().tolist()
                    self._states.edges_jj[:] = factor_graph.jj.cpu().tolist()

                if use_calib:
                    factor_graph.solve_GN_calib()
                else:
                    factor_graph.solve_GN_rays()

                with self._states.lock:
                    if len(self._states.global_optimizer_tasks) > 0:
                        self._states.global_optimizer_tasks.pop(0)

            except Exception as exc:  # pragma: no cover - defensive
                backend_error = RuntimeError(f"MASt3R backend loop failed: {exc}")
                backend_error.__cause__ = exc
                self._backend_error = backend_error
                self._console.error("MASt3R backend loop error: %s", exc)
                self._backend_stop.set()
                break

    def _relocalization(self, frame: Any, factor_graph: Any, retrieval_database: Any, use_calib: bool) -> bool:
        """Port of upstream ``relocalization`` — shares SharedKeyframes with frontend."""
        from mast3r_slam.config import config as mast3r_cfg  # noqa: PLC0415

        with self._keyframes.lock:
            retrieval_inds = retrieval_database.update(
                frame,
                add_after_query=False,
                k=mast3r_cfg["retrieval"]["k"],
                min_thresh=mast3r_cfg["retrieval"]["min_thresh"],
            )
            kf_idx = list(retrieval_inds)
            success = False
            if kf_idx:
                self._keyframes.append(frame)
                n_kf = len(self._keyframes)
                frame_idx = [n_kf - 1] * len(kf_idx)
                if factor_graph.add_factors(
                    frame_idx,
                    kf_idx,
                    mast3r_cfg["reloc"]["min_match_frac"],
                    is_reloc=mast3r_cfg["reloc"]["strict"],
                ):
                    retrieval_database.update(
                        frame,
                        add_after_query=True,
                        k=mast3r_cfg["retrieval"]["k"],
                        min_thresh=mast3r_cfg["retrieval"]["min_thresh"],
                    )
                    success = True
                    self._keyframes.T_WC[n_kf - 1] = self._keyframes.T_WC[kf_idx[0]].clone()
                else:
                    self._keyframes.pop_last()
            if success:
                if use_calib:
                    factor_graph.solve_GN_calib()
                else:
                    factor_graph.solve_GN_rays()
            return success

    # ---- helpers --------------------------------------------------------

    def _maybe_set_intrinsics(self, frame: Observation) -> None:
        """First-frame path to populate K from the observation when use_calib is active.

        This MUST run before the first keyframe is appended — otherwise
        SharedKeyframes.__getitem__ has already baked None into the kf.K field
        of that keyframe via the config["use_calib"] lookup.
        """
        from mast3r_slam.config import config as mast3r_cfg  # noqa: PLC0415

        if not mast3r_cfg.get("use_calib", False):
            return
        if self._K is not None:
            return
        if frame.intrinsics is None:
            raise RuntimeError(
                "MASt3R use_calib=True but Observation.intrinsics is None. "
                "Either provide intrinsics in the Observation or set "
                "Mast3rSlamBackendConfig.use_calib=False."
            )
        # Build the K_frame (intrinsics rescaled to the resized-encoder image)
        # using the same recipe as upstream dataloader.Intrinsics.
        from mast3r_slam.dataloader import Intrinsics  # noqa: PLC0415

        w_raw = frame.intrinsics.width_px or frame.rgb.shape[1]
        h_raw = frame.intrinsics.height_px or frame.rgb.shape[0]
        intrinsics_obj = Intrinsics.from_calib(
            self._img_size,
            w_raw,
            h_raw,
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

        import torch  # noqa: PLC0415

        self._K = torch.from_numpy(intrinsics_obj.K_frame).to(self._device, dtype=torch.float32)
        self._keyframes.set_intrinsics(self._K)

    def _emit_empty_update(self, frame: Observation) -> None:
        """Emit a no-op update for an observation without RGB payload."""
        self._pending_updates.append(
            SlamUpdate(
                seq=frame.seq,
                timestamp_ns=frame.timestamp_ns,
                source_seq=frame.seq,
                source_timestamp_ns=frame.timestamp_ns,
                is_keyframe=False,
                keyframe_index=None,
                num_dense_points=self._num_dense_points,
            )
        )

    def _emit_update(
        self,
        *,
        frame: Observation,
        mast3r_frame: Any,
        is_keyframe: bool,
        keyframe_index: int | None,
        pose_updated: bool,
    ) -> None:
        """Translate the current MASt3R frame state into a canonical SlamUpdate."""
        pose = self._frame_transform_from_sim3(mast3r_frame.T_WC) if pose_updated else None

        pointmap: np.ndarray | None = None
        added_points = 0

        if is_keyframe and self._output_policy.emit_dense_points:
            pointmap, added_points = self._extract_keyframe_pointmap(mast3r_frame)
            self._num_dense_points += added_points

        camera_intrinsics = None
        if is_keyframe and keyframe_index is not None:
            camera_intrinsics = _estimate_camera_intrinsics_from_frame(mast3r_frame)
            if camera_intrinsics is not None:
                self._estimated_intrinsics_samples.append(
                    CameraIntrinsicsSample(
                        index=len(self._estimated_intrinsics_samples),
                        keyframe_index=keyframe_index,
                        timestamp_ns=frame.timestamp_ns,
                        intrinsics=camera_intrinsics,
                    )
                )

        # MASt3R holds the resized RGB raster for every tracked frame in
        # mast3r_frame.uimg (H × W × 3, float [0,1]). We expose it as
        # SlamUpdate.image_rgb so the visualization stage can use it both as
        # the camera image AND as per-point colors for the camera-local
        # pointmap. Crucially, image_rgb shape matches pointmap shape so
        # log_pointcloud's "len(colors) == len(positions)" check passes.
        image_rgb = _ensure_uint8_rgb_from_uimg(mast3r_frame.uimg)

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
                image_rgb=image_rgb,
                pointmap=pointmap,
                camera_intrinsics=camera_intrinsics,
            )
        )

    def _build_estimated_intrinsics_series(self) -> CameraIntrinsicsSeries | None:
        """Build the terminal keyframe intrinsics series collected during tracking."""
        if not self._estimated_intrinsics_samples:
            return None
        first_intrinsics = self._estimated_intrinsics_samples[0].intrinsics
        return CameraIntrinsicsSeries(
            raster_space="mast3r_model",
            source="mast3r_slam.X_canon:focal_from_depth",
            method_id="mast3r",
            width_px=first_intrinsics.width_px,
            height_px=first_intrinsics.height_px,
            samples=self._estimated_intrinsics_samples,
            metadata={
                "estimator": "dust3r.post_process.estimate_focal_knowing_depth",
                "focal_mode": "weiszfeld",
                "min_focal": 0.5,
                "max_focal": 3.5,
                "principal_point": "center_assumed",
            },
        )

    def _extract_keyframe_pointmap(self, mast3r_frame: Any) -> tuple[np.ndarray | None, int]:
        """Pull the camera-local RDF pointmap and count its valid samples."""
        try:
            x_canon = mast3r_frame.X_canon
            c_avg = mast3r_frame.get_average_conf()
            if x_canon is None or c_avg is None:
                return None, 0

            # Reshape source of truth: Frame.img_shape is maintained by
            # create_frame() with the same downsample factor applied to both
            # X_canon and uimg, so it matches both.
            img_shape = mast3r_frame.img_shape
            if img_shape is None:
                return None, 0
            shape_vals = img_shape.flatten().tolist()
            if len(shape_vals) < 2:
                return None, 0
            h, w = int(shape_vals[0]), int(shape_vals[1])

            # X_canon is the per-keyframe camera-local pointmap. Keep it
            # camera-local so SlamUpdate.pointmap remains consistent with the
            # repository contract.
            points_camera = x_canon.detach().cpu().numpy().astype(np.float32).reshape(h, w, 3)

            conf = c_avg.detach().cpu().numpy().reshape(-1)
            valid = int(np.count_nonzero(conf > self._cfg.c_conf_threshold))
            return points_camera, valid
        except Exception:
            return None, 0

    def _frame_transform_from_sim3(self, T_WC: Any) -> FrameTransform:
        """Convert a lietorch.Sim3 pose (what MASt3R tracks) into an SE(3) FrameTransform."""
        from mast3r_slam.lietorch_utils import as_SE3  # noqa: PLC0415

        se3 = as_SE3(T_WC)  # lietorch.SE3 on CPU
        # se3.matrix() -> (B, 4, 4); batch dim is 1.
        matrix = se3.matrix()[0].detach().cpu().numpy().astype(np.float64)
        return FrameTransform.from_matrix(matrix)

    def _resolve_path(self, path: Path) -> Path:
        """Resolve a repo-relative path against the project root."""
        return self._path_config.resolve_repo_path(path)

    def _start_backend_thread(self) -> None:
        """Start the optimization backend after shared state and intrinsics are ready."""
        self._backend_stop.clear()
        self._backend_thread = threading.Thread(target=self._backend_loop, name="mast3r-backend", daemon=True)
        self._backend_thread.start()

    def _raise_if_backend_failed(self) -> None:
        """Raise any deferred backend exception on the frontend thread."""
        if self._backend_error is not None:
            raise self._backend_error

    def _join_backend_thread(self) -> None:
        """Join the backend thread and log if it fails to exit promptly."""
        if self._backend_thread is None:
            return
        self._backend_thread.join(timeout=self._cfg.backend_join_timeout_s)
        if self._backend_thread.is_alive():
            self._console.error("MASt3R backend thread did not stop within timeout.")

    def _inject_sys_path(self) -> None:
        """Make ``mast3r_slam`` importable from this process."""
        mast3r_root = str(self._resolve_path(self._cfg.mast3r_slam_dir))
        if mast3r_root not in sys.path:
            sys.path.insert(0, mast3r_root)

    def _validate_prerequisites(self) -> None:
        """Fail early with actionable diagnostics if upstream assets are missing."""
        missing: list[str] = []
        mast3r_dir = self._resolve_path(self._cfg.mast3r_slam_dir)
        if not (mast3r_dir / "mast3r_slam").exists():
            missing.append(
                f"mast3r-slam submodule not populated at '{mast3r_dir}'. Run: git submodule update --init --recursive"
            )
        checkpoint = self._resolve_path(self._cfg.checkpoint_path)
        if not checkpoint.exists():
            missing.append(
                f"MASt3R backbone checkpoint missing at '{checkpoint}'. "
                "See external/mast3r-slam/README.md — download "
                "MASt3R_ViTLarge_BaseDecoder_512_catmlpdpt_metric.pth."
            )
        retr = self._resolve_path(self._cfg.retrieval_checkpoint_path)
        if not retr.exists():
            missing.append(
                f"MASt3R retrieval checkpoint missing at '{retr}'. "
                "Download MASt3R_ViTLarge_BaseDecoder_512_catmlpdpt_metric_retrieval_trainingfree.pth."
            )
        yaml_cfg = self._resolve_path(self._cfg.yaml_config_path)
        if not yaml_cfg.exists():
            missing.append(f"MASt3R YAML config missing at '{yaml_cfg}'.")

        # Try importing the CUDA extension early — far better to fail here than
        # deep in solve_GN.
        try:
            self._inject_sys_path()
            import mast3r_slam_backends  # noqa: F401, PLC0415
        except ImportError as exc:
            missing.append(
                "C++/CUDA extension 'mast3r_slam_backends' could not be imported. "
                "Run: `cd external/mast3r-slam && pip install -e . --no-build-isolation` "
                f"(after installing the torch/CUDA stack from their README). Inner error: {exc}"
            )

        if missing:
            raise RuntimeError(
                "MASt3R-SLAM prerequisites not satisfied:\n" + "\n".join(f"  • {item}" for item in missing)
            )


# ---------------------------------------------------------------------------
# Backend: offline + streaming entry points (mirrors VistaSlamBackend).
# ---------------------------------------------------------------------------


class Mast3rSlamBackend(SlamBackend):
    """MASt3R-SLAM backend implementing offline and streaming contracts."""

    method_id: MethodId = MethodId.MAST3R

    def __init__(
        self,
        config: Mast3rSlamBackendConfig,
        path_config: PathConfig | None = None,
    ) -> None:
        self._cfg = config
        self._path_config = path_config or PathConfig()
        self._console = Console(__name__).child(self.__class__.__name__)
        self._streaming_session: Mast3rSlamSession | None = None

    def start_streaming(
        self,
        sequence_manifest: SequenceManifest,
        benchmark_inputs: PreparedBenchmarkInputs | None,
        baseline_source: ReferenceSource,
        backend_config: SlamBackendConfig,
        output_policy: SlamOutputPolicy,
        artifact_root: Path,
    ) -> None:
        """Load upstream MASt3R and retain backend-owned streaming state."""
        del sequence_manifest, benchmark_inputs, baseline_source, backend_config
        if output_policy.emit_sparse_points:
            raise ValueError(
                "MASt3R-SLAM does not expose a separate sparse point-cloud artifact; "
                "set `emit_sparse_points=false` for MASt3R runs."
            )
        self._streaming_session = Mast3rSlamSession(
            cfg=self._cfg,
            path_config=self._path_config,
            output_policy=output_policy,
            artifact_root=artifact_root,
            console=self._console,
        )

    def step_streaming(self, frame: Observation) -> None:
        """Consume one streaming observation through the active MASt3R session."""
        self._require_streaming_session().step(frame)

    def drain_streaming_updates(self) -> list[SlamUpdate]:
        """Retrieve pending MASt3R live updates without exposing session state."""
        return self._require_streaming_session().drain_updates()

    def finish_streaming(self) -> SlamArtifacts:
        """Finalize the active MASt3R streaming session and clear it."""
        session = self._require_streaming_session()
        try:
            artifacts = session.finish()
        finally:
            session.stop_backend_thread()
            self._streaming_session = None
        return artifacts

    def run_observations(
        self,
        observations: Iterable[Observation],
        benchmark_inputs: PreparedBenchmarkInputs | None,
        baseline_source: ReferenceSource,
        backend_config: SlamBackendConfig,
        output_policy: SlamOutputPolicy,
        artifact_root: Path,
    ) -> SlamArtifacts:
        """Run MASt3R-SLAM over normalized offline observations and persist artifacts."""
        del benchmark_inputs, baseline_source
        if output_policy.emit_sparse_points:
            raise ValueError(
                "MASt3R-SLAM does not expose a separate sparse point-cloud artifact; "
                "set `emit_sparse_points=false` for MASt3R runs."
            )
        session = Mast3rSlamSession(
            cfg=self._cfg,
            path_config=self._path_config,
            output_policy=output_policy,
            artifact_root=artifact_root,
            console=self._console,
        )
        max_frames = backend_config.max_frames
        self._console.info(
            "Running MASt3R-SLAM on normalized offline observations%s.",
            "" if max_frames is None else f" with max_frames={max_frames}",
        )
        try:
            for frame_count, observation in enumerate(observations, start=1):
                if max_frames is not None and frame_count > max_frames:
                    break
                session.step(observation)
            return session.finish()
        finally:
            session.stop_backend_thread()

    def _require_streaming_session(self) -> Mast3rSlamSession:
        if self._streaming_session is None:
            raise RuntimeError("MASt3R-SLAM streaming backend has not been started.")
        return self._streaming_session


# ---------------------------------------------------------------------------
# Artifact assembly.
# ---------------------------------------------------------------------------


def _build_artifacts(
    *,
    native_output_dir: Path,
    artifact_root: Path,
    output_policy: SlamOutputPolicy,
    traj_native: Path,
    ply_native: Path | None,
    n_keyframes: int,
    n_processed_frames: int,
    n_dense_points: int,
    estimated_intrinsics: CameraIntrinsicsSeries | None = None,
) -> SlamArtifacts:
    """Normalise native MASt3R outputs into repository-owned artifact contracts."""
    from prml_vslam.utils.geometry import write_point_cloud_ply  # noqa: PLC0415

    if not traj_native.exists():
        raise RuntimeError(f"Expected MASt3R trajectory file not found: '{traj_native}'.")

    # Upstream save_traj already writes TUM; copy into canonical location.
    run_paths = RunArtifactPaths.build(artifact_root)
    canonical_traj = run_paths.trajectory_path
    canonical_traj.parent.mkdir(parents=True, exist_ok=True)
    if canonical_traj.resolve() != traj_native.resolve():
        canonical_traj.write_bytes(traj_native.read_bytes())

    trajectory_ref = ArtifactRef(
        path=canonical_traj,
        kind="tum",
        fingerprint=f"mast3r-traj-{n_keyframes}",
    )

    sparse_ref: ArtifactRef | None = None
    dense_ref: ArtifactRef | None = None
    if ply_native is not None and ply_native.exists():
        # Copy the PLY through the canonical path while preserving colors
        # when Open3D is available; fall back to a byte-for-byte copy
        # otherwise.
        try:
            import open3d as o3d  # noqa: PLC0415
        except ModuleNotFoundError:
            canonical_ply = run_paths.dense_points_path
            canonical_ply.parent.mkdir(parents=True, exist_ok=True)
            canonical_ply.write_bytes(ply_native.read_bytes())
        else:
            point_cloud = o3d.io.read_point_cloud(str(ply_native))
            points_xyz = np.asarray(point_cloud.points, dtype=np.float64)
            colors_rgb = np.asarray(point_cloud.colors, dtype=np.float64) if point_cloud.has_colors() else None
            canonical_ply = write_point_cloud_ply(run_paths.dense_points_path, points_xyz, colors_rgb=colors_rgb)

        canonical_ref = ArtifactRef(
            path=canonical_ply,
            kind="ply",
            fingerprint=f"mast3r-point-cloud-{ply_native.stat().st_size}",
        )
        # MASt3R-SLAM does not maintain a separate sparse landmark store —
        # the only PLY surface upstream produces is the dense pointmap export.
        # Surface it only via dense_points_ply so artifact semantics stay clear.
        if output_policy.emit_dense_points:
            dense_ref = canonical_ref

    extras: dict[str, ArtifactRef] = {}
    skip_names = {traj_native.name}
    if ply_native is not None:
        skip_names.add(ply_native.name)
    for path in sorted(native_output_dir.iterdir()):
        if not path.is_file():
            continue
        if path.name in skip_names:
            continue
        extras[path.name] = ArtifactRef(
            path=path.resolve(),
            kind=path.suffix.lstrip(".") or "file",
            fingerprint=f"mast3r-extra-{path.name}-{path.stat().st_size}",
        )
    if estimated_intrinsics is not None and estimated_intrinsics.samples:
        run_paths.estimated_intrinsics_path.parent.mkdir(parents=True, exist_ok=True)
        run_paths.estimated_intrinsics_path.write_text(
            estimated_intrinsics.model_dump_json(indent=2),
            encoding="utf-8",
        )
        extras[run_paths.estimated_intrinsics_path.name] = ArtifactRef(
            path=run_paths.estimated_intrinsics_path,
            kind="json",
            fingerprint=f"mast3r-intrinsics-{len(estimated_intrinsics.samples)}",
        )

    return SlamArtifacts(
        trajectory_tum=trajectory_ref,
        sparse_points_ply=sparse_ref,
        dense_points_ply=dense_ref,
        extras=extras,
        num_processed_frames=n_processed_frames,
        num_keyframes=n_keyframes,
        # MASt3R does not maintain a separate sparse landmark store; expose the
        # dense pointmap accumulation for both UI counters so the dashboard does
        # not look hollow when only emit_dense_points is set.
        num_sparse_points=0,
        num_dense_points=n_dense_points if dense_ref is not None else 0,
    )


__all__ = ["Mast3rSlamBackend", "Mast3rSlamSession"]
