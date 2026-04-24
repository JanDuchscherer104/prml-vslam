"""Canonical MASt3R-SLAM backend adapter (offline + streaming).

This adapter wraps the upstream MASt3R-SLAM codebase located under
``external/mast3r-slam`` and exposes the ``SlamBackend`` protocol so the
repository pipeline (offline + streaming + Streamlit) can drive it.

Architecture (mirrors VistaSlamBackend):

- ``Mast3rSlamBackend`` implements ``run_sequence`` (offline, materialized
  frames) and ``start_session`` (streaming, returns ``MultiprocessSlamSession``).
- ``Mast3rSlamSession`` runs MASt3R's front-end (FrameTracker FSM) on the
  calling thread and spawns a background *thread* that runs MASt3R's
  back-end loop (FactorGraph local optimisation + retrieval loop
  closure). The two threads share ``SharedKeyframes`` / ``SharedStates``
  which already carry their own locks upstream.
- ``_Mast3rSessionFactory`` is a pickleable callable used by
  ``MultiprocessSlamSession`` to re-instantiate the session in a spawn
  worker process (needed because CUDA contexts don't survive fork).
"""

from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import cv2
import numpy as np

from prml_vslam.benchmark import PreparedBenchmarkInputs, ReferenceSource
from prml_vslam.interfaces import FramePacket, FrameTransform
from prml_vslam.methods.contracts import MethodId, SlamBackendConfig, SlamOutputPolicy
from prml_vslam.methods.protocols import SlamBackend
from prml_vslam.methods.updates import SlamUpdate
from prml_vslam.pipeline.contracts.artifacts import ArtifactRef, SlamArtifacts
from prml_vslam.pipeline.contracts.sequence import SequenceManifest
from prml_vslam.utils import Console, PathConfig, RunArtifactPaths

from .config import Mast3rSlamBackendConfig

if TYPE_CHECKING:
    from prml_vslam.methods.protocols import SlamSession


# ---------------------------------------------------------------------------
# Session: wraps the upstream FrameTracker FSM + background FactorGraph loop.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# In-process manager shim.
#
# MultiprocessSlamSession runs us inside a *daemonic* subprocess, and Python
# forbids daemonic processes from spawning children — so mp.Manager() (which
# spawns its own helper process) is off-limits here. Since our backend is a
# thread in the same process, we don't actually need cross-process sharing;
# threading primitives are enough. This shim matches the small subset of the
# Manager API that upstream SharedKeyframes/SharedStates actually call.
# ---------------------------------------------------------------------------


class _InProcessValue:
    """Stand-in for ``mp.Manager().Value`` without a helper subprocess."""

    __slots__ = ("value",)

    def __init__(self, typecode: str, initial: Any) -> None:  # noqa: ARG002
        self.value = initial


class _InProcessManager:
    """Drop-in substitute for ``mp.Manager()`` usable from daemonic workers."""

    def RLock(self):  # noqa: N802 — match mp.Manager API
        return threading.RLock()

    def Value(self, typecode: str, initial: Any):  # noqa: N802
        return _InProcessValue(typecode, initial)

    def list(self):  # noqa: A003
        return []


class Mast3rSlamSession:
    """Stateful streaming session over the upstream MASt3R-SLAM runtime."""

    def __init__(
        self,
        *,
        cfg: Mast3rSlamBackendConfig,
        output_policy: SlamOutputPolicy,
        artifact_root: Path,
        console: Console,
    ) -> None:
        self._cfg = cfg
        self._output_policy = output_policy
        self._artifact_root = artifact_root
        self._console = console.child("Mast3rSlamSession")

        # Lazy-loaded heavy objects (populated by _initialize below).
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
        self._timestamps_s: list[float] = []  # indexed by internal frame_id (= step call order)
        self._pending_updates: list[SlamUpdate] = []
        self._backend_error: Exception | None = None

        # Backend thread control.
        self._backend_thread: threading.Thread | None = None
        self._backend_stop = threading.Event()

        self._initialize()

    # ---- initialisation -------------------------------------------------

    def _initialize(self) -> None:
        """Load the upstream runtime and model state needed before first-frame setup."""
        import torch  # noqa: PLC0415

        self._inject_sys_path()
        self._validate_prerequisites()

        # Upstream config is a GLOBAL dict — load it in this process first
        # so that every imported mast3r_slam module sees the correct values.
        from mast3r_slam.config import load_config  # noqa: PLC0415

        load_config(str(self._resolve_path(self._cfg.yaml_config_path)))
        from mast3r_slam.config import config as mast3r_cfg  # noqa: PLC0415

        # Apply optional override for use_calib before any downstream module reads it.
        if self._cfg.use_calib is not None:
            mast3r_cfg["use_calib"] = bool(self._cfg.use_calib)

        torch.backends.cuda.matmul.allow_tf32 = True
        torch.set_grad_enabled(False)

        # Load model + share memory so backend thread (same process) sees same weights.
        from mast3r_slam.mast3r_utils import load_mast3r  # noqa: PLC0415
        from mast3r_slam.frame import Mode, SharedKeyframes, SharedStates, create_frame  # noqa: PLC0415
        from mast3r_slam.mast3r_utils import mast3r_inference_mono, resize_img  # noqa: PLC0415
        from mast3r_slam.tracker import FrameTracker  # noqa: PLC0415
        import lietorch  # noqa: PLC0415

        checkpoint = str(self._resolve_path(self._cfg.checkpoint_path))
        self._console.info("Loading MASt3R model from '%s'...", checkpoint)
        self._model = load_mast3r(path=checkpoint, device=self._device)
        self._model.share_memory()
        self._lietorch = lietorch
        self._Mode = Mode
        self._create_frame = create_frame
        self._resize_img = resize_img
        self._SharedKeyframes = SharedKeyframes
        self._SharedStates = SharedStates
        self._FrameTracker = FrameTracker
        self._mast3r_inference_mono = mast3r_inference_mono

    # ---- streaming step -------------------------------------------------

    def step(self, frame: FramePacket) -> None:
        """Feed one frame to MASt3R and emit an incremental SlamUpdate."""
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
            self._keyframes = self._SharedKeyframes(self._manager, self._h, self._w, device=self._device)
            self._states = self._SharedStates(self._manager, self._h, self._w, device=self._device)
            self._tracker = self._FrameTracker(self._model, self._keyframes, self._device)
            self._console.info(f"MASt3R initialized with dynamic size: {self._h}x{self._w}")

        internal_idx = self._source_frame_count
        self._timestamps_s.append(frame.timestamp_ns / 1e9)

        # If we're configured for use_calib and we haven't set K yet, grab it
        # from the packet. We compute K_frame on first use (scaled intrinsics
        # for the resized MASt3R image).
        self._maybe_set_intrinsics(frame)
        if self._backend_thread is None:
            self._start_backend_thread()

        # uint8 RGB H×W×3 → float32 [0,1] (what mast3r_slam.frame.create_frame expects).
        img_f32 = (frame.rgb.astype(np.float32) / 255.0) if frame.rgb.dtype != np.float32 else frame.rgb

        # Prior pose for this frame: last tracked frame's pose, or identity for the very first.
        if internal_idx == 0:
            T_WC = self._lietorch.Sim3.Identity(1, device=self._device)
        else:
            prev = self._states.get_frame()
            T_WC = prev.T_WC

        mast3r_frame = self._create_frame(
            internal_idx, img_f32, T_WC, img_size=self._img_size, device=self._device
        )

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
            # We do not wait for reloc to complete here — let streaming proceed;
            # if single_thread config is set, upstream main.py spins until done;
            # we choose non-blocking for pipeline throughput.

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
        """Return and clear any pending SLAM updates."""
        self._raise_if_backend_failed()
        updates = self._pending_updates
        self._pending_updates = []
        return updates

    def close(self) -> SlamArtifacts:
        """Stop the backend thread, persist artifacts, return them canonical."""
        from mast3r_slam.frame import Mode  # noqa: PLC0415

        if self._states is None or self._keyframes is None:
            raise RuntimeError("MASt3R-SLAM cannot close before any RGB frame has been processed.")
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
                self._console.warn(
                    "MASt3R-SLAM reconstruction export failed: %s (trajectory still saved).", exc
                )

        self._console.info(
            "MASt3R-SLAM session closed after %d frames, %d keyframes. Native outputs in '%s'.",
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
            n_keyframes=self._accepted_keyframe_count,
        )

    # ---- backend thread -------------------------------------------------

    def _backend_loop(self) -> None:
        """Run upstream ``run_backend`` logic inside this process as a thread."""
        from mast3r_slam.config import config as mast3r_cfg  # noqa: PLC0415
        from mast3r_slam.frame import Mode  # noqa: PLC0415
        from mast3r_slam.global_opt import FactorGraph  # noqa: PLC0415
        from mast3r_slam.mast3r_utils import load_retriever  # noqa: PLC0415

        factor_graph = FactorGraph(self._model, self._keyframes, self._K, self._device)
        retriever_path = str(self._resolve_path(self._cfg.retrieval_checkpoint_path))
        retrieval_database = load_retriever(
            self._model, retriever_path=retriever_path, device=self._device
        )

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
                    success = self._relocalization(
                        frame, factor_graph, retrieval_database, use_calib
                    )
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
                    factor_graph.add_factors(
                        kf_idx_list, frame_idx, mast3r_cfg["local_opt"]["min_match_frac"]
                    )

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
                self._backend_error = RuntimeError(f"MASt3R backend loop failed: {exc}")
                self._console.error("MASt3R backend loop error: %s", exc)
                self._backend_stop.set()
                break

    def _relocalization(
        self, frame: Any, factor_graph: Any, retrieval_database: Any, use_calib: bool
    ) -> bool:
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

    def _maybe_set_intrinsics(self, frame: FramePacket) -> None:
        """First-frame path to populate K from the packet when use_calib is active.

        Note: this MUST run before the first keyframe is appended — otherwise
        SharedKeyframes.__getitem__ has already baked None into the kf.K field
        of that keyframe via the config["use_calib"] lookup.
        """
        from mast3r_slam.config import config as mast3r_cfg  # noqa: PLC0415

        if not mast3r_cfg.get("use_calib", False):
            return
        if self._K is not None:
            return
        if frame.intrinsics is None:
            # use_calib is requested but we have no intrinsics — fail loud rather than
            # silently tracking in the wrong branch.
            raise RuntimeError(
                "MASt3R use_calib=True but FramePacket.intrinsics is None. "
                "Either provide intrinsics in the FramePacket or set Mast3rSlamBackendConfig.use_calib=False."
            )
        # Build the K_frame (intrinsics rescaled to the resized-encoder image) using
        # the same recipe as upstream dataloader.Intrinsics.
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

        self._K = torch.from_numpy(intrinsics_obj.K_frame).to(
            self._device, dtype=torch.float32
        )
        self._keyframes.set_intrinsics(self._K)

    def _emit_empty_update(self, frame: FramePacket) -> None:
        """Emit a no-op update for a frame without RGB payload."""
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
        frame: FramePacket,
        mast3r_frame: Any,
        is_keyframe: bool,
        keyframe_index: int | None,
        pose_updated: bool,
    ) -> None:
        """Translate the current MASt3R frame state into a canonical SlamUpdate."""
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
                preview_rgb=preview_rgb,
            )
        )

    def _extract_keyframe_visuals(
        self, mast3r_frame: Any
    ) -> tuple[np.ndarray | None, np.ndarray | None, int]:
        """Pull the camera-local RDF pointmap + RGB preview for live visualisation."""
        try:
            x_canon = mast3r_frame.X_canon
            c_avg = mast3r_frame.get_average_conf()
            if x_canon is None or c_avg is None:
                return None, None, 0

            # Reshape source of truth: Frame.img_shape is maintained by
            # create_frame() with the same downsample factor applied to both
            # X_canon and uimg, so it matches both.
            img_shape = mast3r_frame.img_shape
            if img_shape is None:
                return None, None, 0
            shape_vals = img_shape.flatten().tolist()
            if len(shape_vals) < 2:
                return None, None, 0
            h, w = int(shape_vals[0]), int(shape_vals[1])

            # X_canon is the per-keyframe camera-local pointmap. Keep it camera-local
            # so SlamUpdate.pointmap remains consistent with the repository contract.
            points_camera = x_canon.detach().cpu().numpy().astype(np.float32).reshape(h, w, 3)

            preview_rgb: np.ndarray | None = None
            if mast3r_frame.uimg is not None:
                preview_rgb = (
                    (mast3r_frame.uimg.detach().cpu().numpy() * 255.0)
                    .clip(0, 255)
                    .astype(np.uint8)
                )

            conf = c_avg.detach().cpu().numpy().reshape(-1)
            valid = int(np.count_nonzero(conf > self._cfg.c_conf_threshold))
            return points_camera, preview_rgb, valid
        except Exception:
            return None, None, 0

    def _frame_transform_from_sim3(self, T_WC: Any) -> FrameTransform:
        """Convert a lietorch.Sim3 pose (what MASt3R tracks) to our SE(3) FrameTransform."""
        from mast3r_slam.lietorch_utils import as_SE3  # noqa: PLC0415

        se3 = as_SE3(T_WC)  # lietorch.SE3 on CPU
        # se3.matrix() -> (B, 4, 4); batch dim is 1.
        matrix = se3.matrix()[0].detach().cpu().numpy().astype(np.float64)
        return FrameTransform.from_matrix(matrix)

    def _resolve_path(self, path: Path) -> Path:
        """Resolve a repo-relative path against the project root."""
        return PathConfig().resolve_repo_path(path)

    def _start_backend_thread(self) -> None:
        """Start the optimization backend after shared state and intrinsics are ready."""
        self._backend_stop.clear()
        self._backend_thread = threading.Thread(
            target=self._backend_loop, name="mast3r-backend", daemon=True
        )
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
        # Also its embedded third-party dirs (mast3r, dust3r) which live under mast3r_slam/thirdparty.
        # Upstream `pip install -e .` handles this; we add the src root as a safety net.

    def _validate_prerequisites(self) -> None:
        """Fail early with actionable diagnostics if upstream assets are missing."""
        missing: list[str] = []
        mast3r_dir = self._resolve_path(self._cfg.mast3r_slam_dir)
        if not (mast3r_dir / "mast3r_slam").exists():
            missing.append(
                f"mast3r-slam submodule not populated at '{mast3r_dir}'. "
                "Run: git submodule update --init --recursive"
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

        # Try importing the CUDA extension early — far better to fail here than deep in solve_GN.
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
                "MASt3R-SLAM prerequisites not satisfied:\n"
                + "\n".join(f"  • {item}" for item in missing)
            )


# ---------------------------------------------------------------------------
# Backend: offline + streaming entry points.
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

    def start_session(
        self,
        backend_config: SlamBackendConfig,
        output_policy: SlamOutputPolicy,
        artifact_root: Path,
    ) -> "SlamSession":
        """Return a spawn-backed MultiprocessSlamSession running MASt3R."""
        from prml_vslam.methods.multiprocess import MultiprocessSlamSession  # noqa: PLC0415

        factory = _Mast3rSessionFactory(
            config=self._cfg,
            output_policy=output_policy,
            artifact_root=artifact_root,
        )
        session = MultiprocessSlamSession(session_factory=factory, console=self._console)
        self._console.info("MASt3R-SLAM worker process launched; session ready.")
        return session

    def run_sequence(
        self,
        sequence: SequenceManifest,
        benchmark_inputs: PreparedBenchmarkInputs | None,
        baseline_source: ReferenceSource,
        backend_config: SlamBackendConfig,
        output_policy: SlamOutputPolicy,
        artifact_root: Path,
    ) -> SlamArtifacts:
        """Run MASt3R-SLAM offline over a materialized frame directory."""
        del benchmark_inputs, baseline_source
        frames_dir = self._resolve_frames(sequence, artifact_root, backend_config)
        image_paths = sorted(frames_dir.glob("*.png"))
        if backend_config.max_frames is not None:
            image_paths = image_paths[: backend_config.max_frames]

        # Offline runs use the in-process session (no spawn needed); simpler and
        # avoids picklability constraints on FramePacket payloads for local work.
        session = Mast3rSlamSession(
            cfg=self._cfg,
            output_policy=output_policy,
            artifact_root=artifact_root,
            console=self._console,
        )
        self._console.info("Running MASt3R-SLAM on %d frames …", len(image_paths))
        timestamps_ns = self._load_timestamps_ns(sequence=sequence, num_frames=len(image_paths))
        try:
            for seq, image_path in enumerate(image_paths):
                bgr = cv2.imread(str(image_path))
                if bgr is None:
                    raise RuntimeError(f"Failed to read input frame '{image_path}'.")
                rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                session.step(FramePacket(seq=seq, timestamp_ns=timestamps_ns[seq], rgb=rgb))
            return session.close()
        finally:
            if session._states is not None:
                session._backend_stop.set()
                session._join_backend_thread()

    def _resolve_frames(
        self,
        sequence: SequenceManifest,
        artifact_root: Path,
        backend_config: SlamBackendConfig,
    ) -> Path:
        if sequence.rgb_dir is not None and sequence.rgb_dir.exists():
            png_files = sorted(sequence.rgb_dir.glob("*.png"))
            if png_files:
                self._console.info("Using pre-materialized frames from '%s'.", sequence.rgb_dir)
                return sequence.rgb_dir
        if sequence.video_path is None or not sequence.video_path.exists():
            raise RuntimeError(
                "SequenceManifest has no usable frame source: set `rgb_dir` or provide `video_path`."
            )
        frames_dir = RunArtifactPaths.build(artifact_root).input_frames_dir
        return self._extract_video_frames(sequence.video_path, frames_dir, backend_config.max_frames)

    def _extract_video_frames(
        self, video_path: Path, output_dir: Path, max_frames: int | None
    ) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        existing = sorted(output_dir.glob("*.png"))
        if existing and (max_frames is None or len(existing) >= max_frames):
            self._console.info("Reusing %d pre-extracted frames in '%s'.", len(existing), output_dir)
            return output_dir
        for stale in output_dir.glob("*.png"):
            stale.unlink()

        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            raise RuntimeError(f"OpenCV could not open video '{video_path}'.")
        written = 0
        self._console.info("Extracting frames from '%s' …", video_path)
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            if max_frames is not None and written >= max_frames:
                break
            if not cv2.imwrite(str(output_dir / f"{written:06d}.png"), frame):
                raise RuntimeError(f"Failed to write extracted frame #{written} to '{output_dir}'.")
            written += 1
        capture.release()
        self._console.info("Extracted %d frames to '%s'.", written, output_dir)
        return output_dir.resolve()

    def _load_timestamps_ns(self, *, sequence: SequenceManifest, num_frames: int) -> list[int]:
        """Load normalized timestamps from the manifest, falling back to synthetic 30 FPS."""
        fallback = [int(index * 1e9 / 30.0) for index in range(num_frames)]
        if sequence.timestamps_path is None or not sequence.timestamps_path.exists():
            return fallback

        source_path = sequence.timestamps_path
        if source_path.suffix.lower() == ".json":
            payload = json.loads(source_path.read_text(encoding="utf-8"))
            if isinstance(payload, dict) and isinstance(payload.get("timestamps_ns"), list):
                values = [int(value) for value in payload["timestamps_ns"][:num_frames]]
                if len(values) < num_frames:
                    values.extend(fallback[len(values) :])
                return values

        rows = []
        for line in source_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rows.append(line.split(",", maxsplit=1)[0].strip())
        if rows:
            values = [int(round(float(value) * 1e9)) for value in rows[:num_frames]]
            if len(values) < num_frames:
                values.extend(fallback[len(values) :])
            return values
        return fallback


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
        # The PLY is already a valid point cloud — copy it through the canonical path
        # using a single xyz→xyz round-trip so it lives where downstream stages expect.
        try:
            import open3d as o3d  # noqa: PLC0415
        except ModuleNotFoundError:
            # Fallback: bit-identical copy under canonical name.
            canonical_ply = run_paths.point_cloud_path
            canonical_ply.parent.mkdir(parents=True, exist_ok=True)
            canonical_ply.write_bytes(ply_native.read_bytes())
        else:
            point_cloud = o3d.io.read_point_cloud(str(ply_native))
            points_xyz = np.asarray(point_cloud.points, dtype=np.float64)
            canonical_ply = write_point_cloud_ply(run_paths.point_cloud_path, points_xyz)

        canonical_ref = ArtifactRef(
            path=canonical_ply,
            kind="ply",
            fingerprint=f"mast3r-point-cloud-{ply_native.stat().st_size}",
        )
        if output_policy.emit_sparse_points:
            sparse_ref = canonical_ref
        if output_policy.emit_dense_points:
            dense_ref = canonical_ref

    extras: dict[str, ArtifactRef] = {}
    for path in sorted(native_output_dir.iterdir()):
        if not path.is_file():
            continue
        if path.name in {traj_native.name, ply_native.name if ply_native else ""}:
            continue
        extras[path.name] = ArtifactRef(
            path=path.resolve(),
            kind=path.suffix.lstrip(".") or "file",
            fingerprint=f"mast3r-extra-{path.name}-{path.stat().st_size}",
        )

    return SlamArtifacts(
        trajectory_tum=trajectory_ref,
        sparse_points_ply=sparse_ref,
        dense_points_ply=dense_ref,
        extras=extras,
    )


# ---------------------------------------------------------------------------
# Pickleable factory used by MultiprocessSlamSession (spawn context).
# ---------------------------------------------------------------------------


class _Mast3rSessionFactory:
    """Pickleable factory that re-instantiates the session in a worker process."""

    def __init__(
        self,
        config: Mast3rSlamBackendConfig,
        output_policy: SlamOutputPolicy,
        artifact_root: Path,
    ) -> None:
        self.config = config
        self.output_policy = output_policy
        self.artifact_root = artifact_root

    def __call__(self) -> Mast3rSlamSession:
        console = Console("prml_vslam.methods.mast3r").child("Mast3rSlamSession.worker")
        return Mast3rSlamSession(
            cfg=self.config,
            output_policy=self.output_policy,
            artifact_root=self.artifact_root,
            console=console,
        )


__all__ = ["Mast3rSlamBackend", "Mast3rSlamSession"]
