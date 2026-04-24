"""Tests for content-addressed pipeline stage cache helpers."""

from __future__ import annotations

from pathlib import Path

from prml_vslam.interfaces.ingest import SequenceManifest
from prml_vslam.pipeline.contracts.events import StageOutcome
from prml_vslam.pipeline.contracts.provenance import ArtifactRef, StageStatus
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.finalization import write_json
from prml_vslam.pipeline.stage_cache import ContentFingerprinter, StageCacheKey, StageCacheStore
from prml_vslam.pipeline.stages.base.contracts import StageResult, StageRuntimeStatus
from prml_vslam.pipeline.stages.slam.config import MockSlamBackendConfig, SlamStageConfig


def test_content_fingerprint_uses_file_bytes_not_run_root_for_paths_and_artifacts(tmp_path: Path) -> None:
    first = tmp_path / "first" / "input.txt"
    second = tmp_path / "second" / "input.txt"
    first.parent.mkdir()
    second.parent.mkdir()
    first.write_text("same payload", encoding="utf-8")
    second.write_text("same payload", encoding="utf-8")

    fingerprinter = ContentFingerprinter()

    assert fingerprinter.hash_value({"input": first}) == fingerprinter.hash_value({"input": second})
    assert fingerprinter.hash_value(
        {"artifact": ArtifactRef(path=first, kind="txt", fingerprint="first-run-root")}
    ) == fingerprinter.hash_value({"artifact": ArtifactRef(path=second, kind="txt", fingerprint="second-run-root")})

    second.write_text("changed payload", encoding="utf-8")

    assert fingerprinter.hash_value({"input": first}) != fingerprinter.hash_value({"input": second})


def test_stage_cache_key_ignores_cache_policy_for_same_stage_config() -> None:
    first_config = SlamStageConfig(backend=MockSlamBackendConfig())
    second_config = SlamStageConfig(backend=MockSlamBackendConfig())
    second_config.cache.enabled = True
    second_config.cache.cache_root = Path("/tmp/other-cache-root")
    fingerprinter = ContentFingerprinter()

    first_hash = fingerprinter.hash_value(first_config)
    second_hash = fingerprinter.hash_value(second_config)

    assert first_hash == second_hash


def test_stage_cache_round_trips_source_result_into_new_run_root(tmp_path: Path) -> None:
    source_root = tmp_path / "source-run" / "mock"
    target_root = tmp_path / "target-run" / "mock"
    cache_store = StageCacheStore(tmp_path / "_stage_cache")
    run_paths = source_root / "input"
    run_paths.mkdir(parents=True)
    manifest_path = run_paths / "sequence_manifest.json"
    write_json(manifest_path, SequenceManifest(sequence_id="seq-1"))
    result = StageResult(
        stage_key=StageKey.SOURCE,
        payload=SequenceManifest(sequence_id="seq-1"),
        outcome=StageOutcome(
            stage_key=StageKey.SOURCE,
            status=StageStatus.COMPLETED,
            config_hash="config",
            input_fingerprint="input",
            artifacts={
                "sequence_manifest": ArtifactRef(
                    path=manifest_path,
                    kind="json",
                    fingerprint="manifest",
                )
            },
        ),
        final_runtime_status=StageRuntimeStatus(
            stage_key=StageKey.SOURCE,
            lifecycle_state=StageStatus.COMPLETED,
        ),
    )
    key = StageCacheKey.build(stage_key=StageKey.SOURCE, config_hash="config", input_fingerprint="input")

    entry_path = cache_store.write(key, result=result, artifact_root=source_root)
    cached = cache_store.read(key, artifact_root=target_root)

    assert entry_path is not None
    assert cached is not None
    assert cached.outcome.cache is not None
    assert cached.outcome.cache.hit is True
    assert cached.outcome.artifacts["sequence_manifest"].path == (target_root / "input" / "sequence_manifest.json")
    assert cached.payload is not None
    assert (target_root / "input" / "sequence_manifest.json").exists()


def test_stage_cache_rejects_stale_cached_artifact(tmp_path: Path) -> None:
    source_root = tmp_path / "source-run" / "mock"
    cache_store = StageCacheStore(tmp_path / "_stage_cache")
    manifest_path = source_root / "input" / "sequence_manifest.json"
    manifest_path.parent.mkdir(parents=True)
    write_json(manifest_path, SequenceManifest(sequence_id="seq-1"))
    key = StageCacheKey.build(stage_key=StageKey.SOURCE, config_hash="config", input_fingerprint="input")
    result = StageResult(
        stage_key=StageKey.SOURCE,
        payload=SequenceManifest(sequence_id="seq-1"),
        outcome=StageOutcome(
            stage_key=StageKey.SOURCE,
            status=StageStatus.COMPLETED,
            config_hash="config",
            input_fingerprint="input",
            artifacts={
                "sequence_manifest": ArtifactRef(path=manifest_path, kind="json", fingerprint="manifest"),
            },
        ),
        final_runtime_status=StageRuntimeStatus(stage_key=StageKey.SOURCE, lifecycle_state=StageStatus.COMPLETED),
    )

    entry_path = cache_store.write(key, result=result, artifact_root=source_root)
    assert entry_path is not None
    cached_manifest = entry_path / "artifacts" / "input" / "sequence_manifest.json"
    cached_manifest.write_text('{"sequence_id": "tampered"}', encoding="utf-8")

    assert cache_store.read(key, artifact_root=tmp_path / "target-run" / "mock") is None
