# Graph Report - ralph-rerun-scene-registry  (2026-06-07)

## Corpus Check
- 269 files · ~1,063,321 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4043 nodes · 18851 edges · 32 communities detected
- Extraction: 31% EXTRACTED · 69% INFERRED · 0% AMBIGUOUS · INFERRED: 12988 edges (avg confidence: 0.59)
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
- [[_COMMUNITY_Community 32|Community 32]]

## God Nodes (most connected - your core abstractions)
1. `StageKey` - 439 edges
2. `SequenceManifest` - 314 edges
3. `ArtifactRef` - 273 edges
4. `MethodId` - 259 edges
5. `PreparedBenchmarkInputs` - 241 edges
6. `StageRuntimeStatus` - 231 edges
7. `PathConfig` - 224 edges
8. `RunConfig` - 198 edges
9. `CameraIntrinsics` - 192 edges
10. `DatasetId` - 191 edges

## Surprising Connections (you probably didn't know these)
- `Small runtime sources used by focused pipeline smoke tests.` --uses--> `SequenceManifest`  [INFERRED]
  tests/pipeline_testing_support.py → src/prml_vslam/sources/contracts.py
- `Minimal offline source for pipeline smoke tests.` --uses--> `SequenceManifest`  [INFERRED]
  tests/pipeline_testing_support.py → src/prml_vslam/sources/contracts.py
- `Finite in-memory packet stream for streaming smoke tests.` --uses--> `SequenceManifest`  [INFERRED]
  tests/pipeline_testing_support.py → src/prml_vslam/sources/contracts.py
- `Minimal streaming-capable source for pipeline smoke tests.` --uses--> `SequenceManifest`  [INFERRED]
  tests/pipeline_testing_support.py → src/prml_vslam/sources/contracts.py
- `test_visualization_config_rejects_invalid_decimation_values()` --calls--> `VisualizationConfig`  [INFERRED]
  tests/test_visualization.py → src/prml_vslam/visualization/contracts.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.02
Nodes (419): InputArtifactDiagnostics, Inspection helpers for persisted pipeline run artifact roots., One submitted run attempt found in a persisted event log., Structured inspection result for one persisted pipeline run., Discover method-level run roots under the configured artifact directory., Load typed metadata and path inventory for one persisted run root., One selectable persisted method-level run artifact root., Shallow diagnostics for materialized offline input artifacts. (+411 more)

### Community 1 - "Community 1"
Cohesion: 0.01
Nodes (364): _build_artifacts(), _ensure_uint8_rgb_from_uimg(), _estimate_camera_intrinsics_from_frame(), _InProcessManager, _InProcessValue, Mast3rSlamBackend, Mast3rSlamSession, Canonical MASt3R-SLAM backend adapter (offline + streaming).  This adapter wraps (+356 more)

### Community 2 - "Community 2"
Cohesion: 0.01
Nodes (315): build_advio_page_data(), _scene_rows(), AdvioDownloadManager, _ensure_directory_parent(), Return the cache directory used for downloaded scene archives., Return one catalog scene by id., Return local availability status for every catalog scene., Download selected ADVIO scenes and extract the requested modalities. (+307 more)

### Community 3 - "Community 3"
Cohesion: 0.01
Nodes (316): resolve(), _apply_snapshot_fallbacks(), _candidate_from_root(), _canonical_path_rows(), _derive_slam_artifacts(), discover_run_artifact_roots(), _file_inventory(), _format_size() (+308 more)

### Community 4 - "Community 4"
Cohesion: 0.02
Nodes (358): Return explicit target/source frame labels for served ADVIO camera poses., Return the CSV backing one ADVIO pose provider., Load one ADVIO trajectory using the requested serving semantics., Apply one ADVIO serving mode to an already loaded trajectory., AdvioOfflineSample, AdvioSequencePaths, Build one sequence runtime from its validated config., Materialize benchmark-owned reference trajectories for one sequence. (+350 more)

### Community 5 - "Community 5"
Cohesion: 0.02
Nodes (271): build_advio_comparison_trajectories(), build_crowd_density_figure(), build_local_readiness_figure(), build_scene_attribute_figure(), build_scene_mix_figure(), handle_advio_preview_action(), load_advio_explorer_sample(), Plotly figure builders for the ADVIO dataset page. (+263 more)

### Community 6 - "Community 6"
Cohesion: 0.02
Nodes (178): Controller helpers for the ADVIO Streamlit page., Persist the current ADVIO download-form state., Persist the current explorer selection and load its offline sample., Keep persisted preview state aligned with the runtime snapshot., Apply one preview-form action and return an error message when it fails., sync_advio_download_state(), sync_advio_preview_state(), build_context() (+170 more)

### Community 7 - "Community 7"
Cohesion: 0.03
Nodes (138): BaseConfig, _advio_native_fps(), CloudAlignmentStageConfig, CloudEvaluationStageConfig, CloudMetricId, _collect_unknown_field_warnings(), _compile_run_plan(), config_warnings() (+130 more)

### Community 8 - "Community 8"
Cohesion: 0.05
Nodes (153): Render the persisted run artifact inspector., MethodId, FactoryConfig, Mixin for configs that construct one runtime owner or adapter.      This pattern, Instantiate or build the runtime object described by this config., AppContext, AdvioSourceConfig, Record3DSourceConfig (+145 more)

### Community 9 - "Community 9"
Cohesion: 0.03
Nodes (106): _ape_error_colors(), attach_recording_sinks(), augment_viewer_recording_with_ground_plane(), build_default_blueprint(), create_recording_stream(), _decimate_rows(), _entity_token(), evaluation_metric_root() (+98 more)

### Community 10 - "Community 10"
Cohesion: 0.02
Nodes (122): Render directly via Rich for structured or non-log output., ArxivSourceSpec, download_file(), fetch_pdf(), fetch_tex_source(), from_json(), load_manifest(), main() (+114 more)

### Community 11 - "Community 11"
Cohesion: 0.04
Nodes (97): artifact_ref(), _entity_token(), observation_sequence_artifact_key(), Build one stable artifact reference for a materialized path., reference_cloud_artifact_key(), reference_cloud_metadata_artifact_key(), reference_trajectory_artifact_key(), source_artifacts() (+89 more)

### Community 12 - "Community 12"
Cohesion: 0.05
Nodes (67): _coerce_view_graph(), _coerce_view_graph_node(), load_vista_confidences(), load_vista_estimated_intrinsics_series(), load_vista_intrinsics_matrices(), load_vista_native_trajectory(), load_vista_vector(), load_vista_view_graph() (+59 more)

### Community 13 - "Community 13"
Cohesion: 0.07
Nodes (34): Replay clock used by dataset and video source streams., Select whether replay follows source timing or returns observations immediately., Apply source-timestamp pacing for real-time replay., Reset the clock baseline for a new replay loop or connection., Sleep until the replay timestamp should be emitted., ReplayClock, ReplayMode, ImageSequenceObservationSource (+26 more)

### Community 14 - "Community 14"
Cohesion: 0.11
Nodes (34): build_pipeline_snapshot_render_model(), _coerce_int_metric(), _compute_evo_preview(), _format_latency(), _format_optional_rate(), _format_queue(), _format_resources(), _format_tasks() (+26 more)

### Community 15 - "Community 15"
Cohesion: 0.13
Nodes (27): _add_point_cloud_trace(), _add_trajectory_trace(), _apply_comparison_layout(), _build_figure(), build_reference_reconstruction_figure(), build_slam_reference_comparison_figure(), _combined_bounds(), _decimate_mesh() (+19 more)

### Community 16 - "Community 16"
Cohesion: 0.18
Nodes (2): finish_streaming(), start_streaming()

### Community 17 - "Community 17"
Cohesion: 0.31
Nodes (5): _load_agents_db_module(), test_resolve_issue_moves_record_to_resolved_collection(), test_resolve_refactor_moves_record_to_resolved_collection(), test_resolve_todo_moves_record_to_resolved_collection(), _write_toml()

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
Nodes (1): Connect to the source and prepare subsequent blocking observation reads.

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): Disconnect or release the source and any owned runtime resources.

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): Return the short user-facing dataset label.

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): Deserialize one IPC payload back into the target validated model type.

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): Return the human-readable label shown in plan previews.

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): Return whether ``exc`` looks like a transient local Ray connection failure.

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): Build one spec from one JSON object.

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (1): Return the net code-line delta.

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (1): Return the path that should own this change in reports.

## Knowledge Gaps
- **238 isolated node(s):** `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`, `Frame preprocessing helpers for ViSTA-SLAM.`, `One RGB frame prepared for upstream ViSTA ingestion.`, `Use the exact upstream ViSTA crop-and-resize helper path.`, `Convert one upstream ViSTA array-like payload into a numpy array.` (+233 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 16`** (12 nodes): `protocols.py`, `protocols.py`, `drain_runtime_updates()`, `drain_streaming_updates()`, `finish_streaming()`, `run_observations()`, `run_offline()`, `start_streaming()`, `status()`, `step_streaming()`, `stop()`, `submit_stream_item()`
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
- **Thin community `Community 24`** (1 nodes): `Connect to the source and prepare subsequent blocking observation reads.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (1 nodes): `Disconnect or release the source and any owned runtime resources.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `Return the short user-facing dataset label.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `Deserialize one IPC payload back into the target validated model type.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `Return the human-readable label shown in plan previews.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `Return whether ``exc`` looks like a transient local Ray connection failure.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `Build one spec from one JSON object.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `Return the net code-line delta.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (1 nodes): `Return the path that should own this change in reports.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Test package helpers and suites for PRML VSLAM.` connect `Community 2` to `Community 0`, `Community 1`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 12`, `Community 13`, `Community 15`?**
  _High betweenness centrality (0.144) - this node is a cross-community bridge._
- **Why does `StageKey` connect `Community 0` to `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 6`, `Community 7`, `Community 8`, `Community 9`, `Community 11`?**
  _High betweenness centrality (0.085) - this node is a cross-community bridge._
- **Why does `PathConfig` connect `Community 3` to `Community 0`, `Community 1`, `Community 2`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 8`?**
  _High betweenness centrality (0.062) - this node is a cross-community bridge._
- **Are the 436 inferred relationships involving `StageKey` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`StageKey` has 436 INFERRED edges - model-reasoned connections that need verification._
- **Are the 311 inferred relationships involving `SequenceManifest` (e.g. with `OfflineSlamBackend` and `StreamingSlamBackend`) actually correct?**
  _`SequenceManifest` has 311 INFERRED edges - model-reasoned connections that need verification._
- **Are the 269 inferred relationships involving `ArtifactRef` (e.g. with `SlamUpdate` and `SlamArtifacts`) actually correct?**
  _`ArtifactRef` has 269 INFERRED edges - model-reasoned connections that need verification._
- **Are the 256 inferred relationships involving `MethodId` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`MethodId` has 256 INFERRED edges - model-reasoned connections that need verification._