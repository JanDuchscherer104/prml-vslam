"""Tests for target pipeline config and stage-section planning contracts."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from prml_vslam.methods.stage.config import MethodId
from prml_vslam.pipeline.config import (
    STAGE_SECTION_ORDER,
    RunConfig,
    build_run_config,
)
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.config import StageConfig
from prml_vslam.sources.config import (
    AdvioSourceConfig,
    Record3DSourceConfig,
    SourceStageConfig,
    TumRgbdSourceConfig,
    VideoSourceConfig,
)
from prml_vslam.sources.contracts import Record3DTransportId
from prml_vslam.sources.datasets.advio import AdvioPoseFrameMode, AdvioPoseSource, AdvioServingConfig
from prml_vslam.sources.datasets.contracts import DatasetId
from prml_vslam.utils import PathConfig


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
        "evaluate.trajectory",
        "reconstruction",
        "evaluate.cloud",
        "summary",
    ]
    assert list(STAGE_SECTION_ORDER) == [
        (StageKey.SOURCE, "source"),
        (StageKey.SLAM, "slam"),
        (StageKey.GRAVITY_ALIGNMENT, "align_ground"),
        (StageKey.TRAJECTORY_EVALUATION, "evaluate_trajectory"),
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
        evaluate_cloud=True,
        ground_alignment_enabled=True,
    )

    assert isinstance(config.stages.source.backend, VideoSourceConfig)
    assert config.stages.slam.backend.method_id is MethodId.VISTA
    assert config.stages.align_ground.enabled is True
    assert config.stages.evaluate_trajectory.enabled is True
    assert config.stages.reconstruction.enabled is True
    assert config.stages.evaluate_cloud.enabled is True


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

    assert isinstance(run_config.stages.source.backend, AdvioSourceConfig)
    assert run_config.stages.source.backend.sequence_id == "advio-20"
    assert run_config.stages.source.backend.frame_stride == 5
    assert run_config.stages.source.backend.dataset_serving == AdvioServingConfig(
        pose_source=AdvioPoseSource.GROUND_TRUTH,
        pose_frame_mode=AdvioPoseFrameMode.PROVIDER_WORLD,
    )
    assert run_config_plan.source.source_id == DatasetId.ADVIO.value
    assert run_config_plan.source.sequence_id == "advio-20"
    assert run_config_plan.source.metadata["pose_source"] == "ground_truth"
    assert run_config.stages.align_ground.enabled is True
    assert run_config.stages.reconstruction.enabled is True
    assert run_config.stages.reconstruction.backend.extract_mesh is True
    assert run_config.stages.evaluate_trajectory.enabled is False


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
        {"backend": {"source_id": "tum_rgbd", "sequence_id": "freiburg1_room", "target_fps": 15.0}}
    )
    advio = SourceStageConfig.model_validate(
        {
            "backend": {
                "source_id": "advio",
                "sequence_id": "advio-20",
                "dataset_serving": {
                    "pose_source": "ground_truth",
                    "pose_frame_mode": "reference_world",
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
    assert isinstance(advio.backend, AdvioSourceConfig)
    assert isinstance(advio.backend.dataset_serving, AdvioServingConfig)
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


def test_run_config_fail_on_unavailable_stages_happens_during_planning(tmp_path: Path) -> None:
    config = build_run_config(
        experiment_name="unavailable",
        output_dir=tmp_path,
        source_backend=VideoSourceConfig(video_path=Path("captures/demo.mp4")),
        method=MethodId.MAST3R,
    )

    with pytest.raises(ValueError, match="MASt3R-SLAM does not support offline execution"):
        config.compile_plan(
            PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts"), fail_on_unavailable=True
        )


def test_run_config_requires_source_backend_during_planning(tmp_path: Path) -> None:
    config = RunConfig(
        experiment_name="missing-source",
        output_dir=tmp_path,
        stages={"slam": {"backend": {"method_id": "vista"}}},
    )

    with pytest.raises(ValueError, match=r"RunConfig planning requires `\[stages\.source\.backend\]`"):
        config.compile_plan(PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts"))
