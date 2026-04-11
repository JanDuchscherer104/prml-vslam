"""Pipeline planning services."""

from __future__ import annotations

from prml_vslam.io.record3d import Record3DTransportId
from prml_vslam.pipeline.contracts import (
    DatasetSourceSpec,
    LiveSourceSpec,
    Record3DLiveSourceSpec,
    RunPlan,
    RunPlanStage,
    RunPlanStageId,
    RunRequest,
    SlamConfig,
    SourceSpec,
    VideoSourceSpec,
)
from prml_vslam.utils import PathConfig, RunArtifactPaths


class RunPlannerService:
    """Canonical planner for the linear pipeline contract.

    Typical usage constructs a fully specified :class:`RunRequest` and then
    calls either :meth:`build_run_plan` directly or ``RunRequest.build()`` to
    obtain the ordered :class:`RunPlan` consumed by the CLI and app surfaces.
    """

    def build_run_plan(self, request: RunRequest, path_config: PathConfig | None = None) -> RunPlan:
        """Build the canonical run plan for one fully specified request.

        Args:
            request: Complete pipeline request containing the source, SLAM
                config, optional stage toggles, and evaluation toggles.
            path_config: Optional path helper that owns canonical repository
                artifact layout.

        Returns:
            Run plan with stable stage ids, current planner ordering, and
            canonical artifact paths for each enabled stage.
        """
        self._validate_request(request)
        config = path_config or PathConfig()
        run_paths = config.plan_run_paths(
            experiment_name=request.experiment_name,
            method_slug=request.slam.method.value,
            output_dir=request.output_dir,
        )
        return RunPlan(
            run_id=config.slugify_experiment_name(request.experiment_name),
            mode=request.mode,
            method=request.slam.method,
            artifact_root=run_paths.artifact_root,
            source=request.source,
            stages=self._build_stages(request, run_paths),
        )

    def _build_stages(self, request: RunRequest, run_paths: RunArtifactPaths) -> list[RunPlanStage]:
        slam_output_names = ["trajectory_path"]
        if request.slam.emit_sparse_points:
            slam_output_names.append("sparse_points_path")
        if request.slam.emit_dense_points:
            slam_output_names.append("dense_points_path")
        optional_stages = (
            (
                request.reference.enabled,
                (
                    RunPlanStageId.REFERENCE_RECONSTRUCTION,
                    "Build Reference Reconstruction",
                    "Reserve the offline reconstruction step used as a dense geometry reference.",
                    ("reference_cloud_path",),
                ),
            ),
            (
                request.evaluation.evaluate_trajectory,
                (
                    RunPlanStageId.TRAJECTORY_EVALUATION,
                    "Evaluate Trajectory",
                    "Align the trajectory against the available reference and persist trajectory metrics.",
                    ("trajectory_metrics_path",),
                ),
            ),
            (
                request.evaluation.evaluate_cloud,
                (
                    RunPlanStageId.CLOUD_EVALUATION,
                    "Evaluate Dense Cloud",
                    "Compare reconstructed dense geometry against the reference cloud.",
                    ("cloud_metrics_path",),
                ),
            ),
            (
                request.evaluation.evaluate_efficiency,
                (
                    RunPlanStageId.EFFICIENCY_EVALUATION,
                    "Measure Efficiency",
                    "Persist runtime and resource-usage metrics for the run.",
                    ("efficiency_metrics_path",),
                ),
            ),
        )
        return [
            self._stage_from_spec(
                run_paths,
                (
                    RunPlanStageId.INGEST,
                    "Normalize Input Sequence",
                    self._ingest_summary(request.source),
                    ("sequence_manifest_path",),
                ),
            ),
            self._stage_from_spec(
                run_paths,
                (
                    RunPlanStageId.SLAM,
                    "Run SLAM Backend",
                    self._method_summary(request.slam),
                    tuple(slam_output_names),
                ),
            ),
            *(self._stage_from_spec(run_paths, spec) for enabled, spec in optional_stages if enabled),
            self._stage_from_spec(
                run_paths,
                (
                    RunPlanStageId.SUMMARY,
                    "Write Run Summary",
                    "Persist the stage status and top-level artifact summary for the run.",
                    ("summary_path", "stage_manifests_path"),
                ),
            ),
        ]

    @staticmethod
    def _stage_from_spec(
        run_paths: RunArtifactPaths,
        spec: tuple[RunPlanStageId, str, str, tuple[str, ...]],
    ) -> RunPlanStage:
        stage_id, title, summary, output_names = spec
        return RunPlanStage(
            id=stage_id,
            title=title,
            summary=summary,
            outputs=[getattr(run_paths, output_name) for output_name in output_names],
        )

    @staticmethod
    def _ingest_summary(source: SourceSpec) -> str:
        match source:
            case VideoSourceSpec(video_path=video_path, frame_stride=frame_stride):
                return f"Decode '{video_path}' at stride {frame_stride} and materialize a normalized sequence manifest."
            case DatasetSourceSpec(dataset_id=dataset_id, sequence_id=sequence_id):
                return f"Normalize dataset sequence '{dataset_id.value}:{sequence_id}' into a shared sequence manifest."
            case Record3DLiveSourceSpec(
                transport=transport,
                persist_capture=persist_capture,
                device_index=device_index,
                device_address=device_address,
            ):
                persistence = "with persistence" if persist_capture else "without persistence"
                source_descriptor = (
                    f"USB device #{device_index}"
                    if transport is Record3DTransportId.USB and device_index is not None
                    else "default USB device"
                    if transport is Record3DTransportId.USB
                    else device_address or "Wi-Fi preview"
                )
                return (
                    f"Capture the Record3D {transport.label.lower()} source '{source_descriptor}' {persistence} "
                    "into a replayable sequence manifest."
                )
            case LiveSourceSpec(source_id=source_id, persist_capture=persist_capture):
                persistence = "with persistence" if persist_capture else "without persistence"
                return f"Capture the live source '{source_id}' {persistence} into a replayable sequence manifest."

    @staticmethod
    def _method_summary(config: SlamConfig) -> str:
        artifact_names = ["trajectory"]
        if config.emit_sparse_points:
            artifact_names.append("sparse geometry")
        if config.emit_dense_points:
            artifact_names.append("dense geometry")
        return f"Plan the {config.method.display_name} wrapper and export {', '.join(artifact_names)} artifacts."

    @staticmethod
    def _validate_request(request: RunRequest) -> None:
        if request.evaluation.evaluate_cloud and not request.slam.emit_dense_points:
            raise ValueError("Cloud evaluation requires `slam.emit_dense_points=True`.")


__all__ = ["RunPlannerService"]
