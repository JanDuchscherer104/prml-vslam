"""Tests for ViSTA-native persisted artifact diagnostics."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from prml_vslam.interfaces import FrameTransform
from prml_vslam.methods.vista.artifact_io import (
    load_vista_confidences,
    load_vista_intrinsics_matrices,
    load_vista_native_trajectory,
    load_vista_vector,
    load_vista_view_graph,
    load_vista_view_names,
)
from prml_vslam.methods.vista.diagnostics import load_vista_native_slam_diagnostics
from prml_vslam.utils.geometry import write_tum_trajectory


def test_load_vista_native_slam_diagnostics_from_synthetic_artifacts(tmp_path: Path) -> None:
    artifact_root = tmp_path / "run"
    native_dir = artifact_root / "native"
    native_dir.mkdir(parents=True)
    _write_intrinsics_yaml(artifact_root / "input" / "intrinsics.yaml")
    confs = np.asarray(
        [
            [[1.0, 5.0], [6.0, 2.0]],
            [[7.0, 8.0], [3.0, 4.0]],
            [[2.0, 2.0], [9.0, 10.0]],
        ],
        dtype=np.float32,
    )
    np.savez(native_dir / "confs.npz", confs=confs, thres=np.asarray(4.2))
    np.save(native_dir / "scales.npy", np.asarray([[1.0], [1.2], [0.9]], dtype=np.float32))
    intrinsics = np.asarray(
        [
            [[10.0, 0.0, 5.0], [0.0, 11.0, 6.0], [0.0, 0.0, 1.0]],
            [[12.0, 0.0, 5.5], [0.0, 13.0, 6.5], [0.0, 0.0, 1.0]],
            [[14.0, 0.0, 6.0], [0.0, 15.0, 7.0], [0.0, 0.0, 1.0]],
        ],
        dtype=np.float32,
    )
    np.save(native_dir / "intrinsics.npy", intrinsics)
    trajectory = np.tile(np.eye(4, dtype=np.float32), (3, 1, 1))
    trajectory[:, 0, 3] = np.asarray([0.0, 1.0, 1.0], dtype=np.float32)
    trajectory[:, 1, 3] = np.asarray([0.0, 0.0, 2.0], dtype=np.float32)
    np.save(native_dir / "trajectory.npy", trajectory)
    np.savez(
        native_dir / "view_graph.npz",
        view_graph=np.asarray({0: [1, 2], 1: [0, 2], 2: [0, 1]}, dtype=object),
        loop_min_dist=np.asarray(1),
        view_names=np.asarray(["frame_000000", "frame_000001", "frame_000002"]),
    )
    write_tum_trajectory(
        artifact_root / "slam" / "trajectory.tum",
        poses=[
            FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
            FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=0.0, tz=0.0),
            FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=2.0, tz=0.0),
        ],
        timestamps=[0.0, 0.5, 1.25],
    )

    diagnostics = load_vista_native_slam_diagnostics(artifact_root)

    assert diagnostics.keyframe_indices == [0, 1, 2]
    assert diagnostics.confidence_threshold == 4.2
    assert diagnostics.confidence_valid_ratio == [0.5, 0.5, 0.5]
    assert diagnostics.scales == [1.0, 1.2000000476837158, 0.8999999761581421]
    assert diagnostics.fx == [10.0, 12.0, 14.0]
    assert diagnostics.estimated_intrinsics is not None
    assert diagnostics.estimated_intrinsics.raster_space == "vista_model"
    assert diagnostics.intrinsics_comparison is not None
    assert diagnostics.intrinsics_comparison.reference.width_px == 224
    assert diagnostics.native_step_distance_m == [1.0, 2.0]
    assert diagnostics.slam_sample_intervals_s == [0.5, 0.75]
    assert diagnostics.view_graph is not None
    assert diagnostics.view_graph.node_count == 3
    assert diagnostics.view_graph.edge_count == 3
    assert [(edge.source, edge.target, edge.frame_gap) for edge in diagnostics.view_graph.loop_edges] == [(0, 2, 2)]


def test_vista_artifact_io_loads_native_arrays(tmp_path: Path) -> None:
    native_dir = tmp_path / "native"
    native_dir.mkdir()
    confs = np.asarray([[[1.0, 5.0], [6.0, 2.0]]], dtype=np.float32)
    intrinsics = np.asarray([[[10.0, 0.0, 5.0], [0.0, 11.0, 6.0], [0.0, 0.0, 1.0]]], dtype=np.float32)
    trajectory = np.eye(4, dtype=np.float32)[None, :, :]
    np.savez(native_dir / "confs.npz", confs=confs, thres=np.asarray(4.2))
    np.save(native_dir / "scales.npy", np.asarray([1.0], dtype=np.float32))
    np.save(native_dir / "intrinsics.npy", intrinsics)
    np.save(native_dir / "trajectory.npy", trajectory)
    np.savez(
        native_dir / "view_graph.npz",
        view_graph=np.asarray({0: []}, dtype=object),
        loop_min_dist=np.asarray(1),
        view_names=np.asarray(["frame_000000"]),
    )

    loaded_confs, threshold = load_vista_confidences(native_dir / "confs.npz")
    scales = load_vista_vector(native_dir / "scales.npy", expected_length=1, name="scales")
    loaded_intrinsics = load_vista_intrinsics_matrices(native_dir / "intrinsics.npy", expected_length=1)
    positions, step_distance = load_vista_native_trajectory(native_dir / "trajectory.npy", expected_length=1)
    view_graph = load_vista_view_graph(native_dir / "view_graph.npz")

    np.testing.assert_allclose(loaded_confs, confs)
    assert threshold == 4.2
    np.testing.assert_allclose(scales, [1.0])
    np.testing.assert_allclose(loaded_intrinsics, intrinsics)
    np.testing.assert_allclose(positions, [[0.0, 0.0, 0.0]])
    assert step_distance.size == 0
    assert view_graph.view_graph == {0: []}
    assert view_graph.loop_min_dist == 1
    assert view_graph.view_names == ["frame_000000"]
    assert load_vista_view_names(native_dir / "view_graph.npz", count=1) == ["frame_000000"]


def test_vista_view_graph_rejects_non_integer_like_node_ids(tmp_path: Path) -> None:
    path = tmp_path / "view_graph.npz"
    np.savez(path, view_graph=np.asarray({("not", "a-node"): []}, dtype=object))

    with pytest.raises(ValueError, match="integer-like"):
        load_vista_view_graph(path)


def test_vista_view_graph_rejects_text_neighbors(tmp_path: Path) -> None:
    path = tmp_path / "view_graph.npz"
    np.savez(path, view_graph=np.asarray({0: "123"}, dtype=object))

    with pytest.raises(ValueError, match="iterable of node ids"):
        load_vista_view_graph(path)


def _write_intrinsics_yaml(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """
cameras:
- camera:
    image_height: 480
    image_width: 640
    intrinsics:
      data: [517.3, 516.5, 318.6, 255.3]
    distortion:
      type: radial-tangential
      parameters:
        data: [0.2624, -0.9531, -0.0054, 0.0026, 1.1633]
""".strip(),
        encoding="utf-8",
    )
