"""Repo-owned Rerun observer sink and Ray sidecar actor."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from pathlib import Path

import numpy as np
import ray

from prml_vslam.interfaces.alignment import GroundAlignmentMetadata
from prml_vslam.pipeline.contracts.events import RunEvent, StageCompleted
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.visualization.rerun import (
    MODEL_RGB_2D_ENTITY_PATH,
    attach_recording_sinks,
    augment_viewer_recording_with_ground_plane,
    create_recording_stream,
    log_clear,
    log_depth_image,
    log_ground_plane_patch,
    log_line_strip3d,
    log_pinhole,
    log_pointcloud,
    log_rgb_image,
    log_transform,
)

from .rerun_policy import RerunLoggingPolicy

_LOGGER = logging.getLogger(__name__)


class RerunEventSink:
    """Optional observer sink for repo-owned live/export Rerun logging."""

    def __init__(
        self,
        *,
        grpc_url: str | None,
        target_path: Path | None,
        recording_id: str | None = None,
        frusta_history_window_streaming: int | None = 20,
        show_tracking_trajectory: bool = True,
    ) -> None:
        self._live_stream = None
        self._export_stream = None
        self._live_policy = RerunLoggingPolicy(
            log_pinhole=log_pinhole,
            log_pointcloud=log_pointcloud,
            log_line_strip3d=log_line_strip3d,
            log_clear=log_clear,
            log_depth_image=log_depth_image,
            log_ground_plane_patch=log_ground_plane_patch,
            log_rgb_image=log_rgb_image,
            log_transform=log_transform,
            frusta_history_window_streaming=frusta_history_window_streaming,
            show_tracking_trajectory=show_tracking_trajectory,
        )
        self._export_policy = RerunLoggingPolicy(
            log_pinhole=log_pinhole,
            log_pointcloud=log_pointcloud,
            log_line_strip3d=log_line_strip3d,
            log_clear=log_clear,
            log_depth_image=log_depth_image,
            log_ground_plane_patch=log_ground_plane_patch,
            log_rgb_image=log_rgb_image,
            log_transform=log_transform,
            frusta_history_window_streaming=frusta_history_window_streaming,
            show_tracking_trajectory=show_tracking_trajectory,
        )
        self._recording_id = recording_id
        self._target_path = target_path
        self._latest_ground_alignment: GroundAlignmentMetadata | None = None

        if grpc_url is not None:
            self._live_stream = create_recording_stream(app_id="prml-vslam", recording_id=recording_id)
            attach_recording_sinks(self._live_stream, grpc_url=grpc_url, target_path=None)
        if target_path is not None:
            self._export_stream = create_recording_stream(app_id="prml-vslam", recording_id=recording_id)
            attach_recording_sinks(self._export_stream, grpc_url=None, target_path=target_path)

    def observe(self, event: RunEvent, *, payloads: Mapping[str, np.ndarray] | None = None) -> None:
        if self._live_stream is not None:
            self._live_policy.observe(self._live_stream, event, payloads=payloads)
        if self._is_ground_alignment_completion(event):
            self._cache_ground_alignment(event)
            return
        if self._export_stream is not None:
            self._export_policy.observe(self._export_stream, event, payloads=payloads)

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

    @staticmethod
    def _is_ground_alignment_completion(event: RunEvent) -> bool:
        return isinstance(event, StageCompleted) and event.stage_key is StageKey.GROUND_ALIGNMENT

    def _cache_ground_alignment(self, event: RunEvent) -> None:
        if not isinstance(event, StageCompleted):
            return
        metadata = event.ground_alignment
        if metadata is None or not metadata.applied:
            return
        self._latest_ground_alignment = metadata


@ray.remote(num_cpus=0.25, max_restarts=0, max_task_retries=0)
class RerunSinkActor:
    """Best-effort Ray sidecar that owns one Rerun recording stream."""

    def __init__(
        self,
        *,
        grpc_url: str | None,
        target_path: Path | None,
        recording_id: str | None = None,
        frusta_history_window_streaming: int | None = 20,
        show_tracking_trajectory: bool = True,
    ) -> None:
        self._sink = RerunEventSink(
            grpc_url=grpc_url,
            target_path=target_path,
            recording_id=recording_id,
            frusta_history_window_streaming=frusta_history_window_streaming,
            show_tracking_trajectory=show_tracking_trajectory,
        )

    def observe_event(
        self,
        *,
        event: RunEvent,
        rerun_bindings: list[tuple[str, np.ndarray]] | None = None,
    ) -> None:
        try:
            payloads = (
                {}
                if rerun_bindings is None
                else {handle_id: np.asarray(payload) for handle_id, payload in rerun_bindings}
            )
            self._sink.observe(event, payloads=payloads)
        except Exception as exc:  # pragma: no cover - best-effort sink guard
            _LOGGER.warning("Skipping Rerun sink event '%s': %s", event.kind, exc)

    def close(self) -> None:
        self._sink.close()


__all__ = ["MODEL_RGB_2D_ENTITY_PATH", "RerunEventSink", "RerunSinkActor"]
