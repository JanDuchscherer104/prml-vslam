"""Source-owned file-backed observation sequence loading.

The source reads durable ``observation_sequence.v1`` indexes and resolves
RGB/depth payload paths into normalized :class:`Observation` objects. It
keeps source materialization mechanics separate from reconstruction backends.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import cv2
import numpy as np

from prml_vslam.interfaces import (
    Observation,
    ObservationIndexEntry,
    ObservationSequenceIndex,
    ObservationSequenceRef,
)
from prml_vslam.sources.replay.video import iter_rgb_video_frames


class FileObservationSequenceLoader:
    """Open a durable observation sequence index from local files.

    The source validates that the referenced index matches the sequence ref
    before yielding observations, so reconstruction backends can trust source
    id, sequence id, observation count, and payload-root semantics.
    """

    def __init__(self, sequence_ref: ObservationSequenceRef) -> None:
        self._sequence_ref = sequence_ref

    @property
    def label(self) -> str:
        """Return the compact source label used in logs and diagnostics."""
        return f"{self._sequence_ref.source_id}:{self._sequence_ref.sequence_id}"

    def iter_observations(self) -> Iterator[Observation]:
        """Yield observations by resolving payload paths from the sequence ref.

        RGB payloads are optional; depth payloads are required and converted to
        meters with each row's scale factor before constructing the DTO.
        """
        index = load_observation_sequence_index(self._sequence_ref.index_path)
        _validate_index_matches_ref(index, self._sequence_ref)
        video_frames = _video_frames_by_row(index.rows, self._sequence_ref)
        for row in index.rows:
            image_rgb = video_frames.get(row.seq)
            if image_rgb is None and row.rgb_path is not None:
                image_rgb = _load_rgb(_resolve_payload(row.rgb_path, self._sequence_ref))
            if row.depth_path is None:
                raise ValueError(f"Observation seq={row.seq} is missing a depth payload.")
            depth_map_m = _load_depth(_resolve_payload(row.depth_path, self._sequence_ref)) * row.depth_scale_to_m
            yield Observation(
                seq=row.seq,
                timestamp_ns=row.timestamp_ns,
                T_world_camera=row.T_world_camera,
                intrinsics=row.intrinsics,
                rgb=image_rgb,
                depth_m=depth_map_m.astype(np.float32, copy=False),
                provenance=row.provenance,
            )


def load_observation_sequence_index(path: Path) -> ObservationSequenceIndex:
    """Load and validate one durable observation sequence index.

    The JSON payload is validated through the shared interface model so schema
    errors surface before reconstruction begins.
    """
    if not path.exists():
        raise FileNotFoundError(f"Observation index does not exist: {path}")
    return ObservationSequenceIndex.model_validate(json.loads(path.read_text(encoding="utf-8")))


def _validate_index_matches_ref(index: ObservationSequenceIndex, ref: ObservationSequenceRef) -> None:
    if index.format_version != ref.format_version:
        raise ValueError(
            f"Observation index format {index.format_version!r} does not match ref {ref.format_version!r}."
        )
    if index.source_id != ref.source_id:
        raise ValueError(f"Observation index source_id {index.source_id!r} does not match ref {ref.source_id!r}.")
    if index.sequence_id != ref.sequence_id:
        raise ValueError(f"Observation index sequence_id {index.sequence_id!r} does not match ref {ref.sequence_id!r}.")
    if index.observation_count != ref.observation_count:
        raise ValueError(
            f"Observation index observation_count={index.observation_count} does not match ref "
            f"observation_count={ref.observation_count}."
        )
    if ref.rgb_video_path is None and any(row.rgb_path is None for row in index.rows):
        raise ValueError("Observation rows without rgb_path require ObservationSequenceRef.rgb_video_path.")


def _video_frames_by_row(
    rows: list[ObservationIndexEntry],
    ref: ObservationSequenceRef,
) -> dict[int, np.ndarray]:
    if ref.rgb_video_path is None:
        return {}
    video_path = _resolve_payload(ref.rgb_video_path, ref)
    frame_indices = [row.rgb_video_frame_index if row.rgb_video_frame_index is not None else row.seq for row in rows]
    frames = list(iter_rgb_video_frames(video_path, frame_indices))
    if len(frames) != len(frame_indices):
        raise RuntimeError(
            f"Video observation payload '{video_path}' yielded {len(frames)} frame(s) for "
            f"{len(frame_indices)} observation row(s)."
        )
    return {row.seq: frame for row, frame in zip(rows, frames, strict=True)}


def _resolve_payload(path: Path, ref: ObservationSequenceRef) -> Path:
    return path if path.is_absolute() else ref.payload_root / path


def _load_rgb(path: Path) -> np.ndarray:
    if not path.exists():
        raise FileNotFoundError(f"RGB payload does not exist: {path}")
    if path.suffix == ".npy":
        return np.asarray(np.load(path), dtype=np.uint8)
    image_bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image_bgr is None:
        raise FileNotFoundError(f"Cannot read RGB payload: {path}")
    return np.asarray(cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB), dtype=np.uint8)


def _load_depth(path: Path) -> np.ndarray:
    if not path.exists():
        raise FileNotFoundError(f"Depth payload does not exist: {path}")
    if path.suffix == ".npy":
        return np.asarray(np.load(path), dtype=np.float32)
    depth = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if depth is None:
        raise FileNotFoundError(f"Cannot read depth payload: {path}")
    return np.asarray(depth, dtype=np.float32)


__all__ = ["FileObservationSequenceLoader", "load_observation_sequence_index"]
