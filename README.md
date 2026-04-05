# Challenge 5: Uncalibrated Monocular VSLAM

This repository addresses an off-device monocular VSLAM pipeline for smartphone videos-streams with unknown intrinsics. The goal is to recover a high-precision ego-trajectory and a dense 3D point cloud from raw video, and to benchmark the result against ARCore and other state-of-the-art methods.

The rendered [final report](docs/report/main.typ) and [update-meeting slides](docs/slides/update-meetings/) are available on the [GitHub Pages](https://janduchscherer104.github.io/prml-vslam/).

## Setup

### Requirements

- [uv](https://docs.astral.sh/uv/getting-started/installation/) package manager
- [typst](https://typst.app/open-source/#download) for slides & report

### Bootstrap

```bash
uv sync --extra dev
uv run pre-commit install
make ci
```

Optional parallel test runs are available with `pytest-xdist`:

```bash
uv run --extra dev pytest -n auto
make test PYTEST_ARGS="-n auto"
```

### Streamlit Workbench

```bash
uv sync
# add `--extra streaming` to enable Record3D USB / Wi-Fi preview support
uv run streamlit run streamlit_app.py
```

The app supports:

- a `Record3D` live-capture page for USB and Wi-Fi preview inside the workbench
- an `ADVIO` dataset page for local readiness checks, selective downloads, and loop preview
- a `Pipeline` page for run planning, a minimal ADVIO mock pipeline demo, and artifact monitoring
- a `Metrics` page for persisted trajectory review and explicit `evo` evaluation
- `PathConfig`-driven dataset and artifact discovery without app-local path defaults

Pipeline contract and extension guidance lives in
[`src/prml_vslam/pipeline/README.md`](src/prml_vslam/pipeline/README.md).

### TOML-First Run Planning

For durable/reproducible planning, store a `RunRequest` as TOML and resolve it
through the CLI:

```toml
experiment_name = "advio-office-offline-vista"
mode = "offline"
output_dir = "artifacts"

[source]
video_path = "captures/office-03.mp4"
frame_stride = 2

[slam]
method = "vista"
emit_dense_points = true
emit_sparse_points = true

[reference]
enabled = false

[evaluation]
compare_to_arcore = true
evaluate_cloud = false
evaluate_efficiency = true
```

```bash
uv run prml-vslam plan-run-config configs/advio-office-vista.toml
```

## Challenge

Professional SLAM systems usually require rigid factory calibration. Consumer frameworks like ARCore are stable due to real-time sensor fusion, but often fail when processing raw video retrospectively. In particular, they struggle with global metric consistency and high-fidelity dense mapping when camera intrinsics are unknown.

The system should build on existing monocular dense VSLAM methods such as [ViSTA-SLAM](https://arxiv.org/pdf/2509.01584) or [MASt3R-SLAM](https://arxiv.org/abs/2412.12392), take a smartphone monocular video stream as input, autonomously handle unknown intrinsics, and output a high-precision trajectory together with a dense 3D point cloud.

## Evaluation

- Dataset: [ADVIO: An Authentic Dataset for Visual-Inertial Odometry](https://github.com/AaltoVision/ADVIO), plus a custom self-recorded dataset with raw video and odometry logs.
- Identify suitable metrics for pose drift and reconstruction fidelity.
- Evaluate at least two state-of-the-art VSLAM methods.
- Measure trajectory quality, including comparison against ARCore, on the ADVIO dataset and on a custom dataset.
- Measure 3D point cloud quality, including comparison against ARCore mapping, on a self-recorded test dataset.
- Develop a custom app or logging workflow for recording raw video and baseline ARCore logs.
- Measure efficiency in terms of latency and memory consumption.

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
