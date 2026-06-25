# Graph Report - prml-vslam  (2026-06-25)

## Corpus Check
- 306 files · ~2,809,716 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 5100 nodes · 25381 edges · 36 communities detected
- Extraction: 29% EXTRACTED · 71% INFERRED · 0% AMBIGUOUS · INFERRED: 17906 edges (avg confidence: 0.59)
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

## God Nodes (most connected - your core abstractions)
1. `SequenceManifest` - 493 edges
2. `StageKey` - 455 edges
3. `PreparedBenchmarkInputs` - 437 edges
4. `DatasetId` - 423 edges
5. `ReferenceSource` - 342 edges
6. `PathConfig` - 303 edges
7. `FrameSelectionConfig` - 289 edges
8. `ArtifactRef` - 283 edges
9. `MethodId` - 282 edges
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
Cohesion: 0.02
Nodes (458): GroundAlignmentMetadata, InputArtifactDiagnostics, Inspection helpers for persisted pipeline run artifact roots., One submitted run attempt found in a persisted event log., Structured inspection result for one persisted pipeline run., Discover method-level run roots under the configured artifact directory., Load typed metadata and path inventory for one persisted run root., One selectable persisted method-level run artifact root. (+450 more)

### Community 1 - "Community 1"
Cohesion: 0.01
Nodes (478): _build_artifacts(), advio_common_start_local_trajectories(), advio_frame_transform_from_pose(), AdvioFixedpointRegistration, apply_advio_fixedpoint_registration(), estimate_advio_fixedpoint_registration(), _estimate_rigid_no_scale(), _gravity_tilt_deg() (+470 more)

### Community 2 - "Community 2"
Cohesion: 0.01
Nodes (358): build_advio_page_data(), _scene_rows(), AdvioDownloadManager, _ensure_directory_parent(), Return the cache directory used for downloaded scene archives., Return one catalog scene by id., Return local availability status for every catalog scene., Download selected ADVIO scenes and extract complete scene payloads. (+350 more)

### Community 3 - "Community 3"
Cohesion: 0.02
Nodes (393): _DensePredictionArtifacts, _ensure_uint8_rgb_from_uimg(), _estimate_camera_intrinsics_from_frame(), _InProcessManager, _InProcessValue, Mast3rSlamSession, Canonical MASt3R-SLAM backend adapter (offline + streaming).  This adapter wraps, Estimate model-raster intrinsics from a MASt3R keyframe pointmap. (+385 more)

### Community 4 - "Community 4"
Cohesion: 0.02
Nodes (385): handle_advio_preview_action(), Controller helpers for the ADVIO Streamlit page., Persist the current ADVIO download-form state., Keep persisted preview state aligned with the runtime snapshot., Apply one preview-form action and return an error message when it fails., sync_advio_download_state(), sync_advio_preview_state(), AdvioEnvironment (+377 more)

### Community 5 - "Community 5"
Cohesion: 0.01
Nodes (376): build_advio_comparison_trajectories(), build_crowd_density_figure(), build_local_readiness_figure(), build_scene_attribute_figure(), build_scene_mix_figure(), Plotly figure builders for the ADVIO dataset page., Build a crowd-density composition chart., Build a scene-attribute prevalence chart. (+368 more)

### Community 6 - "Community 6"
Cohesion: 0.01
Nodes (323): _coordinator_actor_options(), RayPipelineBackend, BaseConfig, _ConfigFactory, from_toml(), _normalize_value(), Shared config and config-as-factory helpers for the repository.  This module own, Render the config as a Rich tree for quick human inspection. (+315 more)

### Community 7 - "Community 7"
Cohesion: 0.01
Nodes (246): _adapt_checkpoint_state_dict(), _as_numpy(), _build_lingbot_artifacts(), _cast_aggregator_for_inference(), _decode_pose_predictions(), _expect_lingbot_config(), _extract_checkpoint_state_dict(), _extract_dense_prediction_artifacts() (+238 more)

### Community 8 - "Community 8"
Cohesion: 0.05
Nodes (256): BaseConfig, AdvioNormalizedDatasetBuildSource, NormalizedCadenceConfig, NormalizedDatasetBuildConfig, TOML contracts for normalized datastore batch builds., TOML-owned dataset groups for generating normalized datastore entries., Expand grouped dataset settings into per-sequence source configs., Normalize-time frame selection that contributes to datastore identity. (+248 more)

### Community 9 - "Community 9"
Cohesion: 0.02
Nodes (203): LingbotMapSlamBackend, Mast3rSlamBackend, VistaSlamBackend, build_slam_backend_config(), LingbotMapSlamBackendConfig, Persisted SLAM backend config and backend muxing.  The SLAM stage owns the publi, Whether the backend can emit live preview payloads., Whether the backend may emit native visualization artifacts. (+195 more)

### Community 10 - "Community 10"
Cohesion: 0.03
Nodes (173): available_metric_keys(), build_coverage_matrix(), build_heatmap_data(), build_leaderboard(), build_per_sequence_table(), _build_rmse_aggregate_rows(), build_wide_metric_rows(), _clean_records() (+165 more)

### Community 11 - "Community 11"
Cohesion: 0.02
Nodes (90): Replay clock used by dataset and video source streams., Select whether replay follows source timing or returns observations immediately., Apply source-timestamp pacing for real-time replay., Reset the clock baseline for a new replay loop or connection., Sleep until the replay timestamp should be emitted., ReplayClock, ReplayMode, Return the user-facing reconstruction label. (+82 more)

### Community 12 - "Community 12"
Cohesion: 0.04
Nodes (103): AdvioCalibration, _expect_float_list(), _expect_mapping(), _expect_matrix(), _extract_camera_mapping(), load_advio_calibration(), Parse an official ADVIO calibration YAML into a typed camera model., Convert an ADVIO pose CSV into a TUM trajectory file. (+95 more)

### Community 13 - "Community 13"
Cohesion: 0.04
Nodes (71): analyze_file(), analyze_source(), code_lines_for_source(), collect_dirty_diff_stats(), count_code_line_delta(), count_grouped_stats(), count_module_stats(), count_source_code_delta() (+63 more)

### Community 14 - "Community 14"
Cohesion: 0.15
Nodes (2): Tests for package-root public export surfaces., test_source_materialization_does_not_import_stage_package()

### Community 15 - "Community 15"
Cohesion: 0.18
Nodes (2): finish_streaming(), start_streaming()

### Community 16 - "Community 16"
Cohesion: 1.0
Nodes (1): Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays

### Community 17 - "Community 17"
Cohesion: 1.0
Nodes (1): Ray-specific helpers for future stage runtime deployment.  This module intention

### Community 18 - "Community 18"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.

### Community 19 - "Community 19"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from a 4x4 homogeneous matrix.

### Community 20 - "Community 20"
Cohesion: 1.0
Nodes (1): Return the compact source label used in logs and diagnostics.

### Community 21 - "Community 21"
Cohesion: 1.0
Nodes (1): Disconnect or release the source and any owned runtime resources.

### Community 22 - "Community 22"
Cohesion: 1.0
Nodes (1): Return the short user-facing dataset label.

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (1): Deserialize one IPC payload back into the target validated model type.

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (1): Return the human-readable label shown in plan previews.

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): Return whether ``exc`` looks like a transient local Ray connection failure.

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): Build one spec from one JSON object.

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): Return the net code-line delta.

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): Return the path that should own this change in reports.

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): Return the short user-facing dataset label.

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): Coordinate-frame semantics for served ADVIO trajectories.

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (1): Typed ADVIO serving semantics shared by request and manifest contracts.

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (1): Source-prepared RGB-D reference-cloud sampling policy.

### Community 33 - "Community 33"
Cohesion: 1.0
Nodes (1): Local availability summary for one dataset scene.

### Community 34 - "Community 34"
Cohesion: 1.0
Nodes (1): High-level summary of committed and local dataset coverage.

### Community 35 - "Community 35"
Cohesion: 1.0
Nodes (1): Return the effective ADVIO provider for one optional serving config.

## Knowledge Gaps
- **268 isolated node(s):** `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`, `Frame preprocessing helpers for ViSTA-SLAM.`, `One RGB frame prepared for upstream ViSTA ingestion.`, `Use the exact upstream ViSTA crop-and-resize helper path.`, `Convert one upstream ViSTA array-like payload into a numpy array.` (+263 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 14`** (13 nodes): `test_package_exports.py`, `Tests for package-root public export surfaces.`, `test_align_root_does_not_reexport_heavy_subpackages()`, `test_executable_stage_packages_export_canonical_surfaces()`, `test_interfaces_package_exports_only_canonical_pose_surface()`, `test_methods_package_exports_slam_surfaces()`, `test_pipeline_contracts_package_is_not_a_compatibility_hub()`, `test_pipeline_package_exports_only_minimal_public_surface()`, `test_reconstruction_package_exports_runtime_surfaces_without_harness()`, `test_replay_package_exports_only_replay_primitives()`, `test_source_materialization_does_not_import_stage_package()`, `test_sources_package_exports_source_owned_contracts()`, `test_vista_package_is_the_only_canonical_vista_surface()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 15`** (12 nodes): `protocols.py`, `protocols.py`, `drain_runtime_updates()`, `drain_streaming_updates()`, `finish_streaming()`, `run_observations()`, `run_offline()`, `start_streaming()`, `status()`, `step_streaming()`, `stop()`, `submit_stream_item()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 16`** (2 nodes): `streamlit_app.py`, `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 17`** (2 nodes): `ray.py`, `Ray-specific helpers for future stage runtime deployment.  This module intention`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 18`** (1 nodes): `Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 19`** (1 nodes): `Build the shared transform DTO from a 4x4 homogeneous matrix.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 20`** (1 nodes): `Return the compact source label used in logs and diagnostics.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (1 nodes): `Disconnect or release the source and any owned runtime resources.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 22`** (1 nodes): `Return the short user-facing dataset label.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (1 nodes): `Deserialize one IPC payload back into the target validated model type.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (1 nodes): `Return the human-readable label shown in plan previews.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (1 nodes): `Return whether ``exc`` looks like a transient local Ray connection failure.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `Build one spec from one JSON object.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `Return the net code-line delta.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `Return the path that should own this change in reports.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `Return the short user-facing dataset label.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `Coordinate-frame semantics for served ADVIO trajectories.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `Typed ADVIO serving semantics shared by request and manifest contracts.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (1 nodes): `Source-prepared RGB-D reference-cloud sampling policy.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 33`** (1 nodes): `Local availability summary for one dataset scene.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 34`** (1 nodes): `High-level summary of committed and local dataset coverage.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (1 nodes): `Return the effective ADVIO provider for one optional serving config.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Test package helpers and suites for PRML VSLAM.` connect `Community 11` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 9`?**
  _High betweenness centrality (0.071) - this node is a cross-community bridge._
- **Why does `SequenceManifest` connect `Community 3` to `Community 0`, `Community 1`, `Community 2`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 9`, `Community 10`, `Community 11`?**
  _High betweenness centrality (0.070) - this node is a cross-community bridge._
- **Why does `StageKey` connect `Community 0` to `Community 1`, `Community 3`, `Community 4`, `Community 6`, `Community 8`, `Community 9`, `Community 11`, `Community 12`?**
  _High betweenness centrality (0.055) - this node is a cross-community bridge._
- **Are the 490 inferred relationships involving `SequenceManifest` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`SequenceManifest` has 490 INFERRED edges - model-reasoned connections that need verification._
- **Are the 452 inferred relationships involving `StageKey` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`StageKey` has 452 INFERRED edges - model-reasoned connections that need verification._
- **Are the 432 inferred relationships involving `PreparedBenchmarkInputs` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`PreparedBenchmarkInputs` has 432 INFERRED edges - model-reasoned connections that need verification._
- **Are the 420 inferred relationships involving `DatasetId` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`DatasetId` has 420 INFERRED edges - model-reasoned connections that need verification._