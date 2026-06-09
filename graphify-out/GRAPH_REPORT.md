# Graph Report - lingbot-map-origin-main  (2026-06-09)

## Corpus Check
- 272 files · ~1,068,013 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4189 nodes · 19421 edges · 36 communities detected
- Extraction: 31% EXTRACTED · 69% INFERRED · 0% AMBIGUOUS · INFERRED: 13434 edges (avg confidence: 0.58)
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

## God Nodes (most connected - your core abstractions)
1. `StageKey` - 465 edges
2. `SequenceManifest` - 329 edges
3. `ArtifactRef` - 296 edges
4. `MethodId` - 275 edges
5. `PreparedBenchmarkInputs` - 255 edges
6. `StageRuntimeStatus` - 231 edges
7. `PathConfig` - 224 edges
8. `ReferenceSource` - 200 edges
9. `RunConfig` - 193 edges
10. `CameraIntrinsics` - 192 edges

## Surprising Connections (you probably didn't know these)
- `plan_run()` --calls--> `test_plan_run_defaults_to_live_viewer()`  [INFERRED]
  src/prml_vslam/main.py → tests/test_main.py
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
Cohesion: 0.01
Nodes (327): AdvioDownloadManager, _ensure_directory_parent(), Return the cache directory used for downloaded scene archives., Return one catalog scene by id., Return local availability status for every catalog scene., Download selected ADVIO scenes and extract the requested modalities., advio_basis_metadata(), advio_basis_provenance() (+319 more)

### Community 1 - "Community 1"
Cohesion: 0.02
Nodes (283): artifact_ref(), artifact_visualizations(), ArtifactRef, Artifact-to-visualization mapping for durable stage outputs., Reference one materialized repository artifact by path and fingerprint., Build one stable artifact reference for a materialized path., Return neutral visualization items for completed durable artifacts., clean_actor_options() (+275 more)

### Community 2 - "Community 2"
Cohesion: 0.01
Nodes (300): resolve(), BaseConfig, _ConfigFactory, FactoryConfig, from_toml(), _normalize_value(), Shared config and config-as-factory helpers for the repository.  This module own, Render the config as a Rich tree for quick human inspection. (+292 more)

### Community 3 - "Community 3"
Cohesion: 0.02
Nodes (295): _adapt_checkpoint_state_dict(), _as_numpy(), _build_artifacts(), _build_lingbot_artifacts(), _cast_aggregator_for_inference(), _decode_pose_predictions(), _DensePredictionArtifacts, _ensure_uint8_rgb_from_uimg() (+287 more)

### Community 4 - "Community 4"
Cohesion: 0.02
Nodes (313): GroundAlignmentMetadata, GroundPlaneModel, GroundPlaneVisualizationHint, Alignment result DTOs shared outside the alignment package.  These datamodels de, Dominant ground-plane hypothesis expressed in native ``world`` coordinates., Finite plane-patch geometry ready for visualization consumers., Result of one derived ground-plane alignment attempt.      When :attr:`applied`, BaseData (+305 more)

### Community 5 - "Community 5"
Cohesion: 0.02
Nodes (209): _entity_token(), observation_sequence_artifact_key(), Project source output contracts into durable stage artifact refs., Return the source-stage artifact key for one prepared trajectory., Return the source-stage artifact key for one prepared static cloud., Return the source-stage artifact key for one static cloud metadata file., Return the source-stage artifact key for one observation sequence index., reference_cloud_artifact_key() (+201 more)

### Community 6 - "Community 6"
Cohesion: 0.04
Nodes (251): MethodId, BaseConfig, AppContext, AdvioSourceConfig, build_run_config(), CloudAlignmentStageConfig, CloudEvaluationStageConfig, CloudMetricId (+243 more)

### Community 7 - "Community 7"
Cohesion: 0.03
Nodes (184): _apply_snapshot_fallbacks(), _candidate_from_root(), _canonical_path_rows(), _derive_slam_artifacts(), discover_run_artifact_roots(), _file_inventory(), _format_size(), InputArtifactDiagnostics (+176 more)

### Community 8 - "Community 8"
Cohesion: 0.02
Nodes (245): build_crowd_density_figure(), build_advio_page_data(), handle_advio_preview_action(), load_advio_explorer_sample(), _scene_rows(), sync_advio_download_state(), sync_advio_preview_state(), validate_dataset_root() (+237 more)

### Community 9 - "Community 9"
Cohesion: 0.02
Nodes (191): Controller helpers for the ADVIO Streamlit page., Persist the current ADVIO download-form state., Persist the current explorer selection and load its offline sample., Keep persisted preview state aligned with the runtime snapshot., Apply one preview-form action and return an error message when it fails., _build_unfiltered_cloud_export(), build_vista_artifacts(), _load_native_point_cloud() (+183 more)

### Community 10 - "Community 10"
Cohesion: 0.02
Nodes (151): build_advio_comparison_trajectories(), build_local_readiness_figure(), build_scene_attribute_figure(), build_scene_mix_figure(), Plotly figure builders for the ADVIO dataset page., Build a scene-attribute prevalence chart., Build ADVIO explorer overlays with explicit comparison semantics., Build a stacked venue/environment overview for the catalog. (+143 more)

### Community 11 - "Community 11"
Cohesion: 0.02
Nodes (155): Render directly via Rich for structured or non-log output., ArxivSourceSpec, download_file(), fetch_pdf(), fetch_tex_source(), from_json(), load_manifest(), main() (+147 more)

### Community 12 - "Community 12"
Cohesion: 0.03
Nodes (83): Return the user-facing reconstruction label., Configure the minimal Open3D TSDF reconstruction backend.      The repo targets, Return the concrete reconstruction backend type., Instantiate the Open3D TSDF backend while ignoring unrelated kwargs., Describe normalized durable outputs from one reconstruction run.      The minima, ReconstructionArtifacts, ReconstructionMethodId, IntEnum (+75 more)

### Community 13 - "Community 13"
Cohesion: 0.04
Nodes (81): _ape_error_colors(), attach_recording_sinks(), augment_viewer_recording_with_ground_plane(), build_default_blueprint(), create_recording_stream(), _decimate_rows(), _entity_token(), evaluation_metric_root() (+73 more)

### Community 14 - "Community 14"
Cohesion: 0.07
Nodes (34): Replay clock used by dataset and video source streams., Select whether replay follows source timing or returns observations immediately., Apply source-timestamp pacing for real-time replay., Reset the clock baseline for a new replay loop or connection., Sleep until the replay timestamp should be emitted., ReplayClock, ReplayMode, ImageSequenceObservationSource (+26 more)

### Community 15 - "Community 15"
Cohesion: 0.1
Nodes (21): caller_namespace(), configure_logging(), _ConsoleLogFormatter, _ConsoleLogHighlighter, _display_name(), from_callsite(), get_console(), _qualify_namespace() (+13 more)

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
Nodes (1): Connect to the source and prepare subsequent blocking observation reads.

### Community 22 - "Community 22"
Cohesion: 1.0
Nodes (1): Disconnect or release the source and any owned runtime resources.

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (1): Return the short user-facing dataset label.

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (1): Deserialize one IPC payload back into the target validated model type.

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): Return the human-readable label shown in plan previews.

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): Return whether ``exc`` looks like a transient local Ray connection failure.

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): Build one spec from one JSON object.

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): Return the net code-line delta.

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): Return the path that should own this change in reports.

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): Set environment flags that Ray snapshots at import and init time.

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (1): Build the process-wide Ray runtime environment for this backend.

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (1): Own a backend-managed local Ray head process and its reuse metadata.

### Community 33 - "Community 33"
Cohesion: 1.0
Nodes (1): Return a connectable local Ray head address, starting one if needed.

### Community 34 - "Community 34"
Cohesion: 1.0
Nodes (1): Stop any local Ray head owned or tracked by this backend.

### Community 35 - "Community 35"
Cohesion: 1.0
Nodes (1): Return whether ``exc`` looks like a transient local Ray connection failure.

## Knowledge Gaps
- **244 isolated node(s):** `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`, `Frame preprocessing helpers for ViSTA-SLAM.`, `One RGB frame prepared for upstream ViSTA ingestion.`, `Use the exact upstream ViSTA crop-and-resize helper path.`, `Convert one upstream ViSTA array-like payload into a numpy array.` (+239 more)
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
- **Thin community `Community 21`** (1 nodes): `Connect to the source and prepare subsequent blocking observation reads.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 22`** (1 nodes): `Disconnect or release the source and any owned runtime resources.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (1 nodes): `Return the short user-facing dataset label.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (1 nodes): `Deserialize one IPC payload back into the target validated model type.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (1 nodes): `Return the human-readable label shown in plan previews.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `Return whether ``exc`` looks like a transient local Ray connection failure.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `Build one spec from one JSON object.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `Return the net code-line delta.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `Return the path that should own this change in reports.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `Set environment flags that Ray snapshots at import and init time.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `Build the process-wide Ray runtime environment for this backend.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (1 nodes): `Own a backend-managed local Ray head process and its reuse metadata.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 33`** (1 nodes): `Return a connectable local Ray head address, starting one if needed.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 34`** (1 nodes): `Stop any local Ray head owned or tracked by this backend.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (1 nodes): `Return whether ``exc`` looks like a transient local Ray connection failure.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Test package helpers and suites for PRML VSLAM.` connect `Community 0` to `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 9`, `Community 10`, `Community 12`, `Community 14`?**
  _High betweenness centrality (0.136) - this node is a cross-community bridge._
- **Why does `StageKey` connect `Community 6` to `Community 0`, `Community 1`, `Community 2`, `Community 4`, `Community 5`, `Community 7`, `Community 9`?**
  _High betweenness centrality (0.083) - this node is a cross-community bridge._
- **Why does `CameraIntrinsics` connect `Community 4` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 5`, `Community 6`, `Community 9`, `Community 10`, `Community 12`, `Community 13`?**
  _High betweenness centrality (0.063) - this node is a cross-community bridge._
- **Are the 462 inferred relationships involving `StageKey` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`StageKey` has 462 INFERRED edges - model-reasoned connections that need verification._
- **Are the 326 inferred relationships involving `SequenceManifest` (e.g. with `OfflineSlamBackend` and `StreamingSlamBackend`) actually correct?**
  _`SequenceManifest` has 326 INFERRED edges - model-reasoned connections that need verification._
- **Are the 292 inferred relationships involving `ArtifactRef` (e.g. with `SlamUpdate` and `SlamArtifacts`) actually correct?**
  _`ArtifactRef` has 292 INFERRED edges - model-reasoned connections that need verification._
- **Are the 272 inferred relationships involving `MethodId` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`MethodId` has 272 INFERRED edges - model-reasoned connections that need verification._