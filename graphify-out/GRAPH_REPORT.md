# Graph Report - .  (2026-04-11)

## Corpus Check
- 412 files · ~39,305,908 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 3143 nodes · 4493 edges · 80 communities detected
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 331 edges (avg confidence: 0.56)
- Token cost: 0 input · 0 output

## God Nodes (most connected - your core abstractions)
1. `BaseViewGraphDataset` - 30 edges
2. `normalize_grayscale_image` - 25 edges
3. `OnlineSLAM` - 25 edges
4. `FakeStore` - 22 edges
5. `ptr()` - 22 edges
6. `PathConfig` - 20 edges
7. `SymmetricTwoViewAssociation` - 20 edges
8. `load_tum_trajectory` - 19 edges
9. `_write_advio_sequence()` - 18 edges
10. `MultiLoss` - 17 edges

## Surprising Connections (you probably didn't know these)
- `VistaSlamBackend` --uses--> `OnlineSLAM`  [INFERRED]
  src/prml_vslam/methods/vista_slam/runner.py → external/vista-slam/vista_slam/slam.py
- `VistaSlamSession` --uses--> `OnlineSLAM`  [INFERRED]
  src/prml_vslam/methods/vista_slam/runner.py → external/vista-slam/vista_slam/slam.py
- `FakeStore` --uses--> `normalize_grayscale_image`  [INFERRED]
  tests/test_app.py → src/prml_vslam/utils/image_utils.py
- `FakeRecord3DRuntime` --uses--> `normalize_grayscale_image`  [INFERRED]
  tests/test_app.py → src/prml_vslam/utils/image_utils.py
- `FakeAdvioRuntime` --uses--> `normalize_grayscale_image`  [INFERRED]
  tests/test_app.py → src/prml_vslam/utils/image_utils.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.01
Nodes (81): AriaSynthetic, ARKitScene, convert traj_string into translation and rotation matrices         Args:, BaseViewGraphDataset, is_good_type(), This function:             - first downsizes the image with LANCZOS inteprolatio, This function:             - first downsizes the image with LANCZOS inteprolatio, Define all basic options.      Usage:         class MyDataset (BaseStereoViewDat (+73 more)

### Community 1 - "Community 1"
Cohesion: 0.01
Nodes (64): get(), value(), deprecated_call(), pytest.deprecated_call() seems broken in pytest<3.9.x; concretely, it     doesn', # TODO: Remove this when testing requires pytest>=3.9., bind_ConstructorStats(), cpp_std(), PYBIND11_MODULE() (+56 more)

### Community 2 - "Community 2"
Cohesion: 0.01
Nodes (36): clear_instance(), enable_dynamic_attributes(), get_fully_qualified_tp_name(), make_default_metaclass(), make_object_base_type(), make_static_property_type(), pybind11_meta_call(), pybind11_object_dealloc() (+28 more)

### Community 3 - "Community 3"
Cohesion: 0.02
Nodes (59): add(), BoWFrame(), CmdLineParser, loadFeatures(), main(), readImagePaths(), saveToFile(), CmdLineParser (+51 more)

### Community 4 - "Community 4"
Cohesion: 0.02
Nodes (42): multiple_values_error(), nameless_argument_error(), process(), instance_simple_holder_in_ptrs(), size_in_ptrs(), is_instance_method_of_type(), try_get_cpp_conduit_method(), try_raw_pointer_ephemeral_from_cpp_conduit() (+34 more)

### Community 5 - "Community 5"
Cohesion: 0.02
Nodes (13): CustomContains, float_, get_annotations_helper(), m_defs(), C++ default and converting constructors are equivalent to type calls in Python, Tests implicit casting when assigning or appending to dicts and lists., test_class_attribute_types(), test_constructors() (+5 more)

### Community 6 - "Community 6"
Cohesion: 0.03
Nodes (43): collate_with_cat(), listify(), MyNvtxRange, Transfer some variables to another device (i.e. GPU, CPU:torch, CPU:numpy)., to_cpu(), to_cuda(), to_numpy(), todevice() (+35 more)

### Community 7 - "Community 7"
Cohesion: 0.04
Nodes (81): MetricStats, CameraIntrinsics Contract, Homogeneous Transform Operations, load_tum_trajectory, Open3D Point Cloud IO, pointmap_from_depth, PoseTrajectory3D Representation, SE3Pose Contract (+73 more)

### Community 8 - "Community 8"
Cohesion: 0.04
Nodes (60): get_path_config, PathConfig, PathConfig.plan_run_paths, PathConfig.slugify_experiment_name, RunArtifactPaths, RunArtifactPaths.build, _build_path_config(), FakeAdvioRuntime (+52 more)

### Community 9 - "Community 9"
Cohesion: 0.03
Nodes (38): convert_anyset(), convert_elements(), convert_iterable(), load(), PyObjectTypeIsConvertibleToStdMap(), PyObjectTypeIsConvertibleToStdVector(), reserve_maybe(), Load a `py::module_local` type that's only registered in an external module (+30 more)

### Community 10 - "Community 10"
Cohesion: 0.04
Nodes (28): FlowTracker, LoopDetector, PoseGraphEdges, PoseGraphNodes, PoseGraphOpt, PoseGraphOptAll, add a node to the pose graph.          Notice that the absolute pose of the node, LatestCamera (+20 more)

### Community 11 - "Community 11"
Cohesion: 0.03
Nodes (26): Args, BreaksBase, BreaksTramp, Chimera, Dog, ForwardClass, Hamster, Pet (+18 more)

### Community 12 - "Community 12"
Cohesion: 0.04
Nodes (37): advance(), bytearray(), bytes(), capsule(), clear(), delattr(), dict_getitemstring(), dict_getitemstringref() (+29 more)

### Community 13 - "Community 13"
Cohesion: 0.04
Nodes (35): build_ext, cuRoPE2D, cuRoPE2D_func, rope_2d(), rope_2d_cpu(), _Extension, CMakeBuild, CMakeExtension (+27 more)

### Community 14 - "Community 14"
Cohesion: 0.06
Nodes (27): Criterion, Calculate the rotation error between two batches of rotation matrices., gt_views : list of dictionaries, each containing 'pts3d' and 'valid_mask', gt_views : list of dictionaries, each containing 'pts3d' and 'valid_mask', RelPoseLoss, ReprojLoss, ConfLoss, Criterion (+19 more)

### Community 15 - "Community 15"
Cohesion: 0.04
Nodes (24): PythonMyException7, Exception, CustomData(), FlakyException, MyException, MyException2, MyException3, MyException4 (+16 more)

### Community 16 - "Community 16"
Cohesion: 0.04
Nodes (17): auxiliaries(), data(), data_t(), index_at(), index_at_t(), offset_at(), offset_at_t(), PyValueHolder (+9 more)

### Community 17 - "Community 17"
Cohesion: 0.03
Nodes (34): SquareMatrix is derived from Matrix and inherits the buffer protocol, # TODO: fix on recent PyPy, test_inherited_protocol(), Tests the ability to pass bytes to C++ string-accepting functions.  Note that th, Tests the ability to pass bytearray to C++ string-accepting functions, Tests support for C++17 string_view arguments and return values, Tests unicode conversion and error reporting., Issue #929 - out-of-range integer values shouldn't be accepted (+26 more)

### Community 18 - "Community 18"
Cohesion: 0.04
Nodes (29): FakePyMappingBadItems, FakePyMappingGenObj, FakePyMappingItemsNotCallable, FakePyMappingItemsWithArg, FakePyMappingMissingItems, FakePyMappingWithItems, OptionalProperties, pass_std_vector_int() (+21 more)

### Community 19 - "Community 19"
Cohesion: 0.08
Nodes (48): AdvioDownloadManager, ADVIO Package Public API, ADVIO Catalog Loader, ADVIO Modality Path Specs, ADVIO Reference Path Resolver, AdvioCalibration Model, ADVIO Pose TUM Writer, ADVIO Trajectory Loader (+40 more)

### Community 20 - "Community 20"
Cohesion: 0.04
Nodes (35): cast(), cast_impl(), array_copy_but_one(), assert_equal_ref(), assert_keeps_alive(), assert_sparse_equal_ref(), assign_both(), get_elem() (+27 more)

### Community 21 - "Community 21"
Cohesion: 0.06
Nodes (57): ADVIO Page Controller Actions, ADVIO Dataset Page Renderer, App Lazy Entrypoint, Base Config Model, Normalize Config Value Helper, App Bootstrap Context, Caller Namespace Resolver, Console Wrapper (+49 more)

### Community 22 - "Community 22"
Cohesion: 0.06
Nodes (25): _build_streaming_request(), ExplodingPacketStream, FakeStreamingSource, FinitePacketStream, _make_packet(), Tests for the typed pipeline planning surfaces., Packet stream that terminates with EOF after the last packet., Packet stream that keeps producing frames until the service disconnects it. (+17 more)

### Community 23 - "Community 23"
Cohesion: 0.05
Nodes (33): DPTOutputAdapter, FeatureFusionBlock_custom, Interpolate, make_fusion_block(), make_scratch(), pair(), Forward pass.         Args:             x (tensor): input         Returns:, Feature fusion block. (+25 more)

### Community 24 - "Community 24"
Cohesion: 0.05
Nodes (27): adjust_learning_rate(), all_reduce_mean(), filename(), get_grad_norm_(), _get_num_layer_for_vit(), get_parameter_groups(), get_rank(), get_world_size() (+19 more)

### Community 25 - "Community 25"
Cohesion: 0.05
Nodes (28): Capture, doc(), gc_collect(), _make_explanation(), msg(), Output, pytest_assertrepr_compare(), pytest configuration  Extends output capture as needed by pybind11: ignore const (+20 more)

### Community 26 - "Community 26"
Cohesion: 0.05
Nodes (33): ExtendedVirtClass, Makes sure there is no GIL deadlock when running in a thread.      It runs in a, Makes sure there is no GIL deadlock when running in a thread multiple times in p, Makes sure there is no GIL deadlock when running in a thread multiple times sequ, Makes sure there is no GIL deadlock when using processes.      This test is for, Makes sure that the GIL can be acquired by another module from a GIL-released st, Makes sure that the GIL can be acquired by another module from a GIL-acquired st, Makes sure that the GIL can be acquired/released by another module     from a GI (+25 more)

### Community 27 - "Community 27"
Cohesion: 0.04
Nodes (13): custom_unique_ptr, huge_unique_ptr, MyObject1, MyObject2, MyObject3, MyObject4, MyObject4a, MyObject4b (+5 more)

### Community 28 - "Community 28"
Cohesion: 0.04
Nodes (21): ExampleMandA, NoneCastTester, NoneTester, Static property getter and setters expect the type object as the their only argu, Overriding pybind11's default metaclass changes the behavior of `static_property, When returning an rvalue, the return value policy is automatically changed from, #2778: implicit casting from None to object (not pointer), #283: __str__ called on uninitialized instance when constructor arguments invali (+13 more)

### Community 29 - "Community 29"
Cohesion: 0.07
Nodes (31): create_and_destroy(), PYBIND11_OVERRIDE(), PyTF6(), PyTF7(), Tests py::init_factory() wrapper with various upcasting and downcasting returns, Tests py::init_factory() wrapper around various ways of returning the object, Tests py::init_factory() wrapper with value conversions and alias types, Tests init factory functions with dual main/alias factory functions (+23 more)

### Community 30 - "Community 30"
Cohesion: 0.07
Nodes (21): camera_matrix_of_crop(), crop_image_depthmap(), ImageList, Return a crop of the input view., Convenience class to aply the same operation to a whole set of images., Jointly rescale a (image, depthmap)          so that (out_width, out_height) >=, rescale_image_depthmap(), colmap_to_opencv_intrinsics() (+13 more)

### Community 31 - "Community 31"
Cohesion: 0.08
Nodes (11): BatchedRandomSampler, Random sampling under a constraint: each sample in the batch has the same featur, round_by(), CatDataset, EasyDataset, MulDataset, Concatenation of several datasets, a dataset that you can easily resize and combine.     Examples:     --------- (+3 more)

### Community 32 - "Community 32"
Cohesion: 0.06
Nodes (0): 

### Community 33 - "Community 33"
Cohesion: 0.09
Nodes (29): BaseConfig, BaseData, Enum, str, DataOnlyConfig, InvalidTargetConfig, NestedPayload, PlainPayload (+21 more)

### Community 34 - "Community 34"
Cohesion: 0.06
Nodes (12): Mixing bases with and without static properties should be possible     and the r, Mixing bases with and without dynamic attribute support, Returning an offset (non-first MI) base class pointer should recognize the insta, Tests returning an offset (non-first MI) base class pointer to a derived instanc, Tests that diamond inheritance works as expected (issue #959), Tests extending a Python class from a single inheritor of a MI class, test_diamond_inheritance(), test_mi_base_return() (+4 more)

### Community 35 - "Community 35"
Cohesion: 0.09
Nodes (9): assert_equal(), dt_fmt(), packed_dtype_fmt(), partial_dtype_fmt(), partial_ld_offset(), partial_nested_fmt(), simple_dtype_fmt(), test_dtype() (+1 more)

### Community 36 - "Community 36"
Cohesion: 0.07
Nodes (18): CastUnusualOpRefConstRef(), CastUnusualOpRefMovable(), CopyOnlyInt, MoveOnlyInt, MoveOrCopyInt, An object with a private `operator new` cannot be returned by value, #389: rvp::move should fall-through to copy on non-movable objects, Make sure that cast from pytype rvalue to other pytype works (+10 more)

### Community 37 - "Community 37"
Cohesion: 0.09
Nodes (8): cast(), localtime_thread_safe(), IntStruct(), test_bind_shared_instance(), test_implicit_conversion(), test_implicit_conversion_no_gil(), TEST_SUBMODULE(), Thread

### Community 38 - "Community 38"
Cohesion: 0.07
Nodes (0): 

### Community 39 - "Community 39"
Cohesion: 0.17
Nodes (24): _build_fake_catalog(), Tests for the simplified ADVIO adapter and replay stream., test_advio_dataset_service_downloads_selected_modalities_from_cached_archive(), test_advio_dataset_service_handles_official_archive_layout(), test_advio_dataset_service_lists_and_loads_local_sequences(), test_advio_dataset_service_offline_preset_downloads_evaluation_ready_bundle(), test_advio_dataset_service_refreshes_corrupted_cached_archive(), test_advio_dataset_service_summarize_reuses_precomputed_statuses() (+16 more)

### Community 40 - "Community 40"
Cohesion: 0.09
Nodes (6): E_nc, El, times_hundred(), times_ten(), UserMapLike, UserVectorLike

### Community 41 - "Community 41"
Cohesion: 0.1
Nodes (11): accum_dist(), CArray, findNeighbors(), KDTreeEigenMatrixAdaptor(), KDTreeSingleIndexAdaptor, KDTreeSingleIndexAdaptorParams(), KNNResultSet, PooledAllocator (+3 more)

### Community 42 - "Community 42"
Cohesion: 0.11
Nodes (6): FakeRecord3DStream, Tests for the optional Record3D USB integration., Small in-memory stand-in for the upstream Record3D bindings., test_record3d_stream_wait_for_packet_returns_shared_contract(), test_usb_packet_stream_disconnect_stops_active_stream(), test_usb_packet_stream_wait_for_packet_returns_shared_contract()

### Community 43 - "Community 43"
Cohesion: 0.14
Nodes (21): Build ADVIO Crowd Density Figure, Build ADVIO Local Readiness Figure, Build ADVIO Scene Attribute Figure, Build ADVIO Scene Mix Figure, Build Metrics Error Figure, Build Metrics Trajectory Figure, Build Evo APE Colormap Figure, Plotting Package Public API (+13 more)

### Community 44 - "Community 44"
Cohesion: 0.12
Nodes (7): test_call_callback_with_pyobject_ptr_arg(), test_cast_handle_to_pyobject_ptr(), test_cast_object_to_pyobject_ptr(), test_pass_list_pyobject_ptr(), test_pass_pyobject_ptr(), test_type_caster_name_via_incompatible_function_arguments_type_error(), ValueHolder

### Community 45 - "Community 45"
Cohesion: 0.12
Nodes (6): my_func(), TEST_SUBMODULE(), PC, PPCC, test_PC(), test_PPCC()

### Community 46 - "Community 46"
Cohesion: 0.14
Nodes (5): _build_runtime(), Tests for the Python-side Record3D Wi-Fi transport., test_record3d_wifi_closed_after_connect_logs_runtime_failure(), test_record3d_wifi_closed_before_track_sets_setup_failure_without_logging(), test_record3d_wifi_metadata_failure_is_non_fatal()

### Community 47 - "Community 47"
Cohesion: 0.24
Nodes (12): fast_read(), hash_func(), hashat(), memcpy_up(), qlz_decompress(), qlz_decompress_core(), qlz_size_compressed(), qlz_size_decompressed() (+4 more)

### Community 48 - "Community 48"
Cohesion: 0.2
Nodes (7): assert_equal_tensor_ref(), test_bad_python_to_cpp_casts(), test_convert_tensor_to_py(), test_reference_internal(), test_references_actually_refer(), test_round_trip(), test_round_trip_references_actually_refer()

### Community 49 - "Community 49"
Cohesion: 0.16
Nodes (14): Open Record3D USB Packet Stream, Record3D Streaming Source Config, Record3D Streaming Source, Record3D Stream Config, Record3D Transport Id, Record3D USB Packet Stream, Decode Record3D Wi-Fi Depth, Record3D Wi-Fi Metadata (+6 more)

### Community 50 - "Community 50"
Cohesion: 0.18
Nodes (9): get_cmake_dir(), get_include(), get_pkgconfig_dir(), Return the path to the pybind11 CMake module directory., Return the path to the pybind11 pkgconfig directory., Return the path to the pybind11 include directory. The historical "user"     arg, main(), print_includes() (+1 more)

### Community 51 - "Community 51"
Cohesion: 0.2
Nodes (13): count_stats(), extract_markers(), main(), MarkerEntry, parse_args(), Compute Python line-of-code statistics for src/ and tests/., Render a detailed Rich table for one marker kind., Print LOC statistics for src/ and tests/. (+5 more)

### Community 52 - "Community 52"
Cohesion: 0.15
Nodes (1): Tests for centralized repository path handling.

### Community 53 - "Community 53"
Cohesion: 0.15
Nodes (12): build(), docs(), lint(), make_changelog(), Lint the codebase (except for clang-format/tidy)., Run the tests (requires a compiler)., Run the packaging tests., Build the docs. Pass --non-interactive to avoid serving. (+4 more)

### Community 54 - "Community 54"
Cohesion: 0.25
Nodes (3): _fake_advio_service(), Focused CLI tests for ADVIO dataset commands., test_advio_download_command_builds_explicit_request()

### Community 55 - "Community 55"
Cohesion: 0.33
Nodes (7): chamfer_distance_RMSE(), eval_recon(), eval_recon_from_saved_data(), load_data(), gt_depths: N,H,W     gt_poses: N,4,4     gt_intri: 3,3     est_local_pcls: N,H,W, rel_gt_est: None or [R, t, s] for the relative pose between the ground truth and, transform_to_world_coordinates()

### Community 56 - "Community 56"
Cohesion: 0.48
Nodes (4): normalize_line_endings(), read_tz_file(), test_build_global_dist(), test_build_sdist()

### Community 57 - "Community 57"
Cohesion: 0.4
Nodes (1): Tests for package-root public export surfaces.

### Community 58 - "Community 58"
Cohesion: 0.4
Nodes (0): 

### Community 59 - "Community 59"
Cohesion: 0.5
Nodes (0): 

### Community 60 - "Community 60"
Cohesion: 0.67
Nodes (3): Cv2 Producer Config, Cv2 Frame Producer, Open Cv2 Replay Stream

### Community 61 - "Community 61"
Cohesion: 0.67
Nodes (3): PathConfig.resolve_pipeline_config_path, PathConfig.resolve_pipeline_configs_dir, PathConfig.resolve_toml_path

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
Nodes (2): ImageSize.from_payload, ImageSize Model

### Community 69 - "Community 69"
Cohesion: 1.0
Nodes (0): 

### Community 70 - "Community 70"
Cohesion: 1.0
Nodes (0): 

### Community 71 - "Community 71"
Cohesion: 1.0
Nodes (0): 

### Community 72 - "Community 72"
Cohesion: 1.0
Nodes (0): 

### Community 73 - "Community 73"
Cohesion: 1.0
Nodes (1): PRML VSLAM Package Public API

### Community 74 - "Community 74"
Cohesion: 1.0
Nodes (1): Pipeline Mode

### Community 75 - "Community 75"
Cohesion: 1.0
Nodes (0): 

### Community 76 - "Community 76"
Cohesion: 1.0
Nodes (0): 

### Community 77 - "Community 77"
Cohesion: 1.0
Nodes (0): 

### Community 78 - "Community 78"
Cohesion: 1.0
Nodes (0): 

### Community 79 - "Community 79"
Cohesion: 1.0
Nodes (1): The CXX standard level. If set, will add the required flags. If left at

## Ambiguous Edges - Review These
- `normalize_grayscale_image` → `PacketSessionSnapshot`  [AMBIGUOUS]
  src/prml_vslam/utils/image_utils.py · relation: conceptually_related_to

## Knowledge Gaps
- **321 isolated node(s):** `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`, `PRML VSLAM Package Public API`, `Protocols Package Public API`, `MethodId Enum`, `Record3D Transport Id` (+316 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 67`** (2 nodes): `streamlit_app.py`, `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 68`** (2 nodes): `ImageSize.from_payload`, `ImageSize Model`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 69`** (2 nodes): `test_cli.py`, `test_record3d_devices_command_runs()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 70`** (2 nodes): `cam_test.py`, `main()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 71`** (2 nodes): `CMakeCCompilerId.c`, `main()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 72`** (2 nodes): `CMakeCXXCompilerId.cpp`, `main()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 73`** (1 nodes): `PRML VSLAM Package Public API`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 74`** (1 nodes): `Pipeline Mode`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 75`** (1 nodes): `compiler_depend.ts`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 76`** (1 nodes): `make_changelog.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 77`** (1 nodes): `libsize.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 78`** (1 nodes): `test_eval_call.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 79`** (1 nodes): `The CXX standard level. If set, will add the required flags. If left at`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `normalize_grayscale_image` and `PacketSessionSnapshot`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `normalize_grayscale_image` connect `Community 7` to `Community 8`, `Community 21`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._
- **Why does `TrajectoryEvaluationService` connect `Community 19` to `Community 8`, `Community 7`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Why does `OnlineSLAM` connect `Community 10` to `Community 6`, `Community 7`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Are the 18 inferred relationships involving `BaseViewGraphDataset` (e.g. with `SevenScenes` and `ARKitScene`) actually correct?**
  _`BaseViewGraphDataset` has 18 INFERRED edges - model-reasoned connections that need verification._
- **Are the 24 inferred relationships involving `normalize_grayscale_image` (e.g. with `Record3D Live Page Renderer` and `PipelinePageAction`) actually correct?**
  _`normalize_grayscale_image` has 24 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `OnlineSLAM` (e.g. with `VistaSlamBackend` and `VistaSlamSession`) actually correct?**
  _`OnlineSLAM` has 10 INFERRED edges - model-reasoned connections that need verification._