from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from prml_vslam.sources.contracts import PreparedBenchmarkInputs
from prml_vslam.sources.protocols import BenchmarkInputSource, OfflineSequenceSource
from prml_vslam.utils import Console, PathConfig

from .contracts import DatasetSummary, FrameSelectionConfig, SequenceKey
from .fetch import DatasetFetchHelper

if TYPE_CHECKING:
    from prml_vslam.sources.contracts import SequenceManifest


class DatasetSequenceSource(BenchmarkInputSource, OfflineSequenceSource):
    def __init__(
        self,
        *,
        sequence_id: SequenceKey,
        frame_selection: FrameSelectionConfig,
        label: Callable[[SequenceKey], str],
        manifest: Callable[[SequenceKey, Path, FrameSelectionConfig], SequenceManifest],
        benchmark: Callable[[SequenceKey, Path, FrameSelectionConfig], PreparedBenchmarkInputs],
    ) -> None:
        self._sequence_id = sequence_id
        self._frame_selection = frame_selection
        self._label = label
        self._manifest = manifest
        self._benchmark = benchmark

    @property
    def label(self) -> str:
        return self._label(self._sequence_id)

    def prepare_sequence_manifest(self, output_dir: Path) -> SequenceManifest:
        return self._manifest(self._sequence_id, output_dir, self._frame_selection)

    def prepare_benchmark_inputs(self, output_dir: Path) -> PreparedBenchmarkInputs:
        return self._benchmark(self._sequence_id, output_dir, self._frame_selection)


class DatasetServiceBase:
    catalog_loader: Callable[[], Any]
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
        statuses = self.local_scene_statuses() if statuses is None else statuses
        return DatasetSummary(
            total_scene_count=len(statuses),
            local_scene_count=sum(status.sequence_dir is not None for status in statuses),
            replay_ready_scene_count=sum(status.replay_ready for status in statuses),
            offline_ready_scene_count=sum(status.offline_ready for status in statuses),
            cached_archive_count=sum(status.archive_path is not None for status in statuses),
            total_remote_archive_bytes=sum(scene.archive_size_bytes for scene in self.catalog.scenes),
        )

    def list_local_sequence_ids(self) -> list[SequenceKey]:
        return [status.scene.sequence_id for status in self.local_scene_statuses() if status.offline_ready]

    def load_local_sample(self, sequence_id: SequenceKey) -> Any:
        return self._sequence(sequence_id).load_offline_sample()

    def build_sequence_manifest(
        self,
        *,
        sequence_id: SequenceKey,
        output_dir: Path | None = None,
        frame_selection: FrameSelectionConfig | None = None,
        **sequence_kwargs: Any,
    ) -> SequenceManifest:
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
        return self._sequence(sequence_id, **sequence_kwargs).to_benchmark_inputs(
            output_dir=output_dir,
            frame_selection=frame_selection or FrameSelectionConfig(),
        )

    def resolve_sequence_id(self, sequence_slug: str) -> SequenceKey:
        return self.scene(sequence_slug).sequence_id

    def _build_raw_source(
        self, *, sequence_id: SequenceKey, frame_selection: FrameSelectionConfig | None = None
    ) -> DatasetSequenceSource:
        return self._build_source(sequence_id=sequence_id, frame_selection=frame_selection)

    def _build_source(
        self,
        *,
        sequence_id: SequenceKey,
        frame_selection: FrameSelectionConfig | None = None,
        sequence_kwargs: dict[str, Any] | None = None,
    ) -> DatasetSequenceSource:
        sequence_kwargs = {} if sequence_kwargs is None else sequence_kwargs
        return DatasetSequenceSource(
            sequence_id=sequence_id,
            frame_selection=frame_selection or FrameSelectionConfig(),
            label=lambda value: self.scene(value).display_name,
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
        )

    def _sequence(self, sequence_id: SequenceKey, **config_kwargs: Any) -> Any:
        raise NotImplementedError
