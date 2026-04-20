"""Canonical offline-ingest helpers for the pipeline.

This module materializes the normalized on-disk inputs that later pipeline
stages consume. It bridges source-owned manifests into the canonical
``input/`` layout represented by :class:`prml_vslam.utils.RunArtifactPaths`.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from prml_vslam.pipeline.contracts.request import DatasetSourceSpec, PipelineMode, RunRequest, VideoSourceSpec
from prml_vslam.pipeline.contracts.sequence import SequenceManifest
from prml_vslam.utils import Console, RunArtifactPaths
from prml_vslam.utils.video_frames import extract_video_frames

_CONSOLE = Console(__name__).child("materialize_offline_manifest")


def materialize_offline_manifest(
    *,
    request: RunRequest,
    prepared_manifest: SequenceManifest,
    run_paths: RunArtifactPaths,
) -> SequenceManifest:
    """Materialize the canonical offline ingest boundary for one run.

    This function is the main handoff from source preparation into pipeline
    execution. It ensures the returned :class:`SequenceManifest` points at the
    canonical run-owned input layout even when the prepared source came from a
    raw video or a dataset-owned manifest.
    """
    _CONSOLE.info(
        "Materializing offline manifest for sequence '%s'.",
        prepared_manifest.sequence_id,
    )
    rotation_degrees = 0
    rgb_dir = prepared_manifest.rgb_dir
    timestamps_path = prepared_manifest.timestamps_path
    intrinsics_path = prepared_manifest.intrinsics_path

    if prepared_manifest.video_path is not None and rgb_dir is None:
        frame_stride = _frame_stride_for_request(request)
        max_frames = _max_frames_for_request(request)
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
            _write_json_payload(
                rgb_dir / ".ingest_metadata.json",
                {
                    "video_path": str(prepared_manifest.video_path.resolve()),
                    "frame_stride": frame_stride,
                    "max_frames": max_frames,
                },
            )

        timestamps_ns = _resolve_timestamps_ns(
            source_path=_preferred_timestamps_source(
                prepared_manifest=prepared_manifest,
                run_paths=run_paths,
                cached_rgb_dir=cached_rgb_dir,
            ),
            frame_stride=frame_stride,
            fallback_timestamps_ns=[] if cached_rgb_dir is not None else extracted.timestamps_ns,
        )
        if prepared_manifest.timestamps_path is not None and prepared_manifest.timestamps_path.exists():
            _CONSOLE.debug("Using prepared timestamps from '%s'.", prepared_manifest.timestamps_path)
        elif cached_rgb_dir is not None and run_paths.input_timestamps_path.exists():
            _CONSOLE.debug("Using cached canonical timestamps from '%s'.", run_paths.input_timestamps_path)
        else:
            _CONSOLE.debug("Using extracted fallback timestamps for sequence '%s'.", prepared_manifest.sequence_id)
        # If we reused frames, we expect the timestamps to already be materialized if they were part of a previous run.
        # However, materialize_offline_manifest always ensures the input/ directory is populated.
        timestamps_path = _write_json_payload(
            run_paths.input_timestamps_path,
            {"timestamps_ns": timestamps_ns, "frame_stride": frame_stride},
        )

    if intrinsics_path is not None:
        run_paths.input_intrinsics_path.parent.mkdir(parents=True, exist_ok=True)
        if intrinsics_path.resolve() != run_paths.input_intrinsics_path.resolve():
            shutil.copyfile(intrinsics_path, run_paths.input_intrinsics_path)
            _CONSOLE.debug("Copied intrinsics into canonical path '%s'.", run_paths.input_intrinsics_path)
        else:
            _CONSOLE.debug("Intrinsics already at canonical path '%s'.", intrinsics_path)
        intrinsics_path = run_paths.input_intrinsics_path.resolve()

    rotation_metadata_path = _write_json_payload(
        run_paths.input_rotation_metadata_path,
        {"rotation_degrees": rotation_degrees},
    )
    _CONSOLE.debug("Wrote rotation metadata to '%s'.", rotation_metadata_path)

    return prepared_manifest.model_copy(
        update={
            "rgb_dir": rgb_dir,
            "timestamps_path": timestamps_path,
            "intrinsics_path": intrinsics_path,
            "rotation_metadata_path": rotation_metadata_path,
        }
    )


def _frame_stride_for_request(request: RunRequest) -> int:
    match request.source:
        case VideoSourceSpec(frame_stride=frame_stride):
            return frame_stride
        case DatasetSourceSpec():
            return 1
        case _:
            return 1


def _max_frames_for_request(request: RunRequest) -> int | None:
    if request.mode is not PipelineMode.STREAMING:
        return None
    return request.slam.backend.max_frames


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
    rows = []
    for line in source_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        first_field = line.split(",", maxsplit=1)[0].strip()
        rows.append(first_field)
    if not rows:
        return fallback_timestamps_ns
    values = [int(round(float(value) * 1e9)) for value in rows]
    return values[::frame_stride]


def _preferred_timestamps_source(
    *,
    prepared_manifest: SequenceManifest,
    run_paths: RunArtifactPaths,
    cached_rgb_dir: Path | None,
) -> Path | None:
    if prepared_manifest.timestamps_path is not None and prepared_manifest.timestamps_path.exists():
        return prepared_manifest.timestamps_path
    if cached_rgb_dir is not None and run_paths.input_timestamps_path.exists():
        return run_paths.input_timestamps_path
    return prepared_manifest.timestamps_path


def _write_json_payload(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path.resolve()


__all__ = ["materialize_offline_manifest"]
