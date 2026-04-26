"""Focused tests for trajectory-evaluation contracts and persisted semantics."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from prml_vslam.eval.contracts import (
    EvaluationArtifact,
    MetricStats,
    TrajectoryAlignmentMode,
    TrajectoryEvaluationSemantics,
    TrajectoryMetricId,
    TrajectorySeries,
)
from prml_vslam.eval.services import TrajectoryEvaluationService, compute_trajectory_ape_preview
from prml_vslam.interfaces import FrameTransform
from prml_vslam.interfaces.artifacts import ArtifactRef
from prml_vslam.interfaces.slam import SlamArtifacts
from prml_vslam.methods.stage.backend_config import MethodId
from prml_vslam.pipeline import PipelineMode
from prml_vslam.pipeline.config import build_run_config
from prml_vslam.pipeline.contracts.plan import PlannedSource, RunPlan
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
