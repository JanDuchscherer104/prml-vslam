"""Async Record3D Wi-Fi preview receiver runtime."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from contextlib import suppress
from typing import Any

from prml_vslam.interfaces import FramePacket

from .wifi_packets import Record3DWiFiMetadata, record3d_wifi_packet_from_video_frame
from .wifi_signaling import build_record3d_answer_request_payload


def _import_aiortc_modules() -> tuple[type[Any], type[Any]]:
    """Import the optional Python WebRTC dependencies used by Wi-Fi capture."""
    try:
        from aiortc import RTCPeerConnection, RTCSessionDescription
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "The optional `aiortc` dependency is required for Record3D Wi-Fi preview streaming. "
            "Install it with `uv sync --extra streaming`."
        ) from exc
    return RTCPeerConnection, RTCSessionDescription


class _Record3DWiFiReceiverRuntime:
    """Async receiver runtime used by the Record3D Wi-Fi session wrapper."""

    def __init__(
        self,
        config: Any,
        *,
        console: Any,
        device_address: str,
        get_offer: Callable[[], dict[str, Any]],
        get_metadata: Callable[[], dict[str, Any]],
        send_answer: Callable[[dict[str, Any]], None],
        on_metadata: Callable[[Record3DWiFiMetadata], None],
        on_connected: Callable[[Record3DWiFiMetadata], None],
        on_packet: Callable[[FramePacket], None],
        on_failure: Callable[[str], None],
        stop_requested: Callable[[], bool],
    ) -> None:
        self.config = config
        self.console = console
        self.device_address = device_address
        self.get_offer = get_offer
        self.get_metadata = get_metadata
        self.send_answer = send_answer
        self.on_metadata = on_metadata
        self.on_connected = on_connected
        self.on_packet = on_packet
        self.on_failure = on_failure
        self.stop_requested = stop_requested
        self.metadata = Record3DWiFiMetadata(device_address=device_address)
        self._connected = False
        self._next_packet_seq = 0
        self._loop: asyncio.AbstractEventLoop | None = None
        self._async_stop: asyncio.Event | None = None

    def run(self) -> None:
        try:
            asyncio.run(self._run())
        except Exception as exc:
            if not self.stop_requested():
                self.on_failure(str(exc))

    def request_stop(self) -> None:
        if self._async_stop is None:
            return
        if self._loop is None:
            self._async_stop.set()
            return
        try:
            self._loop.call_soon_threadsafe(self._async_stop.set)
        except RuntimeError:
            pass

    def _handle_loop_exception(self, loop: asyncio.AbstractEventLoop, context: dict[str, Any]) -> None:
        exception = context.get("exception")
        message = str(context.get("message", ""))
        if _should_suppress_record3d_async_exception(
            exception=exception if isinstance(exception, BaseException) else None,
            message=message,
            stop_requested=self.stop_requested(),
        ):
            return
        loop.default_exception_handler(context)

    @staticmethod
    def _fail_pending_track_wait(*, connection_state: str, video_track_ready: Any | None) -> None:
        if video_track_ready is None or video_track_ready.done():
            return
        video_track_ready.set_exception(
            RuntimeError(
                "The Record3D Wi-Fi peer connection "
                f"entered `{connection_state}` before the video track became available."
            )
        )

    def _handle_connection_state_change(self, *, connection_state: str, video_track_ready: Any | None) -> None:
        if self.stop_requested():
            return
        if connection_state == "failed":
            if self._connected:
                self.on_failure("The Record3D Wi-Fi peer connection failed.")
            else:
                self._fail_pending_track_wait(connection_state=connection_state, video_track_ready=video_track_ready)
            self.request_stop()
            return
        if connection_state not in {"closed", "disconnected"}:
            return
        if self._connected:
            self.on_failure(f"The Record3D Wi-Fi peer connection entered `{connection_state}`.")
        else:
            self._fail_pending_track_wait(connection_state=connection_state, video_track_ready=video_track_ready)
        self.request_stop()

    async def _wait_for_ice_gathering_complete(self, *, peer_connection: Any) -> None:
        if str(getattr(peer_connection, "iceGatheringState", "new")) == "complete":
            return
        ice_complete = asyncio.Event()

        @peer_connection.on("icegatheringstatechange")
        async def _on_ice_gathering_state_change() -> None:
            if str(getattr(peer_connection, "iceGatheringState", "new")) == "complete":
                ice_complete.set()

        await asyncio.wait_for(ice_complete.wait(), timeout=self.config.setup_timeout_seconds)

    async def _load_metadata_best_effort(self) -> None:
        try:
            payload = await asyncio.to_thread(self.get_metadata)
            self.metadata = Record3DWiFiMetadata.from_api_payload(device_address=self.device_address, payload=payload)
            self.on_metadata(self.metadata)
        except Exception as exc:
            if not self.stop_requested():
                self.console.warning("Could not retrieve Record3D Wi-Fi metadata: %s", exc)

    async def _run(self) -> None:
        RTCPeerConnection, RTCSessionDescription = _import_aiortc_modules()
        self._loop = asyncio.get_running_loop()
        self._loop.set_exception_handler(self._handle_loop_exception)
        self._async_stop = asyncio.Event()
        peer_connection = RTCPeerConnection()
        video_track_ready: asyncio.Future[Any] = self._loop.create_future()
        metadata_task = asyncio.create_task(self._load_metadata_best_effort())

        @peer_connection.on("track")
        def _on_track(track: Any) -> None:
            if getattr(track, "kind", None) == "video" and not video_track_ready.done():
                video_track_ready.set_result(track)

        @peer_connection.on("connectionstatechange")
        async def _on_connection_state_change() -> None:
            self._handle_connection_state_change(
                connection_state=str(getattr(peer_connection, "connectionState", "unknown")),
                video_track_ready=video_track_ready,
            )

        try:
            offer_payload = await asyncio.to_thread(self.get_offer)
            await peer_connection.setRemoteDescription(
                RTCSessionDescription(sdp=str(offer_payload["sdp"]), type=str(offer_payload["type"]))
            )
            answer = await peer_connection.createAnswer()
            await peer_connection.setLocalDescription(answer)
            await self._wait_for_ice_gathering_complete(peer_connection=peer_connection)
            local_description = peer_connection.localDescription
            if local_description is None:
                raise RuntimeError("Failed to produce a local WebRTC answer for the Record3D Wi-Fi preview stream.")

            await asyncio.to_thread(
                self.send_answer,
                build_record3d_answer_request_payload(sdp=local_description.sdp),
            )
            track = await asyncio.wait_for(video_track_ready, timeout=self.config.setup_timeout_seconds)
            self._connected = True
            self.on_connected(self.metadata)
            await self._consume_video_track(track)
        finally:
            if not metadata_task.done():
                metadata_task.cancel()
            with suppress(asyncio.CancelledError):
                await metadata_task
            await peer_connection.close()
            self._loop = None
            self._async_stop = None

    async def _consume_video_track(self, track: Any) -> None:
        while not self.stop_requested():
            if self._async_stop is not None and self._async_stop.is_set():
                break
            try:
                video_frame = await asyncio.wait_for(track.recv(), timeout=self.config.frame_timeout_seconds)
            except TimeoutError:
                continue
            except Exception as exc:
                if self.stop_requested():
                    break
                raise RuntimeError("The Record3D Wi-Fi preview video track stopped unexpectedly.") from exc
            timestamp_ns = time.time_ns()
            self.on_packet(
                record3d_wifi_packet_from_video_frame(
                    video_frame,
                    metadata=self.metadata,
                    seq=self._next_packet_seq,
                    timestamp_ns=timestamp_ns,
                )
            )
            self._next_packet_seq += 1


def _should_suppress_record3d_async_exception(
    *,
    exception: BaseException | None,
    message: str,
    stop_requested: bool,
) -> bool:
    """Return whether an async exception is expected during aiortc teardown."""
    if not stop_requested:
        return False
    combined = message if exception is None else f"{message} {type(exception).__name__}: {exception}"
    return any(
        fragment in combined
        for fragment in (
            "RTCIceTransport is closed",
            "'NoneType' object has no attribute 'sendto'",
            "'NoneType' object has no attribute 'call_exception_handler'",
        )
    )


__all__ = ["_Record3DWiFiReceiverRuntime"]
