# Challenge 5: Uncalibrated Monocular VSLAM

This repository addresses an off-device monocular VSLAM pipeline for smartphone video streams with unknown intrinsics. The goal is to recover a high-precision ego-trajectory and a dense 3D point cloud from raw video, and to benchmark the result against ARCore and other state-of-the-art methods.

The rendered [final report](docs/report/main.typ) and [update-meeting slides](docs/slides/update-meetings/) are available on the [GitHub Pages](https://janduchscherer104.github.io/prml-vslam/).

## Documentation Map

- `README.md`
  - project front door, workflow pointers, and high-level project framing
- `SETUP.md`
  - environment setup, validation commands, and Streamlit launch variants
- `src/prml_vslam/**/README.md`
  - current implementation guidance and code-oriented extension notes
- `src/prml_vslam/**/REQUIREMENTS.md`
  - concise package contracts, current-state boundaries, and target-state rules
- `AGENTS.md` and nested `AGENTS.md`
  - repo policy and agent-facing workflow guidance
- `docs/Questions.md`
  - update-sessions related clarification log for challenge scope and intent

## Status

Implemented or functional:

- Streamlit workbench pages for Record3D capture, ADVIO datasets, pipeline runs, and metrics review
- ADVIO local dataset readiness checks, selective downloads, and replay tooling
- TOML-backed run planning and persisted pipeline request loading
- Separate offline and streaming runner paths
- ViSTA-SLAM wrapper
- Rerun live streaming and `.rrd` file export
- Explicit trajectory evaluation when benchmark inputs are available

Not yet implemented or limited:

- real MASt3R backend
- reference reconstruction stage
- cloud and efficiency evaluation execution
- full custom dataset

## Quick Entry

```bash
uv sync --extra dev
uv lock --check
make ci
```

Launch the Streamlit workbench:

```bash
uv sync --extra streaming
uv run streamlit run streamlit_app.py
```

Plan or run a persisted pipeline request:

```bash
uv run prml-vslam plan-run-config .configs/pipelines/advio-15-offline-vista.toml
uv run prml-vslam run-config .configs/pipelines/advio-15-offline-vista.toml
```

Each `run-config` invocation writes a timestamped command log under
`.logs/runs/<run-id>/`, where `<run-id>` is the filesystem-safe run identifier
derived from the config's `experiment_name`. Log filenames use
`YYYY-MM-DD_HH:MM:SS_<run-id>.log`.

See [SETUP.md](SETUP.md) for environment setup and
[src/prml_vslam/pipeline/README.md](src/prml_vslam/pipeline/README.md) for
pipeline TOML details.

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
