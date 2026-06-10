"""Tests for target pipeline config and stage-section planning contracts."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
from pydantic import ValidationError

from prml_vslam.methods.stage.backend_config import MethodId
from prml_vslam.pipeline.config import (
    STAGE_SECTION_ORDER,
    RunConfig,
    build_run_config,
)
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.reuse import load_reused_stage_results
from prml_vslam.pipeline.stages.base.config import StageConfig
from prml_vslam.sources.config import (
    AdvioSourceConfig,
    Record3DSourceConfig,
    TumRgbdSourceConfig,
    VideoSourceConfig,
)
from prml_vslam.sources.contracts import PreparedBenchmarkInputs, Record3DTransportId, SequenceManifest
from prml_vslam.sources.datasets.advio import AdvioServingConfig
from prml_vslam.sources.datasets.contracts import DatasetId
from prml_vslam.sources.replay import ReplayMode
from prml_vslam.sources.stage.config import SourceStageConfig
from prml_vslam.utils import PathConfig, RunArtifactPaths
from prml_vslam.utils.serialization import write_json


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_stage_config_sections_round_trip_without_runtime_factory() -> None:
    config = StageConfig(
        stage_key=StageKey.SLAM,
        num_cpus=2.0,
        num_gpus=1.0,
        memory_bytes=1024,
        custom_resources={"accelerator": 1.0},
        node_ip_address="127.0.0.1",
        node_labels={"zone": "local"},
        affinity="same-node",
        runtime_env={"profile": "smoke"},
        emit_queue_metrics=True,
        emit_latency_metrics=True,
        emit_throughput_metrics=True,
        sampling_interval_ms=250,
        cleanup_artifact_keys=["native_output_dir", "extra:*"],
        cleanup_on_completed=True,
        cleanup_on_failed=False,
        cleanup_on_stopped=False,
    )

    reloaded = StageConfig.from_toml(config.to_toml())

    assert reloaded == config
    assert config.model_dump_jsonable()["cleanup_artifact_keys"] == ["native_output_dir", "extra:*"]
    assert not hasattr(config, "setup_target")
    assert not hasattr(config, "runtime_factory")
    assert not hasattr(config, "build_offline_input")
    assert not hasattr(config, "build_streaming_start_input")


def test_stage_config_rejects_filesystem_like_cleanup_selectors() -> None:
    StageConfig(cleanup_artifact_keys=["viewer_rrd", "visualization:*"])

    for selector in ["../native", "native/output", "*.rrd", "extra:**", "visualization:rrd"]:
        with pytest.raises(ValidationError):
            StageConfig(cleanup_artifact_keys=[selector])


def test_stage_config_rejects_negative_resource_values() -> None:
    with pytest.raises(ValidationError):
        StageConfig(num_cpus=-1.0)

    with pytest.raises(ValidationError):
        StageConfig(custom_resources={"custom": -1.0})


def test_stage_key_vocabulary_and_static_section_bindings_are_target_only() -> None:
    assert [key.value for key in StageKey] == [
        "source",
        "slam",
        "gravity.align",
        "align.trajectory",
        "evaluate.trajectory",
        "align.cloud",
        "evaluate.cloud",
        "reconstruction",
        "summary",
    ]
    assert list(STAGE_SECTION_ORDER) == [
        (StageKey.SOURCE, "source"),
        (StageKey.SLAM, "slam"),
        (StageKey.GRAVITY_ALIGNMENT, "align_ground"),
        (StageKey.TRAJECTORY_ALIGNMENT, "align_trajectory"),
        (StageKey.TRAJECTORY_EVALUATION, "evaluate_trajectory"),
        (StageKey.CLOUD_ALIGNMENT, "align_cloud"),
        (StageKey.RECONSTRUCTION, "reconstruction"),
        (StageKey.CLOUD_EVALUATION, "evaluate_cloud"),
        (StageKey.SUMMARY, "summary"),
    ]


def test_build_run_config_populates_target_stage_sections(tmp_path: Path) -> None:
    config = build_run_config(
        experiment_name="target-config",
        output_dir=tmp_path,
        source_backend=VideoSourceConfig(video_path=Path("captures/demo.mp4")),
        method=MethodId.VISTA,
        reference_enabled=True,
        trajectory_eval_enabled=True,
        trajectory_alignment_enabled=True,
        cloud_alignment_enabled=True,
        evaluate_cloud=True,
        ground_alignment_enabled=True,
    )

    assert isinstance(config.stages.source.backend, VideoSourceConfig)
    assert config.stages.slam.backend.method_id is MethodId.VISTA
    assert config.stages.align_ground.enabled is True
    assert config.stages.align_trajectory.enabled is True
    assert config.stages.evaluate_trajectory.enabled is True
    assert config.stages.reconstruction.enabled is True
    assert config.stages.align_cloud.enabled is True
    assert config.stages.evaluate_cloud.enabled is True


def test_trajectory_alignment_plan_declares_materialized_outputs(tmp_path: Path) -> None:
    path_config = PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts")
    config = build_run_config(
        experiment_name="alignment-outputs",
        output_dir=path_config.artifacts_dir,
        source_backend=VideoSourceConfig(video_path=Path("captures/demo.mp4")),
        method=MethodId.VISTA,
        trajectory_alignment_enabled=True,
    )

    plan = config.compile_plan(path_config)
    stage = next(stage for stage in plan.stages if stage.key is StageKey.TRAJECTORY_ALIGNMENT)

    assert [path.relative_to(plan.artifact_root).as_posix() for path in stage.outputs] == [
        "evaluation/trajectory_alignment.json",
        "evaluation/trajectory_sim3_aligned.tum",
        "evaluation/point_cloud_sim3_aligned.ply",
    ]


def test_cloud_alignment_plan_declares_materialized_outputs(tmp_path: Path) -> None:
    path_config = PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts")
    config = build_run_config(
        experiment_name="cloud-alignment-outputs",
        output_dir=path_config.artifacts_dir,
        source_backend=VideoSourceConfig(video_path=Path("captures/demo.mp4")),
        method=MethodId.VISTA,
        trajectory_alignment_enabled=True,
        cloud_alignment_enabled=True,
    )

    plan = config.compile_plan(path_config)
    stage = next(stage for stage in plan.stages if stage.key is StageKey.CLOUD_ALIGNMENT)

    assert [path.relative_to(plan.artifact_root).as_posix() for path in stage.outputs] == [
        "evaluation/cloud_alignment.json",
        "evaluation/point_cloud_sim3_icp_aligned.ply",
    ]


def test_tum_rgbd_cloud_alignment_plan_does_not_require_local_ci_data(tmp_path: Path) -> None:
    path_config = PathConfig(
        root=_repo_root(),
        artifacts_dir=tmp_path / ".artifacts",
        data_dir=tmp_path / ".data",
    )
    config = build_run_config(
        experiment_name="tum-rgbd-cloud-alignment",
        output_dir=path_config.artifacts_dir,
        source_backend=TumRgbdSourceConfig(sequence_id="freiburg1_desk"),
        method=MethodId.VISTA,
        trajectory_alignment_enabled=True,
        cloud_alignment_enabled=True,
        reference_enabled=False,
    )

    with pytest.raises(
        ValueError,
        match=(
            "Enabled stage\\(s\\) are unavailable: align\\.cloud: "
            "Cloud alignment requires a source-prepared reference cloud or reference reconstruction\\."
        ),
    ):
        config.compile_plan(path_config, fail_on_unavailable=True)


def test_tum_rgbd_cloud_alignment_plan_requires_depth_without_reconstruction(tmp_path: Path) -> None:
    data_dir = tmp_path / ".data"
    sequence_dir = data_dir / "tum_rgbd" / "rgbd_dataset_freiburg1_desk"
    (sequence_dir / "rgb").mkdir(parents=True)
    (sequence_dir / "rgb.txt").write_text("0.000000 rgb/0.000000.png\n", encoding="utf-8")
    (sequence_dir / "groundtruth.txt").write_text(
        "0.000000 0.0 0.0 0.0 0.0 0.0 0.0 1.0\n",
        encoding="utf-8",
    )
    path_config = PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts", data_dir=data_dir)
    config = build_run_config(
        experiment_name="tum-rgbd-cloud-alignment-missing-depth",
        output_dir=path_config.artifacts_dir,
        source_backend=TumRgbdSourceConfig(sequence_id="freiburg1_desk"),
        method=MethodId.VISTA,
        trajectory_alignment_enabled=True,
        cloud_alignment_enabled=True,
        reference_enabled=False,
    )

    plan = config.compile_plan(path_config)
    stage = next(stage for stage in plan.stages if stage.key is StageKey.CLOUD_ALIGNMENT)

    assert stage.available is False
    assert (
        stage.availability_reason
        == "Cloud alignment requires a source-prepared reference cloud or reference reconstruction."
    )


def test_run_config_uses_stage_config_for_resource_policy(tmp_path: Path) -> None:
    config = build_run_config(
        experiment_name="placement-policy",
        output_dir=tmp_path,
        source_backend=VideoSourceConfig(video_path=Path("captures/demo.mp4")),
        method=MethodId.VISTA,
    )
    stages = config.stages.model_copy(
        update={
            "slam": config.stages.slam.model_copy(
                update={
                    "num_cpus": 2.0,
                    "num_gpus": 1.0,
                    "custom_resources": {"custom_accelerator": 3.0},
                }
            )
        }
    )
    config = config.model_copy(update={"stages": stages})

    assert config.stages.slam.num_cpus == 2.0
    assert config.stages.slam.num_gpus == 1.0
    assert config.stages.slam.custom_resources == {"custom_accelerator": 3.0}


def test_vista_full_target_toml_parses_through_run_config(tmp_path: Path) -> None:
    repo_root = _repo_root()
    config_path = repo_root / ".configs/pipelines/vista-full.toml"
    path_config = PathConfig(root=repo_root, artifacts_dir=tmp_path / ".artifacts")

    run_config = RunConfig.from_toml(config_path)

    run_config_plan = run_config.compile_plan(path_config)

    assert isinstance(run_config.stages.source.backend, TumRgbdSourceConfig)
    assert run_config.stages.source.backend.sequence_id == "freiburg3_large_cabinet"
    assert run_config.stages.source.backend.frame_stride == 3
    assert run_config.stages.source.backend.replay_mode is ReplayMode.FAST_AS_POSSIBLE
    assert run_config_plan.source.source_id == DatasetId.TUM_RGBD.value
    assert run_config_plan.source.sequence_id == "freiburg3_large_cabinet"
    assert run_config_plan.source.replay_mode == "fast_as_possible"
    assert run_config_plan.source.metadata["dataset_id"] == DatasetId.TUM_RGBD.value
    assert run_config.stages.align_ground.enabled is True
    assert run_config.stages.reconstruction.enabled is True
    assert run_config.stages.reconstruction.backend.extract_mesh is True
    assert run_config.stages.evaluate_trajectory.enabled is True
    assert run_config.visualization.point_cloud_decimation_keep_ratio == 0.25
    assert run_config.visualization.mesh_decimation_keep_ratio == 0.25
    assert run_config.visualization.decimation_random_seed == 0


def test_run_plan_expected_fps_uses_advio_frame_stride_metadata(tmp_path: Path) -> None:
    native_fps = 60.04133960359873
    frames_path = tmp_path / ".data" / "advio" / "advio-20" / "iphone" / "frames.csv"
    frames_path.parent.mkdir(parents=True)
    frames_path.write_text(
        "\n".join(f"{frame_index / native_fps:.9f},{frame_index}" for frame_index in range(10)) + "\n",
        encoding="utf-8",
    )
    path_config = PathConfig(
        root=_repo_root(),
        artifacts_dir=tmp_path / ".artifacts",
        data_dir=tmp_path / ".data",
    )
    run_config = build_run_config(
        experiment_name="advio-fps",
        output_dir=path_config.artifacts_dir,
        source_backend=AdvioSourceConfig(sequence_id="advio-20", frame_stride=5),
        method=MethodId.VISTA,
    )

    plan = run_config.compile_plan(path_config)

    assert plan.source.expected_fps == pytest.approx(native_fps / 5)
    assert plan.model_dump(mode="json")["source"]["expected_fps"] == pytest.approx(native_fps / 5)


def test_run_plan_expected_fps_uses_target_fps_without_native_metadata(tmp_path: Path) -> None:
    path_config = PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts")
    run_config = build_run_config(
        experiment_name="target-fps",
        output_dir=path_config.artifacts_dir,
        source_backend=Record3DSourceConfig(target_fps=15.0),
        method=MethodId.VISTA,
    )

    plan = run_config.compile_plan(path_config)

    assert plan.source.expected_fps == 15.0


def test_run_plan_expected_fps_is_none_when_native_cadence_unknown(tmp_path: Path) -> None:
    path_config = PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts")
    run_config = build_run_config(
        experiment_name="unknown-fps",
        output_dir=path_config.artifacts_dir,
        source_backend=VideoSourceConfig(video_path=Path("missing.mp4"), frame_stride=2),
        method=MethodId.VISTA,
    )

    plan = run_config.compile_plan(path_config)

    assert plan.source.expected_fps is None


def test_source_stage_config_parses_discriminated_backend_variants() -> None:
    video = SourceStageConfig.model_validate(
        {"backend": {"source_id": "video", "video_path": "captures/demo.mp4", "frame_stride": 2}}
    )
    tum = SourceStageConfig.model_validate(
        {
            "backend": {
                "source_id": "tum_rgbd",
                "sequence_id": "freiburg1_room",
                "target_fps": 15.0,
                "replay_mode": "fast_as_possible",
            }
        }
    )
    advio = SourceStageConfig.model_validate(
        {
            "backend": {
                "source_id": "advio",
                "sequence_id": "advio-20",
                "dataset_serving": {
                    "pose_source": "ground_truth",
                    "pose_frame_mode": "provider_world",
                },
            }
        }
    )
    record3d = SourceStageConfig.model_validate(
        {
            "backend": {
                "source_id": "record3d",
                "transport": "usb",
                "device_index": 0,
                "frame_stride": 3,
            }
        }
    )

    assert isinstance(video.backend, VideoSourceConfig)
    assert isinstance(tum.backend, TumRgbdSourceConfig)
    assert tum.backend.replay_mode is ReplayMode.FAST_AS_POSSIBLE
    assert isinstance(advio.backend, AdvioSourceConfig)
    assert isinstance(advio.backend.dataset_serving, AdvioServingConfig)
    assert advio.backend.replay_mode is ReplayMode.REALTIME
    assert advio.backend.normalize_video_orientation is True
    assert isinstance(record3d.backend, Record3DSourceConfig)
    assert record3d.backend.transport is Record3DTransportId.USB


def test_source_stage_config_sampling_policy_is_shared() -> None:
    for backend in (
        {"source_id": "video", "video_path": "captures/demo.mp4"},
        {"source_id": "tum_rgbd", "sequence_id": "freiburg1_room"},
        {"source_id": "advio", "sequence_id": "advio-20"},
        {"source_id": "record3d"},
    ):
        with pytest.raises(ValidationError, match="Configure either `frame_stride` or `target_fps`"):
            SourceStageConfig.model_validate({"backend": {**backend, "frame_stride": 2, "target_fps": 15.0}})


def test_source_stage_config_ignores_unknown_variant_fields() -> None:
    tum = SourceStageConfig.model_validate(
        {
            "backend": {
                "source_id": "tum_rgbd",
                "sequence_id": "freiburg1_room",
                "dataset_serving": {"pose_source": "ground_truth"},
            }
        }
    )
    assert isinstance(tum.backend, TumRgbdSourceConfig)

    advio = SourceStageConfig.model_validate({"backend": {"source_id": "advio", "sequence_id": "advio-20"}})

    assert isinstance(advio.backend, AdvioSourceConfig)
    assert advio.backend.dataset_serving.pose_source.value == "ground_truth"


def test_run_config_warns_and_ignores_unknown_fields() -> None:
    with pytest.warns(UserWarning, match="Ignoring unknown config field `source`"):
        config = RunConfig.from_toml(
            """
experiment_name = "invalid-advio"
mode = "streaming"
output_dir = ".artifacts"

[source]
dataset_id = "advio"
sequence_id = "advio-20"

[stages.source.backend]
source_id = "video"
video_path = "captures/demo.mp4"
legacy = true

[stages.slam.backend]
method_id = "vista"
"""
        )
    assert "Ignoring unknown config field `stages.source.backend.legacy`." in config.config_warnings


def test_run_config_parses_reuse_artifact_root_and_rejects_same_root(tmp_path: Path) -> None:
    reuse_root = tmp_path / "old" / "vista"
    reuse_paths = RunArtifactPaths.build(reuse_root)
    write_json(reuse_paths.sequence_manifest_path, SequenceManifest(sequence_id="reused-seq"))
    write_json(reuse_paths.benchmark_inputs_path, PreparedBenchmarkInputs())
    reuse_paths.trajectory_path.parent.mkdir(parents=True, exist_ok=True)
    reuse_paths.trajectory_path.write_text("0 0 0 0 0 0 0 1\n", encoding="utf-8")
    config = RunConfig.from_toml(
        f"""
experiment_name = "reuse"
mode = "offline"
output_dir = "{tmp_path.as_posix()}"
reuse_artifact_root = "{reuse_root.as_posix()}"

[stages.source]
enabled = false

[stages.slam]
enabled = false

[stages.slam.backend]
method_id = "vista"

[stages.align_trajectory]
enabled = true

[stages.align_cloud]
enabled = true
"""
    )

    assert config.reuse_artifact_root == reuse_root
    plan = config.compile_plan(PathConfig(root=tmp_path))
    assert plan.source.source_id == "reused_artifacts"
    assert plan.source.sequence_id == "reused-seq"
    assert [stage.key for stage in plan.stages] == [
        StageKey.TRAJECTORY_ALIGNMENT,
        StageKey.CLOUD_ALIGNMENT,
        StageKey.SUMMARY,
    ]

    planned_root = (
        PathConfig(root=tmp_path)
        .plan_run_paths(
            experiment_name="same",
            method_slug="vista",
            output_dir=tmp_path,
        )
        .artifact_root
    )
    planned_root.mkdir(parents=True)
    same_root = build_run_config(
        experiment_name="same",
        output_dir=tmp_path,
        source_backend=VideoSourceConfig(video_path=Path("captures/demo.mp4")),
        method=MethodId.VISTA,
    ).model_copy(update={"reuse_artifact_root": planned_root})
    with pytest.raises(ValueError, match="must not equal"):
        same_root.compile_plan(PathConfig(root=tmp_path))


def test_load_reused_stage_results_reconstructs_source_and_slam_outputs(tmp_path: Path) -> None:
    run_paths = RunArtifactPaths.build(tmp_path / "old-run")
    write_json(run_paths.sequence_manifest_path, SequenceManifest(sequence_id="seq"))
    write_json(run_paths.benchmark_inputs_path, PreparedBenchmarkInputs())
    run_paths.trajectory_path.parent.mkdir(parents=True)
    run_paths.trajectory_path.write_text("0 0 0 0 0 0 0 1\n", encoding="utf-8")
    run_paths.dense_points_path.write_text("ply\n", encoding="utf-8")

    results = {result.stage_key: result for result in load_reused_stage_results(run_paths.artifact_root)}

    assert results[StageKey.SOURCE].outcome.artifacts["sequence_manifest"].path == run_paths.sequence_manifest_path
    assert results[StageKey.SLAM].outcome.artifacts["dense_points_ply"].path == run_paths.dense_points_path
    missing_paths = RunArtifactPaths.build(tmp_path / "missing-benchmark")
    write_json(missing_paths.sequence_manifest_path, SequenceManifest(sequence_id="seq"))
    with pytest.raises(FileNotFoundError, match="benchmark inputs"):
        load_reused_stage_results(missing_paths.artifact_root)


def test_target_generic_stages_toml_parses_into_stage_bundle() -> None:
    config = RunConfig.from_toml(
        """
experiment_name = "target-shape"
mode = "offline"
output_dir = ".artifacts"

[stages.source]
enabled = true

[stages.slam]
num_cpus = 2.0

[stages.align_ground]
enabled = true

[stages.reconstruction]
cleanup_artifact_keys = ["reference_cloud", "extra:*"]
cleanup_on_completed = true
cleanup_on_failed = false
cleanup_on_stopped = false

[stages.summary]
enabled = true
""".strip()
    )

    assert config.stages.source.stage_key is StageKey.SOURCE
    assert config.stages.slam.num_cpus == 2.0
    assert config.stages.align_ground.enabled is True
    assert config.stages.reconstruction.cleanup_artifact_keys == ["reference_cloud", "extra:*"]


def test_run_config_plans_mast3r_dense_output_without_sparse_default(tmp_path: Path) -> None:
    config = build_run_config(
        experiment_name="mast3r-dense",
        output_dir=tmp_path,
        source_backend=VideoSourceConfig(video_path=Path("captures/demo.mp4")),
        method=MethodId.MAST3R,
    )

    plan = config.compile_plan(
        PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts"), fail_on_unavailable=True
    )
    slam_stage = next(stage for stage in plan.stages if stage.key is StageKey.SLAM)

    assert config.stages.slam.outputs.emit_sparse_points is False
    assert slam_stage.available is True
    assert [path.name for path in slam_stage.outputs] == ["trajectory.tum", "dense_points.ply"]


def test_run_config_rejects_mast3r_sparse_output_during_planning(tmp_path: Path) -> None:
    config = build_run_config(
        experiment_name="mast3r-sparse",
        output_dir=tmp_path,
        source_backend=VideoSourceConfig(video_path=Path("captures/demo.mp4")),
        method=MethodId.MAST3R,
        emit_sparse_points=True,
    )

    with pytest.raises(ValueError, match="does not expose a separate sparse point-cloud artifact"):
        config.compile_plan(
            PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts"), fail_on_unavailable=True
        )


def test_mast3r_extra_declares_required_local_source_anchors() -> None:
    pyproject = tomllib.loads((_repo_root() / "pyproject.toml").read_text(encoding="utf-8"))
    mast3r_extra = set(pyproject["project"]["optional-dependencies"]["mast3r"])

    assert mast3r_extra == {
        "torch==2.5.1",
        "torchvision==0.20.1",
        "torchaudio==2.5.1",
        "xformers",
        "MAST3R-SLAM",
        "MAST3R",
        "in3d",
        "asmk",
        "curope; sys_platform == 'linux' and platform_machine == 'x86_64'",
        "imgui",
    }

    sources = pyproject["tool"]["uv"]["sources"]
    assert {"asmk", "curope", "imgui"}.issubset(sources)

    metadata = {entry["name"]: entry["requires-dist"] for entry in pyproject["tool"]["uv"]["dependency-metadata"]}
    assert "gradio" not in {requirement.split(";", 1)[0].split("[", 1)[0] for requirement in metadata["MAST3R"]}
    assert any(
        requirement.startswith("lietorch @ git+https://github.com/princeton-vl/lietorch.git@e7df865")
        for requirement in metadata["MAST3R-SLAM"]
    )
    assert any(
        requirement.startswith("pyrealsense2; sys_platform == 'linux'") for requirement in metadata["MAST3R-SLAM"]
    )


def test_run_config_requires_source_backend_during_planning(tmp_path: Path) -> None:
    config = RunConfig(
        experiment_name="missing-source",
        output_dir=tmp_path,
        stages={"slam": {"backend": {"method_id": "vista"}}},
    )

    with pytest.raises(ValueError, match=r"RunConfig planning requires `\[stages\.source\.backend\]`"):
        config.compile_plan(PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts"))
