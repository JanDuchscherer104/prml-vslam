"""Bounded runtime adapter for projection-only run summaries."""

from __future__ import annotations

from prml_vslam.interfaces.artifacts import ArtifactRef
from prml_vslam.pipeline.contracts.events import StageOutcome
from prml_vslam.pipeline.contracts.provenance import RunSummary, StageManifest, StageStatus
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.finalization import stable_hash, write_json
from prml_vslam.pipeline.stages.base.contracts import StageResult, StageRuntimeStatus
from prml_vslam.pipeline.stages.base.protocols import OfflineStageRuntime
from prml_vslam.pipeline.stages.summary.contracts import SummaryRuntimeInput


class SummaryRuntime(OfflineStageRuntime[SummaryRuntimeInput]):
    """Project durable run summaries from terminal stage outcomes.

    The runtime is the final pipeline stage and should remain pure projection:
    it hashes, records, and writes what earlier stages already produced. New
    trajectory or cloud metrics belong in eval-owned stages before
    summary executes.
    """

    def __init__(self) -> None:
        self._status = StageRuntimeStatus(stage_key=StageKey.SUMMARY)
        # TODO(pipeline-refactor/post-target-alignment): Remove this side
        # channel when summary manifests are consumed only through durable
        # artifacts or a target summary payload.
        self._stage_manifests: list[StageManifest] = []

    @property
    def stage_manifests(self) -> list[StageManifest]:
        """Return manifests produced by the most recent summary run."""
        return list(self._stage_manifests)

    def status(self) -> StageRuntimeStatus:
        """Return the latest summary runtime status."""
        return self._status

    def stop(self) -> None:
        """Mark the bounded runtime as stopped."""
        self._status = self._status.model_copy(update={"lifecycle_state": StageStatus.STOPPED})

    def run_offline(self, input_payload: SummaryRuntimeInput) -> StageResult:
        """Project summary artifacts and return a canonical stage result.

        The result payload is the pipeline-owned :class:`RunSummary`; the
        stage-manifest side channel remains a migration compatibility surface
        until manifests are consumed only through durable artifacts.
        """
        self._status = self._status.model_copy(
            update={
                "lifecycle_state": StageStatus.RUNNING,
                "progress_message": "Writing run summary.",
            }
        )
        try:
            summary, stage_manifests, outcome = _project_summary(
                experiment_name=input_payload.experiment_name,
                mode=input_payload.mode,
                plan=input_payload.plan,
                run_paths=input_payload.run_paths,
                stage_outcomes=input_payload.stage_outcomes,
            )
        except Exception as exc:
            self._status = self._status.model_copy(
                update={
                    "lifecycle_state": StageStatus.FAILED,
                    "last_error": str(exc),
                }
            )
            raise
        self._stage_manifests = list(stage_manifests)
        result = StageResult(
            stage_key=StageKey.SUMMARY,
            payload=summary,
            outcome=outcome,
            final_runtime_status=StageRuntimeStatus(
                stage_key=StageKey.SUMMARY,
                lifecycle_state=StageStatus.COMPLETED,
                progress_message="Run summary complete.",
                completed_steps=len(stage_manifests),
                total_steps=len(stage_manifests),
                progress_unit="stages",
                processed_items=len(stage_manifests),
            ),
        )
        self._status = result.final_runtime_status
        return result


def _project_summary(
    *,
    experiment_name,
    mode,
    plan,
    run_paths,
    stage_outcomes: list[StageOutcome],
) -> tuple[RunSummary, list[StageManifest], StageOutcome]:
    """Project persisted provenance from terminal stage outcomes."""
    stage_manifests = [
        StageManifest(
            stage_id=outcome.stage_key,
            config_hash=outcome.config_hash,
            input_fingerprint=outcome.input_fingerprint,
            output_paths={name: artifact.path for name, artifact in outcome.artifacts.items()},
            status=outcome.status,
            cache=outcome.cache,
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
        config_hash=stable_hash({"experiment_name": experiment_name, "mode": mode.value}),
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


__all__ = ["SummaryRuntime", "SummaryRuntimeInput"]
