# Graph Report - prml-vslam  (2026-05-10)

## Corpus Check
- 263 files · ~606,033 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4187 nodes · 22976 edges · 41 communities detected
- Extraction: 24% EXTRACTED · 76% INFERRED · 0% AMBIGUOUS · INFERRED: 17450 edges (avg confidence: 0.56)
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
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]

## God Nodes (most connected - your core abstractions)
1. `StageKey` - 627 edges
2. `RunConfig` - 381 edges
3. `MethodId` - 378 edges
4. `PathConfig` - 323 edges
5. `ArtifactRef` - 320 edges
6. `RunSnapshot` - 313 edges
7. `SequenceManifest` - 310 edges
8. `ReferenceSource` - 303 edges
9. `StageRuntimeStatus` - 280 edges
10. `StageRuntimeUpdate` - 269 edges

## Surprising Connections (you probably didn't know these)
- `path()` --calls--> `test_source_materialization_does_not_import_stage_package()`  [INFERRED]
  src/prml_vslam/pipeline/sinks/jsonl.py → tests/test_package_exports.py
- `load_evaluation()` --calls--> `test_trajectory_evaluation_service_loads_pipeline_generated_artifact()`  [INFERRED]
  src/prml_vslam/eval/protocols.py → tests/test_app.py
- `load_tum_trajectory()` --calls--> `test_load_tum_trajectory_normalizes_rounded_quaternions()`  [INFERRED]
  src/prml_vslam/utils/geometry.py → tests/test_geometry.py
- `PathConfig` --calls--> `test_path_config_is_immutable_after_construction()`  [INFERRED]
  src/prml_vslam/utils/path_config.py → tests/test_path_config.py
- `Console` --uses--> `Focused tests for the Rich-backed console wrapper.`  [INFERRED]
  src/prml_vslam/utils/console.py → tests/test_console.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.01
Nodes (428): resolve_sequence_dir(), Convert an ADVIO pose CSV into a TUM trajectory file., write_advio_pose_tum(), resolve(), _apply_snapshot_fallbacks(), _candidate_from_root(), _canonical_path_rows(), _derive_slam_artifacts() (+420 more)

### Community 1 - "Community 1"
Cohesion: 0.01
Nodes (394): build_advio_comparison_trajectories(), build_crowd_density_figure(), build_local_readiness_figure(), build_scene_attribute_figure(), build_scene_mix_figure(), handle_advio_preview_action(), load_advio_explorer_sample(), Controller helpers for the ADVIO Streamlit page. (+386 more)

### Community 2 - "Community 2"
Cohesion: 0.02
Nodes (299): artifact_ref(), Build one stable artifact reference for a materialized path., Return neutral visualization items for completed durable artifacts., Describe one neutral sink-facing visualization item.      The item carries seman, Live observer update emitted by a running stage runtime.      Updates are immuta, Name the neutral visualization action requested from observer sinks., Inputs required to build one reconstruction artifact., ReconstructionInputSourceKind (+291 more)

### Community 3 - "Community 3"
Cohesion: 0.01
Nodes (258): build_advio_page_data(), _scene_rows(), AdvioDownloadManager, _ensure_directory_parent(), Return the cache directory used for downloaded scene archives., Return one catalog scene by id., Return local availability status for every catalog scene., Download selected ADVIO scenes and extract the requested modalities. (+250 more)

### Community 4 - "Community 4"
Cohesion: 0.02
Nodes (331): transform_trajectory_with_alignment(), GroundAlignmentMetadata, GroundPlaneModel, GroundPlaneVisualizationHint, Alignment result DTOs shared outside the alignment package.  These datamodels de, Dominant ground-plane hypothesis expressed in native ``world`` coordinates., Finite plane-patch geometry ready for visualization consumers., Result of one derived ground-plane alignment attempt.      When :attr:`applied` (+323 more)

### Community 5 - "Community 5"
Cohesion: 0.05
Nodes (273): InputArtifactDiagnostics, Inspection helpers for persisted pipeline run artifact roots., One submitted run attempt found in a persisted event log., Structured inspection result for one persisted pipeline run., Discover method-level run roots under the configured artifact directory., Load typed metadata and path inventory for one persisted run root., One selectable persisted method-level run artifact root., Shallow diagnostics for materialized offline input artifacts. (+265 more)

### Community 6 - "Community 6"
Cohesion: 0.05
Nodes (305): MethodId, PipelineBackend, Execute, monitor, and tear down pipeline runs.      Implementations own the conc, Start one run and return the stable run identifier.          Args:             r, Request graceful stop for one active run., Return the latest projected metadata view for one run., Return recent runtime events for one run.          Args:             run_id: Sta, Resolve one target transient payload ref into a local array. (+297 more)

### Community 7 - "Community 7"
Cohesion: 0.01
Nodes (181): artifact_visualizations(), _render_reconstruction(), _render_slam_reference_comparison(), get_events(), get_snapshot(), Backend boundary between launch surfaces and execution substrates.  This module, _coordinator_actor_options(), RayPipelineBackend (+173 more)

### Community 8 - "Community 8"
Cohesion: 0.05
Nodes (183): BenchmarkReference, DatasetId, DenseCloudEvaluationArtifact, DenseCloudEvaluationSelection, ErrorSeries, EvaluationArtifact, EvaluationSelection, FrameSelectionConfig (+175 more)

### Community 9 - "Community 9"
Cohesion: 0.04
Nodes (143): SlamOutputPolicy, BaseConfig, build_run_config(), CloudEvaluationStageConfig, CloudMetricId, _compile_run_plan(), DenseCloudSelectionConfig, GroundAlignmentStageConfig (+135 more)

### Community 10 - "Community 10"
Cohesion: 0.03
Nodes (115): Canonical ViSTA-SLAM backend adapter (offline + streaming)., ViSTA-SLAM backend implementing offline and streaming contracts., Load upstream OnlineSLAM and retain backend-owned streaming state., Consume one streaming frame through the active ViSTA runtime., Retrieve pending ViSTA live updates without exposing runtime state., Finalize the active ViSTA streaming runtime and clear it., Run ViSTA-SLAM over normalized offline observations and persist artifacts., VistaSlamBackend (+107 more)

### Community 11 - "Community 11"
Cohesion: 0.04
Nodes (133): advio_basis_metadata(), advio_basis_provenance(), AdvioBasisMetadata, AdvioRawCoordinateBasis, basis_for_pose_source(), _flatten_matrix(), _pose_matrix(), ADVIO coordinate-basis normalization helpers.  ADVIO stores Apple-family traject (+125 more)

### Community 12 - "Community 12"
Cohesion: 0.07
Nodes (34): Replay clock used by dataset and video source streams., Select whether replay follows source timing or returns observations immediately., Apply source-timestamp pacing for real-time replay., Reset the clock baseline for a new replay loop or connection., Sleep until the replay timestamp should be emitted., ReplayClock, ReplayMode, ImageSequenceObservationSource (+26 more)

### Community 13 - "Community 13"
Cohesion: 0.09
Nodes (38): build_pipeline_snapshot_render_model(), _coerce_int_metric(), _compute_evo_preview(), _format_latency(), _format_optional_rate(), _format_queue(), _format_resources(), _format_tasks() (+30 more)

### Community 14 - "Community 14"
Cohesion: 0.13
Nodes (20): _request_plan_paths(), _rgbd_benchmark_inputs(), _slam_artifacts(), test_ground_alignment_runtime_returns_stage_result(), test_reconstruction_runtime_omits_mesh_visualization_when_mesh_artifact_absent(), test_reconstruction_runtime_returns_reconstruction_artifacts(), test_summary_runtime_returns_run_summary_and_retains_manifests(), test_trajectory_evaluation_runtime_returns_eval_payload() (+12 more)

### Community 15 - "Community 15"
Cohesion: 0.15
Nodes (31): _ancestor_entity_paths(), _component_columns(), _keyed_point_cloud_snapshots(), _latest_live_model_snapshot(), _latest_transform_matrix_before_or_at_log_tick(), load_recording_summary(), _point_cloud_snapshot(), _points_array() (+23 more)

### Community 16 - "Community 16"
Cohesion: 0.14
Nodes (25): _add_point_cloud_trace(), _add_trajectory_trace(), _apply_comparison_layout(), _build_figure(), build_reference_reconstruction_figure(), build_slam_reference_comparison_figure(), _combined_bounds(), _decimate_mesh() (+17 more)

### Community 17 - "Community 17"
Cohesion: 0.17
Nodes (2): Tests for package-root public export surfaces., test_source_materialization_does_not_import_stage_package()

### Community 18 - "Community 18"
Cohesion: 0.36
Nodes (4): test_resolve_issue_moves_record_to_resolved_collection(), test_resolve_refactor_moves_record_to_resolved_collection(), test_resolve_todo_moves_record_to_resolved_collection(), _write_toml()

### Community 19 - "Community 19"
Cohesion: 0.67
Nodes (1): Regression checks for removed pipeline compatibility surfaces.

### Community 20 - "Community 20"
Cohesion: 1.0
Nodes (1): Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays

### Community 21 - "Community 21"
Cohesion: 1.0
Nodes (1): Ray-specific helpers for future stage runtime deployment.  This module intention

### Community 22 - "Community 22"
Cohesion: 1.0
Nodes (1): Return the human-readable label shown in plan previews.

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (1): Return whether ``exc`` looks like a transient local Ray connection failure.

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (1): Deserialize one IPC payload back into the target validated model type.

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): Return the compact source label used in logs and diagnostics.

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): Return the short user-facing dataset label.

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): Connect to the source and prepare subsequent blocking observation reads.

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

### Community 34 - "Community 34"
Cohesion: 1.0
Nodes (1): Return the human-readable label shown in plan previews.

### Community 35 - "Community 35"
Cohesion: 1.0
Nodes (1): Single TODO/FIXME marker found in a Python source file.

### Community 36 - "Community 36"
Cohesion: 1.0
Nodes (1): Parse CLI flags for optional marker detail output.

### Community 37 - "Community 37"
Cohesion: 1.0
Nodes (1): Extract TODO/FIXME comment markers from file lines.

### Community 38 - "Community 38"
Cohesion: 1.0
Nodes (1): Count high-level line statistics for Python files under root.

### Community 39 - "Community 39"
Cohesion: 1.0
Nodes (1): Render a detailed Rich table for one marker kind.

### Community 40 - "Community 40"
Cohesion: 1.0
Nodes (1): Print LOC statistics for src/ and tests/.

## Knowledge Gaps
- **243 isolated node(s):** `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`, `Frame preprocessing helpers for ViSTA-SLAM.`, `One RGB frame prepared for upstream ViSTA ingestion.`, `Use the exact upstream ViSTA crop-and-resize helper path.`, `Convert one upstream ViSTA array-like payload into a numpy array.` (+238 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 17`** (12 nodes): `test_package_exports.py`, `Tests for package-root public export surfaces.`, `test_executable_stage_packages_export_canonical_surfaces()`, `test_interfaces_package_exports_only_canonical_pose_surface()`, `test_methods_package_exports_slam_surfaces()`, `test_pipeline_contracts_package_is_not_a_compatibility_hub()`, `test_pipeline_package_exports_only_minimal_public_surface()`, `test_reconstruction_package_exports_runtime_surfaces_without_harness()`, `test_replay_package_exports_only_replay_primitives()`, `test_source_materialization_does_not_import_stage_package()`, `test_sources_package_exports_source_owned_contracts()`, `test_vista_package_is_the_only_canonical_vista_surface()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 19`** (3 nodes): `test_removed_pipeline_compatibility_surface.py`, `Regression checks for removed pipeline compatibility surfaces.`, `test_removed_pipeline_compatibility_names_stay_deleted()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 20`** (2 nodes): `streamlit_app.py`, `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (2 nodes): `ray.py`, `Ray-specific helpers for future stage runtime deployment.  This module intention`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 22`** (1 nodes): `Return the human-readable label shown in plan previews.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (1 nodes): `Return whether ``exc`` looks like a transient local Ray connection failure.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (1 nodes): `Deserialize one IPC payload back into the target validated model type.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (1 nodes): `Return the compact source label used in logs and diagnostics.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `Return the short user-facing dataset label.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `Connect to the source and prepare subsequent blocking observation reads.`
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
- **Thin community `Community 34`** (1 nodes): `Return the human-readable label shown in plan previews.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (1 nodes): `Single TODO/FIXME marker found in a Python source file.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 36`** (1 nodes): `Parse CLI flags for optional marker detail output.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 37`** (1 nodes): `Extract TODO/FIXME comment markers from file lines.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 38`** (1 nodes): `Count high-level line statistics for Python files under root.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 39`** (1 nodes): `Render a detailed Rich table for one marker kind.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 40`** (1 nodes): `Print LOC statistics for src/ and tests/.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Test package helpers and suites for PRML VSLAM.` connect `Community 3` to `Community 0`, `Community 1`, `Community 2`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 9`, `Community 10`, `Community 11`, `Community 12`, `Community 16`?**
  _High betweenness centrality (0.124) - this node is a cross-community bridge._
- **Why does `StageKey` connect `Community 6` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 7`, `Community 8`, `Community 9`, `Community 11`, `Community 13`, `Community 14`?**
  _High betweenness centrality (0.094) - this node is a cross-community bridge._
- **Why does `path()` connect `Community 0` to `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 10`, `Community 14`, `Community 17`?**
  _High betweenness centrality (0.061) - this node is a cross-community bridge._
- **Are the 624 inferred relationships involving `StageKey` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`StageKey` has 624 INFERRED edges - model-reasoned connections that need verification._
- **Are the 376 inferred relationships involving `RunConfig` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`RunConfig` has 376 INFERRED edges - model-reasoned connections that need verification._
- **Are the 375 inferred relationships involving `MethodId` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`MethodId` has 375 INFERRED edges - model-reasoned connections that need verification._
- **Are the 303 inferred relationships involving `PathConfig` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`PathConfig` has 303 INFERRED edges - model-reasoned connections that need verification._