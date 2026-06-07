# Graph Report - prml-vslam  (2026-06-07)

## Corpus Check
- 269 files · ~1,062,554 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4085 nodes · 20192 edges · 30 communities detected
- Extraction: 29% EXTRACTED · 71% INFERRED · 0% AMBIGUOUS · INFERRED: 14347 edges (avg confidence: 0.58)
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
1. `StageKey` - 451 edges
2. `SequenceManifest` - 333 edges
3. `ArtifactRef` - 287 edges
4. `MethodId` - 276 edges
5. `PreparedBenchmarkInputs` - 262 edges
6. `StageRuntimeStatus` - 243 edges
7. `PathConfig` - 240 edges
8. `RunConfig` - 227 edges
9. `DatasetId` - 206 edges
10. `StageRuntimeUpdate` - 202 edges

## Surprising Connections (you probably didn't know these)
- `path()` --calls--> `test_source_materialization_does_not_import_stage_package()`  [INFERRED]
  src/prml_vslam/pipeline/sinks/jsonl.py → tests/test_package_exports.py
- `PathConfig` --calls--> `test_path_config_is_immutable_after_construction()`  [INFERRED]
  src/prml_vslam/utils/path_config.py → tests/test_path_config.py
- `Console` --uses--> `Focused tests for the Rich-backed console wrapper.`  [INFERRED]
  src/prml_vslam/utils/console.py → tests/test_console.py
- `SequenceManifest` --uses--> `Small runtime sources used by focused pipeline smoke tests.`  [INFERRED]
  src/prml_vslam/sources/contracts.py → tests/pipeline_testing_support.py
- `SequenceManifest` --uses--> `Minimal offline source for pipeline smoke tests.`  [INFERRED]
  src/prml_vslam/sources/contracts.py → tests/pipeline_testing_support.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.02
Nodes (462): GroundAlignmentMetadata, InputArtifactDiagnostics, Inspection helpers for persisted pipeline run artifact roots., One submitted run attempt found in a persisted event log., Structured inspection result for one persisted pipeline run., Discover method-level run roots under the configured artifact directory., Load typed metadata and path inventory for one persisted run root., One selectable persisted method-level run artifact root. (+454 more)

### Community 1 - "Community 1"
Cohesion: 0.01
Nodes (475): _build_artifacts(), Write a raw ADVIO trajectory as a normalized RDF TUM artifact., write_advio_rdf_tum(), resolve_sequence_dir(), Convert an ADVIO pose CSV into a TUM trajectory file., write_advio_pose_tum(), resolve(), _apply_snapshot_fallbacks() (+467 more)

### Community 2 - "Community 2"
Cohesion: 0.01
Nodes (309): _ensure_uint8_rgb_from_uimg(), _estimate_camera_intrinsics_from_frame(), _InProcessManager, _InProcessValue, Mast3rSlamBackend, Mast3rSlamSession, Canonical MASt3R-SLAM backend adapter (offline + streaming).  This adapter wraps, Estimate model-raster intrinsics from a MASt3R keyframe pointmap. (+301 more)

### Community 3 - "Community 3"
Cohesion: 0.01
Nodes (348): build_advio_page_data(), handle_advio_preview_action(), load_advio_explorer_sample(), _scene_rows(), sync_advio_download_state(), sync_advio_preview_state(), archive_member_matches(), list_local_sequence_ids() (+340 more)

### Community 4 - "Community 4"
Cohesion: 0.03
Nodes (392): Controller helpers for the ADVIO Streamlit page., Persist the current ADVIO download-form state., Persist the current explorer selection and load its offline sample., Keep persisted preview state aligned with the runtime snapshot., Apply one preview-form action and return an error message when it fails., MethodId, BaseData, AppContext (+384 more)

### Community 5 - "Community 5"
Cohesion: 0.02
Nodes (267): AdvioDownloadManager, _ensure_directory_parent(), Return the cache directory used for downloaded scene archives., Return one catalog scene by id., Return local availability status for every catalog scene., Download selected ADVIO scenes and extract the requested modalities., advio_basis_metadata(), advio_basis_provenance() (+259 more)

### Community 6 - "Community 6"
Cohesion: 0.01
Nodes (258): GroundPlaneModel, GroundPlaneVisualizationHint, Alignment result DTOs shared outside the alignment package.  These datamodels de, Dominant ground-plane hypothesis expressed in native ``world`` coordinates., Finite plane-patch geometry ready for visualization consumers., Result of one derived ground-plane alignment attempt.      When :attr:`applied`, _frame_transform_from_vista_pose(), Normalize one upstream ViSTA pose matrix into the canonical repo transform DTO. (+250 more)

### Community 7 - "Community 7"
Cohesion: 0.02
Nodes (186): build_advio_comparison_trajectories(), build_crowd_density_figure(), build_local_readiness_figure(), build_scene_attribute_figure(), build_scene_mix_figure(), Plotly figure builders for the ADVIO dataset page., Build a crowd-density composition chart., Build a scene-attribute prevalence chart. (+178 more)

### Community 8 - "Community 8"
Cohesion: 0.03
Nodes (141): BaseConfig, _advio_native_fps(), CloudAlignmentStageConfig, CloudEvaluationStageConfig, CloudMetricId, _collect_unknown_field_warnings(), _compile_run_plan(), config_warnings() (+133 more)

### Community 9 - "Community 9"
Cohesion: 0.03
Nodes (73): extract_pose_position(), _measure_fps(), PacketSessionMetrics, PacketSessionRuntime, _positions_to_array(), Return packet-rate snapshot fields., Return backend-keyframe snapshot fields., Return the current metrics in snapshot-ready form. (+65 more)

### Community 10 - "Community 10"
Cohesion: 0.07
Nodes (34): Replay clock used by dataset and video source streams., Select whether replay follows source timing or returns observations immediately., Apply source-timestamp pacing for real-time replay., Reset the clock baseline for a new replay loop or connection., Sleep until the replay timestamp should be emitted., ReplayClock, ReplayMode, ImageSequenceObservationSource (+26 more)

### Community 11 - "Community 11"
Cohesion: 0.08
Nodes (48): validate_modalities(), iter_sequence_manifest_observations(), _load_manifest_rgb_inputs(), _load_rgb(), _load_timestamps_ns(), _manifest_provenance(), Source-owned readers for normalized offline observations., Yield RGB observations from a normalized source sequence manifest. (+40 more)

### Community 12 - "Community 12"
Cohesion: 0.1
Nodes (38): build_pipeline_snapshot_render_model(), _coerce_int_metric(), _compute_evo_preview(), _format_latency(), _format_optional_rate(), _format_queue(), _format_resources(), _format_tasks() (+30 more)

### Community 13 - "Community 13"
Cohesion: 0.1
Nodes (21): caller_namespace(), configure_logging(), _ConsoleLogFormatter, _ConsoleLogHighlighter, _display_name(), from_callsite(), get_console(), _qualify_namespace() (+13 more)

### Community 14 - "Community 14"
Cohesion: 0.17
Nodes (2): Tests for package-root public export surfaces., test_source_materialization_does_not_import_stage_package()

### Community 15 - "Community 15"
Cohesion: 0.36
Nodes (4): test_resolve_issue_moves_record_to_resolved_collection(), test_resolve_refactor_moves_record_to_resolved_collection(), test_resolve_todo_moves_record_to_resolved_collection(), _write_toml()

### Community 16 - "Community 16"
Cohesion: 1.0
Nodes (1): Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays

### Community 17 - "Community 17"
Cohesion: 1.0
Nodes (1): Ray-specific helpers for future stage runtime deployment.  This module intention

### Community 18 - "Community 18"
Cohesion: 1.0
Nodes (1): Return the human-readable label shown in plan previews.

### Community 19 - "Community 19"
Cohesion: 1.0
Nodes (1): Return whether ``exc`` looks like a transient local Ray connection failure.

### Community 20 - "Community 20"
Cohesion: 1.0
Nodes (1): Deserialize one IPC payload back into the target validated model type.

### Community 21 - "Community 21"
Cohesion: 1.0
Nodes (1): Return the compact source label used in logs and diagnostics.

### Community 22 - "Community 22"
Cohesion: 1.0
Nodes (1): Return the short user-facing dataset label.

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (1): Connect to the source and prepare subsequent blocking observation reads.

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (1): Disconnect or release the source and any owned runtime resources.

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from a 4x4 homogeneous matrix.

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
- **238 isolated node(s):** `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`, `Frame preprocessing helpers for ViSTA-SLAM.`, `One RGB frame prepared for upstream ViSTA ingestion.`, `Use the exact upstream ViSTA crop-and-resize helper path.`, `Convert one upstream ViSTA array-like payload into a numpy array.` (+233 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 14`** (12 nodes): `test_package_exports.py`, `Tests for package-root public export surfaces.`, `test_executable_stage_packages_export_canonical_surfaces()`, `test_interfaces_package_exports_only_canonical_pose_surface()`, `test_methods_package_exports_slam_surfaces()`, `test_pipeline_contracts_package_is_not_a_compatibility_hub()`, `test_pipeline_package_exports_only_minimal_public_surface()`, `test_reconstruction_package_exports_runtime_surfaces_without_harness()`, `test_replay_package_exports_only_replay_primitives()`, `test_source_materialization_does_not_import_stage_package()`, `test_sources_package_exports_source_owned_contracts()`, `test_vista_package_is_the_only_canonical_vista_surface()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 16`** (2 nodes): `streamlit_app.py`, `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 17`** (2 nodes): `ray.py`, `Ray-specific helpers for future stage runtime deployment.  This module intention`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 18`** (1 nodes): `Return the human-readable label shown in plan previews.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 19`** (1 nodes): `Return whether ``exc`` looks like a transient local Ray connection failure.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 20`** (1 nodes): `Deserialize one IPC payload back into the target validated model type.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (1 nodes): `Return the compact source label used in logs and diagnostics.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 22`** (1 nodes): `Return the short user-facing dataset label.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (1 nodes): `Connect to the source and prepare subsequent blocking observation reads.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (1 nodes): `Disconnect or release the source and any owned runtime resources.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (1 nodes): `Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `Build the shared transform DTO from a 4x4 homogeneous matrix.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `Build one spec from one JSON object.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `Return the net code-line delta.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `Return the path that should own this change in reports.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Test package helpers and suites for PRML VSLAM.` connect `Community 5` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 6`, `Community 7`, `Community 8`, `Community 10`?**
  _High betweenness centrality (0.130) - this node is a cross-community bridge._
- **Why does `StageKey` connect `Community 0` to `Community 1`, `Community 2`, `Community 4`, `Community 5`, `Community 6`, `Community 8`?**
  _High betweenness centrality (0.079) - this node is a cross-community bridge._
- **Why does `SequenceManifest` connect `Community 2` to `Community 0`, `Community 1`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 8`, `Community 11`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **Are the 448 inferred relationships involving `StageKey` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`StageKey` has 448 INFERRED edges - model-reasoned connections that need verification._
- **Are the 330 inferred relationships involving `SequenceManifest` (e.g. with `OfflineSlamBackend` and `StreamingSlamBackend`) actually correct?**
  _`SequenceManifest` has 330 INFERRED edges - model-reasoned connections that need verification._
- **Are the 283 inferred relationships involving `ArtifactRef` (e.g. with `SlamUpdate` and `SlamArtifacts`) actually correct?**
  _`ArtifactRef` has 283 INFERRED edges - model-reasoned connections that need verification._
- **Are the 273 inferred relationships involving `MethodId` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`MethodId` has 273 INFERRED edges - model-reasoned connections that need verification._