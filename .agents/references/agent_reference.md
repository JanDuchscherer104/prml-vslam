# Agent Reference

## Context7 Library IDs

- `/websites/astral_sh_uv` - UV package manager
- `/pydantic/pydantic` - Data validation and settings management
- `/pydantic/pydantic-settings` - Environment-backed application settings
- `/websites/streamlit_io` - Streamlit app framework
- `/plotly/plotly.py` - Plotly Python visualization library
- `/websites/typer_tiangolo` - Typer CLI docs
- `/patrick-kidger/jaxtyping` - Shape-and-dtype annotations for arrays and tensors
- `/dfki-ric/pytransform3d` - Transform and frame-convention handling
- `/nerfstudio-project/nerfstudio` - NeRF and scene-reconstruction tooling
- `/numpy/numpy` - NumPy array computing
- `/opencv/opencv` - OpenCV computer vision library
- `/colmap/colmap` - Structure-from-Motion and Multi-View Stereo reconstruction
- `/cloudcompare/cloudcompare` - Point cloud processing and comparison
- `/isl-org/open3d` - 3D data processing and evaluation
- `/michaelgrupp/evo` - Trajectory evaluation for odometry and SLAM

## Primary Sources

- Pydantic settings docs: <https://docs.pydantic.dev/latest/concepts/pydantic_settings/>
- Plotly graph objects docs: <https://plotly.com/python/graph-objects/>
- PyTorch3D README: <https://github.com/facebookresearch/pytorch3d>
- PyTorch3D batching note: <https://github.com/facebookresearch/pytorch3d/blob/main/docs/notes/batching.md>
- pytransform3d docs: <https://dfki-ric.github.io/pytransform3d/>
- Nerfstudio docs: <https://docs.nerf.studio/>
- Nerfstudio data conventions: <https://docs.nerf.studio/quickstart/data_conventions.html>
- ViSTA-SLAM paper: <https://arxiv.org/abs/2509.01584>
- ViSTA-SLAM repo: <https://github.com/zhangganlin/vista-slam>
- MASt3R-SLAM paper: <https://arxiv.org/abs/2412.12392>
- MASt3R-SLAM repo: <https://github.com/rmurai0610/MASt3R-SLAM>

## Contract Lookup

- Full restructuring rationale, current-state findings, target ownership rules,
  minimal public surface, and migration guidance live in
  `docs/architecture/interfaces-and-contracts.md`.
- One semantic concept should have one owner in the repo.
- Repo-wide shared datamodels live in `prml_vslam.interfaces.*`.
- Repo-wide shared protocols live in `prml_vslam.protocols.*`.
  - `FramePacketStream` is owned by `prml_vslam.protocols.runtime`.
- Package DTOs, enums, configs, manifests, requests, and results belong in
  `<package>/contracts.py`.
- Package-local `Protocol` seams belong in `<package>/protocols.py` when a
  package needs them.
- `prml_vslam.app.models` owns Streamlit-only state.
- `services.py` modules own implementations only.
- Minimal public surface to preserve:
  `CameraIntrinsics`, `SE3Pose`, `TimedPoseTrajectory`, `FramePacket`,
  `RunRequest`, `RunPlan`, `SequenceManifest`, `TrackingArtifacts`,
  `RunSummary`, `OfflineTrackerBackend`, `StreamingTrackerBackend`, `MethodId`
- ViSTA-SLAM and MASt3R-SLAM wrappers should normalize into pipeline-owned
  artifacts instead of exposing upstream-native result layouts or live modes as
  repo-wide contracts.
