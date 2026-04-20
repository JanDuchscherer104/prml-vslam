"""Repository-local mock SLAM backend used by the interactive pipeline demo.

The mock backend is the simplest complete implementation of the method-layer
contracts. It replays prepared benchmark references through the same normalized
seams as real wrappers, which makes it useful both as a smoke-test backend and
as a readable example of how :mod:`prml_vslam.methods` connects to
:mod:`prml_vslam.pipeline`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from evo.core.trajectory import PoseTrajectory3D
from numpy.typing import NDArray
from pytransform3d.transformations import transform, vectors_to_points

from prml_vslam.benchmark import (
    PreparedBenchmarkInputs,
    ReferenceCloudCoordinateStatus,
    ReferenceCloudSource,
    ReferencePointCloudSequenceRef,
    ReferenceSource,
)
from prml_vslam.datasets.advio import load_advio_calibration
from prml_vslam.datasets.advio.advio_geometry import (
    Sim3Alignment,
    apply_sim3,
    fit_sim3_alignment,
    interpolate_trajectory_poses,
    load_tango_point_cloud_index,
    load_tango_point_cloud_payload,
    resolve_tango_point_cloud_payload,
)
from prml_vslam.interfaces import CameraIntrinsics, FramePacket, FrameTransform
from prml_vslam.methods.configs import MockSlamBackendConfig
from prml_vslam.methods.contracts import SlamBackendConfig, SlamOutputPolicy
from prml_vslam.methods.protocols import SlamBackend, SlamSession
from prml_vslam.methods.session_init import SlamSessionInit
from prml_vslam.methods.updates import SlamUpdate
from prml_vslam.pipeline.contracts.artifacts import ArtifactRef, SlamArtifacts
from prml_vslam.pipeline.contracts.sequence import SequenceManifest
from prml_vslam.utils.geometry import (
    load_point_cloud_ply,
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
_REFERENCE_PAYLOAD_MAX_TIME_DIFF_S = 0.15
_PREFERRED_REFERENCE_CLOUD_SOURCES = (
    ReferenceCloudSource.TANGO_AREA_LEARNING,
    ReferenceCloudSource.TANGO_RAW,
)


@dataclass(frozen=True, slots=True)
class _PointCloudSequenceRuntime:
    reference: ReferencePointCloudSequenceRef
    trajectory: PoseTrajectory3D
    index_rows: NDArray[np.float64]
    alignment: Sim3Alignment


class MockSlamBackend(SlamBackend):
    """Implement the full method contract with deterministic reference replay."""

    def __init__(self, config: MockSlamBackendConfig) -> None:
        self.config = config
        self.method_id = config.method_id

    def start_session(
        self,
        session_init: SlamSessionInit,
        backend_config: SlamBackendConfig,
        output_policy: SlamOutputPolicy,
        artifact_root: Path,
    ) -> MockSlamSession:
        """Prepare one streaming-capable mock session over normalized repository inputs."""
        return MockSlamSession(
            config=self.config,
            session_init=session_init,
            backend_config=backend_config,
            output_policy=output_policy,
            artifact_root=artifact_root,
        )

    def run_sequence(
        self,
        sequence: SequenceManifest,
        benchmark_inputs: PreparedBenchmarkInputs | None,
        baseline_source: ReferenceSource,
        *,
        backend_config: SlamBackendConfig,
        output_policy: SlamOutputPolicy,
        artifact_root: Path,
    ) -> SlamArtifacts:
        """Run the mock backend over a materialized sequence manifest offline."""
        session = self.start_session(
            session_init=SlamSessionInit(
                sequence_manifest=sequence,
                benchmark_inputs=benchmark_inputs,
                baseline_source=baseline_source,
            ),
            backend_config=backend_config,
            output_policy=output_policy,
            artifact_root=artifact_root,
        )
        session.replay_offline()
        return session.close()


class MockSlamSession(SlamSession):
    """Replay prepared references through the streaming session contract.

    The session demonstrates the method-layer lifecycle end to end: it consumes
    normalized inputs, emits :class:`SlamUpdate` telemetry, and closes into
    normalized :class:`prml_vslam.pipeline.SlamArtifacts`.
    """

    def __init__(
        self,
        *,
        config: MockSlamBackendConfig,
        session_init: SlamSessionInit,
        backend_config: SlamBackendConfig,
        output_policy: SlamOutputPolicy,
        artifact_root: Path,
    ) -> None:
        self.config = config
        self._sequence_manifest = session_init.sequence_manifest
        self._baseline_source = session_init.baseline_source
        self.backend_config = backend_config
        self.output_policy = output_policy
        self._artifact_root = artifact_root.expanduser().resolve()
        self._poses: list[FrameTransform] = []
        self._timestamps_s: list[float] = []
        self._dense_point_chunks_xyz: list[NDArray[np.float64]] = []
        self._num_dense_points = 0
        self._pending_updates: list[SlamUpdate] = []
        self._rng = np.random.default_rng(config.random_seed)
        self._sequence_intrinsics = _load_sequence_intrinsics(self._sequence_manifest)
        self._reference_trajectory = _load_reference_trajectory(
            session_init.benchmark_inputs,
            self._baseline_source,
        )
        self._reference_point_cloud_sequence = _load_reference_point_cloud_sequence(
            benchmark_inputs=session_init.benchmark_inputs,
            baseline_source=self._baseline_source,
            reference_trajectory=self._reference_trajectory,
        )
        self._static_reference_points_xyz_world = _load_static_reference_points_xyz_world(
            benchmark_inputs=session_init.benchmark_inputs,
            baseline_source=self._baseline_source,
        )

    def replay_offline(self) -> None:
        """Replay prepared benchmark references through the offline backend seam."""
        timestamps_ns = _load_sequence_timestamps_ns(self._sequence_manifest)
        if timestamps_ns is not None and self.backend_config.max_frames is not None:
            timestamps_ns = timestamps_ns[: self.backend_config.max_frames]

        if self._reference_trajectory is None:
            self.record_pose_sample(
                seq=0,
                timestamp_ns=0,
                pose=self.fallback_pose(),
                pointmap=self.build_pointmap(intrinsics=self._sequence_intrinsics),
            )
            return

        if timestamps_ns is None or len(timestamps_ns) == 0:
            timestamps_ns = np.rint(np.asarray(self._reference_trajectory.timestamps, dtype=np.float64) * 1e9).astype(
                np.int64,
                copy=False,
            )
            if self.backend_config.max_frames is not None:
                timestamps_ns = timestamps_ns[: self.backend_config.max_frames]

        if len(timestamps_ns) == 0:
            self.record_pose_sample(
                seq=0,
                timestamp_ns=0,
                pose=self.fallback_pose(),
                pointmap=self.build_pointmap(intrinsics=self._sequence_intrinsics),
            )
            return

        use_static_reference_cloud = (
            self.output_policy.emit_dense_points
            and self._reference_point_cloud_sequence is None
            and self._static_reference_points_xyz_world is not None
        )
        poses = interpolate_trajectory_poses(
            self._reference_trajectory,
            np.asarray(timestamps_ns, dtype=np.float64) / 1e9,
            target_frame=f"reference_{self._baseline_source.value}_world",
        )
        for seq, (timestamp_ns, pose) in enumerate(zip(timestamps_ns.tolist(), poses, strict=True)):
            resolved_pose = self._apply_pose_noise(pose)
            pointmap, dense_points_world, warnings = self._resolve_reference_geometry(
                timestamp_ns=timestamp_ns,
                pose_world_camera=resolved_pose,
                camera_intrinsics=self._sequence_intrinsics,
                frame_rgb=None,
            )
            if pointmap is None:
                pointmap = self.build_pointmap(intrinsics=self._sequence_intrinsics)
            self.record_pose_sample(
                seq=seq,
                timestamp_ns=int(timestamp_ns),
                pose=resolved_pose,
                pointmap=pointmap,
                dense_points_world=dense_points_world,
                camera_intrinsics=self._sequence_intrinsics,
                backend_warnings=warnings,
                append_dense_geometry=not use_static_reference_cloud,
            )

        if use_static_reference_cloud and self._static_reference_points_xyz_world is not None:
            self._append_dense_points(
                self._apply_point_noise(np.asarray(self._static_reference_points_xyz_world, dtype=np.float64))
            )

    def step(self, frame: FramePacket) -> None:
        """Consume one frame and buffer a deterministic incremental SLAM update."""
        pose = frame.pose if self._reference_trajectory is None else self._reference_pose(frame.timestamp_ns)
        if pose is None:
            pose = self.fallback_pose()
        pointmap, dense_points_world, warnings = self._resolve_reference_geometry(
            timestamp_ns=frame.timestamp_ns,
            pose_world_camera=pose,
            camera_intrinsics=frame.intrinsics if frame.intrinsics is not None else self._sequence_intrinsics,
            frame_rgb=frame.rgb,
        )
        if pointmap is None:
            fallback_intrinsics = frame.intrinsics if frame.intrinsics is not None else self._sequence_intrinsics
            pointmap = self.build_pointmap(frame=frame, intrinsics=fallback_intrinsics)
        update = self.record_pose_sample(
            seq=frame.seq,
            timestamp_ns=frame.timestamp_ns,
            pose=pose,
            pointmap=pointmap,
            dense_points_world=dense_points_world,
            camera_intrinsics=frame.intrinsics if frame.intrinsics is not None else self._sequence_intrinsics,
            image_rgb=None if frame.rgb is None else np.asarray(frame.rgb, dtype=np.uint8),
            depth_map=None if frame.depth is None else np.asarray(frame.depth, dtype=np.float32),
            backend_warnings=warnings,
        )
        self._pending_updates.append(update)

    def try_get_updates(self) -> list[SlamUpdate]:
        """Retrieve and clear any pending incremental SLAM updates."""
        updates = self._pending_updates
        self._pending_updates = []
        return updates

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

    def fallback_pose(self) -> FrameTransform:
        """Build the next fallback pose when no source pose is available."""
        previous_pose = self._poses[-1] if self._poses else None
        tx = _STEP_DISTANCE_M if previous_pose is None else previous_pose.tx + _STEP_DISTANCE_M
        ty = 0.0 if previous_pose is None else previous_pose.ty
        tz = 0.0 if previous_pose is None else previous_pose.tz
        return FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=tx, ty=ty, tz=tz)

    def record_pose_sample(
        self,
        *,
        seq: int,
        timestamp_ns: int,
        pose: FrameTransform,
        pointmap: NDArray[np.float32] | None = None,
        dense_points_world: NDArray[np.float64] | None = None,
        camera_intrinsics: CameraIntrinsics | None = None,
        image_rgb: NDArray[np.uint8] | None = None,
        depth_map: NDArray[np.float32] | None = None,
        backend_warnings: list[str] | None = None,
        append_dense_geometry: bool = True,
    ) -> SlamUpdate:
        """Record one pose sample and return the matching SLAM update."""
        timestamp_s = self._normalize_timestamp_seconds(timestamp_ns / 1e9)
        self._poses.append(pose)
        self._timestamps_s.append(timestamp_s)

        if self.output_policy.emit_dense_points and append_dense_geometry:
            if dense_points_world is not None:
                self._append_dense_points(dense_points_world)
            else:
                camera_points = (
                    pointmap.reshape(-1, 3) if pointmap is not None else self._synthetic_local_patch_camera()
                )
                self._append_dense_points(transform_points_world_camera(camera_points, pose))

        num_sparse_points = max(len(self._poses) * 12, 12) if self.output_policy.emit_sparse_points else 0
        return SlamUpdate(
            seq=seq,
            timestamp_ns=timestamp_ns,
            source_seq=seq,
            source_timestamp_ns=timestamp_ns,
            pose=pose,
            is_keyframe=True,
            pose_updated=True,
            num_sparse_points=num_sparse_points,
            num_dense_points=self._num_dense_points,
            pointmap=pointmap,
            camera_intrinsics=camera_intrinsics,
            image_rgb=image_rgb,
            depth_map=depth_map,
            backend_warnings=[] if backend_warnings is None else backend_warnings,
        )

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

    def _reference_pose(self, timestamp_ns: int) -> FrameTransform | None:
        if self._reference_trajectory is None:
            return None
        pose = interpolate_trajectory_poses(
            self._reference_trajectory,
            np.asarray([timestamp_ns], dtype=np.float64) / 1e9,
            target_frame=f"reference_{self._baseline_source.value}_world",
        )[0]
        return self._apply_pose_noise(pose)

    def _resolve_reference_geometry(
        self,
        *,
        timestamp_ns: int,
        pose_world_camera: FrameTransform,
        camera_intrinsics: CameraIntrinsics | None,
        frame_rgb: NDArray[np.uint8] | None,
    ) -> tuple[NDArray[np.float32] | None, NDArray[np.float64] | None, list[str]]:
        warnings: list[str] = []
        if self._reference_point_cloud_sequence is None:
            return None, None, warnings
        reference_payload = _nearest_reference_payload(
            self._reference_point_cloud_sequence.index_rows,
            timestamp_ns=timestamp_ns,
            max_diff_s=_REFERENCE_PAYLOAD_MAX_TIME_DIFF_S,
        )
        if reference_payload is None:
            warnings.append(
                "Mock reference point-cloud stream has no payload within "
                f"{_REFERENCE_PAYLOAD_MAX_TIME_DIFF_S:.3f}s for timestamp_ns={timestamp_ns}; "
                "falling back to synthetic pointmap generation."
            )
            return None, None, warnings
        world_points_xyz = self._reference_points_xyz_world(
            payload_timestamp_s=reference_payload[0],
            payload_index=reference_payload[1],
        )
        if camera_intrinsics is None:
            warnings.append(
                "Mock reference point-cloud replay requires camera intrinsics for live pointmap projection; "
                f"timestamp_ns={timestamp_ns} fell back to synthetic pointmap generation."
            )
            return None, world_points_xyz, warnings
        pointmap = _rasterize_world_points_to_pointmap(
            points_xyz_world=world_points_xyz,
            pose_world_camera=pose_world_camera,
            intrinsics=camera_intrinsics,
            image_shape=None if frame_rgb is None else frame_rgb.shape[:2],
        )
        return pointmap, world_points_xyz, warnings

    def _reference_points_xyz_world(self, *, payload_timestamp_s: float, payload_index: int) -> NDArray[np.float64]:
        payload_path = resolve_tango_point_cloud_payload(
            self._reference_point_cloud_sequence.reference.payload_root,
            payload_index,
        )
        payload_points_xyz = load_tango_point_cloud_payload(payload_path)
        pose_world_payload = interpolate_trajectory_poses(
            self._reference_point_cloud_sequence.trajectory,
            np.asarray([payload_timestamp_s], dtype=np.float64),
            target_frame=self._reference_point_cloud_sequence.reference.native_frame,
            source_frame="tango_depth_sensor",
        )[0]
        points_xyz_source_world = transform_points_world_camera(payload_points_xyz, pose_world_payload)
        points_xyz_target_world = apply_sim3(points_xyz_source_world, self._reference_point_cloud_sequence.alignment)
        return self._apply_point_noise(points_xyz_target_world)

    def _append_dense_points(self, points_xyz_world: NDArray[np.float64] | None) -> None:
        if points_xyz_world is None or points_xyz_world.size == 0:
            return
        finite_points = np.asarray(points_xyz_world, dtype=np.float64)[np.all(np.isfinite(points_xyz_world), axis=1)]
        if len(finite_points) == 0:
            return
        self._dense_point_chunks_xyz.append(finite_points)
        self._num_dense_points += int(len(finite_points))

    def _normalize_timestamp_seconds(self, timestamp_s: float) -> float:
        if not self._timestamps_s:
            return float(timestamp_s)
        return max(float(timestamp_s), self._timestamps_s[-1] + 1e-3)

    def _synthetic_local_patch_camera(self) -> NDArray[np.float32]:
        offsets_x, offsets_y = np.meshgrid(
            np.linspace(-0.25, 0.25, 4, dtype=np.float32),
            np.linspace(-0.15, 0.15, 3, dtype=np.float32),
            indexing="xy",
        )
        depth_m = np.full_like(offsets_x, fill_value=_POINTMAP_BASE_DEPTH_M)
        return np.stack([offsets_x, offsets_y, depth_m], axis=-1).reshape(-1, 3)

    def _apply_pose_noise(self, pose: FrameTransform) -> FrameTransform:
        noise_xyz = _awgn_samples(
            self._rng,
            mean=self.config.trajectory_position_noise_mean_m,
            variance=self.config.trajectory_position_noise_variance_m2,
            size=(3,),
        )
        return pose.model_copy(
            update={
                "tx": float(pose.tx + noise_xyz[0]),
                "ty": float(pose.ty + noise_xyz[1]),
                "tz": float(pose.tz + noise_xyz[2]),
            }
        )

    def _apply_point_noise(self, points_xyz: NDArray[np.float64]) -> NDArray[np.float64]:
        points = np.asarray(points_xyz, dtype=np.float64)
        if points.size == 0:
            return points
        return points + _awgn_samples(
            self._rng,
            mean=self.config.point_noise_mean_m,
            variance=self.config.point_noise_variance_m2,
            size=points.shape,
        )


def _load_reference_trajectory(
    benchmark_inputs: PreparedBenchmarkInputs | None,
    baseline_source: ReferenceSource,
) -> PoseTrajectory3D | None:
    if benchmark_inputs is None:
        return None
    reference = benchmark_inputs.trajectory_for_source(baseline_source)
    return None if reference is None else load_tum_trajectory(reference.path)


def _load_reference_point_cloud_sequence(
    *,
    benchmark_inputs: PreparedBenchmarkInputs | None,
    baseline_source: ReferenceSource,
    reference_trajectory: PoseTrajectory3D | None,
) -> _PointCloudSequenceRuntime | None:
    if benchmark_inputs is None or reference_trajectory is None:
        return None
    for source in _PREFERRED_REFERENCE_CLOUD_SOURCES:
        if (reference := benchmark_inputs.point_cloud_sequence_for_source(source)) is None:
            continue
        if reference.coordinate_status is not ReferenceCloudCoordinateStatus.SOURCE_NATIVE:
            continue
        source_trajectory = load_tum_trajectory(reference.trajectory_path)
        alignment = fit_sim3_alignment(
            source_trajectory=source_trajectory,
            target_trajectory=reference_trajectory,
            source_frame=reference.native_frame,
            target_frame=f"reference_{baseline_source.value}_world",
        )
        return _PointCloudSequenceRuntime(
            reference=reference,
            trajectory=source_trajectory,
            index_rows=load_tango_point_cloud_index(reference.index_path),
            alignment=alignment,
        )
    return None


def _load_static_reference_points_xyz_world(
    *,
    benchmark_inputs: PreparedBenchmarkInputs | None,
    baseline_source: ReferenceSource,
) -> NDArray[np.float64] | None:
    if benchmark_inputs is None or baseline_source is not ReferenceSource.GROUND_TRUTH:
        return None
    for source in _PREFERRED_REFERENCE_CLOUD_SOURCES:
        reference = next(
            (
                candidate
                for candidate in benchmark_inputs.reference_clouds
                if candidate.source is source and candidate.coordinate_status is ReferenceCloudCoordinateStatus.ALIGNED
            ),
            None,
        )
        if reference is not None:
            return np.asarray(load_point_cloud_ply(reference.path), dtype=np.float64)
    return None


def _load_sequence_intrinsics(sequence: SequenceManifest) -> CameraIntrinsics | None:
    if sequence.intrinsics_path is None:
        return None
    return load_advio_calibration(sequence.intrinsics_path).intrinsics


def _load_sequence_timestamps_ns(sequence: SequenceManifest) -> NDArray[np.int64] | None:
    if sequence.timestamps_path is None or not sequence.timestamps_path.exists():
        return None
    payload = sequence.timestamps_path.read_text(encoding="utf-8").strip()
    if not payload:
        return np.empty(0, dtype=np.int64)
    try:
        decoded = json.loads(payload)
    except json.JSONDecodeError:
        rows = np.loadtxt(sequence.timestamps_path, delimiter=",", dtype=np.float64)
        rows = np.atleast_2d(rows)
        return np.rint(rows[:, 0] * 1e9).astype(np.int64, copy=False)
    if isinstance(decoded, dict) and isinstance(decoded.get("timestamps_ns"), list):
        return np.asarray([int(timestamp_ns) for timestamp_ns in decoded["timestamps_ns"]], dtype=np.int64)
    raise ValueError(
        "Expected `SequenceManifest.timestamps_path` to contain either normalized JSON with a `timestamps_ns` list "
        f"or a numeric CSV first column, got '{sequence.timestamps_path}'."
    )


def _nearest_reference_payload(
    index_rows: NDArray[np.float64],
    *,
    timestamp_ns: int,
    max_diff_s: float,
) -> tuple[float, int] | None:
    if index_rows.size == 0:
        return None
    timestamps_s = np.asarray(index_rows[:, 0], dtype=np.float64)
    target_timestamp_s = float(timestamp_ns) / 1e9
    nearest_index = int(np.argmin(np.abs(timestamps_s - target_timestamp_s)))
    if float(abs(timestamps_s[nearest_index] - target_timestamp_s)) > max_diff_s:
        return None
    return float(timestamps_s[nearest_index]), int(round(float(index_rows[nearest_index, 1])))


def _rasterize_world_points_to_pointmap(
    *,
    points_xyz_world: NDArray[np.float64],
    pose_world_camera: FrameTransform,
    intrinsics: CameraIntrinsics,
    image_shape: tuple[int, int] | None,
) -> NDArray[np.float32]:
    height_px = (
        int(image_shape[0])
        if image_shape is not None
        else intrinsics.height_px
        if intrinsics.height_px is not None
        else None
    )
    width_px = (
        int(image_shape[1])
        if image_shape is not None
        else intrinsics.width_px
        if intrinsics.width_px is not None
        else None
    )
    if height_px is None or width_px is None:
        raise ValueError("Pointmap rasterization requires image dimensions in the frame or camera intrinsics.")
    points_xyz_camera = _transform_points_camera_world(points_xyz_world, pose_world_camera)
    if points_xyz_camera.size == 0:
        return np.full((height_px, width_px, 3), np.nan, dtype=np.float32)

    z = np.asarray(points_xyz_camera[:, 2], dtype=np.float64)
    valid = np.all(np.isfinite(points_xyz_camera), axis=1) & (z > 0.0)
    if not np.any(valid):
        return np.full((height_px, width_px, 3), np.nan, dtype=np.float32)

    points_xyz_camera = points_xyz_camera[valid]
    z = z[valid]
    u_px = np.rint(intrinsics.fx * points_xyz_camera[:, 0] / z + intrinsics.cx).astype(np.int64, copy=False)
    v_px = np.rint(intrinsics.fy * points_xyz_camera[:, 1] / z + intrinsics.cy).astype(np.int64, copy=False)
    in_bounds = (u_px >= 0) & (u_px < width_px) & (v_px >= 0) & (v_px < height_px)
    if not np.any(in_bounds):
        return np.full((height_px, width_px, 3), np.nan, dtype=np.float32)

    points_xyz_camera = points_xyz_camera[in_bounds]
    z = z[in_bounds]
    u_px = u_px[in_bounds]
    v_px = v_px[in_bounds]
    order = np.argsort(z)
    linear_indices = v_px[order] * width_px + u_px[order]
    _, keep_positions = np.unique(linear_indices, return_index=True)
    selected = order[keep_positions]

    pointmap = np.full((height_px, width_px, 3), np.nan, dtype=np.float32)
    pointmap[v_px[selected], u_px[selected], :] = np.asarray(points_xyz_camera[selected], dtype=np.float32)
    return pointmap


def _transform_points_camera_world(
    points_xyz_world: NDArray[np.float64],
    pose_world_camera: FrameTransform,
) -> NDArray[np.float64]:
    points = np.asarray(points_xyz_world, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError(f"Expected point array shape (N, 3), got {points.shape}.")
    if len(points) == 0:
        return np.empty((0, 3), dtype=np.float64)
    world_from_camera = pose_world_camera.as_matrix()
    camera_from_world = np.linalg.inv(world_from_camera)
    return transform(camera_from_world, vectors_to_points(points))[:, :3]


def _awgn_samples(
    rng: np.random.Generator,
    *,
    mean: float,
    variance: float,
    size: tuple[int, ...],
) -> NDArray[np.float64]:
    return np.asarray(rng.normal(loc=mean, scale=float(np.sqrt(variance)), size=size), dtype=np.float64)


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
