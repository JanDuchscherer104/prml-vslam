from __future__ import annotations

import json
import zipfile
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import pytest
from pydantic import ValidationError

import prml_vslam.sources.datasets.batch_normalization as batch_normalization
import prml_vslam.sources.datasets.normalized_store as normalized_store_module
from prml_vslam.interfaces import (
    ObservationIndexEntry,
    ObservationProvenance,
    ObservationSequenceIndex,
    ObservationSequenceRef,
)
from prml_vslam.methods.stage.backend_config import MethodId
from prml_vslam.pipeline.config import build_run_config
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.sources import FileObservationSequenceLoader
from prml_vslam.sources.config import Record3DDatasetSourceConfig, normalized_profile_for_source_config
from prml_vslam.sources.contracts import (
    PreparedBenchmarkInputs,
    ReferenceCloudSource,
    ReferenceSource,
    SequenceManifest,
)
from prml_vslam.sources.dataset_query import NormalizedDatasetQuery
from prml_vslam.sources.datasets.batch_normalization import (
    NormalizedDatasetBatchConfig,
    NormalizedDatasetMissingPolicy,
    NormalizedDatasetSelection,
    normalize_dataset_batch,
)
from prml_vslam.sources.datasets.contracts import DatasetId, FrameSelectionConfig, ReferenceCloudConfig
from prml_vslam.sources.datasets.normalized_store import (
    NormalizedDatasetEntry,
    NormalizedDatasetProfile,
    NormalizedDatasetStore,
)
from prml_vslam.sources.datasets.normalized_tables import load_depth_array
from prml_vslam.sources.datasets.record3d import (
    Record3DCatalog,
    Record3DDatasetService,
    Record3DDownloadRequest,
    Record3DSceneMetadata,
    Record3DSequence,
    Record3DSequenceConfig,
    record3d_loading,
)
from prml_vslam.sources.datasets.record3d.record3d_download import _redact_url_for_log
from prml_vslam.sources.datasets.record3d.record3d_layout import load_record3d_catalog
from prml_vslam.sources.datasets.registry import list_sequence_slugs, resolve_reference_path
from prml_vslam.sources.replay import ReplayMode
from prml_vslam.sources.stage.config import SourceStageConfig
from prml_vslam.utils import PathConfig
from prml_vslam.utils.geometry import load_point_cloud_ply_with_colors

try:
    import liblzfse as _liblzfse
except ImportError:
    _liblzfse = None


class _PassthroughLzfseCodec:
    @staticmethod
    def compress(payload: bytes) -> bytes:
        return payload

    @staticmethod
    def decompress(payload: bytes) -> bytes:
        return payload


def _test_lzfse_codec() -> object:
    return _liblzfse or _PassthroughLzfseCodec


@pytest.fixture(autouse=True)
def _patch_record3d_lzfse_codec(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(record3d_loading, "_load_liblzfse", _test_lzfse_codec)


def _write_record3d_archive(
    dataset_root: Path,
    *,
    sequence_id: str = "synthetic",
    frame_indices: tuple[int, ...] = (0, 1, 2),
) -> Path:
    dataset_root.mkdir(parents=True, exist_ok=True)
    archive_path = dataset_root / f"{sequence_id}.r3d"
    metadata = {
        "K": [100.0, 0.0, 0.0, 0.0, 100.0, 0.0, 4.0, 4.0, 1.0],
        "w": 8,
        "h": 8,
        "dw": 4,
        "dh": 4,
        "fps": 10,
        "frameTimestamps": [0.0, 0.1, 0.2],
        "poses": [
            [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 1.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 1.0, 2.0, 0.0, 0.0],
        ],
    }
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("metadata", json.dumps(metadata))
        for seq, index in enumerate(frame_indices):
            rgb = np.full((8, 8, 3), seq * 60, dtype=np.uint8)
            ok, jpg = cv2.imencode(".jpg", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
            assert ok
            depth = np.full((4, 4), 1.0 + seq, dtype=np.float32)
            depth[0, 0] = 0.0
            confidence = np.full((4, 4), 2, dtype=np.uint8)
            confidence[0, 1] = 0
            archive.writestr(f"rgbd/{index}.jpg", jpg.tobytes())
            archive.writestr(f"rgbd/{index}.depth", _test_lzfse_codec().compress(depth.tobytes()))
            archive.writestr(f"rgbd/{index}.conf", _test_lzfse_codec().compress(confidence.tobytes()))
    return archive_path


def test_record3d_catalog_registers_zenodo_scenes_without_preview_token() -> None:
    catalog = load_record3d_catalog()

    assert [scene.sequence_index for scene in catalog.scenes] == list(range(8))
    assert [scene.archive_name for scene in catalog.scenes] == [
        "2026-06-03--18-17-10.r3d",
        "2026-06-03--18-20-22.r3d",
        "2026-06-03--18-24-27.r3d",
        "2026-06-03--18-26-32.r3d",
        "2026-06-03--18-27-25.r3d",
        "2026-06-03--18-29-08.r3d",
        "2026-06-03--18-32-27.r3d",
        "2026-06-03--18-35-44.r3d",
    ]
    assert catalog.scenes[3].archive_sha256 == "d76050f5edac45644dd3aafa20e1b73336959a4282c5494ff30c748c86288fc5"
    assert all("token=" not in (scene.archive_url or "") for scene in catalog.scenes)


def test_record3d_download_request_rejects_out_of_range_sequence_ids() -> None:
    assert Record3DDownloadRequest(sequence_ids=[3, 1, 3]).sequence_ids == [1, 3]
    with pytest.raises(ValidationError, match="non-negative"):
        Record3DDownloadRequest(sequence_ids=[-1])


def test_record3d_dataset_service_downloads_selected_archives_from_file_urls(tmp_path: Path) -> None:
    remote_archive = _write_record3d_archive(tmp_path / "remote", sequence_id="downloadable")
    source_hash = sha256(remote_archive.read_bytes()).hexdigest()
    catalog = Record3DCatalog(
        scenes=[
            Record3DSceneMetadata(
                sequence_index=3,
                sequence_id="downloadable",
                archive_name="downloadable.r3d",
                display_name="Downloadable",
                archive_url=remote_archive.as_uri(),
                archive_sha256=source_hash,
            )
        ]
    )
    service = Record3DDatasetService(PathConfig(root=tmp_path, data_dir=tmp_path / ".data"), catalog=catalog)

    first_result = service.download(Record3DDownloadRequest(sequence_ids=[3]))
    second_result = service.download(Record3DDownloadRequest(sequence_ids=[3]))

    local_archive = tmp_path / ".data" / "record3d" / "downloadable.r3d"
    assert local_archive.exists()
    assert sha256(local_archive.read_bytes()).hexdigest() == source_hash
    assert first_result.sequence_ids == [3]
    assert first_result.downloaded_archive_count == 1
    assert first_result.reused_archive_count == 0
    assert first_result.written_path_count == 1
    assert second_result.downloaded_archive_count == 0
    assert second_result.reused_archive_count == 1


def test_record3d_dataset_service_summarizes_catalog_scenes_even_when_missing(tmp_path: Path) -> None:
    catalog = Record3DCatalog(
        scenes=[
            Record3DSceneMetadata(
                sequence_index=0,
                sequence_id="missing",
                archive_name="missing.r3d",
                display_name="Missing",
                archive_url="file:///tmp/missing.r3d",
                archive_sha256="0" * 64,
            )
        ]
    )
    service = Record3DDatasetService(PathConfig(root=tmp_path, data_dir=tmp_path / ".data"), catalog=catalog)

    statuses = service.local_scene_statuses()
    summary = service.summarize(statuses)

    assert len(statuses) == 1
    assert statuses[0].scene.sequence_id == "missing"
    assert statuses[0].sequence_dir is None
    assert statuses[0].archive_path is None
    assert summary.total_scene_count == 1
    assert summary.local_scene_count == 0
    assert summary.offline_ready_scene_count == 0


def test_record3d_dataset_service_appends_local_ad_hoc_archives_to_catalog_statuses(tmp_path: Path) -> None:
    _write_record3d_archive(tmp_path / ".data" / "record3d", sequence_id="synthetic")
    catalog = Record3DCatalog(
        scenes=[
            Record3DSceneMetadata(
                sequence_index=0,
                sequence_id="catalog-missing",
                archive_name="catalog-missing.r3d",
                display_name="Catalog Missing",
            )
        ]
    )
    service = Record3DDatasetService(PathConfig(root=tmp_path, data_dir=tmp_path / ".data"), catalog=catalog)

    statuses = service.local_scene_statuses()

    assert [status.scene.sequence_id for status in statuses] == ["catalog-missing", "synthetic"]
    assert statuses[0].offline_ready is False
    assert statuses[1].offline_ready is True


def test_record3d_dataset_service_rejects_sequence_indices_outside_catalog(tmp_path: Path) -> None:
    catalog = Record3DCatalog(
        scenes=[
            Record3DSceneMetadata(
                sequence_index=0,
                sequence_id="downloadable",
                archive_name="downloadable.r3d",
                display_name="Downloadable",
            )
        ]
    )
    service = Record3DDatasetService(PathConfig(root=tmp_path, data_dir=tmp_path / ".data"), catalog=catalog)

    with pytest.raises(ValueError, match=r"\[0, 0\]"):
        service.download(Record3DDownloadRequest(sequence_ids=[8]))


def test_record3d_download_redacts_sensitive_url_query_values() -> None:
    url = "https://zenodo.org/records/20591352/files/scene.r3d?preview=1&token=secret&access_token=also-secret"

    redacted = _redact_url_for_log(url)

    assert "preview=1" in redacted
    assert "token=%3Credacted%3E" in redacted
    assert "access_token=%3Credacted%3E" in redacted
    assert "secret" not in redacted


def test_record3d_dataset_service_rejects_unsafe_archive_names(tmp_path: Path) -> None:
    remote_archive = _write_record3d_archive(tmp_path / "remote", sequence_id="unsafe")
    catalog = Record3DCatalog(
        scenes=[
            Record3DSceneMetadata(
                sequence_index=0,
                sequence_id="unsafe",
                archive_name="../unsafe.r3d",
                display_name="Unsafe",
                archive_url=remote_archive.as_uri(),
                archive_sha256=sha256(remote_archive.read_bytes()).hexdigest(),
            )
        ]
    )
    service = Record3DDatasetService(PathConfig(root=tmp_path, data_dir=tmp_path / ".data"), catalog=catalog)

    with pytest.raises(ValueError, match="simple `.r3d` filename"):
        service.download(Record3DDownloadRequest(sequence_ids=[0]))


def test_record3d_dataset_service_rejects_download_checksum_mismatch(tmp_path: Path) -> None:
    remote_archive = _write_record3d_archive(tmp_path / "remote", sequence_id="bad-hash")
    catalog = Record3DCatalog(
        scenes=[
            Record3DSceneMetadata(
                sequence_index=0,
                sequence_id="bad-hash",
                archive_name="bad-hash.r3d",
                display_name="Bad Hash",
                archive_url=remote_archive.as_uri(),
                archive_sha256="0" * 64,
            )
        ]
    )
    service = Record3DDatasetService(PathConfig(root=tmp_path, data_dir=tmp_path / ".data"), catalog=catalog)

    with pytest.raises(ValueError, match="Checksum mismatch"):
        service.download(Record3DDownloadRequest(sequence_ids=[0]))
    assert not (tmp_path / ".data" / "record3d" / "bad-hash.r3d").exists()


def test_record3d_sequence_loads_rgbd_observations_and_reference_cloud(tmp_path: Path) -> None:
    _write_record3d_archive(tmp_path)
    sequence = Record3DSequence(
        config=Record3DSequenceConfig(
            dataset_root=tmp_path,
            sequence_id="synthetic",
            reference_cloud=ReferenceCloudConfig(depth_stride_px=1, max_points=20, random_seed=17, min_confidence=1),
        )
    )

    sample = sequence.load_offline_sample()
    manifest = sequence.to_sequence_manifest(output_dir=tmp_path / "manifest")
    benchmark_inputs = sequence.to_benchmark_inputs(output_dir=tmp_path / "benchmark")
    observations = list(FileObservationSequenceLoader(benchmark_inputs.observation_sequences[0]).iter_observations())
    points_xyz, colors_rgb = load_point_cloud_ply_with_colors(benchmark_inputs.reference_clouds[0].path)
    metadata = json.loads(benchmark_inputs.reference_clouds[0].metadata_path.read_text(encoding="utf-8"))

    assert sample.sequence_id == "synthetic"
    assert len(sample.frames) == 3
    assert sample.rgb_intrinsics.width_px == 8
    assert sample.depth_intrinsics.width_px == 4
    assert sample.timestamps_ns == [0, 100_000_000, 200_000_000]
    assert manifest.dataset_id is DatasetId.RECORD3D
    assert sorted(path.name for path in manifest.rgb_dir.glob("*.png")) == ["000000.png", "000001.png", "000002.png"]
    assert benchmark_inputs.reference_trajectories[0].source is ReferenceSource.ARKIT
    assert benchmark_inputs.reference_trajectories[0].target_frame == "record3d_world"
    assert benchmark_inputs.reference_clouds[0].source is ReferenceCloudSource.RECORD3D_LIDAR
    assert benchmark_inputs.reference_clouds[0].coordinate_status.value == "aligned"
    assert len(observations) == 3
    assert observations[0].rgb is not None
    assert observations[0].rgb.shape == (4, 4, 3)
    assert observations[0].depth_m is not None
    assert observations[0].depth_m.shape == (4, 4)
    assert observations[0].intrinsics.width_px == 4
    assert observations[1].T_world_camera.tx == pytest.approx(1.0)
    assert points_xyz.shape[0] == 20
    assert colors_rgb is not None
    assert metadata["max_points"] == 20
    assert metadata["depth_stride_px"] == 1
    assert metadata["min_confidence"] == 1
    assert metadata["seed"] == 17
    assert metadata["point_count"] == 20
    assert metadata["rejected_count"] >= 2


def test_record3d_dataset_service_and_registry_discover_local_archives(tmp_path: Path) -> None:
    _write_record3d_archive(tmp_path / ".data" / "record3d")
    path_config = PathConfig(root=tmp_path, data_dir=tmp_path / ".data")
    service = Record3DDatasetService(path_config)

    source = service.build_streaming_source(
        sequence_id="synthetic",
        frame_selection=None,
        replay_mode=ReplayMode.FAST_AS_POSSIBLE,
    )
    manifest = source.prepare_sequence_manifest(tmp_path / "source")

    assert service.resolve_sequence_id("synthetic.r3d") == "synthetic"
    synthetic_status = next(
        status for status in service.local_scene_statuses() if status.scene.sequence_id == "synthetic"
    )
    assert synthetic_status.offline_ready is True
    assert source.label == "synthetic"
    assert manifest.dataset_id is DatasetId.RECORD3D
    assert list_sequence_slugs(DatasetId.RECORD3D, tmp_path / ".data" / "record3d") == ["synthetic"]
    assert resolve_reference_path(DatasetId.RECORD3D, tmp_path / ".data" / "record3d", "synthetic") is None


def test_normalize_dataset_batch_uses_advio_slugs_for_default_numeric_catalog_statuses(monkeypatch) -> None:
    seen_tasks: list[str] = []

    class FakeAdvioService:
        def local_scene_statuses(self) -> list[object]:
            return [
                SimpleNamespace(
                    scene=SimpleNamespace(sequence_id=1, sequence_slug="advio-01"),
                    offline_ready=True,
                )
            ]

        def resolve_sequence_id(self, sequence_id: str) -> int:
            assert sequence_id == "advio-01"
            return 1

    def fake_dataset_service(dataset_id: DatasetId, _path_config: PathConfig) -> FakeAdvioService:
        assert dataset_id is DatasetId.ADVIO
        return FakeAdvioService()

    def fake_task(task: object) -> object:
        seen_tasks.append(task.sequence_id)
        return batch_normalization.NormalizedDatasetBatchRecord(
            dataset_id=DatasetId.ADVIO,
            sequence_id=task.sequence_id,
            profile_key="profile",
            status="built",
        )

    monkeypatch.setattr(batch_normalization, "dataset_service", fake_dataset_service)
    monkeypatch.setattr(batch_normalization, "_normalize_batch_task", fake_task)

    result = normalize_dataset_batch(
        NormalizedDatasetBatchConfig(datasets=[NormalizedDatasetSelection(dataset_id=DatasetId.ADVIO)], max_workers=1),
        path_config=PathConfig(root=Path.cwd()),
    )

    assert seen_tasks == ["advio-01"]
    assert result.failed == []
    assert result.records[0].sequence_id == "advio-01"


def test_normalize_dataset_batch_accepts_advio_numeric_string_selections(monkeypatch) -> None:
    seen_tasks: list[str] = []

    class FakeAdvioService:
        def local_scene_statuses(self) -> list[object]:
            return [
                SimpleNamespace(
                    scene=SimpleNamespace(sequence_id=1, sequence_slug="advio-01"),
                    offline_ready=True,
                )
            ]

        def resolve_sequence_id(self, sequence_id: str) -> int:
            if sequence_id == "1":
                raise AssertionError("numeric ADVIO selections should not be resolved as slugs")
            assert sequence_id == "advio-01"
            return 1

    def fake_dataset_service(dataset_id: DatasetId, _path_config: PathConfig) -> FakeAdvioService:
        assert dataset_id is DatasetId.ADVIO
        return FakeAdvioService()

    def fake_task(task: object) -> object:
        seen_tasks.append(task.sequence_id)
        return batch_normalization.NormalizedDatasetBatchRecord(
            dataset_id=DatasetId.ADVIO,
            sequence_id=task.sequence_id,
            profile_key="profile",
            status="built",
        )

    monkeypatch.setattr(batch_normalization, "dataset_service", fake_dataset_service)
    monkeypatch.setattr(batch_normalization, "_normalize_batch_task", fake_task)

    result = normalize_dataset_batch(
        NormalizedDatasetBatchConfig(
            datasets=[NormalizedDatasetSelection(dataset_id=DatasetId.ADVIO, sequence_ids=["1"])],
            max_workers=1,
        ),
        path_config=PathConfig(root=Path.cwd()),
    )

    assert seen_tasks == ["advio-01"]
    assert result.failed == []
    assert result.records[0].sequence_id == "advio-01"


def test_normalize_batch_task_reuses_entry_with_single_load(monkeypatch, tmp_path: Path) -> None:
    profile = NormalizedDatasetProfile(
        dataset_id=DatasetId.RECORD3D,
        sequence_id="synthetic",
        source_id="record3d_dataset",
        source_profile={"sequence_id": "synthetic"},
    )
    entry = NormalizedDatasetEntry(
        dataset_id=DatasetId.RECORD3D,
        sequence_id="synthetic",
        source_id="record3d_dataset",
        profile_key=profile.profile_key,
        profile=profile.model_dump(mode="json"),
        root=tmp_path / "entry",
        sequence_manifest_path=tmp_path / "entry" / "sequence_manifest.json",
        benchmark_inputs_path=tmp_path / "entry" / "benchmark_inputs.json",
    )

    class FakeStore:
        load_count = 0

        def entry_root(self, requested_profile: NormalizedDatasetProfile) -> Path:
            assert requested_profile == profile
            return tmp_path / ".data" / "record3d" / ".normalized" / "synthetic" / profile.profile_key

        def load_entry(self, requested_profile: NormalizedDatasetProfile) -> NormalizedDatasetEntry:
            assert requested_profile == profile
            self.load_count += 1
            return entry

    store = FakeStore()
    monkeypatch.setattr(batch_normalization, "dataset_service", lambda _dataset_id, _path_config: SimpleNamespace())
    monkeypatch.setattr(batch_normalization, "source_config_for_normalization", lambda **_kwargs: SimpleNamespace())
    monkeypatch.setattr(batch_normalization, "normalized_profile_for_dataset", lambda **_kwargs: profile)
    monkeypatch.setattr(batch_normalization, "normalized_store_for_service", lambda _dataset_id, _service: store)
    monkeypatch.setattr(
        batch_normalization,
        "normalize_dataset_entry",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("reused entries should not be rebuilt")),
    )

    record = batch_normalization._normalize_batch_task(
        batch_normalization._BatchTask(
            path_config=PathConfig(root=tmp_path),
            selection=NormalizedDatasetSelection(dataset_id=DatasetId.RECORD3D, sequence_ids=["synthetic"]),
            sequence_id="synthetic",
        )
    )

    assert record.status == "reused"
    assert store.load_count == 1


def test_normalize_batch_task_reports_rich_stale_entry_failure(monkeypatch, tmp_path: Path) -> None:
    profile = NormalizedDatasetProfile(
        dataset_id=DatasetId.RECORD3D,
        sequence_id="synthetic",
        source_id="record3d_dataset",
        source_profile={"sequence_id": "synthetic"},
    )
    entry_root = tmp_path / ".data" / "record3d" / ".normalized" / "synthetic" / profile.profile_key

    class FakeStore:
        def entry_root(self, requested_profile: NormalizedDatasetProfile) -> Path:
            assert requested_profile == profile
            return entry_root

        def load_entry(self, requested_profile: NormalizedDatasetProfile) -> NormalizedDatasetEntry:
            assert requested_profile == profile
            raise RuntimeError("schema_version mismatch")

    monkeypatch.setattr(batch_normalization, "dataset_service", lambda _dataset_id, _path_config: SimpleNamespace())
    monkeypatch.setattr(batch_normalization, "source_config_for_normalization", lambda **_kwargs: SimpleNamespace())
    monkeypatch.setattr(batch_normalization, "normalized_profile_for_dataset", lambda **_kwargs: profile)
    monkeypatch.setattr(batch_normalization, "normalized_store_for_service", lambda _dataset_id, _service: FakeStore())
    monkeypatch.setattr(
        batch_normalization,
        "normalize_dataset_entry",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("stale entries should fail before rebuild")),
    )

    record = batch_normalization._normalize_batch_task(
        batch_normalization._BatchTask(
            path_config=PathConfig(root=tmp_path),
            selection=NormalizedDatasetSelection(dataset_id=DatasetId.RECORD3D, sequence_ids=["synthetic"]),
            sequence_id="synthetic",
        )
    )

    assert record.status == "failed"
    assert record.profile_key == profile.profile_key
    assert record.entry_root == entry_root
    assert "RuntimeError" in record.message
    assert "dataset_id=record3d_dataset" in record.message
    assert "sequence_id=synthetic" in record.message
    assert f"profile_key={profile.profile_key}" in record.message
    assert f"entry_root={entry_root}" in record.message
    assert "schema_version mismatch" in record.message


def test_normalized_dataset_batch_defaults_to_available_cpu_workers(monkeypatch) -> None:
    monkeypatch.setattr(batch_normalization.os, "cpu_count", lambda: 7)

    config = NormalizedDatasetBatchConfig()

    assert config.max_workers == 7


def test_normalize_dataset_batch_emits_progress_events(monkeypatch) -> None:
    events: list[batch_normalization.NormalizedDatasetBatchProgress] = []

    class FakeRecord3DService:
        def local_scene_statuses(self) -> list[object]:
            return [
                SimpleNamespace(
                    scene=SimpleNamespace(sequence_id="ready"),
                    offline_ready=True,
                ),
                SimpleNamespace(
                    scene=SimpleNamespace(sequence_id="missing"),
                    offline_ready=False,
                ),
            ]

        def resolve_sequence_id(self, sequence_id: str) -> str:
            return sequence_id

    def fake_dataset_service(dataset_id: DatasetId, _path_config: PathConfig) -> FakeRecord3DService:
        assert dataset_id is DatasetId.RECORD3D
        return FakeRecord3DService()

    def fake_task(task: object) -> object:
        return batch_normalization.NormalizedDatasetBatchRecord(
            dataset_id=DatasetId.RECORD3D,
            sequence_id=task.sequence_id,
            profile_key="profile",
            status="built",
        )

    monkeypatch.setattr(batch_normalization, "dataset_service", fake_dataset_service)
    monkeypatch.setattr(batch_normalization, "_normalize_batch_task", fake_task)

    result = normalize_dataset_batch(
        NormalizedDatasetBatchConfig(
            datasets=[NormalizedDatasetSelection(dataset_id=DatasetId.RECORD3D, sequence_ids=["ready", "missing"])],
            max_workers=1,
            missing_policy=NormalizedDatasetMissingPolicy.SKIP,
        ),
        path_config=PathConfig(root=Path.cwd()),
        progress=events.append,
    )

    assert result.built_count == 1
    assert result.skipped_count == 1
    assert [event.stage for event in events] == [
        "discovering",
        "discovered",
        "skipped",
        "queued",
        "processing",
        "completed",
    ]
    assert events[-1].completed == 1
    assert events[-1].total == 1


def test_record3d_normalized_store_persists_queryable_stats(tmp_path: Path) -> None:
    _write_record3d_archive(tmp_path / ".data" / "record3d")
    path_config = PathConfig(root=tmp_path, data_dir=tmp_path / ".data")
    service = Record3DDatasetService(path_config)
    source_config = Record3DDatasetSourceConfig(
        sequence_id="synthetic",
        reference_cloud=ReferenceCloudConfig(depth_stride_px=1, max_points=20, min_confidence=1),
    )
    store = NormalizedDatasetStore(dataset_root=service.dataset_root, dataset_id=DatasetId.RECORD3D)
    profile = normalized_profile_for_source_config(
        dataset_id=DatasetId.RECORD3D,
        sequence_id="synthetic",
        source_id=source_config.source_id,
        payload=source_config.model_dump(mode="json"),
    )
    raw_source = service.build_streaming_source(
        sequence_id="synthetic",
        frame_selection=FrameSelectionConfig(),
        replay_mode=source_config.replay_mode,
        materialization=source_config.materialization,
        reference_cloud=source_config.reference_cloud,
    )

    entry = store.create_entry_from_source(profile=profile, source=raw_source)
    query = NormalizedDatasetQuery.from_path_config(path_config)
    records = query.record_rows([DatasetId.RECORD3D])
    stats = query.stats_long_rows([DatasetId.RECORD3D])
    metadata = query.metadata_long_rows([DatasetId.RECORD3D])

    benchmark_inputs = json.loads(entry.benchmark_inputs_path.read_text(encoding="utf-8"))
    observation_ref = benchmark_inputs["observation_sequences"][0]
    stored_inputs = PreparedBenchmarkInputs.model_validate_json(entry.benchmark_inputs_path.read_text(encoding="utf-8"))
    observations = list(FileObservationSequenceLoader(stored_inputs.observation_sequences[0]).iter_observations())

    assert entry.stats_long_csv_path is not None and entry.stats_long_csv_path.exists()
    assert entry.metadata_long_csv_path is not None and entry.metadata_long_csv_path.exists()
    assert observation_ref["payload_root"] == (entry.root / "observations").as_posix()
    assert observation_ref["index_path"] == (entry.root / "observations" / "observations.json").as_posix()
    assert (entry.root / "observations" / "rgb").is_dir()
    assert (entry.root / "observations" / "depth").is_dir()
    assert not (entry.root / "observations" / "0").exists()
    assert not (entry.root / "benchmark" / "observations").exists()
    assert len(observations) == 3
    assert observations[0].rgb is not None
    assert observations[0].depth_m is not None
    assert records[0]["schema_version"] == 4
    assert {row["stat_name"] for row in stats} >= {"frame_count", "duration_s", "valid_ratio", "path_length_m"}
    assert {row["stat_name"] for row in metadata} >= {"dataset_id", "sequence_id", "target_frame"}
    frame_count_row = next(row for row in stats if row["stat_name"] == "frame_count")
    assert frame_count_row["dataset_id"] == DatasetId.RECORD3D.value


def test_record3d_normalized_store_rejects_stale_schema_entries(tmp_path: Path) -> None:
    _write_record3d_archive(tmp_path / ".data" / "record3d")
    path_config = PathConfig(root=tmp_path, data_dir=tmp_path / ".data")
    service = Record3DDatasetService(path_config)
    source_config = Record3DDatasetSourceConfig(
        sequence_id="synthetic",
        reference_cloud=ReferenceCloudConfig(depth_stride_px=1, max_points=20, min_confidence=1),
    )
    store = NormalizedDatasetStore(dataset_root=service.dataset_root, dataset_id=DatasetId.RECORD3D)
    profile = normalized_profile_for_source_config(
        dataset_id=DatasetId.RECORD3D,
        sequence_id="synthetic",
        source_id=source_config.source_id,
        payload=source_config.model_dump(mode="json"),
    )
    raw_source = service.build_streaming_source(
        sequence_id="synthetic",
        frame_selection=FrameSelectionConfig(),
        replay_mode=source_config.replay_mode,
        materialization=source_config.materialization,
        reference_cloud=source_config.reference_cloud,
    )

    entry = store.create_entry_from_source(profile=profile, source=raw_source)
    entry_path = entry.root / "entry.json"
    stale_payload = json.loads(entry_path.read_text(encoding="utf-8"))
    stale_payload["schema_version"] = 1
    stale_payload["profile"]["schema_version"] = 1
    entry_path.write_text(json.dumps(stale_payload), encoding="utf-8")

    with pytest.raises(RuntimeError, match="schema_version"):
        store.load_entry(profile)
    assert store.summary() == []
    issues = store.issues()
    assert len(issues) == 1
    assert issues[0].status == "stale_schema"
    assert issues[0].sequence_id == "synthetic"


def test_record3d_normalized_store_rejects_pre_stats_schema_entries(tmp_path: Path) -> None:
    _write_record3d_archive(tmp_path / ".data" / "record3d")
    path_config = PathConfig(root=tmp_path, data_dir=tmp_path / ".data")
    service = Record3DDatasetService(path_config)
    source_config = Record3DDatasetSourceConfig(
        sequence_id="synthetic",
        reference_cloud=ReferenceCloudConfig(depth_stride_px=1, max_points=20, min_confidence=1),
    )
    store = NormalizedDatasetStore(dataset_root=service.dataset_root, dataset_id=DatasetId.RECORD3D)
    profile = normalized_profile_for_source_config(
        dataset_id=DatasetId.RECORD3D,
        sequence_id="synthetic",
        source_id=source_config.source_id,
        payload=source_config.model_dump(mode="json"),
    )
    raw_source = service.build_streaming_source(
        sequence_id="synthetic",
        frame_selection=FrameSelectionConfig(),
        replay_mode=source_config.replay_mode,
        materialization=source_config.materialization,
        reference_cloud=source_config.reference_cloud,
    )

    entry = store.create_entry_from_source(profile=profile, source=raw_source)
    entry_path = entry.root / "entry.json"
    stale_payload = json.loads(entry_path.read_text(encoding="utf-8"))
    stale_payload["schema_version"] = 2
    stale_payload["profile"]["schema_version"] = 2
    stale_payload.pop("stats_long_csv_path")
    stale_payload.pop("metadata_long_csv_path")
    entry.stats_long_csv_path.unlink()
    entry.metadata_long_csv_path.unlink()
    entry_path.write_text(json.dumps(stale_payload), encoding="utf-8")

    with pytest.raises(RuntimeError, match="schema_version"):
        store.load_entry(profile)
    assert store.summary() == []
    issues = store.issues()
    assert len(issues) == 1
    assert issues[0].status == "stale_schema"
    assert issues[0].sequence_id == "synthetic"


def test_record3d_normalized_store_reports_invalid_entries_without_aborting_summary(tmp_path: Path) -> None:
    _write_record3d_archive(tmp_path / ".data" / "record3d")
    path_config = PathConfig(root=tmp_path, data_dir=tmp_path / ".data")
    service = Record3DDatasetService(path_config)
    source_config = Record3DDatasetSourceConfig(
        sequence_id="synthetic",
        reference_cloud=ReferenceCloudConfig(depth_stride_px=1, max_points=20, min_confidence=1),
    )
    store = NormalizedDatasetStore(dataset_root=service.dataset_root, dataset_id=DatasetId.RECORD3D)
    profile = normalized_profile_for_source_config(
        dataset_id=DatasetId.RECORD3D,
        sequence_id="synthetic",
        source_id=source_config.source_id,
        payload=source_config.model_dump(mode="json"),
    )
    raw_source = service.build_streaming_source(
        sequence_id="synthetic",
        frame_selection=FrameSelectionConfig(),
        replay_mode=source_config.replay_mode,
        materialization=source_config.materialization,
        reference_cloud=source_config.reference_cloud,
    )

    entry = store.create_entry_from_source(profile=profile, source=raw_source)
    entry.benchmark_inputs_path.unlink()

    with pytest.raises(FileNotFoundError):
        store.load_entry(profile)
    assert store.summary(strict=False) == []
    issues = store.issues()
    assert len(issues) == 1
    assert issues[0].status == "invalid"
    assert issues[0].sequence_id == "synthetic"
    assert "FileNotFoundError" in issues[0].message

    query = NormalizedDatasetQuery.from_path_config(path_config)
    assert query.record_rows([DatasetId.RECORD3D]) == []
    issue_rows = query.issue_rows([DatasetId.RECORD3D])
    assert len(issue_rows) == 1
    assert issue_rows[0]["status"] == "invalid"


def test_normalized_store_depth_stats_loader_accepts_png_payloads(tmp_path: Path) -> None:
    depth_path = tmp_path / "depth.png"
    depth = np.array([[0, 5000], [2500, 1000]], dtype=np.uint16)
    assert cv2.imwrite(str(depth_path), depth)

    loaded = load_depth_array(depth_path)

    assert loaded.dtype == np.float32
    np.testing.assert_allclose(loaded, depth.astype(np.float32))


def test_normalized_store_preserves_manifest_timestamps_for_video_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class VideoSource:
        @property
        def label(self) -> str:
            return "video"

        def prepare_sequence_manifest(self, output_dir: Path) -> SequenceManifest:
            output_dir.mkdir(parents=True)
            video_path = output_dir / "frames.mov"
            video_path.write_bytes(b"placeholder")
            timestamps_path = output_dir / "frames.csv"
            timestamps_path.write_text("0.000000000,1\n0.123456789,2\n", encoding="utf-8")
            return SequenceManifest(
                sequence_id="video-seq",
                dataset_id=DatasetId.ADVIO,
                video_path=video_path,
                timestamps_path=timestamps_path,
            )

        def prepare_benchmark_inputs(self, output_dir: Path) -> PreparedBenchmarkInputs:
            output_dir.mkdir(parents=True)
            return PreparedBenchmarkInputs()

    extracted_rgb_dir = tmp_path / "extracted-rgb"
    extracted_rgb_dir.mkdir()
    monkeypatch.setattr(
        normalized_store_module,
        "extract_video_frames",
        lambda *, video_path, output_dir: SimpleNamespace(rgb_dir=extracted_rgb_dir, timestamps_ns=[0, 100_000_000]),
    )
    store = NormalizedDatasetStore(dataset_root=tmp_path / ".data" / "advio", dataset_id=DatasetId.ADVIO)
    profile = NormalizedDatasetProfile(
        dataset_id=DatasetId.ADVIO,
        sequence_id="video-seq",
        source_id="video-seq",
        source_profile={"sequence_id": "video-seq"},
    )

    entry = store.create_entry_from_source(profile=profile, source=VideoSource())
    manifest = SequenceManifest.model_validate_json(entry.sequence_manifest_path.read_text(encoding="utf-8"))
    timestamps = json.loads(manifest.timestamps_path.read_text(encoding="utf-8"))

    assert timestamps == {"timestamps_ns": [0, 123_456_789]}


def test_normalize_dataset_batch_reuses_existing_record3d_entry(tmp_path: Path) -> None:
    _write_record3d_archive(tmp_path / ".data" / "record3d")
    path_config = PathConfig(root=tmp_path, data_dir=tmp_path / ".data")
    config = NormalizedDatasetBatchConfig(
        datasets=[
            NormalizedDatasetSelection(
                dataset_id=DatasetId.RECORD3D,
                sequence_ids=["synthetic"],
                record3d_reference_cloud=ReferenceCloudConfig(depth_stride_px=1, max_points=20, min_confidence=1),
            )
        ],
        max_workers=1,
        missing_policy=NormalizedDatasetMissingPolicy.FAIL,
    )

    first = normalize_dataset_batch(config, path_config=path_config)
    second = normalize_dataset_batch(config, path_config=path_config)

    assert first.built_count == 1
    assert second.built_count == 1
    assert first.failed == []
    assert second.records[0].status == "reused"
    assert first.records[0].entry_root == second.records[0].entry_root


def test_normalized_store_preserves_external_benchmark_observation_sources(tmp_path: Path) -> None:
    payload_root = tmp_path / "external" / "benchmark" / "observations"
    rgb_dir = payload_root / "rgb"
    rgb_dir.mkdir(parents=True)
    rgb = np.zeros((2, 2, 3), dtype=np.uint8)
    assert cv2.imwrite(str(rgb_dir / "000000.png"), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    sequence_index = ObservationSequenceIndex(
        source_id="external",
        sequence_id="synthetic",
        observation_count=1,
        rows=[
            ObservationIndexEntry(
                seq=0,
                timestamp_ns=0,
                rgb_path=Path("rgb/000000.png"),
                provenance=ObservationProvenance(source_id="external", sequence_id="synthetic"),
            )
        ],
    )
    index_path = payload_root / "observations.json"
    index_path.write_text(json.dumps(sequence_index.model_dump(mode="json")), encoding="utf-8")
    timestamps_path = tmp_path / "source" / "timestamps.json"
    timestamps_path.parent.mkdir(parents=True)
    timestamps_path.write_text(json.dumps({"timestamps_ns": [0]}), encoding="utf-8")
    store = NormalizedDatasetStore(dataset_root=tmp_path / ".data" / "record3d", dataset_id=DatasetId.RECORD3D)
    profile = NormalizedDatasetProfile(
        dataset_id=DatasetId.RECORD3D,
        sequence_id="synthetic",
        source_id="synthetic",
        source_profile={"sequence_id": "synthetic"},
    )

    entry = store.create_entry(
        profile=profile,
        sequence_manifest=SequenceManifest(
            sequence_id="synthetic", dataset_id=DatasetId.RECORD3D, timestamps_path=timestamps_path
        ),
        benchmark_inputs=PreparedBenchmarkInputs(
            observation_sequences=[
                ObservationSequenceRef(
                    source_id="external",
                    sequence_id="synthetic",
                    index_path=index_path,
                    payload_root=payload_root,
                    observation_count=1,
                )
            ]
        ),
    )

    assert payload_root.exists()
    assert (entry.root / "observations" / "observations.json").exists()


def test_normalized_store_uses_indexed_observation_layout_only_for_multiple_sequences(tmp_path: Path) -> None:
    source_roots: list[Path] = []
    refs: list[ObservationSequenceRef] = []
    for index in range(2):
        payload_root = tmp_path / "source" / f"sequence-{index}"
        rgb_dir = payload_root / "rgb"
        rgb_dir.mkdir(parents=True)
        rgb = np.full((2, 2, 3), index, dtype=np.uint8)
        assert cv2.imwrite(str(rgb_dir / "000000.png"), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        sequence_index = ObservationSequenceIndex(
            source_id=f"source-{index}",
            sequence_id="synthetic",
            observation_count=1,
            rows=[
                ObservationIndexEntry(
                    seq=0,
                    timestamp_ns=index,
                    rgb_path=Path("rgb/000000.png"),
                    provenance=ObservationProvenance(source_id=f"source-{index}", sequence_id="synthetic"),
                )
            ],
        )
        index_path = payload_root / "observations.json"
        index_path.write_text(json.dumps(sequence_index.model_dump(mode="json")), encoding="utf-8")
        source_roots.append(payload_root)
        refs.append(
            ObservationSequenceRef(
                source_id=f"source-{index}",
                sequence_id="synthetic",
                index_path=index_path,
                payload_root=payload_root,
                observation_count=1,
            )
        )
    timestamps_path = tmp_path / "source" / "timestamps.json"
    timestamps_path.write_text(json.dumps({"timestamps_ns": [0]}), encoding="utf-8")
    store = NormalizedDatasetStore(dataset_root=tmp_path / ".data" / "record3d", dataset_id=DatasetId.RECORD3D)
    profile = NormalizedDatasetProfile(
        dataset_id=DatasetId.RECORD3D,
        sequence_id="synthetic",
        source_id="synthetic",
        source_profile={"sequence_id": "synthetic"},
    )

    entry = store.create_entry(
        profile=profile,
        sequence_manifest=SequenceManifest(
            sequence_id="synthetic", dataset_id=DatasetId.RECORD3D, timestamps_path=timestamps_path
        ),
        benchmark_inputs=PreparedBenchmarkInputs(observation_sequences=refs),
    )
    benchmark_inputs = json.loads(entry.benchmark_inputs_path.read_text(encoding="utf-8"))

    assert [
        Path(ref["payload_root"]).relative_to(entry.root).as_posix()
        for ref in benchmark_inputs["observation_sequences"]
    ] == [
        "observations/0",
        "observations/1",
    ]
    assert (entry.root / "observations" / "0" / "observations.json").exists()
    assert (entry.root / "observations" / "1" / "observations.json").exists()


def test_record3d_normalized_store_reuses_full_frame_payload_for_sampled_runs(tmp_path: Path) -> None:
    archive_path = _write_record3d_archive(tmp_path / ".data" / "record3d")
    path_config = PathConfig(root=tmp_path, data_dir=tmp_path / ".data")
    service = Record3DDatasetService(path_config)
    source_config = Record3DDatasetSourceConfig(
        sequence_id="synthetic",
        reference_cloud=ReferenceCloudConfig(depth_stride_px=1, max_points=20, min_confidence=1),
    )
    store = NormalizedDatasetStore(dataset_root=service.dataset_root, dataset_id=DatasetId.RECORD3D)
    profile = normalized_profile_for_source_config(
        dataset_id=DatasetId.RECORD3D,
        sequence_id="synthetic",
        source_id=source_config.source_id,
        payload=source_config.model_dump(mode="json"),
    )
    raw_source = service.build_streaming_source(
        sequence_id="synthetic",
        frame_selection=FrameSelectionConfig(),
        replay_mode=source_config.replay_mode,
        materialization=source_config.materialization,
        reference_cloud=source_config.reference_cloud,
    )
    entry = store.create_entry_from_source(profile=profile, source=raw_source)
    archive_path.rename(archive_path.with_suffix(".r3d.bak"))
    sampled_config = source_config.model_copy(update={"frame_stride": 2})
    sampled_profile = normalized_profile_for_source_config(
        dataset_id=DatasetId.RECORD3D,
        sequence_id="synthetic",
        source_id=sampled_config.source_id,
        payload=sampled_config.model_dump(mode="json"),
    )
    normalized_source = sampled_config.setup_target(path_config=path_config)

    manifest = normalized_source.prepare_sequence_manifest(tmp_path / "run" / "input")
    benchmark_inputs = normalized_source.prepare_benchmark_inputs(tmp_path / "run" / "benchmark")
    frame_indices = json.loads(manifest.source_frame_indices_path.read_text(encoding="utf-8"))
    timestamps = json.loads(manifest.timestamps_path.read_text(encoding="utf-8"))
    observation_ref = benchmark_inputs.observation_sequences[0]
    observation_index = json.loads(observation_ref.index_path.read_text(encoding="utf-8"))

    assert sampled_profile.profile_key == profile.profile_key
    assert entry.root.joinpath("input", "rgb").exists() is False
    assert manifest.rgb_dir == observation_ref.payload_root / "rgb"
    assert manifest.rgb_dir.is_relative_to(entry.root)
    assert not (tmp_path / "run" / "input" / "rgb").exists()
    assert frame_indices == {"source_frame_indices": [0, 2]}
    assert timestamps["timestamps_ns"] == [0, 200_000_000]
    assert observation_ref.payload_root.is_relative_to(entry.root)
    assert [row["provenance"]["source_frame_index"] for row in observation_index["rows"]] == [0, 2]


def test_record3d_normalized_store_rejects_tampered_entry_metadata(tmp_path: Path) -> None:
    _write_record3d_archive(tmp_path / ".data" / "record3d")
    path_config = PathConfig(root=tmp_path, data_dir=tmp_path / ".data")
    service = Record3DDatasetService(path_config)
    source_config = Record3DDatasetSourceConfig(
        sequence_id="synthetic",
        reference_cloud=ReferenceCloudConfig(depth_stride_px=1, max_points=20, min_confidence=1),
    )
    store = NormalizedDatasetStore(dataset_root=service.dataset_root, dataset_id=DatasetId.RECORD3D)
    profile = normalized_profile_for_source_config(
        dataset_id=DatasetId.RECORD3D,
        sequence_id="synthetic",
        source_id=source_config.source_id,
        payload=source_config.model_dump(mode="json"),
    )
    raw_source = service.build_streaming_source(
        sequence_id="synthetic",
        frame_selection=FrameSelectionConfig(),
        replay_mode=source_config.replay_mode,
        materialization=source_config.materialization,
        reference_cloud=source_config.reference_cloud,
    )
    entry = store.create_entry_from_source(profile=profile, source=raw_source)
    payload = entry.model_dump(mode="json")
    payload["sequence_id"] = "other"
    (entry.root / "entry.json").write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(RuntimeError, match="metadata does not match requested profile"):
        store.load_entry(profile)
    with pytest.raises(RuntimeError, match="metadata does not match requested profile"):
        store.summary()


def test_record3d_normalized_store_rejects_tampered_manifest_paths(tmp_path: Path) -> None:
    _write_record3d_archive(tmp_path / ".data" / "record3d")
    path_config = PathConfig(root=tmp_path, data_dir=tmp_path / ".data")
    service = Record3DDatasetService(path_config)
    source_config = Record3DDatasetSourceConfig(
        sequence_id="synthetic",
        reference_cloud=ReferenceCloudConfig(depth_stride_px=1, max_points=20, min_confidence=1),
    )
    store = NormalizedDatasetStore(dataset_root=service.dataset_root, dataset_id=DatasetId.RECORD3D)
    profile = normalized_profile_for_source_config(
        dataset_id=DatasetId.RECORD3D,
        sequence_id="synthetic",
        source_id=source_config.source_id,
        payload=source_config.model_dump(mode="json"),
    )
    raw_source = service.build_streaming_source(
        sequence_id="synthetic",
        frame_selection=FrameSelectionConfig(),
        replay_mode=source_config.replay_mode,
        materialization=source_config.materialization,
        reference_cloud=source_config.reference_cloud,
    )
    entry = store.create_entry_from_source(profile=profile, source=raw_source)
    manifest = json.loads(entry.sequence_manifest_path.read_text(encoding="utf-8"))
    manifest["rgb_dir"] = (tmp_path / "outside-rgb").as_posix()
    entry.sequence_manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(RuntimeError, match="outside entry root"):
        store.load_entry(profile)
    with pytest.raises(RuntimeError, match="outside entry root"):
        store.summary()


def test_record3d_normalized_store_rejects_tampered_observation_paths(tmp_path: Path) -> None:
    _write_record3d_archive(tmp_path / ".data" / "record3d")
    path_config = PathConfig(root=tmp_path, data_dir=tmp_path / ".data")
    service = Record3DDatasetService(path_config)
    source_config = Record3DDatasetSourceConfig(
        sequence_id="synthetic",
        reference_cloud=ReferenceCloudConfig(depth_stride_px=1, max_points=20, min_confidence=1),
    )
    store = NormalizedDatasetStore(dataset_root=service.dataset_root, dataset_id=DatasetId.RECORD3D)
    profile = normalized_profile_for_source_config(
        dataset_id=DatasetId.RECORD3D,
        sequence_id="synthetic",
        source_id=source_config.source_id,
        payload=source_config.model_dump(mode="json"),
    )
    raw_source = service.build_streaming_source(
        sequence_id="synthetic",
        frame_selection=FrameSelectionConfig(),
        replay_mode=source_config.replay_mode,
        materialization=source_config.materialization,
        reference_cloud=source_config.reference_cloud,
    )
    entry = store.create_entry_from_source(profile=profile, source=raw_source)
    benchmark_inputs = json.loads(entry.benchmark_inputs_path.read_text(encoding="utf-8"))
    index_path = Path(benchmark_inputs["observation_sequences"][0]["index_path"])
    observation_index = json.loads(index_path.read_text(encoding="utf-8"))
    observation_index["rows"][0]["depth_path"] = (tmp_path / "outside-depth.npy").as_posix()
    index_path.write_text(json.dumps(observation_index), encoding="utf-8")

    with pytest.raises(RuntimeError, match="outside entry root"):
        store.load_entry(profile)
    with pytest.raises(RuntimeError, match="outside entry root"):
        store.summary()


def test_record3d_dataset_source_requires_normalized_store_entry(tmp_path: Path) -> None:
    _write_record3d_archive(tmp_path / ".data" / "record3d")
    path_config = PathConfig(root=tmp_path, data_dir=tmp_path / ".data")
    source = Record3DDatasetSourceConfig(sequence_id="synthetic").setup_target(path_config=path_config)

    with pytest.raises(FileNotFoundError, match="prml-vslam dataset normalize --dataset record3d"):
        source.prepare_sequence_manifest(tmp_path / "run" / "input")


def test_record3d_dataset_stream_honors_target_fps(tmp_path: Path) -> None:
    _write_record3d_archive(tmp_path / ".data" / "record3d")
    path_config = PathConfig(root=tmp_path, data_dir=tmp_path / ".data")
    service = Record3DDatasetService(path_config)
    source = service.build_streaming_source(
        sequence_id="synthetic",
        frame_selection=FrameSelectionConfig(target_fps=5.0),
        replay_mode=ReplayMode.FAST_AS_POSSIBLE,
    )

    stream = source.open_stream(loop=False)
    stream.connect()
    packet_0 = stream.wait_for_observation()
    packet_1 = stream.wait_for_observation()

    assert packet_0.source_frame_index == 0
    assert packet_1.source_frame_index == 2
    with pytest.raises(EOFError):
        stream.wait_for_observation()


def test_record3d_preview_stream_does_not_require_reference_cloud_points(tmp_path: Path) -> None:
    _write_record3d_archive(tmp_path)
    sequence = Record3DSequence(
        config=Record3DSequenceConfig(
            dataset_root=tmp_path,
            sequence_id="synthetic",
            reference_cloud=ReferenceCloudConfig(min_confidence=3),
        )
    )

    stream = sequence.open_stream(loop=False, replay_mode=ReplayMode.FAST_AS_POSSIBLE)
    stream.connect()
    packet = stream.wait_for_observation()

    assert packet.rgb is not None
    assert packet.depth_m is not None
    with pytest.raises(RuntimeError, match="no valid points"):
        sequence.to_benchmark_inputs(output_dir=tmp_path / "benchmark")


def test_record3d_benchmark_inputs_honor_source_frame_selection(tmp_path: Path) -> None:
    _write_record3d_archive(tmp_path)
    sequence = Record3DSequence(
        config=Record3DSequenceConfig(
            dataset_root=tmp_path,
            sequence_id="synthetic",
            reference_cloud=ReferenceCloudConfig(depth_stride_px=1, max_points=100, random_seed=17, min_confidence=1),
        )
    )

    benchmark_inputs = sequence.to_benchmark_inputs(
        output_dir=tmp_path / "benchmark",
        frame_selection=FrameSelectionConfig(frame_stride=2),
    )

    observation_index = json.loads(benchmark_inputs.observation_sequences[0].index_path.read_text(encoding="utf-8"))
    metadata = json.loads(benchmark_inputs.reference_clouds[0].metadata_path.read_text(encoding="utf-8"))

    assert [row["provenance"]["source_frame_index"] for row in observation_index["rows"]] == [0, 2]
    assert metadata["method_sample_count"] == 2
    assert metadata["selected_frame_count"] == 2
    assert metadata["reference_cloud_sampled_frame_indices"] == [0, 2]
    assert metadata["source_frame_indices"] == [0, 2]


def test_record3d_reference_cloud_config_controls_sampling_and_metadata(tmp_path: Path) -> None:
    _write_record3d_archive(tmp_path)
    base_config = Record3DSequenceConfig(
        dataset_root=tmp_path,
        sequence_id="synthetic",
        reference_cloud=ReferenceCloudConfig(depth_stride_px=1, max_points=6, random_seed=1, min_confidence=1),
    )
    repeat_config = base_config.model_copy(
        update={
            "reference_cloud": ReferenceCloudConfig(depth_stride_px=1, max_points=6, random_seed=1, min_confidence=1)
        }
    )
    different_seed_config = base_config.model_copy(
        update={
            "reference_cloud": ReferenceCloudConfig(depth_stride_px=1, max_points=6, random_seed=2, min_confidence=1)
        }
    )

    first_inputs = Record3DSequence(config=base_config).to_benchmark_inputs(output_dir=tmp_path / "first")
    repeat_inputs = Record3DSequence(config=repeat_config).to_benchmark_inputs(output_dir=tmp_path / "repeat")
    different_seed_inputs = Record3DSequence(config=different_seed_config).to_benchmark_inputs(
        output_dir=tmp_path / "different-seed"
    )
    points_first, _colors_first = load_point_cloud_ply_with_colors(first_inputs.reference_clouds[0].path)
    points_repeat, _colors_repeat = load_point_cloud_ply_with_colors(repeat_inputs.reference_clouds[0].path)
    points_different_seed, _colors_different_seed = load_point_cloud_ply_with_colors(
        different_seed_inputs.reference_clouds[0].path
    )
    metadata = json.loads(first_inputs.reference_clouds[0].metadata_path.read_text(encoding="utf-8"))

    assert metadata["depth_stride_px"] == 1
    assert metadata["max_points"] == 6
    assert metadata["min_confidence"] == 1
    assert metadata["seed"] == 1
    assert metadata["point_count_before_sampling"] > 6
    assert metadata["point_sampling_policy"] == "random_without_replacement"
    np.testing.assert_allclose(points_repeat, points_first)
    assert not np.allclose(points_different_seed, points_first)


def test_record3d_source_config_accepts_reference_cloud_block_and_rejects_old_materialization_cloud_keys() -> None:
    source = SourceStageConfig.from_toml(
        """
        [backend]
        source_id = "record3d_dataset"
        sequence_id = "synthetic"

        [backend.reference_cloud]
        depth_stride_px = 4
        max_points = 64
        random_seed = 5
        min_confidence = 2
        """
    )
    reloaded = SourceStageConfig.from_toml(source.to_toml())

    assert isinstance(source.backend, Record3DDatasetSourceConfig)
    assert source.backend.reference_cloud.depth_stride_px == 4
    assert source.backend.reference_cloud.max_points == 64
    assert source.backend.reference_cloud.random_seed == 5
    assert source.backend.reference_cloud.min_confidence == 2
    assert isinstance(reloaded.backend, Record3DDatasetSourceConfig)
    assert reloaded.backend.reference_cloud == source.backend.reference_cloud

    removed_shapes = [
        {"materialization": {"reference_cloud_max_points": 64}},
        {"reference_cloud_max_points": 64},
        {"reference_cloud_frame_stride": 2},
        {"reference_cloud_pixel_stride": 4},
        {"reference_cloud_min_confidence": 1},
    ]
    for removed_shape in removed_shapes:
        with pytest.raises(ValidationError):
            SourceStageConfig.model_validate(
                {
                    "backend": {
                        "source_id": "record3d_dataset",
                        "sequence_id": "synthetic",
                        **removed_shape,
                    }
                }
            )


def test_record3d_archive_frames_must_match_metadata_indices(tmp_path: Path) -> None:
    _write_record3d_archive(tmp_path, frame_indices=(1, 2, 3))
    sequence = Record3DSequence(config=Record3DSequenceConfig(dataset_root=tmp_path, sequence_id="synthetic"))

    with pytest.raises(ValueError, match="consecutively numbered"):
        sequence.load_offline_sample()


def test_record3d_source_config_plans_arkit_and_cloud_alignment_path(tmp_path: Path) -> None:
    _write_record3d_archive(tmp_path / ".data" / "record3d")
    path_config = PathConfig(root=tmp_path, data_dir=tmp_path / ".data", artifacts_dir=tmp_path / ".artifacts")
    source_backend = Record3DDatasetSourceConfig(sequence_id="synthetic", frame_stride=2)
    run_config = build_run_config(
        experiment_name="record3d-plan",
        output_dir=path_config.artifacts_dir,
        source_backend=source_backend,
        method=MethodId.VISTA,
        trajectory_alignment_enabled=True,
        trajectory_baseline=ReferenceSource.ARKIT,
        cloud_alignment_enabled=True,
        reference_enabled=False,
    )

    plan = run_config.compile_plan(path_config, fail_on_unavailable=True)

    assert run_config.stages.align_trajectory.baseline_source is ReferenceSource.ARKIT
    assert run_config.stages.align_cloud.enabled is True
    assert plan.source.source_id == "record3d_dataset"
    assert plan.source.sequence_id == "synthetic"
    assert plan.source.replay_mode == "realtime"
    assert plan.source.expected_fps == pytest.approx(10.0 / 2)
    assert plan.source.metadata["dataset_id"] == DatasetId.RECORD3D.value
    assert plan.source.metadata["pose_source"] == ReferenceSource.ARKIT.value
    assert plan.source.metadata["reference_cloud_source"] == ReferenceCloudSource.RECORD3D_LIDAR.value
    assert plan.source.metadata["reference_cloud_depth_stride_px"] == 8
    assert plan.source.metadata["reference_cloud_max_points"] == 100_000
    assert plan.source.metadata["reference_cloud_random_seed"] == 17
    assert plan.source.metadata["reference_cloud_min_confidence"] == 1
    assert next(stage for stage in plan.stages if stage.key is StageKey.CLOUD_ALIGNMENT).available is True


def test_record3d_decode_reports_missing_lzfse(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    archive_path = _write_record3d_archive(tmp_path)
    sequence = Record3DSequence(config=Record3DSequenceConfig(dataset_root=tmp_path, sequence_id="synthetic"))
    sample = sequence.load_offline_sample()

    def missing_lzfse() -> object:
        raise RuntimeError("Record3D `.r3d` depth/confidence decoding requires `pyliblzfse`.")

    from prml_vslam.sources.datasets.record3d import record3d_loading

    monkeypatch.setattr(record3d_loading, "_load_liblzfse", missing_lzfse)
    with pytest.raises(RuntimeError, match="pyliblzfse"):
        record3d_loading.decode_depth_frame_m(archive_path, sample.frames[0], sample.metadata)


def test_record3d_real_sample_decodes_rgbd_and_materializes_reference_cloud(tmp_path: Path) -> None:
    if _liblzfse is None:
        pytest.skip("Record3D real sample requires pyliblzfse for LZFSE payloads.")
    dataset_root = PathConfig().resolve_dataset_dir("record3d")
    archive_path = next(
        (
            dataset_root / archive_name
            for archive_name in (
                "2024-03-31--16-17-17.r3d",
                "2026-06-03--18-26-32.r3d",
            )
            if (dataset_root / archive_name).exists()
        ),
        dataset_root / "2024-03-31--16-17-17.r3d",
    )
    if not archive_path.exists():
        pytest.skip(f"Record3D sample is not present: {archive_path}")
    sequence = Record3DSequence(
        config=Record3DSequenceConfig(dataset_root=archive_path.parent, sequence_id=archive_path.stem)
    )

    sample = sequence.load_offline_sample()
    benchmark_inputs = sequence.to_benchmark_inputs(output_dir=tmp_path / "benchmark")
    observations = list(FileObservationSequenceLoader(benchmark_inputs.observation_sequences[0]).iter_observations())
    cloud_metadata = json.loads(benchmark_inputs.reference_clouds[0].metadata_path.read_text(encoding="utf-8"))

    assert len(sample.frames) > 0
    assert sample.metadata.dw > 0
    assert sample.metadata.dh > 0
    assert observations[0].rgb.shape == (sample.metadata.dh, sample.metadata.dw, 3)
    assert observations[0].depth_m.shape == (sample.metadata.dh, sample.metadata.dw)
    assert observations[0].intrinsics.width_px == sample.metadata.dw
    assert benchmark_inputs.reference_clouds[0].path.exists()
    assert cloud_metadata["point_count"] > 0
    assert cloud_metadata["point_count"] <= cloud_metadata["max_points"]
    assert cloud_metadata["depth_stride_px"] == 8
    assert cloud_metadata["min_confidence"] == 1
