"""ViSTA-native artifact readers."""

from __future__ import annotations

from collections.abc import Hashable, Iterable, Mapping
from pathlib import Path

import numpy as np

from prml_vslam.interfaces.camera import CameraIntrinsicsSeries
from prml_vslam.utils import BaseData


class VistaViewGraphArtifact(BaseData):
    """Raw ViSTA view graph coerced into typed Python containers."""

    view_graph: dict[int, list[int]]
    """Adjacency mapping from keyframe index to neighboring keyframe indices."""

    loop_min_dist: int | None = None
    """Native loop minimum frame-distance setting, when available."""

    view_names: list[str] | None = None
    """Native view names aligned to keyframe index, when present and valid."""


def load_vista_confidences(path: Path) -> tuple[np.ndarray, float | None]:
    """Load native ViSTA confidence maps and optional threshold."""
    if not path.exists():
        raise FileNotFoundError(f"Native confidence artifact does not exist: {path}")
    data = np.load(path)
    if "confs" not in data.files:
        raise ValueError(f"Expected `confs` array in '{path}'.")
    confs = np.asarray(data["confs"], dtype=np.float64)
    if confs.ndim != 3:
        raise ValueError(f"Expected native confidence shape (N, H, W), got {confs.shape}.")
    if len(confs) == 0:
        raise ValueError(f"Native confidence artifact is empty: {path}")
    threshold = float(np.asarray(data["thres"]).reshape(())) if "thres" in data.files else None
    return confs, threshold


def load_vista_vector(path: Path, *, expected_length: int, name: str) -> np.ndarray:
    """Load one native ViSTA numeric vector and validate its length."""
    if not path.exists():
        raise FileNotFoundError(f"Native {name} artifact does not exist: {path}")
    values = np.asarray(np.load(path), dtype=np.float64).reshape(-1)
    if len(values) != expected_length:
        raise ValueError(f"Expected {expected_length} native {name} values, got {len(values)}.")
    return values


def load_vista_intrinsics_matrices(path: Path, *, expected_length: int) -> np.ndarray:
    """Load native ViSTA per-keyframe 3x3 intrinsics matrices."""
    if not path.exists():
        raise FileNotFoundError(f"Native intrinsics artifact does not exist: {path}")
    intrinsics = np.asarray(np.load(path), dtype=np.float64)
    if intrinsics.shape != (expected_length, 3, 3):
        raise ValueError(f"Expected native intrinsics shape ({expected_length}, 3, 3), got {intrinsics.shape}.")
    return intrinsics


def load_vista_native_trajectory(path: Path, *, expected_length: int) -> tuple[np.ndarray, np.ndarray]:
    """Load native ViSTA trajectory matrices and per-step translation distances."""
    if not path.exists():
        raise FileNotFoundError(f"Native trajectory artifact does not exist: {path}")
    trajectory = np.asarray(np.load(path), dtype=np.float64)
    if trajectory.shape != (expected_length, 4, 4):
        raise ValueError(f"Expected native trajectory shape ({expected_length}, 4, 4), got {trajectory.shape}.")
    positions = trajectory[:, :3, 3]
    step_distance = np.linalg.norm(np.diff(positions, axis=0), axis=1) if expected_length > 1 else np.empty(0)
    return positions, step_distance


def load_vista_view_graph(path: Path) -> VistaViewGraphArtifact:
    """Load and coerce native ViSTA view-graph metadata."""
    if not path.exists():
        raise FileNotFoundError(f"Native view-graph artifact does not exist: {path}")
    data = np.load(path, allow_pickle=True)
    if "view_graph" not in data.files:
        raise ValueError(f"Expected `view_graph` object in '{path}'.")
    view_graph = data["view_graph"].item()
    if not isinstance(view_graph, Mapping):
        raise ValueError(f"Expected native view graph to be a mapping, got {type(view_graph).__name__}.")
    coerced_view_graph = _coerce_view_graph(view_graph)
    return VistaViewGraphArtifact(
        view_graph=coerced_view_graph,
        loop_min_dist=int(np.asarray(data["loop_min_dist"]).reshape(())) if "loop_min_dist" in data.files else None,
        view_names=load_vista_view_names(path, count=len(coerced_view_graph)),
    )


def load_vista_estimated_intrinsics_series(path: Path) -> CameraIntrinsicsSeries | None:
    """Load the standardized estimated intrinsics artifact written by the ViSTA normalizer."""
    if not path.exists():
        return None
    return CameraIntrinsicsSeries.model_validate_json(path.read_text(encoding="utf-8"))


def load_vista_view_names(path: Path, *, count: int) -> list[str] | None:
    """Load native ViSTA view names when present and aligned to the expected keyframe count."""
    if not path.exists():
        return None
    data = np.load(path, allow_pickle=True)
    if "view_names" not in data.files:
        return None
    view_names = [str(value) for value in np.asarray(data["view_names"]).reshape(-1)]
    if len(view_names) != count:
        return None
    return view_names


def _coerce_view_graph(view_graph: Mapping[Hashable, Iterable[Hashable]]) -> dict[int, list[int]]:
    coerced: dict[int, list[int]] = {}
    for source_raw, neighbors_raw in view_graph.items():
        if isinstance(neighbors_raw, str | bytes):
            raise ValueError("Expected view-graph neighbors to be an iterable of node ids, got text.")
        source = _coerce_view_graph_node(source_raw)
        coerced[source] = [_coerce_view_graph_node(target_raw) for target_raw in neighbors_raw]
    return coerced


def _coerce_view_graph_node(value: Hashable) -> int:
    if isinstance(value, int | np.integer | str | bytes):
        return int(value)
    raise ValueError(f"Expected view-graph node id to be integer-like, got {type(value).__name__}.")


__all__ = [
    "VistaViewGraphArtifact",
    "load_vista_confidences",
    "load_vista_estimated_intrinsics_series",
    "load_vista_intrinsics_matrices",
    "load_vista_native_trajectory",
    "load_vista_vector",
    "load_vista_view_graph",
    "load_vista_view_names",
]
