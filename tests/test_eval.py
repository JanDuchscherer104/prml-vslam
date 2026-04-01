"""Tests for trajectory evaluation helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from prml_vslam.eval import (
    PoseRelationId,
    TrajectoryEvaluationConfig,
    evaluate_tum_trajectories,
    write_evaluation_result,
)


def test_evaluate_tum_trajectories_and_write_result(tmp_path: Path) -> None:
    pytest.importorskip("evo")

    reference_path = tmp_path / "ref.tum"
    estimate_path = tmp_path / "est.tum"
    output_path = tmp_path / "evaluation.json"

    reference_path.write_text(
        "# timestamp tx ty tz qx qy qz qw\n0.0 0 0 0 0 0 0 1\n1.0 1 0 0 0 0 0 1\n",
        encoding="utf-8",
    )
    estimate_path.write_text(
        "# timestamp tx ty tz qx qy qz qw\n0.0 0 0 0 0 0 0 1\n1.0 1.1 0 0 0 0 0 1\n",
        encoding="utf-8",
    )

    result = evaluate_tum_trajectories(
        TrajectoryEvaluationConfig(
            reference_path=reference_path,
            estimate_path=estimate_path,
            pose_relation=PoseRelationId.TRANSLATION_PART,
            align=False,
            correct_scale=False,
            max_diff_s=0.05,
        )
    )

    assert result.matching_pairs == 2
    assert "rmse" in result.stats

    write_evaluation_result(result, output_path)
    assert output_path.exists()
