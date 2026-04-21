"""Streaming session wrapper for ViSTA-SLAM.

This module contains the live-session wrapper that exposes the upstream
`OnlineSLAM` path through repo-owned runtime contracts without changing ViSTA's
native world semantics. The key distinction is that live updates expose scaled
camera-local pointmaps on the ViSTA model raster, while end-of-run export
produces a separately fused world-space dense cloud in the preserved native
output directory.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from prml_vslam.interfaces import CameraIntrinsics, FramePacket
from prml_vslam.methods.config_contracts import SlamOutputPolicy
from prml_vslam.methods.configs import VistaSlamBackendConfig
from prml_vslam.methods.updates import SlamUpdate
from prml_vslam.pipeline.contracts.artifacts import SlamArtifacts
from prml_vslam.utils import Console, PathConfig, RunArtifactPaths

from .artifacts import _frame_transform_from_vista_pose, build_vista_artifacts
from .preprocess import VistaFramePreprocessor, vista_numpy_array
from .runtime import VistaFlowTracker, VistaOnlineSlam, build_vista_runtime_components


class VistaSlamSession:
    """Stateful streaming session that forwards frames to upstream OnlineSLAM.

    The session preserves two different visualization surfaces:

    - source frames arrive as repo `FramePacket.rgb` payloads and can be logged
      independently by the repo-owned Rerun sink;
    - ViSTA model outputs (`image_rgb`, `depth_map`, `camera_intrinsics`,
      `pointmap`, `preview_rgb`) all live on the preprocessed ViSTA raster.

    The session does not normalize ViSTA's RDF-like world orientation into a
    separate repo/world-up basis.
    """

    def __init__(
        self,
        *,
        slam: VistaOnlineSlam,
        flow_tracker: VistaFlowTracker,
        frame_preprocessor: VistaFramePreprocessor,
        artifact_root: Path,
        output_policy: SlamOutputPolicy,
        console: Console,
    ) -> None:
        self._slam = slam
        self._flow_tracker = flow_tracker
        self._frame_preprocessor = frame_preprocessor
        self._artifact_root = artifact_root
        self._output_policy = output_policy
        self._console = console
        self._source_frame_count = 0
        self._accepted_keyframe_count = 0
        self._accepted_keyframe_timestamps_s: list[float] = []
        self._num_dense_points = 0
        self._live_preview_wait_logged = False
        self._pending_updates: list[SlamUpdate] = []

    def step(self, frame: FramePacket) -> None:
        """Feed one frame to OnlineSLAM and buffer incremental telemetry."""
        self._source_frame_count += 1

        if frame.rgb is None:
            self._pending_updates.append(
                SlamUpdate(
                    seq=frame.seq,
                    timestamp_ns=frame.timestamp_ns,
                    source_seq=frame.seq,
                    source_timestamp_ns=frame.timestamp_ns,
                    is_keyframe=False,
                    keyframe_index=None,
                    num_dense_points=self._num_dense_points,
                )
            )
            return

        prepared_frame = self._frame_preprocessor.prepare(
            frame.rgb,
            view_name=f"frame_{self._accepted_keyframe_count:06d}",
        )
        grayscale = prepared_frame.gray_u8
        is_keyframe = bool(self._flow_tracker.compute_disparity(grayscale, visualize=False))
        if not is_keyframe:
            self._pending_updates.append(
                SlamUpdate(
                    seq=frame.seq,
                    timestamp_ns=frame.timestamp_ns,
                    source_seq=frame.seq,
                    source_timestamp_ns=frame.timestamp_ns,
                    is_keyframe=False,
                    keyframe_index=None,
                    num_dense_points=self._num_dense_points,
                )
            )
            return

        import torch  # noqa: PLC0415

        self._accepted_keyframe_timestamps_s.append(frame.timestamp_ns / 1e9)
        value = {
            "rgb": prepared_frame.rgb_tensor.unsqueeze(0).to(self._slam.device),
            "shape": torch.tensor(prepared_frame.rgb_tensor.shape[1:3]).unsqueeze(0),
            "gray": grayscale,
            "view_name": f"frame_{self._accepted_keyframe_count:06d}",
        }
        self._slam.step(value)
        update = self._build_live_update(
            seq=frame.seq,
            timestamp_ns=frame.timestamp_ns,
            view_index=self._accepted_keyframe_count,
            image_rgb=prepared_frame.image_rgb,
        )
        update.is_keyframe = True
        update.keyframe_index = self._accepted_keyframe_count
        self._accepted_keyframe_count += 1
        self._pending_updates.append(update)

    def try_get_updates(self) -> list[SlamUpdate]:
        """Retrieve and clear any pending incremental SLAM updates."""
        updates = self._pending_updates
        self._pending_updates = []
        return updates

    def close(self) -> SlamArtifacts:
        """Persist upstream outputs and convert to canonical repository artifacts."""
        run_paths = RunArtifactPaths.build(self._artifact_root)
        native_output_dir = run_paths.native_output_dir
        native_output_dir.mkdir(parents=True, exist_ok=True)
        try:
            self._slam.save_data_all(str(native_output_dir), save_images=False, save_depths=False)
        except Exception as exc:
            raise RuntimeError(
                f"ViSTA-SLAM failed to export artifacts. "
                f"The sequence ({self._source_frame_count} frames, {self._accepted_keyframe_count} keyframes) "
                "may have been too short to initialize the pose graph."
            ) from exc

        self._console.info(
            "ViSTA-SLAM session closed after %d frames; native outputs in '%s'.",
            self._source_frame_count,
            native_output_dir,
        )
        return build_vista_artifacts(
            native_output_dir=native_output_dir,
            artifact_root=self._artifact_root,
            output_policy=self._output_policy,
            timestamps_s=self._accepted_keyframe_timestamps_s,
        )

    def _build_live_update(
        self,
        *,
        seq: int,
        timestamp_ns: int,
        view_index: int,
        image_rgb: np.ndarray,
    ) -> SlamUpdate:
        """Read one upstream view and convert it into live repo telemetry.

        The returned update intentionally keeps ViSTA's native semantics:

        - `pose` is the upstream `T_world_camera` estimate;
        - `depth_map` is the scaled depth image from `get_view(...)`;
        - `pointmap` is the scaled camera-local pointmap from
          `get_pointmap_vis(...)`;
        - `image_rgb`, `depth_map`, `camera_intrinsics`, and `pointmap` all
          share the ViSTA-preprocessed model raster instead of the original
          source-frame raster.
        """
        try:
            view = self._slam.get_view(
                view_index,
                filter_outlier=False,
                return_pose=True,
                return_depth=True,
                return_intri=True,
            )
        except (IndexError, KeyError, ValueError):
            if not self._live_preview_wait_logged:
                self._console.info("ViSTA-SLAM live preview is not ready yet; waiting for the pose graph to populate.")
                self._live_preview_wait_logged = True
            return SlamUpdate(
                seq=seq,
                timestamp_ns=timestamp_ns,
                source_seq=seq,
                source_timestamp_ns=timestamp_ns,
                is_keyframe=True,
                keyframe_index=view_index,
                num_sparse_points=0,
                num_dense_points=self._num_dense_points,
            )
        pose = _frame_transform_from_vista_pose(vista_numpy_array(view.pose, dtype=np.float64))
        depth_map = vista_numpy_array(view.depth, dtype=np.float32)
        camera_intrinsics = CameraIntrinsics.from_matrix(
            vista_numpy_array(view.intri, dtype=np.float64),
            width_px=int(image_rgb.shape[1]),
            height_px=int(image_rgb.shape[0]),
        )
        try:
            preview_rgb, pointmap = self._slam.get_pointmap_vis(view_index)
        except (IndexError, KeyError, ValueError):
            preview_rgb = None
            pointmap = None
        pointmap = _build_live_pointmap(pointmap)
        valid_dense_points = _count_valid_pointmap_points(pointmap)
        pointmap_warning = _build_pointmap_warning(
            pointmap=pointmap,
            valid_dense_points=valid_dense_points,
            emit_dense_points=self._output_policy.emit_dense_points,
            source_seq=seq,
            keyframe_index=view_index,
        )
        self._num_dense_points += valid_dense_points
        self._live_preview_wait_logged = False
        return SlamUpdate(
            seq=seq,
            timestamp_ns=timestamp_ns,
            source_seq=seq,
            source_timestamp_ns=timestamp_ns,
            pose=pose,
            is_keyframe=True,
            keyframe_index=view_index,
            pose_updated=True,
            num_sparse_points=0,
            num_dense_points=self._num_dense_points,
            pointmap=pointmap if self._output_policy.emit_dense_points else None,
            camera_intrinsics=camera_intrinsics,
            image_rgb=np.asarray(image_rgb, dtype=np.uint8).copy(),
            depth_map=depth_map,
            preview_rgb=None if preview_rgb is None else np.asarray(preview_rgb, dtype=np.uint8),
            backend_warnings=[] if pointmap_warning is None else [pointmap_warning],
        )


def _build_live_pointmap(view: np.ndarray | None) -> np.ndarray | None:
    """Normalize one upstream ViSTA pointmap payload without changing semantics.

    The returned array is still a scaled camera-local pointmap in ViSTA's RDF
    camera basis. This helper performs dtype normalization only.
    """
    if view is None:
        return None
    return vista_numpy_array(view, dtype=np.float32)


def _count_valid_pointmap_points(pointmap: np.ndarray | None) -> int:
    """Count valid metric points in one pointmap."""
    if pointmap is None:
        return 0
    depth = np.asarray(pointmap[..., 2], dtype=np.float32)
    return int(np.count_nonzero(np.isfinite(depth) & (depth > 0.0)))


def _build_pointmap_warning(
    *,
    pointmap: np.ndarray | None,
    valid_dense_points: int,
    emit_dense_points: bool,
    source_seq: int,
    keyframe_index: int,
) -> str | None:
    """Describe a non-fatal pointmap issue for one accepted keyframe."""
    if not emit_dense_points:
        return None
    if pointmap is None:
        return (
            "ViSTA-SLAM accepted a keyframe without a dense pointmap for "
            f"source_seq={source_seq}, keyframe_index={keyframe_index}."
        )
    if valid_dense_points == 0:
        return (
            "ViSTA-SLAM accepted a keyframe whose dense pointmap contained no valid finite "
            f"z>0 points for source_seq={source_seq}, keyframe_index={keyframe_index}."
        )
    return None


def create_vista_session(
    *,
    config: VistaSlamBackendConfig,
    path_config: PathConfig,
    console: Console,
    artifact_root: Path,
    output_policy: SlamOutputPolicy,
    live_mode: bool,
) -> VistaSlamSession:
    """Construct one fully-wired ViSTA session from repo config and paths.

    This helper centralizes the last step of wrapper assembly so both the
    adapter's offline and streaming paths share the same normalized runtime
    wiring.
    """
    runtime = build_vista_runtime_components(
        config=config,
        path_config=path_config,
        console=console,
        live_mode=live_mode,
    )
    return VistaSlamSession(
        slam=runtime.slam,
        flow_tracker=runtime.flow_tracker,
        frame_preprocessor=runtime.frame_preprocessor,
        artifact_root=artifact_root,
        output_policy=output_policy,
        console=console,
    )


__all__ = ["VistaSlamSession", "create_vista_session"]
