"""Source-owned wrappers for stream sampling policy."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from prml_vslam.interfaces import Observation
from prml_vslam.sources.contracts import PreparedBenchmarkInputs, SequenceManifest
from prml_vslam.sources.datasets.contracts import FrameSelectionConfig
from prml_vslam.sources.protocols import BenchmarkInputSource, StreamingSequenceSource
from prml_vslam.sources.replay import ObservationStream


class SampledObservationStream:
    """Apply source sampling policy to an existing observation stream."""

    def __init__(self, stream: ObservationStream, *, frame_selection: FrameSelectionConfig) -> None:
        self._stream = stream
        self._frame_selection = frame_selection
        self._seen_observations = 0
        self._last_emitted_timestamp_ns: int | None = None

    def connect(self) -> Any:
        """Connect the wrapped stream."""
        return self._stream.connect()

    def disconnect(self) -> None:
        """Disconnect the wrapped stream."""
        self._stream.disconnect()

    def wait_for_observation(self, timeout_seconds: float | None = None) -> Observation:
        """Return the next observation accepted by the configured sampling policy."""
        while True:
            observation = self._stream.wait_for_observation(timeout_seconds=timeout_seconds)
            self._seen_observations += 1
            if not self._should_emit(observation):
                continue
            self._last_emitted_timestamp_ns = observation.timestamp_ns
            return observation

    def _should_emit(self, observation: Observation) -> bool:
        if self._frame_selection.target_fps is not None:
            if self._last_emitted_timestamp_ns is None:
                return True
            min_delta_ns = int(round(1e9 / self._frame_selection.target_fps))
            return observation.timestamp_ns - self._last_emitted_timestamp_ns >= min_delta_ns
        return (self._seen_observations - 1) % self._frame_selection.frame_stride == 0


class SampledStreamingSource(StreamingSequenceSource):
    """Apply source sampling policy to an existing streaming source."""

    def __init__(self, source: StreamingSequenceSource, *, frame_selection: FrameSelectionConfig) -> None:
        self._source = source
        self._frame_selection = frame_selection
        self.label = source.label

    def prepare_sequence_manifest(self, output_dir: Path) -> SequenceManifest:
        """Delegate manifest preparation to the wrapped source."""
        return self._source.prepare_sequence_manifest(output_dir)

    def prepare_benchmark_inputs(self, output_dir: Path) -> PreparedBenchmarkInputs | None:
        """Delegate benchmark preparation when the wrapped source supports it."""
        if not isinstance(self._source, BenchmarkInputSource):
            return None
        return self._source.prepare_benchmark_inputs(output_dir)

    def open_stream(self, *, loop: bool) -> ObservationStream:
        """Open the wrapped source stream with sampling applied."""
        return SampledObservationStream(
            self._source.open_stream(loop=loop),
            frame_selection=self._frame_selection,
        )
