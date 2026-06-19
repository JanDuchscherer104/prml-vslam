# Graph Report - sweeper-pr88-integration  (2026-06-19)

## Corpus Check
- 292 files · ~1,096,405 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4744 nodes · 23058 edges · 32 communities detected
- Extraction: 30% EXTRACTED · 70% INFERRED · 0% AMBIGUOUS · INFERRED: 16067 edges (avg confidence: 0.59)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]

## God Nodes (most connected - your core abstractions)
1. `StageKey` - 451 edges
2. `SequenceManifest` - 434 edges
3. `PreparedBenchmarkInputs` - 336 edges
4. `DatasetId` - 319 edges
5. `PathConfig` - 290 edges
6. `ArtifactRef` - 281 edges
7. `MethodId` - 277 edges
8. `ReferenceSource` - 252 edges
9. `RunConfig` - 249 edges
10. `StageRuntimeStatus` - 238 edges

## Surprising Connections (you probably didn't know these)
- `LingbotMapSlamBackendConfig` --calls--> `test_lingbot_config_rejects_invalid_runtime_values()`  [INFERRED]
  src/prml_vslam/methods/stage/backend_config.py → tests/test_lingbot_method.py
- `MetricsPageState` --calls--> `test_metrics_page_state_preserves_persisted_view_fields()`  [INFERRED]
  src/prml_vslam/app/models.py → tests/test_app.py
- `SequenceManifest` --uses--> `Small runtime sources used by focused pipeline smoke tests.`  [INFERRED]
  src/prml_vslam/sources/contracts.py → tests/pipeline_testing_support.py
- `SequenceManifest` --uses--> `Minimal offline source for pipeline smoke tests.`  [INFERRED]
  src/prml_vslam/sources/contracts.py → tests/pipeline_testing_support.py
- `SequenceManifest` --uses--> `Finite in-memory packet stream for streaming smoke tests.`  [INFERRED]
  src/prml_vslam/sources/contracts.py → tests/pipeline_testing_support.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.02
Nodes (463): Trajectory-alignment contracts shared by evaluation and visualization.  Trajecto, Describe how trajectories are aligned before metric computation., State whether an alignment may publish a downstream dense cloud., Persist an explicit trajectory alignment used for diagnostics or metrics., TrajectoryAlignmentArtifact, TrajectoryAlignmentCloudUseStatus, TrajectoryAlignmentMode, InputArtifactDiagnostics (+455 more)

### Community 1 - "Community 1"
Cohesion: 0.01
Nodes (366): AdvioDownloadManager, _ensure_directory_parent(), AdvioDownloadRequest, AdvioEnvironment, AdvioPeopleLevel, AdvioSequenceConfig, AdvioUpstreamMetadata, ADVIO-specific metadata and config models.  This module owns the committed scene (+358 more)

### Community 2 - "Community 2"
Cohesion: 0.01
Nodes (372): _preprocess_images_with_lingbot(), build_slam_backend_config(), _coordinator_actor_options(), RayPipelineBackend, BaseConfig, _ConfigFactory, FactoryConfig, from_toml() (+364 more)

### Community 3 - "Community 3"
Cohesion: 0.01
Nodes (378): build_advio_comparison_trajectories(), Return the cache directory used for downloaded scene archives., Return one catalog scene by id., Return local availability status for every catalog scene., Download selected ADVIO scenes and extract complete scene payloads., advio_basis_metadata(), advio_basis_provenance(), AdvioBasisMetadata (+370 more)

### Community 4 - "Community 4"
Cohesion: 0.02
Nodes (299): _build_artifacts(), _DensePredictionArtifacts, _ensure_uint8_rgb_from_uimg(), _estimate_camera_intrinsics_from_frame(), _InProcessManager, _InProcessValue, LingbotMapSlamBackend, _LingbotRuntime (+291 more)

### Community 5 - "Community 5"
Cohesion: 0.01
Nodes (373): build_advio_page_data(), handle_advio_preview_action(), _scene_rows(), sync_advio_download_state(), sync_advio_preview_state(), _attempt_rows(), _candidate_label(), _inventory_rows() (+365 more)

### Community 6 - "Community 6"
Cohesion: 0.02
Nodes (256): Controller helpers for the ADVIO Streamlit page., Persist the current ADVIO download-form state., Keep persisted preview state aligned with the runtime snapshot., Apply one preview-form action and return an error message when it fails., BaseData, AppContext, build_context(), _build_pages() (+248 more)

### Community 7 - "Community 7"
Cohesion: 0.04
Nodes (276): BaseConfig, AdvioSourceConfig, CloudAlignmentStageConfig, CloudEvaluationStageConfig, CloudMetricId, DenseCloudSelectionConfig, GroundAlignmentStageConfig, Open3dTsdfBackendConfig (+268 more)

### Community 8 - "Community 8"
Cohesion: 0.02
Nodes (214): build_crowd_density_figure(), build_local_readiness_figure(), build_scene_attribute_figure(), build_scene_mix_figure(), Plotly figure builders for the ADVIO dataset page., Build a crowd-density composition chart., Build a scene-attribute prevalence chart., Build a stacked venue/environment overview for the catalog. (+206 more)

### Community 9 - "Community 9"
Cohesion: 0.02
Nodes (153): write_tum_trajectory(), ape_error_colors(), attach_recording_sinks(), augment_viewer_recording_with_ground_plane(), build_default_blueprint(), create_recording_stream(), _decimate_rows(), _entity_token() (+145 more)

### Community 10 - "Community 10"
Cohesion: 0.02
Nodes (145): _adapt_checkpoint_state_dict(), _as_numpy(), _build_lingbot_artifacts(), _cast_aggregator_for_inference(), _decode_pose_predictions(), _expect_lingbot_config(), _extract_checkpoint_state_dict(), _extract_dense_prediction_artifacts() (+137 more)

### Community 11 - "Community 11"
Cohesion: 0.06
Nodes (94): build_coverage_matrix(), build_heatmap_data(), build_leaderboard(), build_per_sequence_table(), CoverageCell, CoverageMatrix, HeatmapData, LeaderboardRow (+86 more)

### Community 12 - "Community 12"
Cohesion: 0.04
Nodes (57): Return the user-facing reconstruction label., Configure the minimal Open3D TSDF reconstruction backend.      The repo targets, Return the concrete reconstruction backend type., Instantiate the Open3D TSDF backend while ignoring unrelated kwargs., Describe normalized durable outputs from one reconstruction run.      The minima, ReconstructionArtifacts, ReconstructionMethodId, Enum (+49 more)

### Community 13 - "Community 13"
Cohesion: 0.07
Nodes (37): DenseCloudEvaluationArtifact, DenseCloudEvaluationSelection, from_evo_statistics(), Persist one dense-cloud evaluation result for later review., Describe the resolved dense-cloud inputs for one evaluation action., DenseCloudEvaluator, Load or compute dense-cloud evaluation over normalized run artifacts.      The p, Load a persisted dense-cloud evaluation when it exists. (+29 more)

### Community 14 - "Community 14"
Cohesion: 0.12
Nodes (37): test_load_recording_summary_reports_live_keyed_and_tracking_surfaces(), test_write_validation_bundle_emits_report_and_projection_images(), test_write_validation_bundle_respects_explicit_keyed_cloud_limit(), _write_synthetic_recording(), _ancestor_entity_paths(), _component_columns(), _keyed_point_cloud_snapshots(), _latest_live_model_snapshot() (+29 more)

### Community 15 - "Community 15"
Cohesion: 0.11
Nodes (34): build_pipeline_snapshot_render_model(), _coerce_int_metric(), _format_latency(), _format_optional_rate(), _format_queue(), _format_resources(), _format_tasks(), _format_throughput() (+26 more)

### Community 16 - "Community 16"
Cohesion: 0.1
Nodes (21): caller_namespace(), configure_logging(), _ConsoleLogFormatter, _ConsoleLogHighlighter, _display_name(), from_callsite(), get_console(), _qualify_namespace() (+13 more)

### Community 17 - "Community 17"
Cohesion: 0.17
Nodes (4): _CappedPacketStream, _CappedStreamingSource, ObservationStream, StreamingSequenceSource

### Community 18 - "Community 18"
Cohesion: 0.17
Nodes (2): Tests for package-root public export surfaces., test_source_materialization_does_not_import_stage_package()

### Community 19 - "Community 19"
Cohesion: 0.36
Nodes (4): test_resolve_issue_moves_record_to_resolved_collection(), test_resolve_refactor_moves_record_to_resolved_collection(), test_resolve_todo_moves_record_to_resolved_collection(), _write_toml()

### Community 21 - "Community 21"
Cohesion: 1.0
Nodes (1): Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays

### Community 22 - "Community 22"
Cohesion: 1.0
Nodes (1): Ray-specific helpers for future stage runtime deployment.  This module intention

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from a 4x4 homogeneous matrix.

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): Return the compact source label used in logs and diagnostics.

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): Disconnect or release the source and any owned runtime resources.

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): Deserialize one IPC payload back into the target validated model type.

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): Return the human-readable label shown in plan previews.

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): Return whether ``exc`` looks like a transient local Ray connection failure.

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): Build one spec from one JSON object.

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (1): Return the net code-line delta.

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (1): Return the path that should own this change in reports.

## Knowledge Gaps
- **265 isolated node(s):** `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`, `Frame preprocessing helpers for ViSTA-SLAM.`, `One RGB frame prepared for upstream ViSTA ingestion.`, `Use the exact upstream ViSTA crop-and-resize helper path.`, `Convert one upstream ViSTA array-like payload into a numpy array.` (+260 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 18`** (12 nodes): `test_package_exports.py`, `Tests for package-root public export surfaces.`, `test_executable_stage_packages_export_canonical_surfaces()`, `test_interfaces_package_exports_only_canonical_pose_surface()`, `test_methods_package_exports_slam_surfaces()`, `test_pipeline_contracts_package_is_not_a_compatibility_hub()`, `test_pipeline_package_exports_only_minimal_public_surface()`, `test_reconstruction_package_exports_runtime_surfaces_without_harness()`, `test_replay_package_exports_only_replay_primitives()`, `test_source_materialization_does_not_import_stage_package()`, `test_sources_package_exports_source_owned_contracts()`, `test_vista_package_is_the_only_canonical_vista_surface()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (2 nodes): `streamlit_app.py`, `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 22`** (2 nodes): `ray.py`, `Ray-specific helpers for future stage runtime deployment.  This module intention`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (1 nodes): `Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (1 nodes): `Build the shared transform DTO from a 4x4 homogeneous matrix.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (1 nodes): `Return the compact source label used in logs and diagnostics.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `Disconnect or release the source and any owned runtime resources.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `Deserialize one IPC payload back into the target validated model type.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `Return the human-readable label shown in plan previews.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `Return whether ``exc`` looks like a transient local Ray connection failure.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `Build one spec from one JSON object.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `Return the net code-line delta.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (1 nodes): `Return the path that should own this change in reports.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Test package helpers and suites for PRML VSLAM.` connect `Community 3` to `Community 0`, `Community 1`, `Community 2`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 10`, `Community 12`, `Community 13`?**
  _High betweenness centrality (0.119) - this node is a cross-community bridge._
- **Why does `StageKey` connect `Community 0` to `Community 2`, `Community 3`, `Community 4`, `Community 6`, `Community 7`, `Community 9`, `Community 12`, `Community 15`?**
  _High betweenness centrality (0.085) - this node is a cross-community bridge._
- **Why does `SequenceManifest` connect `Community 4` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 5`, `Community 6`, `Community 7`, `Community 10`, `Community 11`?**
  _High betweenness centrality (0.074) - this node is a cross-community bridge._
- **Are the 448 inferred relationships involving `StageKey` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`StageKey` has 448 INFERRED edges - model-reasoned connections that need verification._
- **Are the 431 inferred relationships involving `SequenceManifest` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`SequenceManifest` has 431 INFERRED edges - model-reasoned connections that need verification._
- **Are the 331 inferred relationships involving `PreparedBenchmarkInputs` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`PreparedBenchmarkInputs` has 331 INFERRED edges - model-reasoned connections that need verification._
- **Are the 316 inferred relationships involving `DatasetId` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`DatasetId` has 316 INFERRED edges - model-reasoned connections that need verification._