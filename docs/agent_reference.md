# Agent Reference

This file is the detailed reference that the AGENTS scaffold points to. It keeps lookup material and
the benchmark contract out of `AGENTS.md` while remaining binding by reference.

## Source-of-Truth Roles

- `README.md`: repository workflow, setup, developer commands, and deliverables.
- `docs/Questions.md`: high-quality human-maintained ground truth for challenge scope, clarified
  requirements, and operator-facing constraints.
- `docs/agent_reference.md`: detailed benchmark contract, artifact conventions, and lookup material.

## Benchmark Contract

### Ownership Boundary

- `prml_vslam` owns configuration, artifact layout, normalization, evaluation, plotting, and
  reporting.
- External methods own their own inference internals.
- ViSTA-SLAM, MASt3R-SLAM, ARCore, COLMAP, Meshroom, Nerfstudio, Open3D, CloudCompare, and `evo`
  should remain thinly integrated external systems unless a task explicitly requires deeper
  in-repo logic.

### Frame and Transform Naming

- Use explicit frame names in symbols, metadata, and comments.
- Avoid ambiguous names such as `pose`, `transform`, `global`, or `local` without frame labels.
- When storing transforms explicitly in matrices or JSON sidecars, use `T_world_camera` naming for
  world <- camera transforms unless a boundary adapter documents a different convention.
- Raw backend conventions must be normalized at the repo boundary. Do not let upstream frame
  conventions leak into cross-method evaluation.
- Repo-owned runtime and metadata contracts should validate these assumptions at load time. In
  particular, SE(3) matrices, preview trajectories, canonical units, and normalized artifact
  formats should be rejected immediately when malformed.

### Units and Time

- Canonical geometry unit: meters.
- Canonical time unit: seconds.
- Timestamp provenance must be explicit:
  - capture timestamps when sourced from recorded data
  - method timestamps when emitted by an external backend
  - frame indices only when true timestamps are unavailable
- If scale is unknown upstream and later resolved by alignment, record that explicitly instead of
  treating the result as inherently metric.

### Normalized Artifact Expectations

At minimum, normalized benchmark runs should converge on repo-owned artifacts such as:

- `input/capture_manifest.json`
- `planning/run_request.toml`
- `planning/run_plan.toml`
- `slam/trajectory.tum`
- `slam/trajectory.metadata.json`
- `slam/sparse_points.ply` when available
- `dense/dense_points.ply` when available
- `dense/dense_points.metadata.json` when available
- `evaluation/arcore_alignment.json` when ARCore comparison is enabled
- `reference/reference_cloud.ply` when a reference reconstruction is enabled

When the base file format cannot carry enough benchmark metadata, add a JSON sidecar next to the
normalized artifact. Sidecars should record the minimum information needed for reproducible
evaluation, such as:

- frame names and transform direction
- units
- timestamp source
- scale or similarity alignment metadata
- preprocessing choices such as downsampling or filtering
- upstream method identifier and configuration snapshot path

The planning snapshots under `planning/` are also part of the repo-owned contract. They should make
it possible to reconstruct how a workspace was supposed to run before any external backend is
invoked.

### Alignment and Evaluation

- Never evaluate raw backend outputs directly across methods. Normalize first.
- ARCore is an explicit external baseline, not a hidden part of any method wrapper.
- Trajectory metrics must record the alignment policy used, including whether alignment was SE(3),
  Sim(3), or another constrained transform.
- Dense metrics must record any preprocessing needed for comparison, including downsampling,
  filtering, or cropping.
- If a benchmark result depends on an alignment transform, that transform or its parameters must be
  persisted in metadata.
- Keep method execution, alignment, and metric computation as separate stages with separate
  artifacts.

### Wrapper Policy

- Prefer calling official upstream entry points over importing deep internal modules.
- Keep upstream environments separate when practical.
- Snapshot run inputs and upstream config paths in repo-owned artifacts.
- Fail early if an external backend is not runnable.
- Document unsupported cases explicitly.
- Do not hide fallback logic, evaluation logic, or alignment logic inside a method runner.

## Context7 Library IDs

- `/pydantic/pydantic` - Data validation and settings management
- `/pydantic/pydantic-settings` - Environment-backed application settings
- `/websites/typst_app` - Presentations and publications
- `/websites/astral_sh_uv` - UV package manager
- `/plotly/plotly.py` - Plotly Python visualization library
- `/websites/typer_tiangolo` - Typer CLI docs
- `/websites/streamlit_io` - Streamlit app framework
- `/patrick-kidger/jaxtyping` - Shape-and-dtype annotations for arrays and tensors
- `/dfki-ric/pytransform3d` - Transform and frame-convention handling
- `/nerfstudio-project/nerfstudio` - NeRF and scene-reconstruction tooling
- `/numpy/numpy` - NumPy array computing
- `/opencv/opencv` - OpenCV computer vision library
- `/textualize/rich` - Rich terminal rendering and logging
- `/pytest-dev/pytest` - pytest test framework
- `/python/mypy` - mypy static type checker
- `/mwaskom/seaborn` - seaborn statistical plotting
- `/colmap/colmap` - Structure-from-Motion and Multi-View Stereo reconstruction
- `/alicevision/meshroom` - Photogrammetry pipeline and 3D reconstruction
- `/graphdeco-inria/gaussian-splatting` - 3D Gaussian Splatting for scene reconstruction
- `/cloudcompare/cloudcompare` - Point cloud processing and comparison
- `/isl-org/open3d` - 3D data processing and evaluation
- `/michaelgrupp/evo` - Trajectory evaluation for odometry and SLAM
