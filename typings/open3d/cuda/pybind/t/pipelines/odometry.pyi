"""
Tensor odometry pipeline.
"""
from __future__ import annotations
import open3d.cuda.pybind.core
import open3d.cuda.pybind.t.geometry
import typing
__all__: list[str] = ['Hybrid', 'Intensity', 'Method', 'OdometryConvergenceCriteria', 'OdometryLossParams', 'OdometryResult', 'PointToPlane', 'compute_odometry_information_matrix', 'compute_odometry_result_hybrid', 'compute_odometry_result_intensity', 'compute_odometry_result_point_to_plane', 'rgbd_odometry_multi_scale']
class Method:
    """
    Tensor odometry estimation method.
    
    Members:
    
      PointToPlane
    
      Intensity
    
      Hybrid
    """
    Hybrid: typing.ClassVar[Method]
    Intensity: typing.ClassVar[Method]
    PointToPlane: typing.ClassVar[Method]
    __members__: typing.ClassVar[dict[str, Method]]
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
class OdometryConvergenceCriteria:
    """
    Convergence criteria of odometry. Odometry algorithm stops if the relative change of fitness and rmse hit ``relative_fitness`` and ``relative_rmse`` individually, or the iteration number exceeds ``max_iteration``.
    """
    def __copy__(self) -> OdometryConvergenceCriteria:
        ...
    def __deepcopy__(self, arg0: dict) -> OdometryConvergenceCriteria:
        ...
    @typing.overload
    def __init__(self, arg0: OdometryConvergenceCriteria) -> None:
        """
        Copy constructor
        """
    @typing.overload
    def __init__(self, max_iteration: int, relative_rmse: float = 1e-06, relative_fitness: float = 1e-06) -> None:
        ...
    def __repr__(self) -> str:
        ...
    @property
    def max_iteration(self) -> int:
        """
        Maximum iteration before iteration stops.
        """
    @max_iteration.setter
    def max_iteration(self, arg0: int) -> None:
        ...
    @property
    def relative_fitness(self) -> float:
        """
        If relative change (difference) of fitness score is lower than ``relative_fitness``, the iteration stops.
        """
    @relative_fitness.setter
    def relative_fitness(self, arg0: float) -> None:
        ...
    @property
    def relative_rmse(self) -> float:
        """
        If relative change (difference) of inliner RMSE score is lower than ``relative_rmse``, the iteration stops.
        """
    @relative_rmse.setter
    def relative_rmse(self, arg0: float) -> None:
        ...
class OdometryLossParams:
    """
    Odometry loss parameters.
    """
    def __copy__(self) -> OdometryLossParams:
        ...
    def __deepcopy__(self, arg0: dict) -> OdometryLossParams:
        ...
    @typing.overload
    def __init__(self, arg0: OdometryLossParams) -> None:
        """
        Copy constructor
        """
    @typing.overload
    def __init__(self, depth_outlier_trunc: float = 0.07, depth_huber_delta: float = 0.05, intensity_huber_delta: float = 0.1) -> None:
        ...
    def __repr__(self) -> str:
        ...
    @property
    def depth_huber_delta(self) -> float:
        """
        float: Huber norm parameter used in depth loss.
        """
    @depth_huber_delta.setter
    def depth_huber_delta(self, arg0: float) -> None:
        ...
    @property
    def depth_outlier_trunc(self) -> float:
        """
        float: Depth difference threshold used to filter projective associations.
        """
    @depth_outlier_trunc.setter
    def depth_outlier_trunc(self, arg0: float) -> None:
        ...
    @property
    def intensity_huber_delta(self) -> float:
        """
        float: Huber norm parameter used in intensity loss.
        """
    @intensity_huber_delta.setter
    def intensity_huber_delta(self, arg0: float) -> None:
        ...
class OdometryResult:
    """
    Odometry results.
    """
    def __copy__(self) -> OdometryResult:
        ...
    def __deepcopy__(self, arg0: dict) -> OdometryResult:
        ...
    @typing.overload
    def __init__(self, arg0: OdometryResult) -> None:
        """
        Copy constructor
        """
    @typing.overload
    def __init__(self, transformation: open3d.cuda.pybind.core.Tensor = ..., inlier_rmse: float = 0.0, fitness: float = 0.0) -> None:
        ...
    def __repr__(self) -> str:
        ...
    @property
    def fitness(self) -> float:
        """
        float: The overlapping area (# of inlier correspondences / # of points in target). Higher is better.
        """
    @fitness.setter
    def fitness(self, arg0: float) -> None:
        ...
    @property
    def inlier_rmse(self) -> float:
        """
        float: RMSE of all inlier correspondences. Lower is better.
        """
    @inlier_rmse.setter
    def inlier_rmse(self, arg0: float) -> None:
        ...
    @property
    def transformation(self) -> open3d.cuda.pybind.core.Tensor:
        """
        ``4 x 4`` float64 tensor on CPU: The estimated transformation matrix.
        """
    @transformation.setter
    def transformation(self, arg0: open3d.cuda.pybind.core.Tensor) -> None:
        ...
def compute_odometry_information_matrix(source_depth: open3d.cuda.pybind.t.geometry.Image, target_depth: open3d.cuda.pybind.t.geometry.Image, intrinsic: open3d.cuda.pybind.core.Tensor, source_to_target: open3d.cuda.pybind.core.Tensor, dist_threshold: float, depth_scale: float = 1000.0, depth_max: float = 3.0) -> open3d.cuda.pybind.core.Tensor:
    ...
def compute_odometry_result_hybrid(source_depth: open3d.cuda.pybind.core.Tensor, target_depth: open3d.cuda.pybind.core.Tensor, source_intensity: open3d.cuda.pybind.core.Tensor, target_intensity: open3d.cuda.pybind.core.Tensor, target_depth_dx: open3d.cuda.pybind.core.Tensor, target_depth_dy: open3d.cuda.pybind.core.Tensor, target_intensity_dx: open3d.cuda.pybind.core.Tensor, target_intensity_dy: open3d.cuda.pybind.core.Tensor, source_vertex_map: open3d.cuda.pybind.core.Tensor, intrinsics: open3d.cuda.pybind.core.Tensor, init_source_to_target: open3d.cuda.pybind.core.Tensor, depth_outlier_trunc: float, depth_huber_delta: float, intensity_huber_delta: float) -> OdometryResult:
    """
    Estimates the OdometryResult (4x4 rigid transformation T from
    source to target, with inlier rmse and fitness). Performs one
    iteration of RGBD odometry using
    Loss function: :math:`(I_p - I_q)^2 + \\lambda(D_p - (D_q)')^2`
    where,
    :math:`I_p` denotes the intensity at pixel p in the source,
    :math:`I_q` denotes the intensity at pixel q in the target.
    :math:`D_p` denotes the depth pixel p in the source,
    :math:`D_q` denotes the depth pixel q in the target.
    q is obtained by transforming p with init_source_to_target then
    projecting with intrinsics.
    Reference: J. Park, Q.Y. Zhou, and V. Koltun,
    Colored Point Cloud Registration Revisited, ICCV, 2017.
    
    Args:
        source_depth (open3d.cuda.pybind.core.Tensor): (row, col, channel = 1) Float32 source depth image obtained by PreprocessDepth before calling this function.
        target_depth (open3d.cuda.pybind.core.Tensor): (row, col, channel = 1) Float32 target depth image obtained by PreprocessDepth before calling this function.
        source_intensity (open3d.cuda.pybind.core.Tensor): (row, col, channel = 1) Float32 source intensity image obtained by RGBToGray before calling this function
        target_intensity (open3d.cuda.pybind.core.Tensor): (row, col, channel = 1) Float32 target intensity image obtained by RGBToGray before calling this function
        target_depth_dx (open3d.cuda.pybind.core.Tensor): (row, col, channel = 1) Float32 target depth gradient image along x-axis obtained by FilterSobel before calling this function.
        target_depth_dy (open3d.cuda.pybind.core.Tensor): (row, col, channel = 1) Float32 target depth gradient image along y-axis obtained by FilterSobel before calling this function.
        target_intensity_dx (open3d.cuda.pybind.core.Tensor): (row, col, channel = 1) Float32 target intensity gradient image along x-axis obtained by FilterSobel before calling this function.
        target_intensity_dy (open3d.cuda.pybind.core.Tensor): (row, col, channel = 1) Float32 target intensity gradient image along y-axis obtained by FilterSobel before calling this function.
        source_vertex_map (open3d.cuda.pybind.core.Tensor): (row, col, channel = 3) Float32 source vertex image obtained by CreateVertexMap before calling this function.
        intrinsics (open3d.cuda.pybind.core.Tensor): (3, 3) intrinsic matrix for projection.
        init_source_to_target (open3d.cuda.pybind.core.Tensor): (4, 4) initial transformation matrix from source to target.
        depth_outlier_trunc (float): Depth difference threshold used to filter projective associations.
        depth_huber_delta (float): Huber norm parameter used in depth loss.
        intensity_huber_delta (float): Huber norm parameter used in intensity loss.
    
    Returns:
        open3d.cuda.pybind.t.pipelines.odometry.OdometryResult
    """
def compute_odometry_result_intensity(source_depth: open3d.cuda.pybind.core.Tensor, target_depth: open3d.cuda.pybind.core.Tensor, source_intensity: open3d.cuda.pybind.core.Tensor, target_intensity: open3d.cuda.pybind.core.Tensor, target_intensity_dx: open3d.cuda.pybind.core.Tensor, target_intensity_dy: open3d.cuda.pybind.core.Tensor, source_vertex_map: open3d.cuda.pybind.core.Tensor, intrinsics: open3d.cuda.pybind.core.Tensor, init_source_to_target: open3d.cuda.pybind.core.Tensor, depth_outlier_trunc: float, intensity_huber_delta: float) -> OdometryResult:
    """
    Estimates the OdometryResult (4x4 rigid transformation T from
    source to target, with inlier rmse and fitness). Performs one
    iteration of RGBD odometry using
    Loss function: :math:`(I_p - I_q)^2`
    where,
    :math:`I_p` denotes the intensity at pixel p in the source,
    :math:`I_q` denotes the intensity at pixel q in the target.
    q is obtained by transforming p with init_source_to_target then
    projecting with intrinsics.
    Reference:
    Real-time visual odometry from dense RGB-D images,
    ICCV Workshops, 2017.
    
    Args:
        source_depth (open3d.cuda.pybind.core.Tensor): (row, col, channel = 1) Float32 source depth image obtained by PreprocessDepth before calling this function.
        target_depth (open3d.cuda.pybind.core.Tensor): (row, col, channel = 1) Float32 target depth image obtained by PreprocessDepth before calling this function.
        source_intensity (open3d.cuda.pybind.core.Tensor): (row, col, channel = 1) Float32 source intensity image obtained by RGBToGray before calling this function
        target_intensity (open3d.cuda.pybind.core.Tensor): (row, col, channel = 1) Float32 target intensity image obtained by RGBToGray before calling this function
        target_intensity_dx (open3d.cuda.pybind.core.Tensor): (row, col, channel = 1) Float32 target intensity gradient image along x-axis obtained by FilterSobel before calling this function.
        target_intensity_dy (open3d.cuda.pybind.core.Tensor): (row, col, channel = 1) Float32 target intensity gradient image along y-axis obtained by FilterSobel before calling this function.
        source_vertex_map (open3d.cuda.pybind.core.Tensor): (row, col, channel = 3) Float32 source vertex image obtained by CreateVertexMap before calling this function.
        intrinsics (open3d.cuda.pybind.core.Tensor): (3, 3) intrinsic matrix for projection.
        init_source_to_target (open3d.cuda.pybind.core.Tensor): (4, 4) initial transformation matrix from source to target.
        depth_outlier_trunc (float): Depth difference threshold used to filter projective associations.
        intensity_huber_delta (float): Huber norm parameter used in intensity loss.
    
    Returns:
        open3d.cuda.pybind.t.pipelines.odometry.OdometryResult
    """
def compute_odometry_result_point_to_plane(source_vertex_map: open3d.cuda.pybind.core.Tensor, target_vertex_map: open3d.cuda.pybind.core.Tensor, target_normal_map: open3d.cuda.pybind.core.Tensor, intrinsics: open3d.cuda.pybind.core.Tensor, init_source_to_target: open3d.cuda.pybind.core.Tensor, depth_outlier_trunc: float, depth_huber_delta: float) -> OdometryResult:
    """
    Estimates the OdometryResult (4x4 rigid transformation T from
    source to target, with inlier rmse and fitness). Performs one
    iteration of RGBD odometry using
    Loss function: :math:`[(V_p - V_q)^T N_p]^2`
    where,
    :math:`V_p` denotes the vertex at pixel p in the source,
    :math:`V_q` denotes the vertex at pixel q in the target.
    :math:`N_p` denotes the normal at pixel p in the source.
    q is obtained by transforming p with init_source_to_target then
    projecting with intrinsics.
    Reference: KinectFusion, ISMAR 2011.
    
    Args:
        source_vertex_map (open3d.cuda.pybind.core.Tensor): (row, col, channel = 3) Float32 source vertex image obtained by CreateVertexMap before calling this function.
        target_vertex_map (open3d.cuda.pybind.core.Tensor): (row, col, channel = 3) Float32 target vertex image obtained by CreateVertexMap before calling this function.
        target_normal_map (open3d.cuda.pybind.core.Tensor): (row, col, channel = 3) Float32 target normal image obtained by CreateNormalMap before calling this function.
        intrinsics (open3d.cuda.pybind.core.Tensor): (3, 3) intrinsic matrix for projection.
        init_source_to_target (open3d.cuda.pybind.core.Tensor): (4, 4) initial transformation matrix from source to target.
        depth_outlier_trunc (float): Depth difference threshold used to filter projective associations.
        depth_huber_delta (float): Huber norm parameter used in depth loss.
    
    Returns:
        open3d.cuda.pybind.t.pipelines.odometry.OdometryResult
    """
def rgbd_odometry_multi_scale(*args, **kwargs) -> OdometryResult:
    """
    Function for Multi Scale RGBD odometry.
    
    Args:
        source (open3d.cuda.pybind.t.geometry.RGBDImage): The source RGBD image.
        target (open3d.cuda.pybind.t.geometry.RGBDImage): The target RGBD image.
        intrinsics (open3d.cuda.pybind.core.Tensor): (3, 3) intrinsic matrix for projection.
        init_source_to_target (open3d.cuda.pybind.core.Tensor, optional, default=[[1 0 0 0], [0 1 0 0], [0 0 1 0], [0 0 0 1]] Tensor[shape={4, 4}, stride={4, 1}, Float64): (4, 4) initial transformation matrix from source to target.
         ()
        depth_scale (float, optional, default=1000.0): Converts depth pixel values to meters by dividing the scale factor.
        depth_max (float, optional, default=3.0)
        criteria_list (list[open3d.cuda.pybind.t.pipelines.odometry.OdometryConvergenceCriteria], optional, default=[OdometryConvergenceCriteria(max_iteration=10, relative_rmse=1.000000e-06, relative_fitness=1.000000e-06), OdometryConvergenceCriteria(max_iteration=5, relative_rmse=1.000000e-06, relative_fitness=1.000000e-06), OdometryConvergenceCriteria(max_iteration=3, relative_rmse=1.000000e-06, relative_fitness=1.000000e-06)]): List of Odometry convergence criteria.
        method (open3d.cuda.pybind.t.pipelines.odometry.Method, optional, default=<Method.Hybrid: 2>): Estimation method used to apply RGBD odometry. One of (``PointToPlane``, ``Intensity``, ``Hybrid``)
        params (open3d.cuda.pybind.t.pipelines.odometry.OdometryLossParams, optional, default=OdometryLossParams[depth_outlier_trunc=7.000000e-02, depth_huber_delta=5.000000e-02, intensity_huber_delta=1.000000e-01].): Odometry loss parameters.
    
    Returns:
        open3d.cuda.pybind.t.pipelines.odometry.OdometryResult
    """
Hybrid: Method
Intensity: Method
PointToPlane: Method
