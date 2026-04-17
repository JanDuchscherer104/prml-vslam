"""Repo-owned Rerun observer sink and Ray sidecar actor."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeAlias

import numpy as np
import ray

from prml_vslam.methods.events import KeyframeVisualizationReady, PoseEstimated
from prml_vslam.pipeline.contracts.events import BackendNoticeReceived, PacketObserved, RunEvent
from prml_vslam.visualization.contracts import RerunModality, default_rerun_modalities
from prml_vslam.visualization.rerun import (
    attach_recording_sinks,
    create_recording_stream,
    log_depth_image,
    log_pinhole,
    log_pointcloud,
    log_rgb_image,
    log_transform,
)

_LOGGER = logging.getLogger(__name__)


class RerunEventSink:
    """Optional observer sink for repo-owned live/export Rerun logging."""

    def __init__(
        self,
        *,
        grpc_url: str | None,
        target_path: Path | None,
        modalities: list[RerunModality] | None = None,
        recording_id: str | None = None,
    ) -> None:
        self._stream = None
        self._modalities = frozenset(default_rerun_modalities() if modalities is None else modalities)
        if grpc_url is None and target_path is None:
            return
        self._log_pinhole = log_pinhole
        self._log_pointcloud = log_pointcloud
        self._log_depth_image = log_depth_image
        self._log_rgb_image = log_rgb_image
        self._log_transform = log_transform
        self._stream = create_recording_stream(app_id="prml-vslam", recording_id=recording_id)
        attach_recording_sinks(self._stream, grpc_url=grpc_url, target_path=target_path)

    def observe(self, event: RunEvent, *, resolve_handle: Callable[[str], np.ndarray | None]) -> None:
        if self._stream is None:
            return
        match event:
            case PacketObserved(frame=frame) if frame is not None:
                if RerunModality.SOURCE_RGB in self._modalities:
                    self._clear_keyframe_timeline()
                    image = resolve_handle(frame.handle_id)
                    if image is not None:
                        self._log_rgb_image(self._stream, entity_path="world/live/source/rgb", image_rgb=image)
            case BackendNoticeReceived(notice=notice):
                match notice:
                    case PoseEstimated(pose=pose):
                        if RerunModality.CAMERA_POSE in self._modalities:
                            self._clear_keyframe_timeline()
                            self._log_transform(
                                self._stream,
                                entity_path="world/live/camera",
                                transform=pose,
                            )
                    case KeyframeVisualizationReady() as keyframe_notice:
                        self._log_keyframe_visualization(keyframe_notice, resolve_handle=resolve_handle)
                    case _:
                        pass
            case _:
                return

    def close(self) -> None:
        """Release the recording handle after queued events drain."""
        self._stream = None

    def _log_keyframe_visualization(
        self,
        notice: KeyframeVisualizationReady,
        *,
        resolve_handle: Callable[[str], np.ndarray | None],
    ) -> None:
        if self._stream is None:
            return
        live_camera_entity = "world/live/camera"
        live_camera_image_entity = f"{live_camera_entity}/cam"
        live_pointmap_entity = "world/live/pointmap"
        keyframe_camera_entity = f"world/est/cameras/cam_{notice.keyframe_index:06d}"
        keyframe_image_entity = f"{keyframe_camera_entity}/cam"
        keyframe_pointmap_entity = f"world/est/pointmaps/cam_{notice.keyframe_index:06d}"

        rgb = self._resolve_optional_array(
            notice.image,
            resolve_handle=resolve_handle,
            enabled=RerunModality.KEYFRAME_RGB in self._modalities,
        )
        depth_image = self._resolve_optional_array(
            notice.depth,
            resolve_handle=resolve_handle,
            enabled=RerunModality.KEYFRAME_DEPTH in self._modalities,
        )
        preview_image = self._resolve_optional_array(
            notice.preview,
            resolve_handle=resolve_handle,
            enabled=RerunModality.DIAGNOSTIC_PREVIEW in self._modalities,
        )
        pointmap = self._resolve_optional_array(
            notice.pointmap,
            resolve_handle=resolve_handle,
            enabled=RerunModality.POINTMAPS in self._modalities,
        )

        self._log_live_branch(
            pose=notice.pose,
            camera_entity=live_camera_entity,
            camera_image_entity=live_camera_image_entity,
            pointmap_entity=live_pointmap_entity,
            intrinsics=notice.camera_intrinsics,
            rgb=rgb,
            depth_image=depth_image,
            preview_image=preview_image,
            pointmap=pointmap,
        )
        self._log_keyed_branch(
            keyframe_index=notice.keyframe_index,
            pose=notice.pose,
            camera_entity=keyframe_camera_entity,
            camera_image_entity=keyframe_image_entity,
            pointmap_entity=keyframe_pointmap_entity,
            intrinsics=notice.camera_intrinsics,
            rgb=rgb,
            depth_image=depth_image,
            preview_image=preview_image,
            pointmap=pointmap,
        )

    def _log_live_branch(
        self,
        *,
        pose: object,
        camera_entity: str,
        camera_image_entity: str,
        pointmap_entity: str,
        intrinsics: object,
        rgb: np.ndarray | None,
        depth_image: np.ndarray | None,
        preview_image: np.ndarray | None,
        pointmap: np.ndarray | None,
    ) -> None:
        self._clear_keyframe_timeline()
        self._log_transform(self._stream, entity_path=camera_entity, transform=pose)
        self._log_camera_payloads(
            camera_entity=camera_entity,
            camera_image_entity=camera_image_entity,
            intrinsics=intrinsics,
            rgb=rgb,
            depth_image=depth_image,
            preview_image=preview_image,
        )
        self._log_pointmap_branch(pointmap_entity=pointmap_entity, pose=pose, pointmap=pointmap, rgb=rgb)

    def _log_keyed_branch(
        self,
        *,
        keyframe_index: int,
        pose: object,
        camera_entity: str,
        camera_image_entity: str,
        pointmap_entity: str,
        intrinsics: object,
        rgb: np.ndarray | None,
        depth_image: np.ndarray | None,
        preview_image: np.ndarray | None,
        pointmap: np.ndarray | None,
    ) -> None:
        self._stream.set_time("keyframe", sequence=keyframe_index)
        self._log_transform(self._stream, entity_path=camera_entity, transform=pose)
        self._log_camera_payloads(
            camera_entity=camera_entity,
            camera_image_entity=camera_image_entity,
            intrinsics=intrinsics,
            rgb=rgb,
            depth_image=depth_image,
            preview_image=preview_image,
        )
        self._log_pointmap_branch(pointmap_entity=pointmap_entity, pose=pose, pointmap=pointmap, rgb=rgb)

    def _log_camera_payloads(
        self,
        *,
        camera_entity: str,
        camera_image_entity: str,
        intrinsics: object,
        rgb: np.ndarray | None,
        depth_image: np.ndarray | None,
        preview_image: np.ndarray | None,
    ) -> None:
        if intrinsics is not None and self._should_log_camera_pinhole(image=rgb, depth=depth_image):
            self._log_pinhole(self._stream, entity_path=camera_image_entity, intrinsics=intrinsics)

        if rgb is not None and RerunModality.KEYFRAME_RGB in self._modalities:
            self._log_rgb_image(self._stream, entity_path=camera_image_entity, image_rgb=rgb)

        if depth_image is not None and RerunModality.KEYFRAME_DEPTH in self._modalities:
            self._log_depth_image(self._stream, entity_path=f"{camera_image_entity}/depth", depth_m=depth_image)

        if preview_image is not None and RerunModality.DIAGNOSTIC_PREVIEW in self._modalities:
            self._log_rgb_image(self._stream, entity_path=f"{camera_entity}/preview", image_rgb=preview_image)

    def _log_pointmap_branch(
        self,
        *,
        pointmap_entity: str,
        pose: object,
        pointmap: np.ndarray | None,
        rgb: np.ndarray | None,
    ) -> None:
        if pointmap is None or RerunModality.POINTMAPS not in self._modalities:
            return
        self._log_transform(
            self._stream,
            entity_path=pointmap_entity,
            transform=pose,
            axis_length=0.0,
        )
        point_colors = rgb if rgb is not None and RerunModality.KEYFRAME_RGB in self._modalities else None
        self._log_pointcloud(
            self._stream,
            entity_path=f"{pointmap_entity}/points",
            pointmap=pointmap,
            colors=point_colors,
        )

    def _clear_keyframe_timeline(self) -> None:
        if self._stream is None:
            return
        self._stream.disable_timeline("keyframe")

    @staticmethod
    def _resolve_optional_array(
        handle: object,
        *,
        resolve_handle: Callable[[str], np.ndarray | None],
        enabled: bool,
    ) -> np.ndarray | None:
        if not enabled or handle is None:
            return None
        return resolve_handle(handle.handle_id)

    def _should_log_camera_pinhole(self, *, image: object, depth: object) -> bool:
        return any(
            modality in self._modalities
            for modality in (
                RerunModality.CAMERA_INTRINSICS,
                RerunModality.KEYFRAME_RGB if image is not None else None,
                RerunModality.KEYFRAME_DEPTH if depth is not None else None,
            )
            if modality is not None
        )


@ray.remote(num_cpus=0.25, max_restarts=0, max_task_retries=0)
class RerunSinkActor:
    """Best-effort Ray sidecar that owns one Rerun recording stream."""

    HandlePayload: TypeAlias = ray.ObjectRef[Any] | np.ndarray

    def __init__(
        self,
        *,
        grpc_url: str | None,
        target_path: Path | None,
        modalities: list[RerunModality] | None = None,
        recording_id: str | None = None,
    ) -> None:
        self._sink = RerunEventSink(
            grpc_url=grpc_url,
            target_path=target_path,
            modalities=modalities,
            recording_id=recording_id,
        )

    def observe_event(
        self,
        *,
        event: RunEvent,
        bindings: list[tuple[str, HandlePayload]] | None = None,
    ) -> None:
        try:
            payloads = {handle_id: payload for handle_id, payload in ([] if bindings is None else bindings)}
            self._sink.observe(
                event,
                resolve_handle=lambda handle_id: (
                    None if handle_id not in payloads else self._resolve_payload(payloads[handle_id])
                ),
            )
        except Exception as exc:  # pragma: no cover - best-effort sink guard
            _LOGGER.warning("Skipping Rerun sink event '%s': %s", getattr(event, "kind", type(event).__name__), exc)

    def close(self) -> None:
        self._sink.close()

    @staticmethod
    def _resolve_payload(payload: HandlePayload) -> np.ndarray:
        if isinstance(payload, np.ndarray):
            return np.asarray(payload)
        return np.asarray(ray.get(payload))


__all__ = ["RerunEventSink", "RerunSinkActor"]
