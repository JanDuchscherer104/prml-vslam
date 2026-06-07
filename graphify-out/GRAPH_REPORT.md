# Graph Report - prml-vslam-pr87-push  (2026-06-07)

## Corpus Check
- 272 files · ~1,062,698 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4057 nodes · 18411 edges · 31 communities detected
- Extraction: 32% EXTRACTED · 68% INFERRED · 0% AMBIGUOUS · INFERRED: 12537 edges (avg confidence: 0.59)
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
1. `StageKey` - 439 edges
2. `SequenceManifest` - 315 edges
3. `ArtifactRef` - 272 edges
4. `MethodId` - 248 edges
5. `PreparedBenchmarkInputs` - 242 edges
6. `StageRuntimeStatus` - 231 edges
7. `PathConfig` - 224 edges
8. `RunConfig` - 198 edges
9. `ReferenceSource` - 182 edges
10. `FrameTransform` - 181 edges

## Surprising Connections (you probably didn't know these)
- `test_source_materialization_does_not_import_stage_package()` --calls--> `path()`  [INFERRED]
  tests/test_package_exports.py → src/prml_vslam/pipeline/sinks/jsonl.py
- `Focused tests for derived ground-plane alignment.` --uses--> `GroundAlignmentMetadata`  [INFERRED]
  tests/test_ground_alignment.py → src/prml_vslam/interfaces/alignment.py
- `test_pointmap_contract_rejects_sparse_point_cloud_shape()` --calls--> `PointMap`  [INFERRED]
  tests/test_geometry.py → src/prml_vslam/interfaces/geometry.py
- `Focused tests for the Rich-backed console wrapper.` --uses--> `Console`  [INFERRED]
  tests/test_console.py → src/prml_vslam/utils/console.py
- `Small runtime sources used by focused pipeline smoke tests.` --uses--> `SequenceManifest`  [INFERRED]
  tests/pipeline_testing_support.py → src/prml_vslam/sources/contracts.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.01
Nodes (424): _build_artifacts(), _ensure_uint8_rgb_from_uimg(), _estimate_camera_intrinsics_from_frame(), _InProcessManager, _InProcessValue, Mast3rSlamBackend, Mast3rSlamSession, Canonical MASt3R-SLAM backend adapter (offline + streaming).  This adapter wraps (+416 more)

### Community 1 - "Community 1"
Cohesion: 0.01
Nodes (319): build_advio_page_data(), _scene_rows(), AdvioDownloadManager, _ensure_directory_parent(), Return the cache directory used for downloaded scene archives., Return one catalog scene by id., Return local availability status for every catalog scene., Download selected ADVIO scenes and extract the requested modalities. (+311 more)

### Community 2 - "Community 2"
Cohesion: 0.02
Nodes (352): get_events(), get_snapshot(), PipelineBackend, Backend boundary between launch surfaces and execution substrates.  This module, _coordinator_actor_options(), Ray-backed backend for plan execution and run attachment.  This module owns subs, Forward a stop request to the named coordinator actor., Fetch the latest projected snapshot from the coordinator actor. (+344 more)

### Community 3 - "Community 3"
Cohesion: 0.02
Nodes (274): GroundAlignmentMetadata, Result of one derived ground-plane alignment attempt.      When :attr:`applied`, _apply_snapshot_fallbacks(), _candidate_from_root(), _canonical_path_rows(), _derive_slam_artifacts(), discover_run_artifact_roots(), _file_inventory() (+266 more)

### Community 4 - "Community 4"
Cohesion: 0.02
Nodes (281): handle_advio_preview_action(), load_advio_explorer_sample(), Controller helpers for the ADVIO Streamlit page., Persist the current ADVIO download-form state., Persist the current explorer selection and load its offline sample., Keep persisted preview state aligned with the runtime snapshot., Apply one preview-form action and return an error message when it fails., sync_advio_download_state() (+273 more)

### Community 5 - "Community 5"
Cohesion: 0.03
Nodes (222): FailureFingerprint, Reject negative custom resource quantities., Allow only exact artifact keys or safe ``prefix:*`` selectors., Return deterministic output paths declared by this stage., Return whether the configured stage can run., Build a failed :class:`StageOutcome` using this stage's identity., Stable hash inputs for generic stage failure provenance., PipelineExecutionContext (+214 more)

### Community 6 - "Community 6"
Cohesion: 0.01
Nodes (294): build_advio_comparison_trajectories(), build_crowd_density_figure(), build_local_readiness_figure(), build_scene_attribute_figure(), build_scene_mix_figure(), validate_dataset_root(), Plotly figure builders for the ADVIO dataset page., Build a crowd-density composition chart. (+286 more)

### Community 7 - "Community 7"
Cohesion: 0.02
Nodes (215): BaseConfig, AppContext, _advio_native_fps(), build_backend_spec(), CloudAlignmentStageConfig, CloudEvaluationStageConfig, CloudMetricId, _collect_unknown_field_warnings() (+207 more)

### Community 8 - "Community 8"
Cohesion: 0.02
Nodes (194): GroundPlaneModel, GroundPlaneVisualizationHint, Alignment result DTOs shared outside the alignment package.  These datamodels de, Dominant ground-plane hypothesis expressed in native ``world`` coordinates., Finite plane-patch geometry ready for visualization consumers., BaseConfig, _ConfigFactory, FactoryConfig (+186 more)

### Community 9 - "Community 9"
Cohesion: 0.02
Nodes (129): IntEnum, _camera_pose_from_binding(), _device_from_binding(), _import_record3d_module(), _intrinsics_from_binding(), list_record3d_usb_devices(), open_record3d_usb_packet_stream(), Disconnect the current USB device if one is active. (+121 more)

### Community 10 - "Community 10"
Cohesion: 0.02
Nodes (120): ArxivSourceSpec, download_file(), fetch_pdf(), fetch_tex_source(), from_json(), load_manifest(), main(), normalize_member_path() (+112 more)

### Community 11 - "Community 11"
Cohesion: 0.04
Nodes (89): validate_modalities(), config_warnings(), iter_sequence_manifest_observations(), _load_manifest_rgb_inputs(), _load_rgb(), _load_timestamps_ns(), _manifest_provenance(), Source-owned readers for normalized offline observations. (+81 more)

### Community 12 - "Community 12"
Cohesion: 0.07
Nodes (34): Replay clock used by dataset and video source streams., Select whether replay follows source timing or returns observations immediately., Apply source-timestamp pacing for real-time replay., Reset the clock baseline for a new replay loop or connection., Sleep until the replay timestamp should be emitted., ReplayClock, ReplayMode, ImageSequenceObservationSource (+26 more)

### Community 13 - "Community 13"
Cohesion: 0.13
Nodes (35): test_load_recording_summary_reports_live_keyed_and_tracking_surfaces(), test_write_validation_bundle_emits_report_and_projection_images(), test_write_validation_bundle_respects_explicit_keyed_cloud_limit(), _write_synthetic_recording(), _ancestor_entity_paths(), _component_columns(), _keyed_point_cloud_snapshots(), _latest_live_model_snapshot() (+27 more)

### Community 14 - "Community 14"
Cohesion: 0.12
Nodes (33): build_pipeline_snapshot_render_model(), _coerce_int_metric(), _format_latency(), _format_optional_rate(), _format_queue(), _format_resources(), _format_tasks(), _format_throughput() (+25 more)

### Community 15 - "Community 15"
Cohesion: 0.17
Nodes (2): Tests for package-root public export surfaces., test_source_materialization_does_not_import_stage_package()

### Community 16 - "Community 16"
Cohesion: 0.36
Nodes (4): test_resolve_issue_moves_record_to_resolved_collection(), test_resolve_refactor_moves_record_to_resolved_collection(), test_resolve_todo_moves_record_to_resolved_collection(), _write_toml()

### Community 17 - "Community 17"
Cohesion: 1.0
Nodes (1): Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays

### Community 18 - "Community 18"
Cohesion: 1.0
Nodes (1): Ray-specific helpers for future stage runtime deployment.  This module intention

### Community 19 - "Community 19"
Cohesion: 1.0
Nodes (1): Deserialize one IPC payload back into the target validated model type.

### Community 20 - "Community 20"
Cohesion: 1.0
Nodes (1): Return the compact source label used in logs and diagnostics.

### Community 21 - "Community 21"
Cohesion: 1.0
Nodes (1): Connect to the source and prepare subsequent blocking observation reads.

### Community 22 - "Community 22"
Cohesion: 1.0
Nodes (1): Disconnect or release the source and any owned runtime resources.

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (1): Return the short user-facing dataset label.

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (1): Return whether ``exc`` looks like a transient local Ray connection failure.

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): Return the human-readable label shown in plan previews.

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from a 4x4 homogeneous matrix.

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): Return the net code-line delta.

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): Return the path that should own this change in reports.

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): Build one spec from one JSON object.

## Knowledge Gaps
- **251 isolated node(s):** `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`, `Tests for ViSTA-native persisted artifact diagnostics.`, `Tests for offline follow-enabled Rerun artifact generation.`, `Tests for reconstruction artifact Plotly figure builders.`, `Tests for centralized repository path handling.` (+246 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 15`** (12 nodes): `Tests for package-root public export surfaces.`, `test_executable_stage_packages_export_canonical_surfaces()`, `test_interfaces_package_exports_only_canonical_pose_surface()`, `test_methods_package_exports_slam_surfaces()`, `test_pipeline_contracts_package_is_not_a_compatibility_hub()`, `test_pipeline_package_exports_only_minimal_public_surface()`, `test_reconstruction_package_exports_runtime_surfaces_without_harness()`, `test_replay_package_exports_only_replay_primitives()`, `test_source_materialization_does_not_import_stage_package()`, `test_sources_package_exports_source_owned_contracts()`, `test_vista_package_is_the_only_canonical_vista_surface()`, `test_package_exports.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 17`** (2 nodes): `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`, `streamlit_app.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 18`** (2 nodes): `Ray-specific helpers for future stage runtime deployment.  This module intention`, `ray.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 19`** (1 nodes): `Deserialize one IPC payload back into the target validated model type.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 20`** (1 nodes): `Return the compact source label used in logs and diagnostics.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (1 nodes): `Connect to the source and prepare subsequent blocking observation reads.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 22`** (1 nodes): `Disconnect or release the source and any owned runtime resources.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (1 nodes): `Return the short user-facing dataset label.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (1 nodes): `Return whether ``exc`` looks like a transient local Ray connection failure.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (1 nodes): `Return the human-readable label shown in plan previews.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `Build the shared transform DTO from a 4x4 homogeneous matrix.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `Return the net code-line delta.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `Return the path that should own this change in reports.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `Build one spec from one JSON object.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Ground-alignment pipeline stage integration.` connect `Community 1` to `Community 0`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 9`, `Community 12`?**
  _High betweenness centrality (0.122) - this node is a cross-community bridge._
- **Why does `StageKey` connect `Community 5` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 7`, `Community 8`, `Community 11`?**
  _High betweenness centrality (0.079) - this node is a cross-community bridge._
- **Why does `CameraIntrinsics` connect `Community 0` to `Community 1`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 9`, `Community 11`, `Community 13`?**
  _High betweenness centrality (0.061) - this node is a cross-community bridge._
- **Are the 436 inferred relationships involving `StageKey` (e.g. with `Tests for repo-owned visualization helpers.` and `_FakeRecordingStream`) actually correct?**
  _`StageKey` has 436 INFERRED edges - model-reasoned connections that need verification._
- **Are the 312 inferred relationships involving `SequenceManifest` (e.g. with `_FakeVistaBackend` and `Focused tests for the Ray-backed pipeline core.`) actually correct?**
  _`SequenceManifest` has 312 INFERRED edges - model-reasoned connections that need verification._
- **Are the 268 inferred relationships involving `ArtifactRef` (e.g. with `Tests for repo-owned visualization helpers.` and `_FakeVistaBackend`) actually correct?**
  _`ArtifactRef` has 268 INFERRED edges - model-reasoned connections that need verification._
- **Are the 245 inferred relationships involving `MethodId` (e.g. with `_FakeVistaBackend` and `Focused tests for the Ray-backed pipeline core.`) actually correct?**
  _`MethodId` has 245 INFERRED edges - model-reasoned connections that need verification._