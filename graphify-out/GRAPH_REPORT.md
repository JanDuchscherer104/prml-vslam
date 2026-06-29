# Graph Report - lingbot-benchmark-sweep-runs  (2026-06-29)

## Corpus Check
- 311 files · ~2,450,539 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 5184 nodes · 25729 edges · 28 communities detected
- Extraction: 30% EXTRACTED · 70% INFERRED · 0% AMBIGUOUS · INFERRED: 18017 edges (avg confidence: 0.59)
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

## God Nodes (most connected - your core abstractions)
1. `SequenceManifest` - 471 edges
2. `StageKey` - 460 edges
3. `PreparedBenchmarkInputs` - 403 edges
4. `DatasetId` - 392 edges
5. `ReferenceSource` - 306 edges
6. `PathConfig` - 306 edges
7. `ArtifactRef` - 296 edges
8. `MethodId` - 291 edges
9. `StageRuntimeStatus` - 269 edges
10. `FrameSelectionConfig` - 251 edges

## Surprising Connections (you probably didn't know these)
- `test_metrics_page_state_preserves_persisted_view_fields()` --calls--> `MetricsPageState`  [INFERRED]
  tests/test_app.py → src/prml_vslam/app/models.py
- `Small runtime sources used by focused pipeline smoke tests.` --uses--> `SequenceManifest`  [INFERRED]
  tests/pipeline_testing_support.py → src/prml_vslam/sources/contracts.py
- `Minimal offline source for pipeline smoke tests.` --uses--> `SequenceManifest`  [INFERRED]
  tests/pipeline_testing_support.py → src/prml_vslam/sources/contracts.py
- `Finite in-memory packet stream for streaming smoke tests.` --uses--> `SequenceManifest`  [INFERRED]
  tests/pipeline_testing_support.py → src/prml_vslam/sources/contracts.py
- `Minimal streaming-capable source for pipeline smoke tests.` --uses--> `SequenceManifest`  [INFERRED]
  tests/pipeline_testing_support.py → src/prml_vslam/sources/contracts.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.02
Nodes (463): InputArtifactDiagnostics, Inspection helpers for persisted pipeline run artifact roots., One submitted run attempt found in a persisted event log., Structured inspection result for one persisted pipeline run., Discover method-level run roots under the configured artifact directory., Load typed metadata and path inventory for one persisted run root., One selectable persisted method-level run artifact root., Shallow diagnostics for materialized offline input artifacts. (+455 more)

### Community 1 - "Community 1"
Cohesion: 0.01
Nodes (509): _pose_camera_to_world_to_frame_transform(), build_advio_comparison_trajectories(), advio_common_start_local_trajectories(), AdvioFixedpointRegistration, apply_advio_fixedpoint_registration(), estimate_advio_fixedpoint_registration(), _estimate_rigid_no_scale(), _gravity_tilt_deg() (+501 more)

### Community 2 - "Community 2"
Cohesion: 0.03
Nodes (471): Controller helpers for the ADVIO Streamlit page., Persist the current ADVIO download-form state., Keep persisted preview state aligned with the runtime snapshot., Apply one preview-form action and return an error message when it fails., AdvioFixedpointFitMode, AdvioFixpointSet, ADVIO fixedpoint registration helpers.  The official ADVIO visualization registe, Estimate a no-scale rigid transform from provider RDF world to fixpoints. (+463 more)

### Community 3 - "Community 3"
Cohesion: 0.01
Nodes (358): AdvioDownloadManager, _ensure_directory_parent(), Return the cache directory used for downloaded scene archives., Return one catalog scene by id., Return local availability status for every catalog scene., Download selected ADVIO scenes and extract complete scene payloads., arcore_ready(), arkit_ready() (+350 more)

### Community 4 - "Community 4"
Cohesion: 0.01
Nodes (343): _adapt_checkpoint_state_dict(), _as_numpy(), _build_artifacts(), _build_lingbot_artifacts(), _cast_aggregator_for_inference(), _decode_pose_predictions(), _DensePredictionArtifacts, _ensure_uint8_rgb_from_uimg() (+335 more)

### Community 5 - "Community 5"
Cohesion: 0.01
Nodes (392): build_advio_page_data(), handle_advio_preview_action(), _scene_rows(), sync_advio_download_state(), sync_advio_preview_state(), _attempt_rows(), _candidate_label(), _inventory_rows() (+384 more)

### Community 6 - "Community 6"
Cohesion: 0.02
Nodes (331): align_estimate_sim3(), CloudAlignmentService, icp_point_cloud_path(), is_gravity_aligned_target(), ICP point-cloud alignment service., Materialize offline point-cloud alignment artifacts before cloud metrics., Refine a trajectory-Sim(3)-aligned cloud against a reference cloud with ICP., Return True when both trajectories have enough geometric spread for Sim(3) align (+323 more)

### Community 7 - "Community 7"
Cohesion: 0.01
Nodes (297): advio_frame_transform_from_pose(), _apply_snapshot_fallbacks(), _candidate_from_root(), _canonical_path_rows(), _derive_slam_artifacts(), discover_run_artifact_roots(), _file_inventory(), _format_size() (+289 more)

### Community 8 - "Community 8"
Cohesion: 0.02
Nodes (207): PipelineBackend, _coordinator_actor_options(), Ray-backed backend for plan execution and run attachment.  This module owns subs, Forward a stop request to the named coordinator actor., Fetch the latest projected snapshot from the coordinator actor., Fetch trailing events from the coordinator actor., Resolve one coordinator-owned target transient payload ref., Detach from Ray and stop any backend-owned shared infrastructure. (+199 more)

### Community 9 - "Community 9"
Cohesion: 0.03
Nodes (186): BaseConfig, CloudAlignmentStageConfig, CloudEvaluationStageConfig, _compile_run_plan(), DenseCloudSelectionConfig, GroundAlignmentStageConfig, Open3dTsdfBackendConfig, _planned_reused_source() (+178 more)

### Community 10 - "Community 10"
Cohesion: 0.02
Nodes (135): build_context(), _build_pages(), _enter_page(), _load_page_module(), Bootstrap helpers for the packaged PRML VSLAM Streamlit app., Typed per-rerun context passed to page renderers., Construct the typed services and persisted state for one rerun., Render the packaged Streamlit application. (+127 more)

### Community 11 - "Community 11"
Cohesion: 0.02
Nodes (178): build_crowd_density_figure(), build_local_readiness_figure(), build_scene_attribute_figure(), build_scene_mix_figure(), Plotly figure builders for the ADVIO dataset page., Build a crowd-density composition chart., Build a scene-attribute prevalence chart., Build a stacked venue/environment overview for the catalog. (+170 more)

### Community 12 - "Community 12"
Cohesion: 0.06
Nodes (40): Replay clock used by dataset and video source streams., Select whether replay follows source timing or returns observations immediately., Apply source-timestamp pacing for real-time replay., Reset the clock baseline for a new replay loop or connection., Sleep until the replay timestamp should be emitted., ReplayClock, ReplayMode, ImageSequenceObservationSource (+32 more)

### Community 13 - "Community 13"
Cohesion: 0.06
Nodes (26): IntEnum, _camera_pose_from_binding(), _device_from_binding(), _import_record3d_module(), _intrinsics_from_binding(), list_record3d_usb_devices(), open_record3d_usb_packet_stream(), Disconnect the current USB device if one is active. (+18 more)

### Community 14 - "Community 14"
Cohesion: 0.08
Nodes (48): PipelineTelemetryMetricId, PipelineTelemetryViewMode, build_pipeline_snapshot_render_model(), _coerce_int_metric(), _format_latency(), _format_optional_rate(), _format_queue(), _format_resources() (+40 more)

### Community 15 - "Community 15"
Cohesion: 1.0
Nodes (1): Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays

### Community 16 - "Community 16"
Cohesion: 1.0
Nodes (1): Ray-specific helpers for future stage runtime deployment.  This module intention

### Community 17 - "Community 17"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.

### Community 18 - "Community 18"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from a 4x4 homogeneous matrix.

### Community 19 - "Community 19"
Cohesion: 1.0
Nodes (1): Return the compact source label used in logs and diagnostics.

### Community 20 - "Community 20"
Cohesion: 1.0
Nodes (1): Disconnect or release the source and any owned runtime resources.

### Community 21 - "Community 21"
Cohesion: 1.0
Nodes (1): Return the short user-facing dataset label.

### Community 22 - "Community 22"
Cohesion: 1.0
Nodes (1): Deserialize one IPC payload back into the target validated model type.

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (1): Return the human-readable label shown in plan previews.

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (1): Return whether ``exc`` looks like a transient local Ray connection failure.

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): Build one spec from one JSON object.

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): Return the net code-line delta.

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): Return the path that should own this change in reports.

## Knowledge Gaps
- **262 isolated node(s):** `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`, `Frame preprocessing helpers for ViSTA-SLAM.`, `One RGB frame prepared for upstream ViSTA ingestion.`, `Use the exact upstream ViSTA crop-and-resize helper path.`, `Convert one upstream ViSTA array-like payload into a numpy array.` (+257 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 15`** (2 nodes): `streamlit_app.py`, `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 16`** (2 nodes): `ray.py`, `Ray-specific helpers for future stage runtime deployment.  This module intention`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 17`** (1 nodes): `Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 18`** (1 nodes): `Build the shared transform DTO from a 4x4 homogeneous matrix.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 19`** (1 nodes): `Return the compact source label used in logs and diagnostics.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 20`** (1 nodes): `Disconnect or release the source and any owned runtime resources.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (1 nodes): `Return the short user-facing dataset label.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 22`** (1 nodes): `Deserialize one IPC payload back into the target validated model type.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (1 nodes): `Return the human-readable label shown in plan previews.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (1 nodes): `Return whether ``exc`` looks like a transient local Ray connection failure.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (1 nodes): `Build one spec from one JSON object.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `Return the net code-line delta.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `Return the path that should own this change in reports.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Test package helpers and suites for PRML VSLAM.` connect `Community 3` to `Community 0`, `Community 1`, `Community 2`, `Community 4`, `Community 6`, `Community 7`, `Community 9`, `Community 10`, `Community 11`, `Community 12`, `Community 13`, `Community 14`?**
  _High betweenness centrality (0.112) - this node is a cross-community bridge._
- **Why does `SequenceManifest` connect `Community 2` to `Community 0`, `Community 1`, `Community 3`, `Community 4`, `Community 6`, `Community 7`, `Community 8`, `Community 9`?**
  _High betweenness centrality (0.055) - this node is a cross-community bridge._
- **Why does `PathConfig` connect `Community 6` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 7`, `Community 8`, `Community 9`, `Community 10`?**
  _High betweenness centrality (0.054) - this node is a cross-community bridge._
- **Are the 468 inferred relationships involving `SequenceManifest` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`SequenceManifest` has 468 INFERRED edges - model-reasoned connections that need verification._
- **Are the 457 inferred relationships involving `StageKey` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`StageKey` has 457 INFERRED edges - model-reasoned connections that need verification._
- **Are the 398 inferred relationships involving `PreparedBenchmarkInputs` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`PreparedBenchmarkInputs` has 398 INFERRED edges - model-reasoned connections that need verification._
- **Are the 389 inferred relationships involving `DatasetId` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`DatasetId` has 389 INFERRED edges - model-reasoned connections that need verification._