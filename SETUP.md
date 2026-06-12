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

mkdir -p external
git clone https://github.com/Robbyant/lingbot-map.git external/lingbot-map
uv sync --extra lingbot
mkdir -p external/lingbot-map/checkpoints
curl -L https://huggingface.co/robbyant/lingbot-map/resolve/main/lingbot-map.pt \
  -o external/lingbot-map/checkpoints/lingbot-map.pt
```

Validate FlashInfer and the mamba CUDA driver stub before running the full
LingBot benchmark. Use the worktree helper so FlashInfer's JIT linker can find
the mamba CUDA stub library without adding CUDA stubs to `LD_LIBRARY_PATH`:

```bash
prml-vslam-worktree-env run python - <<'PY'
from pathlib import Path
import os
import shutil

import flashinfer
import torch

cuda_home = Path(os.environ["CUDA_HOME"])
stub_dirs = [
    cuda_home / "lib" / "stubs",
    cuda_home / "targets" / "x86_64-linux" / "lib" / "stubs",
]
library_path = os.environ.get("LIBRARY_PATH", "")
library_entries = library_path.split(":")

print("flashinfer:", flashinfer.__file__)
print("nvcc:", shutil.which("nvcc"))
print("CUDAHOSTCXX:", os.environ.get("CUDAHOSTCXX"))
print("NVCC_PREPEND_FLAGS:", os.environ.get("NVCC_PREPEND_FLAGS"))
print("cuda_available:", torch.cuda.is_available())
print("cuda_home:", cuda_home)
print("cuda_stubs:", [str(path / "libcuda.so") for path in stub_dirs])

assert shutil.which("nvcc"), "nvcc is not on PATH"
assert os.environ.get("CUDAHOSTCXX"), "CUDAHOSTCXX is not set to the mamba host compiler"
assert "compiler-bindir" in os.environ.get("NVCC_PREPEND_FLAGS", ""), "nvcc host compiler flag is not set"
assert any((path / "libcuda.so").exists() for path in stub_dirs), "mamba CUDA libcuda.so stub is missing"
assert any(str(path) in library_entries for path in stub_dirs), "CUDA stub dir is missing from LIBRARY_PATH"
assert torch.cuda.is_available(), "PyTorch CUDA is not available"
PY
```

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
