# Graph Report - sweeper-pr88-integration  (2026-06-19)

## Corpus Check
- 292 files · ~1,097,086 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4818 nodes · 24622 edges · 30 communities detected
- Extraction: 28% EXTRACTED · 72% INFERRED · 0% AMBIGUOUS · INFERRED: 17617 edges (avg confidence: 0.58)
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

## God Nodes (most connected - your core abstractions)
1. `StageKey` - 497 edges
2. `SequenceManifest` - 480 edges
3. `PreparedBenchmarkInputs` - 382 edges
4. `DatasetId` - 367 edges
5. `PathConfig` - 337 edges
6. `MethodId` - 323 edges
7. `ReferenceSource` - 316 edges
8. `RunConfig` - 313 edges
9. `ArtifactRef` - 281 edges
10. `AdvioSourceConfig` - 266 edges

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
Nodes (485): build_advio_page_data(), _scene_rows(), AdvioDownloadManager, _ensure_directory_parent(), Return the cache directory used for downloaded scene archives., Return one catalog scene by id., Return local availability status for every catalog scene., Download selected ADVIO scenes and extract complete scene payloads. (+477 more)

### Community 1 - "Community 1"
Cohesion: 0.02
Nodes (419): GroundAlignmentMetadata, _apply_snapshot_fallbacks(), _candidate_from_root(), _canonical_path_rows(), _derive_slam_artifacts(), discover_run_artifact_roots(), _file_inventory(), _format_size() (+411 more)

### Community 2 - "Community 2"
Cohesion: 0.01
Nodes (328): _adapt_checkpoint_state_dict(), _as_numpy(), _build_artifacts(), _build_lingbot_artifacts(), _cast_aggregator_for_inference(), _decode_pose_predictions(), _DensePredictionArtifacts, _ensure_uint8_rgb_from_uimg() (+320 more)

### Community 3 - "Community 3"
Cohesion: 0.01
Nodes (294): interpolate_trajectory_poses(), _nearest_timestamp_indices(), ADVIO trajectory interpolation helpers., Interpolate positions and nearest-neighbor rotations at requested timestamps., GroundPlaneModel, GroundPlaneVisualizationHint, Alignment result DTOs shared outside the alignment package.  These datamodels de, Dominant ground-plane hypothesis expressed in native ``world`` coordinates. (+286 more)

### Community 4 - "Community 4"
Cohesion: 0.05
Nodes (332): Trajectory-alignment contracts shared by evaluation and visualization.  Trajecto, Describe how trajectories are aligned before metric computation., State whether an alignment may publish a downstream dense cloud., Persist an explicit trajectory alignment used for diagnostics or metrics., TrajectoryAlignmentArtifact, TrajectoryAlignmentCloudUseStatus, TrajectoryAlignmentMode, MethodId (+324 more)

### Community 5 - "Community 5"
Cohesion: 0.01
Nodes (307): handle_advio_preview_action(), sync_advio_preview_state(), validate_dataset_root(), _attempt_rows(), _candidate_label(), _inventory_rows(), _metadata_json(), _path_rows() (+299 more)

### Community 6 - "Community 6"
Cohesion: 0.01
Nodes (251): BaseConfig, _ConfigFactory, FactoryConfig, from_toml(), _normalize_value(), Shared config and config-as-factory helpers for the repository.  This module own, Render the config as a Rich tree for quick human inspection., Mixin for configs that construct one runtime owner or adapter.      This pattern (+243 more)

### Community 7 - "Community 7"
Cohesion: 0.04
Nodes (235): BaseConfig, AppContext, AdvioSourceConfig, build_run_config(), CloudAlignmentStageConfig, CloudEvaluationStageConfig, CloudMetricId, _collect_unknown_field_warnings() (+227 more)

### Community 8 - "Community 8"
Cohesion: 0.02
Nodes (191): build_advio_comparison_trajectories(), build_crowd_density_figure(), build_local_readiness_figure(), build_scene_attribute_figure(), build_scene_mix_figure(), Plotly figure builders for the ADVIO dataset page., Build a crowd-density composition chart., Build a scene-attribute prevalence chart. (+183 more)

### Community 9 - "Community 9"
Cohesion: 0.03
Nodes (156): Controller helpers for the ADVIO Streamlit page., Persist the current ADVIO download-form state., Keep persisted preview state aligned with the runtime snapshot., Apply one preview-form action and return an error message when it fails., sync_advio_download_state(), Normalize and validate explicit scene selections., Return the canonical ADVIO folder name used on disk., Reject blank dataset roots before path resolution happens downstream. (+148 more)

### Community 10 - "Community 10"
Cohesion: 0.02
Nodes (117): Record3DTransportId, IntEnum, _camera_pose_from_binding(), _device_from_binding(), _import_record3d_module(), _intrinsics_from_binding(), list_record3d_usb_devices(), open_record3d_usb_packet_stream() (+109 more)

### Community 11 - "Community 11"
Cohesion: 0.02
Nodes (153): ArxivSourceSpec, download_file(), fetch_pdf(), fetch_tex_source(), from_json(), load_manifest(), main(), normalize_member_path() (+145 more)

### Community 12 - "Community 12"
Cohesion: 0.03
Nodes (120): config_warnings(), _check_extraction_cache(), materialize_manifest(), Source-owned manifest materialization helpers., Materialize the run-owned source manifest for this source stage., _resolve_timestamps_ns(), _benchmark_artifact_paths(), _cleanup_temporary_entry_root() (+112 more)

### Community 13 - "Community 13"
Cohesion: 0.06
Nodes (91): build_coverage_matrix(), build_heatmap_data(), build_leaderboard(), build_per_sequence_table(), CoverageCell, CoverageMatrix, HeatmapData, LeaderboardRow (+83 more)

### Community 14 - "Community 14"
Cohesion: 0.04
Nodes (58): PipelineBackend, Backend boundary between launch surfaces and execution substrates.  This module, Execute, monitor, and tear down pipeline runs.      Implementations own the conc, _coordinator_actor_options(), Ray-backed backend for plan execution and run attachment.  This module owns subs, Forward a stop request to the named coordinator actor., Fetch the latest projected snapshot from the coordinator actor., Fetch trailing events from the coordinator actor. (+50 more)

### Community 15 - "Community 15"
Cohesion: 0.07
Nodes (45): Replay clock used by dataset and video source streams., Select whether replay follows source timing or returns observations immediately., Apply source-timestamp pacing for real-time replay., Reset the clock baseline for a new replay loop or connection., Sleep until the replay timestamp should be emitted., ReplayClock, ReplayMode, ImageSequenceObservationSource (+37 more)

### Community 16 - "Community 16"
Cohesion: 0.06
Nodes (37): Return the user-facing reconstruction label., Configure the minimal Open3D TSDF reconstruction backend.      The repo targets, Return the concrete reconstruction backend type., Instantiate the Open3D TSDF backend while ignoring unrelated kwargs., DenseCloudEvaluationArtifact, DenseCloudEvaluationSelection, Persist one dense-cloud evaluation result for later review., Describe normalized durable outputs from one reconstruction run.      The minima (+29 more)

### Community 17 - "Community 17"
Cohesion: 0.11
Nodes (36): build_pipeline_snapshot_render_model(), _coerce_int_metric(), _format_latency(), _format_optional_rate(), _format_queue(), _format_resources(), _format_tasks(), _format_throughput() (+28 more)

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
- **265 isolated node(s):** `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`, `Frame preprocessing helpers for ViSTA-SLAM.`, `One RGB frame prepared for upstream ViSTA ingestion.`, `Use the exact upstream ViSTA crop-and-resize helper path.`, `Convert one upstream ViSTA array-like payload into a numpy array.` (+260 more)
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

- **Why does `Test package helpers and suites for PRML VSLAM.` connect `Community 0` to `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 6`, `Community 7`, `Community 8`, `Community 9`, `Community 10`, `Community 13`, `Community 15`, `Community 16`?**
  _High betweenness centrality (0.110) - this node is a cross-community bridge._
- **Why does `StageKey` connect `Community 1` to `Community 0`, `Community 2`, `Community 3`, `Community 4`, `Community 6`, `Community 7`, `Community 9`, `Community 14`?**
  _High betweenness centrality (0.070) - this node is a cross-community bridge._
- **Why does `SequenceManifest` connect `Community 4` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 5`, `Community 6`, `Community 7`, `Community 9`, `Community 10`, `Community 12`, `Community 13`, `Community 16`?**
  _High betweenness centrality (0.065) - this node is a cross-community bridge._
- **Are the 494 inferred relationships involving `StageKey` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`StageKey` has 494 INFERRED edges - model-reasoned connections that need verification._
- **Are the 477 inferred relationships involving `SequenceManifest` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`SequenceManifest` has 477 INFERRED edges - model-reasoned connections that need verification._
- **Are the 377 inferred relationships involving `PreparedBenchmarkInputs` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`PreparedBenchmarkInputs` has 377 INFERRED edges - model-reasoned connections that need verification._
- **Are the 364 inferred relationships involving `DatasetId` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`DatasetId` has 364 INFERRED edges - model-reasoned connections that need verification._