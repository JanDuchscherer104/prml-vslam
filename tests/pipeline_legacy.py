"""Test-only adapters for legacy request fixtures."""

from __future__ import annotations

from prml_vslam.datasets.contracts import DatasetId
from prml_vslam.pipeline.config import RunConfig, StageBundle
from prml_vslam.pipeline.contracts.request import (
    DatasetSourceSpec,
    PlacementPolicy,
    Record3DLiveSourceSpec,
    RunRequest,
    SourceSpec,
    VideoSourceSpec,
)
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.source.config import (
    AdvioSourceConfig,
    Record3DSourceConfig,
    SourceBackendConfig,
    TumRgbdSourceConfig,
    VideoSourceConfig,
)


def run_config_from_request(request: RunRequest) -> RunConfig:
    """Project an old request fixture into the target config shape for tests."""
    return RunConfig(
        experiment_name=request.experiment_name,
        mode=request.mode,
        output_dir=request.output_dir,
        stages=StageBundle(
            source={
                "backend": source_backend_from_request_source(request.source),
                "execution": execution_payload_from_placement(request.placement, StageKey.INGEST),
            },
            slam={
                "backend": request.slam.backend,
                "outputs": request.slam.outputs,
                "execution": execution_payload_from_placement(request.placement, StageKey.SLAM),
            },
            align_ground={
                "enabled": request.alignment.ground.enabled,
                "execution": execution_payload_from_placement(request.placement, StageKey.GRAVITY_ALIGNMENT),
            },
            evaluate_trajectory={
                "enabled": request.benchmark.trajectory.enabled,
                "execution": execution_payload_from_placement(request.placement, StageKey.TRAJECTORY_EVALUATION),
            },
            reconstruction={
                "enabled": request.benchmark.reference.enabled,
                "execution": execution_payload_from_placement(request.placement, StageKey.REFERENCE_RECONSTRUCTION),
            },
            evaluate_cloud={
                "enabled": request.benchmark.cloud.enabled,
                "execution": execution_payload_from_placement(request.placement, StageKey.CLOUD_EVALUATION),
            },
            evaluate_efficiency={
                "enabled": request.benchmark.efficiency.enabled,
                "execution": execution_payload_from_placement(request.placement, StageKey.EFFICIENCY_EVALUATION),
            },
            summary={"execution": execution_payload_from_placement(request.placement, StageKey.SUMMARY)},
        ),
        benchmark=request.benchmark,
        alignment=request.alignment,
        visualization=request.visualization,
        runtime=request.runtime,
    )


def source_backend_from_request_source(source: SourceSpec) -> SourceBackendConfig:
    """Project an old source fixture into target source backend config."""
    match source:
        case VideoSourceSpec(video_path=video_path, frame_stride=frame_stride, target_fps=target_fps):
            return VideoSourceConfig(video_path=video_path, frame_stride=frame_stride, target_fps=target_fps)
        case DatasetSourceSpec(
            dataset_id=DatasetId.ADVIO,
            sequence_id=sequence_id,
            frame_stride=frame_stride,
            target_fps=target_fps,
            dataset_serving=dataset_serving,
            respect_video_rotation=respect_video_rotation,
        ):
            if dataset_serving is None:
                raise ValueError("ADVIO test fixtures require dataset_serving.")
            return AdvioSourceConfig(
                sequence_id=sequence_id,
                frame_stride=frame_stride,
                target_fps=target_fps,
                dataset_serving=dataset_serving,
                respect_video_rotation=respect_video_rotation,
            )
        case DatasetSourceSpec(
            dataset_id=DatasetId.TUM_RGBD,
            sequence_id=sequence_id,
            frame_stride=frame_stride,
            target_fps=target_fps,
        ):
            return TumRgbdSourceConfig(sequence_id=sequence_id, frame_stride=frame_stride, target_fps=target_fps)
        case Record3DLiveSourceSpec(transport=transport, device_index=device_index, device_address=device_address):
            return Record3DSourceConfig(
                transport=transport,
                device_index=0 if device_index is None else device_index,
                device_address=device_address,
            )


def execution_payload_from_placement(
    placement: PlacementPolicy,
    stage_key: StageKey,
) -> dict[str, dict[str, float | dict[str, float]]]:
    """Project old placement fixture resources into target execution payload."""
    stage_placement = placement.by_stage.get(stage_key)
    if stage_placement is None:
        return {}
    resources = dict(stage_placement.resources)
    custom_resources = dict(resources)
    payload: dict[str, float] = {}
    num_cpus = custom_resources.pop("CPU", None)
    if num_cpus is not None:
        payload["num_cpus"] = num_cpus
    num_gpus = custom_resources.pop("GPU", None)
    if num_gpus is not None:
        payload["num_gpus"] = num_gpus
    return {"resources": {**payload, "custom_resources": custom_resources}}
