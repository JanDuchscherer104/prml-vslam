# Graph Report - .  (2026-04-12)

## Corpus Check
- 418 files · ~39,282,589 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 4314 nodes · 9555 edges · 80 communities detected
- Extraction: 61% EXTRACTED · 39% INFERRED · 0% AMBIGUOUS · INFERRED: 3694 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## God Nodes (most connected - your core abstractions)
1. `DatasetId` - 191 edges
2. `MethodId` - 168 edges
3. `SequenceManifest` - 144 edges
4. `Record3DTransportId` - 136 edges
5. `SlamArtifacts` - 104 edges
6. `RunState` - 103 edges
7. `RunPlanStageId` - 100 edges
8. `SlamUpdate` - 96 edges
9. `BaseData` - 95 edges
10. `RunSnapshot` - 90 edges

## Surprising Connections (you probably didn't know these)
- `FakeRecord3DStream` --uses--> `OfflineSequenceSource`  [INFERRED]
  tests/test_record3d.py → src/prml_vslam/protocols/source.py
- `Small in-memory stand-in for the upstream Record3D bindings.` --uses--> `OfflineSequenceSource`  [INFERRED]
  tests/test_record3d.py → src/prml_vslam/protocols/source.py
- `Tests for the Python-side Record3D Wi-Fi transport.` --uses--> `OfflineSequenceSource`  [INFERRED]
  tests/test_record3d_wifi.py → src/prml_vslam/protocols/source.py
- `FakeRecord3DStream` --uses--> `StreamingSequenceSource`  [INFERRED]
  tests/test_record3d.py → src/prml_vslam/protocols/source.py
- `Small in-memory stand-in for the upstream Record3D bindings.` --uses--> `StreamingSequenceSource`  [INFERRED]
  tests/test_record3d.py → src/prml_vslam/protocols/source.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.03
Nodes (270): _build_artifacts(), _build_live_pointmap(), _count_valid_pointmap_points(), _FlowTracker, _frame_transform_from_vista_pose(), _project_rotation_to_so3(), Canonical ViSTA-SLAM backend adapter (offline + streaming)., Persist upstream outputs and convert to canonical repository artifacts. (+262 more)

### Community 1 - "Community 1"
Cohesion: 0.01
Nodes (119): get(), value(), deprecated_call(), pytest.deprecated_call() seems broken in pytest<3.9.x; concretely, it     doesn', # TODO: Remove this when testing requires pytest>=3.9., bind_ConstructorStats(), cpp_std(), PYBIND11_MODULE() (+111 more)

### Community 2 - "Community 2"
Cohesion: 0.01
Nodes (92): AriaSynthetic, ARKitScene, convert traj_string into translation and rotation matrices         Args:, BaseViewGraphDataset, is_good_type(), This function:         - first downsizes the image with LANCZOS inteprolation,, This function:         - first downsizes the image with LANCZOS inteprolation,, Define all basic options.      Usage:         class MyDataset (BaseStereoViewDat (+84 more)

### Community 3 - "Community 3"
Cohesion: 0.02
Nodes (175): AdvioDownloadFormData, AdvioPageData, AdvioPreviewFormData, build_advio_page_data(), handle_advio_preview_action(), load_advio_explorer_sample(), Controller helpers for the ADVIO Streamlit page., Apply one preview-form action and return an error message when it fails. (+167 more)

### Community 4 - "Community 4"
Cohesion: 0.03
Nodes (190): BaseConfig, BaseData, Rigid camera pose with camera-to-world semantics., SE3Pose, ArtifactRef, BenchmarkConfig, BenchmarkEvaluationConfig, CloudBenchmarkConfig (+182 more)

### Community 5 - "Community 5"
Cohesion: 0.01
Nodes (147): BaseConfig, _normalize_value(), Shared Pydantic model helpers for the PRML VSLAM project., Render the config structure as a Rich tree., Validated config model with TOML IO and config-as-factory helpers., Runtime type used by :meth:`setup_target`., Instantiate or build the runtime object described by this config., Return a JSON-serializable view of the config. (+139 more)

### Community 6 - "Community 6"
Cohesion: 0.01
Nodes (91): add(), BoWFrame(), CmdLineParser, loadFeatures(), main(), readImagePaths(), saveToFile(), CmdLineParser (+83 more)

### Community 7 - "Community 7"
Cohesion: 0.02
Nodes (79): multiple_values_error(), nameless_argument_error(), process(), instance_simple_holder_in_ptrs(), size_in_ptrs(), is_instance_method_of_type(), try_get_cpp_conduit_method(), try_raw_pointer_ephemeral_from_cpp_conduit() (+71 more)

### Community 8 - "Community 8"
Cohesion: 0.01
Nodes (44): cast(), localtime_thread_safe(), clear_instance(), enable_dynamic_attributes(), get_fully_qualified_tp_name(), make_default_metaclass(), make_object_base_type(), make_static_property_type() (+36 more)

### Community 9 - "Community 9"
Cohesion: 0.03
Nodes (100): AdvioDownloadManager, _ensure_directory_parent(), _modalities_present(), _normalize_archive_member(), Return the cache directory used for downloaded scene archives., Return one catalog scene by id., Return local availability status for every catalog scene., Download selected ADVIO scenes and extract the requested modalities. (+92 more)

### Community 10 - "Community 10"
Cohesion: 0.02
Nodes (127): build_crowd_density_figure(), build_local_readiness_figure(), build_scene_attribute_figure(), build_scene_mix_figure(), _preview_caption(), _preview_frame_details(), _preview_metrics(), Build a crowd-density composition chart. (+119 more)

### Community 11 - "Community 11"
Cohesion: 0.02
Nodes (13): CustomContains, float_, get_annotations_helper(), m_defs(), C++ default and converting constructors are equivalent to type calls in Python, Tests implicit casting when assigning or appending to dicts and lists., test_class_attribute_types(), test_constructors() (+5 more)

### Community 12 - "Community 12"
Cohesion: 0.04
Nodes (35): ManyAR_PatchEmbed, PatchEmbedDust3R, Handle images with non-square aspect ratio.     All images in the same batch hav, PatchEmbed, get_1d_sincos_pos_embed_from_grid(), get_2d_sincos_pos_embed(), get_2d_sincos_pos_embed_from_grid(), input:                 * tokens: batch_size x nheads x ntokens x dim (+27 more)

### Community 13 - "Community 13"
Cohesion: 0.04
Nodes (41): _build_runtime(), Tests for the Python-side Record3D Wi-Fi transport., test_record3d_wifi_closed_after_connect_logs_runtime_failure(), test_record3d_wifi_closed_before_track_sets_setup_failure_without_logging(), test_record3d_wifi_metadata_failure_is_non_fatal(), decode_record3d_wifi_depth(), from_api_payload(), _parse_depth_range() (+33 more)

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
Cohesion: 0.03
Nodes (34): SquareMatrix is derived from Matrix and inherits the buffer protocol, # TODO: fix on recent PyPy, test_inherited_protocol(), Tests the ability to pass bytes to C++ string-accepting functions.  Note that th, Tests the ability to pass bytearray to C++ string-accepting functions, Tests support for C++17 string_view arguments and return values, Tests unicode conversion and error reporting., Issue #929 - out-of-range integer values shouldn't be accepted (+26 more)

### Community 18 - "Community 18"
Cohesion: 0.04
Nodes (29): FakePyMappingBadItems, FakePyMappingGenObj, FakePyMappingItemsNotCallable, FakePyMappingItemsWithArg, FakePyMappingMissingItems, FakePyMappingWithItems, OptionalProperties, pass_std_vector_int() (+21 more)

### Community 19 - "Community 19"
Cohesion: 0.05
Nodes (24): PythonMyException7, Exception, CustomData(), FlakyException, MyException, MyException2, MyException3, MyException4 (+16 more)

### Community 20 - "Community 20"
Cohesion: 0.04
Nodes (35): cast(), cast_impl(), array_copy_but_one(), assert_equal_ref(), assert_keeps_alive(), assert_sparse_equal_ref(), assign_both(), get_elem() (+27 more)

### Community 21 - "Community 21"
Cohesion: 0.06
Nodes (24): Criterion, Calculate the rotation error between two batches of rotation matrices., gt_views : list of dictionaries, each containing 'pts3d' and 'valid_mask', gt_views : list of dictionaries, each containing 'pts3d' and 'valid_mask', RelPoseLoss, ReprojLoss, ConfLoss, Criterion (+16 more)

### Community 22 - "Community 22"
Cohesion: 0.04
Nodes (21): NonCopyableInt, NonRefIterator, NonZeroIterator, NonZeroSentinel, #2076: Exception raised by len(arg) should be propagated, #181: iterator passthrough did not compile, #388: Can't make iterators via make_iterator() with different r/v policies, #4100: Check for proper iterator overload with C-Arrays (+13 more)

### Community 23 - "Community 23"
Cohesion: 0.05
Nodes (26): IntEnum, _camera_pose_from_binding(), _device_from_binding(), _import_record3d_module(), _intrinsics_from_binding(), list_record3d_usb_devices(), open_record3d_usb_packet_stream(), List the currently connected USB Record3D devices. (+18 more)

### Community 24 - "Community 24"
Cohesion: 0.05
Nodes (33): DPTOutputAdapter, FeatureFusionBlock_custom, Interpolate, make_fusion_block(), make_scratch(), pair(), Forward pass.         Args:             x (tensor): input         Returns:, Feature fusion block. (+25 more)

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
Cohesion: 0.06
Nodes (26): adjust_learning_rate(), all_reduce_mean(), filename(), get_grad_norm_(), _get_num_layer_for_vit(), get_parameter_groups(), get_rank(), get_world_size() (+18 more)

### Community 29 - "Community 29"
Cohesion: 0.04
Nodes (21): ExampleMandA, NoneCastTester, NoneTester, Static property getter and setters expect the type object as the their only argu, Overriding pybind11's default metaclass changes the behavior of `static_property, When returning an rvalue, the return value policy is automatically changed from, #2778: implicit casting from None to object (not pointer), #283: __str__ called on uninitialized instance when constructor arguments invali (+13 more)

### Community 30 - "Community 30"
Cohesion: 0.07
Nodes (31): create_and_destroy(), PYBIND11_OVERRIDE(), PyTF6(), PyTF7(), Tests py::init_factory() wrapper with various upcasting and downcasting returns, Tests py::init_factory() wrapper around various ways of returning the object, Tests py::init_factory() wrapper with value conversions and alias types, Tests init factory functions with dual main/alias factory functions (+23 more)

### Community 31 - "Community 31"
Cohesion: 0.07
Nodes (29): attach_file_sink(), attach_grpc_sink(), collect_native_visualization_artifacts(), create_recording_stream(), export_viewer_recording(), _import_rerun(), log_transform(), LatestCamera (+21 more)

### Community 32 - "Community 32"
Cohesion: 0.06
Nodes (0): 

### Community 33 - "Community 33"
Cohesion: 0.09
Nodes (9): assert_equal(), dt_fmt(), packed_dtype_fmt(), partial_dtype_fmt(), partial_ld_offset(), partial_nested_fmt(), simple_dtype_fmt(), test_dtype() (+1 more)

### Community 34 - "Community 34"
Cohesion: 0.11
Nodes (21): get_cmake_dir(), get_include(), get_pkgconfig_dir(), Return the path to the pybind11 CMake module directory., Return the path to the pybind11 pkgconfig directory., Return the path to the pybind11 include directory. The historical "user"     arg, advio_download(), advio_summary() (+13 more)

### Community 35 - "Community 35"
Cohesion: 0.17
Nodes (24): _build_fake_catalog(), Tests for the simplified ADVIO adapter and replay stream., test_advio_dataset_service_downloads_selected_modalities_from_cached_archive(), test_advio_dataset_service_handles_official_archive_layout(), test_advio_dataset_service_lists_and_loads_local_sequences(), test_advio_dataset_service_offline_preset_downloads_evaluation_ready_bundle(), test_advio_dataset_service_refreshes_corrupted_cached_archive(), test_advio_dataset_service_summarize_reuses_precomputed_statuses() (+16 more)

### Community 36 - "Community 36"
Cohesion: 0.13
Nodes (22): ArxivSourceSpec, download_file(), fetch_pdf(), fetch_tex_source(), from_json(), load_manifest(), main(), normalize_member_path() (+14 more)

### Community 37 - "Community 37"
Cohesion: 0.12
Nodes (7): test_call_callback_with_pyobject_ptr_arg(), test_cast_handle_to_pyobject_ptr(), test_cast_object_to_pyobject_ptr(), test_pass_list_pyobject_ptr(), test_pass_pyobject_ptr(), test_type_caster_name_via_incompatible_function_arguments_type_error(), ValueHolder

### Community 38 - "Community 38"
Cohesion: 0.13
Nodes (15): collate_with_cat(), listify(), MyNvtxRange, Transfer some variables to another device (i.e. GPU, CPU:torch, CPU:numpy)., to_cpu(), to_cuda(), to_numpy(), todevice() (+7 more)

### Community 39 - "Community 39"
Cohesion: 0.19
Nodes (14): build_stage_manifests(), build_stage_status(), build_summary_manifest(), finalize_run_outputs(), stable_hash(), write_json(), _check_extraction_cache(), _copy_if_needed() (+6 more)

### Community 40 - "Community 40"
Cohesion: 0.13
Nodes (5): PoseGraphEdges, PoseGraphNodes, PoseGraphOpt, PoseGraphOptAll, add a node to the pose graph.         Notice that the absolute pose of the node

### Community 41 - "Community 41"
Cohesion: 0.19
Nodes (7): Cv2FrameProducer, open_cv2_replay_stream(), Return a ready-to-use replay stream for `config`., Blocking RGB frame producer backed by `cv2.VideoCapture`., Open the configured video file and prepare playback state., Release the underlying OpenCV capture if one is open., Decode and return the next sampled RGB frame.

### Community 42 - "Community 42"
Cohesion: 0.2
Nodes (7): camera_matrix_of_crop(), crop_image_depthmap(), ImageList, Return a crop of the input view., Convenience class to aply the same operation to a whole set of images., Jointly rescale a (image, depthmap)     so that (out_width, out_height) >= outpu, rescale_image_depthmap()

### Community 43 - "Community 43"
Cohesion: 0.23
Nodes (14): AdvioCalibration, _expect_float_list(), _expect_mapping(), _expect_matrix(), _extract_camera_mapping(), load_advio_calibration(), load_advio_frame_timestamps_ns(), load_advio_trajectory() (+6 more)

### Community 44 - "Community 44"
Cohesion: 0.2
Nodes (13): count_stats(), extract_markers(), main(), MarkerEntry, parse_args(), Compute Python line-of-code statistics for src/ and tests/., Render a detailed Rich table for one marker kind., Print LOC statistics for src/ and tests/. (+5 more)

### Community 45 - "Community 45"
Cohesion: 0.15
Nodes (1): Tests for centralized repository path handling.

### Community 46 - "Community 46"
Cohesion: 0.15
Nodes (12): build(), docs(), lint(), make_changelog(), Lint the codebase (except for clang-format/tidy)., Run the tests (requires a compiler)., Run the packaging tests., Build the docs. Pass --non-interactive to avoid serving. (+4 more)

### Community 47 - "Community 47"
Cohesion: 0.22
Nodes (3): _fake_advio_service(), Focused CLI tests for ADVIO dataset commands., test_advio_download_command_builds_explicit_request()

### Community 48 - "Community 48"
Cohesion: 0.22
Nodes (5): Dataset-edge frame-graph helpers., Thin wrapper around `pytransform3d.TransformManager` for static frame compositio, Register one static transform., Resolve one composed transform back into the repo-owned transform DTO., StaticFrameGraph

### Community 49 - "Community 49"
Cohesion: 0.25
Nodes (4): Return the transform fields in TUM trajectory order., Return the normalized quaternion in XYZW order., Return the translation vector in XYZ order., Return the transform as a 4x4 matrix.

### Community 50 - "Community 50"
Cohesion: 0.48
Nodes (4): normalize_line_endings(), read_tz_file(), test_build_global_dist(), test_build_sdist()

### Community 51 - "Community 51"
Cohesion: 0.7
Nodes (4): _artifact_ref(), import_vista_artifacts(), _optional_existing_path(), _require_existing_path()

### Community 52 - "Community 52"
Cohesion: 0.4
Nodes (1): Tests for package-root public export surfaces.

### Community 53 - "Community 53"
Cohesion: 0.4
Nodes (0): 

### Community 54 - "Community 54"
Cohesion: 0.5
Nodes (0): 

### Community 55 - "Community 55"
Cohesion: 1.0
Nodes (2): gen(), video()

### Community 56 - "Community 56"
Cohesion: 0.67
Nodes (1): Simple script for rebuilding .codespell-ignore-lines  Usage:  cat < /dev/null >

### Community 57 - "Community 57"
Cohesion: 0.67
Nodes (0): 

### Community 58 - "Community 58"
Cohesion: 0.67
Nodes (0): 

### Community 59 - "Community 59"
Cohesion: 0.67
Nodes (2): imread_cv2(), Open an image or a depthmap with opencv-python.

### Community 60 - "Community 60"
Cohesion: 1.0
Nodes (1): Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays

### Community 61 - "Community 61"
Cohesion: 1.0
Nodes (0): 

### Community 62 - "Community 62"
Cohesion: 1.0
Nodes (0): 

### Community 63 - "Community 63"
Cohesion: 1.0
Nodes (1): Return the human-readable source label.

### Community 64 - "Community 64"
Cohesion: 1.0
Nodes (1): Return the user-facing transport label.

### Community 65 - "Community 65"
Cohesion: 1.0
Nodes (1): Runtime type that exposes shared packet objects.

### Community 66 - "Community 66"
Cohesion: 1.0
Nodes (1): Return the short user-facing dataset label.

### Community 67 - "Community 67"
Cohesion: 1.0
Nodes (1): Return the compact scene label shown in the app and CLI.

### Community 68 - "Community 68"
Cohesion: 1.0
Nodes (1): Normalize and validate explicit scene selections.

### Community 69 - "Community 69"
Cohesion: 1.0
Nodes (1): Remove duplicate modality overrides while preserving order.

### Community 70 - "Community 70"
Cohesion: 1.0
Nodes (1): Return the canonical ADVIO folder name.

### Community 71 - "Community 71"
Cohesion: 1.0
Nodes (1): Reject empty dataset roots.

### Community 72 - "Community 72"
Cohesion: 1.0
Nodes (1): Build a transform from XYZW quaternion and XYZ translation arrays.

### Community 73 - "Community 73"
Cohesion: 1.0
Nodes (1): Build a transform from a 4x4 homogeneous matrix.

### Community 74 - "Community 74"
Cohesion: 1.0
Nodes (0): 

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
Nodes (1): The CXX standard level. If set, will add the required flags. If left at

### Community 79 - "Community 79"
Cohesion: 1.0
Nodes (1): Build one spec from one JSON object.

## Knowledge Gaps
- **425 isolated node(s):** `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`, `Typed source identifier for one available reference trajectory.`, `Return the human-readable source label.`, `One prepared reference trajectory available to a benchmark run.`, `Prepared benchmark-side inputs discovered for one normalized sequence.` (+420 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 60`** (2 nodes): `streamlit_app.py`, `Thin Streamlit entrypoint for the PRML VSLAM workbench scaffold.  The file stays`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 61`** (2 nodes): `test_cli.py`, `test_record3d_devices_command_runs()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 62`** (2 nodes): `cam_test.py`, `main()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 63`** (1 nodes): `Return the human-readable source label.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 64`** (1 nodes): `Return the user-facing transport label.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 65`** (1 nodes): `Runtime type that exposes shared packet objects.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 66`** (1 nodes): `Return the short user-facing dataset label.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 67`** (1 nodes): `Return the compact scene label shown in the app and CLI.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 68`** (1 nodes): `Normalize and validate explicit scene selections.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 69`** (1 nodes): `Remove duplicate modality overrides while preserving order.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 70`** (1 nodes): `Return the canonical ADVIO folder name.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 71`** (1 nodes): `Reject empty dataset roots.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 72`** (1 nodes): `Build a transform from XYZW quaternion and XYZ translation arrays.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 73`** (1 nodes): `Build a transform from a 4x4 homogeneous matrix.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 74`** (1 nodes): `test.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 75`** (1 nodes): `make_changelog.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 76`** (1 nodes): `libsize.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 77`** (1 nodes): `test_eval_call.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 78`** (1 nodes): `The CXX standard level. If set, will add the required flags. If left at`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 79`** (1 nodes): `Build one spec from one JSON object.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Visualization contracts and Rerun helpers.` connect `Community 4` to `Community 0`, `Community 3`, `Community 5`, `Community 9`, `Community 41`, `Community 23`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._
- **Why does `OnlineSLAM` connect `Community 0` to `Community 40`, `Community 2`, `Community 12`, `Community 31`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Why does `# TODO: Save last check point` connect `Community 21` to `Community 28`, `Community 12`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **Are the 188 inferred relationships involving `DatasetId` (e.g. with `VideoOfflineSequenceSource` and `OfflineSourceResolver`) actually correct?**
  _`DatasetId` has 188 INFERRED edges - model-reasoned connections that need verification._
- **Are the 165 inferred relationships involving `MethodId` (e.g. with `MockSlamBackendConfig` and `MockSlamBackend`) actually correct?**
  _`MethodId` has 165 INFERRED edges - model-reasoned connections that need verification._
- **Are the 141 inferred relationships involving `SequenceManifest` (e.g. with `OfflineSequenceSource` and `BenchmarkInputSource`) actually correct?**
  _`SequenceManifest` has 141 INFERRED edges - model-reasoned connections that need verification._
- **Are the 132 inferred relationships involving `Record3DTransportId` (e.g. with `Record3DStreamingSourceConfig` and `Record3DStreamingSource`) actually correct?**
  _`Record3DTransportId` has 132 INFERRED edges - model-reasoned connections that need verification._