# Graph Report - prml-vslam-2  (2026-07-03)

## Corpus Check
- 332 files · ~2,636,767 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 5505 nodes · 27593 edges · 31 communities detected
- Extraction: 29% EXTRACTED · 71% INFERRED · 0% AMBIGUOUS · INFERRED: 19490 edges (avg confidence: 0.59)
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
1. `SequenceManifest` - 490 edges
2. `StageKey` - 474 edges
3. `PreparedBenchmarkInputs` - 409 edges
4. `DatasetId` - 403 edges
5. `PathConfig` - 322 edges
6. `ReferenceSource` - 310 edges
7. `ArtifactRef` - 304 edges
8. `MethodId` - 298 edges
9. `StageRuntimeStatus` - 280 edges
10. `CameraIntrinsics` - 264 edges

## Surprising Connections (you probably didn't know these)
- `Mast3rSlamBackendConfig` --calls--> `test_mast3r_backend_config_validates_supported_img_size()`  [INFERRED]
  src/prml_vslam/methods/stage/backend_config.py → tests/test_pipeline_config.py
- `Mast3rSlamBackendConfig` --calls--> `test_mast3r_backend_config_match_frac_thresh_override()`  [INFERRED]
  src/prml_vslam/methods/stage/backend_config.py → tests/test_pipeline_config.py
- `load_tum_trajectory()` --calls--> `test_load_tum_trajectory_normalizes_rounded_quaternions()`  [INFERRED]
  src/prml_vslam/utils/geometry.py → tests/test_geometry.py
- `load_tum_trajectory()` --calls--> `test_load_tum_trajectory_can_canonicalize_unsorted_duplicate_timestamps()`  [INFERRED]
  src/prml_vslam/utils/geometry.py → tests/test_geometry.py
- `PathConfig` --calls--> `test_path_config_is_immutable_after_construction()`  [INFERRED]
  src/prml_vslam/utils/path_config.py → tests/test_path_config.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.02
Nodes (510): CloudAlignmentService, Materialize offline point-cloud alignment artifacts before cloud metrics., Return the deterministic point-cloud alignment metadata path., Return the deterministic ICP-refined point-cloud path., GroundAlignmentMetadata, InputArtifactDiagnostics, Inspection helpers for persisted pipeline run artifact roots., One submitted run attempt found in a persisted event log. (+502 more)

### Community 1 - "Community 1"
Cohesion: 0.01
Nodes (519): handle_advio_preview_action(), Controller helpers for the ADVIO Streamlit page., Persist the current ADVIO download-form state., Keep persisted preview state aligned with the runtime snapshot., Apply one preview-form action and return an error message when it fails., sync_advio_download_state(), sync_advio_preview_state(), AdvioEnvironment (+511 more)

### Community 2 - "Community 2"
Cohesion: 0.03
Nodes (497): AdvioFixedpointFitMode, AdvioFixpointSet, ADVIO fixedpoint registration helpers.  The official ADVIO visualization registe, Estimate a no-scale rigid transform from provider RDF world to fixpoints., Apply one fixedpoint registration to a provider RDF trajectory., Crop registered ADVIO trajectories and express them in one GT local frame., Build a frame-labelled camera pose from a matrix., Rigid registration mode selected for one ADVIO provider trajectory. (+489 more)

### Community 3 - "Community 3"
Cohesion: 0.01
Nodes (433): build_advio_comparison_trajectories(), build_advio_page_data(), _scene_rows(), AdvioDownloadManager, _ensure_directory_parent(), Return the cache directory used for downloaded scene archives., Return one catalog scene by id., Return local availability status for every catalog scene. (+425 more)

### Community 4 - "Community 4"
Cohesion: 0.01
Nodes (462): _attempt_rows(), _candidate_label(), _inventory_rows(), _metadata_json(), _path_rows(), _raw_preview_language(), _raw_preview_text(), render() (+454 more)

### Community 5 - "Community 5"
Cohesion: 0.01
Nodes (365): advio_common_start_local_trajectories(), advio_frame_transform_from_pose(), AdvioFixedpointRegistration, apply_advio_fixedpoint_registration(), estimate_advio_fixedpoint_registration(), _estimate_rigid_no_scale(), _gravity_tilt_deg(), _horizontal_span_m() (+357 more)

### Community 6 - "Community 6"
Cohesion: 0.02
Nodes (331): _adapt_checkpoint_state_dict(), _as_numpy(), _build_artifacts(), _build_lingbot_artifacts(), _cast_aggregator_for_inference(), _decode_pose_predictions(), _DensePredictionArtifacts, _ensure_uint8_rgb_from_uimg() (+323 more)

### Community 7 - "Community 7"
Cohesion: 0.01
Nodes (310): _apply_snapshot_fallbacks(), _candidate_from_root(), _canonical_path_rows(), _derive_slam_artifacts(), discover_run_artifact_roots(), _file_inventory(), _format_size(), inspect_run_artifacts() (+302 more)

### Community 8 - "Community 8"
Cohesion: 0.02
Nodes (335): build_crowd_density_figure(), build_local_readiness_figure(), build_scene_attribute_figure(), build_scene_mix_figure(), Plotly figure builders for the ADVIO dataset page., Build a crowd-density composition chart., Build a scene-attribute prevalence chart., Build a stacked venue/environment overview for the catalog. (+327 more)

### Community 9 - "Community 9"
Cohesion: 0.02
Nodes (247): artifact_ref(), _entity_token(), observation_sequence_artifact_key(), Build one stable artifact reference for a materialized path., reference_cloud_artifact_key(), reference_cloud_metadata_artifact_key(), reference_trajectory_artifact_key(), source_artifacts() (+239 more)

### Community 10 - "Community 10"
Cohesion: 0.02
Nodes (97): Replay clock used by dataset and video source streams., Select whether replay follows source timing or returns observations immediately., Apply source-timestamp pacing for real-time replay., Reset the clock baseline for a new replay loop or connection., Sleep until the replay timestamp should be emitted., ReplayClock, ReplayMode, NksrBackendConfig (+89 more)

### Community 11 - "Community 11"
Cohesion: 0.06
Nodes (52): _assert_slug(), build_run_config_from_sweep_item(), _build_run_id(), expand_sweep(), _load_method_template(), _load_slam_stage_from_payload(), _load_slam_stage_from_template(), load_sweep_config() (+44 more)

### Community 12 - "Community 12"
Cohesion: 0.11
Nodes (38): from_error_values(), from_frames(), compute_image_metrics(), l1_error(), l2_error(), _mean_absolute_error(), _mean_squared_error(), peak_signal_noise_ratio() (+30 more)

### Community 13 - "Community 13"
Cohesion: 0.1
Nodes (35): main(), _parse_args(), _preferred_trajectory(), _write_reference_svg(), _write_summary_bar_variants(), _write_summary_csv(), build_dataset_summary_bar_figure(), build_dataset_summary_bar_svg() (+27 more)

### Community 14 - "Community 14"
Cohesion: 0.09
Nodes (25): DataOnlyConfig, InvalidTargetConfig, NestedPayload, PlainPayload, Tests for the shared Pydantic base-model split., Runtime object used to verify default setup behavior., Config whose runtime target is constructed via ``target_type``., Config without a runtime target. (+17 more)

### Community 15 - "Community 15"
Cohesion: 1.0
Nodes (1): Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays

### Community 16 - "Community 16"
Cohesion: 1.0
Nodes (1): Ray-specific helpers for future stage runtime deployment.  This module intention

### Community 17 - "Community 17"
Cohesion: 1.0
Nodes (1): Return the human-readable label shown in plan previews.

### Community 18 - "Community 18"
Cohesion: 1.0
Nodes (1): Return whether ``exc`` looks like a transient local Ray connection failure.

### Community 19 - "Community 19"
Cohesion: 1.0
Nodes (1): Deserialize one IPC payload back into the target validated model type.

### Community 20 - "Community 20"
Cohesion: 1.0
Nodes (1): Return the compact source label used in logs and diagnostics.

### Community 21 - "Community 21"
Cohesion: 1.0
Nodes (1): Return the short user-facing dataset label.

### Community 22 - "Community 22"
Cohesion: 1.0
Nodes (1): Disconnect or release the source and any owned runtime resources.

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from a 4x4 homogeneous matrix.

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): Return the user-facing method label.

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): Build one spec from one JSON object.

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): Return the net code-line delta.

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): Return the path that should own this change in reports.

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): Persist side metadata for one normalized reconstruction output.      PLY geometr

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): Describe normalized durable outputs from one reconstruction run.      The minima

## Knowledge Gaps
- **276 isolated node(s):** `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`, `Frame preprocessing helpers for ViSTA-SLAM.`, `One RGB frame prepared for upstream ViSTA ingestion.`, `Use the exact upstream ViSTA crop-and-resize helper path.`, `Convert one upstream ViSTA array-like payload into a numpy array.` (+271 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 15`** (2 nodes): `streamlit_app.py`, `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 16`** (2 nodes): `ray.py`, `Ray-specific helpers for future stage runtime deployment.  This module intention`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 17`** (1 nodes): `Return the human-readable label shown in plan previews.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 18`** (1 nodes): `Return whether ``exc`` looks like a transient local Ray connection failure.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 19`** (1 nodes): `Deserialize one IPC payload back into the target validated model type.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 20`** (1 nodes): `Return the compact source label used in logs and diagnostics.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (1 nodes): `Return the short user-facing dataset label.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 22`** (1 nodes): `Disconnect or release the source and any owned runtime resources.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (1 nodes): `Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (1 nodes): `Build the shared transform DTO from a 4x4 homogeneous matrix.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (1 nodes): `Return the user-facing method label.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `Build one spec from one JSON object.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `Return the net code-line delta.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `Return the path that should own this change in reports.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `Persist side metadata for one normalized reconstruction output.      PLY geometr`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `Describe normalized durable outputs from one reconstruction run.      The minima`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Test package helpers and suites for PRML VSLAM.` connect `Community 10` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 8`?**
  _High betweenness centrality (0.098) - this node is a cross-community bridge._
- **Why does `StageKey` connect `Community 0` to `Community 1`, `Community 2`, `Community 4`, `Community 6`, `Community 7`, `Community 8`, `Community 9`, `Community 10`?**
  _High betweenness centrality (0.066) - this node is a cross-community bridge._
- **Why does `PathConfig` connect `Community 2` to `Community 0`, `Community 1`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 10`, `Community 13`?**
  _High betweenness centrality (0.060) - this node is a cross-community bridge._
- **Are the 487 inferred relationships involving `SequenceManifest` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`SequenceManifest` has 487 INFERRED edges - model-reasoned connections that need verification._
- **Are the 471 inferred relationships involving `StageKey` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`StageKey` has 471 INFERRED edges - model-reasoned connections that need verification._
- **Are the 404 inferred relationships involving `PreparedBenchmarkInputs` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`PreparedBenchmarkInputs` has 404 INFERRED edges - model-reasoned connections that need verification._
- **Are the 400 inferred relationships involving `DatasetId` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`DatasetId` has 400 INFERRED edges - model-reasoned connections that need verification._