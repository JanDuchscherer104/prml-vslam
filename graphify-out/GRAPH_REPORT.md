# Graph Report - normalized-runtime-boundary-fix  (2026-06-23)

## Corpus Check
- 306 files · ~2,089,482 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 5024 nodes · 24518 edges · 33 communities detected
- Extraction: 30% EXTRACTED · 70% INFERRED · 0% AMBIGUOUS · INFERRED: 17093 edges (avg confidence: 0.59)
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

## God Nodes (most connected - your core abstractions)
1. `StageKey` - 453 edges
2. `SequenceManifest` - 449 edges
3. `PreparedBenchmarkInputs` - 381 edges
4. `DatasetId` - 375 edges
5. `ReferenceSource` - 298 edges
6. `PathConfig` - 297 edges
7. `ArtifactRef` - 283 edges
8. `MethodId` - 280 edges
9. `FrameSelectionConfig` - 240 edges
10. `StageRuntimeStatus` - 238 edges

## Surprising Connections (you probably didn't know these)
- `test_metrics_page_state_preserves_persisted_view_fields()` --calls--> `MetricsPageState`  [INFERRED]
  tests/test_app.py → src/prml_vslam/app/models.py
- `Focused tests for derived ground-plane alignment.` --uses--> `GroundAlignmentMetadata`  [INFERRED]
  tests/test_ground_alignment.py → src/prml_vslam/interfaces/alignment.py
- `test_pointmap_contract_rejects_sparse_point_cloud_shape()` --calls--> `PointMap`  [INFERRED]
  tests/test_geometry.py → src/prml_vslam/interfaces/geometry.py
- `Small runtime sources used by focused pipeline smoke tests.` --uses--> `SequenceManifest`  [INFERRED]
  tests/pipeline_testing_support.py → src/prml_vslam/sources/contracts.py
- `Minimal offline source for pipeline smoke tests.` --uses--> `SequenceManifest`  [INFERRED]
  tests/pipeline_testing_support.py → src/prml_vslam/sources/contracts.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.02
Nodes (515): GroundAlignmentMetadata, Result of one derived ground-plane alignment attempt.      When :attr:`applied`, InputArtifactDiagnostics, Inspection helpers for persisted pipeline run artifact roots., One submitted run attempt found in a persisted event log., Structured inspection result for one persisted pipeline run., Discover method-level run roots under the configured artifact directory., Load typed metadata and path inventory for one persisted run root. (+507 more)

### Community 1 - "Community 1"
Cohesion: 0.01
Nodes (401): _coordinator_actor_options(), RayPipelineBackend, BaseConfig, _ConfigFactory, FactoryConfig, from_toml(), _normalize_value(), Shared config and config-as-factory helpers for the repository.  This module own (+393 more)

### Community 2 - "Community 2"
Cohesion: 0.01
Nodes (354): build_advio_page_data(), _scene_rows(), AdvioDownloadManager, _ensure_directory_parent(), Return the cache directory used for downloaded scene archives., Return one catalog scene by id., Return local availability status for every catalog scene., Download selected ADVIO scenes and extract complete scene payloads. (+346 more)

### Community 3 - "Community 3"
Cohesion: 0.02
Nodes (417): AdvioFixedpointFitMode, AdvioFixedpointRegistration, AdvioFixpointSet, ADVIO fixedpoint registration helpers.  The official ADVIO visualization registe, Estimate a no-scale rigid transform from provider RDF world to fixpoints., Apply one fixedpoint registration to a provider RDF trajectory., Crop registered ADVIO trajectories and express them in one GT local frame., Build a frame-labelled camera pose from a matrix. (+409 more)

### Community 4 - "Community 4"
Cohesion: 0.01
Nodes (389): build_advio_comparison_trajectories(), build_crowd_density_figure(), build_local_readiness_figure(), build_scene_attribute_figure(), build_scene_mix_figure(), advio_common_start_local_trajectories(), advio_frame_transform_from_pose(), apply_advio_fixedpoint_registration() (+381 more)

### Community 5 - "Community 5"
Cohesion: 0.02
Nodes (377): handle_advio_preview_action(), Controller helpers for the ADVIO Streamlit page., Persist the current ADVIO download-form state., Keep persisted preview state aligned with the runtime snapshot., Apply one preview-form action and return an error message when it fails., sync_advio_download_state(), sync_advio_preview_state(), MethodId (+369 more)

### Community 6 - "Community 6"
Cohesion: 0.02
Nodes (278): _adapt_checkpoint_state_dict(), _as_numpy(), _build_artifacts(), _build_lingbot_artifacts(), _cast_aggregator_for_inference(), _decode_pose_predictions(), _DensePredictionArtifacts, _ensure_uint8_rgb_from_uimg() (+270 more)

### Community 7 - "Community 7"
Cohesion: 0.03
Nodes (198): BaseConfig, AdvioNormalizedDatasetBuildSource, NormalizedCadenceConfig, TOML contracts for normalized datastore batch builds., TOML-owned dataset groups for generating normalized datastore entries., Expand grouped dataset settings into per-sequence source configs., Normalize-time frame selection that contributes to datastore identity., Grouped ADVIO normalized-store build settings. (+190 more)

### Community 8 - "Community 8"
Cohesion: 0.02
Nodes (204): _apply_snapshot_fallbacks(), _candidate_from_root(), _canonical_path_rows(), _derive_slam_artifacts(), discover_run_artifact_roots(), _file_inventory(), _format_size(), inspect_run_artifacts() (+196 more)

### Community 9 - "Community 9"
Cohesion: 0.04
Nodes (152): available_metric_keys(), build_coverage_matrix(), build_heatmap_data(), build_leaderboard(), build_per_sequence_table(), _build_rmse_aggregate_rows(), build_wide_metric_rows(), _clean_records() (+144 more)

### Community 10 - "Community 10"
Cohesion: 0.02
Nodes (102): Record3DTransportId, IntEnum, _ensure_existing_under(), _ensure_optional_existing_under(), _ensure_under(), _resolve_observation_payload(), _validate_benchmark_input_paths(), _validate_entry_paths() (+94 more)

### Community 11 - "Community 11"
Cohesion: 0.03
Nodes (122): _attempt_rows(), _candidate_label(), _inventory_rows(), _metadata_json(), _path_rows(), _raw_preview_language(), _raw_preview_text(), render() (+114 more)

### Community 12 - "Community 12"
Cohesion: 0.02
Nodes (120): ArxivSourceSpec, download_file(), fetch_pdf(), fetch_tex_source(), from_json(), load_manifest(), main(), normalize_member_path() (+112 more)

### Community 13 - "Community 13"
Cohesion: 0.06
Nodes (58): artifact_ref(), Build one stable artifact reference for a materialized path., ExportRerunEventSink, load_reused_stage_results(), _load_slam_result(), _load_source_result(), _optional_npz(), _optional_ply() (+50 more)

### Community 14 - "Community 14"
Cohesion: 0.06
Nodes (65): _advio_aligned_diagnostic_reference(), _advio_aligned_diagnostic_references(), _benchmark_artifact_paths(), _cleanup_temporary_entry_root(), _copy_once(), _copy_path(), _csv_value(), _dedupe_manifest_rgb() (+57 more)

### Community 15 - "Community 15"
Cohesion: 0.08
Nodes (37): Replay clock used by dataset and video source streams., Select whether replay follows source timing or returns observations immediately., Apply source-timestamp pacing for real-time replay., Reset the clock baseline for a new replay loop or connection., Sleep until the replay timestamp should be emitted., ReplayClock, ReplayMode, ImageSequenceObservationSource (+29 more)

### Community 16 - "Community 16"
Cohesion: 0.11
Nodes (32): GroundPlaneModel, GroundPlaneVisualizationHint, Alignment result DTOs shared outside the alignment package.  These datamodels de, Dominant ground-plane hypothesis expressed in native ``world`` coordinates., Finite plane-patch geometry ready for visualization consumers., GroundAlignmentConfig, _build_viewer_transform(), _camera_down_alignment() (+24 more)

### Community 17 - "Community 17"
Cohesion: 0.11
Nodes (20): caller_namespace(), configure_logging(), _ConsoleLogFormatter, _ConsoleLogHighlighter, _display_name(), from_callsite(), get_console(), _qualify_namespace() (+12 more)

### Community 18 - "Community 18"
Cohesion: 0.15
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
Nodes (1): Return the short user-facing dataset label.

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): Deserialize one IPC payload back into the target validated model type.

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): Return the human-readable label shown in plan previews.

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): Return whether ``exc`` looks like a transient local Ray connection failure.

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (1): Build one spec from one JSON object.

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (1): Return the net code-line delta.

### Community 33 - "Community 33"
Cohesion: 1.0
Nodes (1): Return the path that should own this change in reports.

## Knowledge Gaps
- **262 isolated node(s):** `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`, `Frame preprocessing helpers for ViSTA-SLAM.`, `One RGB frame prepared for upstream ViSTA ingestion.`, `Use the exact upstream ViSTA crop-and-resize helper path.`, `Convert one upstream ViSTA array-like payload into a numpy array.` (+257 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 18`** (13 nodes): `test_package_exports.py`, `Tests for package-root public export surfaces.`, `test_align_root_does_not_reexport_heavy_subpackages()`, `test_executable_stage_packages_export_canonical_surfaces()`, `test_interfaces_package_exports_only_canonical_pose_surface()`, `test_methods_package_exports_slam_surfaces()`, `test_pipeline_contracts_package_is_not_a_compatibility_hub()`, `test_pipeline_package_exports_only_minimal_public_surface()`, `test_reconstruction_package_exports_runtime_surfaces_without_harness()`, `test_replay_package_exports_only_replay_primitives()`, `test_source_materialization_does_not_import_stage_package()`, `test_sources_package_exports_source_owned_contracts()`, `test_vista_package_is_the_only_canonical_vista_surface()`
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
- **Thin community `Community 27`** (1 nodes): `Return the short user-facing dataset label.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `Deserialize one IPC payload back into the target validated model type.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `Return the human-readable label shown in plan previews.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `Return whether ``exc`` looks like a transient local Ray connection failure.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `Build one spec from one JSON object.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (1 nodes): `Return the net code-line delta.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 33`** (1 nodes): `Return the path that should own this change in reports.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Test package helpers and suites for PRML VSLAM.` connect `Community 2` to `Community 0`, `Community 1`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 10`, `Community 15`, `Community 16`?**
  _High betweenness centrality (0.092) - this node is a cross-community bridge._
- **Why does `path()` connect `Community 1` to `Community 0`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 9`, `Community 11`, `Community 12`, `Community 13`, `Community 18`?**
  _High betweenness centrality (0.062) - this node is a cross-community bridge._
- **Why does `FrameTransform` connect `Community 3` to `Community 0`, `Community 1`, `Community 2`, `Community 4`, `Community 5`, `Community 6`, `Community 8`, `Community 10`, `Community 13`, `Community 16`?**
  _High betweenness centrality (0.056) - this node is a cross-community bridge._
- **Are the 450 inferred relationships involving `StageKey` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`StageKey` has 450 INFERRED edges - model-reasoned connections that need verification._
- **Are the 446 inferred relationships involving `SequenceManifest` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`SequenceManifest` has 446 INFERRED edges - model-reasoned connections that need verification._
- **Are the 376 inferred relationships involving `PreparedBenchmarkInputs` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`PreparedBenchmarkInputs` has 376 INFERRED edges - model-reasoned connections that need verification._
- **Are the 372 inferred relationships involving `DatasetId` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`DatasetId` has 372 INFERRED edges - model-reasoned connections that need verification._