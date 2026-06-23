# Graph Report - normalized-runtime-boundary-fix  (2026-06-23)

## Corpus Check
- 306 files · ~2,089,217 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 5060 nodes · 25232 edges · 27 communities detected
- Extraction: 29% EXTRACTED · 71% INFERRED · 0% AMBIGUOUS · INFERRED: 17811 edges (avg confidence: 0.59)
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

## God Nodes (most connected - your core abstractions)
1. `StageKey` - 471 edges
2. `SequenceManifest` - 467 edges
3. `PreparedBenchmarkInputs` - 399 edges
4. `DatasetId` - 393 edges
5. `ReferenceSource` - 328 edges
6. `PathConfig` - 315 edges
7. `MethodId` - 299 edges
8. `ArtifactRef` - 283 edges
9. `FrameSelectionConfig` - 276 edges
10. `RunConfig` - 249 edges

## Surprising Connections (you probably didn't know these)
- `MetricsPageState` --calls--> `test_metrics_page_state_preserves_persisted_view_fields()`  [INFERRED]
  src/prml_vslam/app/models.py → tests/test_app.py
- `GroundAlignmentMetadata` --uses--> `Focused tests for derived ground-plane alignment.`  [INFERRED]
  src/prml_vslam/interfaces/alignment.py → tests/test_ground_alignment.py
- `PointMap` --calls--> `test_pointmap_contract_rejects_sparse_point_cloud_shape()`  [INFERRED]
  src/prml_vslam/interfaces/geometry.py → tests/test_geometry.py
- `SequenceManifest` --uses--> `Small runtime sources used by focused pipeline smoke tests.`  [INFERRED]
  src/prml_vslam/sources/contracts.py → tests/pipeline_testing_support.py
- `SequenceManifest` --uses--> `Minimal offline source for pipeline smoke tests.`  [INFERRED]
  src/prml_vslam/sources/contracts.py → tests/pipeline_testing_support.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.01
Nodes (549): GroundAlignmentMetadata, Result of one derived ground-plane alignment attempt.      When :attr:`applied`, InputArtifactDiagnostics, Inspection helpers for persisted pipeline run artifact roots., One submitted run attempt found in a persisted event log., Structured inspection result for one persisted pipeline run., Discover method-level run roots under the configured artifact directory., Load typed metadata and path inventory for one persisted run root. (+541 more)

### Community 1 - "Community 1"
Cohesion: 0.01
Nodes (508): _cast_aggregator_for_inference(), _extract_checkpoint_state_dict(), _is_cuda_oom(), _preprocess_image_paths_with_lingbot(), _preprocess_images_with_lingbot(), _resolve_model_dtype(), _apply_snapshot_fallbacks(), _candidate_from_root() (+500 more)

### Community 2 - "Community 2"
Cohesion: 0.01
Nodes (357): build_advio_comparison_trajectories(), AdvioDownloadManager, _ensure_directory_parent(), Return the cache directory used for downloaded scene archives., Return one catalog scene by id., Return local availability status for every catalog scene., Download selected ADVIO scenes and extract complete scene payloads., load_advio_fixpoints() (+349 more)

### Community 3 - "Community 3"
Cohesion: 0.02
Nodes (402): build_advio_page_data(), handle_advio_preview_action(), Controller helpers for the ADVIO Streamlit page., Persist the current ADVIO download-form state., Keep persisted preview state aligned with the runtime snapshot., Apply one preview-form action and return an error message when it fails., _scene_rows(), sync_advio_download_state() (+394 more)

### Community 4 - "Community 4"
Cohesion: 0.04
Nodes (366): AdvioFixedpointFitMode, AdvioFixpointSet, ADVIO fixedpoint registration helpers.  The official ADVIO visualization registe, Estimate a no-scale rigid transform from provider RDF world to fixpoints., Apply one fixedpoint registration to a provider RDF trajectory., Crop registered ADVIO trajectories and express them in one GT local frame., Build a frame-labelled camera pose from a matrix., Rigid registration mode selected for one ADVIO provider trajectory. (+358 more)

### Community 5 - "Community 5"
Cohesion: 0.02
Nodes (270): _adapt_checkpoint_state_dict(), _as_numpy(), _build_artifacts(), _build_lingbot_artifacts(), _decode_pose_predictions(), _DensePredictionArtifacts, _ensure_uint8_rgb_from_uimg(), _estimate_camera_intrinsics_from_frame() (+262 more)

### Community 6 - "Community 6"
Cohesion: 0.01
Nodes (320): build_crowd_density_figure(), build_local_readiness_figure(), build_scene_attribute_figure(), build_scene_mix_figure(), advio_common_start_local_trajectories(), advio_frame_transform_from_pose(), AdvioFixedpointRegistration, apply_advio_fixedpoint_registration() (+312 more)

### Community 7 - "Community 7"
Cohesion: 0.02
Nodes (259): align_estimate_sim3(), CloudAlignmentService, icp_point_cloud_path(), is_gravity_aligned_target(), ICP point-cloud alignment service., Materialize offline point-cloud alignment artifacts before cloud metrics., Refine a trajectory-Sim(3)-aligned cloud against a reference cloud with ICP., Return True when both trajectories have enough geometric spread for Sim(3) align (+251 more)

### Community 8 - "Community 8"
Cohesion: 0.03
Nodes (211): BaseConfig, AdvioNormalizedDatasetBuildSource, NormalizedCadenceConfig, TOML contracts for normalized datastore batch builds., TOML-owned dataset groups for generating normalized datastore entries., Expand grouped dataset settings into per-sequence source configs., Normalize-time frame selection that contributes to datastore identity., Grouped ADVIO normalized-store build settings. (+203 more)

### Community 9 - "Community 9"
Cohesion: 0.02
Nodes (187): _collect_unknown_field_warnings(), config_warnings(), _discriminator_matches(), _expected_source_fps(), _fps_for_duration(), _fps_for_timestamps_ns(), _model_type_for_value(), normalized_profile_for_source_config() (+179 more)

### Community 10 - "Community 10"
Cohesion: 0.02
Nodes (166): artifact_visualizations(), label(), dataset_serving(), frame_stride(), trajectory_convention(), build_pipeline_snapshot_render_model(), _coerce_int_metric(), _format_latency() (+158 more)

### Community 11 - "Community 11"
Cohesion: 0.02
Nodes (130): Record3DTransportId, IntEnum, build_record3d_frame_details(), _camera_pose_from_binding(), _device_from_binding(), _import_record3d_module(), _intrinsics_from_binding(), list_record3d_usb_devices() (+122 more)

### Community 12 - "Community 12"
Cohesion: 0.02
Nodes (122): Render directly via Rich for structured or non-log output., ArxivSourceSpec, download_file(), fetch_pdf(), fetch_tex_source(), from_json(), load_manifest(), main() (+114 more)

### Community 13 - "Community 13"
Cohesion: 0.08
Nodes (37): Replay clock used by dataset and video source streams., Select whether replay follows source timing or returns observations immediately., Apply source-timestamp pacing for real-time replay., Reset the clock baseline for a new replay loop or connection., Sleep until the replay timestamp should be emitted., ReplayClock, ReplayMode, ImageSequenceObservationSource (+29 more)

### Community 14 - "Community 14"
Cohesion: 1.0
Nodes (1): Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays

### Community 15 - "Community 15"
Cohesion: 1.0
Nodes (1): Ray-specific helpers for future stage runtime deployment.  This module intention

### Community 16 - "Community 16"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.

### Community 17 - "Community 17"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from a 4x4 homogeneous matrix.

### Community 18 - "Community 18"
Cohesion: 1.0
Nodes (1): Return the compact source label used in logs and diagnostics.

### Community 19 - "Community 19"
Cohesion: 1.0
Nodes (1): Disconnect or release the source and any owned runtime resources.

### Community 20 - "Community 20"
Cohesion: 1.0
Nodes (1): Return the short user-facing dataset label.

### Community 21 - "Community 21"
Cohesion: 1.0
Nodes (1): Deserialize one IPC payload back into the target validated model type.

### Community 22 - "Community 22"
Cohesion: 1.0
Nodes (1): Return the human-readable label shown in plan previews.

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (1): Return whether ``exc`` looks like a transient local Ray connection failure.

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (1): Build one spec from one JSON object.

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): Return the net code-line delta.

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): Return the path that should own this change in reports.

## Knowledge Gaps
- **262 isolated node(s):** `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`, `Frame preprocessing helpers for ViSTA-SLAM.`, `One RGB frame prepared for upstream ViSTA ingestion.`, `Use the exact upstream ViSTA crop-and-resize helper path.`, `Convert one upstream ViSTA array-like payload into a numpy array.` (+257 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 14`** (2 nodes): `streamlit_app.py`, `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 15`** (2 nodes): `ray.py`, `Ray-specific helpers for future stage runtime deployment.  This module intention`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 16`** (1 nodes): `Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 17`** (1 nodes): `Build the shared transform DTO from a 4x4 homogeneous matrix.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 18`** (1 nodes): `Return the compact source label used in logs and diagnostics.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 19`** (1 nodes): `Disconnect or release the source and any owned runtime resources.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 20`** (1 nodes): `Return the short user-facing dataset label.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (1 nodes): `Deserialize one IPC payload back into the target validated model type.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 22`** (1 nodes): `Return the human-readable label shown in plan previews.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (1 nodes): `Return whether ``exc`` looks like a transient local Ray connection failure.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (1 nodes): `Build one spec from one JSON object.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (1 nodes): `Return the net code-line delta.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `Return the path that should own this change in reports.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Test package helpers and suites for PRML VSLAM.` connect `Community 2` to `Community 0`, `Community 1`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 11`, `Community 13`?**
  _High betweenness centrality (0.119) - this node is a cross-community bridge._
- **Why does `StageKey` connect `Community 0` to `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 8`?**
  _High betweenness centrality (0.081) - this node is a cross-community bridge._
- **Why does `SequenceManifest` connect `Community 4` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 9`, `Community 11`?**
  _High betweenness centrality (0.054) - this node is a cross-community bridge._
- **Are the 468 inferred relationships involving `StageKey` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`StageKey` has 468 INFERRED edges - model-reasoned connections that need verification._
- **Are the 464 inferred relationships involving `SequenceManifest` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`SequenceManifest` has 464 INFERRED edges - model-reasoned connections that need verification._
- **Are the 394 inferred relationships involving `PreparedBenchmarkInputs` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`PreparedBenchmarkInputs` has 394 INFERRED edges - model-reasoned connections that need verification._
- **Are the 390 inferred relationships involving `DatasetId` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`DatasetId` has 390 INFERRED edges - model-reasoned connections that need verification._