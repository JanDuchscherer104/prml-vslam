"""Portable single-file export and import for pipeline run artifact roots."""

from __future__ import annotations

import json
import shutil
import tarfile
import time
import uuid
from enum import StrEnum
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path, PurePosixPath

from pydantic import Field, TypeAdapter

from prml_vslam.pipeline.contracts.events import RunEvent
from prml_vslam.pipeline.contracts.provenance import RunSummary, StageManifest
from prml_vslam.utils import BaseData, JsonValue
from prml_vslam.utils.serialization import hash_path, write_json

_BUNDLE_SCHEMA_VERSION = 1
_MANIFEST_MEMBER = "manifest.json"
_ARTIFACTS_PREFIX = "artifacts"
_RUN_EVENTS_ADAPTER = TypeAdapter(RunEvent)
_STAGE_MANIFESTS_ADAPTER = TypeAdapter(list[StageManifest])


class RunBundleCollisionPolicy(StrEnum):
    """Import behavior when the target artifact root already exists."""

    FAIL = "fail"
    RENAME = "rename"
    OVERWRITE = "overwrite"


class RunBundleFile(BaseData):
    """One file included in a portable run bundle."""

    relative_path: Path
    """Path relative to the exported artifact root."""

    size_bytes: int
    """File size in bytes."""

    sha256: str
    """Strict file content hash."""


class RunBundleManifest(BaseData):
    """Manifest stored inside a `.prmlrun.tar.gz` archive."""

    schema_version: int = _BUNDLE_SCHEMA_VERSION
    """Portable run-bundle schema version."""

    package_version: str
    """Installed `prml-vslam` package version used for export."""

    exported_run_id: str
    """Run id from the run summary, or a path-derived fallback."""

    artifact_label: str
    """Import label under the artifacts root, usually `run-id/method`."""

    original_artifact_root: Path
    """Absolute artifact root on the exporting machine."""

    exported_at_ns: int
    """Wall-clock export timestamp in nanoseconds."""

    files: list[RunBundleFile] = Field(default_factory=list)
    """Files included under the artifact root."""


class RunBundleExportResult(BaseData):
    """Result returned after exporting one run bundle."""

    bundle_path: Path
    """Path to the written `.prmlrun.tar.gz` file."""

    manifest: RunBundleManifest
    """Manifest embedded into the bundle."""


class RunBundleImportResult(BaseData):
    """Result returned after importing one run bundle."""

    artifact_root: Path
    """Imported artifact root."""

    manifest: RunBundleManifest
    """Manifest loaded from the bundle."""

    warnings: list[str] = Field(default_factory=list)
    """Non-fatal relocation warnings."""


def export_run_bundle(artifact_root: Path, output_path: Path) -> RunBundleExportResult:
    """Export one run artifact root as a self-contained `.prmlrun.tar.gz` file."""
    resolved_root = artifact_root.expanduser().resolve()
    if not resolved_root.is_dir():
        raise FileNotFoundError(f"Run artifact root '{resolved_root}' does not exist.")
    resolved_output = output_path.expanduser().resolve()
    _validate_bundle_output_path(resolved_output)
    manifest = _build_manifest(resolved_root, output_path=resolved_output)
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(resolved_output, "w:gz") as archive:
        manifest_bytes = manifest.model_dump_json(indent=2).encode("utf-8")
        manifest_info = tarfile.TarInfo(_MANIFEST_MEMBER)
        manifest_info.size = len(manifest_bytes)
        manifest_info.mtime = int(time.time())
        archive.addfile(manifest_info, fileobj=_BytesReader(manifest_bytes))
        for file in manifest.files:
            source = resolved_root / file.relative_path
            archive.add(source, arcname=f"{_ARTIFACTS_PREFIX}/{file.relative_path.as_posix()}", recursive=False)
    return RunBundleExportResult(bundle_path=resolved_output, manifest=manifest)


def import_run_bundle(
    bundle_path: Path,
    *,
    output_dir: Path,
    collision_policy: RunBundleCollisionPolicy = RunBundleCollisionPolicy.FAIL,
) -> RunBundleImportResult:
    """Import one `.prmlrun.tar.gz` bundle into an artifacts directory."""
    resolved_bundle = bundle_path.expanduser().resolve()
    if not resolved_bundle.is_file():
        raise FileNotFoundError(f"Run bundle '{resolved_bundle}' does not exist.")
    artifacts_dir = output_dir.expanduser().resolve()
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(resolved_bundle, "r:gz") as archive:
        members = archive.getmembers()
        _validate_members(members)
        manifest = _load_manifest(archive)
        target_root = _target_root_for(
            manifest=manifest, artifacts_dir=artifacts_dir, collision_policy=collision_policy
        )
        temp_root = artifacts_dir / f".import-{uuid.uuid4().hex}"
        try:
            _extract_artifacts(archive=archive, members=members, temp_root=temp_root)
            _validate_extracted_files(manifest=manifest, temp_root=temp_root)
            warnings = _rewrite_imported_metadata(
                artifact_root=temp_root,
                original_root=manifest.original_artifact_root.expanduser().resolve(),
                target_root=target_root,
            )
            if target_root.exists():
                _remove_existing_target(target_root)
            target_root.parent.mkdir(parents=True, exist_ok=True)
            temp_root.rename(target_root)
        except Exception:
            shutil.rmtree(temp_root, ignore_errors=True)
            raise
    return RunBundleImportResult(artifact_root=target_root, manifest=manifest, warnings=warnings)


def _build_manifest(artifact_root: Path, *, output_path: Path) -> RunBundleManifest:
    files = _inventory_files(artifact_root, output_path=output_path)
    run_summary = _load_run_summary(artifact_root / "summary" / "run_summary.json")
    run_id = run_summary.run_id if run_summary is not None else artifact_root.parent.name
    return RunBundleManifest(
        package_version=_package_version(),
        exported_run_id=run_id,
        artifact_label=f"{artifact_root.parent.name}/{artifact_root.name}",
        original_artifact_root=artifact_root,
        exported_at_ns=time.time_ns(),
        files=files,
    )


def _inventory_files(artifact_root: Path, *, output_path: Path) -> list[RunBundleFile]:
    rows: list[RunBundleFile] = []
    for path in sorted(item for item in artifact_root.rglob("*") if item.is_file()):
        resolved = path.resolve()
        if resolved == output_path:
            continue
        if path.is_symlink():
            raise RuntimeError(f"Refusing to export symlink artifact '{path}'.")
        relative_path = path.relative_to(artifact_root)
        rows.append(
            RunBundleFile(
                relative_path=relative_path,
                size_bytes=path.stat().st_size,
                sha256=hash_path(path),
            )
        )
    return rows


def _load_run_summary(path: Path) -> RunSummary | None:
    if not path.exists():
        return None
    return RunSummary.model_validate_json(path.read_text(encoding="utf-8"))


def _package_version() -> str:
    try:
        return version("prml-vslam")
    except PackageNotFoundError:
        return "0+unknown"


def _validate_bundle_output_path(path: Path) -> None:
    if not path.name.endswith(".prmlrun.tar.gz"):
        raise ValueError(f"Run bundle path must end with `.prmlrun.tar.gz`, got '{path}'.")


def _validate_members(members: list[tarfile.TarInfo]) -> None:
    names = {member.name for member in members}
    if _MANIFEST_MEMBER not in names:
        raise RuntimeError("Run bundle is missing `manifest.json`.")
    seen: set[str] = set()
    for member in members:
        if member.name in seen:
            raise RuntimeError(f"Run bundle contains duplicate member '{member.name}'.")
        seen.add(member.name)
        _validate_member_path(member.name)
        if member.isdir():
            continue
        if not member.isfile():
            raise RuntimeError(f"Unsafe run bundle member type: '{member.name}'.")


def _validate_member_path(name: str) -> None:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        raise RuntimeError(f"Unsafe run bundle member path: '{name}'.")
    if name == _MANIFEST_MEMBER:
        return
    if not path.parts or path.parts[0] != _ARTIFACTS_PREFIX:
        raise RuntimeError(f"Unexpected run bundle member path: '{name}'.")


def _load_manifest(archive: tarfile.TarFile) -> RunBundleManifest:
    member = archive.getmember(_MANIFEST_MEMBER)
    stream = archive.extractfile(member)
    if stream is None:
        raise RuntimeError("Failed to read run bundle manifest.")
    manifest = RunBundleManifest.model_validate_json(stream.read().decode("utf-8"))
    if manifest.schema_version != _BUNDLE_SCHEMA_VERSION:
        raise RuntimeError(f"Unsupported run bundle schema version {manifest.schema_version}.")
    return manifest


def _target_root_for(
    *,
    manifest: RunBundleManifest,
    artifacts_dir: Path,
    collision_policy: RunBundleCollisionPolicy,
) -> Path:
    relative = Path(manifest.artifact_label)
    if relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError(f"Unsafe artifact label in run bundle: '{manifest.artifact_label}'.")
    target = (artifacts_dir / relative).resolve()
    _ensure_under(target, artifacts_dir)
    if not target.exists():
        return target
    match collision_policy:
        case RunBundleCollisionPolicy.FAIL:
            raise FileExistsError(f"Imported run target already exists: '{target}'.")
        case RunBundleCollisionPolicy.OVERWRITE:
            return target
        case RunBundleCollisionPolicy.RENAME:
            for index in range(1, 1000):
                renamed = target.with_name(f"{target.name}-imported-{index}")
                if not renamed.exists():
                    return renamed
    raise RuntimeError(f"Could not resolve import target for '{target}'.")


def _extract_artifacts(*, archive: tarfile.TarFile, members: list[tarfile.TarInfo], temp_root: Path) -> None:
    temp_root.mkdir(parents=True, exist_ok=False)
    for member in members:
        if member.name == _MANIFEST_MEMBER or member.isdir():
            continue
        relative = Path(PurePosixPath(member.name).relative_to(_ARTIFACTS_PREFIX))
        target = (temp_root / relative).resolve()
        _ensure_under(target, temp_root)
        target.parent.mkdir(parents=True, exist_ok=True)
        stream = archive.extractfile(member)
        if stream is None:
            raise RuntimeError(f"Failed to read run bundle member '{member.name}'.")
        with target.open("wb") as output:
            shutil.copyfileobj(stream, output)


def _validate_extracted_files(*, manifest: RunBundleManifest, temp_root: Path) -> None:
    expected = {file.relative_path.as_posix(): file for file in manifest.files}
    actual = {path.relative_to(temp_root).as_posix() for path in temp_root.rglob("*") if path.is_file()}
    if actual != set(expected):
        unexpected = sorted(actual - set(expected))
        missing = sorted(set(expected) - actual)
        raise RuntimeError(f"Imported bundle file inventory mismatch; unexpected={unexpected}, missing={missing}.")
    for relative_path, file in expected.items():
        path = (temp_root / file.relative_path).resolve()
        _ensure_under(path, temp_root)
        if not path.is_file():
            raise RuntimeError(f"Imported bundle is missing file '{relative_path}'.")
        if path.stat().st_size != file.size_bytes:
            raise RuntimeError(f"Imported bundle file '{relative_path}' has the wrong size.")
        if hash_path(path) != file.sha256:
            raise RuntimeError(f"Imported bundle file '{relative_path}' failed SHA-256 validation.")


def _rewrite_imported_metadata(*, artifact_root: Path, original_root: Path, target_root: Path) -> list[str]:
    warnings: list[str] = []
    summary_path = artifact_root / "summary" / "run_summary.json"
    if summary_path.exists():
        summary = RunSummary.model_validate_json(summary_path.read_text(encoding="utf-8"))
        write_json(summary_path, summary.model_copy(update={"artifact_root": target_root}))

    stage_manifests_path = artifact_root / "summary" / "stage_manifests.json"
    if stage_manifests_path.exists():
        stage_manifests = _STAGE_MANIFESTS_ADAPTER.validate_json(stage_manifests_path.read_text(encoding="utf-8"))
        relocated_manifests: list[StageManifest] = []
        for manifest in stage_manifests:
            output_paths: dict[str, Path] = {}
            for key, value in manifest.output_paths.items():
                relocated, path_warning = _relocate_path(value, original_root=original_root, target_root=target_root)
                output_paths[key] = relocated
                if path_warning is not None:
                    warnings.append(path_warning)
            relocated_manifests.append(manifest.model_copy(update={"output_paths": output_paths}))
        write_json(stage_manifests_path, relocated_manifests)

    for json_path in (
        artifact_root / "input" / "sequence_manifest.json",
        artifact_root / "benchmark" / "inputs.json",
    ):
        if json_path.exists():
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            relocated, path_warnings = _relocate_json_value(
                payload,
                original_root=original_root,
                target_root=target_root,
            )
            warnings.extend(path_warnings)
            json_path.write_text(json.dumps(relocated, indent=2, sort_keys=True), encoding="utf-8")

    events_path = artifact_root / "summary" / "run-events.jsonl"
    if events_path.exists():
        relocated_lines: list[str] = []
        for line in events_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            relocated, path_warnings = _relocate_json_value(
                payload,
                original_root=original_root,
                target_root=target_root,
            )
            warnings.extend(path_warnings)
            relocated_lines.append(json.dumps(relocated, sort_keys=True))
            _RUN_EVENTS_ADAPTER.validate_json(relocated_lines[-1])
        events_path.write_text("\n".join(relocated_lines) + ("\n" if relocated_lines else ""), encoding="utf-8")
    return sorted(set(warnings))


def _relocate_path(path: Path, *, original_root: Path, target_root: Path) -> tuple[Path, str | None]:
    try:
        relative = path.expanduser().resolve().relative_to(original_root)
    except ValueError:
        return path, _external_path_warning(path.as_posix(), original_root=original_root)
    return (target_root / relative).resolve(), None


def _relocate_json_value(
    value: JsonValue,
    *,
    original_root: Path,
    target_root: Path,
) -> tuple[JsonValue, list[str]]:
    warnings: list[str] = []
    if isinstance(value, dict):
        relocated: dict[str, JsonValue] = {}
        for key, item in value.items():
            relocated_item, item_warnings = _relocate_json_value(
                item, original_root=original_root, target_root=target_root
            )
            relocated[key] = relocated_item
            warnings.extend(item_warnings)
        return relocated, warnings
    if isinstance(value, list):
        relocated_items: list[JsonValue] = []
        for item in value:
            relocated_item, item_warnings = _relocate_json_value(
                item, original_root=original_root, target_root=target_root
            )
            relocated_items.append(relocated_item)
            warnings.extend(item_warnings)
        return relocated_items, warnings
    if isinstance(value, str):
        relocated = _relocate_path_string(value, original_root=original_root, target_root=target_root)
        if relocated is not None:
            return relocated, warnings
        warning = _external_path_warning(value, original_root=original_root)
        if warning is not None:
            warnings.append(warning)
    return value, warnings


def _relocate_path_string(value: str, *, original_root: Path, target_root: Path) -> str | None:
    original_prefix = original_root.as_posix()
    if value == original_prefix:
        return target_root.as_posix()
    prefix = f"{original_prefix}/"
    if value.startswith(prefix):
        return (target_root / value.removeprefix(prefix)).resolve().as_posix()
    return None


def _ensure_under(path: Path, root: Path) -> None:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise RuntimeError(f"Unsafe path outside target root: '{path}'.") from exc


def _remove_existing_target(target: Path) -> None:
    if target.is_dir():
        shutil.rmtree(target)
        return
    target.unlink()


def _external_path_warning(value: str, *, original_root: Path) -> str | None:
    path = Path(value)
    if not path.is_absolute():
        return None
    try:
        path.expanduser().resolve().relative_to(original_root)
    except ValueError:
        return f"Preserved external path outside exported run root: {value}"
    return None


class _BytesReader:
    """Small file-like wrapper for bytes passed to :mod:`tarfile`."""

    def __init__(self, payload: bytes) -> None:
        self._payload = payload
        self._offset = 0

    def read(self, size: int = -1) -> bytes:
        """Read bytes for `tarfile.addfile`."""
        if size is None or size < 0:
            size = len(self._payload) - self._offset
        start = self._offset
        end = min(len(self._payload), self._offset + size)
        self._offset = end
        return self._payload[start:end]


__all__ = [
    "RunBundleCollisionPolicy",
    "RunBundleExportResult",
    "RunBundleImportResult",
    "RunBundleManifest",
    "export_run_bundle",
    "import_run_bundle",
]
