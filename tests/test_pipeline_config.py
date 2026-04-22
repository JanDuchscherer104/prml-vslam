"""Tests for target pipeline config and stage-section planning contracts."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

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
        StageKey.GROUND_ALIGNMENT: (TargetStageKey.ALIGN_GROUND, "align_ground"),
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


def test_vista_full_legacy_toml_parses_through_run_config_and_matches_current_plan(tmp_path: Path) -> None:
    repo_root = _repo_root()
    config_path = repo_root / ".configs/pipelines/vista-full.toml"
    path_config = PathConfig(root=repo_root, artifacts_dir=tmp_path / ".artifacts")

    run_config = RunConfig.from_toml(config_path)
    legacy_request = RunRequest.from_toml(config_path)

    run_config_plan = run_config.compile_plan(path_config)
    legacy_plan = legacy_request.build(path_config)

    assert [stage.key for stage in run_config_plan.stages] == [stage.key for stage in legacy_plan.stages]
    assert run_config.stages.align_ground.enabled is True
    assert run_config.stages.reconstruction.enabled is True
    assert run_config.stages.evaluate_trajectory.enabled is False


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
