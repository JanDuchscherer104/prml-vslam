"""Trajectory evaluation service for pipeline-driven APE/RPE computation and persistence."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from evo.core import metrics, sync
from evo.tools import file_interface

from prml_vslam.align.trajectory_sim3 import align_estimate_sim3, sim3_up_axis_tilt_deg, trajectory_supports_sim3
from prml_vslam.align.trajectory_sim3.contracts import TrajectoryAlignmentArtifact
from prml_vslam.eval.dataset_aggregation import metric_rows_to_frame
from prml_vslam.eval.services.preview import (
    _EVO_ASSOCIATION_MAX_DIFF_S,
    _TrajectoryMetricPreview,
    compute_trajectory_ape_preview,
    compute_trajectory_rpe_preview,
)
from prml_vslam.eval.trajectory_contracts import (
    DiscoveredRun,
    SelectionSnapshot,
    SkippedMetricRecord,
    TrajectoryEvaluationCase,
    TrajectoryEvaluationManifest,
    TrajectoryMetricResultRow,
    stable_run_id,
)
from prml_vslam.interfaces.slam import SlamArtifacts
from prml_vslam.sources.contracts import PreparedBenchmarkInputs, ReferenceTrajectoryRef, SequenceManifest
from prml_vslam.sources.datasets.contracts import DatasetId
from prml_vslam.utils.geometry import (
    load_point_cloud_ply_with_colors,
    load_tum_trajectory,
    write_point_cloud_ply,
)
from prml_vslam.utils.path_config import PathConfig

if TYPE_CHECKING:
    from prml_vslam.pipeline.config import RunConfig
    from prml_vslam.pipeline.contracts.plan import RunPlan

_SIM3_CLOUD_MIN_MATCHED_PAIRS = 20
_SIM3_CLOUD_MAX_RMS_ERROR_M = 2.0
_SIM3_CLOUD_MAX_UP_AXIS_TILT_DEG = 15.0


@dataclass(frozen=True, slots=True)
class _MetricSpec:
    family: str
    pose_relation: metrics.PoseRelation
    delta: float | None = None
    delta_unit_enum: metrics.Unit | None = None
    delta_unit: str | None = None


_METRIC_SPECS: list[_MetricSpec] = [
    _MetricSpec("ape", metrics.PoseRelation.translation_part),
    _MetricSpec("ape", metrics.PoseRelation.rotation_angle_deg),
    _MetricSpec("rpe", metrics.PoseRelation.translation_part, 1.0, metrics.Unit.meters, "meters"),
    _MetricSpec("rpe", metrics.PoseRelation.rotation_angle_deg, 1.0, metrics.Unit.meters, "meters"),
]

_POSE_RELATION_UNIT: dict[metrics.PoseRelation, str] = {
    metrics.PoseRelation.translation_part: "m",
    metrics.PoseRelation.rotation_angle_deg: "deg",
}


@dataclass(slots=True)
class _TrajectoryEvaluationCandidate:
    """Internal candidate metadata used to persist multi-baseline metrics."""

    path: Path
    source: str
    coordinate_status: str
    method_id: str | None
    method_label: str


class TrajectoryEvaluationService:
    """Discover runs and compute or reload explicit `evo` trajectory metrics.

    The service is the eval-owned implementation behind metrics pages and the
    trajectory-evaluation pipeline stage. It consumes normalized TUM
    trajectories and prepared references, persists metric semantics, and keeps
    evaluation execution explicit rather than tied to app rerenders.
    """

    def __init__(self, path_config: PathConfig) -> None:
        self.path_config = path_config

    def compute_trajectory_alignment(
        self,
        *,
        selection: SelectionSnapshot,
    ) -> tuple[Path, Path, Path | None]:
        """Compute and persist the Sim(3) alignment without running APE metrics.

        Returns ``(alignment_path, aligned_estimate_path, aligned_point_cloud_path)``
        where the last element is ``None`` when no dense-cloud input is provided
        or the Sim(3) transform is not finite enough to apply to the cloud.
        """
        reference_path = selection.reference_path
        if reference_path is None:
            raise FileNotFoundError("The selected dataset slice is missing a TUM reference trajectory.")

        reference_trajectory = load_tum_trajectory(reference_path)
        estimate_trajectory = load_tum_trajectory(selection.run.estimate_path)
        try:
            associated_reference, associated_estimate = sync.associate_trajectories(
                reference_trajectory,
                estimate_trajectory,
                max_diff=_EVO_ASSOCIATION_MAX_DIFF_S,
            )
        except sync.SyncException as exc:
            raise ValueError(
                f"No matching trajectory timestamps found for Sim(3) alignment (max_diff={_EVO_ASSOCIATION_MAX_DIFF_S:.3f}s)."
            ) from exc

        if not trajectory_supports_sim3(associated_reference, associated_estimate):
            raise ValueError("Trajectory lacks sufficient geometric spread for Sim(3) alignment.")

        aligned_estimate, alignment = align_estimate_sim3(
            reference=associated_reference,
            estimate=associated_estimate,
            max_diff_s=_EVO_ASSOCIATION_MAX_DIFF_S,
            target_frame=selection.target_frame or "world",
            source_frame=_method_world_frame(selection.run.method),
            reference_source=selection.reference_source or "reference",
            method_id=selection.run.method,
            method_label=selection.run.label,
        )

        run_root = selection.run.artifact_root
        aligned_estimate_path = self.aligned_estimate_path(run_root)
        aligned_estimate_path.parent.mkdir(parents=True, exist_ok=True)
        file_interface.write_tum_trajectory_file(aligned_estimate_path, aligned_estimate)

        aligned_point_cloud_path = None
        alignment = _apply_sim3_cloud_use_policy(
            alignment,
            cloud_input_present=selection.run.point_cloud_path is not None,
        )
        if selection.run.point_cloud_path is not None and not alignment.cloud_rejection_reasons:
            aligned_point_cloud_path = self.aligned_point_cloud_path(run_root)
            _write_aligned_point_cloud(
                source_path=selection.run.point_cloud_path,
                output_path=aligned_point_cloud_path,
                alignment=alignment,
            )

        alignment_path = self.alignment_path(run_root)
        alignment_path.parent.mkdir(parents=True, exist_ok=True)
        alignment_path.write_text(
            json.dumps(alignment.model_dump(mode="json"), indent=2, sort_keys=True),
            encoding="utf-8",
        )

        return alignment_path, aligned_estimate_path, aligned_point_cloud_path

    def compute_evaluation(
        self,
        *,
        selection: SelectionSnapshot,
        candidate_trajectories: list[ReferenceTrajectoryRef] | None = None,
    ) -> TrajectoryEvaluationManifest:
        """Compute and persist trajectory APE/RPE metrics via the `evo` Python API.

        The persisted manifest and long-form metric table include translation
        and rotation APE/RPE rows for every candidate whose metric can be
        computed. The primary run estimate must produce translation APE.
        """
        reference_path = selection.reference_path
        if reference_path is None:
            raise FileNotFoundError("The selected dataset slice is missing a TUM reference trajectory.")

        return self._persist_metric_manifest(
            selection=selection,
            reference_path=reference_path,
            reference_source=selection.reference_source or "ground_truth",
            candidates=_evaluation_candidates_for(
                selection=selection,
                candidate_trajectories=candidate_trajectories,
            ),
        )

    def compute_pipeline_evaluation(
        self,
        *,
        run_config: RunConfig,
        plan: RunPlan,
        sequence_manifest: SequenceManifest | None,
        benchmark_inputs: PreparedBenchmarkInputs | None,
        slam: SlamArtifacts | None,
    ) -> TrajectoryEvaluationManifest | None:
        """Compute the trajectory-evaluation stage for one pipeline run.

        The stage path uses prepared benchmark inputs instead of rediscovering
        references from dataset folders. Missing requested baselines are runtime
        errors because the request explicitly enabled trajectory evaluation.
        """
        trajectory_config = run_config.stages.evaluate_trajectory
        if not trajectory_config.enabled:
            return None
        if sequence_manifest is None or benchmark_inputs is None or slam is None:
            raise RuntimeError(
                "Trajectory evaluation requires a sequence manifest, benchmark inputs, and SLAM artifacts."
            )
        reference = benchmark_inputs.trajectory_for_source(trajectory_config.baseline_source)
        if reference is None:
            raise RuntimeError(
                "Prepared benchmark inputs do not include the requested trajectory baseline "
                f"'{trajectory_config.baseline_source.value}'."
            )
        return self.compute_evaluation(
            selection=SelectionSnapshot(
                sequence_slug=sequence_manifest.sequence_id,
                reference_path=reference.path,
                target_frame=reference.target_frame
                or _infer_target_frame(sequence_manifest.dataset_id, reference.path),
                coordinate_status=reference.coordinate_status.value
                if reference.coordinate_status
                else _infer_coordinate_status(sequence_manifest.dataset_id, reference.path),
                reference_source=trajectory_config.baseline_source.value,
                run=DiscoveredRun(
                    artifact_root=plan.artifact_root,
                    estimate_path=slam.trajectory_tum.path,
                    point_cloud_path=slam.dense_points_ply.path if slam.dense_points_ply is not None else None,
                    method=run_config.stages.slam.backend.method_id.value
                    if run_config.stages.slam.backend is not None
                    else None,
                    label=(
                        run_config.stages.slam.backend.display_name
                        if run_config.stages.slam.backend is not None
                        else "unknown"
                    ),
                ),
            ),
            candidate_trajectories=list(benchmark_inputs.candidate_trajectories),
        )

    def _persist_metric_manifest(
        self,
        *,
        selection: SelectionSnapshot,
        reference_path: Path,
        reference_source: str,
        candidates: list[_TrajectoryEvaluationCandidate],
    ) -> TrajectoryEvaluationManifest:
        """Persist trajectory metrics for every ordered candidate."""
        run_root = selection.run.artifact_root
        run_id = stable_run_id(run_root, self.path_config)
        evaluation_dir = run_root / "evaluation" / "trajectory"
        error_series_dir = evaluation_dir / "error_series"
        error_series_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = self.manifest_path(run_root)
        metrics_long_path = self.metrics_long_path(run_root)

        rows: list[TrajectoryMetricResultRow] = []
        cases: list[TrajectoryEvaluationCase] = []
        skipped: list[SkippedMetricRecord] = []
        primary_metric_computed = False
        for candidate_index, candidate in enumerate(candidates):
            for spec in _METRIC_SPECS:
                is_primary_translation_ape = (
                    candidate_index == 0
                    and spec.family == "ape"
                    and spec.pose_relation is metrics.PoseRelation.translation_part
                )
                try:
                    if spec.family == "ape":
                        preview = compute_trajectory_ape_preview(
                            reference_path=reference_path,
                            estimate_path=candidate.path,
                            pose_relation=spec.pose_relation,
                            target_frame=selection.target_frame or "world",
                            source_frame=_method_world_frame(candidate.method_id),
                            reference_source=reference_source,
                            method_id=candidate.method_id,
                            method_label=candidate.method_label,
                        )
                    else:
                        preview = compute_trajectory_rpe_preview(
                            reference_path=reference_path,
                            estimate_path=candidate.path,
                            pose_relation=spec.pose_relation,
                            delta=spec.delta or 1.0,
                            delta_unit=spec.delta_unit_enum or metrics.Unit.meters,
                            target_frame=selection.target_frame or "world",
                            source_frame=_method_world_frame(candidate.method_id),
                            reference_source=reference_source,
                            method_id=candidate.method_id,
                            method_label=candidate.method_label,
                        )
                except ValueError as exc:
                    if is_primary_translation_ape:
                        raise
                    skipped.append(
                        SkippedMetricRecord(
                            candidate_source=f"{candidate.source}/{candidate.coordinate_status}",
                            metric_family=spec.family,
                            pose_relation=spec.pose_relation,
                            reason=str(exc),
                            delta=spec.delta,
                            delta_unit=spec.delta_unit,
                        )
                    )
                    continue
                matched_pairs = int(len(preview.error_values))
                relation_token = _entity_token(spec.pose_relation.value)
                error_series_filename = (
                    f"{_entity_token(reference_source)}__{_entity_token(candidate.source)}__"
                    f"{_entity_token(candidate.coordinate_status)}__{spec.family}_{relation_token}.npz"
                )
                error_series_path = error_series_dir / error_series_filename
                _write_error_series(
                    error_series_path,
                    preview=preview,
                    matched_pairs=matched_pairs,
                )
                primary_metric_computed = primary_metric_computed or is_primary_translation_ape
                cases.append(
                    TrajectoryEvaluationCase(
                        reference_path=reference_path,
                        candidate_path=candidate.path,
                        reference_source=reference_source,
                        candidate_source=candidate.source,
                        candidate_coordinate_status=candidate.coordinate_status,
                        metric_family=spec.family,
                        pose_relation=spec.pose_relation,
                        error_series_path=error_series_path,
                        matched_pairs=matched_pairs,
                        delta=spec.delta,
                        delta_unit=spec.delta_unit,
                    )
                )
                # Store a relative path in the CSV so the artifact is portable across machines.
                error_series_relative = Path("error_series") / error_series_filename
                rows.extend(
                    TrajectoryMetricResultRow(
                        run_id=run_id,
                        sequence_id=selection.sequence_slug,
                        reference_source=reference_source,
                        estimate_source=f"{candidate.source}/{candidate.coordinate_status}",
                        metric_family=spec.family,
                        pose_relation=spec.pose_relation,
                        statistic=statistic,
                        value=value,
                        unit=_POSE_RELATION_UNIT.get(spec.pose_relation, ""),
                        matched_pairs=matched_pairs,
                        delta=spec.delta,
                        delta_unit=spec.delta_unit,
                        error_series_path=error_series_relative,
                    )
                    for statistic, value in preview.stats.model_dump(mode="python").items()
                )

        if not primary_metric_computed:
            raise RuntimeError("Primary trajectory translation APE did not produce a metric row.")
        _write_metric_rows(metrics_long_path, rows)
        manifest = TrajectoryEvaluationManifest(
            artifact_root=run_root,
            sequence_id=selection.sequence_slug,
            run_id=run_id,
            reference_trajectories=[reference_path],
            candidate_trajectories=[candidate.path for candidate in candidates],
            error_series_paths=[case.error_series_path for case in cases],
            evaluation_cases=cases,
            skipped_metrics=skipped,
        )
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return manifest

    @staticmethod
    def alignment_path(run_root: Path) -> Path:
        """Return the deterministic persisted trajectory-alignment path."""
        return run_root / "evaluation" / "trajectory_alignment.json"

    @staticmethod
    def aligned_estimate_path(run_root: Path) -> Path:
        """Return the deterministic Sim(3)-aligned trajectory path."""
        return run_root / "evaluation" / "trajectory_sim3_aligned.tum"

    @staticmethod
    def aligned_point_cloud_path(run_root: Path) -> Path:
        """Return the deterministic Sim(3)-aligned point-cloud path."""
        return run_root / "evaluation" / "point_cloud_sim3_aligned.ply"

    @staticmethod
    def manifest_path(run_root: Path) -> Path:
        """Return the canonical trajectory-evaluation manifest path."""
        return run_root / "evaluation" / "trajectory" / "manifest.json"

    @staticmethod
    def metrics_long_path(run_root: Path) -> Path:
        """Return the canonical long-form trajectory metric table path."""
        return run_root / "evaluation" / "trajectory" / "metrics_long.csv"


def _method_world_frame(method_id: str | None) -> str:
    token = "slam" if method_id is None else _entity_token(str(method_id))
    return f"{token}_slam_world"


def _evaluation_candidates_for(
    *,
    selection: SelectionSnapshot,
    candidate_trajectories: list[ReferenceTrajectoryRef] | None,
) -> list[_TrajectoryEvaluationCandidate]:
    candidates = [
        _TrajectoryEvaluationCandidate(
            path=selection.run.estimate_path,
            source=selection.run.method or "vslam",
            coordinate_status="raw",
            method_id=selection.run.method,
            method_label=selection.run.label,
        )
    ]
    if candidate_trajectories is None:
        return candidates
    candidates.extend(
        _TrajectoryEvaluationCandidate(
            path=reference.path,
            source=reference.source.value,
            coordinate_status=(
                reference.coordinate_status.value if reference.coordinate_status is not None else "source_native"
            ),
            method_id=reference.source.value,
            method_label=reference.source.value,
        )
        for reference in candidate_trajectories
    )
    return candidates


def _write_metric_rows(path: Path, rows: list[TrajectoryMetricResultRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    metric_rows_to_frame(rows).to_csv(path, index=False)


def _write_error_series(path: Path, *, preview: _TrajectoryMetricPreview, matched_pairs: int) -> None:
    payload = {
        "values": preview.error_values,
        "timestamps_s": preview.error_timestamps_s,
        "pair_index": np.arange(matched_pairs, dtype=np.int64),
    }
    if preview.reference_positions_xyz is not None and preview.estimate_positions_xyz is not None:
        payload["reference_positions_xyz"] = preview.reference_positions_xyz
        payload["estimate_positions_xyz"] = preview.estimate_positions_xyz
    np.savez(path, **payload)


def _entity_token(value: str) -> str:
    stripped = value.strip().replace(" ", "_")
    return "".join(char if char.isalnum() or char in {"_", "-"} else "_" for char in stripped) or "unknown"


def _apply_sim3_cloud_use_policy(
    alignment: TrajectoryAlignmentArtifact,
    *,
    cloud_input_present: bool,
) -> TrajectoryAlignmentArtifact:
    up_axis_tilt_deg = sim3_up_axis_tilt_deg(np.asarray(alignment.rotation, dtype=np.float64))
    reasons: list[str] = []
    if cloud_input_present:
        if alignment.matched_pairs < _SIM3_CLOUD_MIN_MATCHED_PAIRS:
            reasons.append("insufficient_matched_pairs")
        if not math.isfinite(alignment.scale) or alignment.scale <= 0.0:
            reasons.append("invalid_scale")
        if not math.isfinite(alignment.rms_error_m) or alignment.rms_error_m > _SIM3_CLOUD_MAX_RMS_ERROR_M:
            reasons.append("rms_error_too_high")
        if up_axis_tilt_deg is None:
            reasons.append("unknown_up_axis_tilt")
        elif up_axis_tilt_deg > _SIM3_CLOUD_MAX_UP_AXIS_TILT_DEG:
            reasons.append("up_axis_tilt_too_high")
    return alignment.model_copy(
        update={
            "cloud_input_present": cloud_input_present,
            "cloud_warning_reasons": reasons,
            "cloud_rejection_reasons": ["invalid_scale"] if "invalid_scale" in reasons else [],
            "cloud_gate_min_matched_pairs": _SIM3_CLOUD_MIN_MATCHED_PAIRS,
            "cloud_gate_max_rms_error_m": _SIM3_CLOUD_MAX_RMS_ERROR_M,
            "cloud_gate_max_up_axis_tilt_deg": _SIM3_CLOUD_MAX_UP_AXIS_TILT_DEG,
            "up_axis_tilt_deg": up_axis_tilt_deg,
        }
    )


def _infer_target_frame(dataset: DatasetId | None, reference_path: Path | None) -> str:
    """Inferred target frame name for UI selections without benchmark input metadata."""
    if dataset is DatasetId.ADVIO:
        return "advio_gt_world"
    if dataset is DatasetId.TUM_RGBD:
        return "tum_rgbd_world"
    return "world"


def _infer_coordinate_status(dataset: DatasetId | None, reference_path: Path | None) -> str:
    """Inferred coordinate status for UI selections without benchmark input metadata."""
    if dataset is DatasetId.ADVIO:
        return "aligned"
    return "source_native"


def _write_aligned_point_cloud(
    *,
    source_path: Path,
    output_path: Path,
    alignment: TrajectoryAlignmentArtifact,
) -> None:
    points_xyz, colors_rgb = load_point_cloud_ply_with_colors(source_path)
    rotation = np.asarray(alignment.rotation, dtype=np.float64)
    translation = np.asarray(alignment.translation, dtype=np.float64)
    aligned_points = alignment.scale * (points_xyz @ rotation.T) + translation
    write_point_cloud_ply(output_path, aligned_points, colors_rgb=colors_rgb)


__all__ = ["TrajectoryEvaluationService"]
