"""Deterministic artifact validation for offline experiment runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from prml_vslam.experiments.contracts import ExperimentRunSpec, ExperimentValidationResult
from prml_vslam.pipeline.config import RunConfig
from prml_vslam.pipeline.contracts.runtime import RunSnapshot, RunState
from prml_vslam.utils import RunArtifactPaths


def validate_run_artifacts(
    *,
    spec: ExperimentRunSpec,
    run_config: RunConfig,
    snapshot: RunSnapshot,
    allow_failure: bool,
) -> list[ExperimentValidationResult]:
    """Validate terminal state and configured artifact expectations for one run."""
    paths = RunArtifactPaths.build(spec.artifact_root)
    checks = [
        _check(
            spec,
            "terminal_state",
            snapshot.state in {RunState.COMPLETED, RunState.FAILED, RunState.STOPPED},
            snapshot.state.value,
            f"terminal state is {snapshot.state.value}",
        ),
        _check(
            spec,
            "run_completed",
            snapshot.state is RunState.COMPLETED or allow_failure,
            snapshot.state.value,
            snapshot.error_message,
        ),
        _path_check(spec, "artifact_root_exists", paths.artifact_root, require_non_empty=False),
    ]
    if run_config.stages.slam.enabled:
        checks.append(_path_check(spec, "slam_trajectory_exists", paths.trajectory_path))
        if run_config.stages.slam.outputs.emit_dense_points:
            checks.append(_path_check(spec, "slam_point_cloud_exists", paths.point_cloud_path))
    if run_config.visualization.export_viewer_rrd:
        checks.append(_path_check(spec, "rerun_recording_exists", paths.viewer_rrd_path))
    if run_config.stages.align_trajectory.enabled:
        checks.append(
            _path_check(
                spec,
                "trajectory_alignment_exists",
                paths.artifact_root / "evaluation" / "trajectory_alignment.json",
            )
        )
        checks.append(
            _path_check(
                spec,
                "aligned_trajectory_exists",
                paths.artifact_root / "evaluation" / "trajectory_sim3_aligned.tum",
            )
        )
    if run_config.stages.evaluate_trajectory.enabled:
        checks.append(_json_check(spec, "trajectory_metrics_parseable", paths.trajectory_metrics_path))
    if run_config.stages.align_cloud.enabled:
        checks.append(
            _json_check(spec, "cloud_alignment_parseable", paths.artifact_root / "evaluation" / "cloud_alignment.json")
        )
        checks.extend(
            _json_field_checks(
                spec,
                path=paths.artifact_root / "evaluation" / "cloud_alignment.json",
                fields=("fitness", "inlier_rmse_m"),
            )
        )
    return checks


def _check(
    spec: ExperimentRunSpec,
    check_name: str,
    passed: bool,
    status: str,
    message: str = "",
    artifact_path: Path | None = None,
) -> ExperimentValidationResult:
    return ExperimentValidationResult(
        experiment_id=spec.experiment_id,
        run_id=spec.run_id,
        item_id=spec.item_id,
        check_name=check_name,
        passed=passed,
        status=status,
        message=message,
        artifact_path=artifact_path,
    )


def _path_check(
    spec: ExperimentRunSpec,
    check_name: str,
    path: Path,
    *,
    require_non_empty: bool = True,
) -> ExperimentValidationResult:
    exists = path.exists()
    non_empty = path.is_dir() or (path.is_file() and path.stat().st_size > 0)
    passed = exists and (not require_non_empty or non_empty)
    status = "present" if passed else "missing"
    if exists and require_non_empty and not non_empty:
        status = "empty"
    return _check(spec, check_name, passed, status, artifact_path=path)


def _json_check(spec: ExperimentRunSpec, check_name: str, path: Path) -> ExperimentValidationResult:
    if not path.is_file() or path.stat().st_size == 0:
        return _check(spec, check_name, False, "missing", artifact_path=path)
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return _check(spec, check_name, False, "invalid_json", str(exc), artifact_path=path)
    return _check(spec, check_name, True, "parseable", artifact_path=path)


def _json_field_checks(
    spec: ExperimentRunSpec,
    *,
    path: Path,
    fields: tuple[str, ...],
) -> list[ExperimentValidationResult]:
    try:
        payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return [
            _check(spec, f"cloud_alignment_{field}_present", False, "missing", artifact_path=path) for field in fields
        ]
    return [
        _check(
            spec,
            f"cloud_alignment_{field}_present",
            field in payload,
            "present" if field in payload else "missing",
            artifact_path=path,
        )
        for field in fields
    ]
