"""Stage-local SLAM visualization adapter.

This module translates method-owned :class:`SlamUpdate` values plus
runtime-created payload refs into neutral :class:`VisualizationItem` values.
It deliberately does not know Rerun entity paths, timelines, styling, or SDK
objects; those concerns belong to the Rerun sink policy.
"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
from scipy.spatial.transform import Rotation, Slerp  # type: ignore[import-untyped]

from prml_vslam.interfaces import FrameTransform
from prml_vslam.methods.contracts import SlamUpdate
from prml_vslam.pipeline.stages.base.contracts import VisualizationIntent, VisualizationItem
from prml_vslam.pipeline.stages.base.handles import TransientPayloadRef

SOURCE_RGB_REF = "source_rgb"
IMAGE_REF = "image"
DEPTH_REF = "depth"
PREVIEW_REF = "preview"
POINTMAP_REF = "pointmap"
COLORS_REF = "colors"

ROLE_SOURCE_RGB = "source_rgb"
ROLE_TRACKING_POSE = "tracking_pose"
ROLE_TRACKING_TRAJECTORY = "tracking_trajectory"
ROLE_TRACKING_POSE_SMOOTHED = "tracking_pose_smoothed"
ROLE_TRACKING_TRAJECTORY_SMOOTHED = "tracking_trajectory_smoothed"
ROLE_LIVE_MODEL_POSE = "live_model_pose"
ROLE_LIVE_MODEL_POSE_ALIGNED = "live_model_pose_aligned"
ROLE_MODEL_PINHOLE = "model_pinhole"
ROLE_MODEL_PINHOLE_ALIGNED = "model_pinhole_aligned"
ROLE_MODEL_RGB = "model_rgb"
ROLE_MODEL_CAMERA_RGB = "model_camera_rgb"
ROLE_MODEL_DEPTH = "model_depth"
ROLE_MODEL_PREVIEW = "model_preview"
ROLE_MODEL_POINTMAP = "model_pointmap"
ROLE_MODEL_POINTMAP_ALIGNED = "model_pointmap_aligned"
ROLE_KEYFRAME_CAMERA_POSE = "keyframe_camera_pose"
ROLE_KEYFRAME_CAMERA_POSE_ALIGNED = "keyframe_camera_pose_aligned"
ROLE_KEYFRAME_POINTS_POSE = "keyframe_points_pose"
ROLE_KEYFRAME_POINTS_POSE_ALIGNED = "keyframe_points_pose_aligned"
ROLE_KEYFRAME_PINHOLE = "keyframe_pinhole"
ROLE_KEYFRAME_PINHOLE_ALIGNED = "keyframe_pinhole_aligned"
ROLE_KEYFRAME_RGB = "keyframe_rgb"
ROLE_KEYFRAME_DEPTH = "keyframe_depth"
ROLE_KEYFRAME_PREVIEW = "keyframe_preview"
ROLE_KEYFRAME_POINTMAP = "keyframe_pointmap"
ROLE_KEYFRAME_POINTMAP_ALIGNED = "keyframe_pointmap_aligned"
ROLE_KEYFRAME_CAMERA_WINDOW = "keyframe_camera_window"

_POSE_SMOOTHING_ALPHA = 0.2
_POSE_RESET_TRANSLATION_M = 2.0
_POSE_RESET_ROTATION_DEG = 45.0


class SlamVisualizationAdapter:
    """Build neutral visualization descriptors for live SLAM updates."""

    def __init__(self) -> None:
        self._smoothed_pose: FrameTransform | None = None

    def build_items(
        self,
        update: SlamUpdate,
        payload_refs: Mapping[str, TransientPayloadRef],
    ) -> list[VisualizationItem]:
        """Return sink-facing visualization items for one SLAM update.

        Args:
            update: Method-owned live SLAM update. It may carry semantic pose,
                keyframe, intrinsics, and map-count data, but should not carry
                transient payload refs.
            payload_refs: Runtime-created refs keyed by semantic slots such as
                ``image``, ``depth``, ``preview``, ``pointmap``, or
                ``source_rgb``.

        Returns:
            Neutral visualization descriptors. The descriptors contain only
            semantic roles, small scalar metadata, frame indices, optional pose
            and intrinsics, and payload refs.
        """
        frame_index = update.source_seq if update.source_seq is not None else update.seq
        items: list[VisualizationItem] = []

        source_rgb = payload_refs.get(SOURCE_RGB_REF)
        if source_rgb is not None:
            items.append(
                VisualizationItem(
                    intent=VisualizationIntent.RGB_IMAGE,
                    role=ROLE_SOURCE_RGB,
                    payload_refs={IMAGE_REF: source_rgb},
                    frame_index=frame_index,
                    space="source_raster",
                )
            )

        if update.pose is not None:
            smoothed_pose = self._smooth_pose(update.pose)
            items.append(
                VisualizationItem(
                    intent=VisualizationIntent.POSE_TRANSFORM,
                    role=ROLE_TRACKING_POSE,
                    pose=update.pose,
                    frame_index=frame_index,
                    space="world",
                )
            )
            items.append(
                VisualizationItem(
                    intent=VisualizationIntent.POSE_TRANSFORM,
                    role=ROLE_TRACKING_POSE_SMOOTHED,
                    pose=smoothed_pose,
                    frame_index=frame_index,
                    space="world",
                )
            )
            items.append(
                VisualizationItem(
                    intent=VisualizationIntent.TRAJECTORY,
                    role=ROLE_TRACKING_TRAJECTORY,
                    pose=update.pose,
                    frame_index=frame_index,
                    space="world",
                )
            )
            items.append(
                VisualizationItem(
                    intent=VisualizationIntent.TRAJECTORY,
                    role=ROLE_TRACKING_TRAJECTORY_SMOOTHED,
                    pose=smoothed_pose,
                    frame_index=frame_index,
                    space="world",
                )
            )

        if not update.is_keyframe or update.keyframe_index is None or update.pose is None:
            return items

        keyframe_index = update.keyframe_index
        image = payload_refs.get(IMAGE_REF)
        depth = payload_refs.get(DEPTH_REF)
        preview = payload_refs.get(PREVIEW_REF)
        pointmap = payload_refs.get(POINTMAP_REF)

        items.extend(
            [
                VisualizationItem(
                    intent=VisualizationIntent.POSE_TRANSFORM,
                    role=ROLE_LIVE_MODEL_POSE,
                    pose=update.pose,
                    frame_index=frame_index,
                    keyframe_index=keyframe_index,
                    space="world",
                ),
                VisualizationItem(
                    intent=VisualizationIntent.POSE_TRANSFORM,
                    role=ROLE_LIVE_MODEL_POSE_ALIGNED,
                    pose=update.pose,
                    frame_index=frame_index,
                    keyframe_index=keyframe_index,
                    space="gravity_aligned_world",
                ),
                VisualizationItem(
                    intent=VisualizationIntent.POSE_TRANSFORM,
                    role=ROLE_KEYFRAME_CAMERA_POSE,
                    pose=update.pose,
                    frame_index=frame_index,
                    keyframe_index=keyframe_index,
                    space="world",
                ),
                VisualizationItem(
                    intent=VisualizationIntent.POSE_TRANSFORM,
                    role=ROLE_KEYFRAME_CAMERA_POSE_ALIGNED,
                    pose=update.pose,
                    frame_index=frame_index,
                    keyframe_index=keyframe_index,
                    space="gravity_aligned_world",
                ),
                VisualizationItem(
                    intent=VisualizationIntent.POSE_TRANSFORM,
                    role=ROLE_KEYFRAME_POINTS_POSE,
                    pose=update.pose,
                    frame_index=frame_index,
                    keyframe_index=keyframe_index,
                    space="world",
                ),
                VisualizationItem(
                    intent=VisualizationIntent.POSE_TRANSFORM,
                    role=ROLE_KEYFRAME_POINTS_POSE_ALIGNED,
                    pose=update.pose,
                    frame_index=frame_index,
                    keyframe_index=keyframe_index,
                    space="gravity_aligned_world",
                ),
            ]
        )

        camera_payload_refs = {
            ref_name: ref for ref_name, ref in ((IMAGE_REF, image), (DEPTH_REF, depth)) if ref is not None
        }
        if camera_payload_refs or update.camera_intrinsics is not None:
            for role in (
                ROLE_MODEL_PINHOLE,
                ROLE_KEYFRAME_PINHOLE,
                ROLE_MODEL_PINHOLE_ALIGNED,
                ROLE_KEYFRAME_PINHOLE_ALIGNED,
            ):
                items.append(
                    VisualizationItem(
                        intent=VisualizationIntent.PINHOLE_CAMERA,
                        role=role,
                        payload_refs=camera_payload_refs,
                        intrinsics=update.camera_intrinsics,
                        frame_index=frame_index,
                        keyframe_index=keyframe_index,
                        space="gravity_aligned_camera_raster" if role.endswith("_aligned") else "camera_raster",
                    )
                )

        if image is not None:
            for role in (ROLE_MODEL_RGB, ROLE_MODEL_CAMERA_RGB, ROLE_KEYFRAME_RGB):
                items.append(
                    VisualizationItem(
                        intent=VisualizationIntent.RGB_IMAGE,
                        role=role,
                        payload_refs={IMAGE_REF: image},
                        intrinsics=update.camera_intrinsics,
                        frame_index=frame_index,
                        keyframe_index=keyframe_index,
                        space="model_raster",
                    )
                )

        if depth is not None:
            for role in (ROLE_MODEL_DEPTH, ROLE_KEYFRAME_DEPTH):
                items.append(
                    VisualizationItem(
                        intent=VisualizationIntent.DEPTH_IMAGE,
                        role=role,
                        payload_refs={DEPTH_REF: depth},
                        intrinsics=update.camera_intrinsics,
                        frame_index=frame_index,
                        keyframe_index=keyframe_index,
                        space="model_raster",
                        metadata={"meter": 1.0},
                    )
                )

        if preview is not None:
            for role in (ROLE_MODEL_PREVIEW, ROLE_KEYFRAME_PREVIEW):
                items.append(
                    VisualizationItem(
                        intent=VisualizationIntent.RGB_IMAGE,
                        role=role,
                        payload_refs={IMAGE_REF: preview},
                        frame_index=frame_index,
                        keyframe_index=keyframe_index,
                        space="diagnostic_raster",
                    )
                )

        if pointmap is not None:
            pointmap_refs = {POINTMAP_REF: pointmap}
            if image is not None:
                pointmap_refs[COLORS_REF] = image
            for role in (
                ROLE_MODEL_POINTMAP,
                ROLE_KEYFRAME_POINTMAP,
                ROLE_MODEL_POINTMAP_ALIGNED,
                ROLE_KEYFRAME_POINTMAP_ALIGNED,
            ):
                items.append(
                    VisualizationItem(
                        intent=VisualizationIntent.POINT_CLOUD,
                        role=role,
                        payload_refs=pointmap_refs,
                        pose=update.pose,
                        frame_index=frame_index,
                        keyframe_index=keyframe_index,
                        space="gravity_aligned_camera_local" if role.endswith("_aligned") else "camera_local",
                    )
                )

        items.append(
            VisualizationItem(
                intent=VisualizationIntent.CLEAR,
                role=ROLE_KEYFRAME_CAMERA_WINDOW,
                frame_index=frame_index,
                keyframe_index=keyframe_index,
                space="viewer_window",
            )
        )
        return items

    def _smooth_pose(self, pose: FrameTransform) -> FrameTransform:
        if self._smoothed_pose is None or _pose_jump_exceeds_reset(self._smoothed_pose, pose):
            self._smoothed_pose = pose
            return pose
        previous_translation = self._smoothed_pose.translation_xyz()
        current_translation = pose.translation_xyz()
        translation = (1.0 - _POSE_SMOOTHING_ALPHA) * previous_translation + _POSE_SMOOTHING_ALPHA * current_translation
        rotations = Rotation.from_quat([self._smoothed_pose.quaternion_xyzw(), pose.quaternion_xyzw()])
        rotation = Slerp([0.0, 1.0], rotations)([_POSE_SMOOTHING_ALPHA])[0]
        self._smoothed_pose = FrameTransform.from_quaternion_translation(
            rotation.as_quat(),
            translation,
            target_frame=pose.target_frame,
            source_frame=pose.source_frame,
        )
        return self._smoothed_pose


def _pose_jump_exceeds_reset(previous: FrameTransform, current: FrameTransform) -> bool:
    translation_delta = np.linalg.norm(current.translation_xyz() - previous.translation_xyz())
    rotation_delta = Rotation.from_quat(previous.quaternion_xyzw()).inv() * Rotation.from_quat(
        current.quaternion_xyzw()
    )
    return bool(
        translation_delta > _POSE_RESET_TRANSLATION_M
        or np.rad2deg(rotation_delta.magnitude()) > _POSE_RESET_ROTATION_DEG
    )
