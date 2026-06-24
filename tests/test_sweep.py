"""Unit tests for the sweep config, expansion, and RunConfig factory."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest
from pydantic import ValidationError

from prml_vslam.methods.stage.backend_config import MethodId
from prml_vslam.pipeline.sweep import (
    SweepConfig,
    SweepDataset,
    SweepMeta,
    SweepRunItem,
    _build_run_id,
    _load_slam_stage_from_template,
    build_run_config_from_sweep_item,
    expand_sweep,
    load_sweep_config,
)
from prml_vslam.sources.config import (
    AdvioSourceConfig,
    Record3DDatasetSourceConfig,
    TumRgbdSourceConfig,
)
from prml_vslam.sources.contracts import ReferenceSource
from prml_vslam.sources.datasets.build_config import NormalizedDatasetBuildConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VISTA_SLAM_SECTION = """\
[stages.slam]
enabled  = true
num_gpus = 1.0

    [stages.slam.outputs]
    emit_dense_points  = true
    emit_sparse_points = false

    [stages.slam.backend]
    method_id   = "vista"
    max_frames  = 50
    random_seed = 43
"""

_MAST3R_SLAM_SECTION = """\
[stages.slam]
enabled  = true
num_gpus = 1.0

    [stages.slam.outputs]
    emit_dense_points  = true
    emit_sparse_points = false

    [stages.slam.backend]
    method_id   = "mast3r"
    max_frames  = 50
    random_seed = 43
"""

_LINGBOT_SLAM_SECTION = """\
[stages.slam]
enabled  = true
num_gpus = 1.0

    [stages.slam.outputs]
    emit_dense_points  = true
    emit_sparse_points = false

    [stages.slam.backend]
    method_id = "lingbot_map"
"""


def _write_template(tmp_path: Path, filename: str, content: str) -> Path:
    path = tmp_path / filename
    path.write_text(content, encoding="utf-8")
    return path


def _minimal_sweep_toml(
    *,
    vista_template: Path,
    mast3r_template: Path,
    name: str = "test-sweep",
    output_dir: str = ".artifacts/sweeps",
    extra_datasets: str = "",
) -> str:
    return f"""\
[sweep]
name       = "{name}"
output_dir = "{output_dir}"

[[datasets]]
dataset_id          = "tum_rgbd"
sequence_id         = "freiburg1_xyz"
frame_stride        = 1
baseline_source     = "ground_truth"
align_trajectory    = true
evaluate_trajectory = true

{extra_datasets}

[methods.vista]
config_path = "{vista_template.as_posix()}"

[methods.mast3r]
config_path = "{mast3r_template.as_posix()}"
"""


# ---------------------------------------------------------------------------
# SweepConfig validation
# ---------------------------------------------------------------------------


def test_sweep_config_rejects_empty_datasets() -> None:
    with pytest.raises(ValidationError, match="datasets"):
        SweepConfig.model_validate(
            {
                "sweep": {"name": "s", "output_dir": "."},
                "datasets": [],
                "methods": {"vista": {"config_path": "x.toml"}},
            }
        )


def test_sweep_config_rejects_empty_methods() -> None:
    with pytest.raises(ValidationError, match="methods"):
        SweepConfig.model_validate(
            {
                "sweep": {"name": "s", "output_dir": "."},
                "datasets": [{"dataset_id": "tum_rgbd", "sequence_id": "seq1"}],
                "methods": {},
            }
        )


def test_sweep_config_rejects_non_slug_method_id() -> None:
    with pytest.raises((ValidationError, ValueError), match="not safe"):
        SweepConfig.model_validate(
            {
                "sweep": {"name": "s", "output_dir": "."},
                "datasets": [{"dataset_id": "tum_rgbd", "sequence_id": "seq1"}],
                "methods": {"bad method!": {"config_path": "x.toml"}},
            }
        )


def test_sweep_config_rejects_non_slug_sweep_name() -> None:
    with pytest.raises((ValidationError, ValueError), match="not safe"):
        SweepMeta.model_validate({"name": "bad name here", "output_dir": "."})


def test_sweep_config_rejects_duplicate_dataset_sequence_pair() -> None:
    with pytest.raises((ValidationError, ValueError), match="Duplicate"):
        SweepConfig.model_validate(
            {
                "sweep": {"name": "s", "output_dir": "."},
                "datasets": [
                    {"dataset_id": "tum_rgbd", "sequence_id": "seq1"},
                    {"dataset_id": "tum_rgbd", "sequence_id": "seq1"},
                ],
                "methods": {"vista": {"config_path": "x.toml"}},
            }
        )


def test_sweep_config_accepts_same_sequence_id_different_dataset() -> None:
    cfg = SweepConfig.model_validate(
        {
            "sweep": {"name": "s", "output_dir": "."},
            "datasets": [
                {"dataset_id": "tum_rgbd", "sequence_id": "seq1"},
                {"dataset_id": "advio", "sequence_id": "seq1"},
            ],
            "methods": {"vista": {"config_path": "x.toml"}},
        }
    )
    assert len(cfg.datasets) == 2


def test_sweep_dataset_rejects_ambiguous_sampling() -> None:
    with pytest.raises(ValidationError, match="frame_stride.*target_fps"):
        SweepDataset.model_validate(
            {
                "dataset_id": "tum_rgbd",
                "sequence_id": "freiburg1_xyz",
                "frame_stride": 2,
                "target_fps": 30.0,
            }
        )


@pytest.mark.parametrize("config_type", [AdvioSourceConfig, Record3DDatasetSourceConfig, TumRgbdSourceConfig])
def test_dataset_source_configs_reject_ambiguous_sampling(
    config_type: type[AdvioSourceConfig] | type[Record3DDatasetSourceConfig] | type[TumRgbdSourceConfig],
) -> None:
    with pytest.raises(ValidationError, match="frame_stride.*target_fps"):
        config_type.model_validate(
            {
                "sequence_id": "sequence",
                "frame_stride": 2,
                "target_fps": 30.0,
            }
        )


def test_normalized_dataset_build_config_rejects_empty_sequence_ids() -> None:
    with pytest.raises(ValidationError, match="sequence_ids"):
        NormalizedDatasetBuildConfig.model_validate(
            {
                "sources": [
                    {
                        "source_id": "tum_rgbd",
                        "sequence_ids": [],
                    }
                ]
            }
        )


def test_normalized_dataset_build_config_rejects_ambiguous_sampling() -> None:
    with pytest.raises(ValidationError, match="frame_stride.*target_fps"):
        NormalizedDatasetBuildConfig.model_validate(
            {
                "sources": [
                    {
                        "source_id": "tum_rgbd",
                        "sequence_ids": ["freiburg1_xyz"],
                        "frame_stride": 2,
                        "target_fps": 30.0,
                    }
                ]
            }
        )


def test_normalized_dataset_build_config_expands_shared_fields_for_all_datasets() -> None:
    cfg = NormalizedDatasetBuildConfig.model_validate(
        {
            "sources": [
                {
                    "source_id": "advio",
                    "sequence_ids": ["advio-01", "advio-02"],
                    "target_fps": 15.0,
                    "rgb_max_width_px": 280,
                    "rgb_dimension_multiple": 7,
                },
                {
                    "source_id": "tum_rgbd",
                    "sequence_ids": ["freiburg1_xyz"],
                    "target_fps": 30.0,
                    "rgb_max_width_px": 392,
                    "rgb_dimension_multiple": 14,
                    "reference_cloud": {
                        "depth_stride_px": 6,
                        "max_points": 1234,
                        "random_seed": 19,
                    },
                },
                {
                    "source_id": "record3d_dataset",
                    "sequence_ids": ["scene-a"],
                    "target_fps": 24.0,
                    "rgb_max_width_px": 448,
                    "rgb_dimension_multiple": 28,
                    "reference_cloud": {
                        "depth_stride_px": 10,
                        "max_points": 4321,
                        "random_seed": 23,
                        "min_confidence": 2,
                    },
                },
            ]
        }
    )

    advio_a, advio_b, tum, record3d = cfg.source_configs()

    assert isinstance(advio_a, AdvioSourceConfig)
    assert isinstance(advio_b, AdvioSourceConfig)
    assert [advio_a.sequence_id, advio_b.sequence_id] == ["advio-01", "advio-02"]
    assert {advio_a.target_fps, advio_b.target_fps} == {15.0}
    assert {advio_a.rgb_max_width_px, advio_b.rgb_max_width_px} == {280}
    assert {advio_a.rgb_dimension_multiple, advio_b.rgb_dimension_multiple} == {7}

    assert isinstance(tum, TumRgbdSourceConfig)
    assert tum.sequence_id == "freiburg1_xyz"
    assert tum.target_fps == 30.0
    assert tum.rgb_max_width_px == 392
    assert tum.rgb_dimension_multiple == 14
    assert tum.reference_cloud.depth_stride_px == 6
    assert tum.reference_cloud.max_points == 1234
    assert tum.reference_cloud.random_seed == 19

    assert isinstance(record3d, Record3DDatasetSourceConfig)
    assert record3d.sequence_id == "scene-a"
    assert record3d.target_fps == 24.0
    assert record3d.rgb_max_width_px == 448
    assert record3d.rgb_dimension_multiple == 28
    assert record3d.reference_cloud.depth_stride_px == 10
    assert record3d.reference_cloud.max_points == 4321
    assert record3d.reference_cloud.random_seed == 23
    assert record3d.reference_cloud.min_confidence == 2


def test_normalized_dataset_build_config_expands_independent_reference_cloud_configs() -> None:
    cfg = NormalizedDatasetBuildConfig.model_validate(
        {
            "sources": [
                {
                    "source_id": "tum_rgbd",
                    "sequence_ids": ["freiburg1_xyz", "freiburg1_room"],
                    "reference_cloud": {
                        "depth_stride_px": 6,
                        "max_points": 1234,
                        "random_seed": 19,
                    },
                }
            ]
        }
    )

    first, second = cfg.source_configs()

    assert isinstance(first, TumRgbdSourceConfig)
    assert isinstance(second, TumRgbdSourceConfig)
    first.reference_cloud.max_points = 99
    assert second.reference_cloud.max_points == 1234


@pytest.mark.parametrize(
    "config_path",
    sorted(Path(".configs/sweeps").glob("*sweep.toml")),
    ids=lambda path: path.name,
)
def test_checked_in_record3d_sweep_entries_use_arkit_baseline(config_path: Path) -> None:
    datasets = tomllib.loads(config_path.read_text(encoding="utf-8"))["datasets"]
    record3d_rows = [row for row in datasets if row["dataset_id"] == "record3d_dataset"]

    assert record3d_rows
    assert {row["baseline_source"] for row in record3d_rows} == {ReferenceSource.ARKIT.value}


@pytest.mark.parametrize(
    "config_path",
    sorted(Path(".configs/sweeps").glob("*sweep.toml")),
    ids=lambda path: path.name,
)
def test_checked_in_sweep_method_keys_match_template_backend_ids(config_path: Path) -> None:
    cfg = load_sweep_config(config_path)
    for item in expand_sweep(cfg):
        assert item.slam_stage.backend is not None
        assert item.method_id == item.slam_stage.backend.method_id.value
        assert item.run_id.endswith(f"-{item.method_id}")


def test_benchmark_datastore_config_covers_full_sweep_sources() -> None:
    datastore_sources = NormalizedDatasetBuildConfig.from_toml(
        Path(".configs/datasets/benchmark-vslam-datastore.toml")
    ).source_configs()
    datastore_keys = {(source.source_id, source.sequence_id) for source in datastore_sources}
    full_sweep_keys = {
        (row["dataset_id"], row["sequence_id"])
        for config_path in sorted(Path(".configs/sweeps").glob("full-*-sweep.toml"))
        for row in tomllib.loads(config_path.read_text(encoding="utf-8"))["datasets"]
    }

    assert datastore_keys == full_sweep_keys


def test_full_vista_sweep_uses_bounded_frame_count() -> None:
    cfg = load_sweep_config(Path(".configs/sweeps/full-vista-sweep.toml"))
    items = expand_sweep(cfg)

    assert items
    assert {item.method_id for item in items} == {MethodId.VISTA.value}
    assert {item.slam_stage.backend.max_frames for item in items if item.slam_stage.backend is not None} == {512}


# ---------------------------------------------------------------------------
# Template loading
# ---------------------------------------------------------------------------


def test_load_slam_stage_from_template_ignores_non_slam_sections(tmp_path: Path) -> None:
    template = tmp_path / "method.toml"
    template.write_text(
        "[stages.source.backend]\nsource_id = 'video'\nvideo_path = 'x.mp4'\n\n" + _VISTA_SLAM_SECTION,
        encoding="utf-8",
    )
    slam = _load_slam_stage_from_template(template)
    assert slam.enabled is True
    assert slam.backend is not None
    assert slam.backend.method_id is MethodId.VISTA


def test_load_slam_stage_from_template_preserves_backend_settings(tmp_path: Path) -> None:
    template = _write_template(tmp_path, "vista.toml", _VISTA_SLAM_SECTION)
    slam = _load_slam_stage_from_template(template)
    assert slam.backend is not None
    assert slam.backend.method_id is MethodId.VISTA
    assert slam.backend.max_frames == 50
    assert slam.outputs.emit_dense_points is True
    assert slam.outputs.emit_sparse_points is False


def test_load_slam_stage_from_template_raises_on_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        _load_slam_stage_from_template(tmp_path / "nonexistent.toml")


def test_load_slam_stage_from_template_raises_when_slam_section_absent(tmp_path: Path) -> None:
    template = tmp_path / "no_slam.toml"
    template.write_text("[stages.source.backend]\nsource_id = 'video'\n", encoding="utf-8")
    with pytest.raises(ValueError, match="no \\[stages.slam\\] section"):
        _load_slam_stage_from_template(template)


# ---------------------------------------------------------------------------
# expand_sweep — ordering and run IDs
# ---------------------------------------------------------------------------


def test_expand_sweep_stable_ordering(tmp_path: Path) -> None:
    vista = _write_template(tmp_path, "vista.toml", _VISTA_SLAM_SECTION)
    mast3r = _write_template(tmp_path, "mast3r.toml", _MAST3R_SLAM_SECTION)

    cfg = SweepConfig.model_validate(
        {
            "sweep": {"name": "ord", "output_dir": str(tmp_path)},
            "datasets": [
                {"dataset_id": "tum_rgbd", "sequence_id": "seq-a"},
                {"dataset_id": "advio", "sequence_id": "seq-b"},
            ],
            "methods": {
                "vista": {"config_path": str(vista)},
                "mast3r": {"config_path": str(mast3r)},
            },
        }
    )
    items = expand_sweep(cfg)
    run_ids = [i.run_id for i in items]

    assert run_ids == [
        "ord-tum_rgbd-seq-a-vista",
        "ord-tum_rgbd-seq-a-mast3r",
        "ord-advio-seq-b-vista",
        "ord-advio-seq-b-mast3r",
    ]


def test_expand_sweep_deterministic_run_ids(tmp_path: Path) -> None:
    vista = _write_template(tmp_path, "vista.toml", _VISTA_SLAM_SECTION)
    cfg = SweepConfig.model_validate(
        {
            "sweep": {"name": "my-sweep", "output_dir": str(tmp_path)},
            "datasets": [{"dataset_id": "tum_rgbd", "sequence_id": "freiburg1_xyz"}],
            "methods": {"vista": {"config_path": str(vista)}},
        }
    )
    items = expand_sweep(cfg)
    assert len(items) == 1
    assert items[0].run_id == "my-sweep-tum_rgbd-freiburg1_xyz-vista"


def test_expand_sweep_fails_on_missing_template_file(tmp_path: Path) -> None:
    cfg = SweepConfig.model_validate(
        {
            "sweep": {"name": "s", "output_dir": str(tmp_path)},
            "datasets": [{"dataset_id": "tum_rgbd", "sequence_id": "seq1"}],
            "methods": {"vista": {"config_path": str(tmp_path / "missing.toml")}},
        }
    )
    with pytest.raises(FileNotFoundError):
        expand_sweep(cfg)


def test_expand_sweep_fails_when_template_has_no_slam_section(tmp_path: Path) -> None:
    bad = tmp_path / "bad.toml"
    bad.write_text("[stages.source.backend]\nsource_id = 'video'\n", encoding="utf-8")
    cfg = SweepConfig.model_validate(
        {
            "sweep": {"name": "s", "output_dir": str(tmp_path)},
            "datasets": [{"dataset_id": "tum_rgbd", "sequence_id": "seq1"}],
            "methods": {"vista": {"config_path": str(bad)}},
        }
    )
    with pytest.raises(ValueError, match="no \\[stages.slam\\] section"):
        expand_sweep(cfg)


def test_expand_sweep_rejects_method_key_backend_method_id_mismatch(tmp_path: Path) -> None:
    lingbot = _write_template(tmp_path, "lingbot.toml", _LINGBOT_SLAM_SECTION)
    cfg = SweepConfig.model_validate(
        {
            "sweep": {"name": "s", "output_dir": str(tmp_path)},
            "datasets": [{"dataset_id": "tum_rgbd", "sequence_id": "seq1"}],
            "methods": {"lingbot": {"config_path": str(lingbot)}},
        }
    )
    with pytest.raises(ValueError, match="Use \\[methods\\.lingbot_map\\]"):
        expand_sweep(cfg)


def test_expand_sweep_item_carries_sweep_metadata(tmp_path: Path) -> None:
    vista = _write_template(tmp_path, "vista.toml", _VISTA_SLAM_SECTION)
    out = tmp_path / "out"
    cfg = SweepConfig.model_validate(
        {
            "sweep": {"name": "meta-test", "output_dir": str(out)},
            "datasets": [{"dataset_id": "advio", "sequence_id": "advio-15"}],
            "methods": {"vista": {"config_path": str(vista)}},
        }
    )
    items = expand_sweep(cfg)
    item = items[0]
    assert item.sweep_name == "meta-test"
    assert item.output_dir == out
    assert item.method_id == "vista"
    assert item.dataset.dataset_id == "advio"


# ---------------------------------------------------------------------------
# load_sweep_config
# ---------------------------------------------------------------------------


def test_load_sweep_config_roundtrip(tmp_path: Path) -> None:
    vista = _write_template(tmp_path, "vista.toml", _VISTA_SLAM_SECTION)
    mast3r = _write_template(tmp_path, "mast3r.toml", _MAST3R_SLAM_SECTION)
    toml_content = _minimal_sweep_toml(vista_template=vista, mast3r_template=mast3r)
    sweep_path = tmp_path / "sweep.toml"
    sweep_path.write_text(toml_content, encoding="utf-8")

    cfg = load_sweep_config(sweep_path)
    assert cfg.sweep.name == "test-sweep"
    assert len(cfg.datasets) == 1
    assert len(cfg.methods) == 2


def test_load_sweep_config_raises_on_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_sweep_config(tmp_path / "nonexistent.toml")


# ---------------------------------------------------------------------------
# build_run_config_from_sweep_item
# ---------------------------------------------------------------------------


def _make_item(
    tmp_path: Path,
    *,
    dataset_id: str = "tum_rgbd",
    sequence_id: str = "freiburg1_xyz",
    method_id: str = "vista",
    align_trajectory: bool = False,
    evaluate_trajectory: bool = False,
    align_ground: bool = False,
    reconstruction: bool = False,
    align_cloud: bool = False,
    evaluate_cloud: bool = False,
    baseline_source: ReferenceSource | None = None,
) -> SweepRunItem:
    vista = _write_template(tmp_path, "vista.toml", _VISTA_SLAM_SECTION)
    slam = _load_slam_stage_from_template(vista)
    run_id = _build_run_id(
        sweep_name="s",
        dataset_id=dataset_id,
        sequence_id=sequence_id,
        method_id=method_id,
    )
    return SweepRunItem(
        run_id=run_id,
        sweep_name="s",
        output_dir=tmp_path / "out",
        dataset=SweepDataset(
            dataset_id=dataset_id,
            sequence_id=sequence_id,
            baseline_source=baseline_source,
            align_trajectory=align_trajectory,
            evaluate_trajectory=evaluate_trajectory,
            align_ground=align_ground,
            reconstruction=reconstruction,
            align_cloud=align_cloud,
            evaluate_cloud=evaluate_cloud,
        ),
        method_id=method_id,
        slam_stage=slam,
    )


def test_build_run_config_uses_tum_rgbd_source_backend(tmp_path: Path) -> None:
    item = _make_item(tmp_path, dataset_id="tum_rgbd", sequence_id="freiburg1_xyz")
    run_cfg = build_run_config_from_sweep_item(item)
    assert isinstance(run_cfg.stages.source.backend, TumRgbdSourceConfig)
    assert run_cfg.stages.source.backend.sequence_id == "freiburg1_xyz"


def test_build_run_config_uses_advio_source_backend(tmp_path: Path) -> None:
    item = _make_item(tmp_path, dataset_id="advio", sequence_id="advio-15")
    run_cfg = build_run_config_from_sweep_item(item)
    assert isinstance(run_cfg.stages.source.backend, AdvioSourceConfig)
    assert run_cfg.stages.source.backend.sequence_id == "advio-15"


def test_build_run_config_uses_record3d_dataset_source_backend(tmp_path: Path) -> None:
    item = _make_item(tmp_path, dataset_id="record3d_dataset", sequence_id="2026-06-03--18-29-08")
    run_cfg = build_run_config_from_sweep_item(item)
    assert isinstance(run_cfg.stages.source.backend, Record3DDatasetSourceConfig)
    assert run_cfg.stages.source.backend.sequence_id == "2026-06-03--18-29-08"


def test_build_run_config_rejects_unknown_dataset_id(tmp_path: Path) -> None:
    item = _make_item(tmp_path, dataset_id="unknown_src", sequence_id="seq")
    with pytest.raises(ValueError, match="Unknown dataset_id"):
        build_run_config_from_sweep_item(item)


def test_build_run_config_sets_experiment_name_to_run_id(tmp_path: Path) -> None:
    item = _make_item(tmp_path)
    run_cfg = build_run_config_from_sweep_item(item)
    assert run_cfg.experiment_name == item.run_id


def test_build_run_config_sets_output_dir(tmp_path: Path) -> None:
    item = _make_item(tmp_path)
    run_cfg = build_run_config_from_sweep_item(item)
    assert run_cfg.output_dir == item.output_dir


def test_build_run_config_injects_stage_flags(tmp_path: Path) -> None:
    item = _make_item(
        tmp_path,
        align_trajectory=True,
        evaluate_trajectory=True,
        align_ground=True,
        reconstruction=True,
        align_cloud=True,
        evaluate_cloud=True,
    )
    run_cfg = build_run_config_from_sweep_item(item)
    assert run_cfg.stages.align_trajectory.enabled is True
    assert run_cfg.stages.evaluate_trajectory.enabled is True
    assert run_cfg.stages.align_ground.enabled is True
    assert run_cfg.stages.reconstruction.enabled is True
    assert run_cfg.stages.align_cloud.enabled is True
    assert run_cfg.stages.evaluate_cloud.enabled is True


def test_build_run_config_disabled_stages_by_default(tmp_path: Path) -> None:
    item = _make_item(tmp_path)
    run_cfg = build_run_config_from_sweep_item(item)
    assert run_cfg.stages.align_trajectory.enabled is False
    assert run_cfg.stages.evaluate_trajectory.enabled is False
    assert run_cfg.stages.align_ground.enabled is False
    assert run_cfg.stages.reconstruction.enabled is False
    assert run_cfg.stages.align_cloud.enabled is False
    assert run_cfg.stages.evaluate_cloud.enabled is False


def test_build_run_config_summary_always_enabled(tmp_path: Path) -> None:
    item = _make_item(tmp_path)
    run_cfg = build_run_config_from_sweep_item(item)
    assert run_cfg.stages.summary.enabled is True


def test_build_run_config_visualization_defaults_off(tmp_path: Path) -> None:
    item = _make_item(tmp_path)
    run_cfg = build_run_config_from_sweep_item(item)
    assert run_cfg.visualization.connect_live_viewer is False
    assert run_cfg.visualization.export_viewer_rrd is False


def test_build_run_config_carries_slam_stage_verbatim(tmp_path: Path) -> None:
    item = _make_item(tmp_path)
    run_cfg = build_run_config_from_sweep_item(item)
    assert run_cfg.stages.slam.backend is not None
    assert run_cfg.stages.slam.backend.method_id is MethodId.VISTA
    assert run_cfg.stages.slam.backend.max_frames == 50


def test_build_run_config_baseline_source_propagates(tmp_path: Path) -> None:
    item = _make_item(
        tmp_path,
        align_trajectory=True,
        evaluate_trajectory=True,
        baseline_source=ReferenceSource.ARKIT,
    )
    run_cfg = build_run_config_from_sweep_item(item)
    assert run_cfg.stages.align_trajectory.baseline_source is ReferenceSource.ARKIT
    assert run_cfg.stages.evaluate_trajectory.evaluation.baseline_source is ReferenceSource.ARKIT


def test_build_run_config_defaults_record3d_baseline_to_arkit(tmp_path: Path) -> None:
    item = _make_item(
        tmp_path,
        dataset_id="record3d_dataset",
        sequence_id="2026-06-03--18-17-10",
        align_trajectory=True,
        evaluate_trajectory=True,
    )
    run_cfg = build_run_config_from_sweep_item(item)

    assert run_cfg.stages.align_trajectory.baseline_source is ReferenceSource.ARKIT
    assert run_cfg.stages.evaluate_trajectory.evaluation.baseline_source is ReferenceSource.ARKIT


def test_sweep_toml_record3d_omitted_baseline_expands_to_arkit(tmp_path: Path) -> None:
    vista = _write_template(tmp_path, "vista.toml", _VISTA_SLAM_SECTION)
    mast3r = _write_template(tmp_path, "mast3r.toml", _MAST3R_SLAM_SECTION)
    sweep_path = tmp_path / "sweep.toml"
    sweep_path.write_text(
        _minimal_sweep_toml(
            vista_template=vista,
            mast3r_template=mast3r,
            extra_datasets="""
[[datasets]]
dataset_id          = "record3d_dataset"
sequence_id         = "2026-06-03--18-17-10"
align_trajectory    = true
evaluate_trajectory = true
""",
        ),
        encoding="utf-8",
    )

    cfg = load_sweep_config(sweep_path)
    item = next(item for item in expand_sweep(cfg) if item.dataset.dataset_id == "record3d_dataset")
    run_cfg = build_run_config_from_sweep_item(item)

    assert run_cfg.stages.align_trajectory.baseline_source is ReferenceSource.ARKIT
    assert run_cfg.stages.evaluate_trajectory.evaluation.baseline_source is ReferenceSource.ARKIT


# ---------------------------------------------------------------------------
# SweepRunItem serialisability (required for plan-sweep-config JSON output)
# ---------------------------------------------------------------------------


def test_sweep_run_item_serialises_to_json(tmp_path: Path) -> None:
    item = _make_item(tmp_path)
    dumped = item.model_dump(mode="json")
    # Round-trip through json.dumps must not raise
    serialised = json.dumps(dumped)
    assert item.run_id in serialised
