"""Repo-owned Rerun observer sink and Ray sidecar actor."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from pathlib import Path

import numpy as np
import ray

from prml_vslam.pipeline.contracts.events import RunEvent
from prml_vslam.visualization.rerun import (
    MODEL_RGB_2D_ENTITY_PATH,
    attach_recording_sinks,
    create_recording_stream,
    log_clear,
    log_depth_image,
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
        self._stream = None
        self._policy = RerunLoggingPolicy(
            log_pinhole=log_pinhole,
            log_pointcloud=log_pointcloud,
            log_line_strip3d=log_line_strip3d,
            log_clear=log_clear,
            log_depth_image=log_depth_image,
            log_rgb_image=log_rgb_image,
            log_transform=log_transform,
            frusta_history_window_streaming=frusta_history_window_streaming,
            show_tracking_trajectory=show_tracking_trajectory,
        )
        if grpc_url is None and target_path is None:
            return
        self._stream = create_recording_stream(app_id="prml-vslam", recording_id=recording_id)
        attach_recording_sinks(self._stream, grpc_url=grpc_url, target_path=target_path)

    def observe(self, event: RunEvent, *, payloads: Mapping[str, np.ndarray] | None = None) -> None:
        if self._stream is None:
            return
        self._policy.observe(self._stream, event, payloads=payloads)

    def close(self) -> None:
        """Release the recording handle after queued events drain."""
        self._stream = None


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
