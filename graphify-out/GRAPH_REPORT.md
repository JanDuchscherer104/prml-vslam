# Graph Report - runtime-metrics-summary-artifact  (2026-06-28)

## Corpus Check
- 306 files · ~2,091,675 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 5069 nodes · 25000 edges · 30 communities detected
- Extraction: 30% EXTRACTED · 70% INFERRED · 0% AMBIGUOUS · INFERRED: 17485 edges (avg confidence: 0.59)
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
1. `StageKey` - 457 edges
2. `SequenceManifest` - 454 edges
3. `PreparedBenchmarkInputs` - 398 edges
4. `DatasetId` - 382 edges
5. `PathConfig` - 303 edges
6. `ReferenceSource` - 302 edges
7. `ArtifactRef` - 284 edges
8. `MethodId` - 282 edges
9. `StageRuntimeStatus` - 264 edges
10. `FrameSelectionConfig` - 250 edges

## Surprising Connections (you probably didn't know these)
- `test_metrics_page_state_preserves_persisted_view_fields()` --calls--> `MetricsPageState`  [INFERRED]
  tests/test_app.py → src/prml_vslam/app/models.py
- `Focused tests for derived ground-plane alignment.` --uses--> `GroundAlignmentMetadata`  [INFERRED]
  tests/test_ground_alignment.py → src/prml_vslam/interfaces/alignment.py
- `Small runtime sources used by focused pipeline smoke tests.` --uses--> `SequenceManifest`  [INFERRED]
  tests/pipeline_testing_support.py → src/prml_vslam/sources/contracts.py
- `Minimal offline source for pipeline smoke tests.` --uses--> `SequenceManifest`  [INFERRED]
  tests/pipeline_testing_support.py → src/prml_vslam/sources/contracts.py
- `Finite in-memory packet stream for streaming smoke tests.` --uses--> `SequenceManifest`  [INFERRED]
  tests/pipeline_testing_support.py → src/prml_vslam/sources/contracts.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.01
Nodes (552): GroundAlignmentMetadata, InputArtifactDiagnostics, Inspection helpers for persisted pipeline run artifact roots., One submitted run attempt found in a persisted event log., Structured inspection result for one persisted pipeline run., Discover method-level run roots under the configured artifact directory., Load typed metadata and path inventory for one persisted run root., One selectable persisted method-level run artifact root. (+544 more)

### Community 1 - "Community 1"
Cohesion: 0.01
Nodes (521): build_advio_page_data(), _scene_rows(), AdvioDownloadManager, _ensure_directory_parent(), Return local availability status for every catalog scene., arcore_ready(), arkit_ready(), _complete_scene_ready() (+513 more)

### Community 2 - "Community 2"
Cohesion: 0.02
Nodes (497): Return the cache directory used for downloaded scene archives., Return one catalog scene by id., Download selected ADVIO scenes and extract complete scene payloads., advio_common_start_local_trajectories(), advio_frame_transform_from_pose(), AdvioFixedpointFitMode, AdvioFixedpointRegistration, AdvioFixpointSet (+489 more)

### Community 3 - "Community 3"
Cohesion: 0.01
Nodes (358): handle_advio_preview_action(), Controller helpers for the ADVIO Streamlit page., Persist the current ADVIO download-form state., Keep persisted preview state aligned with the runtime snapshot., Apply one preview-form action and return an error message when it fails., sync_advio_download_state(), sync_advio_preview_state(), BaseData (+350 more)

### Community 4 - "Community 4"
Cohesion: 0.02
Nodes (296): _adapt_checkpoint_state_dict(), _as_numpy(), _build_artifacts(), _build_lingbot_artifacts(), _cast_aggregator_for_inference(), _decode_pose_predictions(), _DensePredictionArtifacts, _ensure_uint8_rgb_from_uimg() (+288 more)

### Community 5 - "Community 5"
Cohesion: 0.01
Nodes (291): _apply_snapshot_fallbacks(), _candidate_from_root(), _canonical_path_rows(), _derive_slam_artifacts(), discover_run_artifact_roots(), _file_inventory(), _format_size(), inspect_run_artifacts() (+283 more)

### Community 6 - "Community 6"
Cohesion: 0.01
Nodes (264): align_estimate_sim3(), CloudAlignmentService, icp_point_cloud_path(), is_gravity_aligned_target(), ICP point-cloud alignment service., Materialize offline point-cloud alignment artifacts before cloud metrics., Refine a trajectory-Sim(3)-aligned cloud against a reference cloud with ICP., Return True when both trajectories have enough geometric spread for Sim(3) align (+256 more)

### Community 7 - "Community 7"
Cohesion: 0.02
Nodes (226): build_crowd_density_figure(), build_local_readiness_figure(), build_scene_attribute_figure(), build_scene_mix_figure(), Plotly figure builders for the ADVIO dataset page., Build a crowd-density composition chart., Build a scene-attribute prevalence chart., Build a stacked venue/environment overview for the catalog. (+218 more)

### Community 8 - "Community 8"
Cohesion: 0.03
Nodes (191): BaseConfig, apply_dataset_default_baselines(), CloudAlignmentStageConfig, CloudEvaluationStageConfig, CloudMetricId, _collect_unknown_field_warnings(), _compile_run_plan(), config_warnings() (+183 more)

### Community 9 - "Community 9"
Cohesion: 0.02
Nodes (172): _normalized_entry_timestamps_ns(), Backward-compatible warning alias., _advio_aligned_diagnostic_reference(), _advio_aligned_diagnostic_references(), _advio_reference_source_for_serving(), _benchmark_artifact_paths(), _copy_once(), _copy_path() (+164 more)

### Community 10 - "Community 10"
Cohesion: 0.02
Nodes (169): _ensure_setup_file(), _has_nvcc(), main(), _prepend_existing_paths(), _prepend_path(), Build the optional CUDA RoPE2D extension for the bundled ViSTA-SLAM checkout., Build ViSTA-SLAM's optional cuRoPE2D extension in-place., _resolve_cuda_home() (+161 more)

### Community 11 - "Community 11"
Cohesion: 0.03
Nodes (157): available_metric_keys(), build_coverage_matrix(), build_heatmap_data(), build_leaderboard(), build_per_sequence_table(), _build_rmse_aggregate_rows(), build_wide_metric_rows(), _clean_records() (+149 more)

### Community 12 - "Community 12"
Cohesion: 0.04
Nodes (62): PipelineBackend, _coordinator_actor_options(), Forward a stop request to the named coordinator actor., Fetch the latest projected snapshot from the coordinator actor., Fetch trailing events from the coordinator actor., Resolve one coordinator-owned target transient payload ref., Detach from Ray and stop any backend-owned shared infrastructure., Execute pipeline runs through detached per-run coordinator actors.      The back (+54 more)

### Community 13 - "Community 13"
Cohesion: 0.06
Nodes (49): build_advio_comparison_trajectories(), advio_basis_metadata(), advio_basis_provenance(), basis_for_pose_source(), _flatten_matrix(), _pose_matrix(), rdf_basis_matrix(), transform_advio_trajectory_to_rdf() (+41 more)

### Community 14 - "Community 14"
Cohesion: 0.08
Nodes (37): Replay clock used by dataset and video source streams., Select whether replay follows source timing or returns observations immediately., Apply source-timestamp pacing for real-time replay., Reset the clock baseline for a new replay loop or connection., Sleep until the replay timestamp should be emitted., ReplayClock, ReplayMode, ImageSequenceObservationSource (+29 more)

### Community 15 - "Community 15"
Cohesion: 0.13
Nodes (23): _build_blueprint_command(), create_follow_trajectory_artifact(), default_follow_output_path(), _default_recording_id(), _follow_blueprint_script(), FollowArtifactResult, main(), _merge_command() (+15 more)

### Community 16 - "Community 16"
Cohesion: 0.18
Nodes (22): build_backend_spec(), parse_optional_float(), parse_optional_int(), _advio_record_sequence_id(), _backend_spec_for_method(), _coerce_lingbot_image_size_to_patch_grid(), _optional_path_input(), _path_input() (+14 more)

### Community 17 - "Community 17"
Cohesion: 1.0
Nodes (1): Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays

### Community 18 - "Community 18"
Cohesion: 1.0
Nodes (1): Ray-specific helpers for future stage runtime deployment.  This module intention

### Community 19 - "Community 19"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.

### Community 20 - "Community 20"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from a 4x4 homogeneous matrix.

### Community 21 - "Community 21"
Cohesion: 1.0
Nodes (1): Return the compact source label used in logs and diagnostics.

### Community 22 - "Community 22"
Cohesion: 1.0
Nodes (1): Disconnect or release the source and any owned runtime resources.

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (1): Return the short user-facing dataset label.

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
- **261 isolated node(s):** `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`, `Frame preprocessing helpers for ViSTA-SLAM.`, `One RGB frame prepared for upstream ViSTA ingestion.`, `Use the exact upstream ViSTA crop-and-resize helper path.`, `Convert one upstream ViSTA array-like payload into a numpy array.` (+256 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 17`** (2 nodes): `streamlit_app.py`, `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 18`** (2 nodes): `ray.py`, `Ray-specific helpers for future stage runtime deployment.  This module intention`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 19`** (1 nodes): `Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 20`** (1 nodes): `Build the shared transform DTO from a 4x4 homogeneous matrix.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (1 nodes): `Return the compact source label used in logs and diagnostics.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 22`** (1 nodes): `Disconnect or release the source and any owned runtime resources.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (1 nodes): `Return the short user-facing dataset label.`
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

- **Why does `Test package helpers and suites for PRML VSLAM.` connect `Community 6` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 7`, `Community 8`, `Community 14`?**
  _High betweenness centrality (0.115) - this node is a cross-community bridge._
- **Why does `StageKey` connect `Community 0` to `Community 2`, `Community 3`, `Community 5`, `Community 6`, `Community 8`, `Community 12`?**
  _High betweenness centrality (0.077) - this node is a cross-community bridge._
- **Why does `PathConfig` connect `Community 2` to `Community 0`, `Community 1`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 8`, `Community 11`, `Community 12`?**
  _High betweenness centrality (0.051) - this node is a cross-community bridge._
- **Are the 454 inferred relationships involving `StageKey` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`StageKey` has 454 INFERRED edges - model-reasoned connections that need verification._
- **Are the 451 inferred relationships involving `SequenceManifest` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`SequenceManifest` has 451 INFERRED edges - model-reasoned connections that need verification._
- **Are the 393 inferred relationships involving `PreparedBenchmarkInputs` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`PreparedBenchmarkInputs` has 393 INFERRED edges - model-reasoned connections that need verification._
- **Are the 379 inferred relationships involving `DatasetId` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`DatasetId` has 379 INFERRED edges - model-reasoned connections that need verification._