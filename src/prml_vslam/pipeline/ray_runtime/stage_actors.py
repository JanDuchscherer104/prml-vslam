"""Ray actors that execute streaming source I/O."""

from __future__ import annotations

import threading
import time
from collections import deque

import numpy as np
import ray

from prml_vslam.pipeline.ray_runtime.common import (
    DEFAULT_MAX_FRAMES_IN_FLIGHT,
    put_transient_payload,
)
from prml_vslam.protocols.source import StreamingSequenceSource
from prml_vslam.utils import FPS_WINDOW, Console, rolling_fps


@ray.remote(num_cpus=1, max_restarts=0, max_task_retries=0)
class PacketSourceActor:
    """Read packets from one streaming source with coordinator-owned credits."""

    def __init__(self, *, coordinator_name: str, namespace: str, frame_timeout_seconds: float = 5.0) -> None:
        self._console = Console(__name__).child(self.__class__.__name__).child(coordinator_name)
        self._coordinator = ray.get_actor(coordinator_name, namespace=namespace)
        self._frame_timeout_seconds = frame_timeout_seconds
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._credits = 0
        self._credits_cv = threading.Condition()
        self._processed_frame_count = 0
        self._packet_timestamps = deque(maxlen=FPS_WINDOW)

    def start_stream(
        self,
        *,
        source: StreamingSequenceSource,
        initial_credits: int = DEFAULT_MAX_FRAMES_IN_FLIGHT,
        loop: bool = False,
    ) -> None:
        if self._thread is not None and self._thread.is_alive():
            raise RuntimeError("Packet source actor is already running.")
        self._console.info(
            "Starting packet stream for source '%s' with loop=%s, initial_credits=%d, timeout=%s.",
            getattr(source, "label", source.__class__.__name__),
            loop,
            initial_credits,
            self._frame_timeout_seconds,
        )
        self._stop_event.clear()
        self._credits = initial_credits
        self._thread = threading.Thread(target=self._run_source, args=(source, loop), daemon=True)
        self._thread.start()

    def grant_credit(self, count: int = 1) -> None:
        with self._credits_cv:
            self._credits += count
            self._credits_cv.notify_all()

    def stop(self) -> None:
        self._stop_event.set()
        with self._credits_cv:
            self._credits_cv.notify_all()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            if self._thread.is_alive():
                self._console.warning("Timed out waiting for packet source worker thread to stop.")

    def _run_source(self, source: StreamingSequenceSource, loop: bool) -> None:
        stream = source.open_stream(loop=loop)
        try:
            stream.connect()
            while not self._stop_event.is_set():
                with self._credits_cv:
                    while self._credits <= 0 and not self._stop_event.is_set():
                        self._credits_cv.wait(timeout=0.1)
                    if self._stop_event.is_set():
                        self._console.debug("Stop requested while waiting for packet credits.")
                        break
                    self._credits -= 1
                packet = stream.wait_for_observation(timeout_seconds=self._frame_timeout_seconds)
                self._processed_frame_count += 1
                self._packet_timestamps.append(time.monotonic())
                frame_payload_ref, frame_ref = put_transient_payload(
                    packet.rgb,
                    payload_kind="image",
                    media_type="image/rgb",
                    metadata={"slot": "image"},
                )
                depth_payload_ref, depth_ref = put_transient_payload(
                    packet.depth_m,
                    payload_kind="depth",
                    media_type="image/depth",
                    metadata={"slot": "depth"},
                )
                confidence_ref = None if packet.confidence is None else ray.put(np.asarray(packet.confidence))
                pointmap_payload_ref, pointmap_ref = put_transient_payload(
                    packet.pointmap_xyz,
                    payload_kind="point_cloud",
                    media_type="application/x.pointmap",
                    metadata={"slot": "pointmap"},
                )
                self._coordinator.on_packet.remote(
                    packet=packet,
                    frame_ref=frame_ref,
                    depth_ref=depth_ref,
                    confidence_ref=confidence_ref,
                    pointmap_ref=pointmap_ref,
                    intrinsics=packet.intrinsics,
                    pose=packet.T_world_camera,
                    provenance=packet.provenance.model_copy(deep=True),
                    processed_frame_count=self._processed_frame_count,
                    measured_fps=rolling_fps(self._packet_timestamps),
                    frame_payload_ref=frame_payload_ref,
                    depth_payload_ref=depth_payload_ref,
                    pointmap_payload_ref=pointmap_payload_ref,
                )
        except EOFError:
            self._console.debug("Streaming source reached EOF.")
            self._coordinator.on_source_eof.remote()
        except Exception as exc:  # pragma: no cover - exercised via integration tests
            self._console.error("Streaming source raised an unexpected exception: %s", exc)
            self._coordinator.on_source_error.remote(str(exc))
        finally:
            try:
                stream.disconnect()
            except Exception:
                pass


__all__ = ["PacketSourceActor"]
