# Pipeline Refactor Review A01 Actions

This note extracts action items from
[review-A01.md](../../.agents/work/pipeline-refactor-2/review-A01.md). It is a
planning companion to [pipeline-stage-refactor-target.md](./pipeline-stage-refactor-target.md),
[pipeline-stage-refactor-pruning.md](./pipeline-stage-refactor-pruning.md), and
[reconstruction-stage-target.md](./reconstruction-stage-target.md).

The review confirms that the stage architecture direction is broadly right,
but it identifies missing architecture decisions around same-LAN execution,
source locality, storage, telemetry, remote attach, and the deletion path for
the current `ray_runtime/stage_program.py` / `stage_execution.py` split.

## Locked Decisions From Review Triage

- Same-LAN distributed execution should be planned now but not implemented in
  the first runtime simplification slice.
- Distributed execution target is Ray on the same Wi-Fi/LAN only; no WAN,
  cloud, VPN, or artifact-service assumptions.
- Durable artifacts and prepared inputs assume a shared filesystem visible to
  all Ray nodes.
- Source placement uses manual node names for now.
- Remote attach target is coordinator attach via Ray address/namespace plus
  snapshot, event, and payload APIs.
- Remote worker log aggregation is deferred.
- Owned queues/backpressure are deferred. Use current credits/counters and
  basic per-stage timing first.
- Do not introduce a new observer bus abstraction. Keep coordinator/update
  forwarding simple while preserving the rule that live updates are observer
  data, not stage-to-stage inputs.
- Add a current-to-target stage naming migration map.
- Trajectory alignment diagnostics belong in `evaluate.trajectory`.

## Primary Runtime Refactor Actions

### Distributed Ray / Same-LAN Execution

Action items:

- Document Ray execution modes: local head and attach existing same-LAN Ray
  cluster.
- Add target config for Ray address, namespace, runtime environment profile,
  `log_to_driver`, `include_dashboard`, and named coordinator actor lookup.
  Keep private Ray init flags such as `_skip_env_hook` backend-internal unless
  the project has a stable public reason to expose them.
- Keep same-LAN scope explicit: no WAN, cloud, VPN, or artifact service in the
  first distributed target.
- Preserve first runtime simplification slice as local/single-node compatible.

Acceptance criteria for future implementation:

- local head startup still works
- existing same-LAN Ray cluster attach works
- app/CLI can reconnect by Ray address, namespace, and run/coordinator name
- stage placement can be inspected through Ray actor/resource metadata

### Source Locality And Node Placement

Action items:

- Document source placement as manual node names for same-LAN Ray runs.
- Specify that USB-bound sources must run on the node physically attached to
  the device.
- Specify that Wi-Fi sources may run on a node that can reach the phone on the
  same LAN.
- Specify that dataset replay expects the shared filesystem or dataset cache to
  be readable from the selected source/replay node.
- Preserve `SequenceManifest` and prepared inputs as the normalized handoff to
  downstream stages.

Acceptance criteria for future implementation:

- Record3D USB source can be pinned to a named node
- Wi-Fi source can be pinned to a named node on the same LAN
- TUM/ADVIO replay can run from a node that sees the shared dataset/artifact
  paths
- downstream stages can read prepared manifests and inputs from the shared
  filesystem

### Shared Artifact And Transient Payload Storage

Action items:

- Make shared filesystem the target durable artifact strategy for same-LAN
  runs.
- Keep durable artifacts under the run artifact root.
- Keep transient payloads behind backend/service resolver APIs, not direct Ray
  object refs in public contracts.
- Defer dedicated artifact service and per-node copy-up scratch.

Acceptance criteria for future implementation:

- durable artifacts remain readable after worker exit
- transient payloads are readable through a resolver while live
- read-after-eviction yields a typed not-found result
- payload store usage and eviction counters can be surfaced later through
  runtime status

### Telemetry And Queue/Backpressure Deferral

Action items:

- Keep `StageRuntimeStatus` as the canonical live status DTO.
- Defer generic owned queues/mailboxes for all stages.
- In the first runtime slice, report lifecycle, progress, errors, wall time,
  submitted/completed/failed/in-flight work counts, and current streaming
  credits/counters.
- Treat queue depth/backlog metrics as accurate only where the pipeline owns
  the counter, such as current streaming source-to-SLAM credits.
- For Ray-backed runtimes, prefer Ray-native actor task refs and
  application-level metrics for FPS, latency, throughput, and owned
  queue/credit counters; do not expose raw Ray mailbox depth as a portable
  pipeline contract.

Acceptance criteria for future implementation:

- offline stages report status/progress/timing
- streaming SLAM reports current credit/backpressure counters
- docs do not promise generic queue-depth metrics until owned queues exist

Ray observability references:

- [Ray actors](https://docs.ray.io/en/latest/ray-core/actors.html): methods
  called on the same actor execute serially in call order by default.
- [Ray State CLI/API](https://docs.ray.io/en/latest/ray-observability/reference/cli.html):
  useful for task/actor diagnostics, but alpha and not guaranteed to return a
  fully live, complete snapshot.
- [Ray custom metrics](https://docs.ray.io/en/latest/ray-observability/user-guides/add-app-metrics.html):
  use `Counter`, `Gauge`, and `Histogram` for actor/stage application metrics.
- [Ray actor termination](https://docs.ray.io/en/latest/ray-core/actors/terminating-actors.html):
  immediate kill fails current, pending, and future tasks, while graceful actor
  exit waits for previously submitted tasks.

### Rerun / Update Observer Flow

Action items:

- Strengthen the rule that `StageRuntimeUpdate` is for live observation,
  metrics/status, UI, and Rerun forwarding.
- Keep `StageResult` and typed payloads as the stage-to-stage execution
  contract.
- Keep `VisualizationItem` sink-facing only.
- Do not introduce a new observer bus abstraction in the first slice; use
  simple coordinator/update forwarding.
- Forbid stages and DTOs from emitting Rerun entity paths, timelines, or SDK
  commands.

Acceptance criteria for future implementation:

- SLAM updates can reach snapshot/status and Rerun without becoming durable
  telemetry JSONL
- no stage or DTO imports the Rerun SDK
- sink policy owns entity paths, timelines, styling, and SDK calls

### App / CLI Remote Coordinator Attach

Action items:

- Document coordinator attach via Ray address, namespace, and coordinator actor
  name.
- Plan backend/service APIs for snapshot reads, event tailing, and payload
  resolution.
- Plan remote viewer/export endpoint display.
- Defer worker log aggregation beyond minimal Ray/local logs.

Acceptance criteria for future implementation:

- CLI can attach to an existing run and tail events
- Streamlit can monitor a run created on the same-LAN Ray cluster
- payload refs resolve through backend/service APIs
- local preview-only behavior remains app-owned

### Stage Runtime Deletion Path

Action items:

- Move stage behavior into `pipeline/stages/<stage>/runtime.py`.
- Keep `pipeline/stages/<stage>/actor.py` only for stateful, streaming,
  GPU-heavy, or remote-placement stages.
- Make `RuntimeManager` build and wire runtimes.
- Use `StageRunner` for generic lifecycle handling and `StageResultStore` for
  shared dependency access between stages.
- Make `RunCoordinatorActor` sequence only through runtime protocols.
- Define `stage_program.py` and `stage_execution.py` as migration scaffolding,
  not target architecture.

Acceptance criteria for future implementation:

- no stage-specific execution logic remains in `ray_runtime/stage_program.py`
- no bounded helper registry remains in `stage_execution.py`
- each stage can be understood by opening its stage module
- grep/import audit proves stage behavior lives under `pipeline/stages/*`

### DTO Ownership Cleanup

Action items:

- Keep the documented DTO taxonomy explicit:
  shared semantic DTO, package-local semantic DTO, transport-safe event,
  runtime update, durable provenance, and transient payload ref.
- Move live SLAM DTOs out of shared `interfaces` if that remains the chosen
  direction.
- Keep stage-local wrappers private unless they cross package boundaries.
- Keep public pipeline contracts generic.

Acceptance criteria for future implementation:

- `interfaces` no longer imports pipeline transport/handle DTOs
- no output bag duplicates `StageResult`
- no generic catch-all DTO package appears
- per-package contract placement follows documented ownership rules

### Naming Migration Map

Action items:

- Add a current-to-target stage naming map to the target architecture.
- Use this map whenever docs mention both current executable code and future
  target vocabulary.

Initial map:

| Current name | Target name | Notes |
| --- | --- | --- |
| `ingest` | `source` | Source normalization and prepared benchmark inputs. |
| `slam` | `slam` | Same public stage concept; target runtime is `SlamStageRuntime` implementing offline and streaming protocols, with Ray hosting hidden behind `StageRuntimeHandle` when needed. |
| `gravity.align` | `gravity.align` | Canonical gravity-alignment key. |
| `trajectory.evaluate` | `evaluate.trajectory` | Target docs use compact verb namespace. |
| `reference.reconstruct` | `reconstruction` | Target umbrella stage with reference/3DGS/future variants. |
| `cloud.evaluate` | `evaluate.cloud` | Diagnostic metric placeholder. |
| `efficiency.evaluate` | removed | Deleted from the target vocabulary during WP-10. |
| `summary` | `summary` | Projection-only stage. |

## Work Package Representation Options

The review recommends turning action groups into issue-sized tickets. The
triage did not choose one representation, so keep all options available:

| Representation | Shape | When to use |
| --- | --- | --- |
| Plan-only architecture packages | Goal, add, verify, and dependency notes in architecture docs. | Best while decisions are still moving. |
| Issue-ready tickets | Copyable issue text with owner placeholders, dependencies, and acceptance criteria. | Best when implementation ownership is ready. |
| Prioritized checklist | Short ordered list without full issue detail. | Best for quick planning or milestone triage. |

## Separate `evaluate.trajectory` Diagnostic Backlog

The review also contains a trajectory-alignment diagnostic proposal. Treat it
as a separate evaluation feature, not as part of the core runtime refactor.

Action items:

- Add an eval-owned artifact such as `TrajectoryAlignmentDiagnostic`.
- Compute global best-fit SE(3) alignment between synchronized trajectories.
- Store global alignment matrix and `log6` deviation from identity.
- Compute per-pose residual transforms and residual `log6` series.
- Compute per-edge relative-motion residuals for frame-consistency diagnosis.
- Add prefix or sliding-window alignment drift.
- Add plots over path length for global bias, per-pose residuals, per-edge
  residuals, and prefix/window drift.
- Optionally emit neutral `VisualizationItem` values for the Rerun sink or
  plotting layer.
- Document that evo's Umeyama alignment is position-based and does not prove
  full pose-orientation consistency.

Acceptance criteria for future implementation:

- diagnostic runs inside `evaluate.trajectory`
- numeric diagnostic artifact is persisted
- plotting output is generated or available through plotting helpers
- SLAM stage and Rerun sink do not own evaluation computation

## First Slice Boundary

The first runtime simplification slice remains focused on:

- local execution compatibility
- `StageResult`
- keyed result store
- stage-local runtimes
- unified `SlamStageRuntime` as a Ray-hostable runtime behind
  `StageRuntimeHandle`
- minimal `RuntimeManager`
- compatible source, Rerun, and snapshot behavior

It should not be expanded to include:

- full same-LAN implementation
- generic owned queues
- remote worker log aggregation
- full app/CLI remote UI polish
- trajectory-alignment diagnostics
- future cloud/efficiency/reconstruction implementations
