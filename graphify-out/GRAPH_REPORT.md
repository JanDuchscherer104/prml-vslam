# Graph Report - codex-record3d-only  (2026-06-13)

## Corpus Check
- 284 files · ~1,079,161 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4413 nodes · 20498 edges · 29 communities detected
- Extraction: 32% EXTRACTED · 68% INFERRED · 0% AMBIGUOUS · INFERRED: 13990 edges (avg confidence: 0.59)
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

## God Nodes (most connected - your core abstractions)
1. `StageKey` - 450 edges
2. `SequenceManifest` - 367 edges
3. `DatasetId` - 287 edges
4. `ArtifactRef` - 272 edges
5. `PreparedBenchmarkInputs` - 269 edges
6. `PathConfig` - 268 edges
7. `MethodId` - 266 edges
8. `StageRuntimeStatus` - 240 edges
9. `RunConfig` - 198 edges
10. `ReferenceSource` - 192 edges

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
Nodes (447): GroundAlignmentMetadata, Result of one derived ground-plane alignment attempt.      When :attr:`applied`, InputArtifactDiagnostics, Inspection helpers for persisted pipeline run artifact roots., One submitted run attempt found in a persisted event log., Structured inspection result for one persisted pipeline run., Discover method-level run roots under the configured artifact directory., Load typed metadata and path inventory for one persisted run root. (+439 more)

### Community 1 - "Community 1"
Cohesion: 0.01
Nodes (335): build_advio_page_data(), _scene_rows(), AdvioDownloadManager, _ensure_directory_parent(), Return the cache directory used for downloaded scene archives., Return one catalog scene by id., Return local availability status for every catalog scene., Download selected ADVIO scenes and extract complete scene payloads. (+327 more)

### Community 2 - "Community 2"
Cohesion: 0.01
Nodes (334): GroundPlaneModel, GroundPlaneVisualizationHint, Alignment result DTOs shared outside the alignment package.  These datamodels de, Dominant ground-plane hypothesis expressed in native ``world`` coordinates., Finite plane-patch geometry ready for visualization consumers., artifact_ref(), artifact_visualizations(), Build one stable artifact reference for a materialized path. (+326 more)

### Community 3 - "Community 3"
Cohesion: 0.03
Nodes (342): AdvioOfflineSample, AdvioSequencePaths, Build one sequence runtime from its validated config., Materialize benchmark-owned reference trajectories for one sequence., Emit a GT-aligned variant of one optional reference so it overlays GT.      Uses, Open the canonical ADVIO preview replay stream for one sequence., Resolve an ``advio-XX`` slug into the numeric ADVIO sequence id., Build the ADVIO-backed offline source adapter for one sequence. (+334 more)

### Community 4 - "Community 4"
Cohesion: 0.01
Nodes (330): build_advio_comparison_trajectories(), build_crowd_density_figure(), build_local_readiness_figure(), build_scene_attribute_figure(), build_scene_mix_figure(), handle_advio_preview_action(), load_advio_explorer_sample(), sync_advio_download_state() (+322 more)

### Community 5 - "Community 5"
Cohesion: 0.02
Nodes (265): Controller helpers for the ADVIO Streamlit page., Persist the current ADVIO download-form state., Persist the current explorer selection and load its offline sample., Keep persisted preview state aligned with the runtime snapshot., Apply one preview-form action and return an error message when it fails., build_slam_backend_config(), MethodId, BaseData (+257 more)

### Community 6 - "Community 6"
Cohesion: 0.02
Nodes (239): _apply_snapshot_fallbacks(), _candidate_from_root(), _canonical_path_rows(), _derive_slam_artifacts(), discover_run_artifact_roots(), _file_inventory(), _format_size(), inspect_run_artifacts() (+231 more)

### Community 7 - "Community 7"
Cohesion: 0.02
Nodes (211): _build_artifacts(), _ensure_uint8_rgb_from_uimg(), _estimate_camera_intrinsics_from_frame(), _InProcessManager, _InProcessValue, Mast3rSlamBackend, Mast3rSlamSession, Canonical MASt3R-SLAM backend adapter (offline + streaming).  This adapter wraps (+203 more)

### Community 8 - "Community 8"
Cohesion: 0.03
Nodes (129): BaseConfig, CloudAlignmentStageConfig, CloudEvaluationStageConfig, CloudMetricId, _compile_run_plan(), DenseCloudSelectionConfig, GroundAlignmentStageConfig, Open3dTsdfBackendConfig (+121 more)

### Community 9 - "Community 9"
Cohesion: 0.02
Nodes (154): BaseConfig, _ConfigFactory, FactoryConfig, from_toml(), _normalize_value(), Shared config and config-as-factory helpers for the repository.  This module own, Render the config as a Rich tree for quick human inspection., Mixin for configs that construct one runtime owner or adapter.      This pattern (+146 more)

### Community 10 - "Community 10"
Cohesion: 0.02
Nodes (155): Render directly via Rich for structured or non-log output., ArxivSourceSpec, download_file(), fetch_pdf(), fetch_tex_source(), from_json(), load_manifest(), main() (+147 more)

### Community 11 - "Community 11"
Cohesion: 0.04
Nodes (122): build_coverage_matrix(), build_heatmap_data(), build_leaderboard(), build_per_sequence_table(), CoverageCell, CoverageMatrix, HeatmapData, LeaderboardRow (+114 more)

### Community 12 - "Community 12"
Cohesion: 0.04
Nodes (81): advio_basis_metadata(), advio_basis_provenance(), AdvioBasisMetadata, AdvioRawCoordinateBasis, basis_for_pose_source(), _flatten_matrix(), _pose_matrix(), ADVIO coordinate-basis normalization helpers.  ADVIO replay and benchmark surfac (+73 more)

### Community 13 - "Community 13"
Cohesion: 0.05
Nodes (46): _build_runtime(), test_decode_record3d_wifi_depth_maps_hue_to_depth_range(), test_normalize_record3d_device_address_adds_http_scheme(), test_record3d_wifi_answer_payload_matches_official_demo(), test_record3d_wifi_closed_after_connect_logs_runtime_failure(), test_record3d_wifi_closed_before_track_sets_setup_failure_without_logging(), test_record3d_wifi_disconnect_does_not_raise_when_worker_lingers(), test_record3d_wifi_metadata_failure_is_non_fatal() (+38 more)

### Community 14 - "Community 14"
Cohesion: 0.06
Nodes (57): Write the repository's canonical single-camera intrinsics YAML schema., write_camera_intrinsics_yaml(), _cleanup_temporary_entry_root(), _copy_optional_path(), _copy_path(), _csv_row_count(), _csv_value(), _dedupe_manifest_rgb() (+49 more)

### Community 15 - "Community 15"
Cohesion: 0.08
Nodes (32): Replay clock used by dataset and video source streams., Select whether replay follows source timing or returns observations immediately., Apply source-timestamp pacing for real-time replay., Reset the clock baseline for a new replay loop or connection., Sleep until the replay timestamp should be emitted., ReplayClock, ReplayMode, ImageSequenceObservationSource (+24 more)

### Community 16 - "Community 16"
Cohesion: 0.11
Nodes (33): build_pipeline_snapshot_render_model(), _coerce_int_metric(), _format_latency(), _format_optional_rate(), _format_queue(), _format_resources(), _format_tasks(), _format_throughput() (+25 more)

### Community 18 - "Community 18"
Cohesion: 1.0
Nodes (1): Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays

### Community 19 - "Community 19"
Cohesion: 1.0
Nodes (1): Ray-specific helpers for future stage runtime deployment.  This module intention

### Community 20 - "Community 20"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.

### Community 21 - "Community 21"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from a 4x4 homogeneous matrix.

### Community 22 - "Community 22"
Cohesion: 1.0
Nodes (1): Return the compact source label used in logs and diagnostics.

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (1): Disconnect or release the source and any owned runtime resources.

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (1): Deserialize one IPC payload back into the target validated model type.

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): Return the human-readable label shown in plan previews.

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): Return whether ``exc`` looks like a transient local Ray connection failure.

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): Build one spec from one JSON object.

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): Return the net code-line delta.

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): Return the path that should own this change in reports.

## Knowledge Gaps
- **258 isolated node(s):** `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`, `Frame preprocessing helpers for ViSTA-SLAM.`, `One RGB frame prepared for upstream ViSTA ingestion.`, `Use the exact upstream ViSTA crop-and-resize helper path.`, `Convert one upstream ViSTA array-like payload into a numpy array.` (+253 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 18`** (2 nodes): `streamlit_app.py`, `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 19`** (2 nodes): `ray.py`, `Ray-specific helpers for future stage runtime deployment.  This module intention`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 20`** (1 nodes): `Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (1 nodes): `Build the shared transform DTO from a 4x4 homogeneous matrix.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 22`** (1 nodes): `Return the compact source label used in logs and diagnostics.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (1 nodes): `Disconnect or release the source and any owned runtime resources.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (1 nodes): `Deserialize one IPC payload back into the target validated model type.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (1 nodes): `Return the human-readable label shown in plan previews.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `Return whether ``exc`` looks like a transient local Ray connection failure.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `Build one spec from one JSON object.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `Return the net code-line delta.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `Return the path that should own this change in reports.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Test package helpers and suites for PRML VSLAM.` connect `Community 8` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 7`, `Community 9`, `Community 12`, `Community 15`?**
  _High betweenness centrality (0.120) - this node is a cross-community bridge._
- **Why does `StageKey` connect `Community 0` to `Community 2`, `Community 3`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 9`?**
  _High betweenness centrality (0.076) - this node is a cross-community bridge._
- **Why does `SequenceManifest` connect `Community 3` to `Community 0`, `Community 1`, `Community 2`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 11`?**
  _High betweenness centrality (0.074) - this node is a cross-community bridge._
- **Are the 447 inferred relationships involving `StageKey` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`StageKey` has 447 INFERRED edges - model-reasoned connections that need verification._
- **Are the 364 inferred relationships involving `SequenceManifest` (e.g. with `OfflineSlamBackend` and `StreamingSlamBackend`) actually correct?**
  _`SequenceManifest` has 364 INFERRED edges - model-reasoned connections that need verification._
- **Are the 284 inferred relationships involving `DatasetId` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`DatasetId` has 284 INFERRED edges - model-reasoned connections that need verification._
- **Are the 268 inferred relationships involving `ArtifactRef` (e.g. with `SlamUpdate` and `SlamArtifacts`) actually correct?**
  _`ArtifactRef` has 268 INFERRED edges - model-reasoned connections that need verification._