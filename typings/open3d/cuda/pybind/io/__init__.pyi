from __future__ import annotations
import open3d.cuda.pybind.camera
import open3d.cuda.pybind.geometry
import open3d.cuda.pybind.pipelines.registration
import open3d.cuda.pybind.visualization.rendering
import os
import typing
from . import rpc

__all__: list[str] = [
    "AzureKinectMKVMetadata",
    "AzureKinectMKVReader",
    "AzureKinectRecorder",
    "AzureKinectSensor",
    "AzureKinectSensorConfig",
    "CONTAINS_LINES",
    "CONTAINS_POINTS",
    "CONTAINS_TRIANGLES",
    "CONTENTS_UNKNOWN",
    "FileGeometry",
    "read_azure_kinect_mkv_metadata",
    "read_azure_kinect_sensor_config",
    "read_feature",
    "read_file_geometry_type",
    "read_image",
    "read_line_set",
    "read_octree",
    "read_pinhole_camera_intrinsic",
    "read_pinhole_camera_parameters",
    "read_pinhole_camera_trajectory",
    "read_point_cloud",
    "read_point_cloud_from_bytes",
    "read_pose_graph",
    "read_triangle_mesh",
    "read_triangle_model",
    "read_voxel_grid",
    "rpc",
    "write_azure_kinect_mkv_metadata",
    "write_azure_kinect_sensor_config",
    "write_feature",
    "write_image",
    "write_line_set",
    "write_octree",
    "write_pinhole_camera_intrinsic",
    "write_pinhole_camera_parameters",
    "write_pinhole_camera_trajectory",
    "write_point_cloud",
    "write_point_cloud_to_bytes",
    "write_pose_graph",
    "write_triangle_mesh",
    "write_voxel_grid",
]

class AzureKinectMKVMetadata:
    """
    AzureKinect mkv metadata.
    """
    def __init__(self) -> None:
        """
        Default constructor
        """
    @property
    def height(self) -> int:
        """
        Height of the video
        """
    @height.setter
    def height(self, arg0: int) -> None: ...
    @property
    def stream_length_usec(self) -> int:
        """
        Length of the video (usec)
        """
    @stream_length_usec.setter
    def stream_length_usec(self, arg0: int) -> None: ...
    @property
    def width(self) -> int:
        """
        Width of the video
        """
    @width.setter
    def width(self, arg0: int) -> None: ...

class AzureKinectMKVReader:
    """
    AzureKinect mkv file reader.
    """
    def __init__(self) -> None: ...
    def close(self) -> None:
        """
        Close the opened mkv playback.

        Returns:
            None
        """
    def get_metadata(self) -> AzureKinectMKVMetadata:
        """
        Get metadata of the mkv playback.

        Returns:
            open3d.cuda.pybind.io.AzureKinectMKVMetadata
        """
    def is_eof(self) -> bool:
        """
        Check if the mkv file is all read.

        Returns:
            bool
        """
    def is_opened(self) -> bool:
        """
        Check if the mkv file  is opened.
        """
    def next_frame(self) -> open3d.cuda.pybind.geometry.RGBDImage:
        """
        Get next frame from the mkv playback and returns the RGBD object.

        Returns:
            open3d.cuda.pybind.geometry.RGBDImage
        """
    def open(self, filename: str) -> bool:
        """
        Open an mkv playback.

        Args:
            filename (str): Path to the mkv file.

        Returns:
            bool
        """
    def seek_timestamp(self, timestamp: int) -> bool:
        """
        Seek to the timestamp (in us).

        Args:
            timestamp (int): Timestamp in the video (usec).

        Returns:
            bool
        """

class AzureKinectRecorder:
    """
    AzureKinect recorder.
    """
    def __init__(self, sensor_config: AzureKinectSensorConfig, sensor_index: int) -> None: ...
    def close_record(self) -> bool:
        """
        Close the recorded mkv file.

        Returns:
            bool
        """
    def init_sensor(self) -> bool:
        """
        Initialize sensor.

        Returns:
            bool
        """
    def is_record_created(self) -> bool:
        """
        Check if the mkv file is created.

        Returns:
            bool
        """
    def open_record(self, filename: str) -> bool:
        """
        Attempt to create and open an mkv file.

        Args:
            filename (str): Path to the mkv file.

        Returns:
            bool
        """
    def record_frame(
        self, enable_record: bool, enable_align_depth_to_color: bool
    ) -> open3d.cuda.pybind.geometry.RGBDImage:
        """
        Record a frame to mkv if flag is on and return an RGBD object.

        Args:
            enable_record (bool): Enable recording to mkv file.
            enable_align_depth_to_color (bool): Enable aligning WFOV depth image to the color image in visualizer.

        Returns:
            open3d.cuda.pybind.geometry.RGBDImage
        """

class AzureKinectSensor:
    """
    AzureKinect sensor.
    """
    @staticmethod
    def list_devices() -> bool:
        """
        List available Azure Kinect devices

        Returns:
            bool
        """
    def __init__(self, sensor_config: AzureKinectSensorConfig) -> None: ...
    def capture_frame(self, enable_align_depth_to_color: bool) -> open3d.cuda.pybind.geometry.RGBDImage:
        """
        Capture an RGBD frame.

        Args:
            enable_align_depth_to_color (bool): Enable aligning WFOV depth image to the color image in visualizer.

        Returns:
            open3d.cuda.pybind.geometry.RGBDImage
        """
    def connect(self, sensor_index: int) -> bool:
        """
        Connect to specified device.

        Args:
            sensor_index (int): The selected device index.

        Returns:
            bool
        """
    def disconnect(self) -> None:
        """
        Disconnect from the connected device.
        """

class AzureKinectSensorConfig:
    """
    AzureKinect sensor configuration.
    """
    @typing.overload
    def __init__(self) -> None:
        """
        Default constructor
        """
    @typing.overload
    def __init__(self, config: dict[str, str]) -> None: ...

class FileGeometry:
    """
    Geometry types
    """

    CONTAINS_LINES: typing.ClassVar[FileGeometry]
    CONTAINS_POINTS: typing.ClassVar[FileGeometry]
    CONTAINS_TRIANGLES: typing.ClassVar[FileGeometry]
    CONTENTS_UNKNOWN: typing.ClassVar[FileGeometry]
    __members__: typing.ClassVar[dict[str, FileGeometry]]
    def __and__(self, other: typing.Any) -> typing.Any: ...
    def __eq__(self, other: typing.Any) -> bool: ...
    def __ge__(self, other: typing.Any) -> bool: ...
    def __getstate__(self) -> int: ...
    def __gt__(self, other: typing.Any) -> bool: ...
    def __hash__(self) -> int: ...
    def __index__(self) -> int: ...
    def __init__(self, value: int) -> None: ...
    def __int__(self) -> int: ...
    def __invert__(self) -> typing.Any: ...
    def __le__(self, other: typing.Any) -> bool: ...
    def __lt__(self, other: typing.Any) -> bool: ...
    def __ne__(self, other: typing.Any) -> bool: ...
    def __or__(self, other: typing.Any) -> typing.Any: ...
    def __rand__(self, other: typing.Any) -> typing.Any: ...
    def __repr__(self) -> str: ...
    def __ror__(self, other: typing.Any) -> typing.Any: ...
    def __rxor__(self, other: typing.Any) -> typing.Any: ...
    def __setstate__(self, state: int) -> None: ...
    def __str__(self) -> str: ...
    def __xor__(self, other: typing.Any) -> typing.Any: ...
    @property
    def name(self) -> str: ...
    @property
    def value(self) -> int: ...

def read_azure_kinect_mkv_metadata(filename: os.PathLike) -> AzureKinectMKVMetadata:
    """
    Function to read Azure Kinect metadata from file

    Args:
        filename (os.PathLike): Path to file.

    Returns:
        open3d.cuda.pybind.io.AzureKinectMKVMetadata
    """

def read_azure_kinect_sensor_config(filename: os.PathLike) -> AzureKinectSensorConfig:
    """
    Function to read Azure Kinect sensor config from file

    Args:
        filename (os.PathLike): Path to file.

    Returns:
        open3d.cuda.pybind.io.AzureKinectSensorConfig
    """

def read_feature(filename: os.PathLike) -> open3d.cuda.pybind.pipelines.registration.Feature:
    """
    Function to read registration.Feature from file

    Args:
        filename (os.PathLike): Path to file.

    Returns:
        open3d.cuda.pybind.pipelines.registration.Feature
    """

def read_file_geometry_type(arg0: str) -> FileGeometry:
    """
    Returns the type of geometry of the file. This is a faster way of determining the file type than attempting to read the file as a point cloud, mesh, or line set in turn.
    """

def read_image(filename: os.PathLike) -> open3d.cuda.pybind.geometry.Image:
    """
    Function to read Image from file

    Args:
        filename (os.PathLike): Path to file.

    Returns:
        open3d.cuda.pybind.geometry.Image
    """

def read_line_set(
    filename: os.PathLike, format: str = "auto", print_progress: bool = False
) -> open3d.cuda.pybind.geometry.LineSet:
    """
    Function to read LineSet from file

    Args:
        filename (os.PathLike): Path to file.
        format (str, optional, default='auto'): The format of the input file. When not specified or set as ``auto``, the format is inferred from file extension name.
        print_progress (bool, optional, default=False): If set to true a progress bar is visualized in the console

    Returns:
        open3d.cuda.pybind.geometry.LineSet
    """

def read_octree(filename: os.PathLike, format: str = "auto") -> open3d.cuda.pybind.geometry.Octree:
    """
    Function to read Octree from file

    Args:
        filename (os.PathLike): Path to file.
        format (str, optional, default='auto'): The format of the input file. When not specified or set as ``auto``, the format is inferred from file extension name.

    Returns:
        open3d.cuda.pybind.geometry.Octree
    """

def read_pinhole_camera_intrinsic(filename: os.PathLike) -> open3d.cuda.pybind.camera.PinholeCameraIntrinsic:
    """
    Function to read PinholeCameraIntrinsic from file

    Args:
        filename (os.PathLike): Path to file.

    Returns:
        open3d.cuda.pybind.camera.PinholeCameraIntrinsic
    """

def read_pinhole_camera_parameters(filename: os.PathLike) -> open3d.cuda.pybind.camera.PinholeCameraParameters:
    """
    Function to read PinholeCameraParameters from file

    Args:
        filename (os.PathLike): Path to file.

    Returns:
        open3d.cuda.pybind.camera.PinholeCameraParameters
    """

def read_pinhole_camera_trajectory(filename: os.PathLike) -> open3d.cuda.pybind.camera.PinholeCameraTrajectory:
    """
    Function to read PinholeCameraTrajectory from file

    Args:
        filename (os.PathLike): Path to file.

    Returns:
        open3d.cuda.pybind.camera.PinholeCameraTrajectory
    """

def read_point_cloud(
    filename: os.PathLike,
    format: str = "auto",
    remove_nan_points: bool = False,
    remove_infinite_points: bool = False,
    print_progress: bool = False,
) -> open3d.cuda.pybind.geometry.PointCloud:
    """
    Function to read PointCloud from file

    Args:
        filename (os.PathLike): Path to file.
        format (str, optional, default='auto'): The format of the input file. When not specified or set as ``auto``, the format is inferred from file extension name.
        remove_nan_points (bool, optional, default=False): If true, all points that include a NaN are removed from the PointCloud.
        remove_infinite_points (bool, optional, default=False): If true, all points that include an infinite value are removed from the PointCloud.
        print_progress (bool, optional, default=False): If set to true a progress bar is visualized in the console

    Returns:
        open3d.cuda.pybind.geometry.PointCloud
    """

def read_point_cloud_from_bytes(
    bytes: bytes,
    format: str = "auto",
    remove_nan_points: bool = False,
    remove_infinite_points: bool = False,
    print_progress: bool = False,
) -> open3d.cuda.pybind.geometry.PointCloud:
    """
    Function to read PointCloud from memory

    Args:
        bytes (bytes)
        format (str, optional, default='auto'): The format of the input file. When not specified or set as ``auto``, the format is inferred from file extension name.
        remove_nan_points (bool, optional, default=False): If true, all points that include a NaN are removed from the PointCloud.
        remove_infinite_points (bool, optional, default=False): If true, all points that include an infinite value are removed from the PointCloud.
        print_progress (bool, optional, default=False): If set to true a progress bar is visualized in the console

    Returns:
        open3d.cuda.pybind.geometry.PointCloud
    """

def read_pose_graph(filename: os.PathLike) -> open3d.cuda.pybind.pipelines.registration.PoseGraph:
    """
    Function to read PoseGraph from file

    Args:
        filename (os.PathLike): Path to file.

    Returns:
        open3d.cuda.pybind.pipelines.registration.PoseGraph
    """

def read_triangle_mesh(
    filename: os.PathLike, enable_post_processing: bool = False, print_progress: bool = False
) -> open3d.cuda.pybind.geometry.TriangleMesh:
    """
    Function to read TriangleMesh from file

    Args:
        filename (os.PathLike): Path to file.
        enable_post_processing (bool, optional, default=False)
        print_progress (bool, optional, default=False): If set to true a progress bar is visualized in the console

    Returns:
        open3d.cuda.pybind.geometry.TriangleMesh
    """

def read_triangle_model(
    filename: os.PathLike, print_progress: bool = False
) -> open3d.cuda.pybind.visualization.rendering.TriangleMeshModel:
    """
    Function to read visualization.rendering.TriangleMeshModel from file

    Args:
        filename (os.PathLike): Path to file.
        print_progress (bool, optional, default=False): If set to true a progress bar is visualized in the console

    Returns:
        open3d.cuda.pybind.visualization.rendering.TriangleMeshModel
    """

def read_voxel_grid(
    filename: os.PathLike, format: str = "auto", print_progress: bool = False
) -> open3d.cuda.pybind.geometry.VoxelGrid:
    """
    Function to read VoxelGrid from file

    Args:
        filename (os.PathLike): Path to file.
        format (str, optional, default='auto'): The format of the input file. When not specified or set as ``auto``, the format is inferred from file extension name.
        print_progress (bool, optional, default=False): If set to true a progress bar is visualized in the console

    Returns:
        open3d.cuda.pybind.geometry.VoxelGrid
    """

def write_azure_kinect_mkv_metadata(filename: os.PathLike, config: AzureKinectMKVMetadata) -> bool:
    """
    Function to write Azure Kinect metadata to file

    Args:
        filename (os.PathLike): Path to file.
        config (open3d.cuda.pybind.io.AzureKinectMKVMetadata): AzureKinectSensor's config file.

    Returns:
        bool
    """

def write_azure_kinect_sensor_config(filename: os.PathLike, config: AzureKinectSensorConfig) -> bool:
    """
    Function to write Azure Kinect sensor config to file

    Args:
        filename (os.PathLike): Path to file.
        config (open3d.cuda.pybind.io.AzureKinectSensorConfig): AzureKinectSensor's config file.

    Returns:
        bool
    """

def write_feature(filename: os.PathLike, feature: open3d.cuda.pybind.pipelines.registration.Feature) -> bool:
    """
    Function to write Feature to file

    Args:
        filename (os.PathLike): Path to file.
        feature (open3d.cuda.pybind.pipelines.registration.Feature): The ``Feature`` object for I/O

    Returns:
        bool
    """

def write_image(filename: os.PathLike, image: open3d.cuda.pybind.geometry.Image, quality: int = -1) -> bool:
    """
    Function to write Image to file

    Args:
        filename (os.PathLike): Path to file.
        image (open3d.cuda.pybind.geometry.Image): The ``Image`` object for I/O
        quality (int, optional, default=-1): Quality of the output file.

    Returns:
        bool
    """

def write_line_set(
    filename: os.PathLike,
    line_set: open3d.cuda.pybind.geometry.LineSet,
    write_ascii: bool = False,
    compressed: bool = False,
    print_progress: bool = False,
) -> bool:
    """
    Function to write LineSet to file

    Args:
        filename (os.PathLike): Path to file.
        line_set (open3d.cuda.pybind.geometry.LineSet): The ``LineSet`` object for I/O
        write_ascii (bool, optional, default=False): Set to ``True`` to output in ascii format, otherwise binary format will be used.
        compressed (bool, optional, default=False): Set to ``True`` to write in compressed format.
        print_progress (bool, optional, default=False): If set to true a progress bar is visualized in the console

    Returns:
        bool
    """

def write_octree(filename: os.PathLike, octree: open3d.cuda.pybind.geometry.Octree) -> bool:
    """
    Function to write Octree to file

    Args:
        filename (os.PathLike): Path to file.
        octree (open3d.cuda.pybind.geometry.Octree): The ``Octree`` object for I/O

    Returns:
        bool
    """

def write_pinhole_camera_intrinsic(
    filename: os.PathLike, intrinsic: open3d.cuda.pybind.camera.PinholeCameraIntrinsic
) -> bool:
    """
    Function to write PinholeCameraIntrinsic to file

    Args:
        filename (os.PathLike): Path to file.
        intrinsic (open3d.cuda.pybind.camera.PinholeCameraIntrinsic): The ``PinholeCameraIntrinsic`` object for I/O

    Returns:
        bool
    """

def write_pinhole_camera_parameters(
    filename: os.PathLike, parameters: open3d.cuda.pybind.camera.PinholeCameraParameters
) -> bool:
    """
    Function to write PinholeCameraParameters to file

    Args:
        filename (os.PathLike): Path to file.
        parameters (open3d.cuda.pybind.camera.PinholeCameraParameters): The ``PinholeCameraParameters`` object for I/O

    Returns:
        bool
    """

def write_pinhole_camera_trajectory(
    filename: os.PathLike, trajectory: open3d.cuda.pybind.camera.PinholeCameraTrajectory
) -> bool:
    """
    Function to write PinholeCameraTrajectory to file

    Args:
        filename (os.PathLike): Path to file.
        trajectory (open3d.cuda.pybind.camera.PinholeCameraTrajectory): The ``PinholeCameraTrajectory`` object for I/O

    Returns:
        bool
    """

def write_point_cloud(
    filename: os.PathLike,
    pointcloud: open3d.cuda.pybind.geometry.PointCloud,
    format: str = "auto",
    write_ascii: bool = False,
    compressed: bool = False,
    print_progress: bool = False,
) -> bool:
    """
    Function to write PointCloud to file

    Args:
        filename (os.PathLike): Path to file.
        pointcloud (open3d.cuda.pybind.geometry.PointCloud): The ``PointCloud`` object for I/O
        format (str, optional, default='auto'): The format of the input file. When not specified or set as ``auto``, the format is inferred from file extension name.
        write_ascii (bool, optional, default=False): Set to ``True`` to output in ascii format, otherwise binary format will be used.
        compressed (bool, optional, default=False): Set to ``True`` to write in compressed format.
        print_progress (bool, optional, default=False): If set to true a progress bar is visualized in the console

    Returns:
        bool
    """

def write_point_cloud_to_bytes(
    pointcloud: open3d.cuda.pybind.geometry.PointCloud,
    format: str = "auto",
    write_ascii: bool = False,
    compressed: bool = False,
    print_progress: bool = False,
) -> bytes:
    """
    Function to write PointCloud to memory

    Args:
        pointcloud (open3d.cuda.pybind.geometry.PointCloud): The ``PointCloud`` object for I/O
        format (str, optional, default='auto'): The format of the input file. When not specified or set as ``auto``, the format is inferred from file extension name.
        write_ascii (bool, optional, default=False): Set to ``True`` to output in ascii format, otherwise binary format will be used.
        compressed (bool, optional, default=False): Set to ``True`` to write in compressed format.
        print_progress (bool, optional, default=False): If set to true a progress bar is visualized in the console

    Returns:
        bytes
    """

def write_pose_graph(filename: os.PathLike, pose_graph: open3d.cuda.pybind.pipelines.registration.PoseGraph) -> None:
    """
    Function to write PoseGraph to file

    Args:
        filename (os.PathLike): Path to file.
        pose_graph (open3d.cuda.pybind.pipelines.registration.PoseGraph): The ``PoseGraph`` object for I/O

    Returns:
        None
    """

def write_triangle_mesh(
    filename: os.PathLike,
    mesh: open3d.cuda.pybind.geometry.TriangleMesh,
    write_ascii: bool = False,
    compressed: bool = False,
    write_vertex_normals: bool = True,
    write_vertex_colors: bool = True,
    write_triangle_uvs: bool = True,
    print_progress: bool = False,
) -> bool:
    """
    Function to write TriangleMesh to file

    Args:
        filename (os.PathLike): Path to file.
        mesh (open3d.cuda.pybind.geometry.TriangleMesh): The ``TriangleMesh`` object for I/O
        write_ascii (bool, optional, default=False): Set to ``True`` to output in ascii format, otherwise binary format will be used.
        compressed (bool, optional, default=False): Set to ``True`` to write in compressed format.
        write_vertex_normals (bool, optional, default=True): Set to ``False`` to not write any vertex normals, even if present on the mesh
        write_vertex_colors (bool, optional, default=True): Set to ``False`` to not write any vertex colors, even if present on the mesh
        write_triangle_uvs (bool, optional, default=True): Set to ``False`` to not write any triangle uvs, even if present on the mesh. For ``obj`` format, mtl file is saved only when ``True`` is set
        print_progress (bool, optional, default=False): If set to true a progress bar is visualized in the console

    Returns:
        bool
    """

def write_voxel_grid(
    filename: os.PathLike,
    voxel_grid: open3d.cuda.pybind.geometry.VoxelGrid,
    write_ascii: bool = False,
    compressed: bool = False,
    print_progress: bool = False,
) -> bool:
    """
    Function to write VoxelGrid to file

    Args:
        filename (os.PathLike): Path to file.
        voxel_grid (open3d.cuda.pybind.geometry.VoxelGrid): The ``VoxelGrid`` object for I/O
        write_ascii (bool, optional, default=False): Set to ``True`` to output in ascii format, otherwise binary format will be used.
        compressed (bool, optional, default=False): Set to ``True`` to write in compressed format.
        print_progress (bool, optional, default=False): If set to true a progress bar is visualized in the console

    Returns:
        bool
    """

CONTAINS_LINES: FileGeometry
CONTAINS_POINTS: FileGeometry
CONTAINS_TRIANGLES: FileGeometry
CONTENTS_UNKNOWN: FileGeometry
