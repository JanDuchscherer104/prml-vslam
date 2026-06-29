# Graph Report - lingbot-upstream-windowed-adapter  (2026-06-29)

## Corpus Check
- 306 files · ~2,092,159 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 5075 nodes · 25036 edges · 29 communities detected
- Extraction: 30% EXTRACTED · 70% INFERRED · 0% AMBIGUOUS · INFERRED: 17514 edges (avg confidence: 0.59)
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

## God Nodes (most connected - your core abstractions)
1. `StageKey` - 457 edges
2. `SequenceManifest` - 456 edges
3. `PreparedBenchmarkInputs` - 399 edges
4. `DatasetId` - 382 edges
5. `PathConfig` - 305 edges
6. `ReferenceSource` - 303 edges
7. `ArtifactRef` - 285 edges
8. `MethodId` - 283 edges
9. `StageRuntimeStatus` - 264 edges
10. `FrameSelectionConfig` - 250 edges

## Surprising Connections (you probably didn't know these)
- `test_plan_run_defaults_to_live_viewer()` --calls--> `plan_run()`  [INFERRED]
  tests/test_main.py → src/prml_vslam/main.py
- `Focused tests for derived ground-plane alignment.` --uses--> `GroundAlignmentMetadata`  [INFERRED]
  tests/test_ground_alignment.py → src/prml_vslam/interfaces/alignment.py
- `test_pointmap_contract_rejects_sparse_point_cloud_shape()` --calls--> `PointMap`  [INFERRED]
  tests/test_geometry.py → src/prml_vslam/interfaces/geometry.py
- `Small runtime sources used by focused pipeline smoke tests.` --uses--> `SequenceManifest`  [INFERRED]
  tests/pipeline_testing_support.py → src/prml_vslam/sources/contracts.py
- `Minimal offline source for pipeline smoke tests.` --uses--> `SequenceManifest`  [INFERRED]
  tests/pipeline_testing_support.py → src/prml_vslam/sources/contracts.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.01
Nodes (414): _build_artifacts(), _DensePredictionArtifacts, _ensure_uint8_rgb_from_uimg(), _estimate_camera_intrinsics_from_frame(), _InProcessManager, _InProcessValue, Mast3rSlamSession, Canonical MASt3R-SLAM backend adapter (offline + streaming).  This adapter wraps (+406 more)

### Community 1 - "Community 1"
Cohesion: 0.01
Nodes (329): build_advio_page_data(), AdvioDownloadManager, _ensure_directory_parent(), arcore_ready(), arkit_ready(), _complete_scene_ready(), load_advio_catalog(), offline_ready() (+321 more)

### Community 2 - "Community 2"
Cohesion: 0.01
Nodes (355): BaseConfig, _ConfigFactory, FactoryConfig, from_toml(), _normalize_value(), Shared config and config-as-factory helpers for the repository.  This module own, Render the config as a Rich tree for quick human inspection., Mixin for configs that construct one runtime owner or adapter.      This pattern (+347 more)

### Community 3 - "Community 3"
Cohesion: 0.02
Nodes (376): handle_advio_preview_action(), Controller helpers for the ADVIO Streamlit page., Persist the current ADVIO download-form state., Keep persisted preview state aligned with the runtime snapshot., Apply one preview-form action and return an error message when it fails., _scene_rows(), sync_advio_download_state(), sync_advio_preview_state() (+368 more)

### Community 4 - "Community 4"
Cohesion: 0.01
Nodes (372): build_advio_comparison_trajectories(), build_crowd_density_figure(), build_local_readiness_figure(), build_scene_attribute_figure(), build_scene_mix_figure(), advio_common_start_local_trajectories(), advio_frame_transform_from_pose(), AdvioFixedpointRegistration (+364 more)

### Community 5 - "Community 5"
Cohesion: 0.02
Nodes (273): artifact_ref(), Build one stable artifact reference for a materialized path., BaseStageRuntime, FailureFingerprint, Reject negative custom resource quantities., Allow only exact artifact keys or safe ``prefix:*`` selectors., Return the declared output paths for a generic stage section., Return deterministic output paths declared by this stage. (+265 more)

### Community 6 - "Community 6"
Cohesion: 0.04
Nodes (334): AdvioFixedpointFitMode, Rigid registration mode selected for one ADVIO provider trajectory., AdvioRawCoordinateBasis, Raw coordinate bases used by official ADVIO provider artifacts., MethodId, BaseConfig, AdvioNormalizedDatasetBuildSource, NormalizedCadenceConfig (+326 more)

### Community 7 - "Community 7"
Cohesion: 0.02
Nodes (247): _adapt_checkpoint_state_dict(), _as_numpy(), _build_lingbot_artifacts(), _cast_aggregator_for_inference(), _decode_pose_predictions(), _expect_lingbot_config(), _extract_checkpoint_state_dict(), _extract_dense_prediction_artifacts() (+239 more)

### Community 8 - "Community 8"
Cohesion: 0.03
Nodes (248): Return the cache directory used for downloaded scene archives., Return one catalog scene by id., Return local availability status for every catalog scene., Download selected ADVIO scenes and extract complete scene payloads., AdvioFixpointSet, load_advio_fixpoints(), ADVIO fixpoints converted to repository RDF coordinates., Load ADVIO fixpoints with upstream-compatible axis handling.      Upstream visua (+240 more)

### Community 9 - "Community 9"
Cohesion: 0.02
Nodes (265): align_estimate_sim3(), is_gravity_aligned_target(), Return True when both trajectories have enough geometric spread for Sim(3) align, Align *estimate* to *reference* via Sim(3) and return the aligned trajectory and, Return the tilt angle in degrees between the transformed and original down-axis,, sim3_up_axis_tilt_deg(), trajectory_supports_sim3(), from_evo_statistics() (+257 more)

### Community 10 - "Community 10"
Cohesion: 0.01
Nodes (212): _coordinator_actor_options(), RayPipelineBackend, Serialize the config to deterministic TOML and optionally persist it., from_toml(), _load_toml_payload(), ArxivSourceSpec, download_file(), fetch_pdf() (+204 more)

### Community 11 - "Community 11"
Cohesion: 0.02
Nodes (162): label(), build_pipeline_snapshot_render_model(), _coerce_int_metric(), _format_latency(), _format_optional_rate(), _format_queue(), _format_resources(), _format_tasks() (+154 more)

### Community 12 - "Community 12"
Cohesion: 0.02
Nodes (112): CloudAlignmentService, icp_point_cloud_path(), ICP point-cloud alignment service., Materialize offline point-cloud alignment artifacts before cloud metrics., Refine a trajectory-Sim(3)-aligned cloud against a reference cloud with ICP., Return the deterministic point-cloud alignment metadata path., Return the deterministic ICP-refined point-cloud path., _read_non_empty_point_cloud() (+104 more)

### Community 13 - "Community 13"
Cohesion: 0.02
Nodes (94): Record3DTransportId, IntEnum, record3d_devices(), build_record3d_frame_details(), _camera_pose_from_binding(), _device_from_binding(), _import_record3d_module(), _intrinsics_from_binding() (+86 more)

### Community 14 - "Community 14"
Cohesion: 0.06
Nodes (62): config_warnings(), _check_extraction_cache(), materialize_manifest(), Source-owned manifest materialization helpers., Materialize the run-owned source manifest for this source stage., _resolve_timestamps_ns(), iter_sequence_manifest_observations(), _load_manifest_rgb_inputs() (+54 more)

### Community 15 - "Community 15"
Cohesion: 0.08
Nodes (38): build_run_config_from_sweep_item(), expand_sweep(), _load_slam_stage_from_template(), load_sweep_config(), _make_item(), _minimal_sweep_toml(), test_benchmark_datastore_config_covers_full_sweep_sources(), test_build_run_config_baseline_source_propagates() (+30 more)

### Community 16 - "Community 16"
Cohesion: 1.0
Nodes (1): Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays

### Community 17 - "Community 17"
Cohesion: 1.0
Nodes (1): Ray-specific helpers for future stage runtime deployment.  This module intention

### Community 18 - "Community 18"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.

### Community 19 - "Community 19"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from a 4x4 homogeneous matrix.

### Community 20 - "Community 20"
Cohesion: 1.0
Nodes (1): Return the compact source label used in logs and diagnostics.

### Community 21 - "Community 21"
Cohesion: 1.0
Nodes (1): Disconnect or release the source and any owned runtime resources.

### Community 22 - "Community 22"
Cohesion: 1.0
Nodes (1): Return the short user-facing dataset label.

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (1): Deserialize one IPC payload back into the target validated model type.

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (1): Return the human-readable label shown in plan previews.

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): Return whether ``exc`` looks like a transient local Ray connection failure.

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): Build one spec from one JSON object.

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): Return the net code-line delta.

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): Return the path that should own this change in reports.

## Knowledge Gaps
- **261 isolated node(s):** `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`, `Frame preprocessing helpers for ViSTA-SLAM.`, `One RGB frame prepared for upstream ViSTA ingestion.`, `Use the exact upstream ViSTA crop-and-resize helper path.`, `Convert one upstream ViSTA array-like payload into a numpy array.` (+256 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 16`** (2 nodes): `streamlit_app.py`, `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 17`** (2 nodes): `ray.py`, `Ray-specific helpers for future stage runtime deployment.  This module intention`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 18`** (1 nodes): `Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 19`** (1 nodes): `Build the shared transform DTO from a 4x4 homogeneous matrix.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 20`** (1 nodes): `Return the compact source label used in logs and diagnostics.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (1 nodes): `Disconnect or release the source and any owned runtime resources.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 22`** (1 nodes): `Return the short user-facing dataset label.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (1 nodes): `Deserialize one IPC payload back into the target validated model type.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (1 nodes): `Return the human-readable label shown in plan previews.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (1 nodes): `Return whether ``exc`` looks like a transient local Ray connection failure.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `Build one spec from one JSON object.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `Return the net code-line delta.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `Return the path that should own this change in reports.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Test package helpers and suites for PRML VSLAM.` connect `Community 12` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 9`, `Community 13`?**
  _High betweenness centrality (0.105) - this node is a cross-community bridge._
- **Why does `PathConfig` connect `Community 6` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 5`, `Community 7`, `Community 8`, `Community 9`, `Community 10`, `Community 12`?**
  _High betweenness centrality (0.058) - this node is a cross-community bridge._
- **Why does `StageKey` connect `Community 5` to `Community 0`, `Community 2`, `Community 3`, `Community 6`, `Community 8`, `Community 9`, `Community 10`, `Community 11`, `Community 12`?**
  _High betweenness centrality (0.056) - this node is a cross-community bridge._
- **Are the 454 inferred relationships involving `StageKey` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`StageKey` has 454 INFERRED edges - model-reasoned connections that need verification._
- **Are the 453 inferred relationships involving `SequenceManifest` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`SequenceManifest` has 453 INFERRED edges - model-reasoned connections that need verification._
- **Are the 394 inferred relationships involving `PreparedBenchmarkInputs` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`PreparedBenchmarkInputs` has 394 INFERRED edges - model-reasoned connections that need verification._
- **Are the 379 inferred relationships involving `DatasetId` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`DatasetId` has 379 INFERRED edges - model-reasoned connections that need verification._