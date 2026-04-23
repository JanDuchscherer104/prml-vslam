"""Tests for portable pipeline run bundle export and import."""

from __future__ import annotations

import io
import tarfile
from pathlib import Path

import pytest

from prml_vslam.interfaces.ingest import SequenceManifest
from prml_vslam.pipeline.artifact_inspection import inspect_run_artifacts
from prml_vslam.pipeline.contracts.events import RunCompleted, RunStarted, RunSubmitted, StageCompleted, StageOutcome
from prml_vslam.pipeline.contracts.provenance import ArtifactRef, RunSummary, StageManifest, StageStatus
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.finalization import write_json
from prml_vslam.pipeline.run_bundle import RunBundleCollisionPolicy, export_run_bundle, import_run_bundle
from prml_vslam.pipeline.sinks.jsonl import JsonlEventSink


def test_run_bundle_export_import_relocates_run_metadata(tmp_path: Path) -> None:
    artifact_root = _write_fake_run(tmp_path / "source-artifacts" / "demo-run" / "mock")
    bundle_path = tmp_path / "demo-run.prmlrun.tar.gz"
    output_dir = tmp_path / "imported-artifacts"

    export_result = export_run_bundle(artifact_root, bundle_path)
    import_result = import_run_bundle(bundle_path, output_dir=output_dir)

    imported_root = output_dir / "demo-run" / "mock"
    inspection = inspect_run_artifacts(import_result.artifact_root)

    assert export_result.bundle_path == bundle_path
    assert import_result.artifact_root == imported_root.resolve()
    assert inspection.summary is not None
    assert inspection.summary.artifact_root == imported_root.resolve()
    assert inspection.sequence_manifest == SequenceManifest(sequence_id="seq-1")
    assert (
        inspection.stage_manifests[0].output_paths["sequence_manifest"]
        == (imported_root / "input" / "sequence_manifest.json").resolve()
    )
    assert (
        inspection.snapshot.artifacts["sequence_manifest"].path
        == (imported_root / "input" / "sequence_manifest.json").resolve()
    )


def test_run_bundle_import_rename_collision_policy(tmp_path: Path) -> None:
    artifact_root = _write_fake_run(tmp_path / "source-artifacts" / "demo-run" / "mock")
    bundle_path = tmp_path / "demo-run.prmlrun.tar.gz"
    output_dir = tmp_path / "imported-artifacts"
    (output_dir / "demo-run" / "mock").mkdir(parents=True)
    export_run_bundle(artifact_root, bundle_path)

    result = import_run_bundle(
        bundle_path,
        output_dir=output_dir,
        collision_policy=RunBundleCollisionPolicy.RENAME,
    )

    assert result.artifact_root == (output_dir / "demo-run" / "mock-imported-1").resolve()


def test_run_bundle_import_warns_about_external_metadata_path(tmp_path: Path) -> None:
    artifact_root = _write_fake_run(tmp_path / "source-artifacts" / "demo-run" / "mock")
    external_path = tmp_path / "outside-artifacts" / "source.mov"
    external_path.parent.mkdir()
    external_path.write_text("outside", encoding="utf-8")
    write_json(
        artifact_root / "summary" / "stage_manifests.json",
        [
            StageManifest(
                stage_id=StageKey.SOURCE,
                config_hash="cfg",
                input_fingerprint="input",
                output_paths={"external_source": external_path},
                status=StageStatus.COMPLETED,
            )
        ],
    )
    bundle_path = tmp_path / "demo-run.prmlrun.tar.gz"

    export_run_bundle(artifact_root, bundle_path)
    result = import_run_bundle(bundle_path, output_dir=tmp_path / "imported-artifacts")

    assert result.warnings == [f"Preserved external path outside exported run root: {external_path}"]


def test_run_bundle_import_rejects_unsafe_member_path(tmp_path: Path) -> None:
    bundle_path = tmp_path / "unsafe.prmlrun.tar.gz"
    manifest = b'{"schema_version": 1, "package_version": "test", "exported_run_id": "run", "artifact_label": "run/mock", "original_artifact_root": "/tmp/run/mock", "exported_at_ns": 1, "files": []}'
    with tarfile.open(bundle_path, "w:gz") as archive:
        info = tarfile.TarInfo("manifest.json")
        info.size = len(manifest)
        archive.addfile(info, io.BytesIO(manifest))
        unsafe = b"bad"
        unsafe_info = tarfile.TarInfo("../evil.txt")
        unsafe_info.size = len(unsafe)
        archive.addfile(unsafe_info, io.BytesIO(unsafe))

    with pytest.raises(RuntimeError, match="Unsafe run bundle member path"):
        import_run_bundle(bundle_path, output_dir=tmp_path / ".artifacts")


def _write_fake_run(artifact_root: Path) -> Path:
    sequence_manifest_path = artifact_root / "input" / "sequence_manifest.json"
    sequence_manifest_path.parent.mkdir(parents=True)
    write_json(sequence_manifest_path, SequenceManifest(sequence_id="seq-1"))
    write_json(
        artifact_root / "summary" / "run_summary.json",
        RunSummary(
            run_id="demo-run",
            artifact_root=artifact_root,
            stage_status={StageKey.SOURCE: StageStatus.COMPLETED},
        ),
    )
    write_json(
        artifact_root / "summary" / "stage_manifests.json",
        [
            StageManifest(
                stage_id=StageKey.SOURCE,
                config_hash="cfg",
                input_fingerprint="input",
                output_paths={"sequence_manifest": sequence_manifest_path},
                status=StageStatus.COMPLETED,
            )
        ],
    )
    sink = JsonlEventSink(artifact_root / "summary" / "run-events.jsonl")
    sink.observe(RunSubmitted(event_id="1", run_id="demo-run", ts_ns=1))
    sink.observe(RunStarted(event_id="2", run_id="demo-run", ts_ns=2))
    sink.observe(
        StageCompleted(
            event_id="3",
            run_id="demo-run",
            ts_ns=3,
            stage_key=StageKey.SOURCE,
            outcome=StageOutcome(
                stage_key=StageKey.SOURCE,
                status=StageStatus.COMPLETED,
                config_hash="cfg",
                input_fingerprint="input",
                artifacts={
                    "sequence_manifest": ArtifactRef(
                        path=sequence_manifest_path,
                        kind="json",
                        fingerprint="manifest",
                    )
                },
            ),
        )
    )
    sink.observe(RunCompleted(event_id="4", run_id="demo-run", ts_ns=4))
    return artifact_root.resolve()
