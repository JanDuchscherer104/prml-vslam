from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

import prml_vslam.app.pages.datasets as advio_page
from prml_vslam.app.models import AdvioPageState, AppState, Record3DDatasetPoseSource
from prml_vslam.interfaces import Observation, ObservationProvenance
from prml_vslam.sources.datasets.advio import AdvioPoseSource
from prml_vslam.sources.datasets.contracts import LocalSceneStatus
from prml_vslam.sources.datasets.normalized_query import (
    NormalizedDatasetQuery,
    NormalizedSequenceRecord,
    normalized_advio_pose_sources,
)
from prml_vslam.sources.datasets.record3d import Record3DSceneMetadata


class _NullContext:
    def __enter__(self):
        return self

    def __exit__(self, *_args: object) -> None:
        return None


def test_advio_preview_frame_uses_live_image_renderer(monkeypatch) -> None:
    calls: dict[str, object] = {}
    monkeypatch.setattr(advio_page.st, "markdown", lambda text: calls.setdefault("markdown", text))
    monkeypatch.setattr(advio_page.st, "image", lambda image, **kwargs: calls.update(image=image, kwargs=kwargs))
    packet = Observation(
        seq=0,
        timestamp_ns=1,
        arrival_timestamp_s=0.0,
        rgb=np.zeros((2, 2, 3), dtype=np.uint8),
        provenance=ObservationProvenance(source_id="demo"),
    )

    advio_page._render_preview_frame(packet)

    assert calls["markdown"] == "**RGB Frame**"
    assert np.array_equal(calls["image"], packet.rgb)
    assert calls["kwargs"] == {"channels": "RGB", "clamp": True}


def test_advio_preview_pose_sources_use_provider_readiness_flags() -> None:
    records = [
        NormalizedSequenceRecord(
            dataset_id="advio",
            sequence_id="advio-15",
            sequence_label="ADVIO 15",
            source_id="advio",
            profile_key=source.value,
            root=Path(".data/vslam-datastore/advio/advio-15") / source.value,
            is_default_profile=source is AdvioPoseSource.GROUND_TRUTH,
            stats_row_count=1,
            metadata_row_count=1,
            advio_pose_source=source,
        )
        for source in (AdvioPoseSource.GROUND_TRUTH, AdvioPoseSource.ARCORE, AdvioPoseSource.ARKIT)
    ]

    assert normalized_advio_pose_sources(records, sequence_id="advio-15") == [
        AdvioPoseSource.GROUND_TRUTH,
        AdvioPoseSource.ARCORE,
        AdvioPoseSource.ARKIT,
    ]


def test_advio_sequence_explorer_saves_normalized_sequence_slug(monkeypatch) -> None:
    saved: list[AppState] = []
    state = AppState(advio=AdvioPageState())
    record = NormalizedSequenceRecord(
        dataset_id="advio",
        sequence_id="advio-21",
        sequence_label="ADVIO 21",
        source_id="advio",
        profile_key=AdvioPoseSource.GROUND_TRUTH.value,
        root=Path(".data/vslam-datastore/advio/advio-21") / AdvioPoseSource.GROUND_TRUTH.value,
        is_default_profile=True,
        stats_row_count=1,
        metadata_row_count=1,
        advio_pose_source=AdvioPoseSource.GROUND_TRUTH,
    )
    context = SimpleNamespace(
        state=state,
        store=SimpleNamespace(save=lambda current_state: saved.append(current_state.model_copy(deep=True))),
    )

    monkeypatch.setattr(advio_page.st, "container", lambda **_kwargs: _NullContext())
    monkeypatch.setattr(advio_page.st, "subheader", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(advio_page.st, "selectbox", lambda *_args, **_kwargs: "advio-21")
    monkeypatch.setattr(advio_page.st, "dataframe", lambda *_args, **_kwargs: None)

    advio_page._render_sequence_explorer_impl(
        context=context,
        records=[record],
        page_state=state.advio,
        dataset_label="ADVIO",
    )

    assert state.advio.explorer_sequence_id == "advio-21"
    assert saved[-1].advio.explorer_sequence_id == "advio-21"


def test_record3d_download_form_builds_index_request_and_syncs_state(monkeypatch) -> None:
    saved: list[AppState] = []
    state = AppState()
    state.record3d_dataset.selected_sequence_ids = [1]
    service = SimpleNamespace(
        catalog=SimpleNamespace(
            scenes=[
                Record3DSceneMetadata(
                    sequence_id="first", archive_name="first.r3d", display_name="First", sequence_index=0
                ),
                Record3DSceneMetadata(
                    sequence_id="second", archive_name="second.r3d", display_name="Second", sequence_index=1
                ),
            ]
        ),
        scene=lambda sequence_id: Record3DSceneMetadata(
            sequence_id=str(sequence_id),
            archive_name=f"{sequence_id}.r3d",
            display_name=f"Scene {sequence_id}",
            sequence_index=int(sequence_id),
        ),
    )
    context = SimpleNamespace(
        state=state,
        store=SimpleNamespace(save=lambda current_state: saved.append(current_state.model_copy(deep=True))),
        record3d_dataset_service=service,
    )

    monkeypatch.setattr(advio_page.st, "form", lambda *_args, **_kwargs: _NullContext())
    monkeypatch.setattr(advio_page.st, "multiselect", lambda *_args, **_kwargs: [1])
    monkeypatch.setattr(advio_page.st, "toggle", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(advio_page.st, "form_submit_button", lambda *_args, **_kwargs: True)

    form = advio_page._render_record3d_download_form(context)

    assert form.submitted is True
    assert form.request.sequence_ids == [1]
    assert form.request.overwrite is True
    assert state.record3d_dataset.selected_sequence_ids == [1]
    assert state.record3d_dataset.overwrite_existing is True
    assert saved


def test_record3d_scene_rows_mark_local_only_archives(monkeypatch) -> None:
    status = LocalSceneStatus[Record3DSceneMetadata](
        scene=Record3DSceneMetadata(
            sequence_id="local-capture",
            archive_name="local-capture.r3d",
            display_name="local-capture",
            archive_size_bytes=42_000_000,
        ),
        sequence_dir=Path(".data/record3d"),
        archive_path=Path(".data/record3d/local-capture.r3d"),
        replay_ready=True,
        offline_ready=True,
    )

    rows = advio_page._record3d_scene_rows([status])
    rows = advio_page._rows_with_normalized_status(
        rows,
        NormalizedDatasetQuery(
            dataset_id="record3d",
            records=[
                NormalizedSequenceRecord(
                    dataset_id="record3d",
                    sequence_id="local-capture",
                    sequence_label="local-capture",
                    source_id="record3d_dataset",
                    profile_key="profile",
                    root=Path(".data/vslam-datastore/record3d/local-capture/profile"),
                    is_default_profile=True,
                    stats_row_count=1,
                    metadata_row_count=1,
                )
            ],
            issues=[],
            stats_df=pd.DataFrame(),
            metadata_df=pd.DataFrame(),
        ),
    )

    assert rows == [
        {
            "Scene": "local-capture",
            "Sequence": "local-capture",
            "Source": "Local-only",
            "Index": "Local",
            "Packed Size (MB)": 42.0,
            "Downloaded Cache": True,
            "Cached Archive": True,
            "Normalized": True,
            "Normalized Profiles": 1,
        }
    ]


def test_normalized_dataset_query_builds_compact_analysis_frames(tmp_path: Path) -> None:
    entry_root = tmp_path / ".data" / "vslam-datastore" / "advio" / "advio-21" / "profile"
    rgb_dir = entry_root / "observations" / "rgb"
    depth_dir = entry_root / "observations" / "depth"
    rgb_dir.mkdir(parents=True)
    depth_dir.mkdir()
    (rgb_dir / "000000.png").write_bytes(b"rgb")
    (depth_dir / "000000.png").write_bytes(b"depth")
    query = NormalizedDatasetQuery(
        dataset_id="advio",
        records=[
            NormalizedSequenceRecord(
                dataset_id="advio",
                sequence_id="advio-21",
                sequence_label="ADVIO 21",
                source_id="advio",
                profile_key="profile",
                root=entry_root,
                is_default_profile=True,
                stats_row_count=8,
                metadata_row_count=1,
            )
        ],
        issues=[],
        stats_df=pd.DataFrame.from_records(
            [
                {
                    "dataset_id": "advio",
                    "sequence_id": "advio-21",
                    "profile_key": "profile",
                    "source_id": "advio",
                    "scope": "observation_sequence",
                    "subject": "advio",
                    "stat": "observation_frame_count",
                    "value": "10",
                    "unit": "count",
                },
                {
                    "dataset_id": "advio",
                    "sequence_id": "advio-21",
                    "profile_key": "profile",
                    "source_id": "advio",
                    "scope": "reference_trajectory",
                    "subject": "ground_truth/source_native",
                    "stat": "trajectory_path_length_m",
                    "value": "3.5",
                    "unit": "m",
                },
                {
                    "dataset_id": "advio",
                    "sequence_id": "advio-21",
                    "profile_key": "profile",
                    "source_id": "advio",
                    "scope": "reference_trajectory",
                    "subject": "ground_truth/source_native",
                    "stat": "trajectory_mean_curvature_rad_m",
                    "value": "0.12",
                    "unit": "rad/m",
                },
            ]
        ),
        metadata_df=pd.DataFrame(),
    )

    assert query.observation_summary_frame()["observation_frame_count"].tolist() == ["10"]
    trajectory_summary = query.trajectory_summary_frame()
    assert trajectory_summary["trajectory_path_length_m"].tolist() == ["3.5"]
    assert trajectory_summary["trajectory_mean_curvature_rad_m"].tolist() == ["0.12"]
    assert query.filtered_stats_frame(sequence_ids=["advio-21"], scopes=["observation_sequence"])["stat"].tolist() == [
        "observation_frame_count"
    ]
    assert query.payload_footprint_frame()[["RGB MB", "Depth MB", "Video MB"]].iloc[0].tolist() == [
        0.0,
        0.0,
        0.0,
    ]


def test_record3d_loop_preview_uses_normalized_default_records(monkeypatch) -> None:
    captured: dict[str, list[NormalizedSequenceRecord]] = {}
    context = SimpleNamespace(
        state=SimpleNamespace(record3d_dataset=SimpleNamespace(preview_include_depth=True)),
    )
    normalized = NormalizedDatasetQuery(
        dataset_id="record3d",
        records=[
            NormalizedSequenceRecord(
                dataset_id="record3d",
                sequence_id="capture",
                sequence_label="capture",
                source_id="record3d_dataset",
                profile_key="profile",
                root=Path(".data/vslam-datastore/record3d/capture/profile"),
                is_default_profile=True,
                stats_row_count=1,
                metadata_row_count=1,
            )
        ],
        issues=[],
        stats_df=pd.DataFrame(),
        metadata_df=pd.DataFrame(),
    )
    monkeypatch.setattr(
        advio_page, "_render_loop_preview_impl", lambda **kwargs: captured.update(records=kwargs["records"])
    )

    advio_page._render_record3d_loop_preview(context, normalized)

    assert [record.sequence_id for record in captured["records"]] == ["capture"]


def test_record3d_preview_action_uses_dataset_service_and_clears_other_previews(monkeypatch) -> None:
    state = AppState()
    state.advio.preview_is_running = True
    state.tum_rgbd.preview_is_running = True
    started: dict[str, object] = {}
    service = SimpleNamespace(
        scene=lambda sequence_id: Record3DSceneMetadata(
            sequence_id=sequence_id,
            archive_name=f"{sequence_id}.r3d",
            display_name="Record3D Scene",
        ),
    )
    context = SimpleNamespace(
        state=state,
        store=SimpleNamespace(save=lambda _state: None),
        record3d_dataset_service=service,
        path_config=SimpleNamespace(resolve_output_dir=lambda path, create=False: Path(".artifacts") / path),
        advio_runtime=SimpleNamespace(
            start=lambda **kwargs: started.update(kwargs),
            stop=lambda: None,
        ),
    )
    monkeypatch.setattr(advio_page, "open_normalized_dataset_stream", lambda **kwargs: ("stream", kwargs))

    error = advio_page._handle_record3d_dataset_preview_action(
        context=context,
        sequence_id="2026-06-03--18-26-32",
        pose_source=Record3DDatasetPoseSource.ARKIT,
        include_depth=False,
        start_requested=True,
        stop_requested=False,
    )

    assert error is None
    assert started["sequence_id"] == "2026-06-03--18-26-32"
    assert started["sequence_label"] == "Record3D Scene"
    assert started["pose_source"] is Record3DDatasetPoseSource.ARKIT
    assert started["stream"] == (
        "stream",
        {
            "dataset_id": advio_page.DatasetId.RECORD3D,
            "service": service,
            "source_config": advio_page.source_config_for_normalization(
                dataset_id=advio_page.DatasetId.RECORD3D,
                sequence_id="2026-06-03--18-26-32",
            ),
            "include_depth": False,
            "path_config": context.path_config,
            "output_dir": Path(".artifacts") / "dataset-preview" / "record3d" / "2026-06-03--18-26-32",
        },
    )
    assert state.record3d_dataset.preview_is_running is True
    assert state.advio.preview_is_running is False
    assert state.tum_rgbd.preview_is_running is False
