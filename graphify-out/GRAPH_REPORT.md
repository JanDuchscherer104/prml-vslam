# Graph Report - prml-vslam-pr99-update  (2026-06-13)

## Corpus Check
- 277 files · ~1,075,198 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4246 nodes · 19433 edges · 31 communities detected
- Extraction: 32% EXTRACTED · 68% INFERRED · 0% AMBIGUOUS · INFERRED: 13219 edges (avg confidence: 0.59)
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

## God Nodes (most connected - your core abstractions)
1. `StageKey` - 438 edges
2. `SequenceManifest` - 347 edges
3. `ArtifactRef` - 281 edges
4. `MethodId` - 259 edges
5. `PreparedBenchmarkInputs` - 248 edges
6. `PathConfig` - 237 edges
7. `StageRuntimeStatus` - 234 edges
8. `FrameTransform` - 195 edges
9. `RunConfig` - 192 edges
10. `StageRuntimeUpdate` - 191 edges

## Surprising Connections (you probably didn't know these)
- `test_visualization_config_rejects_invalid_decimation_values()` --calls--> `VisualizationConfig`  [INFERRED]
  tests/test_visualization.py → src/prml_vslam/visualization/contracts.py
- `test_open3d_tsdf_backend_config_defaults_to_expected_method()` --calls--> `Open3dTsdfBackendConfig`  [INFERRED]
  tests/test_reconstruction.py → src/prml_vslam/reconstruction/config.py
- `Tests for the minimal reconstruction config and Open3D backend.` --uses--> `OfflineReconstructionBackend`  [INFERRED]
  tests/test_reconstruction.py → src/prml_vslam/reconstruction/protocols.py
- `test_source_materialization_does_not_import_stage_package()` --calls--> `path()`  [INFERRED]
  tests/test_package_exports.py → src/prml_vslam/pipeline/sinks/jsonl.py
- `test_console_logging_config_uses_namespace_highlighter()` --calls--> `configure_logging()`  [INFERRED]
  tests/test_console.py → src/prml_vslam/utils/console.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.02
Nodes (482): _DensePredictionArtifacts, _ensure_uint8_rgb_from_uimg(), _InProcessManager, _InProcessValue, Optional LingBot-Map backend adapter., Estimate model-raster intrinsics from a MASt3R keyframe pointmap., Run LingBot-Map and persist normalized trajectory and dense geometry., Stateful streaming runtime over the upstream MASt3R-SLAM stack. (+474 more)

### Community 1 - "Community 1"
Cohesion: 0.02
Nodes (435): Trajectory-alignment contracts shared by evaluation and visualization.  Trajecto, Describe how trajectories are aligned before metric computation., State whether an alignment may publish a downstream dense cloud., Persist an explicit trajectory alignment used for diagnostics or metrics., TrajectoryAlignmentArtifact, TrajectoryAlignmentCloudUseStatus, TrajectoryAlignmentMode, MethodId (+427 more)

### Community 2 - "Community 2"
Cohesion: 0.01
Nodes (399): _build_artifacts(), interpolate_trajectory_poses(), _nearest_timestamp_indices(), ADVIO trajectory interpolation helpers., Interpolate positions and nearest-neighbor rotations at requested timestamps., validate_dataset_root(), GroundAlignmentMetadata, GroundPlaneModel (+391 more)

### Community 3 - "Community 3"
Cohesion: 0.01
Nodes (325): AdvioDownloadManager, _ensure_directory_parent(), Return the cache directory used for downloaded scene archives., Return one catalog scene by id., Return local availability status for every catalog scene., Download selected ADVIO scenes and extract the requested modalities., advio_basis_metadata(), advio_basis_provenance() (+317 more)

### Community 4 - "Community 4"
Cohesion: 0.01
Nodes (226): _adapt_checkpoint_state_dict(), _as_numpy(), _build_lingbot_artifacts(), _cast_aggregator_for_inference(), _decode_pose_predictions(), _estimate_camera_intrinsics_from_frame(), _expect_lingbot_config(), _extract_checkpoint_state_dict() (+218 more)

### Community 5 - "Community 5"
Cohesion: 0.02
Nodes (167): _attempt_rows(), _candidate_label(), _inventory_rows(), _metadata_json(), _path_rows(), _raw_preview_language(), _raw_preview_text(), render() (+159 more)

### Community 6 - "Community 6"
Cohesion: 0.02
Nodes (209): build_advio_page_data(), handle_advio_preview_action(), load_advio_explorer_sample(), Controller helpers for the ADVIO Streamlit page., Persist the current ADVIO download-form state., Persist the current explorer selection and load its offline sample., Keep persisted preview state aligned with the runtime snapshot., Apply one preview-form action and return an error message when it fails. (+201 more)

### Community 7 - "Community 7"
Cohesion: 0.03
Nodes (180): BaseConfig, AppContext, _advio_native_fps(), build_backend_spec(), build_run_config(), CloudAlignmentStageConfig, CloudEvaluationStageConfig, CloudMetricId (+172 more)

### Community 8 - "Community 8"
Cohesion: 0.02
Nodes (187): build_advio_comparison_trajectories(), build_crowd_density_figure(), build_local_readiness_figure(), build_scene_attribute_figure(), build_scene_mix_figure(), Plotly figure builders for the ADVIO dataset page., Build a crowd-density composition chart., Build a scene-attribute prevalence chart. (+179 more)

### Community 9 - "Community 9"
Cohesion: 0.02
Nodes (159): Render directly via Rich for structured or non-log output., ArxivSourceSpec, download_file(), fetch_pdf(), fetch_tex_source(), from_json(), load_manifest(), main() (+151 more)

### Community 10 - "Community 10"
Cohesion: 0.03
Nodes (83): BaseConfig, _ConfigFactory, FactoryConfig, from_toml(), _normalize_value(), Shared config and config-as-factory helpers for the repository.  This module own, Render the config as a Rich tree for quick human inspection., Mixin for configs that construct one runtime owner or adapter.      This pattern (+75 more)

### Community 11 - "Community 11"
Cohesion: 0.04
Nodes (83): validate_modalities(), _apply_snapshot_fallbacks(), _candidate_from_root(), _canonical_path_rows(), _derive_slam_artifacts(), discover_run_artifact_roots(), _file_inventory(), _format_size() (+75 more)

### Community 12 - "Community 12"
Cohesion: 0.07
Nodes (88): build_coverage_matrix(), build_heatmap_data(), build_leaderboard(), build_per_sequence_table(), CoverageCell, CoverageMatrix, HeatmapData, LeaderboardRow (+80 more)

### Community 13 - "Community 13"
Cohesion: 0.03
Nodes (55): IntEnum, _camera_pose_from_binding(), _device_from_binding(), _import_record3d_module(), _intrinsics_from_binding(), open_record3d_usb_packet_stream(), Disconnect the current USB device if one is active., Wait for the next shared observation emitted by the USB device. (+47 more)

### Community 14 - "Community 14"
Cohesion: 0.07
Nodes (34): Replay clock used by dataset and video source streams., Select whether replay follows source timing or returns observations immediately., Apply source-timestamp pacing for real-time replay., Reset the clock baseline for a new replay loop or connection., Sleep until the replay timestamp should be emitted., ReplayClock, ReplayMode, ImageSequenceObservationSource (+26 more)

### Community 15 - "Community 15"
Cohesion: 0.07
Nodes (17): test_resolve_issue_moves_record_to_resolved_collection(), test_resolve_refactor_moves_record_to_resolved_collection(), test_resolve_todo_moves_record_to_resolved_collection(), _write_toml(), Tests for package-root public export surfaces., test_source_materialization_does_not_import_stage_package(), _FakeBackend, _FakeBackendConfig (+9 more)

### Community 16 - "Community 16"
Cohesion: 0.1
Nodes (35): build_pipeline_snapshot_render_model(), _coerce_int_metric(), _format_latency(), _format_optional_rate(), _format_queue(), _format_resources(), _format_tasks(), _format_throughput() (+27 more)

### Community 17 - "Community 17"
Cohesion: 1.0
Nodes (1): Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays

### Community 18 - "Community 18"
Cohesion: 1.0
Nodes (1): Ray-specific helpers for future stage runtime deployment.  This module intention

### Community 19 - "Community 19"
Cohesion: 1.0
Nodes (1): Deserialize one IPC payload back into the target validated model type.

### Community 20 - "Community 20"
Cohesion: 1.0
Nodes (1): Return the compact source label used in logs and diagnostics.

### Community 21 - "Community 21"
Cohesion: 1.0
Nodes (1): Connect to the source and prepare subsequent blocking observation reads.

### Community 22 - "Community 22"
Cohesion: 1.0
Nodes (1): Disconnect or release the source and any owned runtime resources.

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (1): Return the short user-facing dataset label.

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (1): Return whether ``exc`` looks like a transient local Ray connection failure.

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): Return the human-readable label shown in plan previews.

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from a 4x4 homogeneous matrix.

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): Return the net code-line delta.

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): Return the path that should own this change in reports.

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): Build one spec from one JSON object.

## Knowledge Gaps
- **255 isolated node(s):** `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`, `Tests for ViSTA-native persisted artifact diagnostics.`, `Tests for offline follow-enabled Rerun artifact generation.`, `Tests for reconstruction artifact Plotly figure builders.`, `Tests for centralized repository path handling.` (+250 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 17`** (2 nodes): `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`, `streamlit_app.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 18`** (2 nodes): `Ray-specific helpers for future stage runtime deployment.  This module intention`, `ray.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 19`** (1 nodes): `Deserialize one IPC payload back into the target validated model type.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 20`** (1 nodes): `Return the compact source label used in logs and diagnostics.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (1 nodes): `Connect to the source and prepare subsequent blocking observation reads.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 22`** (1 nodes): `Disconnect or release the source and any owned runtime resources.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (1 nodes): `Return the short user-facing dataset label.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (1 nodes): `Return whether ``exc`` looks like a transient local Ray connection failure.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (1 nodes): `Return the human-readable label shown in plan previews.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `Build the shared transform DTO from a 4x4 homogeneous matrix.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `Return the net code-line delta.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `Return the path that should own this change in reports.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `Build one spec from one JSON object.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Ground-alignment pipeline stage integration.` connect `Community 3` to `Community 0`, `Community 1`, `Community 2`, `Community 4`, `Community 6`, `Community 7`, `Community 8`, `Community 10`, `Community 11`, `Community 13`, `Community 14`?**
  _High betweenness centrality (0.164) - this node is a cross-community bridge._
- **Why does `SequenceManifest` connect `Community 0` to `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 6`, `Community 7`, `Community 11`, `Community 12`, `Community 13`, `Community 15`?**
  _High betweenness centrality (0.073) - this node is a cross-community bridge._
- **Why does `FrameTransform` connect `Community 2` to `Community 0`, `Community 1`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 9`, `Community 11`, `Community 13`, `Community 15`?**
  _High betweenness centrality (0.068) - this node is a cross-community bridge._
- **Are the 435 inferred relationships involving `StageKey` (e.g. with `_FakeRecordingStream` and `Tests for repo-owned streaming Rerun sink behavior.`) actually correct?**
  _`StageKey` has 435 INFERRED edges - model-reasoned connections that need verification._
- **Are the 344 inferred relationships involving `SequenceManifest` (e.g. with `_ManifestOnlySource` and `_BenchmarkSource`) actually correct?**
  _`SequenceManifest` has 344 INFERRED edges - model-reasoned connections that need verification._
- **Are the 277 inferred relationships involving `ArtifactRef` (e.g. with `Focused tests for pipeline integration of the `align.gravity` stage.` and `Tests for repo-owned visualization helpers.`) actually correct?**
  _`ArtifactRef` has 277 INFERRED edges - model-reasoned connections that need verification._
- **Are the 256 inferred relationships involving `MethodId` (e.g. with `Focused tests for pipeline integration of the `align.gravity` stage.` and `_FakeBackendConfig`) actually correct?**
  _`MethodId` has 256 INFERRED edges - model-reasoned connections that need verification._