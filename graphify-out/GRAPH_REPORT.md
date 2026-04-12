# Graph Report - .  (2026-04-12)

## Corpus Check
- 417 files · ~39,279,181 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 3925 nodes · 7718 edges · 167 communities detected
- Extraction: 66% EXTRACTED · 34% INFERRED · 0% AMBIGUOUS · INFERRED: 2631 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## God Nodes (most connected - your core abstractions)
1. `SequenceManifest` - 127 edges
2. `SlamArtifacts` - 102 edges
3. `MethodId` - 96 edges
4. `RunState` - 93 edges
5. `RunPlan` - 90 edges
6. `SlamOutputPolicy` - 84 edges
7. `SlamBackendConfig` - 84 edges
8. `RunSnapshot` - 81 edges
9. `SlamUpdate` - 79 edges
10. `ArtifactRef` - 76 edges

## Surprising Connections (you probably didn't know these)
- `FakeRecord3DStream` --uses--> `OfflineSequenceSource`  [INFERRED]
  tests/test_record3d.py → src/prml_vslam/protocols/source.py
- `FakeRecord3DStream` --uses--> `StreamingSequenceSource`  [INFERRED]
  tests/test_record3d.py → src/prml_vslam/protocols/source.py
- `FakeStore` --uses--> `SlamUpdate`  [INFERRED]
  tests/test_app.py → src/prml_vslam/methods/updates.py
- `FakeRecord3DRuntime` --uses--> `SlamUpdate`  [INFERRED]
  tests/test_app.py → src/prml_vslam/methods/updates.py
- `FakeAdvioRuntime` --uses--> `SlamUpdate`  [INFERRED]
  tests/test_app.py → src/prml_vslam/methods/updates.py

## Hyperedges (group relationships)
- **Record3D Wi-Fi Preview Runtime Flow** — wifi_signaling_client, wifi_receiver_runtime, wifi_packets_packet_from_video_fn, wifi_session_preview_session [INFERRED 0.88]
- **Trajectory Plotting Stack** — theme_apply_standard_xy_layout, theme_apply_standard_3d_layout, trajectories_trajectory_plot_builder, metrics_build_trajectory_figure, pipeline_build_evo_ape_colormap_figure, record3d_build_live_trajectory_figure [INFERRED 0.86]
- **ADVIO Download Resolution Flow** — advio_download_adviodownloadmanager, fetch_datasetfetchhelper, advio_layout_modality_specs, advio_models_adviodownloadrequest [INFERRED 0.87]
- **Explicit Trajectory Evaluation Flow** — eval_services_trajectoryevaluationservice, eval_protocols_trajectoryevaluator, eval_contracts_evaluationselection, eval_contracts_evaluationartifact [EXTRACTED 1.00]
- **Trajectory Artifact IO Flow** — geometry_write_tum_trajectory, geometry_load_tum_trajectory, geometry_tum_file_io, geometry_pose_trajectory3d_model [EXTRACTED 1.00]
- **Shared Live Preview Pattern** — live_session_shared_components, record3d_page_live_ui, advio_page_dataset_ui, record3d_controller_actions, advio_controller_page_actions [INFERRED 0.87]
- **Monocular VSLAM Pipeline Orchestration** — pkg_pipeline, pkg_methods, pkg_datasets [INFERRED 0.85]
- **Coordinate Frame Semantics** — concept_se3pose, concept_frametransform, convention_world_camera_pose [INFERRED 0.90]
- **Offline Artifact Boundary** — concept_sequencemanifest, concept_slamartifacts, pkg_pipeline [INFERRED 0.85]
- **Execution Pipeline Flow** — pipeline_package, sequence_manifest, slam_artifacts, run_summary [EXTRACTED 1.00]
- **Benchmark Ecosystem** — pipeline_package, eval_package, visualization_package [INFERRED 0.90]
- **Utils Foundation Pattern** — utils_base_data, base_config_base_config, console_console, utils_requirements_config_factory_pattern [INFERRED 0.82]
- **App Layered Rerun Flow** — bootstrap_app_context, state_session_state_store, pages___init___page_registry, services_runtime_controllers, models_app_state_contracts [EXTRACTED 1.00]
- **ViSTA-SLAM Core Stack** — vista_slam_requirements, python_dbow3, pybind11 [INFERRED 0.80]
- **pybind11 C++ Interface Documentation** — index_rst, object_rst, numpy_rst, utilities_rst [EXTRACTED 1.00]
- **DBoW3 Build System** — dbow3_cmakelists, dbow3_src_cmakelists, dbow3_tests_cmakelists, dbow3_utils_cmakelists [EXTRACTED 1.00]
- **Evaluation Workflow** — tool_evo, tool_path_config, dataset_advio [INFERRED 0.80]
- **Method Normalization Pattern** — contract_slam_update, contract_slam_artifacts, method_vista_slam [INFERRED 0.85]
- **pybind11 Advanced Type Casting Subsystem** — pybind11_chrono_caster, pybind11_type_conversions, pybind11_string_caster, pybind11_custom_caster, pybind11_functional_caster [EXTRACTED 1.00]
- **pybind11 CMake Build Integration Test Matrix** — pybind11_test_cmake_build_root, pybind11_test_cmake_build_installed_embed, pybind11_test_cmake_build_subdirectory_embed, pybind11_test_cmake_build_installed_target, pybind11_test_cmake_build_installed_function, pybind11_test_cmake_build_subdirectory_function, pybind11_test_cmake_build_subdirectory_target [EXTRACTED 1.00]

## Communities

### Community 0 - "Community 0"
Cohesion: 0.01
Nodes (90): get(), value(), deprecated_call(), pytest.deprecated_call() seems broken in pytest<3.9.x; concretely, it     doesn', # TODO: Remove this when testing requires pytest>=3.9., bind_ConstructorStats(), cpp_std(), PYBIND11_MODULE() (+82 more)

### Community 1 - "Community 1"
Cohesion: 0.01
Nodes (94): AriaSynthetic, ARKitScene, convert traj_string into translation and rotation matrices         Args:, BaseViewGraphDataset, is_good_type(), This function:             - first downsizes the image with LANCZOS inteprolatio, This function:             - first downsizes the image with LANCZOS inteprolatio, Define all basic options.      Usage:         class MyDataset (BaseStereoViewDat (+86 more)

### Community 2 - "Community 2"
Cohesion: 0.04
Nodes (177): AppContext, build_advio_demo_request(), load_run_request_toml(), persist_advio_demo_request(), Shared helpers for the bounded ADVIO pipeline demo., Build the canonical bounded ADVIO demo request shared by app and CLI., Load a pipeline request TOML through the repo-owned config path helper., Persist a pipeline request TOML through the repo-owned config path helper. (+169 more)

### Community 3 - "Community 3"
Cohesion: 0.01
Nodes (83): multiple_values_error(), nameless_argument_error(), process(), instance_simple_holder_in_ptrs(), size_in_ptrs(), is_instance_method_of_type(), try_get_cpp_conduit_method(), try_raw_pointer_ephemeral_from_cpp_conduit() (+75 more)

### Community 4 - "Community 4"
Cohesion: 0.02
Nodes (157): ADVIO Page Controller Actions, ADVIO Dataset Page Renderer, Rationale: Explicit Evaluation Actions, Rationale: Single Session-State Adapter, Streamlit Workbench Architecture, Base Config Model, Normalize Config Value Helper, BaseData (+149 more)

### Community 5 - "Community 5"
Cohesion: 0.04
Nodes (150): _build_artifacts(), _build_live_pointmap(), _count_valid_pointmap_points(), _FlowTracker, Canonical ViSTA-SLAM backend adapter (offline + streaming)., Persist upstream outputs and convert to canonical repository artifacts., Read the latest upstream view state and convert it into live repo telemetry., ViSTA-SLAM backend implementing offline and streaming contracts. (+142 more)

### Community 6 - "Community 6"
Cohesion: 0.02
Nodes (82): add(), BoWFrame(), CmdLineParser, loadFeatures(), main(), readImagePaths(), saveToFile(), CmdLineParser (+74 more)

### Community 7 - "Community 7"
Cohesion: 0.02
Nodes (53): cast(), localtime_thread_safe(), clear_instance(), enable_dynamic_attributes(), get_fully_qualified_tp_name(), make_default_metaclass(), make_object_base_type(), make_static_property_type() (+45 more)

### Community 8 - "Community 8"
Cohesion: 0.02
Nodes (13): CustomContains, float_, get_annotations_helper(), m_defs(), C++ default and converting constructors are equivalent to type calls in Python, Tests implicit casting when assigning or appending to dicts and lists., test_class_attribute_types(), test_constructors() (+5 more)

### Community 9 - "Community 9"
Cohesion: 0.03
Nodes (43): collate_with_cat(), listify(), MyNvtxRange, Transfer some variables to another device (i.e. GPU, CPU:torch, CPU:numpy)., to_cpu(), to_cuda(), to_numpy(), todevice() (+35 more)

### Community 10 - "Community 10"
Cohesion: 0.02
Nodes (40): adjust_learning_rate(), all_reduce_mean(), filename(), get_grad_norm_(), _get_num_layer_for_vit(), get_parameter_groups(), get_rank(), get_world_size() (+32 more)

### Community 11 - "Community 11"
Cohesion: 0.06
Nodes (58): AdvioDownloadManager, ADVIO Package Public API, ADVIO Catalog Loader, ADVIO Modality Path Specs, ADVIO Reference Path Resolver, AdvioCalibration, _expect_float_list(), _expect_mapping() (+50 more)

### Community 12 - "Community 12"
Cohesion: 0.03
Nodes (38): PythonMyException7, Exception, CustomData(), FlakyException, MyException, MyException2, MyException3, MyException4 (+30 more)

### Community 13 - "Community 13"
Cohesion: 0.04
Nodes (40): Criterion, count_stats(), extract_markers(), main(), MarkerEntry, parse_args(), Compute Python line-of-code statistics for src/ and tests/., Render a detailed Rich table for one marker kind. (+32 more)

### Community 14 - "Community 14"
Cohesion: 0.03
Nodes (26): Args, BreaksBase, BreaksTramp, Chimera, Dog, ForwardClass, Hamster, Pet (+18 more)

### Community 15 - "Community 15"
Cohesion: 0.04
Nodes (35): build_ext, cuRoPE2D, cuRoPE2D_func, rope_2d(), rope_2d_cpu(), _Extension, CMakeBuild, CMakeExtension (+27 more)

### Community 16 - "Community 16"
Cohesion: 0.04
Nodes (17): auxiliaries(), data(), data_t(), index_at(), index_at_t(), offset_at(), offset_at_t(), PyValueHolder (+9 more)

### Community 17 - "Community 17"
Cohesion: 0.04
Nodes (29): FakePyMappingBadItems, FakePyMappingGenObj, FakePyMappingItemsNotCallable, FakePyMappingItemsWithArg, FakePyMappingMissingItems, FakePyMappingWithItems, OptionalProperties, pass_std_vector_int() (+21 more)

### Community 18 - "Community 18"
Cohesion: 0.03
Nodes (34): SquareMatrix is derived from Matrix and inherits the buffer protocol, # TODO: fix on recent PyPy, test_inherited_protocol(), Tests the ability to pass bytes to C++ string-accepting functions.  Note that th, Tests the ability to pass bytearray to C++ string-accepting functions, Tests support for C++17 string_view arguments and return values, Tests unicode conversion and error reporting., Issue #929 - out-of-range integer values shouldn't be accepted (+26 more)

### Community 19 - "Community 19"
Cohesion: 0.04
Nodes (35): cast(), cast_impl(), array_copy_but_one(), assert_equal_ref(), assert_keeps_alive(), assert_sparse_equal_ref(), assign_both(), get_elem() (+27 more)

### Community 20 - "Community 20"
Cohesion: 0.05
Nodes (33): DPTOutputAdapter, FeatureFusionBlock_custom, Interpolate, make_fusion_block(), make_scratch(), pair(), Forward pass.         Args:             x (tensor): input         Returns:, Feature fusion block. (+25 more)

### Community 21 - "Community 21"
Cohesion: 0.05
Nodes (28): Capture, doc(), gc_collect(), _make_explanation(), msg(), Output, pytest_assertrepr_compare(), pytest configuration  Extends output capture as needed by pybind11: ignore const (+20 more)

### Community 22 - "Community 22"
Cohesion: 0.05
Nodes (33): ExtendedVirtClass, Makes sure there is no GIL deadlock when running in a thread.      It runs in a, Makes sure there is no GIL deadlock when running in a thread multiple times in p, Makes sure there is no GIL deadlock when running in a thread multiple times sequ, Makes sure there is no GIL deadlock when using processes.      This test is for, Makes sure that the GIL can be acquired by another module from a GIL-released st, Makes sure that the GIL can be acquired by another module from a GIL-acquired st, Makes sure that the GIL can be acquired/released by another module     from a GI (+25 more)

### Community 23 - "Community 23"
Cohesion: 0.04
Nodes (21): ExampleMandA, NoneCastTester, NoneTester, Static property getter and setters expect the type object as the their only argu, Overriding pybind11's default metaclass changes the behavior of `static_property, When returning an rvalue, the return value policy is automatically changed from, #2778: implicit casting from None to object (not pointer), #283: __str__ called on uninitialized instance when constructor arguments invali (+13 more)

### Community 24 - "Community 24"
Cohesion: 0.1
Nodes (42): _action_from_page_state(), _advio_sequence_id_from_slug(), _build_preview_plan(), _build_request_from_action(), _build_streaming_source_from_action(), _compute_evo_preview(), _discover_pipeline_config_paths(), _display_repo_relative_path() (+34 more)

### Community 25 - "Community 25"
Cohesion: 0.07
Nodes (31): create_and_destroy(), PYBIND11_OVERRIDE(), PyTF6(), PyTF7(), Tests py::init_factory() wrapper with various upcasting and downcasting returns, Tests py::init_factory() wrapper around various ways of returning the object, Tests py::init_factory() wrapper with value conversions and alias types, Tests init factory functions with dual main/alias factory functions (+23 more)

### Community 26 - "Community 26"
Cohesion: 0.07
Nodes (21): camera_matrix_of_crop(), crop_image_depthmap(), ImageList, Return a crop of the input view., Convenience class to aply the same operation to a whole set of images., Jointly rescale a (image, depthmap)          so that (out_width, out_height) >=, rescale_image_depthmap(), colmap_to_opencv_intrinsics() (+13 more)

### Community 27 - "Community 27"
Cohesion: 0.06
Nodes (0): 

### Community 28 - "Community 28"
Cohesion: 0.06
Nodes (12): Mixing bases with and without static properties should be possible     and the r, Mixing bases with and without dynamic attribute support, Returning an offset (non-first MI) base class pointer should recognize the insta, Tests returning an offset (non-first MI) base class pointer to a derived instanc, Tests that diamond inheritance works as expected (issue #959), Tests extending a Python class from a single inheritor of a MI class, test_diamond_inheritance(), test_mi_base_return() (+4 more)

### Community 29 - "Community 29"
Cohesion: 0.09
Nodes (9): assert_equal(), dt_fmt(), packed_dtype_fmt(), partial_dtype_fmt(), partial_ld_offset(), partial_nested_fmt(), simple_dtype_fmt(), test_dtype() (+1 more)

### Community 30 - "Community 30"
Cohesion: 0.07
Nodes (18): CastUnusualOpRefConstRef(), CastUnusualOpRefMovable(), CopyOnlyInt, MoveOnlyInt, MoveOrCopyInt, An object with a private `operator new` cannot be returned by value, #389: rvp::move should fall-through to copy on non-movable objects, Make sure that cast from pytype rvalue to other pytype works (+10 more)

### Community 31 - "Community 31"
Cohesion: 0.09
Nodes (26): str, DataOnlyConfig, InvalidTargetConfig, NestedPayload, PlainPayload, Tests for the shared Pydantic base-model split., Runtime object used to verify default setup behavior., Config whose runtime target is constructed via ``target_type``. (+18 more)

### Community 32 - "Community 32"
Cohesion: 0.08
Nodes (11): chamfer_distance_RMSE(), eval_recon(), eval_recon_from_saved_data(), load_data(), gt_depths: N,H,W     gt_poses: N,4,4     gt_intri: 3,3     est_local_pcls: N,H,W, rel_gt_est: None or [R, t, s] for the relative pose between the ground truth and, transform_to_world_coordinates(), test_mock_slam_backend_runs_sequence_manifest_offline() (+3 more)

### Community 33 - "Community 33"
Cohesion: 0.16
Nodes (17): DenseCloudEvaluationArtifact, DiscoveredRun, EfficiencyEvaluationArtifact, EvaluationArtifact, EvaluationSelection, TrajectoryEvaluationService Export, DenseCloudEvaluator Protocol, EfficiencyEvaluator Protocol (+9 more)

### Community 34 - "Community 34"
Cohesion: 0.08
Nodes (20): LatestCamera, log_view(), rerun_vis_views(), compute_geo_valid_mask_batched(), compute_local_pointclouds(), compute_symmetric_geo_valid_mask(), depth_from_pointcloud_dot_batched(), estimate_intrinsic_from_pts3d() (+12 more)

### Community 35 - "Community 35"
Cohesion: 0.09
Nodes (7): LoopDetector, PoseGraphEdges, PoseGraphNodes, PoseGraphOpt, PoseGraphOptAll, add a node to the pose graph.          Notice that the absolute pose of the node, PyPose

### Community 36 - "Community 36"
Cohesion: 0.17
Nodes (24): _build_fake_catalog(), Tests for the simplified ADVIO adapter and replay stream., test_advio_dataset_service_downloads_selected_modalities_from_cached_archive(), test_advio_dataset_service_handles_official_archive_layout(), test_advio_dataset_service_lists_and_loads_local_sequences(), test_advio_dataset_service_offline_preset_downloads_evaluation_ready_bundle(), test_advio_dataset_service_refreshes_corrupted_cached_archive(), test_advio_dataset_service_summarize_reuses_precomputed_statuses() (+16 more)

### Community 37 - "Community 37"
Cohesion: 0.09
Nodes (6): E_nc, El, times_hundred(), times_ten(), UserMapLike, UserVectorLike

### Community 38 - "Community 38"
Cohesion: 0.12
Nodes (21): get_cmake_dir(), get_include(), get_pkgconfig_dir(), Return the path to the pybind11 CMake module directory., Return the path to the pybind11 pkgconfig directory., Return the path to the pybind11 include directory. The historical "user"     arg, advio_download(), advio_summary() (+13 more)

### Community 39 - "Community 39"
Cohesion: 0.13
Nodes (22): ArxivSourceSpec, download_file(), fetch_pdf(), fetch_tex_source(), from_json(), load_manifest(), main(), normalize_member_path() (+14 more)

### Community 40 - "Community 40"
Cohesion: 0.14
Nodes (21): Build ADVIO Crowd Density Figure, Build ADVIO Local Readiness Figure, Build ADVIO Scene Attribute Figure, Build ADVIO Scene Mix Figure, Build Metrics Error Figure, Build Metrics Trajectory Figure, Build Evo APE Colormap Figure, Plotting Package Public API (+13 more)

### Community 41 - "Community 41"
Cohesion: 0.12
Nodes (7): test_call_callback_with_pyobject_ptr_arg(), test_cast_handle_to_pyobject_ptr(), test_cast_object_to_pyobject_ptr(), test_pass_list_pyobject_ptr(), test_pass_pyobject_ptr(), test_type_caster_name_via_incompatible_function_arguments_type_error(), ValueHolder

### Community 42 - "Community 42"
Cohesion: 0.12
Nodes (4): FakeRecord3DStream, test_record3d_stream_wait_for_packet_returns_shared_contract(), test_usb_packet_stream_disconnect_stops_active_stream(), test_usb_packet_stream_wait_for_packet_returns_shared_contract()

### Community 43 - "Community 43"
Cohesion: 0.13
Nodes (20): FrameTransform, SE3Pose, SequenceManifest, T_world_camera Pose Convention, Interfaces and Contracts Architecture, prml_vslam.app, prml_vslam.benchmark, prml_vslam.datasets (+12 more)

### Community 44 - "Community 44"
Cohesion: 0.12
Nodes (9): PacketSessionRuntime, Own one threaded `FramePacketStream` worker plus its snapshot state., Return a deep copy of the latest session snapshot., Start a fresh worker after stopping any currently active one., Register the active stream for cooperative stop/disconnect handling., Apply a partial snapshot update under the internal lock., Replace the snapshot under the internal lock., Stop the worker, disconnect the stream, and update the terminal snapshot. (+1 more)

### Community 45 - "Community 45"
Cohesion: 0.15
Nodes (4): _build_runtime(), test_record3d_wifi_closed_after_connect_logs_runtime_failure(), test_record3d_wifi_closed_before_track_sets_setup_failure_without_logging(), test_record3d_wifi_metadata_failure_is_non_fatal()

### Community 46 - "Community 46"
Cohesion: 0.17
Nodes (6): Record3D-backed streaming-source wrapper for pipeline-owned sessions., Record3D-backed live source compatible with pipeline-owned sessions., Return the normalized live-sequence boundary for one Record3D source., Open the configured Record3D packet stream for pipeline consumption., Record3DStreamingSource, StreamingSequenceSource

### Community 47 - "Community 47"
Cohesion: 0.15
Nodes (1): Tests for centralized repository path handling.

### Community 48 - "Community 48"
Cohesion: 0.15
Nodes (12): build(), docs(), lint(), make_changelog(), Lint the codebase (except for clang-format/tidy)., Run the tests (requires a compiler)., Run the packaging tests., Build the docs. Pass --non-interactive to avoid serving. (+4 more)

### Community 49 - "Community 49"
Cohesion: 0.17
Nodes (12): py::arg, call_guard, Eigen Support, PYBIND11_EMBEDDED_MODULE, GIL Management, keep_alive, PYBIND11_MODULE, PYBIND11_MAKE_OPAQUE (+4 more)

### Community 50 - "Community 50"
Cohesion: 0.2
Nodes (11): Eval Package, evo Adapter, Offline Runner, Pipeline Package, Rationale: Explicit Evaluation Separation, Rationale: Normalized Offline Boundary, Rerun Integration Layer, Sequence Manifest (+3 more)

### Community 51 - "Community 51"
Cohesion: 0.2
Nodes (10): MASt3R-SLAM, ViSTA-SLAM, DBoW3Py, prml-vslam, Challenge 5: Uncalibrated Monocular VSLAM, Thin App Surface, Benchmark Policy Separation, Thin Method Wrappers (+2 more)

### Community 52 - "Community 52"
Cohesion: 0.22
Nodes (3): _fake_advio_service(), Focused CLI tests for ADVIO dataset commands., test_advio_download_command_builds_explicit_request()

### Community 53 - "Community 53"
Cohesion: 0.25
Nodes (9): Wi-Fi Single Receiver Limit, Decode Record3D Wi-Fi Depth, Record3D Wi-Fi Metadata, Record3D Wi-Fi Packet From Video Frame, Record3D Wi-Fi Receiver Runtime, Open Record3D Wi-Fi Preview Stream, Record3D Wi-Fi Preview Stream Session, Record3D Wi-Fi Signaling Client (+1 more)

### Community 54 - "Community 54"
Cohesion: 0.44
Nodes (8): _copy_if_needed(), _emit_progress(), _extract_video_frames(), _frame_stride_for_request(), _load_cached_extraction(), materialize_offline_manifest(), _resolve_timestamps_ns(), _write_json_payload()

### Community 55 - "Community 55"
Cohesion: 0.22
Nodes (5): Dataset-edge frame-graph helpers., Thin wrapper around `pytransform3d.TransformManager` for static frame compositio, Register one static transform., Resolve one composed transform back into the repo-owned transform DTO., StaticFrameGraph

### Community 56 - "Community 56"
Cohesion: 0.39
Nodes (5): _ingest_summary(), _method_summary(), _stage_from_spec(), _trajectory_summary(), _validate_request()

### Community 57 - "Community 57"
Cohesion: 0.48
Nodes (4): normalize_line_endings(), read_tz_file(), test_build_global_dist(), test_build_sdist()

### Community 58 - "Community 58"
Cohesion: 0.4
Nodes (1): Tests for package-root public export surfaces.

### Community 59 - "Community 59"
Cohesion: 0.4
Nodes (0): 

### Community 60 - "Community 60"
Cohesion: 0.4
Nodes (5): Python C++ Interface pybind11 Documentation, NumPy pybind11 Documentation, Python Types pybind11 Documentation, pybind11 Logo, Utilities pybind11 Documentation

### Community 61 - "Community 61"
Cohesion: 0.4
Nodes (5): DBoW3 Database Class, DBoW3 Utils Image 1, DBoW3 README, DBoW3 Vocabulary Class, FBOW Library

### Community 62 - "Community 62"
Cohesion: 0.5
Nodes (5): DBoW3 Root CMakeLists, DBoW3 Source CMakeLists, DBoW3 Tests CMakeLists, DBoW3 Utils CMakeLists, OpenCV Library

### Community 63 - "Community 63"
Cohesion: 0.4
Nodes (5): ADVIO Paper, arXiv Source Trees, DROID-SLAM Paper, MASt3R-SLAM Paper, ViSTA-SLAM Paper

### Community 64 - "Community 64"
Cohesion: 0.4
Nodes (5): ADVIO Modalities Overview, ADVIO Transform Tree, ViSTA-SLAM, ADVIO Dataset, System Pipeline Architecture

### Community 65 - "Community 65"
Cohesion: 0.4
Nodes (5): Graphify Report (2026-04-12), Memory: How does the ADVIO UI coordinate with the ViSTA SLAM?, Memory: How does the PoseHead in the SLAM runner use the i...?, SequenceManifest, SlamArtifacts

### Community 66 - "Community 66"
Cohesion: 0.5
Nodes (0): 

### Community 67 - "Community 67"
Cohesion: 0.5
Nodes (4): Agent Reference Documentation, Documentation Standards (AGENTS.md), Questions.md (Product Constraints), Root README.md

### Community 68 - "Community 68"
Cohesion: 0.67
Nodes (4): Record3D Upstream README Citation, Record3D Dual Transport Scope, USB Canonical Record3D Ingress, Wi-Fi Preview Lower Fidelity Constraint

### Community 69 - "Community 69"
Cohesion: 0.5
Nodes (4): ADVIO Repository Adapter, ADVIO Paper, Ground Truth As Authoritative Benchmark World Frame Rationale, Visualization Alignment Mode Rationale

### Community 70 - "Community 70"
Cohesion: 0.83
Nodes (4): RunPlan, RunPlannerService, RunRequest, Pipeline Planning Phase

### Community 71 - "Community 71"
Cohesion: 0.5
Nodes (4): SlamSession, StreamingSequenceSource, StreamingSlamBackend, Pipeline Boundaries

### Community 72 - "Community 72"
Cohesion: 1.0
Nodes (3): Open Record3D USB Packet Stream, Record3D Stream Config, Record3D USB Packet Stream

### Community 73 - "Community 73"
Cohesion: 0.67
Nodes (3): Cv2 Producer Config, Cv2 Frame Producer, Open Cv2 Replay Stream

### Community 74 - "Community 74"
Cohesion: 1.0
Nodes (2): gen(), video()

### Community 75 - "Community 75"
Cohesion: 0.67
Nodes (1): Simple script for rebuilding .codespell-ignore-lines  Usage:  cat < /dev/null >

### Community 76 - "Community 76"
Cohesion: 0.67
Nodes (0): 

### Community 77 - "Community 77"
Cohesion: 0.67
Nodes (0): 

### Community 78 - "Community 78"
Cohesion: 0.67
Nodes (2): imread_cv2(), Open an image or a depthmap with opencv-python.

### Community 79 - "Community 79"
Cohesion: 0.67
Nodes (3): Record3D USB vs Wi-Fi Transport Split, USB As Canonical Ingress Rationale, Wi-Fi Preview Lower-Fidelity Rationale

### Community 80 - "Community 80"
Cohesion: 0.67
Nodes (3): Rerun SDK, ViSTA-SLAM Live Mode Setup, Rationale for Remote Server Execution

### Community 81 - "Community 81"
Cohesion: 0.67
Nodes (3): VISTA-SLAM Teaser, Backend: Sim(3) Pose Graph Optimization, Frontend: Symmetric Two-view Association

### Community 82 - "Community 82"
Cohesion: 0.67
Nodes (3): VISTA-SLAM Architecture, Backend: Pose Graph Optimization with Loop Closure, Frontend: Symmetric Two-view Association (STA)

### Community 83 - "Community 83"
Cohesion: 0.67
Nodes (3): Construction Site with Crane, DBoW3 Example Image 0, Outdoor Scooter Parking

### Community 84 - "Community 84"
Cohesion: 0.67
Nodes (3): Deadlock Avoidance using absl::call_once, Deadlock and Global Interpreter Lock (GIL) in pybind11, Global Interpreter Lock (GIL)

### Community 85 - "Community 85"
Cohesion: 1.0
Nodes (1): Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays

### Community 86 - "Community 86"
Cohesion: 1.0
Nodes (2): Capture Manifest, Frame Sample

### Community 87 - "Community 87"
Cohesion: 1.0
Nodes (2): ImageSize.from_payload, ImageSize Model

### Community 88 - "Community 88"
Cohesion: 1.0
Nodes (0): 

### Community 89 - "Community 89"
Cohesion: 1.0
Nodes (0): 

### Community 90 - "Community 90"
Cohesion: 1.0
Nodes (2): Rationale: Centralize Generic Helpers, Shared Utils Infrastructure Scope

### Community 91 - "Community 91"
Cohesion: 1.0
Nodes (2): PathConfig Ownership Requirement, Rationale: Inject PathConfig For Determinism

### Community 92 - "Community 92"
Cohesion: 1.0
Nodes (2): Rationale: Avoid Hidden Side Effects, Small Predictable Utilities Requirement

### Community 93 - "Community 93"
Cohesion: 1.0
Nodes (2): py::module_local, Rationale for py::module_local

### Community 94 - "Community 94"
Cohesion: 1.0
Nodes (2): Rationale: Avoid raw pointers for objects managed by smart pointers, pybind11 Smart Pointer Support

### Community 95 - "Community 95"
Cohesion: 1.0
Nodes (2): Rationale: Data copying overhead in type conversions, pybind11 Type Conversions

### Community 96 - "Community 96"
Cohesion: 1.0
Nodes (2): pybind11 Test Suite CMake Configuration, pybind11 Embedding Test CMake

### Community 97 - "Community 97"
Cohesion: 1.0
Nodes (2): FakeRecord3DStream, OfflineSequenceSource

### Community 98 - "Community 98"
Cohesion: 1.0
Nodes (1): Return the upstream method name shown to users.

### Community 99 - "Community 99"
Cohesion: 1.0
Nodes (1): Record3D Transport Id

### Community 100 - "Community 100"
Cohesion: 1.0
Nodes (1): Build the canonical artifact layout from an explicit root.

### Community 101 - "Community 101"
Cohesion: 1.0
Nodes (1): Validate that the configured repository root exists.

### Community 102 - "Community 102"
Cohesion: 1.0
Nodes (1): Resolve configured directories against the repository root.

### Community 103 - "Community 103"
Cohesion: 1.0
Nodes (1): Resolve a path relative to the configured repository root.

### Community 104 - "Community 104"
Cohesion: 1.0
Nodes (1): Resolve a directory and optionally create it.

### Community 105 - "Community 105"
Cohesion: 1.0
Nodes (1): Build a transform from a 4x4 homogeneous matrix.

### Community 106 - "Community 106"
Cohesion: 1.0
Nodes (1): App Lazy Entrypoint

### Community 107 - "Community 107"
Cohesion: 1.0
Nodes (0): 

### Community 108 - "Community 108"
Cohesion: 1.0
Nodes (0): 

### Community 109 - "Community 109"
Cohesion: 1.0
Nodes (0): 

### Community 110 - "Community 110"
Cohesion: 1.0
Nodes (1): The CXX standard level. If set, will add the required flags. If left at

### Community 111 - "Community 111"
Cohesion: 1.0
Nodes (1): Build one spec from one JSON object.

### Community 112 - "Community 112"
Cohesion: 1.0
Nodes (1): Claude-Specific Guidance

### Community 113 - "Community 113"
Cohesion: 1.0
Nodes (1): AGENTS Repo Policy

### Community 114 - "Community 114"
Cohesion: 1.0
Nodes (1): Gemini-Specific Guidance

### Community 115 - "Community 115"
Cohesion: 1.0
Nodes (1): Questions.md Ground Truth

### Community 116 - "Community 116"
Cohesion: 1.0
Nodes (1): WP 1: Video Source

### Community 117 - "Community 117"
Cohesion: 1.0
Nodes (1): WP 2: Pipeline Framework

### Community 118 - "Community 118"
Cohesion: 1.0
Nodes (1): WP 3: Uncalibrated Monocular VSLAM Methods

### Community 119 - "Community 119"
Cohesion: 1.0
Nodes (1): FramePacket

### Community 120 - "Community 120"
Cohesion: 1.0
Nodes (1): Benchmark Requirements

### Community 121 - "Community 121"
Cohesion: 1.0
Nodes (1): Pipeline Requirements

### Community 122 - "Community 122"
Cohesion: 1.0
Nodes (1): Run Summary

### Community 123 - "Community 123"
Cohesion: 1.0
Nodes (1): Streamlit App Standards

### Community 124 - "Community 124"
Cohesion: 1.0
Nodes (1): ViSTA-SLAM Requirements

### Community 125 - "Community 125"
Cohesion: 1.0
Nodes (1): pybind11 Conduit README

### Community 126 - "Community 126"
Cohesion: 1.0
Nodes (1): DBoW3 License

### Community 127 - "Community 127"
Cohesion: 1.0
Nodes (1): Challenge 5: Uncalibrated Monocular VSLAM

### Community 128 - "Community 128"
Cohesion: 1.0
Nodes (1): Update Meeting Template

### Community 129 - "Community 129"
Cohesion: 1.0
Nodes (1): HM Hochschule München Logo

### Community 130 - "Community 130"
Cohesion: 1.0
Nodes (1): Pipeline Session State

### Community 131 - "Community 131"
Cohesion: 1.0
Nodes (1): Pipeline Request Sequence

### Community 132 - "Community 132"
Cohesion: 1.0
Nodes (1): Pipeline Request Flow

### Community 133 - "Community 133"
Cohesion: 1.0
Nodes (1): Lucas Profile Image

### Community 134 - "Community 134"
Cohesion: 1.0
Nodes (1): Valentin Profile Image

### Community 135 - "Community 135"
Cohesion: 1.0
Nodes (1): Julian Profile Image

### Community 136 - "Community 136"
Cohesion: 1.0
Nodes (1): Christoph Profile Image

### Community 137 - "Community 137"
Cohesion: 1.0
Nodes (1): Felix Profile Image

### Community 138 - "Community 138"
Cohesion: 1.0
Nodes (1): TUM-RGBD Room Reconstruction

### Community 139 - "Community 139"
Cohesion: 1.0
Nodes (1): VISTA-SLAM Logo

### Community 140 - "Community 140"
Cohesion: 1.0
Nodes (1): 7Scenes Office Reconstruction

### Community 141 - "Community 141"
Cohesion: 1.0
Nodes (1): BF Office 0 Reconstruction

### Community 142 - "Community 142"
Cohesion: 1.0
Nodes (1): 7Scenes Red Kitchen Reconstruction

### Community 143 - "Community 143"
Cohesion: 1.0
Nodes (1): TUM-RGBD Floor Reconstruction

### Community 144 - "Community 144"
Cohesion: 1.0
Nodes (1): BF Apt 1 Reconstruction

### Community 145 - "Community 145"
Cohesion: 1.0
Nodes (1): VISTA-SLAM Teaser 2

### Community 146 - "Community 146"
Cohesion: 1.0
Nodes (1): ScanNet 0054 Reconstruction

### Community 147 - "Community 147"
Cohesion: 1.0
Nodes (1): ScanNet 0000 Reconstruction

### Community 148 - "Community 148"
Cohesion: 1.0
Nodes (1): Record3D

### Community 149 - "Community 149"
Cohesion: 1.0
Nodes (1): ADVIO Dataset

### Community 150 - "Community 150"
Cohesion: 1.0
Nodes (1): evo

### Community 151 - "Community 151"
Cohesion: 1.0
Nodes (1): SlamUpdate

### Community 152 - "Community 152"
Cohesion: 1.0
Nodes (1): SlamArtifacts

### Community 153 - "Community 153"
Cohesion: 1.0
Nodes (1): pybind11 Chrono Conversions

### Community 154 - "Community 154"
Cohesion: 1.0
Nodes (1): pybind11 String and Unicode Conversions

### Community 155 - "Community 155"
Cohesion: 1.0
Nodes (1): pybind11 Custom Type Casters

### Community 156 - "Community 156"
Cohesion: 1.0
Nodes (1): pybind11 Functional/Callback Support

### Community 157 - "Community 157"
Cohesion: 1.0
Nodes (1): pybind11 Test Requirements

### Community 158 - "Community 158"
Cohesion: 1.0
Nodes (1): pybind11 CMake Build Test Root

### Community 159 - "Community 159"
Cohesion: 1.0
Nodes (1): test_installed_embed

### Community 160 - "Community 160"
Cohesion: 1.0
Nodes (1): test_subdirectory_embed

### Community 161 - "Community 161"
Cohesion: 1.0
Nodes (1): test_installed_target

### Community 162 - "Community 162"
Cohesion: 1.0
Nodes (1): test_installed_function

### Community 163 - "Community 163"
Cohesion: 1.0
Nodes (1): test_subdirectory_function

### Community 164 - "Community 164"
Cohesion: 1.0
Nodes (1): test_subdirectory_target

### Community 165 - "Community 165"
Cohesion: 1.0
Nodes (1): MethodId

### Community 166 - "Community 166"
Cohesion: 1.0
Nodes (1): RunState

## Ambiguous Edges - Review These
- `normalize_grayscale_image` → `PacketSessionSnapshot`  [AMBIGUOUS]
  src/prml_vslam/utils/image_utils.py · relation: conceptually_related_to

## Knowledge Gaps
- **552 isolated node(s):** `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`, `Protocols Package Public API`, `Thin visualization-policy contracts.`, `Explicit baseline selection for trajectory evaluation.`, `Policy toggle for the optional reference-reconstruction stage.` (+547 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 85`** (2 nodes): `streamlit_app.py`, `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 86`** (2 nodes): `Capture Manifest`, `Frame Sample`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 87`** (2 nodes): `ImageSize.from_payload`, `ImageSize Model`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 88`** (2 nodes): `test_cli.py`, `test_record3d_devices_command_runs()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 89`** (2 nodes): `cam_test.py`, `main()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 90`** (2 nodes): `Rationale: Centralize Generic Helpers`, `Shared Utils Infrastructure Scope`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 91`** (2 nodes): `PathConfig Ownership Requirement`, `Rationale: Inject PathConfig For Determinism`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 92`** (2 nodes): `Rationale: Avoid Hidden Side Effects`, `Small Predictable Utilities Requirement`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 93`** (2 nodes): `py::module_local`, `Rationale for py::module_local`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 94`** (2 nodes): `Rationale: Avoid raw pointers for objects managed by smart pointers`, `pybind11 Smart Pointer Support`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 95`** (2 nodes): `Rationale: Data copying overhead in type conversions`, `pybind11 Type Conversions`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 96`** (2 nodes): `pybind11 Test Suite CMake Configuration`, `pybind11 Embedding Test CMake`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 97`** (2 nodes): `FakeRecord3DStream`, `OfflineSequenceSource`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 98`** (1 nodes): `Return the upstream method name shown to users.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 99`** (1 nodes): `Record3D Transport Id`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 100`** (1 nodes): `Build the canonical artifact layout from an explicit root.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 101`** (1 nodes): `Validate that the configured repository root exists.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 102`** (1 nodes): `Resolve configured directories against the repository root.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 103`** (1 nodes): `Resolve a path relative to the configured repository root.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 104`** (1 nodes): `Resolve a directory and optionally create it.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 105`** (1 nodes): `Build a transform from a 4x4 homogeneous matrix.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 106`** (1 nodes): `App Lazy Entrypoint`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 107`** (1 nodes): `make_changelog.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 108`** (1 nodes): `libsize.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 109`** (1 nodes): `test_eval_call.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 110`** (1 nodes): `The CXX standard level. If set, will add the required flags. If left at`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 111`** (1 nodes): `Build one spec from one JSON object.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 112`** (1 nodes): `Claude-Specific Guidance`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 113`** (1 nodes): `AGENTS Repo Policy`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 114`** (1 nodes): `Gemini-Specific Guidance`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 115`** (1 nodes): `Questions.md Ground Truth`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 116`** (1 nodes): `WP 1: Video Source`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 117`** (1 nodes): `WP 2: Pipeline Framework`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 118`** (1 nodes): `WP 3: Uncalibrated Monocular VSLAM Methods`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 119`** (1 nodes): `FramePacket`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 120`** (1 nodes): `Benchmark Requirements`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 121`** (1 nodes): `Pipeline Requirements`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 122`** (1 nodes): `Run Summary`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 123`** (1 nodes): `Streamlit App Standards`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 124`** (1 nodes): `ViSTA-SLAM Requirements`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 125`** (1 nodes): `pybind11 Conduit README`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 126`** (1 nodes): `DBoW3 License`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 127`** (1 nodes): `Challenge 5: Uncalibrated Monocular VSLAM`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 128`** (1 nodes): `Update Meeting Template`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 129`** (1 nodes): `HM Hochschule München Logo`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 130`** (1 nodes): `Pipeline Session State`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 131`** (1 nodes): `Pipeline Request Sequence`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 132`** (1 nodes): `Pipeline Request Flow`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 133`** (1 nodes): `Lucas Profile Image`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 134`** (1 nodes): `Valentin Profile Image`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 135`** (1 nodes): `Julian Profile Image`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 136`** (1 nodes): `Christoph Profile Image`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 137`** (1 nodes): `Felix Profile Image`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 138`** (1 nodes): `TUM-RGBD Room Reconstruction`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 139`** (1 nodes): `VISTA-SLAM Logo`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 140`** (1 nodes): `7Scenes Office Reconstruction`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 141`** (1 nodes): `BF Office 0 Reconstruction`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 142`** (1 nodes): `7Scenes Red Kitchen Reconstruction`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 143`** (1 nodes): `TUM-RGBD Floor Reconstruction`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 144`** (1 nodes): `BF Apt 1 Reconstruction`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 145`** (1 nodes): `VISTA-SLAM Teaser 2`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 146`** (1 nodes): `ScanNet 0054 Reconstruction`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 147`** (1 nodes): `ScanNet 0000 Reconstruction`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 148`** (1 nodes): `Record3D`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 149`** (1 nodes): `ADVIO Dataset`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 150`** (1 nodes): `evo`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 151`** (1 nodes): `SlamUpdate`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 152`** (1 nodes): `SlamArtifacts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 153`** (1 nodes): `pybind11 Chrono Conversions`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 154`** (1 nodes): `pybind11 String and Unicode Conversions`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 155`** (1 nodes): `pybind11 Custom Type Casters`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 156`** (1 nodes): `pybind11 Functional/Callback Support`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 157`** (1 nodes): `pybind11 Test Requirements`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 158`** (1 nodes): `pybind11 CMake Build Test Root`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 159`** (1 nodes): `test_installed_embed`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 160`** (1 nodes): `test_subdirectory_embed`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 161`** (1 nodes): `test_installed_target`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 162`** (1 nodes): `test_installed_function`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 163`** (1 nodes): `test_subdirectory_function`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 164`** (1 nodes): `test_subdirectory_target`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 165`** (1 nodes): `MethodId`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 166`** (1 nodes): `RunState`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `normalize_grayscale_image` and `PacketSessionSnapshot`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `OnlineSLAM` connect `Community 5` to `Community 9`, `Community 34`, `Community 35`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Why does `PathConfig` connect `Community 4` to `Community 33`, `Community 2`, `Community 5`?**
  _High betweenness centrality (0.023) - this node is a cross-community bridge._
- **Why does `Visualization contracts and Rerun helpers.` connect `Community 5` to `Community 1`, `Community 2`, `Community 11`?**
  _High betweenness centrality (0.017) - this node is a cross-community bridge._
- **Are the 124 inferred relationships involving `SequenceManifest` (e.g. with `OfflineSequenceSource` and `StreamingSequenceSource`) actually correct?**
  _`SequenceManifest` has 124 INFERRED edges - model-reasoned connections that need verification._
- **Are the 99 inferred relationships involving `SlamArtifacts` (e.g. with `MockSlamBackendConfig` and `MockSlamBackend`) actually correct?**
  _`SlamArtifacts` has 99 INFERRED edges - model-reasoned connections that need verification._
- **Are the 93 inferred relationships involving `MethodId` (e.g. with `MockSlamBackendConfig` and `MockSlamBackend`) actually correct?**
  _`MethodId` has 93 INFERRED edges - model-reasoned connections that need verification._