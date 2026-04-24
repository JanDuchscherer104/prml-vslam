"""Inspection helpers for persisted pipeline run artifact roots."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypeAlias, TypeVar

import cv2
from pydantic import Field, TypeAdapter

from prml_vslam.interfaces.alignment import GroundAlignmentMetadata
from prml_vslam.interfaces.ingest import PreparedBenchmarkInputs, SequenceManifest
from prml_vslam.interfaces.slam import SlamArtifacts
from prml_vslam.pipeline.contracts.events import (
    RunCompleted,
    RunEvent,
    RunFailed,
    RunStarted,
    RunSubmitted,
    StageFailed,
)
from prml_vslam.pipeline.contracts.provenance import ArtifactRef, RunSummary, StageManifest
from prml_vslam.pipeline.contracts.runtime import RunSnapshot
from prml_vslam.pipeline.snapshot_projector import SnapshotProjector
from prml_vslam.reconstruction.contracts import ReconstructionMetadata
from prml_vslam.utils import BaseData, PathConfig, RunArtifactPaths

JsonPrimitive: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonPrimitive | list["JsonValue"] | dict[str, "JsonValue"]
SnapshotUpdateValue: TypeAlias = (
    JsonValue
    | RunSummary
    | list[StageManifest]
    | SequenceManifest
    | PreparedBenchmarkInputs
    | SlamArtifacts
    | GroundAlignmentMetadata
)
BaseDataT = TypeVar("BaseDataT", bound=BaseData)
AdapterT = TypeVar("AdapterT")

_RUN_EVENT_ADAPTER = TypeAdapter(RunEvent)
_STAGE_MANIFESTS_ADAPTER = TypeAdapter(list[StageManifest])
_CANONICAL_PATH_FIELDS = (
    "artifact_root",
    "sequence_manifest_path",
    "benchmark_inputs_path",
    "trajectory_path",
    "point_cloud_path",
    "sparse_points_path",
    "dense_points_path",
    "native_output_dir",
    "native_rerun_rrd_path",
    "ground_alignment_path",
    "trajectory_metrics_path",
    "cloud_metrics_path",
    "reference_cloud_path",
    "summary_path",
    "stage_manifests_path",
)


class RunArtifactCandidate(BaseData):
    """One selectable persisted method-level run artifact root."""

    artifact_root: Path
    """Method-level artifact root."""

    run_id: str
    """Run id from the persisted summary, or a path-derived fallback."""

    label: str
    """Compact label suitable for UI selectors."""


class ArtifactFileRow(BaseData):
    """One file or directory discovered under an artifact root."""

    relative_path: str
    """Path relative to the selected artifact root."""

    path: Path
    """Absolute filesystem path."""

    kind: str
    """Filesystem entry kind."""

    size_bytes: int | None = None
    """File size in bytes, when applicable."""

    size_label: str = ""
    """Human-readable file size."""


class ArtifactPathRow(BaseData):
    """Existence and size information for one named artifact path."""

    name: str
    """Path label."""

    path: Path
    """Absolute filesystem path."""

    exists: bool
    """Whether the path exists."""

    kind: str
    """Existing filesystem kind, or `missing`."""

    size_bytes: int | None = None
    """File size in bytes, when this is an existing file."""

    size_label: str = ""
    """Human-readable file size."""


class StageOutputPathRow(ArtifactPathRow):
    """One output path declared by a stage manifest."""

    stage_id: str
    """Stage that declared this output."""


class InputArtifactDiagnostics(BaseData):
    """Shallow diagnostics for materialized offline input artifacts."""

    rgb_frame_count: int
    """Number of materialized RGB frame files."""

    timestamp_count: int
    """Number of normalized input timestamps."""

    frame_stride: int | None = None
    """Frame stride recorded in normalized timestamp metadata."""

    duration_s: float | None = None
    """Timestamp span in seconds, when at least two timestamps are available."""

    image_width_px: int | None = None
    """Width of the first materialized RGB frame."""

    image_height_px: int | None = None
    """Height of the first materialized RGB frame."""

    warnings: list[str] = Field(default_factory=list)
    """Non-fatal inventory warnings."""


class RunAttemptSummary(BaseData):
    """One submitted run attempt found in a persisted event log."""

    attempt_index: int
    """Zero-based attempt index in event-log order."""

    run_id: str
    """Run id carried by this attempt's events."""

    state: str
    """Terminal or latest known state for this attempt."""

    event_count: int
    """Number of events in the attempt."""

    first_event_id: str
    """First event id in this attempt."""

    last_event_id: str
    """Last event id in this attempt."""

    started_at_ns: int | None = None
    """Run-start timestamp in nanoseconds, when present."""

    ended_at_ns: int | None = None
    """Terminal timestamp in nanoseconds, when present."""

    failed_stage_key: str | None = None
    """Failed stage key, when the attempt failed inside a stage."""

    error_message: str = ""
    """Run or stage error message, when present."""


class RunArtifactInspection(BaseData):
    """Structured inspection result for one persisted pipeline run."""

    artifact_root: Path
    """Selected method-level artifact root."""

    run_paths: RunArtifactPaths
    """Canonical path layout for the selected artifact root."""

    snapshot: RunSnapshot
    """Projected snapshot from persisted events and typed fallback files."""

    event_count: int = 0
    """Number of persisted events loaded from `summary/run-events.jsonl`."""

    summary: RunSummary | None = None
    """Persisted run summary, when available."""

    stage_manifests: list[StageManifest] = Field(default_factory=list)
    """Persisted stage manifest records."""

    sequence_manifest: SequenceManifest | None = None
    """Typed normalized input manifest."""

    benchmark_inputs: PreparedBenchmarkInputs | None = None
    """Typed benchmark input manifest."""

    slam: SlamArtifacts | None = None
    """Derived normalized SLAM artifacts, when trajectory outputs are present."""

    reconstruction_metadata: ReconstructionMetadata | None = None
    """Typed reference reconstruction metadata."""

    ground_alignment: GroundAlignmentMetadata | None = None
    """Typed ground-alignment metadata."""

    input_diagnostics: InputArtifactDiagnostics | None = None
    """Input frame/timestamp inventory diagnostics."""

    attempts: list[RunAttemptSummary] = Field(default_factory=list)
    """Run attempts projected from the persisted event log."""

    canonical_paths: list[ArtifactPathRow] = Field(default_factory=list)
    """Canonical paths from :class:`RunArtifactPaths` with existence metadata."""

    stage_output_paths: list[StageOutputPathRow] = Field(default_factory=list)
    """Actual output paths declared by persisted stage manifests."""

    file_inventory: list[ArtifactFileRow] = Field(default_factory=list)
    """Shallow filesystem inventory under the selected artifact root."""

    load_errors: list[str] = Field(default_factory=list)
    """Non-fatal typed loading errors encountered during inspection."""


def discover_run_artifact_roots(path_config: PathConfig) -> list[RunArtifactCandidate]:
    """Discover method-level run roots under the configured artifact directory."""
    artifacts_dir = path_config.resolve_output_dir()
    if not artifacts_dir.exists():
        return []

    roots = {
        marker.parent.parent
        for pattern in ("summary/run_summary.json", "summary/run-events.jsonl")
        for marker in artifacts_dir.rglob(pattern)
        if marker.is_file()
    }
    return sorted(
        (_candidate_from_root(root, artifacts_dir=artifacts_dir) for root in roots), key=lambda item: item.label
    )


def inspect_run_artifacts(artifact_root: Path) -> RunArtifactInspection:
    """Load typed metadata and path inventory for one persisted run root."""
    resolved_root = artifact_root.expanduser().resolve()
    run_paths = RunArtifactPaths.build(resolved_root)
    load_errors: list[str] = []
    events = _load_run_events(run_paths.summary_path.parent / "run-events.jsonl", load_errors=load_errors)
    snapshot = SnapshotProjector().project(RunSnapshot(), events)

    summary = _load_base_data_model(run_paths.summary_path, RunSummary, load_errors=load_errors)
    stage_manifests = _load_json_adapter(
        run_paths.stage_manifests_path,
        _STAGE_MANIFESTS_ADAPTER,
        load_errors=load_errors,
    )
    sequence_manifest = _load_base_data_model(
        run_paths.sequence_manifest_path, SequenceManifest, load_errors=load_errors
    )
    benchmark_inputs = _load_base_data_model(
        run_paths.benchmark_inputs_path, PreparedBenchmarkInputs, load_errors=load_errors
    )
    reconstruction_metadata = _load_base_data_model(
        resolved_root / "reference" / "reconstruction_metadata.json",
        ReconstructionMetadata,
        load_errors=load_errors,
    )
    ground_alignment = _load_base_data_model(
        run_paths.ground_alignment_path,
        GroundAlignmentMetadata,
        load_errors=load_errors,
    )

    stage_manifests = [] if stage_manifests is None else stage_manifests
    snapshot = _apply_snapshot_fallbacks(snapshot=snapshot, summary=summary)
    slam = _derive_slam_artifacts(run_paths=run_paths, stage_manifests=stage_manifests)

    return RunArtifactInspection(
        artifact_root=resolved_root,
        run_paths=run_paths,
        snapshot=snapshot,
        event_count=len(events),
        summary=summary,
        stage_manifests=stage_manifests,
        sequence_manifest=sequence_manifest,
        benchmark_inputs=benchmark_inputs,
        slam=slam,
        reconstruction_metadata=reconstruction_metadata,
        ground_alignment=ground_alignment,
        input_diagnostics=_load_input_diagnostics(run_paths),
        attempts=_summarize_attempts(events),
        canonical_paths=_canonical_path_rows(run_paths),
        stage_output_paths=_stage_output_path_rows(stage_manifests),
        file_inventory=_file_inventory(resolved_root),
        load_errors=load_errors,
    )


def _candidate_from_root(root: Path, *, artifacts_dir: Path) -> RunArtifactCandidate:
    run_id = root.parent.name
    summary = _read_json_payload(root / "summary" / "run_summary.json")
    if isinstance(summary, dict) and isinstance(summary.get("run_id"), str):
        run_id = summary["run_id"]
    try:
        relative_label = root.relative_to(artifacts_dir).as_posix()
    except ValueError:
        relative_label = root.as_posix()
    return RunArtifactCandidate(artifact_root=root.resolve(), run_id=run_id, label=relative_label)


def _load_run_events(path: Path, *, load_errors: list[str]) -> list[RunEvent]:
    if not path.exists():
        return []
    events: list[RunEvent] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            events.append(_RUN_EVENT_ADAPTER.validate_json(line))
        except ValueError as exc:
            load_errors.append(f"{path.name}:{line_number}: {exc}")
    return events


def _load_base_data_model(path: Path, model_type: type[BaseDataT], *, load_errors: list[str]) -> BaseDataT | None:
    if not path.exists():
        return None
    try:
        return model_type.model_validate_json(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        load_errors.append(f"{path.name}: {exc}")
        return None


def _load_json_adapter(path: Path, adapter: TypeAdapter[AdapterT], *, load_errors: list[str]) -> AdapterT | None:
    if not path.exists():
        return None
    try:
        return adapter.validate_json(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        load_errors.append(f"{path.name}: {exc}")
        return None


def _read_json_payload(path: Path) -> JsonValue:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _apply_snapshot_fallbacks(*, snapshot: RunSnapshot, summary: RunSummary | None) -> RunSnapshot:
    updates: dict[str, SnapshotUpdateValue] = {}
    if summary is not None and not snapshot.run_id:
        updates["run_id"] = summary.run_id
    return snapshot.model_copy(update=updates) if updates else snapshot


def _derive_slam_artifacts(
    *, run_paths: RunArtifactPaths, stage_manifests: list[StageManifest]
) -> SlamArtifacts | None:
    output_paths: dict[str, Path] = {}
    for manifest in stage_manifests:
        output_paths.update(manifest.output_paths)

    trajectory_path = output_paths.get("trajectory_tum", run_paths.trajectory_path)
    if not trajectory_path.exists():
        return None
    dense_path = output_paths.get("dense_points_ply", run_paths.point_cloud_path)
    sparse_path = output_paths.get("sparse_points_ply", run_paths.sparse_points_path)
    dense_ref = _artifact_ref(dense_path, kind="ply") if dense_path.exists() else None
    sparse_ref = _artifact_ref(sparse_path, kind="ply") if sparse_path.exists() else None
    return SlamArtifacts(
        trajectory_tum=_artifact_ref(trajectory_path, kind="tum"),
        sparse_points_ply=sparse_ref,
        dense_points_ply=dense_ref,
    )


def _artifact_ref(path: Path, *, kind: str) -> ArtifactRef:
    resolved = path.resolve()
    return ArtifactRef(path=resolved, kind=kind, fingerprint=f"persisted:{resolved.name}")


def _canonical_path_rows(run_paths: RunArtifactPaths) -> list[ArtifactPathRow]:
    return [_path_row(name=field_name, path=getattr(run_paths, field_name)) for field_name in _CANONICAL_PATH_FIELDS]


def _stage_output_path_rows(stage_manifests: list[StageManifest]) -> list[StageOutputPathRow]:
    rows: list[StageOutputPathRow] = []
    for manifest in stage_manifests:
        for name, path in sorted(manifest.output_paths.items()):
            base_row = _path_row(name=name, path=path)
            rows.append(
                StageOutputPathRow(
                    stage_id=manifest.stage_id.value,
                    name=base_row.name,
                    path=base_row.path,
                    exists=base_row.exists,
                    kind=base_row.kind,
                    size_bytes=base_row.size_bytes,
                    size_label=base_row.size_label,
                )
            )
    return rows


def _file_inventory(root: Path) -> list[ArtifactFileRow]:
    if not root.exists():
        return []
    rows: list[ArtifactFileRow] = []
    for path in sorted(item for item in root.rglob("*") if len(item.relative_to(root).parts) <= 3):
        relative_path = path.relative_to(root).as_posix()
        if path.is_dir():
            rows.append(ArtifactFileRow(relative_path=relative_path, path=path.resolve(), kind="dir"))
            continue
        size_bytes = path.stat().st_size
        rows.append(
            ArtifactFileRow(
                relative_path=relative_path,
                path=path.resolve(),
                kind=path.suffix.lstrip(".") or "file",
                size_bytes=size_bytes,
                size_label=_format_size(size_bytes),
            )
        )
    return rows


def _path_row(*, name: str, path: Path) -> ArtifactPathRow:
    resolved = path.expanduser().resolve()
    if not resolved.exists():
        return ArtifactPathRow(name=name, path=resolved, exists=False, kind="missing")
    if resolved.is_dir():
        return ArtifactPathRow(name=name, path=resolved, exists=True, kind="dir")
    size_bytes = resolved.stat().st_size
    return ArtifactPathRow(
        name=name,
        path=resolved,
        exists=True,
        kind=resolved.suffix.lstrip(".") or "file",
        size_bytes=size_bytes,
        size_label=_format_size(size_bytes),
    )


def _format_size(size_bytes: int) -> str:
    value = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024.0 or unit == "TB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{size_bytes} B"
        value /= 1024.0
    return f"{size_bytes} B"


def _load_input_diagnostics(run_paths: RunArtifactPaths) -> InputArtifactDiagnostics:
    timestamps, frame_stride = _load_normalized_timestamps(run_paths.input_timestamps_path)
    input_rgb_dir = (
        run_paths.input_frames_dir if run_paths.input_frames_dir.exists() else run_paths.artifact_root / "input" / "rgb"
    )
    rgb_paths = sorted(input_rgb_dir.glob("*.png")) if input_rgb_dir.exists() else []
    warnings: list[str] = []
    if rgb_paths and timestamps and len(rgb_paths) != len(timestamps):
        warnings.append(f"Found {len(rgb_paths)} RGB frames but {len(timestamps)} timestamps.")
    width_px: int | None = None
    height_px: int | None = None
    if rgb_paths:
        image = cv2.imread(str(rgb_paths[0]))
        if image is None:
            warnings.append(f"Failed to read first RGB frame '{rgb_paths[0]}'.")
        else:
            height_px, width_px = image.shape[:2]
    duration_s = None if len(timestamps) < 2 else (timestamps[-1] - timestamps[0]) / 1e9
    return InputArtifactDiagnostics(
        rgb_frame_count=len(rgb_paths),
        timestamp_count=len(timestamps),
        frame_stride=frame_stride,
        duration_s=duration_s,
        image_width_px=width_px,
        image_height_px=height_px,
        warnings=warnings,
    )


def _load_normalized_timestamps(path: Path) -> tuple[list[int], int | None]:
    if not path.exists():
        return [], None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("timestamps_ns"), list):
        return [], None
    return [int(value) for value in payload["timestamps_ns"]], (
        int(payload["frame_stride"]) if payload.get("frame_stride") is not None else None
    )


def _summarize_attempts(events: list[RunEvent]) -> list[RunAttemptSummary]:
    groups: list[list[RunEvent]] = []
    current: list[RunEvent] = []
    for event in events:
        if isinstance(event, RunSubmitted) and current:
            groups.append(current)
            current = []
        current.append(event)
    if current:
        groups.append(current)
    return [_summarize_attempt(index, group) for index, group in enumerate(groups)]


def _summarize_attempt(index: int, events: list[RunEvent]) -> RunAttemptSummary:
    state = "submitted"
    ended_at_ns: int | None = None
    error_message = ""
    failed_stage_key: str | None = None
    for event in events:
        match event:
            case RunStarted():
                state = "running"
            case RunCompleted():
                state = "completed"
                ended_at_ns = event.ts_ns
            case RunFailed(error_message=message):
                state = "failed"
                ended_at_ns = event.ts_ns
                error_message = message
            case StageFailed(stage_key=stage_key, outcome=outcome):
                state = "failed"
                failed_stage_key = stage_key.value
                error_message = outcome.error_message
            case _:
                pass
    started_at_ns = next((event.ts_ns for event in events if isinstance(event, RunStarted)), None)
    return RunAttemptSummary(
        attempt_index=index,
        run_id=events[-1].run_id,
        state=state,
        event_count=len(events),
        first_event_id=events[0].event_id,
        last_event_id=events[-1].event_id,
        started_at_ns=started_at_ns,
        ended_at_ns=ended_at_ns,
        failed_stage_key=failed_stage_key,
        error_message=error_message,
    )


__all__ = [
    "ArtifactFileRow",
    "ArtifactPathRow",
    "InputArtifactDiagnostics",
    "RunArtifactCandidate",
    "RunArtifactInspection",
    "RunAttemptSummary",
    "StageOutputPathRow",
    "discover_run_artifact_roots",
    "inspect_run_artifacts",
]
