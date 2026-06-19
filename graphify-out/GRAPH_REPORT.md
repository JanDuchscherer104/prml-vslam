# Graph Report - sweeper-pr88-integration  (2026-06-19)

## Corpus Check
- 292 files · ~1,096,616 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4793 nodes · 24270 edges · 30 communities detected
- Extraction: 29% EXTRACTED · 71% INFERRED · 0% AMBIGUOUS · INFERRED: 17273 edges (avg confidence: 0.58)
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

## God Nodes (most connected - your core abstractions)
1. `StageKey` - 497 edges
2. `SequenceManifest` - 480 edges
3. `PreparedBenchmarkInputs` - 382 edges
4. `DatasetId` - 365 edges
5. `PathConfig` - 337 edges
6. `MethodId` - 323 edges
7. `ReferenceSource` - 298 edges
8. `RunConfig` - 295 edges
9. `ArtifactRef` - 281 edges
10. `AdvioSourceConfig` - 248 edges

## Surprising Connections (you probably didn't know these)
- `GroundAlignmentMetadata` --uses--> `Focused tests for derived ground-plane alignment.`  [INFERRED]
  src/prml_vslam/interfaces/alignment.py → tests/test_ground_alignment.py
- `SequenceManifest` --uses--> `Small runtime sources used by focused pipeline smoke tests.`  [INFERRED]
  src/prml_vslam/sources/contracts.py → tests/pipeline_testing_support.py
- `SequenceManifest` --uses--> `Minimal offline source for pipeline smoke tests.`  [INFERRED]
  src/prml_vslam/sources/contracts.py → tests/pipeline_testing_support.py
- `SequenceManifest` --uses--> `Finite in-memory packet stream for streaming smoke tests.`  [INFERRED]
  src/prml_vslam/sources/contracts.py → tests/pipeline_testing_support.py
- `SequenceManifest` --uses--> `Minimal streaming-capable source for pipeline smoke tests.`  [INFERRED]
  src/prml_vslam/sources/contracts.py → tests/pipeline_testing_support.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.02
Nodes (452): GroundAlignmentMetadata, InputArtifactDiagnostics, Inspection helpers for persisted pipeline run artifact roots., One submitted run attempt found in a persisted event log., Structured inspection result for one persisted pipeline run., Discover method-level run roots under the configured artifact directory., Load typed metadata and path inventory for one persisted run root., One selectable persisted method-level run artifact root. (+444 more)

### Community 1 - "Community 1"
Cohesion: 0.01
Nodes (341): load_advio_served_trajectory(), Return the CSV backing one ADVIO pose provider., Load one ADVIO trajectory using the requested serving semantics., Apply one ADVIO serving mode to an already loaded trajectory., Return explicit target/source frame labels for served ADVIO camera poses., resolve_advio_pose_csv_path(), serve_loaded_advio_trajectory(), AdvioOfflineSample (+333 more)

### Community 2 - "Community 2"
Cohesion: 0.02
Nodes (282): _adapt_checkpoint_state_dict(), _as_numpy(), _build_artifacts(), _build_lingbot_artifacts(), _cast_aggregator_for_inference(), _decode_pose_predictions(), _DensePredictionArtifacts, _ensure_uint8_rgb_from_uimg() (+274 more)

### Community 3 - "Community 3"
Cohesion: 0.01
Nodes (342): build_advio_page_data(), handle_advio_preview_action(), _scene_rows(), sync_advio_download_state(), sync_advio_preview_state(), validate_dataset_root(), _attempt_rows(), _candidate_label() (+334 more)

### Community 4 - "Community 4"
Cohesion: 0.02
Nodes (309): Controller helpers for the ADVIO Streamlit page., Persist the current ADVIO download-form state., Keep persisted preview state aligned with the runtime snapshot., Apply one preview-form action and return an error message when it fails., AdvioDownloadManager, _ensure_directory_parent(), Return the cache directory used for downloaded scene archives., Return one catalog scene by id. (+301 more)

### Community 5 - "Community 5"
Cohesion: 0.01
Nodes (278): _apply_snapshot_fallbacks(), _candidate_from_root(), _canonical_path_rows(), _derive_slam_artifacts(), discover_run_artifact_roots(), _file_inventory(), _format_size(), inspect_run_artifacts() (+270 more)

### Community 6 - "Community 6"
Cohesion: 0.02
Nodes (228): AdvioSequenceConfig, AdvioDatasetService, Build the raw ADVIO source used only for normalized-store ingestion., Build the raw ADVIO streaming source used only for normalized-store ingestion., AdvioDownloadManager, BenchmarkInputSource, DatasetServiceBase, load_point_cloud_ply() (+220 more)

### Community 7 - "Community 7"
Cohesion: 0.07
Nodes (256): Resolve an ``advio-XX`` slug into the numeric ADVIO sequence id., MethodId, AdvioSourceConfig, normalized_profile_for_source_config(), Record3DDatasetSourceConfig, RunConfig, _source_reference_cloud_available(), SourceStageConfig (+248 more)

### Community 8 - "Community 8"
Cohesion: 0.03
Nodes (204): BaseConfig, CloudAlignmentStageConfig, CloudEvaluationStageConfig, CloudMetricId, _compile_run_plan(), DenseCloudSelectionConfig, GroundAlignmentStageConfig, Open3dTsdfBackendConfig (+196 more)

### Community 9 - "Community 9"
Cohesion: 0.02
Nodes (171): _coordinator_actor_options(), RayPipelineBackend, Serialize the config to deterministic TOML and optionally persist it., _enter_page(), build_run_config(), _collect_unknown_field_warnings(), config_warnings(), _discriminator_matches() (+163 more)

### Community 10 - "Community 10"
Cohesion: 0.04
Nodes (175): Trajectory-alignment contracts shared by evaluation and visualization.  Trajecto, Describe how trajectories are aligned before metric computation., State whether an alignment may publish a downstream dense cloud., Persist an explicit trajectory alignment used for diagnostics or metrics., TrajectoryAlignmentArtifact, TrajectoryAlignmentCloudUseStatus, TrajectoryAlignmentMode, CloudAlignmentArtifact (+167 more)

### Community 11 - "Community 11"
Cohesion: 0.02
Nodes (169): build_advio_comparison_trajectories(), build_crowd_density_figure(), build_local_readiness_figure(), build_scene_attribute_figure(), build_scene_mix_figure(), Plotly figure builders for the ADVIO dataset page., Build a crowd-density composition chart., Build a scene-attribute prevalence chart. (+161 more)

### Community 12 - "Community 12"
Cohesion: 0.03
Nodes (126): GroundPlaneModel, GroundPlaneVisualizationHint, Alignment result DTOs shared outside the alignment package.  These datamodels de, Dominant ground-plane hypothesis expressed in native ``world`` coordinates., Finite plane-patch geometry ready for visualization consumers., ape_error_colors(), attach_recording_sinks(), augment_viewer_recording_with_ground_plane() (+118 more)

### Community 13 - "Community 13"
Cohesion: 0.04
Nodes (89): ExportRerunEventSink, _artifact(), test_reconstruction_adapter_maps_cloud_and_mesh_artifacts(), test_reconstruction_adapter_maps_cloud_only_artifacts(), _FakeRecordingStream, _keyframe_update(), _payload_ref(), test_create_recording_stream_default_3d_view_uses_keyed_history_geometry() (+81 more)

### Community 14 - "Community 14"
Cohesion: 0.03
Nodes (81): advio_basis_metadata(), advio_basis_provenance(), AdvioBasisMetadata, AdvioRawCoordinateBasis, basis_for_pose_source(), _flatten_matrix(), _pose_matrix(), ADVIO coordinate-basis normalization helpers.  ADVIO replay and benchmark surfac (+73 more)

### Community 15 - "Community 15"
Cohesion: 0.05
Nodes (51): _build_runtime(), test_decode_record3d_wifi_depth_maps_hue_to_depth_range(), test_normalize_record3d_device_address_adds_http_scheme(), test_record3d_wifi_answer_payload_matches_official_demo(), test_record3d_wifi_closed_after_connect_logs_runtime_failure(), test_record3d_wifi_closed_before_track_sets_setup_failure_without_logging(), test_record3d_wifi_disconnect_does_not_raise_when_worker_lingers(), test_record3d_wifi_metadata_failure_is_non_fatal() (+43 more)

### Community 16 - "Community 16"
Cohesion: 0.06
Nodes (44): Replay clock used by dataset and video source streams., Select whether replay follows source timing or returns observations immediately., Apply source-timestamp pacing for real-time replay., Reset the clock baseline for a new replay loop or connection., Sleep until the replay timestamp should be emitted., ReplayClock, ReplayMode, ImageSequenceObservationSource (+36 more)

### Community 17 - "Community 17"
Cohesion: 0.1
Nodes (36): build_pipeline_snapshot_render_model(), _coerce_int_metric(), _format_latency(), _format_optional_rate(), _format_queue(), _format_resources(), _format_tasks(), _format_throughput() (+28 more)

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
Nodes (1): Deserialize one IPC payload back into the target validated model type.

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): Return the human-readable label shown in plan previews.

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): Return whether ``exc`` looks like a transient local Ray connection failure.

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): Build one spec from one JSON object.

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): Return the net code-line delta.

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): Return the path that should own this change in reports.

## Knowledge Gaps
- **265 isolated node(s):** `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`, `Frame preprocessing helpers for ViSTA-SLAM.`, `One RGB frame prepared for upstream ViSTA ingestion.`, `Use the exact upstream ViSTA crop-and-resize helper path.`, `Convert one upstream ViSTA array-like payload into a numpy array.` (+260 more)
  These have ≤1 connection - possible missing edges or undocumented components.
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
- **Thin community `Community 25`** (1 nodes): `Deserialize one IPC payload back into the target validated model type.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `Return the human-readable label shown in plan previews.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `Return whether ``exc`` looks like a transient local Ray connection failure.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `Build one spec from one JSON object.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `Return the net code-line delta.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `Return the path that should own this change in reports.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Test package helpers and suites for PRML VSLAM.` connect `Community 1` to `Community 0`, `Community 2`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 9`, `Community 10`, `Community 11`, `Community 12`, `Community 14`, `Community 16`?**
  _High betweenness centrality (0.112) - this node is a cross-community bridge._
- **Why does `SequenceManifest` connect `Community 1` to `Community 0`, `Community 2`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 9`, `Community 10`?**
  _High betweenness centrality (0.076) - this node is a cross-community bridge._
- **Why does `StageKey` connect `Community 0` to `Community 1`, `Community 2`, `Community 4`, `Community 5`, `Community 7`, `Community 8`, `Community 9`, `Community 10`, `Community 13`, `Community 17`?**
  _High betweenness centrality (0.066) - this node is a cross-community bridge._
- **Are the 494 inferred relationships involving `StageKey` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`StageKey` has 494 INFERRED edges - model-reasoned connections that need verification._
- **Are the 477 inferred relationships involving `SequenceManifest` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`SequenceManifest` has 477 INFERRED edges - model-reasoned connections that need verification._
- **Are the 377 inferred relationships involving `PreparedBenchmarkInputs` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`PreparedBenchmarkInputs` has 377 INFERRED edges - model-reasoned connections that need verification._
- **Are the 362 inferred relationships involving `DatasetId` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`DatasetId` has 362 INFERRED edges - model-reasoned connections that need verification._