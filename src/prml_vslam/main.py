"""CLI entry point for the project scaffold."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Annotated

import typer

from prml_vslam.datasets.advio import (
    AdvioDatasetService,
    AdvioDownloadPreset,
    AdvioDownloadRequest,
    AdvioModality,
    AdvioPoseSource,
)
from prml_vslam.io import Record3DStreamConfig
from prml_vslam.methods import MethodId
from prml_vslam.pipeline import PipelineMode, RunRequest
from prml_vslam.pipeline.contracts import (
    BenchmarkEvaluationConfig,
    ReferenceConfig,
    SlamConfig,
    VideoSourceSpec,
)
from prml_vslam.pipeline.demo import build_advio_demo_request, load_run_request_toml, persist_advio_demo_request
from prml_vslam.pipeline.run_service import RunService
from prml_vslam.pipeline.session import PipelineSessionSnapshot, PipelineSessionState
from prml_vslam.utils.console import Console
from prml_vslam.utils.path_config import get_path_config

app = typer.Typer(
    add_completion=False,
    no_args_is_help=False,
    help="Utilities and entry points for the PRML monocular VSLAM project scaffold.",
)
advio_app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="ADVIO dataset inspection and download helpers.",
)
console = Console(__name__)

app.add_typer(advio_app, name="advio")


@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context) -> None:
    """Run the offline pipeline demo when the CLI is invoked without a subcommand."""
    if ctx.invoked_subcommand is None:
        pipeline_demo()


@app.command()
def info() -> None:
    """Print a short summary of the current scaffold."""
    console.print(
        "[bold]prml-vslam[/bold]: editable Python package, typed pipeline planner, "
        "Streamlit workbench, and report/slides scaffold."
    )


@app.command("plan-run")
def plan_run(
    experiment_name: Annotated[str, typer.Argument(help="Human-readable experiment name.")],
    video_path: Annotated[Path, typer.Argument(help="Path to the input video.")],
    output_dir: Annotated[Path, typer.Option("--output-dir", help="Root directory for benchmark artifacts.")] = Path(
        ".artifacts"
    ),
    method: Annotated[
        MethodId,
        typer.Option(
            "--method",
            help="External monocular VSLAM backend to plan for.",
            case_sensitive=False,
        ),
    ] = MethodId.VISTA,
    frame_stride: Annotated[int, typer.Option(min=1, max=30, help="Frame subsampling stride.")] = 1,
    dense_mapping: Annotated[
        bool,
        typer.Option("--dense/--no-dense", help="Whether the plan should include dense map export."),
    ] = True,
    compare_to_arcore: Annotated[
        bool,
        typer.Option(
            "--arcore/--no-arcore",
            help="Whether the plan assumes ARCore comparison data is available.",
        ),
    ] = True,
    ground_truth_cloud: Annotated[
        bool,
        typer.Option(
            "--reference-cloud/--no-reference-cloud",
            help="Whether the plan reserves a reference reconstruction stage.",
        ),
    ] = True,
) -> None:
    """Build a typed benchmark run plan from the CLI."""
    request = RunRequest(
        experiment_name=experiment_name,
        output_dir=output_dir,
        source=VideoSourceSpec(video_path=video_path, frame_stride=frame_stride),
        slam=SlamConfig(method=method, emit_dense_points=dense_mapping),
        reference=ReferenceConfig(enabled=ground_truth_cloud),
        evaluation=BenchmarkEvaluationConfig(
            compare_to_arcore=compare_to_arcore,
            evaluate_cloud=dense_mapping and ground_truth_cloud,
            evaluate_efficiency=True,
        ),
    )
    plan = request.build()
    console.plog(plan.model_dump(mode="json"))


@app.command("run")
def run_offline(
    experiment_name: Annotated[str, typer.Argument(help="Human-readable experiment name.")],
    video_path: Annotated[Path, typer.Argument(help="Path to the input video.")],
    output_dir: Annotated[Path, typer.Option("--output-dir", help="Root directory for benchmark artifacts.")] = Path(
        ".artifacts"
    ),
    frame_stride: Annotated[int, typer.Option(min=1, max=30, help="Frame subsampling stride.")] = 1,
    dense_mapping: Annotated[
        bool,
        typer.Option("--dense/--no-dense", help="Whether to emit a dense point cloud artifact."),
    ] = True,
    max_frames: Annotated[
        int | None,
        typer.Option("--max-frames", help="Optional hard cap on the number of frames processed."),
    ] = None,
) -> None:
    """Execute a full offline ViSTA-SLAM benchmark run end-to-end."""
    from prml_vslam.methods.vista_slam.config import VistaSlamBackendConfig
    from prml_vslam.methods.vista_slam.runner import VistaSlamBackend
    from prml_vslam.pipeline.contracts import SequenceManifest

    path_config = get_path_config()

    slam_cfg = SlamConfig(
        method=MethodId.VISTA,
        max_frames=max_frames,
        emit_dense_points=dense_mapping,
        emit_sparse_points=True,
    )
    request = RunRequest(
        experiment_name=experiment_name,
        output_dir=output_dir,
        source=VideoSourceSpec(video_path=video_path, frame_stride=frame_stride),
        slam=slam_cfg,
    )
    plan = request.build(path_config)
    artifact_root = plan.artifact_root
    artifact_root.mkdir(parents=True, exist_ok=True)

    console.info("Run plan built — artifact root: %s", artifact_root)
    console.plog({"run_id": plan.run_id, "stages": [s.id.value for s in plan.stages]})

    sequence = SequenceManifest(
        sequence_id=plan.run_id,
        video_path=path_config.resolve_video_path(video_path),
    )

    backend_cfg = VistaSlamBackendConfig()
    backend = VistaSlamBackend(config=backend_cfg, path_config=path_config)

    try:
        artifacts = backend.run_sequence(sequence=sequence, cfg=slam_cfg, artifact_root=artifact_root)
    except RuntimeError as exc:
        console.error("ViSTA-SLAM run failed: %s", exc)
        raise typer.Exit(code=1) from exc

    console.info("Run complete.")
    console.plog(artifacts.model_dump(mode="json"))


@app.command("plan-run-config")
def plan_run_config(
    config_path: Annotated[
        Path,
        typer.Argument(
            help="Path to a RunRequest TOML file (repo-relative paths are resolved via PathConfig).",
        ),
    ],
) -> None:
    """Build a typed benchmark run plan from a TOML config file."""
    path_config = get_path_config()
    try:
        request = load_run_request_toml(path_config=path_config, config_path=config_path)
        plan = request.build(path_config)
    except Exception as exc:
        console.error(str(exc))
        raise typer.Exit(code=1) from exc
    console.plog(plan.model_dump(mode="json"))


@app.command("write-demo-config")
def write_demo_config(
    sequence_id: Annotated[
        int | None,
        typer.Option(
            "--sequence",
            help="ADVIO sequence id to use. Defaults to the first replay-ready local scene.",
        ),
    ] = None,
    mode: Annotated[
        PipelineMode,
        typer.Option(
            "--mode",
            help="Persist an offline or streaming ADVIO demo request.",
            case_sensitive=False,
        ),
    ] = PipelineMode.OFFLINE,
    method: Annotated[
        MethodId,
        typer.Option(
            "--method",
            help="Method id stored in the persisted demo request.",
            case_sensitive=False,
        ),
    ] = MethodId.VISTA,
    config_path: Annotated[
        Path | None,
        typer.Option(
            "--config-path",
            help="Optional output TOML path. Bare filenames resolve under .configs/pipelines/.",
        ),
    ] = None,
) -> None:
    """Persist the canonical ADVIO demo request as TOML."""
    path_config = get_path_config()
    advio_service = AdvioDatasetService(path_config)
    resolved_sequence_id = _resolve_demo_sequence_id(advio_service, explicit_sequence_id=sequence_id)
    scene = advio_service.scene(resolved_sequence_id)
    resolved_config_path = persist_advio_demo_request(
        path_config=path_config,
        sequence_id=scene.sequence_slug,
        mode=mode,
        method=method,
        config_path=config_path,
    )
    console.plog(
        {
            "config_path": str(resolved_config_path),
            "sequence_id": scene.sequence_slug,
            "mode": mode.value,
            "method": method.value,
        }
    )


@app.command("record3d-devices")
def record3d_devices() -> None:
    """List USB-connected Record3D devices visible to the bindings."""
    try:
        session = Record3DStreamConfig().setup_target()
        if session is None:
            raise RuntimeError("Failed to initialize the Record3D session.")
        devices = session.list_devices()
    except RuntimeError as exc:
        console.error(str(exc))
        raise typer.Exit(code=1) from exc

    if not devices:
        console.warning(
            "No Record3D devices detected. Connect the iPhone via USB, open Record3D, and enable USB Streaming mode."
        )
        return

    console.plog([device.model_dump(mode="json") for device in devices])


@app.command("pipeline-demo")
def pipeline_demo(
    sequence_id: Annotated[
        int | None,
        typer.Option(
            "--sequence",
            help="ADVIO sequence id to replay. Defaults to the first replay-ready local scene.",
        ),
    ] = None,
    mode: Annotated[
        PipelineMode,
        typer.Option(
            "--mode",
            help="Run one offline pass or loop the replay as a streaming session.",
            case_sensitive=False,
        ),
    ] = PipelineMode.OFFLINE,
    method: Annotated[
        MethodId,
        typer.Option(
            "--method",
            help="Mock SLAM backend label used by the bounded demo.",
            case_sensitive=False,
        ),
    ] = MethodId.VISTA,
    pose_source: Annotated[
        AdvioPoseSource,
        typer.Option(
            "--pose-source",
            help="Pose source injected into ADVIO replay packets.",
            case_sensitive=False,
        ),
    ] = AdvioPoseSource.GROUND_TRUTH,
    respect_video_rotation: Annotated[
        bool,
        typer.Option(
            "--respect-video-rotation/--ignore-video-rotation",
            help="Whether to honor ADVIO video rotation metadata during replay.",
        ),
    ] = False,
    poll_interval_seconds: Annotated[
        float,
        typer.Option(
            "--poll-interval",
            min=0.05,
            help="Seconds between status polls while the demo session is active.",
        ),
    ] = 0.2,
) -> None:
    """Run the bounded ADVIO replay demo without starting Streamlit."""
    path_config = get_path_config()
    advio_service = AdvioDatasetService(path_config)
    resolved_sequence_id = _resolve_demo_sequence_id(advio_service, explicit_sequence_id=sequence_id)
    scene = advio_service.scene(resolved_sequence_id)
    request = build_advio_demo_request(
        path_config=path_config,
        sequence_id=scene.sequence_slug,
        mode=mode,
        method=method,
    )
    source = advio_service.build_streaming_source(
        sequence_id=resolved_sequence_id,
        pose_source=pose_source,
        respect_video_rotation=respect_video_rotation,
    )
    run_service = RunService(path_config=path_config)
    console.info(
        "Starting pipeline demo for %s (%s, %s).",
        scene.display_name,
        mode.value,
        method.value,
    )
    try:
        run_service.start_run(request=request, source=source)
        snapshot = _wait_for_pipeline_terminal_snapshot(
            run_service,
            poll_interval_seconds=poll_interval_seconds,
        )
    except KeyboardInterrupt as exc:
        console.warning("Interrupted; stopping the active pipeline demo.")
        run_service.stop_run()
        snapshot = run_service.snapshot()
        _print_pipeline_demo_snapshot(snapshot)
        raise typer.Exit(code=130) from exc
    _print_pipeline_demo_snapshot(snapshot)
    if snapshot.state is PipelineSessionState.FAILED:
        raise typer.Exit(code=1)


@advio_app.command("summary")
def advio_summary() -> None:
    """Print committed and local ADVIO dataset coverage."""
    service = AdvioDatasetService(get_path_config())
    summary = service.summarize()
    payload = {
        "dataset_root": str(service.dataset_root),
        "upstream": service.catalog.upstream.model_dump(mode="json"),
        "summary": summary.model_dump(mode="json"),
        "local_sequence_ids": [
            status.scene.sequence_id for status in service.local_scene_statuses() if status.sequence_dir
        ],
    }
    console.plog(payload)


@advio_app.command("download")
def advio_download(
    sequence_ids: Annotated[
        list[int] | None,
        typer.Option("--sequence", help="Repeat to select one or more ADVIO sequence ids. Omit to target all scenes."),
    ] = None,
    preset: Annotated[
        AdvioDownloadPreset,
        typer.Option(
            "--preset",
            help="Curated modality bundle used when no explicit modality override is provided.",
            case_sensitive=False,
        ),
    ] = AdvioDownloadPreset.OFFLINE,
    modalities: Annotated[
        list[AdvioModality] | None,
        typer.Option(
            "--modality",
            help="Repeat to override the preset with explicit modality groups.",
            case_sensitive=False,
        ),
    ] = None,
    overwrite: Annotated[
        bool,
        typer.Option(
            "--overwrite/--reuse",
            help="Whether to re-download cached ZIPs and replace extracted files.",
        ),
    ] = False,
) -> None:
    """Download selected ADVIO scene archives and extract only requested modality bundles."""
    service = AdvioDatasetService(get_path_config())
    try:
        result = service.download(
            AdvioDownloadRequest(
                sequence_ids=[] if sequence_ids is None else sequence_ids,
                preset=preset,
                modalities=[] if modalities is None else modalities,
                overwrite=overwrite,
            )
        )
    except Exception as exc:
        console.error(str(exc))
        raise typer.Exit(code=1) from exc

    payload = {
        "result": result.model_dump(mode="json"),
        "summary": service.summarize().model_dump(mode="json"),
    }
    console.plog(payload)


def _resolve_demo_sequence_id(service: AdvioDatasetService, *, explicit_sequence_id: int | None) -> int:
    """Resolve one replay-ready ADVIO sequence for the CLI demo."""
    if explicit_sequence_id is not None:
        return explicit_sequence_id
    previewable_ids = [status.scene.sequence_id for status in service.local_scene_statuses() if status.replay_ready]
    if not previewable_ids:
        raise typer.BadParameter(
            "No replay-ready ADVIO scenes were found. Download the streaming bundle first or pass --sequence."
        )
    return previewable_ids[0]


def _wait_for_pipeline_terminal_snapshot(
    run_service: RunService,
    *,
    poll_interval_seconds: float,
) -> PipelineSessionSnapshot:
    """Poll the run service until the current demo session reaches a terminal state."""
    previous_state: PipelineSessionState | None = None
    previous_received_frames = -1
    while True:
        snapshot = run_service.snapshot()
        if snapshot.state is not previous_state:
            plan_run_id = None if snapshot.plan is None else snapshot.plan.run_id
            console.info(
                "Pipeline demo state: %s%s", snapshot.state.value, "" if plan_run_id is None else f" ({plan_run_id})"
            )
            previous_state = snapshot.state
        if snapshot.received_frames and snapshot.received_frames != previous_received_frames:
            console.info(
                "Frames=%d sparse=%d dense=%d",
                snapshot.received_frames,
                snapshot.num_sparse_points,
                snapshot.num_dense_points,
            )
            previous_received_frames = snapshot.received_frames
        if snapshot.state not in {PipelineSessionState.CONNECTING, PipelineSessionState.RUNNING}:
            return snapshot
        time.sleep(poll_interval_seconds)


def _print_pipeline_demo_snapshot(snapshot: PipelineSessionSnapshot) -> None:
    """Render the final CLI demo snapshot in a compact structured form."""
    payload = {
        "state": snapshot.state.value,
        "error_message": snapshot.error_message or None,
        "received_frames": snapshot.received_frames,
        "plan": None if snapshot.plan is None else snapshot.plan.model_dump(mode="json"),
        "sequence_manifest": None
        if snapshot.sequence_manifest is None
        else snapshot.sequence_manifest.model_dump(mode="json"),
        "slam": None if snapshot.slam is None else snapshot.slam.model_dump(mode="json"),
        "summary": None if snapshot.summary is None else snapshot.summary.model_dump(mode="json"),
    }
    console.plog(payload)


def main() -> None:
    """Run the Typer application."""
    app()


if __name__ == "__main__":
    main()
