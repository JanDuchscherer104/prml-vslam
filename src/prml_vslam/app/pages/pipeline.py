"""Static Streamlit page describing the typed pipeline planning surface."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import streamlit as st

from prml_vslam.methods import MethodId
from prml_vslam.pipeline import (
    ArtifactRef,
    BenchmarkEvaluationConfig,
    CloudMetrics,
    DenseArtifacts,
    DenseConfig,
    EfficiencyMetrics,
    LiveSourceSpec,
    PipelineMode,
    ReferenceArtifacts,
    ReferenceConfig,
    RunPlan,
    RunRequest,
    RunSummary,
    SequenceManifest,
    StageExecutionStatus,
    StageManifest,
    TrackingArtifacts,
    TrackingConfig,
    TrajectoryMetrics,
    VideoSourceSpec,
)
from prml_vslam.utils import PathConfig

from ..ui import render_page_intro

if TYPE_CHECKING:
    from ..bootstrap import AppContext


@dataclass(slots=True, frozen=True)
class PipelineExample:
    """One static example shown in the pipeline guidance page."""

    title: str
    summary: str
    request: RunRequest
    code: str


@dataclass(slots=True, frozen=True)
class MockRunDossier:
    """One typed mock run used to demonstrate pipeline outputs."""

    request: RunRequest
    plan: RunPlan
    sequence: SequenceManifest
    tracking: TrackingArtifacts
    dense: DenseArtifacts
    reference: ReferenceArtifacts
    trajectory_metrics: TrajectoryMetrics
    cloud_metrics: CloudMetrics
    efficiency_metrics: EfficiencyMetrics
    stage_manifests: list[StageManifest]
    summary: RunSummary


def render(context: AppContext) -> None:
    """Render a lightweight guide to the pipeline planning API."""
    render_page_intro(
        eyebrow="Planning Surface",
        title="Pipeline Planning",
        body=(
            "Review the typed run-planning API, the direct request shape used to compose stages, "
            "and the exact stage rows produced by one benchmark-style request."
        ),
    )
    st.info("This page is descriptive only. It materializes `RunPlan` objects in memory and never executes a backend.")
    examples = _build_examples(context.path_config)
    mock_run = _build_mock_run(context.path_config)
    with st.container(border=True):
        st.subheader("Example Pipelines")
        for column, example in zip(st.columns(len(examples), gap="large"), examples, strict=True):
            plan = example.request.build(context.path_config)
            with column:
                st.markdown(f"**{example.title}**")
                st.write(example.summary)
                st.caption("Stages")
                st.markdown("\n".join(f"- `{stage.id.value}`" for stage in plan.stages))
    with st.container(border=True):
        st.subheader("Design Pattern")
        st.markdown(
            "\n".join(
                [
                    "- `RunRequest(...)` owns the normalized source, the output root, the tracking config, and the stage toggles.",
                    "- `DenseConfig`, `ReferenceConfig`, and `BenchmarkEvaluationConfig` make enabled stages explicit in one typed payload.",
                    "- `.build(path_config)` materializes a typed `RunPlan` with ordered `RunPlanStage` rows and canonical artifact paths.",
                ]
            )
        )
    with st.container(border=True):
        st.subheader("How To Use It")
        st.code(examples[1].code, language="python")
    with st.container(border=True):
        st.subheader("Request Shape")
        request_tab, config_tab, output_tab = st.tabs(["Direct Request", "Config Serialization", "Output Aliases"])
        with request_tab:
            st.caption("The request stays explicit: stages only exist when their nested config toggles are enabled.")
            st.code(_request_shape_code(), language="python")
        with config_tab:
            st.caption(
                "`RunRequest` inherits `BaseConfig`, so JSON-friendly and TOML-friendly views are already available."
            )
            left, right = st.columns(2, gap="large")
            left.code(_json_dump(mock_run.request.model_dump_jsonable()), language="json")
            right.code(mock_run.request.to_toml(), language="toml")
        with output_tab:
            st.caption(
                "Artifact and metric wrappers keep their public dump keys even though storage shapes are shared."
            )
            left, right = st.columns(2, gap="large")
            left.code(_json_dump(mock_run.dense.model_dump(mode="json")), language="json")
            right.code(_json_dump(mock_run.trajectory_metrics.model_dump(mode="json")), language="json")
    with st.container(border=True):
        st.subheader("Generated Plan")
        st.caption("Rows below come from the benchmark example above and show what the executor would receive.")
        st.dataframe(_stage_rows(examples[1].request.build(context.path_config)), hide_index=True, width="stretch")
    with st.container(border=True):
        st.subheader("Mock Run")
        st.caption(
            "This mock dossier shows what a completed benchmark run could look like after planning and execution."
        )
        overview_tab, outputs_tab, execution_tab = st.tabs(["Overview", "Outputs", "Execution"])
        with overview_tab:
            metrics = st.columns(4, gap="small")
            metrics[0].metric("Run Id", mock_run.plan.run_id)
            metrics[1].metric("Method", mock_run.plan.method.display_name)
            metrics[2].metric("Stages", str(len(mock_run.plan.stages)))
            metrics[3].metric("Artifact Root", mock_run.plan.artifact_root.name)
            st.dataframe(_stage_rows(mock_run.plan), hide_index=True, width="stretch")
        with outputs_tab:
            st.dataframe(_output_rows(mock_run), hide_index=True, width="stretch")
            left, right = st.columns(2, gap="large")
            left.code(_json_dump(mock_run.sequence.model_dump(mode="json")), language="json")
            right.code(_json_dump(mock_run.tracking.model_dump(mode="json")), language="json")
        with execution_tab:
            st.dataframe(_stage_manifest_rows(mock_run.stage_manifests), hide_index=True, width="stretch")
            st.code(_json_dump(mock_run.summary.model_dump(mode="json")), language="json")


def _build_examples(path_config: PathConfig) -> list[PipelineExample]:
    output_dir = path_config.artifacts_dir
    disabled_eval = BenchmarkEvaluationConfig(
        compare_to_arcore=False,
        evaluate_cloud=False,
        evaluate_efficiency=False,
    )
    return [
        PipelineExample(
            title="Tracking Only",
            summary="A narrow offline plan that only normalizes input, runs tracking, and writes a summary.",
            request=RunRequest(
                experiment_name="tracking-only-demo",
                output_dir=output_dir,
                source=VideoSourceSpec(video_path=path_config.captures_dir / "tracking-only.mp4"),
                tracking=TrackingConfig(method=MethodId.VISTA, max_frames=300),
                dense=DenseConfig(enabled=False),
                evaluation=disabled_eval.model_copy(deep=True),
            ),
            code=_tracking_only_code(),
        ),
        PipelineExample(
            title="Benchmark",
            summary="An explicit request that opts into dense export, reference reconstruction, and evaluation.",
            request=RunRequest(
                experiment_name="benchmark-demo",
                output_dir=output_dir,
                source=VideoSourceSpec(video_path=path_config.captures_dir / "lobby.mp4", frame_stride=2),
                tracking=TrackingConfig(method=MethodId.VISTA),
                dense=DenseConfig(enabled=True),
                reference=ReferenceConfig(enabled=True),
                evaluation=BenchmarkEvaluationConfig(
                    compare_to_arcore=True,
                    evaluate_cloud=True,
                    evaluate_efficiency=True,
                ),
            ),
            code=_benchmark_code(),
        ),
        PipelineExample(
            title="Live Capture",
            summary="A streaming plan that captures a live source, tracks it, and keeps optional offline stages disabled.",
            request=RunRequest(
                experiment_name="live-capture-demo",
                mode=PipelineMode.STREAMING,
                output_dir=output_dir,
                source=LiveSourceSpec(source_id="record3d_usb", persist_capture=True),
                tracking=TrackingConfig(method=MethodId.MSTR),
                dense=DenseConfig(enabled=False),
                evaluation=disabled_eval.model_copy(deep=True),
            ),
            code=_live_capture_code(),
        ),
    ]


def _build_mock_run(path_config: PathConfig) -> MockRunDossier:
    request = RunRequest(
        experiment_name="mock-lobby-benchmark",
        output_dir=path_config.artifacts_dir,
        source=VideoSourceSpec(video_path=path_config.captures_dir / "lobby.mp4", frame_stride=2),
        tracking=TrackingConfig(method=MethodId.VISTA),
        dense=DenseConfig(enabled=True),
        reference=ReferenceConfig(enabled=True),
        evaluation=BenchmarkEvaluationConfig(
            compare_to_arcore=True,
            evaluate_cloud=True,
            evaluate_efficiency=True,
        ),
    )
    plan = request.build(path_config)
    run_paths = path_config.plan_run_paths(
        experiment_name=request.experiment_name,
        method_slug=plan.method.artifact_slug,
        output_dir=request.output_dir,
    )
    sequence = SequenceManifest(
        sequence_id="lobby-demo",
        video_path=request.source.video_path if isinstance(request.source, VideoSourceSpec) else None,
        rgb_dir=run_paths.input_frames_dir,
        timestamps_path=run_paths.capture_manifest_path,
        intrinsics_path=run_paths.capture_manifest_path.with_name("camera_intrinsics.json"),
        reference_tum_path=run_paths.reference_cloud_path.with_suffix(".tum"),
        arcore_tum_path=run_paths.arcore_alignment_path.with_suffix(".tum"),
    )
    tracking = TrackingArtifacts(
        trajectory_tum=_artifact(run_paths.trajectory_path, kind="tum", fingerprint="track-trajectory-v1"),
        sparse_points_ply=_artifact(run_paths.sparse_points_path, kind="ply", fingerprint="track-sparse-v1"),
        preview_log_jsonl=_artifact(
            run_paths.artifact_root / "slam" / "preview_log.jsonl", kind="jsonl", fingerprint="preview-log-v1"
        ),
    )
    dense = DenseArtifacts(
        dense_points_ply=_artifact(run_paths.dense_points_path, kind="ply", fingerprint="dense-points-v1")
    )
    reference = ReferenceArtifacts(
        reference_cloud_ply=_artifact(run_paths.reference_cloud_path, kind="ply", fingerprint="reference-cloud-v1")
    )
    trajectory_metrics = TrajectoryMetrics(
        metrics_json=_artifact(run_paths.trajectory_metrics_path, kind="json", fingerprint="trajectory-metrics-v1")
    )
    cloud_metrics = CloudMetrics(
        metrics_json=_artifact(run_paths.cloud_metrics_path, kind="json", fingerprint="cloud-metrics-v1")
    )
    efficiency_metrics = EfficiencyMetrics(
        metrics_json=_artifact(run_paths.efficiency_metrics_path, kind="json", fingerprint="efficiency-metrics-v1")
    )
    stage_status = {
        plan.stages[0].id: StageExecutionStatus.HIT,
        plan.stages[1].id: StageExecutionStatus.RAN,
        plan.stages[2].id: StageExecutionStatus.RAN,
        plan.stages[3].id: StageExecutionStatus.HIT,
        plan.stages[4].id: StageExecutionStatus.RAN,
        plan.stages[5].id: StageExecutionStatus.RAN,
        plan.stages[6].id: StageExecutionStatus.RAN,
        plan.stages[7].id: StageExecutionStatus.RAN,
    }
    stage_manifests = [
        StageManifest(
            stage_id=stage.id,
            config_hash=f"cfg-{stage.id.value}-v1",
            input_fingerprint=f"inputs-{stage.id.value}-v1",
            output_paths={path.stem: path for path in stage.outputs},
            status=stage_status[stage.id],
        )
        for stage in plan.stages
    ]
    summary = RunSummary(run_id=plan.run_id, artifact_root=plan.artifact_root, stage_status=stage_status)
    return MockRunDossier(
        request=request,
        plan=plan,
        sequence=sequence,
        tracking=tracking,
        dense=dense,
        reference=reference,
        trajectory_metrics=trajectory_metrics,
        cloud_metrics=cloud_metrics,
        efficiency_metrics=efficiency_metrics,
        stage_manifests=stage_manifests,
        summary=summary,
    )


def _stage_rows(plan: RunPlan) -> list[dict[str, str]]:
    return [
        {
            "Stage": stage.title,
            "Id": stage.id.value,
            "Outputs": ", ".join(path.name for path in stage.outputs),
        }
        for stage in plan.stages
    ]


def _output_rows(mock_run: MockRunDossier) -> list[dict[str, str]]:
    return [
        {
            "Contract": "SequenceManifest",
            "Primary Output": mock_run.sequence.rgb_dir.name if mock_run.sequence.rgb_dir is not None else "None",
            "Serialized Keys": ", ".join(mock_run.sequence.model_dump(mode="json").keys()),
        },
        {
            "Contract": "TrackingArtifacts",
            "Primary Output": mock_run.tracking.trajectory_tum.path.name,
            "Serialized Keys": ", ".join(mock_run.tracking.model_dump(mode="json").keys()),
        },
        {
            "Contract": "DenseArtifacts",
            "Primary Output": mock_run.dense.dense_points_ply.path.name,
            "Serialized Keys": ", ".join(mock_run.dense.model_dump(mode="json").keys()),
        },
        {
            "Contract": "ReferenceArtifacts",
            "Primary Output": mock_run.reference.reference_cloud_ply.path.name,
            "Serialized Keys": ", ".join(mock_run.reference.model_dump(mode="json").keys()),
        },
        {
            "Contract": "TrajectoryMetrics",
            "Primary Output": mock_run.trajectory_metrics.metrics_json.path.name,
            "Serialized Keys": ", ".join(mock_run.trajectory_metrics.model_dump(mode="json").keys()),
        },
        {
            "Contract": "CloudMetrics",
            "Primary Output": mock_run.cloud_metrics.metrics_json.path.name,
            "Serialized Keys": ", ".join(mock_run.cloud_metrics.model_dump(mode="json").keys()),
        },
        {
            "Contract": "EfficiencyMetrics",
            "Primary Output": mock_run.efficiency_metrics.metrics_json.path.name,
            "Serialized Keys": ", ".join(mock_run.efficiency_metrics.model_dump(mode="json").keys()),
        },
    ]


def _stage_manifest_rows(stage_manifests: list[StageManifest]) -> list[dict[str, str]]:
    return [
        {
            "Stage": manifest.stage_id.value,
            "Status": manifest.status.value,
            "Config Hash": manifest.config_hash,
            "Outputs": ", ".join(path.name for path in manifest.output_paths.values()),
        }
        for manifest in stage_manifests
    ]


def _artifact(path: Path, *, kind: str, fingerprint: str) -> ArtifactRef:
    return ArtifactRef(path=path, kind=kind, fingerprint=fingerprint)


def _json_dump(payload: object) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


def _request_shape_code() -> str:
    return """request = RunRequest(
    ...,
    tracking=TrackingConfig(...),
    dense=DenseConfig(enabled=True),
    reference=ReferenceConfig(enabled=False),
    evaluation=BenchmarkEvaluationConfig(
        compare_to_arcore=True,
        evaluate_cloud=False,
        evaluate_efficiency=True,
    ),
)

plan = request.build(path_config)
request.inspect(show_docs=True)
request.model_dump_jsonable()
request.to_toml()"""


def _tracking_only_code() -> str:
    return """from pathlib import Path

from prml_vslam.methods import MethodId
from prml_vslam.pipeline import BenchmarkEvaluationConfig, DenseConfig, RunRequest, TrackingConfig, VideoSourceSpec

plan = RunRequest(
    experiment_name="tracking-only-demo",
    output_dir=Path("artifacts"),
    source=VideoSourceSpec(video_path=Path("captures/tracking-only.mp4")),
    tracking=TrackingConfig(method=MethodId.VISTA, max_frames=300),
    dense=DenseConfig(enabled=False),
    evaluation=BenchmarkEvaluationConfig(
        compare_to_arcore=False,
        evaluate_cloud=False,
        evaluate_efficiency=False,
    ),
).build(path_config)"""


def _benchmark_code() -> str:
    return """from pathlib import Path

from prml_vslam.methods import MethodId
from prml_vslam.pipeline import BenchmarkEvaluationConfig, DenseConfig, ReferenceConfig, RunRequest, TrackingConfig, VideoSourceSpec

plan = RunRequest(
    experiment_name="benchmark-demo",
    output_dir=Path("artifacts"),
    source=VideoSourceSpec(video_path=Path("captures/lobby.mp4"), frame_stride=2),
    tracking=TrackingConfig(method=MethodId.VISTA),
    dense=DenseConfig(enabled=True),
    reference=ReferenceConfig(enabled=True),
    evaluation=BenchmarkEvaluationConfig(
        compare_to_arcore=True,
        evaluate_cloud=True,
        evaluate_efficiency=True,
    ),
).build(path_config)"""


def _live_capture_code() -> str:
    return """from pathlib import Path

from prml_vslam.methods import MethodId
from prml_vslam.pipeline import BenchmarkEvaluationConfig, DenseConfig, LiveSourceSpec, PipelineMode, RunRequest, TrackingConfig

plan = RunRequest(
    experiment_name="live-capture-demo",
    mode=PipelineMode.STREAMING,
    output_dir=Path("artifacts"),
    source=LiveSourceSpec(source_id="record3d_usb", persist_capture=True),
    tracking=TrackingConfig(method=MethodId.MSTR),
    dense=DenseConfig(enabled=False),
    evaluation=BenchmarkEvaluationConfig(
        compare_to_arcore=False,
        evaluate_cloud=False,
        evaluate_efficiency=False,
    ),
).build(path_config)"""


__all__ = ["render"]
