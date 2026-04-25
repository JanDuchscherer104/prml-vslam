# Pipeline DTO Migration Ledger

This ledger is the implementation checklist for moving from the current
executable DTO/message model to the target model in
[pipeline-stage-refactor-target.md](./pipeline-stage-refactor-target.md).

Use [pipeline-stage-protocols-and-dtos.md](./pipeline-stage-protocols-and-dtos.md)
as the current-state reference. Use this ledger to decide which work package
owns each migration and when a compatibility object can be deleted.

Deletion is deferred to `WP-10` unless the row explicitly names another
package. Work packages must not delete migration objects outside their assigned
rows.

| Current symbol | Current owner | Current role | Target action | Target owner | Work package | Compatibility requirement | Deletion gate | Verification |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `StageCompletionPayload` | `pipeline.ray_runtime.stage_program` | Broad runtime handoff bag for stage outputs. | Replace with `StageResult` plus keyed `StageResultStore`; keep wrapper while current call sites remain. | `pipeline.stages.base.contracts` / `pipeline.runner` | WP-03, WP-10 | Existing helpers and actors keep returning compatible payloads until stage runtimes own the calls. | Delete after all stage bodies return `StageResult` and `RuntimeStageProgram` no longer consumes it. | Grep for `StageCompletionPayload`; stage runtime tests cover all current stages. |
| `RuntimeExecutionState` | `pipeline.ray_runtime.stage_program` | Mutable cross-stage state bag. | Replace with `StageResultStore` keyed by `StageKey`. | `pipeline.runner` | WP-03, WP-10 | Keep state adapter while `RuntimeStageProgram` still executes any stage. | Delete after stage input builders read only `StageResultStore`. | Grep for `RuntimeExecutionState`; missing-dependency tests for `StageResultStore`. |
| `StageRuntimeSpec` | `pipeline.ray_runtime.stage_program` | Central function-pointer stage router. | Replace with stage-local runtimes invoked by `StageRunner`. | `pipeline.runner` / `pipeline.stages.*` | WP-03, WP-10 | Keep as migration router while runtime skeleton wraps current helpers. | Delete after no executable path uses `RuntimeStageProgram.default()`. | Grep for `StageRuntimeSpec`; offline and streaming smoke paths pass. |
| `StageProgress` | `pipeline.contracts.events` | Narrow progress message DTO. | Collapse into `StageRuntimeStatus.progress` or live `StageRuntimeUpdate`. | `pipeline.stages.base.contracts` | WP-08, WP-10 | Keep projection compatibility until app/CLI reads runtime status. | Delete after `StageProgressed` and `RunSnapshot.stage_progress` consumers migrate. | Grep for `StageProgress`; app snapshot tests pass. |
| `StageProgressed` | `pipeline.contracts.events` | Telemetry `RunEvent` for progress. | Move progress telemetry to `StageRuntimeUpdate`; target `RunEvent` is durable-only. | `pipeline.stages.base.contracts` | WP-08, WP-10 | Preserve event reader compatibility until live update projection replaces it. | Delete after no app/CLI/sink consumer requires progress events. | Grep for `StageProgressed`; event JSONL tests prove durable-only model. |
| `PacketObserved` | `pipeline.contracts.events` | Telemetry `RunEvent` for streaming packets. | Move packet telemetry to `StageRuntimeUpdate` or source live update payloads. | `pipeline.stages.base.contracts` / `sources` | WP-08, WP-10 | Keep current streaming projection until source/SLAM live updates cover packet status. | Delete after source packet telemetry reaches snapshots without durable telemetry events. | Grep for `PacketObserved`; streaming snapshot tests pass. |
| `ObservationSummary` | `pipeline.contracts.events` | Transport-safe packet summary. | Make it a live-update payload or stage-local/private runtime DTO. | `sources` or `pipeline.stages.base.contracts` | WP-08, WP-10 | Keep as migration payload while `PacketObserved` and current actors use it. | Delete or move after current event and actor paths migrate. | Grep for `ObservationSummary`; source/SLAM streaming tests pass. |
| `BackendNoticeReceived` | `pipeline.contracts.events` | Telemetry `RunEvent` carrying `BackendEvent`. | Replace with `StageRuntimeUpdate.semantic_events` and visualization items. | `pipeline.stages.base.contracts` | WP-08, WP-10 | Keep for current Rerun/projector paths until `VisualizationItem` routing lands. | Delete after Rerun sink and snapshot projector consume live updates. | Grep for `BackendNoticeReceived`; Rerun tests use `VisualizationItem`. |
| `StreamingRunSnapshot` | `pipeline.contracts.runtime` | Streaming-specific snapshot subclass. | Collapse into keyed `stage_runtime_status`, `stage_outcomes`, and live refs on `RunSnapshot`. | `pipeline.contracts.runtime` | WP-08, WP-09, WP-10 | Keep while app and CLI render current streaming fields. | Delete after app/CLI display status and live refs derive from target snapshot. | Grep for `StreamingRunSnapshot`; app/CLI snapshot tests pass. |
| Top-level `RunSnapshot` stage fields | `pipeline.contracts.runtime` | Convenience stage-specific projections such as `sequence_manifest`, `slam`, `summary`. | Replace with keyed outcomes, artifact refs, runtime status, and minimal convenience views only where needed. | `pipeline.contracts.runtime` | WP-08, WP-09 | Keep compatibility views until app/CLI and old run inspection migrate. | Remove only after every consumer reads keyed fields or explicit helper views. | App artifact/snapshot tests and old run inspection pass. |
| `RunSnapshot.stage_status` | `pipeline.contracts.runtime` | Third per-stage status map. | Remove from target snapshot; derive display status from `StageOutcome` and `StageRuntimeStatus`. | `pipeline.contracts.runtime` / app helpers | WP-08, WP-09, WP-10 | Keep until UI/CLI display helpers are introduced. | Delete after all consumers stop reading `snapshot.stage_status`. | Grep for `stage_status`; app/CLI status tests pass. |
| `ArrayHandle` | `pipeline.contracts.handles` | Ray-specific live array handle. | Collapse into `TransientPayloadRef`. | `pipeline.stages.base.handles` | WP-01, WP-08, WP-10 | Keep while current Rerun/projector/backend APIs use old handles. | Delete after all live payload reads use `TransientPayloadRef` resolver APIs. | Grep for `ArrayHandle`; payload resolver tests pass. |
| `PreviewHandle` | `pipeline.contracts.handles` | Ray-specific preview handle. | Collapse into `TransientPayloadRef`. | `pipeline.stages.base.handles` | WP-01, WP-08, WP-10 | Keep while current preview and Rerun paths use old handles. | Delete after preview payloads use `TransientPayloadRef`. | Grep for `PreviewHandle`; Rerun preview tests pass. |
| `BlobHandle` | `pipeline.contracts.handles` | Generic binary handle. | Collapse into `TransientPayloadRef`. | `pipeline.stages.base.handles` | WP-01, WP-08, WP-10 | Keep only if any current consumer remains. | Delete after no consumers remain. | Grep for `BlobHandle`; contract tests pass. |
| `TransientPayloadRef` | target-only | Backend-agnostic live payload metadata. | Add as pipeline-owned live transport DTO; do not put in pure domain DTOs. | `pipeline.stages.base.handles` | WP-01, WP-08 | Keep resolver API compatibility with old handle reads during transition. | Not deleted. | Import-boundary check: pure domain DTOs do not import it. |
| `SlamUpdate` | `interfaces.slam` currently; target `methods.contracts` | Method-owned rich live SLAM update. | Move out of `interfaces`; keep pure method-owned semantics and arrays inside method/runtime boundary. | `methods.contracts` | WP-06, WP-10 | Keep old import path until method/runtime call sites migrate. | Delete/re-export cleanup after all imports use method-owned location. | Grep imports; ensure no `TransientPayloadRef` import in `SlamUpdate`. |
| `BackendEvent` | `interfaces.slam` currently; target `methods.contracts` or migration-only | Transport-safe backend notice union. | Replace durable event path with domain-owned semantic DTOs in `StageRuntimeUpdate`; move or retire union. | `methods.contracts` / `pipeline.stages.base.contracts` | WP-06, WP-08, WP-10 | Keep while current `BackendNoticeReceived` and Rerun projector path exist. | Delete or move after live update routing and Rerun adapter replace it. | Grep for `BackendEvent`; live update tests cover notices. |
| `SlamSessionInit` | removed from `interfaces.slam` | Former streaming SLAM session init DTO. | Replaced by private `SlamStreamingStartStageInput` behind `SlamStageRuntime`; backend streaming lifecycle receives explicit manifest/reference inputs directly. | `methods.stage` | WP-06 | No production compatibility surface remains. | Deleted. | Grep for `SlamSessionInit`; SLAM runtime tests pass. |
| `KeyframeVisualizationReady` | `interfaces.slam` via `BackendEvent` | Backend event carrying visualization handles. | Replace with `VisualizationItem` values created by `SlamVisualizationAdapter`. | `methods.stage.visualization` | WP-07, WP-08, WP-10 | Keep while current Rerun sink consumes backend notices. | Delete after Rerun consumes `StageRuntimeUpdate.visualizations`. | Rerun tests assert `VisualizationItem` routing. |
| `RunConfig` | `pipeline.contracts.request` | Current persisted request root. | Supersede with `RunConfig`; keep compatibility adapter. | `pipeline.config` | WP-02, WP-09, WP-10 | Current TOML and CLI paths keep loading. | Delete only after target config flow and old config compatibility policy are complete. | `plan-run-config` / `run-config` current configs pass. |
| `SourceBackendConfig` | `pipeline.contracts.request` | Current source request union. | Replace with `SourceStageConfig` + `SourceBackendConfig` referencing dataset/IO-owned variants. | `sources.config` plus domain owners | WP-02, WP-04, WP-09, WP-10 | Keep current source resolver and config compatibility. | Delete after target source configs support old/current configs and old run inspection. | Source resolver/source runtime tests pass. |
| `StagePlacement` | `pipeline.contracts.request` | Current per-stage resource map. | Replace with `runtime policy fields`, `resource fields`, `placement fields`; keep Ray retry knobs implementation-private. | `pipeline.stages.base.config` | WP-02, WP-03, WP-10 | Keep request placement compatibility while Ray translation migrates. | Delete after `runtime policy fields` drives placement. | Placement tests and plan config tests pass. |
| `PlacementPolicy` | `pipeline.contracts.request` | Current placement collection. | Replace with stage execution policy on stage configs. | `pipeline.stages.base.config` / `pipeline.config` | WP-02, WP-03, WP-10 | Keep current request compatibility. | Delete after target configs cover placement. | Grep for `PlacementPolicy`; Ray option tests pass. |
| `StageDefinition` | `pipeline.contracts.stages` | Wrapper around `StageKey`. | Remove; `RunPlanStage` and stage configs carry planning metadata. | `pipeline.contracts.plan` / `pipeline.config` | WP-02, WP-10 | Keep while stage registry still returns definitions. | Delete after planner no longer imports it. | Grep for `StageDefinition`; planning tests pass. |
| `ingest` stage key | `pipeline.contracts.stages.StageKey` | Current executable source-normalization stage name. | Alias/project to target `source`; keep current executable key early. | `pipeline.config` / `pipeline.contracts.stages` | WP-02, WP-09, WP-10 | Old runs and current stage registry remain inspectable. | Delete alias only after persisted/public target naming and old run inspection are addressed. | Alias/projection tests for current and target names. |
| `gravity.align` stage key | `pipeline.contracts.stages.StageKey` | Current executable gravity/ground-alignment stage name. | Keep as the target public stage key. | `pipeline.config` / `alignment.stage` | WP-02, WP-05, WP-09 | Current runs, manifests, summaries, and stage config sections remain inspectable. | Not deleted. | Stage-key projection and gravity-alignment planning tests. |
| `trajectory.evaluate` stage key | `pipeline.contracts.stages.StageKey` | Current executable trajectory-evaluation stage name. | Alias/project to target `evaluate.trajectory`; keep current executable key early. | `pipeline.config` / `eval.stage_trajectory` | WP-02, WP-05, WP-09, WP-10 | Old runs, manifests, summaries, and current stage registry remain inspectable. | Delete alias only after persisted/public target naming and old run inspection are addressed. | Alias/projection and trajectory-evaluation planning tests for current and target names. |
| `reference.reconstruct` stage key | `pipeline.contracts.stages.StageKey` | Current placeholder reconstruction key. | Alias/project to target `reconstruction`; model variants under `[stages.reconstruction]`. | `pipeline.config` / `reconstruction.stage` | WP-02, WP-05, WP-09, WP-10 | Old runs and placeholder diagnostics remain inspectable. | Delete alias only after target reconstruction naming is public and old runs are covered. | Alias/projection and reconstruction planning tests. |
| `cloud.evaluate` stage key | `pipeline.contracts.stages.StageKey` | Current placeholder dense-cloud evaluation key. | Alias/project to target `evaluate.cloud`; keep current placeholder key early. | `pipeline.config` / future eval stage owner | WP-02, WP-09, WP-10 | Old runs, manifests, summaries, and current stage registry remain inspectable. | Delete alias only after persisted/public target naming and old run inspection are addressed. | Alias/projection and unavailable-placeholder planning tests for current and target names. |
| `efficiency.evaluate` stage key | `pipeline.contracts.stages.StageKey` | Former placeholder efficiency evaluation key. | Deleted; efficiency evaluation is outside the current target. | removed | WP-10 | No compatibility remains. | Done. | Stale-symbol grep for `efficiency.evaluate` is clean outside historical notes. |
| `StageManifest` | `pipeline.contracts.provenance` | Durable per-stage manifest. | Keep but derive from `StageOutcome`; avoid duplicating canonical status/artifact truth. | `pipeline.contracts.provenance` | WP-08 | Maintain artifact inspection compatibility. | Not deleted unless replaced by explicit manifest projection. | Manifest/summary tests compare derived outcomes. |
| `RunSummary.stage_status` | `pipeline.contracts.provenance` | Final per-stage status map. | Keep as summary projection derived from terminal `StageOutcome`, not a source of truth. | `pipeline.contracts.provenance` | WP-08 | Preserve existing summaries. | Not deleted unless summary schema is intentionally revised. | Summary projection tests verify derivation. |
| `ArtifactRef` | `interfaces.slam` currently | Durable artifact reference used beyond SLAM. | Move to generic artifact/provenance owner. | `pipeline.contracts.provenance` or generic artifact contract | WP-08, WP-10 | Keep old import path until all artifact bundles migrate. | Delete/re-export cleanup after imports use target owner. | Grep imports; artifact inspection tests pass. |
| `EvaluationArtifact` | `eval.contracts` | Generic evaluation artifact. | Rename/specialize to `TrajectoryEvaluationArtifact` when cloud/efficiency become first-class. | `eval.contracts` | future eval work package | Keep current metric pages/services working. | Defer deletion until new eval artifacts are implemented. | Eval service and metric page tests pass. |

## Config Migration And Compatibility

These config classes directly affect pipeline launch, planning, source/backend
selection, or stage policy. They are not all deleted; the target action says
whether to keep, move, wrap, or specialize them.

| Current symbol | Current owner | Current role | Target action | Target owner | Work package | Compatibility requirement | Deletion gate | Verification |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `VideoSourceBackendConfig` | `pipeline.contracts.request` | Raw-video source selection inside `SourceBackendConfig`. | Preserve through compatibility adapter; target source config references source variants without moving media semantics into pipeline. | `sources.config` plus source owner | WP-02, WP-04, WP-09 | Existing video TOML/request paths continue loading. | Delete only with `SourceBackendConfig` after target config and old-run compatibility are complete. | Current config load tests and source runtime tests. |
| `DatasetSourceBackendConfig` | `pipeline.contracts.request` | Dataset source selection inside `SourceBackendConfig`. | Preserve through compatibility adapter; target source config references dataset-owned config/selection semantics. | `sources.config` plus `datasets` | WP-02, WP-04, WP-09 | Existing ADVIO/TUM configs continue loading. | Delete only with `SourceBackendConfig`. | Dataset source plan/runtime tests. |
| `Record3DLiveSourceBackendConfig` | `pipeline.contracts.request` | Record3D live source selection. | Preserve through compatibility adapter; target source config references IO-owned Record3D transport config. | `sources.config` plus `io` | WP-02, WP-04, WP-09 | Existing streaming config and app controls continue working. | Delete only with `SourceBackendConfig`. | Record3D config/app tests and mocked streaming tests. |
| `RayRuntimeConfig` | `pipeline.contracts.execution` | Single-field local Ray lifecycle wrapper carrying `local_head_lifecycle`. | Inline as `RunConfig.ray_local_head_lifecycle` and delete the wrapper. | `pipeline.config` | WP-10 | No compatibility is required once WP-10 starts; `[runtime.ray]` is removed with request compatibility. | Delete after CLI/backend callers read `RunConfig.ray_local_head_lifecycle` and committed configs use the root field. | Grep for `RayRuntimeConfig`, `RayLocalHeadLifecycle`, and `runtime.ray`; config parsing and Ray backend tests pass. |
| `RunRuntimeConfig` | `pipeline.contracts.execution` | Wrapper whose only field is `ray: RayRuntimeConfig`. | Delete and inline the only carried lifecycle policy onto `RunConfig`. | `pipeline.config` | WP-10 | No compatibility is required once WP-10 starts; `RunConfig.runtime` is removed. | Delete after all callers stop reading `run_config.runtime.ray.local_head_lifecycle`. | Grep for `RunRuntimeConfig` and `runtime.ray.local_head_lifecycle`; CLI reusable-head tests pass. |
| `SlamStageConfig` | `pipeline.contracts.request` | Former SLAM request section. | Replaced by stage-local `SlamStageConfig`; persisted backend variants and output policy are stage-owned. | `methods.stage.config` | WP-02, WP-06, WP-10 | No request compatibility remains. | Done. | SLAM config parsing and runtime tests. |
| `BenchmarkConfig` | `benchmark.contracts` | Former benchmark policy bundle. | Deleted from persisted `RunConfig`; stage policy now lives under stage sections. | removed | WP-10 | Old `[benchmark.*]` TOML sections are ignored with diagnostics only. | Done. | Config-warning and planning tests. |
| `TrajectoryBenchmarkConfig` | `benchmark.contracts` | Former trajectory evaluation policy. | Replaced by `TrajectoryEvaluationPolicy` under `[stages.evaluate_trajectory]`. | `eval.stage_trajectory.config` | WP-05, WP-10 | No benchmark-owned trajectory policy remains. | Done. | Trajectory planning/eval tests. |
| `CloudBenchmarkConfig` | `benchmark.contracts` | Former cloud evaluation placeholder policy. | Replaced by the diagnostic `[stages.evaluate_cloud]` config and binding. | `eval.stage_cloud.config` | WP-10 | No benchmark-owned cloud policy remains. | Done. | Planning unavailable-row tests. |
| `EfficiencyBenchmarkConfig` | `benchmark.contracts` | Former future efficiency placeholder. | Deleted; efficiency evaluation is outside the current target. | removed | WP-10 | No compatibility remains. | Done. | Package export and grep tests. |
| `ReferenceReconstructionConfig` | `benchmark.contracts` | Former reference reconstruction policy/config. | Replaced by `[stages.reconstruction]` using package-owned reconstruction backend configs. | `reconstruction.config` / `reconstruction.stage.config` | WP-05, WP-10 | No `reference.reconstruct` compatibility remains. | Done. | Reconstruction planning tests. |
| `AlignmentConfig` | `alignment.contracts` | Former one-field alignment policy bundle. | Deleted; stage config references `GroundAlignmentConfig` directly. | removed | WP-10 | No alignment bundle compatibility remains. | Done. | Ground alignment tests. |
| `GroundAlignmentConfig` | `alignment.contracts` | Ground alignment stage policy. | Keep alignment-owned and referenced directly from stage config. | `alignment.contracts` | WP-05 | Current alignment service input remains compatible. | Not deleted. | Alignment service/runtime tests. |
| `VisualizationConfig` | `visualization.contracts` | Viewer/export policy. | Keep visualization-owned; stage runtimes/adapters do not own SDK policy. | `visualization.contracts` | WP-07, WP-09 | Current viewer/export settings remain accepted. | Not deleted. | Rerun/CLI/app tests. |
| `SlamOutputPolicy` | `methods.stage.config` | Former method-facing output materialization policy. | Stage-owned output policy is canonical for persisted runs; method protocols consume it structurally. | `methods.stage.config` | WP-06, WP-10 | No persisted method-owned output policy remains. | Done. | Method and SLAM runtime tests. |
| `SlamBackendConfig` | `methods.stage.config` | Former base method backend config. | Shrunk to generic runtime options for method protocols/tests only. | `methods.stage.config` | WP-10 | No discriminated config union remains in methods. | Done. | Backend/runtime tests. |
| `VistaSlamBackendConfig` | `methods.stage.config` | Stage-owned ViSTA backend config variant. | Methods consume the canonical config directly; the structural options protocol was deleted. | `methods.stage.config` | WP-10 | No method-owned `FactoryConfig` or options protocol remains. | Done. | ViSTA config/smoke planning tests. |
| `Mast3rSlamBackendConfig` | `methods.stage.config` | Stage-owned MASt3R backend config variant. | Methods consume the canonical config directly; the structural options protocol was deleted. | `methods.stage.config` | WP-10 | No method-owned `FactoryConfig` or options protocol remains. | Done. | Backend config tests. |
| `ReconstructionBackendConfig` | `reconstruction.config` | Reconstruction backend base config. | Keep reconstruction-owned; stage config references backend variant union. | `reconstruction.config` | WP-02, WP-05 | Existing reconstruction backend configs remain compatible. | Not deleted. | Reconstruction config tests. |
| `Open3dTsdfBackendConfig` | `reconstruction.config` | Open3D TSDF backend config. | Keep reconstruction-owned `FactoryConfig`. | `reconstruction.config` | WP-05 | Existing Open3D TSDF config remains compatible. | Not deleted. | Reconstruction backend tests. |

## Kept Canonical Domain And Shared DTOs

These symbols are intentionally not pipeline-owned migration targets. They
remain with their current domain/shared owners unless a future package-specific
refactor says otherwise.

| Current symbol | Current owner | Current role | Target action | Target owner | Work package | Compatibility requirement | Deletion gate | Verification |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `SequenceManifest` | `sources.contracts` | Normalized source manifest. | Keep canonical source-owned DTO. | `sources.contracts` | WP-04 | Must remain the source-to-downstream boundary. | Not deleted. | Source/runtime tests. |
| `PreparedBenchmarkInputs` | `sources.contracts` | Prepared reference inputs. | Keep canonical source-prepared reference DTO. | `sources.contracts` | WP-04, WP-05 | Existing source/eval stages consume it. | Not deleted. | Eval/reconstruction tests. |
| `SourceStageOutput` | `sources.contracts` | Source-stage result payload bundling the normalized sequence and optional prepared benchmark inputs. | Keep canonical source output DTO for `StageResult.payload`. | `sources.contracts` | WP-04 | Downstream source accessors read this before legacy split fields. | Not deleted. | Source runtime and result-store tests. |
| `ReferenceTrajectoryRef` | `sources.contracts` | Durable reference trajectory ref. | Keep source-prepared reference DTO. | `sources.contracts` | WP-04 | Existing eval consumes it through prepared inputs. | Not deleted. | Trajectory eval tests. |
| `ReferenceCloudRef` | `sources.contracts` | Durable reference cloud ref. | Keep source-prepared reference DTO. | `sources.contracts` | WP-04, WP-05 | Existing/future cloud/reconstruction consumers remain compatible. | Not deleted. | Reconstruction/cloud planning tests. |
| `ReferencePointCloudSequenceRef` | `sources.contracts` | Durable point-cloud sequence ref. | Keep source-prepared reference DTO. | `sources.contracts` | WP-04 | Preserve ADVIO/Tango references. | Not deleted. | ADVIO ingest tests. |
| `Observation` | `sources.contracts` | Live/replay source observation. | Keep source-owned streaming DTO. | `sources.contracts` | WP-04, WP-06 | Current replay and streaming use it. | Not deleted. | Streaming tests. |
| `ObservationProvenance` | `sources.contracts` | Source observation provenance metadata. | Keep source-owned streaming DTO. | `sources.contracts` | WP-04, WP-06 | Preserve provenance through source/SLAM. | Not deleted. | Streaming/source tests. |
| `FrameTransform` | `interfaces.transforms` | Shared transform DTO. | Keep shared DTO. | `interfaces.transforms` | WP-06, WP-07 | Preserve pose semantics. | Not deleted. | SLAM/Rerun tests. |
| `CameraIntrinsics` | `interfaces.camera` | Shared camera model. | Keep shared DTO. | `interfaces.camera` | WP-06, WP-07 | Preserve intrinsics semantics. | Not deleted. | Camera/Rerun tests. |
| `CameraIntrinsicsSample` | `interfaces.camera` | Intrinsics sample in series. | Keep shared DTO. | `interfaces.camera` | future eval/diagnostics | Preserve artifact diagnostics. | Not deleted. | Intrinsics diagnostics tests. |
| `CameraIntrinsicsSeries` | `interfaces.camera` | Intrinsics time/sequence series. | Keep shared DTO. | `interfaces.camera` | future eval/diagnostics | Preserve artifact diagnostics. | Not deleted. | Intrinsics diagnostics tests. |
| `GroundAlignmentMetadata` | `interfaces.alignment` | Derived ground alignment artifact. | Keep alignment-owned semantic DTO. | `interfaces.alignment` | WP-05 | Preserve downstream/app consumption. | Not deleted. | Alignment tests. |
| `GroundPlaneModel` | `interfaces.alignment` | Ground plane model. | Keep alignment-owned semantic DTO. | `interfaces.alignment` | WP-05 | Preserve alignment metadata. | Not deleted. | Alignment tests. |
| `GroundPlaneVisualizationHint` | `interfaces.alignment` | Visualization hint for ground plane. | Keep until visualization adapter explicitly replaces/uses it. | `interfaces.alignment` | WP-05, WP-07 | Preserve current viewer behavior. | Not deleted. | Rerun/alignment tests. |
| `VisualizationArtifacts` | `interfaces.visualization` | Durable visualization artifact refs. | Keep visualization-owned semantic DTO. | `interfaces.visualization` | WP-07 | Preserve native/repo viewer artifacts. | Not deleted. | Visualization artifact tests. |
| `Observation` | `interfaces.observation` | Normalized posed RGB-D observation. | Keep shared DTO. | `interfaces.observation` | WP-05 | Reconstruction consumes it. | Not deleted. | Reconstruction tests. |
| `ObservationProvenance` | `interfaces.observation` | RGB-D observation provenance. | Keep shared DTO. | `interfaces.observation` | WP-05 | Preserve source/method provenance. | Not deleted. | Reconstruction tests. |
| `ObservationIndexEntry` | `interfaces.observation` | RGB-D sequence index row. | Keep shared DTO. | `interfaces.observation` | WP-05 | Preserve file-backed observation loading. | Not deleted. | RGB-D source tests. |
| `ObservationSequenceIndex` | `interfaces.observation` | RGB-D sequence index. | Keep shared DTO. | `interfaces.observation` | WP-05 | Preserve reconstruction source loading. | Not deleted. | RGB-D source tests. |
| `ObservationSequenceRef` | `interfaces.observation` | Durable prepared RGB-D sequence ref. | Keep shared DTO. | `interfaces.observation` | WP-05 | Preserve reconstruction stage input. | Not deleted. | Reconstruction planning/runtime tests. |
| `ReconstructionArtifacts` | `reconstruction.contracts` | Reconstruction output artifact bundle. | Keep reconstruction-owned DTO. | `reconstruction.contracts` | WP-05 | Preserve reconstruction package boundary. | Not deleted. | Reconstruction tests. |
| `ReconstructionMetadata` | `reconstruction.contracts` | Reconstruction side metadata. | Keep reconstruction-owned DTO. | `reconstruction.contracts` | WP-05 | Preserve reconstruction artifacts. | Not deleted. | Reconstruction tests. |

## Eval-Owned DTOs And Future Specialization

| Current symbol | Current owner | Current role | Target action | Target owner | Work package | Compatibility requirement | Deletion gate | Verification |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `MetricStats` | `eval.contracts` | Scalar metric summary. | Keep eval-owned. | `eval.contracts` | WP-05 / future eval | Preserve metric artifacts. | Not deleted. | Eval tests. |
| `TrajectorySeries` | `eval.contracts` | Trajectory series for eval/plots. | Keep eval-owned. | `eval.contracts` | WP-05 | Preserve trajectory eval. | Not deleted. | Eval/plot tests. |
| `ErrorSeries` | `eval.contracts` | Error series for eval/plots. | Keep eval-owned. | `eval.contracts` | WP-05 | Preserve trajectory eval. | Not deleted. | Eval/plot tests. |
| `TrajectoryEvaluationPreview` | `eval.contracts` | Preview payload for trajectory eval. | Keep eval-owned; may feed future visualization items through adapter. | `eval.contracts` | WP-05, WP-07 later | Preserve current metric UI. | Not deleted. | Metrics page tests. |
| `TrajectoryEvaluationSemantics` | `eval.contracts` | Evaluation semantics metadata. | Keep eval-owned. | `eval.contracts` | WP-05 | Preserve eval artifact semantics. | Not deleted. | Eval tests. |
| `IntrinsicsComparisonDiagnostics` | `eval.contracts` | Intrinsics comparison diagnostics. | Keep eval-owned. | `eval.contracts` | future eval | Preserve diagnostics. | Not deleted. | Intrinsics tests. |
| `DenseCloudEvaluationSelection` | `eval.contracts` | Dense-cloud eval selection. | Keep eval-owned future-stage DTO. | `eval.contracts` | future eval | Preserve placeholder/UI state. | Not deleted. | Metrics tests. |
| `DenseCloudEvaluationArtifact` | `eval.contracts` | Dense-cloud eval artifact. | Keep eval-owned future artifact DTO. | `eval.contracts` | future eval | Preserve future stage design. | Not deleted. | Future cloud eval tests. |
| `EfficiencyEvaluationSelection` | `eval.contracts` | Efficiency eval selection. | Keep eval-owned future-stage DTO. | `eval.contracts` | future eval | Preserve placeholder/UI state. | Not deleted. | Metrics tests. |
| `EfficiencyEvaluationArtifact` | `eval.contracts` | Efficiency eval artifact. | Keep eval-owned future artifact DTO. | `eval.contracts` | future eval | Preserve future stage design. | Not deleted. | Future efficiency tests. |
| `DiscoveredRun` | `eval.contracts` | Discovered run for metrics UI. | Keep eval/app-facing DTO. | `eval.contracts` | WP-09 / future eval | Preserve metrics page. | Not deleted. | Metrics page tests. |
| `SelectionSnapshot` | `eval.contracts` | Metrics selection snapshot. | Keep eval/app-facing DTO. | `eval.contracts` | WP-09 / future eval | Preserve metrics page. | Not deleted. | Metrics page tests. |
| `EvaluationSelection` | `eval.contracts` | Evaluation selection state. | Keep eval/app-facing DTO. | `eval.contracts` | WP-09 / future eval | Preserve metrics page. | Not deleted. | Metrics page tests. |

## Dataset, IO, App, Plotting, And Inspection DTOs Out Of Scope

These DTOs are intentionally out of scope for the pipeline runtime refactor
unless a later work package explicitly names them. They remain with their
current owners.

| Current symbol | Current owner | Target action | Owning scope | Verification |
| --- | --- | --- | --- | --- |
| `FrameSelectionConfig` | `datasets.contracts` | Keep dataset/source selection config. | datasets | Dataset/source tests. |
| `AdvioServingConfig` | `datasets.contracts` | Keep dataset-serving config. | datasets | ADVIO tests. |
| `DatasetDownloadResult` | `datasets.contracts` | Keep dataset download DTO. | datasets | Dataset tests. |
| `LocalSceneStatus` | `datasets.contracts` | Keep local scene status DTO. | datasets | Dataset tests. |
| `DatasetSummary` | `datasets.contracts` | Keep dataset summary DTO. | datasets | Dataset tests. |
| `AdvioDownloadRequest` | `datasets.advio.advio_models` | Keep ADVIO download request. | datasets | ADVIO tests. |
| `AdvioSequenceConfig` | `datasets.advio.advio_models` | Keep ADVIO sequence config. | datasets | ADVIO tests. |
| `AdvioStreamingSourceConfig` | `datasets.advio.advio_service` | Keep ADVIO streaming source config. | datasets | Streaming dataset tests. |
| `TumRgbdDownloadRequest` | `datasets.tum_rgbd.tum_rgbd_models` | Keep TUM download request. | datasets | TUM tests. |
| `TumRgbdSequenceConfig` | `datasets.tum_rgbd.tum_rgbd_models` | Keep TUM sequence config. | datasets | TUM tests. |
| `Record3DDevice` | `io.record3d` | Keep IO device DTO. | io | Record3D tests. |
| `Record3DStreamConfig` | `io.record3d` | Keep IO stream config. | io | Record3D tests. |
| `Record3DStreamingSourceConfig` | `io.record3d_source` | Keep IO streaming source config. | io | Record3D source tests. |
| `Record3DWiFiMetadata` | `io.wifi_packets` | Keep Wi-Fi metadata DTO. | io | Wi-Fi tests. |
| `Record3DWiFiPreviewStreamConfig` | `io.wifi_session` | Keep Wi-Fi preview config. | io | Wi-Fi tests. |
| `PyAvVideoObservationSource` | `sources.replay.video` | Keep canonical PyAV video observation source. | sources.replay | Source/replay tests. |
| `PipelinePageState` | `app.models` | Keep Streamlit state DTO. | app | App tests. |
| `AppState` | `app.models` | Keep Streamlit root state DTO. | app | App tests. |
| `AdvioPageState` | `app.models` | Keep app state DTO. | app | App tests. |
| `TumRgbdPageState` | `app.models` | Keep app state DTO. | app | App tests. |
| `MetricsPageState` | `app.models` | Keep app state DTO. | app | App tests. |
| `ArtifactInspectorPageState` | `app.models` | Keep app state DTO. | app | App tests. |
| `Record3DPageState` | `app.models` | Keep app state DTO. | app | App tests. |
| `Record3DPageAction` | `app.models` | Keep app action DTO. | app | App tests. |
| `Record3DTransportSelection` | `app.models` | Keep app selection DTO. | app | App tests. |
| `PacketSessionSnapshot` | `app.preview_runtime` | Keep app preview DTO. | app | App preview tests. |
| `PreviewSessionSnapshot` | `app.models` | Keep app preview DTO. | app | App preview tests. |
| `Record3DStreamSnapshot` | `app.models` | Keep app preview DTO. | app | App preview tests. |
| `AdvioPreviewSnapshot` | `app.models` | Keep app preview DTO. | app | App preview tests. |
| `RunArtifactCandidate` | `pipeline.artifact_inspection` | Keep artifact inspection DTO. | pipeline inspection | Artifact inspection tests. |
| `ArtifactFileRow` | `pipeline.artifact_inspection` | Keep artifact inspection row DTO. | pipeline inspection | Artifact inspection tests. |
| `ArtifactPathRow` | `pipeline.artifact_inspection` | Keep artifact inspection row DTO. | pipeline inspection | Artifact inspection tests. |
| `InputArtifactDiagnostics` | `pipeline.artifact_inspection` | Keep artifact diagnostics DTO. | pipeline inspection | Artifact inspection tests. |
| `RunAttemptSummary` | `pipeline.artifact_inspection` | Keep attempt summary DTO; align with attempt identity target. | pipeline inspection | Artifact inspection tests. |
| `RunArtifactInspection` | `pipeline.artifact_inspection` | Keep artifact inspection DTO. | pipeline inspection | Artifact inspection tests. |
| `ReconstructionVisualizationSummary` | `plotting.reconstruction` | Keep plotting DTO. | plotting | Plotting tests. |
| `SlamReferenceComparisonSummary` | `plotting.reconstruction` | Keep plotting DTO. | plotting | Plotting tests. |

## WP-00B AST Inventory Coverage Addendum

WP-00B audited 207 classes under `src/prml_vslam/**/*.py` whose direct bases
include `BaseData`, `BaseConfig`, `TransportModel`, `BaseModel`, `Protocol`,
`StrEnum`, `Enum`, or `IntEnum`. The rows below classify audited symbols that
were not already named in the ledger sections above. These rows are coverage
and ownership records only; they do not authorize DTO movement or deletion.

### Additional Pipeline And Runtime Migration Contacts

| Current symbol | Current owner | Target action | Owning scope | Verification |
| --- | --- | --- | --- | --- |
| `EventTier` | `pipeline.contracts.events` | Keep current event-tier discriminator until durable/live event split lands. | pipeline migration | Event JSONL and snapshot tests. |
| `_RunEventBase` | `pipeline.contracts.events` | Keep private transport base while current `RunEvent` union exists. | pipeline migration | Event serialization tests. |
| `RunPlan` | `pipeline.contracts.plan` | Keep canonical planning DTO. | pipeline | Planning tests. |
| `StageStatus` | `pipeline.contracts.provenance` | Keep as current summary/manifest vocabulary; target derives from terminal `StageOutcome` and live `StageRuntimeStatus`. | pipeline migration | Summary/manifest projection tests. |
| `RunSummary` | `pipeline.contracts.provenance` | Keep pipeline-owned generic provenance DTO. | pipeline | Summary artifact tests. |
| `PipelineMode` | `pipeline.contracts.request` | Keep current request-mode enum until `RunConfig.mode` supersedes it. | pipeline migration | Config parsing and CLI tests. |
| `RunState` | `pipeline.contracts.runtime` | Keep coarse run lifecycle projection. | pipeline | Snapshot and app/CLI tests. |
| `StageAvailability` | `pipeline.contracts.stages` | Collapse target availability into `RunPlanStage.available` and `availability_reason`; keep while current registry uses it. | pipeline migration | Planning diagnostics tests. |
| `TransportModel` | `pipeline.contracts.transport` | Keep current transport-safe base for events/snapshots until target contracts land. | pipeline migration | Transport serialization tests. |
| `RuntimeStageDriver` | `pipeline.ray_runtime.stage_program` | Replace with runtime manager/proxy protocol hooks; keep while current streaming SLAM driver hooks remain. | pipeline migration | Runtime skeleton and streaming tests. |
| `FrameSample` | `pipeline.workspace` | Keep workspace-local helper DTO. | pipeline workspace | Workspace/materialization tests. |
| `CaptureManifest` | `pipeline.workspace` | Keep workspace-local helper DTO. | pipeline workspace | Workspace/materialization tests. |

### Additional Kept Shared, Domain, And Protocol Symbols

| Current symbol | Current owner | Target action | Owning scope | Verification |
| --- | --- | --- | --- | --- |
| `ReferenceSource` | `sources.contracts` | Keep source-prepared baseline/source policy enum. | sources | Planning and trajectory-eval tests. |
| `ReferenceCloudSource` | `sources.contracts` | Keep source-prepared reference-cloud source enum. | sources | Reference-cloud tests. |
| `ReferenceCloudCoordinateStatus` | `sources.contracts` | Keep coordinate-status enum for prepared reference clouds. | sources | Reference-cloud metadata tests. |
| `TrajectoryMetricId` | `eval.contracts` | Keep eval-owned metric identifier enum. | eval | Eval service tests. |
| `TrajectoryAlignmentMode` | `eval.contracts` | Keep eval-owned metric alignment enum. | eval | Eval service tests. |
| `TrajectoryEvaluator` | `eval.protocols` | Keep eval-owned protocol seam. | eval | Eval service/protocol tests. |
| `DenseCloudEvaluator` | `eval.protocols` | Keep eval-owned future dense-cloud protocol. | eval | Future dense-cloud eval tests. |
| `EfficiencyEvaluator` | `eval.protocols` | Keep eval-owned future efficiency protocol. | eval | Future efficiency eval tests. |
| `AdvioRawPoseRefs` | `sources.contracts` | Keep source-owned DTO for ADVIO-native pose refs. | sources | Source and ADVIO tests. |
| `AdvioManifestAssets` | `sources.contracts` | Keep source-owned DTO for ADVIO-specific normalized assets. | sources | Source and ADVIO tests. |
| `Record3DTransportId` | `sources.contracts` | Keep source-owned transport enum used by live/replay source observations. | sources | Record3D and streaming tests. |
| `SlamArtifacts` | `interfaces.slam` | Keep shared normalized SLAM artifact bundle. | interfaces | SLAM, evaluation, alignment, and artifact tests. |
| `SlamUpdate` | `methods.contracts` | Unified live SLAM semantic update. | Keep one compact method-owned update DTO; pose, keyframe, map stats, warnings, and previews flow through it plus `StageRuntimeStatus`. | methods | WP-10 | Dedicated notice DTO variants are removed. | Done. | Live update and Rerun tests. |
| `MethodId` | `methods.stage.config` | Canonical SLAM backend discriminator. | Single enum used by stage configs, wrappers, protocols, tests, and eval labels. | pipeline stages / methods | WP-10 | The old method config module is deleted. | Done. | Backend config tests. |
| `BackendFactoryProtocol` | `methods.factory` | Removed; stage bindings and backend variant `setup_target()` calls own construction. | removed | Runtime and SLAM stage tests. |
| `SlamSession` | removed from `methods.protocols` | Former method-owned streaming session protocol. | Streaming lifecycle now lives directly on `StreamingSlamBackend`; `SlamStageRuntime` is the only pipeline runtime owner. | methods / WP-06 | SLAM runtime tests. |
| `OfflineSlamBackend` | `methods.protocols` | Keep method-owned offline backend protocol. | methods | Backend tests. |
| `StreamingSlamBackend` | `methods.protocols` | Keep method-owned streaming backend protocol. | methods | Streaming backend tests. |
| `SlamBackend` | `methods.protocols` | Keep combined method backend protocol. | methods | Backend tests. |
| `PipelineBackend` | `pipeline.backend` | Move to pipeline-local protocol owner when target public surface cleanup lands. | pipeline migration | App/CLI run-service tests. |
| `ObservationStream` | `sources.replay.protocols` | Keep source-owned observation-stream protocol. | sources.replay | Streaming tests. |
| `OfflineSequenceSource` | `protocols.source` | Keep shared offline source protocol. | protocols | Source/ingest tests. |
| `BenchmarkInputSource` | `protocols.source` | Keep shared benchmark-input source protocol. | protocols | Source/ingest/eval tests. |
| `StreamingSequenceSource` | `protocols.source` | Keep shared streaming source protocol. | protocols | Streaming source tests. |
| `ReconstructionMethodId` | `reconstruction.contracts` | Keep reconstruction-owned backend id enum. | reconstruction | Reconstruction config tests. |
| `OfflineReconstructionBackend` | `reconstruction.protocols` | Keep reconstruction-owned offline backend protocol. | reconstruction | Reconstruction backend tests. |
| `_ConfigFactory` | `utils.base_config` | Keep private utility protocol for config factories. | utils | Config tests. |
| `BaseConfig` | `utils.base_config` | Keep shared config base. | utils | Config serialization tests. |
| `BaseData` | `utils.base_data` | Keep shared data base. | utils | DTO serialization tests. |
| `RunArtifactPaths` | `utils.path_config` | Keep utility path DTO. | utils | PathConfig tests. |
| `PathConfig` | `utils.path_config` | Keep canonical repo path config. | utils | PathConfig tests. |
| `ExtractedVideoFrames` | `utils.video_frames` | Keep utility DTO for extracted frame batches. | utils | Video-frame helper tests. |

### Additional Explicitly Out-Of-Scope Audited Symbols

| Current symbol | Current owner | Target action | Owning scope | Verification |
| --- | --- | --- | --- | --- |
| `AppPageId` | `app.models` | Keep app navigation enum. | app | App tests. |
| `PreviewStreamState` | `app.models` | Keep app preview lifecycle enum. | app | App preview tests. |
| `AdvioDownloadFormData` | `app.models` | Keep app form DTO. | app | App tests. |
| `AdvioPreviewFormData` | `app.models` | Keep app form DTO. | app | App tests. |
| `AdvioPageData` | `app.models` | Keep app render DTO. | app | App tests. |
| `PipelineSourceId` | `app.models` | Keep app-local source selector enum. | app | Pipeline page tests. |
| `TangoCloudMetadata` | `datasets.advio.advio_geometry` | Keep dataset-local geometry metadata. | datasets | ADVIO geometry tests. |
| `Sim3Alignment` | `datasets.advio.advio_geometry` | Keep dataset-local alignment helper DTO. | datasets | ADVIO geometry tests. |
| `AdvioCalibration` | `datasets.advio.advio_loading` | Keep dataset-local calibration DTO. | datasets | ADVIO loading tests. |
| `AdvioEnvironment` | `datasets.advio.advio_models` | Keep dataset-local enum. | datasets | ADVIO tests. |
| `AdvioPeopleLevel` | `datasets.advio.advio_models` | Keep dataset-local enum. | datasets | ADVIO tests. |
| `AdvioModality` | `datasets.advio.advio_models` | Keep dataset-local enum. | datasets | ADVIO tests. |
| `AdvioDownloadPreset` | `datasets.advio.advio_models` | Keep dataset-local enum. | datasets | ADVIO download tests. |
| `AdvioUpstreamMetadata` | `datasets.advio.advio_models` | Keep dataset-local catalog DTO. | datasets | ADVIO catalog tests. |
| `AdvioSceneMetadata` | `datasets.advio.advio_models` | Keep dataset-local catalog DTO. | datasets | ADVIO catalog tests. |
| `AdvioCatalog` | `datasets.advio.advio_models` | Keep dataset-local catalog DTO. | datasets | ADVIO catalog tests. |
| `AdvioSequencePaths` | `datasets.advio.advio_sequence` | Keep dataset-local path DTO. | datasets | ADVIO sequence tests. |
| `AdvioOfflineSample` | `datasets.advio.advio_sequence` | Keep dataset-local sample DTO. | datasets | ADVIO sequence tests. |
| `AdvioSequence` | `datasets.advio.advio_sequence` | Keep dataset-local sequence DTO. | datasets | ADVIO sequence tests. |
| `DatasetId` | `datasets.contracts` | Keep dataset id enum. | datasets | Dataset tests. |
| `AdvioPoseSource` | `datasets.contracts` | Keep dataset pose-source enum. | datasets | ADVIO tests. |
| `AdvioPoseFrameMode` | `datasets.contracts` | Keep dataset pose-frame enum. | datasets | ADVIO tests. |
| `TumRgbdFrameAssociation` | `datasets.tum_rgbd.tum_rgbd_loading` | Keep dataset-local association DTO. | datasets | TUM RGB-D loading tests. |
| `TumRgbdOfflineSample` | `datasets.tum_rgbd.tum_rgbd_loading` | Keep dataset-local sample DTO. | datasets | TUM RGB-D loading tests. |
| `TumRgbdPoseSource` | `datasets.tum_rgbd.tum_rgbd_models` | Keep dataset-local enum. | datasets | TUM RGB-D tests. |
| `TumRgbdModality` | `datasets.tum_rgbd.tum_rgbd_models` | Keep dataset-local enum. | datasets | TUM RGB-D tests. |
| `TumRgbdDownloadPreset` | `datasets.tum_rgbd.tum_rgbd_models` | Keep dataset-local enum. | datasets | TUM RGB-D download tests. |
| `TumRgbdSceneMetadata` | `datasets.tum_rgbd.tum_rgbd_models` | Keep dataset-local catalog DTO. | datasets | TUM RGB-D catalog tests. |
| `TumRgbdCatalog` | `datasets.tum_rgbd.tum_rgbd_models` | Keep dataset-local catalog DTO. | datasets | TUM RGB-D catalog tests. |
| `TumRgbdSequencePaths` | `datasets.tum_rgbd.tum_rgbd_sequence` | Keep dataset-local path DTO. | datasets | TUM RGB-D sequence tests. |
| `TumRgbdSequence` | `datasets.tum_rgbd.tum_rgbd_sequence` | Keep dataset-local sequence DTO. | datasets | TUM RGB-D sequence tests. |
| `ReplayMode` | `sources.replay.clock` | Keep source replay pacing enum. | sources.replay | Source/replay tests. |
| `Record3DDeviceType` | `io.record3d` | Keep IO-local device enum. | io | Record3D tests. |
| `VistaViewGraphArtifact` | `methods.vista.artifact_io` | Keep ViSTA-native artifact DTO. | methods.vista | ViSTA artifact tests. |
| `VistaViewGraphEdge` | `methods.vista.diagnostics` | Keep ViSTA diagnostics DTO. | methods.vista | ViSTA diagnostics tests. |
| `VistaViewGraphNodeDegree` | `methods.vista.diagnostics` | Keep ViSTA diagnostics DTO. | methods.vista | ViSTA diagnostics tests. |
| `VistaViewGraphDiagnostics` | `methods.vista.diagnostics` | Keep ViSTA diagnostics DTO. | methods.vista | ViSTA diagnostics tests. |
| `VistaNativeSlamDiagnostics` | `methods.vista.diagnostics` | Keep ViSTA diagnostics DTO. | methods.vista | ViSTA diagnostics tests. |
| `_VistaImageDataset` | `methods.vista.preprocess` | Keep private ViSTA preprocess protocol. | methods.vista | ViSTA preprocess tests. |
| `VistaFramePreprocessor` | `methods.vista.preprocess` | Keep ViSTA preprocess protocol. | methods.vista | ViSTA preprocess tests. |
| `VistaFlowTracker` | `methods.vista.runtime` | Keep private ViSTA runtime protocol. | methods.vista | ViSTA runtime tests. |
| `VistaOnlineSlam` | `methods.vista.runtime` | Keep private ViSTA runtime protocol. | methods.vista | ViSTA runtime tests. |
| `_DbowVocabulary` | `methods.vista.runtime` | Keep private ViSTA runtime protocol. | methods.vista | ViSTA runtime tests. |
| `_DbowModule` | `methods.vista.runtime` | Keep private ViSTA runtime protocol. | methods.vista | ViSTA runtime tests. |
| `RerunPointCloudSnapshot` | `visualization.validation` | Keep visualization validation DTO until validation cleanup package moves it. | visualization | Rerun validation tests. |
| `RerunValidationSummary` | `visualization.validation` | Keep visualization validation DTO until validation cleanup package moves it. | visualization | Rerun validation tests. |
| `RerunValidationArtifacts` | `visualization.validation` | Keep visualization validation DTO until validation cleanup package moves it. | visualization | Rerun validation tests. |
