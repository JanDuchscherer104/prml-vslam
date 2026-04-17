"""Focused tests for trajectory-evaluation contracts and persisted semantics."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from prml_vslam.eval.contracts import (
    EvaluationArtifact,
    MetricStats,
    TrajectoryAlignmentMode,
    TrajectoryEvaluationSemantics,
    TrajectoryMetricId,
    TrajectorySeries,
)


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
