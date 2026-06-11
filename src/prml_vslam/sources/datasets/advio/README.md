# ADVIO Dataset Guide

This package owns the repository-local adapter for the ADVIO dataset [1]: path
resolution, typed loading of official files, replay preparation, and app-facing
dataset services.

## Current Surface

ADVIO is trajectory-only in this repository. The supported source data is:

- ground-truth trajectory and fixpoints
- iPhone RGB video, timestamps, sensors, calibration, and optional ARKit poses
- Pixel ARCore poses

ADVIO does not expose legacy auxiliary device streams as supported source data,
replay pose providers, reference-cloud sources, or benchmark-input surfaces.
Download actions fetch full scenes rather than partial modality subsets. Dense
reference clouds are prepared by RGB-D datasets such as TUM RGB-D.

## File Conventions

The official ADVIO repository README and the released ZIP archives are close,
but not perfectly identical. In the checked local ADVIO archives under
`.data/advio/`, all 23 sequences use `ground-truth/pose.csv`,
`iphone/gyro.csv`, and `iphone/platform-locations.csv`, whereas the official
README documents `poses.csv`, `gyroscope.csv`, and `platform-location.csv`.

Canonical per-sequence structure used by the adapter:

```text
data/
├── advio-XX/
│   ├── ground-truth/
│   │   ├── pose.csv                  # 6DoF benchmark reference trajectory
│   │   └── fixpoints.csv             # manually marked position fixes
│   ├── iphone/
│   │   ├── frames.mov                # RGB video capture
│   │   ├── frames.csv                # exact frame timestamps for the RGB video
│   │   ├── platform-locations.csv    # geographic / platform location samples
│   │   ├── accelerometer.csv         # raw accelerometer stream
│   │   ├── gyro.csv                  # raw gyroscope stream
│   │   ├── magnetometer.csv          # raw magnetometer stream
│   │   ├── barometer.csv             # pressure and relative altitude samples
│   │   └── arkit.csv                 # ARKit pose stream for the iPhone camera
│   └── pixel/
│       └── arcore.csv                # ARCore pose stream from the Google Pixel
└── calibration/
    ├── iphone-01.yaml                # iPhone intrinsics, distortion, and T_cam_imu
    ├── iphone-02.yaml
    └── ...
```

Repository loader conventions:

- All numeric CSVs are treated as `timestamp, value_1, value_2, ...`.
- ADVIO pose CSVs are loaded into `evo.core.trajectory.PoseTrajectory3D` as:
  - translation: columns `1:4`
  - quaternion: columns `4:8`
  - timestamps: column `0`
- The repository treats `ground-truth/fixpoints.csv` as part of a complete local
  ADVIO scene. It is preserved for source fidelity and local completeness
  checks, but the trajectory loader reads only the pose CSV.
- The calibration YAML is parsed as pinhole intrinsics, image size, distortion
  parameters, and `T_cam_imu`.
- Poses and calibration transforms use
  [`FrameTransform`](../../interfaces/transforms.py) and the canonical
  camera-to-world runtime convention for poses.

## Ground-Truth Fixpoints

`ground-truth/fixpoints.csv` stores the manually marked position fixes used to
build the ADVIO reference trajectory. The paper describes the ground truth as an
iPhone-IMU inertial-navigation estimate conditioned on these manual fixes,
additional calibration, and the external/reference videos and floor plans.
The fixes constrain position only; orientation comes from the inertial
trajectory inference.

In the released CSVs, each row is numeric and starts with the fix timestamp
followed by the metric 3D fix position used by the trajectory optimizer. The
remaining fields preserve the floor-plan marking metadata used by the ADVIO
annotation tooling, such as image-plane marker coordinates and floor or level
identifier. This repository currently preserves the file and uses it for local
scene completeness checks, but does not parse it into a typed runtime model.

## Ground Truth Versus Device Poses

The repository uses ADVIO ground truth as the authoritative benchmark trajectory
and world frame for evaluation and visualization.

- `GT` is the reference trajectory.
- `ARKit` and `ARCore` are optional baseline pose streams in their own provider
  worlds.
- Direct overlays of provider pose CSVs are not scientific cross-system
  comparisons unless an explicit evaluation/alignment stage produces the
  derived comparison artifact.

## Repo Interpretation For Visualization

For the current Streamlit Sequence Explorer:

- provider-world comparison mode shows each available trajectory in its own
  source frame
- local comparison mode normalizes each trajectory by the inverse of its own
  first pose so each track starts at the origin in its own local frame
- ADVIO is displayed as `Y`-up, so the BEV uses the `X-Z` floor plane

Those display transforms are repository-owned visualization choices. They are
not stored as native ADVIO source data.

## References

[1] AaltoVision, "ADVIO: An Authentic Dataset for Visual-Inertial Odometry,"
GitHub repository. Available: https://github.com/AaltoVision/ADVIO

[2] S. Cortes, A. Solin, E. Rahtu, and J. Kannala, "ADVIO: An authentic
dataset for visual-inertial odometry," arXiv:1807.09828, 2018. Available:
https://arxiv.org/abs/1807.09828
