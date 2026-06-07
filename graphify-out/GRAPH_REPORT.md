# Graph Report - prml-vslam-traj-eval-push  (2026-06-07)

## Corpus Check
- 272 files · ~1,062,167 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4050 nodes · 18404 edges · 32 communities detected
- Extraction: 32% EXTRACTED · 68% INFERRED · 0% AMBIGUOUS · INFERRED: 12537 edges (avg confidence: 0.59)
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

## God Nodes (most connected - your core abstractions)
1. `StageKey` - 439 edges
2. `SequenceManifest` - 315 edges
3. `ArtifactRef` - 272 edges
4. `MethodId` - 248 edges
5. `PreparedBenchmarkInputs` - 242 edges
6. `StageRuntimeStatus` - 231 edges
7. `PathConfig` - 223 edges
8. `RunConfig` - 198 edges
9. `ReferenceSource` - 182 edges
10. `StageRuntimeUpdate` - 182 edges

## Surprising Connections (you probably didn't know these)
- `test_visualization_config_rejects_invalid_decimation_values()` --calls--> `VisualizationConfig`  [INFERRED]
  tests/test_visualization.py → src/prml_vslam/visualization/contracts.py
- `test_open3d_tsdf_backend_config_defaults_to_expected_method()` --calls--> `Open3dTsdfBackendConfig`  [INFERRED]
  tests/test_reconstruction.py → src/prml_vslam/reconstruction/config.py
- `Tests for the minimal reconstruction config and Open3D backend.` --uses--> `OfflineReconstructionBackend`  [INFERRED]
  tests/test_reconstruction.py → src/prml_vslam/reconstruction/protocols.py
- `test_path_config_is_immutable_after_construction()` --calls--> `PathConfig`  [INFERRED]
  tests/test_path_config.py → src/prml_vslam/utils/path_config.py
- `test_source_materialization_does_not_import_stage_package()` --calls--> `path()`  [INFERRED]
  tests/test_package_exports.py → src/prml_vslam/pipeline/sinks/jsonl.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.01
Nodes (379): _build_artifacts(), _estimate_camera_intrinsics_from_frame(), Mast3rSlamSession, interpolate_trajectory_poses(), _nearest_timestamp_indices(), ADVIO trajectory interpolation helpers., Interpolate positions and nearest-neighbor rotations at requested timestamps., GroundAlignmentMetadata (+371 more)

### Community 1 - "Community 1"
Cohesion: 0.02
Nodes (341): _ensure_uint8_rgb_from_uimg(), _InProcessManager, _InProcessValue, Canonical MASt3R-SLAM backend adapter (offline + streaming).  This adapter wraps, Estimate model-raster intrinsics from a MASt3R keyframe pointmap., Stateful streaming runtime over the upstream MASt3R-SLAM stack., Load the upstream runtime and model state needed before the first frame., # NOTE: Upstream calls self._model.share_memory() here for the subprocess (+333 more)

### Community 2 - "Community 2"
Cohesion: 0.01
Nodes (379): validate_dataset_root(), _attempt_rows(), _candidate_label(), _inventory_rows(), _metadata_json(), _path_rows(), _raw_preview_language(), _raw_preview_text() (+371 more)

### Community 3 - "Community 3"
Cohesion: 0.01
Nodes (331): build_advio_page_data(), _scene_rows(), AdvioDownloadManager, _ensure_directory_parent(), Return the cache directory used for downloaded scene archives., Return one catalog scene by id., Return local availability status for every catalog scene., Download selected ADVIO scenes and extract the requested modalities. (+323 more)

### Community 4 - "Community 4"
Cohesion: 0.02
Nodes (287): Return neutral visualization items for completed durable artifacts., VistaSlamBackendConfig, BaseStageRuntime, clean_actor_options(), put_transient_payload(), Shared Ray runtime contracts and helpers., Return the stable Ray actor name for one pipeline run., Store one transient array payload in Ray and return backend-neutral metadata. (+279 more)

### Community 5 - "Community 5"
Cohesion: 0.01
Nodes (284): handle_advio_preview_action(), load_advio_explorer_sample(), Controller helpers for the ADVIO Streamlit page., Persist the current ADVIO download-form state., Persist the current explorer selection and load its offline sample., Keep persisted preview state aligned with the runtime snapshot., Apply one preview-form action and return an error message when it fails., sync_advio_download_state() (+276 more)

### Community 6 - "Community 6"
Cohesion: 0.04
Nodes (262): Trajectory-alignment contracts shared by evaluation and visualization.  Trajecto, Describe how trajectories are aligned before metric computation., State whether an alignment may publish a downstream dense cloud., Persist an explicit trajectory alignment used for diagnostics or metrics., TrajectoryAlignmentArtifact, TrajectoryAlignmentCloudUseStatus, TrajectoryAlignmentMode, MethodId (+254 more)

### Community 7 - "Community 7"
Cohesion: 0.02
Nodes (197): build_advio_comparison_trajectories(), build_crowd_density_figure(), build_local_readiness_figure(), build_scene_attribute_figure(), build_scene_mix_figure(), Plotly figure builders for the ADVIO dataset page., Build a crowd-density composition chart., Build a scene-attribute prevalence chart. (+189 more)

### Community 8 - "Community 8"
Cohesion: 0.03
Nodes (123): BaseConfig, _advio_native_fps(), CloudAlignmentStageConfig, CloudEvaluationStageConfig, CloudMetricId, _collect_unknown_field_warnings(), _compile_run_plan(), DenseCloudSelectionConfig (+115 more)

### Community 9 - "Community 9"
Cohesion: 0.02
Nodes (120): _apply_snapshot_fallbacks(), _candidate_from_root(), _canonical_path_rows(), _derive_slam_artifacts(), discover_run_artifact_roots(), _file_inventory(), _format_size(), inspect_run_artifacts() (+112 more)

### Community 10 - "Community 10"
Cohesion: 0.02
Nodes (122): Render directly via Rich for structured or non-log output., ArxivSourceSpec, download_file(), fetch_pdf(), fetch_tex_source(), from_json(), load_manifest(), main() (+114 more)

### Community 11 - "Community 11"
Cohesion: 0.06
Nodes (43): Mast3rSlamBackend, VistaSlamBackend, build_slam_backend_config(), Persisted SLAM backend config and backend muxing.  The SLAM stage owns the publi, Whether the backend supports repository trajectory evaluation., Return backend-owned default resource hints., Return backend-specific planning notes surfaced to callers., Configure the canonical MASt3R-SLAM backend.      Hyperparameters for tracking / (+35 more)

### Community 12 - "Community 12"
Cohesion: 0.07
Nodes (34): Replay clock used by dataset and video source streams., Select whether replay follows source timing or returns observations immediately., Apply source-timestamp pacing for real-time replay., Reset the clock baseline for a new replay loop or connection., Sleep until the replay timestamp should be emitted., ReplayClock, ReplayMode, ImageSequenceObservationSource (+26 more)

### Community 13 - "Community 13"
Cohesion: 0.09
Nodes (37): validate_modalities(), build_backend_spec(), config_warnings(), iter_sequence_manifest_observations(), _load_manifest_rgb_inputs(), _load_rgb(), _load_timestamps_ns(), _manifest_provenance() (+29 more)

### Community 14 - "Community 14"
Cohesion: 0.12
Nodes (37): test_load_recording_summary_reports_live_keyed_and_tracking_surfaces(), test_write_validation_bundle_emits_report_and_projection_images(), test_write_validation_bundle_respects_explicit_keyed_cloud_limit(), _write_synthetic_recording(), _ancestor_entity_paths(), _component_columns(), _keyed_point_cloud_snapshots(), _latest_live_model_snapshot() (+29 more)

### Community 15 - "Community 15"
Cohesion: 0.12
Nodes (33): build_pipeline_snapshot_render_model(), _coerce_int_metric(), _format_latency(), _format_optional_rate(), _format_queue(), _format_resources(), _format_tasks(), _format_throughput() (+25 more)

### Community 16 - "Community 16"
Cohesion: 0.17
Nodes (2): Tests for package-root public export surfaces., test_source_materialization_does_not_import_stage_package()

### Community 17 - "Community 17"
Cohesion: 0.36
Nodes (4): test_resolve_issue_moves_record_to_resolved_collection(), test_resolve_refactor_moves_record_to_resolved_collection(), test_resolve_todo_moves_record_to_resolved_collection(), _write_toml()

### Community 18 - "Community 18"
Cohesion: 1.0
Nodes (1): Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays

### Community 19 - "Community 19"
Cohesion: 1.0
Nodes (1): Ray-specific helpers for future stage runtime deployment.  This module intention

### Community 20 - "Community 20"
Cohesion: 1.0
Nodes (1): Deserialize one IPC payload back into the target validated model type.

### Community 21 - "Community 21"
Cohesion: 1.0
Nodes (1): Return the compact source label used in logs and diagnostics.

### Community 22 - "Community 22"
Cohesion: 1.0
Nodes (1): Connect to the source and prepare subsequent blocking observation reads.

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (1): Disconnect or release the source and any owned runtime resources.

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (1): Return the short user-facing dataset label.

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): Return whether ``exc`` looks like a transient local Ray connection failure.

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): Return the human-readable label shown in plan previews.

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from a 4x4 homogeneous matrix.

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): Return the net code-line delta.

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): Return the path that should own this change in reports.

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (1): Build one spec from one JSON object.

## Knowledge Gaps
- **251 isolated node(s):** `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`, `Tests for ViSTA-native persisted artifact diagnostics.`, `Tests for offline follow-enabled Rerun artifact generation.`, `Tests for reconstruction artifact Plotly figure builders.`, `Tests for centralized repository path handling.` (+246 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 16`** (12 nodes): `Tests for package-root public export surfaces.`, `test_executable_stage_packages_export_canonical_surfaces()`, `test_interfaces_package_exports_only_canonical_pose_surface()`, `test_methods_package_exports_slam_surfaces()`, `test_pipeline_contracts_package_is_not_a_compatibility_hub()`, `test_pipeline_package_exports_only_minimal_public_surface()`, `test_reconstruction_package_exports_runtime_surfaces_without_harness()`, `test_replay_package_exports_only_replay_primitives()`, `test_source_materialization_does_not_import_stage_package()`, `test_sources_package_exports_source_owned_contracts()`, `test_vista_package_is_the_only_canonical_vista_surface()`, `test_package_exports.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 18`** (2 nodes): `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`, `streamlit_app.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 19`** (2 nodes): `Ray-specific helpers for future stage runtime deployment.  This module intention`, `ray.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 20`** (1 nodes): `Deserialize one IPC payload back into the target validated model type.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (1 nodes): `Return the compact source label used in logs and diagnostics.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 22`** (1 nodes): `Connect to the source and prepare subsequent blocking observation reads.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (1 nodes): `Disconnect or release the source and any owned runtime resources.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (1 nodes): `Return the short user-facing dataset label.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (1 nodes): `Return whether ``exc`` looks like a transient local Ray connection failure.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `Return the human-readable label shown in plan previews.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `Build the shared transform DTO from a 4x4 homogeneous matrix.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `Return the net code-line delta.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `Return the path that should own this change in reports.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `Build one spec from one JSON object.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Ground-alignment pipeline stage integration.` connect `Community 3` to `Community 0`, `Community 1`, `Community 2`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 9`, `Community 11`, `Community 12`?**
  _High betweenness centrality (0.129) - this node is a cross-community bridge._
- **Why does `StageKey` connect `Community 4` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 5`, `Community 6`, `Community 8`, `Community 9`?**
  _High betweenness centrality (0.096) - this node is a cross-community bridge._
- **Why does `SequenceManifest` connect `Community 1` to `Community 0`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 8`, `Community 11`, `Community 13`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **Are the 436 inferred relationships involving `StageKey` (e.g. with `_FakeRecordingStream` and `Focused tests for Rerun layout and modality semantics.`) actually correct?**
  _`StageKey` has 436 INFERRED edges - model-reasoned connections that need verification._
- **Are the 312 inferred relationships involving `SequenceManifest` (e.g. with `_FakeVistaBackend` and `Focused tests for the Ray-backed pipeline core.`) actually correct?**
  _`SequenceManifest` has 312 INFERRED edges - model-reasoned connections that need verification._
- **Are the 268 inferred relationships involving `ArtifactRef` (e.g. with `Tests for repo-owned visualization helpers.` and `_FakeVistaBackend`) actually correct?**
  _`ArtifactRef` has 268 INFERRED edges - model-reasoned connections that need verification._
- **Are the 245 inferred relationships involving `MethodId` (e.g. with `_FakeVistaBackend` and `Focused tests for the Ray-backed pipeline core.`) actually correct?**
  _`MethodId` has 245 INFERRED edges - model-reasoned connections that need verification._