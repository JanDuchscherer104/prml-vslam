"""CLI entry point for the project scaffold."""

from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
import tomllib
from collections.abc import Iterator
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, TextIO

import click
import typer
from pydantic import ValidationError
from rich.console import Console as RichConsole
from rich.panel import Panel
from rich.table import Table
from typer.core import TyperCommand

from prml_vslam.methods.stage.backend_config import MethodId
from prml_vslam.pipeline import PipelineMode
from prml_vslam.pipeline.config import RunConfig, build_run_config
from prml_vslam.pipeline.contracts.runtime import RunSnapshot, RunState
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.demo import (
    build_advio_demo_run_config,
    build_runtime_source_from_run_config,
    load_run_config_toml,
    persist_advio_demo_run_config,
)
from prml_vslam.pipeline.run_service import RunService
from prml_vslam.sources.config import (
    AdvioSourceConfig,
    Record3DDatasetSourceConfig,
    SourceBackendConfig,
    TumRgbdSourceConfig,
    VideoSourceConfig,
)
from prml_vslam.sources.contracts import PreparedBenchmarkInputs, ReferenceSource, SequenceManifest
from prml_vslam.sources.datasets.advio import (
    AdvioDatasetService,
    AdvioDownloadRequest,
    AdvioPoseFrameMode,
    AdvioPoseSource,
)
from prml_vslam.sources.datasets.build_config import NormalizedDatasetBuildConfig
from prml_vslam.sources.datasets.contracts import DatasetId, FrameSelectionConfig, ReferenceCloudConfig
from prml_vslam.sources.datasets.normalization import (
    dataset_id_for_source_config,
    dataset_service,
    default_frame_selection_for_dataset,
    normalize_dataset_entries,
    normalize_dataset_entry,
    normalize_dataset_source_configs,
    normalized_profile_for_dataset,
    normalized_store_for_service,
    parse_dataset_id,
)
from prml_vslam.sources.datasets.normalized_query import (
    NormalizedDatasetQuery,
    NormalizedSequenceRecord,
    query_normalized_dataset,
)
from prml_vslam.sources.datasets.normalized_store import NormalizedDatasetEntry
from prml_vslam.sources.datasets.record3d import Record3DDatasetService, Record3DDownloadRequest
from prml_vslam.sources.datasets.tum_rgbd import (
    TumRgbdDatasetService,
    TumRgbdDownloadRequest,
)
from prml_vslam.sources.record3d import Record3DStreamConfig
from prml_vslam.sources.stage.config import SourceStageConfig
from prml_vslam.utils.console import Console
from prml_vslam.utils.path_config import PathConfig, get_path_config

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Utilities and entry points for the PRML monocular VSLAM project scaffold.",
)
advio_app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="ADVIO dataset inspection and download helpers.",
)
tum_rgbd_app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="TUM RGB-D dataset inspection and download helpers.",
)
record3d_app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Record3D dataset inspection and download helpers.",
)
dataset_app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Normalized offline dataset store helpers.",
)
console = Console(__name__)
pipeline_demo_console = Console("pipeline.demo")

app.add_typer(advio_app, name="advio")
app.add_typer(tum_rgbd_app, name="tum-rgbd")
app.add_typer(record3d_app, name="record3d")
app.add_typer(dataset_app, name="dataset")


def _reference_trajectory_filename(source: ReferenceSource) -> str:
    return "ground_truth.tum" if source is ReferenceSource.GROUND_TRUTH else f"{source.value}.tum"


RUN_CONFIG_OVERRIDE_GROUPS: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    (
        "Run",
        (
            ("--experiment_name", "Run name stored in artifacts and summaries."),
            ("--mode", "Pipeline mode: offline or streaming."),
            ("--output_dir", "Artifact output directory."),
            ("--reuse_artifact_root", "Existing method artifact root for disabled source/SLAM reuse."),
        ),
    ),
    (
        "Source Stage",
        (
            ("--stages.source.enabled", "Enable or disable source normalization."),
            ("--stages.source.backend.source_id", "Source kind: video, advio, tum_rgbd, record3d_dataset, record3d."),
            ("--stages.source.backend.video_path", "Video source path when source_id=video."),
            ("--stages.source.backend.sequence_id", "Dataset sequence id for ADVIO, TUM RGB-D, or Record3D."),
            ("--stages.source.backend.frame_stride", "Frame sampling stride."),
            ("--stages.source.backend.target_fps", "Frame sampling target FPS."),
            ("--stages.source.backend.replay_mode", "Replay pacing: realtime or fast_as_possible."),
            ("--stages.source.backend.dataset_serving.pose_source", "ADVIO pose provider."),
            ("--stages.source.backend.dataset_serving.pose_frame_mode", "ADVIO replay pose frame mode."),
            ("--stages.source.backend.normalize_video_orientation", "Normalize video display orientation."),
            ("--stages.source.backend.transport", "Record3D transport: usb or wifi."),
            ("--stages.source.backend.device_index", "Record3D USB device index."),
            ("--stages.source.backend.device_address", "Record3D Wi-Fi device address."),
        ),
    ),
    (
        "SLAM Stage",
        (
            ("--stages.slam.enabled", "Enable or disable SLAM."),
            ("--stages.slam.outputs.emit_dense_points", "Materialize dense point outputs."),
            ("--stages.slam.outputs.emit_sparse_points", "Materialize sparse point outputs."),
            ("--stages.slam.backend.method_id", "SLAM backend: vista or mast3r."),
            ("--stages.slam.backend.max_frames", "Frame cap for smoke runs."),
            ("--stages.slam.backend.max_view_num", "ViSTA maximum pose-graph keyframes."),
            ("--stages.slam.backend.flow_thres", "ViSTA keyframe optical-flow threshold."),
            ("--stages.slam.backend.neighbor_edge_num", "ViSTA temporal-neighbor edges."),
            ("--stages.slam.backend.loop_edge_num", "ViSTA loop-closure edges."),
            ("--stages.slam.backend.loop_dist_min", "ViSTA loop candidate minimum frame distance."),
            ("--stages.slam.backend.loop_nms", "ViSTA loop non-maximum suppression window."),
            ("--stages.slam.backend.point_conf_thres", "ViSTA retained point-confidence threshold."),
            ("--stages.slam.backend.rel_pose_thres", "ViSTA relative-pose uncertainty threshold."),
            ("--stages.slam.backend.pgo_every", "ViSTA pose-graph optimization interval."),
            ("--stages.slam.backend.random_seed", "Backend random seed."),
            ("--stages.slam.backend.device", "ViSTA device: auto, cuda, cpu."),
        ),
    ),
    (
        "Downstream Stages",
        (
            ("--stages.align_ground.enabled", "Enable or disable gravity alignment."),
            ("--stages.align_ground.ground.strategy", "Ground-alignment strategy."),
            ("--stages.align_ground.ground.min_confidence", "Minimum ground-plane confidence."),
            ("--stages.align_trajectory.baseline_source", "Reference trajectory source for Sim(3) alignment."),
            ("--stages.evaluate_trajectory.enabled", "Enable trajectory evaluation."),
            ("--stages.evaluate_trajectory.evaluation.baseline_source", "Reference trajectory source."),
            ("--stages.reconstruction.enabled", "Enable reconstruction."),
            ("--stages.reconstruction.backend.method_id", "Reconstruction backend id."),
            ("--stages.reconstruction.backend.voxel_length_m", "TSDF voxel length in meters."),
            ("--stages.reconstruction.backend.sdf_trunc_m", "TSDF truncation distance in meters."),
            ("--stages.reconstruction.backend.depth_sampling_stride", "RGB-D reconstruction sampling stride."),
            ("--stages.reconstruction.backend.extract_mesh", "Extract a mesh after integration."),
            ("--stages.align_cloud.enabled", "Enable offline dense-cloud ICP alignment."),
            ("--stages.align_cloud.reference_source", "Preferred source-prepared reference cloud."),
            ("--stages.align_cloud.max_correspondence_distance_m", "ICP maximum correspondence distance in meters."),
            ("--stages.evaluate_cloud.enabled", "Enable dense-cloud diagnostic planning."),
            ("--stages.evaluate_cloud.selection.reference_artifact_key", "Reference cloud artifact key."),
            ("--stages.evaluate_cloud.selection.estimate_artifact_key", "Estimated cloud artifact key."),
            ("--stages.summary.enabled", "Enable summary projection."),
        ),
    ),
    (
        "Visualization",
        (
            ("--visualization.connect_live_viewer", "Attach a live Rerun viewer sink."),
            ("--visualization.export_viewer_rrd", "Export a repo-owned Rerun recording."),
            ("--visualization.grpc_url", "Rerun gRPC endpoint."),
            ("--visualization.viewer_blueprint_path", "Rerun viewer blueprint path."),
            ("--visualization.show_tracking_trajectory", "Show the tracking trajectory."),
            ("--visualization.trajectory_pose_axis_length", "Axis length for trajectory pose transforms."),
            ("--visualization.log_source_rgb", "Log source RGB frames."),
            ("--visualization.log_diagnostic_preview", "Log backend diagnostic previews."),
            (
                "--visualization.reference_point_cloud_decimation_keep_ratio",
                "Reference point-cloud Rerun keep ratio.",
            ),
        ),
    ),
    (
        "Runtime",
        (
            ("--ray_local_head_lifecycle", "Ray local-head lifecycle: ephemeral or reusable."),
            ("--ray_log_to_driver", "Forward Ray worker logs to the driver."),
        ),
    ),
)


class RunConfigOverrideCommand(TyperCommand):
    """Typer command that appends discoverable RunConfig dotted overrides."""

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """Render normal Typer help followed by RunConfig override paths."""
        super().format_help(ctx, formatter)
        _print_run_config_override_options()


def _print_run_config_override_options() -> None:
    console = RichConsole(file=click.get_text_stream("stdout"))
    for title, options in RUN_CONFIG_OVERRIDE_GROUPS:
        table = Table.grid(padding=(0, 2))
        table.add_column("Option", no_wrap=True)
        table.add_column("Meaning")
        for option, help_text in options:
            table.add_row(option, help_text)
        console.print(Panel(table, title=f"RunConfig Overrides - {title}", expand=False))

    notes = Table.grid(padding=(0, 2))
    notes.add_column("Topic", no_wrap=True)
    notes.add_column("Detail")
    notes.add_row("Value parsing", "JSON first, then string fallback. CLI overrides win over TOML.")
    notes.add_row("Object merge", "--stages.slam.outputs '{\"emit_dense_points\": false}'")
    notes.add_row("String value", "--mode '\"offline\"' or --mode offline")
    console.print(Panel(notes, title="RunConfig Override Syntax", expand=False))


@dataclass(slots=True)
class _RerunViewerProcess:
    """CLI-owned Rerun web viewer subprocess plus its stdout forwarder thread."""

    process: subprocess.Popen[str]
    forwarder: threading.Thread


@dataclass(frozen=True, slots=True)
class _ProcessInfo:
    """Process-table row used by the Rerun viewer cleanup command."""

    pid: int
    ppid: int
    pgid: int
    stat: str
    command: str


_ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


class _TimestampedRunLogTee:
    """Mirror terminal output to one timestamped plain-text run log."""

    def __init__(self, *, target: TextIO, log_handle: TextIO, lock: threading.Lock) -> None:
        self._target = target
        self._log_handle = log_handle
        self._lock = lock
        self._pending = ""

    @property
    def encoding(self) -> str:
        return getattr(self._target, "encoding", None) or "utf-8"

    def write(self, text: str) -> int:
        self._target.write(text)
        with self._lock:
            self._pending += text
            while "\n" in self._pending:
                line, self._pending = self._pending.split("\n", maxsplit=1)
                self._write_log_line(line)
        return len(text)

    def flush(self) -> None:
        self._target.flush()
        self._log_handle.flush()

    def isatty(self) -> bool:
        return bool(getattr(self._target, "isatty", lambda: False)())

    def close_log_line(self) -> None:
        with self._lock:
            if self._pending:
                self._write_log_line(self._pending)
                self._pending = ""

    def _write_log_line(self, line: str) -> None:
        timestamp = datetime.now().astimezone().isoformat(timespec="milliseconds")
        self._log_handle.write(f"{timestamp} {_ANSI_ESCAPE_PATTERN.sub('', line)}\n")
        self._log_handle.flush()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._target, name)


@contextmanager
def _capture_run_config_logs(*, path_config: PathConfig, run_id: str) -> Iterator[Path]:
    """Capture one `run-config` command invocation to a timestamped run log."""
    log_dir = path_config.resolve_run_logs_dir(run_id, create=True)
    timestamp = datetime.now().astimezone().strftime("%Y-%m-%d_%H:%M:%S")
    log_path = log_dir / f"{timestamp}_{run_id}.log"
    lock = threading.Lock()
    with log_path.open("w", encoding="utf-8") as log_handle:
        stdout_tee = _TimestampedRunLogTee(target=sys.stdout, log_handle=log_handle, lock=lock)
        stderr_tee = _TimestampedRunLogTee(target=sys.stderr, log_handle=log_handle, lock=lock)
        try:
            with redirect_stdout(stdout_tee), redirect_stderr(stderr_tee):
                yield log_path
        finally:
            stdout_tee.close_log_line()
            stderr_tee.close_log_line()
            stdout_tee.flush()
            stderr_tee.flush()


def _build_rerun_viewer_command(*, run_config: RunConfig, path_config: PathConfig) -> list[str]:
    """Build the authoritative `uv run ... rerun --serve-web` command."""
    command = ["uv", "run", "rerun"]
    blueprint_path = run_config.visualization.viewer_blueprint_path
    if blueprint_path is not None:
        command.append(path_config.resolve_repo_path(blueprint_path).as_posix())
    command.append("--serve-web")
    return command


def _forward_rerun_viewer_stdout(*, stream: TextIO, target: TextIO | None = None) -> None:
    """Forward merged child output into the main process stdout."""
    output = sys.stdout if target is None else target
    try:
        for line in stream:
            output.write(f"[rerun] {line}")
            if not line.endswith("\n"):
                output.write("\n")
            output.flush()
    finally:
        stream.close()


def _launch_rerun_viewer(*, run_config: RunConfig, path_config: PathConfig) -> _RerunViewerProcess | None:
    """Start the best-effort CLI-owned Rerun web viewer when configured."""
    if not run_config.visualization.connect_live_viewer:
        return None
    command = _build_rerun_viewer_command(run_config=run_config, path_config=path_config)
    try:
        process = subprocess.Popen(
            command,
            cwd=path_config.root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            start_new_session=True,
        )
    except OSError as exc:
        console.warning("Failed to launch the Rerun viewer subprocess: %s", exc)
        return None
    if process.stdout is None:
        console.warning("Rerun viewer started without a stdout pipe; continuing without forwarded viewer logs.")
        if process.poll() is None:
            process.terminate()
        return None
    forwarder = threading.Thread(
        target=_forward_rerun_viewer_stdout,
        kwargs={"stream": process.stdout},
        daemon=True,
        name="rerun-viewer-stdout",
    )
    forwarder.start()
    time.sleep(0.2)
    if process.poll() is not None:
        console.warning(
            "Rerun viewer exited early with code %s; continuing without auto-launched live viewer.",
            process.returncode,
        )
        return None
    return _RerunViewerProcess(process=process, forwarder=forwarder)


def _shutdown_rerun_viewer(viewer: _RerunViewerProcess | None) -> None:
    """Terminate the CLI-owned Rerun viewer subprocess and release its pipe."""
    if viewer is None:
        return
    process = viewer.process
    if process.poll() is None:
        _terminate_process_group(process, signal.SIGTERM)
        try:
            process.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            _terminate_process_group(process, signal.SIGKILL)
            process.wait(timeout=5.0)
    if process.stdout is not None and not process.stdout.closed:
        process.stdout.close()
    viewer.forwarder.join(timeout=1.0)


def _wait_for_rerun_viewer_close(viewer: _RerunViewerProcess | None) -> None:
    """Keep an auto-launched viewer alive after the pipeline reaches terminal state."""
    if viewer is None or viewer.process.poll() is not None:
        return
    console.info("Rerun viewer is still running; press Ctrl+C to close it.")
    try:
        viewer.process.wait()
    except KeyboardInterrupt:
        return


def _list_processes() -> list[_ProcessInfo]:
    """Read the host process table in the same shape the cleanup command needs."""
    result = subprocess.run(
        ["ps", "-eo", "pid=,ppid=,pgid=,stat=,command="],
        check=True,
        capture_output=True,
        text=True,
    )
    processes: list[_ProcessInfo] = []
    for line in result.stdout.splitlines():
        parts = line.strip().split(maxsplit=4)
        if len(parts) != 5:
            continue
        pid, ppid, pgid, stat, command = parts
        processes.append(
            _ProcessInfo(
                pid=int(pid),
                ppid=int(ppid),
                pgid=int(pgid),
                stat=stat,
                command=command,
            )
        )
    return processes


def _is_rerun_viewer_process(process: _ProcessInfo) -> bool:
    """Return true for auto-launched Rerun web viewer processes."""
    command = process.command
    if "--serve-web" not in command:
        return False
    if "kill-rerun" in command:
        return False
    rerun_invoked = re.search(r"(^|\s)rerun(\s|$)", command) is not None
    rerun_script = "/bin/rerun" in command
    rerun_cli_binary = "/rerun_sdk/rerun_cli/rerun" in command
    return rerun_invoked or rerun_script or rerun_cli_binary


def _find_rerun_viewer_processes(processes: list[_ProcessInfo] | None = None) -> list[_ProcessInfo]:
    """Find candidate Rerun web viewer processes in stable pid order."""
    process_table = _list_processes() if processes is None else processes
    return sorted(
        (process for process in process_table if _is_rerun_viewer_process(process)), key=lambda item: item.pid
    )


def _rerun_viewer_process_group_ids(processes: list[_ProcessInfo]) -> list[int]:
    """Return unique process-group ids for matched viewer processes."""
    return sorted({process.pgid for process in processes})


def _signal_process_group(pgid: int, sig: signal.Signals) -> bool:
    """Signal one process group if it still exists."""
    try:
        os.killpg(pgid, sig)
    except ProcessLookupError:
        return False
    return True


def _wait_for_rerun_process_groups_to_exit(*, pgids: list[int], timeout_seconds: float) -> list[int]:
    """Wait until no matched Rerun viewer processes remain in the target groups."""
    deadline = time.monotonic() + timeout_seconds
    while True:
        remaining = sorted({process.pgid for process in _find_rerun_viewer_processes() if process.pgid in pgids})
        if not remaining or time.monotonic() >= deadline:
            return remaining
        time.sleep(0.1)


def _format_rerun_processes(processes: list[_ProcessInfo]) -> list[dict[str, int | str]]:
    """Render matched processes as stable JSON-like records for CLI output."""
    return [
        {
            "pid": process.pid,
            "ppid": process.ppid,
            "pgid": process.pgid,
            "stat": process.stat,
            "command": process.command,
        }
        for process in processes
    ]


def _terminate_process_group(process: subprocess.Popen[str], sig: signal.Signals) -> None:
    """Signal a viewer process group, falling back to the direct child."""
    pid = getattr(process, "pid", None)
    if pid is None:
        if sig is signal.SIGTERM:
            process.terminate()
        else:
            process.kill()
        return
    try:
        os.killpg(pid, sig)
    except ProcessLookupError:
        return
    except OSError:
        if sig is signal.SIGTERM:
            process.terminate()
        else:
            process.kill()


@app.command()
def info() -> None:
    """Print a short summary of the current scaffold."""
    console.print(
        "[bold]prml-vslam[/bold]: editable Python package, typed pipeline planner, "
        "Streamlit workbench, and report/slides scaffold."
    )


@app.command("kill-rerun")
def kill_rerun(
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Only list matched Rerun viewer processes without terminating them."),
    ] = False,
    timeout_seconds: Annotated[
        float,
        typer.Option("--timeout", min=0.1, help="Seconds to wait after SIGTERM before sending SIGKILL."),
    ] = 5.0,
) -> None:
    """Inspect and terminate orphaned Rerun web viewer processes."""
    processes = _find_rerun_viewer_processes()
    if not processes:
        console.print("No Rerun web viewer processes found.")
        return

    console.print("Matched Rerun web viewer processes:")
    console.plog(_format_rerun_processes(processes))
    if dry_run:
        return

    pgids = _rerun_viewer_process_group_ids(processes)
    for pgid in pgids:
        _signal_process_group(pgid, signal.SIGTERM)
    remaining = _wait_for_rerun_process_groups_to_exit(pgids=pgids, timeout_seconds=timeout_seconds)
    if remaining:
        for pgid in remaining:
            _signal_process_group(pgid, signal.SIGKILL)
        remaining = _wait_for_rerun_process_groups_to_exit(pgids=remaining, timeout_seconds=1.0)

    if remaining:
        console.error("Rerun viewer process groups still running after SIGKILL: %s", remaining)
        raise typer.Exit(code=1)
    console.print(f"Terminated {len(pgids)} Rerun viewer process group(s).")


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
    emit_dense_points: Annotated[
        bool,
        typer.Option("--dense/--no-dense", help="Whether the plan should include dense map export."),
    ] = True,
    emit_sparse_points: Annotated[
        bool | None,
        typer.Option("--sparse/--no-sparse", help="Whether the plan should include sparse geometry export."),
    ] = None,
    trajectory_evaluation: Annotated[
        bool,
        typer.Option("--trajectory-eval/--no-trajectory-eval", help="Whether to plan trajectory evaluation."),
    ] = False,
    trajectory_baseline: Annotated[
        ReferenceSource,
        typer.Option(
            "--trajectory-baseline",
            help="Reference source selected for trajectory evaluation.",
            case_sensitive=False,
        ),
    ] = ReferenceSource.GROUND_TRUTH,
    reconstruction: Annotated[
        bool,
        typer.Option(
            "--reconstruction/--no-reconstruction",
            help="Whether the plan reserves a reconstruction stage.",
        ),
    ] = False,
) -> None:
    """Build a typed benchmark run plan from the CLI."""
    run_config = build_run_config(
        experiment_name=experiment_name,
        output_dir=output_dir,
        source_backend=VideoSourceConfig(video_path=video_path, frame_stride=frame_stride),
        method=method,
        emit_dense_points=emit_dense_points,
        emit_sparse_points=emit_sparse_points,
        reference_enabled=reconstruction,
        trajectory_eval_enabled=trajectory_evaluation,
        trajectory_baseline=trajectory_baseline,
        evaluate_cloud=emit_dense_points and reconstruction,
        connect_live_viewer=True,
    )
    plan = run_config.compile_plan()
    console.plog(plan.model_dump(mode="json"))


@app.command(
    "plan-run-config",
    cls=RunConfigOverrideCommand,
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def plan_run_config(
    ctx: typer.Context,
    config_path: Annotated[
        Path,
        typer.Argument(
            help="Path to a pipeline config TOML file (repo-relative paths are resolved via PathConfig).",
        ),
    ],
) -> None:
    """Build a typed benchmark run plan from a TOML config file."""
    path_config = get_path_config()
    try:
        run_cfg = load_run_config_toml(path_config=path_config, config_path=config_path)
        run_cfg = _apply_dotted_overrides_to_run_config(run_cfg, ctx.args)
        plan = run_cfg.compile_plan(path_config)
    except Exception as exc:
        console.error(str(exc))
        raise typer.Exit(code=1) from exc
    console.plog(plan.model_dump(mode="json"))


@app.command(
    "run-config",
    cls=RunConfigOverrideCommand,
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def run_config(
    ctx: typer.Context,
    config_path: Annotated[
        Path,
        typer.Argument(
            help="Path to a pipeline config TOML file (repo-relative paths are resolved via PathConfig).",
        ),
    ],
) -> None:
    """Run one offline or streaming pipeline config from a TOML file."""
    path_config = get_path_config()
    try:
        run_cfg = load_run_config_toml(path_config=path_config, config_path=config_path)
        run_cfg = _apply_dotted_overrides_to_run_config(run_cfg, ctx.args)
    except Exception as exc:
        console.error(str(exc))
        raise typer.Exit(code=1) from exc
    run_id = path_config.slugify_experiment_name(run_cfg.experiment_name)
    with _capture_run_config_logs(path_config=path_config, run_id=run_id) as log_path:
        console.info("Persisting run-config log to '%s'.", log_path)
        _run_config_loaded(run_cfg=run_cfg, path_config=path_config)


def _run_config_loaded(*, run_cfg: RunConfig, path_config: PathConfig) -> None:
    """Execute an already loaded run config with durable command-log capture active."""
    run_service: RunService | None = None
    viewer: _RerunViewerProcess | None = None
    snapshot = RunSnapshot()
    preserve_local_head = False
    reached_terminal_snapshot = False
    try:
        viewer = _launch_rerun_viewer(run_config=run_cfg, path_config=path_config)
        runtime_source = build_runtime_source_from_run_config(run_config=run_cfg, path_config=path_config)
        run_service = RunService(path_config=path_config)
        run_service.start_run(run_config=run_cfg, runtime_source=runtime_source)
        snapshot = _wait_for_pipeline_terminal_snapshot(run_service, poll_interval_seconds=0.2)
        reached_terminal_snapshot = True
        preserve_local_head = snapshot.state is RunState.COMPLETED and run_cfg.ray_local_head_lifecycle == "reusable"
    except KeyboardInterrupt as exc:
        if run_service is not None:
            run_service.stop_run()
            snapshot = run_service.snapshot()
            _print_pipeline_demo_snapshot(snapshot)
        raise typer.Exit(code=130) from exc
    except Exception as exc:
        console.error(str(exc))
        raise typer.Exit(code=1) from exc
    finally:
        if run_service is not None:
            run_service.shutdown(preserve_local_head=preserve_local_head)
        if not reached_terminal_snapshot:
            _shutdown_rerun_viewer(viewer)
    _print_pipeline_demo_snapshot(snapshot)
    _wait_for_rerun_viewer_close(viewer)
    _shutdown_rerun_viewer(viewer)
    if snapshot.state is RunState.FAILED:
        raise typer.Exit(code=1)


@app.command("plan-sweep-config")
def plan_sweep_config(
    sweep_path: Annotated[
        Path,
        typer.Argument(
            help="Path to a sweep TOML file.",
        ),
    ],
) -> None:
    """Print the expanded sweep plan as JSON without executing any runs.

    Loads the sweep TOML, validates the config, resolves all method template
    paths, and prints the list of expanded run items.  Use this command to
    inspect ordering and run IDs before committing to a full sweep execution.
    """
    from prml_vslam.pipeline.sweep import expand_sweep, load_sweep_config

    path_config = get_path_config()
    try:
        config = load_sweep_config(sweep_path, path_config)
        items = expand_sweep(config, path_config)
    except Exception as exc:
        console.error(str(exc))
        raise typer.Exit(code=1) from exc
    print(json.dumps([item.model_dump(mode="json") for item in items], indent=2))


@app.command("run-sweep-config")
def run_sweep_config(
    sweep_path: Annotated[
        Path,
        typer.Argument(
            help="Path to a sweep TOML file.",
        ),
    ],
    fail_fast: Annotated[
        bool,
        typer.Option(
            "--fail-fast/--continue-on-failure",
            help=(
                "Stop immediately after the first failed run (--fail-fast, default) "
                "or attempt all runs and report failures at the end (--continue-on-failure)."
            ),
        ),
    ] = True,
) -> None:
    """Execute all expanded runs from a sweep TOML sequentially.

    Each run reuses the existing single-run execution path (``_run_config_loaded``)
    and writes its own timestamped log under the run-log directory.  Local
    artifacts under ``[sweep].output_dir`` remain the only source of truth.

    Exits with code 1 when one or more runs fail.  With ``--fail-fast`` (default)
    execution stops on the first failure; with ``--continue-on-failure`` all runs
    are attempted and a failure summary is printed at the end.  A ``Ctrl-C``
    interrupt always propagates immediately regardless of the mode.
    """
    from prml_vslam.pipeline.sweep import build_run_config_from_sweep_item, expand_sweep, load_sweep_config

    path_config = get_path_config()
    try:
        config = load_sweep_config(sweep_path, path_config)
        items = expand_sweep(config, path_config)
        _preflight_sweep_normalized_entries(items, path_config=path_config)
    except Exception as exc:
        console.error(str(exc))
        raise typer.Exit(code=1) from exc

    total = len(items)
    failures: list[str] = []

    for idx, item in enumerate(items, start=1):
        console.info("Sweep run %d/%d: %s", idx, total, item.run_id)
        try:
            run_cfg = build_run_config_from_sweep_item(item)
        except Exception as exc:
            console.error("Sweep run %s failed to build config (run %d/%d): %s", item.run_id, idx, total, exc)
            failures.append(item.run_id)
            if fail_fast:
                raise typer.Exit(code=1) from exc
            continue
        run_id = path_config.slugify_experiment_name(run_cfg.experiment_name)
        with _capture_run_config_logs(path_config=path_config, run_id=run_id) as log_path:
            console.info("Persisting run-config log to '%s'.", log_path)
            try:
                _run_config_loaded(run_cfg=run_cfg, path_config=path_config)
            except typer.Exit as exc:
                if exc.exit_code == 130:
                    raise
                console.error("Sweep run %s failed (run %d/%d).", item.run_id, idx, total)
                failures.append(item.run_id)
                if fail_fast:
                    raise typer.Exit(code=1) from exc

    if failures:
        console.error(
            "%d of %d sweep run(s) failed: %s",
            len(failures),
            total,
            ", ".join(failures),
        )
        raise typer.Exit(code=1)

    console.info("Sweep complete: %d/%d runs succeeded.", total - len(failures), total)


def _preflight_sweep_normalized_entries(items: list[Any], *, path_config: PathConfig) -> None:
    """Verify dataset-backed sweep runs can resolve a normalized datastore entry."""
    from prml_vslam.pipeline.sweep import build_run_config_from_sweep_item

    failures: list[str] = []
    for item in items:
        try:
            run_cfg = build_run_config_from_sweep_item(item)
            source_backend = run_cfg.stages.source.backend
            if not isinstance(source_backend, AdvioSourceConfig | Record3DDatasetSourceConfig | TumRgbdSourceConfig):
                continue
            dataset_id = dataset_id_for_source_config(source_backend)
            service = dataset_service(dataset_id, path_config)
            profile = normalized_profile_for_dataset(
                dataset_id=dataset_id,
                service=service,
                source_config=source_backend,
            )
            normalized_store_for_service(dataset_id, path_config).resolve_entry(
                profile,
                frame_selection=FrameSelectionConfig(
                    frame_stride=source_backend.frame_stride,
                    target_fps=source_backend.target_fps,
                ),
            )
        except Exception as exc:
            failures.append(f"{item.run_id}: {exc}")
    if failures:
        joined = "\n- ".join(failures)
        raise FileNotFoundError(
            "Sweep normalized datastore preflight failed. Build the missing compatible entries first with "
            "`prml-vslam dataset normalize --config .configs/datasets/benchmark-vslam-datastore.toml`.\n"
            f"- {joined}"
        )


@app.command("eval-trajectory")
def eval_trajectory(
    artifact_root: Annotated[
        Path,
        typer.Argument(
            help="Path to an existing artifact root that contains slam/trajectory.tum and benchmark/<baseline>.tum.",
        ),
    ],
    baseline: Annotated[
        ReferenceSource,
        typer.Option(
            "--baseline",
            help="Reference source used for evaluation.",
            case_sensitive=False,
        ),
    ] = ReferenceSource.GROUND_TRUTH,
    sequence_id: Annotated[
        str | None,
        typer.Option("--sequence-id", help="Sequence slug (inferred from sequence_manifest.json when omitted)."),
    ] = None,
) -> None:
    """Evaluate trajectory against a reference directly from an existing artifact root."""
    from prml_vslam.eval.services import TrajectoryEvaluationRepairService
    from prml_vslam.eval.trajectory_contracts import DiscoveredRun

    path_config = get_path_config()
    resolved_root = path_config.resolve_repo_path(artifact_root)

    estimate_path = resolved_root / "slam" / "trajectory.tum"
    if not estimate_path.exists():
        console.error(f"Estimated trajectory not found: '{estimate_path}'")
        raise typer.Exit(code=1)

    if sequence_id is None:
        manifest_path = resolved_root / "input" / "sequence_manifest.json"
        if manifest_path.exists():
            sequence_id = json.loads(manifest_path.read_text(encoding="utf-8")).get("sequence_id", "unknown")
        else:
            sequence_id = "unknown"

    method: MethodId | None = next(
        (m for part in reversed(resolved_root.parts) for m in MethodId if part == m.value),
        None,
    )
    run = DiscoveredRun(
        artifact_root=resolved_root,
        estimate_path=estimate_path,
        method=method.value if method is not None else None,
        label=method.display_name if method is not None else resolved_root.name,
    )
    try:
        service = TrajectoryEvaluationRepairService(path_config)
        artifact = service.recompute_run_evaluation(run, baseline_source=baseline, sequence_slug=sequence_id)
    except Exception as exc:
        console.error(str(exc))
        raise typer.Exit(code=1) from exc
    console.plog(
        {
            "manifest_path": str((artifact.artifact_root / "evaluation" / "trajectory" / "manifest.json").resolve()),
            "metrics_long_path": str(
                (artifact.artifact_root / "evaluation" / "trajectory" / "metrics_long.csv").resolve()
            ),
            "error_series_count": len(artifact.error_series_paths),
        }
    )


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
            help="Persist an offline or streaming ADVIO demo run config.",
            case_sensitive=False,
        ),
    ] = PipelineMode.OFFLINE,
    method: Annotated[
        MethodId,
        typer.Option(
            "--method",
            help="Method id stored in the persisted demo run config.",
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
    dataset_frame_stride: Annotated[
        int,
        typer.Option("--dataset-frame-stride", min=1, help="Dataset frame stride stored in the demo run config."),
    ] = 1,
    dataset_target_fps: Annotated[
        float | None,
        typer.Option("--dataset-target-fps", min=0.01, help="Dataset target FPS stored in the demo run config."),
    ] = None,
) -> None:
    """Persist the canonical ADVIO demo run config as TOML."""
    path_config = get_path_config()
    advio_service = AdvioDatasetService(path_config)
    resolved_sequence_id = _resolve_demo_sequence_id(path_config, explicit_sequence_id=sequence_id)
    scene = advio_service.scene(resolved_sequence_id)
    resolved_config_path = persist_advio_demo_run_config(
        path_config=path_config,
        sequence_id=scene.sequence_slug,
        mode=mode,
        method=method,
        dataset_frame_stride=dataset_frame_stride,
        dataset_target_fps=dataset_target_fps,
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
    method: Annotated[
        MethodId,
        typer.Option(
            "--method",
            help="SLAM backend used by the bounded demo.",
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
    pose_frame_mode: Annotated[
        AdvioPoseFrameMode,
        typer.Option(
            "--pose-frame-mode",
            help="Frame semantics used when serving ADVIO replay poses.",
            case_sensitive=False,
        ),
    ] = AdvioPoseFrameMode.PROVIDER_WORLD,
    normalize_video_orientation: Annotated[
        bool,
        typer.Option(
            "--normalize-video-orientation/--raw-video-orientation",
            help="Whether to normalize video display orientation during replay.",
        ),
    ] = True,
    dataset_frame_stride: Annotated[
        int,
        typer.Option("--dataset-frame-stride", min=1, help="Frame stride used for ADVIO replay packets."),
    ] = 1,
    dataset_target_fps: Annotated[
        float | None,
        typer.Option("--dataset-target-fps", min=0.01, help="Target FPS used for ADVIO replay packets."),
    ] = None,
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
    resolved_sequence_id = _resolve_demo_sequence_id(path_config, explicit_sequence_id=sequence_id)
    scene = advio_service.scene(resolved_sequence_id)
    run_config = build_advio_demo_run_config(
        path_config=path_config,
        sequence_id=scene.sequence_slug,
        mode=PipelineMode.STREAMING,
        method=method,
        pose_source=pose_source,
        pose_frame_mode=pose_frame_mode,
        normalize_video_orientation=normalize_video_orientation,
        dataset_frame_stride=dataset_frame_stride,
        dataset_target_fps=dataset_target_fps,
    )
    source = build_runtime_source_from_run_config(run_config=run_config, path_config=path_config)
    run_service = RunService(path_config=path_config)
    pipeline_demo_console.info(
        "Starting pipeline demo for %s (%s, %s).",
        scene.display_name,
        PipelineMode.STREAMING.value,
        method.value,
    )
    try:
        run_service.start_run(run_config=run_config, runtime_source=source)
        snapshot = _wait_for_pipeline_terminal_snapshot(
            run_service,
            poll_interval_seconds=poll_interval_seconds,
        )
    except KeyboardInterrupt as exc:
        pipeline_demo_console.warning("Interrupted; stopping the active pipeline demo.")
        run_service.stop_run()
        snapshot = run_service.snapshot()
        _print_pipeline_demo_snapshot(snapshot)
        raise typer.Exit(code=130) from exc
    _print_pipeline_demo_snapshot(snapshot)
    if snapshot.state is RunState.FAILED:
        raise typer.Exit(code=1)


@app.command("app")
def launch_app(
    browser: Annotated[
        bool,
        typer.Option("--browser/--no-browser", help="Whether to open the app in a browser automatically."),
    ] = True,
) -> None:
    """Launch the Streamlit workbench."""
    path_config = get_path_config()
    app_path = path_config.root / "streamlit_app.py"

    if not app_path.exists():
        console.error("Streamlit app file not found: %s", app_path)
        raise typer.Exit(code=1)

    cmd = [sys.executable, "-m", "streamlit", "run", str(app_path)]
    if not browser:
        cmd.extend(["--server.headless", "true"])

    console.info("Launching Streamlit app...")
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        console.info("Streamlit app stopped.")
    except subprocess.CalledProcessError as exc:
        console.error("Streamlit app exited with error: %s", exc)
        raise typer.Exit(code=exc.returncode) from exc


@record3d_app.command("summary")
def record3d_summary() -> None:
    """Print normalized Record3D coverage plus native download-cache state."""
    path_config = get_path_config()
    service = Record3DDatasetService(path_config)
    normalized = query_normalized_dataset(DatasetId.RECORD3D, path_config)
    payload = {
        "normalized": normalized.model_dump(mode="json"),
        "native_cache": _native_cache_facts(service),
    }
    console.plog(payload)


@record3d_app.command("download")
def record3d_download(
    sequence_ids: Annotated[
        list[int] | None,
        typer.Option(
            "--sequence",
            help="Repeat to select one or more zero-based Record3D sequence indices. Omit to target all scenes.",
        ),
    ] = None,
    overwrite: Annotated[
        bool,
        typer.Option(
            "--overwrite/--reuse",
            help="Whether to re-download cached `.r3d` archives.",
        ),
    ] = False,
) -> None:
    """Download selected Record3D `.r3d` archives."""
    service = Record3DDatasetService(get_path_config())
    try:
        result = service.download(
            Record3DDownloadRequest(
                sequence_ids=[] if sequence_ids is None else sequence_ids,
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


def _dataset_source_config_from_toml(
    config_path: Path,
) -> tuple[DatasetId, AdvioSourceConfig | TumRgbdSourceConfig | Record3DDatasetSourceConfig]:
    data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    backend_payload = _source_backend_payload(data)
    backend = SourceStageConfig.model_validate({"backend": backend_payload}).backend
    if isinstance(backend, AdvioSourceConfig):
        return DatasetId.ADVIO, backend
    if isinstance(backend, TumRgbdSourceConfig):
        return DatasetId.TUM_RGBD, backend
    if isinstance(backend, Record3DDatasetSourceConfig):
        return DatasetId.RECORD3D, backend
    raise ValueError(
        "Expected a dataset source config with source_id advio, tum_rgbd, or record3d_dataset; "
        f"got {None if backend is None else backend.source_id!r}."
    )


def _source_backend_payload(data: dict[str, Any]) -> dict[str, Any]:
    if isinstance(data.get("stages"), dict):
        source = data["stages"].get("source")
        if isinstance(source, dict) and isinstance(source.get("backend"), dict):
            return source["backend"]
    if isinstance(data.get("backend"), dict):
        return data["backend"]
    if "source_id" in data:
        return data
    raise ValueError("Expected source config TOML with `source_id`, `[backend]`, or `[stages.source.backend]`.")


@dataset_app.command("normalize")
def dataset_normalize(
    dataset: Annotated[
        str | None,
        typer.Option("--dataset", "-d", help="Dataset id: advio, tum_rgbd, or record3d."),
    ] = None,
    config_path: Annotated[
        Path | None,
        typer.Option(
            "--config",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="TOML build config with dataset groups and shared normalize-time settings.",
        ),
    ] = None,
    source_config_path: Annotated[
        Path | None,
        typer.Option(
            "--source-config",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="TOML source config that defines one byte-affecting normalized-store profile.",
        ),
    ] = None,
    sequences: Annotated[
        list[str] | None,
        typer.Option(
            "--sequence",
            help="Repeat to select one or more sequences. Omit to normalize all offline-ready local sequences.",
        ),
    ] = None,
    workers: Annotated[
        int | None,
        typer.Option("--workers", min=1, help="Parallel workers for all-sequence normalization. Defaults to CPUs."),
    ] = None,
    frame_stride: Annotated[
        int | None,
        typer.Option("--frame-stride", min=1, help="Normalize every Nth frame into the datastore."),
    ] = None,
    target_fps: Annotated[
        float | None,
        typer.Option("--target-fps", min=0.0, help="Normalize an approximate target FPS into the datastore."),
    ] = None,
    reference_cloud_pixel_stride: Annotated[
        int | None,
        typer.Option("--reference-cloud-pixel-stride", "--record3d-reference-cloud-pixel-stride", min=1),
    ] = None,
    reference_cloud_min_confidence: Annotated[
        int | None,
        typer.Option("--reference-cloud-min-confidence", "--record3d-reference-cloud-min-confidence", min=0, max=255),
    ] = None,
    reference_cloud_max_points: Annotated[
        int | None,
        typer.Option("--reference-cloud-max-points", "--record3d-reference-cloud-max-points", min=1),
    ] = None,
) -> None:
    """Create or replace normalized dataset entries."""
    path_config = get_path_config()
    if config_path is not None:
        if dataset is not None or source_config_path is not None or sequences:
            raise typer.BadParameter("--config owns source selection; omit --dataset, --source-config, and --sequence.")
        if any(
            value is not None
            for value in (
                frame_stride,
                target_fps,
                reference_cloud_pixel_stride,
                reference_cloud_min_confidence,
                reference_cloud_max_points,
            )
        ):
            raise typer.BadParameter(
                "--config owns frame selection, RGB preprocessing, and reference-cloud settings; "
                "omit normalize-time override flags."
            )
        try:
            build_config = NormalizedDatasetBuildConfig.from_toml(config_path)
            source_configs = build_config.source_configs()
            worker_count = workers or build_config.workers or (os.cpu_count() or 1)
            entries = normalize_dataset_source_configs(
                path_config=path_config,
                source_configs=source_configs,
                workers=worker_count,
            )
        except (ValueError, ValidationError) as exc:
            raise typer.BadParameter(str(exc)) from exc
        console.plog(
            {
                "config_path": config_path.as_posix(),
                "source_count": len(source_configs),
                "workers": min(worker_count, len(source_configs)),
                "entries": [entry.model_dump(mode="json") for entry in entries],
            }
        )
        return
    if source_config_path is not None:
        if sequences:
            raise typer.BadParameter("--source-config includes sequence_id; omit --sequence.")
        if any(
            value is not None
            for value in (
                frame_stride,
                target_fps,
                reference_cloud_pixel_stride,
                reference_cloud_min_confidence,
                reference_cloud_max_points,
            )
        ):
            raise typer.BadParameter(
                "--source-config owns frame selection, RGB preprocessing, and reference-cloud settings; "
                "omit normalize-time override flags."
            )
        try:
            dataset_id, source_config = _dataset_source_config_from_toml(source_config_path)
            if dataset is not None and parse_dataset_id(dataset) is not dataset_id:
                raise ValueError(f"--dataset {dataset!r} does not match source config dataset {dataset_id.value!r}.")
            service = dataset_service(dataset_id, path_config)
            entry = normalize_dataset_entry(
                dataset_id=dataset_id,
                path_config=path_config,
                service=service,
                source_config=source_config,
            )
        except (ValueError, ValidationError) as exc:
            raise typer.BadParameter(str(exc)) from exc
        console.plog(
            {
                "dataset_id": dataset_id.value,
                "source_config": source_config.model_dump(mode="json"),
                "entry": entry.model_dump(mode="json"),
            }
        )
        return
    if dataset is None:
        raise typer.BadParameter("Pass --dataset or --source-config.")
    try:
        dataset_id = parse_dataset_id(dataset)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    service = dataset_service(dataset_id, path_config)
    default_reference_cloud = (
        ReferenceCloudConfig(min_confidence=1) if dataset_id is DatasetId.RECORD3D else ReferenceCloudConfig()
    )
    reference_cloud = default_reference_cloud.model_copy(
        update={
            key: value
            for key, value in {
                "depth_stride_px": reference_cloud_pixel_stride,
                "min_confidence": reference_cloud_min_confidence,
                "max_points": reference_cloud_max_points,
            }.items()
            if value is not None
        }
    )
    sequence_ids: list[int | str] = list(service.list_local_sequence_ids() if not sequences else sequences)
    if not sequence_ids:
        raise typer.BadParameter(f"No offline-ready local {dataset_id.label} sequences found.")
    try:
        if frame_stride is not None and target_fps is not None:
            raise ValueError("Configure either `frame_stride` or `target_fps`, not both.")
        default_selection = default_frame_selection_for_dataset(dataset_id)
        frame_selection = FrameSelectionConfig(
            frame_stride=1 if frame_stride is None else frame_stride,
            target_fps=(default_selection.target_fps if frame_stride is None and target_fps is None else target_fps),
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    worker_count = workers or (os.cpu_count() or 1)
    entries = normalize_dataset_entries(
        dataset_id=dataset_id,
        path_config=path_config,
        sequence_ids=sequence_ids,
        reference_cloud=None if dataset_id is DatasetId.ADVIO else reference_cloud,
        frame_selection=frame_selection,
        workers=worker_count,
    )
    payload: dict[str, Any] = {
        "dataset_id": dataset_id.value,
        "sequence_count": len(sequence_ids),
        "frame_stride": frame_selection.frame_stride,
        "target_fps": frame_selection.target_fps,
        "workers": min(worker_count, len(sequence_ids)),
    }
    if len(entries) == 1 and sequences:
        payload["entry"] = entries[0].model_dump(mode="json")
    else:
        payload["entries"] = [entry.model_dump(mode="json") for entry in entries]
    console.plog(payload)


@dataset_app.command("summary")
def dataset_summary(
    dataset: Annotated[
        str,
        typer.Option("--dataset", "-d", help="Dataset id: advio, tum_rgbd, or record3d."),
    ],
    sequence: Annotated[
        str | None,
        typer.Option("--sequence", "-s", help="Limit summary tables to one normalized sequence."),
    ] = None,
    profile_key: Annotated[
        str | None,
        typer.Option("--profile-key", help="Profile key for --sequence when more than one profile exists."),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Include full stats and metadata tables."),
    ] = False,
) -> None:
    """Print compact normalized-entry coverage and persisted analysis tables."""
    path_config = get_path_config()
    try:
        dataset_id = parse_dataset_id(dataset)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    query = query_normalized_dataset(dataset_id, path_config)
    console.plog(
        {
            "dataset_id": dataset_id.value,
            "store_root": path_config.resolve_normalized_datastore_dir(dataset_id.value),
            "record_count": len(query.records),
            "default_record_count": len(query.default_records),
            "sequence_count": len(query.sequence_ids),
            "issue_count": len(query.issues),
            **_dataset_summary_tables(query, sequence=sequence, profile_key=profile_key, verbose=verbose),
            "issues": query.issues,
        }
    )


@dataset_app.command("inspect")
def dataset_inspect(
    dataset: Annotated[
        str,
        typer.Option("--dataset", "-d", help="Dataset id: advio, tum_rgbd, or record3d."),
    ],
    sequence: Annotated[
        str,
        typer.Option("--sequence", "-s", help="Normalized sequence id to inspect."),
    ],
    profile_key: Annotated[
        str | None,
        typer.Option("--profile-key", help="Profile key. Omit to prefer the default profile for the sequence."),
    ] = None,
) -> None:
    """Inspect one normalized dataset entry without loading heavy RGB/depth payloads."""
    path_config = get_path_config()
    try:
        dataset_id = parse_dataset_id(dataset)
        query = query_normalized_dataset(dataset_id, path_config)
        record = _select_normalized_record(query.records, sequence=sequence, profile_key=profile_key)
        entry = _load_normalized_entry_from_root(record.root)
        manifest = SequenceManifest.model_validate_json(entry.sequence_manifest_path.read_text(encoding="utf-8"))
        benchmark = PreparedBenchmarkInputs.model_validate_json(entry.benchmark_inputs_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    console.plog(
        {
            "entry": record.model_dump(mode="json"),
            "sequence_manifest": manifest.model_dump(mode="json"),
            "reference_trajectories": [
                ref.model_dump(mode="json")
                for ref in benchmark.reference_trajectories + benchmark.candidate_trajectories
            ],
            "reference_clouds": [ref.model_dump(mode="json") for ref in benchmark.reference_clouds],
            "observation_sequences": [ref.model_dump(mode="json") for ref in benchmark.observation_sequences],
            "observation_summary": _entry_dataframe_records(query.observation_summary_frame(), record),
            "trajectory_summary": _entry_dataframe_records(query.trajectory_summary_frame(), record),
            "payload_footprint": _entry_dataframe_records(query.payload_footprint_frame(), record),
            "metadata": _entry_dataframe_records(query.metadata_df, record),
            "stats": _entry_dataframe_records(query.stats_df, record),
        }
    )


def _load_normalized_entry_from_root(root: Path) -> NormalizedDatasetEntry:
    entry_path = root / "entry.json"
    if not entry_path.exists():
        raise ValueError(f"Normalized entry metadata does not exist: {entry_path}")
    return NormalizedDatasetEntry.model_validate_json(entry_path.read_text(encoding="utf-8"))


def _select_normalized_record(
    records: list[NormalizedSequenceRecord],
    *,
    sequence: str,
    profile_key: str | None,
) -> NormalizedSequenceRecord:
    sequence_records = [record for record in records if record.sequence_id == sequence]
    if not sequence_records:
        raise ValueError(f"No normalized entry found for sequence {sequence!r}.")
    if profile_key is not None:
        matching = [record for record in sequence_records if record.profile_key == profile_key]
        if not matching:
            raise ValueError(f"No normalized entry found for sequence {sequence!r} and profile {profile_key!r}.")
        return matching[0]
    defaults = [record for record in sequence_records if record.is_default_profile]
    if len(defaults) == 1:
        return defaults[0]
    if len(sequence_records) == 1:
        return sequence_records[0]
    raise ValueError(
        f"Sequence {sequence!r} has multiple normalized profiles; pass --profile-key. "
        f"Available profiles: {[record.profile_key for record in sequence_records]}"
    )


def _dataset_summary_tables(
    query: NormalizedDatasetQuery,
    *,
    sequence: str | None,
    profile_key: str | None,
    verbose: bool,
) -> dict[str, Any]:
    if profile_key is not None and sequence is None:
        raise typer.BadParameter("--profile-key requires --sequence.")
    records = (
        [_select_normalized_record(query.records, sequence=sequence, profile_key=profile_key)]
        if sequence is not None
        else query.records
    )
    payload: dict[str, Any] = {
        "records": _record_rows(query, records),
        "observation_summary": _records_dataframe_records(query.observation_summary_frame(), records),
        "payload_footprint": _records_dataframe_records(query.payload_footprint_frame(), records),
    }
    if sequence is not None or verbose:
        payload["trajectory_summary"] = _records_dataframe_records(query.trajectory_summary_frame(), records)
    if verbose:
        payload["metadata"] = _records_dataframe_records(query.metadata_df, records)
        payload["stats"] = _records_dataframe_records(query.stats_df, records)
    else:
        payload["hint"] = (
            "Pass --verbose for full stats/metadata tables."
            if sequence is not None
            else "Pass --sequence for trajectory details or --verbose for full stats/metadata tables."
        )
    return payload


def _record_rows(
    query: NormalizedDatasetQuery, records: list[NormalizedSequenceRecord]
) -> list[dict[str, str | int | float | bool | None]]:
    keys = {(record.sequence_id, record.profile_key) for record in records}
    return [row for row in query.table_rows() if (str(row["Sequence"]), str(row["Profile"])) in keys]


def _dataframe_records(frame: Any) -> list[dict[str, Any]]:
    if bool(getattr(frame, "empty", True)):
        return []
    records = frame.to_dict(orient="records")
    return [dict(record) for record in records]


def _entry_dataframe_records(frame: Any, record: NormalizedSequenceRecord) -> list[dict[str, Any]]:
    return _records_dataframe_records(frame, [record])


def _records_dataframe_records(frame: Any, records: list[NormalizedSequenceRecord]) -> list[dict[str, Any]]:
    keys = {(record.sequence_id, record.profile_key) for record in records}
    return [
        row
        for row in _dataframe_records(frame)
        if (row.get("sequence_id", row.get("Sequence")), row.get("profile_key", row.get("Profile"))) in keys
    ]


@advio_app.command("summary")
def advio_summary() -> None:
    """Print normalized ADVIO coverage plus native download-cache state."""
    path_config = get_path_config()
    service = AdvioDatasetService(path_config)
    normalized = query_normalized_dataset(DatasetId.ADVIO, path_config)
    payload = {
        "upstream": service.catalog.upstream.model_dump(mode="json"),
        "normalized": normalized.model_dump(mode="json"),
        "native_cache": _native_cache_facts(service),
    }
    console.plog(payload)


@advio_app.command("download")
def advio_download(
    sequence_ids: Annotated[
        list[int] | None,
        typer.Option("--sequence", help="Repeat to select one or more ADVIO sequence ids. Omit to target all scenes."),
    ] = None,
    overwrite: Annotated[
        bool,
        typer.Option(
            "--overwrite/--reuse",
            help="Whether to re-download cached ZIPs and replace extracted files.",
        ),
    ] = False,
) -> None:
    """Download selected ADVIO scene archives and extract complete scenes."""
    service = AdvioDatasetService(get_path_config())
    try:
        result = service.download(
            AdvioDownloadRequest(
                sequence_ids=[] if sequence_ids is None else sequence_ids,
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


@tum_rgbd_app.command("summary")
def tum_rgbd_summary() -> None:
    """Print normalized TUM RGB-D coverage plus native download-cache state."""
    path_config = get_path_config()
    service = TumRgbdDatasetService(path_config)
    normalized = query_normalized_dataset(DatasetId.TUM_RGBD, path_config)
    payload = {
        "upstream": service.catalog.upstream,
        "normalized": normalized.model_dump(mode="json"),
        "native_cache": _native_cache_facts(service),
    }
    console.plog(payload)


@tum_rgbd_app.command("download")
def tum_rgbd_download(
    sequence_ids: Annotated[
        list[str] | None,
        typer.Option("--sequence", help="Repeat to select one or more TUM sequence ids. Omit to target all scenes."),
    ] = None,
    overwrite: Annotated[
        bool,
        typer.Option(
            "--overwrite/--reuse",
            help="Whether to re-download cached TGZs and replace extracted files.",
        ),
    ] = False,
) -> None:
    """Download selected TUM RGB-D archives and extract complete scenes."""
    service = TumRgbdDatasetService(get_path_config())
    try:
        result = service.download(
            TumRgbdDownloadRequest(
                sequence_ids=[] if sequence_ids is None else sequence_ids,
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


def _resolve_demo_sequence_id(path_config: PathConfig, *, explicit_sequence_id: int | None) -> int:
    """Resolve one normalized ADVIO sequence for the CLI demo."""
    if explicit_sequence_id is not None:
        return explicit_sequence_id
    records = query_normalized_dataset(DatasetId.ADVIO, path_config).default_records
    sequence_ids = [
        int(record.sequence_id.split("-", maxsplit=1)[1])
        for record in records
        if record.sequence_id.startswith("advio-") and record.sequence_id.split("-", maxsplit=1)[1].isdigit()
    ]
    if not sequence_ids:
        raise typer.BadParameter(
            "No normalized ADVIO entries were found. Run `prml-vslam dataset normalize --dataset advio` first or pass --sequence."
        )
    return sequence_ids[0]


def _native_cache_facts(
    service: AdvioDatasetService | TumRgbdDatasetService | Record3DDatasetService,
) -> dict[str, Any]:
    statuses = service.local_scene_statuses()
    return {
        "dataset_root": str(service.dataset_root),
        "local_scene_count": sum(status.sequence_dir is not None for status in statuses),
        "cached_archive_count": sum(status.archive_path is not None for status in statuses),
        "total_remote_archive_bytes": sum(scene.archive_size_bytes for scene in service.catalog.scenes),
        "sequence_ids": [status.scene.sequence_id for status in statuses if status.sequence_dir is not None],
        "archive_sequence_ids": [status.scene.sequence_id for status in statuses if status.archive_path is not None],
    }


def _apply_dotted_overrides_to_run_config(run_config: RunConfig, args: list[str]) -> RunConfig:
    """Apply canonical ``RunConfig`` field-path overrides after TOML load."""
    if not args:
        return run_config
    overrides = _parse_dotted_overrides(args)
    if not overrides:
        return run_config
    payload = run_config.model_dump(mode="python", round_trip=True)
    _deep_merge(payload, overrides)
    try:
        return RunConfig.model_validate(payload, extra="forbid")
    except ValidationError as exc:
        first_error = exc.errors()[0]
        location = ".".join(str(part) for part in first_error["loc"])
        raise typer.BadParameter(f"Invalid RunConfig override at `{location}`: {first_error['msg']}") from exc


def _parse_dotted_overrides(args: list[str]) -> dict[str, Any]:
    overrides: dict[str, Any] = {}
    index = 0
    while index < len(args):
        token = args[index]
        if not token.startswith("--"):
            raise typer.BadParameter(f"Unexpected dotted override token `{token}`.")
        option = token[2:]
        if not option:
            raise typer.BadParameter("RunConfig override options must include a field path.")
        if "=" in option:
            path, raw_value = option.split("=", maxsplit=1)
            index += 1
        else:
            if index + 1 >= len(args):
                raise typer.BadParameter(f"Dotted override `{token}` requires a value.")
            path = option
            raw_value = args[index + 1]
            index += 2
        _deep_set(overrides, path.split("."), _parse_override_value(raw_value))
    return overrides


def _parse_override_value(raw_value: str) -> Any:
    try:
        return json.loads(raw_value)
    except json.JSONDecodeError:
        return raw_value


def _deep_set(target: dict[str, Any], path: list[str], value: Any) -> None:
    cursor = target
    for segment in path[:-1]:
        existing = cursor.get(segment)
        if not isinstance(existing, dict):
            existing = {}
            cursor[segment] = existing
        cursor = existing
    leaf = path[-1]
    existing_leaf = cursor.get(leaf)
    if isinstance(existing_leaf, dict) and isinstance(value, dict):
        _deep_merge(existing_leaf, value)
    else:
        cursor[leaf] = value


def _deep_merge(target: dict[str, Any], overrides: dict[str, Any]) -> None:
    for key, value in overrides.items():
        existing = target.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            _deep_merge(existing, value)
        else:
            target[key] = value


def _apply_dataset_sampling_overrides(
    source_backend: SourceBackendConfig | None,
    *,
    dataset_frame_stride: int | None,
    dataset_target_fps: float | None,
) -> SourceBackendConfig:
    if dataset_frame_stride is None and dataset_target_fps is None:
        if source_backend is None:
            raise typer.BadParameter("Dataset sampling overrides require a dataset-backed source.")
        return source_backend
    if dataset_frame_stride is not None and dataset_target_fps is not None:
        raise typer.BadParameter("Configure either --dataset-frame-stride or --dataset-target-fps, not both.")
    if not isinstance(source_backend, AdvioSourceConfig | Record3DDatasetSourceConfig | TumRgbdSourceConfig):
        raise typer.BadParameter("Dataset sampling overrides require a dataset-backed source.")
    return source_backend.model_copy(
        update={
            "frame_stride": 1 if dataset_target_fps is not None else dataset_frame_stride,
            "target_fps": dataset_target_fps,
        }
    )


def _wait_for_pipeline_terminal_snapshot(
    run_service: RunService,
    *,
    poll_interval_seconds: float,
) -> RunSnapshot:
    """Poll the run service until the current demo session reaches a terminal state."""
    previous_state: RunState | None = None
    previous_processed_items = -1
    while True:
        snapshot = run_service.snapshot()
        if snapshot.state is not previous_state:
            plan_run_id = None if snapshot.plan is None else snapshot.plan.run_id
            pipeline_demo_console.info(
                "Pipeline demo state: %s%s", snapshot.state.value, "" if plan_run_id is None else f" ({plan_run_id})"
            )
            previous_state = snapshot.state
        slam_runtime_status = snapshot.stage_runtime_status.get(StageKey.SLAM)
        processed_items = 0 if slam_runtime_status is None else slam_runtime_status.processed_items
        if processed_items != previous_processed_items and processed_items > 0:
            fps_text = (
                "n/a"
                if slam_runtime_status is None or slam_runtime_status.fps is None
                else f"{slam_runtime_status.fps:.2f}"
            )
            keyfps_text = (
                "n/a"
                if slam_runtime_status is None or slam_runtime_status.throughput is None
                else f"{slam_runtime_status.throughput:.2f}"
            )
            latency_text = (
                None
                if slam_runtime_status is None or slam_runtime_status.latency_ms is None
                else f" latency={slam_runtime_status.latency_ms:.1f}ms"
            )
            pipeline_demo_console.info(
                "SLAM processed=%d fps=%s keyfps=%s%s",
                processed_items,
                fps_text,
                keyfps_text,
                "" if latency_text is None else latency_text,
            )
            previous_processed_items = processed_items
        if snapshot.state not in {RunState.IDLE, RunState.PREPARING, RunState.RUNNING}:
            return snapshot
        time.sleep(poll_interval_seconds)


def _print_pipeline_demo_snapshot(snapshot: RunSnapshot) -> None:
    """Render the final CLI demo snapshot in a compact structured form."""
    payload = {
        "state": snapshot.state.value,
        "error_message": snapshot.error_message or None,
        "plan": None if snapshot.plan is None else snapshot.plan.model_dump(mode="json"),
        "stage_outcomes": {
            stage_key.value: outcome.model_dump(mode="json") for stage_key, outcome in snapshot.stage_outcomes.items()
        },
        "stage_runtime_status": {
            stage_key.value: status.model_dump(mode="json")
            for stage_key, status in snapshot.stage_runtime_status.items()
        },
        "live_refs": {
            stage_key.value: {ref_key: ref.model_dump(mode="json") for ref_key, ref in refs.items()}
            for stage_key, refs in snapshot.live_refs.items()
        },
        "artifacts": {
            artifact_key: artifact.model_dump(mode="json") for artifact_key, artifact in snapshot.artifacts.items()
        },
    }
    console.plog(payload)


def main() -> None:
    """Run the Typer application."""
    app()


if __name__ == "__main__":
    main()
