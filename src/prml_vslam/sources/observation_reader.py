"""Source-owned readers for normalized offline observations."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import cv2
import numpy as np

from prml_vslam.interfaces import Observation, ObservationProvenance
from prml_vslam.sources.contracts import SequenceManifest


def iter_sequence_manifest_observations(
    sequence: SequenceManifest,
    *,
    max_frames: int | None = None,
) -> Iterator[Observation]:
    """Yield RGB observations from a normalized source sequence manifest."""
    image_paths, timestamps_ns = _load_manifest_rgb_inputs(sequence=sequence, max_frames=max_frames)
    provenance = _manifest_provenance(sequence)
    for seq, (image_path, timestamp_ns) in enumerate(zip(image_paths, timestamps_ns, strict=True)):
        yield Observation(
            seq=seq,
            timestamp_ns=timestamp_ns,
            source_frame_index=seq,
            rgb=_load_rgb(image_path),
            provenance=provenance.model_copy(update={"source_frame_index": seq}),
        )


def _load_manifest_rgb_inputs(
    *,
    sequence: SequenceManifest,
    max_frames: int | None,
) -> tuple[list[Path], list[int]]:
    if sequence.rgb_dir is None or not sequence.rgb_dir.exists():
        raise RuntimeError(
            "Offline observation loading requires a normalized `SequenceManifest.rgb_dir`. "
            "Materialize the source stage before invoking downstream offline stages."
        )
    if sequence.timestamps_path is None or not sequence.timestamps_path.exists():
        raise RuntimeError(
            "Offline observation loading requires a normalized `SequenceManifest.timestamps_path`. "
            "Materialize the source stage before invoking downstream offline stages."
        )
    image_paths = sorted(sequence.rgb_dir.glob("*.png"))
    if not image_paths:
        raise RuntimeError(f"Normalized input directory '{sequence.rgb_dir}' does not contain any PNG frames.")
    timestamps_ns = _load_timestamps_ns(sequence.timestamps_path)
    if max_frames is not None:
        image_paths = image_paths[:max_frames]
        timestamps_ns = timestamps_ns[:max_frames]
    if len(timestamps_ns) != len(image_paths):
        raise RuntimeError(
            "Normalized offline inputs are inconsistent: "
            f"{len(image_paths)} PNG frames in '{sequence.rgb_dir}' but {len(timestamps_ns)} timestamps in "
            f"'{sequence.timestamps_path}'."
        )
    return image_paths, timestamps_ns


def _load_timestamps_ns(path: Path) -> list[int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("timestamps_ns"), list):
        raise RuntimeError(
            "Expected normalized timestamps JSON with a `timestamps_ns` list at "
            f"'{path}', got: {type(payload).__name__}."
        )
    return [int(timestamp_ns) for timestamp_ns in payload["timestamps_ns"]]


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
