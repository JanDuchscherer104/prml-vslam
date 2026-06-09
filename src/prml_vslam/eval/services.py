"""Concrete evaluation services built on normalized run artifacts.

This module implements the explicit evaluation work described by
:mod:`prml_vslam.eval.contracts` and :mod:`prml_vslam.eval.protocols`. It
discovers runs under the artifact root, resolves reference trajectories, and
computes or reloads persisted `evo`-based trajectory metrics.
"""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
from evo.core import metrics, sync
from evo.core.trajectory import PoseTrajectory3D
from evo.tools import file_interface

from prml_vslam.eval.contracts import (
    BenchmarkReference,
    CloudAlignmentArtifact,
    CloudAlignmentSelection,
    DiscoveredRun,
    ErrorSeries,
    EvaluationArtifact,
    EvaluationSelection,
    MetricStats,
    SelectionSnapshot,
    TrajectoryAlignmentArtifact,
    TrajectoryAlignmentCloudUseStatus,
    TrajectoryAlignmentMode,
    TrajectoryEvaluationPreview,
    TrajectoryEvaluationSemantics,
    TrajectoryMetricId,
    TrajectorySeries,
)
from prml_vslam.eval.protocols import TrajectoryEvaluator
from prml_vslam.interfaces.geometry import apply_similarity_to_trajectory, yaw_similarity_align
from prml_vslam.interfaces.slam import SlamArtifacts
from prml_vslam.methods.stage.backend_config import MethodId
from prml_vslam.sources.contracts import PreparedBenchmarkInputs, SequenceManifest
from prml_vslam.sources.datasets.contracts import DatasetId
from prml_vslam.sources.datasets.registry import list_sequence_slugs, resolve_reference_path
from prml_vslam.utils.geometry import load_point_cloud_ply_with_colors, load_tum_trajectory, write_point_cloud_ply
from prml_vslam.utils.path_config import PathConfig

__all__ = [
    "CloudAlignmentService",
    "TrajectoryEvaluationService",
    "compute_trajectory_ape_preview",
]

_EVO_ASSOCIATION_MAX_DIFF_S = 0.01
_SIM3_CLOUD_MIN_MATCHED_PAIRS = 20
_SIM3_CLOUD_MAX_RMS_ERROR_M = 2.0
_SIM3_CLOUD_MAX_UP_AXIS_TILT_DEG = 15.0
_RDF_DOWN_AXIS = np.array([0.0, 1.0, 0.0], dtype=np.float64)


def _sequence_matches(relative_parts: tuple[str, ...], sequence_slug: str) -> bool:
    """Return whether a run artifact path belongs to one dataset sequence.

    A run is attributed to ``sequence_slug`` when any path component equals it or
    begins with ``f"{sequence_slug}-"``. This lets experiments named with a
    suffix (for example ``advio-15-offline-vista``) be discovered for the bare
    sequence slug (``advio-15``) without false-matching ``advio-150``.
    """
    return any(part == sequence_slug or part.startswith(f"{sequence_slug}-") for part in relative_parts)


_BENCHMARK_REFERENCE_FILES: list[tuple[str, str, str]] = [
    ("Ground Truth", "ground_truth", "ground_truth.tum"),
    ("ARCore", "arcore", "arcore.tum"),
    ("ARKit", "arkit", "arkit.tum"),
]

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
            for run_root in [trajectory_path.parent.parent]
            for relative_parts in [run_root.relative_to(self.path_config.artifacts_dir).parts]
            if _sequence_matches(relative_parts, sequence_slug)
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
        reference_path = resolve_reference_path(dataset, dataset_root, sequence_slug)
        return EvaluationSelection(
            dataset=dataset,
            dataset_root=dataset_root,
            artifacts_root=artifacts_root,
            sequence_slugs=sequence_slugs,
            sequence_slug=sequence_slug,
            runs=runs,
            selection=SelectionSnapshot(
                sequence_slug=sequence_slug,
                reference_path=reference_path,
                target_frame=_infer_target_frame(dataset, reference_path),
                coordinate_status=_infer_coordinate_status(dataset, reference_path),
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

        if not _trajectory_supports_sim3(associated_reference, associated_estimate):
            raise ValueError("Trajectory lacks sufficient geometric spread for Sim(3) alignment.")

        aligned_estimate, alignment = _align_estimate_sim3(
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
        if (
            selection.run.point_cloud_path is not None
            and alignment.cloud_use_status is not TrajectoryAlignmentCloudUseStatus.REJECTED
        ):
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
            target_frame=selection.target_frame or "world",
            source_frame=_method_world_frame(selection.run.method),
            reference_source=selection.reference_source or "reference",
            method_id=selection.run.method,
            method_label=selection.run.label,
        )
        result_path = self.result_path(selection.run.artifact_root)
        result_path.parent.mkdir(parents=True, exist_ok=True)
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
            "alignment_path": None,
            "aligned_estimate_path": None,
            "aligned_point_cloud_path": None,
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
            )
        )

    def discover_benchmark_references(self, run_root: Path) -> list[BenchmarkReference]:
        """Return aligned reference trajectories present in the run's ``benchmark/`` directory."""
        benchmark_dir = run_root / "benchmark"
        return [
            BenchmarkReference(label=label, source_key=source_key, path=benchmark_dir / filename)
            for label, source_key, filename in _BENCHMARK_REFERENCE_FILES
            if (benchmark_dir / filename).exists()
        ]

    def load_evaluation_for_source(
        self,
        *,
        run: DiscoveredRun,
        reference: BenchmarkReference,
    ) -> EvaluationArtifact | None:
        """Load a persisted evaluation for one specific benchmark reference source."""
        result_path = self.result_path_for_source(run.artifact_root, reference.source_key)
        if not result_path.exists():
            return None
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        reference_series = _series_from_trajectory(reference.label, load_tum_trajectory(reference.path))
        estimate_series = _series_from_trajectory("Estimate", load_tum_trajectory(run.estimate_path))
        return EvaluationArtifact.from_payload(
            path=result_path,
            payload=payload,
            reference_path=reference.path,
            estimate_path=run.estimate_path,
            trajectories=(reference_series, estimate_series),
        )

    def compute_evaluation_for_source(
        self,
        *,
        run: DiscoveredRun,
        reference: BenchmarkReference,
    ) -> EvaluationArtifact:
        """Compute and persist trajectory APE against one specific benchmark reference."""
        target_frame = _infer_target_frame(
            DatasetId.ADVIO, reference.path
        )  # BenchmarkReferences are ADVIO-only for now
        preview = compute_trajectory_ape_preview(
            reference_path=reference.path,
            estimate_path=run.estimate_path,
            alignment_mode=TrajectoryAlignmentMode.SIM3_UMEYAMA,
            target_frame=target_frame,
            source_frame=_method_world_frame(run.method),
            reference_source=reference.source_key,
            method_id=run.method,
            method_label=run.label,
        )
        result_path = self.result_path_for_source(run.artifact_root, reference.source_key)
        result_path.parent.mkdir(parents=True, exist_ok=True)
        alignment_mode = (
            TrajectoryAlignmentMode.SIM3_UMEYAMA
            if preview.alignment is not None
            else TrajectoryAlignmentMode.TIMESTAMP_ASSOCIATED_ONLY
        )
        payload = {
            "title": f"Trajectory APE (evo) — {reference.label}",
            "matched_pairs": len(preview.error_series.values),
            "stats": preview.stats.model_dump(mode="python"),
            "error_timestamps_s": preview.error_series.timestamps_s.tolist(),
            "error_values": preview.error_series.values.tolist(),
            "alignment_path": None,
            "aligned_estimate_path": None,
            "aligned_point_cloud_path": None,
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
            reference_path=reference.path,
            estimate_path=run.estimate_path,
            trajectories=(preview.reference, preview.estimate),
        )

    @staticmethod
    def result_path_for_source(run_root: Path, source_key: str) -> Path:
        """Return the persisted metrics path for one benchmark reference source."""
        if source_key == "ground_truth":
            return run_root / "evaluation" / "trajectory_metrics.json"
        return run_root / "evaluation" / f"trajectory_metrics_{source_key}.json"

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


class CloudAlignmentService:
    """Materialize offline point-cloud alignment artifacts before cloud metrics."""

    def compute_cloud_alignment(self, *, selection: CloudAlignmentSelection) -> CloudAlignmentArtifact:
        """Refine a trajectory-Sim(3)-aligned cloud against a reference cloud with ICP."""
        reference_pcd = _read_non_empty_point_cloud(selection.reference_cloud_path, label="reference")
        estimate_pcd = _read_non_empty_point_cloud(selection.sim3_cloud_path, label="estimate")
        o3d = _import_open3d()
        registration = o3d.pipelines.registration.registration_icp(
            estimate_pcd,
            reference_pcd,
            selection.max_correspondence_distance_m,
            np.eye(4, dtype=np.float64),
            o3d.pipelines.registration.TransformationEstimationPointToPoint(),
        )
        transformation = np.asarray(registration.transformation, dtype=np.float64)
        points_xyz, colors_rgb = load_point_cloud_ply_with_colors(selection.sim3_cloud_path)
        rotation = transformation[:3, :3]
        translation = transformation[:3, 3]
        refined_points = points_xyz @ rotation.T + translation
        icp_cloud_path = self.icp_point_cloud_path(selection.artifact_root)
        write_point_cloud_ply(icp_cloud_path, refined_points, colors_rgb=colors_rgb)
        artifact = CloudAlignmentArtifact(
            path=self.result_path(selection.artifact_root),
            reference_cloud_path=selection.reference_cloud_path,
            sim3_point_cloud_path=selection.sim3_cloud_path,
            icp_point_cloud_path=icp_cloud_path,
            target_frame=selection.target_frame,
            max_correspondence_distance_m=selection.max_correspondence_distance_m,
            fitness=float(registration.fitness),
            inlier_rmse_m=float(registration.inlier_rmse),
            transformation=transformation.tolist(),
        )
        artifact.path.parent.mkdir(parents=True, exist_ok=True)
        artifact.path.write_text(
            json.dumps(artifact.model_dump(mode="json"), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return artifact

    @staticmethod
    def result_path(run_root: Path) -> Path:
        """Return the deterministic point-cloud alignment metadata path."""
        return run_root / "evaluation" / "cloud_alignment.json"

    @staticmethod
    def icp_point_cloud_path(run_root: Path) -> Path:
        """Return the deterministic ICP-refined point-cloud path."""
        return run_root / "evaluation" / "point_cloud_sim3_icp_aligned.ply"


def compute_trajectory_ape_preview(
    *,
    reference_path: Path,
    estimate_path: Path,
    max_diff_s: float = _EVO_ASSOCIATION_MAX_DIFF_S,
    alignment_mode: TrajectoryAlignmentMode = TrajectoryAlignmentMode.TIMESTAMP_ASSOCIATED_ONLY,
    target_frame: str = "world",
    source_frame: str = "slam_world",
    reference_source: str = "reference",
    method_id: str | None = None,
    method_label: str | None = None,
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
                target_frame=target_frame,
                source_frame=source_frame,
                reference_source=reference_source,
                method_id=method_id,
                method_label=method_label,
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
    target_frame: str = "world",
    source_frame: str = "slam_world",
    reference_source: str = "reference",
    method_id: str | None = None,
    method_label: str | None = None,
) -> tuple[PoseTrajectory3D, TrajectoryAlignmentArtifact]:
    if _is_gravity_aligned_target(target_frame):
        # Gravity-aligned benchmark worlds (e.g. ADVIO) are near-planar; full
        # Umeyama can return an up/down-flipped rotation. Lock rotation to yaw
        # about the RDF gravity axis so the cloud overlay cannot flip upside down.
        scale_value, rotation_matrix, translation_vector = yaw_similarity_align(
            np.asarray(estimate.positions_xyz, dtype=np.float64),
            np.asarray(reference.positions_xyz, dtype=np.float64),
            up_axis=_RDF_DOWN_AXIS,
            correct_scale=True,
        )
        aligned_estimate = apply_similarity_to_trajectory(
            estimate, scale=scale_value, rotation=rotation_matrix, translation=translation_vector
        )
        rotation, translation, scale = rotation_matrix, translation_vector, scale_value
    else:
        aligned_estimate = copy.deepcopy(estimate)
        rotation, translation, scale = aligned_estimate.align(reference, correct_scale=True)
    residual = np.asarray(reference.positions_xyz, dtype=np.float64) - np.asarray(
        aligned_estimate.positions_xyz,
        dtype=np.float64,
    )
    rms_error_m = float(np.sqrt(np.mean(np.sum(residual**2, axis=1))))
    return aligned_estimate, TrajectoryAlignmentArtifact(
        source_frame=source_frame,
        target_frame=target_frame,
        scale=float(scale),
        rotation=np.asarray(rotation, dtype=np.float64).tolist(),
        translation=np.asarray(translation, dtype=np.float64).reshape(3).tolist(),
        matched_pairs=int(len(reference.positions_xyz)),
        rms_error_m=rms_error_m,
        reference_source=reference_source,
        sync_max_diff_s=max_diff_s,
        method_id=method_id,
        method_label=method_label,
    )


def _method_world_frame(method_id: str | None) -> str:
    token = "slam" if method_id is None else _entity_token(str(method_id))
    return f"{token}_slam_world"


def _entity_token(value: str) -> str:
    stripped = value.strip().replace(" ", "_")
    return "".join(char if char.isalnum() or char in {"_", "-"} else "_" for char in stripped) or "unknown"


def _apply_sim3_cloud_use_policy(
    alignment: TrajectoryAlignmentArtifact,
    *,
    cloud_input_present: bool,
) -> TrajectoryAlignmentArtifact:
    up_axis_tilt_deg = _sim3_up_axis_tilt_deg(np.asarray(alignment.rotation, dtype=np.float64))
    reasons: list[str] = []
    status = TrajectoryAlignmentCloudUseStatus.NOT_REQUESTED
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
        status = (
            TrajectoryAlignmentCloudUseStatus.REJECTED
            if "invalid_scale" in reasons
            else TrajectoryAlignmentCloudUseStatus.ACCEPTED
        )
    return alignment.model_copy(
        update={
            "cloud_input_present": cloud_input_present,
            "cloud_use_status": status,
            "cloud_warning_reasons": reasons,
            "cloud_rejection_reasons": ["invalid_scale"] if "invalid_scale" in reasons else [],
            "cloud_gate_min_matched_pairs": _SIM3_CLOUD_MIN_MATCHED_PAIRS,
            "cloud_gate_max_rms_error_m": _SIM3_CLOUD_MAX_RMS_ERROR_M,
            "cloud_gate_max_up_axis_tilt_deg": _SIM3_CLOUD_MAX_UP_AXIS_TILT_DEG,
            "up_axis_tilt_deg": up_axis_tilt_deg,
        }
    )


def _sim3_up_axis_tilt_deg(rotation: np.ndarray) -> float | None:
    if rotation.shape != (3, 3) or not np.all(np.isfinite(rotation)):
        return None
    transformed_down_axis = rotation @ _RDF_DOWN_AXIS
    norm = float(np.linalg.norm(transformed_down_axis))
    if norm <= 0.0 or not math.isfinite(norm):
        return None
    cos_angle = float(np.clip(np.dot(transformed_down_axis / norm, _RDF_DOWN_AXIS), -1.0, 1.0))
    return math.degrees(math.acos(cos_angle))


def _trajectory_supports_sim3(reference: PoseTrajectory3D, estimate: PoseTrajectory3D) -> bool:
    if len(reference.positions_xyz) < 3 or len(estimate.positions_xyz) < 3:
        return False
    reference_centered = np.asarray(reference.positions_xyz, dtype=np.float64) - np.mean(
        reference.positions_xyz,
        axis=0,
    )
    estimate_centered = np.asarray(estimate.positions_xyz, dtype=np.float64) - np.mean(estimate.positions_xyz, axis=0)
    return np.linalg.matrix_rank(reference_centered) >= 2 and np.linalg.matrix_rank(estimate_centered) >= 2


def _is_gravity_aligned_target(target_frame: str) -> bool:
    """Whether the benchmark target frame is gravity-aligned (up == RDF -Y).

    ADVIO provider worlds derive from Apple Y-up, so RDF ``-Y`` is gravity. The
    TUM first-camera RDF frame is *not* gravity-aligned, so it keeps full Umeyama.
    """
    return target_frame.startswith("advio_") and target_frame.endswith("_world")


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


def _read_non_empty_point_cloud(path: Path, *, label: str) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"Point-cloud alignment {label} cloud does not exist: {path}")
    o3d = _import_open3d()
    point_cloud = o3d.io.read_point_cloud(path.as_posix())
    points_xyz = np.asarray(point_cloud.points, dtype=np.float64)
    if points_xyz.shape[0] == 0:
        raise ValueError(f"Point-cloud alignment {label} cloud is empty: {path}")
    if points_xyz.ndim != 2 or points_xyz.shape[1] != 3:
        raise ValueError(f"Expected {label} point cloud shape (N, 3), got {points_xyz.shape} for '{path}'.")
    if not np.isfinite(points_xyz).all():
        raise ValueError(f"Point-cloud alignment {label} cloud contains non-finite points: {path}")
    return point_cloud


def _import_open3d() -> Any:
    try:
        import open3d as o3d
    except ImportError as exc:  # pragma: no cover - exercised only when optional runtime is missing
        raise RuntimeError("Open3D is required for point-cloud alignment.") from exc
    return o3d
