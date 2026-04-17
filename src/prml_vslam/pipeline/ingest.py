"""Canonical ingest helpers for offline execution."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import cv2

from prml_vslam.pipeline.contracts.request import DatasetSourceSpec, RunRequest, VideoSourceSpec
from prml_vslam.pipeline.contracts.sequence import SequenceManifest
from prml_vslam.utils import RunArtifactPaths


def materialize_offline_manifest(
    *,
    request: RunRequest,
    prepared_manifest: SequenceManifest,
    run_paths: RunArtifactPaths,
) -> SequenceManifest:
    """Materialize the canonical offline ingest boundary for one run."""
    rotation_degrees = 0
    rgb_dir = prepared_manifest.rgb_dir
    timestamps_path = prepared_manifest.timestamps_path
    intrinsics_path = prepared_manifest.intrinsics_path

    if prepared_manifest.video_path is not None and rgb_dir is None:
        frame_stride = _frame_stride_for_request(request)
        cached_rgb_dir = _check_extraction_cache(
            video_path=prepared_manifest.video_path,
            output_dir=run_paths.input_frames_dir,
            frame_stride=frame_stride,
        )
        if cached_rgb_dir is not None:
            rgb_dir = cached_rgb_dir
        else:
            extracted = _extract_video_frames(
                video_path=prepared_manifest.video_path,
                output_dir=run_paths.input_frames_dir,
                frame_stride=frame_stride,
            )
            rgb_dir = extracted["rgb_dir"]
            _write_json_payload(
                rgb_dir / ".ingest_metadata.json",
                {"video_path": str(prepared_manifest.video_path.resolve()), "frame_stride": frame_stride},
            )

        timestamps_ns = _resolve_timestamps_ns(
            source_path=_preferred_timestamps_source(
                prepared_manifest=prepared_manifest,
                run_paths=run_paths,
                cached_rgb_dir=cached_rgb_dir,
            ),
            frame_stride=frame_stride,
            fallback_timestamps_ns=[] if cached_rgb_dir is not None else extracted["timestamps_ns"],
        )
        # If we reused frames, we expect the timestamps to already be materialized if they were part of a previous run.
        # However, materialize_offline_manifest always ensures the input/ directory is populated.
        timestamps_path = _write_json_payload(
            run_paths.input_timestamps_path,
            {"timestamps_ns": timestamps_ns, "frame_stride": frame_stride},
        )

    if intrinsics_path is not None:
        intrinsics_path = _copy_if_needed(intrinsics_path, run_paths.input_intrinsics_path)

    rotation_metadata_path = _write_json_payload(
        run_paths.input_rotation_metadata_path,
        {"rotation_degrees": rotation_degrees},
    )

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


def _check_extraction_cache(*, video_path: Path, output_dir: Path, frame_stride: int) -> Path | None:
    metadata_path = output_dir / ".ingest_metadata.json"
    if not metadata_path.exists():
        return None
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if (
            metadata.get("video_path") == str(video_path.resolve())
            and metadata.get("frame_stride") == frame_stride
            and any(output_dir.glob("*.png"))
        ):
            return output_dir.resolve()
    except (json.JSONDecodeError, KeyError):
        pass
    return None


def _extract_video_frames(*, video_path: Path, output_dir: Path, frame_stride: int) -> dict[str, object]:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise FileNotFoundError(f"Cannot open video: {video_path}")
    timestamps_ns: list[int] = []
    frame_index = 0
    written_index = 0
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    while True:
        ok, frame_bgr = capture.read()
        if not ok:
            break
        if frame_index % frame_stride != 0:
            frame_index += 1
            continue
        timestamp_ns = int(round(frame_index / fps * 1e9)) if fps > 0.0 else int(frame_index * 1e9 / 30.0)
        frame_path = output_dir / f"{written_index:06d}.png"
        if not cv2.imwrite(str(frame_path), frame_bgr):
            raise RuntimeError(f"Failed to write extracted frame to '{frame_path}'.")
        timestamps_ns.append(timestamp_ns)
        written_index += 1
        frame_index += 1
    capture.release()
    return {"rgb_dir": output_dir.resolve(), "timestamps_ns": timestamps_ns}


def _copy_if_needed(source_path: Path, target_path: Path) -> Path:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if source_path.resolve() == target_path.resolve():
        return target_path.resolve()
    shutil.copy2(source_path, target_path)
    return target_path.resolve()


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
