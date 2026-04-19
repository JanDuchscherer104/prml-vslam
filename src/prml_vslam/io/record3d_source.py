"""Record3D-backed streaming-source wrapper for pipeline-owned sessions."""

from __future__ import annotations

import re
from pathlib import Path

from prml_vslam.pipeline.contracts.sequence import SequenceManifest
from prml_vslam.protocols.source import StreamingSequenceSource
from prml_vslam.utils import BaseConfig, FactoryConfig

from .record3d import Record3DTransportId, open_record3d_usb_packet_stream


class Record3DStreamingSourceConfig(BaseConfig, FactoryConfig["Record3DStreamingSource"]):
    """Configuration for one Record3D-backed streaming source."""

    transport: Record3DTransportId = Record3DTransportId.USB
    """Selected Record3D transport."""

    device_index: int = 0
    """Zero-based USB device index used when `transport` is `USB`."""

    device_address: str = ""
    """Wi-Fi preview address used when `transport` is `WIFI`."""

    frame_timeout_seconds: float = 5.0
    """Maximum time to wait for the next frame before failing."""

    @property
    def target_type(self) -> type[Record3DStreamingSource]:
        """Runtime type that exposes the shared streaming-source contract."""
        return Record3DStreamingSource


class Record3DStreamingSource(StreamingSequenceSource):
    """Record3D-backed live source compatible with pipeline-owned sessions."""

    def __init__(self, config: Record3DStreamingSourceConfig) -> None:
        self.config = config

    @property
    def label(self) -> str:
        """Return the user-facing source label."""
        match self.config.transport:
            case Record3DTransportId.USB:
                return f"Record3D USB device #{self.config.device_index}"
            case Record3DTransportId.WIFI:
                return (
                    f"Record3D Wi-Fi Preview ({self.config.device_address})"
                    if self.config.device_address
                    else "Record3D Wi-Fi Preview"
                )
            case _:
                raise ValueError(f"Unsupported Record3D transport: {self.config.transport}")

    def prepare_sequence_manifest(self, output_dir: Path) -> SequenceManifest:
        """Return the normalized live-sequence boundary for one Record3D source."""
        del output_dir
        return SequenceManifest(sequence_id=self._sequence_id())

    def open_stream(self, *, loop: bool):
        """Open the configured Record3D packet stream for pipeline consumption."""
        del loop
        match self.config.transport:
            case Record3DTransportId.USB:
                return open_record3d_usb_packet_stream(
                    device_index=self.config.device_index,
                    frame_timeout_seconds=self.config.frame_timeout_seconds,
                )
            case Record3DTransportId.WIFI:
                from .wifi_session import Record3DWiFiPreviewStreamConfig

                return Record3DWiFiPreviewStreamConfig(
                    device_address=self.config.device_address,
                    frame_timeout_seconds=max(1.0, self.config.frame_timeout_seconds),
                    signaling_timeout_seconds=10.0,
                    setup_timeout_seconds=12.0,
                ).setup_target()
            case _:
                raise ValueError(f"Unsupported Record3D transport: {self.config.transport}")

    def _sequence_id(self) -> str:
        match self.config.transport:
            case Record3DTransportId.USB:
                return f"record3d-usb-{self.config.device_index}"
            case Record3DTransportId.WIFI:
                address = self.config.device_address.strip().lower()
                address_slug = re.sub(r"[^a-z0-9]+", "-", address).strip("-") or "preview"
                return f"record3d-wifi-{address_slug}"
            case _:
                raise ValueError(f"Unsupported Record3D transport: {self.config.transport}")


__all__ = [
    "Record3DStreamingSource",
    "Record3DStreamingSourceConfig",
]
