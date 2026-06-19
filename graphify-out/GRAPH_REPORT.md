# Graph Report - sweeper-pr88-integration  (2026-06-19)

## Corpus Check
- 292 files · ~1,097,837 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4872 nodes · 25049 edges · 37 communities detected
- Extraction: 28% EXTRACTED · 72% INFERRED · 0% AMBIGUOUS · INFERRED: 18034 edges (avg confidence: 0.58)
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

## God Nodes (most connected - your core abstractions)
1. `SequenceManifest` - 511 edges
2. `StageKey` - 497 edges
3. `PreparedBenchmarkInputs` - 411 edges
4. `DatasetId` - 404 edges
5. `PathConfig` - 337 edges
6. `MethodId` - 323 edges
7. `ReferenceSource` - 316 edges
8. `RunConfig` - 313 edges
9. `ArtifactRef` - 281 edges
10. `FrameSelectionConfig` - 277 edges

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
Cohesion: 0.01
Nodes (533): _build_artifacts(), _DensePredictionArtifacts, _ensure_uint8_rgb_from_uimg(), _estimate_camera_intrinsics_from_frame(), _InProcessManager, _InProcessValue, Canonical MASt3R-SLAM backend adapter (offline + streaming).  This adapter wraps, Estimate model-raster intrinsics from a MASt3R keyframe pointmap. (+525 more)

### Community 1 - "Community 1"
Cohesion: 0.01
Nodes (469): _preprocess_images_with_lingbot(), _apply_snapshot_fallbacks(), _candidate_from_root(), _canonical_path_rows(), _derive_slam_artifacts(), discover_run_artifact_roots(), _file_inventory(), _format_size() (+461 more)

### Community 2 - "Community 2"
Cohesion: 0.01
Nodes (366): build_advio_page_data(), _scene_rows(), AdvioDownloadManager, _ensure_directory_parent(), Return local availability status for every catalog scene., advio_basis_metadata(), advio_basis_provenance(), AdvioBasisMetadata (+358 more)

### Community 3 - "Community 3"
Cohesion: 0.01
Nodes (315): interpolate_trajectory_poses(), _nearest_timestamp_indices(), ADVIO trajectory interpolation helpers., Interpolate positions and nearest-neighbor rotations at requested timestamps., _poses_for_frame_timestamps(), GroundAlignmentMetadata, GroundPlaneModel, GroundPlaneVisualizationHint (+307 more)

### Community 4 - "Community 4"
Cohesion: 0.02
Nodes (284): handle_advio_preview_action(), Controller helpers for the ADVIO Streamlit page., Persist the current ADVIO download-form state., Keep persisted preview state aligned with the runtime snapshot., Apply one preview-form action and return an error message when it fails., sync_advio_download_state(), sync_advio_preview_state(), AppContext (+276 more)

### Community 5 - "Community 5"
Cohesion: 0.07
Nodes (313): MethodId, Start one run and return the stable run identifier.          Args:             r, Request graceful stop for one active run., Return the latest projected metadata view for one run., Return recent runtime events for one run.          Args:             run_id: Sta, Resolve one target transient payload ref into a local array., Release backend-owned runtime resources.          Args:             preserve_loc, BaseConfig (+305 more)

### Community 6 - "Community 6"
Cohesion: 0.04
Nodes (263): Return the cache directory used for downloaded scene archives., Return one catalog scene by id., Download selected ADVIO scenes and extract complete scene payloads., AdvioRawCoordinateBasis, Raw coordinate bases used by official ADVIO provider artifacts., _RelativePathSpec, AdvioCatalog, AdvioSceneMetadata (+255 more)

### Community 7 - "Community 7"
Cohesion: 0.01
Nodes (156): Mast3rSlamSession, _attempt_rows(), _candidate_label(), _inventory_rows(), _metadata_json(), _path_rows(), _raw_preview_language(), _raw_preview_text() (+148 more)

### Community 8 - "Community 8"
Cohesion: 0.02
Nodes (193): _adapt_checkpoint_state_dict(), _as_numpy(), _build_lingbot_artifacts(), _cast_aggregator_for_inference(), _decode_pose_predictions(), _expect_lingbot_config(), _extract_checkpoint_state_dict(), _extract_dense_prediction_artifacts() (+185 more)

### Community 9 - "Community 9"
Cohesion: 0.02
Nodes (175): build_advio_comparison_trajectories(), build_crowd_density_figure(), build_local_readiness_figure(), build_scene_attribute_figure(), build_scene_mix_figure(), Plotly figure builders for the ADVIO dataset page., Build a crowd-density composition chart., Build a scene-attribute prevalence chart. (+167 more)

### Community 10 - "Community 10"
Cohesion: 0.03
Nodes (100): caller_namespace(), _ConsoleLogFormatter, _display_name(), from_callsite(), get_console(), _qualify_namespace(), Logging-backed Rich console helpers for the PRML VSLAM project., Convenience helper for a callsite-aware console instance. (+92 more)

### Community 11 - "Community 11"
Cohesion: 0.04
Nodes (122): build_coverage_matrix(), build_heatmap_data(), build_leaderboard(), build_per_sequence_table(), CoverageCell, CoverageMatrix, HeatmapData, LeaderboardRow (+114 more)

### Community 12 - "Community 12"
Cohesion: 0.03
Nodes (94): analyze_file(), analyze_source(), code_lines_for_source(), collect_dirty_diff_stats(), count_code_line_delta(), count_grouped_stats(), count_module_stats(), count_source_code_delta() (+86 more)

### Community 13 - "Community 13"
Cohesion: 0.04
Nodes (81): _benchmark_artifact_paths(), _cleanup_temporary_entry_root(), _compatible_entry_identity(), _compatible_entry_profile(), _copy_once(), _copy_optional_path(), _copy_path(), _csv_value() (+73 more)

### Community 14 - "Community 14"
Cohesion: 0.06
Nodes (44): Replay clock used by dataset and video source streams., Select whether replay follows source timing or returns observations immediately., Apply source-timestamp pacing for real-time replay., Reset the clock baseline for a new replay loop or connection., Sleep until the replay timestamp should be emitted., ReplayClock, ReplayMode, ImageSequenceObservationSource (+36 more)

### Community 15 - "Community 15"
Cohesion: 0.05
Nodes (39): Open3dTsdfBackendConfig, Provide the package-local runtime contract shared by reconstruction configs., Return the user-facing reconstruction label., Configure the minimal Open3D TSDF reconstruction backend.      The repo targets, Return the concrete reconstruction backend type., Instantiate the Open3D TSDF backend while ignoring unrelated kwargs., ReconstructionBackendConfig, DenseCloudEvaluationArtifact (+31 more)

### Community 16 - "Community 16"
Cohesion: 0.08
Nodes (43): _assert_slug(), build_run_config_from_sweep_item(), _build_run_id(), expand_sweep(), _load_slam_stage_from_template(), load_sweep_config(), _load_toml_payload(), _resolve_path() (+35 more)

### Community 17 - "Community 17"
Cohesion: 0.12
Nodes (37): test_load_recording_summary_reports_live_keyed_and_tracking_surfaces(), test_write_validation_bundle_emits_report_and_projection_images(), test_write_validation_bundle_respects_explicit_keyed_cloud_limit(), _write_synthetic_recording(), _ancestor_entity_paths(), _component_columns(), _keyed_point_cloud_snapshots(), _latest_live_model_snapshot() (+29 more)

### Community 18 - "Community 18"
Cohesion: 0.11
Nodes (35): build_pipeline_snapshot_render_model(), _coerce_int_metric(), _format_latency(), _format_optional_rate(), _format_queue(), _format_resources(), _format_tasks(), _format_throughput() (+27 more)

### Community 19 - "Community 19"
Cohesion: 0.09
Nodes (25): DataOnlyConfig, InvalidTargetConfig, NestedPayload, PlainPayload, Tests for the shared Pydantic base-model split., Runtime object used to verify default setup behavior., Config whose runtime target is constructed via ``target_type``., Config without a runtime target. (+17 more)

### Community 20 - "Community 20"
Cohesion: 0.14
Nodes (10): IntEnum, Name the device classes exposed by the upstream Record3D bindings., Record3DDeviceType, FakeRecord3DStream, Tests for the optional Record3D USB integration., Small in-memory stand-in for the upstream Record3D bindings., test_record3d_stream_requires_optional_dependency(), test_record3d_stream_wait_for_observation_returns_shared_contract() (+2 more)

### Community 21 - "Community 21"
Cohesion: 0.17
Nodes (4): _CappedPacketStream, _CappedStreamingSource, ObservationStream, StreamingSequenceSource

### Community 22 - "Community 22"
Cohesion: 0.17
Nodes (2): Tests for package-root public export surfaces., test_source_materialization_does_not_import_stage_package()

### Community 23 - "Community 23"
Cohesion: 0.36
Nodes (4): test_resolve_issue_moves_record_to_resolved_collection(), test_resolve_refactor_moves_record_to_resolved_collection(), test_resolve_todo_moves_record_to_resolved_collection(), _write_toml()

### Community 24 - "Community 24"
Cohesion: 0.67
Nodes (2): _valid_artifact_selector(), validate_artifact_key_selectors()

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): Ray-specific helpers for future stage runtime deployment.  This module intention

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from a 4x4 homogeneous matrix.

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): Return the compact source label used in logs and diagnostics.

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): Disconnect or release the source and any owned runtime resources.

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (1): Deserialize one IPC payload back into the target validated model type.

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (1): Return the human-readable label shown in plan previews.

### Community 33 - "Community 33"
Cohesion: 1.0
Nodes (1): Return whether ``exc`` looks like a transient local Ray connection failure.

### Community 34 - "Community 34"
Cohesion: 1.0
Nodes (1): Build one spec from one JSON object.

### Community 35 - "Community 35"
Cohesion: 1.0
Nodes (1): Return the net code-line delta.

### Community 36 - "Community 36"
Cohesion: 1.0
Nodes (1): Return the path that should own this change in reports.

## Knowledge Gaps
- **276 isolated node(s):** `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`, `Frame preprocessing helpers for ViSTA-SLAM.`, `One RGB frame prepared for upstream ViSTA ingestion.`, `Use the exact upstream ViSTA crop-and-resize helper path.`, `Convert one upstream ViSTA array-like payload into a numpy array.` (+271 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 22`** (12 nodes): `test_package_exports.py`, `Tests for package-root public export surfaces.`, `test_executable_stage_packages_export_canonical_surfaces()`, `test_interfaces_package_exports_only_canonical_pose_surface()`, `test_methods_package_exports_slam_surfaces()`, `test_pipeline_contracts_package_is_not_a_compatibility_hub()`, `test_pipeline_package_exports_only_minimal_public_surface()`, `test_reconstruction_package_exports_runtime_surfaces_without_harness()`, `test_replay_package_exports_only_replay_primitives()`, `test_source_materialization_does_not_import_stage_package()`, `test_sources_package_exports_source_owned_contracts()`, `test_vista_package_is_the_only_canonical_vista_surface()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (4 nodes): `_valid_artifact_selector()`, `validate_artifact_key_selectors()`, `validate_custom_resources()`, `config.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (2 nodes): `streamlit_app.py`, `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (2 nodes): `ray.py`, `Ray-specific helpers for future stage runtime deployment.  This module intention`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `Build the shared transform DTO from a 4x4 homogeneous matrix.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `Return the compact source label used in logs and diagnostics.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `Disconnect or release the source and any owned runtime resources.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `Deserialize one IPC payload back into the target validated model type.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (1 nodes): `Return the human-readable label shown in plan previews.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 33`** (1 nodes): `Return whether ``exc`` looks like a transient local Ray connection failure.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 34`** (1 nodes): `Build one spec from one JSON object.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (1 nodes): `Return the net code-line delta.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 36`** (1 nodes): `Return the path that should own this change in reports.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Test package helpers and suites for PRML VSLAM.` connect `Community 3` to `Community 0`, `Community 1`, `Community 2`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 9`, `Community 14`, `Community 15`, `Community 20`?**
  _High betweenness centrality (0.106) - this node is a cross-community bridge._
- **Why does `SequenceManifest` connect `Community 6` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 7`, `Community 8`, `Community 11`, `Community 15`?**
  _High betweenness centrality (0.078) - this node is a cross-community bridge._
- **Why does `path()` connect `Community 1` to `Community 0`, `Community 2`, `Community 3`, `Community 4`, `Community 7`, `Community 8`, `Community 9`, `Community 10`, `Community 11`, `Community 12`, `Community 16`, `Community 22`?**
  _High betweenness centrality (0.070) - this node is a cross-community bridge._
- **Are the 508 inferred relationships involving `SequenceManifest` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`SequenceManifest` has 508 INFERRED edges - model-reasoned connections that need verification._
- **Are the 494 inferred relationships involving `StageKey` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`StageKey` has 494 INFERRED edges - model-reasoned connections that need verification._
- **Are the 406 inferred relationships involving `PreparedBenchmarkInputs` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`PreparedBenchmarkInputs` has 406 INFERRED edges - model-reasoned connections that need verification._
- **Are the 401 inferred relationships involving `DatasetId` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`DatasetId` has 401 INFERRED edges - model-reasoned connections that need verification._