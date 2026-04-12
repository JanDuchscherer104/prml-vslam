# Graph Report - .  (2026-04-12)

## Corpus Check
- 417 files · ~39,277,768 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 3667 nodes · 7318 edges · 86 communities detected
- Extraction: 67% EXTRACTED · 33% INFERRED · 0% AMBIGUOUS · INFERRED: 2444 edges (avg confidence: 0.51)
- Token cost: 0 input · 0 output

## God Nodes (most connected - your core abstractions)
1. `SequenceManifest` - 130 edges
2. `RunState` - 93 edges
3. `MethodId` - 92 edges
4. `RunPlan` - 91 edges
5. `SlamArtifacts` - 90 edges
6. `RunSnapshot` - 82 edges
7. `SlamOutputPolicy` - 76 edges
8. `SlamBackendConfig` - 76 edges
9. `RunService` - 69 edges
10. `DatasetSourceSpec` - 69 edges

## Surprising Connections (you probably didn't know these)
- `FakeRecord3DStream` --uses--> `OfflineSequenceSource`  [INFERRED]
  tests/test_record3d.py → src/prml_vslam/protocols/source.py
- `Tests for the optional Record3D USB integration.` --uses--> `OfflineSequenceSource`  [INFERRED]
  tests/test_record3d.py → src/prml_vslam/protocols/source.py
- `Small in-memory stand-in for the upstream Record3D bindings.` --uses--> `OfflineSequenceSource`  [INFERRED]
  tests/test_record3d.py → src/prml_vslam/protocols/source.py
- `Tests for the Python-side Record3D Wi-Fi transport.` --uses--> `OfflineSequenceSource`  [INFERRED]
  tests/test_record3d_wifi.py → src/prml_vslam/protocols/source.py
- `FakeRecord3DStream` --uses--> `StreamingSequenceSource`  [INFERRED]
  tests/test_record3d.py → src/prml_vslam/protocols/source.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.03
Nodes (239): _build_artifacts(), _build_live_pointmap(), _count_valid_pointmap_points(), Canonical ViSTA-SLAM backend adapter (offline + streaming)., ViSTA-SLAM backend implementing offline and streaming contracts., Load upstream OnlineSLAM and return a ready streaming session., Run ViSTA-SLAM over a materialized sequence and persist artifacts., Raise a runtime error with actionable detail when dependencies are missing. (+231 more)

### Community 1 - "Community 1"
Cohesion: 0.01
Nodes (95): get(), value(), deprecated_call(), pytest.deprecated_call() seems broken in pytest<3.9.x; concretely, it     doesn', # TODO: Remove this when testing requires pytest>=3.9., bind_ConstructorStats(), cpp_std(), PYBIND11_MODULE() (+87 more)

### Community 2 - "Community 2"
Cohesion: 0.01
Nodes (99): AriaSynthetic, ARKitScene, convert traj_string into translation and rotation matrices         Args:, BaseViewGraphDataset, is_good_type(), This function:             - first downsizes the image with LANCZOS inteprolatio, This function:             - first downsizes the image with LANCZOS inteprolatio, Define all basic options.      Usage:         class MyDataset (BaseStereoViewDat (+91 more)

### Community 3 - "Community 3"
Cohesion: 0.03
Nodes (188): ADVIO Page Controller Actions, ADVIO Dataset Page Renderer, Pipeline artifact contracts., BaseData, AppContext, build_context(), _build_pages(), _enter_page() (+180 more)

### Community 4 - "Community 4"
Cohesion: 0.02
Nodes (74): multiple_values_error(), nameless_argument_error(), process(), instance_simple_holder_in_ptrs(), size_in_ptrs(), is_instance_method_of_type(), try_get_cpp_conduit_method(), try_raw_pointer_ephemeral_from_cpp_conduit() (+66 more)

### Community 5 - "Community 5"
Cohesion: 0.01
Nodes (48): clear_instance(), enable_dynamic_attributes(), get_fully_qualified_tp_name(), make_default_metaclass(), make_object_base_type(), make_static_property_type(), pybind11_meta_call(), pybind11_object_dealloc() (+40 more)

### Community 6 - "Community 6"
Cohesion: 0.02
Nodes (68): add(), BoWFrame(), CmdLineParser, loadFeatures(), main(), readImagePaths(), saveToFile(), CmdLineParser (+60 more)

### Community 7 - "Community 7"
Cohesion: 0.02
Nodes (13): CustomContains, float_, get_annotations_helper(), m_defs(), C++ default and converting constructors are equivalent to type calls in Python, Tests implicit casting when assigning or appending to dicts and lists., test_class_attribute_types(), test_constructors() (+5 more)

### Community 8 - "Community 8"
Cohesion: 0.03
Nodes (43): collate_with_cat(), listify(), MyNvtxRange, Transfer some variables to another device (i.e. GPU, CPU:torch, CPU:numpy)., to_cpu(), to_cuda(), to_numpy(), todevice() (+35 more)

### Community 9 - "Community 9"
Cohesion: 0.02
Nodes (40): adjust_learning_rate(), all_reduce_mean(), filename(), get_grad_norm_(), _get_num_layer_for_vit(), get_parameter_groups(), get_rank(), get_world_size() (+32 more)

### Community 10 - "Community 10"
Cohesion: 0.05
Nodes (60): AdvioDownloadManager, ADVIO Package Public API, ADVIO Catalog Loader, ADVIO Modality Path Specs, ADVIO Reference Path Resolver, AdvioCalibration, _expect_float_list(), _expect_mapping() (+52 more)

### Community 11 - "Community 11"
Cohesion: 0.03
Nodes (38): PythonMyException7, Exception, CustomData(), FlakyException, MyException, MyException2, MyException3, MyException4 (+30 more)

### Community 12 - "Community 12"
Cohesion: 0.04
Nodes (40): Criterion, count_stats(), extract_markers(), main(), MarkerEntry, parse_args(), Compute Python line-of-code statistics for src/ and tests/., Render a detailed Rich table for one marker kind. (+32 more)

### Community 13 - "Community 13"
Cohesion: 0.04
Nodes (35): FlowTracker, PoseGraphEdges, PoseGraphNodes, PoseGraphOpt, PoseGraphOptAll, add a node to the pose graph.          Notice that the absolute pose of the node, attach_file_sink(), attach_grpc_sink() (+27 more)

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
Cohesion: 0.07
Nodes (15): NonCopyableInt, NonRefIterator, NonZeroIterator, NonZeroSentinel, #2076: Exception raised by len(arg) should be propagated, #181: iterator passthrough did not compile, #388: Can't make iterators via make_iterator() with different r/v policies, #4100: Check for proper iterator overload with C-Arrays (+7 more)

### Community 29 - "Community 29"
Cohesion: 0.06
Nodes (12): Mixing bases with and without static properties should be possible     and the r, Mixing bases with and without dynamic attribute support, Returning an offset (non-first MI) base class pointer should recognize the insta, Tests returning an offset (non-first MI) base class pointer to a derived instanc, Tests that diamond inheritance works as expected (issue #959), Tests extending a Python class from a single inheritor of a MI class, test_diamond_inheritance(), test_mi_base_return() (+4 more)

### Community 30 - "Community 30"
Cohesion: 0.09
Nodes (9): assert_equal(), dt_fmt(), packed_dtype_fmt(), partial_dtype_fmt(), partial_ld_offset(), partial_nested_fmt(), simple_dtype_fmt(), test_dtype() (+1 more)

### Community 31 - "Community 31"
Cohesion: 0.09
Nodes (26): str, DataOnlyConfig, InvalidTargetConfig, NestedPayload, PlainPayload, Tests for the shared Pydantic base-model split., Runtime object used to verify default setup behavior., Config whose runtime target is constructed via ``target_type``. (+18 more)

### Community 32 - "Community 32"
Cohesion: 0.09
Nodes (8): cast(), localtime_thread_safe(), IntStruct(), test_bind_shared_instance(), test_implicit_conversion(), test_implicit_conversion_no_gil(), TEST_SUBMODULE(), Thread

### Community 33 - "Community 33"
Cohesion: 0.16
Nodes (17): DenseCloudEvaluationArtifact, DiscoveredRun, EfficiencyEvaluationArtifact, EvaluationArtifact, EvaluationSelection, TrajectoryEvaluationService Export, DenseCloudEvaluator Protocol, EfficiencyEvaluator Protocol (+9 more)

### Community 34 - "Community 34"
Cohesion: 0.17
Nodes (24): _build_fake_catalog(), Tests for the simplified ADVIO adapter and replay stream., test_advio_dataset_service_downloads_selected_modalities_from_cached_archive(), test_advio_dataset_service_handles_official_archive_layout(), test_advio_dataset_service_lists_and_loads_local_sequences(), test_advio_dataset_service_offline_preset_downloads_evaluation_ready_bundle(), test_advio_dataset_service_refreshes_corrupted_cached_archive(), test_advio_dataset_service_summarize_reuses_precomputed_statuses() (+16 more)

### Community 35 - "Community 35"
Cohesion: 0.09
Nodes (6): E_nc, El, times_hundred(), times_ten(), UserMapLike, UserVectorLike

### Community 36 - "Community 36"
Cohesion: 0.1
Nodes (11): accum_dist(), CArray, findNeighbors(), KDTreeEigenMatrixAdaptor(), KDTreeSingleIndexAdaptor, KDTreeSingleIndexAdaptorParams(), KNNResultSet, PooledAllocator (+3 more)

### Community 37 - "Community 37"
Cohesion: 0.13
Nodes (22): ArxivSourceSpec, download_file(), fetch_pdf(), fetch_tex_source(), from_json(), load_manifest(), main(), normalize_member_path() (+14 more)

### Community 38 - "Community 38"
Cohesion: 0.11
Nodes (6): FakeRecord3DStream, Tests for the optional Record3D USB integration., Small in-memory stand-in for the upstream Record3D bindings., test_record3d_stream_wait_for_packet_returns_shared_contract(), test_usb_packet_stream_disconnect_stops_active_stream(), test_usb_packet_stream_wait_for_packet_returns_shared_contract()

### Community 39 - "Community 39"
Cohesion: 0.16
Nodes (16): build_stage_manifests(), build_stage_status(), build_summary_manifest(), finalize_run_outputs(), stable_hash(), write_json(), _copy_if_needed(), _emit_progress() (+8 more)

### Community 40 - "Community 40"
Cohesion: 0.14
Nodes (21): Build ADVIO Crowd Density Figure, Build ADVIO Local Readiness Figure, Build ADVIO Scene Attribute Figure, Build ADVIO Scene Mix Figure, Build Metrics Error Figure, Build Metrics Trajectory Figure, Build Evo APE Colormap Figure, Plotting Package Public API (+13 more)

### Community 41 - "Community 41"
Cohesion: 0.14
Nodes (5): _build_runtime(), Tests for the Python-side Record3D Wi-Fi transport., test_record3d_wifi_closed_after_connect_logs_runtime_failure(), test_record3d_wifi_closed_before_track_sets_setup_failure_without_logging(), test_record3d_wifi_metadata_failure_is_non_fatal()

### Community 42 - "Community 42"
Cohesion: 0.24
Nodes (12): fast_read(), hash_func(), hashat(), memcpy_up(), qlz_decompress(), qlz_decompress_core(), qlz_size_compressed(), qlz_size_decompressed() (+4 more)

### Community 43 - "Community 43"
Cohesion: 0.15
Nodes (9): chamfer_distance_RMSE(), eval_recon(), eval_recon_from_saved_data(), load_data(), gt_depths: N,H,W     gt_poses: N,4,4     gt_intri: 3,3     est_local_pcls: N,H,W, rel_gt_est: None or [R, t, s] for the relative pose between the ground truth and, transform_to_world_coordinates(), test_mock_slam_backend_runs_sequence_manifest_offline() (+1 more)

### Community 44 - "Community 44"
Cohesion: 0.15
Nodes (1): Tests for centralized repository path handling.

### Community 45 - "Community 45"
Cohesion: 0.15
Nodes (12): build(), docs(), lint(), make_changelog(), Lint the codebase (except for clang-format/tidy)., Run the tests (requires a compiler)., Run the packaging tests., Build the docs. Pass --non-interactive to avoid serving. (+4 more)

### Community 46 - "Community 46"
Cohesion: 0.25
Nodes (10): Base Config Model, Normalize Config Value Helper, Caller Namespace Resolver, Console Wrapper, Typed layout for one planned benchmark run., Return the canonical Plotly scene path for one method run., RunArtifactPaths, Base Data Model (+2 more)

### Community 47 - "Community 47"
Cohesion: 0.24
Nodes (9): build_advio_demo_request(), load_run_request_toml(), persist_advio_demo_request(), Shared helpers for the bounded ADVIO pipeline demo., Build the canonical bounded ADVIO demo request shared by app and CLI., Load a pipeline request TOML through the repo-owned config path helper., Persist a pipeline request TOML through the repo-owned config path helper., Persist the canonical ADVIO demo request under `.configs/pipelines/` by default. (+1 more)

### Community 48 - "Community 48"
Cohesion: 0.22
Nodes (3): _fake_advio_service(), Focused CLI tests for ADVIO dataset commands., test_advio_download_command_builds_explicit_request()

### Community 49 - "Community 49"
Cohesion: 0.22
Nodes (5): Dataset-edge frame-graph helpers., Thin wrapper around `pytransform3d.TransformManager` for static frame compositio, Register one static transform., Resolve one composed transform back into the repo-owned transform DTO., StaticFrameGraph

### Community 50 - "Community 50"
Cohesion: 0.29
Nodes (8): Decode Record3D Wi-Fi Depth, Record3D Wi-Fi Metadata, Record3D Wi-Fi Packet From Video Frame, Record3D Wi-Fi Receiver Runtime, Open Record3D Wi-Fi Preview Stream, Record3D Wi-Fi Preview Stream Session, Record3D Wi-Fi Signaling Client, Build Record3D Answer Request Payload

### Community 51 - "Community 51"
Cohesion: 0.39
Nodes (5): _ingest_summary(), _method_summary(), _stage_from_spec(), _trajectory_summary(), _validate_request()

### Community 52 - "Community 52"
Cohesion: 0.48
Nodes (4): normalize_line_endings(), read_tz_file(), test_build_global_dist(), test_build_sdist()

### Community 53 - "Community 53"
Cohesion: 0.33
Nodes (3): Return the normalized quaternion in XYZW order., Return the translation vector in XYZ order., Return the transform as a 4x4 matrix.

### Community 54 - "Community 54"
Cohesion: 0.7
Nodes (4): _artifact_ref(), import_vista_artifacts(), _optional_existing_path(), _require_existing_path()

### Community 55 - "Community 55"
Cohesion: 0.4
Nodes (1): Tests for package-root public export surfaces.

### Community 56 - "Community 56"
Cohesion: 0.4
Nodes (0):

### Community 57 - "Community 57"
Cohesion: 0.5
Nodes (3): native_rerun_artifact(), Helpers for preserved native ViSTA Rerun recordings., Return a preserved native `.rrd` artifact when one exists.

### Community 58 - "Community 58"
Cohesion: 0.67
Nodes (4): FramePacketStream Protocol, PacketSessionRuntime.finalize, PacketSessionRuntime.launch, PacketSessionRuntime.stop

### Community 59 - "Community 59"
Cohesion: 0.5
Nodes (0):

### Community 60 - "Community 60"
Cohesion: 1.0
Nodes (3): Open Record3D USB Packet Stream, Record3D Stream Config, Record3D USB Packet Stream

### Community 61 - "Community 61"
Cohesion: 0.67
Nodes (3): Cv2 Producer Config, Cv2 Frame Producer, Open Cv2 Replay Stream

### Community 62 - "Community 62"
Cohesion: 1.0
Nodes (2): gen(), video()

### Community 63 - "Community 63"
Cohesion: 0.67
Nodes (1): Simple script for rebuilding .codespell-ignore-lines  Usage:  cat < /dev/null >

### Community 64 - "Community 64"
Cohesion: 0.67
Nodes (0):

### Community 65 - "Community 65"
Cohesion: 0.67
Nodes (0):

### Community 66 - "Community 66"
Cohesion: 0.67
Nodes (2): imread_cv2(), Open an image or a depthmap with opencv-python.

### Community 67 - "Community 67"
Cohesion: 1.0
Nodes (1): Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays

### Community 68 - "Community 68"
Cohesion: 1.0
Nodes (2): Capture Manifest, Frame Sample

### Community 69 - "Community 69"
Cohesion: 1.0
Nodes (2): ImageSize.from_payload, ImageSize Model

### Community 70 - "Community 70"
Cohesion: 1.0
Nodes (0):

### Community 71 - "Community 71"
Cohesion: 1.0
Nodes (0):

### Community 72 - "Community 72"
Cohesion: 1.0
Nodes (1): Return the upstream method name shown to users.

### Community 73 - "Community 73"
Cohesion: 1.0
Nodes (1): Record3D Transport Id

### Community 74 - "Community 74"
Cohesion: 1.0
Nodes (1): Build the canonical artifact layout from an explicit root.

### Community 75 - "Community 75"
Cohesion: 1.0
Nodes (1): Validate that the configured repository root exists.

### Community 76 - "Community 76"
Cohesion: 1.0
Nodes (1): Resolve configured directories against the repository root.

### Community 77 - "Community 77"
Cohesion: 1.0
Nodes (1): Resolve a path relative to the configured repository root.

### Community 78 - "Community 78"
Cohesion: 1.0
Nodes (1): Resolve a directory and optionally create it.

### Community 79 - "Community 79"
Cohesion: 1.0
Nodes (1): Build a transform from a 4x4 homogeneous matrix.

### Community 80 - "Community 80"
Cohesion: 1.0
Nodes (1): App Lazy Entrypoint

### Community 81 - "Community 81"
Cohesion: 1.0
Nodes (0):

### Community 82 - "Community 82"
Cohesion: 1.0
Nodes (0):

### Community 83 - "Community 83"
Cohesion: 1.0
Nodes (0):

### Community 84 - "Community 84"
Cohesion: 1.0
Nodes (1): The CXX standard level. If set, will add the required flags. If left at

### Community 85 - "Community 85"
Cohesion: 1.0
Nodes (1): Build one spec from one JSON object.

## Ambiguous Edges - Review These
- `normalize_grayscale_image` → `PacketSessionSnapshot`  [AMBIGUOUS]
  src/prml_vslam/utils/image_utils.py · relation: conceptually_related_to

## Knowledge Gaps
- **383 isolated node(s):** `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`, `Protocols Package Public API`, `Thin visualization-policy contracts.`, `Explicit baseline selection for trajectory evaluation.`, `Policy toggle for the optional reference-reconstruction stage.` (+378 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 67`** (2 nodes): `streamlit_app.py`, `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 68`** (2 nodes): `Capture Manifest`, `Frame Sample`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 69`** (2 nodes): `ImageSize.from_payload`, `ImageSize Model`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 70`** (2 nodes): `test_cli.py`, `test_record3d_devices_command_runs()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 71`** (2 nodes): `cam_test.py`, `main()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 72`** (1 nodes): `Return the upstream method name shown to users.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 73`** (1 nodes): `Record3D Transport Id`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 74`** (1 nodes): `Build the canonical artifact layout from an explicit root.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 75`** (1 nodes): `Validate that the configured repository root exists.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 76`** (1 nodes): `Resolve configured directories against the repository root.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 77`** (1 nodes): `Resolve a path relative to the configured repository root.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 78`** (1 nodes): `Resolve a directory and optionally create it.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 79`** (1 nodes): `Build a transform from a 4x4 homogeneous matrix.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 80`** (1 nodes): `App Lazy Entrypoint`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 81`** (1 nodes): `make_changelog.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 82`** (1 nodes): `libsize.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 83`** (1 nodes): `test_eval_call.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 84`** (1 nodes): `The CXX standard level. If set, will add the required flags. If left at`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 85`** (1 nodes): `Build one spec from one JSON object.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `normalize_grayscale_image` and `PacketSessionSnapshot`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `OnlineSLAM` connect `Community 13` to `Community 0`, `Community 8`, `Community 2`?**
  _High betweenness centrality (0.031) - this node is a cross-community bridge._
- **Why does `PathConfig` connect `Community 3` to `Community 0`, `Community 33`, `Community 46`?**
  _High betweenness centrality (0.025) - this node is a cross-community bridge._
- **Why does `SequenceManifest` connect `Community 0` to `Community 10`, `Community 3`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **Are the 127 inferred relationships involving `SequenceManifest` (e.g. with `OfflineSequenceSource` and `StreamingSequenceSource`) actually correct?**
  _`SequenceManifest` has 127 INFERRED edges - model-reasoned connections that need verification._
- **Are the 90 inferred relationships involving `RunState` (e.g. with `CLI entry point for the project scaffold.` and `Print a short summary of the current scaffold.`) actually correct?**
  _`RunState` has 90 INFERRED edges - model-reasoned connections that need verification._
- **Are the 89 inferred relationships involving `MethodId` (e.g. with `MockSlamBackendConfig` and `MockSlamBackend`) actually correct?**
  _`MethodId` has 89 INFERRED edges - model-reasoned connections that need verification._