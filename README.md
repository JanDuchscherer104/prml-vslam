# Challenge 5: Uncalibrated Monocular VSLAM

This repository owns the configuration, artifact layout, bounded runtime, evaluation scaffold, and reporting layers for an off-device monocular VSLAM benchmark on smartphone video or streams with unknown intrinsics.

The project goal is to recover a high-precision ego trajectory and dense 3D geometry from raw smartphone video, compare candidate methods against explicit references or optional ARCore baselines, and document the tradeoffs clearly. The current repository scope is narrower than that long-term goal: it already has typed planning contracts, a bounded executable slice, explicit `evo` trajectory evaluation, and reporting assets, while real method wrappers and the full offline or streaming runner surfaces remain target-state work.

The rendered [final report](docs/report/main.typ) and [update-meeting slides](docs/slides/update-meetings/) are available on [GitHub Pages](https://janduchscherer104.github.io/prml-vslam/).

## Setup

### Requirements

- [uv](https://docs.astral.sh/uv/getting-started/installation/) package manager
- [typst](https://typst.app/open-source/#download) for slides and report builds

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
  - human-maintained clarification log for challenge scope and intent
- `docs/architecture/interfaces-and-contracts.md`
  - human-facing ownership and contract rationale

## Markdown Style

- Write Markdown and Quarto prose with semantic wrapping only.
- Do not hard-wrap ordinary paragraphs to a line-length limit.
- Use line breaks only for real structure such as headings, bullets, tables, block quotes, and code fences.

## Streamlit Workbench

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

Both Record3D transports are implemented in the app and the bounded live-source flows. `USB` remains the richer and canonical programmatic ingress: it exposes RGB, depth, confidence, intrinsics, and pose through the native Python bindings. `Wi-Fi Preview` is implemented in Python through the repo-owned WebRTC receiver, but it is lower fidelity and currently lacks pose and confidence parity with `USB`.

Pipeline contract and extension guidance lives in [`src/prml_vslam/pipeline/README.md`](src/prml_vslam/pipeline/README.md).

## TOML-First Run Planning

For durable and reproducible planning, store a [`RunRequest`](src/prml_vslam/pipeline/contracts.py) as TOML under `.configs/pipelines/` and resolve it through the [`plan-run-config`](src/prml_vslam/main.py) CLI command:

```toml
experiment_name = "advio-office-offline-vista"
mode = "offline"
output_dir = ".artifacts"

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
uv run prml-vslam plan-run-config advio-office-vista.toml
```

The TOML shape mirrors the nested [`RunRequest`](src/prml_vslam/pipeline/contracts.py) model: top-level fields configure the run itself, while `[source]`, `[slam]`, `[reference]`, and `[evaluation]` map directly onto the nested config objects owned by [`contracts.py`](src/prml_vslam/pipeline/contracts.py). That is why an optional method-specific backend config path lives in `[slam]` as `config_path = "..."`, because the field is owned by [`SlamConfig`](src/prml_vslam/pipeline/contracts.py) rather than by the top-level request.

[`plan-run-config`](src/prml_vslam/main.py) loads persisted requests through the repo-owned helpers described in [`src/prml_vslam/pipeline/README.md`](src/prml_vslam/pipeline/README.md). The config file itself is resolved through [`PathConfig`](src/prml_vslam/utils/path_config.py), while nested TOML paths are hydrated as written and should be normalized explicitly in runtime code when repo-relative behavior is required.

`compare_to_arcore` is documented here in its current code shape. Today it is the overloaded planner flag that reserves the trajectory-evaluation stage for ARCore comparison; a later refactor can separate “trajectory evaluation enabled” from “baseline selection,” but this README describes the current behavior as implemented.

## Challenge Context

Professional SLAM systems usually require rigid factory calibration. Consumer frameworks such as ARCore are stable because of real-time sensor fusion, but they often fail when raw video is processed retrospectively. In particular, they struggle with global metric consistency and high-fidelity dense mapping when camera intrinsics are unknown.

The long-term system should build on existing monocular dense VSLAM methods such as [ViSTA-SLAM](https://arxiv.org/pdf/2509.01584) or [MASt3R-SLAM](https://arxiv.org/abs/2412.12392), take a smartphone monocular video stream as input, autonomously handle unknown intrinsics, and output a high-precision trajectory together with dense 3D geometry.

ARCore is treated as an optional external baseline when it helps with comparison or bootstrapping, not as a required part of the primary monocular VSLAM pipeline.

## Evaluation Goals

- use [ADVIO](https://github.com/AaltoVision/ADVIO) plus custom self-recorded data
- identify suitable metrics for pose drift and reconstruction fidelity
- evaluate at least two state-of-the-art VSLAM methods
- compare trajectories against available references and optional ARCore baselines
- compare dense geometry against reference reconstructions and optional ARCore maps when those baselines exist
- develop a custom capture or logging workflow for raw video and optional baseline data
- measure efficiency in terms of latency and memory consumption

## Deliverables

- a reproducible off-device monocular VSLAM pipeline for raw smartphone video with unknown intrinsics
- benchmark results for at least two methods, including trajectory and dense reconstruction quality
- a custom dataset capture workflow or app with raw video and optional baseline logs
- an evaluation report covering accuracy, reconstruction quality, latency, and memory consumption
- a final recommendation for the most suitable pipeline in this challenge setting

## Starting Points

- Ground-truth 3D point clouds: [COLMAP](https://colmap.github.io/index.html) + [Meshroom](https://meshroom.org/) or COLMAP + [3DGS](https://learnopencv.com/3d-gaussian-splatting/)
- Point cloud comparison: [CloudCompare](https://www.cloudcompare.org/), with metrics for example from [Open3D](https://www.open3d.org/)
- Trajectory comparison: [evo](https://github.com/MichaelGrupp/evo)
- Papers: [ViSTA-SLAM](https://arxiv.org/pdf/2509.01584), [MASt3R-SLAM](https://arxiv.org/abs/2412.12392)
