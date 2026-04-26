"""Concrete evaluation services built on normalized run artifacts.

This module implements the explicit evaluation work described by
:mod:`prml_vslam.eval.contracts` and :mod:`prml_vslam.eval.protocols`. It
discovers runs under the artifact root, resolves reference trajectories, and
computes or reloads persisted `evo`-based trajectory metrics.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from evo.core import metrics, sync
from evo.core.trajectory import PoseTrajectory3D
from evo.tools import file_interface

from prml_vslam.eval.contracts import (
    DiscoveredRun,
    ErrorSeries,
    EvaluationArtifact,
    EvaluationSelection,
    MetricStats,
    SelectionSnapshot,
    TrajectoryAlignmentArtifact,
    TrajectoryAlignmentMode,
    TrajectoryEvaluationPreview,
    TrajectoryEvaluationSemantics,
    TrajectoryMetricId,
    TrajectorySeries,
)
from prml_vslam.eval.protocols import TrajectoryEvaluator
from prml_vslam.interfaces.slam import SlamArtifacts
from prml_vslam.methods.stage.backend_config import MethodId
from prml_vslam.sources.contracts import PreparedBenchmarkInputs, SequenceManifest
from prml_vslam.sources.datasets.contracts import DatasetId
from prml_vslam.sources.datasets.registry import list_sequence_slugs, resolve_reference_path
from prml_vslam.utils.geometry import load_point_cloud_ply_with_colors, load_tum_trajectory, write_point_cloud_ply
from prml_vslam.utils.path_config import PathConfig

__all__ = ["TrajectoryEvaluationService", "compute_trajectory_ape_preview"]

_EVO_ASSOCIATION_MAX_DIFF_S = 0.01

if TYPE_CHECKING:
    from prml_vslam.pipeline.config import RunConfig
    from prml_vslam.pipeline.contracts.plan import RunPlan


class TrajectoryEvaluationService(TrajectoryEvaluator):
    """Discover runs and compute or reload explicit `evo` trajectory metrics.

    The service is the eval-owned implementation behind metrics pages and the
    trajectory-evaluation pipeline stage. It consumes normalized TUM
    trajectories and prepared references, persists metric semantics, and keeps
    evaluation execution explicit rather than tied to app rerenders.
    """

    def __init__(self, path_config: PathConfig) -> None:
        self.path_config = path_config

    def discover_runs(self, sequence_slug: str | None) -> list[DiscoveredRun]:
        """Return all runs under the artifacts root that match one sequence slug.

        Discovery is read-only and based on normalized ``slam/trajectory.tum``
        outputs. It does not validate metric availability or compute missing
        results.
        """
        if sequence_slug is None:
            return []
        return [
            DiscoveredRun(
                artifact_root=run_root,
                estimate_path=trajectory_path,
                method=method,
                label=label if not visible_parts else f"{label} · {' / '.join(visible_parts)}",
            )
            for trajectory_path in sorted(self.path_config.artifacts_dir.glob("**/slam/trajectory.tum"))
            if sequence_slug
            in (
                relative_parts := (run_root := trajectory_path.parent.parent)
                .relative_to(self.path_config.artifacts_dir)
                .parts
            )
            or sequence_slug in run_root.name
            for method in [
                next(
                    (method for part in reversed(relative_parts) for method in MethodId if part == method.value),
                    None,
                )
            ]
            for visible_parts in [
                [
                    part
                    for part in relative_parts
                    if part not in ({sequence_slug, "slam"} | ({method.value} if method is not None else set()))
                ]
            ]
            for label in [method.display_name if method is not None else relative_parts[-1]]
        ]

    def resolve_selection(
        self,
        *,
        dataset: DatasetId,
        preferred_sequence_slug: str | None,
        preferred_run_root: Path | None,
    ) -> EvaluationSelection:
        """Resolve dataset sequences, runs, and the current metrics-page selection.

        This method keeps UI state deterministic by turning optional preferred
        values into one concrete selection snapshot when local references and
        run artifacts are available.
        """
        dataset_root = self.path_config.resolve_dataset_dir(dataset.value)
        artifacts_root = self.path_config.artifacts_dir
        sequence_slugs = list_sequence_slugs(dataset, dataset_root)
        if not sequence_slugs:
            return EvaluationSelection(
                dataset=dataset,
                dataset_root=dataset_root,
                artifacts_root=artifacts_root,
            )

        sequence_slug = preferred_sequence_slug if preferred_sequence_slug in sequence_slugs else sequence_slugs[0]
        runs = self.discover_runs(sequence_slug)
        if not runs:
            return EvaluationSelection(
                dataset=dataset,
                dataset_root=dataset_root,
                artifacts_root=artifacts_root,
                sequence_slugs=sequence_slugs,
                sequence_slug=sequence_slug,
                runs=runs,
            )

        run = next((candidate for candidate in runs if candidate.artifact_root == preferred_run_root), runs[0])
        return EvaluationSelection(
            dataset=dataset,
            dataset_root=dataset_root,
            artifacts_root=artifacts_root,
            sequence_slugs=sequence_slugs,
            sequence_slug=sequence_slug,
            runs=runs,
            selection=SelectionSnapshot(
                sequence_slug=sequence_slug,
                reference_path=resolve_reference_path(dataset, dataset_root, sequence_slug),
                run=run,
            ),
        )

    def load_evaluation(
        self,
        *,
        selection: SelectionSnapshot,
    ) -> EvaluationArtifact | None:
        """Load a persisted `evo` evaluation when it exists.

        Returns ``None`` when either the reference or metrics artifact is
        missing, leaving callers free to render an explicit compute action.
        """
        reference_path = selection.reference_path
        result_path = self.result_path(selection.run.artifact_root)
        if reference_path is None or not result_path.exists():
            return None
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        reference_series = _series_from_trajectory("Reference", load_tum_trajectory(reference_path))
        estimate_series = _series_from_trajectory("Estimate", load_tum_trajectory(selection.run.estimate_path))
        trajectories = (reference_series, estimate_series)
        return EvaluationArtifact.from_payload(
            path=result_path,
            payload=payload,
            reference_path=reference_path,
            estimate_path=selection.run.estimate_path,
            trajectories=trajectories,
        )

    def compute_evaluation(
        self,
        *,
        selection: SelectionSnapshot,
    ) -> EvaluationArtifact:
        """Compute and persist trajectory APE via the `evo` Python API.

        The current executable metric is translation APE with timestamp
        association only. The persisted payload records those semantics so
        future RPE or alignment modes can coexist without ambiguity.
        """
        reference_path = selection.reference_path
        if reference_path is None:
            raise FileNotFoundError("The selected dataset slice is missing a TUM reference trajectory.")

        preview = compute_trajectory_ape_preview(
            reference_path=reference_path,
            estimate_path=selection.run.estimate_path,
            alignment_mode=TrajectoryAlignmentMode.SIM3_UMEYAMA,
        )
        result_path = self.result_path(selection.run.artifact_root)
        result_path.parent.mkdir(parents=True, exist_ok=True)
        alignment_path = None
        aligned_estimate_path = None
        aligned_point_cloud_path = None
        if preview.alignment is not None:
            alignment_path = self.alignment_path(selection.run.artifact_root)
            alignment_path.write_text(
                json.dumps(preview.alignment.model_dump(mode="json"), indent=2, sort_keys=True),
                encoding="utf-8",
            )
            aligned_estimate_path = self.aligned_estimate_path(selection.run.artifact_root)
            _write_aligned_estimate_trajectory(
                reference_path=reference_path,
                estimate_path=selection.run.estimate_path,
                alignment_mode=TrajectoryAlignmentMode.SIM3_UMEYAMA,
                max_diff_s=_EVO_ASSOCIATION_MAX_DIFF_S,
                output_path=aligned_estimate_path,
            )
            if selection.run.point_cloud_path is not None:
                aligned_point_cloud_path = self.aligned_point_cloud_path(selection.run.artifact_root)
                _write_aligned_point_cloud(
                    source_path=selection.run.point_cloud_path,
                    output_path=aligned_point_cloud_path,
                    alignment=preview.alignment,
                )
        alignment_mode = (
            TrajectoryAlignmentMode.SIM3_UMEYAMA
            if preview.alignment is not None
            else TrajectoryAlignmentMode.TIMESTAMP_ASSOCIATED_ONLY
        )
        payload = {
            "title": "Trajectory APE (evo)",
            "matched_pairs": len(preview.error_series.values),
            "stats": preview.stats.model_dump(mode="python"),
            "error_timestamps_s": preview.error_series.timestamps_s.tolist(),
            "error_values": preview.error_series.values.tolist(),
            "alignment_path": None if alignment_path is None else alignment_path.as_posix(),
            "aligned_estimate_path": None if aligned_estimate_path is None else aligned_estimate_path.as_posix(),
            "aligned_point_cloud_path": None
            if aligned_point_cloud_path is None
            else aligned_point_cloud_path.as_posix(),
            "semantics": TrajectoryEvaluationSemantics(
                metric_id=TrajectoryMetricId.APE_TRANSLATION,
                pose_relation="translation_part",
                alignment_mode=alignment_mode,
                sync_max_diff_s=_EVO_ASSOCIATION_MAX_DIFF_S,
            ).model_dump(mode="python"),
        }
        result_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return EvaluationArtifact.from_payload(
            path=result_path,
            payload=payload,
            reference_path=reference_path,
            estimate_path=selection.run.estimate_path,
            trajectories=(preview.reference, preview.estimate),
        )

    def compute_pipeline_evaluation(
        self,
        *,
        run_config: RunConfig,
        plan: RunPlan,
        sequence_manifest: SequenceManifest | None,
        benchmark_inputs: PreparedBenchmarkInputs | None,
        slam: SlamArtifacts | None,
    ) -> EvaluationArtifact | None:
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
                run=DiscoveredRun(
                    artifact_root=plan.artifact_root,
                    estimate_path=slam.trajectory_tum.path,
                    point_cloud_path=slam.dense_points_ply.path if slam.dense_points_ply is not None else None,
                    method=run_config.stages.slam.backend.method_id
                    if run_config.stages.slam.backend is not None
                    else None,
                    label=(
                        run_config.stages.slam.backend.display_name
                        if run_config.stages.slam.backend is not None
                        else "unknown"
                    ),
                ),
            )
        )

    @staticmethod
    def result_path(run_root: Path) -> Path:
        """Return the deterministic persisted trajectory-metrics path for the controls."""
        return run_root / "evaluation" / "trajectory_metrics.json"

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


def compute_trajectory_ape_preview(
    *,
    reference_path: Path,
    estimate_path: Path,
    max_diff_s: float = _EVO_ASSOCIATION_MAX_DIFF_S,
    alignment_mode: TrajectoryAlignmentMode = TrajectoryAlignmentMode.TIMESTAMP_ASSOCIATED_ONLY,
) -> TrajectoryEvaluationPreview:
    """Compute in-memory translation APE for two normalized TUM trajectory artifacts.

    Uses evo's timestamp association and APE implementation over
    :class:`evo.core.trajectory.PoseTrajectory3D`. The helper returns a preview
    DTO and leaves persistence to :class:`TrajectoryEvaluationService`.
    """
    reference_trajectory = load_tum_trajectory(reference_path)
    estimate_trajectory = load_tum_trajectory(estimate_path)
    try:
        associated_reference, associated_estimate = sync.associate_trajectories(
            reference_trajectory,
            estimate_trajectory,
            max_diff=max_diff_s,
        )
    except sync.SyncException as exc:
        raise ValueError(
            f"No matching trajectory timestamps were found for evo APE (max_diff={max_diff_s:.3f}s)."
        ) from exc

    evaluation_estimate = associated_estimate
    alignment = None
    if alignment_mode is TrajectoryAlignmentMode.SIM3_UMEYAMA:
        if _trajectory_supports_sim3(associated_reference, associated_estimate):
            evaluation_estimate, alignment = _align_estimate_sim3(
                reference=associated_reference,
                estimate=associated_estimate,
                max_diff_s=max_diff_s,
            )
    elif alignment_mode is not TrajectoryAlignmentMode.TIMESTAMP_ASSOCIATED_ONLY:
        raise ValueError(f"Unsupported trajectory alignment mode: {alignment_mode.value}.")

    metric = metrics.APE(metrics.PoseRelation.translation_part)
    metric.process_data((associated_reference, evaluation_estimate))
    error_values = np.asarray(metric.error, dtype=np.float64)
    if error_values.size == 0:
        raise ValueError("evo APE produced zero matched trajectory pairs.")
    return TrajectoryEvaluationPreview(
        reference=_series_from_trajectory("Reference", associated_reference),
        estimate=_series_from_trajectory("Estimate", evaluation_estimate),
        error_series=ErrorSeries(
            timestamps_s=np.asarray(associated_reference.timestamps, dtype=np.float64),
            values=error_values,
        ),
        stats=MetricStats.from_error_values(error_values),
        alignment=alignment,
    )


def _series_from_trajectory(name: str, trajectory: PoseTrajectory3D) -> TrajectorySeries:
    return TrajectorySeries(
        name=name,
        timestamps_s=np.asarray(trajectory.timestamps, dtype=np.float64),
        positions_xyz=np.asarray(trajectory.positions_xyz, dtype=np.float64),
    )


def _align_estimate_sim3(
    *,
    reference: PoseTrajectory3D,
    estimate: PoseTrajectory3D,
    max_diff_s: float,
) -> tuple[PoseTrajectory3D, TrajectoryAlignmentArtifact]:
    aligned_estimate = copy.deepcopy(estimate)
    rotation, translation, scale = aligned_estimate.align(reference, correct_scale=True)
    residual = np.asarray(reference.positions_xyz, dtype=np.float64) - np.asarray(
        aligned_estimate.positions_xyz,
        dtype=np.float64,
    )
    rms_error_m = float(np.sqrt(np.mean(np.sum(residual**2, axis=1))))
    return aligned_estimate, TrajectoryAlignmentArtifact(
        source_frame="vista_slam_world",
        target_frame="advio_gt_world",
        scale=float(scale),
        rotation=np.asarray(rotation, dtype=np.float64).tolist(),
        translation=np.asarray(translation, dtype=np.float64).reshape(3).tolist(),
        matched_pairs=int(len(reference.positions_xyz)),
        rms_error_m=rms_error_m,
        reference_source="ground_truth",
        sync_max_diff_s=max_diff_s,
    )


def _trajectory_supports_sim3(reference: PoseTrajectory3D, estimate: PoseTrajectory3D) -> bool:
    if len(reference.positions_xyz) < 3 or len(estimate.positions_xyz) < 3:
        return False
    reference_centered = np.asarray(reference.positions_xyz, dtype=np.float64) - np.mean(
        reference.positions_xyz,
        axis=0,
    )
    estimate_centered = np.asarray(estimate.positions_xyz, dtype=np.float64) - np.mean(estimate.positions_xyz, axis=0)
    return np.linalg.matrix_rank(reference_centered) >= 2 and np.linalg.matrix_rank(estimate_centered) >= 2


def _write_aligned_estimate_trajectory(
    *,
    reference_path: Path,
    estimate_path: Path,
    alignment_mode: TrajectoryAlignmentMode,
    max_diff_s: float,
    output_path: Path,
) -> None:
    if alignment_mode is not TrajectoryAlignmentMode.SIM3_UMEYAMA:
        raise ValueError(f"Unsupported aligned trajectory materialization mode: {alignment_mode.value}.")
    reference_trajectory = load_tum_trajectory(reference_path)
    estimate_trajectory = load_tum_trajectory(estimate_path)
    associated_reference, associated_estimate = sync.associate_trajectories(
        reference_trajectory,
        estimate_trajectory,
        max_diff=max_diff_s,
    )
    aligned_estimate, _alignment = _align_estimate_sim3(
        reference=associated_reference,
        estimate=associated_estimate,
        max_diff_s=max_diff_s,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    file_interface.write_tum_trajectory_file(output_path, aligned_estimate)


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
