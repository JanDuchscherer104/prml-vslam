# Graph Report - prml-vslam  (2026-06-25)

## Corpus Check
- 306 files · ~2,810,132 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 5157 nodes · 26087 edges · 43 communities detected
- Extraction: 29% EXTRACTED · 71% INFERRED · 0% AMBIGUOUS · INFERRED: 18583 edges (avg confidence: 0.59)
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
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]

## God Nodes (most connected - your core abstractions)
1. `SequenceManifest` - 539 edges
2. `PreparedBenchmarkInputs` - 483 edges
3. `DatasetId` - 470 edges
4. `StageKey` - 455 edges
5. `ReferenceSource` - 388 edges
6. `FrameSelectionConfig` - 337 edges
7. `PathConfig` - 303 edges
8. `ArtifactRef` - 283 edges
9. `MethodId` - 282 edges
10. `ReferenceTrajectoryRef` - 249 edges

## Surprising Connections (you probably didn't know these)
- `plan_run()` --calls--> `test_plan_run_defaults_to_live_viewer()`  [INFERRED]
  src/prml_vslam/main.py → tests/test_main.py
- `VisualizationConfig` --calls--> `test_visualization_config_rejects_invalid_decimation_values()`  [INFERRED]
  src/prml_vslam/visualization/contracts.py → tests/test_visualization.py
- `MetricsPageState` --calls--> `test_metrics_page_state_preserves_persisted_view_fields()`  [INFERRED]
  src/prml_vslam/app/models.py → tests/test_app.py
- `path()` --calls--> `report_path()`  [INFERRED]
  src/prml_vslam/pipeline/sinks/jsonl.py → scripts/loc_stats.py
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
Nodes (551): _build_artifacts(), _DensePredictionArtifacts, _ensure_uint8_rgb_from_uimg(), _InProcessManager, _InProcessValue, Canonical MASt3R-SLAM backend adapter (offline + streaming).  This adapter wraps, Estimate model-raster intrinsics from a MASt3R keyframe pointmap., Run LingBot-Map and persist normalized trajectory and dense geometry. (+543 more)

### Community 1 - "Community 1"
Cohesion: 0.01
Nodes (470): _adapt_checkpoint_state_dict(), _as_numpy(), _build_lingbot_artifacts(), _cast_aggregator_for_inference(), _decode_pose_predictions(), _estimate_camera_intrinsics_from_frame(), _expect_lingbot_config(), _extract_checkpoint_state_dict() (+462 more)

### Community 2 - "Community 2"
Cohesion: 0.03
Nodes (464): Controller helpers for the ADVIO Streamlit page., Persist the current ADVIO download-form state., Keep persisted preview state aligned with the runtime snapshot., Apply one preview-form action and return an error message when it fails., sync_advio_download_state(), AdvioPeopleLevel, Crowd-density labels committed from the official ADVIO scene table., MethodId (+456 more)

### Community 3 - "Community 3"
Cohesion: 0.01
Nodes (440): build_crowd_density_figure(), build_local_readiness_figure(), build_scene_attribute_figure(), build_scene_mix_figure(), handle_advio_preview_action(), sync_advio_preview_state(), Plotly figure builders for the ADVIO dataset page., Build a crowd-density composition chart. (+432 more)

### Community 4 - "Community 4"
Cohesion: 0.01
Nodes (349): build_advio_page_data(), _scene_rows(), AdvioDownloadManager, _ensure_directory_parent(), Return the cache directory used for downloaded scene archives., Return one catalog scene by id., Return local availability status for every catalog scene., Download selected ADVIO scenes and extract complete scene payloads. (+341 more)

### Community 5 - "Community 5"
Cohesion: 0.01
Nodes (337): _coordinator_actor_options(), RayPipelineBackend, BaseConfig, _ConfigFactory, FactoryConfig, from_toml(), _normalize_value(), Shared config and config-as-factory helpers for the repository.  This module own (+329 more)

### Community 6 - "Community 6"
Cohesion: 0.03
Nodes (353): AdvioFixedpointFitMode, AdvioFixpointSet, ADVIO fixedpoint registration helpers.  The official ADVIO visualization registe, Estimate a no-scale rigid transform from provider RDF world to fixpoints., Apply one fixedpoint registration to a provider RDF trajectory., Crop registered ADVIO trajectories and express them in one GT local frame., Build a frame-labelled camera pose from a matrix., Rigid registration mode selected for one ADVIO provider trajectory. (+345 more)

### Community 7 - "Community 7"
Cohesion: 0.01
Nodes (185): Mast3rSlamSession, _normalized_entry_timestamps_ns(), Backward-compatible warning alias., IntEnum, _advio_aligned_diagnostic_reference(), _advio_aligned_diagnostic_references(), _advio_reference_source_for_serving(), _benchmark_artifact_paths() (+177 more)

### Community 8 - "Community 8"
Cohesion: 0.02
Nodes (208): _apply_snapshot_fallbacks(), _candidate_from_root(), _canonical_path_rows(), _derive_slam_artifacts(), discover_run_artifact_roots(), _file_inventory(), _format_size(), inspect_run_artifacts() (+200 more)

### Community 9 - "Community 9"
Cohesion: 0.03
Nodes (178): available_metric_keys(), build_coverage_matrix(), build_heatmap_data(), build_leaderboard(), build_per_sequence_table(), _build_rmse_aggregate_rows(), build_wide_metric_rows(), _clean_records() (+170 more)

### Community 10 - "Community 10"
Cohesion: 0.03
Nodes (114): LingbotMapSlamBackend, Mast3rSlamBackend, VistaSlamBackend, build_slam_backend_config(), Persisted SLAM backend config and backend muxing.  The SLAM stage owns the publi, Whether the backend can emit live preview payloads., Whether the backend may emit native visualization artifacts., Whether the backend supports repository trajectory evaluation. (+106 more)

### Community 11 - "Community 11"
Cohesion: 0.05
Nodes (63): build_advio_comparison_trajectories(), load_advio_fixpoints(), advio_basis_metadata(), advio_basis_provenance(), AdvioBasisMetadata, basis_for_pose_source(), _flatten_matrix(), _pose_matrix() (+55 more)

### Community 12 - "Community 12"
Cohesion: 0.07
Nodes (47): _assert_slug(), build_run_config_from_sweep_item(), _build_run_id(), expand_sweep(), _load_slam_stage_from_template(), load_sweep_config(), _load_toml_payload(), validate_ids_are_slugs() (+39 more)

### Community 13 - "Community 13"
Cohesion: 0.07
Nodes (38): Replay clock used by dataset and video source streams., Select whether replay follows source timing or returns observations immediately., Apply source-timestamp pacing for real-time replay., Reset the clock baseline for a new replay loop or connection., Sleep until the replay timestamp should be emitted., ReplayClock, ReplayMode, ImageSequenceObservationSource (+30 more)

### Community 14 - "Community 14"
Cohesion: 0.1
Nodes (33): GroundPlaneModel, GroundPlaneVisualizationHint, Alignment result DTOs shared outside the alignment package.  These datamodels de, Dominant ground-plane hypothesis expressed in native ``world`` coordinates., Finite plane-patch geometry ready for visualization consumers., GroundAlignmentConfig, _build_viewer_transform(), _camera_down_alignment() (+25 more)

### Community 15 - "Community 15"
Cohesion: 0.08
Nodes (24): Return the user-facing reconstruction label., Configure the minimal Open3D TSDF reconstruction backend.      The repo targets, Return the concrete reconstruction backend type., Instantiate the Open3D TSDF backend while ignoring unrelated kwargs., Describe normalized durable outputs from one reconstruction run.      The minima, ReconstructionArtifacts, ReconstructionMethodId, _import_open3d() (+16 more)

### Community 16 - "Community 16"
Cohesion: 0.12
Nodes (33): build_pipeline_snapshot_render_model(), _coerce_int_metric(), _format_latency(), _format_optional_rate(), _format_queue(), _format_resources(), _format_tasks(), _format_throughput() (+25 more)

### Community 17 - "Community 17"
Cohesion: 0.13
Nodes (28): _add_point_cloud_trace(), _add_trajectory_trace(), _apply_comparison_layout(), _build_figure(), build_reference_reconstruction_figure(), build_slam_reference_comparison_figure(), _combined_bounds(), _decimate_mesh() (+20 more)

### Community 18 - "Community 18"
Cohesion: 0.09
Nodes (25): DataOnlyConfig, InvalidTargetConfig, NestedPayload, PlainPayload, Tests for the shared Pydantic base-model split., Runtime object used to verify default setup behavior., Config whose runtime target is constructed via ``target_type``., Config without a runtime target. (+17 more)

### Community 19 - "Community 19"
Cohesion: 0.13
Nodes (23): _build_blueprint_command(), create_follow_trajectory_artifact(), default_follow_output_path(), _default_recording_id(), _follow_blueprint_script(), FollowArtifactResult, main(), _merge_command() (+15 more)

### Community 20 - "Community 20"
Cohesion: 0.15
Nodes (2): Tests for package-root public export surfaces., test_source_materialization_does_not_import_stage_package()

### Community 21 - "Community 21"
Cohesion: 0.25
Nodes (1): Backend boundary between launch surfaces and execution substrates.  This module

### Community 22 - "Community 22"
Cohesion: 0.36
Nodes (4): test_resolve_issue_moves_record_to_resolved_collection(), test_resolve_refactor_moves_record_to_resolved_collection(), test_resolve_todo_moves_record_to_resolved_collection(), _write_toml()

### Community 23 - "Community 23"
Cohesion: 1.0
Nodes (1): Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (1): Ray-specific helpers for future stage runtime deployment.  This module intention

### Community 25 - "Community 25"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.

### Community 26 - "Community 26"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from a 4x4 homogeneous matrix.

### Community 27 - "Community 27"
Cohesion: 1.0
Nodes (1): Return the compact source label used in logs and diagnostics.

### Community 28 - "Community 28"
Cohesion: 1.0
Nodes (1): Disconnect or release the source and any owned runtime resources.

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): Return the short user-facing dataset label.

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): Deserialize one IPC payload back into the target validated model type.

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (1): Return the human-readable label shown in plan previews.

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (1): Return whether ``exc`` looks like a transient local Ray connection failure.

### Community 33 - "Community 33"
Cohesion: 1.0
Nodes (1): Build one spec from one JSON object.

### Community 34 - "Community 34"
Cohesion: 1.0
Nodes (1): Return the net code-line delta.

### Community 35 - "Community 35"
Cohesion: 1.0
Nodes (1): Return the path that should own this change in reports.

### Community 36 - "Community 36"
Cohesion: 1.0
Nodes (1): Return the short user-facing dataset label.

### Community 37 - "Community 37"
Cohesion: 1.0
Nodes (1): Coordinate-frame semantics for served ADVIO trajectories.

### Community 38 - "Community 38"
Cohesion: 1.0
Nodes (1): Typed ADVIO serving semantics shared by request and manifest contracts.

### Community 39 - "Community 39"
Cohesion: 1.0
Nodes (1): Source-prepared RGB-D reference-cloud sampling policy.

### Community 40 - "Community 40"
Cohesion: 1.0
Nodes (1): Local availability summary for one dataset scene.

### Community 41 - "Community 41"
Cohesion: 1.0
Nodes (1): High-level summary of committed and local dataset coverage.

### Community 42 - "Community 42"
Cohesion: 1.0
Nodes (1): Return the effective ADVIO provider for one optional serving config.

### Community 52 - "Community 52"
Cohesion: 1.0
Nodes (1): Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays

### Community 53 - "Community 53"
Cohesion: 1.0
Nodes (1): Ray-specific helpers for future stage runtime deployment.  This module intention

### Community 54 - "Community 54"
Cohesion: 1.0
Nodes (1): MemPalace Help

### Community 55 - "Community 55"
Cohesion: 1.0
Nodes (1): MemPalace Init

### Community 56 - "Community 56"
Cohesion: 1.0
Nodes (1): MemPalace Mine

### Community 57 - "Community 57"
Cohesion: 1.0
Nodes (1): MemPalace Search

### Community 58 - "Community 58"
Cohesion: 1.0
Nodes (1): MemPalace Status

### Community 59 - "Community 59"
Cohesion: 1.0
Nodes (1): test

### Community 60 - "Community 60"
Cohesion: 1.0
Nodes (1): Return whether ``exc`` looks like a transient local Ray connection failure.

### Community 61 - "Community 61"
Cohesion: 1.0
Nodes (1): Return the human-readable label shown in plan previews.

### Community 62 - "Community 62"
Cohesion: 1.0
Nodes (1): Deserialize one IPC payload back into the target validated model type.

### Community 63 - "Community 63"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.

### Community 64 - "Community 64"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from a 4x4 homogeneous matrix.

### Community 65 - "Community 65"
Cohesion: 1.0
Nodes (1): Return the compact source label used in logs and diagnostics.

### Community 66 - "Community 66"
Cohesion: 1.0
Nodes (1): Disconnect or release the source and any owned runtime resources.

### Community 67 - "Community 67"
Cohesion: 1.0
Nodes (1): Return the short user-facing dataset label.

### Community 68 - "Community 68"
Cohesion: 1.0
Nodes (1): Return the net code-line delta.

### Community 69 - "Community 69"
Cohesion: 1.0
Nodes (1): Return the path that should own this change in reports.

### Community 70 - "Community 70"
Cohesion: 1.0
Nodes (1): Build one spec from one JSON object.

### Community 71 - "Community 71"
Cohesion: 1.0
Nodes (1): Build the optional CUDA RoPE2D extension for the bundled ViSTA-SLAM checkout.

### Community 72 - "Community 72"
Cohesion: 1.0
Nodes (1): Build ViSTA-SLAM's optional cuRoPE2D extension in-place.

### Community 73 - "Community 73"
Cohesion: 1.0
Nodes (1): Download arXiv e-print source bundles listed in a JSONL manifest.

### Community 74 - "Community 74"
Cohesion: 1.0
Nodes (1): One manifest entry describing how to fetch arXiv assets.

### Community 75 - "Community 75"
Cohesion: 1.0
Nodes (1): Build one spec from one JSON object.

### Community 76 - "Community 76"
Cohesion: 1.0
Nodes (1): Load a JSONL manifest into typed source specs.

### Community 77 - "Community 77"
Cohesion: 1.0
Nodes (1): Download one URL to one local path.

### Community 78 - "Community 78"
Cohesion: 1.0
Nodes (1): Extract a tar archive while rejecting unsafe paths.

### Community 79 - "Community 79"
Cohesion: 1.0
Nodes (1): Normalize one archive member path and reject traversal segments.

### Community 80 - "Community 80"
Cohesion: 1.0
Nodes (1): Download and extract one arXiv TeX source tree.

### Community 81 - "Community 81"
Cohesion: 1.0
Nodes (1): Download one PDF if the manifest entry requests it.

### Community 82 - "Community 82"
Cohesion: 1.0
Nodes (1): Run the downloader CLI.

### Community 83 - "Community 83"
Cohesion: 1.0
Nodes (1): Generate repo-local Open3D stubs with Open3D's pybind11-stubgen workflow.

### Community 84 - "Community 84"
Cohesion: 1.0
Nodes (1): Regenerate Open3D `.pyi` files under `typings/open3d`.

### Community 85 - "Community 85"
Cohesion: 1.0
Nodes (1): Compute Python line-of-code statistics for src/ and tests/.

### Community 86 - "Community 86"
Cohesion: 1.0
Nodes (1): Aggregated line statistics for Python source files.

### Community 87 - "Community 87"
Cohesion: 1.0
Nodes (1): Merge two source line-stat objects.

### Community 88 - "Community 88"
Cohesion: 1.0
Nodes (1): Return the legacy dictionary shape used by older tests and callers.

### Community 89 - "Community 89"
Cohesion: 1.0
Nodes (1): Line statistics and markers for one analyzed Python source file.

### Community 90 - "Community 90"
Cohesion: 1.0
Nodes (1): Code-line delta counts for one or more Python source files.

### Community 91 - "Community 91"
Cohesion: 1.0
Nodes (1): Return the net code-line delta.

### Community 92 - "Community 92"
Cohesion: 1.0
Nodes (1): Return whether this diff contains any code-line additions, edits, or removals.

### Community 93 - "Community 93"
Cohesion: 1.0
Nodes (1): Count this delta as affecting one file when it has code-line changes.

### Community 94 - "Community 94"
Cohesion: 1.0
Nodes (1): Merge two code-line delta objects.

### Community 95 - "Community 95"
Cohesion: 1.0
Nodes (1): One Git worktree file change relative to HEAD.

### Community 96 - "Community 96"
Cohesion: 1.0
Nodes (1): Return the path that should own this change in reports.

### Community 97 - "Community 97"
Cohesion: 1.0
Nodes (1): Single TODO/FIXME marker found in a Python source file.

### Community 98 - "Community 98"
Cohesion: 1.0
Nodes (1): Parse CLI flags for LOC, module, and dirty-worktree reports.

### Community 99 - "Community 99"
Cohesion: 1.0
Nodes (1): Extract TODO/FIXME comment markers from file lines.

### Community 100 - "Community 100"
Cohesion: 1.0
Nodes (1): Return Python source files below a root path.

### Community 101 - "Community 101"
Cohesion: 1.0
Nodes (1): Return line numbers occupied by module, class, and function docstrings.

### Community 102 - "Community 102"
Cohesion: 1.0
Nodes (1): Count source lines and markers for one Python file.

### Community 103 - "Community 103"
Cohesion: 1.0
Nodes (1): Read and count source lines and markers for one Python file.

### Community 104 - "Community 104"
Cohesion: 1.0
Nodes (1): Return source lines counted as code by the LOC rules.

### Community 105 - "Community 105"
Cohesion: 1.0
Nodes (1): Count high-level line statistics for Python files under root.

### Community 106 - "Community 106"
Cohesion: 1.0
Nodes (1): Count line statistics grouped by a caller-provided path bucket.

### Community 107 - "Community 107"
Cohesion: 1.0
Nodes (1): Return the dotted module bucket for a Python source path.

### Community 108 - "Community 108"
Cohesion: 1.0
Nodes (1): Count Python LOC grouped by prml_vslam module.

### Community 109 - "Community 109"
Cohesion: 1.0
Nodes (1): Count inserted, replaced, and removed code lines between two code-line sequences

### Community 110 - "Community 110"
Cohesion: 1.0
Nodes (1): Count code-line changes between two Python source revisions.

### Community 111 - "Community 111"
Cohesion: 1.0
Nodes (1): Run a Git command and return stdout bytes.

### Community 112 - "Community 112"
Cohesion: 1.0
Nodes (1): Parse `git diff --name-status -z` output into file changes.

### Community 113 - "Community 113"
Cohesion: 1.0
Nodes (1): Return tracked Python file changes between HEAD and the worktree.

### Community 114 - "Community 114"
Cohesion: 1.0
Nodes (1): Return untracked Python files below counted roots.

### Community 115 - "Community 115"
Cohesion: 1.0
Nodes (1): Read a file revision from HEAD.

### Community 116 - "Community 116"
Cohesion: 1.0
Nodes (1): Read a file revision from the current worktree.

### Community 117 - "Community 117"
Cohesion: 1.0
Nodes (1): Return the dirty-diff report bucket for a repo-relative path.

### Community 118 - "Community 118"
Cohesion: 1.0
Nodes (1): Collect dirty-worktree Python code-line changes against HEAD.

### Community 119 - "Community 119"
Cohesion: 1.0
Nodes (1): Read one statistic from either the legacy dict or typed stats object.

### Community 120 - "Community 120"
Cohesion: 1.0
Nodes (1): Render a Rich table for aggregate LOC statistics.

### Community 121 - "Community 121"
Cohesion: 1.0
Nodes (1): Return a signed integer string for delta tables.

### Community 122 - "Community 122"
Cohesion: 1.0
Nodes (1): Render a Rich table for dirty-worktree code-line deltas.

### Community 123 - "Community 123"
Cohesion: 1.0
Nodes (1): Render a detailed Rich table for one marker kind.

### Community 124 - "Community 124"
Cohesion: 1.0
Nodes (1): Print LOC statistics for src/ and tests/.

### Community 125 - "Community 125"
Cohesion: 1.0
Nodes (1): Top-level package surface for the PRML VSLAM benchmark stack.  This package expo

### Community 126 - "Community 126"
Cohesion: 1.0
Nodes (1): Alignment algorithms and pipeline stages.  Use explicit subpackages such as :mod

### Community 127 - "Community 127"
Cohesion: 1.0
Nodes (1): Ground-alignment pipeline stage integration.

### Community 128 - "Community 128"
Cohesion: 1.0
Nodes (1): Persisted config for the ``gravity.align`` stage.

### Community 129 - "Community 129"
Cohesion: 1.0
Nodes (1): Stage-owned policy for derived ground-plane alignment.

### Community 130 - "Community 130"
Cohesion: 1.0
Nodes (1): Typed policy contracts for derived ground-plane alignment.  Alignment is a deriv

### Community 131 - "Community 131"
Cohesion: 1.0
Nodes (1): Policy for optional dominant-ground detection and viewer alignment.      The sta

### Community 132 - "Community 132"
Cohesion: 1.0
Nodes (1): Bounded runtime adapter for the ground-alignment stage.

### Community 133 - "Community 133"
Cohesion: 1.0
Nodes (1): Adapt :class:`GroundAlignmentService` to the generic bounded runtime API.      T

### Community 134 - "Community 134"
Cohesion: 1.0
Nodes (1): Return the latest ground-alignment runtime status.

### Community 135 - "Community 135"
Cohesion: 1.0
Nodes (1): Mark the bounded runtime as stopped.

### Community 136 - "Community 136"
Cohesion: 1.0
Nodes (1): Detect and persist the derived ground-alignment artifact.          Returns a ski

### Community 137 - "Community 137"
Cohesion: 1.0
Nodes (1): Open3D-backed dominant-ground detection and viewer alignment helpers.  This modu

### Community 138 - "Community 138"
Cohesion: 1.0
Nodes (1): Detect dominant ground planes without rewriting native SLAM artifacts.      The

### Community 139 - "Community 139"
Cohesion: 1.0
Nodes (1): Estimate one dominant ground plane from normalized SLAM artifacts.          Args

### Community 140 - "Community 140"
Cohesion: 1.0
Nodes (1): # TODO: all of these options should be handeled via StageConfig.backend_config!

### Community 141 - "Community 141"
Cohesion: 1.0
Nodes (1): Runtime spec for the ground-alignment stage.

### Community 142 - "Community 142"
Cohesion: 1.0
Nodes (1): Ground-alignment stage runtime input contracts.

### Community 143 - "Community 143"
Cohesion: 1.0
Nodes (1): Inputs required to derive ground-alignment metadata from SLAM outputs.

### Community 144 - "Community 144"
Cohesion: 1.0
Nodes (1): ICP point-cloud alignment — algorithm and pipeline stage.

### Community 145 - "Community 145"
Cohesion: 1.0
Nodes (1): ICP point-cloud alignment service.

### Community 146 - "Community 146"
Cohesion: 1.0
Nodes (1): Materialize offline point-cloud alignment artifacts before cloud metrics.

### Community 147 - "Community 147"
Cohesion: 1.0
Nodes (1): Refine a trajectory-Sim(3)-aligned cloud against a reference cloud with ICP.

### Community 148 - "Community 148"
Cohesion: 1.0
Nodes (1): Return the deterministic point-cloud alignment metadata path.

### Community 149 - "Community 149"
Cohesion: 1.0
Nodes (1): Return the deterministic ICP-refined point-cloud path.

### Community 150 - "Community 150"
Cohesion: 1.0
Nodes (1): Persisted config for the ``align.cloud`` stage.

### Community 151 - "Community 151"
Cohesion: 1.0
Nodes (1): Bounded runtime adapter for offline point-cloud alignment.

### Community 152 - "Community 152"
Cohesion: 1.0
Nodes (1): Refine a trajectory-Sim(3)-aligned SLAM cloud before dense-cloud metrics.

### Community 153 - "Community 153"
Cohesion: 1.0
Nodes (1): Runtime spec for the offline point-cloud alignment stage.

### Community 154 - "Community 154"
Cohesion: 1.0
Nodes (1): Sim(3) trajectory alignment — algorithm and pipeline stage.

### Community 155 - "Community 155"
Cohesion: 1.0
Nodes (1): Sim(3) Umeyama trajectory alignment helpers.

### Community 156 - "Community 156"
Cohesion: 1.0
Nodes (1): Whether the benchmark target frame is gravity-aligned (up == RDF -Y).      ADVIO

### Community 157 - "Community 157"
Cohesion: 1.0
Nodes (1): Return True when both trajectories have enough geometric spread for Sim(3) align

### Community 158 - "Community 158"
Cohesion: 1.0
Nodes (1): Align *estimate* to *reference* via Sim(3) and return the aligned trajectory and

### Community 159 - "Community 159"
Cohesion: 1.0
Nodes (1): Return the tilt angle in degrees between the transformed and original down-axis,

### Community 160 - "Community 160"
Cohesion: 1.0
Nodes (1): Persisted config for the ``align.trajectory`` stage.

### Community 161 - "Community 161"
Cohesion: 1.0
Nodes (1): Trajectory-alignment contracts shared by evaluation and visualization.  Trajecto

### Community 162 - "Community 162"
Cohesion: 1.0
Nodes (1): Bounded runtime adapter for the Sim(3) trajectory alignment stage.

### Community 163 - "Community 163"
Cohesion: 1.0
Nodes (1): Runtime spec for the trajectory-alignment stage.

### Community 164 - "Community 164"
Cohesion: 1.0
Nodes (1): Trajectory-alignment stage runtime input contracts.

### Community 165 - "Community 165"
Cohesion: 1.0
Nodes (1): Inputs required to compute the Sim(3) trajectory alignment.

### Community 166 - "Community 166"
Cohesion: 1.0
Nodes (1): Packaged Streamlit entrypoint for the PRML VSLAM workbench.

### Community 167 - "Community 167"
Cohesion: 1.0
Nodes (1): Controller helpers for the ADVIO Streamlit page.

### Community 168 - "Community 168"
Cohesion: 1.0
Nodes (1): Persist the current ADVIO download-form state.

### Community 169 - "Community 169"
Cohesion: 1.0
Nodes (1): Keep persisted preview state aligned with the runtime snapshot.

### Community 170 - "Community 170"
Cohesion: 1.0
Nodes (1): Apply one preview-form action and return an error message when it fails.

### Community 171 - "Community 171"
Cohesion: 1.0
Nodes (1): Bootstrap helpers for the packaged PRML VSLAM Streamlit app.

### Community 172 - "Community 172"
Cohesion: 1.0
Nodes (1): Typed per-rerun context passed to page renderers.

### Community 173 - "Community 173"
Cohesion: 1.0
Nodes (1): Construct the typed services and persisted state for one rerun.

### Community 174 - "Community 174"
Cohesion: 1.0
Nodes (1): Render the packaged Streamlit application.

### Community 175 - "Community 175"
Cohesion: 1.0
Nodes (1): Private render helpers for the Streamlit datasets page.

### Community 176 - "Community 176"
Cohesion: 1.0
Nodes (1): Dashboard panels for normalized dataset snapshots.

### Community 177 - "Community 177"
Cohesion: 1.0
Nodes (1): Render normalized-store dashboard charts for one dataset.

### Community 178 - "Community 178"
Cohesion: 1.0
Nodes (1): Select one row per sequence and trajectory subject for dashboard charts.

### Community 179 - "Community 179"
Cohesion: 1.0
Nodes (1): Return compact columns for dashboard detail tables.

### Community 180 - "Community 180"
Cohesion: 1.0
Nodes (1): Render top-level normalized-store and download-cache metrics.

### Community 181 - "Community 181"
Cohesion: 1.0
Nodes (1): Render ADVIO-specific catalog composition charts.

### Community 182 - "Community 182"
Cohesion: 1.0
Nodes (1): Download, catalog, and diagnostics panels for dataset management.

### Community 183 - "Community 183"
Cohesion: 1.0
Nodes (1): Download form data for the TUM RGB-D dataset page.

### Community 184 - "Community 184"
Cohesion: 1.0
Nodes (1): Render ADVIO download controls and normalized diagnostics.

### Community 185 - "Community 185"
Cohesion: 1.0
Nodes (1): Render TUM RGB-D download controls and normalized diagnostics.

### Community 186 - "Community 186"
Cohesion: 1.0
Nodes (1): Render Record3D download controls and normalized diagnostics.

### Community 187 - "Community 187"
Cohesion: 1.0
Nodes (1): Rerun immediately after successful downloads so other tabs cannot render stale s

### Community 188 - "Community 188"
Cohesion: 1.0
Nodes (1): Render the shared download form shell.

### Community 189 - "Community 189"
Cohesion: 1.0
Nodes (1): Render a service notice from a page-data result.

### Community 190 - "Community 190"
Cohesion: 1.0
Nodes (1): Build TUM RGB-D catalog rows and optional download result notice.

### Community 191 - "Community 191"
Cohesion: 1.0
Nodes (1): Build Record3D catalog rows and optional download result notice.

### Community 192 - "Community 192"
Cohesion: 1.0
Nodes (1): Return catalog table rows for Record3D scene statuses.

### Community 193 - "Community 193"
Cohesion: 1.0
Nodes (1): Add normalized-entry status columns to catalog rows.

### Community 194 - "Community 194"
Cohesion: 1.0
Nodes (1): Render read-only normalized-store entry details.

### Community 195 - "Community 195"
Cohesion: 1.0
Nodes (1): Render read-only normalized stats and metadata tables.

### Community 196 - "Community 196"
Cohesion: 1.0
Nodes (1): Render a multiselect that defaults to every available stringified value.

### Community 197 - "Community 197"
Cohesion: 1.0
Nodes (1): Render the dataset service scene catalog table.

### Community 198 - "Community 198"
Cohesion: 1.0
Nodes (1): Render ADVIO scene download controls.

### Community 199 - "Community 199"
Cohesion: 1.0
Nodes (1): Render TUM RGB-D scene download controls.

### Community 200 - "Community 200"
Cohesion: 1.0
Nodes (1): Render Record3D archive download controls.

### Community 201 - "Community 201"
Cohesion: 1.0
Nodes (1): Render common scene-download form fields.

### Community 202 - "Community 202"
Cohesion: 1.0
Nodes (1): Loop-preview controls for normalized dataset entries.

### Community 203 - "Community 203"
Cohesion: 1.0
Nodes (1): Keep TUM RGB-D preview state aligned with the shared preview runtime.

### Community 204 - "Community 204"
Cohesion: 1.0
Nodes (1): Keep Record3D preview state aligned with the shared preview runtime.

### Community 205 - "Community 205"
Cohesion: 1.0
Nodes (1): Apply one TUM RGB-D preview start or stop action.

### Community 206 - "Community 206"
Cohesion: 1.0
Nodes (1): Apply one Record3D preview start or stop action.

### Community 207 - "Community 207"
Cohesion: 1.0
Nodes (1): Render ADVIO normalized loop preview controls.

### Community 208 - "Community 208"
Cohesion: 1.0
Nodes (1): Render TUM RGB-D normalized loop preview controls.

### Community 209 - "Community 209"
Cohesion: 1.0
Nodes (1): Render Record3D normalized loop preview controls.

### Community 210 - "Community 210"
Cohesion: 1.0
Nodes (1): Render the shared normalized dataset loop-preview control.

### Community 211 - "Community 211"
Cohesion: 1.0
Nodes (1): Render the current shared preview-runtime snapshot.

### Community 212 - "Community 212"
Cohesion: 1.0
Nodes (1): Return compact live preview metrics.

### Community 213 - "Community 213"
Cohesion: 1.0
Nodes (1): Return a compact preview caption for the active sequence and pose source.

### Community 214 - "Community 214"
Cohesion: 1.0
Nodes (1): Render RGB and optional depth frames for one preview observation.

### Community 215 - "Community 215"
Cohesion: 1.0
Nodes (1): Render preview runtime state as a Streamlit notice.

### Community 216 - "Community 216"
Cohesion: 1.0
Nodes (1): Return compact observation details for the live packet details tab.

### Community 217 - "Community 217"
Cohesion: 1.0
Nodes (1): Normalize legacy ADVIO integer preview IDs to normalized sequence IDs.

### Community 218 - "Community 218"
Cohesion: 1.0
Nodes (1): Read-only normalized datastore query helpers for the datasets page.

### Community 219 - "Community 219"
Cohesion: 1.0
Nodes (1): Load one cached normalized datastore snapshot for a Streamlit rerun.

### Community 220 - "Community 220"
Cohesion: 1.0
Nodes (1): Invalidate cached normalized datastore query snapshots.

### Community 221 - "Community 221"
Cohesion: 1.0
Nodes (1): Return the cached read-only normalized datastore projection.

### Community 222 - "Community 222"
Cohesion: 1.0
Nodes (1): Build a cache token that changes when trajectory files change.

### Community 223 - "Community 223"
Cohesion: 1.0
Nodes (1): Build a cache token that changes when reference-cloud files change.

### Community 224 - "Community 224"
Cohesion: 1.0
Nodes (1): Represent one artifact path and filesystem freshness metadata.

### Community 225 - "Community 225"
Cohesion: 1.0
Nodes (1): Load normalized TUM trajectory artifacts for scene visualization.

### Community 226 - "Community 226"
Cohesion: 1.0
Nodes (1): Load reference-cloud artifacts and return a cached scene figure.

### Community 227 - "Community 227"
Cohesion: 1.0
Nodes (1): Scene explorer and artifact visualization for normalized datasets.

### Community 228 - "Community 228"
Cohesion: 1.0
Nodes (1): Render the normalized scene explorer, metrics, and artifacts.

### Community 229 - "Community 229"
Cohesion: 1.0
Nodes (1): Select one normalized profile for the chosen scene.

### Community 230 - "Community 230"
Cohesion: 1.0
Nodes (1): Return the visible profile label for a normalized record.

### Community 231 - "Community 231"
Cohesion: 1.0
Nodes (1): Render scene metrics without collapsing multiple trajectories into one unlabeled

### Community 232 - "Community 232"
Cohesion: 1.0
Nodes (1): Return a deterministic subject/scope-qualified scene trajectory table.

### Community 233 - "Community 233"
Cohesion: 1.0
Nodes (1): Render normalized trajectory and reference-cloud artifacts for one scene.

### Community 234 - "Community 234"
Cohesion: 1.0
Nodes (1): Return the bird's-eye plane axes for one dataset's canonical frame.

### Community 235 - "Community 235"
Cohesion: 1.0
Nodes (1): Return the first row for a sequence from a single-subject frame.

### Community 236 - "Community 236"
Cohesion: 1.0
Nodes (1): Return a string metric value from one optional frame row.

### Community 237 - "Community 237"
Cohesion: 1.0
Nodes (1): Format a numeric string for compact metric display.

### Community 238 - "Community 238"
Cohesion: 1.0
Nodes (1): Render scene selection and profile inventory for a normalized dataset.

### Community 239 - "Community 239"
Cohesion: 1.0
Nodes (1): Shared Streamlit helpers for live-session app pages.

### Community 240 - "Community 240"
Cohesion: 1.0
Nodes (1): Resolve the live trajectory figure builder lazily for easier local testing.

### Community 241 - "Community 241"
Cohesion: 1.0
Nodes (1): Render one fragment-scoped live section.

### Community 242 - "Community 242"
Cohesion: 1.0
Nodes (1): Encode one live preview image as a data URL.      Streamlit stores array-backed

### Community 243 - "Community 243"
Cohesion: 1.0
Nodes (1): Render one high-churn live image without using Streamlit's media endpoint.

### Community 244 - "Community 244"
Cohesion: 1.0
Nodes (1): Return the fragment refresh interval only while the session is active.

### Community 245 - "Community 245"
Cohesion: 1.0
Nodes (1): Render one keyed start-or-stop button slot and return requested action flags.

### Community 246 - "Community 246"
Cohesion: 1.0
Nodes (1): Trigger an immediate full-page rerun after a successful explicit action.

### Community 247 - "Community 247"
Cohesion: 1.0
Nodes (1): Render the shared notice, metric, and body structure for one live section.

### Community 248 - "Community 248"
Cohesion: 1.0
Nodes (1): Render a compact metric row.

### Community 249 - "Community 249"
Cohesion: 1.0
Nodes (1): Render a live trajectory figure or a fallback message.

### Community 250 - "Community 250"
Cohesion: 1.0
Nodes (1): Render camera intrinsics using the shared LaTeX presentation.

### Community 251 - "Community 251"
Cohesion: 1.0
Nodes (1): Render the shared packet, trajectory, and camera tabs for live pages.

### Community 252 - "Community 252"
Cohesion: 1.0
Nodes (1): App-owned models for Streamlit page state, snapshots, and view selections.

### Community 253 - "Community 253"
Cohesion: 1.0
Nodes (1): Computed dataset-tab render payload.

### Community 254 - "Community 254"
Cohesion: 1.0
Nodes (1): Top-level pages exposed by the packaged Streamlit app.

### Community 255 - "Community 255"
Cohesion: 1.0
Nodes (1): Return the user-facing page label.

### Community 256 - "Community 256"
Cohesion: 1.0
Nodes (1): Lifecycle states shared by app-owned preview surfaces.

### Community 257 - "Community 257"
Cohesion: 1.0
Nodes (1): Common snapshot state shared by app-owned preview runtimes.

### Community 258 - "Community 258"
Cohesion: 1.0
Nodes (1): Latest Record3D preview snapshot shared inside the app layer.

### Community 259 - "Community 259"
Cohesion: 1.0
Nodes (1): Latest dataset loop-preview snapshot shared inside the app layer.

### Community 260 - "Community 260"
Cohesion: 1.0
Nodes (1): Typed ADVIO dataset-download form payload.

### Community 261 - "Community 261"
Cohesion: 1.0
Nodes (1): Typed ADVIO preview action payload.

### Community 262 - "Community 262"
Cohesion: 1.0
Nodes (1): Computed ADVIO page render payload.

### Community 263 - "Community 263"
Cohesion: 1.0
Nodes (1): Persisted selector state for the ADVIO dataset-management page.

### Community 264 - "Community 264"
Cohesion: 1.0
Nodes (1): Persisted selector state for the TUM RGB-D dataset-management tab.

### Community 265 - "Community 265"
Cohesion: 1.0
Nodes (1): Pose providers supported by the offline Record3D dataset tab.

### Community 266 - "Community 266"
Cohesion: 1.0
Nodes (1): Return the user-facing pose-source label.

### Community 267 - "Community 267"
Cohesion: 1.0
Nodes (1): Persisted selector state for the offline Record3D dataset-management tab.

### Community 268 - "Community 268"
Cohesion: 1.0
Nodes (1): Typed Record3D dataset-download form payload.

### Community 269 - "Community 269"
Cohesion: 1.0
Nodes (1): Persisted selector state for the metrics page.

### Community 270 - "Community 270"
Cohesion: 1.0
Nodes (1): Persisted selector state for the artifact inspector page.

### Community 271 - "Community 271"
Cohesion: 1.0
Nodes (1): Persisted selector state for the Record3D live-stream page.

### Community 272 - "Community 272"
Cohesion: 1.0
Nodes (1): Typed Record3D page action payload.

### Community 273 - "Community 273"
Cohesion: 1.0
Nodes (1): Resolved Record3D transport inputs for one page render.

### Community 274 - "Community 274"
Cohesion: 1.0
Nodes (1): Input-source families supported by the bounded pipeline app surface.

### Community 275 - "Community 275"
Cohesion: 1.0
Nodes (1): Return the user-facing source label.

### Community 276 - "Community 276"
Cohesion: 1.0
Nodes (1): Telemetry presentation modes for the Pipeline run console.

### Community 277 - "Community 277"
Cohesion: 1.0
Nodes (1): Return the user-facing mode label.

### Community 278 - "Community 278"
Cohesion: 1.0
Nodes (1): Stage runtime metrics that can be plotted from live telemetry samples.

### Community 279 - "Community 279"
Cohesion: 1.0
Nodes (1): Return the user-facing metric label.

### Community 280 - "Community 280"
Cohesion: 1.0
Nodes (1): Return the default y-axis unit label.

### Community 281 - "Community 281"
Cohesion: 1.0
Nodes (1): Persisted selector state for the Pipeline run console.

### Community 282 - "Community 282"
Cohesion: 1.0
Nodes (1): Fully typed app state persisted in Streamlit session storage.

### Community 283 - "Community 283"
Cohesion: 1.0
Nodes (1): Page modules for the packaged Streamlit workbench.

### Community 284 - "Community 284"
Cohesion: 1.0
Nodes (1): Streamlit page for inspecting persisted pipeline run artifacts.

### Community 285 - "Community 285"
Cohesion: 1.0
Nodes (1): Render the persisted run artifact inspector.

### Community 286 - "Community 286"
Cohesion: 1.0
Nodes (1): Streamlit datasets page router.

### Community 287 - "Community 287"
Cohesion: 1.0
Nodes (1): Render the public datasets page.

### Community 288 - "Community 288"
Cohesion: 1.0
Nodes (1): Streamlit page for persisted trajectory benchmark aggregation.

### Community 289 - "Community 289"
Cohesion: 1.0
Nodes (1): Render multi-run trajectory metric aggregation from persisted artifacts.

### Community 290 - "Community 290"
Cohesion: 1.0
Nodes (1): Render the dataset-wide benchmark summary view.

### Community 291 - "Community 291"
Cohesion: 1.0
Nodes (1): Streamlit page for the Pipeline run console.

### Community 292 - "Community 292"
Cohesion: 1.0
Nodes (1): Render the interactive Pipeline run console.

### Community 293 - "Community 293"
Cohesion: 1.0
Nodes (1): Rendering helpers for the Pipeline run-console request editor.

### Community 294 - "Community 294"
Cohesion: 1.0
Nodes (1): Return the smallest valid LingBot image size for the selected patch grid.

### Community 295 - "Community 295"
Cohesion: 1.0
Nodes (1): Render grouped request controls and return the resolved action payload.

### Community 296 - "Community 296"
Cohesion: 1.0
Nodes (1): Explain the current execution semantics for the selected method.

### Community 297 - "Community 297"
Cohesion: 1.0
Nodes (1): Rendering helpers for the Pipeline page run snapshot.

### Community 298 - "Community 298"
Cohesion: 1.0
Nodes (1): Render the current pipeline run snapshot.

### Community 299 - "Community 299"
Cohesion: 1.0
Nodes (1): Pure-Streamlit Record3D page for USB and Wi-Fi live preview.

### Community 300 - "Community 300"
Cohesion: 1.0
Nodes (1): Render the dedicated Record3D page.

### Community 301 - "Community 301"
Cohesion: 1.0
Nodes (1): Snapshot-presentation helpers for the Pipeline page.

### Community 302 - "Community 302"
Cohesion: 1.0
Nodes (1): Return the bounded telemetry history after incorporating one snapshot.

### Community 303 - "Community 303"
Cohesion: 1.0
Nodes (1): Return stage keys with planned, live, terminal, or historical telemetry context.

### Community 304 - "Community 304"
Cohesion: 1.0
Nodes (1): Return the Streamlit-facing Rerun viewer link for one run configuration.

### Community 305 - "Community 305"
Cohesion: 1.0
Nodes (1): Return the latest typed backend notice for the pipeline UI.      Durable backend

### Community 306 - "Community 306"
Cohesion: 1.0
Nodes (1): Resolve controller-owned render data for the Pipeline snapshot surface.

### Community 307 - "Community 307"
Cohesion: 1.0
Nodes (1): Request-editing and run-launch helpers for the Pipeline page.

### Community 308 - "Community 308"
Cohesion: 1.0
Nodes (1): Typed action payload for the pipeline page controls.

### Community 309 - "Community 309"
Cohesion: 1.0
Nodes (1): Build the current action payload from persisted page state.

### Community 310 - "Community 310"
Cohesion: 1.0
Nodes (1): Hydrate Pipeline page state from a newly selected request template.

### Community 311 - "Community 311"
Cohesion: 1.0
Nodes (1): Build a typed pipeline run config from one rendered Pipeline page action.

### Community 312 - "Community 312"
Cohesion: 1.0
Nodes (1): Build the preview run plan while surfacing validation errors as strings.

### Community 313 - "Community 313"
Cohesion: 1.0
Nodes (1): Return why the Pipeline app page cannot execute the current request.

### Community 314 - "Community 314"
Cohesion: 1.0
Nodes (1): Return the current source-control validation error.

### Community 315 - "Community 315"
Cohesion: 1.0
Nodes (1): Apply one pipeline-page action and return a surfaced error when one occurs.

### Community 316 - "Community 316"
Cohesion: 1.0
Nodes (1): Return available persisted pipeline request configs.

### Community 317 - "Community 317"
Cohesion: 1.0
Nodes (1): Return one compact config selector label.

### Community 318 - "Community 318"
Cohesion: 1.0
Nodes (1): Load one persisted pipeline run config while surfacing validation errors as stri

### Community 319 - "Community 319"
Cohesion: 1.0
Nodes (1): Parse a blankable integer form field.

### Community 320 - "Community 320"
Cohesion: 1.0
Nodes (1): Parse a blankable positive float form field.

### Community 321 - "Community 321"
Cohesion: 1.0
Nodes (1): Return the compact JSON payload rendered by the Pipeline request preview.

### Community 322 - "Community 322"
Cohesion: 1.0
Nodes (1): Build the typed Record3D live source backend config from one pipeline action.

### Community 323 - "Community 323"
Cohesion: 1.0
Nodes (1): Return backend config overrides for one action.

### Community 324 - "Community 324"
Cohesion: 1.0
Nodes (1): Render one typed payload as pretty JSON when present.

### Community 325 - "Community 325"
Cohesion: 1.0
Nodes (1): App-owned preview runtime primitives for live packet consumers.

### Community 326 - "Community 326"
Cohesion: 1.0
Nodes (1): Generic snapshot fields shared by app-owned packet preview consumers.

### Community 327 - "Community 327"
Cohesion: 1.0
Nodes (1): Extract one finite XYZ camera position from one frame packet.

### Community 328 - "Community 328"
Cohesion: 1.0
Nodes (1): Rolling packet metrics shared by preview and replay sessions.

### Community 329 - "Community 329"
Cohesion: 1.0
Nodes (1): Append one packet arrival to the rolling packet-rate window.

### Community 330 - "Community 330"
Cohesion: 1.0
Nodes (1): Append one accepted keyframe sample to the rolling backend window.

### Community 331 - "Community 331"
Cohesion: 1.0
Nodes (1): Append one packet arrival and optional keyframe sample.

### Community 332 - "Community 332"
Cohesion: 1.0
Nodes (1): Return packet-rate snapshot fields.

### Community 333 - "Community 333"
Cohesion: 1.0
Nodes (1): Return backend-keyframe snapshot fields.

### Community 334 - "Community 334"
Cohesion: 1.0
Nodes (1): Return the current metrics in snapshot-ready form.

### Community 335 - "Community 335"
Cohesion: 1.0
Nodes (1): Own one threaded `ObservationStream` worker plus its snapshot state.

### Community 336 - "Community 336"
Cohesion: 1.0
Nodes (1): Return a deep copy of the latest session snapshot.

### Community 337 - "Community 337"
Cohesion: 1.0
Nodes (1): Start a fresh worker after stopping any currently active one.

### Community 338 - "Community 338"
Cohesion: 1.0
Nodes (1): Register the active stream for cooperative stop/disconnect handling.

### Community 339 - "Community 339"
Cohesion: 1.0
Nodes (1): Apply one typed snapshot update under the internal lock.

### Community 340 - "Community 340"
Cohesion: 1.0
Nodes (1): Replace the snapshot under the internal lock.

### Community 341 - "Community 341"
Cohesion: 1.0
Nodes (1): Stop the worker, disconnect the stream, and update the terminal snapshot.

### Community 342 - "Community 342"
Cohesion: 1.0
Nodes (1): Clear the active worker state and persist the final snapshot.

### Community 343 - "Community 343"
Cohesion: 1.0
Nodes (1): Small controller helpers for the Record3D Streamlit page.

### Community 344 - "Community 344"
Cohesion: 1.0
Nodes (1): Apply one Record3D page action and return the latest snapshot.

### Community 345 - "Community 345"
Cohesion: 1.0
Nodes (1): Keep persisted running state aligned with the latest runtime snapshot.

### Community 346 - "Community 346"
Cohesion: 1.0
Nodes (1): Shared Record3D transport controls for app pages.

### Community 347 - "Community 347"
Cohesion: 1.0
Nodes (1): Render the shared Record3D transport controls and return the selection.

### Community 348 - "Community 348"
Cohesion: 1.0
Nodes (1): Return a surfaced input error for the selected Record3D transport.

### Community 349 - "Community 349"
Cohesion: 1.0
Nodes (1): Render the standard transport-detail block for one Record3D selection.

### Community 350 - "Community 350"
Cohesion: 1.0
Nodes (1): Reusable live-preview services for the packaged Streamlit app. Every component o

### Community 351 - "Community 351"
Cohesion: 1.0
Nodes (1): One packet plus the timing metadata needed by shared preview metrics.

### Community 352 - "Community 352"
Cohesion: 1.0
Nodes (1): Drop live packet fields while preserving the last non-live session summary.

### Community 353 - "Community 353"
Cohesion: 1.0
Nodes (1): Run the shared threaded preview loop used by app-owned packet consumers.

### Community 354 - "Community 354"
Cohesion: 1.0
Nodes (1): Typed Streamlit session-state adapter for the packaged app.

### Community 355 - "Community 355"
Cohesion: 1.0
Nodes (1): Persist the typed app state and opaque runtimes under dedicated session keys.

### Community 356 - "Community 356"
Cohesion: 1.0
Nodes (1): Load the current typed app state from Streamlit session storage.

### Community 357 - "Community 357"
Cohesion: 1.0
Nodes (1): Persist the JSON-friendly app state.

### Community 358 - "Community 358"
Cohesion: 1.0
Nodes (1): Load or create the opaque Record3D runtime controller for this session.

### Community 359 - "Community 359"
Cohesion: 1.0
Nodes (1): Load or create the opaque ADVIO preview runtime controller for this session.

### Community 360 - "Community 360"
Cohesion: 1.0
Nodes (1): Load or create the opaque pipeline run facade for this session.

### Community 361 - "Community 361"
Cohesion: 1.0
Nodes (1): Return one stored runtime or replace a stale session object.

### Community 362 - "Community 362"
Cohesion: 1.0
Nodes (1): Persist model updates only when at least one value changed.

### Community 363 - "Community 363"
Cohesion: 1.0
Nodes (1): UI helpers for the packaged Streamlit workbench.

### Community 364 - "Community 364"
Cohesion: 1.0
Nodes (1): Render a lightweight, theme-native page header.

### Community 365 - "Community 365"
Cohesion: 1.0
Nodes (1): Evaluation entry surface for persisted benchmark artifacts.  The :mod:`prml_vsla

### Community 366 - "Community 366"
Cohesion: 1.0
Nodes (1): Shared evaluation contracts not owned by trajectory metric manifests.  Trajector

### Community 367 - "Community 367"
Cohesion: 1.0
Nodes (1): Capture scalar summary statistics for one evaluated error series.

### Community 368 - "Community 368"
Cohesion: 1.0
Nodes (1): Build stats from ``evo``'s ``metric.get_all_statistics()`` payload.

### Community 369 - "Community 369"
Cohesion: 1.0
Nodes (1): Estimated-vs-reference intrinsics residuals in one raster space.

### Community 370 - "Community 370"
Cohesion: 1.0
Nodes (1): Describe the resolved dense-cloud inputs for one evaluation action.

### Community 371 - "Community 371"
Cohesion: 1.0
Nodes (1): Describe offline point-cloud alignment inputs for benchmark runs.

### Community 372 - "Community 372"
Cohesion: 1.0
Nodes (1): Persist one offline cloud-alignment result.

### Community 373 - "Community 373"
Cohesion: 1.0
Nodes (1): Persist one dense-cloud evaluation result for later review.

### Community 374 - "Community 374"
Cohesion: 1.0
Nodes (1): Pure aggregation functions for dataset-wide trajectory metric review.  No I/O —

### Community 375 - "Community 375"
Cohesion: 1.0
Nodes (1): Selector for a specific metric family / pose-relation / statistic combination.

### Community 376 - "Community 376"
Cohesion: 1.0
Nodes (1): One filtered metric value for a single sequence, run, and estimate source.

### Community 377 - "Community 377"
Cohesion: 1.0
Nodes (1): Aggregated metric summary across all sequences for one estimate source.

### Community 378 - "Community 378"
Cohesion: 1.0
Nodes (1): Coverage state for one (sequence, method) cell in the coverage matrix.

### Community 379 - "Community 379"
Cohesion: 1.0
Nodes (1): Rectangular coverage grid for all sequences × all discovered methods.

### Community 380 - "Community 380"
Cohesion: 1.0
Nodes (1): Metric values for a heatmap of sequences × estimate sources.

### Community 381 - "Community 381"
Cohesion: 1.0
Nodes (1): Convert typed metric rows into the canonical long-form table.

### Community 382 - "Community 382"
Cohesion: 1.0
Nodes (1): Validate a metric table back into typed long-form rows.

### Community 383 - "Community 383"
Cohesion: 1.0
Nodes (1): Return available metric selectors with RMSE defaults first.

### Community 384 - "Community 384"
Cohesion: 1.0
Nodes (1): Filter metric rows by page-selected reference and estimate labels.

### Community 385 - "Community 385"
Cohesion: 1.0
Nodes (1): Return one row per metric row matching *metric_filter* across all discovered run

### Community 386 - "Community 386"
Cohesion: 1.0
Nodes (1): Aggregate per-sequence rows into a leaderboard ranked by mean value.      Multip

### Community 387 - "Community 387"
Cohesion: 1.0
Nodes (1): Build a coverage grid for all sequences × discovered methods.

### Community 388 - "Community 388"
Cohesion: 1.0
Nodes (1): Build a heatmap matrix of values indexed by sequence × estimate source.      Mul

### Community 389 - "Community 389"
Cohesion: 1.0
Nodes (1): Pivot long-format metric rows into one wide row per sequence/run/reference/estim

### Community 390 - "Community 390"
Cohesion: 1.0
Nodes (1): Camera-intrinsics comparison utilities.

### Community 391 - "Community 391"
Cohesion: 1.0
Nodes (1): Compare one estimated intrinsics series against a reference camera model.

### Community 392 - "Community 392"
Cohesion: 1.0
Nodes (1): Protocol seams for repository-local evaluation stages.  These protocols describe

### Community 393 - "Community 393"
Cohesion: 1.0
Nodes (1): Load or compute dense-cloud evaluation over normalized run artifacts.      The p

### Community 394 - "Community 394"
Cohesion: 1.0
Nodes (1): Load a persisted dense-cloud evaluation when it exists.

### Community 395 - "Community 395"
Cohesion: 1.0
Nodes (1): Compute and persist one dense-cloud evaluation result.

### Community 396 - "Community 396"
Cohesion: 1.0
Nodes (1): Post-run trajectory evaluation discovery and aggregation helpers.  This module i

### Community 397 - "Community 397"
Cohesion: 1.0
Nodes (1): Coverage summary for one discovered run under a dataset.

### Community 398 - "Community 398"
Cohesion: 1.0
Nodes (1): All discovered run coverage and metric rows for one dataset.

### Community 399 - "Community 399"
Cohesion: 1.0
Nodes (1): Bundle dataset and run choices exposed to review surfaces.

### Community 400 - "Community 400"
Cohesion: 1.0
Nodes (1): Loaded trajectory evaluation state for one discovered run.

### Community 401 - "Community 401"
Cohesion: 1.0
Nodes (1): Read-only post-run query service for trajectory evaluation artifacts.

### Community 402 - "Community 402"
Cohesion: 1.0
Nodes (1): Return all runs under the artifacts root whose sequence manifest matches ``datas

### Community 403 - "Community 403"
Cohesion: 1.0
Nodes (1): Load all run coverage and metric rows for one dataset.

### Community 404 - "Community 404"
Cohesion: 1.0
Nodes (1): Return coverage summaries for all runs matching ``dataset``.

### Community 405 - "Community 405"
Cohesion: 1.0
Nodes (1): Return all metadata-backed runs under the artifacts root that match one sequence

### Community 406 - "Community 406"
Cohesion: 1.0
Nodes (1): Resolve dataset sequences and matching runs for the metrics page.

### Community 407 - "Community 407"
Cohesion: 1.0
Nodes (1): Load one run's trajectory evaluation manifest and metric rows.

### Community 408 - "Community 408"
Cohesion: 1.0
Nodes (1): Load the long-form metrics CSV emitted by the trajectory evaluator.

### Community 409 - "Community 409"
Cohesion: 1.0
Nodes (1): Return the canonical trajectory evaluation manifest path for a run.

### Community 410 - "Community 410"
Cohesion: 1.0
Nodes (1): Return the canonical long-form trajectory metric table path for a run.

### Community 411 - "Community 411"
Cohesion: 1.0
Nodes (1): Load metric error values from an `.npz` error-series artifact.

### Community 412 - "Community 412"
Cohesion: 1.0
Nodes (1): Return True when the manifest's dataset_id matches or is absent.

### Community 413 - "Community 413"
Cohesion: 1.0
Nodes (1): Resolve an error-series path stored in a metrics CSV row.      Handles three cas

### Community 414 - "Community 414"
Cohesion: 1.0
Nodes (1): Evaluation services: trajectory APE/RPE computation and persistence.

### Community 415 - "Community 415"
Cohesion: 1.0
Nodes (1): In-memory APE and RPE preview helpers for trajectory evaluation.

### Community 416 - "Community 416"
Cohesion: 1.0
Nodes (1): Raised when a requested trajectory alignment cannot be computed.

### Community 417 - "Community 417"
Cohesion: 1.0
Nodes (1): Internal single-metric preview for trajectory evaluation.

### Community 418 - "Community 418"
Cohesion: 1.0
Nodes (1): Compute in-memory APE for two normalized TUM trajectory artifacts.      Uses evo

### Community 419 - "Community 419"
Cohesion: 1.0
Nodes (1): Compute in-memory RPE for two normalized TUM trajectory artifacts.      Translat

### Community 420 - "Community 420"
Cohesion: 1.0
Nodes (1): Explicit repair service for regenerating trajectory evaluation artifacts.

### Community 421 - "Community 421"
Cohesion: 1.0
Nodes (1): Mutating service for rebuilding persisted trajectory evaluation artifacts.

### Community 422 - "Community 422"
Cohesion: 1.0
Nodes (1): Recompute and persist trajectory metrics for one discovered run.          This m

### Community 423 - "Community 423"
Cohesion: 1.0
Nodes (1): Remap an absolute path written on another machine to the local artifact root.

### Community 424 - "Community 424"
Cohesion: 1.0
Nodes (1): Trajectory evaluation service for pipeline-driven APE/RPE computation and persis

### Community 425 - "Community 425"
Cohesion: 1.0
Nodes (1): Internal candidate metadata used to persist multi-baseline metrics.

### Community 426 - "Community 426"
Cohesion: 1.0
Nodes (1): Discover runs and compute or reload explicit `evo` trajectory metrics.      The

### Community 427 - "Community 427"
Cohesion: 1.0
Nodes (1): Compute and persist the Sim(3) alignment without running APE metrics.          R

### Community 428 - "Community 428"
Cohesion: 1.0
Nodes (1): Compute and persist trajectory APE/RPE metrics via the `evo` Python API.

### Community 429 - "Community 429"
Cohesion: 1.0
Nodes (1): Compute the trajectory-evaluation stage for one pipeline run.          The stage

### Community 430 - "Community 430"
Cohesion: 1.0
Nodes (1): Persist trajectory metrics for every ordered candidate.

### Community 431 - "Community 431"
Cohesion: 1.0
Nodes (1): Return the deterministic persisted trajectory-alignment path.

### Community 432 - "Community 432"
Cohesion: 1.0
Nodes (1): Return the deterministic Sim(3)-aligned trajectory path.

### Community 433 - "Community 433"
Cohesion: 1.0
Nodes (1): Return the deterministic Sim(3)-aligned point-cloud path.

### Community 434 - "Community 434"
Cohesion: 1.0
Nodes (1): Return the canonical trajectory-evaluation manifest path.

### Community 435 - "Community 435"
Cohesion: 1.0
Nodes (1): Return the canonical long-form trajectory metric table path.

### Community 436 - "Community 436"
Cohesion: 1.0
Nodes (1): Inferred target frame name for UI selections without benchmark input metadata.

### Community 437 - "Community 437"
Cohesion: 1.0
Nodes (1): Inferred coordinate status for UI selections without benchmark input metadata.

### Community 438 - "Community 438"
Cohesion: 1.0
Nodes (1): Dense-cloud diagnostic pipeline stage integration.

### Community 439 - "Community 439"
Cohesion: 1.0
Nodes (1): Persisted config for the diagnostic ``evaluate.cloud`` stage.

### Community 440 - "Community 440"
Cohesion: 1.0
Nodes (1): Reference and estimate artifact-key selection for cloud diagnostics.

### Community 441 - "Community 441"
Cohesion: 1.0
Nodes (1): Runtime spec placeholder for the planned dense-cloud evaluation stage.

### Community 442 - "Community 442"
Cohesion: 1.0
Nodes (1): Trajectory-evaluation pipeline stage integration.

### Community 443 - "Community 443"
Cohesion: 1.0
Nodes (1): Persisted config for the ``evaluate.trajectory`` stage.

### Community 444 - "Community 444"
Cohesion: 1.0
Nodes (1): Stage-owned trajectory-evaluation selection policy.

### Community 445 - "Community 445"
Cohesion: 1.0
Nodes (1): Trajectory-evaluation stage runtime input contracts.

### Community 446 - "Community 446"
Cohesion: 1.0
Nodes (1): Inputs required to compute repository trajectory metrics.

### Community 447 - "Community 447"
Cohesion: 1.0
Nodes (1): Bounded runtime adapter for trajectory evaluation.

### Community 448 - "Community 448"
Cohesion: 1.0
Nodes (1): Mark the bounded runtime as stopped.

### Community 449 - "Community 449"
Cohesion: 1.0
Nodes (1): Compute trajectory metrics and return a canonical stage result.          The res

### Community 450 - "Community 450"
Cohesion: 1.0
Nodes (1): Runtime spec for the trajectory-evaluation stage.

### Community 451 - "Community 451"
Cohesion: 1.0
Nodes (1): Trajectory-evaluation metric contracts and artifact manifest schema.  The trajec

### Community 452 - "Community 452"
Cohesion: 1.0
Nodes (1): Describe one normalized trajectory candidate under a run artifact root.

### Community 453 - "Community 453"
Cohesion: 1.0
Nodes (1): Capture the resolved reference/candidate choice for trajectory computation.

### Community 454 - "Community 454"
Cohesion: 1.0
Nodes (1): Long-form trajectory metric statistic row for cross-run aggregation.

### Community 455 - "Community 455"
Cohesion: 1.0
Nodes (1): Record for a non-primary metric that was attempted but skipped due to a non-fata

### Community 456 - "Community 456"
Cohesion: 1.0
Nodes (1): Describe one persisted reference-vs-candidate trajectory metric case.

### Community 457 - "Community 457"
Cohesion: 1.0
Nodes (1): Canonical manifest for one run's trajectory evaluation outputs.

### Community 458 - "Community 458"
Cohesion: 1.0
Nodes (1): Return the artifact-root identifier used in persisted evaluation rows.

### Community 459 - "Community 459"
Cohesion: 1.0
Nodes (1): Curated import surface for repo-wide shared DTOs.

### Community 460 - "Community 460"
Cohesion: 1.0
Nodes (1): Alignment result DTOs shared outside the alignment package.  These datamodels de

### Community 461 - "Community 461"
Cohesion: 1.0
Nodes (1): Dominant ground-plane hypothesis expressed in native ``world`` coordinates.

### Community 462 - "Community 462"
Cohesion: 1.0
Nodes (1): Finite plane-patch geometry ready for visualization consumers.

### Community 463 - "Community 463"
Cohesion: 1.0
Nodes (1): Result of one derived ground-plane alignment attempt.      When :attr:`applied`

### Community 464 - "Community 464"
Cohesion: 1.0
Nodes (1): Shared artifact reference contracts.

### Community 465 - "Community 465"
Cohesion: 1.0
Nodes (1): Reference one materialized repository artifact by path and fingerprint.

### Community 466 - "Community 466"
Cohesion: 1.0
Nodes (1): Build one stable artifact reference for a materialized path.

### Community 467 - "Community 467"
Cohesion: 1.0
Nodes (1): Canonical camera-intrinsics DTO shared across the package.  This module owns :cl

### Community 468 - "Community 468"
Cohesion: 1.0
Nodes (1): Describe one camera raster in a backend- and dataset-neutral way.      Use this

### Community 469 - "Community 469"
Cohesion: 1.0
Nodes (1): Return the canonical 3x3 pinhole matrix for downstream math.

### Community 470 - "Community 470"
Cohesion: 1.0
Nodes (1): Render the shared intrinsics matrix in the compact LaTeX form used by UI surface

### Community 471 - "Community 471"
Cohesion: 1.0
Nodes (1): Build the shared DTO from a conventional 3x3 row-major camera matrix.

### Community 472 - "Community 472"
Cohesion: 1.0
Nodes (1): Build the shared DTO from a flat 9-value column-major payload.

### Community 473 - "Community 473"
Cohesion: 1.0
Nodes (1): Build the shared DTO from a flat 9-value row-major payload.

### Community 474 - "Community 474"
Cohesion: 1.0
Nodes (1): One camera model sample in a per-frame or per-keyframe intrinsics series.

### Community 475 - "Community 475"
Cohesion: 1.0
Nodes (1): Typed artifact for a sequence of camera intrinsics in one raster space.

### Community 476 - "Community 476"
Cohesion: 1.0
Nodes (1): Build an intrinsics series from a stack of 3x3 camera matrices.

### Community 477 - "Community 477"
Cohesion: 1.0
Nodes (1): Load the repository's canonical single-camera intrinsics YAML schema.

### Community 478 - "Community 478"
Cohesion: 1.0
Nodes (1): Write the repository's canonical single-camera intrinsics YAML schema.

### Community 479 - "Community 479"
Cohesion: 1.0
Nodes (1): Scale one pinhole camera model into a resized raster.

### Community 480 - "Community 480"
Cohesion: 1.0
Nodes (1): Translate one pinhole camera model into a cropped raster.

### Community 481 - "Community 481"
Cohesion: 1.0
Nodes (1): Project intrinsics through the center-crop-and-resize path used by ViSTA image-o

### Community 482 - "Community 482"
Cohesion: 1.0
Nodes (1): Typed geometry payload contracts shared across source and viewer boundaries.  Th

### Community 483 - "Community 483"
Cohesion: 1.0
Nodes (1): Represent unstructured XYZ samples in one named coordinate frame.      ``points_

### Community 484 - "Community 484"
Cohesion: 1.0
Nodes (1): Normalize arrays and validate frame/shape invariants.

### Community 485 - "Community 485"
Cohesion: 1.0
Nodes (1): Represent a raster-aligned camera-local XYZ pointmap.      ``points_xyz_camera``

### Community 486 - "Community 486"
Cohesion: 1.0
Nodes (1): Normalize arrays and validate pointmap shape/frame invariants.

### Community 487 - "Community 487"
Cohesion: 1.0
Nodes (1): Represent a metric depth raster with explicit camera semantics.

### Community 488 - "Community 488"
Cohesion: 1.0
Nodes (1): Normalize arrays and validate depth shape/frame invariants.

### Community 489 - "Community 489"
Cohesion: 1.0
Nodes (1): Shared RDF observation contracts.  This module owns the single observation bound

### Community 490 - "Community 490"
Cohesion: 1.0
Nodes (1): Describe where one normalized observation came from.

### Community 491 - "Community 491"
Cohesion: 1.0
Nodes (1): Return a compact JSON-ready subset for UI details and telemetry sinks.

### Community 492 - "Community 492"
Cohesion: 1.0
Nodes (1): Represent one live, replayed, or file-backed RDF camera observation.

### Community 493 - "Community 493"
Cohesion: 1.0
Nodes (1): Validate RDF geometry, raster alignment, and pose requirements.

### Community 494 - "Community 494"
Cohesion: 1.0
Nodes (1): One row in a durable observation sequence index.

### Community 495 - "Community 495"
Cohesion: 1.0
Nodes (1): Durable ``observation_sequence.v1`` index payload.

### Community 496 - "Community 496"
Cohesion: 1.0
Nodes (1): Ensure the declared observation count matches the row payload.

### Community 497 - "Community 497"
Cohesion: 1.0
Nodes (1): Durable descriptor for a prepared observation sequence.

### Community 498 - "Community 498"
Cohesion: 1.0
Nodes (1): Compatibility import surface for method-owned SLAM artifact contracts.

### Community 499 - "Community 499"
Cohesion: 1.0
Nodes (1): Explicit frame-labelled transform contracts shared across the repository.  This

### Community 500 - "Community 500"
Cohesion: 1.0
Nodes (1): Serializable rigid transform with explicit frame direction.      The transform m

### Community 501 - "Community 501"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.

### Community 502 - "Community 502"
Cohesion: 1.0
Nodes (1): Return the normalized unit quaternion in XYZW order.

### Community 503 - "Community 503"
Cohesion: 1.0
Nodes (1): Return the translation component in XYZ order.

### Community 504 - "Community 504"
Cohesion: 1.0
Nodes (1): Return the transform as a 4x4 homogeneous matrix.

### Community 505 - "Community 505"
Cohesion: 1.0
Nodes (1): Build the shared transform DTO from a 4x4 homogeneous matrix.

### Community 506 - "Community 506"
Cohesion: 1.0
Nodes (1): Return translation and quaternion fields in canonical TUM trajectory order.

### Community 507 - "Community 507"
Cohesion: 1.0
Nodes (1): Project one near-rotation matrix into a validated SO(3) rotation.      Use this

### Community 508 - "Community 508"
Cohesion: 1.0
Nodes (1): Visualization artifact DTOs shared outside the visualization package.  These DTO

### Community 509 - "Community 509"
Cohesion: 1.0
Nodes (1): CLI entry point for the project scaffold.

### Community 510 - "Community 510"
Cohesion: 1.0
Nodes (1): Typer command that appends discoverable RunConfig dotted overrides.

### Community 511 - "Community 511"
Cohesion: 1.0
Nodes (1): Render normal Typer help followed by RunConfig override paths.

### Community 512 - "Community 512"
Cohesion: 1.0
Nodes (1): CLI-owned Rerun web viewer subprocess plus its stdout forwarder thread.

### Community 513 - "Community 513"
Cohesion: 1.0
Nodes (1): Process-table row used by the Rerun viewer cleanup command.

### Community 514 - "Community 514"
Cohesion: 1.0
Nodes (1): Mirror terminal output to one timestamped plain-text run log.

### Community 515 - "Community 515"
Cohesion: 1.0
Nodes (1): Capture one `run-config` command invocation to a timestamped run log.

### Community 516 - "Community 516"
Cohesion: 1.0
Nodes (1): Build the authoritative `uv run ... rerun --serve-web` command.

### Community 517 - "Community 517"
Cohesion: 1.0
Nodes (1): Forward merged child output into the main process stdout.

### Community 518 - "Community 518"
Cohesion: 1.0
Nodes (1): Start the best-effort CLI-owned Rerun web viewer when configured.

### Community 519 - "Community 519"
Cohesion: 1.0
Nodes (1): Terminate the CLI-owned Rerun viewer subprocess and release its pipe.

### Community 520 - "Community 520"
Cohesion: 1.0
Nodes (1): Keep an auto-launched viewer alive after the pipeline reaches terminal state.

### Community 521 - "Community 521"
Cohesion: 1.0
Nodes (1): Read the host process table in the same shape the cleanup command needs.

### Community 522 - "Community 522"
Cohesion: 1.0
Nodes (1): Return true for auto-launched Rerun web viewer processes.

### Community 523 - "Community 523"
Cohesion: 1.0
Nodes (1): Find candidate Rerun web viewer processes in stable pid order.

### Community 524 - "Community 524"
Cohesion: 1.0
Nodes (1): Return unique process-group ids for matched viewer processes.

### Community 525 - "Community 525"
Cohesion: 1.0
Nodes (1): Signal one process group if it still exists.

### Community 526 - "Community 526"
Cohesion: 1.0
Nodes (1): Wait until no matched Rerun viewer processes remain in the target groups.

### Community 527 - "Community 527"
Cohesion: 1.0
Nodes (1): Render matched processes as stable JSON-like records for CLI output.

### Community 528 - "Community 528"
Cohesion: 1.0
Nodes (1): Signal a viewer process group, falling back to the direct child.

### Community 529 - "Community 529"
Cohesion: 1.0
Nodes (1): Print a short summary of the current scaffold.

### Community 530 - "Community 530"
Cohesion: 1.0
Nodes (1): Inspect and terminate orphaned Rerun web viewer processes.

### Community 531 - "Community 531"
Cohesion: 1.0
Nodes (1): Build a typed benchmark run plan from the CLI.

### Community 532 - "Community 532"
Cohesion: 1.0
Nodes (1): Build a typed benchmark run plan from a TOML config file.

### Community 533 - "Community 533"
Cohesion: 1.0
Nodes (1): Run one offline or streaming pipeline config from a TOML file.

### Community 534 - "Community 534"
Cohesion: 1.0
Nodes (1): Execute an already loaded run config with durable command-log capture active.

### Community 535 - "Community 535"
Cohesion: 1.0
Nodes (1): Print the expanded sweep plan as JSON without executing any runs.      Loads the

### Community 536 - "Community 536"
Cohesion: 1.0
Nodes (1): Execute all expanded runs from a sweep TOML sequentially.      Each run reuses t

### Community 537 - "Community 537"
Cohesion: 1.0
Nodes (1): Verify dataset-backed sweep runs can resolve a normalized datastore entry.

### Community 538 - "Community 538"
Cohesion: 1.0
Nodes (1): Evaluate trajectory against a reference directly from an existing artifact root.

### Community 539 - "Community 539"
Cohesion: 1.0
Nodes (1): Persist the canonical ADVIO demo run config as TOML.

### Community 540 - "Community 540"
Cohesion: 1.0
Nodes (1): List USB-connected Record3D devices visible to the bindings.

### Community 541 - "Community 541"
Cohesion: 1.0
Nodes (1): Run the bounded ADVIO replay demo without starting Streamlit.

### Community 542 - "Community 542"
Cohesion: 1.0
Nodes (1): Launch the Streamlit workbench.

### Community 543 - "Community 543"
Cohesion: 1.0
Nodes (1): Print normalized Record3D coverage plus native download-cache state.

### Community 544 - "Community 544"
Cohesion: 1.0
Nodes (1): Download selected Record3D `.r3d` archives.

### Community 545 - "Community 545"
Cohesion: 1.0
Nodes (1): Create or replace normalized dataset entries.

### Community 546 - "Community 546"
Cohesion: 1.0
Nodes (1): Print compact normalized-entry coverage and persisted analysis tables.

### Community 547 - "Community 547"
Cohesion: 1.0
Nodes (1): Inspect one normalized dataset entry without loading heavy RGB/depth payloads.

### Community 548 - "Community 548"
Cohesion: 1.0
Nodes (1): Print normalized ADVIO coverage plus native download-cache state.

### Community 549 - "Community 549"
Cohesion: 1.0
Nodes (1): Download selected ADVIO scene archives and extract complete scenes.

### Community 550 - "Community 550"
Cohesion: 1.0
Nodes (1): Print normalized TUM RGB-D coverage plus native download-cache state.

### Community 551 - "Community 551"
Cohesion: 1.0
Nodes (1): Download selected TUM RGB-D archives and extract complete scenes.

### Community 552 - "Community 552"
Cohesion: 1.0
Nodes (1): Resolve one normalized ADVIO sequence for the CLI demo.

### Community 553 - "Community 553"
Cohesion: 1.0
Nodes (1): Apply canonical ``RunConfig`` field-path overrides after TOML load.

### Community 554 - "Community 554"
Cohesion: 1.0
Nodes (1): Poll the run service until the current demo session reaches a terminal state.

### Community 555 - "Community 555"
Cohesion: 1.0
Nodes (1): Render the final CLI demo snapshot in a compact structured form.

### Community 556 - "Community 556"
Cohesion: 1.0
Nodes (1): Run the Typer application.

### Community 557 - "Community 557"
Cohesion: 1.0
Nodes (1): Public method-wrapper entry surface for PRML VSLAM backends.

### Community 558 - "Community 558"
Cohesion: 1.0
Nodes (1): Provide lazy access to concrete backend wrappers.

### Community 559 - "Community 559"
Cohesion: 1.0
Nodes (1): Method-owned SLAM semantic DTOs.

### Community 560 - "Community 560"
Cohesion: 1.0
Nodes (1): Represent one method-owned incremental SLAM update.

### Community 561 - "Community 561"
Cohesion: 1.0
Nodes (1): LingBot-Map backend integration.

### Community 562 - "Community 562"
Cohesion: 1.0
Nodes (1): Optional LingBot-Map backend adapter.

### Community 563 - "Community 563"
Cohesion: 1.0
Nodes (1): LingBot-Map does not expose incremental live updates through this adapter.

### Community 564 - "Community 564"
Cohesion: 1.0
Nodes (1): Canonical MASt3R-SLAM backend public surface.  This package contains the thin ad

### Community 565 - "Community 565"
Cohesion: 1.0
Nodes (1): Package-local protocol seams for SLAM backends.  These protocols define the meth

### Community 566 - "Community 566"
Cohesion: 1.0
Nodes (1): Execute a backend over normalized offline observations.      Implementations ada

### Community 567 - "Community 567"
Cohesion: 1.0
Nodes (1): Run the backend over normalized observations and persist artifacts.

### Community 568 - "Community 568"
Cohesion: 1.0
Nodes (1): Expose streaming SLAM lifecycle directly on the backend.      :class:`prml_vslam

### Community 569 - "Community 569"
Cohesion: 1.0
Nodes (1): Prepare backend-owned streaming state before frames arrive.

### Community 570 - "Community 570"
Cohesion: 1.0
Nodes (1): Consume one streaming frame through backend-owned state.

### Community 571 - "Community 571"
Cohesion: 1.0
Nodes (1): Retrieve pending method-owned live updates without blocking.

### Community 572 - "Community 572"
Cohesion: 1.0
Nodes (1): Finalize backend-owned streaming state and persist artifacts.

### Community 573 - "Community 573"
Cohesion: 1.0
Nodes (1): Backend that supports both bounded offline runs and streaming sessions.

### Community 574 - "Community 574"
Cohesion: 1.0
Nodes (1): SLAM pipeline stage integration owned by the methods package.

### Community 575 - "Community 575"
Cohesion: 1.0
Nodes (1): Persisted SLAM backend config and backend muxing.  The SLAM stage owns the publi

### Community 576 - "Community 576"
Cohesion: 1.0
Nodes (1): Name the SLAM backends exposed by the pipeline stage config.

### Community 577 - "Community 577"
Cohesion: 1.0
Nodes (1): Return the upstream method name shown to users.

### Community 578 - "Community 578"
Cohesion: 1.0
Nodes (1): Describe optional SLAM geometry materialization.

### Community 579 - "Community 579"
Cohesion: 1.0
Nodes (1): Base for concrete stage-owned SLAM backend variants.

### Community 580 - "Community 580"
Cohesion: 1.0
Nodes (1): Return the user-facing backend label used by planning and UI surfaces.

### Community 581 - "Community 581"
Cohesion: 1.0
Nodes (1): Return the backend discriminator string.

### Community 582 - "Community 582"
Cohesion: 1.0
Nodes (1): Whether the backend supports offline execution.

### Community 583 - "Community 583"
Cohesion: 1.0
Nodes (1): Whether offline source dematerialization should load RGB arrays.

### Community 584 - "Community 584"
Cohesion: 1.0
Nodes (1): Whether the backend supports streaming execution.

### Community 585 - "Community 585"
Cohesion: 1.0
Nodes (1): Whether the backend can expose point-cloud outputs.

### Community 586 - "Community 586"
Cohesion: 1.0
Nodes (1): Whether the backend can emit live preview payloads.

### Community 587 - "Community 587"
Cohesion: 1.0
Nodes (1): Whether the backend may emit native visualization artifacts.

### Community 588 - "Community 588"
Cohesion: 1.0
Nodes (1): Whether the backend supports repository trajectory evaluation.

### Community 589 - "Community 589"
Cohesion: 1.0
Nodes (1): Return backend-owned default resource hints.

### Community 590 - "Community 590"
Cohesion: 1.0
Nodes (1): Return backend-specific planning notes surfaced to callers.

### Community 591 - "Community 591"
Cohesion: 1.0
Nodes (1): Configure the canonical MASt3R-SLAM backend.      Hyperparameters for tracking /

### Community 592 - "Community 592"
Cohesion: 1.0
Nodes (1): Whether the backend supports offline execution.

### Community 593 - "Community 593"
Cohesion: 1.0
Nodes (1): Whether the backend supports streaming execution.

### Community 594 - "Community 594"
Cohesion: 1.0
Nodes (1): Whether the backend can expose point-cloud outputs.

### Community 595 - "Community 595"
Cohesion: 1.0
Nodes (1): Whether the backend can emit live preview payloads.

### Community 596 - "Community 596"
Cohesion: 1.0
Nodes (1): Whether the backend may emit native visualization artifacts.

### Community 597 - "Community 597"
Cohesion: 1.0
Nodes (1): Whether the backend supports repository trajectory evaluation.

### Community 598 - "Community 598"
Cohesion: 1.0
Nodes (1): Return backend-owned default resource hints.

### Community 599 - "Community 599"
Cohesion: 1.0
Nodes (1): Return backend-specific planning notes.

### Community 600 - "Community 600"
Cohesion: 1.0
Nodes (1): Return the backend type instantiated by ``setup_target``.

### Community 601 - "Community 601"
Cohesion: 1.0
Nodes (1): Instantiate the MASt3R backend in the execution process.

### Community 602 - "Community 602"
Cohesion: 1.0
Nodes (1): Configure the canonical ViSTA-SLAM backend.

### Community 603 - "Community 603"
Cohesion: 1.0
Nodes (1): Whether the backend supports offline execution.

### Community 604 - "Community 604"
Cohesion: 1.0
Nodes (1): Whether the backend supports streaming execution.

### Community 605 - "Community 605"
Cohesion: 1.0
Nodes (1): Whether the backend can expose point-cloud outputs.

### Community 606 - "Community 606"
Cohesion: 1.0
Nodes (1): Whether the backend can emit live preview payloads.

### Community 607 - "Community 607"
Cohesion: 1.0
Nodes (1): Whether the backend may emit native visualization artifacts.

### Community 608 - "Community 608"
Cohesion: 1.0
Nodes (1): Whether the backend supports repository trajectory evaluation.

### Community 609 - "Community 609"
Cohesion: 1.0
Nodes (1): Return backend-owned default resource hints.

### Community 610 - "Community 610"
Cohesion: 1.0
Nodes (1): Return backend-specific planning notes.

### Community 611 - "Community 611"
Cohesion: 1.0
Nodes (1): Return the backend type instantiated by ``setup_target``.

### Community 612 - "Community 612"
Cohesion: 1.0
Nodes (1): Instantiate the ViSTA backend in the execution process.

### Community 613 - "Community 613"
Cohesion: 1.0
Nodes (1): Configure the optional LingBot-Map backend.

### Community 614 - "Community 614"
Cohesion: 1.0
Nodes (1): Ensure LingBot image dimensions produce an integral patch grid.

### Community 615 - "Community 615"
Cohesion: 1.0
Nodes (1): Whether the backend supports offline execution.

### Community 616 - "Community 616"
Cohesion: 1.0
Nodes (1): LingBot consumes normalized RGB paths directly during offline inference.

### Community 617 - "Community 617"
Cohesion: 1.0
Nodes (1): Whether the backend supports streaming execution.

### Community 618 - "Community 618"
Cohesion: 1.0
Nodes (1): Whether the backend can expose point-cloud outputs.

### Community 619 - "Community 619"
Cohesion: 1.0
Nodes (1): Whether the backend can emit live preview payloads.

### Community 620 - "Community 620"
Cohesion: 1.0
Nodes (1): Whether the backend may emit native visualization artifacts.

### Community 621 - "Community 621"
Cohesion: 1.0
Nodes (1): Whether the backend supports repository trajectory evaluation.

### Community 622 - "Community 622"
Cohesion: 1.0
Nodes (1): Return backend-owned default resource hints.

### Community 623 - "Community 623"
Cohesion: 1.0
Nodes (1): Return backend-specific planning notes.

### Community 624 - "Community 624"
Cohesion: 1.0
Nodes (1): Return the backend type instantiated by ``setup_target``.

### Community 625 - "Community 625"
Cohesion: 1.0
Nodes (1): Instantiate the LingBot-Map backend in the execution process.

### Community 626 - "Community 626"
Cohesion: 1.0
Nodes (1): Build a typed backend config from a selected method and overrides.

### Community 627 - "Community 627"
Cohesion: 1.0
Nodes (1): Persisted SLAM stage policy.

### Community 628 - "Community 628"
Cohesion: 1.0
Nodes (1): Persisted SLAM stage policy, backend selection, and output policy.

### Community 629 - "Community 629"
Cohesion: 1.0
Nodes (1): Return SLAM-owned output artifacts.

### Community 630 - "Community 630"
Cohesion: 1.0
Nodes (1): Stage-local SLAM runtime input contracts.  These DTOs are private to the pipelin

### Community 631 - "Community 631"
Cohesion: 1.0
Nodes (1): Input needed to run SLAM over one bounded normalized sequence.

### Community 632 - "Community 632"
Cohesion: 1.0
Nodes (1): Input needed to start one incremental SLAM runtime.

### Community 633 - "Community 633"
Cohesion: 1.0
Nodes (1): Terminal SLAM output consumed by downstream stage input builders.

### Community 634 - "Community 634"
Cohesion: 1.0
Nodes (1): SLAM stage runtime implementing the target runtime protocols.  `SlamStageRuntime

### Community 635 - "Community 635"
Cohesion: 1.0
Nodes (1): In-memory run-scoped payload store for live SLAM observer payloads.

### Community 636 - "Community 636"
Cohesion: 1.0
Nodes (1): Store one optional array and return transport-safe metadata.

### Community 637 - "Community 637"
Cohesion: 1.0
Nodes (1): Return a stored payload by transient ref, if still retained.

### Community 638 - "Community 638"
Cohesion: 1.0
Nodes (1): Return a stored payload by handle id, if still retained.

### Community 639 - "Community 639"
Cohesion: 1.0
Nodes (1): Pipeline-facing runtime for offline and streaming SLAM execution.

### Community 640 - "Community 640"
Cohesion: 1.0
Nodes (1): Return the latest queryable SLAM runtime status.

### Community 641 - "Community 641"
Cohesion: 1.0
Nodes (1): Request streaming runtime stop.

### Community 642 - "Community 642"
Cohesion: 1.0
Nodes (1): Run the selected backend over one bounded normalized sequence.

### Community 643 - "Community 643"
Cohesion: 1.0
Nodes (1): Start one incremental SLAM backend session.

### Community 644 - "Community 644"
Cohesion: 1.0
Nodes (1): Submit one frame to the active streaming backend.

### Community 645 - "Community 645"
Cohesion: 1.0
Nodes (1): Return pending live SLAM updates without blocking.

### Community 646 - "Community 646"
Cohesion: 1.0
Nodes (1): Resolve one runtime-owned live payload by transient reference.

### Community 647 - "Community 647"
Cohesion: 1.0
Nodes (1): Resolve one runtime-owned live payload by handle id.

### Community 648 - "Community 648"
Cohesion: 1.0
Nodes (1): Return visualization artifacts collected by the last terminal run.

### Community 649 - "Community 649"
Cohesion: 1.0
Nodes (1): Finalize streaming SLAM and return terminal artifacts.

### Community 650 - "Community 650"
Cohesion: 1.0
Nodes (1): Return a semantic-only update with bulk arrays removed.

### Community 651 - "Community 651"
Cohesion: 1.0
Nodes (1): Runtime spec for the SLAM stage.

### Community 652 - "Community 652"
Cohesion: 1.0
Nodes (1): Stage-local SLAM visualization adapter.  This module translates method-owned :cl

### Community 653 - "Community 653"
Cohesion: 1.0
Nodes (1): Build neutral visualization descriptors for live SLAM updates.

### Community 654 - "Community 654"
Cohesion: 1.0
Nodes (1): Return sink-facing visualization items for one SLAM update.          Args:

### Community 655 - "Community 655"
Cohesion: 1.0
Nodes (1): Canonical ViSTA backend public surface.  This package contains the thin adapter

### Community 656 - "Community 656"
Cohesion: 1.0
Nodes (1): Canonical ViSTA-SLAM backend adapter (offline + streaming).

### Community 657 - "Community 657"
Cohesion: 1.0
Nodes (1): ViSTA-SLAM backend implementing offline and streaming contracts.

### Community 658 - "Community 658"
Cohesion: 1.0
Nodes (1): Load upstream OnlineSLAM and retain backend-owned streaming state.

### Community 659 - "Community 659"
Cohesion: 1.0
Nodes (1): Consume one streaming frame through the active ViSTA runtime.

### Community 660 - "Community 660"
Cohesion: 1.0
Nodes (1): Retrieve pending ViSTA live updates without exposing runtime state.

### Community 661 - "Community 661"
Cohesion: 1.0
Nodes (1): Finalize the active ViSTA streaming runtime and clear it.

### Community 662 - "Community 662"
Cohesion: 1.0
Nodes (1): Run ViSTA-SLAM over normalized offline observations and persist artifacts.

### Community 663 - "Community 663"
Cohesion: 1.0
Nodes (1): ViSTA-native artifact readers.

### Community 664 - "Community 664"
Cohesion: 1.0
Nodes (1): Raw ViSTA view graph coerced into typed Python containers.

### Community 665 - "Community 665"
Cohesion: 1.0
Nodes (1): Load native ViSTA confidence maps and optional threshold.

### Community 666 - "Community 666"
Cohesion: 1.0
Nodes (1): Load one native ViSTA numeric vector and validate its length.

### Community 667 - "Community 667"
Cohesion: 1.0
Nodes (1): Load native ViSTA per-keyframe 3x3 intrinsics matrices.

### Community 668 - "Community 668"
Cohesion: 1.0
Nodes (1): Load native ViSTA trajectory matrices and per-step translation distances.

### Community 669 - "Community 669"
Cohesion: 1.0
Nodes (1): Load and coerce native ViSTA view-graph metadata.

### Community 670 - "Community 670"
Cohesion: 1.0
Nodes (1): Load the standardized estimated intrinsics artifact written by the ViSTA normali

### Community 671 - "Community 671"
Cohesion: 1.0
Nodes (1): Load native ViSTA view names when present and aligned to the expected keyframe c

### Community 672 - "Community 672"
Cohesion: 1.0
Nodes (1): Native artifact normalization helpers for ViSTA-SLAM.  This module handles end-o

### Community 673 - "Community 673"
Cohesion: 1.0
Nodes (1): Diagnostics derived from ViSTA-native persisted artifacts.

### Community 674 - "Community 674"
Cohesion: 1.0
Nodes (1): One undirected edge in the native ViSTA view graph.

### Community 675 - "Community 675"
Cohesion: 1.0
Nodes (1): Degree summary for one view-graph node.

### Community 676 - "Community 676"
Cohesion: 1.0
Nodes (1): Summary of the native ViSTA view graph.

### Community 677 - "Community 677"
Cohesion: 1.0
Nodes (1): Diagnostic summary derived from native ViSTA outputs.

### Community 678 - "Community 678"
Cohesion: 1.0
Nodes (1): Load lightweight diagnostic summaries from native ViSTA artifacts.

### Community 679 - "Community 679"
Cohesion: 1.0
Nodes (1): Frame preprocessing helpers for ViSTA-SLAM.

### Community 680 - "Community 680"
Cohesion: 1.0
Nodes (1): One RGB frame prepared for upstream ViSTA ingestion.

### Community 681 - "Community 681"
Cohesion: 1.0
Nodes (1): Use the exact upstream ViSTA crop-and-resize helper path.

### Community 682 - "Community 682"
Cohesion: 1.0
Nodes (1): Convert one upstream ViSTA array-like payload into a numpy array.

### Community 683 - "Community 683"
Cohesion: 1.0
Nodes (1): Upstream ViSTA runtime and bootstrap helpers.  This module owns the heavy liftin

### Community 684 - "Community 684"
Cohesion: 1.0
Nodes (1): Subset of the upstream flow-tracker API consumed by the session wrapper.

### Community 685 - "Community 685"
Cohesion: 1.0
Nodes (1): Return whether the current frame should become a new keyframe.

### Community 686 - "Community 686"
Cohesion: 1.0
Nodes (1): Subset of the upstream OnlineSLAM API consumed by the wrapper.

### Community 687 - "Community 687"
Cohesion: 1.0
Nodes (1): Consume one prepared keyframe payload through the upstream runtime API.

### Community 688 - "Community 688"
Cohesion: 1.0
Nodes (1): Persist native ViSTA outputs for later normalization.

### Community 689 - "Community 689"
Cohesion: 1.0
Nodes (1): Return one live view payload from the upstream pose graph.

### Community 690 - "Community 690"
Cohesion: 1.0
Nodes (1): Return preview RGB and dense pointmap payloads for one live view.

### Community 691 - "Community 691"
Cohesion: 1.0
Nodes (1): Subset of the DBoW vocabulary API used for binary cache generation.

### Community 692 - "Community 692"
Cohesion: 1.0
Nodes (1): Load the text vocabulary from disk.

### Community 693 - "Community 693"
Cohesion: 1.0
Nodes (1): Write the vocabulary back to disk in the requested format.

### Community 694 - "Community 694"
Cohesion: 1.0
Nodes (1): Subset of the imported DBoW module used by this wrapper.

### Community 695 - "Community 695"
Cohesion: 1.0
Nodes (1): Construct one vocabulary instance.

### Community 696 - "Community 696"
Cohesion: 1.0
Nodes (1): Bundle the concrete upstream runtime objects consumed by the session wrapper.

### Community 697 - "Community 697"
Cohesion: 1.0
Nodes (1): Instantiate one configured upstream ViSTA runtime bundle.      This is the main

### Community 698 - "Community 698"
Cohesion: 1.0
Nodes (1): Return the effective vocabulary path, building the binary cache when needed.

### Community 699 - "Community 699"
Cohesion: 1.0
Nodes (1): Register the upstream `vista_slam` checkout as an explicit namespace package.

### Community 700 - "Community 700"
Cohesion: 1.0
Nodes (1): Import the installed `DBoW3Py` dependency with an actionable error.

### Community 701 - "Community 701"
Cohesion: 1.0
Nodes (1): Streaming runtime wrapper for ViSTA-SLAM.  This module exposes the upstream `Onl

### Community 702 - "Community 702"
Cohesion: 1.0
Nodes (1): Stateful streaming runtime that forwards frames to upstream OnlineSLAM.      The

### Community 703 - "Community 703"
Cohesion: 1.0
Nodes (1): Feed one frame to OnlineSLAM and buffer incremental telemetry.

### Community 704 - "Community 704"
Cohesion: 1.0
Nodes (1): Retrieve and clear any pending incremental SLAM updates.

### Community 705 - "Community 705"
Cohesion: 1.0
Nodes (1): Persist upstream outputs and convert to canonical repository artifacts.

### Community 706 - "Community 706"
Cohesion: 1.0
Nodes (1): Read one upstream view and convert it into live repo telemetry.          The ret

### Community 707 - "Community 707"
Cohesion: 1.0
Nodes (1): Normalize one upstream ViSTA pointmap payload without changing semantics.      T

### Community 708 - "Community 708"
Cohesion: 1.0
Nodes (1): Count valid metric points in one pointmap.

### Community 709 - "Community 709"
Cohesion: 1.0
Nodes (1): Describe a non-fatal pointmap issue for one accepted keyframe.

### Community 710 - "Community 710"
Cohesion: 1.0
Nodes (1): Construct one fully-wired ViSTA runtime from repo config and paths.

### Community 711 - "Community 711"
Cohesion: 1.0
Nodes (1): Public orchestration surface for the repository pipeline.

### Community 712 - "Community 712"
Cohesion: 1.0
Nodes (1): Inspection helpers for persisted pipeline run artifact roots.

### Community 713 - "Community 713"
Cohesion: 1.0
Nodes (1): One selectable persisted method-level run artifact root.

### Community 714 - "Community 714"
Cohesion: 1.0
Nodes (1): Shallow diagnostics for materialized offline input artifacts.

### Community 715 - "Community 715"
Cohesion: 1.0
Nodes (1): One submitted run attempt found in a persisted event log.

### Community 716 - "Community 716"
Cohesion: 1.0
Nodes (1): Structured inspection result for one persisted pipeline run.

### Community 717 - "Community 717"
Cohesion: 1.0
Nodes (1): Discover method-level run roots under the configured artifact directory.

### Community 718 - "Community 718"
Cohesion: 1.0
Nodes (1): Load typed metadata and path inventory for one persisted run root.

### Community 719 - "Community 719"
Cohesion: 1.0
Nodes (1): Backend boundary between launch surfaces and execution substrates.  This module

### Community 720 - "Community 720"
Cohesion: 1.0
Nodes (1): Execute, monitor, and tear down pipeline runs.      Implementations own the conc

### Community 721 - "Community 721"
Cohesion: 1.0
Nodes (1): Start one run and return the stable run identifier.          Args:             r

### Community 722 - "Community 722"
Cohesion: 1.0
Nodes (1): Request graceful stop for one active run.

### Community 723 - "Community 723"
Cohesion: 1.0
Nodes (1): Return the latest projected metadata view for one run.

### Community 724 - "Community 724"
Cohesion: 1.0
Nodes (1): Return recent runtime events for one run.          Args:             run_id: Sta

### Community 725 - "Community 725"
Cohesion: 1.0
Nodes (1): Resolve one target transient payload ref into a local array.

### Community 726 - "Community 726"
Cohesion: 1.0
Nodes (1): Release backend-owned runtime resources.          Args:             preserve_loc

### Community 727 - "Community 727"
Cohesion: 1.0
Nodes (1): Ray-backed backend for plan execution and run attachment.  This module owns subs

### Community 728 - "Community 728"
Cohesion: 1.0
Nodes (1): Return Ray resources for the coordinator-hosted execution runtime.

### Community 729 - "Community 729"
Cohesion: 1.0
Nodes (1): Execute pipeline runs through detached per-run coordinator actors.      The back

### Community 730 - "Community 730"
Cohesion: 1.0
Nodes (1): Build the plan, ensure Ray is available, and boot one coordinator.

### Community 731 - "Community 731"
Cohesion: 1.0
Nodes (1): Forward a stop request to the named coordinator actor.

### Community 732 - "Community 732"
Cohesion: 1.0
Nodes (1): Fetch the latest projected snapshot from the coordinator actor.

### Community 733 - "Community 733"
Cohesion: 1.0
Nodes (1): Fetch trailing events from the coordinator actor.

### Community 734 - "Community 734"
Cohesion: 1.0
Nodes (1): Resolve one coordinator-owned target transient payload ref.

### Community 735 - "Community 735"
Cohesion: 1.0
Nodes (1): Detach from Ray and stop any backend-owned shared infrastructure.

### Community 736 - "Community 736"
Cohesion: 1.0
Nodes (1): Pipeline run configuration and fixed stage-section bundle.

### Community 737 - "Community 737"
Cohesion: 1.0
Nodes (1): Pipeline-owned contract namespace.  This package contains the typed context, pla

### Community 738 - "Community 738"
Cohesion: 1.0
Nodes (1): Inputs available while compiling a deterministic run plan.

### Community 739 - "Community 739"
Cohesion: 1.0
Nodes (1): Inputs available while constructing and executing stage runtimes.

### Community 740 - "Community 740"
Cohesion: 1.0
Nodes (1): Pipeline execution mode contract.

### Community 741 - "Community 741"
Cohesion: 1.0
Nodes (1): Select whether the run is batch/offline or live/incremental.

### Community 742 - "Community 742"
Cohesion: 1.0
Nodes (1): Deterministic planning contracts for the pipeline.  This module owns the side-ef

### Community 743 - "Community 743"
Cohesion: 1.0
Nodes (1): Compact source selection snapshot captured in the deterministic plan.

### Community 744 - "Community 744"
Cohesion: 1.0
Nodes (1): Describe one planned stage in the deterministic execution order.

### Community 745 - "Community 745"
Cohesion: 1.0
Nodes (1): Represent the deterministic plan compiled from one launch config.      The plan

### Community 746 - "Community 746"
Cohesion: 1.0
Nodes (1): Return compact rows suitable for CLI or UI plan previews.

### Community 747 - "Community 747"
Cohesion: 1.0
Nodes (1): Projected runtime snapshot contracts.  This module owns the live metadata view d

### Community 748 - "Community 748"
Cohesion: 1.0
Nodes (1): Project the latest run state from the append-only event stream.      Callers sho

### Community 749 - "Community 749"
Cohesion: 1.0
Nodes (1): Typed stage vocabulary shared across planning, runtime, and provenance.

### Community 750 - "Community 750"
Cohesion: 1.0
Nodes (1): Name the canonical target stage vocabulary.

### Community 751 - "Community 751"
Cohesion: 1.0
Nodes (1): Return the human-readable label shown in plan previews.

### Community 752 - "Community 752"
Cohesion: 1.0
Nodes (1): Strict transport-safe model base for pipeline-owned runtime contracts.  This mod

### Community 753 - "Community 753"
Cohesion: 1.0
Nodes (1): Provide the strict validation baseline for transport-safe pipeline DTOs.

### Community 754 - "Community 754"
Cohesion: 1.0
Nodes (1): Shared helpers for the bounded dataset pipeline demo.

### Community 755 - "Community 755"
Cohesion: 1.0
Nodes (1): Build the canonical bounded ADVIO demo run config shared by app and CLI.

### Community 756 - "Community 756"
Cohesion: 1.0
Nodes (1): Load one launchable pipeline config through the target RunConfig contract.

### Community 757 - "Community 757"
Cohesion: 1.0
Nodes (1): Build the runtime source required by one target run config.

### Community 758 - "Community 758"
Cohesion: 1.0
Nodes (1): Persist a pipeline run config TOML through the repo-owned config path helper.

### Community 759 - "Community 759"
Cohesion: 1.0
Nodes (1): Persist the canonical ADVIO demo run config under `.configs/pipelines/` by defau

### Community 760 - "Community 760"
Cohesion: 1.0
Nodes (1): Repo-owned placement policy translation for the Ray backend.  This module contai

### Community 761 - "Community 761"
Cohesion: 1.0
Nodes (1): Translate one repo-owned stage execution policy into Ray actor options.

### Community 762 - "Community 762"
Cohesion: 1.0
Nodes (1): Ray runtime package for pipeline execution actors.

### Community 763 - "Community 763"
Cohesion: 1.0
Nodes (1): Ray actors that execute streaming source I/O.

### Community 764 - "Community 764"
Cohesion: 1.0
Nodes (1): Read packets from one streaming source with coordinator-owned credits.

### Community 765 - "Community 765"
Cohesion: 1.0
Nodes (1): Drop raster payloads that are transported through explicit Ray refs.

### Community 766 - "Community 766"
Cohesion: 1.0
Nodes (1): Ray substrate bootstrap helpers for the pipeline backend.

### Community 767 - "Community 767"
Cohesion: 1.0
Nodes (1): Set environment flags that Ray snapshots at import and init time.

### Community 768 - "Community 768"
Cohesion: 1.0
Nodes (1): Build the process-wide Ray runtime environment for this backend.

### Community 769 - "Community 769"
Cohesion: 1.0
Nodes (1): Own a backend-managed local Ray head process and its reuse metadata.

### Community 770 - "Community 770"
Cohesion: 1.0
Nodes (1): Return a connectable local Ray head address, starting one if needed.

### Community 771 - "Community 771"
Cohesion: 1.0
Nodes (1): Stop any local Ray head owned or tracked by this backend.

### Community 772 - "Community 772"
Cohesion: 1.0
Nodes (1): Return whether ``exc`` looks like a transient local Ray connection failure.

### Community 773 - "Community 773"
Cohesion: 1.0
Nodes (1): Thin launch-surface façade over the active pipeline backend.  This module contai

### Community 774 - "Community 774"
Cohesion: 1.0
Nodes (1): Start and inspect at most one active run from app or CLI code.      The service

### Community 775 - "Community 775"
Cohesion: 1.0
Nodes (1): Start one run and replace any previously tracked active run.

### Community 776 - "Community 776"
Cohesion: 1.0
Nodes (1): Request stop for the currently tracked run, if one exists.

### Community 777 - "Community 777"
Cohesion: 1.0
Nodes (1): Return the latest projected snapshot for the active run.          Returns an emp

### Community 778 - "Community 778"
Cohesion: 1.0
Nodes (1): Return trailing events for the active run.          Args:             after_even

### Community 779 - "Community 779"
Cohesion: 1.0
Nodes (1): Resolve one active-run transient payload ref into a local NumPy array.

### Community 780 - "Community 780"
Cohesion: 1.0
Nodes (1): Shut down the backing runtime if one has been created.

### Community 781 - "Community 781"
Cohesion: 1.0
Nodes (1): Observer sinks for pipeline runtime events.

### Community 782 - "Community 782"
Cohesion: 1.0
Nodes (1): Durable JSONL event sink.

### Community 783 - "Community 783"
Cohesion: 1.0
Nodes (1): Append-only JSONL sink for durable semantic events.

### Community 784 - "Community 784"
Cohesion: 1.0
Nodes (1): Project append-only runtime events into live metadata snapshots.  This module co

### Community 785 - "Community 785"
Cohesion: 1.0
Nodes (1): Derive :class:`RunSnapshot` values from append-only runtime events.      This pr

### Community 786 - "Community 786"
Cohesion: 1.0
Nodes (1): Apply a sequence of events in order and return the final projected snapshot.

### Community 787 - "Community 787"
Cohesion: 1.0
Nodes (1): Apply one event to one snapshot.          Args:             snapshot: Previous p

### Community 788 - "Community 788"
Cohesion: 1.0
Nodes (1): Apply one live runtime update to one snapshot without durable events.

### Community 789 - "Community 789"
Cohesion: 1.0
Nodes (1): Copy only the mutable containers that projection mutates.

### Community 790 - "Community 790"
Cohesion: 1.0
Nodes (1): Stage-local pipeline runtime packages.

### Community 791 - "Community 791"
Cohesion: 1.0
Nodes (1): Generic stage runtime contract package.

### Community 792 - "Community 792"
Cohesion: 1.0
Nodes (1): Base declarative policy shared by target stage config sections.

### Community 793 - "Community 793"
Cohesion: 1.0
Nodes (1): Generic stage runtime DTOs for the pipeline refactor target.  These contracts de

### Community 794 - "Community 794"
Cohesion: 1.0
Nodes (1): Generic transient payload references for stage runtime updates.  This module own

### Community 795 - "Community 795"
Cohesion: 1.0
Nodes (1): Reference one run-scoped live payload stored outside durable artifacts.      The

### Community 796 - "Community 796"
Cohesion: 1.0
Nodes (1): Generic runtime capability protocols for pipeline stages.  These protocols descr

### Community 797 - "Community 797"
Cohesion: 1.0
Nodes (1): Common lifecycle surface implemented by every stage runtime.      The base proto

### Community 798 - "Community 798"
Cohesion: 1.0
Nodes (1): Return the latest queryable runtime status.

### Community 799 - "Community 799"
Cohesion: 1.0
Nodes (1): Request runtime shutdown or cancellation.

### Community 800 - "Community 800"
Cohesion: 1.0
Nodes (1): Capability surface for bounded or batch-like stage execution.      ``Offline`` m

### Community 801 - "Community 801"
Cohesion: 1.0
Nodes (1): Run the stage over one bounded input payload.

### Community 802 - "Community 802"
Cohesion: 1.0
Nodes (1): Capability surface for runtimes that emit live observer updates.      Draining i

### Community 803 - "Community 803"
Cohesion: 1.0
Nodes (1): Return pending live updates without blocking for new work.

### Community 804 - "Community 804"
Cohesion: 1.0
Nodes (1): Capability surface for active runtimes that accept stream items.      Streaming

### Community 805 - "Community 805"
Cohesion: 1.0
Nodes (1): Start the streaming runtime with its run-scoped input payload.

### Community 806 - "Community 806"
Cohesion: 1.0
Nodes (1): Submit one hot-path stream item to the runtime.

### Community 807 - "Community 807"
Cohesion: 1.0
Nodes (1): Finalize streaming execution and return the terminal stage result.

### Community 808 - "Community 808"
Cohesion: 1.0
Nodes (1): Minimal local runtime handle used by the pipeline coordinator.

### Community 809 - "Community 809"
Cohesion: 1.0
Nodes (1): Wrap one local runtime with status counters.

### Community 810 - "Community 810"
Cohesion: 1.0
Nodes (1): Return wrapped runtime status with handle-owned counters.

### Community 811 - "Community 811"
Cohesion: 1.0
Nodes (1): Request runtime stop through the wrapped runtime.

### Community 812 - "Community 812"
Cohesion: 1.0
Nodes (1): Invoke the wrapped offline runtime.

### Community 813 - "Community 813"
Cohesion: 1.0
Nodes (1): Drain updates from a live-update runtime.

### Community 814 - "Community 814"
Cohesion: 1.0
Nodes (1): Start the wrapped streaming runtime.

### Community 815 - "Community 815"
Cohesion: 1.0
Nodes (1): Submit one item to the wrapped streaming runtime.

### Community 816 - "Community 816"
Cohesion: 1.0
Nodes (1): Finalize the wrapped streaming runtime.

### Community 817 - "Community 817"
Cohesion: 1.0
Nodes (1): Ray-specific helpers for future stage runtime deployment.  This module intention

### Community 818 - "Community 818"
Cohesion: 1.0
Nodes (1): Lifecycle-only helpers for stage runtimes.

### Community 819 - "Community 819"
Cohesion: 1.0
Nodes (1): Reusable lifecycle/status state for concrete stage runtimes.      The mixin deli

### Community 820 - "Community 820"
Cohesion: 1.0
Nodes (1): Return the current lifecycle status.

### Community 821 - "Community 821"
Cohesion: 1.0
Nodes (1): Mark the runtime as stopped and remember the stop request.

### Community 822 - "Community 822"
Cohesion: 1.0
Nodes (1): Stage-owned runtime integration contracts.  Specs bind the generic runner to dom

### Community 823 - "Community 823"
Cohesion: 1.0
Nodes (1): Stage-owned integration surface used by generic runtime plumbing.

### Community 824 - "Community 824"
Cohesion: 1.0
Nodes (1): Registry of stage-owned runtime specs.

### Community 825 - "Community 825"
Cohesion: 1.0
Nodes (1): Return the registered runtime spec for ``stage_key``.

### Community 826 - "Community 826"
Cohesion: 1.0
Nodes (1): Summary stage runtime package.

### Community 827 - "Community 827"
Cohesion: 1.0
Nodes (1): Persisted config for the projection-only ``summary`` stage.

### Community 828 - "Community 828"
Cohesion: 1.0
Nodes (1): Bounded runtime adapter for projection-only run summaries.

### Community 829 - "Community 829"
Cohesion: 1.0
Nodes (1): Inputs required to project durable summary artifacts.

### Community 830 - "Community 830"
Cohesion: 1.0
Nodes (1): Mark the bounded runtime as stopped.

### Community 831 - "Community 831"
Cohesion: 1.0
Nodes (1): Runtime spec for the summary stage.

### Community 832 - "Community 832"
Cohesion: 1.0
Nodes (1): Dataset × method sweep expansion and sequential execution support.  This module

### Community 833 - "Community 833"
Cohesion: 1.0
Nodes (1): Raise ValueError when *value* is not safe for use in a run ID.      Args:

### Community 834 - "Community 834"
Cohesion: 1.0
Nodes (1): Read a TOML file and return its raw dict.      Args:         path: Absolute or r

### Community 835 - "Community 835"
Cohesion: 1.0
Nodes (1): Extract only ``[stages.slam]`` from a method template TOML.      All sections ot

### Community 836 - "Community 836"
Cohesion: 1.0
Nodes (1): Map a :class:`SweepDataset` to the matching :class:`SourceBackendConfig`.      A

### Community 837 - "Community 837"
Cohesion: 1.0
Nodes (1): Top-level sweep identity and output routing.      Attributes:         name: Huma

### Community 838 - "Community 838"
Cohesion: 1.0
Nodes (1): Ensure *name* is safe to embed in run IDs.

### Community 839 - "Community 839"
Cohesion: 1.0
Nodes (1): One dataset entry in a sweep, including downstream stage-enablement policy.

### Community 840 - "Community 840"
Cohesion: 1.0
Nodes (1): Ensure *dataset_id* and *sequence_id* are safe to embed in run IDs.

### Community 841 - "Community 841"
Cohesion: 1.0
Nodes (1): Keep stored-profile sampling unambiguous.

### Community 842 - "Community 842"
Cohesion: 1.0
Nodes (1): Reference to a method template TOML file.      The sweeper reads only ``[stages.

### Community 843 - "Community 843"
Cohesion: 1.0
Nodes (1): Root sweep configuration loaded from a sweep TOML file.      A sweep TOML has th

### Community 844 - "Community 844"
Cohesion: 1.0
Nodes (1): Ensure every method ID is slug-safe.

### Community 845 - "Community 845"
Cohesion: 1.0
Nodes (1): Ensure no two ``[[datasets]]`` entries share ``(dataset_id, sequence_id)``.

### Community 846 - "Community 846"
Cohesion: 1.0
Nodes (1): One fully-expanded sweep item ready for execution.      :func:`expand_sweep` pro

### Community 847 - "Community 847"
Cohesion: 1.0
Nodes (1): Load and validate a sweep TOML file.      Args:         path: Path to the sweep

### Community 848 - "Community 848"
Cohesion: 1.0
Nodes (1): Expand a :class:`SweepConfig` into a deterministic list of :class:`SweepRunItem`

### Community 849 - "Community 849"
Cohesion: 1.0
Nodes (1): Build a :class:`RunConfig` from one expanded :class:`SweepRunItem`.      The res

### Community 850 - "Community 850"
Cohesion: 1.0
Nodes (1): Derive the deterministic run ID for one dataset × method combination.

### Community 851 - "Community 851"
Cohesion: 1.0
Nodes (1): Resolve *path* using *path_config* when provided, otherwise return as-is.

### Community 852 - "Community 852"
Cohesion: 1.0
Nodes (1): Plotly figure builders for the packaged Streamlit app.

### Community 853 - "Community 853"
Cohesion: 1.0
Nodes (1): Plotly figure builders for the ADVIO dataset page.

### Community 854 - "Community 854"
Cohesion: 1.0
Nodes (1): Build a stacked venue/environment overview for the catalog.

### Community 855 - "Community 855"
Cohesion: 1.0
Nodes (1): Build a high-level local availability summary.

### Community 856 - "Community 856"
Cohesion: 1.0
Nodes (1): Build a crowd-density composition chart.

### Community 857 - "Community 857"
Cohesion: 1.0
Nodes (1): Build a scene-attribute prevalence chart.

### Community 858 - "Community 858"
Cohesion: 1.0
Nodes (1): Build ADVIO explorer overlays with explicit comparison semantics.

### Community 859 - "Community 859"
Cohesion: 1.0
Nodes (1): Plotly builders for persisted artifact diagnostics.

### Community 860 - "Community 860"
Cohesion: 1.0
Nodes (1): Build confidence and valid-pixel-ratio diagnostics over native keyframes.

### Community 861 - "Community 861"
Cohesion: 1.0
Nodes (1): Build native scale estimates over keyframes.

### Community 862 - "Community 862"
Cohesion: 1.0
Nodes (1): Build native intrinsics drift over keyframes.

### Community 863 - "Community 863"
Cohesion: 1.0
Nodes (1): Build model-raster estimated-vs-reference intrinsics residuals.

### Community 864 - "Community 864"
Cohesion: 1.0
Nodes (1): Build native trajectory step distance and normalized TUM timestamp spacing.

### Community 865 - "Community 865"
Cohesion: 1.0
Nodes (1): Build view-graph degree and edge-gap diagnostics.

### Community 866 - "Community 866"
Cohesion: 1.0
Nodes (1): Plotly figure builders for normalized dataset analysis tables.

### Community 867 - "Community 867"
Cohesion: 1.0
Nodes (1): Build a stacked payload-size chart from normalized footprint rows.

### Community 868 - "Community 868"
Cohesion: 1.0
Nodes (1): Build a per-scene observation metric bar chart.

### Community 869 - "Community 869"
Cohesion: 1.0
Nodes (1): Build a per-scene trajectory metric bar chart.

### Community 870 - "Community 870"
Cohesion: 1.0
Nodes (1): Build a sampled 3D reference-cloud view with optional trajectory overlays.

### Community 871 - "Community 871"
Cohesion: 1.0
Nodes (1): Plotly figure builders for the metrics page.

### Community 872 - "Community 872"
Cohesion: 1.0
Nodes (1): Trajectory payload needed by the metrics plot builders.

### Community 873 - "Community 873"
Cohesion: 1.0
Nodes (1): Error-series payload needed by the metrics plot builders.

### Community 874 - "Community 874"
Cohesion: 1.0
Nodes (1): Build a compact XY trajectory overlay figure.

### Community 875 - "Community 875"
Cohesion: 1.0
Nodes (1): Build the per-pair `evo` error profile.

### Community 876 - "Community 876"
Cohesion: 1.0
Nodes (1): Build a cross-run RMSE summary for persisted trajectory metric rows.

### Community 877 - "Community 877"
Cohesion: 1.0
Nodes (1): Build an empirical CDF for one or more persisted error series.

### Community 878 - "Community 878"
Cohesion: 1.0
Nodes (1): Build a distribution box plot for one or more persisted error series.

### Community 879 - "Community 879"
Cohesion: 1.0
Nodes (1): Build a Plotly heatmap of metric values indexed by sequence × estimate source.

### Community 880 - "Community 880"
Cohesion: 1.0
Nodes (1): Build a grouped bar chart of metric values by sequence and estimate source.

### Community 881 - "Community 881"
Cohesion: 1.0
Nodes (1): Build a heatmap showing manifest coverage for each sequence × method cell.

### Community 882 - "Community 882"
Cohesion: 1.0
Nodes (1): Build a violin plot of metric values grouped by estimate source.

### Community 883 - "Community 883"
Cohesion: 1.0
Nodes (1): Plotly figure builders for pipeline-demo-specific visualizations.

### Community 884 - "Community 884"
Cohesion: 1.0
Nodes (1): Trajectory payload needed by pipeline plot builders.

### Community 885 - "Community 885"
Cohesion: 1.0
Nodes (1): Error-series payload needed by pipeline plot builders.

### Community 886 - "Community 886"
Cohesion: 1.0
Nodes (1): Build a 3D trajectory overlay with `evo` APE shown as a color map.

### Community 887 - "Community 887"
Cohesion: 1.0
Nodes (1): Return a renderable preview image for one pointmap-like preview artifact.

### Community 888 - "Community 888"
Cohesion: 1.0
Nodes (1): Build a compact rolling telemetry line chart for one stage metric.

### Community 889 - "Community 889"
Cohesion: 1.0
Nodes (1): Plotly builders for persisted reconstruction artifacts.

### Community 890 - "Community 890"
Cohesion: 1.0
Nodes (1): Summary of one rendered reconstruction artifact view.

### Community 891 - "Community 891"
Cohesion: 1.0
Nodes (1): Summary of one SLAM-vs-reference comparison figure.

### Community 892 - "Community 892"
Cohesion: 1.0
Nodes (1): Build an interactive Plotly view for reference reconstruction PLY artifacts.

### Community 893 - "Community 893"
Cohesion: 1.0
Nodes (1): Build a sampled SLAM-vs-reference spatial comparison figure.

### Community 894 - "Community 894"
Cohesion: 1.0
Nodes (1): Plotly figure builders for the Record3D page.

### Community 895 - "Community 895"
Cohesion: 1.0
Nodes (1): Build a compact 3D ego-trajectory figure for live Record3D poses.

### Community 896 - "Community 896"
Cohesion: 1.0
Nodes (1): Shared Plotly theme helpers for the packaged Streamlit app.

### Community 897 - "Community 897"
Cohesion: 1.0
Nodes (1): Apply the shared 2D layout used across workbench figures.

### Community 898 - "Community 898"
Cohesion: 1.0
Nodes (1): Apply the shared 3D layout used across workbench figures.

### Community 899 - "Community 899"
Cohesion: 1.0
Nodes (1): Reusable trajectory plotting helpers for dataset and evaluation pages.

### Community 900 - "Community 900"
Cohesion: 1.0
Nodes (1): Build a bird's-eye trajectory overlay for one or more trajectories.

### Community 901 - "Community 901"
Cohesion: 1.0
Nodes (1): Build a 3D trajectory overlay and optional sampled pose axes.

### Community 902 - "Community 902"
Cohesion: 1.0
Nodes (1): Build a per-trajectory speed-over-time figure.

### Community 903 - "Community 903"
Cohesion: 1.0
Nodes (1): Build a height-over-time profile for one or more trajectories.

### Community 904 - "Community 904"
Cohesion: 1.0
Nodes (1): Build a per-series timestamp-spacing profile in milliseconds.

### Community 905 - "Community 905"
Cohesion: 1.0
Nodes (1): Return the total path length in metres.

### Community 906 - "Community 906"
Cohesion: 1.0
Nodes (1): Lightweight builder for BEV and 3D trajectory views.

### Community 907 - "Community 907"
Cohesion: 1.0
Nodes (1): Add one trajectory trace with start and end markers.

### Community 908 - "Community 908"
Cohesion: 1.0
Nodes (1): Add sampled local pose axes for a 3D trajectory.

### Community 909 - "Community 909"
Cohesion: 1.0
Nodes (1): Finalize the figure layout and return it.

### Community 910 - "Community 910"
Cohesion: 1.0
Nodes (1): Public reconstruction entry surface for reference-scene builders.  The :mod:`prm

### Community 911 - "Community 911"
Cohesion: 1.0
Nodes (1): Canonical reconstruction backend configs.  These are package-owned method-select

### Community 912 - "Community 912"
Cohesion: 1.0
Nodes (1): Return the user-facing reconstruction label.

### Community 913 - "Community 913"
Cohesion: 1.0
Nodes (1): Configure the minimal Open3D TSDF reconstruction backend.      The repo targets

### Community 914 - "Community 914"
Cohesion: 1.0
Nodes (1): Return the concrete reconstruction backend type.

### Community 915 - "Community 915"
Cohesion: 1.0
Nodes (1): Instantiate the Open3D TSDF backend while ignoring unrelated kwargs.

### Community 916 - "Community 916"
Cohesion: 1.0
Nodes (1): Typed contracts for reconstruction adapters.  This module owns the method ids an

### Community 917 - "Community 917"
Cohesion: 1.0
Nodes (1): Name reconstruction backends supported by package-owned configs.

### Community 918 - "Community 918"
Cohesion: 1.0
Nodes (1): Return the user-facing method label.

### Community 919 - "Community 919"
Cohesion: 1.0
Nodes (1): Persist side metadata for one normalized reconstruction output.      PLY geometr

### Community 920 - "Community 920"
Cohesion: 1.0
Nodes (1): Describe normalized durable outputs from one reconstruction run.      The minima

### Community 921 - "Community 921"
Cohesion: 1.0
Nodes (1): Minimal Open3D TSDF reconstruction backend.  This module is the first executable

### Community 922 - "Community 922"
Cohesion: 1.0
Nodes (1): Reconstruct one world-space reference cloud using Open3D TSDF fusion.      The b

### Community 923 - "Community 923"
Cohesion: 1.0
Nodes (1): Integrate one offline RGB-D sequence into a fused world-space cloud.          Th

### Community 924 - "Community 924"
Cohesion: 1.0
Nodes (1): # TODO: this is a shared util helper!

### Community 925 - "Community 925"
Cohesion: 1.0
Nodes (1): # TODO: This is a shared i/o helper that convers our canonical Observation into

### Community 926 - "Community 926"
Cohesion: 1.0
Nodes (1): Package-local execution seams for reconstruction backends.  Reconstruction is th

### Community 927 - "Community 927"
Cohesion: 1.0
Nodes (1): Consume typed RGB-D observations and write normalized artifacts.      Implementa

### Community 928 - "Community 928"
Cohesion: 1.0
Nodes (1): Reconstruct one scene from an offline sequence of RGB-D observations.          A

### Community 929 - "Community 929"
Cohesion: 1.0
Nodes (1): Reconstruction pipeline stage integration.

### Community 930 - "Community 930"
Cohesion: 1.0
Nodes (1): Mark the bounded runtime as stopped.

### Community 931 - "Community 931"
Cohesion: 1.0
Nodes (1): Source package for normalized source preparation.

### Community 932 - "Community 932"
Cohesion: 1.0
Nodes (1): Source-owned contracts for durable manifests and prepared references.  This modu

### Community 933 - "Community 933"
Cohesion: 1.0
Nodes (1): Name the supported Record3D ingress transports across app, CLI, and source confi

### Community 934 - "Community 934"
Cohesion: 1.0
Nodes (1): Return the transport label shown by launch surfaces and logs.

### Community 935 - "Community 935"
Cohesion: 1.0
Nodes (1): Return a compact explanation of how the selected transport behaves.

### Community 936 - "Community 936"
Cohesion: 1.0
Nodes (1): Preserve ADVIO-native pose artifacts discovered during normalization.

### Community 937 - "Community 937"
Cohesion: 1.0
Nodes (1): Carry ADVIO-specific normalized assets without widening the base manifest.

### Community 938 - "Community 938"
Cohesion: 1.0
Nodes (1): Describe the normalized source sequence consumed by downstream stages.

### Community 939 - "Community 939"
Cohesion: 1.0
Nodes (1): Typed source identifier for one prepared reference trajectory.      ``GROUND_TRU

### Community 940 - "Community 940"
Cohesion: 1.0
Nodes (1): Return the human-readable source label.

### Community 941 - "Community 941"
Cohesion: 1.0
Nodes (1): Typed source identifier for one prepared reference cloud.

### Community 942 - "Community 942"
Cohesion: 1.0
Nodes (1): Coordinate status for one prepared reference cloud or trajectory.

### Community 943 - "Community 943"
Cohesion: 1.0
Nodes (1): Reference one prepared trajectory in a source-declared frame.      The file is u

### Community 944 - "Community 944"
Cohesion: 1.0
Nodes (1): Reference one prepared static point cloud for comparison or reconstruction.

### Community 945 - "Community 945"
Cohesion: 1.0
Nodes (1): Collect optional reference inputs prepared alongside a source sequence.      Thi

### Community 946 - "Community 946"
Cohesion: 1.0
Nodes (1): Return the prepared reference trajectory for one requested source.

### Community 947 - "Community 947"
Cohesion: 1.0
Nodes (1): Return the default prepared observation sequence, when one exists.

### Community 948 - "Community 948"
Cohesion: 1.0
Nodes (1): Dataset package entry surface for normalized dataset adapters.  The :mod:`prml_v

### Community 949 - "Community 949"
Cohesion: 1.0
Nodes (1): Public ADVIO dataset surface for app, tests, and pipeline integration.  This pac

### Community 950 - "Community 950"
Cohesion: 1.0
Nodes (1): Return the cache directory used for downloaded scene archives.

### Community 951 - "Community 951"
Cohesion: 1.0
Nodes (1): Return one catalog scene by id.

### Community 952 - "Community 952"
Cohesion: 1.0
Nodes (1): Return local availability status for every catalog scene.

### Community 953 - "Community 953"
Cohesion: 1.0
Nodes (1): Download selected ADVIO scenes and extract complete scene payloads.

### Community 954 - "Community 954"
Cohesion: 1.0
Nodes (1): ADVIO fixedpoint registration helpers.  The official ADVIO visualization registe

### Community 955 - "Community 955"
Cohesion: 1.0
Nodes (1): Rigid registration mode selected for one ADVIO provider trajectory.

### Community 956 - "Community 956"
Cohesion: 1.0
Nodes (1): ADVIO fixpoints converted to repository RDF coordinates.

### Community 957 - "Community 957"
Cohesion: 1.0
Nodes (1): Static transform from one provider RDF world into the fixedpoint frame.

### Community 958 - "Community 958"
Cohesion: 1.0
Nodes (1): Load ADVIO fixpoints with upstream-compatible axis handling.      Upstream visua

### Community 959 - "Community 959"
Cohesion: 1.0
Nodes (1): Estimate a no-scale rigid transform from provider RDF world to fixpoints.

### Community 960 - "Community 960"
Cohesion: 1.0
Nodes (1): Apply one fixedpoint registration to a provider RDF trajectory.

### Community 961 - "Community 961"
Cohesion: 1.0
Nodes (1): Crop registered ADVIO trajectories and express them in one GT local frame.

### Community 962 - "Community 962"
Cohesion: 1.0
Nodes (1): Build a frame-labelled camera pose from a matrix.

### Community 963 - "Community 963"
Cohesion: 1.0
Nodes (1): ADVIO coordinate-basis normalization helpers.  ADVIO replay and benchmark surfac

### Community 964 - "Community 964"
Cohesion: 1.0
Nodes (1): Raw coordinate bases used by official ADVIO provider artifacts.

### Community 965 - "Community 965"
Cohesion: 1.0
Nodes (1): Persist basis conversion details for normalized ADVIO artifacts.

### Community 966 - "Community 966"
Cohesion: 1.0
Nodes (1): Return the raw ADVIO basis used by one provider source.

### Community 967 - "Community 967"
Cohesion: 1.0
Nodes (1): Return the 3x3 raw-to-RDF basis matrix for one ADVIO raw basis.

### Community 968 - "Community 968"
Cohesion: 1.0
Nodes (1): Build side metadata describing one ADVIO raw-to-RDF conversion.

### Community 969 - "Community 969"
Cohesion: 1.0
Nodes (1): Return scalar provenance fields suitable for runtime DTO metadata.

### Community 970 - "Community 970"
Cohesion: 1.0
Nodes (1): Convert one raw ADVIO trajectory into canonical RDF pose matrices.

### Community 971 - "Community 971"
Cohesion: 1.0
Nodes (1): Write a raw ADVIO trajectory as a normalized RDF TUM artifact.

### Community 972 - "Community 972"
Cohesion: 1.0
Nodes (1): ADVIO trajectory interpolation helpers.

### Community 973 - "Community 973"
Cohesion: 1.0
Nodes (1): Interpolate positions and nearest-neighbor rotations at requested timestamps.

### Community 974 - "Community 974"
Cohesion: 1.0
Nodes (1): Load exact iPhone frame timestamps from `frames.csv` as nanoseconds.

### Community 975 - "Community 975"
Cohesion: 1.0
Nodes (1): Load an ADVIO trajectory CSV into an `evo` pose trajectory.

### Community 976 - "Community 976"
Cohesion: 1.0
Nodes (1): Load raw numeric ADVIO trajectory rows with timestamp, XYZ, and WXYZ fields.

### Community 977 - "Community 977"
Cohesion: 1.0
Nodes (1): Parse an official ADVIO calibration YAML into a typed camera model.

### Community 978 - "Community 978"
Cohesion: 1.0
Nodes (1): Convert an ADVIO pose CSV into a TUM trajectory file.

### Community 979 - "Community 979"
Cohesion: 1.0
Nodes (1): ADVIO-specific metadata and config models.  This module owns the committed scene

### Community 980 - "Community 980"
Cohesion: 1.0
Nodes (1): Environment labels committed from the official ADVIO scene table.

### Community 981 - "Community 981"
Cohesion: 1.0
Nodes (1): Return the user-facing environment label.

### Community 982 - "Community 982"
Cohesion: 1.0
Nodes (1): Crowd-density labels committed from the official ADVIO scene table.

### Community 983 - "Community 983"
Cohesion: 1.0
Nodes (1): Return the user-facing crowd-density label.

### Community 984 - "Community 984"
Cohesion: 1.0
Nodes (1): Describe the committed upstream ADVIO metadata sources for the adapter.

### Community 985 - "Community 985"
Cohesion: 1.0
Nodes (1): Describe one ADVIO scene committed into the repository catalog.

### Community 986 - "Community 986"
Cohesion: 1.0
Nodes (1): Return the compact scene label shown in the app and CLI.

### Community 987 - "Community 987"
Cohesion: 1.0
Nodes (1): Bundle the committed ADVIO catalog plus upstream metadata provenance.

### Community 988 - "Community 988"
Cohesion: 1.0
Nodes (1): Explicit ADVIO download selection used by the CLI and Streamlit app.

### Community 989 - "Community 989"
Cohesion: 1.0
Nodes (1): Normalize and validate explicit scene selections.

### Community 990 - "Community 990"
Cohesion: 1.0
Nodes (1): Local availability summary for one ADVIO scene.

### Community 991 - "Community 991"
Cohesion: 1.0
Nodes (1): Configure one local ADVIO sequence owner.      This config is the main click-thr

### Community 992 - "Community 992"
Cohesion: 1.0
Nodes (1): Return the canonical ADVIO folder name used on disk.

### Community 993 - "Community 993"
Cohesion: 1.0
Nodes (1): Reject blank dataset roots before path resolution happens downstream.

### Community 994 - "Community 994"
Cohesion: 1.0
Nodes (1): Return the expected sequence type for the config.

### Community 995 - "Community 995"
Cohesion: 1.0
Nodes (1): Return the CSV backing one ADVIO pose provider.

### Community 996 - "Community 996"
Cohesion: 1.0
Nodes (1): Load one ADVIO trajectory using the requested serving semantics.

### Community 997 - "Community 997"
Cohesion: 1.0
Nodes (1): Apply one ADVIO serving mode to an already loaded trajectory.

### Community 998 - "Community 998"
Cohesion: 1.0
Nodes (1): Return explicit target/source frame labels for served ADVIO camera poses.

### Community 999 - "Community 999"
Cohesion: 1.0
Nodes (1): Build one sequence runtime from its validated config.

### Community 1000 - "Community 1000"
Cohesion: 1.0
Nodes (1): Materialize benchmark-owned reference trajectories for one sequence.

### Community 1001 - "Community 1001"
Cohesion: 1.0
Nodes (1): Persist display-oriented ADVIO replay packets as normalized observations.

### Community 1002 - "Community 1002"
Cohesion: 1.0
Nodes (1): Emit a GT-aligned variant of one optional reference so it overlays GT.      Uses

### Community 1003 - "Community 1003"
Cohesion: 1.0
Nodes (1): Resolve an ``advio-XX`` slug into the numeric ADVIO sequence id.

### Community 1004 - "Community 1004"
Cohesion: 1.0
Nodes (1): Build the raw ADVIO source used only for normalized-store ingestion.

### Community 1005 - "Community 1005"
Cohesion: 1.0
Nodes (1): Build the raw ADVIO streaming source used only for normalized-store ingestion.

### Community 1006 - "Community 1006"
Cohesion: 1.0
Nodes (1): Open the raw ADVIO preview stream for ingestion-only tests.

### Community 1007 - "Community 1007"
Cohesion: 1.0
Nodes (1): TOML contracts for normalized datastore batch builds.

### Community 1008 - "Community 1008"
Cohesion: 1.0
Nodes (1): Grouped ADVIO normalized-store build settings.

### Community 1009 - "Community 1009"
Cohesion: 1.0
Nodes (1): Expand this dataset group into concrete per-sequence source configs.

### Community 1010 - "Community 1010"
Cohesion: 1.0
Nodes (1): Grouped TUM RGB-D normalized-store build settings.

### Community 1011 - "Community 1011"
Cohesion: 1.0
Nodes (1): Expand this dataset group into concrete per-sequence source configs.

### Community 1012 - "Community 1012"
Cohesion: 1.0
Nodes (1): Grouped Record3D normalized-store build settings.

### Community 1013 - "Community 1013"
Cohesion: 1.0
Nodes (1): Expand this dataset group into concrete per-sequence source configs.

### Community 1014 - "Community 1014"
Cohesion: 1.0
Nodes (1): TOML-owned dataset groups for generating normalized datastore entries.

### Community 1015 - "Community 1015"
Cohesion: 1.0
Nodes (1): Expand grouped dataset settings into per-sequence source configs.

### Community 1016 - "Community 1016"
Cohesion: 1.0
Nodes (1): Datasets exposed through evaluation surfaces.

### Community 1017 - "Community 1017"
Cohesion: 1.0
Nodes (1): Return the short user-facing dataset label.

### Community 1018 - "Community 1018"
Cohesion: 1.0
Nodes (1): ADVIO trajectory providers surfaced through replay and pipeline contracts.

### Community 1019 - "Community 1019"
Cohesion: 1.0
Nodes (1): Coordinate-frame semantics for served ADVIO trajectories.

### Community 1020 - "Community 1020"
Cohesion: 1.0
Nodes (1): Typed ADVIO serving semantics shared by request and manifest contracts.

### Community 1021 - "Community 1021"
Cohesion: 1.0
Nodes (1): Source-prepared RGB-D reference-cloud sampling policy.

### Community 1022 - "Community 1022"
Cohesion: 1.0
Nodes (1): Summary of one explicit dataset download action.

### Community 1023 - "Community 1023"
Cohesion: 1.0
Nodes (1): Local availability summary for one dataset scene.

### Community 1024 - "Community 1024"
Cohesion: 1.0
Nodes (1): High-level summary of committed and local dataset coverage.

### Community 1025 - "Community 1025"
Cohesion: 1.0
Nodes (1): Return the effective ADVIO provider for one optional serving config.

### Community 1026 - "Community 1026"
Cohesion: 1.0
Nodes (1): Shared pure helpers for dataset download managers.

### Community 1027 - "Community 1027"
Cohesion: 1.0
Nodes (1): Normalize one archive member path and reject unsafe traversal parts.

### Community 1028 - "Community 1028"
Cohesion: 1.0
Nodes (1): Return the member path relative to one dataset sequence root.

### Community 1029 - "Community 1029"
Cohesion: 1.0
Nodes (1): Thin cache-aware fetch helper for dataset-owned assets.

### Community 1030 - "Community 1030"
Cohesion: 1.0
Nodes (1): Fetch one asset into a stable local path and report whether it was refreshed.

### Community 1031 - "Community 1031"
Cohesion: 1.0
Nodes (1): Read-only normalized datastore projections for app and pipeline surfaces.

### Community 1032 - "Community 1032"
Cohesion: 1.0
Nodes (1): One normalized sequence/profile row projected from the datastore.

### Community 1033 - "Community 1033"
Cohesion: 1.0
Nodes (1): One trajectory artifact available for static normalized-scene plots.

### Community 1034 - "Community 1034"
Cohesion: 1.0
Nodes (1): One reference-cloud artifact available for static normalized-scene plots.

### Community 1035 - "Community 1035"
Cohesion: 1.0
Nodes (1): Tolerant read-only normalized datastore snapshot for one dataset.

### Community 1036 - "Community 1036"
Cohesion: 1.0
Nodes (1): Return one preferred normalized record per sequence for Scene selectors.

### Community 1037 - "Community 1037"
Cohesion: 1.0
Nodes (1): Return all normalized records for one sequence in stable preference order.

### Community 1038 - "Community 1038"
Cohesion: 1.0
Nodes (1): Return the preferred profile key for selected-scene statistics and artifacts.

### Community 1039 - "Community 1039"
Cohesion: 1.0
Nodes (1): Return one dataframe row per usable normalized entry.

### Community 1040 - "Community 1040"
Cohesion: 1.0
Nodes (1): Return the canonical long stats table after UI-selected categorical filters.

### Community 1041 - "Community 1041"
Cohesion: 1.0
Nodes (1): Return compact observation count, duration, and FPS statistics.

### Community 1042 - "Community 1042"
Cohesion: 1.0
Nodes (1): Return compact trajectory motion statistics for reference/candidate rows.

### Community 1043 - "Community 1043"
Cohesion: 1.0
Nodes (1): Return stored RGB/depth/video footprint by normalized entry.

### Community 1044 - "Community 1044"
Cohesion: 1.0
Nodes (1): Return reference-cloud artifact refs for one normalized sequence/profile.

### Community 1045 - "Community 1045"
Cohesion: 1.0
Nodes (1): Return trajectory artifact refs for one normalized sequence/profile.

### Community 1046 - "Community 1046"
Cohesion: 1.0
Nodes (1): Return a tolerant normalized-store snapshot for one dataset.

### Community 1047 - "Community 1047"
Cohesion: 1.0
Nodes (1): Return a boolean mask for ADVIO trajectories to exclude known outliers from stat

### Community 1048 - "Community 1048"
Cohesion: 1.0
Nodes (1): Return a Streamlit cache token for normalized entry and analysis files.

### Community 1049 - "Community 1049"
Cohesion: 1.0
Nodes (1): Resolve an ADVIO slug only if a matching normalized default-profile entry exists

### Community 1050 - "Community 1050"
Cohesion: 1.0
Nodes (1): Return ADVIO pose providers backed by normalized entries for one sequence.

### Community 1051 - "Community 1051"
Cohesion: 1.0
Nodes (1): Persistent normalized dataset entries for offline dataset-backed sources.

### Community 1052 - "Community 1052"
Cohesion: 1.0
Nodes (1): Canonical byte-affecting profile used to key one normalized entry.

### Community 1053 - "Community 1053"
Cohesion: 1.0
Nodes (1): Return the deterministic store key for this profile.

### Community 1054 - "Community 1054"
Cohesion: 1.0
Nodes (1): Read-only diagnostic for a normalized-store entry that is not currently usable.

### Community 1055 - "Community 1055"
Cohesion: 1.0
Nodes (1): Metadata for one complete normalized dataset entry.

### Community 1056 - "Community 1056"
Cohesion: 1.0
Nodes (1): Filesystem store for reusable normalized dataset replay payloads.

### Community 1057 - "Community 1057"
Cohesion: 1.0
Nodes (1): Return the run-local preview scratch root for normalized entries.

### Community 1058 - "Community 1058"
Cohesion: 1.0
Nodes (1): Return the root directory for one profile.

### Community 1059 - "Community 1059"
Cohesion: 1.0
Nodes (1): Load one complete normalized entry.

### Community 1060 - "Community 1060"
Cohesion: 1.0
Nodes (1): Load the exact entry or the only compatible current-schema entry.

### Community 1061 - "Community 1061"
Cohesion: 1.0
Nodes (1): Return whether one complete normalized entry exists.

### Community 1062 - "Community 1062"
Cohesion: 1.0
Nodes (1): Return an actionable missing-entry diagnostic.

### Community 1063 - "Community 1063"
Cohesion: 1.0
Nodes (1): Persist one normalized entry.

### Community 1064 - "Community 1064"
Cohesion: 1.0
Nodes (1): Prepare and persist one normalized entry from a dataset source.

### Community 1065 - "Community 1065"
Cohesion: 1.0
Nodes (1): Load the stored manifest and apply run-local frame selection by index.

### Community 1066 - "Community 1066"
Cohesion: 1.0
Nodes (1): Load benchmark inputs and apply run-local observation selection.

### Community 1067 - "Community 1067"
Cohesion: 1.0
Nodes (1): Open a replay stream backed by stored observation payloads.

### Community 1068 - "Community 1068"
Cohesion: 1.0
Nodes (1): Return entries discovered from authoritative JSON files.

### Community 1069 - "Community 1069"
Cohesion: 1.0
Nodes (1): Return normalized entries that need rebuild or operator attention.

### Community 1070 - "Community 1070"
Cohesion: 1.0
Nodes (1): Build a profile from source settings that change stored bytes.

### Community 1071 - "Community 1071"
Cohesion: 1.0
Nodes (1): Build the normalized store for one dataset under the shared datastore root.

### Community 1072 - "Community 1072"
Cohesion: 1.0
Nodes (1): Return compact row-count metadata for one entry's analysis tables.

### Community 1073 - "Community 1073"
Cohesion: 1.0
Nodes (1): Load persisted long-form statistics as a dataframe.

### Community 1074 - "Community 1074"
Cohesion: 1.0
Nodes (1): Load persisted long-form statistics rows for one normalized entry.

### Community 1075 - "Community 1075"
Cohesion: 1.0
Nodes (1): Load persisted long-form metadata as a dataframe.

### Community 1076 - "Community 1076"
Cohesion: 1.0
Nodes (1): Load persisted long-form metadata rows for one normalized entry.

### Community 1077 - "Community 1077"
Cohesion: 1.0
Nodes (1): Load a metric-depth payload stored as `.npy` or image data.

### Community 1078 - "Community 1078"
Cohesion: 1.0
Nodes (1): Load normalized timestamps from JSON or simple delimited text.

### Community 1079 - "Community 1079"
Cohesion: 1.0
Nodes (1): Source that can materialize both normalized run input and benchmark sidecars.

### Community 1080 - "Community 1080"
Cohesion: 1.0
Nodes (1): Materialize benchmark inputs required for a normalized-store entry.

### Community 1081 - "Community 1081"
Cohesion: 1.0
Nodes (1): Offline Record3D dataset support for local `.r3d` archives.

### Community 1082 - "Community 1082"
Cohesion: 1.0
Nodes (1): Download manager for static Record3D `.r3d` archive scenes.

### Community 1083 - "Community 1083"
Cohesion: 1.0
Nodes (1): Resolve and download Record3D archive scenes into the dataset root.

### Community 1084 - "Community 1084"
Cohesion: 1.0
Nodes (1): Download selected Record3D `.r3d` archives with SHA-256 verification.

### Community 1085 - "Community 1085"
Cohesion: 1.0
Nodes (1): Filesystem layout helpers for local Record3D `.r3d` archives.

### Community 1086 - "Community 1086"
Cohesion: 1.0
Nodes (1): Return the static catalog of downloadable Record3D archives.

### Community 1087 - "Community 1087"
Cohesion: 1.0
Nodes (1): Return the default Zenodo file URL for one Record3D archive.

### Community 1088 - "Community 1088"
Cohesion: 1.0
Nodes (1): Normalize UI and path-ish sequence names into archive stems.

### Community 1089 - "Community 1089"
Cohesion: 1.0
Nodes (1): Return the expected archive path for one sequence id.

### Community 1090 - "Community 1090"
Cohesion: 1.0
Nodes (1): Return the default local materialization cache for one archive.

### Community 1091 - "Community 1091"
Cohesion: 1.0
Nodes (1): Return local `.r3d` archive stems under the dataset root.

### Community 1092 - "Community 1092"
Cohesion: 1.0
Nodes (1): Resolve one sequence id from the static catalog or local disk.

### Community 1093 - "Community 1093"
Cohesion: 1.0
Nodes (1): Return the materialized ARKit TUM trajectory path when it exists.

### Community 1094 - "Community 1094"
Cohesion: 1.0
Nodes (1): Record3D `.r3d` archive parsing and materialization helpers.

### Community 1095 - "Community 1095"
Cohesion: 1.0
Nodes (1): One RGB-D frame triplet inside a `.r3d` archive.

### Community 1096 - "Community 1096"
Cohesion: 1.0
Nodes (1): Validated subset of Record3D metadata used by the adapter.

### Community 1097 - "Community 1097"
Cohesion: 1.0
Nodes (1): Decoded archive-level metadata for one Record3D sequence.

### Community 1098 - "Community 1098"
Cohesion: 1.0
Nodes (1): Read and validate the Record3D archive metadata JSON.

### Community 1099 - "Community 1099"
Cohesion: 1.0
Nodes (1): Return ordered RGB-D frame triplets from an `.r3d` archive.

### Community 1100 - "Community 1100"
Cohesion: 1.0
Nodes (1): Parse the Record3D column-major K matrix for the RGB raster.

### Community 1101 - "Community 1101"
Cohesion: 1.0
Nodes (1): Scale RGB intrinsics into the depth raster used by `.depth` payloads.

### Community 1102 - "Community 1102"
Cohesion: 1.0
Nodes (1): Convert Record3D floating second timestamps into nanoseconds.

### Community 1103 - "Community 1103"
Cohesion: 1.0
Nodes (1): Convert Record3D pose rows into frame-labelled transforms.

### Community 1104 - "Community 1104"
Cohesion: 1.0
Nodes (1): Convert one `[qx, qy, qz, qw, tx, ty, tz]` metadata pose row.

### Community 1105 - "Community 1105"
Cohesion: 1.0
Nodes (1): Decode one RGB frame from an archive into RGB channel order.

### Community 1106 - "Community 1106"
Cohesion: 1.0
Nodes (1): Decode one LZFSE-compressed depth payload into meters.

### Community 1107 - "Community 1107"
Cohesion: 1.0
Nodes (1): Decode one LZFSE-compressed confidence payload.

### Community 1108 - "Community 1108"
Cohesion: 1.0
Nodes (1): Write normalized timestamp JSON for materialized RGB frames.

### Community 1109 - "Community 1109"
Cohesion: 1.0
Nodes (1): Resize an RGB frame into the depth raster dimensions.

### Community 1110 - "Community 1110"
Cohesion: 1.0
Nodes (1): Typed models for offline Record3D dataset archives.

### Community 1111 - "Community 1111"
Cohesion: 1.0
Nodes (1): Pose-frame conversion policy for Record3D metadata poses.

### Community 1112 - "Community 1112"
Cohesion: 1.0
Nodes (1): Policy for deriving metric artifacts from one Record3D archive.

### Community 1113 - "Community 1113"
Cohesion: 1.0
Nodes (1): Configure one local `.r3d` archive sequence.

### Community 1114 - "Community 1114"
Cohesion: 1.0
Nodes (1): Local metadata for one Record3D archive.

### Community 1115 - "Community 1115"
Cohesion: 1.0
Nodes (1): Small catalog wrapper used by the shared dataset service base.

### Community 1116 - "Community 1116"
Cohesion: 1.0
Nodes (1): Explicit Record3D archive download selection used by the CLI.

### Community 1117 - "Community 1117"
Cohesion: 1.0
Nodes (1): Normalize explicit scene selections and reject negative indices.

### Community 1118 - "Community 1118"
Cohesion: 1.0
Nodes (1): Record3D `.r3d` sequence owner.

### Community 1119 - "Community 1119"
Cohesion: 1.0
Nodes (1): Resolved local paths for one Record3D sequence.

### Community 1120 - "Community 1120"
Cohesion: 1.0
Nodes (1): Load and materialize one local Record3D `.r3d` archive.

### Community 1121 - "Community 1121"
Cohesion: 1.0
Nodes (1): Dataset lookup helpers kept outside dataset identifier contracts.

### Community 1122 - "Community 1122"
Cohesion: 1.0
Nodes (1): Return local sequence slugs available for one dataset family.

### Community 1123 - "Community 1123"
Cohesion: 1.0
Nodes (1): Return the canonical default reference trajectory for one dataset sequence.

### Community 1124 - "Community 1124"
Cohesion: 1.0
Nodes (1): Shared normalized-store RGB raster preprocessing.

### Community 1125 - "Community 1125"
Cohesion: 1.0
Nodes (1): Downscale one RGB raster into the canonical normalized-store cache size.

### Community 1126 - "Community 1126"
Cohesion: 1.0
Nodes (1): Resize a depth raster to the preprocessed RGB shape without changing depth units

### Community 1127 - "Community 1127"
Cohesion: 1.0
Nodes (1): Scale camera intrinsics into the preprocessed normalized-store raster.

### Community 1128 - "Community 1128"
Cohesion: 1.0
Nodes (1): Write a normalized-store RGB PNG with high compression.

### Community 1129 - "Community 1129"
Cohesion: 1.0
Nodes (1): Public TUM RGB-D dataset surface for app, tests, and pipeline integration.  This

### Community 1130 - "Community 1130"
Cohesion: 1.0
Nodes (1): Download selected TUM RGB-D scenes and extract complete scene payloads.

### Community 1131 - "Community 1131"
Cohesion: 1.0
Nodes (1): Path bundle contract needed by loaded TUM RGB-D offline samples.

### Community 1132 - "Community 1132"
Cohesion: 1.0
Nodes (1): Load raw TUM RGB-D ground truth with deterministic timestamp canonicalization.

### Community 1133 - "Community 1133"
Cohesion: 1.0
Nodes (1): Load TUM ground truth relativized to the first pose (first-camera RDF frame).

### Community 1134 - "Community 1134"
Cohesion: 1.0
Nodes (1): Write ``ground_truth.tum`` relativized to the first pose (first-camera RDF frame

### Community 1135 - "Community 1135"
Cohesion: 1.0
Nodes (1): TUM RGB-D-specific metadata and config models.  This module owns the committed s

### Community 1136 - "Community 1136"
Cohesion: 1.0
Nodes (1): Name the pose providers supported by the TUM RGB-D adapter.

### Community 1137 - "Community 1137"
Cohesion: 1.0
Nodes (1): Return the user-facing pose-source label.

### Community 1138 - "Community 1138"
Cohesion: 1.0
Nodes (1): Describe one TUM RGB-D scene committed into the repository catalog.

### Community 1139 - "Community 1139"
Cohesion: 1.0
Nodes (1): Bundle the committed TUM RGB-D catalog and upstream metadata pointers.

### Community 1140 - "Community 1140"
Cohesion: 1.0
Nodes (1): Describe one explicit TUM RGB-D download selection.

### Community 1141 - "Community 1141"
Cohesion: 1.0
Nodes (1): Configure one local TUM RGB-D sequence owner.

### Community 1142 - "Community 1142"
Cohesion: 1.0
Nodes (1): Open one TUM RGB-D sequence through the shared image-sequence replay stack.

### Community 1143 - "Community 1143"
Cohesion: 1.0
Nodes (1): Write a durable observation index for reconstruction, if depth exists.

### Community 1144 - "Community 1144"
Cohesion: 1.0
Nodes (1): Fuse method-input RGB-D observations into the aligned TUM RGB-D reference cloud.

### Community 1145 - "Community 1145"
Cohesion: 1.0
Nodes (1): Return preview timestamps derived from the RGB association rows.

### Community 1146 - "Community 1146"
Cohesion: 1.0
Nodes (1): Source-owned manifest materialization helpers.

### Community 1147 - "Community 1147"
Cohesion: 1.0
Nodes (1): Adapt a raw video path into the normalized offline source seam.

### Community 1148 - "Community 1148"
Cohesion: 1.0
Nodes (1): Return the compact user-facing label for this source.

### Community 1149 - "Community 1149"
Cohesion: 1.0
Nodes (1): Resolve the video path and return the minimal normalized manifest.

### Community 1150 - "Community 1150"
Cohesion: 1.0
Nodes (1): Materialize the run-owned source manifest for this source stage.

### Community 1151 - "Community 1151"
Cohesion: 1.0
Nodes (1): Source-owned readers for normalized offline observations.

### Community 1152 - "Community 1152"
Cohesion: 1.0
Nodes (1): Yield RGB observations from a normalized source sequence manifest.

### Community 1153 - "Community 1153"
Cohesion: 1.0
Nodes (1): Source-owned file-backed observation sequence loading.  The source reads durable

### Community 1154 - "Community 1154"
Cohesion: 1.0
Nodes (1): Open a durable observation sequence index from local files.      The source vali

### Community 1155 - "Community 1155"
Cohesion: 1.0
Nodes (1): Return the compact source label used in logs and diagnostics.

### Community 1156 - "Community 1156"
Cohesion: 1.0
Nodes (1): Yield observations by resolving payload paths from the sequence ref.          RG

### Community 1157 - "Community 1157"
Cohesion: 1.0
Nodes (1): Load and validate one durable observation sequence index.      The JSON payload

### Community 1158 - "Community 1158"
Cohesion: 1.0
Nodes (1): Materialize the normalized offline input boundary for one run.      Implementati

### Community 1159 - "Community 1159"
Cohesion: 1.0
Nodes (1): Return the user-facing label for the prepared sequence.

### Community 1160 - "Community 1160"
Cohesion: 1.0
Nodes (1): Materialize or resolve the normalized :class:`SequenceManifest` for one run.

### Community 1161 - "Community 1161"
Cohesion: 1.0
Nodes (1): Optionally materialize prepared benchmark-side reference inputs.

### Community 1162 - "Community 1162"
Cohesion: 1.0
Nodes (1): Materialize prepared benchmark inputs that complement the offline sequence.

### Community 1163 - "Community 1163"
Cohesion: 1.0
Nodes (1): Extend :class:`OfflineSequenceSource` with a live or replay packet stream.

### Community 1164 - "Community 1164"
Cohesion: 1.0
Nodes (1): Open the frame stream that feeds the active SLAM session.

### Community 1165 - "Community 1165"
Cohesion: 1.0
Nodes (1): Record3D source adapters and transport helpers.

### Community 1166 - "Community 1166"
Cohesion: 1.0
Nodes (1): Record3D USB streaming integration for shared source observations.  This module

### Community 1167 - "Community 1167"
Cohesion: 1.0
Nodes (1): Name the device classes exposed by the upstream Record3D bindings.

### Community 1168 - "Community 1168"
Cohesion: 1.0
Nodes (1): Describe one USB-connected Record3D device discovered through the bindings.

### Community 1169 - "Community 1169"
Cohesion: 1.0
Nodes (1): Import the optional native Record3D bindings.

### Community 1170 - "Community 1170"
Cohesion: 1.0
Nodes (1): Configure one USB Record3D packet stream.

### Community 1171 - "Community 1171"
Cohesion: 1.0
Nodes (1): Runtime type that exposes shared packet objects.

### Community 1172 - "Community 1172"
Cohesion: 1.0
Nodes (1): Adapt the upstream USB stream to the shared packet-stream contract.

### Community 1173 - "Community 1173"
Cohesion: 1.0
Nodes (1): List the currently connected USB Record3D devices.

### Community 1174 - "Community 1174"
Cohesion: 1.0
Nodes (1): Connect to the configured USB device and return its normalized device metadata.

### Community 1175 - "Community 1175"
Cohesion: 1.0
Nodes (1): Disconnect the current USB device if one is active.

### Community 1176 - "Community 1176"
Cohesion: 1.0
Nodes (1): Wait for the next shared observation emitted by the USB device.

### Community 1177 - "Community 1177"
Cohesion: 1.0
Nodes (1): Yield shared observations indefinitely until the caller stops consuming them.

### Community 1178 - "Community 1178"
Cohesion: 1.0
Nodes (1): List currently connected USB devices through the canonical Record3D IO owner.

### Community 1179 - "Community 1179"
Cohesion: 1.0
Nodes (1): Build one validated USB packet stream ready for the shared runtime seam.

### Community 1180 - "Community 1180"
Cohesion: 1.0
Nodes (1): Build the compact frame-details payload shown by Record3D consumers.

### Community 1181 - "Community 1181"
Cohesion: 1.0
Nodes (1): Record3D-backed streaming-source wrapper for pipeline-owned sessions.  This modu

### Community 1182 - "Community 1182"
Cohesion: 1.0
Nodes (1): Configure one Record3D-backed streaming source adapter.

### Community 1183 - "Community 1183"
Cohesion: 1.0
Nodes (1): Runtime type that exposes the shared streaming-source contract.

### Community 1184 - "Community 1184"
Cohesion: 1.0
Nodes (1): Expose Record3D live capture through the shared streaming-source seam.

### Community 1185 - "Community 1185"
Cohesion: 1.0
Nodes (1): Return the user-facing label for the configured live Record3D source adapter.

### Community 1186 - "Community 1186"
Cohesion: 1.0
Nodes (1): Return the minimal normalized live-sequence manifest for Record3D.

### Community 1187 - "Community 1187"
Cohesion: 1.0
Nodes (1): Open the configured Record3D packet stream for pipeline consumption.

### Community 1188 - "Community 1188"
Cohesion: 1.0
Nodes (1): Metadata parsing and packet decoding for Record3D Wi-Fi streaming.

### Community 1189 - "Community 1189"
Cohesion: 1.0
Nodes (1): Typed metadata returned by the Record3D Wi-Fi HTTP API.

### Community 1190 - "Community 1190"
Cohesion: 1.0
Nodes (1): Parse the raw Record3D metadata payload.

### Community 1191 - "Community 1191"
Cohesion: 1.0
Nodes (1): Decode the HSV-encoded Record3D Wi-Fi depth half into a depth map.

### Community 1192 - "Community 1192"
Cohesion: 1.0
Nodes (1): Convert one Record3D composite WebRTC frame into the shared source contract.

### Community 1193 - "Community 1193"
Cohesion: 1.0
Nodes (1): Async Record3D Wi-Fi preview receiver runtime.

### Community 1194 - "Community 1194"
Cohesion: 1.0
Nodes (1): Import the optional Python WebRTC dependencies used by Wi-Fi capture.

### Community 1195 - "Community 1195"
Cohesion: 1.0
Nodes (1): Async receiver runtime used by the Record3D Wi-Fi session wrapper.

### Community 1196 - "Community 1196"
Cohesion: 1.0
Nodes (1): Return whether an async exception is expected during aiortc teardown.

### Community 1197 - "Community 1197"
Cohesion: 1.0
Nodes (1): Preview-only Record3D Wi-Fi session wrapper.  This module owns the Python-side W

### Community 1198 - "Community 1198"
Cohesion: 1.0
Nodes (1): Configure the optional Python-side Record3D Wi-Fi preview receiver.

### Community 1199 - "Community 1199"
Cohesion: 1.0
Nodes (1): Return the runtime session type constructed from this config.

### Community 1200 - "Community 1200"
Cohesion: 1.0
Nodes (1): Manage one Python-side Record3D Wi-Fi preview session.      The lifecycle matche

### Community 1201 - "Community 1201"
Cohesion: 1.0
Nodes (1): Establish signaling, start the worker, and wait for the preview stream to become

### Community 1202 - "Community 1202"
Cohesion: 1.0
Nodes (1): Request shutdown and join the background worker when possible.

### Community 1203 - "Community 1203"
Cohesion: 1.0
Nodes (1): Block until the next normalized preview packet is available.

### Community 1204 - "Community 1204"
Cohesion: 1.0
Nodes (1): HTTP signaling helpers for Record3D Wi-Fi preview streaming.

### Community 1205 - "Community 1205"
Cohesion: 1.0
Nodes (1): Normalize a Record3D device address into an explicit HTTP URL.

### Community 1206 - "Community 1206"
Cohesion: 1.0
Nodes (1): Build the JSON answer payload expected by Record3D's signaling API.

### Community 1207 - "Community 1207"
Cohesion: 1.0
Nodes (1): Small synchronous client for the Record3D Wi-Fi signaling endpoints.

### Community 1208 - "Community 1208"
Cohesion: 1.0
Nodes (1): Fetch the device's WebRTC offer from `/getOffer`.

### Community 1209 - "Community 1209"
Cohesion: 1.0
Nodes (1): Fetch the device metadata from `/metadata`.

### Community 1210 - "Community 1210"
Cohesion: 1.0
Nodes (1): Post the local WebRTC answer back to the Record3D device.

### Community 1211 - "Community 1211"
Cohesion: 1.0
Nodes (1): Shared replay primitives for source-owned observation streams.

### Community 1212 - "Community 1212"
Cohesion: 1.0
Nodes (1): Replay clock used by dataset and video source streams.

### Community 1213 - "Community 1213"
Cohesion: 1.0
Nodes (1): Select whether replay follows source timing or returns observations immediately.

### Community 1214 - "Community 1214"
Cohesion: 1.0
Nodes (1): Apply source-timestamp pacing for real-time replay.

### Community 1215 - "Community 1215"
Cohesion: 1.0
Nodes (1): Reset the clock baseline for a new replay loop or connection.

### Community 1216 - "Community 1216"
Cohesion: 1.0
Nodes (1): Sleep until the replay timestamp should be emitted.

### Community 1217 - "Community 1217"
Cohesion: 1.0
Nodes (1): Timestamped image-sequence replay source.

### Community 1218 - "Community 1218"
Cohesion: 1.0
Nodes (1): Replay pre-indexed timestamped image frames as a live observation stream.      T

### Community 1219 - "Community 1219"
Cohesion: 1.0
Nodes (1): Initialize the sequence playback state.          Args:             sequence_dir:

### Community 1220 - "Community 1220"
Cohesion: 1.0
Nodes (1): Validate the sequence directory and prepare the replay clock.          This meth

### Community 1221 - "Community 1221"
Cohesion: 1.0
Nodes (1): Release sequence resources and halt playback.          For this source, this is

### Community 1222 - "Community 1222"
Cohesion: 1.0
Nodes (1): Load and return the next sampled observation aligned to the replay clock.

### Community 1223 - "Community 1223"
Cohesion: 1.0
Nodes (1): Source replay behavior seams.

### Community 1224 - "Community 1224"
Cohesion: 1.0
Nodes (1): Blockingly deliver shared :class:`Observation` values.

### Community 1225 - "Community 1225"
Cohesion: 1.0
Nodes (1): Connect to the source and prepare subsequent blocking observation reads.

### Community 1226 - "Community 1226"
Cohesion: 1.0
Nodes (1): Disconnect or release the source and any owned runtime resources.

### Community 1227 - "Community 1227"
Cohesion: 1.0
Nodes (1): Wait for and return the next normalized source observation.

### Community 1228 - "Community 1228"
Cohesion: 1.0
Nodes (1): PyAV-backed video replay source.

### Community 1229 - "Community 1229"
Cohesion: 1.0
Nodes (1): Stream a local video iteratively as if it were a live camera source.      This s

### Community 1230 - "Community 1230"
Cohesion: 1.0
Nodes (1): Initialize the video playback state.          Args:             video_path: The

### Community 1231 - "Community 1231"
Cohesion: 1.0
Nodes (1): Open the configured video and prepare playback state.          This method initi

### Community 1232 - "Community 1232"
Cohesion: 1.0
Nodes (1): Release sequence resources and halt PyAV container playback.          This metho

### Community 1233 - "Community 1233"
Cohesion: 1.0
Nodes (1): Decode and return the next sampled RGB observation seamlessly.          This met

### Community 1234 - "Community 1234"
Cohesion: 1.0
Nodes (1): Encode RGB frames into a compact normalized video payload.

### Community 1235 - "Community 1235"
Cohesion: 1.0
Nodes (1): Yield RGB frames from a video, optionally filtering by zero-based frame index.

### Community 1236 - "Community 1236"
Cohesion: 1.0
Nodes (1): Read display rotation metadata from a video file.      Extracts the angle encode

### Community 1237 - "Community 1237"
Cohesion: 1.0
Nodes (1): Source pipeline stage integration.

### Community 1238 - "Community 1238"
Cohesion: 1.0
Nodes (1): Source-stage artifact key and projection helpers.

### Community 1239 - "Community 1239"
Cohesion: 1.0
Nodes (1): Persisted source-stage config and source backend muxing.

### Community 1240 - "Community 1240"
Cohesion: 1.0
Nodes (1): Target source-stage policy plus source backend selection.

### Community 1241 - "Community 1241"
Cohesion: 1.0
Nodes (1): Return source-owned normalized input artifacts.

### Community 1242 - "Community 1242"
Cohesion: 1.0
Nodes (1): Source-stage runtime input and output contracts.

### Community 1243 - "Community 1243"
Cohesion: 1.0
Nodes (1): Run-scoped input required to prepare one normalized source stage.

### Community 1244 - "Community 1244"
Cohesion: 1.0
Nodes (1): Bundle the normalized source result for downstream stages.

### Community 1245 - "Community 1245"
Cohesion: 1.0
Nodes (1): Source-stage runtime for normalized sequence preparation.

### Community 1246 - "Community 1246"
Cohesion: 1.0
Nodes (1): Prepare the normalized source output for offline or streaming runs.

### Community 1247 - "Community 1247"
Cohesion: 1.0
Nodes (1): Return the latest source-runtime status.

### Community 1248 - "Community 1248"
Cohesion: 1.0
Nodes (1): Mark the source runtime as stopped.

### Community 1249 - "Community 1249"
Cohesion: 1.0
Nodes (1): Prepare and persist the canonical source-stage output.

### Community 1250 - "Community 1250"
Cohesion: 1.0
Nodes (1): Runtime spec for the source stage.

### Community 1251 - "Community 1251"
Cohesion: 1.0
Nodes (1): Source-stage visualization adapter.  The source stage owns dataset/reference sem

### Community 1252 - "Community 1252"
Cohesion: 1.0
Nodes (1): Source-owned wrappers for stream sampling policy.

### Community 1253 - "Community 1253"
Cohesion: 1.0
Nodes (1): Apply source sampling policy to an existing observation stream.

### Community 1254 - "Community 1254"
Cohesion: 1.0
Nodes (1): Connect the wrapped stream.

### Community 1255 - "Community 1255"
Cohesion: 1.0
Nodes (1): Disconnect the wrapped stream.

### Community 1256 - "Community 1256"
Cohesion: 1.0
Nodes (1): Return the next observation accepted by the configured sampling policy.

### Community 1257 - "Community 1257"
Cohesion: 1.0
Nodes (1): Apply source sampling policy to an existing streaming source.

### Community 1258 - "Community 1258"
Cohesion: 1.0
Nodes (1): Return the wrapped source label.

### Community 1259 - "Community 1259"
Cohesion: 1.0
Nodes (1): Delegate manifest preparation to the wrapped source.

### Community 1260 - "Community 1260"
Cohesion: 1.0
Nodes (1): Delegate benchmark preparation when the wrapped source supports it.

### Community 1261 - "Community 1261"
Cohesion: 1.0
Nodes (1): Open the wrapped source stream with sampling applied.

### Community 1262 - "Community 1262"
Cohesion: 1.0
Nodes (1): Shared utility surfaces for the project.

### Community 1263 - "Community 1263"
Cohesion: 1.0
Nodes (1): Shared config and config-as-factory helpers for the repository.  This module own

### Community 1264 - "Community 1264"
Cohesion: 1.0
Nodes (1): Augment :class:`BaseData` with deterministic TOML IO and config inspection.

### Community 1265 - "Community 1265"
Cohesion: 1.0
Nodes (1): Return a JSON-serializable view suitable for UI payloads and debugging.

### Community 1266 - "Community 1266"
Cohesion: 1.0
Nodes (1): Normalize nested config values into JSON-friendly primitives.

### Community 1267 - "Community 1267"
Cohesion: 1.0
Nodes (1): Serialize the config to deterministic TOML and optionally persist it.

### Community 1268 - "Community 1268"
Cohesion: 1.0
Nodes (1): Persist the config to TOML and return the resulting file path.

### Community 1269 - "Community 1269"
Cohesion: 1.0
Nodes (1): Load the validated config from TOML text, bytes, or a file path.

### Community 1270 - "Community 1270"
Cohesion: 1.0
Nodes (1): Render the config as a Rich tree for quick human inspection.

### Community 1271 - "Community 1271"
Cohesion: 1.0
Nodes (1): Mixin for configs that construct one runtime owner or adapter.      This pattern

### Community 1272 - "Community 1272"
Cohesion: 1.0
Nodes (1): Return the runtime type or owner constructed by :meth:`setup_target`.

### Community 1273 - "Community 1273"
Cohesion: 1.0
Nodes (1): Instantiate or build the runtime object described by this config.

### Community 1274 - "Community 1274"
Cohesion: 1.0
Nodes (1): Shared validated payload base class for repo-owned DTOs.  This module provides :

### Community 1275 - "Community 1275"
Cohesion: 1.0
Nodes (1): Provide a consistent base for typed repo-owned data containers.      Use :class:

### Community 1276 - "Community 1276"
Cohesion: 1.0
Nodes (1): Return a pickle-ready Python payload for lightweight IPC transport.

### Community 1277 - "Community 1277"
Cohesion: 1.0
Nodes (1): Serialize this model into IPC bytes without widening its public JSON shape.

### Community 1278 - "Community 1278"
Cohesion: 1.0
Nodes (1): Deserialize one IPC payload back into the target validated model type.

### Community 1279 - "Community 1279"
Cohesion: 1.0
Nodes (1): Logging-backed Rich console helpers for the PRML VSLAM project.

### Community 1280 - "Community 1280"
Cohesion: 1.0
Nodes (1): Return a dotted namespace for the caller.      The namespace is derived from the

### Community 1281 - "Community 1281"
Cohesion: 1.0
Nodes (1): Small wrapper that unifies Rich output and standard logging.

### Community 1282 - "Community 1282"
Cohesion: 1.0
Nodes (1): Attach a Rich logging handler to the ``prml_vslam`` logger tree.

### Community 1283 - "Community 1283"
Cohesion: 1.0
Nodes (1): Create a console using the caller's module and qualified function name.

### Community 1284 - "Community 1284"
Cohesion: 1.0
Nodes (1): Return a child console with additional namespace parts.

### Community 1285 - "Community 1285"
Cohesion: 1.0
Nodes (1): Render directly via Rich for structured or non-log output.

### Community 1286 - "Community 1286"
Cohesion: 1.0
Nodes (1): Pretty-print a Python object with Rich.

### Community 1287 - "Community 1287"
Cohesion: 1.0
Nodes (1): Log an informational message.

### Community 1288 - "Community 1288"
Cohesion: 1.0
Nodes (1): Log a warning message.

### Community 1289 - "Community 1289"
Cohesion: 1.0
Nodes (1): Backward-compatible warning alias.

### Community 1290 - "Community 1290"
Cohesion: 1.0
Nodes (1): Log an error message.

### Community 1291 - "Community 1291"
Cohesion: 1.0
Nodes (1): Log an exception with traceback information.

### Community 1292 - "Community 1292"
Cohesion: 1.0
Nodes (1): Set the level on the bound logger.

### Community 1293 - "Community 1293"
Cohesion: 1.0
Nodes (1): Convenience helper for a callsite-aware console instance.

### Community 1294 - "Community 1294"
Cohesion: 1.0
Nodes (1): Formatter that keeps the logger tree rooted at ``prml_vslam`` but shortens displ

### Community 1295 - "Community 1295"
Cohesion: 1.0
Nodes (1): Highlight log payload reprs while preserving the namespace prefix style.

### Community 1296 - "Community 1296"
Cohesion: 1.0
Nodes (1): Shared geometry helpers used across repository-owned interfaces.

### Community 1297 - "Community 1297"
Cohesion: 1.0
Nodes (1): Write a TUM trajectory file from canonical camera-to-world transforms and timest

### Community 1298 - "Community 1298"
Cohesion: 1.0
Nodes (1): Load a TUM trajectory file into an `evo` pose trajectory.

### Community 1299 - "Community 1299"
Cohesion: 1.0
Nodes (1): Express every pose relative to the first pose.

### Community 1300 - "Community 1300"
Cohesion: 1.0
Nodes (1): Write an XYZ point cloud to PLY using the repository's Open3D dependency.

### Community 1301 - "Community 1301"
Cohesion: 1.0
Nodes (1): Load an XYZ point cloud from PLY using the repository's Open3D dependency.

### Community 1302 - "Community 1302"
Cohesion: 1.0
Nodes (1): Load XYZ points and optional RGB colors from PLY using Open3D.

### Community 1303 - "Community 1303"
Cohesion: 1.0
Nodes (1): Transform camera-frame XYZ points into world coordinates.

### Community 1304 - "Community 1304"
Cohesion: 1.0
Nodes (1): Unproject sampled depth into world-frame XYZ points and optional RGB.      This

### Community 1305 - "Community 1305"
Cohesion: 1.0
Nodes (1): Deterministically cap a fused point cloud without changing frame selection.

### Community 1306 - "Community 1306"
Cohesion: 1.0
Nodes (1): Unproject a depth raster into a sampled camera-frame pointmap.

### Community 1307 - "Community 1307"
Cohesion: 1.0
Nodes (1): Gravity-locked similarity mapping ``estimate`` onto ``reference``.      Solves `

### Community 1308 - "Community 1308"
Cohesion: 1.0
Nodes (1): Return a copy of ``trajectory`` transformed by ``p -> s R p + t``.      Rotation

### Community 1309 - "Community 1309"
Cohesion: 1.0
Nodes (1): Shared image normalization helpers.

### Community 1310 - "Community 1310"
Cohesion: 1.0
Nodes (1): Scale a grayscale image into an 8-bit displayable range.

### Community 1311 - "Community 1311"
Cohesion: 1.0
Nodes (1): Shared recursive JSON type aliases.

### Community 1312 - "Community 1312"
Cohesion: 1.0
Nodes (1): Centralized repository-owned path semantics.  This module owns the canonical fil

### Community 1313 - "Community 1313"
Cohesion: 1.0
Nodes (1): Describe the canonical artifact layout for one planned run.      The pipeline pl

### Community 1314 - "Community 1314"
Cohesion: 1.0
Nodes (1): Build the canonical artifact layout from an explicit root.          The returned

### Community 1315 - "Community 1315"
Cohesion: 1.0
Nodes (1): Return the canonical Plotly scene path for one method run.

### Community 1316 - "Community 1316"
Cohesion: 1.0
Nodes (1): Alias for input_frames_dir used in early scaffold versions.

### Community 1317 - "Community 1317"
Cohesion: 1.0
Nodes (1): Return the path to the repo-owned viewer recording.

### Community 1318 - "Community 1318"
Cohesion: 1.0
Nodes (1): Return the canonical path to one stage manifest.

### Community 1319 - "Community 1319"
Cohesion: 1.0
Nodes (1): Centralize all repository-owned path semantics and directory defaults.      Inje

### Community 1320 - "Community 1320"
Cohesion: 1.0
Nodes (1): Validate that the configured repository root exists.

### Community 1321 - "Community 1321"
Cohesion: 1.0
Nodes (1): Resolve configured directories against the repository root.

### Community 1322 - "Community 1322"
Cohesion: 1.0
Nodes (1): Resolve a path relative to the configured repository root.

### Community 1323 - "Community 1323"
Cohesion: 1.0
Nodes (1): Resolve a directory and optionally create it.

### Community 1324 - "Community 1324"
Cohesion: 1.0
Nodes (1): Resolve a path relative to the repository root or an explicit base directory.

### Community 1325 - "Community 1325"
Cohesion: 1.0
Nodes (1): Resolve a video path, defaulting bare filenames into the captures directory.

### Community 1326 - "Community 1326"
Cohesion: 1.0
Nodes (1): Resolve an output directory, defaulting to the configured artifacts root.

### Community 1327 - "Community 1327"
Cohesion: 1.0
Nodes (1): Resolve the repo-owned dataset root directory.

### Community 1328 - "Community 1328"
Cohesion: 1.0
Nodes (1): Resolve one dataset directory under the shared data root.

### Community 1329 - "Community 1329"
Cohesion: 1.0
Nodes (1): Resolve one normalized datastore directory under the shared data root.

### Community 1330 - "Community 1330"
Cohesion: 1.0
Nodes (1): Resolve the shared runtime logs directory.

### Community 1331 - "Community 1331"
Cohesion: 1.0
Nodes (1): Resolve the durable command-log directory for one pipeline run.

### Community 1332 - "Community 1332"
Cohesion: 1.0
Nodes (1): Resolve the shared repo-owned config directory.

### Community 1333 - "Community 1333"
Cohesion: 1.0
Nodes (1): Resolve the shared pipeline config directory under the repo config root.

### Community 1334 - "Community 1334"
Cohesion: 1.0
Nodes (1): Resolve one upstream method checkout path under the shared logs directory.

### Community 1335 - "Community 1335"
Cohesion: 1.0
Nodes (1): Resolve one dedicated virtual environment path for an external backend.

### Community 1336 - "Community 1336"
Cohesion: 1.0
Nodes (1): Resolve one shared checkpoint directory for an external backend.

### Community 1337 - "Community 1337"
Cohesion: 1.0
Nodes (1): Resolve a TOML file path relative to the repository root.          Use this for

### Community 1338 - "Community 1338"
Cohesion: 1.0
Nodes (1): Resolve a pipeline config TOML path.          Bare filenames are placed under `.

### Community 1339 - "Community 1339"
Cohesion: 1.0
Nodes (1): Convert a human-readable experiment name into a filesystem-safe slug.

### Community 1340 - "Community 1340"
Cohesion: 1.0
Nodes (1): Build the canonical artifact layout used by the pipeline for one run.          T

### Community 1341 - "Community 1341"
Cohesion: 1.0
Nodes (1): Return the cached default :class:`PathConfig` for the current process.

### Community 1342 - "Community 1342"
Cohesion: 1.0
Nodes (1): Shared deterministic JSON and hashing helpers.

### Community 1343 - "Community 1343"
Cohesion: 1.0
Nodes (1): Compute a stable SHA-256 fingerprint for JSON-normalizable payloads.

### Community 1344 - "Community 1344"
Cohesion: 1.0
Nodes (1): Return a SHA-256 digest for a file or directory tree.

### Community 1345 - "Community 1345"
Cohesion: 1.0
Nodes (1): Persist one JSON artifact with deterministic formatting.

### Community 1346 - "Community 1346"
Cohesion: 1.0
Nodes (1): Small shared telemetry math helpers.

### Community 1347 - "Community 1347"
Cohesion: 1.0
Nodes (1): Compute a rolling frames-per-second estimate.

### Community 1348 - "Community 1348"
Cohesion: 1.0
Nodes (1): Shared video-frame materialization helpers.

### Community 1349 - "Community 1349"
Cohesion: 1.0
Nodes (1): Materialized RGB frames plus their derived timestamps.

### Community 1350 - "Community 1350"
Cohesion: 1.0
Nodes (1): Extract PNG frames from one video with deterministic timestamps.

### Community 1351 - "Community 1351"
Cohesion: 1.0
Nodes (1): Visualization package for repo-owned contracts, helpers, and validation.

### Community 1352 - "Community 1352"
Cohesion: 1.0
Nodes (1): Thin visualization-policy contracts.  Visualization policy controls viewer attac

### Community 1353 - "Community 1353"
Cohesion: 1.0
Nodes (1): Viewer-export policy attached to one run request or target run config.      The

### Community 1354 - "Community 1354"
Cohesion: 1.0
Nodes (1): Offline Rerun artifact post-processing for tracked 3D camera playback.  The repo

### Community 1355 - "Community 1355"
Cohesion: 1.0
Nodes (1): Paths produced by one offline follow-artifact build.

### Community 1356 - "Community 1356"
Cohesion: 1.0
Nodes (1): Return the default follow-enabled artifact path for an existing recording.

### Community 1357 - "Community 1357"
Cohesion: 1.0
Nodes (1): Create an offline Rerun recording whose 3D view follows the tracked camera.

### Community 1358 - "Community 1358"
Cohesion: 1.0
Nodes (1): Command-line entry point for creating a follow-enabled `.rrd` artifact.

### Community 1359 - "Community 1359"
Cohesion: 1.0
Nodes (1): Visualization-policy layer for the repo-owned Rerun event sink.

### Community 1360 - "Community 1360"
Cohesion: 1.0
Nodes (1): Own Rerun entity layout, timelines, and branch logging semantics.      The curre

### Community 1361 - "Community 1361"
Cohesion: 1.0
Nodes (1): Map one SDK-free visualization item to the current Rerun policy.

### Community 1362 - "Community 1362"
Cohesion: 1.0
Nodes (1): Log one transform child per trajectory pose.

### Community 1363 - "Community 1363"
Cohesion: 1.0
Nodes (1): Return a conservative token for one Rerun entity path component.

### Community 1364 - "Community 1364"
Cohesion: 1.0
Nodes (1): Repo-owned Rerun observer sinks and Ray sidecar actors.

### Community 1365 - "Community 1365"
Cohesion: 1.0
Nodes (1): Shared single-stream Rerun sink behavior.

### Community 1366 - "Community 1366"
Cohesion: 1.0
Nodes (1): Observe one runtime update without durable `RunEvent` wrapping.

### Community 1367 - "Community 1367"
Cohesion: 1.0
Nodes (1): Release the recording handle.

### Community 1368 - "Community 1368"
Cohesion: 1.0
Nodes (1): Best-effort live Rerun viewer sink.

### Community 1369 - "Community 1369"
Cohesion: 1.0
Nodes (1): Durable RRD export sink with export-only post-processing.

### Community 1370 - "Community 1370"
Cohesion: 1.0
Nodes (1): Ray sidecar that owns one live Rerun viewer stream.

### Community 1371 - "Community 1371"
Cohesion: 1.0
Nodes (1): Ray sidecar that owns one durable RRD export stream.

### Community 1372 - "Community 1372"
Cohesion: 1.0
Nodes (1): Deterministic validation helpers for repo-owned Rerun recordings.

### Community 1373 - "Community 1373"
Cohesion: 1.0
Nodes (1): Summary of one populated point-cloud entity in a recording.

### Community 1374 - "Community 1374"
Cohesion: 1.0
Nodes (1): Deterministic semantic summary extracted from one `.rrd` recording.

### Community 1375 - "Community 1375"
Cohesion: 1.0
Nodes (1): Artifacts emitted by the repo-owned validation loop.

### Community 1376 - "Community 1376"
Cohesion: 1.0
Nodes (1): Load one `.rrd` and summarize the current repo-owned Rerun surfaces.

### Community 1377 - "Community 1377"
Cohesion: 1.0
Nodes (1): Write a deterministic validation bundle for one `.rrd` recording.

### Community 1378 - "Community 1378"
Cohesion: 1.0
Nodes (1): Run the validation loop on one `.rrd` recording and print the artifact paths.

### Community 1379 - "Community 1379"
Cohesion: 1.0
Nodes (1): Opt-in real-data integration test for the full ViSTA streaming pipeline.  This f

### Community 1380 - "Community 1380"
Cohesion: 1.0
Nodes (1): Small runtime sources used by focused pipeline smoke tests.

### Community 1381 - "Community 1381"
Cohesion: 1.0
Nodes (1): Minimal offline source for pipeline smoke tests.

### Community 1382 - "Community 1382"
Cohesion: 1.0
Nodes (1): Finite in-memory packet stream for streaming smoke tests.

### Community 1383 - "Community 1383"
Cohesion: 1.0
Nodes (1): Minimal streaming-capable source for pipeline smoke tests.

### Community 1384 - "Community 1384"
Cohesion: 1.0
Nodes (1): Tests for the simplified ADVIO adapter and replay stream.

### Community 1385 - "Community 1385"
Cohesion: 1.0
Nodes (1): Focused tests for app-owned preview runtime controllers.

### Community 1386 - "Community 1386"
Cohesion: 1.0
Nodes (1): Emit one packet, then block until the test disconnects the stream.

### Community 1387 - "Community 1387"
Cohesion: 1.0
Nodes (1): Tests for the shared Pydantic base-model split.

### Community 1388 - "Community 1388"
Cohesion: 1.0
Nodes (1): Runtime object used to verify default setup behavior.

### Community 1389 - "Community 1389"
Cohesion: 1.0
Nodes (1): Config whose runtime target is constructed via ``target_type``.

### Community 1390 - "Community 1390"
Cohesion: 1.0
Nodes (1): Config without a runtime target.

### Community 1391 - "Community 1391"
Cohesion: 1.0
Nodes (1): Config that exposes an invalid target_type.

### Community 1392 - "Community 1392"
Cohesion: 1.0
Nodes (1): Plain validated payload without config helper methods.

### Community 1393 - "Community 1393"
Cohesion: 1.0
Nodes (1): Enum used to verify serialized primitive conversion.

### Community 1394 - "Community 1394"
Cohesion: 1.0
Nodes (1): Nested payload used to verify recursive normalization.

### Community 1395 - "Community 1395"
Cohesion: 1.0
Nodes (1): Config used to lock JSON and TOML serialization behavior.

### Community 1396 - "Community 1396"
Cohesion: 1.0
Nodes (1): Config used to verify TOML normalization semantics.

### Community 1397 - "Community 1397"
Cohesion: 1.0
Nodes (1): Return (sweep_toml, vista_template, mast3r_template) paths.

### Community 1398 - "Community 1398"
Cohesion: 1.0
Nodes (1): Tests for the repo-local Codex history utility.

### Community 1399 - "Community 1399"
Cohesion: 1.0
Nodes (1): Focused tests for the Rich-backed console wrapper.

### Community 1400 - "Community 1400"
Cohesion: 1.0
Nodes (1): Tests for pure dataset-wide aggregation functions.

### Community 1401 - "Community 1401"
Cohesion: 1.0
Nodes (1): Each sequence must contribute exactly one value to the leaderboard even when

### Community 1402 - "Community 1402"
Cohesion: 1.0
Nodes (1): Two runs on the same (sequence, source) must be averaged, not last-write-wins.

### Community 1403 - "Community 1403"
Cohesion: 1.0
Nodes (1): Tests for dataset-wide Plotly figure builders.

### Community 1404 - "Community 1404"
Cohesion: 1.0
Nodes (1): Two runs on the same (sequence, source) must be averaged, not last-write-wins.

### Community 1405 - "Community 1405"
Cohesion: 1.0
Nodes (1): Tests for dataset-wide trajectory evaluation query helpers.

### Community 1406 - "Community 1406"
Cohesion: 1.0
Nodes (1): Create a minimal run artifact tree for one ADVIO sequence.

### Community 1407 - "Community 1407"
Cohesion: 1.0
Nodes (1): Write a non-degenerate 4-pose trajectory (required for Sim3 rank check).

### Community 1408 - "Community 1408"
Cohesion: 1.0
Nodes (1): Tests for shared geometry primitives.

### Community 1409 - "Community 1409"
Cohesion: 1.0
Nodes (1): Focused tests for derived ground-plane alignment.

### Community 1410 - "Community 1410"
Cohesion: 1.0
Nodes (1): Tests for camera-intrinsics comparison utilities.

### Community 1411 - "Community 1411"
Cohesion: 1.0
Nodes (1): Minimal CLI-facing smoke tests for the refactored pipeline module.

### Community 1412 - "Community 1412"
Cohesion: 1.0
Nodes (1): Tests for the method wrappers.

### Community 1413 - "Community 1413"
Cohesion: 1.0
Nodes (1): Tests for package-root public export surfaces.

### Community 1414 - "Community 1414"
Cohesion: 1.0
Nodes (1): Tests for centralized repository path handling.

### Community 1415 - "Community 1415"
Cohesion: 1.0
Nodes (1): Tests for shared trajectory plotting helpers.

### Community 1416 - "Community 1416"
Cohesion: 1.0
Nodes (1): Tests for the minimal reconstruction config and Open3D backend.

### Community 1417 - "Community 1417"
Cohesion: 1.0
Nodes (1): Tests for reconstruction artifact Plotly figure builders.

### Community 1418 - "Community 1418"
Cohesion: 1.0
Nodes (1): Tests for the optional Record3D USB integration.

### Community 1419 - "Community 1419"
Cohesion: 1.0
Nodes (1): Small in-memory stand-in for the upstream Record3D bindings.

### Community 1420 - "Community 1420"
Cohesion: 1.0
Nodes (1): Tests for the Python-side Record3D Wi-Fi transport.

### Community 1421 - "Community 1421"
Cohesion: 1.0
Nodes (1): Tests for offline follow-enabled Rerun artifact generation.

### Community 1422 - "Community 1422"
Cohesion: 1.0
Nodes (1): Focused tests for Rerun layout and modality semantics.

### Community 1423 - "Community 1423"
Cohesion: 1.0
Nodes (1): Recording-level semantic tests for the repo-owned Rerun integration.

### Community 1424 - "Community 1424"
Cohesion: 1.0
Nodes (1): Focused tests for explicit Rerun timeline semantics.

### Community 1425 - "Community 1425"
Cohesion: 1.0
Nodes (1): Tests for repo-owned Rerun validation helpers.

### Community 1426 - "Community 1426"
Cohesion: 1.0
Nodes (1): Tests for the SLAM stage visualization adapter.

### Community 1427 - "Community 1427"
Cohesion: 1.0
Nodes (1): Tests for the target source stage runtime.

### Community 1428 - "Community 1428"
Cohesion: 1.0
Nodes (1): Tests for repo-owned streaming Rerun sink behavior.

### Community 1429 - "Community 1429"
Cohesion: 1.0
Nodes (1): Tests for ViSTA-native persisted artifact diagnostics.

### Community 1435 - "Community 1435"
Cohesion: 1.0
Nodes (1): Build a profile from source settings that change stored bytes.

### Community 1436 - "Community 1436"
Cohesion: 1.0
Nodes (1): Return compact row-count metadata for one entry's analysis tables.

### Community 1437 - "Community 1437"
Cohesion: 1.0
Nodes (1): Load persisted long-form statistics as a dataframe.

### Community 1438 - "Community 1438"
Cohesion: 1.0
Nodes (1): Load persisted long-form metadata as a dataframe.

### Community 1439 - "Community 1439"
Cohesion: 1.0
Nodes (1): Load a metric-depth payload stored as `.npy` or image data.

### Community 1440 - "Community 1440"
Cohesion: 1.0
Nodes (1): Source that can materialize both normalized run input and benchmark sidecars.

### Community 1441 - "Community 1441"
Cohesion: 1.0
Nodes (1): Materialize benchmark inputs required for a normalized-store entry.

### Community 1442 - "Community 1442"
Cohesion: 1.0
Nodes (1): Build the normalized store for one dataset under the shared datastore root.

### Community 1443 - "Community 1443"
Cohesion: 1.0
Nodes (1): Load persisted long-form statistics rows for one normalized entry.

### Community 1444 - "Community 1444"
Cohesion: 1.0
Nodes (1): Load persisted long-form metadata rows for one normalized entry.

### Community 1445 - "Community 1445"
Cohesion: 1.0
Nodes (1): Load normalized timestamps from JSON or simple delimited text.

### Community 1446 - "Community 1446"
Cohesion: 1.0
Nodes (1): Return the effective ADVIO provider for one optional serving config.

## Knowledge Gaps
- **268 isolated node(s):** `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`, `Frame preprocessing helpers for ViSTA-SLAM.`, `One RGB frame prepared for upstream ViSTA ingestion.`, `Use the exact upstream ViSTA crop-and-resize helper path.`, `Convert one upstream ViSTA array-like payload into a numpy array.` (+263 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 20`** (13 nodes): `test_package_exports.py`, `Tests for package-root public export surfaces.`, `test_align_root_does_not_reexport_heavy_subpackages()`, `test_executable_stage_packages_export_canonical_surfaces()`, `test_interfaces_package_exports_only_canonical_pose_surface()`, `test_methods_package_exports_slam_surfaces()`, `test_pipeline_contracts_package_is_not_a_compatibility_hub()`, `test_pipeline_package_exports_only_minimal_public_surface()`, `test_reconstruction_package_exports_runtime_surfaces_without_harness()`, `test_replay_package_exports_only_replay_primitives()`, `test_source_materialization_does_not_import_stage_package()`, `test_sources_package_exports_source_owned_contracts()`, `test_vista_package_is_the_only_canonical_vista_surface()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (8 nodes): `get_events()`, `get_snapshot()`, `Backend boundary between launch surfaces and execution substrates.  This module`, `read_payload()`, `shutdown()`, `stop_run()`, `submit_run()`, `backend.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 23`** (2 nodes): `streamlit_app.py`, `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 24`** (2 nodes): `ray.py`, `Ray-specific helpers for future stage runtime deployment.  This module intention`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 25`** (1 nodes): `Build the shared transform DTO from XYZW quaternion and XYZ translation arrays.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 26`** (1 nodes): `Build the shared transform DTO from a 4x4 homogeneous matrix.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 27`** (1 nodes): `Return the compact source label used in logs and diagnostics.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 28`** (1 nodes): `Disconnect or release the source and any owned runtime resources.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `Return the short user-facing dataset label.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `Deserialize one IPC payload back into the target validated model type.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `Return the human-readable label shown in plan previews.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (1 nodes): `Return whether ``exc`` looks like a transient local Ray connection failure.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 33`** (1 nodes): `Build one spec from one JSON object.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 34`** (1 nodes): `Return the net code-line delta.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (1 nodes): `Return the path that should own this change in reports.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 36`** (1 nodes): `Return the short user-facing dataset label.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 37`** (1 nodes): `Coordinate-frame semantics for served ADVIO trajectories.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 38`** (1 nodes): `Typed ADVIO serving semantics shared by request and manifest contracts.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 39`** (1 nodes): `Source-prepared RGB-D reference-cloud sampling policy.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 40`** (1 nodes): `Local availability summary for one dataset scene.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 41`** (1 nodes): `High-level summary of committed and local dataset coverage.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 42`** (1 nodes): `Return the effective ADVIO provider for one optional serving config.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Test package helpers and suites for PRML VSLAM.` connect `Community 4` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 5`, `Community 6`, `Community 7`, `Community 10`, `Community 13`, `Community 14`, `Community 15`, `Community 17`?**
  _High betweenness centrality (0.145) - this node is a cross-community bridge._
- **Why does `SequenceManifest` connect `Community 6` to `Community 0`, `Community 1`, `Community 2`, `Community 4`, `Community 5`, `Community 7`, `Community 9`, `Community 10`, `Community 11`, `Community 14`, `Community 15`?**
  _High betweenness centrality (0.064) - this node is a cross-community bridge._
- **Why does `StageKey` connect `Community 2` to `Community 0`, `Community 1`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 8`?**
  _High betweenness centrality (0.057) - this node is a cross-community bridge._
- **Are the 536 inferred relationships involving `SequenceManifest` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`SequenceManifest` has 536 INFERRED edges - model-reasoned connections that need verification._
- **Are the 478 inferred relationships involving `PreparedBenchmarkInputs` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`PreparedBenchmarkInputs` has 478 INFERRED edges - model-reasoned connections that need verification._
- **Are the 467 inferred relationships involving `DatasetId` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`DatasetId` has 467 INFERRED edges - model-reasoned connections that need verification._
- **Are the 452 inferred relationships involving `StageKey` (e.g. with `RunConfigOverrideCommand` and `_RerunViewerProcess`) actually correct?**
  _`StageKey` has 452 INFERRED edges - model-reasoned connections that need verification._
