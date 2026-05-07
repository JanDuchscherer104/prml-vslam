"""Focused tests for trajectory-evaluation contracts and persisted semantics."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from prml_vslam.eval.contracts import (
    DiscoveredRun,
    EvaluationArtifact,
    MetricStats,
    SelectionSnapshot,
    TrajectoryAlignmentMode,
    TrajectoryEvaluationSemantics,
    TrajectoryMetricId,
    TrajectorySeries,
)
from prml_vslam.eval.services import TrajectoryEvaluationService, compute_trajectory_ape_preview
from prml_vslam.eval.stage_alignment.contracts import TrajectoryAlignmentStageInput
from prml_vslam.eval.stage_alignment.runtime import TrajectoryAlignmentRuntime
from prml_vslam.interfaces import FrameTransform
from prml_vslam.interfaces.artifacts import ArtifactRef
from prml_vslam.interfaces.slam import SlamArtifacts
from prml_vslam.methods.stage.backend_config import MethodId
from prml_vslam.pipeline import PipelineMode
from prml_vslam.pipeline.config import build_run_config
from prml_vslam.pipeline.contracts.plan import PlannedSource, RunPlan
from prml_vslam.pipeline.contracts.provenance import StageStatus
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.sources.config import VideoSourceConfig
from prml_vslam.sources.contracts import (
    PreparedBenchmarkInputs,
    ReferenceSource,
    ReferenceTrajectoryRef,
    SequenceManifest,
)
from prml_vslam.utils import PathConfig
from prml_vslam.utils.geometry import write_tum_trajectory


def test_evaluation_artifact_round_trips_explicit_semantics(tmp_path: Path) -> None:
    payload = {
        "title": "Trajectory APE (evo)",
        "matched_pairs": 2,
        "stats": MetricStats(
            rmse=1.0,
            mean=1.0,
            median=1.0,
            std=0.0,
            min=1.0,
            max=1.0,
            sse=2.0,
        ).model_dump(mode="python"),
        "error_timestamps_s": [0.0, 1.0],
        "error_values": [0.5, 1.5],
        "semantics": TrajectoryEvaluationSemantics(
            metric_id=TrajectoryMetricId.APE_TRANSLATION,
            pose_relation="translation_part",
            alignment_mode=TrajectoryAlignmentMode.TIMESTAMP_ASSOCIATED_ONLY,
            sync_max_diff_s=0.01,
        ).model_dump(mode="python"),
    }

    artifact = EvaluationArtifact.from_payload(
        path=tmp_path / "trajectory_metrics.json",
        payload=payload,
        reference_path=tmp_path / "reference.tum",
        estimate_path=tmp_path / "estimate.tum",
        trajectories=(
            TrajectorySeries(
                name="Reference",
                positions_xyz=np.zeros((2, 3), dtype=np.float64),
                timestamps_s=np.array([0.0, 1.0], dtype=np.float64),
            ),
            TrajectorySeries(
                name="Estimate",
                positions_xyz=np.ones((2, 3), dtype=np.float64),
                timestamps_s=np.array([0.0, 1.0], dtype=np.float64),
            ),
        ),
    )

    assert artifact.semantics.metric_id is TrajectoryMetricId.APE_TRANSLATION
    assert artifact.semantics.alignment_mode is TrajectoryAlignmentMode.TIMESTAMP_ASSOCIATED_ONLY
    assert artifact.semantics.candidate_next_metrics == [TrajectoryMetricId.RPE_TRANSLATION]


def test_sim3_umeyama_preview_recovers_metric_scale(tmp_path: Path) -> None:
    translation = np.array([3.0, -1.0, 0.5], dtype=np.float64)
    scale = 2.0
    reference_positions = [
        np.array([0.0, 0.0, 0.0], dtype=np.float64),
        np.array([1.0, 0.0, 0.0], dtype=np.float64),
        np.array([0.0, 1.0, 0.0], dtype=np.float64),
        np.array([1.0, 1.0, 0.0], dtype=np.float64),
    ]
    reference_path = write_tum_trajectory(
        tmp_path / "reference.tum",
        poses=[
            FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=float(point[0]), ty=float(point[1]), tz=float(point[2]))
            for point in reference_positions
        ],
        timestamps=[0.0, 1.0, 2.0, 3.0],
    )
    estimate_path = write_tum_trajectory(
        tmp_path / "estimate.tum",
        poses=[
            FrameTransform(
                qx=0.0,
                qy=0.0,
                qz=0.0,
                qw=1.0,
                tx=float(((point - translation) / scale)[0]),
                ty=float(((point - translation) / scale)[1]),
                tz=float(((point - translation) / scale)[2]),
            )
            for point in reference_positions
        ],
        timestamps=[0.0, 1.0, 2.0, 3.0],
    )

    preview = compute_trajectory_ape_preview(
        reference_path=reference_path,
        estimate_path=estimate_path,
        alignment_mode=TrajectoryAlignmentMode.SIM3_UMEYAMA,
    )

    assert preview.alignment is not None
    assert preview.alignment.scale == pytest.approx(scale)
    assert preview.stats.rmse < 1e-12


def test_trajectory_evaluation_service_computes_pipeline_stage_payload(tmp_path: Path) -> None:
    reference_path = write_tum_trajectory(
        tmp_path / "reference.tum",
        poses=[
            FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
            FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=0.0, tz=0.0),
        ],
        timestamps=[0.0, 1.0],
    )
    estimate_path = write_tum_trajectory(
        tmp_path / "estimate.tum",
        poses=[
            FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
            FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.1, ty=0.0, tz=0.0),
        ],
        timestamps=[0.0, 1.0],
    )
    artifact_root = tmp_path / "run"
    run_config = build_run_config(
        experiment_name="trajectory-stage",
        output_dir=tmp_path,
        source_backend=VideoSourceConfig(video_path=tmp_path / "demo.mp4"),
        method=MethodId.VISTA,
        trajectory_eval_enabled=True,
    )
    plan = RunPlan(
        run_id="trajectory-stage",
        mode=PipelineMode.OFFLINE,
        artifact_root=artifact_root,
        source=PlannedSource(source_id="video", video_path=tmp_path / "demo.mp4"),
    )
    benchmark_inputs = PreparedBenchmarkInputs(
        reference_trajectories=[
            ReferenceTrajectoryRef(source=ReferenceSource.GROUND_TRUTH, path=reference_path),
        ]
    )
    slam = SlamArtifacts(
        trajectory_tum=ArtifactRef(path=estimate_path, kind="tum", fingerprint="estimate"),
    )

    artifact = TrajectoryEvaluationService(
        PathConfig(root=tmp_path, artifacts_dir=tmp_path)
    ).compute_pipeline_evaluation(
        run_config=run_config,
        plan=plan,
        sequence_manifest=SequenceManifest(sequence_id="demo-sequence"),
        benchmark_inputs=benchmark_inputs,
        slam=slam,
    )

    assert artifact is not None
    assert artifact.path == artifact_root / "evaluation" / "trajectory_metrics.json"
    assert artifact.reference_path == reference_path
    assert artifact.estimate_path == estimate_path
    assert artifact.semantics.metric_id is TrajectoryMetricId.APE_TRANSLATION


# ---------------------------------------------------------------------------
# compute_trajectory_alignment
# ---------------------------------------------------------------------------


def _write_scaled_trajectory(
    path: Path,
    reference_positions: list[np.ndarray],
    timestamps: list[float],
    scale: float,
    translation: np.ndarray,
) -> Path:
    return write_tum_trajectory(
        path,
        poses=[
            FrameTransform(
                qx=0.0,
                qy=0.0,
                qz=0.0,
                qw=1.0,
                tx=float(((pt - translation) / scale)[0]),
                ty=float(((pt - translation) / scale)[1]),
                tz=float(((pt - translation) / scale)[2]),
            )
            for pt in reference_positions
        ],
        timestamps=timestamps,
    )


_REFERENCE_POSITIONS = [
    np.array([0.0, 0.0, 0.0]),
    np.array([1.0, 0.0, 0.0]),
    np.array([0.0, 1.0, 0.0]),
    np.array([1.0, 1.0, 0.0]),
]
_TIMESTAMPS = [0.0, 1.0, 2.0, 3.0]


def test_compute_trajectory_alignment_writes_files_and_recovers_scale(tmp_path: Path) -> None:
    scale = 4.2
    translation = np.array([1.0, 2.0, 0.5])
    reference_path = write_tum_trajectory(
        tmp_path / "reference.tum",
        poses=[
            FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=float(p[0]), ty=float(p[1]), tz=float(p[2]))
            for p in _REFERENCE_POSITIONS
        ],
        timestamps=_TIMESTAMPS,
    )
    estimate_path = _write_scaled_trajectory(
        tmp_path / "estimate.tum", _REFERENCE_POSITIONS, _TIMESTAMPS, scale, translation
    )
    artifact_root = tmp_path / "run"
    service = TrajectoryEvaluationService(PathConfig(root=tmp_path, artifacts_dir=tmp_path))

    alignment_path, aligned_estimate_path, aligned_cloud_path = service.compute_trajectory_alignment(
        selection=SelectionSnapshot(
            sequence_slug="seq",
            reference_path=reference_path,
            run=DiscoveredRun(artifact_root=artifact_root, estimate_path=estimate_path, label="test"),
        )
    )

    assert alignment_path.exists()
    assert aligned_estimate_path.exists()
    assert aligned_cloud_path is None
    alignment = json.loads(alignment_path.read_text())
    assert alignment["scale"] == pytest.approx(scale, rel=1e-6)


def test_compute_trajectory_alignment_writes_aligned_point_cloud(tmp_path: Path) -> None:
    from prml_vslam.utils.geometry import write_point_cloud_ply

    scale = 2.0
    translation = np.array([0.0, 0.0, 0.0])
    reference_path = write_tum_trajectory(
        tmp_path / "reference.tum",
        poses=[
            FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=float(p[0]), ty=float(p[1]), tz=float(p[2]))
            for p in _REFERENCE_POSITIONS
        ],
        timestamps=_TIMESTAMPS,
    )
    estimate_path = _write_scaled_trajectory(
        tmp_path / "estimate.tum", _REFERENCE_POSITIONS, _TIMESTAMPS, scale, translation
    )
    cloud_path = tmp_path / "cloud.ply"
    write_point_cloud_ply(cloud_path, np.array(_REFERENCE_POSITIONS, dtype=np.float64))
    artifact_root = tmp_path / "run"
    service = TrajectoryEvaluationService(PathConfig(root=tmp_path, artifacts_dir=tmp_path))

    _, _, aligned_cloud_path = service.compute_trajectory_alignment(
        selection=SelectionSnapshot(
            sequence_slug="seq",
            reference_path=reference_path,
            run=DiscoveredRun(
                artifact_root=artifact_root,
                estimate_path=estimate_path,
                point_cloud_path=cloud_path,
                label="test",
            ),
        )
    )

    assert aligned_cloud_path is not None
    assert aligned_cloud_path.exists()


def test_compute_trajectory_alignment_raises_on_missing_reference(tmp_path: Path) -> None:
    estimate_path = write_tum_trajectory(
        tmp_path / "estimate.tum",
        poses=[FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0)],
        timestamps=[0.0],
    )
    service = TrajectoryEvaluationService(PathConfig(root=tmp_path, artifacts_dir=tmp_path))

    with pytest.raises(FileNotFoundError, match="missing a TUM reference trajectory"):
        service.compute_trajectory_alignment(
            selection=SelectionSnapshot(
                sequence_slug="seq",
                reference_path=None,
                run=DiscoveredRun(artifact_root=tmp_path / "run", estimate_path=estimate_path, label="test"),
            )
        )


# ---------------------------------------------------------------------------
# TrajectoryAlignmentRuntime
# ---------------------------------------------------------------------------


def test_trajectory_alignment_runtime_produces_aligned_artifacts(tmp_path: Path) -> None:
    scale = 3.0
    translation = np.array([0.5, -0.5, 0.0])
    reference_path = write_tum_trajectory(
        tmp_path / "reference.tum",
        poses=[
            FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=float(p[0]), ty=float(p[1]), tz=float(p[2]))
            for p in _REFERENCE_POSITIONS
        ],
        timestamps=_TIMESTAMPS,
    )
    estimate_path = _write_scaled_trajectory(
        tmp_path / "estimate.tum", _REFERENCE_POSITIONS, _TIMESTAMPS, scale, translation
    )
    artifact_root = tmp_path / "run"
    benchmark_inputs = PreparedBenchmarkInputs(
        reference_trajectories=[ReferenceTrajectoryRef(source=ReferenceSource.GROUND_TRUTH, path=reference_path)]
    )
    slam = SlamArtifacts(trajectory_tum=ArtifactRef(path=estimate_path, kind="tum", fingerprint="est"))
    input_payload = TrajectoryAlignmentStageInput(
        artifact_root=artifact_root,
        sequence_manifest=SequenceManifest(sequence_id="seq"),
        benchmark_inputs=benchmark_inputs,
        slam=slam,
    )

    runtime = TrajectoryAlignmentRuntime()
    result = runtime.run_offline(input_payload)

    assert result.stage_key is StageKey.TRAJECTORY_ALIGNMENT
    assert result.outcome.status is StageStatus.COMPLETED
    assert "aligned_estimate_tum" in result.outcome.artifacts
    assert "trajectory_alignment" in result.outcome.artifacts
    assert result.outcome.artifacts["aligned_estimate_tum"].path.exists()
    alignment = json.loads(result.outcome.artifacts["trajectory_alignment"].path.read_text())
    assert alignment["scale"] == pytest.approx(scale, rel=1e-6)


def test_trajectory_alignment_runtime_fails_without_benchmark_inputs(tmp_path: Path) -> None:
    estimate_path = write_tum_trajectory(
        tmp_path / "estimate.tum",
        poses=[FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0)],
        timestamps=[0.0],
    )
    slam = SlamArtifacts(trajectory_tum=ArtifactRef(path=estimate_path, kind="tum", fingerprint="est"))
    input_payload = TrajectoryAlignmentStageInput(
        artifact_root=tmp_path / "run",
        sequence_manifest=SequenceManifest(sequence_id="seq"),
        benchmark_inputs=None,
        slam=slam,
    )

    runtime = TrajectoryAlignmentRuntime()

    with pytest.raises(RuntimeError, match="benchmark inputs"):
        runtime.run_offline(input_payload)

    assert runtime.status().lifecycle_state is StageStatus.FAILED


def test_trajectory_alignment_stage_spec_is_well_formed() -> None:
    from prml_vslam.eval.stage_alignment.spec import TRAJECTORY_ALIGNMENT_STAGE_SPEC

    assert TRAJECTORY_ALIGNMENT_STAGE_SPEC.stage_key is StageKey.TRAJECTORY_ALIGNMENT
    assert TRAJECTORY_ALIGNMENT_STAGE_SPEC.build_offline_input is not None
    assert TRAJECTORY_ALIGNMENT_STAGE_SPEC.failure_fingerprint is not None


def test_stage_bundle_align_trajectory_defaults_disabled(tmp_path: Path) -> None:
    config = build_run_config(
        experiment_name="align-traj-default",
        output_dir=tmp_path,
        source_backend=VideoSourceConfig(video_path=tmp_path / "demo.mp4"),
        method=MethodId.VISTA,
    )

    assert config.stages.align_trajectory.enabled is False
    assert config.stages.align_trajectory.stage_key is StageKey.TRAJECTORY_ALIGNMENT
