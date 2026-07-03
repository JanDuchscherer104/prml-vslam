# Graph Report - prml-vslam-2  (2026-07-03)

## Corpus Check
- 332 files · ~2,636,755 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 5495 nodes · 27540 edges · 33 communities detected
- Extraction: 29% EXTRACTED · 71% INFERRED · 0% AMBIGUOUS · INFERRED: 19437 edges (avg confidence: 0.59)
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
- [[_COMMUNITY_Community 33|Community 33]]

## God Nodes (most connected - your core abstractions)
1. `SequenceManifest` - 490 edges
2. `StageKey` - 474 edges
3. `PreparedBenchmarkInputs` - 409 edges
4. `DatasetId` - 403 edges
5. `PathConfig` - 322 edges
6. `ReferenceSource` - 310 edges
7. `ArtifactRef` - 303 edges
8. `MethodId` - 298 edges
9. `StageRuntimeStatus` - 280 edges
10. `CameraIntrinsics` - 264 edges

## Surprising Connections (you probably didn't know these)
- `Mast3rSlamBackendConfig` --calls--> `test_mast3r_backend_config_validates_supported_img_size()`  [INFERRED]
  src/prml_vslam/methods/stage/backend_config.py → tests/test_pipeline_config.py
- `Mast3rSlamBackendConfig` --calls--> `test_mast3r_backend_config_match_frac_thresh_override()`  [INFERRED]
  src/prml_vslam/methods/stage/backend_config.py → tests/test_pipeline_config.py
- `clean_actor_options()` --calls--> `test_clean_actor_options_keeps_nonempty_resources_dict()`  [INFERRED]
  src/prml_vslam/pipeline/ray_runtime/common.py → tests/test_pipeline.py
- `path()` --calls--> `test_source_materialization_does_not_import_stage_package()`  [INFERRED]
  src/prml_vslam/pipeline/sinks/jsonl.py → tests/test_package_exports.py
- `path()` --calls--> `report_path()`  [INFERRED]
  src/prml_vslam/pipeline/sinks/jsonl.py → scripts/loc_stats.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.01
Nodes (547): GroundAlignmentMetadata, Result of one derived ground-plane alignment attempt.      When :attr:`applied`, InputArtifactDiagnostics, Inspection helpers for persisted pipeline run artifact roots., One submitted run attempt found in a persisted event log., Structured inspection result for one persisted pipeline run., Discover method-level run roots under the configured artifact directory., Load typed metadata and path inventory for one persisted run root. (+539 more)

### Community 1 - "Community 1"
Cohesion: 0.01
Nodes (472): build_advio_comparison_trajectories(), AdvioDownloadManager, _ensure_directory_parent(), Return the cache directory used for downloaded scene archives., Return one catalog scene by id., Return local availability status for every catalog scene., Download selected ADVIO scenes and extract complete scene payloads., load_advio_fixpoints() (+464 more)

### Community 2 - "Community 2"
Cohesion: 0.01
Nodes (488): _apply_snapshot_fallbacks(), _candidate_from_root(), _canonical_path_rows(), _derive_slam_artifacts(), discover_run_artifact_roots(), _file_inventory(), _format_size(), inspect_run_artifacts() (+480 more)

### Community 3 - "Community 3"
Cohesion: 0.03
Nodes (472): _DensePredictionArtifacts, _ensure_uint8_rgb_from_uimg(), _estimate_camera_intrinsics_from_frame(), _InProcessManager, _InProcessValue, Mast3rSlamSession, Canonical MASt3R-SLAM backend adapter (offline + streaming).  This adapter wraps, Run LingBot terminal inference and clear streaming state. (+464 more)

### Community 4 - "Community 4"
Cohesion: 0.01
Nodes (355): build_advio_page_data(), handle_advio_preview_action(), Controller helpers for the ADVIO Streamlit page., Persist the current ADVIO download-form state., Keep persisted preview state aligned with the runtime snapshot., Apply one preview-form action and return an error message when it fails., _scene_rows(), sync_advio_download_state() (+347 more)

### Community 5 - "Community 5"
Cohesion: 0.01
Nodes (362): align_estimate_sim3(), is_gravity_aligned_target(), Return True when both trajectories have enough geometric spread for Sim(3) align, Align *estimate* to *reference* via Sim(3) and return the aligned trajectory and, Return the tilt angle in degrees between the transformed and original down-axis,, sim3_up_axis_tilt_deg(), trajectory_supports_sim3(), build_intrinsics_residual_figure() (+354 more)

### Community 6 - "Community 6"
Cohesion: 0.02
Nodes (344): build_crowd_density_figure(), build_local_readiness_figure(), build_scene_attribute_figure(), build_scene_mix_figure(), Plotly figure builders for the ADVIO dataset page., Build a crowd-density composition chart., Build a scene-attribute prevalence chart., Build a stacked venue/environment overview for the catalog. (+336 more)

### Community 7 - "Community 7"
Cohesion: 0.02
Nodes (240): _adapt_checkpoint_state_dict(), _as_numpy(), _build_artifacts(), _build_lingbot_artifacts(), _cast_aggregator_for_inference(), _decode_pose_predictions(), _expect_lingbot_config(), _extract_checkpoint_state_dict() (+232 more)

### Community 8 - "Community 8"
Cohesion: 0.03
Nodes (234): BaseConfig, apply_dataset_default_baselines(), CloudAlignmentStageConfig, CloudEvaluationStageConfig, _collect_unknown_field_warnings(), _compile_run_plan(), config_warnings(), default_trajectory_baseline_for_source() (+226 more)

### Community 9 - "Community 9"
Cohesion: 0.02
Nodes (220): artifact_ref(), artifact_visualizations(), _entity_token(), observation_sequence_artifact_key(), Build one stable artifact reference for a materialized path., reference_cloud_artifact_key(), reference_cloud_metadata_artifact_key(), reference_trajectory_artifact_key() (+212 more)

### Community 10 - "Community 10"
Cohesion: 0.02
Nodes (152): main(), _parse_args(), _preferred_trajectory(), _write_reference_svg(), _write_summary_bar_variants(), _write_summary_csv(), Render directly via Rich for structured or non-log output., build_dataset_summary_bar_figure() (+144 more)

### Community 11 - "Community 11"
Cohesion: 0.02
Nodes (79): GroundPlaneModel, GroundPlaneVisualizationHint, Alignment result DTOs shared outside the alignment package.  These datamodels de, Dominant ground-plane hypothesis expressed in native ``world`` coordinates., Finite plane-patch geometry ready for visualization consumers., GroundAlignmentConfig, Record3DTransportId, _CappedPacketStream (+71 more)

### Community 12 - "Community 12"
Cohesion: 0.04
Nodes (107): advio_common_start_local_trajectories(), advio_frame_transform_from_pose(), AdvioFixedpointRegistration, apply_advio_fixedpoint_registration(), estimate_advio_fixedpoint_registration(), _estimate_rigid_no_scale(), _gravity_tilt_deg(), _horizontal_span_m() (+99 more)

### Community 13 - "Community 13"
Cohesion: 0.05
Nodes (51): Replay clock used by dataset and video source streams., Select whether replay follows source timing or returns observations immediately., Apply source-timestamp pacing for real-time replay., Reset the clock baseline for a new replay loop or connection., Sleep until the replay timestamp should be emitted., ReplayClock, ReplayMode, ImageSequenceObservationSource (+43 more)

### Community 14 - "Community 14"
Cohesion: 0.05
Nodes (64): build_stage_telemetry_figure(), ErrorPlotSeries, pointmap_preview_image(), Build a compact rolling telemetry line chart for one stage metric., Trajectory payload needed by pipeline plot builders., Error-series payload needed by pipeline plot builders., Return a renderable preview image for one pointmap-like preview artifact., TrajectoryPlotSeries (+56 more)

### Community 15 - "Community 15"
Cohesion: 0.12
Nodes (33): build_pipeline_snapshot_render_model(), _coerce_int_metric(), _format_latency(), _format_optional_rate(), _format_queue(), _format_resources(), _format_tasks(), _format_throughput() (+25 more)

### Community 16 - "Community 16"
Cohesion: 0.1
Nodes (21): caller_namespace(), configure_logging(), _ConsoleLogFormatter, _ConsoleLogHighlighter, _display_name(), from_callsite(), get_console(), _qualify_namespace() (+13 more)

### Community 17 - "Community 17"
Cohesion: 0.15
Nodes (2): Tests for package-root public export surfaces., test_source_materialization_does_not_import_stage_package()

### Community 18 - "Community 18"
Cohesion: 0.18
Nodes (2): finish_streaming(), start_streaming()

### Community 19 - "Community 19"
Cohesion: 0.36
Nodes (4): test_resolve_issue_moves_record_to_resolved_collection(), test_resolve_refactor_moves_record_to_resolved_collection(), test_resolve_todo_moves_record_to_resolved_collection(), _write_toml()

### Community 21 - "Community 21"
Cohesion: 1.0
Nodes (1): Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays

### Community 22 - "Community 22"
Cohesion: 1.0
Nodes (1): Ray-specific helpers for future stage runtime deployment.  This module intention

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (1): Return the human-readable label shown in plan previews.

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (1): Return whether ``exc`` looks like a transient local Ray connection failure.

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): Deserialize one IPC payload back into the target validated model type.

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): Return the compact source label used in logs and diagnostics.

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): Return the short user-facing dataset label.

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): Disconnect or release the source and any owned runtime resources.

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from a 4x4 homogeneous matrix.

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (1): Build one spec from one JSON object.

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (1): Return the net code-line delta.

### Community 33 - "Community 33"
Cohesion: 1.0
Nodes (1): Return the path that should own this change in reports.

## Knowledge Gaps
- **274 isolated node(s):** `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`, `Frame preprocessing helpers for ViSTA-SLAM.`, `One RGB frame prepared for upstream ViSTA ingestion.`, `Use the exact upstream ViSTA crop-and-resize helper path.`, `Convert one upstream ViSTA array-like payload into a numpy array.` (+269 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 17`** (13 nodes): `test_package_exports.py`, `Tests for package-root public export surfaces.`, `test_align_root_does_not_reexport_heavy_subpackages()`, `test_executable_stage_packages_export_canonical_surfaces()`, `test_interfaces_package_exports_only_canonical_pose_surface()`, `test_methods_package_exports_slam_surfaces()`, `test_pipeline_contracts_package_is_not_a_compatibility_hub()`, `test_pipeline_package_exports_only_minimal_public_surface()`, `test_reconstruction_package_exports_runtime_surfaces_without_harness()`, `test_replay_package_exports_only_replay_primitives()`, `test_source_materialization_does_not_import_stage_package()`, `test_sources_package_exports_source_owned_contracts()`, `test_vista_package_is_the_only_canonical_vista_surface()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 18`** (12 nodes): `protocols.py`, `protocols.py`, `drain_runtime_updates()`, `drain_streaming_updates()`, `finish_streaming()`, `run_observations()`, `run_offline()`, `start_streaming()`, `status()`, `step_streaming()`, `stop()`, `submit_stream_item()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (2 nodes): `streamlit_app.py`, `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 22`** (2 nodes): `ray.py`, `Ray-specific helpers for future stage runtime deployment.  This module intention`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (1 nodes): `Return the human-readable label shown in plan previews.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (1 nodes): `Return whether ``exc`` looks like a transient local Ray connection failure.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (1 nodes): `Deserialize one IPC payload back into the target validated model type.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `Return the compact source label used in logs and diagnostics.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `Return the short user-facing dataset label.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `Disconnect or release the source and any owned runtime resources.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `Build the shared transform DTO from a 4x4 homogeneous matrix.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `Build one spec from one JSON object.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (1 nodes): `Return the net code-line delta.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 33`** (1 nodes): `Return the path that should own this change in reports.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Test package helpers and suites for PRML VSLAM.` connect `Community 11` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 13`, `Community 14`?**
  _High betweenness centrality (0.102) - this node is a cross-community bridge._
- **Why does `SequenceManifest` connect `Community 3` to `Community 0`, `Community 1`, `Community 2`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 9`, `Community 11`, `Community 12`, `Community 13`?**
  _High betweenness centrality (0.062) - this node is a cross-community bridge._
- **Why does `CameraIntrinsics` connect `Community 3` to `Community 0`, `Community 1`, `Community 2`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 9`, `Community 11`, `Community 12`?**
  _High betweenness centrality (0.061) - this node is a cross-community bridge._
- **Are the 487 inferred relationships involving `SequenceManifest` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`SequenceManifest` has 487 INFERRED edges - model-reasoned connections that need verification._
- **Are the 471 inferred relationships involving `StageKey` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`StageKey` has 471 INFERRED edges - model-reasoned connections that need verification._
- **Are the 404 inferred relationships involving `PreparedBenchmarkInputs` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`PreparedBenchmarkInputs` has 404 INFERRED edges - model-reasoned connections that need verification._
- **Are the 400 inferred relationships involving `DatasetId` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`DatasetId` has 400 INFERRED edges - model-reasoned connections that need verification._