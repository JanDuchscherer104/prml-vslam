# TUM RGB-D Dataset Guide

This package owns the repository-local adapter for the
[TUM RGB-D dataset](https://cvg.cit.tum.de/data/datasets/rgbd-dataset): local
path resolution, typed loading of official list files and trajectories,
RGB-D replay preparation, and app/pipeline-facing dataset services.

The official benchmark combines time-stamped RGB frames, time-stamped depth
frames, and a ground-truth camera trajectory from a motion-capture system. The
most important distinction relative to ADVIO is that TUM RGB-D is already an
RGB-D dataset with pre-registered depth in the RGB camera frame, so the
repository does not need to invent a second sensor-alignment layer to replay
RGB and depth together.

## Sources

- Official dataset page:
  [TUM RGB-D SLAM Dataset and Benchmark](https://cvg.cit.tum.de/data/datasets/rgbd-dataset)
- Official file-format and calibration notes:
  [File Formats](https://cvg.cit.tum.de/data/datasets/rgbd-dataset/file_formats)
- Official tools and association/evaluation scripts:
  [Useful Tools for the RGB-D Benchmark](https://cvg.cit.tum.de/data/datasets/rgbd-dataset/tools)
- Official benchmark paper:
  [A Benchmark for the Evaluation of RGB-D SLAM Systems (IROS 2012)](https://vision.in.tum.de/_media/data/datasets/rgbd-dataset/iros2012.pdf)
- Repo-owned loader and layout code:
  [`tum_rgbd_layout.py`](./tum_rgbd_layout.py),
  [`tum_rgbd_loading.py`](./tum_rgbd_loading.py),
  [`tum_rgbd_sequence.py`](./tum_rgbd_sequence.py),
  [`tum_rgbd_replay_adapter.py`](./tum_rgbd_replay_adapter.py)

## Current Scope

The repository currently exposes the ViSTA-oriented TUM RGB-D subset committed
in [`tum_rgbd_layout.py`](./tum_rgbd_layout.py). That subset includes selected
Freiburg 1/2/3 sequences such as `freiburg1_desk`, `freiburg2_desk`, and
`freiburg3_long_office_household`.

This package preserves the currently supported TUM RGB-D surface:

- RGB image lists and RGB frame replay
- optional aligned depth replay
- ground-truth trajectory export to normalized `.tum` files
- generated intrinsics YAML for pipeline/method compatibility

## Official Capture Characteristics

From the official dataset page and file-format notes:

- RGB-D data was recorded at the Kinect full frame rate of `30 Hz` and
  `640×480` resolution.
- Ground truth was recorded by a motion-capture system at `100 Hz`.
- RGB and depth images are already pre-registered by OpenNI/PrimeSense, so RGB
  pixels and depth pixels correspond `1:1`.
- Depth PNG values are stored as unsigned 16-bit images scaled by `5000`, so a
  raw value of `5000` corresponds to `1.0 m` and `0` means missing data.

The official calibration notes also report Freiburg-specific RGB intrinsics:

- Freiburg 1 RGB: `fx=517.3`, `fy=516.5`, `cx=318.6`, `cy=255.3`
- Freiburg 2 RGB: `fx=520.9`, `fy=521.0`, `cx=325.1`, `cy=249.7`
- Freiburg 3 RGB: `fx=535.4`, `fy=539.2`, `cx=320.1`, `cy=247.6`

The official site lists Freiburg-specific RGB distortion parameters as well and
notes that Freiburg 3 color/IR images were already undistorted, so those
distortion values are zero.

The official file-format page also lists depth correction factors:

- Freiburg 1 depth: `1.035`
- Freiburg 2 depth: `1.031`
- Freiburg 3 depth: `1.000`

The same page states that the released depth images were already pre-scaled
accordingly, so no extra user-side depth correction is required beyond the
standard `depth / 5000` conversion.

## File Conventions

Canonical per-sequence structure:

```text
rgbd_dataset_freiburgX_sequence/
├── rgb/
│   ├── <timestamp>.png             # 640x480 RGB frame
│   └── ...
├── depth/
│   ├── <timestamp>.png             # 640x480 16-bit depth frame
│   └── ...
├── rgb.txt                         # timestamp + relative RGB path
├── depth.txt                       # timestamp + relative depth path
├── groundtruth.txt                 # timestamp tx ty tz qx qy qz qw
└── pose.txt                        # optional GT filename variant in some layouts
```

Repository loader conventions:

- `rgb.txt` and `depth.txt` are parsed as whitespace-separated
  `timestamp relative_path` rows.
- `groundtruth.txt` and `pose.txt` are loaded through the shared TUM trajectory
  parser and treated as the canonical benchmark reference trajectory.
- RGB file rows are mandatory for sequence loading.
- Depth rows are optional at the association level; replay can be configured to
  include or omit depth.
- Ground-truth rows are mandatory for the current TUM sequence adapter because
  the package currently targets benchmark/evaluation-ready scenes.

## Association Semantics

The official tools page notes that Kinect RGB and depth timestamps are not
perfectly synchronized and recommends nearest-timestamp matching with the
`associate.py` helper. The official script defaults to a maximum allowed time
difference of `0.02 s`.

The repository follows the same nearest-neighbor association idea but currently
uses a looser `max_delta_s=0.08` inside
[`load_tum_rgbd_associations()`](./tum_rgbd_loading.py) so one local sequence
load can produce RGB/depth/pose tuples even when the nearest pose/depth sample
is not within the stricter official default.

That means:

- the repository preserves the official timestamped source files
- the repository creates a deterministic local association view for replay
- the repository does not rewrite the original list files in place

## Ground-Truth Frame Semantics

The official file-format notes define each ground-truth row as:

```text
timestamp tx ty tz qx qy qz qw
```

where:

- `tx ty tz` is the position of the optical center of the color camera with
  respect to the mocap world origin
- `qx qy qz qw` is the orientation of that same color-camera optical center
  with respect to the mocap world origin

For this repository, that means:

- TUM ground truth is already a color-camera trajectory, not a separate IMU or
  depth-sensor trajectory
- depth replay should be interpreted in the RGB camera frame because the depth
  images are pre-registered to RGB
- benchmark trajectory evaluation can use the official ground-truth trajectory
  directly after `.tum` normalization

## Calibration And Transform Semantics

The official dataset provides RGB and IR calibration notes, but the repository
normalizes TUM RGB-D intrinsics into a generated `intrinsics.yaml` file through
[`ensure_tum_rgbd_intrinsics_yaml()`](./tum_rgbd_loading.py).

Important repo-specific detail:

- the generated YAML writes an identity `T_cam_imu`

That identity transform is **not** an official TUM RGB-D sensor extrinsic. It
is a repository-owned compatibility placeholder so downstream code that expects
the same calibration YAML shape as ADVIO can still consume TUM RGB-D intrinsics
through one normalized interface.

Callers should therefore treat:

- `intrinsics`: source-backed RGB camera intrinsics
- `T_cam_imu`: repo-owned normalization filler for compatibility, not an
  official published sensor transform

## Depth And Point-Cloud Semantics

Because the official depth images are already registered to RGB and scaled by
`5000`, the repository converts them to metric depth maps by:

```text
depth_m = depth_png / 5000.0
```

This is implemented in [`load_depth_image_m()`](./tum_rgbd_loading.py).

The official tools page also provides a `generate_pointcloud.py` example for
building colored point clouds from one registered RGB/depth pair. The current
repository adapter does not expose a dedicated TUM-native point-cloud artifact
bundle analogous to the ADVIO Tango reference-cloud path; instead it preserves
RGB, depth, intrinsics, and trajectory so downstream stages can derive the
geometry they need.

## Repo Interpretation For Replay

For the current TUM RGB-D replay path:

- `TumRgbdImageSequenceStream` replays RGB frames from `rgb.txt`
- optional depth is loaded from the nearest associated `depth.txt` row
- pose is loaded from the nearest associated ground-truth row
- packet intrinsics are the Freiburg RGB intrinsics (or an explicit
  `intrinsics.txt` override when present)

The stream therefore emits one repository-owned `FramePacket` carrying:

- RGB in the RGB camera raster
- optional metric depth aligned to the same raster
- RGB-camera intrinsics
- optional ground-truth pose of the RGB camera in the mocap world

## Repo Interpretation For Pipeline Inputs

For offline pipeline execution:

- `TumRgbdSequence.to_sequence_manifest()` materializes or reuses an RGB frame
  directory and an `intrinsics.yaml`
- `TumRgbdSequence.to_benchmark_inputs()` exports the official ground truth to a
  normalized `ground_truth.tum`
- the resulting `SequenceManifest` stays RGB-directory-based rather than
  video-based

This keeps TUM RGB-D aligned with the repository’s normalized pipeline surface
without reintroducing raw dataset discovery in downstream stages.
