"""Service layer for local Record3D `.r3d` archives."""

from __future__ import annotations

from prml_vslam.sources.datasets.normalized_store import NormalizedDatasetProfile, NormalizedDatasetStore
from prml_vslam.sources.datasets.sources import DatasetSequenceSource, DatasetServiceBase
from prml_vslam.sources.replay import ReplayMode
from prml_vslam.utils import Console, PathConfig

from ..contracts import DatasetSummary, FrameSelectionConfig, LocalSceneStatus, ReferenceCloudConfig, SequenceKey
from . import record3d_layout
from .record3d_download import Record3DDownloadManager
from .record3d_models import (
    Record3DCatalog,
    Record3DMaterializationConfig,
    Record3DSceneMetadata,
    Record3DSequenceConfig,
)
from .record3d_sequence import Record3DSequence


class Record3DDatasetService(DatasetServiceBase, Record3DDownloadManager):
    """Provide app and pipeline service helpers for local Record3D archives."""

    catalog_loader = staticmethod(record3d_layout.load_record3d_catalog)
    summary_model = DatasetSummary
    sequence_config_model = Record3DSequenceConfig
    sequence_model = Record3DSequence

    def __init__(self, path_config: PathConfig, *, catalog: Record3DCatalog | None = None) -> None:
        resolved_catalog = self.catalog_loader() if catalog is None else catalog
        self.dataset_root = path_config.resolve_dataset_dir("record3d")
        self.catalog = resolved_catalog
        self.console = Console(self.__class__.__module__).child(self.__class__.__name__)
        Record3DDownloadManager.__init__(
            self,
            self.dataset_root,
            catalog=resolved_catalog,
            console=self.console,
        )

    def scene(self, sequence_slug: SequenceKey) -> Record3DSceneMetadata:
        return record3d_layout.scene_for_sequence_id(self.catalog, self.dataset_root, str(sequence_slug))

    def local_scene_statuses(self) -> list[LocalSceneStatus[Record3DSceneMetadata]]:
        statuses: list[LocalSceneStatus[Record3DSceneMetadata]] = []
        seen_sequence_ids: set[str] = set()
        for scene in self.catalog.scenes:
            archive_path = record3d_layout.archive_path_for_sequence(self.dataset_root, scene.sequence_id)
            archive_exists = archive_path.exists()
            seen_sequence_ids.add(scene.sequence_id)
            statuses.append(
                LocalSceneStatus[Record3DSceneMetadata](
                    scene=scene,
                    sequence_dir=archive_path.parent if archive_exists else None,
                    archive_path=archive_path if archive_exists else None,
                    replay_ready=archive_exists,
                    offline_ready=archive_exists,
                )
            )
        for sequence_id in record3d_layout.list_local_sequence_ids(self.dataset_root):
            if sequence_id in seen_sequence_ids:
                continue
            scene = record3d_layout.scene_for_sequence_id(self.catalog, self.dataset_root, sequence_id)
            archive_path = record3d_layout.archive_path_for_sequence(self.dataset_root, sequence_id)
            statuses.append(
                LocalSceneStatus[Record3DSceneMetadata](
                    scene=scene,
                    sequence_dir=archive_path.parent,
                    archive_path=archive_path,
                    replay_ready=archive_path.exists(),
                    offline_ready=archive_path.exists(),
                )
            )
        return statuses

    def build_streaming_source(
        self,
        *,
        sequence_id: SequenceKey,
        frame_selection: FrameSelectionConfig | None = None,
        replay_mode: ReplayMode = ReplayMode.REALTIME,
        materialization: Record3DMaterializationConfig | None = None,
        reference_cloud: ReferenceCloudConfig | None = None,
        normalized_store: NormalizedDatasetStore | None = None,
        normalized_profile: NormalizedDatasetProfile | None = None,
    ) -> DatasetSequenceSource:
        return self._build_streaming_source(
            sequence_id=sequence_id,
            frame_selection=frame_selection or FrameSelectionConfig(),
            replay_mode=replay_mode,
            sequence_kwargs={
                "materialization": materialization or Record3DMaterializationConfig(),
                "reference_cloud": reference_cloud or ReferenceCloudConfig(min_confidence=1),
            },
            normalized_store=normalized_store,
            normalized_profile=normalized_profile,
        )

    def _preview_timestamps_ns(self, sequence: Record3DSequence) -> list[int]:
        return sequence.load_offline_sample().timestamps_ns
