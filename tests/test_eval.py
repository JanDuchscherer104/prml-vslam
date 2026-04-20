"""Focused tests for trajectory-evaluation contracts and persisted semantics."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from prml_vslam.benchmark import ReferenceSource
from prml_vslam.eval.contracts import (
    EvaluationArtifact,
    MetricStats,
    TrajectoryAlignmentMode,
    TrajectoryEvaluationSemantics,
    TrajectoryMetricId,
    TrajectorySeries,
)
from prml_vslam.eval.services import TrajectoryEvaluationService
from prml_vslam.interfaces import FrameTransform
from prml_vslam.interfaces.ingest import PreparedBenchmarkInputs, ReferenceTrajectoryRef, SequenceManifest
from prml_vslam.interfaces.slam import ArtifactRef, SlamArtifacts
from prml_vslam.pipeline import PipelineMode, RunRequest
from prml_vslam.pipeline.contracts.plan import RunPlan
from prml_vslam.pipeline.contracts.request import SlamStageConfig, VideoSourceSpec
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
    request = RunRequest(
        experiment_name="trajectory-stage",
        mode=PipelineMode.OFFLINE,
        output_dir=tmp_path,
        source=VideoSourceSpec(video_path=tmp_path / "demo.mp4"),
        slam=SlamStageConfig(backend={"method_id": "mock"}),
        benchmark={"trajectory": {"enabled": True, "baseline_source": ReferenceSource.GROUND_TRUTH}},
    )
    plan = RunPlan(
        run_id="trajectory-stage",
        mode=PipelineMode.OFFLINE,
        artifact_root=artifact_root,
        source=request.source,
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
        request=request,
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
