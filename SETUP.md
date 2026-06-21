# PRML VSLAM Setup

This file owns local environment setup for development, the Streamlit workbench,
and optional ViSTA-SLAM, MASt3R-SLAM, or LingBot-Map GPU execution.

## Requirements

- `git` with submodule support
- [mamba](https://docs.mamba.io/projects/mamba/en/latest/user-guide/install/index.html) or `conda`
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [typst](https://typst.app/open-source/#download) for report and slide builds

## Base Setup

Use this path for repository tooling, tests, docs, and non-ViSTA development:

```bash
git submodule update --init --recursive
uv sync --extra dev
uv run pre-commit install
make ci
```

Optional parallel test runs are available with `pytest-xdist`:

```bash
uv run pytest -n auto
make test PYTEST_ARGS="-n auto"
```

### Install Mamba on Unix

If you are on Unix and already have `conda` or Miniforge installed, you can add
`mamba` with conda-forge:

```bash
conda install -n base -c conda-forge mamba
```

If you do not have `conda` installed, the easiest way to get both `conda` and
`mamba` is to install [Miniforge](https://github.com/conda-forge/miniforge):

```bash
curl -L -O "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-$(uname)-$(uname -m).sh"
bash Miniforge3-$(uname)-$(uname -m).sh
```

For the ViSTA environment setup that uses `environment.yml`, see the ViSTA/CUDA
section below.

## ViSTA/CUDA Setup

The ViSTA integration uses `environment.yml` for native build dependencies that
ordinary Python wheels do not provide:

- `cmake`
- `gcc_linux-64` and `gxx_linux-64`
- `libopencv=4.12.0`, which provides `OpenCVConfig.cmake` for DBoW3Py
- `cuda-nvcc` and `cuda-cudart-dev`, which provide the CUDA compiler and runtime
  headers used by cuROPE

Important:

- When using anything under the `vista` extra, work inside the `prml-vslam`
  mamba environment.
- This applies to `uv sync --extra vista`, ViSTA smoke runs, and the Streamlit
  workbench when launched with `--extra vista`.
- If the active shell is not inside the `prml-vslam` mamba env, expect native
  build or runtime failures such as missing `cmake`, missing OpenCV CMake
  config, or missing CUDA toolchain components.

Primary fresh-environment flow:

```bash
mamba env create -f environment.yml
mamba activate prml-vslam

unset VIRTUAL_ENV
export UV_PROJECT_ENVIRONMENT="$CONDA_PREFIX"

uv sync --extra dev --extra vista --extra streaming
```

Do not use `uv sync --all-extras`: the optional `vista` and `mast3r` extras are
intentionally marked as conflicting because they install separate CUDA SLAM
stacks with different native dependency assumptions.

Quick sanity check before installing or running ViSTA surfaces:

```bash
mamba activate prml-vslam
echo "$CONDA_PREFIX"
which python
which cmake
```

`$CONDA_PREFIX` and `python` should point at the `prml-vslam` mamba env before
you use any `vista` extra commands.

Build the optional CUDA RoPE2D extension after activating the mamba environment; do not install it manually from the submodule:

```bash
uv run python scripts/build_vista_curope.py
```

This helper sets `CUDA_HOME` from the active mamba environment when `nvcc` is
available there. If it cannot find `nvcc`, update or recreate the mamba
environment from `environment.yml`.

### ViSTA Pretrained Files

Download the upstream model weights and ORB vocabulary:

```bash
mkdir -p external/vista-slam/pretrains
curl -L "https://huggingface.co/zhangganlin/vista_slam/resolve/main/frontend_sta_weights.pth?download=true" \
  -o external/vista-slam/pretrains/frontend_sta_weights.pth
curl -L "https://huggingface.co/zhangganlin/vista_slam/resolve/main/ORBvoc.txt?download=true" \
  -o external/vista-slam/pretrains/ORBvoc.txt
```

### Validation

Before running ViSTA, verify the native and Python dependencies:

```bash
find "$CONDA_PREFIX" -name OpenCVConfig.cmake -o -name opencv-config.cmake
which nvcc

uv run --extra vista python - <<'PY'
import torch
import DBoW3Py as dbow

print("cuda_available:", torch.cuda.is_available())
print("DBoW3Py Vocabulary:", dbow.Vocabulary)
PY
```

Run the standard local checks:

```bash
uv lock --check
make ci
```

Optionally run the ViSTA smoke pipeline:

```bash
uv run --extra vista prml-vslam run-config .configs/pipelines/vista-smoke-test.toml
```

## MASt3R/CUDA Setup

Activate the same `prml-vslam` conda environment used above (provides
`cuda-nvcc=12.4`, `gcc_linux-64`, and `libopencv=4.12.0`):

```bash
mamba activate prml-vslam
unset LD_LIBRARY_PATH
export UV_PROJECT_ENVIRONMENT="$CONDA_PREFIX"
```

Install MASt3R-SLAM and its two nested Python packages through the optional
`mast3r` extra. The upstream package builds a CUDA extension and requires the recursive submodule to be present.

```bash
uv sync --extra dev --extra streaming --extra mast3r
```

Optionally enable faster MP4 decoding:

```bash
uv pip install torchcodec==0.1
```

### MASt3R Pretrained Files

Download the upstream NaverLabs checkpoints (weights) into
`external/mast3r-slam/checkpoints/`:

```bash
mkdir -p external/mast3r-slam/checkpoints
wget https://download.europe.naverlabs.com/ComputerVision/MASt3R/MASt3R_ViTLarge_BaseDecoder_512_catmlpdpt_metric.pth \
  -P external/mast3r-slam/checkpoints/
wget https://download.europe.naverlabs.com/ComputerVision/MASt3R/MASt3R_ViTLarge_BaseDecoder_512_catmlpdpt_metric_retrieval_trainingfree.pth \
  -P external/mast3r-slam/checkpoints/
wget https://download.europe.naverlabs.com/ComputerVision/MASt3R/MASt3R_ViTLarge_BaseDecoder_512_catmlpdpt_metric_retrieval_codebook.pkl \
  -P external/mast3r-slam/checkpoints/
```

## LingBot/CUDA Setup

LingBot-Map is installed through the optional `lingbot` extra from an
operator-managed upstream checkout. Clone the checkout, install the extra, and
download the checkpoint at the configured default:

```bash
mamba activate prml-vslam
unset VIRTUAL_ENV
export UV_PROJECT_ENVIRONMENT="$CONDA_PREFIX"
export PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}"

git submodule update --init --recursive external/lingbot-map
uv sync --extra lingbot
mkdir -p external/lingbot-map/checkpoints
curl -L https://huggingface.co/robbyant/lingbot-map/resolve/main/lingbot-map.pt \
  -o external/lingbot-map/checkpoints/lingbot-map.pt
```

## Dataset Downloads and VSLAM Datastore

Dataset-backed pipeline configs and sweeps read from the normalized VSLAM
datastore under `.data/vslam-datastore/<dataset>/`. Build it from complete local
raw dataset caches under `.data/advio/`, `.data/tum_rgbd/`, and `.data/record3d/`.

Download all benchmark scenes:

```bash
uv run prml-vslam advio download
uv run prml-vslam tum-rgbd download
uv run prml-vslam record3d download
```

To limit a download, repeat `--sequence`. ADVIO uses numeric sequence ids,
TUM RGB-D uses scene slugs, and Record3D uses zero-based catalog indices:

```bash
uv run prml-vslam advio download --sequence 15
uv run prml-vslam tum-rgbd download --sequence freiburg3_large_cabinet
uv run prml-vslam record3d download --sequence 0
```

Inspect raw cache and normalized coverage:

```bash
uv run prml-vslam advio summary
uv run prml-vslam tum-rgbd summary
uv run prml-vslam record3d summary
```

Build the full normalized benchmark datastore used by the full sweep files:

```bash
uv run prml-vslam dataset normalize --config .configs/datasets/benchmark-vslam-datastore.toml
```

The checked-in datastore config covers 50 benchmark sequences: 23 ADVIO, 19
TUM RGB-D, and 8 Record3D scenes. It owns the normalize-time frame cadence,
RGB resizing, and reference-cloud settings for each dataset group.

Verify the built entries before running sweeps or dataset-backed pipelines:

```bash
uv run prml-vslam dataset summary --dataset advio
uv run prml-vslam dataset summary --dataset tum_rgbd
uv run prml-vslam dataset summary --dataset record3d
```

Use `--overwrite` on the dataset download commands only when refreshing cached
archives intentionally. The default `--reuse` mode keeps already-downloaded
archives and extracted scenes.

## Dataset × Method Sweep

The sweep feature runs a cross-product of datasets and methods through the
existing single-run pipeline, writing local artifacts only.  No aggregation,
dashboards, or W&B integration are included.

### Sweep TOML

A sweep is described by a single TOML file with three sections:

```toml
[sweep]
name       = "vista-vs-mast3r"   # prefix for all run IDs
output_dir = ".artifacts/sweeps" # shared artifact root

# One [[datasets]] block per dataset/sequence combination.
[[datasets]]
dataset_id          = "tum_rgbd"              # "tum_rgbd" | "advio"
sequence_id         = "freiburg3_large_cabinet"
frame_stride        = 1
normalized_target_fps = 30.0                  # persisted datastore profile cadence
baseline_source     = "ground_truth"          # ReferenceSource enum value
align_ground        = true
align_trajectory    = true
evaluate_trajectory = true
reconstruction      = false
align_cloud         = false
evaluate_cloud      = false

[[datasets]]
dataset_id          = "advio"
sequence_id         = "advio-15"
frame_stride        = 2
normalized_target_fps = 15.0
baseline_source     = "ground_truth"
align_trajectory    = true
evaluate_trajectory = true

# One [methods.<id>] block per SLAM method.
# Only [stages.slam] is read from each template; all other sections are ignored.
[methods.vista]
config_path = ".configs/templates/vista-slam.toml"

[methods.mast3r]
config_path = ".configs/templates/mast3r-slam.toml"
```

Run IDs are derived deterministically:
`{sweep.name}-{dataset_id}-{sequence_id}-{method_id}`

### Method Templates

A method template is a standard pipeline TOML that must contain
`[stages.slam]`.  All other sections are silently ignored by the sweep loader.

```toml
# .configs/templates/vista-slam.toml
[stages.slam]
enabled  = true
num_gpus = 1.0

    [stages.slam.outputs]
    emit_dense_points  = true
    emit_sparse_points = false

    [stages.slam.backend]
    method_id   = "vista"
    max_frames  = 50
    random_seed = 43
```

Ready-to-use templates live in `.configs/templates/`.

### CLI Commands

Inspect the expanded plan without executing (no GPU required, works for any sweep):

```bash
uv run prml-vslam plan-sweep-config .configs/sweeps/<sweep>.toml
```

Each run writes its own timestamped log under `.logs/runs/<run-id>/` and its
artifacts under `[sweep].output_dir`.  Artifacts from summary stages under
`summary/run-events.jsonl` remain the only source of truth for downstream query
and aggregation.  Sweep artifacts are discovered automatically by the Streamlit
app via its recursive artifact scan.

### ViSTA sweeps

```bash
mamba activate prml-vslam
export UV_PROJECT_ENVIRONMENT="$CONDA_PREFIX"

# 5-sequence example (2 TUM + 2 ADVIO + 1 Record3D)
uv run --extra vista prml-vslam run-sweep-config .configs/sweeps/example-vista-sweep.toml

# All 50 normalized benchmark sequences
uv run --extra vista prml-vslam run-sweep-config .configs/sweeps/full-vista-sweep.toml \
    --continue-on-failure
```

### MASt3R sweeps

Requires a separate install (conflicts with `vista` and `lingbot`):

```bash
mamba activate prml-vslam
export UV_PROJECT_ENVIRONMENT="$CONDA_PREFIX"
uv sync --extra dev --extra streaming --extra mast3r

# 5-sequence example (2 TUM + 2 ADVIO + 1 Record3D)
uv run --extra mast3r prml-vslam run-sweep-config .configs/sweeps/example-mast3r-sweep.toml

# All 50 normalized benchmark sequences
uv run --extra mast3r prml-vslam run-sweep-config .configs/sweeps/full-mast3r-sweep.toml \
    --continue-on-failure
```

### LingBot sweeps

Requires a separate install (conflicts with `vista` and `mast3r`).  LingBot is
trained within ~320 direct-mode views; the sweep files use higher frame strides
(TUM ×5, ADVIO ×10) to stay within that range.

```bash
mamba activate prml-vslam
export UV_PROJECT_ENVIRONMENT="$CONDA_PREFIX"
uv sync --extra dev --extra streaming --extra lingbot

# 5-sequence example (2 TUM + 2 ADVIO + 1 Record3D)
uv run --extra lingbot prml-vslam run-sweep-config .configs/sweeps/example-lingbot-sweep.toml

# All 50 normalized benchmark sequences
uv run --extra lingbot prml-vslam run-sweep-config .configs/sweeps/full-lingbot-sweep.toml \
    --continue-on-failure
```

### Sweep file reference

| File | Method | Sequences |
|---|---|---|
| `example-vista-sweep.toml` | ViSTA | 5 (2 TUM + 2 ADVIO + 1 Record3D) |
| `example-mast3r-sweep.toml` | MASt3R | 5 (2 TUM + 2 ADVIO + 1 Record3D) |
| `example-lingbot-sweep.toml` | LingBot | 5 (2 TUM + 2 ADVIO + 1 Record3D) |
| `full-vista-sweep.toml` | ViSTA | 50 (19 TUM + 23 ADVIO + 8 Record3D) |
| `full-mast3r-sweep.toml` | MASt3R | 50 (19 TUM + 23 ADVIO + 8 Record3D) |
| `full-lingbot-sweep.toml` | LingBot | 50 (19 TUM + 23 ADVIO + 8 Record3D) |

Build and verify the normalized benchmark datastore before running the full
sweeps; see
[Dataset Downloads and VSLAM Datastore](#dataset-downloads-and-vslam-datastore).

## Streamlit Workbench

For the Streamlit app without ViSTA:

```bash
uv run prml-vslam app
```

## Codex History Utilities

Use the repo-local helper under `.agents/scripts/` to refresh the Codex history
exports and inspect one session by id:

```bash
python3 .agents/scripts/codex_history.py update
python3 .agents/scripts/codex_history.py conversation 019da090-0d2b-72b2-aa63-dc0a4ecfaf44 --speaker both --write-default
python3 .agents/scripts/codex_history.py overview 019da090-0d2b-72b2-aa63-dc0a4ecfaf44
```

What each command does:

- `update`
  - refreshes `codex-messages-prml-vslam.jsonl` and
    `codex-user-messages-prml-vslam.jsonl` from the raw Codex session store
- `conversation <session-id>`
  - fetches the full conversation for one session directly from the raw session
    file
  - `--speaker user|agent|both` filters the visible roles
  - `--format md|jsonl` chooses Markdown or JSONL output
  - `--write-default` writes the result to the default repo-root file such as
    `codex-session-<id>-messages.md`
- `overview <session-id>`
  - prints a minimal session summary including message counts, patch-touched
    files, successful verification commands, and the last final-answer summary

## MemPalace

MemPalace is installed into the repo `.venv` and exposed through a repo-local
Codex plugin plus a repo-local skill wrapper.

Refresh the repo-local palace for docs and Codex chat histories:

```bash
python3 .agents/skills/mempalace-repo/scripts/mempalace_repo.py refresh
```

Inspect or query the repo-local palace:

```bash
python3 .agents/skills/mempalace-repo/scripts/mempalace_repo.py status
python3 .agents/skills/mempalace-repo/scripts/mempalace_repo.py search "ViewCoordinates.RDF"
python3 .agents/skills/mempalace-repo/scripts/mempalace_repo.py wake-up
```

Codex sessions also run a repo-local startup hook that starts a background
refresh and prints wake-up context. The hook entry lives in `.codex/hooks.json`;
the script is `.agents/scripts/mempalace_startup_context.sh`.
