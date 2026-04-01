"""Reusable pipeline services shared by the CLI and UI."""

from __future__ import annotations

import re
from pathlib import Path

from prml_vslam.pipeline.contracts import MethodId, RunPlan, RunPlanRequest, RunPlanStage, RunPlanStageId


class PipelinePlannerService:
    """Build a lightweight typed execution plan for a benchmark run."""

    def build_plan(self, request: RunPlanRequest) -> RunPlan:
        """Build an ordered run plan from a typed planning request.

        Args:
            request: Planning inputs describing the dataset, method, and optional stages.

        Returns:
            Typed run plan with ordered stages and expected artifact paths.
        """
        artifact_root = request.output_dir / self._slugify(request.experiment_name) / request.method.value
        stages = self._build_stages(request=request, artifact_root=artifact_root)
        return RunPlan(
            experiment_name=request.experiment_name,
            mode=request.mode,
            method=request.method,
            input_video=request.video_path,
            artifact_root=artifact_root,
            stages=stages,
        )

    def _build_stages(self, *, request: RunPlanRequest, artifact_root: Path) -> list[RunPlanStage]:
        stages = [
            RunPlanStage(
                id=RunPlanStageId.INGEST,
                title="Ingest Video",
                summary=f"Decode frames at stride {request.frame_stride} and normalize benchmark metadata.",
                outputs=[
                    artifact_root / "input" / "frames",
                    artifact_root / "input" / "capture_manifest.json",
                ],
            ),
            RunPlanStage(
                id=RunPlanStageId.SLAM,
                title="Run SLAM Backend",
                summary=self._method_summary(request.method),
                outputs=[
                    artifact_root / "slam" / "trajectory.tum",
                    artifact_root / "slam" / "sparse_points.ply",
                ],
            ),
        ]

        if request.enable_dense_mapping:
            stages.append(
                RunPlanStage(
                    id=RunPlanStageId.DENSE_MAPPING,
                    title="Export Dense Mapping",
                    summary="Generate dense geometry artifacts suitable for downstream quality evaluation.",
                    outputs=[artifact_root / "dense" / "dense_points.ply"],
                )
            )

        if request.compare_to_arcore:
            stages.append(
                RunPlanStage(
                    id=RunPlanStageId.ARCORE_COMPARISON,
                    title="Compare Against ARCore",
                    summary="Align the trajectory against ARCore outputs and compute comparison-ready artifacts.",
                    outputs=[artifact_root / "evaluation" / "arcore_alignment.json"],
                )
            )

        if request.build_ground_truth_cloud:
            stages.append(
                RunPlanStage(
                    id=RunPlanStageId.REFERENCE_RECONSTRUCTION,
                    title="Build Reference Reconstruction",
                    summary="Reserve the offline reconstruction step used as a dense geometry reference.",
                    outputs=[artifact_root / "reference" / "reference_cloud.ply"],
                )
            )

        return stages

    @staticmethod
    def _method_summary(method: MethodId) -> str:
        match method:
            case MethodId.VISTA_SLAM:
                return "Plan the ViSTA-SLAM wrapper and export trajectory plus sparse geometry artifacts."
            case MethodId.MAST3R_SLAM:
                return "Plan the MASt3R-SLAM wrapper and export trajectory plus sparse geometry artifacts."

    @staticmethod
    def _slugify(experiment_name: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", experiment_name.strip().lower())
        return slug.strip("-") or "experiment"
