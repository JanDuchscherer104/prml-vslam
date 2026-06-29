"""Tests for normalized dataset summary aggregation and slide SVG builders."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from prml_vslam.interfaces import (
    ObservationIndexEntry,
    ObservationProvenance,
    ObservationSequenceIndex,
    ObservationSequenceRef,
)
from prml_vslam.plotting.dataset_summary import (
    build_dataset_summary_bar_figure,
    build_dataset_summary_bar_svg,
    dataset_summary_chart_variants,
)
from prml_vslam.sources.contracts import PreparedBenchmarkInputs, SequenceManifest
from prml_vslam.sources.datasets.contracts import DatasetId
from prml_vslam.sources.datasets.normalized_query import NormalizedDatasetQuery, NormalizedSequenceRecord
from prml_vslam.sources.datasets.normalized_store import (
    ENTRY_FILENAME,
    METADATA_LONG_HEADER,
    STATS_LONG_HEADER,
    NormalizedDatasetEntry,
    NormalizedDatasetProfile,
    NormalizedDatasetStore,
)
from prml_vslam.sources.datasets.summary import (
    DatasetObservationSummary,
    summarize_dataset_observations,
)


def test_normalized_store_resolves_legacy_relative_entry_paths(tmp_path: Path) -> None:
    store = NormalizedDatasetStore(store_root=tmp_path / "store" / "record3d", dataset_id=DatasetId.RECORD3D)
    profile = NormalizedDatasetProfile(
        dataset_id=DatasetId.RECORD3D,
        sequence_id="scene-a",
        source_id="record3d_dataset",
        source_profile={},
    )
    entry_root = store.entry_root(profile)
    entry_root.mkdir(parents=True)
    observations_root = entry_root / "observations"
    rgb_dir = observations_root / "rgb"
    rgb_dir.mkdir(parents=True)
    (rgb_dir / "0.png").write_bytes(b"not decoded by this test")
    observation_index_path = observations_root / "index.json"
    observation_index_path.write_text(
        ObservationSequenceIndex(
            source_id="record3d_dataset",
            sequence_id="scene-a",
            observation_count=1,
            rows=[
                ObservationIndexEntry(
                    seq=0,
                    timestamp_ns=0,
                    rgb_path=Path("rgb/0.png"),
                    provenance=ObservationProvenance(dataset_id="record3d", sequence_id="scene-a"),
                )
            ],
        ).model_dump_json(),
        encoding="utf-8",
    )
    (entry_root / "sequence_manifest.json").write_text(
        SequenceManifest(
            sequence_id="scene-a",
            dataset_id=DatasetId.RECORD3D,
            rgb_dir=Path("observations/rgb"),
            observation_index_path=Path("observations/index.json"),
        ).model_dump_json(),
        encoding="utf-8",
    )
    (entry_root / "benchmark_inputs.json").write_text(
        PreparedBenchmarkInputs(
            observation_sequences=[
                ObservationSequenceRef(
                    source_id="record3d_dataset",
                    sequence_id="scene-a",
                    index_path=Path("observations/index.json"),
                    payload_root=Path("observations"),
                    observation_count=1,
                )
            ]
        ).model_dump_json(),
        encoding="utf-8",
    )
    (entry_root / "stats_long.csv").write_text(
        ",".join(STATS_LONG_HEADER)
        + "\nrecord3d,scene-a,"
        + profile.profile_key
        + ",record3d_dataset,observation_sequence,sequence,observation_duration_s,12.5,s\n",
        encoding="utf-8",
    )
    (entry_root / "metadata_long.csv").write_text(",".join(METADATA_LONG_HEADER) + "\n", encoding="utf-8")
    entry = NormalizedDatasetEntry(
        dataset_id=DatasetId.RECORD3D,
        sequence_id="scene-a",
        source_id="record3d_dataset",
        profile_key=profile.profile_key,
        profile=profile.model_dump(mode="json"),
        root=Path("."),
        sequence_manifest_path=Path("sequence_manifest.json"),
        benchmark_inputs_path=Path("benchmark_inputs.json"),
        stats_long_path=Path("stats_long.csv"),
        metadata_long_path=Path("metadata_long.csv"),
    )
    (entry_root / ENTRY_FILENAME).write_text(entry.model_dump_json(), encoding="utf-8")

    loaded = store.load_entry(profile)

    assert loaded.root == entry_root.resolve()
    assert loaded.sequence_manifest_path == (entry_root / "sequence_manifest.json").resolve()
    assert loaded.stats_long_path == (entry_root / "stats_long.csv").resolve()
    assert store.issues() == []


def test_dataset_summary_uses_one_preferred_profile_per_sequence() -> None:
    query = NormalizedDatasetQuery(
        dataset_id=DatasetId.ADVIO,
        records=[
            _record("advio-01", "old", is_default=False),
            _record("advio-01", "default", is_default=True),
            _record("advio-02", "only", is_default=False),
        ],
        issues=[],
        stats_df=pd.DataFrame.from_records(
            [
                _duration_row("advio-01", "old", 100.0),
                _duration_row("advio-01", "default", 40.0),
                _duration_row("advio-02", "only", 20.0),
            ]
        ),
        metadata_df=pd.DataFrame(columns=METADATA_LONG_HEADER),
    )

    summary = summarize_dataset_observations(query, strict=True)

    assert summary.dataset_label == "ADVIO"
    assert summary.sequence_count == 2
    assert summary.total_duration_s == pytest.approx(60.0)
    assert summary.average_duration_s == pytest.approx(30.0)


def test_dataset_summary_bar_svg_contains_three_metrics_and_stable_labels() -> None:
    summaries = [
        DatasetObservationSummary(
            dataset_id=DatasetId.ADVIO,
            dataset_label="ADVIO",
            sequence_count=23,
            total_duration_s=4070.56,
            average_duration_s=176.98,
        ),
        DatasetObservationSummary(
            dataset_id=DatasetId.TUM_RGBD,
            dataset_label="TUM RGB-D",
            sequence_count=19,
            total_duration_s=1176.41,
            average_duration_s=61.92,
        ),
    ]
    figure = build_dataset_summary_bar_figure(summaries)
    svg = build_dataset_summary_bar_svg(summaries)

    assert dataset_summary_chart_variants() == ("clean", "presentation", "minimal", "contrast", "wide")
    assert len(figure.data) == 3
    assert list(figure.data[0].x) == ["ADVIO", "TUM RGB-D"]
    assert list(figure.data[0].text) == ["23", "19"]
    assert list(figure.data[1].text) == ["67.8", "19.6"]
    assert list(figure.data[2].text) == ["177.0", "61.9"]
    assert figure.layout.title.text is None
    assert figure.layout.xaxis.tickangle == 45
    assert figure.layout.xaxis.tickfont.size == 28
    assert figure.layout.yaxis.title.text == "count"
    assert figure.layout.yaxis2.title.text == "min"
    assert figure.layout.yaxis3.title.text == "s"
    assert "Sequences" in svg
    assert "Total duration" in svg
    assert "Avg. duration" in svg
    assert "ADVIO" in svg
    assert "TUM RGB-D" in svg
    assert "67.8" in svg


def _record(sequence_id: str, profile_key: str, *, is_default: bool) -> NormalizedSequenceRecord:
    return NormalizedSequenceRecord(
        dataset_id=DatasetId.ADVIO,
        sequence_id=sequence_id,
        sequence_label=sequence_id,
        source_id="advio",
        profile_key=profile_key,
        root=Path("/tmp") / sequence_id / profile_key,
        is_default_profile=is_default,
        stats_row_count=1,
        metadata_row_count=0,
    )


def _duration_row(sequence_id: str, profile_key: str, duration_s: float) -> dict[str, str | float]:
    return {
        "dataset_id": "advio",
        "sequence_id": sequence_id,
        "profile_key": profile_key,
        "source_id": "advio",
        "scope": "observation_sequence",
        "subject": "sequence",
        "stat": "observation_duration_s",
        "value": duration_s,
        "unit": "s",
    }
