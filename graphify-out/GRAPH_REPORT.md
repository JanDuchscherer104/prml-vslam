# Graph Report - prml-vslam  (2026-06-24)

## Corpus Check
- 306 files · ~2,809,455 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 5048 nodes · 24755 edges · 31 communities detected
- Extraction: 30% EXTRACTED · 70% INFERRED · 0% AMBIGUOUS · INFERRED: 17288 edges (avg confidence: 0.59)
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
1. `StageKey` - 455 edges
2. `SequenceManifest` - 451 edges
3. `PreparedBenchmarkInputs` - 395 edges
4. `DatasetId` - 381 edges
5. `PathConfig` - 301 edges
6. `ReferenceSource` - 300 edges
7. `ArtifactRef` - 283 edges
8. `MethodId` - 282 edges
9. `FrameSelectionConfig` - 246 edges
10. `StageRuntimeStatus` - 238 edges

## Surprising Connections (you probably didn't know these)
- `MetricsPageState` --calls--> `test_metrics_page_state_preserves_persisted_view_fields()`  [INFERRED]
  src/prml_vslam/app/models.py → tests/test_app.py
- `GroundAlignmentMetadata` --uses--> `Focused tests for derived ground-plane alignment.`  [INFERRED]
  src/prml_vslam/interfaces/alignment.py → tests/test_ground_alignment.py
- `PointMap` --calls--> `test_pointmap_contract_rejects_sparse_point_cloud_shape()`  [INFERRED]
  src/prml_vslam/interfaces/geometry.py → tests/test_geometry.py
- `SequenceManifest` --uses--> `Small runtime sources used by focused pipeline smoke tests.`  [INFERRED]
  src/prml_vslam/sources/contracts.py → tests/pipeline_testing_support.py
- `SequenceManifest` --uses--> `Minimal offline source for pipeline smoke tests.`  [INFERRED]
  src/prml_vslam/sources/contracts.py → tests/pipeline_testing_support.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.02
Nodes (444): AdvioSceneMetadata, Return the CSV backing one ADVIO pose provider., Load one ADVIO trajectory using the requested serving semantics., Apply one ADVIO serving mode to an already loaded trajectory., Return explicit target/source frame labels for served ADVIO camera poses., AdvioOfflineSample, AdvioSequencePaths, Build one sequence runtime from its validated config. (+436 more)

### Community 1 - "Community 1"
Cohesion: 0.02
Nodes (387): CloudAlignmentService, icp_point_cloud_path(), ICP point-cloud alignment service., Materialize offline point-cloud alignment artifacts before cloud metrics., Refine a trajectory-Sim(3)-aligned cloud against a reference cloud with ICP., Return the deterministic point-cloud alignment metadata path., Return the deterministic ICP-refined point-cloud path., _read_non_empty_point_cloud() (+379 more)

### Community 2 - "Community 2"
Cohesion: 0.02
Nodes (304): GroundAlignmentMetadata, Result of one derived ground-plane alignment attempt.      When :attr:`applied`, _apply_snapshot_fallbacks(), _candidate_from_root(), _canonical_path_rows(), _derive_slam_artifacts(), discover_run_artifact_roots(), _file_inventory() (+296 more)

### Community 3 - "Community 3"
Cohesion: 0.01
Nodes (365): build_advio_comparison_trajectories(), build_advio_page_data(), AdvioDownloadManager, _ensure_directory_parent(), Return the cache directory used for downloaded scene archives., Return one catalog scene by id., Return local availability status for every catalog scene., Download selected ADVIO scenes and extract complete scene payloads. (+357 more)

### Community 4 - "Community 4"
Cohesion: 0.02
Nodes (385): handle_advio_preview_action(), Controller helpers for the ADVIO Streamlit page., Persist the current ADVIO download-form state., Keep persisted preview state aligned with the runtime snapshot., Apply one preview-form action and return an error message when it fails., _scene_rows(), sync_advio_download_state(), sync_advio_preview_state() (+377 more)

### Community 5 - "Community 5"
Cohesion: 0.01
Nodes (365): build_crowd_density_figure(), build_local_readiness_figure(), build_scene_attribute_figure(), build_scene_mix_figure(), advio_common_start_local_trajectories(), advio_frame_transform_from_pose(), AdvioFixedpointRegistration, AdvioFixpointSet (+357 more)

### Community 6 - "Community 6"
Cohesion: 0.02
Nodes (298): _adapt_checkpoint_state_dict(), _as_numpy(), _build_artifacts(), _build_lingbot_artifacts(), _cast_aggregator_for_inference(), _decode_pose_predictions(), _DensePredictionArtifacts, _ensure_uint8_rgb_from_uimg() (+290 more)

### Community 7 - "Community 7"
Cohesion: 0.02
Nodes (275): BaseConfig, _ConfigFactory, FactoryConfig, from_toml(), _normalize_value(), Shared config and config-as-factory helpers for the repository.  This module own, Render the config as a Rich tree for quick human inspection., Mixin for configs that construct one runtime owner or adapter.      This pattern (+267 more)

### Community 8 - "Community 8"
Cohesion: 0.03
Nodes (191): BaseConfig, CloudAlignmentStageConfig, CloudEvaluationStageConfig, CloudMetricId, _compile_run_plan(), DenseCloudSelectionConfig, GroundAlignmentStageConfig, Open3dTsdfBackendConfig (+183 more)

### Community 9 - "Community 9"
Cohesion: 0.02
Nodes (237): _attempt_rows(), _candidate_label(), _inventory_rows(), _metadata_json(), _path_rows(), _raw_preview_language(), _raw_preview_text(), render() (+229 more)

### Community 10 - "Community 10"
Cohesion: 0.03
Nodes (194): available_metric_keys(), build_coverage_matrix(), build_heatmap_data(), build_leaderboard(), build_per_sequence_table(), _build_rmse_aggregate_rows(), build_wide_metric_rows(), _clean_records() (+186 more)

### Community 11 - "Community 11"
Cohesion: 0.03
Nodes (81): IntEnum, _camera_pose_from_binding(), _device_from_binding(), _import_record3d_module(), _intrinsics_from_binding(), open_record3d_usb_packet_stream(), Disconnect the current USB device if one is active., Wait for the next shared observation emitted by the USB device. (+73 more)

### Community 12 - "Community 12"
Cohesion: 0.03
Nodes (108): analyze_file(), analyze_source(), code_lines_for_source(), collect_dirty_diff_stats(), count_code_line_delta(), count_grouped_stats(), count_module_stats(), count_source_code_delta() (+100 more)

### Community 13 - "Community 13"
Cohesion: 0.04
Nodes (86): _normalized_entry_timestamps_ns(), Backward-compatible warning alias., _advio_aligned_diagnostic_reference(), _advio_aligned_diagnostic_references(), _benchmark_artifact_paths(), _cleanup_temporary_entry_root(), _copy_once(), _copy_path() (+78 more)

### Community 14 - "Community 14"
Cohesion: 0.05
Nodes (77): ape_error_colors(), augment_viewer_recording_with_ground_plane(), build_default_blueprint(), create_recording_stream(), _decimate_rows(), _entity_token(), evaluation_case_root(), evaluation_metric_root() (+69 more)

### Community 15 - "Community 15"
Cohesion: 0.07
Nodes (38): Replay clock used by dataset and video source streams., Select whether replay follows source timing or returns observations immediately., Apply source-timestamp pacing for real-time replay., Reset the clock baseline for a new replay loop or connection., Sleep until the replay timestamp should be emitted., ReplayClock, ReplayMode, ImageSequenceObservationSource (+30 more)

### Community 16 - "Community 16"
Cohesion: 0.11
Nodes (35): build_pipeline_snapshot_render_model(), _coerce_int_metric(), _format_latency(), _format_optional_rate(), _format_queue(), _format_resources(), _format_tasks(), _format_throughput() (+27 more)

### Community 17 - "Community 17"
Cohesion: 0.15
Nodes (2): Tests for package-root public export surfaces., test_source_materialization_does_not_import_stage_package()

### Community 19 - "Community 19"
Cohesion: 1.0
Nodes (1): Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays

### Community 20 - "Community 20"
Cohesion: 1.0
Nodes (1): Ray-specific helpers for future stage runtime deployment.  This module intention

### Community 21 - "Community 21"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.

### Community 22 - "Community 22"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from a 4x4 homogeneous matrix.

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (1): Return the compact source label used in logs and diagnostics.

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (1): Disconnect or release the source and any owned runtime resources.

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): Return the short user-facing dataset label.

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
- **262 isolated node(s):** `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`, `Frame preprocessing helpers for ViSTA-SLAM.`, `One RGB frame prepared for upstream ViSTA ingestion.`, `Use the exact upstream ViSTA crop-and-resize helper path.`, `Convert one upstream ViSTA array-like payload into a numpy array.` (+257 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 17`** (13 nodes): `test_package_exports.py`, `Tests for package-root public export surfaces.`, `test_align_root_does_not_reexport_heavy_subpackages()`, `test_executable_stage_packages_export_canonical_surfaces()`, `test_interfaces_package_exports_only_canonical_pose_surface()`, `test_methods_package_exports_slam_surfaces()`, `test_pipeline_contracts_package_is_not_a_compatibility_hub()`, `test_pipeline_package_exports_only_minimal_public_surface()`, `test_reconstruction_package_exports_runtime_surfaces_without_harness()`, `test_replay_package_exports_only_replay_primitives()`, `test_source_materialization_does_not_import_stage_package()`, `test_sources_package_exports_source_owned_contracts()`, `test_vista_package_is_the_only_canonical_vista_surface()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 19`** (2 nodes): `streamlit_app.py`, `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 20`** (2 nodes): `ray.py`, `Ray-specific helpers for future stage runtime deployment.  This module intention`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (1 nodes): `Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 22`** (1 nodes): `Build the shared transform DTO from a 4x4 homogeneous matrix.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (1 nodes): `Return the compact source label used in logs and diagnostics.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (1 nodes): `Disconnect or release the source and any owned runtime resources.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (1 nodes): `Return the short user-facing dataset label.`
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

- **Why does `Test package helpers and suites for PRML VSLAM.` connect `Community 8` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 11`, `Community 15`?**
  _High betweenness centrality (0.100) - this node is a cross-community bridge._
- **Why does `SequenceManifest` connect `Community 0` to `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 9`, `Community 10`, `Community 11`?**
  _High betweenness centrality (0.066) - this node is a cross-community bridge._
- **Why does `StageKey` connect `Community 1` to `Community 0`, `Community 2`, `Community 4`, `Community 7`, `Community 8`, `Community 14`, `Community 16`?**
  _High betweenness centrality (0.062) - this node is a cross-community bridge._
- **Are the 452 inferred relationships involving `StageKey` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`StageKey` has 452 INFERRED edges - model-reasoned connections that need verification._
- **Are the 448 inferred relationships involving `SequenceManifest` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`SequenceManifest` has 448 INFERRED edges - model-reasoned connections that need verification._
- **Are the 390 inferred relationships involving `PreparedBenchmarkInputs` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`PreparedBenchmarkInputs` has 390 INFERRED edges - model-reasoned connections that need verification._
- **Are the 378 inferred relationships involving `DatasetId` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`DatasetId` has 378 INFERRED edges - model-reasoned connections that need verification._