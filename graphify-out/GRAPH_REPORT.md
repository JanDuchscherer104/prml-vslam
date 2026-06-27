# Graph Report - prml-vslam  (2026-06-27)

## Corpus Check
- 310 files · ~2,094,851 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 5182 nodes · 26231 edges · 34 communities detected
- Extraction: 29% EXTRACTED · 71% INFERRED · 0% AMBIGUOUS · INFERRED: 18584 edges (avg confidence: 0.59)
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
- [[_COMMUNITY_Community 33|Community 33]]

## God Nodes (most connected - your core abstractions)
1. `SequenceManifest` - 501 edges
2. `StageKey` - 469 edges
3. `PreparedBenchmarkInputs` - 435 edges
4. `DatasetId` - 426 edges
5. `ReferenceSource` - 337 edges
6. `PathConfig` - 303 edges
7. `MethodId` - 302 edges
8. `ArtifactRef` - 293 edges
9. `FrameSelectionConfig` - 272 edges
10. `StageRuntimeStatus` - 242 edges

## Surprising Connections (you probably didn't know these)
- `VisualizationConfig` --calls--> `test_visualization_config_rejects_invalid_decimation_values()`  [INFERRED]
  src/prml_vslam/visualization/contracts.py → tests/test_visualization.py
- `MetricsPageState` --calls--> `test_metrics_page_state_preserves_persisted_view_fields()`  [INFERRED]
  src/prml_vslam/app/models.py → tests/test_app.py
- `path()` --calls--> `test_advio_summary_reports_normalized_entries_and_native_cache()`  [INFERRED]
  src/prml_vslam/pipeline/sinks/jsonl.py → tests/test_cli.py
- `path()` --calls--> `test_dataset_normalize_defaults_to_all_local_sequences_and_cpu_workers()`  [INFERRED]
  src/prml_vslam/pipeline/sinks/jsonl.py → tests/test_cli.py
- `path()` --calls--> `test_dataset_normalize_advio_defaults_to_15_fps()`  [INFERRED]
  src/prml_vslam/pipeline/sinks/jsonl.py → tests/test_cli.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.02
Nodes (413): InputArtifactDiagnostics, Inspection helpers for persisted pipeline run artifact roots., One submitted run attempt found in a persisted event log., Structured inspection result for one persisted pipeline run., Discover method-level run roots under the configured artifact directory., Load typed metadata and path inventory for one persisted run root., One selectable persisted method-level run artifact root., Shallow diagnostics for materialized offline input artifacts. (+405 more)

### Community 1 - "Community 1"
Cohesion: 0.01
Nodes (358): build_advio_comparison_trajectories(), build_advio_page_data(), _scene_rows(), AdvioDownloadManager, _ensure_directory_parent(), Return the cache directory used for downloaded scene archives., Return one catalog scene by id., Return local availability status for every catalog scene. (+350 more)

### Community 2 - "Community 2"
Cohesion: 0.01
Nodes (411): apply_advio_fixedpoint_registration(), GroundAlignmentMetadata, GroundPlaneModel, GroundPlaneVisualizationHint, Alignment result DTOs shared outside the alignment package.  These datamodels de, Dominant ground-plane hypothesis expressed in native ``world`` coordinates., Finite plane-patch geometry ready for visualization consumers., Result of one derived ground-plane alignment attempt.      When :attr:`applied` (+403 more)

### Community 3 - "Community 3"
Cohesion: 0.01
Nodes (331): AdvioCalibration, _expect_float_list(), _expect_mapping(), _expect_matrix(), _extract_camera_mapping(), load_advio_calibration(), load_advio_trajectory_rows(), Load raw numeric ADVIO trajectory rows with timestamp, XYZ, and WXYZ fields. (+323 more)

### Community 4 - "Community 4"
Cohesion: 0.02
Nodes (356): handle_advio_preview_action(), Controller helpers for the ADVIO Streamlit page., Persist the current ADVIO download-form state., Keep persisted preview state aligned with the runtime snapshot., Apply one preview-form action and return an error message when it fails., sync_advio_download_state(), sync_advio_preview_state(), AppContext (+348 more)

### Community 5 - "Community 5"
Cohesion: 0.02
Nodes (349): build_crowd_density_figure(), build_local_readiness_figure(), build_scene_attribute_figure(), build_scene_mix_figure(), Plotly figure builders for the ADVIO dataset page., Build a crowd-density composition chart., Build a scene-attribute prevalence chart., Build a stacked venue/environment overview for the catalog. (+341 more)

### Community 6 - "Community 6"
Cohesion: 0.02
Nodes (296): _adapt_checkpoint_state_dict(), _as_numpy(), _build_artifacts(), _build_lingbot_artifacts(), _cast_aggregator_for_inference(), _decode_pose_predictions(), _DensePredictionArtifacts, _ensure_uint8_rgb_from_uimg() (+288 more)

### Community 7 - "Community 7"
Cohesion: 0.01
Nodes (300): resolve(), BaseConfig, _ConfigFactory, FactoryConfig, from_toml(), _normalize_value(), Shared config and config-as-factory helpers for the repository.  This module own, Render the config as a Rich tree for quick human inspection. (+292 more)

### Community 8 - "Community 8"
Cohesion: 0.04
Nodes (316): MethodId, PipelineBackend, Execute, monitor, and tear down pipeline runs.      Implementations own the conc, Start one run and return the stable run identifier.          Args:             r, Request graceful stop for one active run., Return the latest projected metadata view for one run., Return recent runtime events for one run.          Args:             run_id: Sta, Resolve one target transient payload ref into a local array. (+308 more)

### Community 9 - "Community 9"
Cohesion: 0.04
Nodes (283): advio_common_start_local_trajectories(), AdvioFixedpointFitMode, AdvioFixedpointRegistration, AdvioFixpointSet, estimate_advio_fixedpoint_registration(), _estimate_rigid_no_scale(), _gravity_tilt_deg(), _horizontal_span_m() (+275 more)

### Community 10 - "Community 10"
Cohesion: 0.02
Nodes (165): Render directly via Rich for structured or non-log output., Pretty-print a Python object with Rich., ArxivSourceSpec, download_file(), fetch_pdf(), fetch_tex_source(), from_json(), load_manifest() (+157 more)

### Community 11 - "Community 11"
Cohesion: 0.03
Nodes (109): advio_frame_transform_from_pose(), apply_dataset_default_baselines(), _collect_unknown_field_warnings(), config_warnings(), default_trajectory_baseline_for_source(), _discriminator_matches(), _expected_source_fps(), _fps_for_duration() (+101 more)

### Community 12 - "Community 12"
Cohesion: 0.04
Nodes (80): iter_sequence_manifest_observations(), _load_manifest_rgb_inputs(), _load_observation_index_rgb_inputs(), _load_rgb(), _load_rgb_input(), _load_source_frame_indices(), _load_timestamps_ns(), _manifest_provenance() (+72 more)

### Community 13 - "Community 13"
Cohesion: 0.04
Nodes (46): Record3DTransportId, _CappedPacketStream, _CappedStreamingSource, IntEnum, ObservationStream, build_record3d_frame_details(), _camera_pose_from_binding(), _device_from_binding() (+38 more)

### Community 14 - "Community 14"
Cohesion: 0.07
Nodes (48): plan_sweep_config(), _assert_slug(), build_run_config_from_sweep_item(), _build_run_id(), expand_sweep(), _load_slam_stage_from_template(), load_sweep_config(), _load_toml_payload() (+40 more)

### Community 15 - "Community 15"
Cohesion: 0.05
Nodes (43): Provide the package-local runtime contract shared by reconstruction configs., Return the user-facing reconstruction label., Configure the minimal Open3D TSDF reconstruction backend.      The repo targets, Return the concrete reconstruction backend type., Instantiate the Open3D TSDF backend while ignoring unrelated kwargs., Describe normalized durable outputs from one reconstruction run.      The minima, ReconstructionArtifacts, ReconstructionMethodId (+35 more)

### Community 16 - "Community 16"
Cohesion: 0.07
Nodes (38): Replay clock used by dataset and video source streams., Select whether replay follows source timing or returns observations immediately., Apply source-timestamp pacing for real-time replay., Reset the clock baseline for a new replay loop or connection., Sleep until the replay timestamp should be emitted., ReplayClock, ReplayMode, ImageSequenceObservationSource (+30 more)

### Community 17 - "Community 17"
Cohesion: 0.14
Nodes (26): _add_point_cloud_trace(), _add_trajectory_trace(), _apply_comparison_layout(), _build_figure(), build_reference_reconstruction_figure(), build_slam_reference_comparison_figure(), _combined_bounds(), _decimate_mesh() (+18 more)

### Community 18 - "Community 18"
Cohesion: 0.33
Nodes (13): load_reused_stage_results(), _load_slam_result(), _load_source_result(), _optional_npz(), _optional_ply(), _outcome(), _rebase_artifact_path(), _rebase_benchmark_inputs() (+5 more)

### Community 19 - "Community 19"
Cohesion: 0.25
Nodes (1): Backend boundary between launch surfaces and execution substrates.  This module

### Community 20 - "Community 20"
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
Nodes (1): Return whether ``exc`` looks like a transient local Ray connection failure.

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (1): Return the human-readable label shown in plan previews.

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): Deserialize one IPC payload back into the target validated model type.

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from a 4x4 homogeneous matrix.

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): Return the compact source label used in logs and diagnostics.

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): Disconnect or release the source and any owned runtime resources.

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): Return the short user-facing dataset label.

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (1): Return the net code-line delta.

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (1): Return the path that should own this change in reports.

### Community 33 - "Community 33"
Cohesion: 1.0
Nodes (1): Build one spec from one JSON object.

## Knowledge Gaps
- **262 isolated node(s):** `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`, `Frame preprocessing helpers for ViSTA-SLAM.`, `One RGB frame prepared for upstream ViSTA ingestion.`, `Use the exact upstream ViSTA crop-and-resize helper path.`, `Convert one upstream ViSTA array-like payload into a numpy array.` (+257 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 19`** (8 nodes): `get_events()`, `get_snapshot()`, `Backend boundary between launch surfaces and execution substrates.  This module`, `read_payload()`, `shutdown()`, `stop_run()`, `submit_run()`, `backend.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (2 nodes): `streamlit_app.py`, `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 22`** (2 nodes): `ray.py`, `Ray-specific helpers for future stage runtime deployment.  This module intention`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (1 nodes): `Return whether ``exc`` looks like a transient local Ray connection failure.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (1 nodes): `Return the human-readable label shown in plan previews.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (1 nodes): `Deserialize one IPC payload back into the target validated model type.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `Build the shared transform DTO from a 4x4 homogeneous matrix.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `Return the compact source label used in logs and diagnostics.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `Disconnect or release the source and any owned runtime resources.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `Return the short user-facing dataset label.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `Return the net code-line delta.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (1 nodes): `Return the path that should own this change in reports.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 33`** (1 nodes): `Build one spec from one JSON object.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Test package helpers and suites for PRML VSLAM.` connect `Community 1` to `Community 0`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 9`, `Community 12`, `Community 13`, `Community 15`, `Community 16`, `Community 17`?**
  _High betweenness centrality (0.093) - this node is a cross-community bridge._
- **Why does `PathConfig` connect `Community 7` to `Community 0`, `Community 1`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 8`, `Community 9`, `Community 10`, `Community 12`?**
  _High betweenness centrality (0.065) - this node is a cross-community bridge._
- **Why does `SequenceManifest` connect `Community 9` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 12`, `Community 13`?**
  _High betweenness centrality (0.064) - this node is a cross-community bridge._
- **Are the 498 inferred relationships involving `SequenceManifest` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`SequenceManifest` has 498 INFERRED edges - model-reasoned connections that need verification._
- **Are the 466 inferred relationships involving `StageKey` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`StageKey` has 466 INFERRED edges - model-reasoned connections that need verification._
- **Are the 430 inferred relationships involving `PreparedBenchmarkInputs` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`PreparedBenchmarkInputs` has 430 INFERRED edges - model-reasoned connections that need verification._
- **Are the 423 inferred relationships involving `DatasetId` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`DatasetId` has 423 INFERRED edges - model-reasoned connections that need verification._