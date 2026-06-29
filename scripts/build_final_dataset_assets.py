#!/usr/bin/env python3
"""Generate final-slide dataset summary SVG assets from the normalized datastore."""

from __future__ import annotations

import argparse
import csv
from collections.abc import Sequence
from pathlib import Path

from evo.core.trajectory import PoseTrajectory3D

from prml_vslam.plotting.dataset_summary import (
    build_dataset_summary_bar_svg,
    build_reference_data_svg,
    dataset_summary_chart_variants,
)
from prml_vslam.sources.datasets.contracts import DatasetId
from prml_vslam.sources.datasets.normalized_query import (
    NormalizedDatasetQuery,
    query_normalized_dataset,
)
from prml_vslam.sources.datasets.summary import DatasetObservationSummary, build_dataset_observation_summaries
from prml_vslam.utils import PathConfig
from prml_vslam.utils.geometry import load_point_cloud_ply_with_colors, load_tum_trajectory

_DATASET_IDS = (DatasetId.ADVIO, DatasetId.TUM_RGBD, DatasetId.RECORD3D)


def main() -> None:
    args = _parse_args()
    path_config = PathConfig(root=args.root)
    output_dir = path_config.resolve_repo_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    summaries = build_dataset_observation_summaries(path_config, dataset_ids=_DATASET_IDS, strict=True)
    _write_summary_csv(output_dir / "dataset-summary.csv", summaries)
    _write_summary_bar_variants(output_dir, summaries)

    queries = {dataset_id: query_normalized_dataset(dataset_id, path_config) for dataset_id in _DATASET_IDS}
    _write_reference_svg(
        output_dir / "dataset-gt-advio.svg",
        query=queries[DatasetId.ADVIO],
        title="ADVIO: ground-truth trajectory",
        sequence_id="advio-20",
        trajectory_preference=("Ground truth",),
        include_cloud=False,
        plane_axes=(0, 2),
    )
    _write_reference_svg(
        output_dir / "dataset-gt-tum-rgbd.svg",
        query=queries[DatasetId.TUM_RGBD],
        title="TUM RGB-D: reference cloud + GT",
        sequence_id="freiburg3_large_cabinet",
        trajectory_preference=("Ground truth",),
        include_cloud=True,
        plane_axes=(0, 1),
    )
    _write_reference_svg(
        output_dir / "dataset-gt-record3d.svg",
        query=queries[DatasetId.RECORD3D],
        title="Record3D: LiDAR cloud + ARKit path",
        sequence_id="2026-06-03--18-29-08",
        trajectory_preference=("Arkit", "ARKit"),
        include_cloud=True,
        plane_axes=(0, 1),
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("docs/figures/evidence"),
        help="Repo-relative directory for generated SVG assets.",
    )
    return parser.parse_args()


def _write_summary_csv(path: Path, summaries: Sequence[DatasetObservationSummary]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=("dataset_id", "dataset_label", "sequence_count", "total_duration_s", "average_duration_s"),
        )
        writer.writeheader()
        for summary in summaries:
            writer.writerow(
                {
                    "dataset_id": summary.dataset_id.value,
                    "dataset_label": summary.dataset_label,
                    "sequence_count": summary.sequence_count,
                    "total_duration_s": f"{summary.total_duration_s:.6f}",
                    "average_duration_s": f"{summary.average_duration_s:.6f}",
                }
            )


def _write_summary_bar_variants(output_dir: Path, summaries: Sequence[DatasetObservationSummary]) -> None:
    variants = dataset_summary_chart_variants()
    if len(variants) != 5:
        raise RuntimeError(f"Expected five dataset-summary chart variants, got {len(variants)}.")
    for index, variant in enumerate(variants, start=1):
        svg = build_dataset_summary_bar_svg(summaries, variant=variant)
        (output_dir / f"dataset-summary-bars-{index:02d}-{variant}.svg").write_text(svg, encoding="utf-8")
        if index == 1:
            (output_dir / "dataset-summary-bars.svg").write_text(svg, encoding="utf-8")


def _write_reference_svg(
    path: Path,
    *,
    query: NormalizedDatasetQuery,
    title: str,
    sequence_id: str,
    trajectory_preference: Sequence[str],
    include_cloud: bool,
    plane_axes: tuple[int, int],
) -> None:
    profile_key = query.preferred_profile_key(sequence_id=sequence_id)
    if profile_key is None:
        raise RuntimeError(f"Missing normalized profile for {query.dataset_id.label} sequence '{sequence_id}'.")
    trajectory = _preferred_trajectory(
        query, sequence_id=sequence_id, profile_key=profile_key, names=trajectory_preference
    )
    clouds = []
    if include_cloud:
        for cloud in query.reference_cloud_artifacts(sequence_id=sequence_id, profile_key=profile_key)[:1]:
            points_xyz, colors_rgb = load_point_cloud_ply_with_colors(cloud.path)
            clouds.append((cloud.label, points_xyz, colors_rgb))
    path.write_text(
        build_reference_data_svg(
            title=title,
            trajectories=[trajectory],
            clouds=clouds,
            plane_axes=plane_axes,
        ),
        encoding="utf-8",
    )


def _preferred_trajectory(
    query: NormalizedDatasetQuery,
    *,
    sequence_id: str,
    profile_key: str,
    names: Sequence[str],
) -> tuple[str, PoseTrajectory3D]:
    artifacts = query.trajectory_artifacts(sequence_id=sequence_id, profile_key=profile_key)
    for name in names:
        for artifact in artifacts:
            if name.lower() in artifact.label.lower():
                return (artifact.label, load_tum_trajectory(artifact.path))
    if artifacts:
        artifact = artifacts[0]
        return (artifact.label, load_tum_trajectory(artifact.path))
    raise RuntimeError(f"Missing trajectory artifact for {query.dataset_id.label} sequence '{sequence_id}'.")


if __name__ == "__main__":
    main()
