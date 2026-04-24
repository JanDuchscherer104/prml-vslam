"""Source-stage visualization adapter.

The source stage owns dataset/reference semantics, but it does not own Rerun
entity paths or SDK calls. This adapter turns source-stage outputs and live
source packets into neutral :class:`VisualizationItem` values for observer
sinks.
"""

from __future__ import annotations

from collections.abc import Mapping

from prml_vslam.benchmark.contracts import ReferenceCloudCoordinateStatus, ReferenceSource
from prml_vslam.datasets.contracts import DatasetId
from prml_vslam.interfaces.ingest import (
    ReferenceCloudRef,
    ReferencePointCloudSequenceRef,
    RgbdObservationSequenceRef,
    SourceStageOutput,
)
from prml_vslam.interfaces.runtime import FramePacket
from prml_vslam.pipeline.contracts.provenance import ArtifactRef
from prml_vslam.pipeline.stages.base.contracts import VisualizationIntent, VisualizationItem
from prml_vslam.pipeline.stages.base.handles import TransientPayloadRef

IMAGE_REF = "image"
DEPTH_REF = "depth"
POINTMAP_REF = "pointmap"
COLORS_REF = "colors"
TRAJECTORY_ARTIFACT = "trajectory"
POINT_CLOUD_ARTIFACT = "point_cloud"
METADATA_ARTIFACT = "metadata"

ROLE_SOURCE_RGB = "source_rgb"
ROLE_SOURCE_CAMERA_POSE = "source_camera_pose"
ROLE_SOURCE_PINHOLE = "source_pinhole"
ROLE_SOURCE_CAMERA_RGB = "source_camera_rgb"
ROLE_SOURCE_DEPTH = "source_depth"
ROLE_SOURCE_POINTMAP = "source_pointmap"
ROLE_SOURCE_REFERENCE_TRAJECTORY = "source_reference_trajectory"
ROLE_SOURCE_REFERENCE_POINT_CLOUD = "source_reference_point_cloud"


class SourceVisualizationAdapter:
    """Build neutral visualization descriptors for source-owned payloads."""

    def build_packet_items(
        self,
        *,
        packet: FramePacket,
        frame_payload_ref: TransientPayloadRef | None,
        depth_payload_ref: TransientPayloadRef | None = None,
        pointmap_payload_ref: TransientPayloadRef | None = None,
    ) -> list[VisualizationItem]:
        """Return live source-packet visualization items."""
        items: list[VisualizationItem] = []
        if frame_payload_ref is not None:
            items.append(
                VisualizationItem(
                    intent=VisualizationIntent.RGB_IMAGE,
                    role=ROLE_SOURCE_RGB,
                    payload_refs={IMAGE_REF: frame_payload_ref},
                    frame_index=packet.seq,
                    space="source_raster",
                )
            )

        if packet.pose is None or packet.intrinsics is None:
            return items

        camera_payload_refs = {
            ref_name: ref
            for ref_name, ref in ((IMAGE_REF, frame_payload_ref), (DEPTH_REF, depth_payload_ref))
            if ref is not None
        }
        if camera_payload_refs:
            items.extend(
                [
                    VisualizationItem(
                        intent=VisualizationIntent.POSE_TRANSFORM,
                        role=ROLE_SOURCE_CAMERA_POSE,
                        pose=packet.pose,
                        intrinsics=packet.intrinsics,
                        frame_index=packet.seq,
                        space=packet.pose.target_frame,
                    ),
                    VisualizationItem(
                        intent=VisualizationIntent.PINHOLE_CAMERA,
                        role=ROLE_SOURCE_PINHOLE,
                        payload_refs=camera_payload_refs,
                        pose=packet.pose,
                        intrinsics=packet.intrinsics,
                        frame_index=packet.seq,
                        space="source_camera_raster",
                    ),
                ]
            )
        if frame_payload_ref is not None:
            items.append(
                VisualizationItem(
                    intent=VisualizationIntent.RGB_IMAGE,
                    role=ROLE_SOURCE_CAMERA_RGB,
                    payload_refs={IMAGE_REF: frame_payload_ref},
                    pose=packet.pose,
                    intrinsics=packet.intrinsics,
                    frame_index=packet.seq,
                    space="source_camera_raster",
                )
            )
        if depth_payload_ref is not None:
            items.append(
                VisualizationItem(
                    intent=VisualizationIntent.DEPTH_IMAGE,
                    role=ROLE_SOURCE_DEPTH,
                    payload_refs={DEPTH_REF: depth_payload_ref},
                    pose=packet.pose,
                    intrinsics=packet.intrinsics,
                    frame_index=packet.seq,
                    space="source_camera_raster",
                    metadata={"meter": 1.0},
                )
            )
        if pointmap_payload_ref is not None:
            pointmap_refs = {POINTMAP_REF: pointmap_payload_ref}
            if frame_payload_ref is not None:
                pointmap_refs[COLORS_REF] = frame_payload_ref
            items.append(
                VisualizationItem(
                    intent=VisualizationIntent.POINT_CLOUD,
                    role=ROLE_SOURCE_POINTMAP,
                    payload_refs=pointmap_refs,
                    pose=packet.pose,
                    intrinsics=packet.intrinsics,
                    frame_index=packet.seq,
                    space="camera_local",
                )
            )
        return items

    def build_reference_items(
        self,
        *,
        output: SourceStageOutput,
        artifact_refs: Mapping[str, ArtifactRef],
    ) -> list[VisualizationItem]:
        """Return source reference trajectory/cloud visualization items."""
        benchmark_inputs = output.benchmark_inputs
        if benchmark_inputs is None:
            return []

        items: list[VisualizationItem] = []
        sequence_manifest = output.sequence_manifest
        for reference in benchmark_inputs.reference_trajectories:
            artifact = artifact_refs.get(reference_trajectory_artifact_key(reference.source))
            if artifact is None:
                continue
            target_frame = _trajectory_world_frame(sequence_manifest.dataset_id, reference.source)
            items.append(
                VisualizationItem(
                    intent=VisualizationIntent.TRAJECTORY,
                    role=ROLE_SOURCE_REFERENCE_TRAJECTORY,
                    artifact_refs={TRAJECTORY_ARTIFACT: artifact},
                    space=target_frame,
                    metadata={
                        "reference_source": reference.source.value,
                        "sequence_id": sequence_manifest.sequence_id,
                        "target_frame": target_frame,
                        "coordinate_status": _trajectory_coordinate_status(sequence_manifest.dataset_id, target_frame),
                    },
                )
            )

        for reference in benchmark_inputs.reference_point_cloud_sequences:
            artifact = artifact_refs.get(reference_point_cloud_sequence_trajectory_artifact_key(reference))
            if artifact is None:
                continue
            items.append(
                VisualizationItem(
                    intent=VisualizationIntent.TRAJECTORY,
                    role=ROLE_SOURCE_REFERENCE_TRAJECTORY,
                    artifact_refs={TRAJECTORY_ARTIFACT: artifact},
                    space=reference.target_frame,
                    metadata={
                        "reference_source": reference.source.value,
                        "sequence_id": sequence_manifest.sequence_id,
                        "target_frame": reference.target_frame,
                        "native_frame": reference.native_frame,
                        "coordinate_status": reference.coordinate_status.value,
                    },
                )
            )

        for reference in benchmark_inputs.reference_clouds:
            artifact = artifact_refs.get(reference_cloud_artifact_key(reference))
            if artifact is None:
                continue
            metadata_artifact = artifact_refs.get(reference_cloud_metadata_artifact_key(reference))
            item_artifacts = {POINT_CLOUD_ARTIFACT: artifact}
            if metadata_artifact is not None:
                item_artifacts[METADATA_ARTIFACT] = metadata_artifact
            items.append(
                VisualizationItem(
                    intent=VisualizationIntent.POINT_CLOUD,
                    role=ROLE_SOURCE_REFERENCE_POINT_CLOUD,
                    artifact_refs=item_artifacts,
                    space=reference.target_frame,
                    metadata={
                        "reference_source": reference.source.value,
                        "coordinate_status": reference.coordinate_status.value,
                        "target_frame": reference.target_frame,
                        "sequence_id": sequence_manifest.sequence_id,
                    },
                )
            )
        return items


def reference_trajectory_artifact_key(source: ReferenceSource) -> str:
    """Return the source-stage artifact key for one prepared trajectory."""
    return f"reference_tum:{source.value}"


def reference_cloud_artifact_key(reference: ReferenceCloudRef) -> str:
    """Return the source-stage artifact key for one prepared static cloud."""
    return f"reference_cloud:{reference.source.value}:{reference.coordinate_status.value}"


def reference_cloud_metadata_artifact_key(reference: ReferenceCloudRef) -> str:
    """Return the source-stage artifact key for one static cloud metadata file."""
    return f"reference_cloud_metadata:{reference.source.value}:{reference.coordinate_status.value}"


def reference_point_cloud_sequence_index_artifact_key(reference: ReferencePointCloudSequenceRef) -> str:
    """Return the source-stage artifact key for one point-cloud sequence index."""
    return f"reference_point_cloud_sequence_index:{reference.source.value}"


def reference_point_cloud_sequence_trajectory_artifact_key(reference: ReferencePointCloudSequenceRef) -> str:
    """Return the source-stage artifact key for one point-cloud sequence trajectory."""
    return f"reference_point_cloud_sequence_trajectory:{reference.source.value}"


def reference_point_cloud_sequence_payload_artifact_key(reference: ReferencePointCloudSequenceRef) -> str:
    """Return the source-stage artifact key for one point-cloud sequence payload root."""
    return f"reference_point_cloud_sequence_payload_root:{reference.source.value}"


def rgbd_observation_sequence_artifact_key(reference: RgbdObservationSequenceRef) -> str:
    """Return the source-stage artifact key for one RGB-D observation sequence index."""
    return f"rgbd_observation_sequence:{reference.source_id}:{reference.sequence_id}"


def _trajectory_world_frame(dataset_id: DatasetId | None, source: ReferenceSource) -> str:
    if dataset_id is DatasetId.TUM_RGBD:
        return "tum_rgbd_mocap_world"
    if dataset_id is DatasetId.ADVIO:
        return {
            ReferenceSource.GROUND_TRUTH: "advio_gt_world",
            ReferenceSource.ARCORE: "advio_arcore_world",
            ReferenceSource.ARKIT: "advio_arkit_world",
        }.get(source, f"advio_{source.value}_world")
    return "world"


def _trajectory_coordinate_status(dataset_id: DatasetId | None, target_frame: str) -> str:
    if dataset_id is DatasetId.ADVIO and target_frame == "advio_gt_world":
        return ReferenceCloudCoordinateStatus.ALIGNED.value
    return ReferenceCloudCoordinateStatus.SOURCE_NATIVE.value


__all__ = [
    "IMAGE_REF",
    "COLORS_REF",
    "DEPTH_REF",
    "METADATA_ARTIFACT",
    "POINT_CLOUD_ARTIFACT",
    "POINTMAP_REF",
    "ROLE_SOURCE_CAMERA_POSE",
    "ROLE_SOURCE_CAMERA_RGB",
    "ROLE_SOURCE_DEPTH",
    "ROLE_SOURCE_PINHOLE",
    "ROLE_SOURCE_POINTMAP",
    "ROLE_SOURCE_REFERENCE_POINT_CLOUD",
    "ROLE_SOURCE_REFERENCE_TRAJECTORY",
    "ROLE_SOURCE_RGB",
    "SourceVisualizationAdapter",
    "TRAJECTORY_ARTIFACT",
    "reference_cloud_artifact_key",
    "reference_cloud_metadata_artifact_key",
    "reference_point_cloud_sequence_index_artifact_key",
    "reference_point_cloud_sequence_payload_artifact_key",
    "reference_point_cloud_sequence_trajectory_artifact_key",
    "reference_trajectory_artifact_key",
    "rgbd_observation_sequence_artifact_key",
]
