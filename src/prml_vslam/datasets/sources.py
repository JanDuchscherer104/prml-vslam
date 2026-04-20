from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from prml_vslam.benchmark import PreparedBenchmarkInputs
from prml_vslam.io import Cv2ReplayMode
from prml_vslam.protocols import FramePacketStream
from prml_vslam.protocols.source import BenchmarkInputSource, StreamingSequenceSource
from prml_vslam.utils import BaseData, Console, PathConfig

from .contracts import FrameSelectionConfig, SequenceKey

if TYPE_CHECKING:
    from prml_vslam.pipeline.contracts.sequence import SequenceManifest


class DatasetSequenceSource(BenchmarkInputSource, StreamingSequenceSource):
    def __init__(
        self,
        *,
        sequence_id: SequenceKey,
        frame_selection: FrameSelectionConfig,
        label: Callable[[SequenceKey], str],
        manifest: Callable[[SequenceKey, Path, FrameSelectionConfig], SequenceManifest],
        benchmark: Callable[[SequenceKey, Path], PreparedBenchmarkInputs],
        stream: Callable[[SequenceKey, bool, Cv2ReplayMode, FrameSelectionConfig], FramePacketStream] | None = None,
    ) -> None:
        self._sequence_id = sequence_id
        self._frame_selection = frame_selection
        self._label = label
        self._manifest = manifest
        self._benchmark = benchmark
        self._stream = stream

    @property
    def label(self) -> str:
        return self._label(self._sequence_id)

    def prepare_sequence_manifest(self, output_dir: Path) -> SequenceManifest:
        return self._manifest(self._sequence_id, output_dir, self._frame_selection)

    def prepare_benchmark_inputs(self, output_dir: Path) -> PreparedBenchmarkInputs:
        return self._benchmark(self._sequence_id, output_dir)

    def open_stream(self, *, loop: bool) -> FramePacketStream:
        if self._stream is None:
            raise RuntimeError("This dataset sequence source does not expose a replay stream.")
        return self._stream(self._sequence_id, loop, Cv2ReplayMode.REALTIME, self._frame_selection)


def open_dataset_sequence_stream(
    *,
    sequence: Any,
    timestamps_ns: list[int],
    frame_selection: FrameSelectionConfig,
    loop: bool,
    replay_mode: Cv2ReplayMode,
    **stream_kwargs: Any,
) -> FramePacketStream:
    """Open one dataset stream using the shared frame-selection policy."""
    stride = frame_selection.stride_for_timestamps_ns(timestamps_ns)
    return sequence.open_stream(stride=stride, loop=loop, replay_mode=replay_mode, **stream_kwargs)


class DatasetServiceBase:
    catalog_loader: Callable[[], Any]
    summary_model: type[BaseData]
    sequence_config_model: type[Any]
    sequence_model: type[Any]

    def __init__(self, path_config: PathConfig, *, catalog: Any | None = None) -> None:
        resolved_catalog = self.catalog_loader() if catalog is None else catalog
        super().__init__(
            path_config.resolve_dataset_dir(resolved_catalog.dataset_id),
            catalog=resolved_catalog,
            console=Console(self.__class__.__module__).child(self.__class__.__name__),
        )

    def summarize(self, statuses: list[Any] | None = None) -> BaseData:
        statuses = self.local_scene_statuses() if statuses is None else statuses
        return self.summary_model(
            total_scene_count=len(statuses),
            local_scene_count=sum(status.sequence_dir is not None for status in statuses),
            replay_ready_scene_count=sum(status.replay_ready for status in statuses),
            offline_ready_scene_count=sum(status.offline_ready for status in statuses),
            cached_archive_count=sum(status.archive_path is not None for status in statuses),
            total_remote_archive_bytes=sum(scene.archive_size_bytes for scene in self.catalog.scenes),
        )

    def list_local_sequence_ids(self) -> list[SequenceKey]:
        return [status.scene.sequence_id for status in self.local_scene_statuses() if status.offline_ready]

    def load_local_sample(self, sequence_id: SequenceKey) -> object:
        return self._sequence(sequence_id).load_offline_sample()

    def build_sequence_manifest(
        self,
        *,
        sequence_id: SequenceKey,
        output_dir: Path | None = None,
        frame_selection: FrameSelectionConfig | None = None,
    ) -> SequenceManifest:
        return self._sequence(sequence_id).to_sequence_manifest(
            output_dir=output_dir,
            frame_selection=frame_selection or FrameSelectionConfig(),
        )

    def build_benchmark_inputs(
        self, *, sequence_id: SequenceKey, output_dir: Path | None = None
    ) -> PreparedBenchmarkInputs:
        return self._sequence(sequence_id).to_benchmark_inputs(output_dir=output_dir)

    def resolve_sequence_id(self, sequence_slug: str) -> SequenceKey:
        return self.scene(sequence_slug).sequence_id

    def build_offline_source(
        self, *, sequence_id: SequenceKey, frame_selection: FrameSelectionConfig | None = None
    ) -> DatasetSequenceSource:
        return self._build_source(sequence_id=sequence_id, frame_selection=frame_selection)

    def build_streaming_source(
        self,
        *,
        sequence_id: SequenceKey,
        frame_selection: FrameSelectionConfig | None = None,
        **stream_kwargs: Any,
    ) -> DatasetSequenceSource:
        return self._build_streaming_source(
            sequence_id=sequence_id,
            frame_selection=frame_selection,
            **stream_kwargs,
        )

    def open_preview_stream(
        self,
        *,
        sequence_id: SequenceKey,
        frame_selection: FrameSelectionConfig | None = None,
        loop: bool = True,
        replay_mode: Cv2ReplayMode = Cv2ReplayMode.REALTIME,
        **stream_kwargs: Any,
    ) -> FramePacketStream:
        return self._open_preview_stream(
            sequence_id=sequence_id,
            frame_selection=frame_selection,
            loop=loop,
            replay_mode=replay_mode,
            **stream_kwargs,
        )

    def _build_source(
        self,
        *,
        sequence_id: SequenceKey,
        frame_selection: FrameSelectionConfig | None = None,
        stream: Callable[[SequenceKey, bool, Cv2ReplayMode, FrameSelectionConfig], FramePacketStream] | None = None,
    ) -> DatasetSequenceSource:
        return DatasetSequenceSource(
            sequence_id=sequence_id,
            frame_selection=frame_selection or FrameSelectionConfig(),
            label=lambda value: self.scene(value).display_name,
            manifest=lambda value, output_dir, selection: self.build_sequence_manifest(
                sequence_id=value,
                output_dir=output_dir,
                frame_selection=selection,
            ),
            benchmark=lambda value, output_dir: self.build_benchmark_inputs(sequence_id=value, output_dir=output_dir),
            stream=stream,
        )

    def _build_streaming_source(
        self,
        *,
        sequence_id: SequenceKey,
        frame_selection: FrameSelectionConfig | None = None,
        **stream_kwargs: Any,
    ) -> DatasetSequenceSource:
        return self._build_source(
            sequence_id=sequence_id,
            frame_selection=frame_selection,
            stream=lambda value, loop, replay_mode, selection: self.open_preview_stream(
                sequence_id=value,
                frame_selection=selection,
                loop=loop,
                replay_mode=replay_mode,
                **stream_kwargs,
            ),
        )

    def _open_preview_stream(
        self,
        *,
        sequence_id: SequenceKey,
        frame_selection: FrameSelectionConfig | None,
        loop: bool,
        replay_mode: Cv2ReplayMode,
        **stream_kwargs: Any,
    ) -> FramePacketStream:
        sequence = self._sequence(sequence_id)
        return open_dataset_sequence_stream(
            sequence=sequence,
            timestamps_ns=self._preview_timestamps_ns(sequence),
            frame_selection=frame_selection or FrameSelectionConfig(),
            loop=loop,
            replay_mode=replay_mode,
            **stream_kwargs,
        )

    def _preview_timestamps_ns(self, sequence: Any) -> list[int]:
        raise NotImplementedError

    def _sequence(self, sequence_id: SequenceKey) -> Any:
        return self.sequence_model(
            config=self.sequence_config_model(dataset_root=self.dataset_root, sequence_id=sequence_id),
            catalog=self.catalog,
        )
