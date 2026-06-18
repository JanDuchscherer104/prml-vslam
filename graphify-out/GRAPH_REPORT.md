# Graph Report - sweeper-pr88-integration  (2026-06-19)

## Corpus Check
- 292 files · ~1,096,189 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4736 nodes · 22960 edges · 32 communities detected
- Extraction: 30% EXTRACTED · 70% INFERRED · 0% AMBIGUOUS · INFERRED: 15973 edges (avg confidence: 0.59)
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
- [[_COMMUNITY_Community 20|Community 20]]
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

## God Nodes (most connected - your core abstractions)
1. `StageKey` - 451 edges
2. `SequenceManifest` - 434 edges
3. `PreparedBenchmarkInputs` - 336 edges
4. `DatasetId` - 319 edges
5. `PathConfig` - 290 edges
6. `ArtifactRef` - 281 edges
7. `MethodId` - 277 edges
8. `ReferenceSource` - 247 edges
9. `RunConfig` - 244 edges
10. `StageRuntimeStatus` - 238 edges

## Surprising Connections (you probably didn't know these)
- `MetricsPageState` --calls--> `test_metrics_page_state_preserves_persisted_view_fields()`  [INFERRED]
  src/prml_vslam/app/models.py → tests/test_app.py
- `GroundAlignmentMetadata` --uses--> `Focused tests for derived ground-plane alignment.`  [INFERRED]
  src/prml_vslam/interfaces/alignment.py → tests/test_ground_alignment.py
- `SequenceManifest` --uses--> `Small runtime sources used by focused pipeline smoke tests.`  [INFERRED]
  src/prml_vslam/sources/contracts.py → tests/pipeline_testing_support.py
- `SequenceManifest` --uses--> `Minimal offline source for pipeline smoke tests.`  [INFERRED]
  src/prml_vslam/sources/contracts.py → tests/pipeline_testing_support.py
- `SequenceManifest` --uses--> `Finite in-memory packet stream for streaming smoke tests.`  [INFERRED]
  src/prml_vslam/sources/contracts.py → tests/pipeline_testing_support.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.01
Nodes (490): GroundAlignmentMetadata, Result of one derived ground-plane alignment attempt.      When :attr:`applied`, InputArtifactDiagnostics, Inspection helpers for persisted pipeline run artifact roots., One submitted run attempt found in a persisted event log., Structured inspection result for one persisted pipeline run., Discover method-level run roots under the configured artifact directory., Load typed metadata and path inventory for one persisted run root. (+482 more)

### Community 1 - "Community 1"
Cohesion: 0.01
Nodes (461): Return the cache directory used for downloaded scene archives., Return one catalog scene by id., Return local availability status for every catalog scene., Download selected ADVIO scenes and extract complete scene payloads., advio_basis_metadata(), advio_basis_provenance(), AdvioBasisMetadata, AdvioRawCoordinateBasis (+453 more)

### Community 2 - "Community 2"
Cohesion: 0.01
Nodes (302): _coordinator_actor_options(), RayPipelineBackend, BaseConfig, _ConfigFactory, from_toml(), _normalize_value(), Shared config and config-as-factory helpers for the repository.  This module own, Render the config as a Rich tree for quick human inspection. (+294 more)

### Community 3 - "Community 3"
Cohesion: 0.03
Nodes (290): _build_artifacts(), _DensePredictionArtifacts, _ensure_uint8_rgb_from_uimg(), _estimate_camera_intrinsics_from_frame(), _expect_lingbot_config(), _InProcessManager, _InProcessValue, LingbotMapSlamBackend (+282 more)

### Community 4 - "Community 4"
Cohesion: 0.02
Nodes (255): build_advio_page_data(), handle_advio_preview_action(), _scene_rows(), sync_advio_download_state(), sync_advio_preview_state(), _apply_snapshot_fallbacks(), _candidate_from_root(), _canonical_path_rows() (+247 more)

### Community 5 - "Community 5"
Cohesion: 0.03
Nodes (246): Trajectory-alignment contracts shared by evaluation and visualization.  Trajecto, Describe how trajectories are aligned before metric computation., State whether an alignment may publish a downstream dense cloud., Persist an explicit trajectory alignment used for diagnostics or metrics., TrajectoryAlignmentArtifact, TrajectoryAlignmentCloudUseStatus, TrajectoryAlignmentMode, CloudAlignmentArtifact (+238 more)

### Community 6 - "Community 6"
Cohesion: 0.02
Nodes (232): Controller helpers for the ADVIO Streamlit page., Persist the current ADVIO download-form state., Keep persisted preview state aligned with the runtime snapshot., Apply one preview-form action and return an error message when it fails., Normalize and validate explicit scene selections., Return the canonical ADVIO folder name used on disk., Reject blank dataset roots before path resolution happens downstream., Return the expected sequence type for the config. (+224 more)

### Community 7 - "Community 7"
Cohesion: 0.04
Nodes (201): BaseConfig, BenchmarkInputSource, AdvioSourceConfig, CloudAlignmentStageConfig, CloudEvaluationStageConfig, CloudMetricId, _compile_run_plan(), DenseCloudSelectionConfig (+193 more)

### Community 8 - "Community 8"
Cohesion: 0.02
Nodes (172): AdvioDownloadManager, _ensure_directory_parent(), arcore_ready(), arkit_ready(), _complete_scene_ready(), load_advio_catalog(), offline_ready(), _RelativePathSpec (+164 more)

### Community 9 - "Community 9"
Cohesion: 0.02
Nodes (178): build_advio_comparison_trajectories(), build_crowd_density_figure(), build_local_readiness_figure(), build_scene_attribute_figure(), build_scene_mix_figure(), Plotly figure builders for the ADVIO dataset page., Build a crowd-density composition chart., Build a scene-attribute prevalence chart. (+170 more)

### Community 10 - "Community 10"
Cohesion: 0.03
Nodes (157): ape_error_colors(), attach_recording_sinks(), augment_viewer_recording_with_ground_plane(), build_default_blueprint(), create_recording_stream(), _decimate_rows(), _entity_token(), evaluation_case_root() (+149 more)

### Community 11 - "Community 11"
Cohesion: 0.02
Nodes (118): _is_cuda_oom(), IntEnum, record3d_devices(), iter_sequence_manifest_observations(), _load_manifest_rgb_inputs(), _load_rgb(), _load_rgb_input(), _load_source_frame_indices() (+110 more)

### Community 12 - "Community 12"
Cohesion: 0.03
Nodes (107): _adapt_checkpoint_state_dict(), _as_numpy(), _build_lingbot_artifacts(), _cast_aggregator_for_inference(), _decode_pose_predictions(), _extract_checkpoint_state_dict(), _extract_dense_prediction_artifacts(), _flatten_depth_points() (+99 more)

### Community 13 - "Community 13"
Cohesion: 0.02
Nodes (120): ArxivSourceSpec, download_file(), fetch_pdf(), fetch_tex_source(), from_json(), load_manifest(), main(), normalize_member_path() (+112 more)

### Community 14 - "Community 14"
Cohesion: 0.03
Nodes (83): Replay clock used by dataset and video source streams., Select whether replay follows source timing or returns observations immediately., Apply source-timestamp pacing for real-time replay., Reset the clock baseline for a new replay loop or connection., Sleep until the replay timestamp should be emitted., ReplayClock, ReplayMode, Enum (+75 more)

### Community 15 - "Community 15"
Cohesion: 0.04
Nodes (94): _advio_pose_source(), _record_from_entry(), _benchmark_artifact_paths(), _cleanup_temporary_entry_root(), _compatible_entry_identity(), _compatible_entry_profile(), _copy_once(), _copy_optional_path() (+86 more)

### Community 16 - "Community 16"
Cohesion: 0.12
Nodes (32): GroundPlaneModel, GroundPlaneVisualizationHint, Alignment result DTOs shared outside the alignment package.  These datamodels de, Dominant ground-plane hypothesis expressed in native ``world`` coordinates., Finite plane-patch geometry ready for visualization consumers., GroundAlignmentConfig, Inputs required to derive ground-alignment metadata from SLAM outputs., _build_viewer_transform() (+24 more)

### Community 17 - "Community 17"
Cohesion: 0.1
Nodes (36): build_pipeline_snapshot_render_model(), _coerce_int_metric(), _format_latency(), _format_optional_rate(), _format_queue(), _format_resources(), _format_tasks(), _format_throughput() (+28 more)

### Community 18 - "Community 18"
Cohesion: 0.18
Nodes (2): finish_streaming(), start_streaming()

### Community 19 - "Community 19"
Cohesion: 0.17
Nodes (2): Tests for package-root public export surfaces., test_source_materialization_does_not_import_stage_package()

### Community 20 - "Community 20"
Cohesion: 1.0
Nodes (1): Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays

### Community 21 - "Community 21"
Cohesion: 1.0
Nodes (1): Ray-specific helpers for future stage runtime deployment.  This module intention

### Community 22 - "Community 22"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from a 4x4 homogeneous matrix.

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (1): Return the compact source label used in logs and diagnostics.

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): Disconnect or release the source and any owned runtime resources.

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): Deserialize one IPC payload back into the target validated model type.

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): Return the human-readable label shown in plan previews.

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): Return whether ``exc`` looks like a transient local Ray connection failure.

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): Build one spec from one JSON object.

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): Return the net code-line delta.

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (1): Return the path that should own this change in reports.

## Knowledge Gaps
- **265 isolated node(s):** `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`, `Frame preprocessing helpers for ViSTA-SLAM.`, `One RGB frame prepared for upstream ViSTA ingestion.`, `Use the exact upstream ViSTA crop-and-resize helper path.`, `Convert one upstream ViSTA array-like payload into a numpy array.` (+260 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 18`** (12 nodes): `protocols.py`, `protocols.py`, `drain_runtime_updates()`, `drain_streaming_updates()`, `finish_streaming()`, `run_observations()`, `run_offline()`, `start_streaming()`, `status()`, `step_streaming()`, `stop()`, `submit_stream_item()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 19`** (12 nodes): `test_package_exports.py`, `Tests for package-root public export surfaces.`, `test_executable_stage_packages_export_canonical_surfaces()`, `test_interfaces_package_exports_only_canonical_pose_surface()`, `test_methods_package_exports_slam_surfaces()`, `test_pipeline_contracts_package_is_not_a_compatibility_hub()`, `test_pipeline_package_exports_only_minimal_public_surface()`, `test_reconstruction_package_exports_runtime_surfaces_without_harness()`, `test_replay_package_exports_only_replay_primitives()`, `test_source_materialization_does_not_import_stage_package()`, `test_sources_package_exports_source_owned_contracts()`, `test_vista_package_is_the_only_canonical_vista_surface()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 20`** (2 nodes): `streamlit_app.py`, `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (2 nodes): `ray.py`, `Ray-specific helpers for future stage runtime deployment.  This module intention`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 22`** (1 nodes): `Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (1 nodes): `Build the shared transform DTO from a 4x4 homogeneous matrix.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (1 nodes): `Return the compact source label used in logs and diagnostics.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (1 nodes): `Disconnect or release the source and any owned runtime resources.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `Deserialize one IPC payload back into the target validated model type.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `Return the human-readable label shown in plan previews.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `Return whether ``exc`` looks like a transient local Ray connection failure.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `Build one spec from one JSON object.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `Return the net code-line delta.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `Return the path that should own this change in reports.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Test package helpers and suites for PRML VSLAM.` connect `Community 1` to `Community 0`, `Community 2`, `Community 3`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 9`, `Community 11`, `Community 12`, `Community 14`, `Community 16`?**
  _High betweenness centrality (0.130) - this node is a cross-community bridge._
- **Why does `SequenceManifest` connect `Community 3` to `Community 0`, `Community 1`, `Community 2`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 11`, `Community 12`, `Community 15`?**
  _High betweenness centrality (0.073) - this node is a cross-community bridge._
- **Why does `StageKey` connect `Community 0` to `Community 1`, `Community 2`, `Community 3`, `Community 5`, `Community 6`, `Community 7`, `Community 10`, `Community 14`, `Community 17`?**
  _High betweenness centrality (0.063) - this node is a cross-community bridge._
- **Are the 448 inferred relationships involving `StageKey` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`StageKey` has 448 INFERRED edges - model-reasoned connections that need verification._
- **Are the 431 inferred relationships involving `SequenceManifest` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`SequenceManifest` has 431 INFERRED edges - model-reasoned connections that need verification._
- **Are the 331 inferred relationships involving `PreparedBenchmarkInputs` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`PreparedBenchmarkInputs` has 331 INFERRED edges - model-reasoned connections that need verification._
- **Are the 316 inferred relationships involving `DatasetId` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`DatasetId` has 316 INFERRED edges - model-reasoned connections that need verification._