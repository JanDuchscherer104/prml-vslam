# Refactor Plan


THE FOLLOWING INSTRUCTIONS ARE HIGHEST LEVEL AND READ ONLY!

- All stages must use config as factory pattern.
- final config's target is the runtime class that is used inside the pipeline, for statefull stages this must be the ray StageActor, so all of these top level configs must derive from a shared stage config base type that allows the pipeline to reason about them uniformly (i.e. compute ressources (num gpus, num_cpus, memory, ip-address for remoote actors, etc.!))
- configs are nested and composable, differentiate backends / variants by unions of child configs or via StrEnum fields, this needs to be decided.
- decide: how should we optimally implement the muxing between different backends? this must be unified across stages, i.e. IO muxing is currently defined in src/prml_vslam/pipeline/source_resolver.py, vslam in src/prml_vslam/methods/factory.py.
- Every stage has strictly defined DTOs for inputs and outputs for both offline and streaming execution.
- the output DTO must implement rerun integration (i.e. conversion to rerun events), here we should probably define shared functionalities or base classes when different modalities need to be supported across stages.
- all rerun events arrive at the rerun sink which is the only place that is responsible for talking to the rerun sdk
- for all stages it must be easy to query their running status (queue sizes, fps / throughput, latency)
- start by planning by creating uml diagrams of the target state
- the goal of this refactor is to create a clean separtion of concerns and improve the maintainability of the codebase.
- Decide: where should we optimally define the public interfaces, DTOs, stage-specific configs and protocols - in dedicated moudles or in the stage modules itself?


---

## CODEX Plan

# Pre-UML Decision Register For Pipeline Refactor

## Current State
- The executable pipeline is still a linear, event-first slice: `ingest -> slam -> [ground.align] -> [trajectory.evaluate] -> summary`.
- `RunRequest` is currently the top-level persisted config, with nested `source`, `slam.backend`, benchmark, alignment, visualization, placement, and runtime policy.
- SLAM backend muxing is method-owned through `methods.configs.BackendConfig` and `BackendFactory`; source muxing is separately pipeline-owned in `pipeline.source_resolver`.
- Runtime execution is split between bounded helper functions and Ray actors: offline SLAM uses `OfflineSlamStageActor`, streaming uses `StreamingSlamStageActor`, and the coordinator owns events, snapshots, sinks, and streaming credits.
- The attached sketch points toward a target where every stage config is a factory whose target is a stage runtime actor, with common resource/status/control behavior and stage-specific backend config nested inside.

## Decisions Before UML
- Stage abstraction: decide whether every stage becomes a derived `StageActor` class, or whether stateless stages remain bounded helpers while only stateful stages are actors. Default recommendation: define a common `StageRuntime` protocol for all stages, but use Ray actors only for stateful/long-running stages.
- Offline vs streaming lifecycle: decide whether one actor handles both offline and streaming methods or whether offline and streaming remain separate entrypoints. Default recommendation: one `SlamStageActor` with explicit `run_offline()`, `start_streaming()`, `push_frame()`, and `finalize()` methods.
- Config hierarchy: decide the canonical top-level shape: `RunConfig -> StageConfig[]` versus today’s named fields on `RunRequest`. Default recommendation: keep named top-level sections for TOML readability, but make each stage section implement a shared `StageConfig` base.
- Backend muxing: decide whether backend variants use Pydantic discriminated unions or `StrEnum` plus nested config. Default recommendation: keep discriminated unions for typed backend configs; avoid a separate enum switch when the config type already identifies the target.
- Unified muxing pattern: decide one factory pattern for sources, SLAM backends, and future stages so `source_resolver.py` and `methods/factory.py` stop using unrelated selection styles.
- Public contract placement: decide where DTOs/configs/protocols live. Default recommendation: repo-wide semantic DTOs in `interfaces`, repo-wide behavior protocols in `protocols`, package-local stage configs/DTOs in `<package>/contracts/`, package-local behavior seams in `<package>/protocols.py`.
- Stage DTO boundaries: decide the required input/output DTO per stage for offline prepare, streaming hot path, and streaming finalize. This must be fixed before UML so each diagram shows real contracts, not inferred state.
- Rerun integration: decide whether stage output DTOs expose `to_rerun_events()` or whether a separate visualization adapter translates stage outputs. Default recommendation: separate adapter/policy, with Rerun SDK calls only in the sink.
- Status and telemetry: decide the shared runtime status model for all stages: lifecycle state, queue sizes, FPS, latency, throughput, errors, and resource usage.
- Resource placement model: replace current Ray option aliases with a typed `StageResourceConfig` that can express CPUs, GPUs, memory, custom resources, node/IP constraints, restart policy, and task retries.
- Benchmark vs eval split: decide whether `benchmark` owns policy only and `eval` owns metric computation/results. Default recommendation: keep that split and move duplicated config/result concepts to one owner.
- IO vs datasets split: decide whether datasets stay top-level or become IO submodules. Default recommendation: keep `datasets` top-level; remove the `io.datasets` compatibility alias.
- Snapshot/event ownership: decide whether `RunSnapshot` and `RunState` remain pipeline contracts or move to shared runtime models. Default recommendation: keep them in pipeline unless another package consumes identical semantics independently.
- Artifact serialization: decide whether `write_json`/stable serialization belongs in `BaseConfig/BaseData` utilities or remains pipeline-local finalization.
- Placeholder stages: decide which future stages must be first-class in the target UML: `reference.reconstruct`, `cloud.evaluate`, `efficiency.evaluate`, 3DGS/reconstruction, visualization/export, and source capture.
- App/CLI contract: decide whether launch surfaces still submit a single `RunRequest`, or whether they construct a stage graph/config object directly.

## UML Plan
- Start with four diagrams: package ownership, config/factory hierarchy, runtime actor lifecycle, and stage DTO dataflow.
- Then add one stage-local sequence diagram for SLAM, because it is the highest-risk split between backend config, Ray actor lifecycle, offline execution, streaming session state, and Rerun telemetry.
- Use the current architecture docs as the baseline, but mark changed ownership explicitly instead of redrawing today’s system as if it were the target.

## Acceptance Criteria
- Every TODO above maps to a resolved architectural decision.
- Every stage in the UML has a config type, runtime target, input DTO, output DTO, status DTO, and Rerun/event translation path.
- The target design preserves the repo’s non-negotiables: artifact-first outputs, append-only runtime events, projected snapshots, thin method wrappers, explicit alignment artifacts, and no app-owned pipeline semantics.
