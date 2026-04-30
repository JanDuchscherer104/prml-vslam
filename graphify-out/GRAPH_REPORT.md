# Graph Report - prml-vslam-mast3r-runtime-cleanup  (2026-04-30)

## Corpus Check
- 259 files · ~603,578 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 3893 nodes · 17841 edges · 40 communities detected
- Extraction: 31% EXTRACTED · 69% INFERRED · 0% AMBIGUOUS · INFERRED: 12374 edges (avg confidence: 0.59)
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
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]

## God Nodes (most connected - your core abstractions)
1. `StageKey` - 441 edges
2. `SequenceManifest` - 299 edges
3. `MethodId` - 270 edges
4. `PreparedBenchmarkInputs` - 244 edges
5. `FrameTransform` - 222 edges
6. `StageRuntimeStatus` - 210 edges
7. `ArtifactRef` - 206 edges
8. `ReferenceSource` - 200 edges
9. `PathConfig` - 185 edges
10. `RunConfig` - 185 edges

## Surprising Connections (you probably didn't know these)
- `test_open3d_tsdf_backend_config_defaults_to_expected_method()` --calls--> `Open3dTsdfBackendConfig`  [INFERRED]
  tests/test_reconstruction.py → src/prml_vslam/reconstruction/config.py
- `Tests for the minimal reconstruction config and Open3D backend.` --uses--> `OfflineReconstructionBackend`  [INFERRED]
  tests/test_reconstruction.py → src/prml_vslam/reconstruction/protocols.py
- `test_path_config_is_immutable_after_construction()` --calls--> `PathConfig`  [INFERRED]
  tests/test_path_config.py → src/prml_vslam/utils/path_config.py
- `test_source_materialization_does_not_import_stage_package()` --calls--> `path()`  [INFERRED]
  tests/test_package_exports.py → src/prml_vslam/pipeline/sinks/jsonl.py
- `test_plan_run_defaults_to_live_viewer()` --calls--> `plan_run()`  [INFERRED]
  tests/test_main.py → src/prml_vslam/main.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.02
Nodes (350): GroundAlignmentMetadata, Result of one derived ground-plane alignment attempt.      When :attr:`applied`, InputArtifactDiagnostics, Inspection helpers for persisted pipeline run artifact roots., One submitted run attempt found in a persisted event log., Structured inspection result for one persisted pipeline run., Discover method-level run roots under the configured artifact directory., Load typed metadata and path inventory for one persisted run root. (+342 more)

### Community 1 - "Community 1"
Cohesion: 0.01
Nodes (318): build_advio_page_data(), _scene_rows(), AdvioDownloadManager, _ensure_directory_parent(), Return the cache directory used for downloaded scene archives., Return one catalog scene by id., Return local availability status for every catalog scene., Download selected ADVIO scenes and extract the requested modalities. (+310 more)

### Community 2 - "Community 2"
Cohesion: 0.02
Nodes (377): build_slam_backend_config(), Build a typed backend config from a selected method and overrides., get_events(), get_snapshot(), PipelineBackend, _coordinator_actor_options(), Detach from Ray and stop any backend-owned shared infrastructure., Execute pipeline runs through detached per-run coordinator actors.      The back (+369 more)

### Community 3 - "Community 3"
Cohesion: 0.01
Nodes (361): build_advio_comparison_trajectories(), build_crowd_density_figure(), build_local_readiness_figure(), build_scene_attribute_figure(), build_scene_mix_figure(), handle_advio_preview_action(), load_advio_explorer_sample(), Controller helpers for the ADVIO Streamlit page. (+353 more)

### Community 4 - "Community 4"
Cohesion: 0.02
Nodes (326): _build_artifacts(), _InProcessManager, _InProcessValue, _load_upstream_main_module(), Mast3rSlamBackend, _Mast3rSlamSession, _normalize_preview_rgb(), Canonical ViSTA-SLAM backend adapter (offline + streaming). (+318 more)

### Community 5 - "Community 5"
Cohesion: 0.01
Nodes (280): local_modalities(), _modality_present(), _require_path(), resolve_calibration_path(), resolve_existing_sequence_dir(), resolve_ground_truth_csv(), resolve_optional_arkit_csv(), resolve_optional_fixpoints_csv() (+272 more)

### Community 6 - "Community 6"
Cohesion: 0.02
Nodes (290): _coerce_view_graph(), _coerce_view_graph_node(), load_vista_confidences(), load_vista_estimated_intrinsics_series(), load_vista_intrinsics_matrices(), load_vista_native_trajectory(), load_vista_vector(), load_vista_view_graph() (+282 more)

### Community 7 - "Community 7"
Cohesion: 0.02
Nodes (178): transform_trajectory_with_alignment(), artifact_ref(), _frame_transform_from_vista_pose(), Build one stable artifact reference for a materialized path., Normalize one upstream ViSTA pose matrix into the canonical repo transform DTO., from_matrix(), Return the canonical 3x3 pinhole matrix for downstream math., Transform camera-frame XYZ points into world coordinates. (+170 more)

### Community 8 - "Community 8"
Cohesion: 0.03
Nodes (139): advio_basis_metadata(), advio_basis_provenance(), AdvioBasisMetadata, AdvioRawCoordinateBasis, basis_for_pose_source(), _flatten_matrix(), _pose_matrix(), ADVIO coordinate-basis normalization helpers.  ADVIO stores Apple-family traject (+131 more)

### Community 9 - "Community 9"
Cohesion: 0.03
Nodes (93): analyze_file(), analyze_source(), code_lines_for_source(), collect_dirty_diff_stats(), count_code_line_delta(), count_grouped_stats(), count_module_stats(), count_source_code_delta() (+85 more)

### Community 10 - "Community 10"
Cohesion: 0.05
Nodes (48): _build_runtime(), test_decode_record3d_wifi_depth_maps_hue_to_depth_range(), test_normalize_record3d_device_address_adds_http_scheme(), test_record3d_wifi_answer_payload_matches_official_demo(), test_record3d_wifi_closed_after_connect_logs_runtime_failure(), test_record3d_wifi_closed_before_track_sets_setup_failure_without_logging(), test_record3d_wifi_metadata_failure_is_non_fatal(), test_record3d_wifi_metadata_parses_row_major_intrinsics_and_original_size() (+40 more)

### Community 11 - "Community 11"
Cohesion: 0.07
Nodes (33): Replay clock used by dataset and video source streams., Select whether replay follows source timing or returns observations immediately., Apply source-timestamp pacing for real-time replay., Reset the clock baseline for a new replay loop or connection., Sleep until the replay timestamp should be emitted., ReplayClock, ReplayMode, ImageSequenceObservationSource (+25 more)

### Community 12 - "Community 12"
Cohesion: 0.13
Nodes (30): GroundPlaneModel, GroundPlaneVisualizationHint, Alignment result DTOs shared outside the alignment package.  These datamodels de, Dominant ground-plane hypothesis expressed in native ``world`` coordinates., Finite plane-patch geometry ready for visualization consumers., GroundAlignmentConfig, _camera_down_alignment(), GroundAlignmentService (+22 more)

### Community 13 - "Community 13"
Cohesion: 0.11
Nodes (35): build_pipeline_snapshot_render_model(), _coerce_int_metric(), _compute_evo_preview(), _format_latency(), _format_optional_rate(), _format_queue(), _format_resources(), _format_tasks() (+27 more)

### Community 14 - "Community 14"
Cohesion: 0.09
Nodes (24): DataOnlyConfig, InvalidTargetConfig, NestedPayload, PlainPayload, Tests for the shared Pydantic base-model split., Runtime object used to verify default setup behavior., Config whose runtime target is constructed via ``target_type``., Config without a runtime target. (+16 more)

### Community 15 - "Community 15"
Cohesion: 0.15
Nodes (18): Return the user-facing reconstruction label., Configure the minimal Open3D TSDF reconstruction backend.      The repo targets, Return the concrete reconstruction backend type., Instantiate the Open3D TSDF backend while ignoring unrelated kwargs., Describe normalized durable outputs from one reconstruction run.      The minima, ReconstructionArtifacts, ReconstructionMethodId, _import_open3d() (+10 more)

### Community 16 - "Community 16"
Cohesion: 0.17
Nodes (2): Tests for package-root public export surfaces., test_source_materialization_does_not_import_stage_package()

### Community 17 - "Community 17"
Cohesion: 0.18
Nodes (2): finish_streaming(), start_streaming()

### Community 18 - "Community 18"
Cohesion: 0.36
Nodes (4): test_resolve_issue_moves_record_to_resolved_collection(), test_resolve_refactor_moves_record_to_resolved_collection(), test_resolve_todo_moves_record_to_resolved_collection(), _write_toml()

### Community 19 - "Community 19"
Cohesion: 0.67
Nodes (1): Regression checks for removed pipeline compatibility surfaces.

### Community 20 - "Community 20"
Cohesion: 1.0
Nodes (1): Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays

### Community 21 - "Community 21"
Cohesion: 1.0
Nodes (1): Ray-specific helpers for future stage runtime deployment.  This module intention

### Community 22 - "Community 22"
Cohesion: 1.0
Nodes (1): Deserialize one IPC payload back into the target validated model type.

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (1): Return the compact source label used in logs and diagnostics.

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (1): Connect to the source and prepare subsequent blocking observation reads.

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): Disconnect or release the source and any owned runtime resources.

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): Return the short user-facing dataset label.

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): Return whether ``exc`` looks like a transient local Ray connection failure.

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): Return the human-readable label shown in plan previews.

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from a 4x4 homogeneous matrix.

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (1): Return the net code-line delta.

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (1): Return the path that should own this change in reports.

### Community 33 - "Community 33"
Cohesion: 1.0
Nodes (1): Build one spec from one JSON object.

### Community 34 - "Community 34"
Cohesion: 1.0
Nodes (1): Single TODO/FIXME marker found in a Python source file.

### Community 35 - "Community 35"
Cohesion: 1.0
Nodes (1): Parse CLI flags for optional marker detail output.

### Community 36 - "Community 36"
Cohesion: 1.0
Nodes (1): Extract TODO/FIXME comment markers from file lines.

### Community 37 - "Community 37"
Cohesion: 1.0
Nodes (1): Count high-level line statistics for Python files under root.

### Community 38 - "Community 38"
Cohesion: 1.0
Nodes (1): Render a detailed Rich table for one marker kind.

### Community 39 - "Community 39"
Cohesion: 1.0
Nodes (1): Print LOC statistics for src/ and tests/.

## Knowledge Gaps
- **291 isolated node(s):** `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`, `Tests for ViSTA-native persisted artifact diagnostics.`, `Tests for offline follow-enabled Rerun artifact generation.`, `Regression checks for removed pipeline compatibility surfaces.`, `Tests for reconstruction artifact Plotly figure builders.` (+286 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 16`** (12 nodes): `Tests for package-root public export surfaces.`, `test_executable_stage_packages_export_canonical_surfaces()`, `test_interfaces_package_exports_only_canonical_pose_surface()`, `test_methods_package_exports_slam_surfaces()`, `test_pipeline_contracts_package_is_not_a_compatibility_hub()`, `test_pipeline_package_exports_only_minimal_public_surface()`, `test_reconstruction_package_exports_runtime_surfaces_without_harness()`, `test_replay_package_exports_only_replay_primitives()`, `test_source_materialization_does_not_import_stage_package()`, `test_sources_package_exports_source_owned_contracts()`, `test_vista_package_is_the_only_canonical_vista_surface()`, `test_package_exports.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 17`** (12 nodes): `drain_runtime_updates()`, `drain_streaming_updates()`, `finish_streaming()`, `run_observations()`, `run_offline()`, `start_streaming()`, `status()`, `step_streaming()`, `stop()`, `submit_stream_item()`, `protocols.py`, `protocols.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 19`** (3 nodes): `Regression checks for removed pipeline compatibility surfaces.`, `test_removed_pipeline_compatibility_names_stay_deleted()`, `test_removed_pipeline_compatibility_surface.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 20`** (2 nodes): `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`, `streamlit_app.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (2 nodes): `Ray-specific helpers for future stage runtime deployment.  This module intention`, `ray.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 22`** (1 nodes): `Deserialize one IPC payload back into the target validated model type.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (1 nodes): `Return the compact source label used in logs and diagnostics.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (1 nodes): `Connect to the source and prepare subsequent blocking observation reads.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (1 nodes): `Disconnect or release the source and any owned runtime resources.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `Return the short user-facing dataset label.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `Return whether ``exc`` looks like a transient local Ray connection failure.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `Return the human-readable label shown in plan previews.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `Build the shared transform DTO from a 4x4 homogeneous matrix.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `Return the net code-line delta.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (1 nodes): `Return the path that should own this change in reports.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 33`** (1 nodes): `Build one spec from one JSON object.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 34`** (1 nodes): `Single TODO/FIXME marker found in a Python source file.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (1 nodes): `Parse CLI flags for optional marker detail output.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 36`** (1 nodes): `Extract TODO/FIXME comment markers from file lines.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 37`** (1 nodes): `Count high-level line statistics for Python files under root.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 38`** (1 nodes): `Render a detailed Rich table for one marker kind.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 39`** (1 nodes): `Print LOC statistics for src/ and tests/.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Test package helpers and suites for PRML VSLAM.` connect `Community 1` to `Community 0`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 8`, `Community 11`, `Community 12`, `Community 15`?**
  _High betweenness centrality (0.104) - this node is a cross-community bridge._
- **Why does `StageKey` connect `Community 0` to `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 13`?**
  _High betweenness centrality (0.087) - this node is a cross-community bridge._
- **Why does `SequenceManifest` connect `Community 4` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 5`, `Community 6`, `Community 8`?**
  _High betweenness centrality (0.054) - this node is a cross-community bridge._
- **Are the 438 inferred relationships involving `StageKey` (e.g. with `Tests for target pipeline config and stage-section planning contracts.` and `Focused app/controller tests for the refactored pipeline surface.`) actually correct?**
  _`StageKey` has 438 INFERRED edges - model-reasoned connections that need verification._
- **Are the 296 inferred relationships involving `SequenceManifest` (e.g. with `Tests for the method wrappers.` and `_ManifestOnlySource`) actually correct?**
  _`SequenceManifest` has 296 INFERRED edges - model-reasoned connections that need verification._
- **Are the 267 inferred relationships involving `MethodId` (e.g. with `Tests for target pipeline config and stage-section planning contracts.` and `Tests for the method wrappers.`) actually correct?**
  _`MethodId` has 267 INFERRED edges - model-reasoned connections that need verification._
- **Are the 238 inferred relationships involving `PreparedBenchmarkInputs` (e.g. with `_ManifestOnlySource` and `_BenchmarkSource`) actually correct?**
  _`PreparedBenchmarkInputs` has 238 INFERRED edges - model-reasoned connections that need verification._