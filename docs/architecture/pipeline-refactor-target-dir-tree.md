# Pipeline Refactor Target Directory Tree

This document is the implementation scaffold for the pipeline stage refactor.
It turns the target architecture into concrete package ownership, file
ownership, and leaf-symbol placement so implementation agents do not invent
parallel homes for the same concept.

Authoritative design context remains in:

- [Pipeline stage refactor target](./pipeline-stage-refactor-target.md)
- [Pipeline stage present-state audit](./pipeline-stage-present-state-audit.md)
- [Pipeline stage protocols and DTOs](./pipeline-stage-protocols-and-dtos.md)


## Purpose

- Provide the canonical implementation scaffold for the pipeline refactor.
- Define one owning file for each important class, protocol, DTO, and helper.
- Keep production behavior unchanged until work packages implement the listed
  files and symbols.
- Give parallel agents a shared directory map before they edit code.

This file is not a replacement for
[pipeline-stage-refactor-target.md](./pipeline-stage-refactor-target.md). It is
a narrower implementation index derived from that architecture.

## Current Affected Tree

Legend:

- `[A]`: existing module affected by the refactor.
- `[N]`: new target module to add.
- `[M]`: migration contact; keep working until the replacement is proven, then
  delete or shrink in a later cleanup work package.
- `[C]`: context module; generally read-only for the pipeline refactor unless
  a work package explicitly needs a boundary adjustment.

Every current module marked `[A]` or `[M]` is expected to change during the
full refactor, but work-package ownership is authoritative only when a package
explicitly lists the path under `Owned paths`. Modules marked `[C]` are
included so agents can see the whole package boundary and avoid inventing
parallel ownership. New target modules are not shown in this current tree; they
appear in the target tree below.

```text
src/prml_vslam/
├── AGENTS.md [A]
├── REFACTOR_PLAN.md [A]
├── REQUIREMENTS.md [A]
├── __init__.py [C]
├── alignment [A]
│   ├── README.md [C]
│   ├── REQUIREMENTS.md [A]
│   ├── __init__.py [C]
│   ├── contracts.py [A]
│   └── services.py [C]
├── app [A]
│   ├── AGENTS.md [C]
│   ├── README.md [C]
│   ├── REQUIREMENTS.md [A]
│   ├── __init__.py [C]
│   ├── advio_controller.py [C]
│   ├── bootstrap.py [C]
│   ├── live_session.py [A]
│   ├── models.py [A]
│   ├── pages [A]
│   │   ├── __init__.py [C]
│   │   ├── artifacts.py [A]
│   │   ├── datasets.py [C]
│   │   ├── graphify.py [C]
│   │   ├── metrics.py [A]
│   │   ├── pipeline.py [A]
│   │   ├── pipeline_request_editor.py [A]
│   │   ├── pipeline_snapshot_view.py [A]
│   │   └── record3d.py [C]
│   ├── pipeline_controller.py [A]
│   ├── pipeline_controls.py [A]
│   ├── preview_runtime.py [A]
│   ├── record3d_controller.py [C]
│   ├── record3d_controls.py [C]
│   ├── services.py [A]
│   ├── state.py [A]
│   └── ui.py [C]
├── benchmark [A]
│   ├── README.md [C]
│   ├── REQUIREMENTS.md [A]
│   ├── __init__.py [C]
│   └── contracts.py [A]
├── datasets [A]
│   ├── README.md [C]
│   ├── __init__.py [M]
│   ├── advio [C]
│   │   ├── README.md [C]
│   │   ├── __init__.py [C]
│   │   ├── advio_catalog.json [C]
│   │   ├── advio_download.py [C]
│   │   ├── advio_geometry.py [C]
│   │   ├── advio_layout.py [C]
│   │   ├── advio_loading.py [C]
│   │   ├── advio_models.py [C]
│   │   ├── advio_replay_adapter.py [C]
│   │   ├── advio_sequence.py [C]
│   │   └── advio_service.py [C]
│   ├── contracts.py [C]
│   ├── download_helpers.py [C]
│   ├── fetch.py [C]
│   ├── registry.py [C]
│   ├── sources.py [C]
│   └── tum_rgbd [C]
│       ├── README.md [C]
│       ├── __init__.py [C]
│       ├── tum_rgbd_download.py [C]
│       ├── tum_rgbd_layout.py [C]
│       ├── tum_rgbd_loading.py [C]
│       ├── tum_rgbd_models.py [C]
│       ├── tum_rgbd_replay_adapter.py [C]
│       ├── tum_rgbd_sequence.py [C]
│       └── tum_rgbd_service.py [C]
├── eval [A]
│   ├── README.md [C]
│   ├── REQUIREMENTS.md [A]
│   ├── __init__.py [C]
│   ├── contracts.py [A]
│   ├── intrinsics.py [C]
│   ├── protocols.py [C]
│   └── services.py [C]
├── interfaces [A]
│   ├── __init__.py [A]
│   ├── alignment.py [C]
│   ├── camera.py [A]
│   ├── ingest.py [C]
│   ├── rgbd.py [C]
│   ├── runtime.py [C]
│   ├── slam.py [A]
│   ├── transforms.py [C]
│   └── visualization.py [A]
├── io [A]
│   ├── README.md [C]
│   ├── RECORD3D_PROTOCOL.md [C]
│   ├── __init__.py [M]
│   ├── cv2_producer.py [C]
│   ├── record3d.py [C]
│   ├── record3d_source.py [A]
│   ├── wifi_packets.py [C]
│   ├── wifi_receiver.py [C]
│   ├── wifi_session.py [C]
│   └── wifi_signaling.py [C]
├── main.py [A]
├── methods [A]
│   ├── README.md [C]
│   ├── REQUIREMENTS.md [A]
│   ├── __init__.py [C]
│   ├── config_contracts.py [A]
│   ├── configs.py [A]
│   ├── descriptors.py [A]
│   ├── events.py [A]
│   ├── factory.py [A]
│   ├── mast3r.py [C]
│   ├── mock_vslam.py [A]
│   ├── protocols.py [A]
│   └── vista [A]
│       ├── README.md [C]
│       ├── REQUIREMENTS.md [A]
│       ├── __init__.py [C]
│       ├── adapter.py [C]
│       ├── artifact_io.py [A]
│       ├── artifacts.py [A]
│       ├── diagnostics.py [C]
│       ├── preprocess.py [A]
│       ├── runtime.py [A]
│       └── session.py [M]
├── pipeline [A]
│   ├── README.md [A]
│   ├── REQUIREMENTS.md [A]
│   ├── __init__.py [A]
│   ├── artifact_inspection.py [A]
│   ├── backend.py [A]
│   ├── backend_ray.py [A]
│   ├── contracts [A]
│   │   ├── __init__.py [A]
│   │   ├── events.py [A]
│   │   ├── handles.py [M]
│   │   ├── plan.py [A]
│   │   ├── provenance.py [A]
│   │   ├── request.py [M]
│   │   ├── runtime.py [A]
│   │   ├── stages.py [M]
│   │   └── transport.py [A]
│   ├── demo.py [M]
│   ├── finalization.py [A]
│   ├── ingest.py [M]
│   ├── placement.py [M]
│   ├── ray_runtime [M]
│   │   ├── __init__.py [M]
│   │   ├── common.py [M]
│   │   ├── coordinator.py [A]
│   │   ├── stage_actors.py [M]
│   │   ├── stage_execution.py [M]
│   │   └── stage_program.py [M]
│   ├── run_service.py [A]
│   ├── sinks [A]
│   │   ├── __init__.py [C]
│   │   ├── jsonl.py [A]
│   │   ├── rerun.py [A]
│   │   └── rerun_policy.py [A]
│   ├── snapshot_projector.py [A]
│   ├── source_resolver.py [M]
│   ├── stage_registry.py [M]
│   └── workspace.py [C]
├── plotting [A]
│   ├── __init__.py [C]
│   ├── advio.py [C]
│   ├── artifact_diagnostics.py [A]
│   ├── metrics.py [A]
│   ├── pipeline.py [A]
│   ├── reconstruction.py [A]
│   ├── record3d.py [C]
│   ├── theme.py [C]
│   └── trajectories.py [A]
├── protocols [A]
│   ├── __init__.py [C]
│   ├── rgbd.py [C]
│   ├── runtime.py [C]
│   └── source.py [A]
├── py.typed [C]
├── reconstruction [A]
│   ├── README.md [C]
│   ├── REQUIREMENTS.md [A]
│   ├── __init__.py [C]
│   ├── config.py [A]
│   ├── configs.py [A]
│   ├── contracts.py [A]
│   ├── open3d_tsdf.py [C]
│   ├── protocols.py [A]
│   └── rgbd_source.py [A]
├── utils [A]
│   ├── REQUIREMENTS.md [C]
│   ├── __init__.py [A]
│   ├── base_config.py [A]
│   ├── base_data.py [A]
│   ├── console.py [C]
│   ├── geometry.py [A]
│   ├── image_utils.py [C]
│   ├── path_config.py [C]
│   └── video_frames.py [C]
└── visualization [A]
    ├── DEBUGGING.md [C]
    ├── ISSUES.md [C]
    ├── README.md [C]
    ├── REQUIREMENTS.md [A]
    ├── RERUN_SEMANTICS.md [A]
    ├── VISTA_NOTES.md [C]
    ├── __init__.py [A]
    ├── contracts.py [A]
    ├── rerun.py [A]
    └── validation.py [M]
```

## Target Tree

This target tree includes only files expected to be added or modified by the
pipeline refactor. Important target classes, protocols, DTOs, and helpers are
listed as leaf nodes under their owning files. Context-only packages from the
current tree are intentionally omitted here.

```text
src/prml_vslam/
├── REFACTOR_PLAN.md
├── REQUIREMENTS.md
├── main.py
│   └── run-config / plan-run-config adapters for RunConfig compatibility
├── alignment
│   ├── REQUIREMENTS.md
│   └── contracts.py
│       └── GroundAlignmentMetadata
├── app
│   ├── REQUIREMENTS.md
│   ├── live_session.py
│   │   └── live run/session compatibility helpers
│   ├── models.py
│   │   └── pipeline snapshot render models
│   ├── pages
│   │   ├── artifacts.py
│   │   │   └── artifact inspection view bindings
│   │   ├── metrics.py
│   │   │   └── metric artifact view bindings
│   │   ├── pipeline.py
│   │   │   └── pipeline page orchestration bindings
│   │   ├── pipeline_request_editor.py
│   │   │   └── RunConfig editor bindings
│   │   └── pipeline_snapshot_view.py
│   │       └── RunSnapshot display-status projection
│   ├── pipeline_controller.py
│   │   └── pipeline launch/monitor controller
│   ├── pipeline_controls.py
│   │   └── RunConfig control bindings
│   ├── preview_runtime.py
│   │   └── live payload preview resolver usage
│   ├── services.py
│   │   └── pipeline service adapter usage
│   └── state.py
│       └── pipeline page state
├── benchmark
│   ├── REQUIREMENTS.md
│   └── contracts.py
│       └── benchmark policy configs
├── eval
│   ├── REQUIREMENTS.md
│   └── contracts.py
│       ├── EvaluationArtifact
│       └── future metric artifact DTOs
├── interfaces
│   ├── __init__.py
│   │   └── shared DTO export cleanup
│   ├── camera.py
│   │   └── CameraIntrinsicsSeries, ...
│   ├── slam.py
│   │   └── SlamArtifacts
│   └── visualization.py
│       └── VisualizationArtifacts
├── io
│   ├── __init__.py
│   │   └── datasets alias removal audit
│   └── record3d_source.py
│       └── Record3D source config compatibility
├── methods
│   ├── REQUIREMENTS.md
│   ├── config_contracts.py
│   │   └── SlamOutputPolicy
│   ├── configs.py
│   │   ├── BackendConfig
│   │   ├── MockSlamBackendConfig
│   │   ├── VistaSlamBackendConfig
│   │   └── Mast3rSlamBackendConfig
│   ├── contracts.py
│   │   ├── SlamUpdate
│   │   ├── BackendEvent
│   │   └── backend notice/event DTOs
│   ├── descriptors.py
│   │   └── BackendDescriptor
│   ├── events.py
│   │   └── translate_slam_update migration adapter
│   ├── factory.py
│   │   └── BackendFactory
│   ├── mock_vslam.py
│   │   └── MockSlamBackend
│   └── vista
│       ├── REQUIREMENTS.md
│       ├── artifact_io.py
│       │   └── ViSTA artifact IO helpers
│       ├── artifacts.py
│       │   └── ViSTA artifact normalization helpers
│       ├── preprocess.py
│       │   └── ViSTA preprocessing metadata
│       ├── runtime.py
│       │   └── VistaSlamBackend
│       └── session.py
│           └── VistaSlamSession migration contact
├── pipeline
│   ├── README.md
│   ├── REQUIREMENTS.md
│   ├── __init__.py
│   │   └── curated public API cleanup
│   ├── artifact_inspection.py
│   │   └── run/attempt artifact inspection helpers
│   ├── backend.py
│   │   ├── PipelineBackend
│   │   └── read_payload(run_id, ref)
│   ├── backend_ray.py
│   │   └── RayPipelineBackend
│   ├── config.py
│   │   ├── RunConfig
│   │   ├── StageBundle
│   │   └── stage-key/config-section mapping
│   ├── contracts
│   │   ├── __init__.py
│   │   │   └── public contract export cleanup
│   │   ├── events.py
│   │   │   ├── RunEvent
│   │   │   ├── StageOutcome
│   │   │   ├── StageCompleted
│   │   │   └── StageFailed
│   │   ├── handles.py
│   │   │   └── old handle DTO migration contacts
│   │   ├── plan.py
│   │   │   ├── RunPlan
│   │   │   └── RunPlanStage
│   │   ├── provenance.py
│   │   │   ├── ArtifactRef
│   │   │   ├── StageManifest
│   │   │   └── RunSummary
│   │   ├── request.py
│   │   │   ├── RunRequest migration contact
│   │   │   ├── SourceSpec migration contact
│   │   │   └── PlacementPolicy migration contact
│   │   ├── runtime.py
│   │   │   ├── RunState
│   │   │   └── RunSnapshot
│   │   ├── stages.py
│   │   │   └── StageKey alias/projection mapping
│   │   └── transport.py
│   │       └── transport-safe event base contracts
│   ├── demo.py
│   │   └── streaming source construction migration contact
│   ├── finalization.py
│   │   └── project_summary
│   ├── ingest.py
│   │   └── materialize_offline_manifest migration contact
│   ├── placement.py
│   │   └── actor_options_for_stage migration adapter
│   ├── ray_runtime
│   │   ├── common.py
│   │   │   └── Ray helper migration contacts
│   │   ├── coordinator.py
│   │   │   └── RunCoordinatorActor
│   │   ├── stage_actors.py
│   │   │   ├── OfflineSlamStageActor migration contact
│   │   │   ├── StreamingSlamStageActor migration contact
│   │   │   └── PacketSourceActor migration contact
│   │   ├── stage_execution.py
│   │   │   └── run_* helper migration contacts
│   │   └── stage_program.py
│   │       ├── RuntimeStageProgram migration contact
│   │       ├── RuntimeExecutionState migration contact
│   │       └── StageCompletionPayload migration contact
│   ├── run_service.py
│   │   └── RunService
│   ├── runner.py
│   │   ├── StageRunner
│   │   └── StageResultStore
│   ├── runtime_manager.py
│   │   ├── RuntimeManager
│   │   └── RuntimePreflightResult
│   ├── sinks
│   │   ├── jsonl.py
│   │   │   └── durable RunEvent JSONL sink
│   │   ├── rerun.py
│   │   │   ├── RerunEventSink
│   │   │   └── RerunSinkActor
│   │   └── rerun_policy.py
│   │       └── RerunLoggingPolicy
│   ├── snapshot_projector.py
│   │   └── SnapshotProjector
│   ├── source_resolver.py
│   │   └── OfflineSourceResolver migration contact
│   ├── stage_registry.py
│   │   └── StageRegistry migration contact
│   ├── stages
│   │   ├── __init__.py
│   │   ├── base
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   │   ├── StageConfig
│   │   │   │   ├── StageExecutionConfig
│   │   │   │   ├── ResourceSpec
│   │   │   │   ├── PlacementConstraint
│   │   │   │   ├── StageTelemetryConfig
│   │   │   │   └── StageCleanupPolicy
│   │   │   ├── contracts.py
│   │   │   │   ├── StageResult
│   │   │   │   ├── StageRuntimeStatus
│   │   │   │   ├── StageRuntimeUpdate
│   │   │   │   ├── VisualizationItem
│   │   │   │   └── VisualizationIntent
│   │   │   ├── handles.py
│   │   │   │   ├── TransientPayloadRef
│   │   │   │   └── PayloadResolver
│   │   │   ├── protocols.py
│   │   │   │   ├── BaseStageRuntime
│   │   │   │   ├── OfflineStageRuntime
│   │   │   │   ├── LiveUpdateStageRuntime
│   │   │   │   ├── StreamingStageRuntime
│   │   │   │   └── VisualizationAdapter
│   │   │   ├── proxy.py
│   │   │   │   ├── StageRuntimeProxy
│   │   │   │   └── private local/Ray invocation helpers
│   │   │   └── ray.py
│   │   │       └── Ray placement/invocation helpers
│   │   ├── source
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   │   ├── SourceStageConfig
│   │   │   │   ├── SourceBackendConfig
│   │   │   │   └── thin references to dataset/IO-owned source variants
│   │   │   └── runtime.py
│   │   │       ├── SourceRuntime
│   │   │       └── StreamingSourceSidecar
│   │   ├── slam
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   │   └── SlamStageConfig
│   │   │   ├── runtime.py
│   │   │   │   └── SlamStageRuntime
│   │   │   └── visualization.py
│   │   │       └── SlamVisualizationAdapter
│   │   ├── ground_alignment
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   │   └── GroundAlignmentStageConfig
│   │   │   └── runtime.py
│   │   │       └── GroundAlignmentRuntime
│   │   ├── trajectory_eval
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   │   └── TrajectoryEvaluationStageConfig
│   │   │   └── runtime.py
│   │   │       └── TrajectoryEvaluationRuntime
│   │   ├── reconstruction
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   │   ├── ReconstructionStageConfig
│   │   │   │   └── references to reconstruction-owned backend config variants
│   │   │   ├── runtime.py
│   │   │   │   └── ReconstructionRuntime
│   │   │   └── visualization.py
│   │   │       └── optional future ReconstructionVisualizationAdapter
│   │   └── summary
│   │       ├── __init__.py
│   │       ├── config.py
│   │       │   └── SummaryStageConfig
│   │       └── runtime.py
│   │           └── SummaryRuntime
│   └── workspace.py
│       └── artifact workspace helpers
├── plotting
│   ├── artifact_diagnostics.py
│   │   └── artifact diagnostic figures
│   ├── metrics.py
│   │   └── metric figures
│   ├── pipeline.py
│   │   └── pipeline figure helpers
│   ├── reconstruction.py
│   │   └── reconstruction artifact figures
│   └── trajectories.py
│       └── trajectory figures
├── protocols
│   └── source.py
│       ├── OfflineSequenceSource
│       ├── StreamingSequenceSource
│       └── BenchmarkInputSource
├── reconstruction
│   ├── REQUIREMENTS.md
│   ├── config.py
│   │   ├── ReconstructionBackendConfig
│   │   ├── Open3dTsdfBackendConfig
│   │   └── future reconstruction backend config variants
│   ├── configs.py
│   │   └── reconstruction config compatibility re-exports
│   ├── contracts.py
│   │   ├── ReconstructionArtifacts
│   │   └── ReconstructionMetadata
│   ├── protocols.py
│   │   └── ReconstructionBackend
│   └── rgbd_source.py
│       └── RgbdObservationSource
├── utils
│   ├── __init__.py
│   │   └── utility export cleanup
│   ├── base_config.py
│   │   ├── BaseConfig
│   │   └── FactoryConfig
│   ├── base_data.py
│   │   └── BaseData
│   └── geometry.py
│       └── shared geometry / color-preserving PLY helpers
└── visualization
    ├── REQUIREMENTS.md
    ├── RERUN_SEMANTICS.md
    ├── __init__.py
    │   └── visualization export cleanup
    ├── contracts.py
    │   ├── VisualizationConfig
    │   └── visualization validation DTOs
    ├── rerun.py
    │   └── Rerun SDK helper boundary
    └── validation.py
        └── validation DTO migration contact
```

## Ownership Rules

- `config.py` owns the persisted declarative root and stage-section mapping.
  It does not construct runtimes, proxies, Ray actors, sink sidecars, or
  payload stores.
- `runtime_manager.py` is the only construction/deployment authority for stage
  runtimes, runtime proxies, payload stores, and runtime sidecars.
- `runner.py` owns generic stage lifecycle sequencing, result storage, and
  dependency lookup. It must not become a central per-stage input registry.
- `stages/base/*` owns generic pipeline runtime contracts only.
- `stages/<stage>/config.py` owns stage policy only. Backend/source/domain
  variant construction remains in the owning domain package.
- `stages/<stage>/runtime.py` adapts domain services/backends into pipeline
  runtime protocols.
- `stages/<stage>/visualization.py` converts semantic updates plus named
  transient refs into `VisualizationItem` values. It does not call the Rerun
  SDK.
- `stages/base/ray.py` contains Ray translation and invocation helpers only.
  Raw Ray handles, object refs, `.remote()` calls, and task refs do not leave
  Ray/runtime plumbing.

## Leaf-Symbol Rule

- Every listed class, protocol, DTO, and helper has exactly one owning file.
- Do not add shallow re-export hubs unless an existing public API already
  requires them.
- Stage-specific private input wrappers live in the stage package only when
  they carry real runtime-boundary semantics.
- Semantic payload DTOs stay with their domain owner. Examples:
  `SlamArtifacts` stays shared, `SlamUpdate` stays method-owned, and
  `GroundAlignmentMetadata` stays alignment-owned.
- Pipeline-owned DTOs remain generic orchestration, runtime, provenance,
  status, update, artifact-reference, and transient-payload contracts.

## Explicit Non-Targets

These names may appear here only to mark rejected target shapes:

- no `StageCatalog` as a central runtime source of truth
- no public `StageActor` role
- no `StageRuntimePolicy`
- no public `RetryPolicy` in the first slice
- no required public `StageInput` or `StageOutput` base DTOs for every stage
- no `StageRuntimeHandle`
- no `ActorBackedStageRuntime`
- no `LocalStageRuntime`
- no `VisualizationEnvelope`
- no Rerun SDK calls outside sinks/policy

## Migration Aliases

The implementation should keep current executable vocabulary working while the
new target vocabulary lands.

| Current key | Target key | Rule |
| --- | --- | --- |
| `ingest` | `source` | Keep current key during early runtime slices; add alias/projection tests before persisted public rename. |
| `ground.align` | `align.ground` | Keep current key during early runtime slices; add alias/projection tests before persisted public rename. |
| `reference.reconstruct` | `reconstruction` | Keep old run inspection working; model future variants under `[stages.reconstruction]`. |

Deletion of migration aliases belongs in the final migration-removal work
package only.

## Work Package Coordination

Work packages are persisted under
[pipeline-refactor-work-packages](./pipeline-refactor-work-packages/README.md).
Agents should use those files as the shared handoff surface:

- update only the assigned work-package file and owned code paths
- keep cross-package status in the work-package README index
- do not delete migration objects until their replacement and compatibility
  tests are named in a later work package
- use
  [WP-00A Baseline Acceptance](./pipeline-refactor-work-packages/WP-00A-baseline-acceptance.md)
  as the pre-implementation behavior-preservation gate
- use
  [WP-03A Telemetry Status](./pipeline-refactor-work-packages/WP-03A-telemetry-status.md)
  as the owner for `StageRuntimeStatus`, runtime telemetry fields, and
  time-domain semantics
- do not add a distributed-Ray target document or work package until cluster
  attach, runtime-env, storage locality, or on-prem deployment design is
  explicitly brought back into scope

## Implementation Hurdles

- Parallel agents can conflict in central docs and shared contracts. Mitigate
  by assigning owned paths per work package.
- The dirty worktree is not a valid behavioral baseline. Create a clean git
  worktree from the current branch/commit before production refactor work.
- Streaming credit release is fragile and must be tested independently from
  Rerun observers.
- Baseline acceptance is not optional. Implementation packages must preserve
  stage order, stage outcomes, artifact presence/type, event semantics, status
  projection, and affected viewer artifacts, even when exact scientific
  outputs are not byte-identical.
- Runtime telemetry must use the `WP-03A` field meanings: source timestamps for
  frame/sensor semantics, monotonic runtime time for latency/throughput/FPS,
  and wallclock time only for user-facing events/logs.
- Stage-key aliasing can break old run inspection silently. Add explicit
  alias/projection tests before renaming persisted/public keys.
- `TransientPayloadRef` must not leak into pure domain DTOs. Add import-boundary
  or grep tests.
- Rerun SDK usage must not leak into DTOs, runtimes, methods, or visualization
  adapters. Add import-boundary tests.
- The target can become over-abstract again. Termination criteria must require
  behavior preservation, not just scaffolding completion.
- Migration objects should be deleted only after every consumer has moved to a
  named replacement and compatibility tests pass.

## Required Docs Checks

- `git diff --check -- docs/architecture/pipeline-refactor-target-dir-tree.md docs/architecture/pipeline-refactor-work-packages`
- Verify work-package links for `WP-00A-baseline-acceptance.md` and
  `WP-03A-telemetry-status.md`.
- Grep stale target terms in this file and confirm all hits are in
  `Explicit Non-Targets` or explicitly marked migration contacts.
- Verify links resolve to:
  - [pipeline-stage-refactor-target.md](./pipeline-stage-refactor-target.md)
  - [pipeline-stage-present-state-audit.md](./pipeline-stage-present-state-audit.md)
  - [pipeline-stage-protocols-and-dtos.md](./pipeline-stage-protocols-and-dtos.md)
