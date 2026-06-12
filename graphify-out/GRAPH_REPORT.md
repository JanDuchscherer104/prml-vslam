# Graph Report - prml-vslam  (2026-06-13)

## Corpus Check
- 275 files · ~1,787,241 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4224 nodes · 20351 edges · 39 communities detected
- Extraction: 30% EXTRACTED · 70% INFERRED · 0% AMBIGUOUS · INFERRED: 14306 edges (avg confidence: 0.58)
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

## God Nodes (most connected - your core abstractions)
1. `StageKey` - 494 edges
2. `SequenceManifest` - 349 edges
3. `MethodId` - 288 edges
4. `ArtifactRef` - 287 edges
5. `PathConfig` - 270 edges
6. `PreparedBenchmarkInputs` - 251 edges
7. `StageRuntimeStatus` - 251 edges
8. `RunConfig` - 246 edges
9. `RunSnapshot` - 231 edges
10. `ReferenceSource` - 219 edges

## Surprising Connections (you probably didn't know these)
- `GroundAlignmentMetadata` --uses--> `Focused tests for derived ground-plane alignment.`  [INFERRED]
  src/prml_vslam/interfaces/alignment.py → tests/test_ground_alignment.py
- `SequenceManifest` --uses--> `Small runtime sources used by focused pipeline smoke tests.`  [INFERRED]
  src/prml_vslam/sources/contracts.py → tests/pipeline_testing_support.py
- `SequenceManifest` --uses--> `Minimal offline source for pipeline smoke tests.`  [INFERRED]
  src/prml_vslam/sources/contracts.py → tests/pipeline_testing_support.py
- `SequenceManifest` --uses--> `Finite in-memory packet stream for streaming smoke tests.`  [INFERRED]
  src/prml_vslam/sources/contracts.py → tests/pipeline_testing_support.py
- `SequenceManifest` --uses--> `Minimal streaming-capable source for pipeline smoke tests.`  [INFERRED]
  src/prml_vslam/sources/contracts.py → tests/pipeline_testing_support.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.02
Nodes (353): ArtifactRef, _entity_token(), observation_sequence_artifact_key(), Reference one materialized repository artifact by path and fingerprint., Project source output contracts into durable stage artifact refs., Return the source-stage artifact key for one prepared trajectory., Return the source-stage artifact key for one prepared static cloud., Return the source-stage artifact key for one static cloud metadata file. (+345 more)

### Community 1 - "Community 1"
Cohesion: 0.01
Nodes (366): _build_artifacts(), resolve(), _attempt_rows(), _candidate_label(), _inventory_rows(), _metadata_json(), _path_rows(), _raw_preview_language() (+358 more)

### Community 2 - "Community 2"
Cohesion: 0.01
Nodes (316): build_advio_page_data(), handle_advio_preview_action(), load_advio_explorer_sample(), Controller helpers for the ADVIO Streamlit page., Persist the current ADVIO download-form state., Persist the current explorer selection and load its offline sample., Keep persisted preview state aligned with the runtime snapshot., Apply one preview-form action and return an error message when it fails. (+308 more)

### Community 3 - "Community 3"
Cohesion: 0.03
Nodes (325): _ensure_uint8_rgb_from_uimg(), _estimate_camera_intrinsics_from_frame(), _InProcessManager, _InProcessValue, Mast3rSlamSession, Canonical MASt3R-SLAM backend adapter (offline + streaming).  This adapter wraps, Estimate model-raster intrinsics from a MASt3R keyframe pointmap., Stateful streaming runtime over the upstream MASt3R-SLAM stack. (+317 more)

### Community 4 - "Community 4"
Cohesion: 0.02
Nodes (265): AdvioDownloadManager, _ensure_directory_parent(), Return the cache directory used for downloaded scene archives., Return one catalog scene by id., Return local availability status for every catalog scene., Download selected ADVIO scenes and extract the requested modalities., archive_member_matches(), list_local_sequence_ids() (+257 more)

### Community 5 - "Community 5"
Cohesion: 0.03
Nodes (224): Persist an explicit trajectory alignment used for diagnostics or metrics., TrajectoryAlignmentArtifact, GroundAlignmentMetadata, Result of one derived ground-plane alignment attempt.      When :attr:`applied`, _apply_snapshot_fallbacks(), _candidate_from_root(), _canonical_path_rows(), _derive_slam_artifacts() (+216 more)

### Community 6 - "Community 6"
Cohesion: 0.02
Nodes (266): advio_basis_metadata(), advio_basis_provenance(), AdvioBasisMetadata, AdvioRawCoordinateBasis, basis_for_pose_source(), _flatten_matrix(), _pose_matrix(), ADVIO coordinate-basis normalization helpers.  ADVIO replay and benchmark surfac (+258 more)

### Community 7 - "Community 7"
Cohesion: 0.02
Nodes (162): artifact_ref(), artifact_visualizations(), Artifact-to-visualization mapping for durable stage outputs., Build one stable artifact reference for a materialized path., Return neutral visualization items for completed durable artifacts., VisualizationItem, write_tum_trajectory(), ape_error_colors() (+154 more)

### Community 8 - "Community 8"
Cohesion: 0.02
Nodes (160): Mast3rSlamBackend, VistaSlamBackend, _build_unfiltered_cloud_export(), build_vista_artifacts(), _frame_transform_from_vista_pose(), _load_native_point_cloud(), _load_unfiltered_cloud_colors(), Normalize one upstream ViSTA pose matrix into the canonical repo transform DTO. (+152 more)

### Community 9 - "Community 9"
Cohesion: 0.03
Nodes (111): BaseConfig, CloudAlignmentStageConfig, CloudEvaluationStageConfig, CloudMetricId, _compile_run_plan(), DenseCloudSelectionConfig, GroundAlignmentStageConfig, Open3dTsdfBackendConfig (+103 more)

### Community 10 - "Community 10"
Cohesion: 0.02
Nodes (166): build_advio_comparison_trajectories(), build_crowd_density_figure(), build_local_readiness_figure(), build_scene_attribute_figure(), build_scene_mix_figure(), Plotly figure builders for the ADVIO dataset page., Build a crowd-density composition chart., Build a scene-attribute prevalence chart. (+158 more)

### Community 11 - "Community 11"
Cohesion: 0.02
Nodes (135): ArxivSourceSpec, download_file(), fetch_pdf(), fetch_tex_source(), from_json(), load_manifest(), main(), normalize_member_path() (+127 more)

### Community 12 - "Community 12"
Cohesion: 0.05
Nodes (108): build_coverage_matrix(), build_heatmap_data(), build_leaderboard(), build_per_sequence_table(), CoverageCell, CoverageMatrix, HeatmapData, LeaderboardRow (+100 more)

### Community 13 - "Community 13"
Cohesion: 0.04
Nodes (83): build_pipeline_snapshot_render_model(), build_pipeline_viewer_link_model(), _coerce_int_metric(), _format_latency(), _format_optional_rate(), _format_queue(), _format_resources(), _format_tasks() (+75 more)

### Community 14 - "Community 14"
Cohesion: 0.09
Nodes (75): Trajectory-alignment contracts shared by evaluation and visualization.  Trajecto, Describe how trajectories are aligned before metric computation., State whether an alignment may publish a downstream dense cloud., TrajectoryAlignmentCloudUseStatus, TrajectoryAlignmentMode, CloudAlignmentArtifact, CloudAlignmentSelection, from_evo_statistics() (+67 more)

### Community 15 - "Community 15"
Cohesion: 0.08
Nodes (32): Replay clock used by dataset and video source streams., Select whether replay follows source timing or returns observations immediately., Apply source-timestamp pacing for real-time replay., Reset the clock baseline for a new replay loop or connection., Sleep until the replay timestamp should be emitted., ReplayClock, ReplayMode, ImageSequenceObservationSource (+24 more)

### Community 16 - "Community 16"
Cohesion: 0.25
Nodes (8): _load_depth(), load_observation_sequence_index(), _load_rgb(), Source-owned file-backed observation sequence loading.  The source reads durable, Yield observations by resolving payload paths from the sequence ref.          RG, Load and validate one durable observation sequence index.      The JSON payload, _resolve_payload(), _validate_index_matches_ref()

### Community 17 - "Community 17"
Cohesion: 0.31
Nodes (5): _load_agents_db_module(), test_resolve_issue_moves_record_to_resolved_collection(), test_resolve_refactor_moves_record_to_resolved_collection(), test_resolve_todo_moves_record_to_resolved_collection(), _write_toml()

### Community 18 - "Community 18"
Cohesion: 1.0
Nodes (1): Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays

### Community 19 - "Community 19"
Cohesion: 1.0
Nodes (1): Ray-specific helpers for future stage runtime deployment.  This module intention

### Community 20 - "Community 20"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.

### Community 21 - "Community 21"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from a 4x4 homogeneous matrix.

### Community 22 - "Community 22"
Cohesion: 1.0
Nodes (1): Return the compact source label used in logs and diagnostics.

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (1): Connect to the source and prepare subsequent blocking observation reads.

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (1): Disconnect or release the source and any owned runtime resources.

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): Return the short user-facing dataset label.

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): Deserialize one IPC payload back into the target validated model type.

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): Return the human-readable label shown in plan previews.

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): Return whether ``exc`` looks like a transient local Ray connection failure.

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): Build one spec from one JSON object.

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): Return the net code-line delta.

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (1): Return the path that should own this change in reports.

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (1): Load a JSONL manifest into typed source specs.

### Community 33 - "Community 33"
Cohesion: 1.0
Nodes (1): Download one URL to one local path.

### Community 34 - "Community 34"
Cohesion: 1.0
Nodes (1): Extract a tar archive while rejecting unsafe paths.

### Community 35 - "Community 35"
Cohesion: 1.0
Nodes (1): Normalize one archive member path and reject traversal segments.

### Community 36 - "Community 36"
Cohesion: 1.0
Nodes (1): Download and extract one arXiv TeX source tree.

### Community 37 - "Community 37"
Cohesion: 1.0
Nodes (1): Download one PDF if the manifest entry requests it.

### Community 38 - "Community 38"
Cohesion: 1.0
Nodes (1): Run the downloader CLI.

## Knowledge Gaps
- **263 isolated node(s):** `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`, `Frame preprocessing helpers for ViSTA-SLAM.`, `One RGB frame prepared for upstream ViSTA ingestion.`, `Use the exact upstream ViSTA crop-and-resize helper path.`, `Convert one upstream ViSTA array-like payload into a numpy array.` (+258 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 18`** (2 nodes): `streamlit_app.py`, `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 19`** (2 nodes): `ray.py`, `Ray-specific helpers for future stage runtime deployment.  This module intention`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 20`** (1 nodes): `Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (1 nodes): `Build the shared transform DTO from a 4x4 homogeneous matrix.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 22`** (1 nodes): `Return the compact source label used in logs and diagnostics.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (1 nodes): `Connect to the source and prepare subsequent blocking observation reads.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (1 nodes): `Disconnect or release the source and any owned runtime resources.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (1 nodes): `Return the short user-facing dataset label.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `Deserialize one IPC payload back into the target validated model type.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `Return the human-readable label shown in plan previews.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `Return whether ``exc`` looks like a transient local Ray connection failure.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `Build one spec from one JSON object.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `Return the net code-line delta.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `Return the path that should own this change in reports.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (1 nodes): `Load a JSONL manifest into typed source specs.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 33`** (1 nodes): `Download one URL to one local path.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 34`** (1 nodes): `Extract a tar archive while rejecting unsafe paths.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (1 nodes): `Normalize one archive member path and reject traversal segments.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 36`** (1 nodes): `Download and extract one arXiv TeX source tree.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 37`** (1 nodes): `Download one PDF if the manifest entry requests it.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 38`** (1 nodes): `Run the downloader CLI.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Test package helpers and suites for PRML VSLAM.` connect `Community 9` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 8`, `Community 10`, `Community 15`?**
  _High betweenness centrality (0.177) - this node is a cross-community bridge._
- **Why does `SequenceManifest` connect `Community 0` to `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 8`, `Community 9`, `Community 12`, `Community 13`, `Community 14`?**
  _High betweenness centrality (0.070) - this node is a cross-community bridge._
- **Why does `StageKey` connect `Community 0` to `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 7`, `Community 8`, `Community 9`, `Community 14`?**
  _High betweenness centrality (0.068) - this node is a cross-community bridge._
- **Are the 491 inferred relationships involving `StageKey` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`StageKey` has 491 INFERRED edges - model-reasoned connections that need verification._
- **Are the 346 inferred relationships involving `SequenceManifest` (e.g. with `OfflineSlamBackend` and `StreamingSlamBackend`) actually correct?**
  _`SequenceManifest` has 346 INFERRED edges - model-reasoned connections that need verification._
- **Are the 285 inferred relationships involving `MethodId` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`MethodId` has 285 INFERRED edges - model-reasoned connections that need verification._
- **Are the 283 inferred relationships involving `ArtifactRef` (e.g. with `SlamUpdate` and `SlamArtifacts`) actually correct?**
  _`ArtifactRef` has 283 INFERRED edges - model-reasoned connections that need verification._