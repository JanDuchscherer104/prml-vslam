"""
Tensor DenseSLAM pipeline.
"""

from __future__ import annotations
import open3d.cuda.pybind.core
import open3d.cuda.pybind.t.geometry
import open3d.cuda.pybind.t.pipelines.odometry
import typing

__all__: list[str] = ["Frame", "Model"]

class Frame:
    """
    A frame container that stores a map from keys (color, depth) to tensor images.
    """
    def __copy__(self) -> Frame: ...
    def __deepcopy__(self, arg0: dict) -> Frame: ...
    @typing.overload
    def __init__(self, arg0: Frame) -> None:
        """
            Copy constructor

        Args:
            arg0 (open3d.cuda.pybind.t.pipelines.slam.Frame)
        """
    @typing.overload
    def __init__(
        self,
        height: int,
        width: int,
        intrinsics: open3d.cuda.pybind.core.Tensor,
        device: open3d.cuda.pybind.core.Device,
    ) -> None:
        """
        Args:
            height (int): Height of an image frame.
            width (int): Width of an image frame.
            intrinsics (open3d.cuda.pybind.core.Tensor): Intrinsic matrix stored in a 3x3 Tensor.
            device (open3d.cuda.pybind.core.Device): The CPU or CUDA device used for the object.
        """
    def get_data(self, arg0: str) -> open3d.cuda.pybind.core.Tensor:
        """
        Get a 2D tensor from a image from the given key in the map.
        """
    def get_data_as_image(self, arg0: str) -> open3d.cuda.pybind.t.geometry.Image:
        """
        Get a 2D image from from the given key in the map.
        """
    def height(self) -> int: ...
    def set_data(self, arg0: str, arg1: open3d.cuda.pybind.core.Tensor) -> None:
        """
        Set a 2D tensor to a image to the given key in the map.
        """
    def set_data_from_image(self, arg0: str, arg1: open3d.cuda.pybind.t.geometry.Image) -> None:
        """
        Set a 2D image to the given key in the map.
        """
    def width(self) -> int: ...

class Model:
    """
    Volumetric model for Dense SLAM.
    """
    @staticmethod
    @typing.overload
    def __init__(*args, **kwargs) -> None:
        """
            Constructor of a VoxelBlockGrid

        Args:
            voxel_size (float): The voxel size of the volume in meters.
            block_resolution (int, optional, default=16,  block_count: int = 10000): Resolution of local dense voxel blocks. By default 16 is used to create 16^3 voxel blocks.
            transformation (open3d.cuda.pybind.core.Tensor, optional, default=[[1 0 0 0], [0 1 0 0], [0 0 1 0], [0 0 0 1]] Tensor[shape={4, 4}, stride={4, 1}, Float64): A 4x4 3D transformation matrix.
             ()
            device (open3d.cuda.pybind.core.Device, optional, default=CUDA:0): The CPU or CUDA device used for the object.
        """
    def __copy__(self) -> Model: ...
    def __deepcopy__(self, arg0: dict) -> Model: ...
    @typing.overload
    def __init__(self, arg0: Model) -> None:
        """
            Copy constructor

        Args:
            arg0 (open3d.cuda.pybind.t.pipelines.slam.Model)
        """
    @typing.overload
    def __init__(self) -> None: ...
    def extract_pointcloud(
        self, weight_threshold: float = 3.0, estimated_number: int = -1
    ) -> open3d.cuda.pybind.t.geometry.PointCloud:
        """
        Extract point cloud from the volumetric model.

        Args:
            weight_threshold (float, optional, default=3.0): Weight threshold to filter outlier voxel blocks.
            estimated_number (int, optional, default=-1): Estimated number of surface points. Use -1 if no estimation is available.

        Returns:
            open3d.cuda.pybind.t.geometry.PointCloud
        """
    def extract_trianglemesh(
        self, weight_threshold: float = 3.0, estimated_number: int = -1
    ) -> open3d.cuda.pybind.t.geometry.TriangleMesh:
        """
        Extract triangle mesh from the volumetric model.

        Args:
            weight_threshold (float, optional, default=3.0): Weight threshold to filter outlier voxel blocks.
            estimated_number (int, optional, default=-1): Estimated number of surface points. Use -1 if no estimation is available.

        Returns:
            open3d.cuda.pybind.t.geometry.TriangleMesh
        """
    def get_current_frame_pose(self) -> open3d.cuda.pybind.core.Tensor: ...
    def get_hashmap(self) -> open3d.cuda.pybind.core.HashMap:
        """
        Get the underlying hash map from 3D coordinates to voxel blocks.
        """
    def integrate(
        self,
        input_frame: Frame,
        depth_scale: float = 1000.0,
        depth_max: float = 3.0,
        trunc_voxel_multiplier: float = 8.0,
    ) -> None:
        """
        Integrate an input frame to a volume.

        Args:
            input_frame (open3d.cuda.pybind.t.pipelines.slam.Frame): The frame that contains raw depth and optionally images with the same size from the input.
            depth_scale (float, optional, default=1000.0): The scale factor to convert raw depth into meters.
            depth_max (float, optional, default=3.0): The max clipping depth to filter noisy observations too far.
            trunc_voxel_multiplier (float, optional, default=8.0): Truncation distance multiplier in voxel size for signed distance. For instance, --trunc_voxel_multiplier=8 with --voxel_size=0.006(m) creates a truncation distance of 0.048(m).

        Returns:
            None
        """
    def synthesize_model_frame(
        self,
        model_frame: Frame,
        depth_scale: float = 1000.0,
        depth_min: float = 0.1,
        depth_max: float = 3.0,
        trunc_voxel_multiplier: float = 8.0,
        enable_color: bool = False,
        weight_threshold: float = -1.0,
    ) -> None:
        """
        Synthesize frame from the volumetric model using ray casting.

        Args:
            model_frame (open3d.cuda.pybind.t.pipelines.slam.Frame): The frame that contains ray casted depth and optionally color from the volumetric model.
            depth_scale (float, optional, default=1000.0): The scale factor to convert raw depth into meters.
            depth_min (float, optional, default=0.1): The min clipping depth.
            depth_max (float, optional, default=3.0): The max clipping depth to filter noisy observations too far.
            trunc_voxel_multiplier (float, optional, default=8.0): Truncation distance multiplier in voxel size for signed distance. For instance, --trunc_voxel_multiplier=8 with --voxel_size=0.006(m) creates a truncation distance of 0.048(m).
            enable_color (bool, optional, default=False)
            weight_threshold (float, optional, default=-1.0): Weight threshold to filter outlier voxel blocks.

        Returns:
            None
        """
    def track_frame_to_model(
        self,
        input_frame: Frame,
        model_frame: Frame,
        depth_scale: float = 1000.0,
        depth_max: float = 3.0,
        depth_diff: float = 0.07,
        method: open3d.cuda.pybind.t.pipelines.odometry.Method = ...,
        criteria: list[open3d.cuda.pybind.t.pipelines.odometry.OdometryConvergenceCriteria] = ...,
    ) -> open3d.cuda.pybind.t.pipelines.odometry.OdometryResult:
        """
        Track input frame against raycasted frame from model.

        Args:
            input_frame (open3d.cuda.pybind.t.pipelines.slam.Frame): The frame that contains raw depth and optionally images with the same size from the input.
            model_frame (open3d.cuda.pybind.t.pipelines.slam.Frame): The frame that contains ray casted depth and optionally color from the volumetric model.
            depth_scale (float, optional, default=1000.0): The scale factor to convert raw depth into meters.
            depth_max (float, optional, default=3.0): The max clipping depth to filter noisy observations too far.
            depth_diff (float, optional, default=0.07)
            method (open3d.cuda.pybind.t.pipelines.odometry.Method, optional, default=Method.PointToPlane)
            criteria (list[open3d.cuda.pybind.t.pipelines.odometry.OdometryConvergenceCriteria], optional, default=[OdometryConvergenceCriteria(max_iteration=6, relative_rmse=1.000000e-06, relative_fitness=1.000000e-06), OdometryConvergenceCriteria(max_iteration=3, relative_rmse=1.000000e-06, relative_fitness=1.000000e-06), OdometryConvergenceCriteria(max_iteration=1, relative_rmse=1.000000e-06, relative_fitness=1.000000e-06)])

        Returns:
            open3d.cuda.pybind.t.pipelines.odometry.OdometryResult
        """
    def update_frame_pose(self, arg0: int, arg1: open3d.cuda.pybind.core.Tensor) -> None: ...
    @property
    def frame_id(self) -> int:
        """
        Get the current frame index in a sequence.
        """
    @frame_id.setter
    def frame_id(self, arg0: int) -> None: ...
    @property
    def frustum_block_coords(self) -> open3d.cuda.pybind.core.Tensor:
        """
        Active block coordinates from prior integration
        """
    @frustum_block_coords.setter
    def frustum_block_coords(self, arg0: open3d.cuda.pybind.core.Tensor) -> None: ...
    @property
    def transformation_frame_to_world(self) -> open3d.cuda.pybind.core.Tensor:
        """
        Get the 4x4 transformation matrix from the current frame to the world frame.
        """
    @transformation_frame_to_world.setter
    def transformation_frame_to_world(self, arg0: open3d.cuda.pybind.core.Tensor) -> None: ...
    @property
    def voxel_grid(self) -> open3d.cuda.pybind.t.geometry.VoxelBlockGrid:
        """
        Get the maintained VoxelBlockGrid.
        """
    @voxel_grid.setter
    def voxel_grid(self, arg0: open3d.cuda.pybind.t.geometry.VoxelBlockGrid) -> None: ...
