from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from prml_vslam.pipeline.contracts import SequenceManifest

if TYPE_CHECKING:
    from .advio_sequence import AdvioSequence

SequenceManifestType = SequenceManifest


def build_advio_sequence_manifest(sequence: AdvioSequence, *, output_dir: Path | None = None) -> SequenceManifest:
    sample = sequence.load_offline_sample()
    evaluation_dir = sample.paths.sequence_dir / "evaluation" if output_dir is None else output_dir
    evaluation_dir.mkdir(parents=True, exist_ok=True)
    reference_tum_path = _ensure_tum(sequence.write_ground_truth_tum, evaluation_dir / "ground_truth.tum")
    arcore_tum_path = _ensure_tum(sequence.write_arcore_tum, evaluation_dir / "arcore.tum")
    return SequenceManifest(
        sequence_id=sample.sequence_name,
        video_path=sample.paths.video_path,
        timestamps_path=sample.paths.frame_timestamps_path,
        intrinsics_path=sample.paths.calibration_path,
        reference_tum_path=reference_tum_path,
        arcore_tum_path=arcore_tum_path,
    )


def _ensure_tum(write_tum: Callable[[Path], Path], target_path: Path) -> Path:
    if not target_path.exists():
        write_tum(target_path)
    return target_path
