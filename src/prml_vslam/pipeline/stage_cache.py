"""Content-addressed cache helpers for offline pipeline stage results.

The cache stores durable stage artifacts and enough typed provenance to rebuild
the terminal :class:`prml_vslam.pipeline.stages.base.contracts.StageResult`
inside a new run root. It deliberately stays behind the existing artifact
contracts: TUM, PLY, JSON, YAML, and viewer files remain the public outputs.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import uuid
from enum import Enum
from pathlib import Path
from typing import Any, TypeAlias

from pydantic import Field

from prml_vslam.eval.contracts import EvaluationArtifact
from prml_vslam.interfaces.alignment import GroundAlignmentMetadata
from prml_vslam.interfaces.artifacts import ArtifactRef
from prml_vslam.interfaces.slam import SlamArtifacts
from prml_vslam.pipeline.contracts.events import StageOutcome
from prml_vslam.pipeline.contracts.provenance import StageCacheInfo, StageStatus
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.finalization import stable_hash, write_json
from prml_vslam.pipeline.stages.base.config import StageConfig
from prml_vslam.pipeline.stages.base.contracts import StageResult, StageRuntimeStatus
from prml_vslam.reconstruction.contracts import ReconstructionArtifacts
from prml_vslam.sources.contracts import PreparedBenchmarkInputs, SequenceManifest, SourceStageOutput
from prml_vslam.utils import BaseConfig, BaseData, RunArtifactPaths

HashPayload: TypeAlias = (
    BaseData
    | BaseConfig
    | Path
    | dict[str, Any]
    | list[Any]
    | tuple[Any, ...]
    | set[Any]
    | str
    | int
    | float
    | bool
    | None
)

_CACHE_SCHEMA_VERSION = 1
_HASH_CHUNK_BYTES = 1024 * 1024


class ContentFingerprinter:
    """Compute deterministic content fingerprints for cache key inputs."""

    def hash_value(self, value: HashPayload) -> str:
        """Return a SHA-256 digest for a nested cache-key payload."""
        normalized = self._normalize(value)
        encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def hash_path(self, path: Path) -> str:
        """Return a SHA-256 digest for a file or directory tree."""
        resolved = path.expanduser().resolve()
        if resolved.is_file():
            return self._hash_file(resolved)
        if resolved.is_dir():
            digest = hashlib.sha256()
            digest.update(b"dir-v1\0")
            for child in sorted(item for item in resolved.rglob("*") if item.is_file()):
                relative = child.relative_to(resolved).as_posix().encode("utf-8")
                digest.update(relative)
                digest.update(b"\0")
                digest.update(self._hash_file(child).encode("ascii"))
                digest.update(b"\0")
            return digest.hexdigest()
        return self.hash_value({"missing_path": resolved.as_posix()})

    def _normalize(self, value: HashPayload) -> Any:
        if isinstance(value, ArtifactRef):
            return {
                "artifact_kind": value.kind,
                "content_sha256": self.hash_path(value.path),
            }
        if isinstance(value, StageConfig):
            return self._normalize(value.model_dump(mode="python", round_trip=True, exclude={"cache"}))
        if isinstance(value, BaseData):
            return self._normalize(value.model_dump(mode="python", round_trip=True))
        if isinstance(value, BaseConfig):
            return self._normalize(value.model_dump(mode="python", round_trip=True))
        if isinstance(value, Path):
            resolved = value.expanduser().resolve()
            if resolved.exists():
                return {
                    "path_kind": "dir" if resolved.is_dir() else "file",
                    "content_sha256": self.hash_path(resolved),
                }
            return {"path_kind": "missing", "path": resolved.as_posix()}
        if isinstance(value, dict):
            return {
                str(key): self._normalize(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            }
        if isinstance(value, list | tuple):
            return [self._normalize(item) for item in value]
        if isinstance(value, set):
            return sorted(self._normalize(item) for item in value)
        if isinstance(value, Enum):
            return value.value
        return BaseConfig.to_jsonable(value)

    @staticmethod
    def _hash_file(path: Path) -> str:
        digest = hashlib.sha256()
        digest.update(b"file-v1\0")
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(_HASH_CHUNK_BYTES), b""):
                digest.update(chunk)
        return digest.hexdigest()


class StageCacheKey(BaseData):
    """Stable content-addressed key for one stage result."""

    stage_key: StageKey
    """Stage whose result is cached."""

    config_hash: str
    """Content hash of the stage-relevant config payload."""

    input_fingerprint: str
    """Content hash of the stage-relevant input payload."""

    cache_key: str
    """Final digest used as the cache entry id."""

    @classmethod
    def build(cls, *, stage_key: StageKey, config_hash: str, input_fingerprint: str) -> StageCacheKey:
        """Build the final stable cache key from stage, config, and input hashes."""
        cache_key = stable_hash(
            {
                "schema": "stage-cache-v1",
                "stage_key": stage_key.value,
                "config_hash": config_hash,
                "input_fingerprint": input_fingerprint,
            }
        )
        return cls(
            stage_key=stage_key,
            config_hash=config_hash,
            input_fingerprint=input_fingerprint,
            cache_key=cache_key,
        )


class CachedStageArtifact(BaseData):
    """One durable artifact copied into a cache entry."""

    artifact_key: str
    """Stage-local artifact map key."""

    kind: str
    """Artifact kind from the original :class:`ArtifactRef`."""

    relative_path: Path
    """Artifact path relative to the original run artifact root."""

    content_hash: str
    """SHA-256 content hash of the cached file or directory."""

    original_fingerprint: str
    """Original artifact fingerprint recorded by the stage runtime."""


class StageCacheEntry(BaseData):
    """Manifest stored beside one cached stage-result artifact set."""

    schema_version: int = _CACHE_SCHEMA_VERSION
    """Cache entry schema version."""

    key: StageCacheKey
    """Content-addressed cache key."""

    status: StageStatus
    """Terminal stage status stored in the entry."""

    metrics: dict[str, float | int | str] = Field(default_factory=dict)
    """Terminal stage metrics."""

    error_message: str = ""
    """Terminal error message, expected to be empty for cached successes."""

    artifacts: list[CachedStageArtifact] = Field(default_factory=list)
    """Artifact files and directories copied into the cache entry."""

    final_runtime_status: StageRuntimeStatus
    """Final runtime status to project when the cache entry is reused."""


class StageCacheStore:
    """Read and write content-addressed offline stage-result cache entries."""

    def __init__(self, cache_root: Path) -> None:
        self.cache_root = cache_root.expanduser().resolve()
        self._fingerprinter = ContentFingerprinter()

    def entry_dir(self, key: StageCacheKey) -> Path:
        """Return the directory for one cache key."""
        return (self.cache_root / key.stage_key.value / key.cache_key).resolve()

    def read(self, key: StageCacheKey, *, artifact_root: Path) -> StageResult | None:
        """Hydrate a cached stage result into ``artifact_root`` when available."""
        entry_dir = self.entry_dir(key)
        entry_path = entry_dir / "stage_cache_entry.json"
        if not entry_path.exists():
            return None
        try:
            entry = StageCacheEntry.model_validate_json(entry_path.read_text(encoding="utf-8"))
            self._validate_entry(key=key, entry=entry, entry_dir=entry_dir)
            artifacts = self._hydrate_artifacts(entry=entry, entry_dir=entry_dir, artifact_root=artifact_root)
        except (OSError, ValueError, RuntimeError):
            return None
        cache_info = StageCacheInfo(
            cache_key=key.cache_key,
            cache_root=self.cache_root,
            hit=True,
            entry_path=entry_dir,
        )
        outcome = StageOutcome(
            stage_key=key.stage_key,
            status=entry.status,
            config_hash=key.config_hash,
            input_fingerprint=key.input_fingerprint,
            artifacts=artifacts,
            metrics=entry.metrics,
            error_message=entry.error_message,
            cache=cache_info,
        )
        return StageResult(
            stage_key=key.stage_key,
            payload=_payload_for_cached_stage(
                stage_key=key.stage_key, artifacts=artifacts, artifact_root=artifact_root
            ),
            outcome=outcome,
            final_runtime_status=entry.final_runtime_status.model_copy(
                update={
                    "lifecycle_state": entry.status,
                    "progress_message": "Reused stage result from cache.",
                }
            ),
        )

    def write(self, key: StageCacheKey, *, result: StageResult, artifact_root: Path) -> Path | None:
        """Persist one successful stage result to the cache if it is not present."""
        if result.outcome.status not in {StageStatus.COMPLETED, StageStatus.SKIPPED}:
            return None
        entry_dir = self.entry_dir(key)
        if entry_dir.exists():
            return entry_dir
        temp_dir = entry_dir.parent / f".{entry_dir.name}.{uuid.uuid4().hex}.tmp"
        artifacts_dir = temp_dir / "artifacts"
        temp_dir.mkdir(parents=True, exist_ok=False)
        try:
            cached_artifacts = self._copy_artifacts_to_cache(
                result=result,
                artifact_root=artifact_root.expanduser().resolve(),
                artifacts_dir=artifacts_dir,
            )
            write_json(
                temp_dir / "stage_cache_entry.json",
                StageCacheEntry(
                    key=key,
                    status=result.outcome.status,
                    metrics=result.outcome.metrics,
                    error_message=result.outcome.error_message,
                    artifacts=cached_artifacts,
                    final_runtime_status=result.final_runtime_status,
                ),
            )
            entry_dir.parent.mkdir(parents=True, exist_ok=True)
            try:
                temp_dir.rename(entry_dir)
            except FileExistsError:
                shutil.rmtree(temp_dir, ignore_errors=True)
            return entry_dir
        except Exception:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise

    def _copy_artifacts_to_cache(
        self,
        *,
        result: StageResult,
        artifact_root: Path,
        artifacts_dir: Path,
    ) -> list[CachedStageArtifact]:
        cached: list[CachedStageArtifact] = []
        for artifact_key, artifact in sorted(result.outcome.artifacts.items()):
            relative_path = _relative_artifact_path(artifact.path, artifact_root=artifact_root)
            if relative_path is None:
                continue
            source = artifact.path.expanduser().resolve()
            if not source.exists():
                raise FileNotFoundError(f"Cannot cache missing artifact '{source}'.")
            target = (artifacts_dir / relative_path).resolve()
            _copy_artifact(source, target)
            cached.append(
                CachedStageArtifact(
                    artifact_key=artifact_key,
                    kind=artifact.kind,
                    relative_path=relative_path,
                    content_hash=self._fingerprinter.hash_path(target),
                    original_fingerprint=artifact.fingerprint,
                )
            )
        return cached

    def _hydrate_artifacts(
        self,
        *,
        entry: StageCacheEntry,
        entry_dir: Path,
        artifact_root: Path,
    ) -> dict[str, ArtifactRef]:
        hydrated: dict[str, ArtifactRef] = {}
        for artifact in entry.artifacts:
            cached_path = (entry_dir / "artifacts" / artifact.relative_path).resolve()
            if not _is_relative_to(cached_path, entry_dir / "artifacts"):
                raise RuntimeError(f"Unsafe cached artifact path '{cached_path}'.")
            if self._fingerprinter.hash_path(cached_path) != artifact.content_hash:
                raise RuntimeError(f"Cached artifact '{artifact.relative_path}' failed content validation.")
            target = (artifact_root.expanduser().resolve() / artifact.relative_path).resolve()
            if not _is_relative_to(target, artifact_root.expanduser().resolve()):
                raise RuntimeError(f"Unsafe target artifact path '{target}'.")
            _copy_artifact(cached_path, target)
            hydrated[artifact.artifact_key] = ArtifactRef(
                path=target,
                kind=artifact.kind,
                fingerprint=stable_hash({"path": target.as_posix(), "kind": artifact.kind}),
            )
        return hydrated

    @staticmethod
    def _validate_entry(*, key: StageCacheKey, entry: StageCacheEntry, entry_dir: Path) -> None:
        if entry.schema_version != _CACHE_SCHEMA_VERSION:
            raise RuntimeError(f"Unsupported stage cache schema version {entry.schema_version}.")
        if entry.key != key:
            raise RuntimeError(f"Stage cache key mismatch at '{entry_dir}'.")


def _payload_for_cached_stage(
    *,
    stage_key: StageKey,
    artifacts: dict[str, ArtifactRef],
    artifact_root: Path,
) -> BaseData | None:
    run_paths = RunArtifactPaths.build(artifact_root)
    match stage_key:
        case StageKey.SOURCE:
            if not run_paths.sequence_manifest_path.exists():
                return None
            sequence_manifest = SequenceManifest.model_validate_json(
                run_paths.sequence_manifest_path.read_text(encoding="utf-8")
            )
            benchmark_inputs = (
                PreparedBenchmarkInputs.model_validate_json(run_paths.benchmark_inputs_path.read_text(encoding="utf-8"))
                if run_paths.benchmark_inputs_path.exists()
                else None
            )
            return SourceStageOutput(sequence_manifest=sequence_manifest, benchmark_inputs=benchmark_inputs)
        case StageKey.SLAM:
            trajectory = artifacts.get("trajectory_tum")
            if trajectory is None:
                return None
            extras = {key.removeprefix("extra:"): value for key, value in artifacts.items() if key.startswith("extra:")}
            return SlamArtifacts(
                trajectory_tum=trajectory,
                sparse_points_ply=artifacts.get("sparse_points_ply"),
                dense_points_ply=artifacts.get("dense_points_ply"),
                extras=extras,
            )
        case StageKey.GRAVITY_ALIGNMENT:
            ground_alignment = artifacts.get("ground_alignment")
            if ground_alignment is None or not ground_alignment.path.exists():
                return None
            return GroundAlignmentMetadata.model_validate_json(ground_alignment.path.read_text(encoding="utf-8"))
        case StageKey.TRAJECTORY_EVALUATION:
            trajectory_metrics = artifacts.get("trajectory_metrics")
            if trajectory_metrics is None or not trajectory_metrics.path.exists():
                return None
            return EvaluationArtifact.model_validate_json(trajectory_metrics.path.read_text(encoding="utf-8"))
        case StageKey.RECONSTRUCTION:
            reference_cloud = artifacts.get("reference_cloud")
            metadata = artifacts.get("reconstruction_metadata")
            if reference_cloud is None or metadata is None:
                return None
            extras = {
                key.removeprefix("extra:"): value.path for key, value in artifacts.items() if key.startswith("extra:")
            }
            return ReconstructionArtifacts(
                reference_cloud_path=reference_cloud.path,
                metadata_path=metadata.path,
                mesh_path=None if artifacts.get("reference_mesh") is None else artifacts["reference_mesh"].path,
                extras=extras,
            )
        case _:
            return None


def _relative_artifact_path(path: Path, *, artifact_root: Path) -> Path | None:
    try:
        return path.expanduser().resolve().relative_to(artifact_root)
    except ValueError:
        return None


def _copy_artifact(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
    if source.is_dir():
        shutil.copytree(source, target)
        return
    shutil.copy2(source, target)


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


__all__ = [
    "ContentFingerprinter",
    "StageCacheEntry",
    "StageCacheKey",
    "StageCacheStore",
]
