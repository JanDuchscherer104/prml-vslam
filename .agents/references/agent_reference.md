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

## Repo Contract Notes

- Pipeline plans are built from `RunRequest.build()` after `RunRequest(...)` is fully specified with nested tracking, stage, and evaluation configs.
- `DenseConfig` and `ReferenceConfig` share one toggle storage shape, while `BenchmarkEvaluationConfig` owns the optional evaluation stage toggles.
- The repository-local metrics surface currently persists one deterministic mock trajectory-comparison result per run and does not expose pose/alignment/scale/tolerance knobs until a real `evo` adapter exists.
- Shared camera, pose, trajectory, and runtime frame contracts live in `prml_vslam.interfaces`.
- `SE3Pose`, `CameraIntrinsics`, `TimedPoseTrajectory`, `FramePacket`, and `FramePacketStream` are the canonical repo-wide datamodels.
