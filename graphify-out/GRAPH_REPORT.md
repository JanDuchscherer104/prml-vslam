# Graph Report - pr88-normalized-source-boundary  (2026-06-19)

## Corpus Check
- 287 files · ~1,086,194 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4812 nodes · 26138 edges · 28 communities detected
- Extraction: 26% EXTRACTED · 74% INFERRED · 0% AMBIGUOUS · INFERRED: 19415 edges (avg confidence: 0.57)
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

## God Nodes (most connected - your core abstractions)
1. `StageKey` - 619 edges
2. `DatasetId` - 581 edges
3. `SequenceManifest` - 490 edges
4. `PathConfig` - 472 edges
5. `FrameSelectionConfig` - 457 edges
6. `MethodId` - 433 edges
7. `PreparedBenchmarkInputs` - 391 edges
8. `ReferenceSource` - 377 edges
9. `RunConfig` - 367 edges
10. `AdvioSourceConfig` - 346 edges

## Surprising Connections (you probably didn't know these)
- `MetricsPageState` --calls--> `test_metrics_page_state_preserves_persisted_view_fields()`  [INFERRED]
  src/prml_vslam/app/models.py → tests/test_app.py
- `GroundAlignmentMetadata` --uses--> `Focused tests for derived ground-plane alignment.`  [INFERRED]
  src/prml_vslam/interfaces/alignment.py → tests/test_ground_alignment.py
- `SequenceManifest` --uses--> `Small runtime sources used by focused pipeline smoke tests.`  [INFERRED]
  src/prml_vslam/sources/contracts.py → tests/pipeline_testing_support.py
- `SequenceManifest` --uses--> `Minimal offline source for pipeline smoke tests.`  [INFERRED]
  src/prml_vslam/sources/contracts.py → tests/pipeline_testing_support.py
- `SequenceManifest` --uses--> `Finite in-memory packet stream for streaming smoke tests.`  [INFERRED]
  src/prml_vslam/sources/contracts.py → tests/pipeline_testing_support.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.01
Nodes (506): build_advio_page_data(), handle_advio_preview_action(), _scene_rows(), sync_advio_download_state(), sync_advio_preview_state(), _apply_snapshot_fallbacks(), _candidate_from_root(), _canonical_path_rows() (+498 more)

### Community 1 - "Community 1"
Cohesion: 0.02
Nodes (441): GroundAlignmentMetadata, InputArtifactDiagnostics, Inspection helpers for persisted pipeline run artifact roots., One submitted run attempt found in a persisted event log., Structured inspection result for one persisted pipeline run., Discover method-level run roots under the configured artifact directory., Load typed metadata and path inventory for one persisted run root., One selectable persisted method-level run artifact root. (+433 more)

### Community 2 - "Community 2"
Cohesion: 0.01
Nodes (411): interpolate_trajectory_poses(), _nearest_timestamp_indices(), ADVIO trajectory interpolation helpers., Interpolate positions and nearest-neighbor rotations at requested timestamps., GroundPlaneModel, GroundPlaneVisualizationHint, Alignment result DTOs shared outside the alignment package.  These datamodels de, Dominant ground-plane hypothesis expressed in native ``world`` coordinates. (+403 more)

### Community 3 - "Community 3"
Cohesion: 0.01
Nodes (349): Controller helpers for the ADVIO Streamlit page., Persist the current ADVIO download-form state., Keep persisted preview state aligned with the runtime snapshot., Apply one preview-form action and return an error message when it fails., AdvioEnvironment, AdvioPeopleLevel, Normalize and validate explicit scene selections., Return the canonical ADVIO folder name used on disk. (+341 more)

### Community 4 - "Community 4"
Cohesion: 0.01
Nodes (323): AdvioUpstreamMetadata, Describe the committed upstream ADVIO metadata sources for the adapter., AdvioDatasetService, AdvioDownloadManager, config_warnings(), normalized_profile_for_source_config(), _normalized_source_fps(), _source_reference_cloud_available() (+315 more)

### Community 5 - "Community 5"
Cohesion: 0.02
Nodes (303): AdvioDownloadManager, _ensure_directory_parent(), Return the cache directory used for downloaded scene archives., Return one catalog scene by id., Return local availability status for every catalog scene., Download selected ADVIO scenes and extract complete scene payloads., advio_basis_metadata(), advio_basis_provenance() (+295 more)

### Community 6 - "Community 6"
Cohesion: 0.09
Nodes (331): MethodId, AdvioSourceConfig, Record3DDatasetSourceConfig, RunConfig, SourceStageConfig, TumRgbdSourceConfig, VideoSourceConfig, Console (+323 more)

### Community 7 - "Community 7"
Cohesion: 0.02
Nodes (207): _build_artifacts(), _ensure_uint8_rgb_from_uimg(), _estimate_camera_intrinsics_from_frame(), _InProcessManager, _InProcessValue, Mast3rSlamBackend, Mast3rSlamSession, Canonical MASt3R-SLAM backend adapter (offline + streaming).  This adapter wraps (+199 more)

### Community 8 - "Community 8"
Cohesion: 0.03
Nodes (216): Trajectory-alignment contracts shared by evaluation and visualization.  Trajecto, Describe how trajectories are aligned before metric computation., State whether an alignment may publish a downstream dense cloud., Persist an explicit trajectory alignment used for diagnostics or metrics., TrajectoryAlignmentArtifact, TrajectoryAlignmentCloudUseStatus, TrajectoryAlignmentMode, CloudAlignmentArtifact (+208 more)

### Community 9 - "Community 9"
Cohesion: 0.03
Nodes (135): BaseConfig, CloudAlignmentStageConfig, CloudEvaluationStageConfig, CloudMetricId, _collect_unknown_field_warnings(), _compile_run_plan(), DenseCloudSelectionConfig, _discriminator_matches() (+127 more)

### Community 10 - "Community 10"
Cohesion: 0.02
Nodes (178): build_advio_comparison_trajectories(), build_crowd_density_figure(), build_local_readiness_figure(), build_scene_attribute_figure(), build_scene_mix_figure(), Plotly figure builders for the ADVIO dataset page., Build a crowd-density composition chart., Build a scene-attribute prevalence chart. (+170 more)

### Community 11 - "Community 11"
Cohesion: 0.03
Nodes (109): Write the repository's canonical single-camera intrinsics YAML schema., write_camera_intrinsics_yaml(), Replay clock used by dataset and video source streams., Select whether replay follows source timing or returns observations immediately., Apply source-timestamp pacing for real-time replay., Reset the clock baseline for a new replay loop or connection., Sleep until the replay timestamp should be emitted., ReplayClock (+101 more)

### Community 12 - "Community 12"
Cohesion: 0.02
Nodes (120): ArxivSourceSpec, download_file(), fetch_pdf(), fetch_tex_source(), from_json(), load_manifest(), main(), normalize_member_path() (+112 more)

### Community 13 - "Community 13"
Cohesion: 0.11
Nodes (34): build_pipeline_snapshot_render_model(), _coerce_int_metric(), _format_latency(), _format_optional_rate(), _format_queue(), _format_resources(), _format_tasks(), _format_throughput() (+26 more)

### Community 14 - "Community 14"
Cohesion: 0.09
Nodes (22): caller_namespace(), configure_logging(), _ConsoleLogFormatter, _ConsoleLogHighlighter, _display_name(), from_callsite(), get_console(), _qualify_namespace() (+14 more)

### Community 15 - "Community 15"
Cohesion: 0.25
Nodes (1): Backend boundary between launch surfaces and execution substrates.  This module

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
Nodes (1): Deserialize one IPC payload back into the target validated model type.

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (1): Return the human-readable label shown in plan previews.

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (1): Return whether ``exc`` looks like a transient local Ray connection failure.

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): Build one spec from one JSON object.

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): Return the net code-line delta.

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): Return the path that should own this change in reports.

## Knowledge Gaps
- **269 isolated node(s):** `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`, `Frame preprocessing helpers for ViSTA-SLAM.`, `One RGB frame prepared for upstream ViSTA ingestion.`, `Use the exact upstream ViSTA crop-and-resize helper path.`, `Convert one upstream ViSTA array-like payload into a numpy array.` (+264 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 15`** (8 nodes): `get_events()`, `get_snapshot()`, `Backend boundary between launch surfaces and execution substrates.  This module`, `read_payload()`, `shutdown()`, `stop_run()`, `submit_run()`, `backend.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
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
- **Thin community `Community 22`** (1 nodes): `Deserialize one IPC payload back into the target validated model type.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (1 nodes): `Return the human-readable label shown in plan previews.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (1 nodes): `Return whether ``exc`` looks like a transient local Ray connection failure.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (1 nodes): `Build one spec from one JSON object.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `Return the net code-line delta.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `Return the path that should own this change in reports.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Test package helpers and suites for PRML VSLAM.` connect `Community 9` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 10`, `Community 11`?**
  _High betweenness centrality (0.103) - this node is a cross-community bridge._
- **Why does `path()` connect `Community 0` to `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 7`, `Community 8`, `Community 11`, `Community 12`?**
  _High betweenness centrality (0.069) - this node is a cross-community bridge._
- **Why does `StageKey` connect `Community 6` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 5`, `Community 7`, `Community 8`, `Community 9`?**
  _High betweenness centrality (0.061) - this node is a cross-community bridge._
- **Are the 616 inferred relationships involving `StageKey` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`StageKey` has 616 INFERRED edges - model-reasoned connections that need verification._
- **Are the 578 inferred relationships involving `DatasetId` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`DatasetId` has 578 INFERRED edges - model-reasoned connections that need verification._
- **Are the 487 inferred relationships involving `SequenceManifest` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`SequenceManifest` has 487 INFERRED edges - model-reasoned connections that need verification._
- **Are the 451 inferred relationships involving `PathConfig` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`PathConfig` has 451 INFERRED edges - model-reasoned connections that need verification._