"""Tests for run-level render-and-score image evaluation (the render-run engine)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np
import pytest

from prml_vslam.eval.render_eval import RenderEvalConfig, evaluate_run_from_artifact_root
from prml_vslam.interfaces.transforms import FrameTransform
from prml_vslam.rendering import write_image_rgb
from prml_vslam.utils.geometry import write_point_cloud_ply, write_tum_trajectory

_W, _H = 64, 64
_INTRINSICS_YAML = """
cameras:
- camera:
    image_width: 64
    image_height: 64
    intrinsics:
      data: [100.0, 100.0, 32.0, 32.0]
"""


def _build_synthetic_run(root: Path, *, frame_count: int = 5) -> None:
    (root / "input").mkdir(parents=True, exist_ok=True)
    (root / "slam").mkdir(parents=True, exist_ok=True)

    # Input frames + per-frame timestamps (0.0s, 0.1s, ...).
    timestamps_ns = [i * 100_000_000 for i in range(frame_count)]
    rng = np.random.default_rng(0)
    for i in range(frame_count):
        write_image_rgb(root / "input" / "frames" / f"{i:06d}.png", rng.integers(0, 256, (_H, _W, 3), dtype=np.uint8))
    (root / "input" / "timestamps.json").write_text(json.dumps({"frame_stride": 1, "timestamps_ns": timestamps_ns}))
    (root / "input" / "intrinsics.yaml").write_text(_INTRINSICS_YAML)

    # A colored point cloud in front of the camera.
    xs = np.linspace(-0.5, 0.5, 60)
    ys = np.linspace(-0.5, 0.5, 60)
    grid_x, grid_y = np.meshgrid(xs, ys)
    points = np.stack([grid_x.ravel(), grid_y.ravel(), np.full(grid_x.size, 2.0)], axis=1)
    colors = np.tile(np.array([200, 40, 40], dtype=np.uint8), (points.shape[0], 1))
    write_point_cloud_ply(root / "slam" / "point_cloud.ply", points, colors_rgb=colors)

    # Two keyframe poses at t=0.0s and t=0.2s -> pair to frames 0 and 2.
    identity = FrameTransform.from_matrix(np.eye(4), target_frame="world", source_frame="camera_rdf")
    write_tum_trajectory(root / "slam" / "trajectory.tum", [identity, identity], [0.0, 0.2])


def test_evaluate_run_from_artifact_root(tmp_path: Path) -> None:
    root = tmp_path / "run"
    _build_synthetic_run(root)

    result = evaluate_run_from_artifact_root(root, config=RenderEvalConfig(gallery_every=1))

    assert result.scored_pairs == 2
    assert result.summary.pair_count == 2
    assert set(result.summary.stats) == {"image.l1", "image.l2", "image.mse", "image.psnr", "image.ssim"}

    # Metrics JSON persisted at the canonical location.
    assert result.metrics_path == (root / "evaluation" / "image_metrics.json")
    assert result.metrics_path.exists()
    payload = json.loads(result.metrics_path.read_text())
    assert payload["pair_count"] == 2

    # Gallery written with GT / rendered / side-by-side.
    assert result.gallery_dir == (root / "evaluation" / "render_eval")
    for sub in ("gt", "rendered", "side_by_side"):
        files = sorted((result.gallery_dir / sub).glob("*.png"))
        assert len(files) == 2
        assert files[0].name == "000000_src000000.png"
    # Second pose (t=0.2s) paired to frame index 2.
    assert (result.gallery_dir / "rendered" / "000001_src000002.png").exists()


def test_manifest_rgb_dir_resolves_frames_outside_canonical(tmp_path: Path) -> None:
    root = tmp_path / "run"
    _build_synthetic_run(root)

    # Relocate the RGB frames to a source-owned directory and point the persisted
    # sequence manifest at it, then remove the canonical input/frames entirely.
    source_rgb = tmp_path / "source_rgb"
    source_rgb.mkdir()
    for frame in sorted((root / "input" / "frames").glob("*.png")):
        shutil.move(str(frame), str(source_rgb / frame.name))
    (root / "input" / "frames").rmdir()
    (root / "input" / "sequence_manifest.json").write_text(
        json.dumps({"sequence_id": "demo", "rgb_dir": str(source_rgb)})
    )

    result = evaluate_run_from_artifact_root(root, config=RenderEvalConfig(save_gallery=False))

    assert not (root / "input" / "frames").exists()  # canonical layout is gone
    assert result.scored_pairs == 2  # manifest-backed rgb_dir still scores


def test_zero_coverage_poses_are_skipped(tmp_path: Path) -> None:
    root = tmp_path / "run"
    _build_synthetic_run(root)
    # Replace the trajectory: two poses see the cloud (z=2), one sits past it looking away.
    identity = FrameTransform.from_matrix(np.eye(4), target_frame="world", source_frame="camera_rdf")
    away = np.eye(4)
    away[2, 3] = 10.0  # camera at z=10 looking +z -> the z=2 cloud is behind it
    looking_away = FrameTransform.from_matrix(away, target_frame="world", source_frame="camera_rdf")
    write_tum_trajectory(root / "slam" / "trajectory.tum", [identity, identity, looking_away], [0.0, 0.2, 0.4])

    result = evaluate_run_from_artifact_root(root, config=RenderEvalConfig(save_gallery=False))
    assert result.scored_pairs == 2  # the looking-away pose contributed no covered pixels and was skipped


def test_no_gallery_skips_image_output(tmp_path: Path) -> None:
    root = tmp_path / "run"
    _build_synthetic_run(root)
    result = evaluate_run_from_artifact_root(root, config=RenderEvalConfig(save_gallery=False))
    assert result.gallery_dir is None
    assert not (root / "evaluation" / "render_eval").exists()
    assert result.metrics_path.exists()


def test_missing_cloud_raises(tmp_path: Path) -> None:
    root = tmp_path / "empty"
    (root / "input").mkdir(parents=True)
    with pytest.raises(FileNotFoundError, match="No dense cloud"):
        evaluate_run_from_artifact_root(root)


def test_image_evaluation_stage_runtime(tmp_path: Path) -> None:
    from prml_vslam.eval.render_eval import RenderEvalConfig
    from prml_vslam.eval.stage_image.contracts import ImageEvaluationStageInput
    from prml_vslam.eval.stage_image.runtime import ImageEvaluationRuntime
    from prml_vslam.interfaces.artifacts import artifact_ref
    from prml_vslam.interfaces.slam import SlamArtifacts
    from prml_vslam.pipeline.contracts.provenance import StageStatus
    from prml_vslam.pipeline.contracts.stages import StageKey

    root = tmp_path / "run"
    _build_synthetic_run(root)
    slam = SlamArtifacts(
        trajectory_tum=artifact_ref(root / "slam" / "trajectory.tum", kind="tum"),
        dense_points_ply=artifact_ref(root / "slam" / "point_cloud.ply", kind="ply"),
        num_processed_frames=5,
        num_keyframes=2,
        num_sparse_points=0,
        num_dense_points=3600,
    )

    runtime = ImageEvaluationRuntime()
    result = runtime.run_offline(
        ImageEvaluationStageInput(
            artifact_root=root,
            render_config=RenderEvalConfig(save_gallery=False),
            slam=slam,
        )
    )

    assert result.stage_key is StageKey.IMAGE_EVALUATION
    assert result.outcome.status is StageStatus.COMPLETED
    assert "image_metrics" in result.outcome.artifacts
    assert result.outcome.metrics["image.psnr.mean"] is not None
    assert result.outcome.metrics["scored_pairs"] == 2
    assert (root / "evaluation" / "image_metrics.json").exists()
    assert runtime.status().lifecycle_state is StageStatus.COMPLETED


def test_image_evaluation_stage_registered_and_planned(tmp_path: Path) -> None:
    from prml_vslam.pipeline.config import build_run_config
    from prml_vslam.pipeline.contracts.stages import StageKey
    from prml_vslam.pipeline.stages.specs import stage_runtime_spec_for
    from prml_vslam.sources.config import VideoSourceConfig

    # Spec is registered in the global registry.
    assert stage_runtime_spec_for(StageKey.IMAGE_EVALUATION).stage_key is StageKey.IMAGE_EVALUATION

    # Enabling it via build_run_config wires the section and it plans as an available stage.
    from prml_vslam.methods.stage.backend_config import MethodId

    config = build_run_config(
        experiment_name="image-eval",
        output_dir=tmp_path,
        source_backend=VideoSourceConfig(video_path=Path("captures/demo.mp4")),
        method=MethodId.VISTA,
        evaluate_image=True,
    )
    assert config.stages.evaluate_image.enabled is True
    plan = config.compile_plan()
    image_stage = next(stage for stage in plan.stages if stage.key is StageKey.IMAGE_EVALUATION)
    assert image_stage.available is True
    assert any("image_metrics.json" in str(output) for output in image_stage.outputs)
