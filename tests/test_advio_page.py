from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np

import prml_vslam.app.pages.datasets as advio_page
from prml_vslam.app.models import AppState, Record3DDatasetPoseSource
from prml_vslam.interfaces import CameraIntrinsics, FrameTransform, Observation, ObservationProvenance
from prml_vslam.sources.datasets.advio import AdvioPoseSource
from prml_vslam.sources.datasets.contracts import LocalSceneStatus
from prml_vslam.sources.datasets.record3d import Record3DSceneMetadata
from prml_vslam.sources.datasets.record3d.record3d_loading import (
    Record3DArchiveFrame,
    Record3DArchiveMetadata,
    Record3DOfflineSample,
)


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
    status = SimpleNamespace(
        scene=SimpleNamespace(sequence_id=15),
        arcore_ready=True,
        arkit_ready=True,
    )

    options = advio_page._advio_preview_pose_sources([status], sequence_id=15)

    assert options == [
        AdvioPoseSource.GROUND_TRUTH,
        AdvioPoseSource.ARCORE,
        AdvioPoseSource.NONE,
        AdvioPoseSource.ARKIT,
    ]


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
    rows = advio_page._record3d_rows_with_normalized_status(
        rows,
        advio_page.NormalizedDatasetSnapshot(
            records=[],
            issues=[],
            stats_rows=[],
            metadata_rows=[],
            sequence_ids={"local-capture"},
            default_profile_sequence_ids={"local-capture"},
            profile_counts={"local-capture": 1},
        ),
    )

    assert rows == [
        {
            "Scene": "local-capture",
            "Sequence": "local-capture",
            "Source": "Local-only",
            "Index": "Local",
            "Packed Size (MB)": 42.0,
            "Local": True,
            "Replay Ready": True,
            "Offline Ready": True,
            "Normalized": True,
            "Normalized Profiles": 1,
        }
    ]


def test_record3d_loop_preview_requires_default_normalized_profile(monkeypatch) -> None:
    captured: dict[str, list[LocalSceneStatus[Record3DSceneMetadata]]] = {}
    status = LocalSceneStatus[Record3DSceneMetadata](
        scene=Record3DSceneMetadata(
            sequence_id="capture",
            archive_name="capture.r3d",
            display_name="capture",
            archive_size_bytes=1,
        ),
        sequence_dir=Path(".data/record3d"),
        archive_path=Path(".data/record3d/capture.r3d"),
        replay_ready=True,
        offline_ready=True,
    )
    context = SimpleNamespace(
        state=SimpleNamespace(record3d_dataset=SimpleNamespace(preview_include_depth=True)),
        record3d_dataset_service=SimpleNamespace(),
    )
    normalized = advio_page.NormalizedDatasetSnapshot(
        records=[],
        issues=[],
        stats_rows=[],
        metadata_rows=[],
        sequence_ids={"capture"},
        default_profile_sequence_ids=set(),
        profile_counts={"capture": 1},
    )
    monkeypatch.setattr(
        advio_page, "_render_loop_preview_impl", lambda **kwargs: captured.update(statuses=kwargs["statuses"])
    )

    advio_page._render_record3d_loop_preview(context, [status], normalized)

    assert captured["statuses"] == []


def test_record3d_sequence_details_uses_metadata_trajectory(monkeypatch) -> None:
    captured: dict[str, object] = {}
    sample = _record3d_sample()
    monkeypatch.setattr(
        advio_page,
        "_render_sequence_details",
        lambda **kwargs: captured.update(kwargs),
    )

    advio_page._render_record3d_sequence_details(sample)

    trajectories = captured["trajectories"]
    assert trajectories[0][0] == "Record3D / ARKit"
    assert np.allclose(trajectories[0][1].positions_xyz, np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]))
    assert captured["metrics"] == (("Depth", "Available"),)
    assert captured["intrinsics"] == sample.depth_intrinsics


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


def _record3d_sample() -> Record3DOfflineSample:
    intrinsics = CameraIntrinsics(fx=1.0, fy=1.0, cx=0.5, cy=0.5, width_px=2, height_px=2)
    return Record3DOfflineSample(
        sequence_id="demo",
        sequence_name="Demo",
        archive_path=Path(".data/record3d/demo.r3d"),
        metadata=Record3DArchiveMetadata(
            K=[1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.5, 0.5, 1.0],
            w=2,
            h=2,
            dw=2,
            dh=2,
            fps=30.0,
            frameTimestamps=[0.0, 1.0],
            poses=[[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0], [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0]],
        ),
        frames=[
            Record3DArchiveFrame(index=0, jpg_name="0.jpg", depth_name="0.depth", confidence_name="0.conf"),
            Record3DArchiveFrame(index=1, jpg_name="1.jpg", depth_name="1.depth", confidence_name="1.conf"),
        ],
        rgb_intrinsics=intrinsics,
        depth_intrinsics=intrinsics,
        timestamps_ns=[0, 1_000_000_000],
        poses_world_camera=[
            FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
            FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=0.0, tz=0.0),
        ],
    )
