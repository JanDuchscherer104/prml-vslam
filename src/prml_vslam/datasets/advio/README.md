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

## File Conventions

The official ADVIO repository README and the released ZIP archives are close,
but not perfectly identical. In the checked local ADVIO archives under
`.data/advio/`, all 23 sequences use `ground-truth/pose.csv`,
`iphone/gyro.csv`, and `iphone/platform-locations.csv`, whereas the official
README documents `poses.csv`, `gyroscope.csv`, and `platform-location.csv`.
The repository adapter intentionally accepts both spellings where needed, but
the examples below prefer the names present in the released archives.

Canonical per-sequence structure:

```text
data/
├── advio-XX/
│   ├── ground-truth/
│   │   ├── pose.csv                  # 6DoF benchmark reference trajectory in the released archives
│   │   └── fixpoints.csv             # manually marked position fixes used to build the reference
│   ├── iphone/
│   │   ├── frames.mov                # RGB video capture
│   │   ├── frames.csv                # exact frame timestamps for the RGB video
│   │   ├── platform-locations.csv    # geographic / platform location samples
│   │   ├── accelerometer.csv         # raw accelerometer stream
│   │   ├── gyro.csv                  # raw gyroscope stream
│   │   ├── magnetometer.csv          # raw magnetometer stream
│   │   ├── barometer.csv             # pressure and relative altitude samples
│   │   └── arkit.csv                 # ARKit pose stream for the iPhone camera
│   ├── pixel/
│   │   └── arcore.csv                # ARCore pose stream from the Google Pixel
│   └── tango/
│       ├── frames.mov                # Tango fisheye video
│       ├── frames.csv                # exact frame timestamps for the fisheye video
│       ├── raw.csv                   # Tango raw odometry
│       ├── area-learning.csv         # Tango loop-closing / map-building odometry
│       ├── point-cloud.csv           # point-cloud timestamps / index table
│       ├── point-cloud-001.csv       # Tango point-cloud capture
│       ├── point-cloud-002.csv       # Tango point-cloud capture
│       └── ...
└── calibration/
    ├── iphone-01.yaml                # iPhone intrinsics, distortion, and T_cam_imu
    ├── iphone-02.yaml
    └── ...
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
