"""Incremental mock tracking runtime used by the interactive pipeline demo."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from prml_vslam.interfaces import FramePacket, SE3Pose
from prml_vslam.methods.interfaces import MethodId
from prml_vslam.pipeline.contracts import (
    ArtifactRef,
    DenseArtifacts,
    SequenceManifest,
    TrackingArtifacts,
    TrackingConfig,
)
from prml_vslam.pipeline.interfaces import OfflineTrackerBackend, StreamingTrackerBackend, TrackingUpdate
from prml_vslam.utils import BaseConfig
from prml_vslam.utils.geometry import write_tum_trajectory


class MockTrackingRuntimeConfig(BaseConfig):
    """Config that builds the incremental mock tracking runtime."""

    method_id: MethodId = MethodId.VISTA
    """Mock backend label shown in plans and artifact paths."""

    step_distance_m: float = 0.05
    """Fallback translation increment when the input stream does not provide a pose."""

    pointmap_stride_px: int = 16
    """Pixel stride used when synthesizing the mock per-frame pointmap preview."""

    pointmap_base_depth_m: float = 1.5
    """Base camera-space depth used for the synthetic pointmap."""

    pointmap_depth_span_m: float = 1.0
    """Additional depth variation inferred from image intensity."""

    @property
    def target_type(self) -> type[MockTrackingRuntime]:
        """Return the runtime type used for the interactive pipeline demo."""
        return MockTrackingRuntime


class MockTrackingRuntime(OfflineTrackerBackend, StreamingTrackerBackend):
    """Mock tracker that supports both offline and incremental tracking contracts."""

    def __init__(self, config: MockTrackingRuntimeConfig) -> None:
        self.config = config
        self.method_id = config.method_id
        self._artifact_root: Path | None = None
        self._tracking_config: TrackingConfig | None = None
        self._poses: list[SE3Pose] = []
        self._timestamps_s: list[float] = []
        self._preview_events: list[dict[str, object]] = []
        self._dense_point_chunks_xyz: list[NDArray[np.float64]] = []
        self._num_dense_points: int = 0

    def open(self, cfg: TrackingConfig, artifact_root: Path) -> None:
        """Prepare the runtime for a new tracked session."""
        self._artifact_root = artifact_root.expanduser().resolve()
        self._tracking_config = cfg
        self._poses = []
        self._timestamps_s = []
        self._preview_events = []
        self._dense_point_chunks_xyz = []
        self._num_dense_points = 0

    def step(self, frame: FramePacket) -> TrackingUpdate:
        """Consume one frame and return a deterministic tracking update."""
        self._require_open()
        pose = frame.pose if frame.pose is not None else self._fallback_pose()
        pointmap = self._build_pointmap(frame)
        self._append_dense_points(self._world_points_from_frame(frame=frame, pose=pose, pointmap=pointmap))
        return self._append_pose(
            seq=frame.seq,
            timestamp_ns=frame.timestamp_ns,
            pose=pose,
            used_source_pose=frame.pose is not None,
            pointmap=pointmap,
        )

    def run_sequence(
        self,
        sequence: SequenceManifest,
        cfg: TrackingConfig,
        artifact_root: Path,
    ) -> TrackingArtifacts:
        """Run the mock tracker over a materialized sequence manifest offline."""
        self.open(cfg, artifact_root)
        for seq, timestamp_s, pose, used_source_pose in self._offline_samples(sequence):
            self._append_dense_points(self._world_points_from_pose(self._synthetic_local_patch_camera(), pose))
            self._append_pose(
                seq=seq,
                timestamp_ns=int(round(timestamp_s * 1e9)),
                pose=pose,
                used_source_pose=used_source_pose,
            )
        return self.close()

    def close(self) -> TrackingArtifacts:
        """Finalize the current run and persist the minimal tracking artifacts."""
        artifact_root = self._require_open()
        trajectory_path = write_tum_trajectory(
            artifact_root / "slam" / "trajectory.tum", self._poses, self._timestamps_s
        )
        sparse_points_path = self._write_sparse_points(artifact_root / "slam" / "sparse_points.ply")
        dense_points_path = self._write_dense_points(artifact_root / "dense" / "dense_points.ply")
        preview_log_path = self._write_preview_log(artifact_root / "slam" / "preview_log.jsonl")
        processed_frames = len(self._poses)
        artifacts = TrackingArtifacts(
            trajectory_tum=self._artifact_ref(
                trajectory_path, kind="tum", fingerprint=f"trajectory-{processed_frames}"
            ),
            sparse_points_ply=self._artifact_ref(
                sparse_points_path,
                kind="ply",
                fingerprint=f"sparse-points-{processed_frames}",
            ),
            preview_log_jsonl=self._artifact_ref(
                preview_log_path,
                kind="jsonl",
                fingerprint=f"preview-log-{processed_frames}",
            ),
            dense=DenseArtifacts(
                dense_points_ply=self._artifact_ref(
                    dense_points_path,
                    kind="ply",
                    fingerprint=f"dense-points-{self._num_dense_points}",
                )
            ),
        )
        self._artifact_root = None
        self._tracking_config = None
        return artifacts

    def _require_open(self) -> Path:
        if self._artifact_root is None or self._tracking_config is None:
            raise RuntimeError("MockTrackingRuntime.open() must be called before tracking frames.")
        return self._artifact_root

    def _append_pose(
        self,
        *,
        seq: int,
        timestamp_ns: int,
        pose: SE3Pose,
        used_source_pose: bool,
        pointmap: NDArray[np.float32] | None = None,
    ) -> TrackingUpdate:
        timestamp_s = self._normalize_timestamp_seconds(timestamp_ns / 1e9)
        self._poses.append(pose)
        self._timestamps_s.append(timestamp_s)
        num_map_points = max(len(self._poses) * 12, 12)
        self._preview_events.append(
            {
                "seq": seq,
                "timestamp_ns": timestamp_ns,
                "timestamp_s": timestamp_s,
                "num_map_points": num_map_points,
                "num_dense_points": self._num_dense_points,
                "used_source_pose": used_source_pose,
                "tx": pose.tx,
                "ty": pose.ty,
                "tz": pose.tz,
            }
        )
        return TrackingUpdate(
            seq=seq,
            timestamp_ns=timestamp_ns,
            pose=pose,
            num_map_points=num_map_points,
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

    def _fallback_pose(self) -> SE3Pose:
        previous_pose = self._poses[-1] if self._poses else None
        tx = self.config.step_distance_m if previous_pose is None else previous_pose.tx + self.config.step_distance_m
        ty = 0.0 if previous_pose is None else previous_pose.ty
        tz = 0.0 if previous_pose is None else previous_pose.tz
        return SE3Pose(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=tx, ty=ty, tz=tz)

    def _normalize_timestamp_seconds(self, timestamp_s: float) -> float:
        if not self._timestamps_s:
            return float(timestamp_s)
        return max(float(timestamp_s), self._timestamps_s[-1] + 1e-3)

    def _offline_samples(self, sequence: SequenceManifest) -> list[tuple[int, float, SE3Pose, bool]]:
        reference_path = sequence.reference_tum_path or sequence.arcore_tum_path
        if reference_path is not None and reference_path.exists():
            return [
                (seq, timestamp_s, pose, True)
                for seq, (timestamp_s, pose) in enumerate(self._load_tum_sequence(reference_path))
            ]
        return [(0, 0.0, self._fallback_pose(), False)]

    @staticmethod
    def _load_tum_sequence(path: Path) -> list[tuple[float, SE3Pose]]:
        rows: list[tuple[float, SE3Pose]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            values = stripped.split()
            if len(values) != 8:
                raise ValueError(f"Expected 8 columns in TUM trajectory row, got {len(values)}: {stripped}")
            timestamp_s, tx, ty, tz, qx, qy, qz, qw = (float(value) for value in values)
            rows.append(
                (
                    timestamp_s,
                    SE3Pose(qx=qx, qy=qy, qz=qz, qw=qw, tx=tx, ty=ty, tz=tz),
                )
            )
        return rows

    def _write_sparse_points(self, path: Path) -> Path:
        positions = (
            np.asarray([(pose.tx, pose.ty, pose.tz) for pose in self._poses], dtype=np.float64)
            if self._poses
            else np.empty((0, 3), dtype=np.float64)
        )
        return self._write_points_ply(path, positions)

    def _write_dense_points(self, path: Path) -> Path:
        positions = (
            np.vstack(self._dense_point_chunks_xyz)
            if self._dense_point_chunks_xyz
            else np.empty((0, 3), dtype=np.float64)
        )
        return self._write_points_ply(path, positions)

    def _write_points_ply(self, path: Path, positions: NDArray[np.float64]) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "ply",
            "format ascii 1.0",
            f"element vertex {len(positions)}",
            "property float x",
            "property float y",
            "property float z",
            "end_header",
        ]
        if len(positions):
            lines.extend(f"{row[0]:.6f} {row[1]:.6f} {row[2]:.6f}" for row in positions)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path.resolve()

    def _write_preview_log(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "\n".join(json.dumps(event, sort_keys=True) for event in self._preview_events) + "\n",
            encoding="utf-8",
        )
        return path.resolve()

    def _build_pointmap(self, frame: FramePacket) -> NDArray[np.float32] | None:
        if frame.intrinsics is None:
            return None
        if frame.rgb is not None:
            height_px, width_px = frame.rgb.shape[:2]
        elif frame.intrinsics.height_px is not None and frame.intrinsics.width_px is not None:
            height_px = frame.intrinsics.height_px
            width_px = frame.intrinsics.width_px
        else:
            return None
        stride_px = max(self.config.pointmap_stride_px, 1)
        rows_px = np.arange(0, height_px, stride_px, dtype=np.float32)
        cols_px = np.arange(0, width_px, stride_px, dtype=np.float32)
        grid_y_px, grid_x_px = np.meshgrid(rows_px, cols_px, indexing="ij")
        normalized_y = grid_y_px / max(float(height_px - 1), 1.0)
        depth_m = self.config.pointmap_base_depth_m + self.config.pointmap_depth_span_m * (1.0 - normalized_y)
        pointmap_camera = np.stack(
            [
                (grid_x_px - frame.intrinsics.cx) / frame.intrinsics.fx * depth_m,
                (grid_y_px - frame.intrinsics.cy) / frame.intrinsics.fy * depth_m,
                depth_m,
            ],
            axis=-1,
        ).astype(np.float32)
        if not np.all(np.isfinite(pointmap_camera)):
            raise ValueError(f"Mock pointmap generation produced non-finite values for frame {frame.seq}.")
        return pointmap_camera

    def _world_points_from_frame(
        self,
        *,
        frame: FramePacket,
        pose: SE3Pose,
        pointmap: NDArray[np.float32] | None,
    ) -> NDArray[np.float64] | None:
        if pointmap is not None:
            return self._world_points_from_pose(pointmap.reshape(-1, 3), pose)
        return self._world_points_from_pose(self._synthetic_local_patch_camera(), pose)

    @staticmethod
    def _world_points_from_pose(
        points_xyz_camera: NDArray[np.float32] | NDArray[np.float64], pose: SE3Pose
    ) -> NDArray[np.float64]:
        if points_xyz_camera.size == 0:
            return np.empty((0, 3), dtype=np.float64)
        homogeneous_points = np.concatenate(
            [np.asarray(points_xyz_camera, dtype=np.float64), np.ones((len(points_xyz_camera), 1), dtype=np.float64)],
            axis=1,
        )
        transform_world_camera = pose.as_matrix()
        return (transform_world_camera @ homogeneous_points.T).T[:, :3]

    def _synthetic_local_patch_camera(self) -> NDArray[np.float32]:
        offsets_x, offsets_y = np.meshgrid(
            np.linspace(-0.25, 0.25, 4, dtype=np.float32),
            np.linspace(-0.15, 0.15, 3, dtype=np.float32),
            indexing="xy",
        )
        depth_m = np.full_like(offsets_x, fill_value=self.config.pointmap_base_depth_m)
        return np.stack([offsets_x, offsets_y, depth_m], axis=-1).reshape(-1, 3)

    @staticmethod
    def _artifact_ref(path: Path, *, kind: str, fingerprint: str) -> ArtifactRef:
        return ArtifactRef(path=path, kind=kind, fingerprint=fingerprint)


__all__ = ["MockTrackingRuntime", "MockTrackingRuntimeConfig"]
