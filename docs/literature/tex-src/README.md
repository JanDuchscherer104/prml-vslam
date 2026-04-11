# arXiv Source Trees

This directory stores extracted arXiv LaTeX source bundles for papers that directly shape the benchmark design in this repository.

## Included papers

- `arXiv-ViSTA-SLAM/`
  - ViSTA-SLAM: Visual SLAM with Symmetric Two-view Association
  - extracted from the arXiv e-print source bundle for `2509.01584`
- `arXiv-MASt3R-SLAM/`
  - MASt3R-SLAM: Real-Time Dense SLAM with 3D Reconstruction Priors
  - extracted from the arXiv e-print source bundle for `2412.12392`
- `arXiv-DROID-SLAM/`
  - DROID-SLAM: Deep Visual SLAM for Monocular, Stereo, and RGB-D Cameras
  - extracted from the arXiv e-print source bundle for `2108.10869`
- `arXiv-ADVIO/`
  - ADVIO: An authentic dataset for visual-inertial odometry.
  - extracted from the arXiv e-print source bundle for `2004.06121`

## Manifest and refresh workflow

The checked-in manifest for this directory lives at:

- `sources.jsonl`

Each JSONL row describes one paper and the local output names needed to fetch its arXiv e-print source tree and, optionally, its PDF. The current schema is:

- required: `arxiv_id`, `tex_dir`
- optional: `title`, `source_url`, `pdf_url`, `pdf_file`

Run the downloader from the repo root:

```bash
uv run python scripts/download_arxiv_tex_src.py docs/literature/tex-src/sources.jsonl
uv run python scripts/download_arxiv_tex_src.py docs/literature/tex-src/sources.jsonl --download-pdfs
```

By default the script writes extracted source trees into `docs/literature/tex-src/` and PDFs into `docs/literature/pdf/`. Use `--overwrite` to replace an existing extracted tree or PDF target.

## Why these sources are kept locally

- to inspect the exact paper contribution statements and method structure
- to recover figure, notation, and pipeline terminology directly from the source
- to anchor our wrapper and stage design to the paper, not only to the GitHub README
- to make future report writing and figure reuse easier

## Most useful files

### ViSTA-SLAM

- `arXiv-ViSTA-SLAM/main.tex`
- `arXiv-ViSTA-SLAM/sec/1_2_intro_contribution.tex`
- `arXiv-ViSTA-SLAM/sec/2_method.tex`

### MASt3R-SLAM

- `arXiv-MASt3R-SLAM/main.tex`
- `arXiv-MASt3R-SLAM/supp.tex`

### DROID-SLAM

- `arXiv-DROID-SLAM/main.tex`
- `arXiv-DROID-SLAM/supp.tex`

The repo-level lookup material for these papers lives in:

- `.agents/references/agent_reference.md`
