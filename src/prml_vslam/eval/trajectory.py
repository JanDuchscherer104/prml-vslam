"""Trajectory evaluation utilities built on top of `evo`."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field

from prml_vslam.utils import BaseConfig


class PoseRelationId(StrEnum):
    """Subset of `evo` pose relations exposed through the CLI."""

    TRANSLATION_PART = "translation_part"
    FULL_TRANSFORMATION = "full_transformation"
    ROTATION_PART = "rotation_part"
    ROTATION_ANGLE_DEG = "rotation_angle_deg"


class TrajectoryEvaluationConfig(BaseConfig):
    """Configuration for evaluating two TUM trajectories with `evo`."""

    reference_path: Path
    """Reference trajectory in TUM format."""

    estimate_path: Path
    """Estimated trajectory in TUM format."""

    pose_relation: PoseRelationId = PoseRelationId.TRANSLATION_PART
    """Pose relation reported by `evo`."""

    align: bool = True
    """Whether to apply rigid alignment before metric computation."""

    correct_scale: bool = True
    """Whether to allow Sim(3)-style scale correction."""

    max_diff_s: float = Field(default=0.02, gt=0.0)
    """Maximum timestamp association difference in seconds."""

    estimate_offset_s: float = 0.0
    """Optional timestamp offset applied to the estimate before association."""


class TrajectoryEvaluationResult(BaseModel):
    """Repo-owned summary of one `evo` trajectory evaluation."""

    reference_path: Path
    """Reference trajectory path."""

    estimate_path: Path
    """Estimated trajectory path."""

    pose_relation: PoseRelationId
    """Pose relation reported by `evo`."""

    align: bool
    """Whether rigid alignment was enabled."""

    correct_scale: bool
    """Whether scale correction was enabled."""

    max_diff_s: float
    """Timestamp association threshold in seconds."""

    matching_pairs: int
    """Number of associated poses used for evaluation."""

    stats: dict[str, float]
    """Scalar metric outputs from `evo`."""


def evaluate_tum_trajectories(config: TrajectoryEvaluationConfig) -> TrajectoryEvaluationResult:
    """Evaluate two TUM trajectories with `evo` and return structured stats."""
    try:
        from evo.core.metrics import PoseRelation
        from evo.core.sync import associate_trajectories
        from evo.main_ape import ape
        from evo.tools import file_interface
    except ImportError as exc:  # pragma: no cover - depends on optional extra
        msg = "Trajectory evaluation requires the eval extra. Install with `uv sync --extra eval`."
        raise RuntimeError(msg) from exc

    relation = PoseRelation[config.pose_relation.value]
    trajectory_ref = file_interface.read_tum_trajectory_file(config.reference_path)
    trajectory_est = file_interface.read_tum_trajectory_file(config.estimate_path)
    associated_ref, associated_est = associate_trajectories(
        trajectory_ref,
        trajectory_est,
        max_diff=config.max_diff_s,
        offset_2=config.estimate_offset_s,
        first_name="reference trajectory",
        snd_name="estimated trajectory",
    )
    result = ape(
        associated_ref,
        associated_est,
        relation,
        align=config.align,
        correct_scale=config.correct_scale,
        ref_name=config.reference_path.name,
        est_name=config.estimate_path.name,
    )
    return TrajectoryEvaluationResult(
        reference_path=config.reference_path,
        estimate_path=config.estimate_path,
        pose_relation=config.pose_relation,
        align=config.align,
        correct_scale=config.correct_scale,
        max_diff_s=config.max_diff_s,
        matching_pairs=associated_ref.num_poses,
        stats={name: float(value) for name, value in result.stats.items()},
    )


def write_evaluation_result(result: TrajectoryEvaluationResult, output_path: Path) -> Path:
    """Persist a trajectory evaluation result as JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return output_path
