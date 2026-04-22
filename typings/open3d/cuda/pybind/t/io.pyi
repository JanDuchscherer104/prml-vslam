"""
Tensor-based input-output handling module.
"""
from __future__ import annotations
import open3d.cuda.pybind.camera
import open3d.cuda.pybind.core
import open3d.cuda.pybind.t.geometry
import os
import typing
__all__: list[str] = ['DepthNoiseSimulator', 'RGBDSensor', 'RGBDVideoMetadata', 'RGBDVideoReader', 'RSBagReader', 'RealSenseSensor', 'RealSenseSensorConfig', 'RealSenseValidConfigs', 'SensorType', 'read_image', 'read_point_cloud', 'read_triangle_mesh', 'write_image', 'write_point_cloud', 'write_triangle_mesh']
class DepthNoiseSimulator:
    """
    Simulate depth image noise from a given noise distortion model. The distortion model is based on *Teichman et. al. "Unsupervised intrinsic calibration of depth sensors via SLAM" RSS 2009*. Also see <http://redwood-data.org/indoor/dataset.html>__
    
    Example::
    
        import open3d as o3d
    
        # Redwood Indoor LivingRoom1 (Augmented ICL-NUIM)
        # http://redwood-data.org/indoor/
        data = o3d.data.RedwoodIndoorLivingRoom1()
        noise_model_path = data.noise_model_path
        im_src_path = data.depth_paths[0]
        depth_scale = 1000.0
    
        # Read clean depth image (uint16)
        im_src = o3d.t.io.read_image(im_src_path)
    
        # Run noise model simulation
        simulator = o3d.t.io.DepthNoiseSimulator(noise_model_path)
        im_dst = simulator.simulate(im_src, depth_scale=depth_scale)
    
        # Save noisy depth image (uint16)
        o3d.t.io.write_image("noisy_depth.png", im_dst)
                
    """
    def __init__(self, noise_model_path: os.PathLike) -> None:
        """
        Args:
            noise_model_path (os.PathLike): Path to the noise model file. See http://redwood-data.org/indoor/dataset.html for the format. Or, you may use one of our example datasets, e.g., RedwoodIndoorLivingRoom1.
        """
    def enable_deterministic_debug_mode(self) -> None:
        """
        Enable deterministic debug mode. All normally distributed noise will be replaced by 0.
        
        Returns:
            None
        """
    def simulate(self, im_src: open3d.cuda.pybind.t.geometry.Image, depth_scale: float = 1000.0) -> open3d.cuda.pybind.t.geometry.Image:
        """
        Apply noise model to a depth image.
        
        Args:
            im_src (open3d.cuda.pybind.t.geometry.Image): Source depth image, must be with dtype UInt16 or Float32, channels==1.
            depth_scale (float, optional, default=1000.0): Scale factor to the depth image. As a sanity check, if the dtype is Float32, the depth_scale must be 1.0. If the dtype is is UInt16, the depth_scale is typically larger than 1.0, e.g. it can be 1000.0.
        
        Returns:
            open3d.cuda.pybind.t.geometry.Image
        """
    @property
    def noise_model(self) -> open3d.cuda.pybind.core.Tensor:
        """
        The noise model tensor.
        """
class RGBDSensor:
    """
    Interface class for control of RGBD cameras.
    """
    def __repr__(self) -> str:
        ...
class RGBDVideoMetadata:
    """
    RGBD Video metadata.
    """
    def __init__(self) -> None:
        ...
    def __repr__(self) -> str:
        ...
    @property
    def color_channels(self) -> int:
        """
        Number of color channels.
        """
    @color_channels.setter
    def color_channels(self, arg0: int) -> None:
        ...
    @property
    def color_dt(self) -> open3d.cuda.pybind.core.Dtype:
        """
        Pixel Dtype for color data.
        """
    @color_dt.setter
    def color_dt(self, arg0: open3d.cuda.pybind.core.Dtype) -> None:
        ...
    @property
    def color_format(self) -> str:
        """
        Pixel format for color data
        """
    @color_format.setter
    def color_format(self, arg0: str) -> None:
        ...
    @property
    def depth_dt(self) -> open3d.cuda.pybind.core.Dtype:
        """
        Pixel Dtype for depth data.
        """
    @depth_dt.setter
    def depth_dt(self, arg0: open3d.cuda.pybind.core.Dtype) -> None:
        ...
    @property
    def depth_format(self) -> str:
        """
        Pixel format for depth data
        """
    @depth_format.setter
    def depth_format(self, arg0: str) -> None:
        ...
    @property
    def depth_scale(self) -> float:
        """
        Number of depth units per meter (depth in m = depth_pixel_value/depth_scale).
        """
    @depth_scale.setter
    def depth_scale(self, arg0: float) -> None:
        ...
    @property
    def device_name(self) -> str:
        """
        Capture device name
        """
    @device_name.setter
    def device_name(self, arg0: str) -> None:
        ...
    @property
    def fps(self) -> float:
        """
        Video frame rate (common for both color and depth)
        """
    @fps.setter
    def fps(self, arg0: float) -> None:
        ...
    @property
    def height(self) -> int:
        """
        Height of the video
        """
    @height.setter
    def height(self, arg0: int) -> None:
        ...
    @property
    def intrinsics(self) -> open3d.cuda.pybind.camera.PinholeCameraIntrinsic:
        """
        Shared intrinsics between RGB & depth
        """
    @intrinsics.setter
    def intrinsics(self, arg0: open3d.cuda.pybind.camera.PinholeCameraIntrinsic) -> None:
        ...
    @property
    def serial_number(self) -> str:
        """
        Capture device serial number
        """
    @serial_number.setter
    def serial_number(self, arg0: str) -> None:
        ...
    @property
    def stream_length_usec(self) -> int:
        """
        Length of the video (usec). 0 for live capture.
        """
    @stream_length_usec.setter
    def stream_length_usec(self, arg0: int) -> None:
        ...
    @property
    def width(self) -> int:
        """
        Width of the video
        """
    @width.setter
    def width(self, arg0: int) -> None:
        ...
class RGBDVideoReader:
    """
    RGBD Video file reader.
    """
    @staticmethod
    def create(filename: os.PathLike) -> RGBDVideoReader:
        """
        Create RGBD video reader based on filename
        
        Args:
            filename (os.PathLike): Path to the RGBD video file.
        
        Returns:
            open3d.cuda.pybind.t.io.RGBDVideoReader
        """
    def __init__(self) -> None:
        ...
    def __repr__(self) -> str:
        ...
    def save_frames(self, frame_path: str, start_time_us: int = 0, end_time_us: int = 18446744073709551615) -> None:
        """
        Save synchronized and aligned individual frames to subfolders.
        
        Args:
            frame_path (str): Frames will be stored in stream subfolders 'color' and 'depth' here. The intrinsic camera calibration for the color stream will be saved in 'intrinsic.json'
            start_time_us (int, optional, default=0): Start saving frames from this time (us)
            end_time_us (int, optional, default=18446744073709551615): (default video length) Save frames till this time (us)
        
        Returns:
            None
        """
class RSBagReader(RGBDVideoReader):
    """
    RealSense Bag file reader.
    	Only the first color and depth streams from the bag file will be read.
     - The streams must have the same frame rate.
     - The color stream must have RGB 8 bit (RGB8/BGR8) pixel format
     - The depth stream must have 16 bit unsigned int (Z16) pixel format
    The output is synchronized color and depth frame pairs with the depth frame aligned to the color frame. Unsynchronized frames will be dropped. With alignment, the depth and color frames have the same  viewpoint and resolution. See format documentation `here <https://intelrealsense.github.io/librealsense/doxygen/rs__sensor_8h.html#ae04b7887ce35d16dbd9d2d295d23aac7>`__
    
    .. warning:: A few frames may be dropped if user code takes a long time (>10 frame intervals) to process a frame.
    """
    @typing.overload
    def __init__(self) -> None:
        ...
    @typing.overload
    def __init__(self, buffer_size: int = 32) -> None:
        """
        Args:
            buffer_size (int, optional, default=32): Size of internal frame buffer, increase this if you experience frame drops.
        """
    def __repr__(self) -> str:
        ...
    def close(self) -> None:
        """
        Close the opened RS bag playback.
        """
    def get_timestamp(self) -> int:
        """
        Get current timestamp (in us).
        """
    def is_eof(self) -> bool:
        """
        Check if the RS bag file is all read.
        """
    def is_opened(self) -> bool:
        """
        Check if the RS bag file  is opened.
        """
    def next_frame(self) -> open3d.cuda.pybind.t.geometry.RGBDImage:
        """
        Get next frame from the RS bag playback and returns the RGBD object.
        """
    def open(self, filename: str) -> bool:
        """
        Open an RS bag playback.
        
        Args:
            filename (str): Path to the RGBD video file.
        
        Returns:
            bool
        """
    def save_frames(self, frame_path: str, start_time_us: int = 0, end_time_us: int = 18446744073709551615) -> None:
        """
        Save synchronized and aligned individual frames to subfolders.
        
        Args:
            frame_path (str): Frames will be stored in stream subfolders 'color' and 'depth' here. The intrinsic camera calibration for the color stream will be saved in 'intrinsic.json'
            start_time_us (int, optional, default=0): Start saving frames from this time (us)
            end_time_us (int, optional, default=18446744073709551615): (default video length) Save frames till this time (us)
        
        Returns:
            None
        """
    def seek_timestamp(self, timestamp: int) -> bool:
        """
        Seek to the timestamp (in us).
        
        Args:
            timestamp (int): Timestamp in the video (usec).
        
        Returns:
            bool
        """
    @property
    def metadata(self) -> RGBDVideoMetadata:
        """
        Get metadata of the RS bag playback.
        """
    @metadata.setter
    def metadata(self) -> RGBDVideoMetadata:
        ...
class RealSenseSensor(RGBDSensor):
    """
    RealSense camera discovery, configuration, streaming and recording
    """
    @staticmethod
    def enumerate_devices() -> list[RealSenseValidConfigs]:
        """
        Query all connected RealSense cameras for their capabilities.
        """
    @staticmethod
    def list_devices() -> bool:
        """
        List all RealSense cameras connected to the system along with their capabilities. Use this listing to select an appropriate configuration for a camera
        """
    def __init__(self) -> None:
        """
        Initialize with default settings.
        """
    def __repr__(self) -> str:
        ...
    def capture_frame(self, wait: bool = True, align_depth_to_color: bool = True) -> open3d.cuda.pybind.t.geometry.RGBDImage:
        """
        Acquire the next synchronized RGBD frameset from the camera.
        
        Args:
            wait (bool, optional, default=True): If true wait for the next frame set, else return immediately with an empty RGBDImage if it is not yet available.
            align_depth_to_color (bool, optional, default=True): Enable aligning WFOV depth image to the color image in visualizer.
        
        Returns:
            open3d.cuda.pybind.t.geometry.RGBDImage
        """
    def get_filename(self) -> str:
        """
        Get filename being written.
        """
    def get_metadata(self) -> RGBDVideoMetadata:
        """
        Get metadata of the RealSense video capture.
        """
    def get_timestamp(self) -> int:
        """
        Get current timestamp (in us)
        """
    @typing.overload
    def init_sensor(self, sensor_config: ... = ..., sensor_index: int = 0, filename: str = '') -> bool:
        """
            Configure sensor with custom settings. If this is skipped, default settings will be used. You can enable recording to a bag file by specifying a filename.
        
        Args:
            sensor_config (open3d::io::RGBDSensorConfig, optional, default=<open3d.cuda.pybind.t.io.RealSenseSensorConfig object at 0x7cfc8dcacb70>): Camera configuration, such as resolution and framerate. A serial number can be entered here to connect to a specific camera.
            sensor_index (int, optional, default=0): Connect to a camera at this position in the enumeration of RealSense cameras that are currently connected. Use enumerate_devices() or list_devices() to obtain a list of connected cameras. This is ignored if sensor_config contains a serial entry.
            filename (str, optional, default=''): Save frames to a bag file
        
        Returns:
            bool
        """
    @typing.overload
    def init_sensor(self, sensor_config: RealSenseSensorConfig = ..., sensor_index: int = 0, filename: str = '') -> bool:
        """
            Configure sensor with custom settings. If this is skipped, default settings will be used. You can enable recording to a bag file by specifying a filename.
        
        Args:
            sensor_config (open3d.cuda.pybind.t.io.RealSenseSensorConfig, optional, default=<open3d.cuda.pybind.t.io.RealSenseSensorConfig object at 0x7cfc8dca3ef0>): Camera configuration, such as resolution and framerate. A serial number can be entered here to connect to a specific camera.
            sensor_index (int, optional, default=0): Connect to a camera at this position in the enumeration of RealSense cameras that are currently connected. Use enumerate_devices() or list_devices() to obtain a list of connected cameras. This is ignored if sensor_config contains a serial entry.
            filename (str, optional, default=''): Save frames to a bag file
        
        Returns:
            bool
        """
    def pause_record(self) -> None:
        """
        Pause recording to the bag file. Note: If this is called immediately after start_capture, the bag file may have an incorrect end time.
        """
    def resume_record(self) -> None:
        """
        Resume recording to the bag file. The file will contain discontinuous segments.
        """
    def start_capture(self, start_record: bool = False) -> bool:
        """
        Start capturing synchronized depth and color frames.
        
        Args:
            start_record (bool, optional, default=False): Start recording to the specified bag file as well.
        
        Returns:
            bool
        """
    def stop_capture(self) -> None:
        """
        Stop capturing frames.
        """
class RealSenseSensorConfig:
    """
    Configuration for a RealSense camera
    """
    @typing.overload
    def __init__(self) -> None:
        """
        Default config will be used
        """
    @typing.overload
    def __init__(self, config: dict[str, str]) -> None:
        """
        Initialize config with a map
        """
class RealSenseValidConfigs:
    """
    Store set of valid configuration options for a connected RealSense device.  From this structure, a user can construct a RealSenseSensorConfig object meeting their specifications.
    """
    @property
    def name(self) -> str:
        """
        Device name.
        """
    @name.setter
    def name(self, arg0: str) -> None:
        ...
    @property
    def serial(self) -> str:
        """
        Device serial number.
        """
    @serial.setter
    def serial(self, arg0: str) -> None:
        ...
    @property
    def valid_configs(self) -> dict[str, set[str]]:
        """
        Mapping between configuration option name and a list of valid values.
        """
    @valid_configs.setter
    def valid_configs(self, arg0: dict[str, set[str]]) -> None:
        ...
class SensorType:
    """
    Sensor type
    
    Members:
    
      AZURE_KINECT
    
      REAL_SENSE
    """
    AZURE_KINECT: typing.ClassVar[SensorType]
    REAL_SENSE: typing.ClassVar[SensorType]
    __members__: typing.ClassVar[dict[str, SensorType]]
    def __eq__(self, other: typing.Any) -> bool:
        ...
    def __getstate__(self) -> int:
        ...
    def __hash__(self) -> int:
        ...
    def __index__(self) -> int:
        ...
    def __init__(self, value: int) -> None:
        ...
    def __int__(self) -> int:
        ...
    def __ne__(self, other: typing.Any) -> bool:
        ...
    def __repr__(self) -> str:
        ...
    def __setstate__(self, state: int) -> None:
        ...
    def __str__(self) -> str:
        ...
    @property
    def name(self) -> str:
        ...
    @property
    def value(self) -> int:
        ...
def read_image(filename: os.PathLike) -> open3d.cuda.pybind.t.geometry.Image:
    """
    Function to read image from file.
    
    Args:
        filename (os.PathLike): Path to file.
    
    Returns:
        open3d.cuda.pybind.t.geometry.Image
    """
def read_point_cloud(filename: os.PathLike, format: str = 'auto', remove_nan_points: bool = False, remove_infinite_points: bool = False, print_progress: bool = False) -> open3d.cuda.pybind.t.geometry.PointCloud:
    """
    Function to read PointCloud with tensor attributes from file.
    
    Args:
        filename (os.PathLike): Path to file.
        format (str, optional, default='auto'): The format of the input file. When not specified or set as ``auto``, the format is inferred from file extension name.
        remove_nan_points (bool, optional, default=False): If true, all points that include a NaN are removed from the PointCloud.
        remove_infinite_points (bool, optional, default=False): If true, all points that include an infinite value are removed from the PointCloud.
        print_progress (bool, optional, default=False): If set to true a progress bar is visualized in the console.
    
    Returns:
        open3d.cuda.pybind.t.geometry.PointCloud
    """
def read_triangle_mesh(filename: os.PathLike, enable_post_processing: bool = False, print_progress: bool = False) -> open3d.cuda.pybind.t.geometry.TriangleMesh:
    """
    The general entrance for reading a TriangleMesh from a file.
    The function calls read functions based on the extension name of filename.
    Supported formats are `obj, ply, stl, off, gltf, glb, fbx`.
    
    The following example reads a triangle mesh with the .ply extension::
        import open3d as o3d
        mesh = o3d.t.io.read_triangle_mesh('mesh.ply')
    
    Args:
        filename (str): Path to the mesh file.
        enable_post_processing (bool): If True enables post-processing.
            Post-processing will
              - triangulate meshes with polygonal faces
              - remove redundant materials
              - pretransform vertices
              - generate face normals if needed
    
            For more information see ASSIMPs documentation on the flags
            `aiProcessPreset_TargetRealtime_Fast, aiProcess_RemoveRedundantMaterials,
            aiProcess_OptimizeMeshes, aiProcess_PreTransformVertices`.
    
            Note that identical vertices will always be joined regardless of whether
            post-processing is enabled or not, which changes the number of vertices
            in the mesh.
    
            The `ply`-format is not affected by the post-processing.
    
        print_progress (bool): If True print the reading progress to the terminal.
    
    Returns:
        Returns the mesh object. On failure an empty mesh is returned.
    """
def write_image(filename: os.PathLike, image: open3d.cuda.pybind.t.geometry.Image, quality: int = -1) -> bool:
    """
    Function to write Image to file.
    
    Args:
        filename (os.PathLike): Path to file.
        image (open3d.cuda.pybind.t.geometry.Image): The ``Image`` object for I/O.
        quality (int, optional, default=-1): Quality of the output file.
    
    Returns:
        bool
    """
def write_point_cloud(filename: os.PathLike, pointcloud: open3d.cuda.pybind.t.geometry.PointCloud, write_ascii: bool = False, compressed: bool = False, print_progress: bool = False) -> bool:
    """
    Function to write PointCloud with tensor attributes to file.
    
    Args:
        filename (os.PathLike): Path to file.
        pointcloud (open3d.cuda.pybind.t.geometry.PointCloud): The ``PointCloud`` object for I/O.
        write_ascii (bool, optional, default=False): Set to ``True`` to output in ascii format, otherwise binary format will be used.
        compressed (bool, optional, default=False): Set to ``True`` to write in compressed format.
        print_progress (bool, optional, default=False): If set to true a progress bar is visualized in the console.
    
    Returns:
        bool
    """
def write_triangle_mesh(filename: os.PathLike, mesh: open3d.cuda.pybind.t.geometry.TriangleMesh, write_ascii: bool = False, compressed: bool = False, write_vertex_normals: bool = True, write_vertex_colors: bool = True, write_triangle_uvs: bool = True, print_progress: bool = False) -> bool:
    """
    Function to write TriangleMesh to file
    
    Args:
        filename (os.PathLike): Path to file.
        mesh (open3d.cuda.pybind.t.geometry.TriangleMesh): The ``TriangleMesh`` object for I/O.
        write_ascii (bool, optional, default=False): Set to ``True`` to output in ascii format, otherwise binary format will be used.
        compressed (bool, optional, default=False): Set to ``True`` to write in compressed format.
        write_vertex_normals (bool, optional, default=True): Set to ``False`` to not write any vertex normals, even if present on the mesh.
        write_vertex_colors (bool, optional, default=True): Set to ``False`` to not write any vertex colors, even if present on the mesh.
        write_triangle_uvs (bool, optional, default=True): Set to ``False`` to not write any triangle uvs, even if present on the mesh. For ``obj`` format, mtl file is saved only when ``True`` is set.
        print_progress (bool, optional, default=False): If set to true a progress bar is visualized in the console.
    
    Returns:
        bool
    """
