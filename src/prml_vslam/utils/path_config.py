"""Centralized filesystem path handling for the PRML VSLAM project."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from pydantic import Field, ValidationInfo, field_validator

from .base_config import BaseConfig

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _default_root() -> Path:
    """Return the repository root used for root-relative paths."""
    return PROJECT_ROOT


class RunArtifactPaths(BaseConfig):
    """Typed layout for one planned benchmark run."""

    artifact_root: Path
    """Root directory for all artifacts in the run."""

    input_frames_dir: Path
    """Directory containing decoded input frames."""

    capture_manifest_path: Path
    """Path to the normalized capture manifest."""

    trajectory_path: Path
    """Path to the exported trajectory."""

    sparse_points_path: Path
    """Path to the exported sparse point cloud."""

    dense_points_path: Path
    """Path to the exported dense point cloud."""

    arcore_alignment_path: Path
    """Path to the ARCore alignment artifact."""

    reference_cloud_path: Path
    """Path to the reference reconstruction artifact."""


class PathConfig(BaseConfig):
    """Centralize all repository-owned path semantics."""

    root: Path = Field(default_factory=_default_root)
    """Repository root used to anchor relative paths."""

    artifacts_dir: Path = Field(default_factory=lambda: Path("artifacts"))
    """Default root directory for generated benchmark artifacts."""

    captures_dir: Path = Field(default_factory=lambda: Path("captures"))
    """Default root directory for input capture videos."""

    @field_validator("root", mode="before")
    @classmethod
    def _validate_root(cls, value: str | Path) -> Path:
        """Validate that the configured repository root exists."""
        root = Path(value).expanduser().resolve()
        if not root.exists():
            raise ValueError(f"Configured project root '{root}' does not exist.")
        return root

    @field_validator("artifacts_dir", "captures_dir", mode="before")
    @classmethod
    def _resolve_root_relative_dirs(cls, value: str | Path, info: ValidationInfo) -> Path:
        """Resolve configured directories against the repository root."""
        return cls._resolve_path(value, info)

    @classmethod
    def _resolve_path(cls, value: str | Path, info: ValidationInfo) -> Path:
        """Resolve a path relative to the configured repository root."""
        root = info.data.get("root", PROJECT_ROOT)
        path = Path(value)
        if not path.is_absolute():
            path = root / path
        return path.expanduser().resolve()

    def resolve_repo_path(self, path: str | Path, *, base_dir: Path | None = None) -> Path:
        """Resolve a path relative to the repository root or a provided base directory."""
        base_path = self.root if base_dir is None else self.resolve_repo_path(base_dir)
        resolved = Path(path)
        if not resolved.is_absolute():
            resolved = base_path / resolved
        return resolved.expanduser().resolve()

    def resolve_video_path(self, path: str | Path, *, must_exist: bool = False) -> Path:
        """Resolve a video path, defaulting bare filenames into the captures directory."""
        candidate = Path(path)
        base_dir = self.captures_dir if candidate.parent == Path() else self.root
        resolved = self.resolve_repo_path(candidate, base_dir=base_dir)
        if must_exist and not resolved.exists():
            raise FileNotFoundError(f"Video path '{resolved}' does not exist.")
        return resolved

    def resolve_output_dir(self, path: str | Path | None = None, *, create: bool = False) -> Path:
        """Resolve an output directory, defaulting to the configured artifacts root."""
        resolved = self.artifacts_dir if path is None else self.resolve_repo_path(path)
        if create:
            resolved.mkdir(parents=True, exist_ok=True)
        return resolved

    def resolve_toml_path(
        self,
        path: str | Path,
        *,
        must_exist: bool = False,
        create_parent: bool = False,
    ) -> Path:
        """Resolve a TOML file path relative to the repository root."""
        resolved = self.resolve_repo_path(path)
        if resolved.suffix != ".toml":
            raise ValueError(f"Config path must be a .toml file, got {resolved}")
        if create_parent:
            resolved.parent.mkdir(parents=True, exist_ok=True)
        if must_exist and not resolved.exists():
            raise FileNotFoundError(f"Config file not found: {resolved}")
        return resolved

    def slugify_experiment_name(self, experiment_name: str) -> str:
        """Convert a human-readable experiment name into a filesystem-safe slug."""
        slug = re.sub(r"[^a-z0-9]+", "-", experiment_name.strip().lower())
        return slug.strip("-") or "experiment"

    def plan_run_paths(
        self,
        *,
        experiment_name: str,
        method_slug: str,
        output_dir: str | Path | None = None,
    ) -> RunArtifactPaths:
        """Build the canonical artifact layout for one benchmark run."""
        artifact_root = (
            self.resolve_output_dir(output_dir) / self.slugify_experiment_name(experiment_name) / method_slug
        )
        return RunArtifactPaths(
            artifact_root=artifact_root,
            input_frames_dir=self.resolve_repo_path("frames", base_dir=artifact_root / "input"),
            capture_manifest_path=self.resolve_repo_path("capture_manifest.json", base_dir=artifact_root / "input"),
            trajectory_path=self.resolve_repo_path("trajectory.tum", base_dir=artifact_root / "slam"),
            sparse_points_path=self.resolve_repo_path("sparse_points.ply", base_dir=artifact_root / "slam"),
            dense_points_path=self.resolve_repo_path("dense_points.ply", base_dir=artifact_root / "dense"),
            arcore_alignment_path=self.resolve_repo_path(
                "arcore_alignment.json",
                base_dir=artifact_root / "evaluation",
            ),
            reference_cloud_path=self.resolve_repo_path("reference_cloud.ply", base_dir=artifact_root / "reference"),
        )


@lru_cache(maxsize=1)
def get_path_config() -> PathConfig:
    """Return the process-wide default path configuration."""
    return PathConfig()


__all__ = [
    "PROJECT_ROOT",
    "PathConfig",
    "RunArtifactPaths",
    "get_path_config",
]
