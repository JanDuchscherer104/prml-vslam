"""Repo-owned Rerun observer sinks and Ray sidecar actors."""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass
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
)

from .rerun_policy import RerunLoggingPolicy

_LOGGER = logging.getLogger(__name__)
PayloadResolver = Callable[[TransientPayloadRef], np.ndarray | None]


@dataclass(frozen=True, slots=True)
class _RerunSinkOptions:
    recording_id: str | None = None
    show_tracking_trajectory: bool = True
    trajectory_pose_axis_length: float = 0.0
    log_source_rgb: bool = False
    log_diagnostic_preview: bool = False
    log_camera_image_rgb: bool = True
    point_cloud_decimation_keep_ratio: float = 1.0
    reference_point_cloud_decimation_keep_ratio: float = 1.0
    mesh_decimation_keep_ratio: float = 1.0
    decimation_random_seed: int = 0
    view_coordinates: str = "RDF"


class _BaseRerunEventSink:
    """Shared single-stream Rerun sink behavior."""

    def __init__(
        self,
        *,
        options: _RerunSinkOptions,
    ) -> None:
        self._console = Console(__name__).child(self.__class__.__name__)
        self._recording_id = options.recording_id
        self._stream = create_recording_stream(
            app_id="prml-vslam",
            recording_id=options.recording_id,
            show_source_rgb=options.log_source_rgb,
            show_diagnostic_preview=options.log_diagnostic_preview,
            view_coordinates=options.view_coordinates,
        )
        self._policy = RerunLoggingPolicy(
            show_tracking_trajectory=options.show_tracking_trajectory,
            trajectory_pose_axis_length=options.trajectory_pose_axis_length,
            log_source_rgb=options.log_source_rgb,
            log_diagnostic_preview=options.log_diagnostic_preview,
            log_camera_image_rgb=options.log_camera_image_rgb,
            point_cloud_decimation_keep_ratio=options.point_cloud_decimation_keep_ratio,
            reference_point_cloud_decimation_keep_ratio=options.reference_point_cloud_decimation_keep_ratio,
            mesh_decimation_keep_ratio=options.mesh_decimation_keep_ratio,
            decimation_random_seed=options.decimation_random_seed,
        )
        self._console.info(
            f"Rerun sink policy: source_rgb={options.log_source_rgb} "
            f"diagnostic_preview={options.log_diagnostic_preview} "
            f"camera_image_rgb={options.log_camera_image_rgb} trajectory={options.show_tracking_trajectory} "
            f"point_cloud_keep_ratio={options.point_cloud_decimation_keep_ratio} "
            f"reference_point_cloud_keep_ratio={options.reference_point_cloud_decimation_keep_ratio} "
            f"mesh_keep_ratio={options.mesh_decimation_keep_ratio} view_coordinates={options.view_coordinates}."
        )

    def observe_update(
        self,
        update: StageRuntimeUpdate,
        *,
        payloads: Mapping[str, np.ndarray] | None = None,
        payload_resolver: PayloadResolver | None = None,
    ) -> None:
        """Observe one runtime update without durable `RunEvent` wrapping."""
        resolved_payloads = self._resolve_update_payloads(update, payloads=payloads, payload_resolver=payload_resolver)
        self._observe_resolved_update(update, payloads=resolved_payloads)

    def _observe_resolved_update(self, update: StageRuntimeUpdate, *, payloads: Mapping[str, np.ndarray]) -> None:
        self._policy.observe_update(self._stream, update, payloads=payloads)

    def close(self) -> None:
        """Release the recording handle."""
        self._stream.flush(blocking=True)
        self._stream.disconnect()

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


class LiveRerunEventSink(_BaseRerunEventSink):
    """Best-effort live Rerun viewer sink."""

    def __init__(
        self,
        *,
        grpc_url: str,
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
        super().__init__(
            options=_RerunSinkOptions(
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
        )
        attach_recording_sinks(self._stream, grpc_url=grpc_url, target_path=None)

    def _observe_resolved_update(self, update: StageRuntimeUpdate, *, payloads: Mapping[str, np.ndarray]) -> None:
        try:
            super()._observe_resolved_update(update, payloads=payloads)
            self._stream.flush(blocking=False)
        except Exception as exc:  # pragma: no cover - live viewer is best effort
            _LOGGER.warning("Skipping live Rerun update for stage '%s': %s", update.stage_key.value, exc)


class ExportRerunEventSink(_BaseRerunEventSink):
    """Durable RRD export sink with export-only post-processing."""

    def __init__(
        self,
        *,
        target_path: Path,
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
        super().__init__(
            options=_RerunSinkOptions(
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
        )
        self._target_path = target_path
        self._latest_ground_alignment: GroundAlignmentMetadata | None = None
        attach_recording_sinks(self._stream, grpc_url=None, target_path=target_path)

    def _observe_resolved_update(self, update: StageRuntimeUpdate, *, payloads: Mapping[str, np.ndarray]) -> None:
        if self._cache_ground_alignment_update(update):
            return
        super()._observe_resolved_update(update, payloads=payloads)

    def close(self) -> None:
        super().close()
        if not self._target_path.exists() or self._latest_ground_alignment is None:
            return
        augment_viewer_recording_with_ground_plane(
            metadata=self._latest_ground_alignment,
            viewer_recording_path=self._target_path,
            recording_id="prml-vslam" if self._recording_id is None else self._recording_id,
        )

    def _cache_ground_alignment_update(self, update: StageRuntimeUpdate) -> bool:
        for semantic_event in update.semantic_events:
            if isinstance(semantic_event, GroundAlignmentMetadata) and semantic_event.applied:
                self._latest_ground_alignment = semantic_event
                return True
        return False


class _ActorPayloadResolverMixin:
    def _observe_with_actor_resolver(
        self,
        *,
        sink: _BaseRerunEventSink,
        update: StageRuntimeUpdate,
        payload_resolver: ActorHandle | None,
    ) -> None:
        def resolve_payload(ref: TransientPayloadRef) -> np.ndarray | None:
            if payload_resolver is None:
                return None
            return cast(np.ndarray | None, ray.get(payload_resolver.read_payload.remote(ref.handle_id)))

        try:
            sink.observe_update(update, payload_resolver=None if payload_resolver is None else resolve_payload)
        except Exception as exc:  # pragma: no cover - best-effort sink guard
            _LOGGER.warning("Skipping Rerun sink runtime update for stage '%s': %s", update.stage_key.value, exc)


@ray.remote(num_cpus=1.0, max_restarts=0, max_task_retries=0)
class LiveRerunSinkActor(_ActorPayloadResolverMixin):
    """Ray sidecar that owns one live Rerun viewer stream."""

    def __init__(
        self,
        *,
        grpc_url: str,
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
        self._sink = LiveRerunEventSink(
            grpc_url=grpc_url,
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

    def observe_update(self, *, update: StageRuntimeUpdate, payload_resolver: ActorHandle | None = None) -> None:
        self._observe_with_actor_resolver(sink=self._sink, update=update, payload_resolver=payload_resolver)

    def close(self) -> None:
        self._sink.close()


@ray.remote(num_cpus=1.0, max_restarts=0, max_task_retries=0)
class ExportRerunSinkActor(_ActorPayloadResolverMixin):
    """Ray sidecar that owns one durable RRD export stream."""

    def __init__(
        self,
        *,
        target_path: Path,
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
        self._sink = ExportRerunEventSink(
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

    def observe_update(self, *, update: StageRuntimeUpdate, payload_resolver: ActorHandle | None = None) -> None:
        self._observe_with_actor_resolver(sink=self._sink, update=update, payload_resolver=payload_resolver)

    def close(self) -> None:
        self._sink.close()


__all__ = [
    "MODEL_RGB_2D_ENTITY_PATH",
    "ExportRerunEventSink",
    "ExportRerunSinkActor",
    "LiveRerunEventSink",
    "LiveRerunSinkActor",
]
