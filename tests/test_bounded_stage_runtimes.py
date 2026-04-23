"""Tests for WP-05 bounded stage runtime adapters."""

from __future__ import annotations

from pathlib import Path

import pytest

from prml_vslam.eval.contracts import (
    EvaluationArtifact,
    MetricStats,
    TrajectoryEvaluationSemantics,
)
from prml_vslam.interfaces.alignment import GroundAlignmentMetadata
from prml_vslam.interfaces.ingest import PreparedBenchmarkInputs, SequenceManifest
from prml_vslam.interfaces.rgbd import RgbdObservationSequenceRef
from prml_vslam.interfaces.slam import SlamArtifacts
from prml_vslam.pipeline import PipelineMode, RunRequest
from prml_vslam.pipeline.contracts.events import StageOutcome
from prml_vslam.pipeline.contracts.plan import RunPlan, RunPlanStage
from prml_vslam.pipeline.contracts.provenance import ArtifactRef, StageStatus
from prml_vslam.pipeline.contracts.request import SlamStageConfig, VideoSourceSpec
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.contracts import VisualizationIntent
from prml_vslam.pipeline.stages.ground_alignment import GroundAlignmentRuntime, GroundAlignmentRuntimeInput
from prml_vslam.pipeline.stages.reconstruction import ReconstructionRuntime, ReconstructionRuntimeInput
from prml_vslam.pipeline.stages.reconstruction.visualization import (
    ROLE_RECONSTRUCTION_MESH,
    ROLE_RECONSTRUCTION_POINT_CLOUD,
)
from prml_vslam.pipeline.stages.summary import SummaryRuntime, SummaryRuntimeInput
from prml_vslam.pipeline.stages.trajectory_eval import (
    TrajectoryEvaluationRuntime,
    TrajectoryEvaluationRuntimeInput,
)
from prml_vslam.reconstruction import ReconstructionArtifacts
from prml_vslam.utils import BaseData, RunArtifactPaths


def test_ground_alignment_runtime_returns_stage_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, plan, run_paths = _request_plan_paths(tmp_path, alignment={"ground": {"enabled": True}})
    slam = _slam_artifacts(tmp_path)

    class FakeGroundAlignmentService:
        def __init__(self, *, config) -> None:
            self.config = config

        def estimate_from_slam_artifacts(self, *, slam: SlamArtifacts) -> GroundAlignmentMetadata:
            assert slam.dense_points_ply is not None
            return GroundAlignmentMetadata(
                applied=False,
                confidence=0.25,
                point_cloud_source="dense_points_ply",
                candidate_count=3,
                skip_reason="No reliable dominant ground plane found.",
            )

    monkeypatch.setattr(
        "prml_vslam.pipeline.stages.ground_alignment.runtime.GroundAlignmentService",
        FakeGroundAlignmentService,
    )

    result = GroundAlignmentRuntime().run_offline(
        GroundAlignmentRuntimeInput(request=request, run_paths=run_paths, slam=slam)
    )

    assert result.stage_key is StageKey.GRAVITY_ALIGNMENT
    assert result.outcome.status is StageStatus.SKIPPED
    assert result.final_runtime_status.lifecycle_state is StageStatus.SKIPPED
    assert isinstance(result.payload, GroundAlignmentMetadata)
    assert result.outcome.artifacts["ground_alignment"].path == run_paths.ground_alignment_path
    assert run_paths.ground_alignment_path.exists()


def test_trajectory_evaluation_runtime_returns_eval_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, plan, _run_paths = _request_plan_paths(tmp_path, benchmark={"trajectory": {"enabled": True}})
    artifact = _evaluation_artifact(tmp_path)
    calls: list[dict[str, object]] = []

    class FakeTrajectoryEvaluationService:
        def __init__(self, path_config) -> None:
            self.path_config = path_config

        def compute_pipeline_evaluation(self, **kwargs) -> EvaluationArtifact:
            calls.append(kwargs)
            return artifact

    monkeypatch.setattr(
        "prml_vslam.pipeline.stages.trajectory_eval.runtime.TrajectoryEvaluationService",
        FakeTrajectoryEvaluationService,
    )

    result = TrajectoryEvaluationRuntime().run_offline(
        TrajectoryEvaluationRuntimeInput(
            request=request,
            plan=plan,
            sequence_manifest=SequenceManifest(sequence_id="seq-1"),
            benchmark_inputs=PreparedBenchmarkInputs(),
            slam=_slam_artifacts(tmp_path),
        )
    )

    assert calls
    assert result.stage_key is StageKey.TRAJECTORY_EVALUATION
    assert result.payload == artifact
    assert result.outcome.status is StageStatus.COMPLETED
    assert result.final_runtime_status.lifecycle_state is StageStatus.COMPLETED
    assert set(result.outcome.artifacts) == {"trajectory_metrics", "reference_tum", "estimate_tum"}


def test_reconstruction_runtime_returns_reconstruction_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, _plan, run_paths = _request_plan_paths(
        tmp_path,
        benchmark={"reference": {"enabled": True, "extract_mesh": True}},
    )

    class FakeBackendConfig(BaseData):
        extract_mesh: bool = False

        def setup_target(self):
            return FakeBackend()

    class FakeBackend:
        def run_sequence(self, observations, *, backend_config, artifact_root: Path) -> ReconstructionArtifacts:
            del observations, backend_config
            artifact_root.mkdir(parents=True, exist_ok=True)
            cloud = artifact_root / "reference_cloud.ply"
            metadata = artifact_root / "reconstruction_metadata.json"
            mesh = artifact_root / "reference_mesh.ply"
            cloud.write_text("ply\n", encoding="utf-8")
            metadata.write_text("{}\n", encoding="utf-8")
            mesh.write_text("ply\n", encoding="utf-8")
            return ReconstructionArtifacts(reference_cloud_path=cloud, metadata_path=metadata, mesh_path=mesh)

    class FakeRgbdObservationSource:
        def __init__(self, sequence_ref: RgbdObservationSequenceRef) -> None:
            self.sequence_ref = sequence_ref

        def iter_observations(self):
            return iter(())

    monkeypatch.setattr(
        "prml_vslam.pipeline.stages.reconstruction.runtime.Open3dTsdfBackendConfig",
        FakeBackendConfig,
    )
    monkeypatch.setattr(
        "prml_vslam.pipeline.stages.reconstruction.runtime.FileRgbdObservationSource",
        FakeRgbdObservationSource,
    )

    runtime = ReconstructionRuntime()
    result = runtime.run_offline(
        ReconstructionRuntimeInput(
            request=request,
            run_paths=run_paths,
            benchmark_inputs=_rgbd_benchmark_inputs(tmp_path),
        )
    )

    assert result.stage_key is StageKey.REFERENCE_RECONSTRUCTION
    assert result.outcome.status is StageStatus.COMPLETED
    assert result.final_runtime_status.lifecycle_state is StageStatus.COMPLETED
    assert isinstance(result.payload, ReconstructionArtifacts)
    assert set(result.outcome.artifacts) == {
        "reference_cloud",
        "reconstruction_metadata",
        "reference_mesh",
    }
    updates = runtime.drain_runtime_updates()
    assert len(updates) == 1
    assert updates[0].stage_key is StageKey.REFERENCE_RECONSTRUCTION
    assert [(item.intent, item.role) for item in updates[0].visualizations] == [
        (VisualizationIntent.POINT_CLOUD, ROLE_RECONSTRUCTION_POINT_CLOUD),
        (VisualizationIntent.MESH, ROLE_RECONSTRUCTION_MESH),
    ]
    assert updates[0].runtime_status == result.final_runtime_status
    assert all(item.frame_index is None for item in updates[0].visualizations)
    assert all(item.keyframe_index is None for item in updates[0].visualizations)
    assert runtime.drain_runtime_updates() == []


def test_reconstruction_runtime_omits_mesh_visualization_when_mesh_artifact_absent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, _plan, run_paths = _request_plan_paths(
        tmp_path,
        benchmark={"reference": {"enabled": True, "extract_mesh": False}},
    )

    class FakeBackendConfig(BaseData):
        extract_mesh: bool = False

        def setup_target(self):
            return FakeBackend()

    class FakeBackend:
        def run_sequence(self, observations, *, backend_config, artifact_root: Path) -> ReconstructionArtifacts:
            del observations, backend_config
            artifact_root.mkdir(parents=True, exist_ok=True)
            cloud = artifact_root / "reference_cloud.ply"
            metadata = artifact_root / "reconstruction_metadata.json"
            cloud.write_text("ply\n", encoding="utf-8")
            metadata.write_text("{}\n", encoding="utf-8")
            return ReconstructionArtifacts(reference_cloud_path=cloud, metadata_path=metadata, mesh_path=None)

    class FakeRgbdObservationSource:
        def __init__(self, sequence_ref: RgbdObservationSequenceRef) -> None:
            self.sequence_ref = sequence_ref

        def iter_observations(self):
            return iter(())

    monkeypatch.setattr(
        "prml_vslam.pipeline.stages.reconstruction.runtime.Open3dTsdfBackendConfig",
        FakeBackendConfig,
    )
    monkeypatch.setattr(
        "prml_vslam.pipeline.stages.reconstruction.runtime.FileRgbdObservationSource",
        FakeRgbdObservationSource,
    )

    runtime = ReconstructionRuntime()
    result = runtime.run_offline(
        ReconstructionRuntimeInput(
            request=request,
            run_paths=run_paths,
            benchmark_inputs=_rgbd_benchmark_inputs(tmp_path),
        )
    )

    assert set(result.outcome.artifacts) == {"reference_cloud", "reconstruction_metadata"}
    updates = runtime.drain_runtime_updates()
    assert len(updates) == 1
    assert [(item.intent, item.role) for item in updates[0].visualizations] == [
        (VisualizationIntent.POINT_CLOUD, ROLE_RECONSTRUCTION_POINT_CLOUD),
    ]


def test_summary_runtime_returns_run_summary_and_retains_manifests(tmp_path: Path) -> None:
    request, plan, run_paths = _request_plan_paths(tmp_path)
    prior_outcome = StageOutcome(
        stage_key=StageKey.SLAM,
        status=StageStatus.COMPLETED,
        config_hash="slam-config",
        input_fingerprint="slam-input",
        artifacts={"trajectory_tum": ArtifactRef(path=tmp_path / "trajectory.tum", kind="tum", fingerprint="traj")},
    )

    runtime = SummaryRuntime()
    result = runtime.run_offline(
        SummaryRuntimeInput(
            request=request,
            plan=plan,
            run_paths=run_paths,
            stage_outcomes=[prior_outcome],
        )
    )

    assert result.stage_key is StageKey.SUMMARY
    assert result.outcome.status is StageStatus.COMPLETED
    assert result.final_runtime_status.lifecycle_state is StageStatus.COMPLETED
    assert result.payload is not None
    assert result.payload.stage_status == {StageKey.SLAM: StageStatus.COMPLETED}
    assert runtime.stage_manifests[0].stage_id is StageKey.SLAM
    assert run_paths.summary_path.exists()
    assert run_paths.stage_manifests_path.exists()


def _request_plan_paths(
    tmp_path: Path,
    *,
    benchmark: dict[str, object] | None = None,
    alignment: dict[str, object] | None = None,
) -> tuple[RunRequest, RunPlan, RunArtifactPaths]:
    request = RunRequest(
        experiment_name="bounded-runtime",
        mode=PipelineMode.OFFLINE,
        output_dir=tmp_path / ".artifacts",
        source=VideoSourceSpec(video_path=Path("captures/demo.mp4")),
        slam=SlamStageConfig(backend={"kind": "mock"}),
        benchmark={} if benchmark is None else benchmark,
        alignment={} if alignment is None else alignment,
    )
    artifact_root = tmp_path / ".artifacts" / "bounded-runtime"
    plan = RunPlan(
        run_id="bounded-runtime",
        mode=PipelineMode.OFFLINE,
        artifact_root=artifact_root,
        source=request.source,
        stages=[RunPlanStage(key=StageKey.SLAM), RunPlanStage(key=StageKey.SUMMARY)],
    )
    return request, plan, RunArtifactPaths.build(artifact_root)


def _slam_artifacts(tmp_path: Path) -> SlamArtifacts:
    return SlamArtifacts(
        trajectory_tum=ArtifactRef(path=tmp_path / "trajectory.tum", kind="tum", fingerprint="traj"),
        dense_points_ply=ArtifactRef(path=tmp_path / "dense.ply", kind="ply", fingerprint="dense"),
    )


def _evaluation_artifact(tmp_path: Path) -> EvaluationArtifact:
    return EvaluationArtifact(
        path=tmp_path / "trajectory_metrics.json",
        title="Trajectory APE (evo)",
        matched_pairs=1,
        stats=MetricStats(rmse=0.0, mean=0.0, median=0.0, std=0.0, min=0.0, max=0.0, sse=0.0),
        reference_path=tmp_path / "reference.tum",
        estimate_path=tmp_path / "estimate.tum",
        semantics=TrajectoryEvaluationSemantics(sync_max_diff_s=0.01),
    )


def _rgbd_benchmark_inputs(tmp_path: Path) -> PreparedBenchmarkInputs:
    return PreparedBenchmarkInputs(
        rgbd_observation_sequences=[
            RgbdObservationSequenceRef(
                source_id="test",
                sequence_id="test-sequence",
                index_path=tmp_path / "rgbd_observations.json",
                payload_root=tmp_path,
                observation_count=2,
            )
        ]
    )
