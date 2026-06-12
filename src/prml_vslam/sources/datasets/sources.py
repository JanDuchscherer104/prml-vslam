"""Shared dataset-source adapters that bridge datasets into pipeline seams.

This module owns the dataset-side implementation of the shared source protocols.
It lets concrete dataset services build normalized offline or streaming sources
without duplicating the common glue between dataset-owned sequence objects and
pipeline-owned source contracts.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from prml_vslam.sources.contracts import PreparedBenchmarkInputs
from prml_vslam.sources.protocols import BenchmarkInputSource, StreamingSequenceSource
from prml_vslam.sources.replay import ObservationStream, ReplayMode
from prml_vslam.utils import Console, PathConfig

from .contracts import DatasetSummary, FrameSelectionConfig, SequenceKey
from .fetch import DatasetFetchHelper
from .normalized_store import NormalizedDatasetProfile, NormalizedDatasetStore

if TYPE_CHECKING:
    from prml_vslam.sources.contracts import SequenceManifest


class DatasetSequenceSource(BenchmarkInputSource, StreamingSequenceSource):
    """Adapt one dataset sequence into the shared offline/streaming source seams."""

    def __init__(
        self,
        *,
        sequence_id: SequenceKey,
        frame_selection: FrameSelectionConfig,
        label: Callable[[SequenceKey], str],
        manifest: Callable[[SequenceKey, Path, FrameSelectionConfig], SequenceManifest],
        benchmark: Callable[[SequenceKey, Path, FrameSelectionConfig], PreparedBenchmarkInputs],
        stream: Callable[[SequenceKey, bool, ReplayMode, FrameSelectionConfig], ObservationStream] | None = None,
        replay_mode: ReplayMode = ReplayMode.REALTIME,
        normalized_store: NormalizedDatasetStore | None = None,
        normalized_profile: NormalizedDatasetProfile | None = None,
    ) -> None:
        self._sequence_id = sequence_id
        self._frame_selection = frame_selection
        self._label = label
        self._manifest = manifest
        self._benchmark = benchmark
        self._stream = stream
        self._replay_mode = replay_mode
        self._normalized_store = normalized_store
        self._normalized_profile = normalized_profile

    @property
    def label(self) -> str:
        """Return the user-facing label for the selected dataset sequence."""
        return self._label(self._sequence_id)

    def prepare_sequence_manifest(self, output_dir: Path) -> SequenceManifest:
        """Materialize the normalized manifest for the selected dataset sequence."""
        if self._normalized_store is not None and self._normalized_profile is not None:
            entry = self._normalized_store.load_entry(self._normalized_profile)
            return self._normalized_store.read_sequence_manifest(
                entry,
                frame_selection=self._frame_selection,
                output_dir=output_dir,
            )
        return self._manifest(self._sequence_id, output_dir, self._frame_selection)

    def prepare_benchmark_inputs(self, output_dir: Path) -> PreparedBenchmarkInputs:
        """Materialize prepared benchmark inputs for the selected dataset sequence."""
        if self._normalized_store is not None and self._normalized_profile is not None:
            entry = self._normalized_store.load_entry(self._normalized_profile)
            return self._normalized_store.read_benchmark_inputs(
                entry,
                frame_selection=self._frame_selection,
                output_dir=output_dir,
            )
        return self._benchmark(self._sequence_id, output_dir, self._frame_selection)

    def open_stream(self, *, loop: bool) -> ObservationStream:
        """Open the replay stream for the selected dataset sequence."""
        if self._normalized_store is not None and self._normalized_profile is not None:
            entry = self._normalized_store.load_entry(self._normalized_profile)
            return self._normalized_store.open_stream(
                entry,
                frame_selection=self._frame_selection,
                output_dir=self._normalized_store.dataset_root / ".preview" / entry.sequence_id / entry.profile_key,
                loop=loop,
                replay_mode=self._replay_mode,
            )
        if self._stream is None:
            raise RuntimeError("This dataset sequence source does not expose a replay stream.")
        return self._stream(self._sequence_id, loop, self._replay_mode, self._frame_selection)


def open_dataset_sequence_stream(
    *,
    sequence: Any,
    timestamps_ns: list[int],
    frame_selection: FrameSelectionConfig,
    loop: bool,
    replay_mode: ReplayMode,
    **stream_kwargs: Any,
) -> ObservationStream:
    """Open one dataset stream using the shared frame-selection policy."""
    stride = frame_selection.stride_for_timestamps_ns(timestamps_ns)
    return sequence.open_stream(stride=stride, loop=loop, replay_mode=replay_mode, **stream_kwargs)


class DatasetServiceBase:
    """Provide shared dataset-service behavior for app and pipeline entry points.

    Concrete dataset services own catalog details, local layout, and
    dataset-specific replay logic. This base class centralizes the shared logic
    that turns those sequence owners into normalized source adapters and summary
    surfaces.
    """

    catalog_loader: Callable[[], Any]
    summary_model: type[DatasetSummary]
    sequence_config_model: type[Any]
    sequence_model: type[Any]
    dataset_root: Path
    catalog: Any
    console: Console
    _fetch_helper: DatasetFetchHelper

    def __init__(self, path_config: PathConfig, *, catalog: Any | None = None) -> None:
        resolved_catalog = self.catalog_loader() if catalog is None else catalog
        self.dataset_root = path_config.resolve_dataset_dir(resolved_catalog.dataset_id)
        self.catalog = resolved_catalog
        self.console = Console(self.__class__.__module__).child(self.__class__.__name__)
        self._fetch_helper = DatasetFetchHelper()

    def summarize(self, statuses: list[Any] | None = None) -> DatasetSummary:
        """Return the high-level local-coverage summary for the dataset."""
        statuses = self.local_scene_statuses() if statuses is None else statuses  # type: ignore[attr-defined]
        return self.summary_model(
            total_scene_count=len(statuses),
            local_scene_count=sum(status.sequence_dir is not None for status in statuses),
            replay_ready_scene_count=sum(status.replay_ready for status in statuses),
            offline_ready_scene_count=sum(status.offline_ready for status in statuses),
            cached_archive_count=sum(status.archive_path is not None for status in statuses),
            total_remote_archive_bytes=sum(scene.archive_size_bytes for scene in self.catalog.scenes),
        )

    def list_local_sequence_ids(self) -> list[SequenceKey]:
        """Return the offline-ready local sequence ids for the dataset."""
        return [status.scene.sequence_id for status in self.local_scene_statuses() if status.offline_ready]  # type: ignore[attr-defined]

    def load_local_sample(self, sequence_id: SequenceKey) -> Any:
        """Load one dataset-owned offline sample for inspection or tests."""
        return self._sequence(sequence_id).load_offline_sample()

    def build_sequence_manifest(
        self,
        *,
        sequence_id: SequenceKey,
        output_dir: Path | None = None,
        frame_selection: FrameSelectionConfig | None = None,
        **sequence_kwargs: Any,
    ) -> SequenceManifest:
        """Build the normalized offline manifest for one dataset sequence."""
        return self._sequence(sequence_id, **sequence_kwargs).to_sequence_manifest(
            output_dir=output_dir,
            frame_selection=frame_selection or FrameSelectionConfig(),
        )

    def build_benchmark_inputs(
        self,
        *,
        sequence_id: SequenceKey,
        output_dir: Path | None = None,
        frame_selection: FrameSelectionConfig | None = None,
        **sequence_kwargs: Any,
    ) -> PreparedBenchmarkInputs:
        """Build prepared benchmark inputs for one dataset sequence."""
        return self._sequence(sequence_id, **sequence_kwargs).to_benchmark_inputs(
            output_dir=output_dir,
            frame_selection=frame_selection or FrameSelectionConfig(),
        )

    def resolve_sequence_id(self, sequence_slug: str) -> SequenceKey:
        """Resolve a UI- or CLI-facing slug into the dataset's canonical sequence id."""
        return self.scene(sequence_slug).sequence_id  # type: ignore[attr-defined]

    def build_offline_source(
        self, *, sequence_id: SequenceKey, frame_selection: FrameSelectionConfig | None = None
    ) -> DatasetSequenceSource:
        """Build the dataset-backed offline source adapter for one sequence."""
        return self._build_source(sequence_id=sequence_id, frame_selection=frame_selection)

    def build_streaming_source(
        self,
        *,
        sequence_id: SequenceKey,
        frame_selection: FrameSelectionConfig | None = None,
        **stream_kwargs: Any,
    ) -> DatasetSequenceSource:
        """Build the dataset-backed streaming source adapter for one sequence."""
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
        replay_mode: ReplayMode = ReplayMode.REALTIME,
        **stream_kwargs: Any,
    ) -> ObservationStream:
        """Open a preview replay stream for one local dataset sequence."""
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
        sequence_kwargs: dict[str, Any] | None = None,
        stream: Callable[[SequenceKey, bool, ReplayMode, FrameSelectionConfig], ObservationStream] | None = None,
        replay_mode: ReplayMode = ReplayMode.REALTIME,
        normalized_store: NormalizedDatasetStore | None = None,
        normalized_profile: NormalizedDatasetProfile | None = None,
    ) -> DatasetSequenceSource:
        sequence_kwargs = {} if sequence_kwargs is None else sequence_kwargs
        return DatasetSequenceSource(
            sequence_id=sequence_id,
            frame_selection=frame_selection or FrameSelectionConfig(),
            label=lambda value: self.scene(value).display_name,  # type: ignore[attr-defined]
            manifest=lambda value, output_dir, selection: self.build_sequence_manifest(
                sequence_id=value,
                output_dir=output_dir,
                frame_selection=selection,
                **sequence_kwargs,
            ),
            benchmark=lambda value, output_dir, selection: self.build_benchmark_inputs(
                sequence_id=value,
                output_dir=output_dir,
                frame_selection=selection,
                **sequence_kwargs,
            ),
            stream=stream,
            replay_mode=replay_mode,
            normalized_store=normalized_store,
            normalized_profile=normalized_profile,
        )

    def _build_streaming_source(
        self,
        *,
        sequence_id: SequenceKey,
        frame_selection: FrameSelectionConfig | None = None,
        replay_mode: ReplayMode = ReplayMode.REALTIME,
        sequence_kwargs: dict[str, Any] | None = None,
        normalized_store: NormalizedDatasetStore | None = None,
        normalized_profile: NormalizedDatasetProfile | None = None,
        **stream_kwargs: Any,
    ) -> DatasetSequenceSource:
        sequence_kwargs = {} if sequence_kwargs is None else sequence_kwargs
        return self._build_source(
            sequence_id=sequence_id,
            frame_selection=frame_selection,
            sequence_kwargs=sequence_kwargs,
            replay_mode=replay_mode,
            normalized_store=normalized_store,
            normalized_profile=normalized_profile,
            stream=lambda value, loop, replay_mode, selection: self._open_sequence_stream(
                sequence=self._sequence(value, **sequence_kwargs),
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
        replay_mode: ReplayMode,
        **stream_kwargs: Any,
    ) -> ObservationStream:
        sequence = self._sequence(sequence_id)
        return self._open_sequence_stream(
            sequence=sequence,
            frame_selection=frame_selection or FrameSelectionConfig(),
            loop=loop,
            replay_mode=replay_mode,
            **stream_kwargs,
        )

    def _open_sequence_stream(
        self,
        *,
        sequence: Any,
        frame_selection: FrameSelectionConfig,
        loop: bool,
        replay_mode: ReplayMode,
        **stream_kwargs: Any,
    ) -> ObservationStream:
        return open_dataset_sequence_stream(
            sequence=sequence,
            timestamps_ns=self._preview_timestamps_ns(sequence),
            frame_selection=frame_selection,
            loop=loop,
            replay_mode=replay_mode,
            **stream_kwargs,
        )

    def _preview_timestamps_ns(self, sequence: Any) -> list[int]:
        raise NotImplementedError

    def _sequence(self, sequence_id: SequenceKey, **config_kwargs: Any) -> Any:
        return self.sequence_model(
            config=self.sequence_config_model(dataset_root=self.dataset_root, sequence_id=sequence_id, **config_kwargs),
            catalog=self.catalog,
        )
