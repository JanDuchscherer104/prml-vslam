"""Focused tests for trajectory-evaluation contracts and persisted semantics."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from prml_vslam.eval.contracts import (
    CloudAlignmentArtifact,
    CloudAlignmentSelection,
    DiscoveredRun,
    EvaluationArtifact,
    MetricStats,
    SelectionSnapshot,
    TrajectoryAlignmentArtifact,
    TrajectoryAlignmentCloudUseStatus,
    TrajectoryAlignmentMode,
    TrajectoryEvaluationSemantics,
    TrajectoryMetricId,
    TrajectorySeries,
)
from prml_vslam.eval.services import CloudAlignmentService, TrajectoryEvaluationService, compute_trajectory_ape_preview
from prml_vslam.eval.stage_alignment.contracts import TrajectoryAlignmentStageInput
from prml_vslam.eval.stage_alignment.runtime import TrajectoryAlignmentRuntime
from prml_vslam.eval.stage_cloud_alignment.contracts import CloudAlignmentStageInput
from prml_vslam.eval.stage_cloud_alignment.runtime import CloudAlignmentRuntime
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
    ReferenceCloudCoordinateStatus,
    ReferenceSource,
    ReferenceTrajectoryRef,
    SequenceManifest,
)
from prml_vslam.utils import PathConfig
from prml_vslam.utils.geometry import load_point_cloud_ply, write_point_cloud_ply, write_tum_trajectory


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
    scale = 2.0
    translation = np.array([0.0, 0.0, 0.0])
    reference_positions = [
        np.array([float(index % 5), float(index // 5), float(index % 3) * 0.1], dtype=np.float64) for index in range(20)
    ]
    timestamps = [float(index) for index in range(len(reference_positions))]
    reference_path = write_tum_trajectory(
        tmp_path / "reference.tum",
        poses=[
            FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=float(p[0]), ty=float(p[1]), tz=float(p[2]))
            for p in reference_positions
        ],
        timestamps=timestamps,
    )
    estimate_path = _write_scaled_trajectory(
        tmp_path / "estimate.tum", reference_positions, timestamps, scale, translation
    )
    cloud_path = tmp_path / "cloud.ply"
    write_point_cloud_ply(cloud_path, np.array(reference_positions, dtype=np.float64))
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


def test_compute_trajectory_alignment_publishes_cloud_despite_warning_diagnostics(tmp_path: Path) -> None:
    reference_positions = [
        np.array([float(index % 5), float(index // 5), float(index % 3)], dtype=np.float64) for index in range(20)
    ]
    estimate_positions = list(reference_positions)
    estimate_positions[-1] = np.array([40.0, -35.0, 20.0], dtype=np.float64)
    timestamps = [float(index) for index in range(len(reference_positions))]
    reference_path = write_tum_trajectory(
        tmp_path / "reference.tum",
        poses=[
            FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=float(p[0]), ty=float(p[1]), tz=float(p[2]))
            for p in reference_positions
        ],
        timestamps=timestamps,
    )
    estimate_path = write_tum_trajectory(
        tmp_path / "estimate.tum",
        poses=[
            FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=float(p[0]), ty=float(p[1]), tz=float(p[2]))
            for p in estimate_positions
        ],
        timestamps=timestamps,
    )
    cloud_path = tmp_path / "cloud.ply"
    write_point_cloud_ply(cloud_path, np.array(reference_positions, dtype=np.float64))
    artifact_root = tmp_path / "run"

    alignment_path, _, aligned_cloud_path = TrajectoryEvaluationService(
        PathConfig(root=tmp_path, artifacts_dir=tmp_path)
    ).compute_trajectory_alignment(
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

    alignment = TrajectoryAlignmentArtifact.model_validate_json(alignment_path.read_text(encoding="utf-8"))
    assert aligned_cloud_path is not None
    assert aligned_cloud_path.exists()
    assert alignment.cloud_use_status is TrajectoryAlignmentCloudUseStatus.ACCEPTED
    assert set(alignment.cloud_warning_reasons) & {"rms_error_too_high", "up_axis_tilt_too_high"}
    assert alignment.cloud_rejection_reasons == []


def test_cloud_alignment_service_writes_distinct_icp_refined_cloud(tmp_path: Path) -> None:
    pytest.importorskip("open3d")
    reference_points = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 2.0, 0.0],
            [0.0, 0.0, 3.0],
            [1.0, 2.0, 0.5],
        ],
        dtype=np.float64,
    )
    offset = np.array([0.04, -0.02, 0.01], dtype=np.float64)
    reference_path = write_point_cloud_ply(tmp_path / "reference.ply", reference_points)
    sim3_path = write_point_cloud_ply(tmp_path / "point_cloud_sim3_aligned.ply", reference_points + offset)

    artifact = CloudAlignmentService().compute_cloud_alignment(
        selection=CloudAlignmentSelection(
            artifact_root=tmp_path / "run",
            reference_cloud_path=reference_path,
            sim3_cloud_path=sim3_path,
            target_frame="advio_gt_world",
            max_correspondence_distance_m=0.25,
        )
    )

    assert artifact.path.exists()
    assert artifact.target_frame == "advio_gt_world"
    assert json.loads(artifact.path.read_text(encoding="utf-8"))["target_frame"] == "advio_gt_world"
    assert artifact.icp_point_cloud_path.exists()
    assert artifact.icp_point_cloud_path.name == "point_cloud_sim3_icp_aligned.ply"
    assert artifact.icp_point_cloud_path != artifact.sim3_point_cloud_path
    refined_points = load_point_cloud_ply(artifact.icp_point_cloud_path)
    assert np.mean(np.linalg.norm(refined_points - reference_points, axis=1)) < np.linalg.norm(offset)


def test_cloud_alignment_runtime_consumes_sim3_aligned_cloud_only(tmp_path: Path) -> None:
    pytest.importorskip("open3d")
    reference_points = np.array(
        [[0.0, 0.0, 0.0], [0.8, 0.1, 0.0], [0.0, 1.1, 0.2], [0.2, 0.0, 1.2]],
        dtype=np.float64,
    )
    reference_path = write_point_cloud_ply(tmp_path / "reference.ply", reference_points)
    sim3_path = write_point_cloud_ply(
        tmp_path / "point_cloud_sim3_aligned.ply",
        reference_points + np.array([0.03, 0.0, 0.0], dtype=np.float64),
    )

    alignment_result = CloudAlignmentRuntime().run_offline(
        input_payload=CloudAlignmentStageInput(
            artifact_root=tmp_path / "run",
            reference_cloud=ArtifactRef(path=reference_path, kind="ply", fingerprint="ref"),
            sim3_point_cloud=ArtifactRef(path=sim3_path, kind="ply", fingerprint="sim3"),
            target_frame="advio_gt_world",
            max_correspondence_distance_m=0.2,
        )
    )

    assert alignment_result.stage_key is StageKey.CLOUD_ALIGNMENT
    assert isinstance(alignment_result.payload, CloudAlignmentArtifact)
    assert alignment_result.payload.target_frame == "advio_gt_world"
    assert "icp_aligned_point_cloud_ply" in alignment_result.outcome.artifacts
    assert alignment_result.outcome.artifacts["sim3_aligned_point_cloud_ply"].path == sim3_path
    assert alignment_result.outcome.artifacts["icp_aligned_point_cloud_ply"].path != sim3_path


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
        reference_trajectories=[
            ReferenceTrajectoryRef(
                source=ReferenceSource.GROUND_TRUTH,
                path=reference_path,
                target_frame="custom_reference_world",
                coordinate_status=ReferenceCloudCoordinateStatus.ALIGNED,
            )
        ]
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
    assert alignment["target_frame"] == "custom_reference_world"
    assert isinstance(result.payload, TrajectoryAlignmentArtifact)
    assert result.payload.scale == pytest.approx(scale, rel=1e-6)


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


def test_cloud_alignment_stage_spec_is_well_formed() -> None:
    from prml_vslam.eval.stage_cloud.spec import CLOUD_EVALUATION_STAGE_SPEC
    from prml_vslam.eval.stage_cloud_alignment.spec import CLOUD_ALIGNMENT_STAGE_SPEC

    assert CLOUD_ALIGNMENT_STAGE_SPEC.stage_key is StageKey.CLOUD_ALIGNMENT
    assert CLOUD_ALIGNMENT_STAGE_SPEC.build_offline_input is not None
    assert CLOUD_ALIGNMENT_STAGE_SPEC.failure_fingerprint is not None
    assert CLOUD_EVALUATION_STAGE_SPEC.stage_key is StageKey.CLOUD_EVALUATION
    assert CLOUD_EVALUATION_STAGE_SPEC.build_offline_input is None
    assert CLOUD_EVALUATION_STAGE_SPEC.failure_fingerprint is None


def test_stage_bundle_align_trajectory_defaults_disabled(tmp_path: Path) -> None:
    config = build_run_config(
        experiment_name="align-traj-default",
        output_dir=tmp_path,
        source_backend=VideoSourceConfig(video_path=tmp_path / "demo.mp4"),
        method=MethodId.VISTA,
    )

    assert config.stages.align_trajectory.enabled is False
    assert config.stages.align_trajectory.stage_key is StageKey.TRAJECTORY_ALIGNMENT


def _planar_yawed_pair(
    *, yaw_deg: float, scale: float, vertical_jitter: float = 0.0
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    angles = np.linspace(0.0, 2.0 * np.pi, 120)
    estimate = np.stack([30.0 * np.cos(angles), vertical_jitter * np.sin(2.0 * angles), 30.0 * np.sin(angles)], axis=1)
    theta = np.radians(yaw_deg)
    rotation_about_up = np.array(
        [[np.cos(theta), 0.0, np.sin(theta)], [0.0, 1.0, 0.0], [-np.sin(theta), 0.0, np.cos(theta)]]
    )
    reference = scale * (estimate @ rotation_about_up.T) + np.array([1.0, 0.3, -0.5])
    return estimate, reference, np.asarray(angles, dtype=np.float64)


def test_yaw_similarity_align_recovers_planar_yaw_without_up_flip() -> None:
    from prml_vslam.eval.services import _sim3_up_axis_tilt_deg
    from prml_vslam.utils.geometry import yaw_similarity_align

    estimate, reference, _ = _planar_yawed_pair(yaw_deg=175.0, scale=1.3)
    scale, rotation, translation = yaw_similarity_align(estimate, reference, up_axis=(0.0, 1.0, 0.0))

    residual = reference - (scale * (estimate @ rotation.T) + translation)
    assert scale == pytest.approx(1.3, abs=1e-6)
    assert np.linalg.det(rotation) == pytest.approx(1.0, abs=1e-9)
    assert _sim3_up_axis_tilt_deg(rotation) == pytest.approx(0.0, abs=1e-9)
    assert np.sqrt(np.mean(np.sum(residual**2, axis=1))) == pytest.approx(0.0, abs=1e-6)


def test_is_gravity_aligned_target_only_for_advio_worlds() -> None:
    from prml_vslam.eval.services import _is_gravity_aligned_target

    assert _is_gravity_aligned_target("advio_gt_world")
    assert _is_gravity_aligned_target("advio_arkit_world")
    assert not _is_gravity_aligned_target("tum_rgbd_world")
    assert not _is_gravity_aligned_target("world")


def test_align_estimate_sim3_gravity_lock_keeps_up_axis_flat() -> None:
    from evo.core.trajectory import PoseTrajectory3D

    from prml_vslam.eval.services import _align_estimate_sim3, _sim3_up_axis_tilt_deg

    estimate_xyz, reference_xyz, timestamps = _planar_yawed_pair(yaw_deg=176.0, scale=1.2, vertical_jitter=0.01)
    quaternions = np.tile(np.array([1.0, 0.0, 0.0, 0.0]), (len(timestamps), 1))
    estimate = PoseTrajectory3D(positions_xyz=estimate_xyz, orientations_quat_wxyz=quaternions, timestamps=timestamps)
    reference = PoseTrajectory3D(positions_xyz=reference_xyz, orientations_quat_wxyz=quaternions, timestamps=timestamps)

    _, advio_alignment = _align_estimate_sim3(
        reference=reference, estimate=estimate, max_diff_s=0.01, target_frame="advio_gt_world"
    )
    _, tum_alignment = _align_estimate_sim3(
        reference=reference, estimate=estimate, max_diff_s=0.01, target_frame="tum_rgbd_world"
    )

    # Gravity-locked ADVIO path fixes the up axis exactly and recovers the planar yaw + scale.
    assert _sim3_up_axis_tilt_deg(np.asarray(advio_alignment.rotation)) == pytest.approx(0.0, abs=1e-6)
    assert advio_alignment.scale == pytest.approx(1.2, abs=1e-2)
    # Non-gravity (TUM) target keeps the full Umeyama solve.
    assert _sim3_up_axis_tilt_deg(np.asarray(tum_alignment.rotation)) is not None
