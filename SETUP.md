# PRML VSLAM Setup

This file owns local environment setup for development, the Streamlit workbench,
and optional ViSTA-SLAM GPU execution.

## Requirements

- `git` with submodule support
- [conda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html) or `mamba`
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

## ViSTA/CUDA Setup

The ViSTA integration uses `environment.yml` for native build dependencies that
ordinary Python wheels do not provide:

- `cmake`
- `gcc_linux-64` and `gxx_linux-64`
- `libopencv=4.12.0`, which provides `OpenCVConfig.cmake` for DBoW3Py
- `cuda-nvcc` and `cuda-cudart-dev`, which provide the CUDA compiler and runtime
  headers used by cuROPE

Primary fresh-environment flow:

```bash
conda env create -f environment.yml
conda activate prml-vslam

unset VIRTUAL_ENV
export UV_PROJECT_ENVIRONMENT="$CONDA_PREFIX"

uv sync --all-extras
# uv sync --extra dev --extra vista --extra streaming
```

Build the optional CUDA RoPE2D extension after activating the conda environment; do not install it manually from the submodule:

```bash
uv run python scripts/build_vista_curope.py
```

This helper sets `CUDA_HOME` from the active conda environment when `nvcc` is
available there. If it cannot find `nvcc`, update or recreate the conda
environment from `environment.yml`.

## ViSTA Pretrained Files

Download the upstream model weights and ORB vocabulary:

```bash
mkdir -p external/vista-slam/pretrains
curl -L "https://huggingface.co/zhangganlin/vista_slam/resolve/main/frontend_sta_weights.pth?download=true" \
  -o external/vista-slam/pretrains/frontend_sta_weights.pth
curl -L "https://huggingface.co/zhangganlin/vista_slam/resolve/main/ORBvoc.txt?download=true" \
  -o external/vista-slam/pretrains/ORBvoc.txt
```

## Validation

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

conda activate prml-vslam
unset LD_LIBRARY_PATH
export UV_PROJECT_ENVIRONMENT="$CONDA_PREFIX"


Install MASt3R-SLAM and its two nested Python packages as editable installs
into the project environment. They are not listed in `pyproject.toml` because
they require the submodule to be present at install time:

    uv pip install --no-build-isolation -e external/mast3r-slam/thirdparty/mast3r
    uv pip install --no-build-isolation -e external/mast3r-slam/thirdparty/in3d
    uv pip install --no-build-isolation -e external/mast3r-slam

Optionally enable faster MP4 decoding:

    uv pip install torchcodec==0.1

## MASt3R Pretrained Files

Download the upstream NaverLabs checkpoints (weigths) into
`external/mast3r-slam/checkpoints/`:

    mkdir -p external/mast3r-slam/checkpoints
    wget https://download.europe.naverlabs.com/ComputerVision/MASt3R/MASt3R_ViTLarge_BaseDecoder_512_catmlpdpt_metric.pth \
      -P external/mast3r-slam/checkpoints/
    wget https://download.europe.naverlabs.com/ComputerVision/MASt3R/MASt3R_ViTLarge_BaseDecoder_512_catmlpdpt_metric_retrieval_trainingfree.pth \
      -P external/mast3r-slam/checkpoints/
    wget https://download.europe.naverlabs.com/ComputerVision/MASt3R/MASt3R_ViTLarge_BaseDecoder_512_catmlpdpt_metric_retrieval_codebook.pkl \
      -P external/mast3r-slam/checkpoints/


## Streamlit Workbench

For the Streamlit app without ViSTA:

```bash
uv sync --extra streaming
uv run streamlit run streamlit_app.py
```

For the Streamlit app with ViSTA and Rerun support, complete the ViSTA/CUDA setup
above, then run:

```bash
uv run --extra vista --extra streaming streamlit run streamlit_app.py
```
