"""Bounded runtime adapter for projection-only run summaries."""

from __future__ import annotations

from prml_vslam.pipeline.contracts.provenance import StageManifest, StageStatus
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.finalization import project_summary
from prml_vslam.pipeline.stages.base.contracts import StageResult, StageRuntimeStatus
from prml_vslam.pipeline.stages.base.protocols import OfflineStageRuntime
from prml_vslam.pipeline.stages.summary.contracts import SummaryRuntimeInput


class SummaryRuntime(OfflineStageRuntime[SummaryRuntimeInput]):
    """Project durable run summaries from terminal stage outcomes.

    The runtime is the final pipeline stage and should remain pure projection:
    it hashes, records, and writes what earlier stages already produced. New
    trajectory, cloud, or efficiency metrics belong in eval-owned stages before
    summary executes.
    """

    def __init__(self) -> None:
        self._status = StageRuntimeStatus(stage_key=StageKey.SUMMARY)
        # TODO(pipeline-refactor/WP-10): Remove this side channel when summary
        # manifests are consumed only through durable artifacts or a target
        # summary payload.
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
            summary, stage_manifests, outcome = project_summary(
                request=input_payload.request,
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


__all__ = ["SummaryRuntime", "SummaryRuntimeInput"]
