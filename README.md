# Challenge 5: Uncalibrated Monocular VSLAM

This repository addresses an off-device monocular VSLAM pipeline for smartphone videos-streams with unknown intrinsics. The goal is to recover a high-precision ego-trajectory and a dense 3D point cloud from raw video, and to benchmark the result against ARCore and other state-of-the-art methods.

The rendered [final report](docs/report/main.typ) and [update-meeting slides](docs/slides/update-meetings/) are available on the [GitHub Pages](https://janduchscherer104.github.io/prml-vslam/).

## Setup

### Requirements

- [uv](https://docs.astral.sh/uv/getting-started/installation/) package manager
- [typst](https://typst.app/open-source/#download) for slides & report
- System OpenCV dev headers: `sudo apt-get install -y libopencv-dev` (required to build the ViSTA-SLAM loop-detector extension)

### Bootstrap

```bash
# 1. Clone with submodules (includes the ViSTA-SLAM upstream repo)
git clone --recurse-submodules <repo-url>
# if already cloned:
git submodule update --init --recursive

# 2. Sync Python dependencies (includes torch, xformers, rerun-sdk and all ViSTA-SLAM deps)
uv sync --all-extras

# 3. Install C build tools into the project venv (run from repo root)
uv pip install setuptools wheel cmake

# 4. Build the DBoW3Py loop-detector C extension
#    Output goes directly to external/vista-slam/ so it is importable via sys.path.
#    Requires libopencv-dev; one-time step after cloning.
cmake -S external/vista-slam/DBoW3Py -B external/vista-slam/DBoW3Py/cmake_build \
  -DPYTHON_EXECUTABLE=$(uv run which python) \
  -DCMAKE_LIBRARY_OUTPUT_DIRECTORY=$(pwd)/external/vista-slam \
  -DCMAKE_BUILD_TYPE=Release
make -C external/vista-slam/DBoW3Py/cmake_build -j$(nproc)

# 5. Download ViSTA-SLAM pretrained weights into external/vista-slam/pretrains/
#    (one-time step, not git tracked)
wget -O external/vista-slam/pretrains/frontend_sta_weights.pth \
  "https://huggingface.co/zhangganlin/vista_slam/resolve/main/frontend_sta_weights.pth?download=true"
wget -O external/vista-slam/pretrains/ORBvoc.txt \
  "https://huggingface.co/zhangganlin/vista_slam/resolve/main/ORBvoc.txt?download=true"

# 6. Install pre-commit hooks and run CI checks
uv run pre-commit install
make ci
```

Optional parallel test runs are available with `pytest-xdist`:

```bash
uv run pytest -n auto
make test PYTEST_ARGS="-n auto"
```

Repo-owned datasets and generated benchmark outputs resolve under `.data/` and `.artifacts/` by default via [`PathConfig`](src/prml_vslam/utils/path_config.py).

<<<<<<< HEAD
## Documentation Map

- `README.md`
  - onboarding, setup, repo workflow, and high-level project framing
- `src/prml_vslam/**/README.md`
  - current implementation guidance and code-oriented extension notes
- `src/prml_vslam/**/REQUIREMENTS.md`
  - concise package contracts, current-state boundaries, and target-state rules
- `AGENTS.md` and nested `AGENTS.md`
  - repo policy and agent-facing workflow guidance
- `docs/Questions.md`
  - update-sessions related clarification log for challenge scope and intent

## Streamlit Workbench
=======
### ViSTA-SLAM: Run Offline

Run the full offline ViSTA-SLAM pipeline on any video:

```bash
uv run prml-vslam run "My Experiment" path/to/video.mp4 \
  --output-dir .artifacts \
  --max-frames 200          # optional: cap frames for quick tests
```

This command:
1. Extracts frames from the video into `.artifacts/<slug>/vista/input/frames/`
2. Runs ViSTA-SLAM in-process (no subprocess; imports from `external/vista-slam/`)
3. Writes `trajectory.tum` and `sparse_points.ply` into `.artifacts/<slug>/vista/slam/`

Use the demo video bundled with the submodule for a quick smoke test:

```bash
uv run prml-vslam run "Smoke Test" external/vista-slam/media/tumrgbd_room.mp4 \
  --max-frames 50
```

### Streamlit Workbench
>>>>>>> cb23d46 (docs: add vista-slam setup and usage to README)

```bash
uv sync
# add `--extra streaming` to enable Record3D USB and Wi-Fi Preview support
uv run streamlit run streamlit_app.py
```

The app currently supports:

- a `Record3D` live-capture page for `USB` and `Wi-Fi Preview`
- an `ADVIO` dataset page for local readiness checks, selective downloads, and loop preview
- a `Pipeline` page for TOML-backed request editing, ADVIO or Record3D source selection, bounded mock execution, and artifact monitoring
- a `Metrics` page for persisted trajectory review and explicit `evo` evaluation
- [`PathConfig`](src/prml_vslam/utils/path_config.py)-driven dataset and artifact discovery without app-local path defaults


Pipeline contract and extension guidance lives in [`src/prml_vslam/pipeline/README.md`](src/prml_vslam/pipeline/README.md).

## TOML-First Run Planning

For durable and reproducible planning, store a [`RunRequest`](src/prml_vslam/pipeline/README.md) as TOML under
`.configs/pipelines/` and resolve it through the [`plan-run-config`](src/prml_vslam/main.py) CLI command:

```toml
experiment_name = "advio-office-offline-vista"
mode = "offline"
output_dir = ".artifacts"

[source]
video_path = "captures/office-03.mp4"
frame_stride = 2

[slam]
method = "vista"

[slam.outputs]
emit_dense_points = true
emit_sparse_points = true

[benchmark.reference]
enabled = false

[benchmark.trajectory]
enabled = true
baseline_source = "ground_truth"

[benchmark.cloud]
enabled = false

[benchmark.efficiency]
enabled = true
```

```bash
uv run prml-vslam plan-run-config offline-advio-15-vista.toml
uv run prml-vslam run-config offline-advio-15-vista.toml
```

The TOML shape mirrors the nested `RunRequest` model: top-level fields configure
the run itself, while `[source]`, `[slam]`, `[benchmark]`, and
`[visualization]` map directly onto the nested config objects owned by the
repository. Method-private config now lives under `[slam.backend]`, and output
policy lives under `[slam.outputs]`.

[`plan-run-config`](src/prml_vslam/main.py) loads persisted requests through the
repo-owned helpers described in
[`src/prml_vslam/pipeline/README.md`](src/prml_vslam/pipeline/README.md). Use
[`run-config`](src/prml_vslam/main.py) for true offline execution. The config
file itself is resolved through
[`PathConfig`](src/prml_vslam/utils/path_config.py), while nested TOML paths are
hydrated as written and should be normalized explicitly in runtime code when
repo-relative behavior is required.

`pipeline-demo` now refers only to the bounded ADVIO streaming demo slice.
Offline execution uses the new `run-config` path instead of reusing the
streaming-first demo launcher.

## Challenge Context

Professional SLAM systems usually require rigid factory calibration. Consumer frameworks like ARCore are stable due to real-time sensor fusion, but often fail when processing raw video retrospectively. In particular, they struggle with global metric consistency and high-fidelity dense mapping when camera intrinsics are unknown.

The system should build on existing monocular dense VSLAM methods such as [ViSTA-SLAM](https://arxiv.org/pdf/2509.01584) or [MASt3R-SLAM](https://arxiv.org/abs/2412.12392), take a smartphone monocular video stream as input, autonomously handle unknown intrinsics, and output a high-precision trajectory together with a dense 3D point cloud.

## Evaluation

- use [ADVIO](https://github.com/AaltoVision/ADVIO) plus custom self-recorded dataset with raw video and odometry logs.
- Identify suitable metrics for pose drift and reconstruction fidelity.
- Evaluate at least two state-of-the-art VSLAM methods.
- Compare trajectories against available references and optional ARCore baselines.
- Compare dense geometry against reference reconstructions and optional ARCore maps when those baselines exist.
- Develop a custom capture or logging workflow for raw video and optional baseline data
- Measure efficiency in terms of latency and memory consumption

## Deliverables

- A reproducible off-device monocular VSLAM pipeline for raw smartphone video with unknown intrinsics.
- Benchmark results for at least two methods, including trajectory and dense reconstruction quality.
- A custom dataset capture workflow or app with raw video and ARCore baseline logs.
- An evaluation report covering accuracy, reconstruction quality, latency, and memory consumption.
- A final recommendation for the most suitable pipeline in this challenge setting.

## Starting Points

- Ground-truth 3D point clouds: [COLMAP](https://colmap.github.io/index.html) + [Meshroom](https://meshroom.org/) or COLMAP + [3DGS](https://learnopencv.com/3d-gaussian-splatting/)
- Point cloud comparison: [CloudCompare](https://www.cloudcompare.org/), with metrics for example from [Open3D](https://www.open3d.org/)
- Trajectory comparison: [evo](https://github.com/MichaelGrupp/evo)
- Papers: [ViSTA-SLAM](https://arxiv.org/pdf/2509.01584), [MASt3R-SLAM](https://arxiv.org/abs/2412.12392)
