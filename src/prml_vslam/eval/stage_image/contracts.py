"""Image-evaluation stage runtime input contracts."""

from __future__ import annotations

from pathlib import Path

from prml_vslam.eval.render_eval import RenderEvalConfig
from prml_vslam.interfaces.slam import SlamArtifacts
from prml_vslam.utils import BaseData
from prml_vslam.utils.serialization import hash_path


class ImageEvaluationStageInput(BaseData):
    """Inputs required to render and score one run's dense cloud.

    The runtime resolves the cloud, trajectory, intrinsics, and input frames from
    ``artifact_root`` (written by the source and SLAM stages). ``slam`` is carried
    for availability and provenance only.
    """

    artifact_root: Path
    render_config: RenderEvalConfig
    slam: SlamArtifacts
    sequence_manifest_path: Path
    input_timestamps_path: Path
    input_intrinsics_path: Path
    input_frames_dir: Path


def image_evaluation_input_fingerprint_payload(input_payload: ImageEvaluationStageInput) -> dict[str, object]:
    """Return the source and SLAM inputs that define image-evaluation provenance."""
    return {
        "slam_dense": input_payload.slam.dense_points_ply,
        "slam_trajectory": input_payload.slam.trajectory_tum,
        "sequence_manifest": _path_state(input_payload.sequence_manifest_path),
        "input_timestamps": _path_state(input_payload.input_timestamps_path),
        "input_intrinsics": _path_state(input_payload.input_intrinsics_path),
        "input_frames_dir": input_payload.input_frames_dir,
    }


def _path_state(path: Path) -> dict[str, str]:
    return {"path": path.resolve().as_posix(), "fingerprint": hash_path(path)}


__all__ = ["ImageEvaluationStageInput", "image_evaluation_input_fingerprint_payload"]
