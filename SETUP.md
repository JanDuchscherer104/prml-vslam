# PRML VSLAM Setup

This file owns local environment setup for development, the Streamlit workbench,
and optional ViSTA-SLAM, MASt3R-SLAM, or LingBot-Map GPU execution.

## Requirements

- `git` with submodule support
- [mamba](https://docs.mamba.io/projects/mamba/en/latest/user-guide/install/index.html) or `conda`
- [typst](https://typst.app/open-source/#download) for report and slide builds

## Base Setup

Use this path for repository tooling, tests, docs, and non-ViSTA development:

```bash
git submodule update --init --recursive
uv sync --extra dev
uv run pre-commit install
make ci
```

## GPU Method Setup

The ViSTA, MASt3R, and LingBot GPU integrations use conflicting optional
Python dependency graphs, but they can share one mamba environment for native
toolchain dependencies. Use mamba for `cmake`, compiler wrappers, OpenCV CMake
files, CUDA headers, and `nvcc`; let uv manage the active Python method graph
in the project `.venv`.

```bash
mamba env create -f environment.yml
mamba activate prml-vslam
```

Quick sanity check before installing or running ViSTA surfaces:

```bash
mamba activate prml-vslam
echo "$CONDA_PREFIX"
which python
which uv
which cmake
which nvcc
```

`$CONDA_PREFIX`, `python`, `uv`, `cmake`, and `nvcc` should point at the
`prml-vslam` mamba env before you use any GPU method extra commands.

**Important:**

- When using anything under the one of the vSLAM extras, i.e., `vista`, `mast3r`, or `lingbot`, the mamba env
`prml-vslam` must be activated first. Otherwise, the extra will not be installed correctly.
- uv mutates the same `.venv` to match the selected method. This is expected:
for example, switching from `mast3r` to `lingbot` removes MASt3R-only packages
and installs LingBot-only packages.
- If a native package fails after switching mamba environments, remove generated
native build caches before retrying. CMake caches absolute compiler and OpenCV
paths:

```bash
rm -rf external/vista-slam/DBoW3Py/build
rm -rf external/vista-slam/DBoW3Py/*.egg-info
```

## ViSTA/CUDA Setup

The ViSTA integration uses `environment.yml` for native build dependencies that
ordinary Python wheels do not provide:

- `cmake`
- `gcc_linux-64` and `gxx_linux-64`
- `libopencv=4.12.0`, which provides `OpenCVConfig.cmake` for DBoW3Py
- `cuda-nvcc` and `cuda-cudart-dev`, which provide the CUDA compiler and runtime
  headers used by cuROPE

Create and activate the shared mamba environment from `environment.yml` if you have not already done so, then sync the
ViSTA extra into the project `.venv`:

```bash
# mamba env create -f environment.yml
mamba activate prml-vslam
uv sync --extra dev --extra vista --extra streaming
```

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

Optionally run the local CI checks and the ViSTA smoke pipeline:

```bash
uv run --extra vista prml-vslam run-config .configs/pipelines/vista-smoke-test.toml
```

### Resolving DBoW3Py Compilation Error

If a native package fails after switching mamba environments, remove generated
native build caches before retrying. CMake caches absolute compiler and OpenCV
paths:

```bash
rm -rf external/vista-slam/DBoW3Py/build
rm -rf external/vista-slam/DBoW3Py/*.egg-info
```

Then retry the `uv sync` command with the `vista` extra.

## MASt3R/CUDA Setup

Create and activate the shared mamba environment from `environment.yml` if you have not already done so:

```bash
# mamba env create -f environment.yml
mamba activate prml-vslam
```

Install MASt3R-SLAM and its two nested Python packages through the optional
`mast3r` extra. The upstream package builds a CUDA extension and requires the recursive submodule to be present.

```bash
uv sync --extra dev --extra streaming --extra mast3r
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

### Validation

Run the MASt3R smoke pipeline:

```bash
uv run --extra mast3r prml-vslam run-config .configs/pipelines/advio-15-offline-mast3r-smoke.toml
```

**Note**: This requires the _normalized_ vslam-datastore entry of `advio-15` to be present. See [Dataset Downloads and VSLAM Datastore](#dataset-downloads-and-vslam-datastore) for details.

## LingBot/CUDA Setup

LingBot-Map is installed through the optional `lingbot` extra from an
operator-managed upstream checkout. Clone the checkout, install the extra, and
download the checkpoint at the configured default:

```bash
# mamba env create -f environment.yml
mamba activate prml-vslam

# If you have not already updated the submodules:
# git submodule update --init --recursive external/lingbot-map
uv sync --extra dev --extra streaming --extra lingbot
mkdir -p external/lingbot-map/checkpoints
curl -L https://huggingface.co/robbyant/lingbot-map/resolve/main/lingbot-map.pt \
  -o external/lingbot-map/checkpoints/lingbot-map.pt
```

Run the LingBot smoke pipeline:

```bash
uv run --extra lingbot prml-vslam run-config .configs/pipelines/lingbot-smoke.toml
```

**Note**: This requires the _normalized_ vslam-datastore entry of `freiburg3_large_cabinet` to be present. See [Dataset Downloads and VSLAM Datastore](#dataset-downloads-and-vslam-datastore) for details.

## Dataset Downloads and VSLAM Datastore

Dataset-backed pipeline configs and sweeps read from the normalized VSLAM
datastore under `.data/vslam-datastore/<dataset>/`. Build it from complete local
raw dataset caches under `.data/advio/`, `.data/tum_rgbd/`, and `.data/record3d/`.

Download select sequences, repeat `--sequence`. ADVIO uses numeric sequence ids,
TUM RGB-D uses scene slugs, and Record3D uses zero-based catalog indices:

```bash
uv run prml-vslam advio download --sequence 15
uv run prml-vslam tum-rgbd download --sequence freiburg3_large_cabinet
uv run prml-vslam record3d download --sequence 0
```

Download all benchmark scenes:

```bash
uv run prml-vslam advio download # 2.7GB
uv run prml-vslam tum-rgbd download # 11GB
uv run prml-vslam record3d download # 21GB
```

The Record3D samples will be persisted to

```
.data/record3d
├── 2026-06-03--18-17-10.r3d # sequence 0
├── 2026-06-03--18-20-22.r3d
├── 2026-06-03--18-24-27.r3d
├── 2026-06-03--18-26-32.r3d
├── 2026-06-03--18-27-25.r3d
├── 2026-06-03--18-29-08.r3d
├── 2026-06-03--18-32-27.r3d
└── 2026-06-03--18-35-44.r3d # sequence 7
```

Build the full normalized benchmark datastore used by the full sweep files:

```bash
uv run prml-vslam dataset normalize --config .configs/datasets/benchmark-vslam-datastore.toml
```

**Note**: You can simply comment out any sequences or dataset sections in the TOML to skip them.
Single sequences can be normalized directly via cli:

```bash
uv run prml-vslam dataset normalize \
  --dataset record3d \ #  advio, tum_rgbd, or record3d
  --sequence 2026-06-03--18-17-10 \ # stem of the original .r3d filename or directoy name for TUM or ADVIO
  --target-fps 15
```

The checked-in datastore config covers 50 benchmark sequences: 23 ADVIO, 19
TUM RGB-D, and 8 Record3D scenes. It owns the normalize-time frame cadence,
RGB resizing, and reference-cloud settings for each dataset group.

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
uv sync --extra dev --extra streaming --extra vista

# 5-sequence example (2 TUM + 2 ADVIO + 1 Record3D)
uv run --extra vista prml-vslam run-sweep-config .configs/sweeps/example-vista-sweep.toml

# All 50 normalized benchmark sequences
uv run --extra vista prml-vslam run-sweep-config .configs/sweeps/full-vista-sweep.toml \
    --continue-on-failure
```

### MASt3R sweeps

Switch the project `.venv` to MASt3R before running MASt3R sweeps:

```bash
mamba activate prml-vslam
uv sync --extra dev --extra streaming --extra mast3r

# 5-sequence example (2 TUM + 2 ADVIO + 1 Record3D)
uv run --extra mast3r prml-vslam run-sweep-config .configs/sweeps/example-mast3r-sweep.toml

# All 50 normalized benchmark sequences
uv run --extra mast3r prml-vslam run-sweep-config .configs/sweeps/full-mast3r-sweep.toml \
    --continue-on-failure
```

### LingBot sweeps

Switch the project `.venv` to LingBot before running LingBot sweeps. LingBot is
trained within ~320 direct-mode views; the sweep files use higher frame strides
(TUM ×5, ADVIO ×10) to stay within that range.

```bash
mamba activate prml-vslam
uv sync --extra dev --extra streaming --extra lingbot

# 5-sequence example (2 TUM + 2 ADVIO + 1 Record3D)
uv run --extra lingbot prml-vslam run-sweep-config .configs/sweeps/example-lingbot-sweep.toml

# All 50 normalized benchmark sequences
uv run --extra lingbot prml-vslam run-sweep-config .configs/sweeps/full-lingbot-sweep.toml \
    --continue-on-failure
```

### Sweep file reference

| File                         | Method  | Sequences                           |
| ---------------------------- | ------- | ----------------------------------- |
| `example-vista-sweep.toml`   | ViSTA   | 5 (2 TUM + 2 ADVIO + 1 Record3D)    |
| `example-mast3r-sweep.toml`  | MASt3R  | 5 (2 TUM + 2 ADVIO + 1 Record3D)    |
| `example-lingbot-sweep.toml` | LingBot | 5 (2 TUM + 2 ADVIO + 1 Record3D)    |
| `full-vista-sweep.toml`      | ViSTA   | 50 (19 TUM + 23 ADVIO + 8 Record3D) |
| `full-mast3r-sweep.toml`     | MASt3R  | 50 (19 TUM + 23 ADVIO + 8 Record3D) |
| `full-lingbot-sweep.toml`    | LingBot | 50 (19 TUM + 23 ADVIO + 8 Record3D) |

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
