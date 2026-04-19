"""Pure helpers for summary projection and stable artifact serialization.

These helpers turn executed :class:`StageOutcome` values into durable pipeline
provenance without reaching back into runtime actors. They are intentionally
side-effect light and deterministic apart from the explicit JSON writes they
perform.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from prml_vslam.pipeline.contracts.artifacts import ArtifactRef
from prml_vslam.pipeline.contracts.events import StageOutcome, StageStatus
from prml_vslam.pipeline.contracts.plan import RunPlan
from prml_vslam.pipeline.contracts.provenance import RunSummary, StageManifest
from prml_vslam.pipeline.contracts.request import RunRequest
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.utils import BaseConfig, RunArtifactPaths


def project_summary(
    *,
    request: RunRequest,
    plan: RunPlan,
    run_paths: RunArtifactPaths,
    stage_outcomes: list[StageOutcome],
) -> tuple[RunSummary, list[StageManifest], StageOutcome]:
    """Project persisted provenance from terminal stage outcomes.

    Returns:
        The run-level summary, the per-stage manifests derived from the passed
        outcomes, and the summary stage's own :class:`StageOutcome`.
    """
    stage_manifests = [
        StageManifest(
            stage_id=outcome.stage_key,
            config_hash=outcome.config_hash,
            input_fingerprint=outcome.input_fingerprint,
            output_paths={name: artifact.path for name, artifact in outcome.artifacts.items()},
            status=outcome.status,
        )
        for outcome in stage_outcomes
    ]
    summary = RunSummary(
        run_id=plan.run_id,
        artifact_root=plan.artifact_root,
        stage_status={manifest.stage_id: manifest.status for manifest in stage_manifests},
    )
    write_json(run_paths.summary_path, summary)
    write_json(run_paths.stage_manifests_path, stage_manifests)
    summary_outcome = StageOutcome(
        stage_key=StageKey.SUMMARY,
        status=StageStatus.COMPLETED,
        config_hash=stable_hash({"experiment_name": request.experiment_name, "mode": request.mode.value}),
        input_fingerprint=stable_hash(stage_outcomes),
        artifacts={
            "run_summary": ArtifactRef(
                path=run_paths.summary_path,
                kind="json",
                fingerprint=stable_hash(summary),
            ),
            "stage_manifests": ArtifactRef(
                path=run_paths.stage_manifests_path,
                kind="json",
                fingerprint=stable_hash(stage_manifests),
            ),
        },
        metrics={"stage_count": len(stage_outcomes)},
    )
    return summary, stage_manifests, summary_outcome


def stable_hash(payload: object) -> str:
    """Compute a stable SHA-256 fingerprint for JSON-normalizable payloads."""
    normalized_payload = BaseConfig.to_jsonable(payload)
    encoded = json.dumps(normalized_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


# TODO: should be handle dby BaseConfig or via native BaseModel functionalities!
def write_json(path: Path, payload: object) -> None:
    """Persist one JSON artifact with deterministic formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(BaseConfig.to_jsonable(payload), indent=2, sort_keys=True), encoding="utf-8")


__all__ = [
    "project_summary",
    "stable_hash",
    "write_json",
]
