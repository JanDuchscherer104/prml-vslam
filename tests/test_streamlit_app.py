"""Tests for the metrics-first Streamlit app."""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

from prml_vslam.app import build_advio_asset_figure, build_advio_timeline_figure
from prml_vslam.datasets import AdvioSequenceConfig, summarize_advio_sequence
from prml_vslam.eval import PoseRelationId, TrajectoryEvaluationResult, write_evaluation_result
from prml_vslam.pipeline.contracts import MethodId, PipelineMode


def _write_advio_sequence(root: Path, *, sequence_id: int = 15, include_ground_truth_tum: bool = True) -> Path:
    sequence_dir = root / f"advio-{sequence_id:02d}"
    (sequence_dir / "iphone").mkdir(parents=True, exist_ok=True)
    (sequence_dir / "pixel").mkdir(parents=True, exist_ok=True)
    (sequence_dir / "ground-truth").mkdir(parents=True, exist_ok=True)
    (sequence_dir / "tango").mkdir(parents=True, exist_ok=True)
    (root / "calibration").mkdir(parents=True, exist_ok=True)

    (sequence_dir / "iphone" / "frames.mov").write_bytes(b"fake-mov")
    (sequence_dir / "iphone" / "frames.csv").write_text("0.0,1\n0.1,2\n0.2,3\n", encoding="utf-8")
    (sequence_dir / "iphone" / "accelerometer.csv").write_text("0.0,0,0,0\n0.1,1,1,1\n", encoding="utf-8")
    (sequence_dir / "iphone" / "gyro.csv").write_text("0.0,0,0,0\n0.1,1,1,1\n", encoding="utf-8")
    (sequence_dir / "iphone" / "arkit.csv").write_text("0.0,0,0,0,1,0,0,0\n0.1,0,0,0,1,0,0,0\n", encoding="utf-8")
    (sequence_dir / "pixel" / "arcore.csv").write_text("0.0,0,0,0,1,0,0,0\n0.2,0,0,0,1,0,0,0\n", encoding="utf-8")
    (sequence_dir / "ground-truth" / "pose.csv").write_text("0.0,0,0,0,1,0,0,0\n0.2,1,0,0,1,0,0,0\n", encoding="utf-8")
    if include_ground_truth_tum:
        (sequence_dir / "ground-truth" / "ground_truth.tum").write_text(
            "# timestamp tx ty tz qx qy qz qw\n0.0 0 0 0 0 0 0 1\n0.2 1 0 0 0 0 0 1\n",
            encoding="utf-8",
        )
    (sequence_dir / "tango" / "frames.mov").write_bytes(b"fake-tango-mov")
    (sequence_dir / "tango" / "frames.csv").write_text("0.0,1\n0.2,2\n0.4,3\n", encoding="utf-8")
    (sequence_dir / "tango" / "area-learning.csv").write_text(
        "0.0,0,0,0,1,0,0,0\n0.4,0,0,0,1,0,0,0\n", encoding="utf-8"
    )
    (sequence_dir / "tango" / "point-cloud-00001.csv").write_text("0,0,0\n1,1,1\n", encoding="utf-8")
    (root / "calibration" / "iphone-03.yaml").write_text("camera: {}\n", encoding="utf-8")
    return sequence_dir


def _write_run(artifacts_root: Path, *, sequence_id: int = 15, method: MethodId = MethodId.VISTA_SLAM) -> Path:
    artifact_root = artifacts_root / f"advio-{sequence_id:02d}" / PipelineMode.BATCH.value / method.value
    (artifact_root / "slam").mkdir(parents=True, exist_ok=True)
    (artifact_root / "evaluation").mkdir(parents=True, exist_ok=True)
    (artifact_root / "slam" / "trajectory.tum").write_text(
        "# timestamp tx ty tz qx qy qz qw\n0.0 0 0 0 0 0 0 1\n0.2 0.9 0 0 0 0 0 1\n",
        encoding="utf-8",
    )
    (artifact_root / "slam" / "trajectory.metadata.json").write_text(
        (
            "{\n"
            '  "artifact_path": "slam/trajectory.tum",\n'
            '  "format": "tum",\n'
            '  "frame_name": "world",\n'
            '  "transform_convention": "T_world_camera"\n'
            "}\n"
        ),
        encoding="utf-8",
    )
    return artifact_root


def _find_button(at: AppTest, label: str):
    for widget in at.button:
        if widget.label == label:
            return widget
    raise AssertionError(f"Could not find button with label {label!r}")


def test_metrics_app_renders_persisted_advio_evaluation(monkeypatch, tmp_path: Path) -> None:
    dataset_root = tmp_path / "data" / "advio"
    artifacts_root = tmp_path / "artifacts"
    _write_advio_sequence(dataset_root)
    artifact_root = _write_run(artifacts_root)

    evaluation_result = TrajectoryEvaluationResult(
        reference_path=dataset_root / "advio-15" / "ground-truth" / "ground_truth.tum",
        estimate_path=artifact_root / "slam" / "trajectory.tum",
        pose_relation=PoseRelationId.TRANSLATION_PART,
        align=True,
        correct_scale=True,
        max_diff_s=0.02,
        matching_pairs=2,
        stats={"rmse": 0.1, "mean": 0.08, "median": 0.08, "std": 0.02},
    )
    write_evaluation_result(
        evaluation_result,
        artifact_root / "evaluation" / "trajectory_eval__translation_part__align__scale__diff-0p02.json",
    )

    monkeypatch.setenv("PRML_VSLAM_ADVIO_ROOT", str(dataset_root))
    monkeypatch.setenv("PRML_VSLAM_ARTIFACTS_ROOT", str(artifacts_root))

    at = AppTest.from_file("streamlit_app.py")
    at.run()

    assert any("Trajectory Metrics" in markdown.value for markdown in at.markdown)
    assert any(button.label == "Compute evo metrics" for button in at.button)
    assert any(metric.label == "RMSE" for metric in at.metric)
    assert any(metric.label == "Pairs" for metric in at.metric)


def test_metrics_app_explicitly_computes_and_persists_evaluation(monkeypatch, tmp_path: Path) -> None:
    dataset_root = tmp_path / "data" / "advio"
    artifacts_root = tmp_path / "artifacts"
    _write_advio_sequence(dataset_root, include_ground_truth_tum=False)
    artifact_root = _write_run(artifacts_root)

    def _fake_evaluate(config):
        return TrajectoryEvaluationResult(
            reference_path=config.reference_path,
            estimate_path=config.estimate_path,
            pose_relation=config.pose_relation,
            align=config.align,
            correct_scale=config.correct_scale,
            max_diff_s=config.max_diff_s,
            matching_pairs=2,
            stats={"rmse": 0.12, "mean": 0.09, "median": 0.09, "std": 0.03},
        )

    monkeypatch.setenv("PRML_VSLAM_ADVIO_ROOT", str(dataset_root))
    monkeypatch.setenv("PRML_VSLAM_ARTIFACTS_ROOT", str(artifacts_root))
    monkeypatch.setattr("prml_vslam.app.services.evaluate_tum_trajectories", _fake_evaluate)

    at = AppTest.from_file("streamlit_app.py")
    at.run()
    _find_button(at, "Compute evo metrics").click().run()

    output_files = sorted((artifact_root / "evaluation").glob("trajectory_eval__*.json"))
    assert output_files
    assert any("Saved evaluation to" in success.value for success in at.success)


def test_streamlit_dataset_figures_summarize_advio_modalities(tmp_path: Path) -> None:
    dataset_root = tmp_path / "data" / "advio"
    _write_advio_sequence(dataset_root)
    summary = summarize_advio_sequence(AdvioSequenceConfig(dataset_root=dataset_root, sequence_id=15))

    timeline = build_advio_timeline_figure(summary)
    assets = build_advio_asset_figure(summary)

    assert len(timeline.data) == summary.timed_modality_count
    assert assets.data[0].type == "treemap"


def test_streamlit_dataset_page_renders_for_local_advio_sequence(monkeypatch, tmp_path: Path) -> None:
    dataset_root = tmp_path / "data" / "advio"
    _write_advio_sequence(dataset_root)

    monkeypatch.setenv("PRML_VSLAM_ADVIO_ROOT", str(dataset_root))

    at = AppTest.from_string("from prml_vslam.app import run_dataset_page\nrun_dataset_page()\n")
    at.run()

    assert any("ADVIO Dataset Explorer" in markdown.value for markdown in at.markdown)
    assert any(metric.label == "Timed streams" for metric in at.metric)
    assert any("Temporal coverage" in markdown.value for markdown in at.markdown)


def test_streamlit_record3d_page_renders_streaming_surface() -> None:
    at = AppTest.from_string("from prml_vslam.app import run_record3d_page\nrun_record3d_page()\n")
    at.run()

    assert any("Record3D Streaming" in markdown.value for markdown in at.markdown)
    assert any("Connection summary" in markdown.value for markdown in at.markdown)
    assert any("USB status" in markdown.value for markdown in at.markdown)
