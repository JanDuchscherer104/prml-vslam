"""Reusable pipeline services shared by the CLI and UI."""

from __future__ import annotations

import json
import re
from pathlib import Path

from prml_vslam.pipeline.contracts import (
    CaptureManifest,
    DenseArtifactMetadata,
    InsightTone,
    MaterializedWorkspace,
    MethodId,
    PipelineMode,
    RunPlan,
    RunPlanInsight,
    RunPlanRequest,
    RunPlanStage,
    RunPlanStageId,
    TrajectoryArtifactMetadata,
    WorkspaceArtifact,
)


class PipelinePlannerService:
    """Build typed execution plans and interpretations for benchmark runs."""

    def build_plan(self, request: RunPlanRequest) -> RunPlan:
        """Build an ordered run plan from a typed planning request."""
        artifact_root = (
            request.output_dir / self._slugify(request.experiment_name) / request.mode.value / request.method.value
        )
        stages = self._build_stages(request=request, artifact_root=artifact_root)
        return RunPlan(
            experiment_name=request.experiment_name,
            mode=request.mode,
            method=request.method,
            input_video=request.video_path,
            artifact_root=artifact_root,
            stages=stages,
        )

    def build_capture_manifest(self, request: RunPlanRequest) -> CaptureManifest:
        """Build the repo-owned capture manifest for a request."""
        plan = self.build_plan(request)
        return CaptureManifest(
            experiment_name=request.experiment_name,
            mode=request.mode,
            method=request.method,
            input_video=request.video_path,
            output_root=plan.artifact_root,
            frame_stride=request.frame_stride,
            capture=request.capture,
        )

    def interpret_plan(self, request: RunPlanRequest, plan: RunPlan | None = None) -> list[RunPlanInsight]:
        """Return human-readable planning insights for the workbench."""
        resolved_plan = plan or self.build_plan(request)
        insights = [
            RunPlanInsight(
                title="Batch-first planning" if request.mode is PipelineMode.BATCH else "Streaming-first planning",
                detail=(
                    "This run emphasizes deterministic artifact generation and later evaluation surfaces."
                    if request.mode is PipelineMode.BATCH
                    else "This run emphasizes low-latency tracking and chunk persistence before later normalization."
                ),
                tone=InsightTone.ACCENT,
            ),
            RunPlanInsight(
                title="Method boundary stays explicit",
                detail=self._method_summary(request.method),
                tone=InsightTone.INFO,
            ),
            RunPlanInsight(
                title="Normalized outputs are first-class",
                detail=(
                    "The plan reserves explicit normalization stages so the app, CLI, and evaluation code can interpret "
                    "repo-owned artifacts rather than raw upstream folders."
                ),
                tone=InsightTone.INFO,
            ),
        ]

        if request.enable_dense_mapping:
            insights.append(
                RunPlanInsight(
                    title="Dense geometry is enabled",
                    detail="A normalized dense point-cloud placeholder and sidecar will be materialized for downstream inspection.",
                    tone=InsightTone.ACCENT,
                )
            )
        else:
            insights.append(
                RunPlanInsight(
                    title="Dense geometry is disabled",
                    detail="The run will stay trajectory-focused until the dense branch is enabled.",
                    tone=InsightTone.WARNING,
                )
            )

        if request.compare_to_arcore:
            arcore_note = (
                f"ARCore comparison is reserved with side-channel path {request.capture.arcore_log_path}."
                if request.capture.arcore_log_path is not None
                else "ARCore comparison is reserved, but no side-channel path has been attached yet."
            )
            insights.append(
                RunPlanInsight(
                    title="ARCore baseline stays external",
                    detail=arcore_note,
                    tone=InsightTone.INFO,
                )
            )

        if request.build_ground_truth_cloud:
            insights.append(
                RunPlanInsight(
                    title="Reference geometry remains downstream",
                    detail="Reference reconstruction is planned explicitly instead of being hidden inside the SLAM wrapper.",
                    tone=InsightTone.INFO,
                )
            )

        insights.append(
            RunPlanInsight(
                title="Artifact root reserved",
                detail=f"The run is staged under {resolved_plan.artifact_root}.",
                tone=InsightTone.ACCENT,
            )
        )
        return insights

    def _build_stages(self, *, request: RunPlanRequest, artifact_root: Path) -> list[RunPlanStage]:
        if request.mode is PipelineMode.STREAMING:
            return self._build_streaming_stages(request=request, artifact_root=artifact_root)
        return self._build_batch_stages(request=request, artifact_root=artifact_root)

    def _build_batch_stages(self, *, request: RunPlanRequest, artifact_root: Path) -> list[RunPlanStage]:
        stages = [
            RunPlanStage(
                id=RunPlanStageId.CAPTURE_MANIFEST,
                title="Capture Manifest",
                summary="Persist the repo-owned manifest that records video provenance, capture metadata, and optional side channels.",
                outputs=[artifact_root / "input" / "capture_manifest.json"],
            ),
            RunPlanStage(
                id=RunPlanStageId.VIDEO_DECODE,
                title="Video Decode",
                summary=f"Decode the input video at frame stride {request.frame_stride} into the normalized input workspace.",
                outputs=[artifact_root / "input" / "frames"],
            ),
            RunPlanStage(
                id=RunPlanStageId.METHOD_PREPARE,
                title="Method Prepare",
                summary="Resolve wrapper inputs, checkpoints, and execution assumptions before invoking the external backend.",
                outputs=[artifact_root / "planning" / "method_prepare.json"],
            ),
            RunPlanStage(
                id=RunPlanStageId.SLAM_RUN,
                title="Run SLAM Backend",
                summary=self._method_summary(request.method),
                outputs=[
                    artifact_root / "slam" / "trajectory.tum",
                    artifact_root / "slam" / "sparse_points.ply",
                ],
            ),
            RunPlanStage(
                id=RunPlanStageId.TRAJECTORY_NORMALIZATION,
                title="Normalize Trajectory",
                summary="Persist the normalized TUM trajectory together with explicit frame, unit, and timestamp metadata.",
                outputs=[artifact_root / "slam" / "trajectory.metadata.json"],
            ),
        ]

        if request.enable_dense_mapping:
            stages.append(
                RunPlanStage(
                    id=RunPlanStageId.DENSE_NORMALIZATION,
                    title="Normalize Dense Geometry",
                    summary="Persist the normalized dense geometry artifact together with explicit comparison metadata.",
                    outputs=[
                        artifact_root / "dense" / "dense_points.ply",
                        artifact_root / "dense" / "dense_points.metadata.json",
                    ],
                )
            )

        if request.compare_to_arcore:
            stages.append(
                RunPlanStage(
                    id=RunPlanStageId.ARCORE_ALIGNMENT,
                    title="Reserve ARCore Alignment",
                    summary="Materialize the baseline-alignment placeholder without hiding ARCore logic inside the method wrapper.",
                    outputs=[artifact_root / "evaluation" / "arcore_alignment.json"],
                )
            )

        if request.build_ground_truth_cloud:
            stages.append(
                RunPlanStage(
                    id=RunPlanStageId.REFERENCE_RECONSTRUCTION,
                    title="Reserve Reference Reconstruction",
                    summary="Reserve the offline reference geometry stage used for later dense comparison.",
                    outputs=[artifact_root / "reference" / "reference_cloud.ply"],
                )
            )

        stages.append(
            RunPlanStage(
                id=RunPlanStageId.VISUALIZATION_EXPORT,
                title="Visualization Export",
                summary="Reserve the interpretation and dashboard surfaces that summarize the planned run.",
                outputs=[artifact_root / "visualization" / "plan_summary.json"],
            )
        )
        return stages

    def _build_streaming_stages(self, *, request: RunPlanRequest, artifact_root: Path) -> list[RunPlanStage]:
        stages = [
            RunPlanStage(
                id=RunPlanStageId.CAPTURE_MANIFEST,
                title="Capture Manifest",
                summary="Persist capture and stream provenance for the live run.",
                outputs=[artifact_root / "input" / "capture_manifest.json"],
            ),
            RunPlanStage(
                id=RunPlanStageId.STREAM_SOURCE_OPEN,
                title="Open Stream Source",
                summary="Open the stream source and prepare incremental persistence.",
                outputs=[artifact_root / "stream" / "chunks"],
            ),
            RunPlanStage(
                id=RunPlanStageId.METHOD_PREPARE,
                title="Method Prepare",
                summary=self._method_summary(request.method),
                outputs=[artifact_root / "planning" / "method_prepare.json"],
            ),
            RunPlanStage(
                id=RunPlanStageId.ONLINE_TRACKING,
                title="Online Tracking",
                summary="Track poses incrementally for operator-facing feedback.",
                outputs=[artifact_root / "slam" / "trajectory.tum"],
            ),
            RunPlanStage(
                id=RunPlanStageId.CHUNK_PERSIST,
                title="Chunk Persist",
                summary="Persist incremental stream artifacts for later replay and evaluation.",
                outputs=[artifact_root / "stream" / "chunks"],
            ),
            RunPlanStage(
                id=RunPlanStageId.STREAM_FINALIZE,
                title="Stream Finalize",
                summary="Flush the live run into repo-owned normalized artifacts and summaries.",
                outputs=[artifact_root / "visualization" / "plan_summary.json"],
            ),
        ]
        return stages

    @staticmethod
    def _method_summary(method: MethodId) -> str:
        match method:
            case MethodId.VISTA_SLAM:
                return "Plan the ViSTA-SLAM wrapper with explicit uncalibrated assumptions and repo-owned outputs."
            case MethodId.MAST3R_SLAM:
                return "Plan the MASt3R-SLAM wrapper with explicit pointmap-driven dense outputs and repo-owned normalization."

    @staticmethod
    def _slugify(experiment_name: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", experiment_name.strip().lower())
        return slug.strip("-") or "experiment"


class WorkspaceMaterializerService:
    """Create a deterministic on-disk workspace for a planned run."""

    def __init__(self, planner: PipelinePlannerService | None = None) -> None:
        self.planner = planner or PipelinePlannerService()

    def materialize(self, request: RunPlanRequest) -> MaterializedWorkspace:
        """Materialize the planned run workspace and write placeholder artifacts."""
        plan = self.planner.build_plan(request)
        manifest = self.planner.build_capture_manifest(request)

        artifact_root = plan.artifact_root
        capture_manifest_path = artifact_root / "input" / "capture_manifest.json"
        run_request_path = artifact_root / "planning" / "run_request.toml"
        run_plan_path = artifact_root / "planning" / "run_plan.toml"
        blocked_paths = [
            capture_manifest_path,
            run_request_path,
            run_plan_path,
            *(output for stage in plan.stages for output in stage.outputs if output.suffix),
        ]
        for path in blocked_paths:
            if path.exists():
                raise FileExistsError(f"Refusing to overwrite existing artifact: {path}")

        artifacts: list[WorkspaceArtifact] = []
        capture_manifest_path.parent.mkdir(parents=True, exist_ok=True)
        capture_manifest_path.write_text(self._render_json(manifest.model_dump_jsonable()), encoding="utf-8")
        artifacts.append(
            WorkspaceArtifact(
                stage_id=RunPlanStageId.CAPTURE_MANIFEST,
                label="Capture manifest",
                path=capture_manifest_path,
                kind="manifest",
            )
        )

        run_request_path.parent.mkdir(parents=True, exist_ok=True)
        request.save_toml(run_request_path)
        plan.save_toml(run_plan_path)
        artifacts.extend(
            [
                WorkspaceArtifact(
                    stage_id=RunPlanStageId.METHOD_PREPARE,
                    label="Run request snapshot",
                    path=run_request_path,
                    kind="config",
                ),
                WorkspaceArtifact(
                    stage_id=RunPlanStageId.METHOD_PREPARE,
                    label="Run plan snapshot",
                    path=run_plan_path,
                    kind="plan",
                ),
            ]
        )

        trajectory_metadata = TrajectoryArtifactMetadata(
            artifact_path=artifact_root / "slam" / "trajectory.tum",
            method=request.method,
            timestamp_source=request.capture.timestamp_source,
        )
        trajectory_metadata_path = trajectory_metadata.artifact_path.with_suffix(".metadata.json")
        dense_metadata = DenseArtifactMetadata(
            artifact_path=artifact_root / "dense" / "dense_points.ply",
            method=request.method,
        )
        dense_metadata_path = dense_metadata.artifact_path.with_suffix(".metadata.json")

        for stage in plan.stages:
            for output in stage.outputs:
                if output == capture_manifest_path:
                    continue
                if output == run_request_path or output == run_plan_path:
                    continue
                if output == trajectory_metadata_path or output == dense_metadata_path:
                    continue
                if not output.suffix:
                    output.mkdir(parents=True, exist_ok=True)
                    artifacts.append(
                        WorkspaceArtifact(
                            stage_id=stage.id,
                            label=output.name,
                            path=output,
                            kind="directory",
                        )
                    )
                    continue

                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(
                    self._placeholder_contents(output=output, stage_id=stage.id),
                    encoding="utf-8",
                )
                artifacts.append(
                    WorkspaceArtifact(
                        stage_id=stage.id,
                        label=output.name,
                        path=output,
                        kind=output.suffix.lstrip(".") or "file",
                        is_placeholder=True,
                    )
                )

        if not trajectory_metadata_path.exists():
            trajectory_metadata_path.write_text(
                self._render_json(trajectory_metadata.model_dump_jsonable()),
                encoding="utf-8",
            )
            artifacts.append(
                WorkspaceArtifact(
                    stage_id=RunPlanStageId.TRAJECTORY_NORMALIZATION,
                    label="trajectory.metadata.json",
                    path=trajectory_metadata_path,
                    kind="metadata",
                )
            )

        if request.enable_dense_mapping:
            if not dense_metadata_path.exists():
                dense_metadata_path.write_text(
                    self._render_json(dense_metadata.model_dump_jsonable()),
                    encoding="utf-8",
                )
                artifacts.append(
                    WorkspaceArtifact(
                        stage_id=RunPlanStageId.DENSE_NORMALIZATION,
                        label="dense_points.metadata.json",
                        path=dense_metadata_path,
                        kind="metadata",
                    )
                )

        return MaterializedWorkspace(
            artifact_root=artifact_root,
            capture_manifest_path=capture_manifest_path,
            run_request_path=run_request_path,
            run_plan_path=run_plan_path,
            artifacts=artifacts,
        )

    @staticmethod
    def _render_json(payload: dict[str, object]) -> str:
        return json.dumps(payload, indent=2, sort_keys=True) + "\n"

    def _placeholder_contents(self, *, output: Path, stage_id: RunPlanStageId) -> str:
        if output.suffix == ".json":
            payload = {
                "status": "placeholder",
                "stage_id": stage_id.value,
                "path": output.as_posix(),
            }
            return self._render_json(payload)
        if output.suffix == ".tum":
            return "# placeholder trajectory generated by WorkspaceMaterializerService\n"
        if output.suffix == ".ply":
            return "\n".join(
                [
                    "ply",
                    "format ascii 1.0",
                    "comment placeholder geometry generated by WorkspaceMaterializerService",
                    "element vertex 0",
                    "property float x",
                    "property float y",
                    "property float z",
                    "end_header",
                    "",
                ]
            )
        return f"placeholder artifact for stage {stage_id.value}\n"
