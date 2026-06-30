# Graph Report - prml-vslam  (2026-06-25)

## Corpus Check
- 306 files · ~2,810,132 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 5157 nodes · 26087 edges · 43 communities detected
- Extraction: 29% EXTRACTED · 71% INFERRED · 0% AMBIGUOUS · INFERRED: 18583 edges (avg confidence: 0.59)
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
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]

## God Nodes (most connected - your core abstractions)
1. `SequenceManifest` - 539 edges
2. `PreparedBenchmarkInputs` - 483 edges
3. `DatasetId` - 470 edges
4. `StageKey` - 455 edges
5. `ReferenceSource` - 388 edges
6. `FrameSelectionConfig` - 337 edges
7. `PathConfig` - 303 edges
8. `ArtifactRef` - 283 edges
9. `MethodId` - 282 edges
10. `ReferenceTrajectoryRef` - 249 edges

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
Nodes (551): _build_artifacts(), _DensePredictionArtifacts, _ensure_uint8_rgb_from_uimg(), _InProcessManager, _InProcessValue, Canonical MASt3R-SLAM backend adapter (offline + streaming).  This adapter wraps, Estimate model-raster intrinsics from a MASt3R keyframe pointmap., Run LingBot-Map and persist normalized trajectory and dense geometry. (+543 more)

### Community 1 - "Community 1"
Cohesion: 0.01
Nodes (470): _adapt_checkpoint_state_dict(), _as_numpy(), _build_lingbot_artifacts(), _cast_aggregator_for_inference(), _decode_pose_predictions(), _estimate_camera_intrinsics_from_frame(), _expect_lingbot_config(), _extract_checkpoint_state_dict() (+462 more)

### Community 2 - "Community 2"
Cohesion: 0.03
Nodes (464): Controller helpers for the ADVIO Streamlit page., Persist the current ADVIO download-form state., Keep persisted preview state aligned with the runtime snapshot., Apply one preview-form action and return an error message when it fails., sync_advio_download_state(), AdvioPeopleLevel, Crowd-density labels committed from the official ADVIO scene table., MethodId (+456 more)

### Community 3 - "Community 3"
Cohesion: 0.01
Nodes (440): build_crowd_density_figure(), build_local_readiness_figure(), build_scene_attribute_figure(), build_scene_mix_figure(), handle_advio_preview_action(), sync_advio_preview_state(), Plotly figure builders for the ADVIO dataset page., Build a crowd-density composition chart. (+432 more)

### Community 4 - "Community 4"
Cohesion: 0.01
Nodes (349): build_advio_page_data(), _scene_rows(), AdvioDownloadManager, _ensure_directory_parent(), Return the cache directory used for downloaded scene archives., Return one catalog scene by id., Return local availability status for every catalog scene., Download selected ADVIO scenes and extract complete scene payloads. (+341 more)

### Community 5 - "Community 5"
Cohesion: 0.01
Nodes (337): _coordinator_actor_options(), RayPipelineBackend, BaseConfig, _ConfigFactory, FactoryConfig, from_toml(), _normalize_value(), Shared config and config-as-factory helpers for the repository.  This module own (+329 more)

### Community 6 - "Community 6"
Cohesion: 0.03
Nodes (353): AdvioFixedpointFitMode, AdvioFixpointSet, ADVIO fixedpoint registration helpers.  The official ADVIO visualization registe, Estimate a no-scale rigid transform from provider RDF world to fixpoints., Apply one fixedpoint registration to a provider RDF trajectory., Crop registered ADVIO trajectories and express them in one GT local frame., Build a frame-labelled camera pose from a matrix., Rigid registration mode selected for one ADVIO provider trajectory. (+345 more)

### Community 7 - "Community 7"
Cohesion: 0.01
Nodes (185): Mast3rSlamSession, _normalized_entry_timestamps_ns(), Backward-compatible warning alias., IntEnum, _advio_aligned_diagnostic_reference(), _advio_aligned_diagnostic_references(), _advio_reference_source_for_serving(), _benchmark_artifact_paths() (+177 more)

### Community 8 - "Community 8"
Cohesion: 0.02
Nodes (208): _apply_snapshot_fallbacks(), _candidate_from_root(), _canonical_path_rows(), _derive_slam_artifacts(), discover_run_artifact_roots(), _file_inventory(), _format_size(), inspect_run_artifacts() (+200 more)

### Community 9 - "Community 9"
Cohesion: 0.03
Nodes (178): available_metric_keys(), build_coverage_matrix(), build_heatmap_data(), build_leaderboard(), build_per_sequence_table(), _build_rmse_aggregate_rows(), build_wide_metric_rows(), _clean_records() (+170 more)

### Community 10 - "Community 10"
Cohesion: 0.03
Nodes (114): LingbotMapSlamBackend, Mast3rSlamBackend, VistaSlamBackend, build_slam_backend_config(), Persisted SLAM backend config and backend muxing.  The SLAM stage owns the publi, Whether the backend can emit live preview payloads., Whether the backend may emit native visualization artifacts., Whether the backend supports repository trajectory evaluation. (+106 more)

### Community 11 - "Community 11"
Cohesion: 0.05
Nodes (63): build_advio_comparison_trajectories(), load_advio_fixpoints(), advio_basis_metadata(), advio_basis_provenance(), AdvioBasisMetadata, basis_for_pose_source(), _flatten_matrix(), _pose_matrix() (+55 more)

### Community 12 - "Community 12"
Cohesion: 0.07
Nodes (47): _assert_slug(), build_run_config_from_sweep_item(), _build_run_id(), expand_sweep(), _load_slam_stage_from_template(), load_sweep_config(), _load_toml_payload(), validate_ids_are_slugs() (+39 more)

### Community 13 - "Community 13"
Cohesion: 0.07
Nodes (38): Replay clock used by dataset and video source streams., Select whether replay follows source timing or returns observations immediately., Apply source-timestamp pacing for real-time replay., Reset the clock baseline for a new replay loop or connection., Sleep until the replay timestamp should be emitted., ReplayClock, ReplayMode, ImageSequenceObservationSource (+30 more)

### Community 14 - "Community 14"
Cohesion: 0.1
Nodes (33): GroundPlaneModel, GroundPlaneVisualizationHint, Alignment result DTOs shared outside the alignment package.  These datamodels de, Dominant ground-plane hypothesis expressed in native ``world`` coordinates., Finite plane-patch geometry ready for visualization consumers., GroundAlignmentConfig, _build_viewer_transform(), _camera_down_alignment() (+25 more)

### Community 15 - "Community 15"
Cohesion: 0.08
Nodes (24): Return the user-facing reconstruction label., Configure the minimal Open3D TSDF reconstruction backend.      The repo targets, Return the concrete reconstruction backend type., Instantiate the Open3D TSDF backend while ignoring unrelated kwargs., Describe normalized durable outputs from one reconstruction run.      The minima, ReconstructionArtifacts, ReconstructionMethodId, _import_open3d() (+16 more)

### Community 16 - "Community 16"
Cohesion: 0.12
Nodes (33): build_pipeline_snapshot_render_model(), _coerce_int_metric(), _format_latency(), _format_optional_rate(), _format_queue(), _format_resources(), _format_tasks(), _format_throughput() (+25 more)

### Community 17 - "Community 17"
Cohesion: 0.13
Nodes (28): _add_point_cloud_trace(), _add_trajectory_trace(), _apply_comparison_layout(), _build_figure(), build_reference_reconstruction_figure(), build_slam_reference_comparison_figure(), _combined_bounds(), _decimate_mesh() (+20 more)

### Community 18 - "Community 18"
Cohesion: 0.09
Nodes (25): DataOnlyConfig, InvalidTargetConfig, NestedPayload, PlainPayload, Tests for the shared Pydantic base-model split., Runtime object used to verify default setup behavior., Config whose runtime target is constructed via ``target_type``., Config without a runtime target. (+17 more)

### Community 19 - "Community 19"
Cohesion: 0.13
Nodes (23): _build_blueprint_command(), create_follow_trajectory_artifact(), default_follow_output_path(), _default_recording_id(), _follow_blueprint_script(), FollowArtifactResult, main(), _merge_command() (+15 more)

### Community 20 - "Community 20"
Cohesion: 0.15
Nodes (2): Tests for package-root public export surfaces., test_source_materialization_does_not_import_stage_package()

### Community 21 - "Community 21"
Cohesion: 0.25
Nodes (1): Backend boundary between launch surfaces and execution substrates.  This module

### Community 22 - "Community 22"
Cohesion: 0.36
Nodes (4): test_resolve_issue_moves_record_to_resolved_collection(), test_resolve_refactor_moves_record_to_resolved_collection(), test_resolve_todo_moves_record_to_resolved_collection(), _write_toml()

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (1): Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (1): Ray-specific helpers for future stage runtime deployment.  This module intention

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from a 4x4 homogeneous matrix.

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): Return the compact source label used in logs and diagnostics.

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

### Community 36 - "Community 36"
Cohesion: 1.0
Nodes (1): Return the short user-facing dataset label.

### Community 37 - "Community 37"
Cohesion: 1.0
Nodes (1): Coordinate-frame semantics for served ADVIO trajectories.

### Community 38 - "Community 38"
Cohesion: 1.0
Nodes (1): Typed ADVIO serving semantics shared by request and manifest contracts.

### Community 39 - "Community 39"
Cohesion: 1.0
Nodes (1): Source-prepared RGB-D reference-cloud sampling policy.

### Community 40 - "Community 40"
Cohesion: 1.0
Nodes (1): Local availability summary for one dataset scene.

### Community 41 - "Community 41"
Cohesion: 1.0
Nodes (1): High-level summary of committed and local dataset coverage.

### Community 42 - "Community 42"
Cohesion: 1.0
Nodes (1): Return the effective ADVIO provider for one optional serving config.

## Knowledge Gaps
- **268 isolated node(s):** `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`, `Frame preprocessing helpers for ViSTA-SLAM.`, `One RGB frame prepared for upstream ViSTA ingestion.`, `Use the exact upstream ViSTA crop-and-resize helper path.`, `Convert one upstream ViSTA array-like payload into a numpy array.` (+263 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 20`** (13 nodes): `test_package_exports.py`, `Tests for package-root public export surfaces.`, `test_align_root_does_not_reexport_heavy_subpackages()`, `test_executable_stage_packages_export_canonical_surfaces()`, `test_interfaces_package_exports_only_canonical_pose_surface()`, `test_methods_package_exports_slam_surfaces()`, `test_pipeline_contracts_package_is_not_a_compatibility_hub()`, `test_pipeline_package_exports_only_minimal_public_surface()`, `test_reconstruction_package_exports_runtime_surfaces_without_harness()`, `test_replay_package_exports_only_replay_primitives()`, `test_source_materialization_does_not_import_stage_package()`, `test_sources_package_exports_source_owned_contracts()`, `test_vista_package_is_the_only_canonical_vista_surface()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (8 nodes): `get_events()`, `get_snapshot()`, `Backend boundary between launch surfaces and execution substrates.  This module`, `read_payload()`, `shutdown()`, `stop_run()`, `submit_run()`, `backend.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (2 nodes): `streamlit_app.py`, `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (2 nodes): `ray.py`, `Ray-specific helpers for future stage runtime deployment.  This module intention`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (1 nodes): `Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `Build the shared transform DTO from a 4x4 homogeneous matrix.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `Return the compact source label used in logs and diagnostics.`
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
- **Thin community `Community 36`** (1 nodes): `Return the short user-facing dataset label.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 37`** (1 nodes): `Coordinate-frame semantics for served ADVIO trajectories.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 38`** (1 nodes): `Typed ADVIO serving semantics shared by request and manifest contracts.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 39`** (1 nodes): `Source-prepared RGB-D reference-cloud sampling policy.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 40`** (1 nodes): `Local availability summary for one dataset scene.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 41`** (1 nodes): `High-level summary of committed and local dataset coverage.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 42`** (1 nodes): `Return the effective ADVIO provider for one optional serving config.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Test package helpers and suites for PRML VSLAM.` connect `Community 4` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 5`, `Community 6`, `Community 7`, `Community 10`, `Community 13`, `Community 14`, `Community 15`, `Community 17`?**
  _High betweenness centrality (0.145) - this node is a cross-community bridge._
- **Why does `SequenceManifest` connect `Community 6` to `Community 0`, `Community 1`, `Community 2`, `Community 4`, `Community 5`, `Community 7`, `Community 9`, `Community 10`, `Community 11`, `Community 14`, `Community 15`?**
  _High betweenness centrality (0.064) - this node is a cross-community bridge._
- **Why does `StageKey` connect `Community 2` to `Community 0`, `Community 1`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 8`?**
  _High betweenness centrality (0.057) - this node is a cross-community bridge._
- **Are the 536 inferred relationships involving `SequenceManifest` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`SequenceManifest` has 536 INFERRED edges - model-reasoned connections that need verification._
- **Are the 478 inferred relationships involving `PreparedBenchmarkInputs` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`PreparedBenchmarkInputs` has 478 INFERRED edges - model-reasoned connections that need verification._
- **Are the 467 inferred relationships involving `DatasetId` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`DatasetId` has 467 INFERRED edges - model-reasoned connections that need verification._
- **Are the 452 inferred relationships involving `StageKey` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`StageKey` has 452 INFERRED edges - model-reasoned connections that need verification._