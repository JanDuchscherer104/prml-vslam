"""
Data handling module.
"""
from __future__ import annotations
import typing
__all__: list[str] = ['ArmadilloMesh', 'AvocadoModel', 'BedroomRGBDImages', 'BunnyMesh', 'CrateModel', 'DamagedHelmetModel', 'DataDescriptor', 'Dataset', 'DemoColoredICPPointClouds', 'DemoCropPointCloud', 'DemoCustomVisualization', 'DemoDopplerICPSequence', 'DemoFeatureMatchingPointClouds', 'DemoICPPointClouds', 'DemoPoseGraphOptimization', 'DownloadDataset', 'EaglePointCloud', 'FlightHelmetModel', 'JackJackL515Bag', 'JuneauImage', 'KnotMesh', 'LivingRoomPointClouds', 'LoungeRGBDImages', 'MetalTexture', 'MonkeyModel', 'OfficePointClouds', 'PCDPointCloud', 'PLYPointCloud', 'PaintedPlasterTexture', 'RedwoodIndoorLivingRoom1', 'RedwoodIndoorLivingRoom2', 'RedwoodIndoorOffice1', 'RedwoodIndoorOffice2', 'SampleFountainRGBDImages', 'SampleL515Bag', 'SampleNYURGBDImage', 'SampleRedwoodRGBDImages', 'SampleSUNRGBDImage', 'SampleTUMRGBDImage', 'SwordModel', 'TerrazzoTexture', 'TilesTexture', 'WoodFloorTexture', 'WoodTexture', 'open3d_downloads_prefix']
class ArmadilloMesh(DownloadDataset):
    """
    Data class for `ArmadilloMesh` contains the `ArmadilloMesh.ply` from the `Stanford 3D Scanning Repository`.
    """
    def __init__(self, data_root: str = '') -> None:
        ...
    @property
    def path(self) -> str:
        """
        Path to the `ArmadilloMesh.ply` file.
        """
class AvocadoModel(DownloadDataset):
    """
    Data class for `AvocadoModel` contains a avocado model file, along with material and PNG format embedded textures.
    """
    def __init__(self, data_root: str = '') -> None:
        ...
    @property
    def path(self) -> str:
        """
        Path to the `AvocadoModel.glb` file.
        """
class BedroomRGBDImages(DownloadDataset):
    """
    Data class for `BedroomRGBDImages` contains a sample set of 21931 color and depth images from Redwood Bedroom RGBD dataset. Additionally it also contains camera trajectory log, and mesh reconstruction.
    """
    def __init__(self, data_root: str = '') -> None:
        ...
    @property
    def color_paths(self) -> list[str]:
        """
        List of paths to color image samples of size 21931. Use `color_paths[0]`, `color_paths[1]` ... `color_paths[21930]` to access the paths.
        """
    @property
    def depth_paths(self) -> list[str]:
        """
        List of paths to depth image samples of size 21931. Use `depth_paths[0]`, `depth_paths[1]` ... `depth_paths[21930]` to access the paths.
        """
    @property
    def reconstruction_path(self) -> str:
        """
        Path to mesh reconstruction.
        """
    @property
    def trajectory_log_path(self) -> str:
        """
        Path to camera trajectory log file `trajectory.log`.
        """
class BunnyMesh(DownloadDataset):
    """
    Data class for `BunnyMesh` contains the `BunnyMesh.ply` from the `Stanford 3D Scanning Repository`.
    """
    def __init__(self, data_root: str = '') -> None:
        ...
    @property
    def path(self) -> str:
        """
        Path to the `BunnyMesh.ply` file.
        """
class CrateModel(DownloadDataset):
    """
    Data class for `CrateModel` contains a crate model file, along with material and various other texture files. The model file can be accessed using `path`, however in order to access the paths to the texture files one may use path_map["filename"]` method.
    """
    def __init__(self, data_root: str = '') -> None:
        ...
    @property
    def path(self) -> str:
        """
        Returns the `crate` model file.
        """
    @property
    def path_map(self) -> dict[str, str]:
        """
        Returns the map of filename to path. Refer documentation page for available options.
        """
class DamagedHelmetModel(DownloadDataset):
    """
    Data class for `DamagedHelmetModel` contains a damaged helmet model file, along with material and JPG format embedded textures. 
    """
    def __init__(self, data_root: str = '') -> None:
        ...
    @property
    def path(self) -> str:
        """
        Path to the `DamagedHelmetModel.glb` file.
        """
class DataDescriptor:
    """
    DataDescriptor is a class that describes a data file. It contains the URL mirrors to download the file, the MD5 hash of the file, and whether to extract the file.
    """
    @typing.overload
    def __init__(self, urls: list[str], md5: str, extract_in_subdir: str = '') -> None:
        ...
    @typing.overload
    def __init__(self, url: str, md5: str, extract_in_subdir: str = '') -> None:
        ...
    @property
    def extract_in_subdir(self) -> str:
        """
        Subdirectory to extract the file. If empty, the file will be extracted in the root extract directory of the dataset.
        """
    @property
    def md5(self) -> str:
        """
        MD5 hash of the data file.
        """
    @property
    def urls(self) -> list[str]:
        """
        URL to download the data file.
        """
class Dataset:
    """
    The base dataset class.
    """
    def __init__(self, prefix: str, data_root: str = '') -> None:
        ...
    @property
    def data_root(self) -> str:
        """
        Get data root directory. The data root is set at construction time or automatically determined.
        """
    @property
    def download_dir(self) -> str:
        """
        Get absolute path to download directory. i.e. ${data_root}/${download_prefix}/${prefix}
        """
    @property
    def extract_dir(self) -> str:
        """
        Get absolute path to extract directory. i.e. ${data_root}/${extract_prefix}/${prefix}
        """
    @property
    def prefix(self) -> str:
        """
        Get prefix for the dataset.
        """
class DemoColoredICPPointClouds(DownloadDataset):
    """
    Data class for `DemoColoredICPPointClouds` contains 2 point clouds of `ply` format. This dataset is used in Open3D for colored ICP demo.
    """
    def __init__(self, data_root: str = '') -> None:
        ...
    @property
    def paths(self) -> list[str]:
        """
        List of 2 point cloud paths. Use `paths[0]`, and `paths[1]`, to access the paths.
        """
class DemoCropPointCloud(DownloadDataset):
    """
    Data class for `DemoCropPointCloud` contains a point cloud, and `cropped.json` (a saved selected polygon volume file). This dataset is used in Open3D for point cloud crop demo.
    """
    def __init__(self, data_root: str = '') -> None:
        ...
    @property
    def cropped_json_path(self) -> str:
        """
        Path to the saved selected polygon volume file.
        """
    @property
    def point_cloud_path(self) -> str:
        """
        Path to the example point cloud.
        """
class DemoCustomVisualization(DownloadDataset):
    """
    Data class for `DemoCustomVisualization` contains an example point-cloud, camera trajectory (json file), rendering options (json file). This data is used in Open3D for custom visualization with camera trajectory demo.
    """
    def __init__(self, data_root: str = '') -> None:
        ...
    @property
    def camera_trajectory_path(self) -> str:
        """
        Returns path to the camera_trajectory.json.
        """
    @property
    def point_cloud_path(self) -> str:
        """
        Returns path to the point cloud (ply).
        """
    @property
    def render_option_path(self) -> str:
        """
        Returns path to the renderoption.json.
        """
class DemoDopplerICPSequence(DownloadDataset):
    """
    Data class for `DemoDopplerICPSequence` contains an example sequence of 100 point clouds with Doppler velocity channel and corresponding ground truth poses. The sequence was generated using the CARLA simulator.
    """
    def __init__(self, data_root: str = '') -> None:
        ...
    @property
    def calibration_path(self) -> str:
        """
        Path to the calibration metadata file, containing transformation between the vehicle and sensor frames and the time period.
        """
    @property
    def paths(self) -> list[str]:
        """
        Returns list of the point cloud paths in the sequence.
        """
    @property
    def trajectory_path(self) -> str:
        """
        Path to the ground truth poses for the entire sequence.
        """
class DemoFeatureMatchingPointClouds(DownloadDataset):
    """
    Data class for `DemoFeatureMatchingPointClouds` contains 2 pointcloud fragments and their respective FPFH features and L32D features. This dataset is used in Open3D for point cloud feature matching demo.
    """
    def __init__(self, data_root: str = '') -> None:
        ...
    @property
    def fpfh_feature_paths(self) -> list[str]:
        """
        List of 2 saved FPFH feature binary of the respective point cloud paths. Use `fpfh_feature_paths[0]`, and `fpfh_feature_paths[1]`, to access the paths.
        """
    @property
    def l32d_feature_paths(self) -> list[str]:
        """
        List of 2 saved L32D feature binary of the respective point cloud paths. Use `l32d_feature_paths[0]`, and `l32d_feature_paths[1]`, to access the paths.
        """
    @property
    def point_cloud_paths(self) -> list[str]:
        """
        List of 2 point cloud paths. Use `point_cloud_paths[0]`, and `point_cloud_paths[1]`, to access the paths.
        """
class DemoICPPointClouds(DownloadDataset):
    """
    Data class for `DemoICPPointClouds` contains 3 point clouds of binary PCD format. This dataset is used in Open3D for ICP demo.
    """
    def __init__(self, data_root: str = '') -> None:
        ...
    @property
    def paths(self) -> list[str]:
        """
        List of 3 point cloud paths. Use `paths[0]`, `paths[1]`, and `paths[2]` to access the paths.
        """
    @property
    def transformation_log_path(self) -> str:
        """
        Path to the transformation metadata log file, containing transformation between frame 0 and 1, and frame 1 and 2.
        """
class DemoPoseGraphOptimization(DownloadDataset):
    """
    Data class for `DemoPoseGraphOptimization` contains an example fragment pose graph, and global pose graph. This dataset is used in Open3D for pose graph optimization demo.
    """
    def __init__(self, data_root: str = '') -> None:
        ...
    @property
    def pose_graph_fragment_path(self) -> str:
        """
        Path to example global pose graph (json).
        """
    @property
    def pose_graph_global_path(self) -> str:
        """
        Path to example fragment pose graph (json).
        """
class DownloadDataset(Dataset):
    """
    Single file download dataset class.
    """
    def __init__(self, prefix: str, data_descriptor: DataDescriptor, data_root: str = '') -> None:
        ...
class EaglePointCloud(DownloadDataset):
    """
    Data class for `EaglePointCloud` contains the `EaglePointCloud.ply` file.
    """
    def __init__(self, data_root: str = '') -> None:
        ...
    @property
    def path(self) -> str:
        """
        Path to the `EaglePointCloud.ply` file.
        """
class FlightHelmetModel(DownloadDataset):
    """
    Data class for `FlightHelmetModel` contains a flight helmet GLTF model file, along with material and various other texture files. The model file can be accessed using `path`, however in order to access the paths to the texture files one may use path_map["filename"]` method.
    """
    def __init__(self, data_root: str = '') -> None:
        ...
    @property
    def path(self) -> str:
        """
        Returns the `FlightHelmet.gltf` model file.
        """
    @property
    def path_map(self) -> dict[str, str]:
        """
        Returns the map of filename to path. Refer documentation page for available options.
        """
class JackJackL515Bag(DownloadDataset):
    """
    Data class for `SampleL515Bag` contains the `JackJackL515Bag.bag` file.
    """
    def __init__(self, data_root: str = '') -> None:
        ...
    @property
    def path(self) -> str:
        """
        Path to the `JackJackL515Bag.bag` file.
        """
class JuneauImage(DownloadDataset):
    """
    Data class for `JuneauImage` contains the `JuneauImage.jpg` file.
    """
    def __init__(self, data_root: str = '') -> None:
        ...
    @property
    def path(self) -> str:
        """
        Path to the `JuneauImage.jgp` file.
        """
class KnotMesh(DownloadDataset):
    """
    Data class for `KnotMesh` contains the `KnotMesh.ply`.
    """
    def __init__(self, data_root: str = '') -> None:
        ...
    @property
    def path(self) -> str:
        """
        Path to the `KnotMesh.ply` file.
        """
class LivingRoomPointClouds(DownloadDataset):
    """
    Dataset class for `LivingRoomPointClouds` contains 57 point clouds of binary PLY format.
    """
    def __init__(self, data_root: str = '') -> None:
        ...
    @property
    def paths(self) -> list[str]:
        """
        List of paths to ply point-cloud fragments of size 57. Use `paths[0]`, `paths[1]` ... `paths[56]` to access the paths.
        """
class LoungeRGBDImages(DownloadDataset):
    """
    Data class for `LoungeRGBDImages` contains a sample set of 3000 color and depth images from Stanford Lounge RGBD dataset. Additionally it also contains camera trajectory log, and mesh reconstruction.
    """
    def __init__(self, data_root: str = '') -> None:
        ...
    @property
    def color_paths(self) -> list[str]:
        """
        List of paths to color image samples of size 3000. Use `color_paths[0]`, `color_paths[1]` ... `color_paths[2999]` to access the paths.
        """
    @property
    def depth_paths(self) -> list[str]:
        """
        List of paths to depth image samples of size 3000. Use `depth_paths[0]`, `depth_paths[1]` ... `depth_paths[2999]` to access the paths.
        """
    @property
    def reconstruction_path(self) -> str:
        """
        Path to mesh reconstruction.
        """
    @property
    def trajectory_log_path(self) -> str:
        """
        Path to camera trajectory log file `trajectory.log`.
        """
class MetalTexture(DownloadDataset):
    """
    Data class for `MetalTexture` contains albedo, normal, roughness and metallic texture files for metal based material.
    """
    def __init__(self, data_root: str = '') -> None:
        ...
    @property
    def albedo_texture_path(self) -> str:
        """
        Path to albedo color texture image.
        """
    @property
    def metallic_texture_path(self) -> str:
        """
        Path to metallic texture image.
        """
    @property
    def normal_texture_path(self) -> str:
        """
        Path to normal texture image.
        """
    @property
    def path_map(self) -> dict[str, str]:
        """
        Returns the map of filename to path.
        """
    @property
    def roughness_texture_path(self) -> str:
        """
        Path to roughness texture image.
        """
class MonkeyModel(DownloadDataset):
    """
    Data class for `MonkeyModel` contains a monkey model file, along with material and various other texture files. The model file can be accessed using `path`, however in order to access the paths to the texture files one may use path_map["filename"]` method.
    """
    def __init__(self, data_root: str = '') -> None:
        ...
    @property
    def path(self) -> str:
        """
        Returns the `monkey` model file.
        """
    @property
    def path_map(self) -> dict[str, str]:
        """
        Returns the map of filename to path. Refer documentation page for available options.
        """
class OfficePointClouds(DownloadDataset):
    """
    Dataset class for `OfficePointClouds` contains 53 point clouds of binary PLY format.
    """
    def __init__(self, data_root: str = '') -> None:
        ...
    @property
    def paths(self) -> list[str]:
        """
        List of paths to ply point-cloud fragments of size 53. Use `paths[0]`, `paths[1]` ... `paths[52]` to access the paths.
        """
class PCDPointCloud(DownloadDataset):
    """
    Data class for `PCDPointCloud` contains the `fragment.pcd` point cloud mesh from the `Redwood Living Room` dataset.
    """
    def __init__(self, data_root: str = '') -> None:
        ...
    @property
    def path(self) -> str:
        """
        Path to the `pcd` format point cloud.
        """
class PLYPointCloud(DownloadDataset):
    """
    Data class for `PLYPointCloud` contains the `fragment.pcd` point cloud mesh from the `Redwood Living Room` dataset.
    """
    def __init__(self, data_root: str = '') -> None:
        ...
    @property
    def path(self) -> str:
        """
        Path to the `ply` format point cloud.
        """
class PaintedPlasterTexture(DownloadDataset):
    """
    Data class for `PaintedPlasterTexture` contains albedo, normal and roughness texture files for painted plaster based material.
    """
    def __init__(self, data_root: str = '') -> None:
        ...
    @property
    def albedo_texture_path(self) -> str:
        """
        Path to albedo color texture image.
        """
    @property
    def normal_texture_path(self) -> str:
        """
        Path to normal texture image.
        """
    @property
    def path_map(self) -> dict[str, str]:
        """
        Returns the map of filename to path.
        """
    @property
    def roughness_texture_path(self) -> str:
        """
        Path to roughness texture image.
        """
class RedwoodIndoorLivingRoom1(DownloadDataset):
    """
    RedwoodIndoorLivingRoom1 (Augmented ICL-NUIM Dataset)
    Data class for `RedwoodIndoorLivingRoom1`, containing dense point
    cloud, rgb sequence, clean depth sequence, noisy depth sequence, oni
    sequence, and ground-truth camera trajectory. ::
    
        RedwoodIndoorLivingRoom1
        |-- colors
        |   |-- 00000.jpg
        |   |-- 00001.jpg
        |   |-- ...
        |   '-- 02869.jpg
        |-- depth
        |   |-- 00000.png
        |   |-- 00001.png
        |   |-- ...
        |   '-- 02869.png
        |-- depth_noisy
        |   |-- 00000.png
        |   |-- 00001.png
        |   |-- ...
        |   '-- 02869.png
        |-- dist-model.txt
        |-- livingroom1.oni
        |-- livingroom1-traj.txt
        '-- livingroom.ply
    """
    def __init__(self, data_root: str = '') -> None:
        ...
    @property
    def color_paths(self) -> list[str]:
        """
        List of paths to color images.
        """
    @property
    def depth_paths(self) -> list[str]:
        """
        List of paths to depth images.
        """
    @property
    def noise_model_path(self) -> str:
        """
        Path to the noise model file.
        """
    @property
    def noisy_depth_paths(self) -> list[str]:
        """
        List of paths to noisy depth images.
        """
    @property
    def oni_path(self) -> str:
        """
        Path to the oni file.
        """
    @property
    def point_cloud_path(self) -> str:
        """
        Path to the point cloud.
        """
    @property
    def trajectory_path(self) -> str:
        """
        Path to the trajectory file.
        """
class RedwoodIndoorLivingRoom2(DownloadDataset):
    """
    RedwoodIndoorLivingRoom2 (Augmented ICL-NUIM Dataset)
    Data class for `RedwoodIndoorLivingRoom2`, containing dense point
    cloud, rgb sequence, clean depth sequence, noisy depth sequence, oni
    sequence, and ground-truth camera trajectory. ::
    
        RedwoodIndoorLivingRoom2
        |-- colors
        |   |-- 00000.jpg
        |   |-- 00001.jpg
        |   |-- ...
        |   '-- 02349.jpg
        |-- depth
        |   |-- 00000.png
        |   |-- 00001.png
        |   |-- ...
        |   '-- 02349.png
        |-- depth_noisy
        |   |-- 00000.png
        |   |-- 00001.png
        |   |-- ...
        |   '-- 02349.png
        |-- dist-model.txt
        |-- livingroom2.oni
        |-- livingroom2-traj.txt
        '-- livingroom.ply
    """
    def __init__(self, data_root: str = '') -> None:
        ...
    @property
    def color_paths(self) -> list[str]:
        """
        List of paths to color images.
        """
    @property
    def depth_paths(self) -> list[str]:
        """
        List of paths to depth images.
        """
    @property
    def noise_model_path(self) -> str:
        """
        Path to the noise model file.
        """
    @property
    def noisy_depth_paths(self) -> list[str]:
        """
        List of paths to noisy depth images.
        """
    @property
    def oni_path(self) -> str:
        """
        Path to the oni file.
        """
    @property
    def point_cloud_path(self) -> str:
        """
        Path to the point cloud.
        """
    @property
    def trajectory_path(self) -> str:
        """
        Path to the trajectory file.
        """
class RedwoodIndoorOffice1(DownloadDataset):
    """
    RedwoodIndoorOffice1 (Augmented ICL-NUIM Dataset)
    Data class for `RedwoodIndoorOffice1`, containing dense point
    cloud, rgb sequence, clean depth sequence, noisy depth sequence, oni
    sequence, and ground-truth camera trajectory. ::
    
        RedwoodIndoorOffice1
        |-- colors
        |   |-- 00000.jpg
        |   |-- 00001.jpg
        |   |-- ...
        |   '-- 02689.jpg
        |-- depth
        |   |-- 00000.png
        |   |-- 00001.png
        |   |-- ...
        |   '-- 02689.png
        |-- depth_noisy
        |   |-- 00000.png
        |   |-- 00001.png
        |   |-- ...
        |   '-- 02689.png
        |-- dist-model.txt
        |-- office1.oni
        |-- office1-traj.txt
        '-- office.ply
    """
    def __init__(self, data_root: str = '') -> None:
        ...
    @property
    def color_paths(self) -> list[str]:
        """
        List of paths to color images.
        """
    @property
    def depth_paths(self) -> list[str]:
        """
        List of paths to depth images.
        """
    @property
    def noise_model_path(self) -> str:
        """
        Path to the noise model file.
        """
    @property
    def noisy_depth_paths(self) -> list[str]:
        """
        List of paths to noisy depth images.
        """
    @property
    def oni_path(self) -> str:
        """
        Path to the oni file.
        """
    @property
    def point_cloud_path(self) -> str:
        """
        Path to the point cloud.
        """
    @property
    def trajectory_path(self) -> str:
        """
        Path to the trajectory file.
        """
class RedwoodIndoorOffice2(DownloadDataset):
    """
    RedwoodIndoorOffice2 (Augmented ICL-NUIM Dataset)
    Data class for `RedwoodIndoorOffice2`, containing dense point
    cloud, rgb sequence, clean depth sequence, noisy depth sequence, oni
    sequence, and ground-truth camera trajectory. ::
    
        RedwoodIndoorOffice2
        |-- colors
        |   |-- 00000.jpg
        |   |-- 00001.jpg
        |   |-- ...
        |   '-- 02537.jpg
        |-- depth
        |   |-- 00000.png
        |   |-- 00001.png
        |   |-- ...
        |   '-- 02537.png
        |-- depth_noisy
        |   |-- 00000.png
        |   |-- 00001.png
        |   |-- ...
        |   '-- 02537.png
        |-- dist-model.txt
        |-- office2.oni
        |-- office2-traj.txt
        '-- office.ply
    """
    def __init__(self, data_root: str = '') -> None:
        ...
    @property
    def color_paths(self) -> list[str]:
        """
        List of paths to color images.
        """
    @property
    def depth_paths(self) -> list[str]:
        """
        List of paths to depth images.
        """
    @property
    def noise_model_path(self) -> str:
        """
        Path to the noise model file.
        """
    @property
    def noisy_depth_paths(self) -> list[str]:
        """
        List of paths to noisy depth images.
        """
    @property
    def oni_path(self) -> str:
        """
        Path to the oni file.
        """
    @property
    def point_cloud_path(self) -> str:
        """
        Path to the point cloud.
        """
    @property
    def trajectory_path(self) -> str:
        """
        Path to the trajectory file.
        """
class SampleFountainRGBDImages(DownloadDataset):
    """
    Data class for `SampleFountainRGBDImages` contains a sample set of 33 color and depth images from the `Fountain RGBD dataset`. It also contains `camera poses at keyframes log` and `mesh reconstruction`. It is used in demo of `Color Map Optimization`.
    """
    def __init__(self, data_root: str = '') -> None:
        ...
    @property
    def color_paths(self) -> list[str]:
        """
        List of paths to color image samples of size 33. Use `color_paths[0]`, `color_paths[1]` ... `color_paths[32]` to access the paths.
        """
    @property
    def depth_paths(self) -> list[str]:
        """
        List of paths to depth image samples of size 33. Use `depth_paths[0]`, `depth_paths[1]` ... `depth_paths[32]` to access the paths.
        """
    @property
    def keyframe_poses_log_path(self) -> str:
        """
        Path to camera poses at key frames log file `key.log`.
        """
    @property
    def reconstruction_path(self) -> str:
        """
        Path to mesh reconstruction.
        """
class SampleL515Bag(DownloadDataset):
    """
    Data class for `SampleL515Bag` contains the `SampleL515Bag.bag` file.
    """
    def __init__(self, data_root: str = '') -> None:
        ...
    @property
    def path(self) -> str:
        """
        Path to the `SampleL515Bag.bag` file.
        """
class SampleNYURGBDImage(DownloadDataset):
    """
    Data class for `SampleNYURGBDImage` contains a color image `NYU_color.ppm` and a depth image `NYU_depth.pgm` sample from NYU RGBD dataset.
    """
    def __init__(self, data_root: str = '') -> None:
        ...
    @property
    def color_path(self) -> str:
        """
        Path to color image sample.
        """
    @property
    def depth_path(self) -> str:
        """
        Path to depth image sample.
        """
class SampleRedwoodRGBDImages(DownloadDataset):
    """
    Data class for `SampleRedwoodRGBDImages` contains a sample set of 5 color and depth images from Redwood RGBD dataset living-room1. Additionally it also contains camera trajectory log, camera odometry log, rgbd match, and point cloud reconstruction obtained using TSDF.
    """
    def __init__(self, data_root: str = '') -> None:
        ...
    @property
    def camera_intrinsic_path(self) -> str:
        """
        Path to pinhole camera intrinsic (json).
        """
    @property
    def color_paths(self) -> list[str]:
        """
        List of paths to color image samples of size 5. Use `color_paths[0]`, `color_paths[1]` ... `color_paths[4]` to access the paths.
        """
    @property
    def depth_paths(self) -> list[str]:
        """
        List of paths to depth image samples of size 5. Use `depth_paths[0]`, `depth_paths[1]` ... `depth_paths[4]` to access the paths.
        """
    @property
    def odometry_log_path(self) -> str:
        """
        Path to camera odometry log file `odometry.log`.
        """
    @property
    def reconstruction_path(self) -> str:
        """
        Path to pointcloud reconstruction from TSDF.
        """
    @property
    def rgbd_match_path(self) -> str:
        """
        Path to color and depth image match file `rgbd.match`.
        """
    @property
    def trajectory_log_path(self) -> str:
        """
        Path to camera trajectory log file `trajectory.log`.
        """
class SampleSUNRGBDImage(DownloadDataset):
    """
    Data class for `SampleSUNRGBDImage` contains a color image `SUN_color.jpg` and a depth image `SUN_depth.png` sample from SUN RGBD dataset.
    """
    def __init__(self, data_root: str = '') -> None:
        ...
    @property
    def color_path(self) -> str:
        """
        Path to color image sample.
        """
    @property
    def depth_path(self) -> str:
        """
        Path to depth image sample.
        """
class SampleTUMRGBDImage(DownloadDataset):
    """
    Data class for `SampleTUMRGBDImage` contains a color image `TUM_color.png` and a depth image `TUM_depth.png` sample from TUM RGBD dataset.
    """
    def __init__(self, data_root: str = '') -> None:
        ...
    @property
    def color_path(self) -> str:
        """
        Path to color image sample.
        """
    @property
    def depth_path(self) -> str:
        """
        Path to depth image sample.
        """
class SwordModel(DownloadDataset):
    """
    Data class for `SwordModel` contains a monkey model file, along with material and various other texture files. The model file can be accessed using `path`, however in order to access the paths to the texture files one may use path_map["filename"]` method.
    """
    def __init__(self, data_root: str = '') -> None:
        ...
    @property
    def path(self) -> str:
        """
        Returns the `sword` model file.
        """
    @property
    def path_map(self) -> dict[str, str]:
        """
        Returns the map of filename to path. Refer documentation page for available options.
        """
class TerrazzoTexture(DownloadDataset):
    """
    Data class for `TerrazzoTexture` contains albedo, normal and roughness texture files for terrazzo based material.
    """
    def __init__(self, data_root: str = '') -> None:
        ...
    @property
    def albedo_texture_path(self) -> str:
        """
        Path to albedo color texture image.
        """
    @property
    def normal_texture_path(self) -> str:
        """
        Path to normal texture image.
        """
    @property
    def path_map(self) -> dict[str, str]:
        """
        Returns the map of filename to path.
        """
    @property
    def roughness_texture_path(self) -> str:
        """
        Path to roughness texture image.
        """
class TilesTexture(DownloadDataset):
    """
    Data class for `TilesTexture` contains albedo, normal and roughness texture files for tiles based material.
    """
    def __init__(self, data_root: str = '') -> None:
        ...
    @property
    def albedo_texture_path(self) -> str:
        """
        Path to albedo color texture image.
        """
    @property
    def normal_texture_path(self) -> str:
        """
        Path to normal texture image.
        """
    @property
    def path_map(self) -> dict[str, str]:
        """
        Returns the map of filename to path.
        """
    @property
    def roughness_texture_path(self) -> str:
        """
        Path to roughness texture image.
        """
class WoodFloorTexture(DownloadDataset):
    """
     Data class for `WoodFloorTexture` contains albedo, normal and roughness texture files for wooden floor based material.
    """
    def __init__(self, data_root: str = '') -> None:
        ...
    @property
    def albedo_texture_path(self) -> str:
        """
        Path to albedo color texture image.
        """
    @property
    def normal_texture_path(self) -> str:
        """
        Path to normal texture image.
        """
    @property
    def path_map(self) -> dict[str, str]:
        """
        Returns the map of filename to path.
        """
    @property
    def roughness_texture_path(self) -> str:
        """
        Path to roughness texture image.
        """
class WoodTexture(DownloadDataset):
    """
    Data class for `WoodTexture` contains albedo, normal and roughness texture files for wood based material.
    """
    def __init__(self, data_root: str = '') -> None:
        ...
    @property
    def albedo_texture_path(self) -> str:
        """
        Path to albedo color texture image.
        """
    @property
    def normal_texture_path(self) -> str:
        """
        Path to normal texture image.
        """
    @property
    def path_map(self) -> dict[str, str]:
        """
        Returns the map of filename to path.
        """
    @property
    def roughness_texture_path(self) -> str:
        """
        Path to roughness texture image.
        """
open3d_downloads_prefix: str = 'https://github.com/isl-org/open3d_downloads/releases/download/'
