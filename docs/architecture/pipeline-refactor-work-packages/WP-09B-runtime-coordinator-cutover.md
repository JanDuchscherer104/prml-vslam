# WP-09B Runtime Coordinator Cutover

Status: Draft

Owner: Unassigned

Dependencies:
- WP-00A Baseline Acceptance
- WP-03 Runtime Skeleton
- WP-03A Telemetry Status
- WP-04 Source Runtime
- WP-05 Bounded Runtimes
- WP-06 SLAM Runtime Live Updates
- WP-09A Target Config Launch Cutover

Decision:
- No backward compatibility is required for `RuntimeStageProgram`,
  `RuntimeExecutionState`, `StageRuntimeSpec`, or `StageCompletionPayload`.
  Replace the executable runtime path rather than layering new wrappers around
  the old program.

Owned paths:
- `src/prml_vslam/pipeline/runtime_manager.py`
- `src/prml_vslam/pipeline/runner.py`
- `src/prml_vslam/pipeline/ray_runtime/coordinator.py`
- `src/prml_vslam/pipeline/ray_runtime/stage_actors.py`
- `src/prml_vslam/pipeline/stages/base/proxy.py`
- `src/prml_vslam/pipeline/stages/base/ray.py`
- `src/prml_vslam/pipeline/stages/*/runtime.py`
- runtime and pipeline tests under `tests/`

Read-only context paths:
- `.agents/references/ray-runtime-patterns.md`
- `docs/architecture/pipeline-stage-refactor-target.md`
- `docs/architecture/pipeline-dto-migration-ledger.md`
- `src/prml_vslam/methods/`
- `src/prml_vslam/protocols/`
- `src/prml_vslam/pipeline/sinks/`

Target architecture sections:
- `Target Runtime Integration`
- `Current To Target Responsibility Map`
- `SLAM Stage Target Sequence`
- `Runtime Capability Versus Deployment`

Goal:
- Make `RuntimeManager`, `StageRunner`, `StageRuntimeProxy`, and stage-local
  runtime classes the only executable runtime path.
- Remove the old function-pointer runtime program and completion payload bag.

Current worktree note:
- `src/prml_vslam/pipeline/ray_runtime/stage_program.py` and
  `src/prml_vslam/pipeline/ray_runtime/stage_execution.py` are already gone
  from tracked source in the current worktree. Treat remaining references to
  those files as historical or migration-only notes, not as current executable
  ownership.

Out of scope:
- App/CLI snapshot presentation.
- Durable telemetry event deletion unless needed to prevent duplicate live
  projection.
- New distributed-Ray cluster attach, runtime-env, storage-locality, or on-prem
  design.

Implementation notes:
- Coordinator startup builds one `RuntimeManager` from the compiled `RunPlan`
  and target stage configs.
- `StageRunner` sequences bounded stages and stores `StageResult` values in
  `StageResultStore`.
- Stage input builders read only from `StageResultStore`; do not read from
  `RuntimeExecutionState`.
- Source, SLAM, ground alignment, trajectory evaluation, reconstruction, and
  summary stages return `StageResult` directly to `StageRunner` or the
  coordinator.
- Delete free `run_*` compatibility wrappers from `stage_execution.py` after
  their production callers are migrated.
- Delete `RuntimeStageProgram`, `RuntimeExecutionState`, `StageRuntimeSpec`,
  and `StageCompletionPayload` after coordinator execution no longer imports
  them.
- In the current worktree, the remaining `WP-09B` closure work is grep/test
  verification plus cleanup of stale notes and doc references; do not recreate
  deleted runtime-program wrappers just to satisfy historical package text.
- Fix the Ray deployment truth boundary. Either implement Ray-hosted
  `StageRuntimeProxy` invocation with actor creation, task refs, counters, and
  status projection, or reject `deployment_kind="ray"` with an explicit
  planning/preflight error. Do not accept `"ray"` while invoking in-process.
- Release source-to-SLAM credit immediately after the SLAM runtime or proxy has
  accepted and processed the frame. Rerun, observer, and payload materialization
  work must not participate in credit release.
- Prevent duplicate live snapshot projection. If legacy notices still exist
  while this package is underway, do not apply both `StageRuntimeUpdate` and
  translated backend notices to the same live snapshot fields.

DTO migration scope:
- Own final deletion of `StageCompletionPayload`, `RuntimeExecutionState`,
  `StageRuntimeSpec`, `RuntimeStageProgram`, and free stage execution wrappers.
- Own Ray proxy honesty for `deployment_kind="ray"`.

Termination criteria:
- Offline and streaming execution no longer import or instantiate
  `RuntimeStageProgram`.
- `StageCompletionPayload` has no production or test imports outside
  historical docs.
- Source-credit release is tested independently from observer/Rerun payload
  routing.
- Ray proxy behavior is either implemented or rejected before invocation.
- Duplicate live projection tests prove one backend update changes live
  snapshot counters once.

Required checks:
- `uv run pytest tests/test_pipeline.py tests/test_pipeline_runtime_skeleton.py`
- `uv run pytest tests/test_source_runtime.py tests/test_bounded_stage_runtimes.py tests/test_slam_stage_runtime.py`
- mocked offline and streaming run-service smoke tests
- stale-symbol greps for `StageCompletionPayload`, `RuntimeExecutionState`,
  `StageRuntimeSpec`, and `RuntimeStageProgram`
- `make lint`
- `git diff --check`

Known risks:
- Migrating only bounded stages but leaving streaming SLAM on the old actor
  wrapper will keep two runtime authorities alive.
- Materializing visualization payloads before credit release can silently
  reintroduce viewer backpressure into the SLAM hot path.
- Accepting fake Ray deployment support makes resource planning tests
  misleading.
