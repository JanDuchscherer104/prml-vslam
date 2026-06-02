"""Repo-owned Rerun observer sink and Ray sidecar actor."""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import cast

import numpy as np
import ray
from ray.actor import ActorHandle

from prml_vslam.interfaces.alignment import GroundAlignmentMetadata
from prml_vslam.pipeline.stages.base.contracts import StageRuntimeUpdate
from prml_vslam.pipeline.stages.base.handles import TransientPayloadRef
from prml_vslam.utils import Console
from prml_vslam.visualization.rerun import (
    MODEL_RGB_2D_ENTITY_PATH,
    attach_recording_sinks,
    augment_viewer_recording_with_ground_plane,
    create_recording_stream,
    log_clear,
    log_depth_image,
    log_ground_plane_patch,
    log_line_strip3d,
    log_mesh_ply,
    log_pinhole,
    log_pointcloud,
    log_pointcloud_ply,
    log_rgb_image,
    log_sim3_transform,
    log_transform,
)

from .rerun_policy import RerunLoggingPolicy

_LOGGER = logging.getLogger(__name__)
PayloadResolver = Callable[[TransientPayloadRef], np.ndarray | None]


# TODO: stop passing individual logging functions to RerunLoggingPolicy!?
# TODO: RerunEventSink should be either live or export not both, such that each of them would get their own RerunSinkActor!
class RerunEventSink:
    """Optional observer sink for repo-owned live/export Rerun logging."""

    def __init__(
        self,
        *,
        grpc_url: str | None,
        target_path: Path | None,
        recording_id: str | None = None,
        show_tracking_trajectory: bool = True,
        trajectory_pose_axis_length: float = 0.0,
        log_source_rgb: bool = False,
        log_diagnostic_preview: bool = False,
        log_camera_image_rgb: bool = True,
        point_cloud_decimation_keep_ratio: float = 1.0,
        reference_point_cloud_decimation_keep_ratio: float = 1.0,
        mesh_decimation_keep_ratio: float = 1.0,
        decimation_random_seed: int = 0,
        view_coordinates: str = "RDF",
    ) -> None:
        self._console = Console(__name__).child(self.__class__.__name__)
        self._live_stream = None
        self._export_stream = None
        self._live_policy = RerunLoggingPolicy(
            log_pinhole=log_pinhole,
            log_pointcloud=log_pointcloud,
            log_line_strip3d=log_line_strip3d,
            log_mesh_ply=log_mesh_ply,
            log_clear=log_clear,
            log_depth_image=log_depth_image,
            log_ground_plane_patch=log_ground_plane_patch,
            log_rgb_image=log_rgb_image,
            log_pointcloud_ply=log_pointcloud_ply,
            log_transform=log_transform,
            log_sim3_transform=log_sim3_transform,
            show_tracking_trajectory=show_tracking_trajectory,
            trajectory_pose_axis_length=trajectory_pose_axis_length,
            log_source_rgb=log_source_rgb,
            log_diagnostic_preview=log_diagnostic_preview,
            log_camera_image_rgb=log_camera_image_rgb,
            point_cloud_decimation_keep_ratio=point_cloud_decimation_keep_ratio,
            reference_point_cloud_decimation_keep_ratio=reference_point_cloud_decimation_keep_ratio,
            mesh_decimation_keep_ratio=mesh_decimation_keep_ratio,
            decimation_random_seed=decimation_random_seed,
        )
        self._export_policy = RerunLoggingPolicy(
            log_pinhole=log_pinhole,
            log_pointcloud=log_pointcloud,
            log_line_strip3d=log_line_strip3d,
            log_mesh_ply=log_mesh_ply,
            log_clear=log_clear,
            log_depth_image=log_depth_image,
            log_ground_plane_patch=log_ground_plane_patch,
            log_rgb_image=log_rgb_image,
            log_pointcloud_ply=log_pointcloud_ply,
            log_transform=log_transform,
            log_sim3_transform=log_sim3_transform,
            show_tracking_trajectory=show_tracking_trajectory,
            trajectory_pose_axis_length=trajectory_pose_axis_length,
            log_source_rgb=log_source_rgb,
            log_diagnostic_preview=log_diagnostic_preview,
            log_camera_image_rgb=log_camera_image_rgb,
            point_cloud_decimation_keep_ratio=point_cloud_decimation_keep_ratio,
            reference_point_cloud_decimation_keep_ratio=reference_point_cloud_decimation_keep_ratio,
            mesh_decimation_keep_ratio=mesh_decimation_keep_ratio,
            decimation_random_seed=decimation_random_seed,
        )
        self._recording_id = recording_id
        self._target_path = target_path
        self._latest_ground_alignment: GroundAlignmentMetadata | None = None
        self._console.info(
            f"Rerun sink policy: source_rgb={log_source_rgb} diagnostic_preview={log_diagnostic_preview} "
            f"camera_image_rgb={log_camera_image_rgb} trajectory={show_tracking_trajectory} "
            f"point_cloud_keep_ratio={point_cloud_decimation_keep_ratio} "
            f"reference_point_cloud_keep_ratio={reference_point_cloud_decimation_keep_ratio} "
            f"mesh_keep_ratio={mesh_decimation_keep_ratio} view_coordinates={view_coordinates}."
        )

        if grpc_url is not None:
            self._live_stream = create_recording_stream(
                app_id="prml-vslam",
                recording_id=recording_id,
                show_source_rgb=log_source_rgb,
                show_diagnostic_preview=log_diagnostic_preview,
                view_coordinates=view_coordinates,
            )
            attach_recording_sinks(self._live_stream, grpc_url=grpc_url, target_path=None)
        if target_path is not None:
            self._export_stream = create_recording_stream(
                app_id="prml-vslam",
                recording_id=recording_id,
                show_source_rgb=log_source_rgb,
                show_diagnostic_preview=log_diagnostic_preview,
                view_coordinates=view_coordinates,
            )
            attach_recording_sinks(self._export_stream, grpc_url=None, target_path=target_path)

    def observe_update(
        self,
        update: StageRuntimeUpdate,
        *,
        payloads: Mapping[str, np.ndarray] | None = None,
        payload_resolver: PayloadResolver | None = None,
    ) -> None:
        """Observe one live runtime update without durable `RunEvent` wrapping."""
        resolved_payloads = self._resolve_update_payloads(update, payloads=payloads, payload_resolver=payload_resolver)
        if self._live_stream is not None:
            try:
                self._live_policy.observe_update(self._live_stream, update, payloads=resolved_payloads)
                self._live_stream.flush(blocking=False)
            except Exception as exc:  # pragma: no cover - live viewer is best effort
                _LOGGER.warning("Skipping live Rerun update for stage '%s': %s", update.stage_key.value, exc)
        if self._cache_ground_alignment_update(update):
            return
        if self._export_stream is not None:
            self._export_policy.observe_update(self._export_stream, update, payloads=resolved_payloads)

    def close(self) -> None:
        """Release recording handles and post-process export-only overlays."""
        self._close_stream(self._live_stream)
        self._close_stream(self._export_stream)
        self._live_stream = None
        self._export_stream = None
        if self._target_path is None or not self._target_path.exists() or self._latest_ground_alignment is None:
            return
        augment_viewer_recording_with_ground_plane(
            metadata=self._latest_ground_alignment,
            viewer_recording_path=self._target_path,
            recording_id="prml-vslam" if self._recording_id is None else self._recording_id,
        )

    @staticmethod
    def _close_stream(stream) -> None:
        if stream is None:
            return
        stream.flush(blocking=True)
        stream.disconnect()

    def _cache_ground_alignment_update(self, update: StageRuntimeUpdate) -> bool:
        for semantic_event in update.semantic_events:
            if isinstance(semantic_event, GroundAlignmentMetadata) and semantic_event.applied:
                self._latest_ground_alignment = semantic_event
                return True
        return False

    @staticmethod
    def _resolve_update_payloads(
        update: StageRuntimeUpdate,
        *,
        payloads: Mapping[str, np.ndarray] | None,
        payload_resolver: PayloadResolver | None,
    ) -> dict[str, np.ndarray]:
        resolved = (
            {} if payloads is None else {handle_id: np.asarray(payload) for handle_id, payload in payloads.items()}
        )
        if payload_resolver is None:
            return resolved
        for item in update.visualizations:
            for ref in item.payload_refs.values():
                if ref.handle_id in resolved:
                    continue
                payload = payload_resolver(ref)
                if payload is not None:
                    resolved[ref.handle_id] = np.asarray(payload)
        return resolved


@ray.remote(num_cpus=1.0, max_restarts=0, max_task_retries=0)
class RerunSinkActor:
    """Best-effort Ray sidecar that owns one Rerun recording stream."""

    def __init__(
        self,
        *,
        grpc_url: str | None,
        target_path: Path | None,
        recording_id: str | None = None,
        show_tracking_trajectory: bool = True,
        trajectory_pose_axis_length: float = 0.0,
        log_source_rgb: bool = False,
        log_diagnostic_preview: bool = False,
        log_camera_image_rgb: bool = True,
        point_cloud_decimation_keep_ratio: float = 1.0,
        reference_point_cloud_decimation_keep_ratio: float = 1.0,
        mesh_decimation_keep_ratio: float = 1.0,
        decimation_random_seed: int = 0,
        view_coordinates: str = "RDF",
    ) -> None:
        self._sink = RerunEventSink(
            grpc_url=grpc_url,
            target_path=target_path,
            recording_id=recording_id,
            show_tracking_trajectory=show_tracking_trajectory,
            trajectory_pose_axis_length=trajectory_pose_axis_length,
            log_source_rgb=log_source_rgb,
            log_diagnostic_preview=log_diagnostic_preview,
            log_camera_image_rgb=log_camera_image_rgb,
            point_cloud_decimation_keep_ratio=point_cloud_decimation_keep_ratio,
            reference_point_cloud_decimation_keep_ratio=reference_point_cloud_decimation_keep_ratio,
            mesh_decimation_keep_ratio=mesh_decimation_keep_ratio,
            decimation_random_seed=decimation_random_seed,
            view_coordinates=view_coordinates,
        )

    def observe_update(
        self,
        *,
        update: StageRuntimeUpdate,
        payload_resolver: ActorHandle | None = None,
    ) -> None:
        """Forward one live runtime update to the local sink without `ray.get`."""

        def resolve_payload(ref: TransientPayloadRef) -> np.ndarray | None:
            if payload_resolver is None:
                return None
            return cast(np.ndarray | None, ray.get(payload_resolver.read_payload.remote(ref.handle_id)))

        try:
            self._sink.observe_update(
                update,
                payload_resolver=None if payload_resolver is None else resolve_payload,
            )
        except Exception as exc:  # pragma: no cover - best-effort sink guard
            _LOGGER.warning("Skipping Rerun sink runtime update for stage '%s': %s", update.stage_key.value, exc)

    def close(self) -> None:
        self._sink.close()


__all__ = ["MODEL_RGB_2D_ENTITY_PATH", "RerunEventSink", "RerunSinkActor"]
