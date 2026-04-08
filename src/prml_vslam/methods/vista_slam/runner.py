"""Offline ViSTA-SLAM backend adapter.

Wraps the upstream ``OnlineSLAM`` class from the ``external/vista-slam``
submodule and exposes it behind the repository's :class:`OfflineSlamBackend`
protocol.  The submodule is injected into ``sys.path`` lazily at runtime so
that the heavy torch/rerun imports are deferred until the backend is actually
invoked.
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
import open3d as o3d

from prml_vslam.interfaces import SE3Pose
from prml_vslam.methods.contracts import MethodId
from prml_vslam.pipeline.contracts import ArtifactRef, SequenceManifest, SlamArtifacts, SlamConfig
from prml_vslam.utils import Console
from prml_vslam.utils.geometry import write_point_cloud_ply, write_tum_trajectory
from prml_vslam.utils.path_config import PathConfig

from .config import VistaSlamBackendConfig


class VistaSlamBackend:
    """Offline ViSTA-SLAM backend satisfying the :class:`OfflineSlamBackend` protocol.

    Invoked by calling :meth:`run_sequence` with a materialised
    :class:`SequenceManifest`.  The backend injects the ``external/vista-slam``
    submodule into ``sys.path`` and imports ``OnlineSLAM`` in-process so that
    all heavy dependencies (torch, rerun, pypose …) live in the common
    project environment.
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
    # OfflineSlamBackend protocol
    # ------------------------------------------------------------------

    def run_sequence(
        self,
        sequence: SequenceManifest,
        cfg: SlamConfig,
        artifact_root: Path,
    ) -> SlamArtifacts:
        """Run ViSTA-SLAM over a materialised sequence and persist artifacts.

        Args:
            sequence: Normalised boundary between ingest and SLAM stages.
            cfg: SLAM-stage configuration (dense/sparse toggles, frame cap).
            artifact_root: Run-level artifact root directory.

        Returns:
            Materialised SLAM artifacts in the repository's canonical layout.
        """
        self._validate_prerequisites()
        self._inject_sys_path()

        frames_dir = self._resolve_frames(sequence, artifact_root, cfg)
        raw_out = artifact_root / "slam" / "vista_raw"
        raw_out.mkdir(parents=True, exist_ok=True)

        self._console.info("Running ViSTA-SLAM on %d frames …", len(list(frames_dir.glob("*.png"))))
        self._run_online_slam(frames_dir, raw_out)
        return self._build_artifacts(raw_out, artifact_root, cfg)

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
        """Decode a video file to PNG frames using OpenCV.

        Args:
            video_path: Input video.
            out_dir: Target directory for frame PNGs.
            cfg: SLAM config — ``max_frames`` acts as an optional hard cap.

        Returns:
            Resolved directory containing the written PNG frames.
        """
        out_dir.mkdir(parents=True, exist_ok=True)
        existing = sorted(out_dir.glob("*.png"))
        if existing:
            self._console.info("Reusing %d already-extracted frames in '%s'.", len(existing), out_dir)
            return out_dir

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise RuntimeError(f"OpenCV could not open video '{video_path}'.")

        written = 0
        frame_idx = 0
        self._console.info("Extracting frames from '%s' …", video_path)
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if cfg.max_frames is not None and written >= cfg.max_frames:
                break
            cv2.imwrite(str(out_dir / f"frame_{written:06d}.png"), frame)
            written += 1
            frame_idx += 1

        cap.release()
        self._console.info("Extracted %d frames to '%s'.", written, out_dir)
        return out_dir.resolve()

    def _run_online_slam(self, frames_dir: Path, raw_out: Path) -> None:
        """Import OnlineSLAM in-process and process all PNG frames in frames_dir."""
        import torch  # noqa: PLC0415  (deferred heavy import)
        from vista_slam.datasets.slam_images_only import SLAM_image_only  # noqa: PLC0415
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

        image_paths = [str(p) for p in sorted(frames_dir.glob("*.png"))]
        if not image_paths:
            raise RuntimeError(f"No PNG frames found in '{frames_dir}'.")

        dataset = SLAM_image_only(image_paths, resolution=(224, 224))
        device = slam.device
        for data in dataset:
            # Match run.py's input_value construction exactly:
            # rgb: (1, C, H, W) float tensor on device
            # shape: (1, 2) tensor with [H, W]
            # gray: (H, W) uint8 numpy array
            # view_name: str
            img = data["rgb"].unsqueeze(0).to(device)
            img_shape = torch.tensor(data["rgb"].shape[1:3]).unsqueeze(0)
            img_gray = (data["gray"].squeeze(0).numpy() * 255).astype(np.uint8)
            value = {
                "rgb": img,
                "shape": img_shape,
                "gray": img_gray,
                "view_name": data["img_name"],
            }
            slam.step(value)

        slam.save_data_all(str(raw_out), save_images=False, save_depths=False)
        self._console.info("ViSTA-SLAM completed; raw outputs in '%s'.", raw_out)

    def _build_artifacts(
        self,
        raw_out: Path,
        artifact_root: Path,
        cfg: SlamConfig,
    ) -> SlamArtifacts:
        """Convert raw vista-slam outputs to the repository's canonical artifact layout."""
        # --- trajectory -------------------------------------------------
        traj_npy = raw_out / "trajectory.npy"
        if not traj_npy.exists():
            raise RuntimeError(f"Expected trajectory file not found: '{traj_npy}'")

        poses_se3: np.ndarray = np.load(traj_npy)  # (N, 4, 4)
        poses = [SE3Pose.from_matrix(T.astype(np.float64)) for T in poses_se3]
        timestamps = [float(i) for i in range(len(poses))]

        traj_path = write_tum_trajectory(
            artifact_root / "slam" / "trajectory.tum",
            poses,
            timestamps,
        )
        trajectory_ref = ArtifactRef(
            path=traj_path,
            kind="tum",
            fingerprint=f"vista-traj-{len(poses)}",
        )

        # --- point cloud ------------------------------------------------
        ply_src = raw_out / "pointcloud.ply"
        sparse_ref: ArtifactRef | None = None
        dense_ref: ArtifactRef | None = None

        if ply_src.exists() and (cfg.emit_sparse_points or cfg.emit_dense_points):
            pcd = o3d.io.read_point_cloud(str(ply_src))
            pts = np.asarray(pcd.points, dtype=np.float64)

            if cfg.emit_sparse_points:
                sp_path = write_point_cloud_ply(artifact_root / "slam" / "sparse_points.ply", pts)
                sparse_ref = ArtifactRef(
                    path=sp_path,
                    kind="ply",
                    fingerprint=f"vista-sparse-{len(pts)}",
                )

            if cfg.emit_dense_points:
                dp_path = write_point_cloud_ply(artifact_root / "dense" / "dense_points.ply", pts)
                dense_ref = ArtifactRef(
                    path=dp_path,
                    kind="ply",
                    fingerprint=f"vista-dense-{len(pts)}",
                )
        else:
            self._console.warning("No pointcloud.ply found at '%s'; skipping point cloud artifacts.", ply_src)

        return SlamArtifacts(
            trajectory_tum=trajectory_ref,
            sparse_points_ply=sparse_ref,
            dense_points_ply=dense_ref,
        )


__all__ = ["VistaSlamBackend"]
