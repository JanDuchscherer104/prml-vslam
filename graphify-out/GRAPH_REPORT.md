# Graph Report - codex-record3d-only  (2026-06-12)

## Corpus Check
- 284 files · ~1,078,155 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4403 nodes · 20688 edges · 34 communities detected
- Extraction: 31% EXTRACTED · 69% INFERRED · 0% AMBIGUOUS · INFERRED: 14231 edges (avg confidence: 0.59)
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
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]

## God Nodes (most connected - your core abstractions)
1. `StageKey` - 449 edges
2. `SequenceManifest` - 379 edges
3. `DatasetId` - 293 edges
4. `PreparedBenchmarkInputs` - 281 edges
5. `ArtifactRef` - 272 edges
6. `MethodId` - 266 edges
7. `PathConfig` - 261 edges
8. `StageRuntimeStatus` - 240 edges
9. `RunConfig` - 198 edges
10. `ReferenceSource` - 192 edges

## Surprising Connections (you probably didn't know these)
- `test_plan_run_defaults_to_live_viewer()` --calls--> `plan_run()`  [INFERRED]
  tests/test_main.py → src/prml_vslam/main.py
- `test_metrics_page_state_preserves_persisted_view_fields()` --calls--> `MetricsPageState`  [INFERRED]
  tests/test_app.py → src/prml_vslam/app/models.py
- `Focused tests for derived ground-plane alignment.` --uses--> `GroundAlignmentMetadata`  [INFERRED]
  tests/test_ground_alignment.py → src/prml_vslam/interfaces/alignment.py
- `test_pointmap_contract_rejects_sparse_point_cloud_shape()` --calls--> `PointMap`  [INFERRED]
  tests/test_geometry.py → src/prml_vslam/interfaces/geometry.py
- `Small runtime sources used by focused pipeline smoke tests.` --uses--> `SequenceManifest`  [INFERRED]
  tests/pipeline_testing_support.py → src/prml_vslam/sources/contracts.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.01
Nodes (535): GroundAlignmentMetadata, Result of one derived ground-plane alignment attempt.      When :attr:`applied`, InputArtifactDiagnostics, Inspection helpers for persisted pipeline run artifact roots., One submitted run attempt found in a persisted event log., Structured inspection result for one persisted pipeline run., Discover method-level run roots under the configured artifact directory., Load typed metadata and path inventory for one persisted run root. (+527 more)

### Community 1 - "Community 1"
Cohesion: 0.01
Nodes (504): AdvioDownloadManager, _ensure_directory_parent(), Return the cache directory used for downloaded scene archives., Return one catalog scene by id., Return local availability status for every catalog scene., Download selected ADVIO scenes and extract complete scene payloads., resolve_calibration_path(), load_advio_frame_timestamps_ns() (+496 more)

### Community 2 - "Community 2"
Cohesion: 0.01
Nodes (312): _coordinator_actor_options(), RayPipelineBackend, BaseConfig, _ConfigFactory, FactoryConfig, from_toml(), _normalize_value(), Shared config and config-as-factory helpers for the repository.  This module own (+304 more)

### Community 3 - "Community 3"
Cohesion: 0.01
Nodes (320): build_advio_page_data(), handle_advio_preview_action(), load_advio_explorer_sample(), _scene_rows(), sync_advio_download_state(), sync_advio_preview_state(), _apply_snapshot_fallbacks(), _candidate_from_root() (+312 more)

### Community 4 - "Community 4"
Cohesion: 0.02
Nodes (220): _build_artifacts(), _ensure_uint8_rgb_from_uimg(), _estimate_camera_intrinsics_from_frame(), _InProcessManager, _InProcessValue, Mast3rSlamBackend, Mast3rSlamSession, Canonical MASt3R-SLAM backend adapter (offline + streaming).  This adapter wraps (+212 more)

### Community 5 - "Community 5"
Cohesion: 0.02
Nodes (250): Controller helpers for the ADVIO Streamlit page., Persist the current ADVIO download-form state., Persist the current explorer selection and load its offline sample., Keep persisted preview state aligned with the runtime snapshot., Apply one preview-form action and return an error message when it fails., AdvioEnvironment, AdvioPeopleLevel, Environment labels committed from the official ADVIO scene table. (+242 more)

### Community 6 - "Community 6"
Cohesion: 0.05
Nodes (214): Trajectory-alignment contracts shared by evaluation and visualization.  Trajecto, Describe how trajectories are aligned before metric computation., State whether an alignment may publish a downstream dense cloud., Persist an explicit trajectory alignment used for diagnostics or metrics., TrajectoryAlignmentArtifact, TrajectoryAlignmentCloudUseStatus, TrajectoryAlignmentMode, AdvioSourceConfig (+206 more)

### Community 7 - "Community 7"
Cohesion: 0.02
Nodes (186): build_advio_comparison_trajectories(), build_crowd_density_figure(), build_local_readiness_figure(), build_scene_attribute_figure(), build_scene_mix_figure(), Plotly figure builders for the ADVIO dataset page., Build a crowd-density composition chart., Build a scene-attribute prevalence chart. (+178 more)

### Community 8 - "Community 8"
Cohesion: 0.03
Nodes (131): BaseConfig, _advio_native_fps(), CloudAlignmentStageConfig, CloudEvaluationStageConfig, CloudMetricId, _collect_unknown_field_warnings(), _compile_run_plan(), config_warnings() (+123 more)

### Community 9 - "Community 9"
Cohesion: 0.02
Nodes (150): GroundPlaneModel, GroundPlaneVisualizationHint, Alignment result DTOs shared outside the alignment package.  These datamodels de, Dominant ground-plane hypothesis expressed in native ``world`` coordinates., Finite plane-patch geometry ready for visualization consumers., CameraIntrinsicsSample, center_crop_resize_intrinsics(), crop_camera_intrinsics() (+142 more)

### Community 10 - "Community 10"
Cohesion: 0.03
Nodes (110): ape_error_colors(), attach_recording_sinks(), augment_viewer_recording_with_ground_plane(), build_default_blueprint(), create_recording_stream(), _decimate_rows(), _entity_token(), evaluation_case_root() (+102 more)

### Community 11 - "Community 11"
Cohesion: 0.04
Nodes (122): build_coverage_matrix(), build_heatmap_data(), build_leaderboard(), build_per_sequence_table(), CoverageCell, CoverageMatrix, HeatmapData, LeaderboardRow (+114 more)

### Community 12 - "Community 12"
Cohesion: 0.04
Nodes (71): advio_basis_metadata(), advio_basis_provenance(), AdvioBasisMetadata, AdvioRawCoordinateBasis, basis_for_pose_source(), _flatten_matrix(), _pose_matrix(), ADVIO coordinate-basis normalization helpers.  ADVIO replay and benchmark surfac (+63 more)

### Community 13 - "Community 13"
Cohesion: 0.04
Nodes (49): _build_runtime(), test_decode_record3d_wifi_depth_maps_hue_to_depth_range(), test_normalize_record3d_device_address_adds_http_scheme(), test_record3d_wifi_answer_payload_matches_official_demo(), test_record3d_wifi_closed_after_connect_logs_runtime_failure(), test_record3d_wifi_closed_before_track_sets_setup_failure_without_logging(), test_record3d_wifi_disconnect_does_not_raise_when_worker_lingers(), test_record3d_wifi_metadata_failure_is_non_fatal() (+41 more)

### Community 14 - "Community 14"
Cohesion: 0.08
Nodes (32): Replay clock used by dataset and video source streams., Select whether replay follows source timing or returns observations immediately., Apply source-timestamp pacing for real-time replay., Reset the clock baseline for a new replay loop or connection., Sleep until the replay timestamp should be emitted., ReplayClock, ReplayMode, ImageSequenceObservationSource (+24 more)

### Community 15 - "Community 15"
Cohesion: 0.06
Nodes (23): IntEnum, build_record3d_frame_details(), _camera_pose_from_binding(), _device_from_binding(), _intrinsics_from_binding(), open_record3d_usb_packet_stream(), Disconnect the current USB device if one is active., Wait for the next shared observation emitted by the USB device. (+15 more)

### Community 16 - "Community 16"
Cohesion: 0.12
Nodes (37): test_load_recording_summary_reports_live_keyed_and_tracking_surfaces(), test_write_validation_bundle_emits_report_and_projection_images(), test_write_validation_bundle_respects_explicit_keyed_cloud_limit(), _write_synthetic_recording(), _ancestor_entity_paths(), _component_columns(), _keyed_point_cloud_snapshots(), _latest_live_model_snapshot() (+29 more)

### Community 17 - "Community 17"
Cohesion: 0.11
Nodes (34): build_pipeline_snapshot_render_model(), _coerce_int_metric(), _format_latency(), _format_optional_rate(), _format_queue(), _format_resources(), _format_tasks(), _format_throughput() (+26 more)

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
Nodes (1): Connect to the source and prepare subsequent blocking observation reads.

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): Disconnect or release the source and any owned runtime resources.

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): Return the short user-facing dataset label.

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): Deserialize one IPC payload back into the target validated model type.

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): Return the human-readable label shown in plan previews.

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (1): Return whether ``exc`` looks like a transient local Ray connection failure.

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (1): Build one spec from one JSON object.

### Community 33 - "Community 33"
Cohesion: 1.0
Nodes (1): Return the net code-line delta.

### Community 34 - "Community 34"
Cohesion: 1.0
Nodes (1): Return the path that should own this change in reports.

## Knowledge Gaps
- **257 isolated node(s):** `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`, `Frame preprocessing helpers for ViSTA-SLAM.`, `One RGB frame prepared for upstream ViSTA ingestion.`, `Use the exact upstream ViSTA crop-and-resize helper path.`, `Convert one upstream ViSTA array-like payload into a numpy array.` (+252 more)
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
- **Thin community `Community 26`** (1 nodes): `Connect to the source and prepare subsequent blocking observation reads.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `Disconnect or release the source and any owned runtime resources.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `Return the short user-facing dataset label.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `Deserialize one IPC payload back into the target validated model type.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `Return the human-readable label shown in plan previews.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `Return whether ``exc`` looks like a transient local Ray connection failure.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (1 nodes): `Build one spec from one JSON object.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 33`** (1 nodes): `Return the net code-line delta.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 34`** (1 nodes): `Return the path that should own this change in reports.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Test package helpers and suites for PRML VSLAM.` connect `Community 8` to `Community 0`, `Community 1`, `Community 2`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 9`, `Community 12`, `Community 14`, `Community 15`?**
  _High betweenness centrality (0.133) - this node is a cross-community bridge._
- **Why does `StageKey` connect `Community 0` to `Community 1`, `Community 2`, `Community 4`, `Community 5`, `Community 6`, `Community 8`, `Community 10`, `Community 17`?**
  _High betweenness centrality (0.068) - this node is a cross-community bridge._
- **Why does `SequenceManifest` connect `Community 1` to `Community 0`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 8`, `Community 11`?**
  _High betweenness centrality (0.063) - this node is a cross-community bridge._
- **Are the 446 inferred relationships involving `StageKey` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`StageKey` has 446 INFERRED edges - model-reasoned connections that need verification._
- **Are the 376 inferred relationships involving `SequenceManifest` (e.g. with `OfflineSlamBackend` and `StreamingSlamBackend`) actually correct?**
  _`SequenceManifest` has 376 INFERRED edges - model-reasoned connections that need verification._
- **Are the 290 inferred relationships involving `DatasetId` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`DatasetId` has 290 INFERRED edges - model-reasoned connections that need verification._
- **Are the 276 inferred relationships involving `PreparedBenchmarkInputs` (e.g. with `OfflineSlamBackend` and `StreamingSlamBackend`) actually correct?**
  _`PreparedBenchmarkInputs` has 276 INFERRED edges - model-reasoned connections that need verification._