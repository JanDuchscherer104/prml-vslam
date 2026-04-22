# WP-09C Live Events Handles Cutover

Status: Draft

Owner: Unassigned

Dependencies:
- WP-00A Baseline Acceptance
- WP-01 Contracts
- WP-03A Telemetry Status
- WP-06 SLAM Runtime Live Updates
- WP-07 Visualization Rerun
- WP-08 Snapshot Events Payloads
- WP-09B Runtime Coordinator Cutover

Decision:
- No backward compatibility is required for telemetry `RunEvent` variants,
  legacy live handles, or backend notice envelopes. Durable events become
  lifecycle/provenance only; live data travels through `StageRuntimeUpdate`.

Owned paths:
- `src/prml_vslam/pipeline/contracts/events.py`
- `src/prml_vslam/pipeline/contracts/handles.py`
- `src/prml_vslam/pipeline/contracts/runtime.py`
- `src/prml_vslam/pipeline/snapshot_projector.py`
- `src/prml_vslam/pipeline/ray_runtime/coordinator.py`
- `src/prml_vslam/pipeline/ray_runtime/stage_actors.py`
- `src/prml_vslam/pipeline/ray_runtime/common.py`
- `src/prml_vslam/pipeline/sinks/rerun.py`
- `src/prml_vslam/pipeline/sinks/rerun_policy.py`
- `src/prml_vslam/pipeline/stages/slam/runtime.py`
- `src/prml_vslam/pipeline/stages/slam/visualization.py`
- `src/prml_vslam/interfaces/slam.py`
- `src/prml_vslam/methods/events.py`
- snapshot, Rerun, live-update, and payload tests under `tests/`

Read-only context paths:
- `src/prml_vslam/app/`
- `src/prml_vslam/visualization/`
- `.agents/skills/rerun-slam-integration/SKILL.md`
- `docs/architecture/pipeline-stage-refactor-target.md`
- `docs/architecture/pipeline-dto-migration-ledger.md`

Target architecture sections:
- `Runtime Updates, Events, And Visualization Items`
- `Durable Run Events And Live Updates`
- `Transient Payload Handles`
- `Target Snapshot Shape`

Goal:
- Remove live telemetry from durable `RunEvent`.
- Replace old live handles and backend notice envelopes with
  `StageRuntimeUpdate`, `VisualizationItem`, and `TransientPayloadRef`.

Out of scope:
- App/CLI rendering changes unless needed by event and handle removal.
- Runtime sequencing changes beyond live update and payload routing.
- New visualization modalities.

Implementation notes:
- Delete `StageProgress`, `StageProgressed`, `PacketObserved`,
  `FramePacketSummary`, `BackendNoticeReceived`, and `EventTier` once no
  production path consumes them.
- `StageCompleted` and `StageFailed` carry `StageOutcome` only. Remove rich
  payload fields from durable completion events when snapshots derive payload
  views from `StageResult`, artifacts, or target projection helpers.
- Delete `ArrayHandle`, `PreviewHandle`, and `BlobHandle` after all live reads
  use `TransientPayloadRef` through `read_payload(...)`.
- Remove `read_array(...)` APIs from `PipelineBackend`, `RayPipelineBackend`,
  and `RunService` after app/CLI callers use `read_payload(...)`.
- Move or retire `BackendEvent`, `PoseEstimated`, `KeyframeAccepted`,
  `KeyframeVisualizationReady`, `MapStatsUpdated`, `BackendWarning`,
  `BackendError`, and `SessionClosed` from `interfaces.slam`. Method semantic
  DTOs belong in `methods`, and visualization descriptors belong in
  `pipeline.stages.slam.visualization`.
- Delete `methods.events.translate_slam_update(...)` when the SLAM runtime
  emits `SlamUpdate` semantic events and `VisualizationItem`s directly.
- Rerun sink consumes only `StageRuntimeUpdate.visualizations` and
  `TransientPayloadRef` payload maps/resolvers. Remove `observe(event=...)`
  and legacy event policy branches.
- Snapshot projection consumes live status and semantic events only through
  `StageRuntimeUpdate`.
- Keep Rerun SDK imports isolated to sink, policy, helper, and visualization
  validation modules.

DTO migration scope:
- Own final deletion or rehome for telemetry events, old handles,
  backend notice envelopes, and the old event-tier discriminator.
- `TransientPayloadRef`, `StageRuntimeUpdate`, `VisualizationItem`, and
  `StageRuntimeStatus` are target objects and are not deleted.

Termination criteria:
- Durable `RunEvent` union contains only run lifecycle, stage lifecycle,
  artifact registration, and terminal outcome events.
- No production import of `ArrayHandle`, `PreviewHandle`, `BlobHandle`,
  `BackendNoticeReceived`, `PacketObserved`, `FramePacketSummary`,
  `StageProgress`, or `StageProgressed` remains.
- Rerun tests assert `StageRuntimeUpdate` / `VisualizationItem` routing only.
- `interfaces.slam` no longer imports pipeline contracts.
- App and backend payload reads use `TransientPayloadRef`.

Required checks:
- `uv run pytest tests/test_pipeline.py tests/test_streaming_visualization.py`
- `uv run pytest tests/test_rerun_layout_semantics.py tests/test_rerun_timeline_semantics.py`
- `uv run pytest tests/test_slam_visualization_adapter.py tests/test_slam_stage_runtime.py`
- import-boundary grep for Rerun SDK usage outside sink/policy/helper modules
- stale-symbol greps for every deleted event, handle, and backend notice symbol
- `make lint`
- `git diff --check`

Known risks:
- Leaving old event branches in Rerun policy will keep legacy handle DTOs alive.
- Removing `BackendError` without a replacement runtime failure path can hide
  streaming backend failures.
- Persisting `TransientPayloadRef` in durable events or summaries would make
  ephemeral payloads look like scientific artifacts.
