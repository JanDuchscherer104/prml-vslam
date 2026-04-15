# Challenge 5: Uncalibrated Monocular VSLAM

This repository addresses an off-device monocular VSLAM pipeline for smartphone videos-streams with unknown intrinsics. The goal is to recover a high-precision ego-trajectory and a dense 3D point cloud from raw video, and to benchmark the result against ARCore and other state-of-the-art methods.

The rendered [final report](docs/report/main.typ) and [update-meeting slides](docs/slides/update-meetings/) are available on the [GitHub Pages](https://janduchscherer104.github.io/prml-vslam/).

## Setup

### Requirements

- `git` with submodule support
- [conda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html) (or `mamba`)
- [uv](https://docs.astral.sh/uv/getting-started/installation/) package manager
- [typst](https://typst.app/open-source/#download) for slides & report

### Bootstrap

```bash
# If you did not clone recursively:
git submodule update --init --recursive

# Base repository tooling and tests:
uv sync --extra dev

# Optional Linux/CUDA helper environment for ViSTA work:
# For a fresh environment:
conda env create -f environment.yml

# Or, if updating an older prml-vslam conda env, prune packages no longer owned by environment.yml:
conda env update --prune -f environment.yml

conda activate prml-vslam
unset VIRTUAL_ENV
export UV_PROJECT_ENVIRONMENT="$CONDA_PREFIX"
uv sync --extra dev --extra vista --extra streaming

# Optional: build CUDA RoPE2D acceleration for ViSTA-SLAM
uv run --extra vista python scripts/build_vista_curope.py

# ViSTA pretrained files expected by the upstream backend
mkdir -p external/vista-slam/pretrains
curl -L "https://huggingface.co/zhangganlin/vista_slam/resolve/main/frontend_sta_weights.pth?download=true" \
  -o external/vista-slam/pretrains/frontend_sta_weights.pth
curl -L "https://huggingface.co/zhangganlin/vista_slam/resolve/main/ORBvoc.txt?download=true" \
  -o external/vista-slam/pretrains/ORBvoc.txt

uv run pre-commit install
make ci
```

Optional parallel test runs are available with `pytest-xdist`:

```bash
uv run pytest -n auto
make test PYTEST_ARGS="-n auto"
```

Repo-owned datasets and generated benchmark outputs resolve under `.data/` and `.artifacts/` by default via [`PathConfig`](src/prml_vslam/utils/path_config.py).

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

```bash
# add `--extra streaming` for Record3D and `--extra vista` for ViSTA + Rerun support
uv sync --extra streaming
uv run streamlit run streamlit_app.py
```

The app currently supports:

- a `Record3D` live-capture page for `USB` and `Wi-Fi Preview`
- an `ADVIO` dataset page for local readiness checks, selective downloads, and loop preview
- a `Pipeline` page for TOML-backed request editing, ADVIO or Record3D source selection, and artifact monitoring
- an **Async Multiprocessing Backend** for ViSTA-SLAM that isolates heavy GPU inference to prevent UI lag
- **Live Rerun Visualization** for streaming 3D poses and dense point clouds in real-time
- a `Metrics` page for persisted trajectory review and explicit `evo` evaluation
- [`PathConfig`](src/prml_vslam/utils/path_config.py)-driven dataset and artifact discovery without app-local path defaults

## Rerun Visualization

The repository includes a comprehensive integration with the [Rerun](https://rerun.io) viewer for both live and offline analysis.

### Live Mode
1. Start the Rerun viewer with the project blueprint:
   ```bash
   uv run rerun .configs/visualization/vista_blueprint.rbl --serve-web
   ```
2. In the Streamlit UI, toggle **"Connect live Rerun viewer"** to ON.
3. Run the pipeline. Data will stream live to the Rerun window.

### Offline Mode
To analyze a completed run, pass the generated `.rrd` artifact and the blueprint to the Rerun CLI:
```bash
uv run rerun .artifacts/<run_id>/vista/visualization/viewer_recording.rrd .configs/visualization/vista_blueprint.rbl
```

A utility script is available to regenerate the blueprint if needed:
```bash
uv run scripts/vista_rerun_viewer.py
```

## TOML-First Run Planning

For durable and reproducible planning, store a [`RunRequest`](src/prml_vslam/pipeline/README.md) as TOML under
`.configs/pipelines/`. These files are automatically discovered by the Streamlit **"Pipeline Config"** dropdown.

```toml
experiment_name = "vista-full-tuning"
mode = "streaming"
output_dir = ".artifacts"

[source]
dataset_id = "advio"
sequence_id = "advio-15"

[slam]
method = "vista"

[slam.backend.slam]
# algorithmic overrides for the ViSTA backend
flow_thres = 5.0
max_view_num = 400

[visualization]
connect_live_viewer = true
export_viewer_rrd = true
```

A comprehensive example with all available tuning parameters is provided in [`.configs/pipelines/vista-full.toml`](.configs/pipelines/vista-full.toml).

```bash
uv run prml-vslam plan-run-config advio-15-offline-vista.toml
uv run prml-vslam run-config advio-15-offline-vista.toml
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

## ViSTA Run Quick Checks

### Video Smoke Test (TUM sample clip)

```bash
cat > .configs/pipelines/vista-smoke-test.toml <<'EOF'
experiment_name = "smoke-test"
mode = "offline"
output_dir = ".artifacts"

[source]
video_path = "external/vista-slam/media/tumrgbd_room.mp4"
frame_stride = 1

[slam]
method = "vista"

[slam.backend]
max_frames = 50

[benchmark.reference]
enabled = false

[benchmark.trajectory]
enabled = false

[benchmark.cloud]
enabled = false

[benchmark.efficiency]
enabled = false
EOF

uv run prml-vslam run-config .configs/pipelines/vista-smoke-test.toml
```

### ADVIO Offline ViSTA Demo

```bash
uv run prml-vslam write-demo-config --mode offline --method vista --sequence 15
uv run prml-vslam run-config .configs/pipelines/advio-15-offline-vista.toml
```

The first ADVIO offline run extracts video frames into `.artifacts/.../input/frames`
and can take around 1-3 minutes depending on disk/CPU. Re-running the same config
reuses cached extracted frames.

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
