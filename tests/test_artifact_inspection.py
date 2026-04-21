"""Tests for persisted run artifact inspection helpers."""

from __future__ import annotations

from pathlib import Path

from prml_vslam.interfaces.ingest import PreparedBenchmarkInputs, SequenceManifest
from prml_vslam.interfaces.slam import ArtifactRef, SlamArtifacts
from prml_vslam.pipeline.artifact_inspection import discover_run_artifact_roots, inspect_run_artifacts
from prml_vslam.pipeline.contracts.events import RunCompleted, RunStarted, RunSubmitted, StageCompleted, StageOutcome
from prml_vslam.pipeline.contracts.provenance import RunSummary, StageManifest, StageStatus
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.finalization import write_json
from prml_vslam.pipeline.sinks.jsonl import JsonlEventSink
from prml_vslam.reconstruction.contracts import ReconstructionMetadata, ReconstructionMethodId
from prml_vslam.utils import PathConfig


def test_discover_run_artifact_roots_finds_method_level_roots(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / ".artifacts")
    artifact_root = path_config.artifacts_dir / "demo-run" / "vista"
    write_json(
        artifact_root / "summary" / "run_summary.json",
        RunSummary(run_id="demo-run", artifact_root=artifact_root, stage_status={StageKey.SLAM: StageStatus.COMPLETED}),
    )

    candidates = discover_run_artifact_roots(path_config)

    assert [candidate.artifact_root for candidate in candidates] == [artifact_root.resolve()]
    assert candidates[0].run_id == "demo-run"
    assert candidates[0].label == "demo-run/vista"


def test_inspect_run_artifacts_projects_events_and_typed_metadata(tmp_path: Path) -> None:
    artifact_root = tmp_path / ".artifacts" / "demo-run" / "vista"
    trajectory_path = artifact_root / "slam" / "trajectory.tum"
    point_cloud_path = artifact_root / "slam" / "point_cloud.ply"
    trajectory_path.parent.mkdir(parents=True)
    trajectory_path.write_text("", encoding="utf-8")
    point_cloud_path.write_text("ply\n", encoding="utf-8")

    sequence_manifest = SequenceManifest(sequence_id="demo-sequence")
    benchmark_inputs = PreparedBenchmarkInputs()
    slam = SlamArtifacts(
        trajectory_tum=ArtifactRef(path=trajectory_path, kind="tum", fingerprint="traj"),
        dense_points_ply=ArtifactRef(path=point_cloud_path, kind="ply", fingerprint="cloud"),
    )
    summary = RunSummary(
        run_id="demo-run",
        artifact_root=artifact_root,
        stage_status={StageKey.SLAM: StageStatus.COMPLETED},
    )
    stage_manifests = [
        StageManifest(
            stage_id=StageKey.SLAM,
            config_hash="cfg",
            input_fingerprint="input",
            output_paths={"trajectory_tum": trajectory_path, "dense_points_ply": point_cloud_path},
            status=StageStatus.COMPLETED,
        )
    ]
    reconstruction_metadata = ReconstructionMetadata(
        method_id=ReconstructionMethodId.OPEN3D_TSDF,
        observation_count=2,
        point_count=3,
        target_frame="world",
        voxel_length_m=0.02,
        sdf_trunc_m=0.08,
        depth_trunc_m=3.0,
        depth_scale=1.0,
        integrate_color=False,
    )

    write_json(artifact_root / "input" / "sequence_manifest.json", sequence_manifest)
    write_json(artifact_root / "benchmark" / "inputs.json", benchmark_inputs)
    write_json(artifact_root / "summary" / "run_summary.json", summary)
    write_json(artifact_root / "summary" / "stage_manifests.json", stage_manifests)
    write_json(artifact_root / "reference" / "reconstruction_metadata.json", reconstruction_metadata)

    sink = JsonlEventSink(artifact_root / "summary" / "run-events.jsonl")
    sink.observe(RunSubmitted(event_id="1", run_id="demo-run", ts_ns=1))
    sink.observe(RunStarted(event_id="2", run_id="demo-run", ts_ns=2))
    sink.observe(
        StageCompleted(
            event_id="3",
            run_id="demo-run",
            ts_ns=3,
            stage_key=StageKey.SLAM,
            outcome=StageOutcome(
                stage_key=StageKey.SLAM,
                status=StageStatus.COMPLETED,
                config_hash="cfg",
                input_fingerprint="input",
                artifacts={"trajectory_tum": slam.trajectory_tum},
            ),
            sequence_manifest=sequence_manifest,
            benchmark_inputs=benchmark_inputs,
            slam=slam,
        )
    )
    sink.observe(RunCompleted(event_id="4", run_id="demo-run", ts_ns=4))

    inspection = inspect_run_artifacts(artifact_root)

    assert inspection.snapshot.run_id == "demo-run"
    assert inspection.snapshot.state.value == "completed"
    assert inspection.snapshot.sequence_manifest == sequence_manifest
    assert inspection.snapshot.slam == slam
    assert inspection.summary == summary
    assert inspection.stage_manifests == stage_manifests
    assert inspection.reconstruction_metadata == reconstruction_metadata
    assert inspection.event_count == 4
    assert any(row.name == "trajectory_path" and row.exists for row in inspection.canonical_paths)
    assert any(row.stage_id == "slam" and row.name == "dense_points_ply" for row in inspection.stage_output_paths)
