"""Source-owned manifest materialization and artifact projection helpers."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from prml_vslam.interfaces.artifacts import ArtifactRef, artifact_ref
from prml_vslam.pipeline.contracts.mode import PipelineMode
from prml_vslam.sources.contracts import SequenceManifest, SourceStageOutput
from prml_vslam.sources.visualization import (
    observation_sequence_artifact_key,
    reference_cloud_artifact_key,
    reference_cloud_metadata_artifact_key,
    reference_point_cloud_sequence_index_artifact_key,
    reference_point_cloud_sequence_payload_artifact_key,
    reference_point_cloud_sequence_trajectory_artifact_key,
    reference_trajectory_artifact_key,
)
from prml_vslam.utils import Console, PathConfig, RunArtifactPaths
from prml_vslam.utils.serialization import write_json
from prml_vslam.utils.video_frames import extract_video_frames

if TYPE_CHECKING:
    from prml_vslam.sources.runtime import SourceStageInput

_CONSOLE = Console(__name__).child("SourceMaterialization")


class VideoOfflineSequenceSource:
    """Adapt a raw video path into the normalized offline source seam."""

    def __init__(self, *, path_config: PathConfig, video_path: Path) -> None:
        self._path_config = path_config
        self._video_path = video_path

    @property
    def label(self) -> str:
        """Return the compact user-facing label for this source."""
        return f"Video '{self._video_path.name}'"

    def prepare_sequence_manifest(self, output_dir: Path) -> SequenceManifest:
        """Resolve the video path and return the minimal normalized manifest."""
        del output_dir
        resolved_video_path = self._path_config.resolve_video_path(self._video_path, must_exist=True)
        return SequenceManifest(
            sequence_id=resolved_video_path.stem,
            video_path=resolved_video_path,
        )


def source_artifacts(*, run_paths: RunArtifactPaths, output: SourceStageOutput) -> dict[str, ArtifactRef]:
    """Project source output contracts into durable stage artifact refs."""
    sequence_manifest = output.sequence_manifest
    artifacts = {
        "sequence_manifest": artifact_ref(run_paths.sequence_manifest_path, kind="json"),
    }
    for key, path, kind in (
        ("rgb_dir", sequence_manifest.rgb_dir, "dir"),
        ("timestamps", sequence_manifest.timestamps_path, "json"),
        ("intrinsics", sequence_manifest.intrinsics_path, "yaml"),
        ("rotation_metadata", sequence_manifest.rotation_metadata_path, "json"),
    ):
        if path is not None:
            artifacts[key] = artifact_ref(path, kind=kind)
    if output.benchmark_inputs is not None:
        artifacts["benchmark_inputs"] = artifact_ref(run_paths.benchmark_inputs_path, kind="json")
        for reference in output.benchmark_inputs.reference_trajectories:
            artifacts[reference_trajectory_artifact_key(reference)] = artifact_ref(reference.path, kind="tum")
        for reference in output.benchmark_inputs.reference_clouds:
            artifacts[reference_cloud_artifact_key(reference)] = artifact_ref(reference.path, kind="ply")
            artifacts[reference_cloud_metadata_artifact_key(reference)] = artifact_ref(
                reference.metadata_path,
                kind="json",
            )
        for reference in output.benchmark_inputs.reference_point_cloud_sequences:
            for key_func, path, kind in (
                (reference_point_cloud_sequence_index_artifact_key, reference.index_path, "csv"),
                (reference_point_cloud_sequence_trajectory_artifact_key, reference.trajectory_path, "tum"),
                (reference_point_cloud_sequence_payload_artifact_key, reference.payload_root, "dir"),
            ):
                artifacts[key_func(reference)] = artifact_ref(path, kind=kind)
        for reference in output.benchmark_inputs.observation_sequences:
            artifacts[observation_sequence_artifact_key(reference)] = artifact_ref(
                reference.index_path,
                kind="observation_sequence",
            )
    return artifacts


def materialize_manifest(
    *,
    input_payload: SourceStageInput,
    prepared_manifest: SequenceManifest,
    run_paths: RunArtifactPaths,
) -> SequenceManifest:
    """Materialize the run-owned source manifest for this source stage."""
    _CONSOLE.info("Materializing source manifest for sequence '%s'.", prepared_manifest.sequence_id)
    rotation_degrees = 0
    rgb_dir = prepared_manifest.rgb_dir
    timestamps_path = prepared_manifest.timestamps_path
    intrinsics_path = prepared_manifest.intrinsics_path
    frame_stride = input_payload.frame_stride if prepared_manifest.video_path is not None else 1
    cached_rgb_dir: Path | None = None
    fallback_timestamps_ns: list[int] = []

    if prepared_manifest.video_path is not None and rgb_dir is None:
        max_frames = input_payload.streaming_max_frames if input_payload.mode is PipelineMode.STREAMING else None
        cached_rgb_dir = _check_extraction_cache(
            video_path=prepared_manifest.video_path,
            output_dir=run_paths.input_frames_dir,
            frame_stride=frame_stride,
            max_frames=max_frames,
        )
        if cached_rgb_dir is not None:
            _CONSOLE.info(
                "Reusing extracted frames from '%s' with frame_stride=%d and max_frames=%s.",
                cached_rgb_dir,
                frame_stride,
                max_frames,
            )
            rgb_dir = cached_rgb_dir
        else:
            _CONSOLE.info(
                "Extracting frames from '%s' into '%s' with frame_stride=%d and max_frames=%s.",
                prepared_manifest.video_path,
                run_paths.input_frames_dir,
                frame_stride,
                max_frames,
            )
            extracted = extract_video_frames(
                video_path=prepared_manifest.video_path,
                output_dir=run_paths.input_frames_dir,
                frame_stride=frame_stride,
                max_frames=max_frames,
            )
            rgb_dir = extracted.rgb_dir
            write_json(
                rgb_dir / ".ingest_metadata.json",
                {
                    "video_path": str(prepared_manifest.video_path.resolve()),
                    "frame_stride": frame_stride,
                    "max_frames": max_frames,
                },
            )

        fallback_timestamps_ns = [] if cached_rgb_dir is not None else extracted.timestamps_ns

    timestamps_source = prepared_manifest.timestamps_path
    if timestamps_source is None and cached_rgb_dir is not None and run_paths.input_timestamps_path.exists():
        timestamps_source = run_paths.input_timestamps_path
    elif timestamps_source is not None and not timestamps_source.exists():
        timestamps_source = run_paths.input_timestamps_path if cached_rgb_dir is not None else timestamps_source
    if (timestamps_source is not None and timestamps_source.exists()) or fallback_timestamps_ns:
        timestamps_ns = _resolve_timestamps_ns(
            source_path=timestamps_source,
            frame_stride=frame_stride,
            fallback_timestamps_ns=fallback_timestamps_ns,
        )
        write_json(run_paths.input_timestamps_path, {"timestamps_ns": timestamps_ns, "frame_stride": frame_stride})
        timestamps_path = run_paths.input_timestamps_path.resolve()

    if intrinsics_path is not None:
        run_paths.input_intrinsics_path.parent.mkdir(parents=True, exist_ok=True)
        if intrinsics_path.resolve() != run_paths.input_intrinsics_path.resolve():
            shutil.copyfile(intrinsics_path, run_paths.input_intrinsics_path)
        intrinsics_path = run_paths.input_intrinsics_path.resolve()

    write_json(run_paths.input_rotation_metadata_path, {"rotation_degrees": rotation_degrees})
    rotation_metadata_path = run_paths.input_rotation_metadata_path.resolve()

    return prepared_manifest.model_copy(
        update={
            "rgb_dir": rgb_dir,
            "timestamps_path": timestamps_path,
            "intrinsics_path": intrinsics_path,
            "rotation_metadata_path": rotation_metadata_path,
        }
    )


def _check_extraction_cache(
    *,
    video_path: Path,
    output_dir: Path,
    frame_stride: int,
    max_frames: int | None,
) -> Path | None:
    metadata_path = output_dir / ".ingest_metadata.json"
    if not metadata_path.exists():
        return None
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if (
            metadata.get("video_path") == str(video_path.resolve())
            and metadata.get("frame_stride") == frame_stride
            and metadata.get("max_frames") == max_frames
            and any(output_dir.glob("*.png"))
        ):
            return output_dir.resolve()
    except (json.JSONDecodeError, KeyError):
        pass
    return None


def _resolve_timestamps_ns(
    *,
    source_path: Path | None,
    frame_stride: int,
    fallback_timestamps_ns: list[int],
) -> list[int]:
    if source_path is None or not source_path.exists():
        return fallback_timestamps_ns
    suffix = source_path.suffix.lower()
    if suffix == ".json":
        payload = json.loads(source_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and isinstance(payload.get("timestamps_ns"), list):
            values = [int(value) for value in payload["timestamps_ns"]]
            return values[::frame_stride]
        raise RuntimeError(f"Expected normalized timestamps JSON with a `timestamps_ns` list at '{source_path}'.")
    rows = []
    for line in source_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        first_field = stripped.split(",", maxsplit=1)[0].strip() if "," in stripped else stripped.split()[0]
        rows.append(first_field)
    if not rows:
        return fallback_timestamps_ns
    values = [int(round(float(value) * 1e9)) for value in rows]
    return values[::frame_stride]
