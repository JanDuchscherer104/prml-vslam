# Work Packages

## WP 0: Project Organisation - Issues
Assignee: Valentin Bumeder
- Create issues for tracking progress of work packages
- Assign Tasks
- Communicate handling of issues to team

## WP 1: Video Source
**Goal:** Capture datasets as input for VSLAM Pipeline.

### WP 1.1: ADVIO Dataset
Assignee: Jan Duchscherer
Output: Dataset containing RGB Video Stream & baseline log data
- review and prepare data from ADVIO dataset for benchmarking of VSLAM Pipeline

### WP 1.2: Mobile Client (Record 3D)
Assignee: Jan Duchscherer
Output: RGB Video Stream
- Setup Workflow for creating sample video data stream incl. baseline logs
- Setup Live Streaming Client for live processing pipeline (Video only)

### WP 1.3: Acquisition of own Dataset
Assignee: Lukas Röß
Output: Dataset containing RGB Video Stream & baseline log data
- record raw monocular video together with baseline logs (ARCore or similar) for custom evaluation data
- provided sample data in reusable format for further usage in pipeline
- format is aligned with ADVIO Dataset format



## WP 2: Uncalibrated Monocular VSLAM Pipeline
**Goal:** Setup livestream-capable uncalibrated monocular VSLAM pipeline with two different VSLAM Algorithms.

### WP 2.1: Pipeline Framework
Assignee(s): Open
- integrate singular services into configurable pipeline workflow
- defined & implemented clear interfaces between services

### WP 2.2: ViSTA-SLAM
Assignees: Lukas Röß, Jan Duchscherer
input: RGB Video Stream
output: incrementally updating Pointcloud & Trajectory
- defined input / output interface for VSLAM algorithms
- setup real-time capable ViSTA-SLAM algorithm

### WP 2.3: MASt3R-SLAM
Assignee: Christopher Kirschner
input: RGB Video Stream
output: incrementally updating Pointcloud & Trajectory
- defined input / output interface for VSLAM algorithms
- setup real-time capable MASt3R-SLAM algorithm

## WP 3: Incremental Streaming (3DGS)
Assignee: Florian Beck
input: VSLAM Pointcloud & Trajectory 
output: 2D/3D visualization of VSLAM output
- implemented service that renders the VSLAM output in 2D / 3D


## WP 4: Metrics - Component Throughput
Assignee: Florian Beck
input: services in pipeline
output: performance metrics (throughput per component)
- setup throughput metric that can be reused over the all components of the pipeline

## WP 5: Metrics - Point Cloud Comparison
Assignees: Valentin Bumeder, Jan Duchscherer, Florian Beck
input: VSLAM point cloud, ground truth point cloud
output: comparison metric
- setup service to create point cloud comparison metrics
- defined input interface


## WP 6: Metrics - Trajectory Comparison
Assignees: Lukas Röß, Valentin Bumeder
input: VSLAM trajectory, ground truth trajectory
output: comparison metric
- setup service to create trajectory comparison metrics
- defined input interface


## WP 7: Metrics - Output Images (Quality)
Assignee: Christopher Kirschner
input: VSLAM image output
- created quality metrics based on VSLAM image output (PSNR or other Standard Reconstruction Metrics)

## WP 8: (Optional) Ground Truth Creation -> Grab if you're bored! 
Assignee(s): Open

## WP 9: (Optional) ARCore - Grab if you're bored! 
Assignee(s): Open
