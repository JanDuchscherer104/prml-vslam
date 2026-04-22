"""Tests for target pipeline config and stage-section planning contracts."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from prml_vslam.datasets.advio import AdvioServingConfig
from prml_vslam.datasets.contracts import DatasetId
from prml_vslam.interfaces import Record3DTransportId
from prml_vslam.methods import MethodId
from prml_vslam.pipeline.config import (
    RunConfig,
    TargetStageKey,
    current_stage_key_for_section,
    current_stage_key_for_target,
    section_for_current_stage,
    section_for_target_stage,
    target_stage_key_for_current,
    target_stage_key_for_section,
)
from prml_vslam.pipeline.contracts.request import (
    DatasetSourceSpec,
    PlacementPolicy,
    RunRequest,
    StagePlacement,
    VideoSourceSpec,
    build_run_request,
)
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.config import (
    PlacementConstraint,
    ResourceSpec,
    StageCleanupPolicy,
    StageConfig,
    StageExecutionConfig,
    StageTelemetryConfig,
)
from prml_vslam.pipeline.stages.source.config import (
    AdvioSourceConfig,
    Record3DSourceConfig,
    SourceStageConfig,
    TumRgbdSourceConfig,
    VideoSourceConfig,
    source_stage_config_from_source_spec,
)
from prml_vslam.utils import PathConfig


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_stage_config_contracts_round_trip_without_runtime_factory() -> None:
    config = StageConfig(
        stage_key=StageKey.SLAM,
        execution=StageExecutionConfig(
            resources=ResourceSpec(
                num_cpus=2.0,
                num_gpus=1.0,
                memory_bytes=1024,
                custom_resources={"accelerator": 1.0},
            ),
            placement=PlacementConstraint(
                node_ip_address="127.0.0.1",
                node_labels={"zone": "local"},
                affinity="same-node",
            ),
            runtime_env={"profile": "smoke"},
        ),
        telemetry=StageTelemetryConfig(
            emit_queue_metrics=True,
            emit_latency_metrics=True,
            emit_throughput_metrics=True,
            sampling_interval_ms=250,
        ),
        cleanup=StageCleanupPolicy(
            artifact_keys=["native_output_dir", "extra:*"],
            on_completed=True,
            on_failed=False,
            on_stopped=False,
        ),
    )

    reloaded = StageConfig.from_toml(config.to_toml())

    assert reloaded == config
    assert config.model_dump_jsonable()["cleanup"]["artifact_keys"] == ["native_output_dir", "extra:*"]
    assert not hasattr(config, "setup_target")
    assert not hasattr(config.execution, "setup_target")


def test_stage_cleanup_policy_rejects_filesystem_like_selectors() -> None:
    StageCleanupPolicy(artifact_keys=["viewer_rrd", "visualization:*"])

    for selector in ["../native", "native/output", "*.rrd", "extra:**", "visualization:rrd"]:
        with pytest.raises(ValidationError):
            StageCleanupPolicy(artifact_keys=[selector])


def test_resource_spec_rejects_negative_values() -> None:
    with pytest.raises(ValidationError):
        ResourceSpec(num_cpus=-1.0)

    with pytest.raises(ValidationError):
        ResourceSpec(custom_resources={"custom": -1.0})


def test_stage_key_section_alias_mapping_covers_current_and_target_names() -> None:
    expected = {
        StageKey.INGEST: (TargetStageKey.SOURCE, "source"),
        StageKey.SLAM: (TargetStageKey.SLAM, "slam"),
        StageKey.GRAVITY_ALIGNMENT: (TargetStageKey.ALIGN_GROUND, "align_ground"),
        StageKey.TRAJECTORY_EVALUATION: (
            TargetStageKey.EVALUATE_TRAJECTORY,
            "evaluate_trajectory",
        ),
        StageKey.REFERENCE_RECONSTRUCTION: (TargetStageKey.RECONSTRUCTION, "reconstruction"),
        StageKey.CLOUD_EVALUATION: (TargetStageKey.EVALUATE_CLOUD, "evaluate_cloud"),
        StageKey.EFFICIENCY_EVALUATION: (TargetStageKey.EVALUATE_EFFICIENCY, "evaluate_efficiency"),
        StageKey.SUMMARY: (TargetStageKey.SUMMARY, "summary"),
    }

    for current_key, (target_key, section) in expected.items():
        assert target_stage_key_for_current(current_key) is target_key
        assert current_stage_key_for_target(target_key) is current_key
        assert section_for_current_stage(current_key) is section
        assert section_for_target_stage(target_key) is section
        assert target_stage_key_for_section(section) is target_key
        assert current_stage_key_for_section(section) is current_key


def test_run_config_round_trips_current_run_request_semantics(tmp_path: Path) -> None:
    request = build_run_request(
        experiment_name="round-trip",
        output_dir=tmp_path,
        source=VideoSourceSpec(video_path=Path("captures/demo.mp4")),
        method=MethodId.MOCK,
        reference_enabled=True,
        trajectory_eval_enabled=True,
        evaluate_cloud=True,
        evaluate_efficiency=True,
        ground_alignment_enabled=True,
    )

    config = RunConfig.from_run_request(request)
    restored = config.to_run_request()

    assert restored.model_dump(mode="json") == request.model_dump(mode="json")
    assert config.stages.align_ground.enabled is True
    assert config.stages.evaluate_trajectory.enabled is True
    assert config.stages.reconstruction.enabled is True
    assert config.stages.evaluate_cloud.enabled is True
    assert config.stages.evaluate_efficiency.enabled is True


def test_run_config_projects_placement_policy_through_stage_execution_config(tmp_path: Path) -> None:
    request = build_run_request(
        experiment_name="placement-round-trip",
        output_dir=tmp_path,
        source=VideoSourceSpec(video_path=Path("captures/demo.mp4")),
        method=MethodId.MOCK,
    ).model_copy(
        update={
            "placement": PlacementPolicy(
                by_stage={
                    StageKey.SLAM: StagePlacement(
                        resources={
                            "CPU": 2.0,
                            "GPU": 1.0,
                            "custom_accelerator": 3.0,
                        }
                    )
                }
            )
        }
    )

    config = RunConfig.from_run_request(request)
    restored = config.to_run_request()

    assert config.stages.slam.execution.resources.num_cpus == 2.0
    assert config.stages.slam.execution.resources.num_gpus == 1.0
    assert config.stages.slam.execution.resources.custom_resources == {"custom_accelerator": 3.0}
    assert restored.placement.by_stage[StageKey.SLAM].resources == {
        "CPU": 2.0,
        "GPU": 1.0,
        "custom_accelerator": 3.0,
    }


def test_vista_full_target_toml_parses_through_run_config_and_matches_launch_plan(tmp_path: Path) -> None:
    repo_root = _repo_root()
    config_path = repo_root / ".configs/pipelines/vista-full.toml"
    path_config = PathConfig(root=repo_root, artifacts_dir=tmp_path / ".artifacts")

    run_config = RunConfig.from_toml(config_path)
    launch_request = run_config.to_run_request()

    run_config_plan = run_config.compile_plan(path_config)
    launch_plan = launch_request.build(path_config)

    assert run_config.source is None
    assert run_config.slam is None
    assert isinstance(launch_request.source, DatasetSourceSpec)
    assert launch_request.source.dataset_id is DatasetId.TUM_RGBD
    assert launch_request.source.sequence_id == "freiburg1_room"
    assert launch_request.source.frame_stride == 5
    assert launch_request.source.dataset_serving is None
    assert [stage.key for stage in run_config_plan.stages] == [stage.key for stage in launch_plan.stages]
    assert run_config.stages.align_ground.enabled is True
    assert run_config.stages.reconstruction.enabled is True
    assert run_config.stages.evaluate_trajectory.enabled is False


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


def test_source_stage_config_keeps_serving_variant_owned() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        SourceStageConfig.model_validate(
            {
                "backend": {
                    "source_id": "tum_rgbd",
                    "sequence_id": "freiburg1_room",
                    "dataset_serving": {"pose_source": "ground_truth"},
                }
            }
        )

    advio = SourceStageConfig.model_validate({"backend": {"source_id": "advio", "sequence_id": "advio-20"}})

    assert isinstance(advio.backend, AdvioSourceConfig)
    assert advio.backend.dataset_serving.pose_source.value == "ground_truth"


def test_legacy_source_spec_projects_to_target_source_stage_config() -> None:
    advio_source = DatasetSourceSpec(
        dataset_id=DatasetId.ADVIO,
        sequence_id="advio-20",
        target_fps=10.0,
        dataset_serving=AdvioServingConfig(pose_frame_mode="reference_world"),
        respect_video_rotation=True,
    )
    tum_source = DatasetSourceSpec(
        dataset_id=DatasetId.TUM_RGBD,
        sequence_id="freiburg1_room",
        frame_stride=5,
    )

    advio_config = source_stage_config_from_source_spec(advio_source)
    tum_config = source_stage_config_from_source_spec(tum_source)

    assert isinstance(advio_config.backend, AdvioSourceConfig)
    assert advio_config.backend.target_fps == 10.0
    assert advio_config.backend.respect_video_rotation is True
    assert advio_config.backend.dataset_serving.pose_frame_mode.value == "reference_world"
    assert isinstance(tum_config.backend, TumRgbdSourceConfig)
    assert tum_config.backend.frame_stride == 5


def test_invalid_advio_source_does_not_parse_as_record3d() -> None:
    payload = {
        "experiment_name": "invalid-advio",
        "mode": "streaming",
        "output_dir": ".artifacts",
        "source": {
            "dataset_id": "advio",
            "sequence_id": "advio-20",
        },
        "slam": {"backend": {"method_id": "mock"}},
    }

    with pytest.raises(ValidationError, match="ADVIO dataset sources must provide `dataset_serving`"):
        RunRequest.model_validate(payload)


def test_target_generic_stages_toml_parses_into_stage_bundle() -> None:
    config = RunConfig.from_toml(
        """
experiment_name = "target-shape"
mode = "offline"
output_dir = ".artifacts"

[stages.source]
enabled = true

[stages.slam.execution.resources]
num_cpus = 2.0

[stages.align_ground]
enabled = true

[stages.reconstruction.cleanup]
artifact_keys = ["reference_cloud", "extra:*"]
on_completed = true
on_failed = false
on_stopped = false

[stages.summary]
enabled = true
""".strip()
    )

    assert config.stages.source.stage_key is StageKey.INGEST
    assert config.stages.slam.execution.resources.num_cpus == 2.0
    assert config.stages.align_ground.enabled is True
    assert config.stages.reconstruction.cleanup.artifact_keys == ["reference_cloud", "extra:*"]
    assert config.source is None
    assert config.slam is None


def test_run_config_fail_on_unavailable_stages_happens_during_planning(tmp_path: Path) -> None:
    request = build_run_request(
        experiment_name="unavailable",
        output_dir=tmp_path,
        source=VideoSourceSpec(video_path=Path("captures/demo.mp4")),
        method=MethodId.MAST3R,
    )
    config = RunConfig.from_run_request(request)

    with pytest.raises(ValueError, match="MASt3R-SLAM does not support offline execution"):
        config.compile_plan(
            PathConfig(root=_repo_root(), artifacts_dir=tmp_path / ".artifacts"), fail_on_unavailable=True
        )


def test_run_config_rejects_disabled_required_stage_for_current_request_projection(tmp_path: Path) -> None:
    request = build_run_request(
        experiment_name="disabled-source",
        output_dir=tmp_path,
        source=VideoSourceSpec(video_path=Path("captures/demo.mp4")),
        method=MethodId.MOCK,
    )
    config = RunConfig.from_run_request(request)
    disabled_stages = config.stages.model_copy(update={"source": StageConfig(stage_key=StageKey.INGEST, enabled=False)})
    disabled = config.model_copy(update={"stages": disabled_stages})

    with pytest.raises(ValueError, match="source"):
        disabled.to_run_request()
