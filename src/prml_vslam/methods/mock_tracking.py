"""Incremental mock tracking runtime used by the interactive pipeline demo."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from prml_vslam.interfaces import FramePacket, SE3Pose
from prml_vslam.methods.interfaces import MethodId
from prml_vslam.pipeline.contracts import ArtifactRef, TrackingArtifacts, TrackingConfig
from prml_vslam.pipeline.interfaces import TrackingUpdate
from prml_vslam.utils import BaseConfig
from prml_vslam.utils.geometry import write_tum_trajectory


class MockTrackingRuntimeConfig(BaseConfig):
    """Config that builds the incremental mock tracking runtime."""

    method_id: MethodId = MethodId.VISTA
    """Mock backend label shown in plans and artifact paths."""

    step_distance_m: float = 0.05
    """Fallback translation increment when the input stream does not provide a pose."""

    @property
    def target_type(self) -> type[MockTrackingRuntime]:
        """Return the runtime type used for the interactive pipeline demo."""
        return MockTrackingRuntime


class MockTrackingRuntime:
    """Incremental mock tracker that mirrors source poses and persists small artifacts."""

    def __init__(self, config: MockTrackingRuntimeConfig) -> None:
        self.config = config
        self.method_id = config.method_id
        self._artifact_root: Path | None = None
        self._tracking_config: TrackingConfig | None = None
        self._poses: list[SE3Pose] = []
        self._timestamps_s: list[float] = []
        self._preview_events: list[dict[str, object]] = []

    def open(self, cfg: TrackingConfig, artifact_root: Path) -> None:
        """Prepare the runtime for a new tracked session."""
        self._artifact_root = artifact_root.expanduser().resolve()
        self._tracking_config = cfg
        self._poses = []
        self._timestamps_s = []
        self._preview_events = []

    def step(self, frame: FramePacket) -> TrackingUpdate:
        """Consume one frame and return a deterministic tracking update."""
        self._require_open()
        pose = frame.pose if frame.pose is not None else self._fallback_pose()
        timestamp_s = self._normalize_timestamp_seconds(frame.timestamp_ns / 1e9)
        self._poses.append(pose)
        self._timestamps_s.append(timestamp_s)

        num_map_points = max(len(self._poses) * 12, 12)
        self._preview_events.append(
            {
                "seq": frame.seq,
                "timestamp_ns": frame.timestamp_ns,
                "timestamp_s": timestamp_s,
                "num_map_points": num_map_points,
                "used_source_pose": frame.pose is not None,
                "tx": pose.tx,
                "ty": pose.ty,
                "tz": pose.tz,
            }
        )
        return TrackingUpdate(
            seq=frame.seq,
            timestamp_ns=frame.timestamp_ns,
            pose=pose,
            num_map_points=num_map_points,
        )

    def close(self) -> TrackingArtifacts:
        """Finalize the current run and persist the minimal tracking artifacts."""
        artifact_root = self._require_open()
        trajectory_path = write_tum_trajectory(
            artifact_root / "slam" / "trajectory.tum", self._poses, self._timestamps_s
        )
        sparse_points_path = self._write_sparse_points(artifact_root / "slam" / "sparse_points.ply")
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
        )
        self._artifact_root = None
        self._tracking_config = None
        return artifacts

    def _require_open(self) -> Path:
        if self._artifact_root is None or self._tracking_config is None:
            raise RuntimeError("MockTrackingRuntime.open() must be called before tracking frames.")
        return self._artifact_root

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

    def _write_sparse_points(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        positions = (
            np.asarray([(pose.tx, pose.ty, pose.tz) for pose in self._poses], dtype=np.float64)
            if self._poses
            else np.empty((0, 3), dtype=np.float64)
        )
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

    @staticmethod
    def _artifact_ref(path: Path, *, kind: str, fingerprint: str) -> ArtifactRef:
        return ArtifactRef(path=path, kind=kind, fingerprint=fingerprint)


__all__ = ["MockTrackingRuntime", "MockTrackingRuntimeConfig"]
