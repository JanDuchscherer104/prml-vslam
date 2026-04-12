"""Canonical ViSTA-SLAM backend adapter (offline + streaming)."""

from __future__ import annotations

import ctypes
import site
import sys
from pathlib import Path
from typing import Protocol

import cv2
import numpy as np
import open3d as o3d

from prml_vslam.benchmark import PreparedBenchmarkInputs, ReferenceSource
from prml_vslam.interfaces import FramePacket, FrameTransform
from prml_vslam.methods.contracts import MethodId, SlamBackendConfig, SlamOutputPolicy
from prml_vslam.methods.protocols import SlamBackend
from prml_vslam.methods.updates import SlamUpdate
from prml_vslam.pipeline.contracts.artifacts import ArtifactRef, SlamArtifacts
from prml_vslam.pipeline.contracts.sequence import SequenceManifest
from prml_vslam.utils import Console, PathConfig, RunArtifactPaths
from prml_vslam.utils.geometry import write_point_cloud_ply, write_tum_trajectory

from .config import VistaSlamBackendConfig

_VISTA_INPUT_RESOLUTION = (224, 224)


class _FlowTracker(Protocol):
    """Upstream flow tracker seam used to gate accepted keyframes."""

    def compute_disparity(self, image: np.ndarray, visualize: bool = False) -> bool:
        """Return whether the current frame should become a new keyframe."""


class VistaSlamSession:
    """Stateful streaming session that forwards frames to upstream OnlineSLAM."""

    def __init__(
        self,
        *,
        slam: object,
        flow_tracker: _FlowTracker,
        artifact_root: Path,
        output_policy: SlamOutputPolicy,
        console: Console,
    ) -> None:
        self._slam = slam
        self._flow_tracker = flow_tracker
        self._artifact_root = artifact_root
        self._output_policy = output_policy
        self._console = console
        self._source_frame_count = 0
        self._accepted_keyframe_count = 0
        self._num_dense_points = 0
        self._live_preview_wait_logged = False

    def step(self, frame: FramePacket) -> SlamUpdate:
        """Feed one frame to OnlineSLAM and return incremental telemetry."""
        self._source_frame_count += 1

        if frame.rgb is None:
            return SlamUpdate(
                seq=frame.seq,
                timestamp_ns=frame.timestamp_ns,
                is_keyframe=False,
                keyframe_index=None,
                num_dense_points=self._num_dense_points,
            )

        height_px, width_px = _VISTA_INPUT_RESOLUTION
        resized_rgb = cv2.resize(frame.rgb, (width_px, height_px), interpolation=cv2.INTER_LINEAR)
        grayscale = cv2.cvtColor(resized_rgb, cv2.COLOR_RGB2GRAY)
        is_keyframe = bool(self._flow_tracker.compute_disparity(grayscale, visualize=False))
        if not is_keyframe:
            return SlamUpdate(
                seq=frame.seq,
                timestamp_ns=frame.timestamp_ns,
                is_keyframe=False,
                keyframe_index=None,
                num_dense_points=self._num_dense_points,
            )

        import torch  # noqa: PLC0415

        rgb_float = torch.from_numpy(resized_rgb).permute(2, 0, 1).float() / 255.0
        value = {
            "rgb": rgb_float.unsqueeze(0).to(self._slam.device),
            "shape": torch.tensor(rgb_float.shape[1:3]).unsqueeze(0),
            "gray": grayscale,
            "view_name": f"frame_{self._accepted_keyframe_count:06d}",
        }
        self._slam.step(value)
        update = self._build_live_update(
            seq=frame.seq,
            timestamp_ns=frame.timestamp_ns,
            view_index=self._accepted_keyframe_count,
        )
        update.is_keyframe = True
        update.keyframe_index = self._accepted_keyframe_count
        self._accepted_keyframe_count += 1
        return update

    def close(self) -> SlamArtifacts:
        """Persist upstream outputs and convert to canonical repository artifacts."""
        run_paths = RunArtifactPaths.build(self._artifact_root)
        native_output_dir = run_paths.native_output_dir
        native_output_dir.mkdir(parents=True, exist_ok=True)
        self._slam.save_data_all(str(native_output_dir), save_images=False, save_depths=False)
        self._console.info(
            "ViSTA-SLAM session closed after %d frames; native outputs in '%s'.",
            self._source_frame_count,
            native_output_dir,
        )
        return _build_artifacts(
            native_output_dir=native_output_dir,
            artifact_root=self._artifact_root,
            output_policy=self._output_policy,
        )

    def _build_live_update(
        self,
        *,
        seq: int,
        timestamp_ns: int,
        view_index: int,
    ) -> SlamUpdate:
        """Read the latest upstream view state and convert it into live repo telemetry."""
        try:
            view = self._slam.get_view(
                view_index,
                filter_outlier=False,
                return_pose=True,
                return_depth=True,
                return_intri=True,
            )
        except (IndexError, KeyError, ValueError):
            if not self._live_preview_wait_logged:
                self._console.info("ViSTA-SLAM live preview is not ready yet; waiting for the pose graph to populate.")
                self._live_preview_wait_logged = True
            return SlamUpdate(
                seq=seq,
                timestamp_ns=timestamp_ns,
                is_keyframe=True,
                keyframe_index=view_index,
                num_sparse_points=0,
                num_dense_points=self._num_dense_points,
            )
        pose = FrameTransform.from_matrix(np.asarray(view.pose, dtype=np.float64))
        try:
            preview_rgb, pointmap = self._slam.get_pointmap_vis(view_index)
        except (IndexError, KeyError, ValueError):
            preview_rgb = None
            pointmap = None
        pointmap = _build_live_pointmap(pointmap)
        self._num_dense_points += _count_valid_pointmap_points(pointmap)
        self._live_preview_wait_logged = False
        return SlamUpdate(
            seq=seq,
            timestamp_ns=timestamp_ns,
            pose=pose,
            is_keyframe=True,
            keyframe_index=view_index,
            pose_updated=True,
            num_sparse_points=0,
            num_dense_points=self._num_dense_points,
            pointmap=pointmap if self._output_policy.emit_dense_points else None,
            preview_rgb=preview_rgb,
        )


class VistaSlamBackend(SlamBackend):
    """ViSTA-SLAM backend implementing offline and streaming contracts."""

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
        self._checkpoint_path = self._path_config.resolve_repo_path(config.checkpoint_path)
        self._vocab_path = self._path_config.resolve_repo_path(config.vocab_path)

    def start_session(
        self,
        backend_config: SlamBackendConfig,
        output_policy: SlamOutputPolicy,
        artifact_root: Path,
    ) -> VistaSlamSession:
        """Load upstream OnlineSLAM and return a ready streaming session."""
        del backend_config
        session = self._build_session(
            artifact_root=artifact_root,
            output_policy=output_policy,
            live_mode=True,
        )
        self._console.info("OnlineSLAM model loaded; session ready.")
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
        """Run ViSTA-SLAM over a materialized sequence and persist artifacts."""
        del benchmark_inputs, baseline_source
        frames_dir = self._resolve_frames(sequence, artifact_root, backend_config)
        image_paths = sorted(frames_dir.glob("*.png"))
        if backend_config.max_frames is not None:
            image_paths = image_paths[: backend_config.max_frames]

        session = self._build_session(
            artifact_root=artifact_root,
            output_policy=output_policy,
            live_mode=False,
        )
        self._console.info("Running ViSTA-SLAM on %d frames …", len(image_paths))
        for seq, image_path in enumerate(image_paths):
            bgr = cv2.imread(str(image_path))
            if bgr is None:
                raise RuntimeError(f"Failed to read input frame '{image_path}'.")
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            session.step(FramePacket(seq=seq, timestamp_ns=seq, rgb=rgb))
        return session.close()

    def _validate_prerequisites(self) -> None:
        """Raise a runtime error with actionable detail when dependencies are missing."""
        missing: list[str] = []
        if not self._vista_dir.exists():
            missing.append(f"vista-slam repo not found at '{self._vista_dir}'")
        if not self._checkpoint_path.exists():
            missing.append(
                f"STA checkpoint missing at '{self._checkpoint_path}' — download it from the upstream release."
            )
        if not self._vocab_path.exists():
            missing.append(f"ORB vocabulary missing at '{self._vocab_path}' — download it from the upstream release.")
        if missing:
            raise RuntimeError(
                "ViSTA-SLAM prerequisites not satisfied:\n" + "\n".join(f"  • {item}" for item in missing)
            )

    def _inject_sys_path(self) -> None:
        """Ensure the ViSTA submodule root is importable."""
        vista_root = str(self._vista_dir)
        if vista_root not in sys.path:
            sys.path.insert(0, vista_root)

    def _build_session(
        self,
        *,
        artifact_root: Path,
        output_policy: SlamOutputPolicy,
        live_mode: bool,
    ) -> VistaSlamSession:
        """Create one configured upstream OnlineSLAM session."""
        self._validate_prerequisites()
        self._inject_sys_path()
        self._preload_dbow3_shared_library()

        try:
            import torch  # noqa: PLC0415
            from vista_slam.flow_tracker import FlowTracker  # noqa: PLC0415
            from vista_slam.slam import OnlineSLAM  # noqa: PLC0415
        except Exception as exc:  # pragma: no cover - environment-dependent runtime guard
            raise RuntimeError(
                "Failed to import ViSTA-SLAM runtime dependencies. "
                "Verify the active environment satisfies external/vista-slam requirements "
                "(torch/xformers/CUDA stack and ViSTA python deps)."
            ) from exc

        torch.manual_seed(self._cfg.slam.random_seed)
        if live_mode:
            self._console.info(
                "Forcing upstream live defaults: max_view_num=1000, neighbor_edge_num=2, loop_edge_num=2, pgo_every=50."
            )
        slam = OnlineSLAM(
            ckpt_path=str(self._checkpoint_path),
            vocab_path=str(self._vocab_path),
            max_view_num=1000 if live_mode else self._cfg.slam.max_view_num,
            neighbor_edge_num=2 if live_mode else self._cfg.slam.neighbor_edge_num,
            loop_edge_num=2 if live_mode else self._cfg.slam.loop_edge_num,
            loop_dist_min=self._cfg.slam.loop_dist_min,
            loop_nms=self._cfg.slam.loop_nms,
            loop_cand_thresh_neighbor=self._cfg.slam.loop_cand_thresh_neighbor,
            conf_thres=self._cfg.slam.point_conf_thres,
            rel_pose_thres=self._cfg.slam.rel_pose_thres,
            flow_thres=self._cfg.slam.flow_thres,
            pgo_every=50 if live_mode else self._cfg.slam.pgo_every,
            live_mode=live_mode,
        )
        flow_tracker = FlowTracker(self._cfg.slam.flow_thres)
        return VistaSlamSession(
            slam=slam,
            flow_tracker=flow_tracker,
            artifact_root=artifact_root,
            output_policy=output_policy,
            console=self._console,
        )

    def _preload_dbow3_shared_library(self) -> None:
        """Load the bundled DBoW3 shared library before importing DBoW3Py."""
        candidates = [
            Path(package_dir) / "libDBoW3.so.0.0"
            for package_dir in (
                *site.getsitepackages(),
                site.getusersitepackages(),
            )
        ]
        candidates.extend(self._vista_dir.glob("DBoW3Py/build/**/libDBoW3.so.0.0"))
        for candidate in candidates:
            if candidate.exists():
                try:
                    ctypes.CDLL(str(candidate), mode=ctypes.RTLD_GLOBAL)
                except OSError:
                    continue
                return

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
                "SequenceManifest has no usable frame source: set `rgb_dir` or provide an existing `video_path`."
            )
        frames_dir = RunArtifactPaths.build(artifact_root).input_frames_dir
        return self._extract_video_frames(sequence.video_path, frames_dir, backend_config.max_frames)

    def _extract_video_frames(self, video_path: Path, output_dir: Path, max_frames: int | None) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        existing_frames = sorted(output_dir.glob("*.png"))
        if existing_frames and (max_frames is None or len(existing_frames) >= max_frames):
            self._console.info("Reusing %d pre-extracted frames in '%s'.", len(existing_frames), output_dir)
            return output_dir

        for stale_frame in output_dir.glob("*.png"):
            stale_frame.unlink()

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


def _build_artifacts(
    *,
    native_output_dir: Path,
    artifact_root: Path,
    output_policy: SlamOutputPolicy,
) -> SlamArtifacts:
    """Normalize native ViSTA outputs into repository-owned artifact contracts."""
    trajectory_npy = native_output_dir / "trajectory.npy"
    if not trajectory_npy.exists():
        raise RuntimeError(f"Expected trajectory file not found: '{trajectory_npy}'.")
    trajectory_se3 = np.load(trajectory_npy).astype(np.float64)
    poses = [FrameTransform.from_matrix(transform) for transform in trajectory_se3]
    timestamps_s = [float(index) for index in range(len(poses))]
    trajectory_path = write_tum_trajectory(artifact_root / "slam" / "trajectory.tum", poses, timestamps_s)

    sparse_points_ref: ArtifactRef | None = None
    dense_points_ref: ArtifactRef | None = None
    pointcloud_ply = native_output_dir / "pointcloud.ply"
    if pointcloud_ply.exists() and (output_policy.emit_sparse_points or output_policy.emit_dense_points):
        point_cloud = o3d.io.read_point_cloud(str(pointcloud_ply))
        points_xyz = np.asarray(point_cloud.points, dtype=np.float64)
        if output_policy.emit_sparse_points:
            sparse_points_path = write_point_cloud_ply(artifact_root / "slam" / "sparse_points.ply", points_xyz)
            sparse_points_ref = ArtifactRef(
                path=sparse_points_path,
                kind="ply",
                fingerprint=f"vista-sparse-{len(points_xyz)}",
            )
        if output_policy.emit_dense_points:
            dense_points_path = write_point_cloud_ply(artifact_root / "dense" / "dense_points.ply", points_xyz)
            dense_points_ref = ArtifactRef(
                path=dense_points_path,
                kind="ply",
                fingerprint=f"vista-dense-{len(points_xyz)}",
            )

    native_rerun_path = native_output_dir / "rerun_recording.rrd"
    extras = {
        path.name: ArtifactRef(
            path=path.resolve(),
            kind=path.suffix.lstrip(".") or "file",
            fingerprint=f"vista-extra-{path.name}",
        )
        for path in sorted(native_output_dir.glob("*"))
        if path.is_file() and path.name not in {"trajectory.npy", "pointcloud.ply", "rerun_recording.rrd"}
    }
    return SlamArtifacts(
        trajectory_tum=ArtifactRef(
            path=trajectory_path,
            kind="tum",
            fingerprint=f"vista-traj-{len(trajectory_se3)}",
        ),
        sparse_points_ply=sparse_points_ref,
        dense_points_ply=dense_points_ref,
        native_rerun_rrd=(
            None
            if not native_rerun_path.exists()
            else ArtifactRef(path=native_rerun_path.resolve(), kind="rrd", fingerprint="vista-native-rerun")
        ),
        native_output_dir=ArtifactRef(path=native_output_dir.resolve(), kind="dir", fingerprint="vista-native-output"),
        extras=extras,
    )


def _build_live_pointmap(view: object) -> np.ndarray | None:
    """Convert one upstream pointcloud payload into the repository-local dtype."""
    if view is None:
        return None
    return np.asarray(view, dtype=np.float32)


def _count_valid_pointmap_points(pointmap: np.ndarray | None) -> int:
    """Count valid metric points in one pointmap."""
    if pointmap is None:
        return 0
    depth = np.asarray(pointmap[..., 2], dtype=np.float32)
    return int(np.count_nonzero(np.isfinite(depth) & (depth > 0.0)))


__all__ = ["VistaSlamBackend", "VistaSlamSession"]
