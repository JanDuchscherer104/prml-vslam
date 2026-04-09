# ADVIO Dataset Guide

This package owns the repository-local adapter for the
[ADVIO dataset](https://github.com/AaltoVision/ADVIO): path resolution,
typed loading of official files, replay preparation, and app-facing dataset
services.

The official dataset combines one benchmark reference track with several
device-specific modalities. The most important distinction is that the
ground-truth track is the benchmark reference frame, while ARKit, ARCore, and
Tango pose streams are recorded in their own device-local world frames and must
be aligned before cross-system comparison.

## Sources

- Official dataset repository:
  [AaltoVision/ADVIO](https://github.com/AaltoVision/ADVIO)
- Official paper:
  [ADVIO: An authentic dataset for visual-inertial odometry](https://arxiv.org/abs/1807.09828)
- Repo-owned loader and layout code:
  [`advio_layout.py`](./advio_layout.py),
  [`advio_loading.py`](./advio_loading.py),
  [`advio_sequence.py`](./advio_sequence.py),
  [`advio_replay_adapter.py`](./advio_replay_adapter.py)

## Modality Overview

![ADVIO modality overview](../../../../docs/figures/mermaid/advio-modalities-overview.svg)

Source diagram:
[`docs/figures/mermaid/advio-modalities-overview.mmd`](../../../../docs/figures/mermaid/advio-modalities-overview.mmd)

Practical summary:

- `ground-truth`
  - `pose.csv` or `poses.csv`: 6DoF benchmark reference trajectory
  - `fixpoints.csv`: manually marked position fixes used to build the reference
- `iphone`
  - `frames.mov`, `frames.csv`: RGB video plus exact frame timestamps
  - `arkit.csv`: ARKit pose stream for the iPhone camera
  - `accelerometer.csv`, `gyroscope.csv` or `gyro.csv`,
    `magnetometer.csv`, `barometer.csv`
  - `platform-location.csv` or `platform-locations.csv`: geographic/platform
    location samples
- `pixel`
  - `arcore.csv`: ARCore pose stream from the Google Pixel
- `tango`
  - `raw.csv`: Tango raw odometry
  - `area-learning.csv`: Tango loop-closing/map-building odometry
  - `frames.mov`, `frames.csv`: Tango fisheye video
  - `point-cloud.csv` and `point-cloud-*.csv`: Tango point-cloud capture
- `calibration`
  - `iphone-XX.yaml`: iPhone intrinsics, distortion, and `T_cam_imu`

## File Conventions

The official docs and the released ZIP files are close, but not perfectly
identical. The repository adapter intentionally accepts the known variants
present in the public data.

Canonical per-sequence structure:

```text
data/
  advio-XX/
    ground-truth/
      pose.csv or poses.csv
      fixpoints.csv
    iphone/
      frames.mov
      frames.csv
      platform-location.csv or platform-locations.csv
      accelerometer.csv
      gyroscope.csv or gyro.csv
      magnetometer.csv
      barometer.csv
      arkit.csv
    pixel/
      arcore.csv
    tango/
      frames.mov
      frames.csv
      raw.csv
      area-learning.csv
      point-cloud.csv
      point-cloud-001.csv
      point-cloud-002.csv
      ...
  calibration/
    iphone-01.yaml
    iphone-02.yaml
    ...
```

Repository loader conventions:

- All numeric CSVs are treated as:
  `timestamp, value_1, value_2, ...`
- ADVIO pose CSVs are loaded into `evo.core.trajectory.PoseTrajectory3D` as:
  - translation: columns `1:4`
  - quaternion: columns `4:8`
  - timestamps: column `0`
- The calibration YAML is parsed as:
  - pinhole intrinsics: `fx, fy, cx, cy`
  - image size
  - distortion model and coefficients
  - `T_cam_imu`
- In this repository, poses are handled with camera-to-world semantics through
  [`SE3Pose`](../../interfaces/camera.py).

## Frame And Transform Tree

![ADVIO transform tree](../../../../docs/figures/mermaid/advio-transform-tree.svg)

Source diagram:
[`docs/figures/mermaid/advio-transform-tree.mmd`](../../../../docs/figures/mermaid/advio-transform-tree.mmd)

How to read the tree:

- `GT world` is the benchmark reference frame.
- `ARKit world`, `ARCore world`, `Tango raw world`, and
  `Tango area-learning world` are separate pose-system frames.
- `T_cam_imu` is the main explicit static SE(3) transform shipped in the
  calibration YAML and consumed by this repository.
- Cross-device rig extrinsics are described in the paper as part of the capture
  setup, but they are not surfaced as a canonical repo-owned public transform
  file here.
- Any edge from a device-local world into `GT world` is a derived comparison
  transform, not an official stored ADVIO pose stream.

## Ground Truth Versus Device Poses

The official paper describes the ground-truth as a reference trajectory inferred
from the iPhone IMU, additional calibration, and manually marked fixation
points from an external reference video and floor plans. In practice, the
repository uses it as the authoritative benchmark trajectory and world frame for
evaluation and visualization.

That means:

- `GT` is the reference trajectory.
- `ARKit`, `ARCore`, `Tango/raw`, and `Tango/area-learning` are baseline or auxiliary pose streams.
- Direct overlays of raw pose CSVs are not valid cross-system comparisons until
  an explicit alignment step is applied.

## Repo Interpretation For Visualization

For the current Streamlit Sequence Explorer:

- global comparison mode aligns ARKit and ARCore into the ground-truth frame
  with an SE(3) fit for display
- local comparison mode normalizes each trajectory by the inverse of its own
  first pose so each track starts at the origin in its own local frame
- ADVIO is displayed as `Y`-up, so the BEV uses the `X-Z` floor plane

Those display transforms are repository-owned visualization choices. They are
not stored as native ADVIO modalities.
