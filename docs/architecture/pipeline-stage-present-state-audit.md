# Pipeline Stage Present-State Audit

This document is the current-state counterpart to
[pipeline-stage-refactor-target.md](./pipeline-stage-refactor-target.md). It
describes how the pipeline, stages, DTOs, configs, runtime helpers, actors, and
factories are placed today, then calls out issues, redundancies, diffuse
responsibilities, and definitions that are currently in awkward or incorrect
locations.

Boundary: this document is diagnostic. It does not define the desired target
architecture. Target module layout, target UML, and implementation-order
decisions belong in
[pipeline-stage-refactor-target.md](./pipeline-stage-refactor-target.md).

Read this together with:

- [Current executable stage protocols and DTOs](./pipeline-stage-protocols-and-dtos.md)
- [Target refactor architecture](./pipeline-stage-refactor-target.md)
- [Package ownership requirements](../../src/prml_vslam/REQUIREMENTS.md)
- [Pipeline requirements](../../src/prml_vslam/pipeline/REQUIREMENTS.md)
- [Refactor notes](../../src/prml_vslam/REFACTOR_PLAN.md)

## Executive Summary

The present pipeline is typed and functional, but stage concepts are spread
across several unrelated modules:

- stage identity and availability live in
  [stage_registry.py](../../src/prml_vslam/pipeline/stage_registry.py)
- request/config fragments live in
  [pipeline/contracts/request.py](../../src/prml_vslam/pipeline/contracts/request.py)
- runtime phase wiring lives in
  [ray_runtime/stage_program.py](../../src/prml_vslam/pipeline/ray_runtime/stage_program.py)
- bounded stage implementations live in
  [ray_runtime/stage_execution.py](../../src/prml_vslam/pipeline/ray_runtime/stage_execution.py)
- stateful actors live in
  [ray_runtime/stage_actors.py](../../src/prml_vslam/pipeline/ray_runtime/stage_actors.py)
- orchestration, status, sinks, streaming credits, and finalization live in
  [ray_runtime/coordinator.py](../../src/prml_vslam/pipeline/ray_runtime/coordinator.py)
- source muxing lives in
  [source_resolver.py](../../src/prml_vslam/pipeline/source_resolver.py)
- SLAM backend muxing lives separately in
  [methods/factory.py](../../src/prml_vslam/methods/factory.py)

The main present-state issue is not that the code is untyped. It is typed, but
the stage abstraction is implicit. There is no single module where one can see
for a stage: config, input DTO, output DTO, runtime target, status telemetry,
resource policy, backend muxing, and Rerun/event integration.

## Present-State Module Tree

The current stage architecture is not organized as stage modules. It is
organized around pipeline contracts, a registry, Ray runtime helpers, and
method wrappers.

```text
src/prml_vslam/pipeline/
├── contracts/
│   ├── request.py       # RunRequest, SourceSpec, SlamStageConfig, placement/runtime policy
│   ├── stages.py        # StageKey, StageDefinition, StageAvailability
│   ├── plan.py          # RunPlan and RunPlanStage
│   ├── events.py        # RunEvent, StageOutcome, runtime event vocabulary
│   ├── runtime.py       # RunSnapshot, StreamingRunSnapshot, RunState
│   ├── handles.py       # transient bulk payload handles
│   └── provenance.py    # RunSummary, StageManifest, StageStatus
├── stage_registry.py    # stage order, availability, expected outputs
├── source_resolver.py   # SourceSpec -> OfflineSequenceSource muxing
├── placement.py         # PlacementPolicy -> RayActorOptions translation
├── finalization.py      # summary projection, stable_hash, write_json
├── ingest.py            # source manifest materialization helpers
├── backend.py           # PipelineBackend protocol and PipelineRuntimeSource alias
├── backend_ray.py       # RayPipelineBackend
├── run_service.py       # app/CLI facade
├── ray_runtime/
│   ├── coordinator.py   # authoritative run coordinator, event fanout, streaming credits
│   ├── stage_program.py # phase-specific stage function wiring
│   ├── stage_execution.py # bounded stage helper implementations
│   ├── stage_actors.py  # OfflineSlamStageActor, StreamingSlamStageActor, PacketSourceActor
│   └── common.py        # Ray handles, artifact maps, backend_config_payload
└── sinks/
    ├── jsonl.py
    ├── rerun.py
    └── rerun_policy.py
```

Related packages:

```text
src/prml_vslam/
├── interfaces/          # shared DTOs, but also imports pipeline handles in slam.py
├── protocols/           # source and packet stream protocols
├── methods/             # backend configs, backend factory, SLAM protocols, method wrappers
├── benchmark/           # benchmark policy config
├── eval/                # metric contracts and services
├── alignment/           # ground alignment config/service
├── visualization/       # Rerun helpers, config, validation DTOs
├── io/                  # transport adapters
└── datasets/            # dataset catalogs, normalization, benchmark references
```

## Present-State Architecture

```mermaid
flowchart TB
    App["CLI / Streamlit"]
    Service["RunService"]
    Backend["RayPipelineBackend"]
    Request["RunRequest"]
    Registry["StageRegistry"]
    Plan["RunPlan"]
    Coordinator["RunCoordinatorActor"]
    Program["RuntimeStageProgram"]

    SourceResolver["OfflineSourceResolver"]
    StageExecution["stage_execution.py\nbounded stage helpers"]
    StageActors["stage_actors.py\nSLAM + packet actors"]
    MethodFactory["BackendFactory"]
    EventSink["JsonlEventSink / RerunSinkActor"]
    Projector["SnapshotProjector"]

    App --> Service --> Backend
    Backend --> Request
    Request --> Registry --> Plan
    Backend --> Coordinator
    Coordinator --> Program
    Coordinator --> SourceResolver
    Program --> StageExecution
    Program --> StageActors
    StageActors --> MethodFactory
    Coordinator --> EventSink
    Coordinator --> Projector

    classDef app fill:#E7F6EE,stroke:#2E8B57,color:#222222;
    classDef pipeline fill:#ECECFF,stroke:#9370DB,color:#222222;
    classDef runtime fill:#FFF4DD,stroke:#C28A2C,color:#222222;
    classDef external fill:#FBEAEA,stroke:#B85042,color:#222222;

    class App,Service app;
    class Request,Registry,Plan,Projector pipeline;
    class Backend,Coordinator,Program,StageExecution,StageActors,SourceResolver,EventSink runtime;
    class MethodFactory external;
```

Present-state facts:

- There is no `pipeline/stages/` package.
- There is no generic `StageConfig` base.
- There is no generic `StageRuntime` protocol.
- There is no generic `StageRuntimeStatus` DTO.
- Some stage config lives in `RunRequest`; some stage behavior lives in
  `RuntimeStageProgram`; some stage execution lives in helper functions; some
  stage execution lives in Ray actors.
- Planning is side-effect free, but runtime target construction is not
  config-driven at the stage level.

## Present Stage Wiring

```mermaid
flowchart LR
    subgraph Planning["planning"]
        Request["RunRequest"]
        Registry["StageRegistry.default()"]
        Plan["RunPlan"]
    end

    subgraph RuntimeProgram["runtime phase wiring"]
        RuntimeStageProgram["RuntimeStageProgram.default()"]
        RuntimeExecutionState["RuntimeExecutionState"]
        StageCompletionPayload["StageCompletionPayload"]
    end

    subgraph BoundedHelpers["bounded helper functions"]
        IngestFn["run_ingest_stage()"]
        SlamOfflineFn["run_offline_slam_stage()"]
        GroundFn["run_ground_alignment_stage()"]
        TrajFn["run_trajectory_evaluation_stage()"]
        RefReconFn["run_reference_reconstruction_stage()"]
        SummaryFn["run_summary_stage()"]
    end

    subgraph Actors["Ray actors"]
        OfflineSlam["OfflineSlamStageActor"]
        StreamingSlam["StreamingSlamStageActor"]
        PacketSource["PacketSourceActor"]
    end

    Request --> Registry --> Plan --> RuntimeStageProgram
    RuntimeStageProgram --> RuntimeExecutionState
    RuntimeStageProgram --> IngestFn
    RuntimeStageProgram --> SlamOfflineFn
    RuntimeStageProgram --> GroundFn
    RuntimeStageProgram --> TrajFn
    RuntimeStageProgram --> RefReconFn
    RuntimeStageProgram --> SummaryFn
    SlamOfflineFn --> OfflineSlam
    RuntimeStageProgram --> StreamingSlam
    PacketSource --> StreamingSlam
    IngestFn --> StageCompletionPayload
    OfflineSlam --> StageCompletionPayload
    StreamingSlam --> StageCompletionPayload
    GroundFn --> StageCompletionPayload
    TrajFn --> StageCompletionPayload
    RefReconFn --> StageCompletionPayload
    SummaryFn --> StageCompletionPayload
```

Key contact points:

- [RunRequest](../../src/prml_vslam/pipeline/contracts/request.py#L175)
- [SlamStageConfig](../../src/prml_vslam/pipeline/contracts/request.py#L150)
- [StageRegistry.default()](../../src/prml_vslam/pipeline/stage_registry.py#L136)
- [RuntimeExecutionState](../../src/prml_vslam/pipeline/ray_runtime/stage_program.py#L38)
- [StageCompletionPayload](../../src/prml_vslam/pipeline/ray_runtime/stage_program.py#L60)
- [StageRuntimeSpec](../../src/prml_vslam/pipeline/ray_runtime/stage_program.py#L118)
- [bounded stage helpers](../../src/prml_vslam/pipeline/ray_runtime/stage_execution.py#L60)
- [stage actors](../../src/prml_vslam/pipeline/ray_runtime/stage_actors.py#L42)

## Current Stage Execution Flow

[RuntimeStageProgram.default()](../../src/prml_vslam/pipeline/ray_runtime/stage_program.py#L140)
is the current runtime phase router. It binds each available
[`StageKey`](../../src/prml_vslam/pipeline/contracts/stages.py#L12) to
hardcoded function pointers in
[`StageRuntimeSpec`](../../src/prml_vslam/pipeline/ray_runtime/stage_program.py#L118),
then executes only the entrypoints that apply to the current phase:

| Stage | Offline phase | Streaming prepare phase | Streaming finalize phase |
| --- | --- | --- | --- |
| `ingest` | `_run_ingest()` -> [run_ingest_stage()](../../src/prml_vslam/pipeline/ray_runtime/stage_execution.py#L60) | `_run_ingest()` -> [run_ingest_stage()](../../src/prml_vslam/pipeline/ray_runtime/stage_execution.py#L60) | none |
| `slam` | `_run_slam_offline()` -> [run_offline_slam_stage()](../../src/prml_vslam/pipeline/ray_runtime/stage_execution.py#L101) -> [OfflineSlamStageActor.run()](../../src/prml_vslam/pipeline/ray_runtime/stage_actors.py#L46) | `_run_slam_streaming_prepare()` -> [RunCoordinatorActor.start_streaming_slam_stage()](../../src/prml_vslam/pipeline/ray_runtime/coordinator.py#L471) | `_run_slam_streaming_finalize()` -> [RunCoordinatorActor.close_streaming_slam_stage()](../../src/prml_vslam/pipeline/ray_runtime/coordinator.py#L510) |
| `gravity.align` | `_run_ground_alignment()` -> [run_ground_alignment_stage()](../../src/prml_vslam/pipeline/ray_runtime/stage_execution.py#L179) | none | `_run_ground_alignment()` -> [run_ground_alignment_stage()](../../src/prml_vslam/pipeline/ray_runtime/stage_execution.py#L179) |
| `trajectory.evaluate` | `_run_trajectory()` -> [run_trajectory_evaluation_stage()](../../src/prml_vslam/pipeline/ray_runtime/stage_execution.py#L137) | none | `_run_trajectory()` -> [run_trajectory_evaluation_stage()](../../src/prml_vslam/pipeline/ray_runtime/stage_execution.py#L137), skipped after streaming error or stop |
| `reference.reconstruct` | `_run_reference_reconstruction()` -> [run_reference_reconstruction_stage()](../../src/prml_vslam/pipeline/ray_runtime/stage_execution.py#L212) | none | `_run_reference_reconstruction()` -> [run_reference_reconstruction_stage()](../../src/prml_vslam/pipeline/ray_runtime/stage_execution.py#L212) |
| `summary` | `_run_summary()` -> [run_summary_stage()](../../src/prml_vslam/pipeline/ray_runtime/stage_execution.py#L257) | none | `_run_summary()` -> [run_summary_stage()](../../src/prml_vslam/pipeline/ray_runtime/stage_execution.py#L257) |

Offline execution starts in
[RunCoordinatorActor._run_offline()](../../src/prml_vslam/pipeline/ray_runtime/coordinator.py#L340).
The coordinator resolves the source through
[OfflineSourceResolver](../../src/prml_vslam/pipeline/source_resolver.py#L46)
unless a runtime source was injected, builds one
[`StageExecutionContext`](../../src/prml_vslam/pipeline/ray_runtime/stage_execution.py#L31),
and calls
[`RuntimeStageProgram.execute_offline()`](../../src/prml_vslam/pipeline/ray_runtime/stage_program.py#L222).
For each available planned stage, the program emits stage-start callbacks,
invokes the hardcoded stage function, applies the returned completion payload
to mutable runtime state, and calls back into the coordinator to record
artifacts plus `StageCompleted`. The coordinator then emits either
`RunCompleted` or `RunStopped`.

Streaming execution is split across prepare, hot path, and finalize code:

1. [RunCoordinatorActor._run_streaming()](../../src/prml_vslam/pipeline/ray_runtime/coordinator.py#L374)
   requires an injected streaming source and calls
   [`execute_streaming_prepare()`](../../src/prml_vslam/pipeline/ray_runtime/stage_program.py#L248).
   In this phase, `ingest` prepares the normalized sequence manifest and
   `slam` asks the coordinator driver hook to construct and start
   [`StreamingSlamStageActor`](../../src/prml_vslam/pipeline/ray_runtime/stage_actors.py#L203).
2. The coordinator creates
   [`PacketSourceActor`](../../src/prml_vslam/pipeline/ray_runtime/stage_actors.py#L99),
   which owns the source read loop, credit blocking, frame handle creation,
   and `on_packet()`, `on_source_eof()`, or `on_source_error()` callbacks.
3. [RunCoordinatorActor.on_packet()](../../src/prml_vslam/pipeline/ray_runtime/coordinator.py#L169)
   records packet telemetry and forwards frame payload refs to
   [`StreamingSlamStageActor.push_frame()`](../../src/prml_vslam/pipeline/ray_runtime/stage_actors.py#L240).
   The SLAM actor resolves payloads, steps the method session, translates
   backend updates through
   [`translate_slam_update()`](../../src/prml_vslam/methods/events.py),
   creates transient preview/array handles, and calls
   `on_slam_notices()`.
4. [RunCoordinatorActor.on_slam_notices()](../../src/prml_vslam/pipeline/ray_runtime/coordinator.py#L220)
   stores transient handles, records backend notice events, forwards Rerun
   bindings, releases packet credits, and finalizes once the source is
   finished and in-flight frames drain.
5. [RunCoordinatorActor._finalize_streaming()](../../src/prml_vslam/pipeline/ray_runtime/coordinator.py#L419)
   calls
   [`execute_streaming_finalize()`](../../src/prml_vslam/pipeline/ray_runtime/stage_program.py#L272).
   The SLAM finalizer closes the streaming actor and returns a
   `StageCompletionPayload`; downstream finalize-only stages then run against
   the accumulated runtime state before the coordinator emits `RunCompleted`,
   `RunFailed`, or `RunStopped`.

The cross-stage handoff is mutable and broad:

- [`StageCompletionPayload`](../../src/prml_vslam/pipeline/ray_runtime/stage_program.py#L60)
  carries the terminal `StageOutcome` plus whichever rich payload fields the
  stage happened to produce.
- [`_apply_completion()`](../../src/prml_vslam/pipeline/ray_runtime/stage_program.py#L483)
  mutates [`RuntimeExecutionState`](../../src/prml_vslam/pipeline/ray_runtime/stage_program.py#L38)
  by copying non-`None` payload fields into shared state.
- `RuntimeExecutionState.stage_outcomes` accumulates terminal outcomes in
  execution order and is the direct input to `summary`.
- [RunCoordinatorActor._record_stage_completion()](../../src/prml_vslam/pipeline/ray_runtime/coordinator.py#L574)
  emits artifact registration events, then duplicates the rich payload fields
  into `StageCompleted` so the snapshot projector can retain them.

The actor split is therefore not a clean stage-runtime boundary:

- [`OfflineSlamStageActor`](../../src/prml_vslam/pipeline/ray_runtime/stage_actors.py#L42)
  owns offline backend construction, `run_sequence()`, native visualization
  collection, and normalized SLAM completion.
- [`StreamingSlamStageActor`](../../src/prml_vslam/pipeline/ray_runtime/stage_actors.py#L203)
  owns method streaming-session state, frame payload resolution, backend update
  translation, transient update handles, and streaming SLAM completion.
- [`PacketSourceActor`](../../src/prml_vslam/pipeline/ray_runtime/stage_actors.py#L99)
  owns live source reads, credit blocking, frame handle creation, source EOF
  and source-error callbacks.
- [`RunCoordinatorActor`](../../src/prml_vslam/pipeline/ray_runtime/coordinator.py#L75)
  owns actor construction, streaming credits, transient handle cache, event
  recording, snapshot projection, JSONL persistence, Rerun fanout, and terminal
  run-state decisions.

The practical problem is not simply that some work is in actors and some work
is in helper functions. The current execution model splits one stage concept
across phase routing, mutable cross-stage state, actor lifecycle, and
observer/event policy.

## Present Stage Inventory

| Stage | Config today | Planning today | Runtime today | Output today | Present issue |
| --- | --- | --- | --- | --- | --- |
| `ingest` | `RunRequest.source` through `SourceSpec` | [StageRegistry](../../src/prml_vslam/pipeline/stage_registry.py#L140) | [run_ingest_stage()](../../src/prml_vslam/pipeline/ray_runtime/stage_execution.py#L60) | `StageCompletionPayload.sequence_manifest`, `benchmark_inputs` | No `IngestStageConfig`, `IngestStageInput`, or `IngestStageOutput`; source muxing is not factory-aligned with backend muxing. |
| `slam` | [SlamStageConfig](../../src/prml_vslam/pipeline/contracts/request.py#L150) with method-owned backend config | [StageRegistry](../../src/prml_vslam/pipeline/stage_registry.py#L145) | [OfflineSlamStageActor](../../src/prml_vslam/pipeline/ray_runtime/stage_actors.py#L42) and [StreamingSlamStageActor](../../src/prml_vslam/pipeline/ray_runtime/stage_actors.py#L203) | `StageCompletionPayload.slam`, `visualization` | Offline and streaming are separate actors; stage lifecycle is not represented by one stage runtime target. |
| `gravity.align` | [AlignmentConfig](../../src/prml_vslam/alignment/contracts.py#L26), enabled through `request.alignment.ground` | [StageRegistry](../../src/prml_vslam/pipeline/stage_registry.py#L150) | [run_ground_alignment_stage()](../../src/prml_vslam/pipeline/ray_runtime/stage_execution.py#L179) | `StageCompletionPayload.ground_alignment` | Config is package-local but injected through a top-level request field, not a stage config; output DTO is implicit. |
| `trajectory.evaluate` | [TrajectoryBenchmarkConfig](../../src/prml_vslam/benchmark/contracts.py), enabled through `request.benchmark.trajectory` | [StageRegistry](../../src/prml_vslam/pipeline/stage_registry.py#L156) | [run_trajectory_evaluation_stage()](../../src/prml_vslam/pipeline/ray_runtime/stage_execution.py#L137) | artifact map only; `EvaluationArtifact` not retained in payload | Benchmark policy and eval computation are split, but output retention is inconsistent with other stages. |
| `reference.reconstruct` | [ReferenceReconstructionConfig](../../src/prml_vslam/benchmark/contracts.py) | [StageRegistry](../../src/prml_vslam/pipeline/stage_registry.py#L164), available only for TUM RGB-D dataset sources | [run_reference_reconstruction_stage()](../../src/prml_vslam/pipeline/ray_runtime/stage_execution.py#L212) | `reference_cloud`, reconstruction metadata, optional mesh | Stage now has a bounded runtime helper, but no stage-local config/input/output DTO or clear reconstruction package runtime owner. |
| `cloud.evaluate` | [CloudBenchmarkConfig](../../src/prml_vslam/benchmark/contracts.py) | placeholder unavailable in [StageRegistry](../../src/prml_vslam/pipeline/stage_registry.py#L171) | none | expected output path only | Stage key exists but metric owner and DTO ownership are not fully wired. |
| `efficiency.evaluate` | [EfficiencyBenchmarkConfig](../../src/prml_vslam/benchmark/contracts.py) | placeholder unavailable in [StageRegistry](../../src/prml_vslam/pipeline/stage_registry.py#L180) | none | expected output path only | Stage key exists but should likely derive metrics from `RunEvent` stream; no DTO/runtime yet. |
| `summary` | no dedicated stage config | [StageRegistry](../../src/prml_vslam/pipeline/stage_registry.py#L189) | [run_summary_stage()](../../src/prml_vslam/pipeline/ray_runtime/stage_execution.py#L257) | `RunSummary`, `StageManifest[]` | Projection-only behavior is correct, but summary config/runtime is implicit. |

## Current Config Placement

```mermaid
classDiagram
    class RunRequest {
        +experiment_name
        +mode
        +output_dir
        +source
        +slam
        +benchmark
        +alignment
        +visualization
        +placement
        +runtime
    }

    class SourceSpec {
        <<union>>
    }

    class SlamStageConfig {
        +outputs
        +backend
    }

    class BackendConfig {
        <<method-owned union>>
    }

    class BenchmarkConfig {
        +reference
        +trajectory
        +cloud
        +efficiency
    }

    class AlignmentConfig {
        +ground
    }

    class VisualizationConfig
    class PlacementPolicy
    class RunRuntimeConfig

    RunRequest --> SourceSpec
    RunRequest --> SlamStageConfig
    SlamStageConfig --> BackendConfig
    RunRequest --> BenchmarkConfig
    RunRequest --> AlignmentConfig
    RunRequest --> VisualizationConfig
    RunRequest --> PlacementPolicy
    RunRequest --> RunRuntimeConfig
```

Findings:

- `SlamStageConfig` is the only current stage-like config class, but it does
  not derive from a common stage base and does not build a stage runtime target.
- Source config is represented by `SourceSpec`, but source construction happens
  in [OfflineSourceResolver](../../src/prml_vslam/pipeline/source_resolver.py#L46),
  not by a config-as-factory pattern.
- `benchmark`, `alignment`, and `visualization` are top-level run sections.
  They carry stage-like policy but are not modeled as stage configs.
- Placement is a separate map keyed by `StageKey`, not part of each stage
  config.
- Runtime lifecycle policy is run-level only; stage runtime lifecycle is
  implicit in helper functions and actor construction.

## Current Runtime Responsibilities

```mermaid
flowchart TB
    Coordinator["RunCoordinatorActor"]
    Program["RuntimeStageProgram"]
    State["RuntimeExecutionState"]
    Payload["StageCompletionPayload"]
    Events["RunEvent stream"]
    Snapshot["RunSnapshot / StreamingRunSnapshot"]
    Jsonl["JsonlEventSink"]
    Rerun["RerunSinkActor"]
    SourceActor["PacketSourceActor"]
    SlamActor["StreamingSlamStageActor"]

    Coordinator --> Program
    Program --> State
    Program --> Payload
    Coordinator --> Events
    Events --> Snapshot
    Events --> Jsonl
    Events --> Rerun
    Coordinator --> SourceActor
    SourceActor --> Coordinator
    Coordinator --> SlamActor
    SlamActor --> Coordinator

    classDef coordinator fill:#ECECFF,stroke:#9370DB,color:#222222;
    classDef data fill:#E7F6EE,stroke:#2E8B57,color:#222222;
    classDef actor fill:#FFF4DD,stroke:#C28A2C,color:#222222;

    class Coordinator,Program coordinator;
    class State,Payload,Events,Snapshot data;
    class SourceActor,SlamActor,Rerun actor;
```

Findings:

- [RunCoordinatorActor](../../src/prml_vslam/pipeline/ray_runtime/coordinator.py#L75)
  owns too many runtime concerns at once: event log, snapshot projection,
  JSONL sink, Rerun sink, transient handle cache, source credit loop, streaming
  finalization, stage start/completion/failure event emission, and actor
  lifecycle.
- [RuntimeStageProgram](../../src/prml_vslam/pipeline/ray_runtime/stage_program.py#L132)
  looks like a generic stage executor but is currently a hardcoded list of
  function pointers rather than a stage runtime abstraction.
- Stage execution authority is split four ways: `RuntimeStageProgram` owns
  phase routing, `RuntimeExecutionState` owns mutable handoff state, Ray actors
  own parts of the stage lifecycle, and the coordinator owns observer/event
  policy.
- [StageCompletionPayload](../../src/prml_vslam/pipeline/ray_runtime/stage_program.py#L60)
  is the de facto cross-stage output DTO, but it is a broad union-like bag
  rather than stage-specific output contracts.
- [RuntimeExecutionState](../../src/prml_vslam/pipeline/ray_runtime/stage_program.py#L38)
  is mutable cross-stage state. It works, but it hides which stage produces and
  consumes which fields.
- There is no per-stage status DTO beyond `StageProgress` and projected
  streaming counters.

## Current Backend And Source Muxing

```mermaid
flowchart TB
    subgraph SourceMux["Source muxing"]
        SourceSpec["SourceSpec union"]
        SourceResolver["OfflineSourceResolver.match"]
        VideoSource["VideoOfflineSequenceSource"]
        AdvioService["AdvioDatasetService"]
    end

    subgraph BackendMux["SLAM backend muxing"]
        BackendConfig["BackendConfig discriminated union"]
        BackendFactory["BackendFactory"]
        MockConfig["MockSlamBackendConfig"]
        VistaConfig["VistaSlamBackendConfig"]
        Mast3rConfig["Mast3rSlamBackendConfig"]
        SlamBackend["SlamBackend"]
    end

    SourceSpec --> SourceResolver
    SourceResolver --> VideoSource
    SourceResolver --> AdvioService

    BackendConfig --> MockConfig
    BackendConfig --> VistaConfig
    BackendConfig --> Mast3rConfig
    BackendFactory --> BackendConfig
    BackendFactory --> SlamBackend
```

Findings:

- Backend muxing has a typed discriminated union in
  [methods/configs.py](../../src/prml_vslam/methods/configs.py#L251) and a
  factory in [methods/factory.py](../../src/prml_vslam/methods/factory.py#L24).
- Source muxing uses a manual `match` inside
  [OfflineSourceResolver.resolve()](../../src/prml_vslam/pipeline/source_resolver.py#L51).
- Streaming source construction is elsewhere, in
  [pipeline/demo.py](../../src/prml_vslam/pipeline/demo.py), rather than using
  the same resolver/factory abstraction.
- This creates two muxing styles and makes it harder to add new source or
  stage backends consistently.

## Current DTO And Contract Placement Issues

| Contact | Present placement | Issue |
| --- | --- | --- |
| [interfaces/slam.py](../../src/prml_vslam/interfaces/slam.py) | `interfaces` owns `SlamArtifacts`, `SlamUpdate`, `BackendEvent`, but imports pipeline handles and transport model | Shared SLAM DTOs depend on pipeline contracts, which blurs the intended direction from shared interfaces to pipeline. |
| [pipeline/contracts/runtime.py](../../src/prml_vslam/pipeline/contracts/runtime.py#L26) | `RunState`, `RunSnapshot`, `StreamingRunSnapshot` in pipeline contracts | Probably acceptable because snapshots are event projections, but the inline TODO shows ownership is unsettled. |
| [pipeline/contracts/handles.py](../../src/prml_vslam/pipeline/contracts/handles.py#L16) | transient payload handles in pipeline contracts | Placement is probably right, but module comment still says motivation needs explanation. |
| [pipeline/backend.py](../../src/prml_vslam/pipeline/backend.py#L26) | `PipelineBackend` protocol in `backend.py` | Public behavior seam is not in a clearly named `protocols.py` module. |
| [alignment/contracts.py](../../src/prml_vslam/alignment/contracts.py#L12) | alignment configs in package contracts | Placement is likely right, but TODO indicates lack of a documented rule for config ownership. |
| [visualization/validation.py](../../src/prml_vslam/visualization/validation.py#L27) | validation DTOs inside implementation/CLI helper module | DTO definitions should move to `visualization.contracts` or a validation contracts module. |
| [pipeline/finalization.py](../../src/prml_vslam/pipeline/finalization.py#L80) | `stable_hash` and `write_json` in pipeline finalization | Generic serialization/fingerprinting helpers are reused outside finalization, including method code, so ownership is diffuse. |
| [pipeline/placement.py](../../src/prml_vslam/pipeline/placement.py#L16) | Ray option type aliases | The TODO is accurate: resource policy should be a typed config, not a loose dict alias. |

## Current Responsibility Diffusion

### Stage Definition Is Split Across Too Many Places

For one stage, the reader must inspect:

- [StageKey](../../src/prml_vslam/pipeline/contracts/stages.py)
- [StageRegistry.default()](../../src/prml_vslam/pipeline/stage_registry.py#L136)
- [RunRequest fields](../../src/prml_vslam/pipeline/contracts/request.py#L175)
- [RuntimeStageProgram.default()](../../src/prml_vslam/pipeline/ray_runtime/stage_program.py#L138)
- [stage_execution.py](../../src/prml_vslam/pipeline/ray_runtime/stage_execution.py)
- [stage_actors.py](../../src/prml_vslam/pipeline/ray_runtime/stage_actors.py)
- [coordinator.py](../../src/prml_vslam/pipeline/ray_runtime/coordinator.py)

Issue: there is no stage-local “home” where config, runtime, DTOs, resources,
and telemetry are all discoverable.

### Coordinator Owns Runtime Policy And Observer Policy

The coordinator builds the JSONL sink, builds the Rerun sink, handles event
projection, stores transient handles, controls packet credits, starts/stops
actors, and records stage events. Each responsibility is reasonable, but the
combination makes the actor the center of too many policy decisions.

Contact points:

- [Rerun sink creation](../../src/prml_vslam/pipeline/ray_runtime/coordinator.py#L525)
- [stage actor options](../../src/prml_vslam/pipeline/ray_runtime/coordinator.py#L540)
- [stage event emission](../../src/prml_vslam/pipeline/ray_runtime/coordinator.py#L562)
- [packet observation and credits](../../src/prml_vslam/pipeline/ray_runtime/coordinator.py#L206)

### Stage Outputs Are Broad Payloads Instead Of Stage-Specific DTOs

[StageCompletionPayload](../../src/prml_vslam/pipeline/ray_runtime/stage_program.py#L60)
carries optional fields for many stages:

- `sequence_manifest`
- `benchmark_inputs`
- `slam`
- `ground_alignment`
- `visualization`
- `summary`
- `stage_manifests`

Issue: this gives a convenient internal handoff but does not document or
enforce stage-specific input/output contracts. It also encourages downstream
logic to inspect broad optional state instead of typed stage outputs.

### Resource Placement Is Ray-Specific And Untyped

[StagePlacement](../../src/prml_vslam/pipeline/contracts/request.py#L124)
stores `resources: dict[str, float]`. [actor_options_for_stage()](../../src/prml_vslam/pipeline/placement.py#L22)
then interprets `"CPU"` and `"GPU"` keys specially and passes the rest to Ray.

Issues:

- CPU/GPU are magic string keys.
- memory, object-store memory, node/IP affinity, accelerator type, restart
  policy, and task retry policy have no typed request model.
- placement lives outside the stage config, even though it is stage runtime
  policy.

### Serialization Helpers Are Used As Shared Utilities But Owned By Pipeline Finalization

[stable_hash](../../src/prml_vslam/pipeline/finalization.py#L80) and
[write_json](../../src/prml_vslam/pipeline/finalization.py#L88) are generic,
but `stable_hash` is imported by method code such as
[methods/vista/artifacts.py](../../src/prml_vslam/methods/vista/artifacts.py).

Issue: method code depending on pipeline finalization for generic hashing
inverts ownership and makes `pipeline.finalization` more than summary
projection.

### `interfaces` Is Not A Purely Independent Shared Layer

[interfaces/slam.py](../../src/prml_vslam/interfaces/slam.py) imports
[ArrayHandle](../../src/prml_vslam/pipeline/contracts/handles.py) and
[TransportModel](../../src/prml_vslam/pipeline/contracts/transport.py).

Issue: repo-wide interfaces depending on pipeline contracts weakens the
intended layering. Either handles/transport base need to be promoted to a
shared runtime contract, or SLAM streaming notice DTOs should remain
pipeline/method boundary contracts rather than `interfaces`.

## Artifact Handling Gaps

Recent offline ViSTA runs expose several artifact-handling gaps that are not
runtime failures, but do make inspection and evaluation ambiguous:

- ViSTA preserves important native arrays such as `intrinsics.npy`,
  `confs.npz`, `scales.npy`, `trajectory.npy`, and `view_graph.npz`, but they
  currently remain mostly raw `SlamArtifacts.extras` rather than typed,
  raster/frame-annotated repo artifacts.
- Estimated ViSTA intrinsics are not standardized. Native `intrinsics.npy`
  represents per-keyframe camera models in the ViSTA model raster, while
  `input/intrinsics.yaml` represents the source TUM RGB-D raster. Directly
  comparing those values is misleading without persisted source-to-model
  preprocessing metadata.
- The source-to-model raster relationship used by the upstream image-only
  crop/resize path is documented, but not persisted as a run artifact. This
  blocks reliable ground-truth intrinsics projection into ViSTA model space.
- Normalizing `native/pointcloud.ply` into `slam/point_cloud.ply` currently
  risks losing native RGB colors when the generic writer only persists XYZ.
  Generic color-preserving PLY IO should be a shared helper, while the decision
  to preserve ViSTA colors belongs in the ViSTA artifact normalizer.
- `summary/run-events.jsonl` can accumulate repeated attempts for the same run
  id when a run root is reused. The final summary may look clean while older
  failed attempts remain in the event log, so run/attempt inspection should be
  pipeline-owned and explicit.

## Current Redundancies

| Redundant / overlapping concept | Current locations | Problem |
| --- | --- | --- |
| Stage execution authority | `RuntimeStageProgram`, `RuntimeExecutionState`, `stage_execution.py`, `stage_actors.py`, `RunCoordinatorActor` | One stage lifecycle is split across phase routing, mutable state, helper functions, actors, and event/observer policy. |
| Runtime stage result | `StageCompletionPayload`, `StageOutcome`, `StageCompleted` event, `RuntimeExecutionState` | Multiple objects represent partly overlapping “stage result” semantics. |
| Stage status | `StageStatus`, `RunState`, `StageProgress`, `StreamingRunSnapshot` counters | No single stage runtime status DTO for queue, FPS, latency, throughput, and resource use. |
| Source construction | `OfflineSourceResolver`, `pipeline/demo.py`, dataset services, IO configs | Offline and streaming source construction do not share one mux/factory abstraction. |
| Backend capability/resource metadata | backend config properties, `BackendFactory.describe()`, `StageRegistry` availability checks, placement defaults | Capability and resource data are available but spread across planning, factory, and placement code. |
| JSON writing / hashing | `pipeline.finalization.write_json`, `pipeline.ingest._write_json_payload`, `BaseConfig.to_jsonable`, external imports of `stable_hash` | Generic serialization rules are duplicated or pulled from pipeline finalization. |
| Visualization artifacts | `interfaces.visualization.VisualizationArtifacts`, `visualization.contracts.VisualizationConfig`, `pipeline.sinks.rerun`, native artifact collection in SLAM actors | Viewer policy, native artifact preservation, and sink behavior are split across multiple layers. |

## Inline TODO / Issue Map

| Contact | Present issue | Why this matters for planning |
| --- | --- | --- |
| [io/__init__.py](../../src/prml_vslam/io/__init__.py#L20) | `io.datasets` alias and explicit uncertainty about dataset ownership | Removed; datasets stays top-level. |
| [datasets/__init__.py](../../src/prml_vslam/datasets/__init__.py) | mirror alias for `prml_vslam.io.datasets` | Removed; datasets stays top-level. |
| [interfaces/__init__.py](../../src/prml_vslam/interfaces/__init__.py#L63) | unclear DTO/protocol/module organization | Document and enforce shared DTO vs package-local contract rule. |
| [benchmark/__init__.py](../../src/prml_vslam/benchmark/__init__.py#L25) | benchmark/eval responsibility conflict | Keep benchmark as policy, eval as computation/result owner. |
| [methods/protocols.py](../../src/prml_vslam/methods/protocols.py#L22) | former split between `SlamSession` and `SlamBackend` | Resolved: streaming lifecycle now lives on `StreamingSlamBackend` and pipeline ownership lives in `SlamStageRuntime`. |
| [visualization/validation.py](../../src/prml_vslam/visualization/validation.py#L27) | DTOs in validation implementation module | Move DTOs to visualization contracts. |
| [pipeline/contracts/handles.py](../../src/prml_vslam/pipeline/contracts/handles.py#L16) | missing module motivation | Explain transient handle ownership and why arrays stay out of public persisted contracts. |
| [pipeline/backend.py](../../src/prml_vslam/pipeline/backend.py#L26) | protocol in ambiguously named module | Move to `pipeline/protocols.py` or explicitly codify `backend.py` as substrate protocol owner. |
| [pipeline/placement.py](../../src/prml_vslam/pipeline/placement.py#L16) | loose Ray option aliases | Replace with typed `StageResourceConfig`. |
| [alignment/contracts.py](../../src/prml_vslam/alignment/contracts.py#L12) | config placement uncertainty | Keep package-local configs in contracts; document that durable request policy is a contract. |
| [pipeline/contracts/runtime.py](../../src/prml_vslam/pipeline/contracts/runtime.py#L26) | runtime DTO ownership uncertainty | Keep pipeline-owned unless a second package needs identical semantics. |
| [pipeline/finalization.py](../../src/prml_vslam/pipeline/finalization.py#L87) | generic JSON helper in pipeline finalization | Move generic serialization to shared utility; keep summary projection here. |

## Present-State Issue Severity

| Severity | Issue | Why it matters |
| --- | --- | --- |
| High | No generic stage config/runtime abstraction | Blocks clean stage-wise refactor and makes new stages require edits across registry, runtime program, coordinator, and helper modules. The current issue is a four-way split across phase routing, mutable state, actor lifecycle, and observer/event policy, not merely actor/helper placement. |
| High | SLAM stage split into offline actor and streaming actor | Duplicates backend construction/finalization logic and obscures one stage lifecycle. |
| High | Coordinator owns too many runtime/observer responsibilities | Makes streaming changes risky and hard to test in isolation. |
| Medium | Source muxing and backend muxing use different patterns | New source/backend variants require different extension paths. |
| Medium | `StageCompletionPayload` is a broad optional bag | Stage outputs are not self-documenting or decision-complete. |
| Medium | Resource placement is untyped and Ray-specific | Hard to express planned remote actor policy from the sketch. |
| Medium | Shared `interfaces` import pipeline contracts | Layering violation or at least an unresolved layering smell. |
| Low | Placeholder stages exist without DTO/runtime ownership | Acceptable for planning today, but must be resolved before implementation. |
| Low | Validation DTOs live in validation implementation module | Localized cleanup. |

## Present-State Strengths To Preserve

- `RunEvent` is the runtime source of truth, and `RunSnapshot` is projected.
- The executable slice is deterministic and linear.
- `SequenceManifest` is a stable normalized ingest boundary.
- SLAM wrappers return normalized `SlamArtifacts`.
- Alignment is a derived artifact and does not mutate native SLAM outputs.
- Rerun SDK calls are isolated behind the sink sidecar.
- `BackendConfig` already uses a discriminated union for method variants.

## Current Pressure Points For Refactor Planning

The smallest useful refactor should account for these current pressure points:

1. Add a generic stage config/runtime/status contract without moving behavior.
2. Add explicit stage input/output DTOs while keeping `StageCompletionPayload`
   as an internal adapter during migration.
3. Replace `StageRuntimeSpec` function pointers with stage runtime objects
   gradually.
4. Introduce typed resource config before adding remote actor support.
5. Align source muxing with backend muxing.
6. Merge the SLAM stage actor surfaces after the generic runtime abstraction is
   present.
7. Split coordinator responsibilities only after stage runtimes expose clean
   lifecycle and status methods.
