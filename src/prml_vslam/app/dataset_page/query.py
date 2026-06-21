"""Read-only normalized datastore query helpers for the datasets page."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, cast

import streamlit as st
from evo.core.trajectory import PoseTrajectory3D  # type: ignore[import-untyped]
from plotly.graph_objects import Figure

from prml_vslam.plotting.datasets import build_reference_cloud_scene_figure
from prml_vslam.sources.datasets.contracts import DatasetId
from prml_vslam.sources.datasets.normalized_query import (
    NormalizedDatasetQuery,
    NormalizedReferenceCloudArtifact,
    NormalizedTrajectoryArtifact,
    normalized_query_fingerprint,
    query_normalized_dataset,
)
from prml_vslam.utils import PathConfig
from prml_vslam.utils.geometry import load_tum_trajectory

if TYPE_CHECKING:
    from ..bootstrap import AppContext


def load_normalized_dataset_snapshot_for_context(context: AppContext, dataset_id: DatasetId) -> NormalizedDatasetQuery:
    """Load one cached normalized datastore snapshot for a Streamlit rerun."""
    return load_normalized_dataset_snapshot(
        context.path_config.root.as_posix(),
        context.path_config.data_dir.as_posix(),
        dataset_id.value,
        normalized_query_fingerprint(context.path_config, dataset_id),
    )


def clear_normalized_dataset_snapshot_cache() -> None:
    """Invalidate cached normalized datastore query snapshots."""
    cast(Callable[[], None], load_normalized_dataset_snapshot.clear)()


@st.cache_data
def load_normalized_dataset_snapshot(
    root: str, data_dir: str, dataset_id: str, freshness_token: tuple[tuple[str, int, int], ...]
) -> NormalizedDatasetQuery:
    """Return the cached read-only normalized datastore projection."""
    del freshness_token
    path_config = PathConfig(root=Path(root), data_dir=Path(data_dir))
    dataset = DatasetId(dataset_id)
    return query_normalized_dataset(dataset, path_config)


def trajectory_artifact_cache_key(
    artifacts: list[NormalizedTrajectoryArtifact],
) -> tuple[tuple[str, str, int, int], ...]:
    """Build a cache token that changes when trajectory files change."""
    return tuple((artifact.label, *path_cache_token(artifact.path)) for artifact in artifacts)


def reference_cloud_artifact_cache_key(
    artifacts: list[NormalizedReferenceCloudArtifact],
) -> tuple[tuple[str, str, int, int], ...]:
    """Build a cache token that changes when reference-cloud files change."""
    return tuple((artifact.label, *path_cache_token(artifact.path)) for artifact in artifacts)


def path_cache_token(path: Path) -> tuple[str, int, int]:
    """Represent one artifact path and filesystem freshness metadata."""
    stat = path.stat()
    return (path.as_posix(), stat.st_mtime_ns, stat.st_size)


@st.cache_data
def load_scene_trajectory_series(
    artifacts: tuple[tuple[str, str, int, int], ...],
) -> list[tuple[str, PoseTrajectory3D]]:
    """Load normalized TUM trajectory artifacts for scene visualization."""
    return [(label, load_tum_trajectory(Path(path))) for label, path, _mtime_ns, _size in artifacts]


@st.cache_data
def build_reference_cloud_scene_figure_cached(
    clouds: tuple[tuple[str, str, int, int], ...],
    trajectories: tuple[tuple[str, str, int, int], ...],
) -> Figure:
    """Load reference-cloud artifacts and return a cached scene figure."""
    return build_reference_cloud_scene_figure(
        clouds=[(label, Path(path)) for label, path, _mtime_ns, _size in clouds],
        trajectories=load_scene_trajectory_series(trajectories),
    )
