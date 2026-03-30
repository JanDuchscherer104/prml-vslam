= Related Work

The initial benchmark focuses on recent monocular dense methods such as ViSTA-SLAM @zhang2026vistaslam
and MASt3R-SLAM @murai2025mast3rslam. These systems provide concrete starting points for recovering
camera motion and dense geometry from monocular inputs while reducing the amount of hand-designed
calibration logic required from the project.

The project also relies on established evaluation and reconstruction tooling. Trajectories are
expected to be compared with evo @grupp2017evo, while reference reconstructions can be built with
COLMAP @schoenberger2016sfm @schoenberger2016mvs and inspected with Open3D @zhou2018open3d.
Nerfstudio is relevant as a downstream neural scene representation and export tool for static-scene
reconstruction, but it should be treated as an external adjunct rather than as a primary monocular
VSLAM backend.
