"""Python-side Record3D Wi-Fi capture and packet decoding."""

from __future__ import annotations

import asyncio
import json
import time
from contextlib import suppress
from queue import Empty, Queue
from threading import Event, Thread, current_thread
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import numpy as np
from numpy.typing import NDArray
from pydantic import Field

from prml_vslam.utils import BaseConfig, Console

from .record3d import (
    Record3DConnectionError,
    Record3DDependencyError,
    Record3DError,
    Record3DFramePacket,
    Record3DIntrinsicMatrix,
    Record3DTimeoutError,
    Record3DTransportId,
)


def _import_aiortc_modules() -> tuple[type[Any], type[Any]]:
    """Import the optional Python WebRTC dependencies used by Wi-Fi capture."""
    try:
        from aiortc import RTCPeerConnection, RTCSessionDescription
    except ModuleNotFoundError as exc:
        raise Record3DDependencyError(
            "The optional `aiortc` dependency is required for Record3D Wi-Fi streaming. "
            "Install it with `uv sync --extra streaming`."
        ) from exc

    return RTCPeerConnection, RTCSessionDescription


def normalize_record3d_device_address(value: str) -> str:
    """Normalize a Record3D device address into an explicit HTTP URL.

    Args:
        value: User-provided mDNS name, IP address, or absolute URL.

    Returns:
        Normalized absolute URL without a trailing slash.
    """
    trimmed = value.strip()
    if trimmed == "":
        return ""
    if trimmed.startswith(("http://", "https://")):
        return trimmed.rstrip("/")
    return f"http://{trimmed.rstrip('/')}"


class Record3DWiFiMetadata(BaseConfig):
    """Typed metadata returned by the Record3D Wi-Fi HTTP API."""

    device_address: str
    """Normalized device base URL used for signaling."""

    intrinsic_matrix: Record3DIntrinsicMatrix | None = None
    """Camera intrinsic matrix reported by the device when available."""

    original_width: int | None = None
    """Original composite-frame width reported by the device."""

    original_height: int | None = None
    """Original composite-frame height reported by the device."""

    depth_max_meters: float = 3.0
    """Depth range upper bound used by the HSV transport encoding."""

    raw_metadata: dict[str, Any] = Field(default_factory=dict)
    """Raw metadata payload returned by the Record3D endpoint."""

    @classmethod
    def from_api_payload(cls, *, device_address: str, payload: dict[str, Any]) -> Record3DWiFiMetadata:
        """Parse the raw Record3D metadata payload.

        Args:
            device_address: Normalized Record3D base URL.
            payload: Raw JSON object returned by `/metadata`.

        Returns:
            Typed Wi-Fi metadata.
        """
        intrinsic_matrix = cls._parse_intrinsic_matrix(payload)
        original_width, original_height = cls._parse_original_size(payload)
        depth_max_meters = cls._parse_depth_range(payload)
        return cls(
            device_address=device_address,
            intrinsic_matrix=intrinsic_matrix,
            original_width=original_width,
            original_height=original_height,
            depth_max_meters=depth_max_meters,
            raw_metadata=dict(payload),
        )

    @staticmethod
    def _parse_intrinsic_matrix(payload: dict[str, Any]) -> Record3DIntrinsicMatrix | None:
        raw_matrix = payload.get("K")
        if raw_matrix is None:
            return None

        matrix = np.asarray(raw_matrix, dtype=np.float64)
        if matrix.shape == (9,):
            matrix = matrix.reshape(3, 3)
        if matrix.shape != (3, 3):
            raise Record3DError(
                "Record3D Wi-Fi metadata field `K` must be a flat 9-vector or a 3x3 matrix, "
                f"but received shape {tuple(matrix.shape)}."
            )

        return Record3DIntrinsicMatrix(
            fx=float(matrix[0, 0]),
            fy=float(matrix[1, 1]),
            tx=float(matrix[0, 2]),
            ty=float(matrix[1, 2]),
        )

    @staticmethod
    def _parse_original_size(payload: dict[str, Any]) -> tuple[int | None, int | None]:
        raw_size = payload.get("originalSize")
        if isinstance(raw_size, dict):
            width = raw_size.get("width")
            height = raw_size.get("height")
        elif isinstance(raw_size, list | tuple) and len(raw_size) >= 2:
            width, height = raw_size[:2]
        else:
            width = payload.get("width") or payload.get("rgbWidth")
            height = payload.get("height") or payload.get("rgbHeight")

        normalized_width = int(width) if width is not None else None
        normalized_height = int(height) if height is not None else None
        return normalized_width, normalized_height

    @staticmethod
    def _parse_depth_range(payload: dict[str, Any]) -> float:
        for key in ("depthMaxMeters", "depth_max_meters", "maxDepthMeters", "maxDepth"):
            value = payload.get(key)
            if value is not None:
                return float(value)
        return 3.0


class Record3DWiFiSignalingClient:
    """Small synchronous client for the Record3D Wi-Fi signaling endpoints."""

    def __init__(self, device_address: str, *, timeout_seconds: float) -> None:
        normalized = normalize_record3d_device_address(device_address)
        if normalized == "":
            raise Record3DConnectionError("Record3D Wi-Fi streaming requires a device address.")
        self.device_address = normalized
        self.timeout_seconds = timeout_seconds

    def get_offer(self) -> dict[str, Any]:
        """Fetch the device's WebRTC offer from `/getOffer`."""
        try:
            return self._request_json("GET", "/getOffer")
        except HTTPError as exc:
            if exc.code == 403:
                raise Record3DConnectionError(
                    "Record3D allows only one Wi-Fi receiver at a time. Disconnect the existing peer and retry."
                ) from exc
            raise Record3DConnectionError(f"Record3D offer request failed with HTTP {exc.code}.") from exc
        except TimeoutError as exc:
            raise Record3DConnectionError("Timed out waiting for the Record3D Wi-Fi offer from the device.") from exc
        except URLError as exc:
            raise Record3DConnectionError(
                "Could not reach the Record3D device. Check that the iPhone and this machine are on the same network."
            ) from exc

    def get_metadata(self) -> dict[str, Any]:
        """Fetch the device metadata from `/metadata`."""
        try:
            return self._request_json("GET", "/metadata")
        except HTTPError as exc:
            raise Record3DConnectionError(f"Record3D metadata request failed with HTTP {exc.code}.") from exc
        except TimeoutError as exc:
            raise Record3DConnectionError("Timed out waiting for Record3D Wi-Fi metadata from the device.") from exc
        except URLError as exc:
            raise Record3DConnectionError("Could not retrieve Record3D metadata from the configured device.") from exc

    def send_answer(self, answer: dict[str, Any]) -> None:
        """Post the local WebRTC answer to the Record3D device.

        The official Record3D browser demo and the local `feat/record3d` prototype both
        post to `/answer`. The README mentions `/sendAnswer`, so the client uses the
        browser-demo path first and only falls back when the alternate endpoint is the
        only one available.

        Args:
            answer: Local WebRTC answer payload.
        """
        for endpoint in ("/answer", "/sendAnswer"):
            try:
                self._request_json("POST", endpoint, payload=answer, expect_json=False)
                return
            except HTTPError as exc:
                if exc.code in {404, 405}:
                    continue
                raise Record3DConnectionError(
                    f"Record3D answer request to `{endpoint}` failed with HTTP {exc.code}."
                ) from exc
            except TimeoutError as exc:
                if endpoint == "/answer":
                    continue
                raise Record3DConnectionError(
                    f"Timed out sending the WebRTC answer to `{endpoint}` on the Record3D device."
                ) from exc
            except URLError as exc:
                raise Record3DConnectionError("Could not send the WebRTC answer back to the Record3D device.") from exc

        raise Record3DConnectionError("Record3D did not accept the WebRTC answer on `/answer` or `/sendAnswer`.")

    def _request_json(
        self,
        method: str,
        endpoint: str,
        *,
        payload: dict[str, Any] | None = None,
        expect_json: bool = True,
    ) -> dict[str, Any]:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            url=f"{self.device_address}{endpoint}",
            data=data,
            method=method,
            headers={"Content-Type": "application/json"} if payload is not None else {},
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310
            body = response.read()
        if not expect_json:
            return {}
        loaded = json.loads(body.decode("utf-8"))
        if not isinstance(loaded, dict):
            raise Record3DError(f"Expected JSON object from `{endpoint}`, but received {type(loaded).__name__}.")
        return loaded


class Record3DWiFiStreamConfig(BaseConfig):
    """Configuration for a Python-side Record3D Wi-Fi receiver."""

    device_address: str = ""
    """mDNS host, IP address, or absolute URL advertised by the Record3D app."""

    frame_timeout_seconds: float = 5.0
    """Maximum time to wait for the next frame before failing."""

    signaling_timeout_seconds: float = 5.0
    """Maximum time to wait for signaling and peer setup."""

    setup_timeout_seconds: float = 10.0
    """Maximum time to wait for ICE gathering and the initial video track."""

    @property
    def target_type(self) -> type[Record3DWiFiStreamSession]:
        """Runtime type used to manage one Record3D Wi-Fi session."""
        return Record3DWiFiStreamSession


class Record3DWiFiStreamSession:
    """Manage one Python-side Record3D Wi-Fi session."""

    def __init__(self, config: Record3DWiFiStreamConfig) -> None:
        self.config = config
        self.console = Console(__name__).child(self.__class__.__name__)
        self.signaling_client = Record3DWiFiSignalingClient(
            config.device_address,
            timeout_seconds=config.signaling_timeout_seconds,
        )
        self._packet_queue: Queue[Record3DFramePacket] = Queue()
        self._connected_event = Event()
        self._failure_event = Event()
        self._stop_event = Event()
        self._worker: Thread | None = None
        self._failure_message = ""
        self._metadata: Record3DWiFiMetadata | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._async_stop: asyncio.Event | None = None
        self._peer_connection: Any | None = None

    def connect(self) -> Record3DWiFiMetadata:
        """Connect to the configured Wi-Fi sender and start queueing packets.

        Returns:
            Typed metadata reported by the Record3D device.
        """
        if self._worker is not None and self._worker.is_alive():
            raise Record3DConnectionError("The Record3D Wi-Fi session is already active.")

        self._metadata = Record3DWiFiMetadata(
            device_address=self.signaling_client.device_address,
        )
        self._packet_queue = Queue()
        self._connected_event.clear()
        self._failure_event.clear()
        self._stop_event.clear()
        self._failure_message = ""

        self._worker = Thread(target=self._run_worker, name="Record3DWiFiStreamSession", daemon=True)
        self._worker.start()

        deadline = time.monotonic() + self.config.setup_timeout_seconds
        while time.monotonic() < deadline:
            if self._connected_event.wait(timeout=0.05):
                self.console.info("Connected to Record3D Wi-Fi stream at %s.", self.signaling_client.device_address)
                return self._metadata
            if self._failure_event.is_set():
                raise Record3DConnectionError(self._failure_message)
            if self._worker is not None and not self._worker.is_alive():
                break

        self.disconnect()
        raise Record3DConnectionError(
            f"Timed out establishing the Record3D Wi-Fi stream at {self.signaling_client.device_address}."
        )

    def disconnect(self) -> None:
        """Disconnect the current Wi-Fi session and stop the worker thread."""
        self._stop_event.set()
        if self._async_stop is not None and self._loop is not None:
            try:
                self._loop.call_soon_threadsafe(self._async_stop.set)
            except RuntimeError:
                pass

        worker = self._worker
        if worker is None:
            return

        if current_thread() is worker:
            return

        join_timeout_seconds = max(5.0, self.config.setup_timeout_seconds + 1.0)
        worker.join(timeout=join_timeout_seconds)
        if worker.is_alive():
            self.console.warning("Timed out stopping the Record3D Wi-Fi worker thread during cleanup.")
            return
        self._worker = None

    def wait_for_packet(self, timeout_seconds: float | None = None) -> Record3DFramePacket:
        """Wait for the next decoded Wi-Fi packet.

        Args:
            timeout_seconds: Optional timeout override. Defaults to the config value.

        Returns:
            Next decoded packet from the Wi-Fi receiver.
        """
        timeout = self.config.frame_timeout_seconds if timeout_seconds is None else timeout_seconds
        try:
            return self._packet_queue.get(timeout=timeout)
        except Empty as exc:
            if self._failure_event.is_set():
                raise Record3DConnectionError(self._failure_message) from exc
            if self._stop_event.is_set():
                raise Record3DConnectionError("The Record3D Wi-Fi stream is not active.") from exc
            raise Record3DTimeoutError(f"Timed out waiting {timeout:.2f}s for a Record3D Wi-Fi frame.") from exc

    def _run_worker(self) -> None:
        try:
            asyncio.run(self._run_receiver())
        except Exception as exc:
            if not self._stop_event.is_set():
                self._register_failure(str(exc))
        finally:
            self._worker = None

    @staticmethod
    def _answer_request_payload(*, sdp: str) -> dict[str, str]:
        """Build the JSON answer payload expected by Record3D's signaling API."""
        return {"type": "answer", "data": sdp}

    def _request_async_stop(self) -> None:
        """Request shutdown of the async receiver loop."""
        if self._async_stop is not None:
            self._async_stop.set()

    @staticmethod
    def _should_suppress_async_exception(*, exception: BaseException | None, message: str, stop_requested: bool) -> bool:
        """Return whether an async exception is expected during aiortc teardown."""
        if not stop_requested:
            return False

        combined = message
        if exception is not None:
            combined = f"{combined} {type(exception).__name__}: {exception}"
        suppressed_fragments = (
            "RTCIceTransport is closed",
            "'NoneType' object has no attribute 'sendto'",
            "'NoneType' object has no attribute 'call_exception_handler'",
        )
        return any(fragment in combined for fragment in suppressed_fragments)

    def _handle_loop_exception(self, loop: asyncio.AbstractEventLoop, context: dict[str, Any]) -> None:
        """Handle event-loop exceptions for the dedicated Wi-Fi receiver loop."""
        exception = context.get("exception")
        message = str(context.get("message", ""))
        if self._should_suppress_async_exception(
            exception=exception if isinstance(exception, BaseException) else None,
            message=message,
            stop_requested=self._stop_event.is_set(),
        ):
            return
        loop.default_exception_handler(context)

    def _set_pre_track_failure(self, *, connection_state: str, video_track_ready: Any | None) -> None:
        """Fail the initial track wait without masking the underlying setup error."""
        if video_track_ready is None or video_track_ready.done():
            return
        video_track_ready.set_exception(
            Record3DConnectionError(
                "The Record3D Wi-Fi peer connection "
                f"entered `{connection_state}` before the video track became available."
            )
        )

    def _handle_connection_state_change(self, *, connection_state: str, video_track_ready: Any | None) -> None:
        """Handle aiortc connection-state transitions.

        During setup, `closed`/`failed` can occur while an earlier signaling error is still
        unwinding. In that case, fail the pending track wait instead of overwriting the
        more useful root-cause error with a generic peer-closed message.
        """
        if self._stop_event.is_set():
            return

        match connection_state:
            case "failed":
                if self._connected_event.is_set():
                    self._register_failure("The Record3D Wi-Fi peer connection failed.")
                else:
                    self._set_pre_track_failure(
                        connection_state=connection_state,
                        video_track_ready=video_track_ready,
                    )
                self._request_async_stop()
            case "closed" | "disconnected":
                if self._failure_event.is_set():
                    return
                if self._connected_event.is_set():
                    self._register_failure(f"The Record3D Wi-Fi peer connection entered `{connection_state}`.")
                else:
                    self._set_pre_track_failure(
                        connection_state=connection_state,
                        video_track_ready=video_track_ready,
                    )
                self._request_async_stop()
            case _:
                return

    async def _wait_for_ice_gathering_complete(self, *, peer_connection: Any) -> None:
        """Wait until aiortc finishes ICE gathering before sending the answer SDP."""
        if str(getattr(peer_connection, "iceGatheringState", "new")) == "complete":
            return

        ice_complete = asyncio.Event()

        @peer_connection.on("icegatheringstatechange")
        async def _on_ice_gathering_state_change() -> None:
            if str(getattr(peer_connection, "iceGatheringState", "new")) == "complete":
                ice_complete.set()

        await asyncio.wait_for(ice_complete.wait(), timeout=self.config.setup_timeout_seconds)

    async def _load_metadata_best_effort(self) -> None:
        """Load Record3D Wi-Fi metadata without blocking stream startup."""
        try:
            payload = await asyncio.to_thread(self.signaling_client.get_metadata)
            self._metadata = Record3DWiFiMetadata.from_api_payload(
                device_address=self.signaling_client.device_address,
                payload=payload,
            )
        except Exception as exc:
            if not self._stop_event.is_set():
                self.console.warning("Could not retrieve Record3D Wi-Fi metadata: %s", exc)

    async def _run_receiver(self) -> None:
        RTCPeerConnection, RTCSessionDescription = _import_aiortc_modules()
        self._loop = asyncio.get_running_loop()
        self._loop.set_exception_handler(self._handle_loop_exception)
        self._async_stop = asyncio.Event()
        peer_connection = RTCPeerConnection()
        self._peer_connection = peer_connection
        video_track_ready: asyncio.Future[Any] = self._loop.create_future()
        metadata_task = asyncio.create_task(self._load_metadata_best_effort())

        @peer_connection.on("track")
        def _on_track(track: Any) -> None:
            if getattr(track, "kind", None) != "video":
                return
            if not video_track_ready.done():
                video_track_ready.set_result(track)

        @peer_connection.on("connectionstatechange")
        async def _on_connection_state_change() -> None:
            connection_state = str(getattr(peer_connection, "connectionState", "unknown"))
            self._handle_connection_state_change(
                connection_state=connection_state,
                video_track_ready=video_track_ready,
            )

        try:
            offer_payload = await asyncio.to_thread(self.signaling_client.get_offer)
            await peer_connection.setRemoteDescription(
                RTCSessionDescription(sdp=str(offer_payload["sdp"]), type=str(offer_payload["type"]))
            )
            answer = await peer_connection.createAnswer()
            await peer_connection.setLocalDescription(answer)
            await self._wait_for_ice_gathering_complete(peer_connection=peer_connection)
            local_description = peer_connection.localDescription
            if local_description is None:
                raise Record3DConnectionError("Failed to produce a local WebRTC answer for the Record3D Wi-Fi stream.")

            await asyncio.to_thread(
                self.signaling_client.send_answer,
                self._answer_request_payload(sdp=local_description.sdp),
            )
            track = await asyncio.wait_for(video_track_ready, timeout=self.config.setup_timeout_seconds)
            self._connected_event.set()
            await self._consume_video_track(track)
        finally:
            if not metadata_task.done():
                metadata_task.cancel()
            with suppress(asyncio.CancelledError):
                await metadata_task
            await peer_connection.close()
            self._peer_connection = None
            self._loop = None
            self._async_stop = None

    async def _consume_video_track(self, track: Any) -> None:
        if self._metadata is None:
            raise Record3DError("Wi-Fi metadata must be loaded before consuming Record3D video frames.")

        while not self._stop_event.is_set():
            if self._async_stop is not None and self._async_stop.is_set():
                break
            try:
                video_frame = await asyncio.wait_for(track.recv(), timeout=self.config.frame_timeout_seconds)
            except TimeoutError:
                continue
            except Exception as exc:
                if self._stop_event.is_set():
                    break
                raise Record3DConnectionError("The Record3D Wi-Fi video track stopped unexpectedly.") from exc

            packet = self._packet_from_video_frame(video_frame, metadata=self._metadata)
            self._packet_queue.put(packet)

    def _register_failure(self, message: str) -> None:
        if self._failure_event.is_set():
            return
        self._failure_message = message
        self._failure_event.set()
        self.console.error(message)

    @staticmethod
    def _packet_from_video_frame(video_frame: Any, *, metadata: Record3DWiFiMetadata) -> Record3DFramePacket:
        composite_frame = np.asarray(video_frame.to_ndarray(format="rgb24"), dtype=np.uint8)
        if composite_frame.ndim != 3 or composite_frame.shape[2] != 3:
            raise Record3DError(
                "Record3D Wi-Fi video frames must be RGB images with shape `(height, width, 3)`."
            )
        if composite_frame.shape[1] < 2:
            raise Record3DError("Record3D Wi-Fi composite frames must contain both depth and RGB halves.")

        half_width = composite_frame.shape[1] // 2
        depth_rgb = composite_frame[:, :half_width, :]
        rgb = composite_frame[:, -half_width:, :]
        depth = decode_record3d_wifi_depth(depth_rgb, depth_max_meters=metadata.depth_max_meters)

        packet_metadata = dict(metadata.raw_metadata)
        packet_metadata["device_address"] = metadata.device_address
        if metadata.original_width is not None and metadata.original_height is not None:
            packet_metadata["original_size"] = [metadata.original_width, metadata.original_height]

        return Record3DFramePacket(
            transport=Record3DTransportId.WIFI,
            rgb=rgb,
            depth=depth,
            intrinsic_matrix=metadata.intrinsic_matrix,
            uncertainty=None,
            metadata=packet_metadata,
            arrival_timestamp_s=time.time(),
        )


def decode_record3d_wifi_depth(
    depth_rgb: NDArray[np.uint8],
    *,
    depth_max_meters: float,
) -> NDArray[np.float32]:
    """Decode the HSV-encoded Record3D Wi-Fi depth half into a depth map.

    Args:
        depth_rgb: Left half of the Record3D composite RGBD frame.
        depth_max_meters: Maximum depth represented by the hue channel.

    Returns:
        Depth image in meters.
    """
    normalized = depth_rgb.astype(np.float32) / 255.0
    red = normalized[..., 0]
    green = normalized[..., 1]
    blue = normalized[..., 2]

    maximum = np.max(normalized, axis=2)
    minimum = np.min(normalized, axis=2)
    delta = maximum - minimum

    hue = np.zeros_like(maximum, dtype=np.float32)
    has_delta = delta > 0.0

    red_max = has_delta & (maximum == red)
    green_max = has_delta & (maximum == green)
    blue_max = has_delta & (maximum == blue)

    hue[red_max] = np.mod((green[red_max] - blue[red_max]) / delta[red_max], 6.0) / 6.0
    hue[green_max] = (((blue[green_max] - red[green_max]) / delta[green_max]) + 2.0) / 6.0
    hue[blue_max] = (((red[blue_max] - green[blue_max]) / delta[blue_max]) + 4.0) / 6.0

    # Record3D maps invalid depth samples to red, which wraps hue back to zero.
    depth = np.where(hue <= 1e-6, depth_max_meters, depth_max_meters * hue)
    return depth.astype(np.float32)


__all__ = [
    "Record3DWiFiMetadata",
    "Record3DWiFiSignalingClient",
    "Record3DWiFiStreamConfig",
    "Record3DWiFiStreamSession",
    "decode_record3d_wifi_depth",
    "normalize_record3d_device_address",
]
