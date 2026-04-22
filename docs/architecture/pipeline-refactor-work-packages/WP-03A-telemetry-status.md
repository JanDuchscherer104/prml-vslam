# WP-03A Telemetry Status

Status: Draft

Owner: Unassigned

Dependencies:
- WP-00A Baseline Acceptance
- WP-00B DTO Class Inventory Audit
- WP-01 Contracts

Owned paths:
- `docs/architecture/pipeline-refactor-work-packages/WP-03A-telemetry-status.md`
- telemetry/status target notes if split from the work-package file later
- focused telemetry/status tests created specifically for this package

Read-only context paths:
- `docs/architecture/pipeline-stage-refactor-target.md`
- `docs/architecture/pipeline-refactor-target-dir-tree.md`
- `docs/architecture/pipeline-stage-protocols-and-dtos.md`
- `docs/architecture/pipeline-dto-migration-ledger.md`
- `src/prml_vslam/pipeline/stages/base/contracts.py`
- `docs/architecture/pipeline-refactor-work-packages/WP-03-runtime-skeleton.md`
- `src/prml_vslam/pipeline/stages/base/proxy.py` if already created by WP-03
- `src/prml_vslam/pipeline/ray_runtime/`
- `.agents/references/ray-runtime-patterns.md`

Target architecture sections:
- `Status And Telemetry`
- `Runtime Protocol Taxonomy`
- `Target Runtime Integration`
- `Durable Run Events And Live Updates`
- `Target Snapshot Shape`


Goal:
- Freeze `StageRuntimeStatus` and runtime telemetry semantics before runtime-heavy implementation packages depend on them.

Out of scope:
- Distributed-Ray cluster attach, runtime-env, storage locality, or on-prem deployment design.
- Production runtime migration.
- App presentation changes.
- Replacing package-specific telemetry tests owned by later work packages.
- Changing `StageRuntimeStatus` field names or field shapes in
  `src/prml_vslam/pipeline/stages/base/contracts.py`. If field names or
  shapes need to change, reopen WP-01 or create an explicit follow-up.

Implementation notes:
- Use [Pipeline Stage Protocols And DTOs](../pipeline-stage-protocols-and-dtos.md)
  for current telemetry/status DTO behavior and
  [Pipeline DTO Migration Ledger](../pipeline-dto-migration-ledger.md) for
  target ownership/deletion gates.
- Read `.agents/references/ray-runtime-patterns.md` before defining Ray-hosted runtime telemetry, especially actor mailbox limitations, task-ref counters, State API diagnostics, and custom metrics.
- `StageRuntimeStatus` is the public pipeline status contract; proxy-internal submitted/completed/failed/in-flight counters surface only through it.
- Ray mailbox depth is not a portable queue-depth field. Only expose queue/backlog values for queues, credits, or buffers owned and measured by the pipeline/runtime.
- Freeze meanings for lifecycle state, progress, queue/backlog, submitted/completed/failed/in-flight counts, throughput, FPS, latency, executor identity, resource assignment, last warning/error, and status update timestamp.
- Use source timestamps for sensor/frame semantics, monotonic runtime time for latency/throughput/FPS, and wallclock time only for user-facing events/logs.
- Status may be pushed through `StageRuntimeUpdate` and polled through `status()`; both surfaces must have consistent field meanings.

## StageRuntimeStatus Field Semantics

WP-03A freezes the semantics of the WP-01 field names; it does not rename or
reshape them.

| Field | Semantics |
| --- | --- |
| `stage_key` | Stage whose runtime or proxy produced the status. |
| `lifecycle_state` | Current live lifecycle projection using `StageStatus`; terminal durable truth remains `StageOutcome.status`. |
| `progress_message` | Operator-facing progress detail. It is display text, not a parseable state machine. |
| `completed_steps` | Count of completed bounded progress units when the runtime can measure them. |
| `total_steps` | Expected bounded progress units when known; `None` means unknown or unbounded. |
| `progress_unit` | Unit label for progress counters, such as `frames`, `items`, or `stages`. |
| `queue_depth` | Runtime- or pipeline-owned queue/credit depth only; never Ray actor mailbox depth. |
| `backlog_count` | Known unprocessed work backlog when distinct from queue depth. |
| `submitted_count` | Work items or actor method calls accepted by the runtime/proxy. |
| `completed_count` | Submitted work items or actor method calls that completed successfully. |
| `failed_count` | Submitted work items or actor method calls that failed. |
| `in_flight_count` | Submitted work items or actor method calls accepted but not yet completed or failed. |
| `processed_items` | Domain-neutral count of items processed by the stage runtime. |
| `fps` | Frame throughput for frame-like workloads, computed from monotonic runtime time. |
| `throughput` | Generic item throughput for non-frame workloads, computed from monotonic runtime time. |
| `throughput_unit` | Unit label for `throughput`, such as `items/s` or `stages/s`. |
| `latency_ms` | Runtime-measured latency in milliseconds, computed from monotonic runtime time. |
| `last_warning` | Latest non-fatal warning text suitable for operator diagnostics. |
| `last_error` | Latest error text suitable for operator diagnostics. |
| `executor_id` | Substrate-neutral runtime/proxy identity, such as a local executor label or Ray actor label. |
| `resource_assignment` | Substrate-neutral resource assignment details. Do not expose raw Ray handles or private Ray objects. |
| `updated_at_ns` | Status update timestamp in nanoseconds. Use monotonic runtime time for latency/throughput/FPS and wallclock time only for user-facing events/logs. |

## Ray Telemetry Caveats

- Ray actor task order is a deployment detail, not a portable pipeline queue
  contract. Synchronous single-threaded actors preserve same submitter order
  only when out-of-order execution and task retries do not intervene; different
  submitters can interleave.
- Async or threaded actors do not guarantee actor method execution order, so
  status counters must be derived from proxy-owned task refs and runtime-owned
  counters rather than inferred from actor mailbox order.
- `StageRuntimeProxy` owns submitted task refs and derives
  submitted/completed/failed/in-flight counts from those refs. Coordinator, app,
  CLI, stage runners, and snapshots must not receive Ray object refs, actor
  handles, or mailbox handles.
- Ray State API and Dashboard data are diagnostic and may be stale or partial.
  They are not canonical pipeline state and must not override
  `StageRuntimeStatus`.
- Ray custom metrics such as `Counter`, `Gauge`, and `Histogram` are
  observability aids for runtime-owned counters. They can mirror status values
  but do not define the pipeline status contract.

Termination criteria:
- `StageRuntimeStatus` field semantics are documented clearly enough for runtime, SLAM, snapshot, and Rerun packages to implement without redefining them.
- Time-domain rules are documented for source timestamp, monotonic runtime time, and wallclock time.
- Ray mailbox, task-ref, State API, and custom-metric caveats are referenced.
- Runtime, SLAM, Rerun, and snapshot/event packages list this work package as a dependency.

Required checks:
- `git diff --check`
- grep for `StageRuntimeStatus`, `ray-runtime-patterns.md`, `monotonic`,
  `wallclock`, `source timestamp`, `mailbox`, `same submitter`, `async`,
  `Counter`, `Gauge`, `Histogram`, and `State API` in the telemetry/status
  docs
- targeted tests added by this package, if any

Known risks:
- Letting each runtime define telemetry independently will produce incompatible status semantics.
- Treating Ray-observed actor state as canonical pipeline state can make snapshots stale or inconsistent.
- Mixing source time, monotonic time, and wallclock time will make latency and throughput metrics misleading.
