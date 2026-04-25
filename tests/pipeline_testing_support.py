"""Small runtime sources used by focused pipeline smoke tests."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from prml_vslam.interfaces import CAMERA_RDF_FRAME, FrameTransform, Observation, ObservationProvenance
from prml_vslam.sources.contracts import SequenceManifest


class FakeOfflineSource:
    """Minimal offline source for pipeline smoke tests."""

    label = "fake-offline"

    def prepare_sequence_manifest(self, output_dir: Path) -> SequenceManifest:
        del output_dir
        return SequenceManifest(sequence_id="fake-offline")


class FakePacketStream:
    """Finite in-memory packet stream for streaming smoke tests."""

    def __init__(self) -> None:
        self._index = 0

    def connect(self) -> None:
        return None

    def disconnect(self) -> None:
        return None

    def wait_for_observation(self, timeout_seconds: float | None = None) -> Observation:
        del timeout_seconds
        if self._index >= 3:
            raise EOFError("done")
        index = self._index
        self._index += 1
        return Observation(
            seq=index,
            timestamp_ns=index * 1_000_000,
            rgb=np.full((8, 8, 3), fill_value=index * 25, dtype=np.uint8),
            T_world_camera=FrameTransform(
                qx=0.0,
                qy=0.0,
                qz=0.0,
                qw=1.0,
                tx=float(index),
                ty=0.0,
                tz=0.0,
                source_frame=CAMERA_RDF_FRAME,
            ),
            provenance=ObservationProvenance(source_id="fake-stream"),
        )


class FakeStreamingSource:
    """Minimal streaming-capable source for pipeline smoke tests."""

    label = "fake-stream"

    def prepare_sequence_manifest(self, output_dir: Path) -> SequenceManifest:
        del output_dir
        return SequenceManifest(sequence_id="fake-stream")

    def open_stream(self, *, loop: bool):
        del loop
        return FakePacketStream()


__all__ = ["FakeOfflineSource", "FakePacketStream", "FakeStreamingSource"]
