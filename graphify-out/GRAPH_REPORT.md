# Graph Report - lingbot-benchmark-sweep-runs-merge-main  (2026-07-03)

## Corpus Check
- 331 files · ~2,636,391 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 5433 nodes · 27025 edges · 35 communities detected
- Extraction: 30% EXTRACTED · 70% INFERRED · 0% AMBIGUOUS · INFERRED: 18938 edges (avg confidence: 0.59)
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
- [[_COMMUNITY_Community 34|Community 34]]

## God Nodes (most connected - your core abstractions)
1. `SequenceManifest` - 490 edges
2. `StageKey` - 470 edges
3. `PreparedBenchmarkInputs` - 409 edges
4. `DatasetId` - 403 edges
5. `PathConfig` - 322 edges
6. `ReferenceSource` - 310 edges
7. `MethodId` - 298 edges
8. `ArtifactRef` - 298 edges
9. `StageRuntimeStatus` - 275 edges
10. `CameraIntrinsics` - 267 edges

## Surprising Connections (you probably didn't know these)
- `test_mast3r_backend_config_validates_supported_img_size()` --calls--> `Mast3rSlamBackendConfig`  [INFERRED]
  tests/test_pipeline_config.py → src/prml_vslam/methods/stage/backend_config.py
- `test_mast3r_backend_config_match_frac_thresh_override()` --calls--> `Mast3rSlamBackendConfig`  [INFERRED]
  tests/test_pipeline_config.py → src/prml_vslam/methods/stage/backend_config.py
- `Focused tests for derived ground-plane alignment.` --uses--> `GroundAlignmentMetadata`  [INFERRED]
  tests/test_ground_alignment.py → src/prml_vslam/interfaces/alignment.py
- `Small runtime sources used by focused pipeline smoke tests.` --uses--> `SequenceManifest`  [INFERRED]
  tests/pipeline_testing_support.py → src/prml_vslam/sources/contracts.py
- `Minimal offline source for pipeline smoke tests.` --uses--> `SequenceManifest`  [INFERRED]
  tests/pipeline_testing_support.py → src/prml_vslam/sources/contracts.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.01
Nodes (553): _build_artifacts(), GroundAlignmentMetadata, Result of one derived ground-plane alignment attempt.      When :attr:`applied`, InputArtifactDiagnostics, Inspection helpers for persisted pipeline run artifact roots., One submitted run attempt found in a persisted event log., Structured inspection result for one persisted pipeline run., Discover method-level run roots under the configured artifact directory. (+545 more)

### Community 1 - "Community 1"
Cohesion: 0.01
Nodes (417): build_advio_page_data(), _scene_rows(), AdvioDownloadManager, _ensure_directory_parent(), Return the cache directory used for downloaded scene archives., Return one catalog scene by id., Return local availability status for every catalog scene., Download selected ADVIO scenes and extract complete scene payloads. (+409 more)

### Community 2 - "Community 2"
Cohesion: 0.01
Nodes (453): handle_advio_preview_action(), Controller helpers for the ADVIO Streamlit page., Persist the current ADVIO download-form state., Keep persisted preview state aligned with the runtime snapshot., Apply one preview-form action and return an error message when it fails., sync_advio_download_state(), sync_advio_preview_state(), BaseData (+445 more)

### Community 3 - "Community 3"
Cohesion: 0.01
Nodes (442): build_advio_comparison_trajectories(), build_crowd_density_figure(), build_local_readiness_figure(), build_scene_attribute_figure(), build_scene_mix_figure(), advio_common_start_local_trajectories(), advio_frame_transform_from_pose(), AdvioFixedpointRegistration (+434 more)

### Community 4 - "Community 4"
Cohesion: 0.02
Nodes (392): _DensePredictionArtifacts, _ensure_uint8_rgb_from_uimg(), _estimate_camera_intrinsics_from_frame(), _InProcessManager, _InProcessValue, Mast3rSlamSession, Canonical MASt3R-SLAM backend adapter (offline + streaming).  This adapter wraps, Run LingBot terminal inference and clear streaming state. (+384 more)

### Community 5 - "Community 5"
Cohesion: 0.02
Nodes (375): PipelineBackend, Execute, monitor, and tear down pipeline runs.      Implementations own the conc, Ray-backed backend for plan execution and run attachment.  This module owns subs, Forward a stop request to the named coordinator actor., Fetch the latest projected snapshot from the coordinator actor., Fetch trailing events from the coordinator actor., Resolve one coordinator-owned target transient payload ref., Detach from Ray and stop any backend-owned shared infrastructure. (+367 more)

### Community 6 - "Community 6"
Cohesion: 0.02
Nodes (296): align_estimate_sim3(), is_gravity_aligned_target(), ICP point-cloud alignment service., Materialize offline point-cloud alignment artifacts before cloud metrics., Return True when both trajectories have enough geometric spread for Sim(3) align, Align *estimate* to *reference* via Sim(3) and return the aligned trajectory and, Return the tilt angle in degrees between the transformed and original down-axis,, sim3_up_axis_tilt_deg() (+288 more)

### Community 7 - "Community 7"
Cohesion: 0.02
Nodes (204): AdvioCalibration, _expect_float_list(), _expect_mapping(), _expect_matrix(), _extract_camera_mapping(), load_advio_calibration(), Parse an official ADVIO calibration YAML into a typed camera model., Convert an ADVIO pose CSV into a TUM trajectory file. (+196 more)

### Community 8 - "Community 8"
Cohesion: 0.02
Nodes (209): _adapt_checkpoint_state_dict(), _as_numpy(), _build_lingbot_artifacts(), _cast_aggregator_for_inference(), _decode_pose_predictions(), _expect_lingbot_config(), _extract_checkpoint_state_dict(), _extract_dense_prediction_artifacts() (+201 more)

### Community 9 - "Community 9"
Cohesion: 0.03
Nodes (189): BaseConfig, CloudAlignmentStageConfig, CloudEvaluationStageConfig, _compile_run_plan(), GroundAlignmentStageConfig, ImageEvaluationPolicy, ImageEvaluationStageConfig, Open3dTsdfBackendConfig (+181 more)

### Community 10 - "Community 10"
Cohesion: 0.03
Nodes (134): _coordinator_actor_options(), RayPipelineBackend, Serialize the config to deterministic TOML and optionally persist it., build_run_config(), from_toml(), _load_toml_payload(), path(), Durable JSONL event sink. (+126 more)

### Community 11 - "Community 11"
Cohesion: 0.03
Nodes (122): LingbotMapSlamBackend, Mast3rSlamBackend, VistaSlamBackend, build_slam_backend_config(), Persisted SLAM backend config and backend muxing.  The SLAM stage owns the publi, Whether the backend can emit live preview payloads., Whether the backend may emit native visualization artifacts., Whether the backend supports repository trajectory evaluation. (+114 more)

### Community 12 - "Community 12"
Cohesion: 0.02
Nodes (100): BaseConfig, _ConfigFactory, FactoryConfig, from_toml(), _normalize_value(), Shared config and config-as-factory helpers for the repository.  This module own, Render the config as a Rich tree for quick human inspection., Mixin for configs that construct one runtime owner or adapter.      This pattern (+92 more)

### Community 13 - "Community 13"
Cohesion: 0.02
Nodes (120): ArxivSourceSpec, download_file(), fetch_pdf(), fetch_tex_source(), from_json(), load_manifest(), main(), normalize_member_path() (+112 more)

### Community 14 - "Community 14"
Cohesion: 0.05
Nodes (28): IntEnum, Return a compact JSON-ready subset for UI details and telemetry sinks., build_record3d_frame_details(), _camera_pose_from_binding(), _device_from_binding(), _import_record3d_module(), _intrinsics_from_binding(), open_record3d_usb_packet_stream() (+20 more)

### Community 15 - "Community 15"
Cohesion: 0.11
Nodes (32): GroundPlaneModel, GroundPlaneVisualizationHint, Alignment result DTOs shared outside the alignment package.  These datamodels de, Dominant ground-plane hypothesis expressed in native ``world`` coordinates., Finite plane-patch geometry ready for visualization consumers., GroundAlignmentConfig, _build_viewer_transform(), _camera_down_alignment() (+24 more)

### Community 16 - "Community 16"
Cohesion: 0.11
Nodes (38): from_error_values(), from_frames(), compute_image_metrics(), l1_error(), l2_error(), _mean_absolute_error(), _mean_squared_error(), peak_signal_noise_ratio() (+30 more)

### Community 17 - "Community 17"
Cohesion: 0.1
Nodes (35): main(), _parse_args(), _preferred_trajectory(), _write_reference_svg(), _write_summary_bar_variants(), _write_summary_csv(), build_dataset_summary_bar_figure(), build_dataset_summary_bar_svg() (+27 more)

### Community 18 - "Community 18"
Cohesion: 0.11
Nodes (35): build_pipeline_snapshot_render_model(), _coerce_int_metric(), _format_latency(), _format_optional_rate(), _format_queue(), _format_resources(), _format_tasks(), _format_throughput() (+27 more)

### Community 19 - "Community 19"
Cohesion: 0.33
Nodes (13): load_reused_stage_results(), _load_slam_result(), _load_source_result(), _optional_npz(), _optional_ply(), _outcome(), _rebase_artifact_path(), _rebase_benchmark_inputs() (+5 more)

### Community 20 - "Community 20"
Cohesion: 0.18
Nodes (2): finish_streaming(), start_streaming()

### Community 21 - "Community 21"
Cohesion: 0.25
Nodes (1): Backend boundary between launch surfaces and execution substrates.  This module

### Community 22 - "Community 22"
Cohesion: 1.0
Nodes (1): Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (1): Ray-specific helpers for future stage runtime deployment.  This module intention

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from a 4x4 homogeneous matrix.

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): Return the compact source label used in logs and diagnostics.

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): Disconnect or release the source and any owned runtime resources.

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): Return the short user-facing dataset label.

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): Deserialize one IPC payload back into the target validated model type.

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): Return the human-readable label shown in plan previews.

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (1): Return whether ``exc`` looks like a transient local Ray connection failure.

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (1): Build one spec from one JSON object.

### Community 33 - "Community 33"
Cohesion: 1.0
Nodes (1): Return the net code-line delta.

### Community 34 - "Community 34"
Cohesion: 1.0
Nodes (1): Return the path that should own this change in reports.

## Knowledge Gaps
- **267 isolated node(s):** `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`, `Frame preprocessing helpers for ViSTA-SLAM.`, `One RGB frame prepared for upstream ViSTA ingestion.`, `Use the exact upstream ViSTA crop-and-resize helper path.`, `Convert one upstream ViSTA array-like payload into a numpy array.` (+262 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 20`** (12 nodes): `protocols.py`, `protocols.py`, `drain_runtime_updates()`, `drain_streaming_updates()`, `finish_streaming()`, `run_observations()`, `run_offline()`, `start_streaming()`, `status()`, `step_streaming()`, `stop()`, `submit_stream_item()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (8 nodes): `get_events()`, `get_snapshot()`, `Backend boundary between launch surfaces and execution substrates.  This module`, `read_payload()`, `shutdown()`, `stop_run()`, `submit_run()`, `backend.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 22`** (2 nodes): `streamlit_app.py`, `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (2 nodes): `ray.py`, `Ray-specific helpers for future stage runtime deployment.  This module intention`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (1 nodes): `Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (1 nodes): `Build the shared transform DTO from a 4x4 homogeneous matrix.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `Return the compact source label used in logs and diagnostics.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `Disconnect or release the source and any owned runtime resources.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `Return the short user-facing dataset label.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `Deserialize one IPC payload back into the target validated model type.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `Return the human-readable label shown in plan previews.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `Return whether ``exc`` looks like a transient local Ray connection failure.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (1 nodes): `Build one spec from one JSON object.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 33`** (1 nodes): `Return the net code-line delta.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 34`** (1 nodes): `Return the path that should own this change in reports.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Test package helpers and suites for PRML VSLAM.` connect `Community 1` to `Community 0`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 8`, `Community 9`, `Community 10`, `Community 11`, `Community 12`, `Community 14`, `Community 15`?**
  _High betweenness centrality (0.107) - this node is a cross-community bridge._
- **Why does `StageKey` connect `Community 0` to `Community 1`, `Community 2`, `Community 4`, `Community 5`, `Community 7`, `Community 9`, `Community 10`, `Community 12`, `Community 18`?**
  _High betweenness centrality (0.070) - this node is a cross-community bridge._
- **Why does `SequenceManifest` connect `Community 4` to `Community 0`, `Community 1`, `Community 2`, `Community 5`, `Community 6`, `Community 8`, `Community 9`, `Community 10`, `Community 11`, `Community 14`?**
  _High betweenness centrality (0.066) - this node is a cross-community bridge._
- **Are the 487 inferred relationships involving `SequenceManifest` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`SequenceManifest` has 487 INFERRED edges - model-reasoned connections that need verification._
- **Are the 467 inferred relationships involving `StageKey` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`StageKey` has 467 INFERRED edges - model-reasoned connections that need verification._
- **Are the 404 inferred relationships involving `PreparedBenchmarkInputs` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`PreparedBenchmarkInputs` has 404 INFERRED edges - model-reasoned connections that need verification._
- **Are the 400 inferred relationships involving `DatasetId` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`DatasetId` has 400 INFERRED edges - model-reasoned connections that need verification._