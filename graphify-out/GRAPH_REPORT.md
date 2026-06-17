# Graph Report - pr103-surgical-fixes  (2026-06-17)

## Corpus Check
- 277 files · ~1,072,932 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4226 nodes · 19249 edges · 35 communities detected
- Extraction: 32% EXTRACTED · 68% INFERRED · 0% AMBIGUOUS · INFERRED: 13090 edges (avg confidence: 0.59)
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
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]

## God Nodes (most connected - your core abstractions)
1. `StageKey` - 435 edges
2. `SequenceManifest` - 355 edges
3. `ArtifactRef` - 284 edges
4. `MethodId` - 265 edges
5. `PreparedBenchmarkInputs` - 254 edges
6. `PathConfig` - 235 edges
7. `StageRuntimeStatus` - 229 edges
8. `ReferenceSource` - 195 edges
9. `RunConfig` - 193 edges
10. `FrameTransform` - 183 edges

## Surprising Connections (you probably didn't know these)
- `Small runtime sources used by focused pipeline smoke tests.` --uses--> `SequenceManifest`  [INFERRED]
  tests/pipeline_testing_support.py → src/prml_vslam/sources/contracts.py
- `Minimal offline source for pipeline smoke tests.` --uses--> `SequenceManifest`  [INFERRED]
  tests/pipeline_testing_support.py → src/prml_vslam/sources/contracts.py
- `Finite in-memory packet stream for streaming smoke tests.` --uses--> `SequenceManifest`  [INFERRED]
  tests/pipeline_testing_support.py → src/prml_vslam/sources/contracts.py
- `Minimal streaming-capable source for pipeline smoke tests.` --uses--> `SequenceManifest`  [INFERRED]
  tests/pipeline_testing_support.py → src/prml_vslam/sources/contracts.py
- `test_visualization_config_rejects_invalid_decimation_values()` --calls--> `VisualizationConfig`  [INFERRED]
  tests/test_visualization.py → src/prml_vslam/visualization/contracts.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.02
Nodes (441): InputArtifactDiagnostics, Inspection helpers for persisted pipeline run artifact roots., One submitted run attempt found in a persisted event log., Structured inspection result for one persisted pipeline run., Discover method-level run roots under the configured artifact directory., Load typed metadata and path inventory for one persisted run root., One selectable persisted method-level run artifact root., Shallow diagnostics for materialized offline input artifacts. (+433 more)

### Community 1 - "Community 1"
Cohesion: 0.01
Nodes (313): AdvioDownloadManager, _ensure_directory_parent(), Return the cache directory used for downloaded scene archives., Return one catalog scene by id., Return local availability status for every catalog scene., Download selected ADVIO scenes and extract the requested modalities., advio_basis_metadata(), advio_basis_provenance() (+305 more)

### Community 2 - "Community 2"
Cohesion: 0.02
Nodes (307): _adapt_checkpoint_state_dict(), _as_numpy(), _build_artifacts(), _build_lingbot_artifacts(), _cast_aggregator_for_inference(), _decode_pose_predictions(), _DensePredictionArtifacts, _ensure_uint8_rgb_from_uimg() (+299 more)

### Community 3 - "Community 3"
Cohesion: 0.02
Nodes (330): resolve(), _coordinator_actor_options(), RayPipelineBackend, _enter_page(), AdvioSourceConfig, build_run_config(), from_toml(), _load_toml_payload() (+322 more)

### Community 4 - "Community 4"
Cohesion: 0.01
Nodes (283): build_advio_comparison_trajectories(), build_crowd_density_figure(), build_local_readiness_figure(), build_scene_attribute_figure(), build_scene_mix_figure(), build_advio_page_data(), handle_advio_preview_action(), load_advio_explorer_sample() (+275 more)

### Community 5 - "Community 5"
Cohesion: 0.02
Nodes (254): _trajectory_from_pose_matrices(), GroundAlignmentMetadata, GroundPlaneModel, GroundPlaneVisualizationHint, Alignment result DTOs shared outside the alignment package.  These datamodels de, Dominant ground-plane hypothesis expressed in native ``world`` coordinates., Finite plane-patch geometry ready for visualization consumers., Result of one derived ground-plane alignment attempt.      When :attr:`applied` (+246 more)

### Community 6 - "Community 6"
Cohesion: 0.03
Nodes (237): Trajectory-alignment contracts shared by evaluation and visualization.  Trajecto, Describe how trajectories are aligned before metric computation., State whether an alignment may publish a downstream dense cloud., Persist an explicit trajectory alignment used for diagnostics or metrics., TrajectoryAlignmentArtifact, TrajectoryAlignmentCloudUseStatus, TrajectoryAlignmentMode, CloudAlignmentArtifact (+229 more)

### Community 7 - "Community 7"
Cohesion: 0.02
Nodes (195): Controller helpers for the ADVIO Streamlit page., Persist the current ADVIO download-form state., Persist the current explorer selection and load its offline sample., Keep persisted preview state aligned with the runtime snapshot., Apply one preview-form action and return an error message when it fails., BaseData, build_context(), _build_pages() (+187 more)

### Community 8 - "Community 8"
Cohesion: 0.03
Nodes (186): BaseConfig, AppContext, _advio_native_fps(), build_backend_spec(), CloudAlignmentStageConfig, CloudEvaluationStageConfig, CloudMetricId, _collect_unknown_field_warnings() (+178 more)

### Community 9 - "Community 9"
Cohesion: 0.02
Nodes (156): BaseConfig, _ConfigFactory, FactoryConfig, from_toml(), _normalize_value(), Shared config and config-as-factory helpers for the repository.  This module own, Render the config as a Rich tree for quick human inspection., Mixin for configs that construct one runtime owner or adapter.      This pattern (+148 more)

### Community 10 - "Community 10"
Cohesion: 0.02
Nodes (120): ArxivSourceSpec, download_file(), fetch_pdf(), fetch_tex_source(), from_json(), load_manifest(), main(), normalize_member_path() (+112 more)

### Community 11 - "Community 11"
Cohesion: 0.03
Nodes (57): IntEnum, _camera_pose_from_binding(), _device_from_binding(), _import_record3d_module(), _intrinsics_from_binding(), list_record3d_usb_devices(), open_record3d_usb_packet_stream(), Disconnect the current USB device if one is active. (+49 more)

### Community 12 - "Community 12"
Cohesion: 0.06
Nodes (72): _coerce_view_graph(), _coerce_view_graph_node(), load_vista_confidences(), load_vista_estimated_intrinsics_series(), load_vista_intrinsics_matrices(), load_vista_native_trajectory(), load_vista_vector(), load_vista_view_graph() (+64 more)

### Community 13 - "Community 13"
Cohesion: 0.07
Nodes (34): Replay clock used by dataset and video source streams., Select whether replay follows source timing or returns observations immediately., Apply source-timestamp pacing for real-time replay., Reset the clock baseline for a new replay loop or connection., Sleep until the replay timestamp should be emitted., ReplayClock, ReplayMode, ImageSequenceObservationSource (+26 more)

### Community 14 - "Community 14"
Cohesion: 0.09
Nodes (49): iter_sequence_manifest_observations(), _load_manifest_rgb_inputs(), _load_rgb(), load_sequence_manifest_rgb_inputs(), _load_timestamps_ns(), _manifest_provenance(), Source-owned readers for normalized offline observations., Yield RGB observations from a normalized source sequence manifest. (+41 more)

### Community 15 - "Community 15"
Cohesion: 0.12
Nodes (37): test_load_recording_summary_reports_live_keyed_and_tracking_surfaces(), test_write_validation_bundle_emits_report_and_projection_images(), test_write_validation_bundle_respects_explicit_keyed_cloud_limit(), _write_synthetic_recording(), _ancestor_entity_paths(), _component_columns(), _keyed_point_cloud_snapshots(), _latest_live_model_snapshot() (+29 more)

### Community 16 - "Community 16"
Cohesion: 0.11
Nodes (33): build_pipeline_snapshot_render_model(), _coerce_int_metric(), _format_latency(), _format_optional_rate(), _format_queue(), _format_resources(), _format_tasks(), _format_throughput() (+25 more)

### Community 17 - "Community 17"
Cohesion: 0.13
Nodes (28): _add_point_cloud_trace(), _add_trajectory_trace(), _apply_comparison_layout(), _build_figure(), build_reference_reconstruction_figure(), build_slam_reference_comparison_figure(), _combined_bounds(), _decimate_mesh() (+20 more)

### Community 18 - "Community 18"
Cohesion: 0.21
Nodes (18): _apply_snapshot_fallbacks(), _candidate_from_root(), _canonical_path_rows(), _derive_slam_artifacts(), discover_run_artifact_roots(), _file_inventory(), _format_size(), inspect_run_artifacts() (+10 more)

### Community 19 - "Community 19"
Cohesion: 0.17
Nodes (2): Tests for package-root public export surfaces., test_source_materialization_does_not_import_stage_package()

### Community 20 - "Community 20"
Cohesion: 0.36
Nodes (4): test_resolve_issue_moves_record_to_resolved_collection(), test_resolve_refactor_moves_record_to_resolved_collection(), test_resolve_todo_moves_record_to_resolved_collection(), _write_toml()

### Community 22 - "Community 22"
Cohesion: 1.0
Nodes (1): Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (1): Ray-specific helpers for future stage runtime deployment.  This module intention

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from a 4x4 homogeneous matrix.

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): Return the compact source label used in logs and diagnostics.

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): Connect to the source and prepare subsequent blocking observation reads.

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): Disconnect or release the source and any owned runtime resources.

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): Return the short user-facing dataset label.

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): Deserialize one IPC payload back into the target validated model type.

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (1): Return the human-readable label shown in plan previews.

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (1): Return whether ``exc`` looks like a transient local Ray connection failure.

### Community 33 - "Community 33"
Cohesion: 1.0
Nodes (1): Build one spec from one JSON object.

### Community 34 - "Community 34"
Cohesion: 1.0
Nodes (1): Return the net code-line delta.

### Community 35 - "Community 35"
Cohesion: 1.0
Nodes (1): Return the path that should own this change in reports.

## Knowledge Gaps
- **255 isolated node(s):** `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`, `Frame preprocessing helpers for ViSTA-SLAM.`, `One RGB frame prepared for upstream ViSTA ingestion.`, `Use the exact upstream ViSTA crop-and-resize helper path.`, `Convert one upstream ViSTA array-like payload into a numpy array.` (+250 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 19`** (12 nodes): `test_package_exports.py`, `Tests for package-root public export surfaces.`, `test_executable_stage_packages_export_canonical_surfaces()`, `test_interfaces_package_exports_only_canonical_pose_surface()`, `test_methods_package_exports_slam_surfaces()`, `test_pipeline_contracts_package_is_not_a_compatibility_hub()`, `test_pipeline_package_exports_only_minimal_public_surface()`, `test_reconstruction_package_exports_runtime_surfaces_without_harness()`, `test_replay_package_exports_only_replay_primitives()`, `test_source_materialization_does_not_import_stage_package()`, `test_sources_package_exports_source_owned_contracts()`, `test_vista_package_is_the_only_canonical_vista_surface()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 22`** (2 nodes): `streamlit_app.py`, `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (2 nodes): `ray.py`, `Ray-specific helpers for future stage runtime deployment.  This module intention`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (1 nodes): `Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (1 nodes): `Build the shared transform DTO from a 4x4 homogeneous matrix.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `Return the compact source label used in logs and diagnostics.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `Connect to the source and prepare subsequent blocking observation reads.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `Disconnect or release the source and any owned runtime resources.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `Return the short user-facing dataset label.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `Deserialize one IPC payload back into the target validated model type.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `Return the human-readable label shown in plan previews.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (1 nodes): `Return whether ``exc`` looks like a transient local Ray connection failure.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 33`** (1 nodes): `Build one spec from one JSON object.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 34`** (1 nodes): `Return the net code-line delta.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (1 nodes): `Return the path that should own this change in reports.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Test package helpers and suites for PRML VSLAM.` connect `Community 1` to `Community 0`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 9`, `Community 11`, `Community 12`, `Community 13`, `Community 17`?**
  _High betweenness centrality (0.143) - this node is a cross-community bridge._
- **Why does `StageKey` connect `Community 0` to `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 9`, `Community 14`?**
  _High betweenness centrality (0.088) - this node is a cross-community bridge._
- **Why does `SequenceManifest` connect `Community 2` to `Community 0`, `Community 1`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 9`, `Community 11`, `Community 14`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **Are the 432 inferred relationships involving `StageKey` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`StageKey` has 432 INFERRED edges - model-reasoned connections that need verification._
- **Are the 352 inferred relationships involving `SequenceManifest` (e.g. with `OfflineSlamBackend` and `OfflineSequenceSlamBackend`) actually correct?**
  _`SequenceManifest` has 352 INFERRED edges - model-reasoned connections that need verification._
- **Are the 280 inferred relationships involving `ArtifactRef` (e.g. with `SlamUpdate` and `SlamArtifacts`) actually correct?**
  _`ArtifactRef` has 280 INFERRED edges - model-reasoned connections that need verification._
- **Are the 262 inferred relationships involving `MethodId` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`MethodId` has 262 INFERRED edges - model-reasoned connections that need verification._