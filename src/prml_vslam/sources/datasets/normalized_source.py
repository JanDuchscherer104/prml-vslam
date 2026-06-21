from __future__ import annotations

from pathlib import Path

from prml_vslam.sources.contracts import PreparedBenchmarkInputs, SequenceManifest
from prml_vslam.sources.replay import ObservationStream, ReplayMode

from .contracts import FrameSelectionConfig
from .normalized_store import NormalizedDatasetProfile, NormalizedDatasetStore


class NormalizedDatasetRuntimeSource:
    """Runtime source backed only by an exact normalized datastore entry."""

    def __init__(
        self,
        *,
        label: str,
        store: NormalizedDatasetStore,
        profile: NormalizedDatasetProfile,
        frame_selection: FrameSelectionConfig,
        replay_mode: ReplayMode,
    ) -> None:
        self._label = label
        self._store = store
        self._profile = profile
        self._frame_selection = frame_selection
        self._replay_mode = replay_mode

    @property
    def label(self) -> str:
        return self._label

    def prepare_sequence_manifest(self, output_dir: Path) -> SequenceManifest:
        entry = self._store.load_entry_for_runtime(self._profile, frame_selection=self._frame_selection)
        return self._store.read_sequence_manifest(entry, frame_selection=self._frame_selection, output_dir=output_dir)

    def prepare_benchmark_inputs(self, output_dir: Path) -> PreparedBenchmarkInputs:
        entry = self._store.load_entry_for_runtime(self._profile, frame_selection=self._frame_selection)
        return self._store.read_benchmark_inputs(entry, frame_selection=self._frame_selection, output_dir=output_dir)

    def open_stream(self, *, loop: bool) -> ObservationStream:
        entry = self._store.load_entry_for_runtime(self._profile, frame_selection=self._frame_selection)
        return self._store.open_stream(
            entry,
            frame_selection=self._frame_selection,
            output_dir=self._store.preview_root / entry.sequence_id / entry.profile_key,
            loop=loop,
            replay_mode=self._replay_mode,
        )
