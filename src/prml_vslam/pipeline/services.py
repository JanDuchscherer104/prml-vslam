"""Reusable pipeline planning services shared by the CLI and UI."""

from __future__ import annotations

from prml_vslam.methods.interfaces import MethodId
from prml_vslam.pipeline.contracts import (
    DatasetSourceSpec,
    LiveSourceSpec,
    RunPlan,
    RunPlanStage,
    RunPlanStageId,
    RunRequest,
    VideoSourceSpec,
)
from prml_vslam.utils import PathConfig, RunArtifactPaths


class PipelinePlannerService:
    """Build a lightweight typed execution plan for a benchmark run."""

    def __init__(self, path_config: PathConfig | None = None) -> None:
        self.path_config = path_config or PathConfig()

    def build_plan(self, request: RunRequest) -> RunPlan:
        """Build an ordered run plan from a typed request."""
        run_paths = self.path_config.plan_run_paths(
            experiment_name=request.experiment_name,
            method_slug=request.tracking.method.artifact_slug,
            output_dir=request.output_dir,
        )
        run_id = self.path_config.slugify_experiment_name(request.experiment_name)
        stages = self._build_stages(request=request, run_paths=run_paths)
        return RunPlan(
            run_id=run_id,
            mode=request.mode,
            method=request.tracking.method,
            artifact_root=run_paths.artifact_root,
            source=request.source,
            stages=stages,
        )

    def _build_stages(self, *, request: RunRequest, run_paths: RunArtifactPaths) -> list[RunPlanStage]:
        stages = [
            RunPlanStage(
                id=RunPlanStageId.INGEST,
                title="Normalize Input Sequence",
                summary=self._ingest_summary(request.source),
                outputs=[run_paths.sequence_manifest_path],
            ),
            RunPlanStage(
                id=RunPlanStageId.SLAM,
                title="Run SLAM Backend",
                summary=self._method_summary(request.tracking.method),
                outputs=[
                    run_paths.trajectory_path,
                    run_paths.sparse_points_path,
                ],
            ),
        ]

        if request.dense.enabled:
            stages.append(
                RunPlanStage(
                    id=RunPlanStageId.DENSE_MAPPING,
                    title="Export Dense Mapping",
                    summary="Generate dense geometry artifacts suitable for downstream quality evaluation.",
                    outputs=[run_paths.dense_points_path],
                )
            )

        if request.reference.enabled:
            stages.append(
                RunPlanStage(
                    id=RunPlanStageId.REFERENCE_RECONSTRUCTION,
                    title="Build Reference Reconstruction",
                    summary="Reserve the offline reconstruction step used as a dense geometry reference.",
                    outputs=[run_paths.reference_cloud_path],
                )
            )

        if request.evaluation.compare_to_arcore:
            stages.append(
                RunPlanStage(
                    id=RunPlanStageId.TRAJECTORY_EVALUATION,
                    title="Evaluate Trajectory",
                    summary="Align the trajectory against the available reference and persist trajectory metrics.",
                    outputs=[run_paths.trajectory_metrics_path],
                )
            )

        if request.evaluation.evaluate_cloud:
            stages.append(
                RunPlanStage(
                    id=RunPlanStageId.CLOUD_EVALUATION,
                    title="Evaluate Dense Cloud",
                    summary="Compare reconstructed dense geometry against the reference cloud.",
                    outputs=[run_paths.cloud_metrics_path],
                )
            )

        if request.evaluation.evaluate_efficiency:
            stages.append(
                RunPlanStage(
                    id=RunPlanStageId.EFFICIENCY_EVALUATION,
                    title="Measure Efficiency",
                    summary="Persist runtime and resource-usage metrics for the run.",
                    outputs=[run_paths.efficiency_metrics_path],
                )
            )

        stages.append(
            RunPlanStage(
                id=RunPlanStageId.SUMMARY,
                title="Write Run Summary",
                summary="Persist the stage status and top-level artifact summary for the run.",
                outputs=[run_paths.summary_path],
            )
        )
        return stages

    @staticmethod
    def _ingest_summary(source: VideoSourceSpec | DatasetSourceSpec | LiveSourceSpec) -> str:
        match source:
            case VideoSourceSpec(video_path=video_path, frame_stride=frame_stride):
                return f"Decode '{video_path}' at stride {frame_stride} and materialize a normalized sequence manifest."
            case DatasetSourceSpec(dataset_id=dataset_id, sequence_id=sequence_id):
                return f"Normalize dataset sequence '{dataset_id.value}:{sequence_id}' into a shared sequence manifest."
            case LiveSourceSpec(source_id=source_id, persist_capture=persist_capture):
                persistence = "with persistence" if persist_capture else "without persistence"
                return f"Capture the live source '{source_id}' {persistence} into a replayable sequence manifest."

    @staticmethod
    def _method_summary(method: MethodId) -> str:
        return f"Plan the {method.display_name} wrapper and export trajectory plus sparse geometry artifacts."


__all__ = ["PipelinePlannerService"]
