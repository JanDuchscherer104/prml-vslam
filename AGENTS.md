# PRML VSLAM Agent Guidance

This file orients coding agents and contributors working in this repository.
<!-- TODO: Add concise but exhaustive description of the project goals and deliverables -->

## Repo Map

- Project overview: `README.md` (read for broader context awareness)
- `docs/Questions.md` is another groundtruth.
- `src/prml_vslam/`: installable Python package
- `tests/`: pytests
- `docs/report/main.typ`: report entry point
- `docs/slides/update-meetings/update-slides.typ`: unified weekly update meeting deck
- `docs/slides/update-meetings/meeting-0X/*.typ`: meeting-local contributor fragments and shared content
- Python venv: `.venv/bin/python`

## Instructions

- Use [conventional commits](https://www.conventionalcommits.org/en/v1.0.0/#summary) with concise and descriptive messages for focused and self-contained commits.
- For larger changes, break down into multiple commits that each represent a single logical change or step
- Read and follow the nearest nested `AGENTS.md` before editing.
  - Python code and module-local instructions: `src/prml_vslam/`
  - Instructions on our docs (i.e. slides, report) in `docs/AGENTS.md`
- Do not use `git restore`, `git reset --hard` or other destructive commands unless explicitly requested.
- *NEVER* implement functionalities or modifications which are not clearly cotained within the scope of your task.

## Context7 Library Index
<!-- TODO: move this to a separate file -->
- `/pydantic/pydantic` - Data validation and settings management
- `/websites/typst_app` - Presentations and publications
- `/websites/astral_sh_uv` - UV package manager
- `/colmap/colmap` - Structure-from-Motion and Multi-View Stereo reconstruction
- `/alicevision/meshroom` - Photogrammetry pipeline and 3D reconstruction
- `/graphdeco-inria/gaussian-splatting` - 3D Gaussian Splatting for scene reconstruction
- `/cloudcompare/cloudcompare` - Point cloud processing and comparison
- `/isl-org/open3d` - 3D data processing and evaluation
- `/michaelgrupp/evo` - Trajectory evaluation for odometry and SLAM
