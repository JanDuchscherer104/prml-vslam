from __future__ import annotations

import sys
import types
from pathlib import Path
from typing import Any

import numpy as np
import pytest

import prml_vslam.app.pages.pipeline_request_editor as pipeline_request_editor
import prml_vslam.methods.lingbot.adapter as lingbot_adapter
from prml_vslam.app.models import PipelineSourceId
from prml_vslam.app.pipeline_controls import PipelinePageAction, build_run_config_from_action
from prml_vslam.interfaces import CAMERA_RDF_FRAME, Observation, ObservationProvenance
from prml_vslam.methods.lingbot.adapter import (
    LingbotMapSlamBackend,
    _adapt_checkpoint_state_dict,
    _build_lingbot_artifacts,
    _images_to_tensor,
    _pose_camera_to_world_to_frame_transform,
    _resolve_keyframe_interval,
)
from prml_vslam.methods.stage.backend_config import (
    LingbotMapSlamBackendConfig,
    MethodId,
    SlamOutputPolicy,
    build_slam_backend_config,
)
from prml_vslam.methods.stage.config import SlamStageConfig
from prml_vslam.pipeline.config import build_run_config
from prml_vslam.pipeline.contracts.context import PipelinePlanContext
from prml_vslam.pipeline.contracts.mode import PipelineMode
from prml_vslam.pipeline.demo import load_run_config_toml
from prml_vslam.sources.config import TumRgbdSourceConfig
from prml_vslam.sources.contracts import ReferenceSource, SequenceManifest
from prml_vslam.sources.datasets.advio import AdvioPoseFrameMode, AdvioPoseSource
from prml_vslam.sources.record3d.record3d import Record3DTransportId
from prml_vslam.utils import PathConfig, RunArtifactPaths
from prml_vslam.utils.geometry import load_point_cloud_ply, load_tum_trajectory


def test_lingbot_backend_config_is_discriminated() -> None:
    backend = build_slam_backend_config(method=MethodId.LINGBOT_MAP, max_frames=3)

    assert isinstance(backend, LingbotMapSlamBackendConfig)
    assert backend.kind == "lingbot_map"
    assert backend.supports_offline is True
    assert backend.supports_streaming is True
    assert backend.supports_dense_points is True


def test_lingbot_backend_config_is_exported_from_stage_package() -> None:
    from prml_vslam.methods.stage import LingbotMapSlamBackendConfig as ExportedLingbotMapSlamBackendConfig

    assert ExportedLingbotMapSlamBackendConfig is LingbotMapSlamBackendConfig


def test_lingbot_streaming_is_available_and_sparse_requests_are_unavailable(tmp_path: Path) -> None:
    backend = LingbotMapSlamBackendConfig()
    context = PipelinePlanContext(
        run_config=build_run_config(
            experiment_name="lingbot",
            mode=PipelineMode.STREAMING,
            output_dir=tmp_path,
            source_backend=TumRgbdSourceConfig(sequence_id="freiburg3_large_cabinet"),
            method=MethodId.LINGBOT_MAP,
        ),
        path_config=PathConfig(),
        run_paths=RunArtifactPaths.build(tmp_path / "lingbot"),
        slam_backend=backend,
    )

    available, reason = SlamStageConfig(backend=backend).availability(context)

    assert available is True
    assert reason is None

    offline_context = PipelinePlanContext(
        run_config=build_run_config(
            experiment_name="lingbot",
            mode=PipelineMode.OFFLINE,
            output_dir=tmp_path,
            source_backend=TumRgbdSourceConfig(sequence_id="freiburg3_large_cabinet"),
            method=MethodId.LINGBOT_MAP,
        ),
        path_config=PathConfig(),
        run_paths=context.run_paths,
        slam_backend=backend,
    )
    available, reason = SlamStageConfig(
        backend=backend,
        outputs=SlamOutputPolicy(emit_dense_points=True, emit_sparse_points=True),
    ).availability(offline_context)

    assert available is False
    assert "does not expose a separate sparse point-cloud artifact" in str(reason)


def test_lingbot_full_toml_parses_through_run_config() -> None:
    config = load_run_config_toml(
        path_config=PathConfig(),
        config_path=Path(".configs/pipelines/lingbot-full.toml"),
    )

    assert config.mode is PipelineMode.OFFLINE
    assert config.stages.slam.backend.method_id is MethodId.LINGBOT_MAP
    assert config.stages.slam.backend.enable_point_head is False
    assert config.stages.slam.backend.confidence_threshold == 1.5
    assert config.stages.slam.outputs.emit_dense_points is True
    assert config.stages.slam.outputs.emit_sparse_points is False
    assert config.stages.align_ground.enabled is True
    assert config.stages.reconstruction.enabled is False
    assert config.visualization.export_viewer_rrd is True
    assert config.visualization.connect_live_viewer is False


def test_lingbot_planned_outputs_use_normalized_geometry_paths(tmp_path: Path) -> None:
    config = build_run_config(
        experiment_name="lingbot-plan",
        mode=PipelineMode.OFFLINE,
        output_dir=tmp_path,
        source_backend=TumRgbdSourceConfig(sequence_id="freiburg3_large_cabinet"),
        method=MethodId.LINGBOT_MAP,
    )

    plan = config.compile_plan(PathConfig(root=tmp_path), fail_on_unavailable=True)
    slam_stage = next(stage for stage in plan.stages if stage.key.value == "slam")

    assert [path.name for path in slam_stage.outputs] == [
        "trajectory.tum",
        "point_cloud.ply",
    ]


def test_lingbot_streaming_smoke_toml_parses_through_run_config() -> None:
    config = load_run_config_toml(
        path_config=PathConfig(),
        config_path=Path(".configs/pipelines/lingbot-smoke-streaming-gpu.toml"),
    )

    assert config.mode is PipelineMode.STREAMING
    assert config.stages.slam.backend.method_id is MethodId.LINGBOT_MAP
    assert config.stages.slam.backend.max_frames == 2
    assert config.stages.slam.outputs.emit_dense_points is True
    assert config.stages.slam.outputs.emit_sparse_points is False


def test_lingbot_config_rejects_invalid_runtime_values() -> None:
    with pytest.raises(ValueError, match="image_size"):
        LingbotMapSlamBackendConfig(image_size=225, patch_size=14)
    with pytest.raises(ValueError, match="point_stride"):
        LingbotMapSlamBackendConfig(point_stride=0)
    with pytest.raises(ValueError, match="max_points"):
        LingbotMapSlamBackendConfig(max_points=0)
    with pytest.raises(ValueError, match="keyframe_interval"):
        LingbotMapSlamBackendConfig(keyframe_interval=0)
    assert LingbotMapSlamBackendConfig(confidence_threshold=1.5).confidence_threshold == 1.5


def test_lingbot_app_action_coerces_sparse_output(tmp_path: Path) -> None:
    context = types.SimpleNamespace(
        path_config=PathConfig(root=tmp_path),
        advio_service=types.SimpleNamespace(scene=lambda _sequence_id: types.SimpleNamespace(sequence_slug="advio-01")),
    )
    action = PipelinePageAction(
        experiment_name="lingbot-app",
        config_path=Path(".configs/pipelines/lingbot-full.toml"),
        source_kind=PipelineSourceId.ADVIO,
        advio_sequence_id=1,
        record3d_transport=Record3DTransportId.USB,
        pose_source=AdvioPoseSource.GROUND_TRUTH,
        pose_frame_mode=AdvioPoseFrameMode.PROVIDER_WORLD,
        method=MethodId.LINGBOT_MAP,
        slam_backend_spec=LingbotMapSlamBackendConfig(max_frames=2),
        emit_sparse_points=True,
    )

    run_config, error = build_run_config_from_action(context, action)

    assert error is None
    assert run_config is not None
    assert run_config.stages.slam.backend.method_id is MethodId.LINGBOT_MAP
    assert run_config.stages.slam.outputs.emit_sparse_points is False


def test_lingbot_app_editor_preserves_gpu_fit_backend_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeColumn:
        def __enter__(self) -> FakeColumn:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

    backend = LingbotMapSlamBackendConfig(
        max_frames=2,
        image_size=224,
        patch_size=14,
        num_scale_frames=1,
        model_dtype="float32",
        checkpoint_pos_embed="interpolate",
        camera_num_iterations=1,
        enable_point_head=True,
    )

    monkeypatch.setattr(pipeline_request_editor.st, "columns", lambda *_args, **_kwargs: [FakeColumn(), FakeColumn()])
    monkeypatch.setattr(pipeline_request_editor.st, "expander", lambda *_args, **_kwargs: FakeColumn())
    monkeypatch.setattr(
        pipeline_request_editor.st,
        "selectbox",
        lambda _label, *, options, index=0, **_kwargs: options[index],
    )
    monkeypatch.setattr(
        pipeline_request_editor.st,
        "number_input",
        lambda _label, *, value, **_kwargs: value,
    )
    monkeypatch.setattr(
        pipeline_request_editor.st,
        "toggle",
        lambda _label, *, value, **_kwargs: value,
    )
    monkeypatch.setattr(
        pipeline_request_editor.st,
        "text_input",
        lambda _label, *, value, **_kwargs: value,
    )

    rendered = pipeline_request_editor._render_lingbot_backend_settings(backend, max_frames=backend.max_frames)

    assert rendered.model_dtype == "float32"
    assert rendered.checkpoint_pos_embed == "interpolate"
    assert (rendered.camera_num_iterations, rendered.enable_point_head) == (1, False)


def test_lingbot_pose_conversion_uses_benchmark_camera_to_world_convention() -> None:
    T_world_camera = np.eye(4, dtype=np.float64)
    T_world_camera[0, 3] = 2.0

    transform = _pose_camera_to_world_to_frame_transform(T_world_camera[:3])

    assert transform.target_frame == "lingbot_world"
    assert transform.source_frame == CAMERA_RDF_FRAME
    np.testing.assert_allclose(transform.as_matrix(), T_world_camera)


def test_lingbot_auto_keyframe_interval_resolves_to_upstream_int() -> None:
    assert _resolve_keyframe_interval("auto", num_frames=20, num_scale_frames=8) == 1
    assert _resolve_keyframe_interval("auto", num_frames=700, num_scale_frames=8) == 3
    assert _resolve_keyframe_interval("auto", num_frames=1011, num_scale_frames=8) == 4
    assert _resolve_keyframe_interval(0, num_frames=700, num_scale_frames=8) == 1
    assert _resolve_keyframe_interval(3, num_frames=700, num_scale_frames=8) == 3


def test_lingbot_preprocesses_images_to_patch_aligned_width() -> None:
    torch = pytest.importorskip("torch")
    rgb = np.zeros((480, 640, 3), dtype=np.uint8)

    tensor = _images_to_tensor(torch, [rgb], device="cpu", image_size=518, patch_size=14)

    assert tuple(tensor.shape) == (1, 3, 392, 518)


def test_lingbot_checkpoint_pos_embed_interpolates_to_smaller_image_grid() -> None:
    torch = pytest.importorskip("torch")
    source = torch.arange(1 * (37 * 37 + 1) * 4, dtype=torch.float32).reshape(1, 37 * 37 + 1, 4)
    target = torch.zeros((1, 16 * 16 + 1, 4), dtype=torch.float32)
    state_dict = {"aggregator.patch_embed.pos_embed": source.clone()}

    _adapt_checkpoint_state_dict(
        torch,
        state_dict,
        target_state_dict={"aggregator.patch_embed.pos_embed": target},
        pos_embed_policy="interpolate",
    )

    resized = state_dict["aggregator.patch_embed.pos_embed"]
    assert tuple(resized.shape) == tuple(target.shape)
    np.testing.assert_allclose(resized[:, :1].numpy(), source[:, :1].numpy())


def test_lingbot_checkpoint_pos_embed_requires_policy_for_smaller_image_grid() -> None:
    torch = pytest.importorskip("torch")
    source = torch.zeros((1, 37 * 37 + 1, 4), dtype=torch.float32)
    target = torch.zeros((1, 16 * 16 + 1, 4), dtype=torch.float32)

    with pytest.raises(RuntimeError, match="checkpoint_pos_embed"):
        _adapt_checkpoint_state_dict(
            torch,
            {"aggregator.patch_embed.pos_embed": source},
            target_state_dict={"aggregator.patch_embed.pos_embed": target},
            pos_embed_policy="error",
        )


def test_lingbot_checkpoint_pos_embed_can_be_dropped_for_smaller_image_grid() -> None:
    torch = pytest.importorskip("torch")
    state_dict = {"aggregator.patch_embed.pos_embed": torch.zeros((1, 37 * 37 + 1, 4), dtype=torch.float32)}

    _adapt_checkpoint_state_dict(
        torch,
        state_dict,
        target_state_dict={"aggregator.patch_embed.pos_embed": torch.zeros((1, 16 * 16 + 1, 4), dtype=torch.float32)},
        pos_embed_policy="drop",
    )

    assert "aggregator.patch_embed.pos_embed" not in state_dict


def test_lingbot_backend_caps_max_frames_before_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_pose_decoder(monkeypatch, num_frames=2)
    captured: dict[str, int] = {}
    rgb = np.zeros((2, 2, 3), dtype=np.uint8)
    observations = [
        Observation(seq=idx, timestamp_ns=idx * 1_000_000_000, provenance=ObservationProvenance(), rgb=rgb)
        for idx in range(4)
    ]

    class FakeRuntime:
        def __init__(self, _config: LingbotMapSlamBackendConfig, *, path_config: PathConfig) -> None:
            del path_config

        def infer(self, images_rgb: list[np.ndarray]) -> tuple[dict[str, Any], np.ndarray]:
            captured["num_images"] = len(images_rgb)
            predictions = {
                "pose_enc": np.zeros((1, 2, 9), dtype=np.float32),
                "depth": np.ones((1, 2, 2, 2, 1), dtype=np.float32),
            }
            processed_images = np.zeros((1, 2, 3, 2, 2), dtype=np.float32)
            return predictions, processed_images

    monkeypatch.setattr(lingbot_adapter, "_LingbotRuntime", FakeRuntime)
    config = LingbotMapSlamBackendConfig(max_frames=2)

    artifacts = LingbotMapSlamBackend(config).run_observations(
        observations,
        benchmark_inputs=None,
        baseline_source=ReferenceSource.GROUND_TRUTH,
        backend_config=config,
        output_policy=SlamOutputPolicy(emit_dense_points=False, emit_sparse_points=False),
        artifact_root=tmp_path,
    )

    assert captured["num_images"] == 2
    assert artifacts.num_keyframes == 2


def test_lingbot_streaming_buffers_frames_and_writes_terminal_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_fake_pose_decoder(monkeypatch, num_frames=2)
    captured: dict[str, int] = {}
    rgb = np.zeros((2, 2, 3), dtype=np.uint8)

    class FakeRuntime:
        def __init__(self, _config: LingbotMapSlamBackendConfig, *, path_config: PathConfig) -> None:
            del path_config

        def infer(self, images_rgb: list[np.ndarray]) -> tuple[dict[str, Any], np.ndarray]:
            captured["num_images"] = len(images_rgb)
            predictions = {
                "pose_enc": np.zeros((1, 2, 9), dtype=np.float32),
                "depth": np.ones((1, 2, 2, 2, 1), dtype=np.float32),
            }
            processed_images = np.zeros((1, 2, 3, 2, 2), dtype=np.float32)
            return predictions, processed_images

    monkeypatch.setattr(lingbot_adapter, "_LingbotRuntime", FakeRuntime)
    config = LingbotMapSlamBackendConfig(max_frames=2)
    backend = LingbotMapSlamBackend(config)

    backend.start_streaming(
        sequence_manifest=SequenceManifest(sequence_id="seq-1"),
        benchmark_inputs=None,
        baseline_source=ReferenceSource.GROUND_TRUTH,
        backend_config=config,
        output_policy=SlamOutputPolicy(emit_dense_points=False, emit_sparse_points=False),
        artifact_root=tmp_path,
    )
    for idx in range(4):
        backend.step_streaming(
            Observation(seq=idx, timestamp_ns=idx * 1_000_000_000, provenance=ObservationProvenance(), rgb=rgb)
        )

    assert backend.drain_streaming_updates() == []
    artifacts = backend.finish_streaming()

    assert captured["num_images"] == 2
    assert artifacts.num_processed_frames == 2
    assert artifacts.num_keyframes == 2


def test_lingbot_artifact_builder_writes_mandatory_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    extrinsics_camera_to_world = np.tile(np.eye(4, dtype=np.float32)[:3], (1, 2, 1, 1))
    extrinsics_camera_to_world[0, 0, 0, 3] = 1.0
    extrinsics_camera_to_world[0, 1, 0, 3] = 2.0
    _install_fake_pose_decoder(monkeypatch, extrinsics_camera_to_world=extrinsics_camera_to_world)
    rgb = np.full((2, 2, 3), 128, dtype=np.uint8)
    observations = [
        Observation(seq=idx, timestamp_ns=idx * 1_000_000_000, provenance=ObservationProvenance(), rgb=rgb)
        for idx in range(2)
    ]
    predictions = {
        "pose_enc": np.zeros((1, 2, 9), dtype=np.float32),
        "depth": np.ones((1, 2, 2, 2, 1), dtype=np.float32),
        "depth_conf": np.ones((1, 2, 2, 2), dtype=np.float32),
        "world_points": np.full((1, 2, 2, 2, 3), 99.0, dtype=np.float32),
    }
    processed_images = np.stack([rgb.transpose(2, 0, 1), rgb.transpose(2, 0, 1)], axis=0) / 255.0

    artifacts = _build_lingbot_artifacts(
        predictions=predictions,
        processed_images=processed_images,
        observations=observations,
        artifact_root=tmp_path,
        output_policy=SlamOutputPolicy(emit_dense_points=True, emit_sparse_points=False),
        config=LingbotMapSlamBackendConfig(
            point_stride=1,
            max_points=None,
            max_depth_m=None,
            confidence_threshold=0.5,
        ),
    )

    run_paths = RunArtifactPaths.build(tmp_path)
    assert artifacts.trajectory_tum.path == run_paths.trajectory_path
    assert artifacts.trajectory_tum.path.read_text(encoding="utf-8").count("\n") == 2
    trajectory = load_tum_trajectory(artifacts.trajectory_tum.path)
    np.testing.assert_allclose(trajectory.positions_xyz[:, 0], [1.0, 2.0])
    assert artifacts.dense_points_ply is not None
    assert artifacts.dense_points_ply.path == run_paths.point_cloud_path
    cloud = load_point_cloud_ply(artifacts.dense_points_ply.path)
    assert len(cloud) == 8
    np.testing.assert_allclose(np.unique(cloud[:, 0]), [0.0, 1.0, 2.0])
    assert artifacts.depth_maps_npz is None
    assert artifacts.point_maps_npz is None
    assert artifacts.point_cloud_confidences_npz is None
    assert "predictions_normalized.npz" in artifacts.extras
    with np.load(artifacts.extras["predictions_normalized.npz"].path) as native_predictions:
        assert "extrinsics_camera_to_world" in native_predictions
        assert "extrinsics_camera_from_world" not in native_predictions
        np.testing.assert_allclose(native_predictions["extrinsics_camera_to_world"][:, 0, 3], [1.0, 2.0])
    assert "lingbot_metadata.json" in artifacts.extras
    assert artifacts.num_processed_frames == 2
    assert artifacts.num_keyframes == 2
    assert artifacts.num_dense_points == 8


def test_lingbot_artifact_builder_rejects_pose_count_mismatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_pose_decoder(monkeypatch, num_frames=1)
    rgb = np.full((2, 2, 3), 128, dtype=np.uint8)
    observations = [
        Observation(seq=idx, timestamp_ns=idx * 1_000_000_000, provenance=ObservationProvenance(), rgb=rgb)
        for idx in range(2)
    ]
    predictions = {
        "pose_enc": np.zeros((1, 1, 9), dtype=np.float32),
        "depth": np.ones((1, 1, 2, 2, 1), dtype=np.float32),
    }
    processed_images = np.stack([rgb.transpose(2, 0, 1), rgb.transpose(2, 0, 1)], axis=0) / 255.0

    with pytest.raises(RuntimeError, match="pose prediction count"):
        _build_lingbot_artifacts(
            predictions=predictions,
            processed_images=processed_images,
            observations=observations,
            artifact_root=tmp_path,
            output_policy=SlamOutputPolicy(emit_dense_points=False, emit_sparse_points=False),
            config=LingbotMapSlamBackendConfig(),
        )


def test_lingbot_artifact_builder_rejects_missing_confidence_when_filtering(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_fake_pose_decoder(monkeypatch, num_frames=1)
    rgb = np.full((2, 2, 3), 128, dtype=np.uint8)
    observations = [Observation(seq=0, timestamp_ns=0, provenance=ObservationProvenance(), rgb=rgb)]
    predictions = {
        "pose_enc": np.zeros((1, 1, 9), dtype=np.float32),
        "depth": np.ones((1, 1, 2, 2, 1), dtype=np.float32),
    }
    processed_images = rgb.transpose(2, 0, 1)[None, ...] / 255.0

    with pytest.raises(RuntimeError, match="confidence filtering requested"):
        _build_lingbot_artifacts(
            predictions=predictions,
            processed_images=processed_images,
            observations=observations,
            artifact_root=tmp_path,
            output_policy=SlamOutputPolicy(emit_dense_points=True, emit_sparse_points=False),
            config=LingbotMapSlamBackendConfig(confidence_threshold=1.5),
        )
    predictions["depth_conf"] = np.ones((1, 1, 1, 1), dtype=np.float32)
    with pytest.raises(RuntimeError, match="confidence map `depth_conf` shape"):
        _build_lingbot_artifacts(
            predictions=predictions,
            processed_images=processed_images,
            observations=observations,
            artifact_root=tmp_path,
            output_policy=SlamOutputPolicy(emit_dense_points=True, emit_sparse_points=False),
            config=LingbotMapSlamBackendConfig(confidence_threshold=1.5),
        )


def test_lingbot_artifact_builder_accepts_batched_single_frame_images(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_fake_pose_decoder(monkeypatch, num_frames=1)
    rgb = np.full((2, 2, 3), 64, dtype=np.uint8)
    observations = [Observation(seq=0, timestamp_ns=0, provenance=ObservationProvenance(), rgb=rgb)]
    predictions = {
        "pose_enc": np.zeros((1, 1, 9), dtype=np.float32),
        "depth": np.ones((1, 1, 2, 2, 1), dtype=np.float32),
    }
    processed_images = rgb.transpose(2, 0, 1)[None, None, ...] / 255.0

    artifacts = _build_lingbot_artifacts(
        predictions=predictions,
        processed_images=processed_images,
        observations=observations,
        artifact_root=tmp_path,
        output_policy=SlamOutputPolicy(emit_dense_points=True, emit_sparse_points=False),
        config=LingbotMapSlamBackendConfig(point_stride=1, max_points=None, max_depth_m=None),
    )

    assert artifacts.num_keyframes == 1
    assert artifacts.dense_points_ply is not None
    cloud = load_point_cloud_ply(artifacts.dense_points_ply.path)
    assert len(cloud) == 4


def _install_fake_pose_decoder(
    monkeypatch: pytest.MonkeyPatch,
    *,
    num_frames: int = 2,
    extrinsics_camera_to_world: np.ndarray | None = None,
) -> None:
    package = types.ModuleType("lingbot_map")
    utils = types.ModuleType("lingbot_map.utils")
    pose_enc = types.ModuleType("lingbot_map.utils.pose_enc")

    def pose_encoding_to_extri_intri(
        _pose_enc: object, image_size_hw: tuple[int, int]
    ) -> tuple[np.ndarray, np.ndarray]:
        height, width = image_size_hw
        extrinsics = (
            np.asarray(extrinsics_camera_to_world, dtype=np.float32)
            if extrinsics_camera_to_world is not None
            else np.tile(np.eye(4, dtype=np.float32)[:3], (1, num_frames, 1, 1))
        )
        intrinsics = np.tile(
            np.array([[1.0, 0.0, width / 2.0], [0.0, 1.0, height / 2.0], [0.0, 0.0, 1.0]], dtype=np.float32),
            (1, num_frames, 1, 1),
        )
        return extrinsics, intrinsics

    pose_enc.pose_encoding_to_extri_intri = pose_encoding_to_extri_intri
    monkeypatch.setitem(sys.modules, "lingbot_map", package)
    monkeypatch.setitem(sys.modules, "lingbot_map.utils", utils)
    monkeypatch.setitem(sys.modules, "lingbot_map.utils.pose_enc", pose_enc)
