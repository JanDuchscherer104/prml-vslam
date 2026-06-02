# Graph Report - prml-vslam  (2026-06-02)

## Corpus Check
- 269 files · ~1,723,024 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 3998 nodes · 18480 edges · 33 communities detected
- Extraction: 31% EXTRACTED · 69% INFERRED · 0% AMBIGUOUS · INFERRED: 12679 edges (avg confidence: 0.59)
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

## God Nodes (most connected - your core abstractions)
1. `StageKey` - 439 edges
2. `SequenceManifest` - 306 edges
3. `ArtifactRef` - 270 edges
4. `MethodId` - 253 edges
5. `PreparedBenchmarkInputs` - 234 edges
6. `StageRuntimeStatus` - 230 edges
7. `PathConfig` - 214 edges
8. `RunConfig` - 192 edges
9. `CameraIntrinsics` - 184 edges
10. `ReferenceSource` - 183 edges

## Surprising Connections (you probably didn't know these)
- `Focused tests for derived ground-plane alignment.` --uses--> `GroundAlignmentMetadata`  [INFERRED]
  tests/test_ground_alignment.py → src/prml_vslam/interfaces/alignment.py
- `Small runtime sources used by focused pipeline smoke tests.` --uses--> `SequenceManifest`  [INFERRED]
  tests/pipeline_testing_support.py → src/prml_vslam/sources/contracts.py
- `Minimal offline source for pipeline smoke tests.` --uses--> `SequenceManifest`  [INFERRED]
  tests/pipeline_testing_support.py → src/prml_vslam/sources/contracts.py
- `Finite in-memory packet stream for streaming smoke tests.` --uses--> `SequenceManifest`  [INFERRED]
  tests/pipeline_testing_support.py → src/prml_vslam/sources/contracts.py
- `Minimal streaming-capable source for pipeline smoke tests.` --uses--> `SequenceManifest`  [INFERRED]
  tests/pipeline_testing_support.py → src/prml_vslam/sources/contracts.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.02
Nodes (265): artifact_ref(), artifact_visualizations(), ArtifactRef, Reference one materialized repository artifact by path and fingerprint., Build one stable artifact reference for a materialized path., Return neutral visualization items for completed durable artifacts., clean_actor_options(), put_transient_payload() (+257 more)

### Community 1 - "Community 1"
Cohesion: 0.03
Nodes (318): _ensure_uint8_rgb_from_uimg(), _estimate_camera_intrinsics_from_frame(), _InProcessManager, _InProcessValue, Canonical MASt3R-SLAM backend adapter (offline + streaming).  This adapter wraps, Estimate model-raster intrinsics from a MASt3R keyframe pointmap., Stateful streaming runtime over the upstream MASt3R-SLAM stack., Load the upstream runtime and model state needed before the first frame. (+310 more)

### Community 2 - "Community 2"
Cohesion: 0.02
Nodes (251): AdvioDownloadManager, _ensure_directory_parent(), Return the cache directory used for downloaded scene archives., Return one catalog scene by id., Return local availability status for every catalog scene., Download selected ADVIO scenes and extract the requested modalities., archive_member_matches(), list_local_sequence_ids() (+243 more)

### Community 3 - "Community 3"
Cohesion: 0.02
Nodes (318): _build_artifacts(), advio_basis_metadata(), advio_basis_provenance(), AdvioBasisMetadata, AdvioRawCoordinateBasis, basis_for_pose_source(), _flatten_matrix(), _pose_matrix() (+310 more)

### Community 4 - "Community 4"
Cohesion: 0.02
Nodes (259): resolve(), BaseConfig, _ConfigFactory, FactoryConfig, from_toml(), _normalize_value(), Shared config and config-as-factory helpers for the repository.  This module own, Render the config as a Rich tree for quick human inspection. (+251 more)

### Community 5 - "Community 5"
Cohesion: 0.01
Nodes (151): Mast3rSlamSession, _attempt_rows(), _candidate_label(), _inventory_rows(), _metadata_json(), _path_rows(), _raw_preview_language(), _raw_preview_text() (+143 more)

### Community 6 - "Community 6"
Cohesion: 0.03
Nodes (159): _entity_token(), observation_sequence_artifact_key(), reference_cloud_artifact_key(), reference_cloud_metadata_artifact_key(), reference_point_cloud_sequence_index_artifact_key(), reference_point_cloud_sequence_payload_artifact_key(), reference_point_cloud_sequence_trajectory_artifact_key(), reference_trajectory_artifact_key() (+151 more)

### Community 7 - "Community 7"
Cohesion: 0.02
Nodes (203): build_advio_comparison_trajectories(), build_crowd_density_figure(), build_local_readiness_figure(), build_scene_attribute_figure(), build_scene_mix_figure(), build_advio_page_data(), handle_advio_preview_action(), load_advio_explorer_sample() (+195 more)

### Community 8 - "Community 8"
Cohesion: 0.02
Nodes (168): Controller helpers for the ADVIO Streamlit page., Persist the current ADVIO download-form state., Persist the current explorer selection and load its offline sample., Keep persisted preview state aligned with the runtime snapshot., Apply one preview-form action and return an error message when it fails., build_context(), _build_pages(), _enter_page() (+160 more)

### Community 9 - "Community 9"
Cohesion: 0.02
Nodes (143): Mast3rSlamBackend, VistaSlamBackend, build_slam_backend_config(), Persisted SLAM backend config and backend muxing.  The SLAM stage owns the publi, Whether the backend supports repository trajectory evaluation., Return backend-owned default resource hints., Return backend-specific planning notes surfaced to callers., Configure the canonical MASt3R-SLAM backend.      Hyperparameters for tracking / (+135 more)

### Community 10 - "Community 10"
Cohesion: 0.05
Nodes (154): GroundAlignmentMetadata, Result of one derived ground-plane alignment attempt.      When :attr:`applied`, _apply_snapshot_fallbacks(), _candidate_from_root(), _canonical_path_rows(), _derive_slam_artifacts(), discover_run_artifact_roots(), _file_inventory() (+146 more)

### Community 11 - "Community 11"
Cohesion: 0.02
Nodes (155): Render directly via Rich for structured or non-log output., ArxivSourceSpec, download_file(), fetch_pdf(), fetch_tex_source(), from_json(), load_manifest(), main() (+147 more)

### Community 12 - "Community 12"
Cohesion: 0.07
Nodes (123): BenchmarkReference, CloudAlignmentArtifact, CloudAlignmentSelection, DatasetId, DenseCloudEvaluationArtifact, DenseCloudEvaluationSelection, DiscoveredRun, ErrorSeries (+115 more)

### Community 13 - "Community 13"
Cohesion: 0.02
Nodes (96): Record3DTransportId, _CappedPacketStream, _CappedStreamingSource, Enum, IntEnum, ObservationStream, Persisted provenance contracts for completed pipeline runs.  This module owns th, table_rows() (+88 more)

### Community 14 - "Community 14"
Cohesion: 0.07
Nodes (63): _coerce_view_graph(), _coerce_view_graph_node(), load_vista_confidences(), load_vista_estimated_intrinsics_series(), load_vista_intrinsics_matrices(), load_vista_native_trajectory(), load_vista_vector(), load_vista_view_graph() (+55 more)

### Community 15 - "Community 15"
Cohesion: 0.07
Nodes (59): iter_sequence_manifest_observations(), _load_manifest_rgb_inputs(), _load_rgb(), _load_timestamps_ns(), _manifest_provenance(), Source-owned readers for normalized offline observations., Yield RGB observations from a normalized source sequence manifest., parse_optional_float() (+51 more)

### Community 16 - "Community 16"
Cohesion: 0.07
Nodes (34): Replay clock used by dataset and video source streams., Select whether replay follows source timing or returns observations immediately., Apply source-timestamp pacing for real-time replay., Reset the clock baseline for a new replay loop or connection., Sleep until the replay timestamp should be emitted., ReplayClock, ReplayMode, ImageSequenceObservationSource (+26 more)

### Community 17 - "Community 17"
Cohesion: 0.12
Nodes (34): build_pipeline_snapshot_render_model(), _coerce_int_metric(), _compute_evo_preview(), _format_latency(), _format_optional_rate(), _format_queue(), _format_resources(), _format_tasks() (+26 more)

### Community 18 - "Community 18"
Cohesion: 0.13
Nodes (18): Return the user-facing reconstruction label., Configure the minimal Open3D TSDF reconstruction backend.      The repo targets, Return the concrete reconstruction backend type., Instantiate the Open3D TSDF backend while ignoring unrelated kwargs., Describe normalized durable outputs from one reconstruction run.      The minima, ReconstructionArtifacts, ReconstructionMethodId, _import_open3d() (+10 more)

### Community 19 - "Community 19"
Cohesion: 1.0
Nodes (1): Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays

### Community 20 - "Community 20"
Cohesion: 1.0
Nodes (1): Ray-specific helpers for future stage runtime deployment.  This module intention

### Community 21 - "Community 21"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.

### Community 22 - "Community 22"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from a 4x4 homogeneous matrix.

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (1): Return the compact source label used in logs and diagnostics.

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (1): Connect to the source and prepare subsequent blocking observation reads.

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): Disconnect or release the source and any owned runtime resources.

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): Return the short user-facing dataset label.

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): Deserialize one IPC payload back into the target validated model type.

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): Return the human-readable label shown in plan previews.

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): Return whether ``exc`` looks like a transient local Ray connection failure.

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): Build one spec from one JSON object.

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (1): Return the net code-line delta.

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (1): Return the path that should own this change in reports.

## Knowledge Gaps
- **234 isolated node(s):** `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`, `Frame preprocessing helpers for ViSTA-SLAM.`, `One RGB frame prepared for upstream ViSTA ingestion.`, `Use the exact upstream ViSTA crop-and-resize helper path.`, `Convert one upstream ViSTA array-like payload into a numpy array.` (+229 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 19`** (2 nodes): `streamlit_app.py`, `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 20`** (2 nodes): `ray.py`, `Ray-specific helpers for future stage runtime deployment.  This module intention`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (1 nodes): `Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 22`** (1 nodes): `Build the shared transform DTO from a 4x4 homogeneous matrix.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (1 nodes): `Return the compact source label used in logs and diagnostics.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (1 nodes): `Connect to the source and prepare subsequent blocking observation reads.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (1 nodes): `Disconnect or release the source and any owned runtime resources.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `Return the short user-facing dataset label.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `Deserialize one IPC payload back into the target validated model type.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `Return the human-readable label shown in plan previews.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `Return whether ``exc`` looks like a transient local Ray connection failure.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `Build one spec from one JSON object.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `Return the net code-line delta.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (1 nodes): `Return the path that should own this change in reports.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Test package helpers and suites for PRML VSLAM.` connect `Community 2` to `Community 0`, `Community 1`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 9`, `Community 10`, `Community 12`, `Community 13`, `Community 14`, `Community 16`, `Community 18`?**
  _High betweenness centrality (0.146) - this node is a cross-community bridge._
- **Why does `StageKey` connect `Community 1` to `Community 0`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 8`, `Community 9`, `Community 10`, `Community 12`, `Community 13`?**
  _High betweenness centrality (0.078) - this node is a cross-community bridge._
- **Why does `FrameTransform` connect `Community 3` to `Community 0`, `Community 1`, `Community 2`, `Community 4`, `Community 6`, `Community 7`, `Community 8`, `Community 9`, `Community 10`, `Community 12`, `Community 13`, `Community 14`, `Community 15`?**
  _High betweenness centrality (0.055) - this node is a cross-community bridge._
- **Are the 436 inferred relationships involving `StageKey` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`StageKey` has 436 INFERRED edges - model-reasoned connections that need verification._
- **Are the 303 inferred relationships involving `SequenceManifest` (e.g. with `OfflineSlamBackend` and `StreamingSlamBackend`) actually correct?**
  _`SequenceManifest` has 303 INFERRED edges - model-reasoned connections that need verification._
- **Are the 266 inferred relationships involving `ArtifactRef` (e.g. with `SlamUpdate` and `SlamArtifacts`) actually correct?**
  _`ArtifactRef` has 266 INFERRED edges - model-reasoned connections that need verification._
- **Are the 250 inferred relationships involving `MethodId` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`MethodId` has 250 INFERRED edges - model-reasoned connections that need verification._