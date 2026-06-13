"""Bounded runtime adapter for the ground-alignment stage."""

from __future__ import annotations

import time
from typing import Literal

import numpy as np
from numpy.typing import NDArray

from prml_vslam.alignment.services import GroundAlignmentService
from prml_vslam.alignment.stage.contracts import (
    GroundAlignmentKeyframeSample,
    GroundAlignmentStageInput,
    GroundAlignmentStreamingStartInput,
)
from prml_vslam.interfaces.alignment import GroundAlignmentMetadata
from prml_vslam.interfaces.artifacts import artifact_ref
from prml_vslam.pipeline.contracts.events import StageOutcome
from prml_vslam.pipeline.contracts.provenance import StageStatus
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.contracts import StageResult, StageRuntimeStatus, StageRuntimeUpdate
from prml_vslam.pipeline.stages.base.protocols import LiveUpdateStageRuntime, OfflineStageRuntime, StreamingStageRuntime
from prml_vslam.utils import RunArtifactPaths
from prml_vslam.utils.geometry import transform_points_world_camera
from prml_vslam.utils.serialization import stable_hash, write_json


class GroundAlignmentRuntime(
    OfflineStageRuntime[GroundAlignmentStageInput],
    StreamingStageRuntime[GroundAlignmentStreamingStartInput, GroundAlignmentKeyframeSample],
    LiveUpdateStageRuntime,
):
    """Adapt :class:`GroundAlignmentService` to the generic bounded runtime API.

    The runtime owns stage-result construction, artifact registration, and live
    status for the pipeline. Plane fitting and frame semantics remain
    alignment-owned in :mod:`prml_vslam.alignment.services`.
    """

    def __init__(self, *, service_type: type[GroundAlignmentService] | None = None) -> None:
        self._service_type = GroundAlignmentService if service_type is None else service_type
        self._status = StageRuntimeStatus(stage_key=StageKey.GRAVITY_ALIGNMENT)
        self._pending_updates: list[StageRuntimeUpdate] = []
        self._streaming_input: GroundAlignmentStreamingStartInput | None = None
        self._streaming_service: GroundAlignmentService | None = None
        self._streaming_points_xyz_world: list[NDArray[np.float64]] = []
        self._streaming_poses_world_camera: list[NDArray[np.float64]] = []
        self._streaming_keyframe_indices: list[int] = []
        self._accepted_keyframe_count = 0
        self._last_estimated_keyframe_count = 0
        self._last_keyframe_index: int | None = None
        self._anchor_metadata: GroundAlignmentMetadata | None = None
        self._smoothed_metadata: GroundAlignmentMetadata | None = None
        self._latest_metadata: GroundAlignmentMetadata | None = None
        self._stop_requested = False

    def status(self) -> StageRuntimeStatus:
        """Return the latest ground-alignment runtime status."""
        return self._status

    def stop(self) -> None:
        """Mark the bounded runtime as stopped."""
        self._stop_requested = True
        self._status = self._status.model_copy(update={"lifecycle_state": StageStatus.STOPPED})

    def start_streaming(self, input_payload: GroundAlignmentStreamingStartInput) -> None:
        """Start live ground alignment for streaming SLAM keyframe samples."""
        self._streaming_input = input_payload
        self._streaming_service = self._service_type(config=input_payload.config)
        self._streaming_points_xyz_world = []
        self._streaming_poses_world_camera = []
        self._streaming_keyframe_indices = []
        self._pending_updates = []
        self._accepted_keyframe_count = 0
        self._last_estimated_keyframe_count = 0
        self._last_keyframe_index = None
        self._anchor_metadata = None
        self._smoothed_metadata = None
        self._latest_metadata = None
        self._stop_requested = False
        self._status = StageRuntimeStatus(
            stage_key=StageKey.GRAVITY_ALIGNMENT,
            lifecycle_state=StageStatus.RUNNING,
            progress_message="Waiting for streaming keyframes.",
            completed_steps=0,
            progress_unit="keyframes",
            processed_items=0,
            updated_at_ns=time.time_ns(),
        )

    def submit_stream_item(self, item: GroundAlignmentKeyframeSample) -> None:
        """Accept one SLAM keyframe pointmap and run the configured estimator."""
        if self._streaming_input is None or self._streaming_service is None:
            raise RuntimeError("Streaming ground alignment has not been started.")
        if self._stop_requested:
            return
        points_xyz_world = _world_points_from_sample(item)
        if len(points_xyz_world) == 0:
            self._status = self._status.model_copy(
                update={
                    "progress_message": f"Skipped keyframe {item.keyframe_index}: no valid z>0 pointmap samples.",
                    "updated_at_ns": time.time_ns(),
                }
            )
            return

        target = self._streaming_input.config.streaming_keyframes
        anchor_target = min(self._streaming_input.config.anchor_keyframes, target)
        if (
            self._streaming_input.config.streaming_policy == "first_keyframes"
            and self._anchor_metadata is None
            and self._accepted_keyframe_count >= target
        ):
            return
        self._streaming_points_xyz_world.append(points_xyz_world)
        self._streaming_poses_world_camera.append(item.T_world_camera.as_matrix())
        self._streaming_keyframe_indices.append(item.keyframe_index)
        if self._streaming_input.config.streaming_policy == "running_ransac" or self._anchor_metadata is not None:
            self._streaming_points_xyz_world = self._streaming_points_xyz_world[-target:]
            self._streaming_poses_world_camera = self._streaming_poses_world_camera[-target:]
            self._streaming_keyframe_indices = self._streaming_keyframe_indices[-target:]
        self._accepted_keyframe_count += 1
        self._last_keyframe_index = item.keyframe_index

        if self._streaming_input.config.streaming_policy == "first_keyframes":
            should_estimate = self._accepted_keyframe_count >= anchor_target and (
                self._anchor_metadata is not None or self._accepted_keyframe_count <= target
            )
        else:
            should_estimate = self._accepted_keyframe_count % target == 0
        metadata = self._estimate_streaming_metadata() if should_estimate else None
        if metadata is not None:
            metadata = self._observe_streaming_estimate(metadata)
            self._latest_metadata = metadata
            self._last_estimated_keyframe_count = self._accepted_keyframe_count
            self._pending_updates.append(
                StageRuntimeUpdate(
                    stage_key=StageKey.GRAVITY_ALIGNMENT,
                    timestamp_ns=time.time_ns(),
                    semantic_events=[metadata],
                    runtime_status=self._status,
                )
            )
        self._status = self._status.model_copy(
            update={
                "lifecycle_state": StageStatus.RUNNING,
                "progress_message": _streaming_progress_message(
                    keyframes=self._accepted_keyframe_count,
                    target=target,
                    metadata=metadata,
                ),
                "completed_steps": self._accepted_keyframe_count,
                "progress_unit": "keyframes",
                "processed_items": self._accepted_keyframe_count,
                "updated_at_ns": time.time_ns(),
            }
        )

    def drain_runtime_updates(self, max_items: int | None = None) -> list[StageRuntimeUpdate]:
        """Return queued live ground-alignment metadata updates."""
        if max_items is None:
            updates = list(self._pending_updates)
            self._pending_updates.clear()
            return updates
        updates = self._pending_updates[:max_items]
        del self._pending_updates[:max_items]
        return updates

    def finish_streaming(self) -> StageResult:
        """Persist the latest streaming ground-alignment metadata and finalize."""
        if self._streaming_input is None:
            raise RuntimeError("Streaming ground alignment has not been started.")
        metadata = (
            self._observe_streaming_estimate(self._estimate_streaming_metadata())
            if self._streaming_points_xyz_world
            and self._streaming_poses_world_camera
            and (self._anchor_metadata is None or self._streaming_input.config.streaming_policy == "running_ransac")
            and self._last_estimated_keyframe_count != self._accepted_keyframe_count
            else self._anchor_metadata
            or self._latest_metadata
            or GroundAlignmentMetadata(
                applied=False,
                confidence=0.0,
                point_cloud_source="streaming_pointmaps",
                skip_reason="No streaming ground-alignment keyframe samples were available before finalization.",
            )
        )
        return self._build_result(
            run_paths=self._streaming_input.run_paths,
            metadata=metadata,
            config_hash=stable_hash(self._streaming_input.config),
            input_fingerprint=stable_hash(
                {
                    "point_cloud_source": "streaming_pointmaps",
                    "accepted_keyframes": self._accepted_keyframe_count,
                    "last_keyframe_index": self._last_keyframe_index,
                }
            ),
            processed_items=self._accepted_keyframe_count,
            progress_unit="keyframes",
        )

    def run_offline(self, input_payload: GroundAlignmentStageInput) -> StageResult:
        """Detect and persist the derived ground-alignment artifact.

        Returns a skipped stage outcome when the alignment service explicitly
        declines to apply a transform, preserving a durable diagnostic record
        without failing the run.
        """
        self._status = self._status.model_copy(
            update={
                "lifecycle_state": StageStatus.RUNNING,
                "progress_message": "Estimating ground alignment.",
            }
        )
        try:
            result = self._run(input_payload)
        except Exception as exc:
            self._status = self._status.model_copy(
                update={
                    "lifecycle_state": StageStatus.FAILED,
                    "last_error": str(exc),
                }
            )
            raise
        self._status = result.final_runtime_status
        return result

    def _run(self, input_payload: GroundAlignmentStageInput) -> StageResult:
        metadata = self._service_type(config=input_payload.config).estimate_from_slam_artifacts(slam=input_payload.slam)
        return self._build_result(
            run_paths=input_payload.run_paths,
            metadata=metadata,
            config_hash=stable_hash(input_payload.config),
            input_fingerprint=stable_hash(
                {
                    "trajectory_tum": input_payload.slam.trajectory_tum,
                    "dense_points_ply": input_payload.slam.dense_points_ply,
                    "sparse_points_ply": input_payload.slam.sparse_points_ply,
                }
            ),
            processed_items=1,
            progress_unit="artifacts",
        )

    def _estimate_streaming_metadata(self) -> GroundAlignmentMetadata:
        if self._streaming_service is None:
            raise RuntimeError("Streaming ground alignment has not been started.")
        return self._streaming_service.estimate_from_world_points(
            points_xyz_world=np.concatenate(self._streaming_points_xyz_world, axis=0),
            poses_world_camera=np.stack(self._streaming_poses_world_camera, axis=0),
            point_cloud_source="streaming_pointmaps",
        )

    def _observe_streaming_estimate(self, metadata: GroundAlignmentMetadata) -> GroundAlignmentMetadata:
        metadata = self._annotate_streaming_metadata(
            metadata, role="anchor" if self._anchor_metadata is None else "final"
        )
        if not metadata.applied:
            return metadata
        if self._anchor_metadata is None:
            self._anchor_metadata = metadata
            self._smoothed_metadata = metadata
            return metadata
        smoothed = self._smooth_streaming_metadata(metadata)
        self._smoothed_metadata = smoothed
        return smoothed

    def _annotate_streaming_metadata(
        self,
        metadata: GroundAlignmentMetadata,
        *,
        role: Literal["anchor", "live_smoothed", "final"],
    ) -> GroundAlignmentMetadata:
        return metadata.model_copy(
            update={
                "estimate_role": role,
                "sample_count": self._accepted_keyframe_count,
                "first_keyframe_index": self._streaming_keyframe_indices[0]
                if self._streaming_keyframe_indices
                else None,
                "last_keyframe_index": self._last_keyframe_index,
                "smoothing_alpha": self._streaming_input.config.smoothing_alpha if self._streaming_input else None,
            }
        )

    def _smooth_streaming_metadata(self, metadata: GroundAlignmentMetadata) -> GroundAlignmentMetadata:
        if (
            self._smoothed_metadata is None
            or self._smoothed_metadata.ground_plane_world is None
            or metadata.ground_plane_world is None
            or self._streaming_service is None
        ):
            return self._annotate_streaming_metadata(metadata, role="live_smoothed")
        alpha = self._streaming_input.config.smoothing_alpha if self._streaming_input is not None else 0.2
        previous_plane = self._smoothed_metadata.ground_plane_world
        current_plane = metadata.ground_plane_world
        previous_normal = np.asarray(previous_plane.normal_xyz_world, dtype=np.float64)
        current_normal = np.asarray(current_plane.normal_xyz_world, dtype=np.float64)
        if float(np.dot(previous_normal, current_normal)) < 0.0:
            current_normal = -current_normal
            current_offset = -float(current_plane.offset_world)
        else:
            current_offset = float(current_plane.offset_world)
        normal = (1.0 - alpha) * previous_normal + alpha * current_normal
        normal_norm = np.linalg.norm(normal)
        if not np.isfinite(normal_norm) or normal_norm <= 0.0:
            return self._annotate_streaming_metadata(metadata, role="live_smoothed")
        normal /= normal_norm
        offset = (1.0 - alpha) * float(previous_plane.offset_world) + alpha * current_offset
        yaw_source, transform_viewer_world_world = self._streaming_service.viewer_transform_for_plane(
            normal_xyz_world=normal,
            offset_world=offset,
            poses_world_camera=np.stack(self._streaming_poses_world_camera, axis=0),
        )
        smoothed_plane = current_plane.model_copy(
            update={
                "normal_xyz_world": tuple(float(value) for value in normal),
                "offset_world": float(offset),
            }
        )
        return self._annotate_streaming_metadata(
            metadata.model_copy(
                update={
                    "ground_plane_world": smoothed_plane,
                    "T_viewer_world_world": transform_viewer_world_world,
                    "yaw_source": yaw_source,
                }
            ),
            role="live_smoothed",
        )

    def _build_result(
        self,
        *,
        run_paths: RunArtifactPaths,
        metadata: GroundAlignmentMetadata,
        config_hash: str,
        input_fingerprint: str,
        processed_items: int,
        progress_unit: str,
    ) -> StageResult:
        write_json(run_paths.ground_alignment_path, metadata)
        outcome_status = (
            StageStatus.STOPPED
            if self._stop_requested
            else StageStatus.COMPLETED
            if metadata.applied
            else StageStatus.SKIPPED
        )
        outcome = StageOutcome(
            stage_key=StageKey.GRAVITY_ALIGNMENT,
            status=outcome_status,
            config_hash=config_hash,
            input_fingerprint=input_fingerprint,
            artifacts={
                "ground_alignment": artifact_ref(run_paths.ground_alignment_path, kind="json"),
            },
            metrics={
                "confidence": metadata.confidence,
                "candidate_count": metadata.candidate_count,
            },
        )
        result = StageResult(
            stage_key=StageKey.GRAVITY_ALIGNMENT,
            payload=metadata,
            outcome=outcome,
            final_runtime_status=_final_status(
                stage_key=StageKey.GRAVITY_ALIGNMENT,
                status=outcome_status,
                processed_items=processed_items,
                progress_unit=progress_unit,
                progress_message="Ground alignment complete.",
            ),
        )
        self._status = result.final_runtime_status
        return result


def _final_status(
    *,
    stage_key: StageKey,
    status: StageStatus,
    processed_items: int,
    progress_unit: str,
    progress_message: str,
) -> StageRuntimeStatus:
    return StageRuntimeStatus(
        stage_key=stage_key,
        lifecycle_state=status,
        progress_message=progress_message,
        completed_steps=processed_items,
        total_steps=processed_items,
        progress_unit=progress_unit,
        processed_items=processed_items,
    )


def _world_points_from_sample(sample: GroundAlignmentKeyframeSample) -> NDArray[np.float64]:
    points_xyz_camera = np.asarray(sample.pointmap_xyz_camera, dtype=np.float32).reshape(-1, 3)
    valid_mask = np.all(np.isfinite(points_xyz_camera), axis=1) & (points_xyz_camera[:, 2] > 0.0)
    if not np.any(valid_mask):
        return np.empty((0, 3), dtype=np.float64)
    return transform_points_world_camera(points_xyz_camera[valid_mask], sample.T_world_camera)


def _streaming_progress_message(
    *,
    keyframes: int,
    target: int,
    metadata: GroundAlignmentMetadata | None,
) -> str:
    if metadata is None:
        return f"Accepted {keyframes} keyframes; waiting for estimator window {target}."
    if metadata.applied:
        return f"Updated {metadata.estimate_role} streaming ground alignment from {keyframes} keyframes."
    return f"Skipped streaming ground alignment update: {metadata.skip_reason or 'no reliable plane'}"


__all__ = ["GroundAlignmentRuntime"]
