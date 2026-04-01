"""Reusable pipeline services shared by the CLI and UI."""

from __future__ import annotations

import json
import re
from pathlib import Path

from prml_vslam.pipeline.contracts import (
    CaptureManifest,
    MaterializedWorkspace,
    MethodId,
    PipelineMode,
    RunPlan,
    RunPlanRequest,
    RunPlanStage,
    RunPlanStageId,
)


class PipelinePlannerService:
    """Build typed execution plans for benchmark runs."""

    def build_plan(self, request: RunPlanRequest) -> RunPlan:
        """Build an ordered run plan from a typed planning request."""
        artifact_root = self._artifact_root(request)
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
        return CaptureManifest(
            experiment_name=request.experiment_name,
            mode=request.mode,
            method=request.method,
            input_video=request.video_path,
            output_root=self._artifact_root(request),
            frame_stride=request.frame_stride,
            capture=request.capture,
        )

    def _build_stages(self, *, request: RunPlanRequest, artifact_root: Path) -> list[RunPlanStage]:
        if request.mode is PipelineMode.STREAMING:
            return self._build_streaming_stages(request=request, artifact_root=artifact_root)
        return self._build_batch_stages(request=request, artifact_root=artifact_root)

    def _build_batch_stages(self, *, request: RunPlanRequest, artifact_root: Path) -> list[RunPlanStage]:
        stages = [
            RunPlanStage(
                id=RunPlanStageId.CAPTURE_MANIFEST,
                title="Capture Manifest",
                summary=(
                    "Persist the repo-owned manifest that records video provenance, "
                    "capture metadata, and optional side channels."
                ),
                outputs=[artifact_root / "input" / "capture_manifest.json"],
            ),
            RunPlanStage(
                id=RunPlanStageId.VIDEO_DECODE,
                title="Video Decode",
                summary=(
                    f"Decode the input video at frame stride {request.frame_stride} "
                    "into the normalized input workspace."
                ),
                outputs=[artifact_root / "input" / "frames"],
            ),
            RunPlanStage(
                id=RunPlanStageId.METHOD_PREPARE,
                title="Method Prepare",
                summary=(
                    "Resolve wrapper inputs, checkpoints, and execution assumptions "
                    "before invoking the external backend."
                ),
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
                summary=(
                    "Persist the normalized TUM trajectory together with explicit frame, unit, and timestamp metadata."
                ),
                outputs=[artifact_root / "slam" / "trajectory.metadata.json"],
            ),
        ]

        if request.enable_dense_mapping:
            stages.append(
                RunPlanStage(
                    id=RunPlanStageId.DENSE_NORMALIZATION,
                    title="Normalize Dense Geometry",
                    summary=(
                        "Persist the normalized dense geometry artifact together with explicit comparison metadata."
                    ),
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
                    summary=(
                        "Materialize the baseline-alignment placeholder without "
                        "hiding ARCore logic inside the method wrapper."
                    ),
                    outputs=[artifact_root / "evaluation" / "arcore_alignment.json"],
                )
            )

        if request.build_ground_truth_cloud:
            stages.append(
                RunPlanStage(
                    id=RunPlanStageId.REFERENCE_RECONSTRUCTION,
                    title="Reserve Reference Reconstruction",
                    summary=("Reserve the offline reference geometry stage used for later dense comparison."),
                    outputs=[artifact_root / "reference" / "reference_cloud.ply"],
                )
            )

        stages.append(
            RunPlanStage(
                id=RunPlanStageId.VISUALIZATION_EXPORT,
                title="Visualization Export",
                summary="Reserve the dashboard surfaces that summarize the planned run.",
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
                summary=("Flush the live run into repo-owned normalized artifacts and summaries."),
                outputs=[artifact_root / "visualization" / "plan_summary.json"],
            ),
        ]
        return stages

    @staticmethod
    def _artifact_root(request: RunPlanRequest) -> Path:
        return (
            request.output_dir
            / PipelinePlannerService._slugify(request.experiment_name)
            / request.mode.value
            / request.method.value
        )

    @staticmethod
    def _method_summary(method: MethodId) -> str:
        match method:
            case MethodId.VISTA_SLAM:
                return "Plan the ViSTA-SLAM wrapper with explicit uncalibrated assumptions and repo-owned outputs."
            case MethodId.MAST3R_SLAM:
                return (
                    "Plan the MASt3R-SLAM wrapper with explicit pointmap-driven dense "
                    "outputs and repo-owned normalization."
                )

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

        capture_manifest_path.parent.mkdir(parents=True, exist_ok=True)
        capture_manifest_path.write_text(self._render_json(manifest.model_dump_jsonable()), encoding="utf-8")

        run_request_path.parent.mkdir(parents=True, exist_ok=True)
        request.save_toml(run_request_path)
        plan.save_toml(run_plan_path)
        trajectory_metadata_path = artifact_root / "slam" / "trajectory.metadata.json"
        dense_metadata_path = artifact_root / "dense" / "dense_points.metadata.json"

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
                    continue

                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(
                    self._placeholder_contents(output=output, stage_id=stage.id),
                    encoding="utf-8",
                )

        if not trajectory_metadata_path.exists():
            trajectory_metadata_path.write_text(
                self._render_json(
                    {
                        "artifact_path": (artifact_root / "slam" / "trajectory.tum").as_posix(),
                        "method": request.method.value,
                        "format": "tum",
                        "frame_name": "world",
                        "transform_convention": "T_world_camera",
                        "units": "meters",
                        "timestamp_source": request.capture.timestamp_source.value,
                    }
                ),
                encoding="utf-8",
            )

        if request.enable_dense_mapping:
            if not dense_metadata_path.exists():
                dense_metadata_path.write_text(
                    self._render_json(
                        {
                            "artifact_path": (artifact_root / "dense" / "dense_points.ply").as_posix(),
                            "method": request.method.value,
                            "format": "ply",
                            "frame_name": "world",
                            "units": "meters",
                            "color_available": False,
                        }
                    ),
                    encoding="utf-8",
                )

        return MaterializedWorkspace(
            artifact_root=artifact_root,
            capture_manifest_path=capture_manifest_path,
            run_request_path=run_request_path,
            run_plan_path=run_plan_path,
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
