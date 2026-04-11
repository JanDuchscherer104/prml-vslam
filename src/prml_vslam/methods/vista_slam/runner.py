"""ViSTA-SLAM backend adapter (offline and streaming).

Wraps the upstream ``OnlineSLAM`` class from the ``external/vista-slam``
submodule and exposes it behind the repository's :class:`SlamBackend`
protocol (both :class:`OfflineSlamBackend` and :class:`StreamingSlamBackend`).

The submodule is injected into ``sys.path`` lazily at runtime so that the
heavy torch/rerun imports are deferred until the backend is actually invoked.
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
import open3d as o3d

from prml_vslam.interfaces import FramePacket, SE3Pose
from prml_vslam.methods.contracts import MethodId
from prml_vslam.pipeline.contracts import ArtifactRef, SequenceManifest, SlamArtifacts, SlamConfig, SlamUpdate
from prml_vslam.utils import Console
from prml_vslam.utils.geometry import write_point_cloud_ply, write_tum_trajectory
from prml_vslam.utils.path_config import PathConfig

from .config import VistaSlamBackendConfig

_VISTA_INPUT_RESOLUTION = (224, 224)


# ------------------------------------------------------------------
# Session
# ------------------------------------------------------------------


class VistaSlamSession:
    """Live SLAM session that forwards frames to OnlineSLAM one at a time.

    Satisfies the :class:`SlamSession` protocol.  Per-frame pose feedback is
    not available from the upstream model so :meth:`step` returns updates with
    ``pose=None``; the full trajectory is materialised in :meth:`close`.
    """

    def __init__(
        self,
        *,
        slam: object,
        cfg: SlamConfig,
        artifact_root: Path,
        console: Console,
    ) -> None:
        self._slam = slam
        self._cfg = cfg
        self._artifact_root = artifact_root
        self._console = console
        self._frame_count = 0

    def step(self, frame: FramePacket) -> SlamUpdate:
        """Feed one frame to OnlineSLAM and return a progress update."""
        import torch  # noqa: PLC0415

        rgb_uint8 = frame.rgb
        if rgb_uint8 is None:
            return SlamUpdate(seq=frame.seq, timestamp_ns=frame.timestamp_ns)

        h, w = _VISTA_INPUT_RESOLUTION
        resized = cv2.resize(rgb_uint8, (w, h), interpolation=cv2.INTER_LINEAR)

        # Build the input dict matching run.py / SLAM_image_only conventions:
        #   rgb   – (1, C, H, W) float tensor on device
        #   shape – (1, 2) tensor [H, W]
        #   gray  – (H, W) uint8 numpy
        #   view_name – str
        rgb_float = torch.from_numpy(resized).permute(2, 0, 1).float() / 255.0
        device = self._slam.device
        value = {
            "rgb": rgb_float.unsqueeze(0).to(device),
            "shape": torch.tensor(rgb_float.shape[1:3]).unsqueeze(0),
            "gray": cv2.cvtColor(resized, cv2.COLOR_RGB2GRAY),
            "view_name": f"frame_{self._frame_count:06d}",
        }
        self._slam.step(value)
        self._frame_count += 1

        pose: SE3Pose | None = None
        pointmap: np.ndarray | None = None
        try:
            view_dict = self._slam.get_view(
                self._frame_count - 1,
                filter_outlier=True,
                return_pose=True,
                return_depth=True,
                return_intri=True,
            )
            pose_tensor = view_dict.get("pose")
            if pose_tensor is not None:
                pose = SE3Pose.from_matrix(pose_tensor.numpy().astype(np.float64))

            depth_tensor = view_dict.get("depth")
            intri_tensor = view_dict.get("intri")
            if depth_tensor is not None and intri_tensor is not None and pose is not None:
                from prml_vslam.interfaces import CameraIntrinsics
                from prml_vslam.utils.geometry import pointmap_from_depth

                depth_np = depth_tensor.numpy().astype(np.float32)
                intri_np = intri_tensor.numpy().astype(np.float64)
                fx, fy = float(intri_np[0, 0]), float(intri_np[1, 1])
                cx, cy = float(intri_np[0, 2]), float(intri_np[1, 2])
                h_px, w_px = depth_np.shape
                
                # Use frame intrinsics if present; else infer from view dict
                intrinsics = frame.intrinsics or CameraIntrinsics(
                    fx=fx, fy=fy, cx=cx, cy=cy, width_px=w_px, height_px=h_px
                )
                pointmap = pointmap_from_depth(depth_np, intrinsics=intrinsics, stride_px=16)
        except Exception as e:
            self._console.warning("Failed to extract per-frame preview: %s", e)

        return SlamUpdate(
            seq=frame.seq,
            timestamp_ns=frame.timestamp_ns,
            pose=pose,
            pointmap=pointmap,
        )

    def close(self) -> SlamArtifacts:
        """Save OnlineSLAM outputs and convert to canonical artifacts."""
        raw_out = self._artifact_root / "slam" / "vista_raw"
        raw_out.mkdir(parents=True, exist_ok=True)

        self._slam.save_data_all(str(raw_out), save_images=False, save_depths=False)
        self._console.info(
            "ViSTA-SLAM session closed after %d frames; raw outputs in '%s'.",
            self._frame_count,
            raw_out,
        )
        return _build_artifacts(raw_out, self._artifact_root, self._cfg, self._console)


# ------------------------------------------------------------------
# Backend
# ------------------------------------------------------------------


class VistaSlamBackend:
    """ViSTA-SLAM backend satisfying the :class:`SlamBackend` protocol.

    Supports both offline batch execution via :meth:`run_sequence` and
    incremental streaming via :meth:`start_session`, mirroring the
    :class:`MockSlamBackend` pattern.
    """

    method_id: MethodId = MethodId.VISTA

    def __init__(
        self,
        config: VistaSlamBackendConfig,
        path_config: PathConfig | None = None,
    ) -> None:
        self._cfg = config
        self._path_config = path_config or PathConfig()
        self._console = Console(__name__).child(self.__class__.__name__)
        self._vista_dir = self._path_config.resolve_repo_path(config.vista_slam_dir)
        self._ckpt = self._path_config.resolve_repo_path(config.checkpoint_path)
        self._vocab = self._path_config.resolve_repo_path(config.vocab_path)

    # ------------------------------------------------------------------
    # StreamingSlamBackend protocol
    # ------------------------------------------------------------------

    def start_session(self, cfg: SlamConfig, artifact_root: Path) -> VistaSlamSession:
        """Load the OnlineSLAM model and return a ready-to-step session."""
        self._validate_prerequisites()
        self._inject_sys_path()

        import torch  # noqa: PLC0415
        from vista_slam.slam import OnlineSLAM  # noqa: PLC0415

        torch.manual_seed(self._cfg.slam.random_seed)

        slam = OnlineSLAM(
            ckpt_path=str(self._ckpt),
            vocab_path=str(self._vocab),
            max_view_num=self._cfg.slam.max_view_num,
            neighbor_edge_num=self._cfg.slam.neighbor_edge_num,
            loop_edge_num=self._cfg.slam.loop_edge_num,
            loop_dist_min=self._cfg.slam.loop_dist_min,
            loop_nms=self._cfg.slam.loop_nms,
            loop_cand_thresh_neighbor=self._cfg.slam.loop_cand_thresh_neighbor,
            conf_thres=self._cfg.slam.point_conf_thres,
            rel_pose_thres=self._cfg.slam.rel_pose_thres,
            flow_thres=self._cfg.slam.flow_thres,
            pgo_every=self._cfg.slam.pgo_every,
        )
        self._console.info("OnlineSLAM model loaded; session ready.")
        return VistaSlamSession(
            slam=slam,
            cfg=cfg,
            artifact_root=artifact_root,
            console=self._console,
        )

    # ------------------------------------------------------------------
    # OfflineSlamBackend protocol
    # ------------------------------------------------------------------

    def run_sequence(
        self,
        sequence: SequenceManifest,
        cfg: SlamConfig,
        artifact_root: Path,
    ) -> SlamArtifacts:
        """Run ViSTA-SLAM over a materialised sequence and persist artifacts.

        Delegates to :meth:`start_session` and feeds each extracted frame
        through the session, mirroring the :class:`MockSlamBackend` pattern.
        """
        frames_dir = self._resolve_frames(sequence, artifact_root, cfg)
        session = self.start_session(cfg, artifact_root)

        image_paths = sorted(frames_dir.glob("*.png"))
        self._console.info("Running ViSTA-SLAM on %d frames …", len(image_paths))

        for seq, img_path in enumerate(image_paths):
            rgb = cv2.cvtColor(cv2.imread(str(img_path)), cv2.COLOR_BGR2RGB)
            packet = FramePacket(seq=seq, timestamp_ns=seq, rgb=rgb)
            session.step(packet)

        return session.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_prerequisites(self) -> None:
        """Raise RuntimeError early if the submodule or weights are missing."""
        missing: list[str] = []
        if not self._vista_dir.exists():
            missing.append(f"vista-slam repo not found at '{self._vista_dir}'")
        if not self._ckpt.exists():
            missing.append(
                f"STA checkpoint missing at '{self._ckpt}' — "
                "download from the upstream release and place it under external/vista-slam/pretrains/"
            )
        if not self._vocab.exists():
            missing.append(
                f"ORB vocabulary missing at '{self._vocab}' — "
                "download from the upstream release and place it under external/vista-slam/pretrains/"
            )
        if missing:
            raise RuntimeError("ViSTA-SLAM prerequisites not satisfied:\n" + "\n".join(f"  • {m}" for m in missing))

    def _inject_sys_path(self) -> None:
        """Insert the vista-slam submodule root into sys.path if not already present."""
        vista_str = str(self._vista_dir)
        if vista_str not in sys.path:
            sys.path.insert(0, vista_str)

    def _resolve_frames(
        self,
        sequence: SequenceManifest,
        artifact_root: Path,
        cfg: SlamConfig,
    ) -> Path:
        """Return a directory of PNG frames, extracting from video if needed."""
        if sequence.rgb_dir is not None and sequence.rgb_dir.exists():
            png_files = sorted(sequence.rgb_dir.glob("*.png"))
            if png_files:
                self._console.info("Using pre-materialised frames from '%s'.", sequence.rgb_dir)
                return sequence.rgb_dir

        if sequence.video_path is not None and sequence.video_path.exists():
            frames_dir = artifact_root / "input" / "frames"
            return self._extract_video_frames(sequence.video_path, frames_dir, cfg)

        raise RuntimeError(
            "SequenceManifest has no usable frame source: "
            "set rgb_dir to a directory of PNG files or video_path to a video file."
        )

    def _extract_video_frames(
        self,
        video_path: Path,
        out_dir: Path,
        cfg: SlamConfig,
    ) -> Path:
        """Decode a video file to PNG frames using OpenCV."""
        out_dir.mkdir(parents=True, exist_ok=True)
        existing = sorted(out_dir.glob("*.png"))
        if existing:
            self._console.info("Reusing %d already-extracted frames in '%s'.", len(existing), out_dir)
            return out_dir

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise RuntimeError(f"OpenCV could not open video '{video_path}'.")

        written = 0
        self._console.info("Extracting frames from '%s' …", video_path)
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if cfg.max_frames is not None and written >= cfg.max_frames:
                break
            cv2.imwrite(str(out_dir / f"frame_{written:06d}.png"), frame)
            written += 1

        cap.release()
        self._console.info("Extracted %d frames to '%s'.", written, out_dir)
        return out_dir.resolve()


# ------------------------------------------------------------------
# Shared artifact builder
# ------------------------------------------------------------------


def _build_artifacts(
    raw_out: Path,
    artifact_root: Path,
    cfg: SlamConfig,
    console: Console,
) -> SlamArtifacts:
    """Convert raw vista-slam outputs to the repository's canonical artifact layout."""
    traj_npy = raw_out / "trajectory.npy"
    if not traj_npy.exists():
        raise RuntimeError(f"Expected trajectory file not found: '{traj_npy}'")

    poses_se3: np.ndarray = np.load(traj_npy)
    poses = [SE3Pose.from_matrix(T.astype(np.float64)) for T in poses_se3]
    timestamps = [float(i) for i in range(len(poses))]

    traj_path = write_tum_trajectory(artifact_root / "slam" / "trajectory.tum", poses, timestamps)
    trajectory_ref = ArtifactRef(path=traj_path, kind="tum", fingerprint=f"vista-traj-{len(poses)}")

    sparse_ref: ArtifactRef | None = None
    dense_ref: ArtifactRef | None = None
    ply_src = raw_out / "pointcloud.ply"

    if ply_src.exists() and (cfg.emit_sparse_points or cfg.emit_dense_points):
        pcd = o3d.io.read_point_cloud(str(ply_src))
        pts = np.asarray(pcd.points, dtype=np.float64)

        if cfg.emit_sparse_points:
            sp_path = write_point_cloud_ply(artifact_root / "slam" / "sparse_points.ply", pts)
            sparse_ref = ArtifactRef(path=sp_path, kind="ply", fingerprint=f"vista-sparse-{len(pts)}")

        if cfg.emit_dense_points:
            dp_path = write_point_cloud_ply(artifact_root / "dense" / "dense_points.ply", pts)
            dense_ref = ArtifactRef(path=dp_path, kind="ply", fingerprint=f"vista-dense-{len(pts)}")
    else:
        console.warning("No pointcloud.ply found at '%s'; skipping point cloud artifacts.", ply_src)

    return SlamArtifacts(
        trajectory_tum=trajectory_ref,
        sparse_points_ply=sparse_ref,
        dense_points_ply=dense_ref,
    )


__all__ = ["VistaSlamBackend", "VistaSlamSession"]
