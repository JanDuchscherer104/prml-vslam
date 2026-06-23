from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

import prml_vslam.app.dataset_page.dashboard as dataset_dashboard
import prml_vslam.app.dataset_page.downloads as dataset_downloads
import prml_vslam.app.dataset_page.preview as dataset_preview
import prml_vslam.app.dataset_page.query as dataset_query
import prml_vslam.app.dataset_page.scene as dataset_scene
import prml_vslam.app.pages.datasets as advio_page
from prml_vslam.app.models import AdvioPageState, AppState, Record3DDatasetPoseSource
from prml_vslam.interfaces import FrameTransform, Observation, ObservationProvenance
from prml_vslam.sources.contracts import (
    PreparedBenchmarkInputs,
    ReferenceCloudCoordinateStatus,
    ReferenceCloudRef,
    ReferenceCloudSource,
    ReferenceSource,
    ReferenceTrajectoryRef,
)
from prml_vslam.sources.datasets.advio import AdvioPoseSource
from prml_vslam.sources.datasets.contracts import LocalSceneStatus
from prml_vslam.sources.datasets.normalized_query import (
    NormalizedDatasetQuery,
    NormalizedSequenceRecord,
    normalized_advio_pose_sources,
)
from prml_vslam.sources.datasets.record3d import Record3DSceneMetadata
from prml_vslam.utils.geometry import write_point_cloud_ply, write_tum_trajectory


class _NullContext:
    def __enter__(self):
        return self

    def __exit__(self, *_args: object) -> None:
        return None


def test_dataset_sections_keep_visible_order_but_render_diagnostics_first(monkeypatch) -> None:
    labels: list[list[str]] = []
    rendered: list[str] = []

    class Tab:
        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> None:
            return None

    def capture_tabs(tab_labels: list[str]) -> list[Tab]:
        labels.append(tab_labels)
        return [Tab() for _ in tab_labels]

    monkeypatch.setattr(advio_page.st, "tabs", capture_tabs)

    advio_page._render_dataset_sections(
        dashboard=lambda: rendered.append("Dashboard"),
        scene=lambda: rendered.append("Scene"),
        preview=lambda: rendered.append("Preview"),
        diagnostics=lambda: rendered.append("Diagnostics"),
    )

    assert labels == [["Dashboard", "Scene", "Preview", "Diagnostics"]]
    assert rendered == ["Diagnostics", "Dashboard", "Scene", "Preview"]


def test_advio_preview_frame_uses_live_image_renderer(monkeypatch) -> None:
    calls: dict[str, object] = {}
    monkeypatch.setattr(dataset_preview.st, "markdown", lambda text: calls.setdefault("markdown", text))
    monkeypatch.setattr(
        dataset_preview, "render_live_image", lambda image, **kwargs: calls.update(image=image, kwargs=kwargs)
    )
    packet = Observation(
        seq=0,
        timestamp_ns=1,
        arrival_timestamp_s=0.0,
        rgb=np.zeros((2, 2, 3), dtype=np.uint8),
        provenance=ObservationProvenance(source_id="demo"),
    )

    dataset_preview.render_preview_frame(packet)

    assert calls["markdown"] == "**RGB Frame**"
    assert np.array_equal(calls["image"], packet.rgb)
    assert calls["kwargs"] == {"channels": "RGB", "clamp": True, "width": "stretch"}


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

    monkeypatch.setattr(dataset_scene.st, "container", lambda **_kwargs: _NullContext())
    monkeypatch.setattr(dataset_scene.st, "subheader", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(dataset_scene.st, "selectbox", lambda *_args, **_kwargs: "advio-21")
    monkeypatch.setattr(dataset_scene.st, "dataframe", lambda *_args, **_kwargs: None)

    dataset_scene.render_sequence_explorer(
        context=context,
        records=[record],
        all_records=[record],
        page_state=state.advio,
        dataset_label="ADVIO",
        key_prefix="advio-scene",
    )

    assert state.advio.explorer_sequence_id == "advio-21"
    assert saved[-1].advio.explorer_sequence_id == "advio-21"


def test_sequence_explorer_dedupes_scene_options_but_shows_all_profiles(monkeypatch) -> None:
    selected_options: list[list[str]] = []
    detail_rows: list[list[dict[str, object]]] = []
    state = AppState(advio=AdvioPageState())
    records = [
        NormalizedSequenceRecord(
            dataset_id="advio",
            sequence_id="advio-21",
            sequence_label="ADVIO 21",
            source_id="advio",
            profile_key="non-default",
            root=Path(".data/vslam-datastore/advio/advio-21/non-default"),
            is_default_profile=False,
            stats_row_count=1,
            metadata_row_count=1,
            advio_pose_source=AdvioPoseSource.ARCORE,
        ),
        NormalizedSequenceRecord(
            dataset_id="advio",
            sequence_id="advio-21",
            sequence_label="ADVIO 21",
            source_id="advio",
            profile_key="default",
            root=Path(".data/vslam-datastore/advio/advio-21/default"),
            is_default_profile=True,
            stats_row_count=2,
            metadata_row_count=2,
            advio_pose_source=AdvioPoseSource.GROUND_TRUTH,
        ),
    ]
    query = NormalizedDatasetQuery(
        dataset_id="advio",
        records=records,
        issues=[],
        stats_df=pd.DataFrame.from_records(
            [
                {
                    "dataset_id": "advio",
                    "sequence_id": "advio-21",
                    "profile_key": "non-default",
                    "source_id": "advio",
                    "scope": "observation_sequence",
                    "subject": "advio",
                    "stat": "observation_frame_count",
                    "value": "5",
                    "unit": "count",
                },
                {
                    "dataset_id": "advio",
                    "sequence_id": "advio-21",
                    "profile_key": "default",
                    "source_id": "advio",
                    "scope": "observation_sequence",
                    "subject": "advio",
                    "stat": "observation_frame_count",
                    "value": "10",
                    "unit": "count",
                },
            ]
        ),
        metadata_df=pd.DataFrame(),
    )
    context = SimpleNamespace(
        state=state,
        store=SimpleNamespace(save=lambda _state: None),
    )

    def capture_selectbox(_label: str, *, options: list[str], **_kwargs) -> str:
        selected_options.append(options)
        return "advio-21"

    monkeypatch.setattr(dataset_scene.st, "container", lambda **_kwargs: _NullContext())
    monkeypatch.setattr(dataset_scene.st, "subheader", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(dataset_scene.st, "selectbox", capture_selectbox)
    monkeypatch.setattr(dataset_scene.st, "dataframe", lambda rows, **_kwargs: detail_rows.append(rows))

    selected = dataset_scene.render_sequence_explorer(
        context=context,
        records=query.scene_sequence_records(),
        all_records=query.records,
        page_state=state.advio,
        dataset_label="ADVIO",
        key_prefix="advio-scene",
    )

    assert selected == "advio-21"
    assert selected_options == [["advio-21"]]
    assert [row["Profile"] for row in detail_rows[0]] == ["non-default", "default"]
    assert query.preferred_profile_key(sequence_id="advio-21") == "default"
    assert query.observation_summary_frame(sequence_id="advio-21", profile_key="default")[
        "observation_frame_count"
    ].tolist() == ["10"]


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

    monkeypatch.setattr(dataset_downloads.st, "form", lambda *_args, **_kwargs: _NullContext())
    monkeypatch.setattr(dataset_downloads.st, "multiselect", lambda *_args, **_kwargs: [1])
    monkeypatch.setattr(dataset_downloads.st, "toggle", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(dataset_downloads.st, "form_submit_button", lambda *_args, **_kwargs: True)

    form = dataset_downloads.render_record3d_download_form(context)

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

    rows = dataset_downloads.record3d_scene_rows([status])
    rows = dataset_downloads.rows_with_normalized_status(
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


def test_successful_download_invalidates_normalized_snapshot_and_reruns(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(dataset_downloads, "clear_normalized_dataset_snapshot_cache", lambda: calls.append("clear"))
    monkeypatch.setattr(dataset_downloads.st, "rerun", lambda: calls.append("rerun"))

    dataset_downloads.rerun_after_successful_download(form_submitted=True, notice_level="success")

    assert calls == ["clear", "rerun"]


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
                {
                    "dataset_id": "advio",
                    "sequence_id": "advio-21",
                    "profile_key": "profile",
                    "source_id": "advio",
                    "scope": "reference_trajectory",
                    "subject": "ground_truth/source_native",
                    "stat": "trajectory_mean_speed_m_s",
                    "value": "0.5",
                    "unit": "m/s",
                },
                {
                    "dataset_id": "advio",
                    "sequence_id": "advio-21",
                    "profile_key": "profile",
                    "source_id": "advio",
                    "scope": "reference_trajectory",
                    "subject": "ground_truth/source_native",
                    "stat": "ego_motion_class",
                    "value": "high_curvature",
                    "unit": "class",
                },
            ]
        ),
        metadata_df=pd.DataFrame(),
    )

    assert query.observation_summary_frame()["observation_frame_count"].tolist() == ["10"]
    trajectory_summary = query.trajectory_summary_frame()
    assert trajectory_summary["trajectory_path_length_m"].tolist() == ["3.5"]
    assert trajectory_summary["trajectory_mean_curvature_rad_m"].tolist() == ["0.12"]
    assert trajectory_summary["trajectory_mean_speed_m_s"].tolist() == ["0.5"]
    assert "ego_motion_class" not in trajectory_summary.columns
    assert query.filtered_stats_frame(sequence_ids=["advio-21"], scopes=["observation_sequence"])["stat"].tolist() == [
        "observation_frame_count"
    ]
    assert query.payload_footprint_frame()[["RGB MB", "Depth MB", "Video MB"]].iloc[0].tolist() == [
        0.0,
        0.0,
        0.0,
    ]


def test_normalized_dataset_query_filters_known_bad_advio_23_arkit_summary() -> None:
    def row(sequence_id: str, subject: str) -> dict[str, str]:
        return {
            "dataset_id": "advio",
            "sequence_id": sequence_id,
            "profile_key": "profile",
            "source_id": "advio",
            "scope": "reference_trajectory",
            "subject": subject,
            "stat": "trajectory_path_length_m",
            "value": "1.0",
            "unit": "m",
        }

    query = NormalizedDatasetQuery(
        dataset_id="advio",
        records=[],
        issues=[],
        stats_df=pd.DataFrame.from_records(
            [
                row("advio-23", "arkit/source_native"),
                row("advio-23", "arkit/aligned"),
                row("advio-23", "arcore/aligned"),
                row("advio-23", "ground_truth/source_native"),
                row("advio-22", "arkit/source_native"),
            ]
        ),
        metadata_df=pd.DataFrame(),
    )

    subjects = set(query.trajectory_summary_frame()[["sequence_id", "subject"]].itertuples(index=False, name=None))

    assert ("advio-23", "arkit/source_native") not in subjects
    assert ("advio-23", "arkit/aligned") not in subjects
    assert {
        ("advio-23", "arcore/aligned"),
        ("advio-23", "ground_truth/source_native"),
        ("advio-22", "arkit/source_native"),
    }.issubset(subjects)


def test_trajectory_dashboard_chart_frame_dedupes_provider_rows() -> None:
    frame = pd.DataFrame.from_records(
        [
            {
                "sequence_id": "advio-01",
                "scope": "candidate_trajectory",
                "subject": "arcore/aligned",
                "trajectory_path_length_m": "10",
            },
            {
                "sequence_id": "advio-01",
                "scope": "reference_trajectory",
                "subject": "arcore/aligned",
                "trajectory_path_length_m": "11",
            },
            {
                "sequence_id": "advio-01",
                "scope": "reference_trajectory",
                "subject": "ground_truth/source_native",
                "trajectory_path_length_m": "12",
            },
            {
                "sequence_id": "advio-02",
                "scope": "candidate_trajectory",
                "subject": "arkit/source_native",
                "trajectory_path_length_m": "13",
            },
        ]
    )

    chart_frame = dataset_dashboard.trajectory_dashboard_chart_frame(frame)

    assert chart_frame[["sequence_id", "scope", "subject", "trajectory_path_length_m"]].to_dict("records") == [
        {
            "sequence_id": "advio-01",
            "scope": "reference_trajectory",
            "subject": "arcore/aligned",
            "trajectory_path_length_m": "11",
        },
        {
            "sequence_id": "advio-01",
            "scope": "reference_trajectory",
            "subject": "ground_truth/source_native",
            "trajectory_path_length_m": "12",
        },
        {
            "sequence_id": "advio-02",
            "scope": "candidate_trajectory",
            "subject": "arkit/source_native",
            "trajectory_path_length_m": "13",
        },
    ]


def test_normalized_dataset_query_loads_scene_trajectory_artifacts(tmp_path: Path) -> None:
    entry_root = tmp_path / ".data" / "vslam-datastore" / "tum_rgbd" / "freiburg3_large_cabinet" / "profile"
    trajectory_path = write_tum_trajectory(
        entry_root / "benchmark" / "trajectories" / "ground_truth.tum",
        poses=[
            FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
            FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=0.0, tz=0.0),
        ],
        timestamps=[0.0, 1.0],
    )
    benchmark_inputs = PreparedBenchmarkInputs(
        reference_trajectories=[
            ReferenceTrajectoryRef(
                source=ReferenceSource.GROUND_TRUTH,
                path=trajectory_path,
                coordinate_status=ReferenceCloudCoordinateStatus.SOURCE_NATIVE,
            )
        ]
    )
    (entry_root / "benchmark_inputs.json").write_text(benchmark_inputs.model_dump_json(), encoding="utf-8")
    query = NormalizedDatasetQuery(
        dataset_id="tum_rgbd",
        records=[
            NormalizedSequenceRecord(
                dataset_id="tum_rgbd",
                sequence_id="freiburg3_large_cabinet",
                sequence_label="Freiburg 3 Large Cabinet",
                source_id="tum_rgbd",
                profile_key="profile",
                root=entry_root,
                is_default_profile=True,
                stats_row_count=1,
                metadata_row_count=1,
            )
        ],
        issues=[],
        stats_df=pd.DataFrame(),
        metadata_df=pd.DataFrame(),
    )

    artifacts = query.trajectory_artifacts(sequence_id="freiburg3_large_cabinet")

    assert [(artifact.label, artifact.path) for artifact in artifacts] == [
        ("Ground truth (source native)", trajectory_path.resolve())
    ]
    assert query.trajectory_artifacts(sequence_id="freiburg3_large_cabinet", profile_key="missing-profile") == []


def test_normalized_dataset_query_loads_scene_reference_cloud_artifacts(tmp_path: Path) -> None:
    entry_root = tmp_path / ".data" / "vslam-datastore" / "tum_rgbd" / "freiburg3_large_cabinet" / "profile"
    cloud_path = write_point_cloud_ply(
        entry_root / "benchmark" / "reference_clouds" / "tum_rgbd.ply",
        np.asarray([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]], dtype=np.float64),
    )
    metadata_path = cloud_path.with_suffix(".metadata.json")
    metadata_path.write_text("{}", encoding="utf-8")
    benchmark_inputs = PreparedBenchmarkInputs(
        reference_clouds=[
            ReferenceCloudRef(
                source=ReferenceCloudSource.TUM_RGBD,
                path=cloud_path,
                metadata_path=metadata_path,
                target_frame="tum_rgbd_world",
                coordinate_status=ReferenceCloudCoordinateStatus.ALIGNED,
            )
        ]
    )
    (entry_root / "benchmark_inputs.json").write_text(benchmark_inputs.model_dump_json(), encoding="utf-8")
    query = NormalizedDatasetQuery(
        dataset_id="tum_rgbd",
        records=[
            NormalizedSequenceRecord(
                dataset_id="tum_rgbd",
                sequence_id="freiburg3_large_cabinet",
                sequence_label="Freiburg 3 Large Cabinet",
                source_id="tum_rgbd",
                profile_key="profile",
                root=entry_root,
                is_default_profile=True,
                stats_row_count=1,
                metadata_row_count=1,
            )
        ],
        issues=[],
        stats_df=pd.DataFrame(),
        metadata_df=pd.DataFrame(),
    )

    artifacts = query.reference_cloud_artifacts(
        sequence_id="freiburg3_large_cabinet",
        profile_key="profile",
    )

    assert [(artifact.label, artifact.path, artifact.metadata_path) for artifact in artifacts] == [
        ("Tum Rgbd (aligned)", cloud_path.resolve(), metadata_path.resolve())
    ]
    assert query.reference_cloud_artifacts(sequence_id="freiburg3_large_cabinet", profile_key="missing-profile") == []


def test_scene_profile_selector_exposes_profile_choice(monkeypatch) -> None:
    select_calls: list[dict[str, object]] = []
    records = [
        NormalizedSequenceRecord(
            dataset_id="advio",
            sequence_id="advio-21",
            sequence_label="ADVIO 21",
            source_id="advio",
            profile_key="secondary",
            root=Path(".data/vslam-datastore/advio/advio-21/secondary"),
            is_default_profile=False,
            stats_row_count=1,
            metadata_row_count=1,
        ),
        NormalizedSequenceRecord(
            dataset_id="advio",
            sequence_id="advio-21",
            sequence_label="ADVIO 21",
            source_id="advio",
            profile_key="default",
            root=Path(".data/vslam-datastore/advio/advio-21/default"),
            is_default_profile=True,
            stats_row_count=1,
            metadata_row_count=1,
        ),
    ]
    query = NormalizedDatasetQuery(
        dataset_id="advio",
        records=records,
        issues=[],
        stats_df=pd.DataFrame(),
        metadata_df=pd.DataFrame(),
    )

    def capture_selectbox(_label: str, *, options: list[str], index: int, **_kwargs) -> str:
        select_calls.append({"options": options, "index": index})
        return options[0]

    monkeypatch.setattr(dataset_scene.st, "selectbox", capture_selectbox)

    selected = dataset_scene.render_scene_profile_selector(
        normalized=query,
        sequence_id="advio-21",
        key_prefix="advio-scene",
    )

    assert selected == "default"
    assert select_calls == [{"options": ["default", "secondary"], "index": 0}]


def test_scene_statistics_keeps_trajectory_metrics_subject_qualified(monkeypatch) -> None:
    metric_calls: list[tuple[str, str]] = []
    trajectory_tables: list[pd.DataFrame] = []
    query = NormalizedDatasetQuery(
        dataset_id="advio",
        records=[],
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
                    "value": "42",
                    "unit": "count",
                },
                {
                    "dataset_id": "advio",
                    "sequence_id": "advio-21",
                    "profile_key": "profile",
                    "source_id": "advio",
                    "scope": "observation_sequence",
                    "subject": "advio",
                    "stat": "observation_duration_s",
                    "value": "2.5",
                    "unit": "s",
                },
                {
                    "dataset_id": "advio",
                    "sequence_id": "advio-21",
                    "profile_key": "profile",
                    "source_id": "advio",
                    "scope": "reference_trajectory",
                    "subject": "ground_truth/source_native",
                    "stat": "trajectory_path_length_m",
                    "value": "10",
                    "unit": "m",
                },
                {
                    "dataset_id": "advio",
                    "sequence_id": "advio-21",
                    "profile_key": "profile",
                    "source_id": "advio",
                    "scope": "candidate_trajectory",
                    "subject": "arcore/source_native",
                    "stat": "trajectory_path_length_m",
                    "value": "12",
                    "unit": "m",
                },
            ]
        ),
        metadata_df=pd.DataFrame(),
    )

    monkeypatch.setattr(
        dataset_scene.st,
        "columns",
        lambda *_args, **_kwargs: [
            SimpleNamespace(metric=lambda label, value: metric_calls.append((label, value))) for _ in range(3)
        ],
    )
    monkeypatch.setattr(dataset_scene.st, "subheader", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(dataset_scene.st, "dataframe", lambda frame, **_kwargs: trajectory_tables.append(frame))

    dataset_scene.render_scene_statistics(normalized=query, sequence_id="advio-21", profile_key="profile")

    assert [label for label, _value in metric_calls] == ["Frames", "Duration", "Mean FPS"]
    assert trajectory_tables
    assert trajectory_tables[0][["scope", "subject", "trajectory_path_length_m"]].to_dict("records") == [
        {
            "scope": "reference_trajectory",
            "subject": "ground_truth/source_native",
            "trajectory_path_length_m": "10",
        },
        {
            "scope": "candidate_trajectory",
            "subject": "arcore/source_native",
            "trajectory_path_length_m": "12",
        },
    ]


def test_scene_trajectory_section_renders_bev_and_3d_figures(monkeypatch, tmp_path: Path) -> None:
    bev_calls: list[dict[str, object]] = []
    trajectory_3d_calls: list[dict[str, object]] = []
    rendered: list[object] = []
    entry_root = tmp_path / ".data" / "vslam-datastore" / "tum_rgbd" / "freiburg3_large_cabinet" / "profile"
    trajectory_path = write_tum_trajectory(
        entry_root / "benchmark" / "trajectories" / "ground_truth.tum",
        poses=[
            FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
            FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=1.0, tz=0.0),
        ],
        timestamps=[0.0, 1.0],
    )
    benchmark_inputs = PreparedBenchmarkInputs(
        reference_trajectories=[ReferenceTrajectoryRef(source=ReferenceSource.GROUND_TRUTH, path=trajectory_path)]
    )
    (entry_root / "benchmark_inputs.json").write_text(benchmark_inputs.model_dump_json(), encoding="utf-8")
    query = NormalizedDatasetQuery(
        dataset_id="tum_rgbd",
        records=[
            NormalizedSequenceRecord(
                dataset_id="tum_rgbd",
                sequence_id="freiburg3_large_cabinet",
                sequence_label="Freiburg 3 Large Cabinet",
                source_id="tum_rgbd",
                profile_key="profile",
                root=entry_root,
                is_default_profile=True,
                stats_row_count=1,
                metadata_row_count=1,
            )
        ],
        issues=[],
        stats_df=pd.DataFrame(),
        metadata_df=pd.DataFrame(),
    )
    monkeypatch.setattr(dataset_scene.st, "subheader", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        dataset_scene.plots,
        "build_bev_trajectory_figure",
        lambda trajectories, **kwargs: bev_calls.append({"trajectories": trajectories, **kwargs})
        or SimpleNamespace(layout=SimpleNamespace(title=SimpleNamespace(text="BEV Trajectory Overlay"))),
    )
    monkeypatch.setattr(
        dataset_scene.plots,
        "build_3d_trajectory_figure",
        lambda trajectories, **kwargs: trajectory_3d_calls.append({"trajectories": trajectories, **kwargs})
        or SimpleNamespace(layout=SimpleNamespace(title=SimpleNamespace(text="3D Trajectory Overlay"))),
    )
    monkeypatch.setattr(
        dataset_scene.st,
        "columns",
        lambda *_args, **_kwargs: [
            SimpleNamespace(plotly_chart=lambda figure, **_kwargs: rendered.append(figure)) for _ in range(2)
        ],
    )

    dataset_scene.render_scene_trajectories(
        normalized=query,
        sequence_id="freiburg3_large_cabinet",
        profile_key="profile",
        key_prefix="tum-rgbd-scene",
    )

    assert len(rendered) == 2
    assert rendered[0].layout.title.text == "BEV Trajectory Overlay"
    assert rendered[1].layout.title.text == "3D Trajectory Overlay"
    assert bev_calls[0]["plane_axes"] == (0, 1)
    assert "pose_axes_name" not in trajectory_3d_calls[0]


def test_advio_scene_trajectory_uses_xz_bev_axes(monkeypatch, tmp_path: Path) -> None:
    bev_calls: list[dict[str, object]] = []
    entry_root = tmp_path / ".data" / "vslam-datastore" / "advio" / "advio-21" / "profile"
    trajectory_path = write_tum_trajectory(
        entry_root / "benchmark" / "trajectories" / "ground_truth.tum",
        poses=[
            FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
            FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=1.0, tz=1.0),
        ],
        timestamps=[0.0, 1.0],
    )
    benchmark_inputs = PreparedBenchmarkInputs(
        reference_trajectories=[ReferenceTrajectoryRef(source=ReferenceSource.GROUND_TRUTH, path=trajectory_path)]
    )
    (entry_root / "benchmark_inputs.json").write_text(benchmark_inputs.model_dump_json(), encoding="utf-8")
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
                stats_row_count=1,
                metadata_row_count=1,
            )
        ],
        issues=[],
        stats_df=pd.DataFrame(),
        metadata_df=pd.DataFrame(),
    )
    monkeypatch.setattr(dataset_scene.st, "subheader", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        dataset_scene.plots,
        "build_bev_trajectory_figure",
        lambda trajectories, **kwargs: bev_calls.append({"trajectories": trajectories, **kwargs})
        or SimpleNamespace(layout=SimpleNamespace(title=SimpleNamespace(text="BEV"))),
    )
    monkeypatch.setattr(
        dataset_scene.plots,
        "build_3d_trajectory_figure",
        lambda *_args, **_kwargs: SimpleNamespace(layout=SimpleNamespace(title=SimpleNamespace(text="3D"))),
    )
    monkeypatch.setattr(
        dataset_scene.st,
        "columns",
        lambda *_args, **_kwargs: [SimpleNamespace(plotly_chart=lambda figure, **_kwargs: None) for _ in range(2)],
    )

    dataset_scene.render_scene_trajectories(
        normalized=query,
        sequence_id="advio-21",
        profile_key="profile",
        key_prefix="advio-scene",
    )

    assert bev_calls[0]["plane_axes"] == (0, 2)


def test_scene_reference_cloud_plot_requires_explicit_load(monkeypatch, tmp_path: Path) -> None:
    rendered_tables: list[object] = []
    entry_root = tmp_path / ".data" / "vslam-datastore" / "tum_rgbd" / "freiburg3_large_cabinet" / "profile"
    trajectory_path = write_tum_trajectory(
        entry_root / "benchmark" / "trajectories" / "ground_truth.tum",
        poses=[
            FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
            FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=1.0, tz=0.0),
        ],
        timestamps=[0.0, 1.0],
    )
    cloud_path = write_point_cloud_ply(
        entry_root / "benchmark" / "reference_clouds" / "tum_rgbd.ply",
        np.asarray([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]], dtype=np.float64),
    )
    metadata_path = cloud_path.with_suffix(".metadata.json")
    metadata_path.write_text("{}", encoding="utf-8")
    benchmark_inputs = PreparedBenchmarkInputs(
        reference_trajectories=[ReferenceTrajectoryRef(source=ReferenceSource.GROUND_TRUTH, path=trajectory_path)],
        reference_clouds=[
            ReferenceCloudRef(
                source=ReferenceCloudSource.TUM_RGBD,
                path=cloud_path,
                metadata_path=metadata_path,
                target_frame="tum_rgbd_world",
                coordinate_status=ReferenceCloudCoordinateStatus.ALIGNED,
            )
        ],
    )
    (entry_root / "benchmark_inputs.json").write_text(benchmark_inputs.model_dump_json(), encoding="utf-8")
    query = NormalizedDatasetQuery(
        dataset_id="tum_rgbd",
        records=[
            NormalizedSequenceRecord(
                dataset_id="tum_rgbd",
                sequence_id="freiburg3_large_cabinet",
                sequence_label="Freiburg 3 Large Cabinet",
                source_id="tum_rgbd",
                profile_key="profile",
                root=entry_root,
                is_default_profile=True,
                stats_row_count=1,
                metadata_row_count=1,
            )
        ],
        issues=[],
        stats_df=pd.DataFrame(),
        metadata_df=pd.DataFrame(),
    )

    monkeypatch.setattr(dataset_scene.st, "subheader", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        dataset_scene.st,
        "columns",
        lambda *_args, **_kwargs: [SimpleNamespace(plotly_chart=lambda *_args, **_kwargs: None) for _ in range(2)],
    )
    monkeypatch.setattr(dataset_scene.st, "dataframe", lambda rows, **_kwargs: rendered_tables.append(rows))
    monkeypatch.setattr(dataset_scene.st, "button", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(
        dataset_query,
        "build_reference_cloud_scene_figure",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("reference cloud loaded eagerly")),
    )

    dataset_scene.render_scene_trajectories(
        normalized=query,
        sequence_id="freiburg3_large_cabinet",
        profile_key="profile",
        key_prefix="tum-rgbd-scene",
    )

    assert rendered_tables[0][0]["Cloud"] == "Tum Rgbd (aligned)"


def test_normalized_analysis_filters_use_dataset_scoped_widget_keys(monkeypatch) -> None:
    keys: list[str] = []
    stats_df = pd.DataFrame.from_records(
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
            }
        ]
    )

    def capture_multiselect(_label: str, *, default: list[str], key: str, **_kwargs) -> list[str]:
        keys.append(key)
        return default

    monkeypatch.setattr(dataset_downloads.st, "multiselect", capture_multiselect)
    monkeypatch.setattr(
        dataset_downloads.st,
        "columns",
        lambda *_args, **_kwargs: [SimpleNamespace(metric=lambda *_args, **_kwargs: None) for _ in range(4)],
    )
    monkeypatch.setattr(dataset_downloads.st, "subheader", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(dataset_downloads.st, "dataframe", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(dataset_downloads.st, "expander", lambda *_args, **_kwargs: _NullContext())

    for dataset_id in ("advio", "tum_rgbd", "record3d"):
        dataset_downloads.render_normalized_analysis_tables(
            NormalizedDatasetQuery(
                dataset_id=dataset_id,
                records=[],
                issues=[],
                stats_df=stats_df.assign(dataset_id=dataset_id),
                metadata_df=pd.DataFrame(),
            ),
            key_prefix=f"normalized:{dataset_id}",
        )

    assert keys == [
        "normalized:advio:sequence-filter",
        "normalized:advio:scope-filter",
        "normalized:advio:stat-filter",
        "normalized:tum_rgbd:sequence-filter",
        "normalized:tum_rgbd:scope-filter",
        "normalized:tum_rgbd:stat-filter",
        "normalized:record3d:sequence-filter",
        "normalized:record3d:scope-filter",
        "normalized:record3d:stat-filter",
    ]
    assert len(keys) == len(set(keys))


def test_record3d_loop_preview_uses_current_normalized_records(monkeypatch) -> None:
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
        dataset_preview, "render_loop_preview", lambda **kwargs: captured.update(records=kwargs["records"])
    )

    dataset_preview.render_record3d_loop_preview(context, normalized)

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
        dataset_preview_runtime=SimpleNamespace(
            start=lambda **kwargs: started.update(kwargs),
            stop=lambda: None,
        ),
    )
    monkeypatch.setattr(dataset_preview, "open_normalized_dataset_stream", lambda **kwargs: ("stream", kwargs))

    error = dataset_preview.handle_record3d_dataset_preview_action(
        context=context,
        sequence_id="2026-06-03--18-26-32",
        profile_key="exact-profile",
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
            "dataset_id": dataset_preview.DatasetId.RECORD3D,
            "sequence_id": "2026-06-03--18-26-32",
            "profile_key": "exact-profile",
            "frame_selection": dataset_preview.FrameSelectionConfig(),
            "include_depth": False,
            "path_config": context.path_config,
            "output_dir": Path(".artifacts") / "dataset-preview" / "record3d" / "2026-06-03--18-26-32",
        },
    )
    assert state.record3d_dataset.preview_is_running is True
    assert state.advio.preview_is_running is False
    assert state.tum_rgbd.preview_is_running is False
