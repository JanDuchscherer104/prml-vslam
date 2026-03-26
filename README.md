# Challenge 5: Uncalibrated Monocular VSLAM

This repository addresses an off-device monocular VSLAM pipeline for smartphone videos-streams with unknown intrinsics. The goal is to recover a high-precision ego-trajectory and a dense 3D point cloud from raw video, and to benchmark the result against ARCore and other state-of-the-art methods.

## Setup

### Requirements

- [uv](https://docs.astral.sh/uv/getting-started/installation/) package manager
- [typst](https://typst.app/open-source/#download) for slides & report
- [typstyle](https://github.com/typstyle-rs/typstyle/releases) for Typst formatting checks

### Bootstrap

```bash
uv sync --extra dev --extra eval
uv run pre-commit install
uv run pre-commit run --all-files
uv run pytest
make typst-check
```

## Challenge

Professional SLAM systems usually require rigid factory calibration. Consumer frameworks like ARCore are stable due to real-time sensor fusion, but often fail when processing raw video retrospectively. In particular, they struggle with global metric consistency and high-fidelity dense mapping when camera intrinsics are unknown.

The system should build on existing monocular dense VSLAM methods such as [ViSTA-SLAM](https://arxiv.org/pdf/2509.01584) or [MASt3R-SLAM](https://arxiv.org/abs/2412.12392), take a smartphone monocular video stream as input, autonomously handle unknown intrinsics, and output a high-precision trajectory together with a dense 3D point cloud.

## Evaluation

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
