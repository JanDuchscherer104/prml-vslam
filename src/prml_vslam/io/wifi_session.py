"""Public Record3D Wi-Fi session wrapper."""

from __future__ import annotations

import time
from queue import Empty, Queue
from threading import Event, Thread, current_thread

from prml_vslam.utils import BaseConfig, Console

from .record3d import Record3DConnectionError, Record3DFramePacket, Record3DTimeoutError
from .wifi_packets import Record3DWiFiMetadata
from .wifi_receiver import _Record3DWiFiReceiverRuntime
from .wifi_signaling import Record3DWiFiSignalingClient


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
        self._runtime: _Record3DWiFiReceiverRuntime | None = None
        self._failure_message = ""
        self._metadata: Record3DWiFiMetadata | None = None

    def connect(self) -> Record3DWiFiMetadata:
        if self._worker is not None and self._worker.is_alive():
            raise Record3DConnectionError("The Record3D Wi-Fi session is already active.")

        self._packet_queue = Queue()
        self._connected_event.clear()
        self._failure_event.clear()
        self._stop_event.clear()
        self._failure_message = ""
        self._metadata = Record3DWiFiMetadata(device_address=self.signaling_client.device_address)
        self._runtime = _Record3DWiFiReceiverRuntime(
            config=self.config,
            console=self.console,
            device_address=self.signaling_client.device_address,
            get_offer=self.signaling_client.get_offer,
            get_metadata=self.signaling_client.get_metadata,
            send_answer=self.signaling_client.send_answer,
            on_metadata=self._store_metadata,
            on_connected=self._mark_connected,
            on_packet=self._packet_queue.put,
            on_failure=self._register_failure,
            stop_requested=self._stop_event.is_set,
        )
        self._worker = Thread(target=self._runtime.run, name="Record3DWiFiStreamSession", daemon=True)
        self._worker.start()

        deadline = time.monotonic() + self.config.setup_timeout_seconds
        while time.monotonic() < deadline:
            if self._connected_event.wait(timeout=0.05):
                self.console.info("Connected to Record3D Wi-Fi stream at %s.", self.signaling_client.device_address)
                return self._metadata or Record3DWiFiMetadata(device_address=self.signaling_client.device_address)
            if self._failure_event.is_set():
                raise Record3DConnectionError(self._failure_message)
            if self._worker is not None and not self._worker.is_alive():
                break

        self.disconnect()
        raise Record3DConnectionError(
            f"Timed out establishing the Record3D Wi-Fi stream at {self.signaling_client.device_address}."
        )

    def disconnect(self) -> None:
        self._stop_event.set()
        if self._runtime is not None:
            self._runtime.request_stop()

        worker = self._worker
        if worker is None or current_thread() is worker:
            return

        worker.join(timeout=max(5.0, self.config.setup_timeout_seconds + 1.0))
        if worker.is_alive():
            self.console.warning("Timed out stopping the Record3D Wi-Fi worker thread during cleanup.")
            return
        self._worker = None
        self._runtime = None

    def wait_for_packet(self, timeout_seconds: float | None = None) -> Record3DFramePacket:
        timeout = self.config.frame_timeout_seconds if timeout_seconds is None else timeout_seconds
        try:
            return self._packet_queue.get(timeout=timeout)
        except Empty as exc:
            if self._failure_event.is_set():
                raise Record3DConnectionError(self._failure_message) from exc
            if self._stop_event.is_set():
                raise Record3DConnectionError("The Record3D Wi-Fi stream is not active.") from exc
            raise Record3DTimeoutError(f"Timed out waiting {timeout:.2f}s for a Record3D Wi-Fi frame.") from exc

    def _store_metadata(self, metadata: Record3DWiFiMetadata) -> None:
        self._metadata = metadata

    def _mark_connected(self, metadata: Record3DWiFiMetadata) -> None:
        self._store_metadata(metadata)
        self._connected_event.set()

    def _register_failure(self, message: str) -> None:
        if self._failure_event.is_set():
            return
        self._failure_message = message
        self._failure_event.set()
        self.console.error(message)
