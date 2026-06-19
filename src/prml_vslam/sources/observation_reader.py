"""Source-owned readers for normalized offline observations."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import cv2
import numpy as np

from prml_vslam.interfaces import Observation, ObservationProvenance
from prml_vslam.sources.contracts import SequenceManifest
from prml_vslam.sources.observation_sequence import load_observation_sequence_index
from prml_vslam.sources.replay.video import iter_rgb_video_frames


def iter_sequence_manifest_observations(
    sequence: SequenceManifest,
    *,
    max_frames: int | None = None,
) -> Iterator[Observation]:
    """Yield RGB observations from a normalized source sequence manifest."""
    rgb_inputs, timestamps_ns, source_frame_indices = _load_manifest_rgb_inputs(
        sequence=sequence, max_frames=max_frames
    )
    provenance = _manifest_provenance(sequence)
    for seq, (rgb_input, timestamp_ns, source_frame_index) in enumerate(
        zip(rgb_inputs, timestamps_ns, source_frame_indices, strict=True)
    ):
        yield Observation(
            seq=seq,
            timestamp_ns=timestamp_ns,
            source_frame_index=source_frame_index,
            rgb=_load_rgb_input(rgb_input),
            provenance=provenance.model_copy(update={"source_frame_index": source_frame_index}),
        )


def _load_manifest_rgb_inputs(
    *,
    sequence: SequenceManifest,
    max_frames: int | None,
) -> tuple[list[Path | np.ndarray], list[int], list[int]]:
    if sequence.timestamps_path is None or not sequence.timestamps_path.exists():
        raise RuntimeError(
            "Offline observation loading requires a normalized `SequenceManifest.timestamps_path`. "
            "Materialize the source stage before invoking downstream offline stages."
        )
    if sequence.observation_index_path is not None:
        return _load_observation_index_rgb_inputs(sequence=sequence, max_frames=max_frames)
    timestamps_ns = _load_timestamps_ns(sequence.timestamps_path)
    if sequence.video_path is not None:
        if not sequence.video_path.exists():
            raise RuntimeError(f"Normalized video input does not exist: {sequence.video_path}")
        source_frame_indices = _manifest_source_frame_indices(sequence, len(timestamps_ns))
        if sequence.source_frame_indices_path is not None and len(timestamps_ns) != len(source_frame_indices):
            timestamps_ns = [timestamps_ns[index] for index in source_frame_indices]
        if max_frames is not None:
            timestamps_ns = timestamps_ns[:max_frames]
            source_frame_indices = source_frame_indices[:max_frames]
        frames: list[Path | np.ndarray] = list(iter_rgb_video_frames(sequence.video_path, source_frame_indices))
        if len(frames) != len(timestamps_ns):
            raise RuntimeError(
                "Normalized offline inputs are inconsistent: "
                f"{len(frames)} video frame(s) from '{sequence.video_path}' but {len(timestamps_ns)} timestamp(s) "
                f"in '{sequence.timestamps_path}'."
            )
        return frames, timestamps_ns, source_frame_indices
    if sequence.rgb_dir is None or not sequence.rgb_dir.exists():
        raise RuntimeError(
            "Offline observation loading requires either `SequenceManifest.video_path` or `SequenceManifest.rgb_dir`. "
            "Materialize the source stage before invoking downstream offline stages."
        )
    image_paths: list[Path | np.ndarray] = sorted(sequence.rgb_dir.glob("*.png"))
    if sequence.source_frame_indices_path is None:
        source_frame_indices = list(range(len(image_paths)))
    else:
        source_frame_indices = _load_source_frame_indices(sequence.source_frame_indices_path)
        image_paths = [image_paths[index] for index in source_frame_indices]
        timestamps_ns = _select_timestamps_for_indices(
            timestamps_ns=timestamps_ns,
            source_frame_indices=source_frame_indices,
            timestamps_path=sequence.timestamps_path,
        )
    if not image_paths:
        raise RuntimeError(f"Normalized input directory '{sequence.rgb_dir}' does not contain any PNG frames.")
    if max_frames is not None:
        image_paths = image_paths[:max_frames]
        timestamps_ns = timestamps_ns[:max_frames]
        source_frame_indices = source_frame_indices[:max_frames]
    if len(timestamps_ns) != len(image_paths):
        raise RuntimeError(
            "Normalized offline inputs are inconsistent: "
            f"{len(image_paths)} PNG frames in '{sequence.rgb_dir}' but {len(timestamps_ns)} timestamps in "
            f"'{sequence.timestamps_path}'."
        )
    return image_paths, timestamps_ns, source_frame_indices


def _load_observation_index_rgb_inputs(
    *,
    sequence: SequenceManifest,
    max_frames: int | None,
) -> tuple[list[Path | np.ndarray], list[int], list[int]]:
    if sequence.observation_index_path is None or not sequence.observation_index_path.exists():
        raise RuntimeError(f"Normalized observation index does not exist: {sequence.observation_index_path}")
    if sequence.rgb_dir is None or not sequence.rgb_dir.exists():
        raise RuntimeError(
            "Observation-index-backed offline loading requires `SequenceManifest.rgb_dir` to resolve row payloads."
        )
    rows = load_observation_sequence_index(sequence.observation_index_path).rows
    if max_frames is not None:
        rows = rows[:max_frames]
    image_paths: list[Path | np.ndarray] = []
    timestamps_ns = []
    source_frame_indices = []
    payload_root = sequence.rgb_dir.parent
    for row in rows:
        if row.rgb_path is None:
            raise RuntimeError(f"Observation row seq={row.seq} in '{sequence.observation_index_path}' has no rgb_path.")
        image_paths.append(row.rgb_path if row.rgb_path.is_absolute() else payload_root / row.rgb_path)
        timestamps_ns.append(row.timestamp_ns)
        source_frame_indices.append(
            row.provenance.source_frame_index if row.provenance.source_frame_index is not None else row.seq
        )
    return image_paths, timestamps_ns, source_frame_indices


def _select_timestamps_for_indices(
    *,
    timestamps_ns: list[int],
    source_frame_indices: list[int],
    timestamps_path: Path,
) -> list[int]:
    if len(timestamps_ns) == len(source_frame_indices):
        return timestamps_ns
    try:
        return [timestamps_ns[index] for index in source_frame_indices]
    except IndexError as exc:
        raise RuntimeError(
            "Normalized offline inputs are inconsistent: "
            f"frame-index sidecar references {max(source_frame_indices, default=-1)} but "
            f"'{timestamps_path}' contains {len(timestamps_ns)} timestamp(s)."
        ) from exc


def _manifest_source_frame_indices(sequence: SequenceManifest, frame_count: int) -> list[int]:
    if sequence.source_frame_indices_path is None:
        return list(range(frame_count))
    return _load_source_frame_indices(sequence.source_frame_indices_path)


def _load_timestamps_ns(path: Path) -> list[int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("timestamps_ns"), list):
        raise RuntimeError(
            "Expected normalized timestamps JSON with a `timestamps_ns` list at "
            f"'{path}', got: {type(payload).__name__}."
        )
    return [int(timestamp_ns) for timestamp_ns in payload["timestamps_ns"]]


def _load_source_frame_indices(path: Path) -> list[int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("source_frame_indices"), list):
        raise RuntimeError(
            "Expected normalized frame-index JSON with a `source_frame_indices` list at "
            f"'{path}', got: {type(payload).__name__}."
        )
    return [int(index) for index in payload["source_frame_indices"]]


def _load_rgb_input(rgb: Path | np.ndarray) -> np.ndarray:
    return rgb if isinstance(rgb, np.ndarray) else _load_rgb(rgb)


def _load_rgb(path: Path) -> np.ndarray:
    bgr = cv2.imread(str(path))
    if bgr is None:
        raise RuntimeError(f"Failed to read input frame '{path}'.")
    return np.asarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), dtype=np.uint8)


def _manifest_provenance(sequence: SequenceManifest) -> ObservationProvenance:
    dataset_id = "" if sequence.dataset_id is None else sequence.dataset_id.value
    source_id = dataset_id or "source_manifest"
    pose_source = ""
    if sequence.dataset_serving is not None:
        pose_source = sequence.dataset_serving.pose_source.value
    return ObservationProvenance(
        source_id=source_id,
        dataset_id=dataset_id,
        sequence_id=sequence.sequence_id,
        pose_source=pose_source,
    )


__all__ = ["iter_sequence_manifest_observations"]
