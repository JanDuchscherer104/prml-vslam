# arXiv Source Trees

This directory stores extracted arXiv LaTeX source bundles for papers that directly shape the benchmark design in this repository.

## Included papers

- `arXiv-2509.01584/`
  - ViSTA-SLAM: Visual SLAM with Symmetric Two-view Association
  - extracted from the arXiv e-print source bundle for `2509.01584`
- `arXiv-2412.12392/`
  - MASt3R-SLAM: Real-Time Dense SLAM with 3D Reconstruction Priors
  - extracted from the arXiv e-print source bundle for `2412.12392`
- `arXiv-2108.10869/`
  - DROID-SLAM: Deep Visual SLAM for Monocular, Stereo, and RGB-D Cameras
  - extracted from the arXiv e-print source bundle for `2108.10869`
- `arXiv-2308.04079/`
  - 3D Gaussian Splatting for Real-Time Radiance Field Rendering
  - extracted from the arXiv e-print source bundle for `2308.04079`

## Why these sources are kept locally

- to inspect the exact paper contribution statements and method structure
- to recover figure, notation, and pipeline terminology directly from the source
- to anchor our wrapper and stage design to the paper, not only to the GitHub README
- to make future report writing and figure reuse easier

## Most useful files

### ViSTA-SLAM

- `arXiv-2509.01584/main.tex`
- `arXiv-2509.01584/sec/1_2_intro_contribution.tex`
- `arXiv-2509.01584/sec/2_method.tex`

### MASt3R-SLAM

- `arXiv-2412.12392/main.tex`
- `arXiv-2412.12392/supp.tex`

### DROID-SLAM

- `arXiv-2108.10869/main.tex`
- `arXiv-2108.10869/supp.tex`

### 3D Gaussian Splatting

- `arXiv-2308.04079/overview.tex`
- `arXiv-2308.04079/volume_gaussians.tex`
- `arXiv-2308.04079/related.tex`

The repo-level interpretation of these papers lives in:

- `docs/framework-method-research.md`
- `docs/pipeline-wrapper-design.md`
