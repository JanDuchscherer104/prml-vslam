# Graph Report - prml-vslam  (2026-06-15)

## Corpus Check
- 279 files · ~1,075,353 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4296 nodes · 20204 edges · 32 communities detected
- Extraction: 31% EXTRACTED · 69% INFERRED · 0% AMBIGUOUS · INFERRED: 13974 edges (avg confidence: 0.59)
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
1. `StageKey` - 448 edges
2. `SequenceManifest` - 347 edges
3. `ArtifactRef` - 281 edges
4. `MethodId` - 275 edges
5. `PathConfig` - 252 edges
6. `PreparedBenchmarkInputs` - 248 edges
7. `RunConfig` - 230 edges
8. `StageRuntimeStatus` - 229 edges
9. `ReferenceSource` - 227 edges
10. `FrameTransform` - 183 edges

## Surprising Connections (you probably didn't know these)
- `_forward_rerun_viewer_stdout()` --calls--> `test_forward_rerun_viewer_stdout_prefixes_child_output()`  [INFERRED]
  src/prml_vslam/main.py → tests/test_main.py
- `_forward_rerun_viewer_stdout()` --calls--> `test_forward_rerun_viewer_stdout_uses_current_stdout_by_default()`  [INFERRED]
  src/prml_vslam/main.py → tests/test_main.py
- `plan_run()` --calls--> `test_plan_run_defaults_to_live_viewer()`  [INFERRED]
  src/prml_vslam/main.py → tests/test_main.py
- `GroundAlignmentMetadata` --uses--> `Focused tests for derived ground-plane alignment.`  [INFERRED]
  src/prml_vslam/interfaces/alignment.py → tests/test_ground_alignment.py
- `Open3dTsdfBackendConfig` --calls--> `test_open3d_tsdf_backend_config_defaults_to_expected_method()`  [INFERRED]
  src/prml_vslam/reconstruction/config.py → tests/test_reconstruction.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.01
Nodes (406): Write a raw ADVIO trajectory as a normalized RDF TUM artifact., write_advio_rdf_tum(), resolve_sequence_dir(), load_advio_trajectory(), load_advio_trajectory_rows(), Load an ADVIO trajectory CSV into an `evo` pose trajectory., Load raw numeric ADVIO trajectory rows with timestamp, XYZ, and WXYZ fields., Convert an ADVIO pose CSV into a TUM trajectory file. (+398 more)

### Community 1 - "Community 1"
Cohesion: 0.02
Nodes (349): artifact_visualizations(), ArtifactRef, _entity_token(), observation_sequence_artifact_key(), Artifact-to-visualization mapping for durable stage outputs., Reference one materialized repository artifact by path and fingerprint., Project source output contracts into durable stage artifact refs., Return neutral visualization items for completed durable artifacts. (+341 more)

### Community 2 - "Community 2"
Cohesion: 0.01
Nodes (339): _as_numpy(), _build_lingbot_artifacts(), _decode_pose_predictions(), _extract_dense_prediction_artifacts(), _flatten_depth_points(), _images_chw_to_rgb(), _optional_prediction_map(), _pose_camera_to_world_to_frame_transform() (+331 more)

### Community 3 - "Community 3"
Cohesion: 0.01
Nodes (313): build_advio_page_data(), AdvioDownloadManager, _ensure_directory_parent(), Return the cache directory used for downloaded scene archives., Return one catalog scene by id., Return local availability status for every catalog scene., Download selected ADVIO scenes and extract the requested modalities., advio_basis_metadata() (+305 more)

### Community 4 - "Community 4"
Cohesion: 0.02
Nodes (267): _adapt_checkpoint_state_dict(), _build_artifacts(), _DensePredictionArtifacts, _ensure_uint8_rgb_from_uimg(), _estimate_camera_intrinsics_from_frame(), _expect_lingbot_config(), _InProcessManager, _InProcessValue (+259 more)

### Community 5 - "Community 5"
Cohesion: 0.04
Nodes (228): Trajectory-alignment contracts shared by evaluation and visualization.  Trajecto, Describe how trajectories are aligned before metric computation., State whether an alignment may publish a downstream dense cloud., Persist an explicit trajectory alignment used for diagnostics or metrics., TrajectoryAlignmentArtifact, TrajectoryAlignmentCloudUseStatus, TrajectoryAlignmentMode, BaseConfig (+220 more)

### Community 6 - "Community 6"
Cohesion: 0.02
Nodes (214): handle_advio_preview_action(), load_advio_explorer_sample(), Controller helpers for the ADVIO Streamlit page., Persist the current ADVIO download-form state., Persist the current explorer selection and load its offline sample., Keep persisted preview state aligned with the runtime snapshot., Apply one preview-form action and return an error message when it fails., _scene_rows() (+206 more)

### Community 7 - "Community 7"
Cohesion: 0.04
Nodes (231): MethodId, AppContext, AdvioSourceConfig, Record3DSourceConfig, RunConfig, VideoSourceConfig, caller_namespace(), configure_logging() (+223 more)

### Community 8 - "Community 8"
Cohesion: 0.04
Nodes (134): _is_cuda_oom(), GroundAlignmentMetadata, Result of one derived ground-plane alignment attempt.      When :attr:`applied`, _apply_snapshot_fallbacks(), _candidate_from_root(), _canonical_path_rows(), _derive_slam_artifacts(), discover_run_artifact_roots() (+126 more)

### Community 9 - "Community 9"
Cohesion: 0.02
Nodes (128): Backend boundary between launch surfaces and execution substrates.  This module, Execute, monitor, and tear down pipeline runs.      Implementations own the conc, Start one run and return the stable run identifier.          Args:             r, Request graceful stop for one active run., Return the latest projected metadata view for one run., Return recent runtime events for one run.          Args:             run_id: Sta, Resolve one target transient payload ref into a local array., Release backend-owned runtime resources.          Args:             preserve_loc (+120 more)

### Community 10 - "Community 10"
Cohesion: 0.02
Nodes (192): _cast_aggregator_for_inference(), _extract_checkpoint_state_dict(), _preprocess_images_with_lingbot(), _resolve_model_dtype(), build_advio_comparison_trajectories(), build_crowd_density_figure(), build_local_readiness_figure(), build_scene_attribute_figure() (+184 more)

### Community 11 - "Community 11"
Cohesion: 0.02
Nodes (143): validate_dataset_root(), _ensure_setup_file(), _has_nvcc(), main(), _prepend_existing_paths(), _prepend_path(), Build the optional CUDA RoPE2D extension for the bundled ViSTA-SLAM checkout., Build ViSTA-SLAM's optional cuRoPE2D extension in-place. (+135 more)

### Community 12 - "Community 12"
Cohesion: 0.05
Nodes (105): validate_modalities(), build_coverage_matrix(), build_heatmap_data(), build_leaderboard(), build_per_sequence_table(), CoverageCell, CoverageMatrix, HeatmapData (+97 more)

### Community 13 - "Community 13"
Cohesion: 0.03
Nodes (74): ArxivSourceSpec, download_file(), fetch_pdf(), fetch_tex_source(), from_json(), load_manifest(), main(), normalize_member_path() (+66 more)

### Community 14 - "Community 14"
Cohesion: 0.1
Nodes (30): Return the user-facing reconstruction label., Configure the minimal Open3D TSDF reconstruction backend.      The repo targets, Return the concrete reconstruction backend type., Instantiate the Open3D TSDF backend while ignoring unrelated kwargs., Describe normalized durable outputs from one reconstruction run.      The minima, ReconstructionArtifacts, ReconstructionMethodId, _import_open3d() (+22 more)

### Community 15 - "Community 15"
Cohesion: 0.12
Nodes (33): build_pipeline_snapshot_render_model(), _coerce_int_metric(), _format_latency(), _format_optional_rate(), _format_queue(), _format_resources(), _format_tasks(), _format_throughput() (+25 more)

### Community 16 - "Community 16"
Cohesion: 0.14
Nodes (33): _ancestor_entity_paths(), _component_columns(), _keyed_point_cloud_snapshots(), _latest_live_model_snapshot(), _latest_transform_matrix_before_or_at_log_tick(), load_recording_summary(), main(), _point_cloud_snapshot() (+25 more)

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
Nodes (1): Build one spec from one JSON object.

### Community 21 - "Community 21"
Cohesion: 1.0
Nodes (1): Return the net code-line delta.

### Community 22 - "Community 22"
Cohesion: 1.0
Nodes (1): Return the path that should own this change in reports.

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from a 4x4 homogeneous matrix.

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): Return the human-readable label shown in plan previews.

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): Return whether ``exc`` looks like a transient local Ray connection failure.

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): Return the compact source label used in logs and diagnostics.

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): Return the short user-facing dataset label.

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): Connect to the source and prepare subsequent blocking observation reads.

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): Disconnect or release the source and any owned runtime resources.

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (1): Deserialize one IPC payload back into the target validated model type.

## Knowledge Gaps
- **255 isolated node(s):** `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`, `Build the optional CUDA RoPE2D extension for the bundled ViSTA-SLAM checkout.`, `Build ViSTA-SLAM's optional cuRoPE2D extension in-place.`, `Download arXiv e-print source bundles listed in a JSONL manifest.`, `One manifest entry describing how to fetch arXiv assets.` (+250 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 18`** (2 nodes): `streamlit_app.py`, `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 19`** (2 nodes): `ray.py`, `Ray-specific helpers for future stage runtime deployment.  This module intention`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 20`** (1 nodes): `Build one spec from one JSON object.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (1 nodes): `Return the net code-line delta.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 22`** (1 nodes): `Return the path that should own this change in reports.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (1 nodes): `Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (1 nodes): `Build the shared transform DTO from a 4x4 homogeneous matrix.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (1 nodes): `Return the human-readable label shown in plan previews.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `Return whether ``exc`` looks like a transient local Ray connection failure.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `Return the compact source label used in logs and diagnostics.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `Return the short user-facing dataset label.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `Connect to the source and prepare subsequent blocking observation reads.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `Disconnect or release the source and any owned runtime resources.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `Deserialize one IPC payload back into the target validated model type.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Test package helpers and suites for PRML VSLAM.` connect `Community 3` to `Community 0`, `Community 1`, `Community 2`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 9`, `Community 10`, `Community 11`, `Community 14`?**
  _High betweenness centrality (0.106) - this node is a cross-community bridge._
- **Why does `SequenceManifest` connect `Community 4` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 9`, `Community 11`, `Community 12`?**
  _High betweenness centrality (0.079) - this node is a cross-community bridge._
- **Why does `StageKey` connect `Community 1` to `Community 0`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 9`?**
  _High betweenness centrality (0.077) - this node is a cross-community bridge._
- **Are the 445 inferred relationships involving `StageKey` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`StageKey` has 445 INFERRED edges - model-reasoned connections that need verification._
- **Are the 344 inferred relationships involving `SequenceManifest` (e.g. with `DatasetRunCoverage` and `DatasetEvaluationSelection`) actually correct?**
  _`SequenceManifest` has 344 INFERRED edges - model-reasoned connections that need verification._
- **Are the 277 inferred relationships involving `ArtifactRef` (e.g. with `TrajectoryAlignmentRuntime` and `Bounded runtime adapter for offline reference reconstruction.`) actually correct?**
  _`ArtifactRef` has 277 INFERRED edges - model-reasoned connections that need verification._
- **Are the 272 inferred relationships involving `MethodId` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`MethodId` has 272 INFERRED edges - model-reasoned connections that need verification._