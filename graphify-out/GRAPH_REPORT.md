# Graph Report - agent-tooling-mempalace-graphify  (2026-06-12)

## Corpus Check
- 279 files · ~1,072,418 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4214 nodes · 19112 edges · 33 communities detected
- Extraction: 32% EXTRACTED · 68% INFERRED · 0% AMBIGUOUS · INFERRED: 12991 edges (avg confidence: 0.59)
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

## God Nodes (most connected - your core abstractions)
1. `StageKey` - 434 edges
2. `SequenceManifest` - 347 edges
3. `ArtifactRef` - 281 edges
4. `MethodId` - 259 edges
5. `PreparedBenchmarkInputs` - 248 edges
6. `PathConfig` - 235 edges
7. `StageRuntimeStatus` - 229 edges
8. `RunConfig` - 192 edges
9. `ReferenceSource` - 189 edges
10. `FrameTransform` - 183 edges

## Surprising Connections (you probably didn't know these)
- `plan_run()` --calls--> `test_plan_run_defaults_to_live_viewer()`  [INFERRED]
  src/prml_vslam/main.py → tests/test_main.py
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
Nodes (424): GroundAlignmentMetadata, InputArtifactDiagnostics, Inspection helpers for persisted pipeline run artifact roots., One submitted run attempt found in a persisted event log., Structured inspection result for one persisted pipeline run., Discover method-level run roots under the configured artifact directory., Load typed metadata and path inventory for one persisted run root., One selectable persisted method-level run artifact root. (+416 more)

### Community 1 - "Community 1"
Cohesion: 0.01
Nodes (324): AdvioDownloadManager, _ensure_directory_parent(), Return the cache directory used for downloaded scene archives., Return one catalog scene by id., Return local availability status for every catalog scene., Download selected ADVIO scenes and extract the requested modalities., advio_basis_metadata(), advio_basis_provenance() (+316 more)

### Community 2 - "Community 2"
Cohesion: 0.03
Nodes (332): _DensePredictionArtifacts, _ensure_uint8_rgb_from_uimg(), _estimate_camera_intrinsics_from_frame(), _InProcessManager, _InProcessValue, _LingbotRuntime, Mast3rSlamSession, Canonical MASt3R-SLAM backend adapter (offline + streaming).  This adapter wraps (+324 more)

### Community 3 - "Community 3"
Cohesion: 0.01
Nodes (292): build_advio_comparison_trajectories(), build_crowd_density_figure(), build_local_readiness_figure(), build_scene_attribute_figure(), build_scene_mix_figure(), build_advio_page_data(), handle_advio_preview_action(), load_advio_explorer_sample() (+284 more)

### Community 4 - "Community 4"
Cohesion: 0.01
Nodes (285): GroundPlaneModel, GroundPlaneVisualizationHint, Alignment result DTOs shared outside the alignment package.  These datamodels de, Dominant ground-plane hypothesis expressed in native ``world`` coordinates., Finite plane-patch geometry ready for visualization consumers., Result of one derived ground-plane alignment attempt.      When :attr:`applied`, CameraIntrinsics, CameraIntrinsicsSample (+277 more)

### Community 5 - "Community 5"
Cohesion: 0.01
Nodes (235): _build_artifacts(), resolve(), _apply_snapshot_fallbacks(), _candidate_from_root(), _canonical_path_rows(), _derive_slam_artifacts(), discover_run_artifact_roots(), _file_inventory() (+227 more)

### Community 6 - "Community 6"
Cohesion: 0.02
Nodes (171): _is_cuda_oom(), PipelineBackend, _coordinator_actor_options(), Ray-backed backend for plan execution and run attachment.  This module owns subs, Forward a stop request to the named coordinator actor., Fetch the latest projected snapshot from the coordinator actor., Fetch trailing events from the coordinator actor., Resolve one coordinator-owned target transient payload ref. (+163 more)

### Community 7 - "Community 7"
Cohesion: 0.03
Nodes (233): BaseConfig, AppContext, AdvioSourceConfig, build_run_config(), CloudAlignmentStageConfig, CloudEvaluationStageConfig, CloudMetricId, _compile_run_plan() (+225 more)

### Community 8 - "Community 8"
Cohesion: 0.02
Nodes (228): Controller helpers for the ADVIO Streamlit page., Persist the current ADVIO download-form state., Persist the current explorer selection and load its offline sample., Keep persisted preview state aligned with the runtime snapshot., Apply one preview-form action and return an error message when it fails., _coerce_view_graph(), _coerce_view_graph_node(), load_vista_confidences() (+220 more)

### Community 9 - "Community 9"
Cohesion: 0.02
Nodes (192): _adapt_checkpoint_state_dict(), _as_numpy(), _build_lingbot_artifacts(), _cast_aggregator_for_inference(), _decode_pose_predictions(), _expect_lingbot_config(), _extract_checkpoint_state_dict(), _extract_dense_prediction_artifacts() (+184 more)

### Community 10 - "Community 10"
Cohesion: 0.05
Nodes (115): build_coverage_matrix(), build_heatmap_data(), build_leaderboard(), build_per_sequence_table(), CoverageCell, CoverageMatrix, HeatmapData, LeaderboardRow (+107 more)

### Community 11 - "Community 11"
Cohesion: 0.03
Nodes (88): ArxivSourceSpec, download_file(), fetch_pdf(), fetch_tex_source(), from_json(), load_manifest(), main(), normalize_member_path() (+80 more)

### Community 12 - "Community 12"
Cohesion: 0.03
Nodes (60): IntEnum, build_record3d_frame_details(), _camera_pose_from_binding(), _device_from_binding(), _import_record3d_module(), _intrinsics_from_binding(), list_record3d_usb_devices(), open_record3d_usb_packet_stream() (+52 more)

### Community 13 - "Community 13"
Cohesion: 0.07
Nodes (34): Replay clock used by dataset and video source streams., Select whether replay follows source timing or returns observations immediately., Apply source-timestamp pacing for real-time replay., Reset the clock baseline for a new replay loop or connection., Sleep until the replay timestamp should be emitted., ReplayClock, ReplayMode, ImageSequenceObservationSource (+26 more)

### Community 14 - "Community 14"
Cohesion: 0.08
Nodes (40): validate_modalities(), build_backend_spec(), iter_sequence_manifest_observations(), _load_manifest_rgb_inputs(), _load_rgb(), _load_timestamps_ns(), _manifest_provenance(), Source-owned readers for normalized offline observations. (+32 more)

### Community 15 - "Community 15"
Cohesion: 0.12
Nodes (36): test_load_recording_summary_reports_live_keyed_and_tracking_surfaces(), test_write_validation_bundle_emits_report_and_projection_images(), test_write_validation_bundle_respects_explicit_keyed_cloud_limit(), _ancestor_entity_paths(), _component_columns(), _keyed_point_cloud_snapshots(), _latest_live_model_snapshot(), _latest_transform_matrix_before_or_at_log_tick() (+28 more)

### Community 16 - "Community 16"
Cohesion: 0.12
Nodes (33): build_pipeline_snapshot_render_model(), _coerce_int_metric(), _format_latency(), _format_optional_rate(), _format_queue(), _format_resources(), _format_tasks(), _format_throughput() (+25 more)

### Community 17 - "Community 17"
Cohesion: 0.13
Nodes (18): Return the user-facing reconstruction label., Configure the minimal Open3D TSDF reconstruction backend.      The repo targets, Return the concrete reconstruction backend type., Instantiate the Open3D TSDF backend while ignoring unrelated kwargs., Describe normalized durable outputs from one reconstruction run.      The minima, ReconstructionArtifacts, ReconstructionMethodId, _import_open3d() (+10 more)

### Community 18 - "Community 18"
Cohesion: 0.18
Nodes (2): finish_streaming(), start_streaming()

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
- **255 isolated node(s):** `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`, `Frame preprocessing helpers for ViSTA-SLAM.`, `One RGB frame prepared for upstream ViSTA ingestion.`, `Use the exact upstream ViSTA crop-and-resize helper path.`, `Convert one upstream ViSTA array-like payload into a numpy array.` (+250 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 18`** (12 nodes): `protocols.py`, `protocols.py`, `drain_runtime_updates()`, `drain_streaming_updates()`, `finish_streaming()`, `run_observations()`, `run_offline()`, `start_streaming()`, `status()`, `step_streaming()`, `stop()`, `submit_stream_item()`
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

- **Why does `Test package helpers and suites for PRML VSLAM.` connect `Community 1` to `Community 0`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 7`, `Community 8`, `Community 9`, `Community 12`, `Community 13`, `Community 17`?**
  _High betweenness centrality (0.114) - this node is a cross-community bridge._
- **Why does `StageKey` connect `Community 7` to `Community 0`, `Community 1`, `Community 2`, `Community 5`, `Community 6`, `Community 8`?**
  _High betweenness centrality (0.084) - this node is a cross-community bridge._
- **Why does `SequenceManifest` connect `Community 2` to `Community 0`, `Community 1`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 9`, `Community 10`, `Community 12`, `Community 14`?**
  _High betweenness centrality (0.069) - this node is a cross-community bridge._
- **Are the 431 inferred relationships involving `StageKey` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`StageKey` has 431 INFERRED edges - model-reasoned connections that need verification._
- **Are the 344 inferred relationships involving `SequenceManifest` (e.g. with `OfflineSlamBackend` and `StreamingSlamBackend`) actually correct?**
  _`SequenceManifest` has 344 INFERRED edges - model-reasoned connections that need verification._
- **Are the 277 inferred relationships involving `ArtifactRef` (e.g. with `SlamUpdate` and `SlamArtifacts`) actually correct?**
  _`ArtifactRef` has 277 INFERRED edges - model-reasoned connections that need verification._
- **Are the 256 inferred relationships involving `MethodId` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`MethodId` has 256 INFERRED edges - model-reasoned connections that need verification._