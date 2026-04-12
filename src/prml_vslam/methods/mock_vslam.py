"""Repository-local mock SLAM backend used by the interactive pipeline demo."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from prml_vslam.datasets.advio import load_advio_calibration
from prml_vslam.interfaces import CameraIntrinsics, FramePacket, SE3Pose
from prml_vslam.methods.contracts import MethodId, SlamBackendConfig, SlamOutputPolicy
from prml_vslam.methods.protocols import SlamBackend, SlamSession
from prml_vslam.methods.updates import SlamUpdate
from prml_vslam.pipeline.contracts.artifacts import ArtifactRef, SlamArtifacts
from prml_vslam.pipeline.contracts.sequence import SequenceManifest
from prml_vslam.utils import BaseConfig
from prml_vslam.utils.geometry import (
    load_tum_trajectory,
    pointmap_from_depth,
    transform_points_world_camera,
    write_point_cloud_ply,
    write_tum_trajectory,
)

_STEP_DISTANCE_M = 0.05
_POINTMAP_STRIDE_PX = 16
_POINTMAP_BASE_DEPTH_M = 1.5
_POINTMAP_DEPTH_SPAN_M = 1.0


class MockSlamBackendConfig(BaseConfig):
    """Config that builds the repository-local mock SLAM backend."""

    method_id: MethodId = MethodId.VISTA
    """Selected mock backend label."""

    @property
    def target_type(self) -> type[MockSlamBackend]:
        """Return the mock backend type used for the pipeline demo."""
        return MockSlamBackend


class MockSlamBackend(SlamBackend):
    """Mock SLAM backend that supports both batch and streaming execution."""

    def __init__(self, config: MockSlamBackendConfig) -> None:
        self.config = config
        self.method_id = config.method_id

    def start_session(
        self,
        backend_config: SlamBackendConfig,
        output_policy: SlamOutputPolicy,
        artifact_root: Path,
    ) -> MockSlamSession:
        """Prepare one streaming-capable session."""
        return MockSlamSession(backend_config=backend_config, output_policy=output_policy, artifact_root=artifact_root)

    def run_sequence(
        self,
        sequence: SequenceManifest,
        backend_config: SlamBackendConfig,
        output_policy: SlamOutputPolicy,
        artifact_root: Path,
    ) -> SlamArtifacts:
        """Run the mock backend over a materialized sequence manifest offline."""
        session = self.start_session(backend_config, output_policy, artifact_root)
        intrinsics = _load_sequence_intrinsics(sequence)
        reference_path = sequence.reference_tum_path or sequence.arcore_tum_path
        if reference_path is not None and reference_path.exists():
            trajectory = load_tum_trajectory(reference_path)
            pointmap = session.build_pointmap(intrinsics=intrinsics)
            for seq, timestamp_s in enumerate(np.asarray(trajectory.timestamps, dtype=np.float64).tolist()):
                session.record_pose_sample(
                    seq=seq,
                    timestamp_ns=int(round(timestamp_s * 1e9)),
                    pose=SE3Pose.from_matrix(np.asarray(trajectory.poses_se3[seq], dtype=np.float64)),
                    used_source_pose=True,
                    pointmap=pointmap,
                )
        else:
            session.record_pose_sample(
                seq=0,
                timestamp_ns=0,
                pose=session.fallback_pose(),
                used_source_pose=False,
                pointmap=session.build_pointmap(intrinsics=intrinsics),
            )
        return session.close()


class MockSlamSession(SlamSession):
    """Stateful mock SLAM session shared by offline and streaming execution."""

    def __init__(
        self,
        *,
        backend_config: SlamBackendConfig,
        output_policy: SlamOutputPolicy,
        artifact_root: Path,
    ) -> None:
        self.backend_config = backend_config
        self.output_policy = output_policy
        self._artifact_root = artifact_root.expanduser().resolve()
        self._poses: list[SE3Pose] = []
        self._timestamps_s: list[float] = []
        self._dense_point_chunks_xyz: list[NDArray[np.float64]] = []
        self._num_dense_points = 0

    def step(self, frame: FramePacket) -> SlamUpdate:
        """Consume one frame and return a deterministic incremental SLAM update."""
        pose = frame.pose if frame.pose is not None else self.fallback_pose()
        pointmap = self.build_pointmap(frame=frame)
        return self.record_pose_sample(
            seq=frame.seq,
            timestamp_ns=frame.timestamp_ns,
            pose=pose,
            used_source_pose=frame.pose is not None,
            pointmap=pointmap,
        )

    def close(self) -> SlamArtifacts:
        """Finalize the current run and persist the minimal SLAM artifacts."""
        trajectory_path = write_tum_trajectory(
            self._artifact_root / "slam" / "trajectory.tum",
            self._poses,
            self._timestamps_s,
        )
        sparse_points_ref = None
        if self.output_policy.emit_sparse_points:
            sparse_points_path = write_point_cloud_ply(
                self._artifact_root / "slam" / "sparse_points.ply",
                np.asarray([(pose.tx, pose.ty, pose.tz) for pose in self._poses], dtype=np.float64)
                if self._poses
                else np.empty((0, 3), dtype=np.float64),
            )
            sparse_points_ref = _artifact_ref(
                sparse_points_path,
                kind="ply",
                fingerprint=f"sparse-points-{len(self._poses)}",
            )

        dense_points_ref = None
        if self.output_policy.emit_dense_points:
            dense_points_path = write_point_cloud_ply(
                self._artifact_root / "dense" / "dense_points.ply",
                np.vstack(self._dense_point_chunks_xyz)
                if self._dense_point_chunks_xyz
                else np.empty((0, 3), dtype=np.float64),
            )
            dense_points_ref = _artifact_ref(
                dense_points_path,
                kind="ply",
                fingerprint=f"dense-points-{self._num_dense_points}",
            )

        return SlamArtifacts(
            trajectory_tum=_artifact_ref(
                trajectory_path,
                kind="tum",
                fingerprint=f"trajectory-{len(self._poses)}",
            ),
            sparse_points_ply=sparse_points_ref,
            dense_points_ply=dense_points_ref,
        )

    def fallback_pose(self) -> SE3Pose:
        """Build the next fallback pose when no source pose is available."""
        previous_pose = self._poses[-1] if self._poses else None
        tx = _STEP_DISTANCE_M if previous_pose is None else previous_pose.tx + _STEP_DISTANCE_M
        ty = 0.0 if previous_pose is None else previous_pose.ty
        tz = 0.0 if previous_pose is None else previous_pose.tz
        return SE3Pose(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=tx, ty=ty, tz=tz)

    def record_pose_sample(
        self,
        *,
        seq: int,
        timestamp_ns: int,
        pose: SE3Pose,
        used_source_pose: bool,
        pointmap: NDArray[np.float32] | None = None,
    ) -> SlamUpdate:
        """Record one pose sample and return the matching SLAM update."""
        timestamp_s = self._normalize_timestamp_seconds(timestamp_ns / 1e9)
        self._poses.append(pose)
        self._timestamps_s.append(timestamp_s)

        if self.output_policy.emit_dense_points:
            camera_points = pointmap.reshape(-1, 3) if pointmap is not None else self._synthetic_local_patch_camera()
            self._append_dense_points(transform_points_world_camera(camera_points, pose))

        num_sparse_points = max(len(self._poses) * 12, 12) if self.output_policy.emit_sparse_points else 0
        return SlamUpdate(
            seq=seq,
            timestamp_ns=timestamp_ns,
            pose=pose,
            is_keyframe=True,
            pose_updated=True,
            num_sparse_points=num_sparse_points,
            num_dense_points=self._num_dense_points,
            pointmap=pointmap,
        )

    def _append_dense_points(self, points_xyz_world: NDArray[np.float64] | None) -> None:
        if points_xyz_world is None or points_xyz_world.size == 0:
            return
        finite_points = points_xyz_world[np.all(np.isfinite(points_xyz_world), axis=1)]
        if len(finite_points) == 0:
            return
        self._dense_point_chunks_xyz.append(finite_points)
        self._num_dense_points += int(len(finite_points))

    def _normalize_timestamp_seconds(self, timestamp_s: float) -> float:
        if not self._timestamps_s:
            return float(timestamp_s)
        return max(float(timestamp_s), self._timestamps_s[-1] + 1e-3)

    def build_pointmap(
        self,
        *,
        frame: FramePacket | None = None,
        intrinsics: CameraIntrinsics | None = None,
    ) -> NDArray[np.float32] | None:
        """Resolve one mock-SLAM pointmap from depth or known camera intrinsics."""
        resolved_intrinsics = (
            intrinsics if intrinsics is not None else (frame.intrinsics if frame is not None else None)
        )
        if resolved_intrinsics is None:
            return None

        depth_map = _resolve_depth_map(frame=frame, intrinsics=resolved_intrinsics)
        return pointmap_from_depth(depth_map, resolved_intrinsics, stride_px=_POINTMAP_STRIDE_PX)

    def _synthetic_local_patch_camera(self) -> NDArray[np.float32]:
        offsets_x, offsets_y = np.meshgrid(
            np.linspace(-0.25, 0.25, 4, dtype=np.float32),
            np.linspace(-0.15, 0.15, 3, dtype=np.float32),
            indexing="xy",
        )
        depth_m = np.full_like(offsets_x, fill_value=_POINTMAP_BASE_DEPTH_M)
        return np.stack([offsets_x, offsets_y, depth_m], axis=-1).reshape(-1, 3)


def _load_sequence_intrinsics(sequence: SequenceManifest) -> CameraIntrinsics | None:
    if sequence.intrinsics_path is None:
        return None
    return load_advio_calibration(sequence.intrinsics_path).intrinsics


def _resolve_depth_map(
    *,
    frame: FramePacket | None,
    intrinsics: CameraIntrinsics,
) -> NDArray[np.float32]:
    if frame is not None and frame.depth is not None:
        return np.asarray(frame.depth, dtype=np.float32)
    height_px = intrinsics.height_px if intrinsics.height_px is not None else None
    width_px = intrinsics.width_px if intrinsics.width_px is not None else None
    if frame is not None and frame.rgb is not None:
        height_px, width_px = frame.rgb.shape[:2]
    if height_px is None or width_px is None:
        raise ValueError("Mock pointmap generation requires image dimensions in the frame or camera intrinsics.")

    normalized_y = np.linspace(0.0, 1.0, height_px, dtype=np.float32)[:, None]
    depth_map = _POINTMAP_BASE_DEPTH_M + _POINTMAP_DEPTH_SPAN_M * (1.0 - normalized_y)
    depth_map = np.repeat(depth_map, width_px, axis=1)
    if frame is not None and frame.rgb is not None:
        grayscale = np.asarray(frame.rgb, dtype=np.float32).mean(axis=2) / 255.0
        depth_map = depth_map + 0.1 * (0.5 - grayscale)
    return depth_map.astype(np.float32, copy=False)


def _artifact_ref(path: Path, *, kind: str, fingerprint: str) -> ArtifactRef:
    return ArtifactRef(path=path, kind=kind, fingerprint=fingerprint)


__all__ = ["MockSlamBackend", "MockSlamBackendConfig", "MockSlamSession"]
