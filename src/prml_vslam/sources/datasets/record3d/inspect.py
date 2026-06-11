"""CLI smoke helper for local Record3D `.r3d` archives."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from prml_vslam.sources import FileObservationSequenceLoader
from prml_vslam.sources.datasets.record3d import Record3DSequence, Record3DSequenceConfig


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect and materialize one Record3D .r3d archive.")
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--sequence-id", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    sequence = Record3DSequence(
        config=Record3DSequenceConfig(dataset_root=args.dataset_root, sequence_id=args.sequence_id)
    )
    sample = sequence.load_offline_sample()
    manifest = sequence.to_sequence_manifest(output_dir=args.output_dir / "manifest")
    benchmark_inputs = sequence.to_benchmark_inputs(output_dir=args.output_dir / "benchmark")
    observations = list(FileObservationSequenceLoader(benchmark_inputs.observation_sequences[0]).iter_observations())
    payload = {
        "sequence_id": sample.sequence_id,
        "frame_count": len(sample.frames),
        "rgb_size": [sample.metadata.w, sample.metadata.h],
        "depth_size": [sample.metadata.dw, sample.metadata.dh],
        "manifest_rgb_dir": str(manifest.rgb_dir),
        "observation_count": len(observations),
        "first_depth_shape": list(observations[0].depth_m.shape) if observations[0].depth_m is not None else None,
        "reference_cloud_path": str(benchmark_inputs.reference_clouds[0].path),
        "reference_cloud_metadata_path": str(benchmark_inputs.reference_clouds[0].metadata_path),
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
