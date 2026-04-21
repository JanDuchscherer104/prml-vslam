"""
Tensor-based registration pipeline.
"""
from __future__ import annotations
import open3d.cuda.pybind.core
import open3d.cuda.pybind.t.geometry
import typing
from . import robust_kernel
__all__: list[str] = ['ICPConvergenceCriteria', 'RegistrationResult', 'TransformationEstimation', 'TransformationEstimationForColoredICP', 'TransformationEstimationForDopplerICP', 'TransformationEstimationPointToPlane', 'TransformationEstimationPointToPoint', 'compute_fpfh_feature', 'correspondences_from_features', 'evaluate_registration', 'get_information_matrix', 'icp', 'multi_scale_icp', 'robust_kernel']
class ICPConvergenceCriteria:
    """
    Convergence criteria of ICP. ICP algorithm stops if the relative change of fitness and rmse hit ``relative_fitness`` and ``relative_rmse`` individually, or the iteration number exceeds ``max_iteration``.
    """
    def __copy__(self) -> ICPConvergenceCriteria:
        ...
    def __deepcopy__(self, arg0: dict) -> ICPConvergenceCriteria:
        ...
    @typing.overload
    def __init__(self, arg0: ICPConvergenceCriteria) -> None:
        """
        Copy constructor
        """
    @typing.overload
    def __init__(self, relative_fitness: float = 1e-06, relative_rmse: float = 1e-06, max_iteration: int = 30) -> None:
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
        If relative change (difference) of inlier RMSE score is lower than ``relative_rmse``, the iteration stops.
        """
    @relative_rmse.setter
    def relative_rmse(self, arg0: float) -> None:
        ...
class RegistrationResult:
    """
    Registration results.
    """
    def __copy__(self) -> RegistrationResult:
        ...
    def __deepcopy__(self, arg0: dict) -> RegistrationResult:
        ...
    @typing.overload
    def __init__(self) -> None:
        """
        Default constructor
        """
    @typing.overload
    def __init__(self, arg0: RegistrationResult) -> None:
        """
        Copy constructor
        """
    def __repr__(self) -> str:
        ...
    @property
    def converged(self) -> bool:
        """
        bool: Specifies whether the algorithm converged or not.
        """
    @converged.setter
    def converged(self, arg0: bool) -> None:
        ...
    @property
    def correspondence_set(self) -> open3d.cuda.pybind.core.Tensor:
        """
        Tensor of type Int64 containing indices of corresponding target points, where the value is the target index and the index of the value itself is the source index. It contains -1 as value at index with no correspondence.
        """
    @correspondence_set.setter
    def correspondence_set(self, arg0: open3d.cuda.pybind.core.Tensor) -> None:
        ...
    @property
    def fitness(self) -> float:
        """
        float: The overlapping area (# of inlier correspondences / # of points in source). Higher is better.
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
    def num_iterations(self) -> int:
        """
        int: Number of iterations the algorithm took to converge.
        """
    @num_iterations.setter
    def num_iterations(self, arg0: int) -> None:
        ...
    @property
    def transformation(self) -> open3d.cuda.pybind.core.Tensor:
        """
        ``4 x 4`` float64 tensor on CPU: The estimated transformation matrix.
        """
    @transformation.setter
    def transformation(self, arg0: open3d.cuda.pybind.core.Tensor) -> None:
        ...
class TransformationEstimation:
    """
    Base class that estimates a transformation between two point clouds. The virtual function ComputeTransformation() must be implemented in subclasses.
    """
    @staticmethod
    def compute_transformation(*args, **kwargs) -> open3d.cuda.pybind.core.Tensor:
        """
        Compute transformation from source to target point cloud given correspondences.
        
        Args:
            source (open3d.cuda.pybind.t.geometry.PointCloud): Source point cloud.
            target (open3d.cuda.pybind.t.geometry.PointCloud): Target point cloud.
            correspondences (open3d.cuda.pybind.core.Tensor): Tensor of type Int64 containing indices of corresponding target points, where the value is the target index and the index of the value itself is the source index. It contains -1 as value at index with no correspondence.
            current_transform (open3d.cuda.pybind.core.Tensor, optional, default=[[1 0 0 0], [0 1 0 0], [0 0 1 0], [0 0 0 1]] Tensor[shape={4, 4}, stride={4, 1}, Float64): The current pose estimate of ICP.
             ()
            iteration (int, optional, default=0): The current iteration number of the ICP algorithm.
        
        Returns:
            open3d.cuda.pybind.core.Tensor
        """
    def compute_rmse(self, source: open3d.cuda.pybind.t.geometry.PointCloud, target: open3d.cuda.pybind.t.geometry.PointCloud, correspondences: open3d.cuda.pybind.core.Tensor) -> float:
        """
        Compute RMSE between source and target points cloud given correspondences.
        
        Args:
            source (open3d.cuda.pybind.t.geometry.PointCloud): Source point cloud.
            target (open3d.cuda.pybind.t.geometry.PointCloud): Target point cloud.
            correspondences (open3d.cuda.pybind.core.Tensor): Tensor of type Int64 containing indices of corresponding target points, where the value is the target index and the index of the value itself is the source index. It contains -1 as value at index with no correspondence.
        
        Returns:
            float
        """
class TransformationEstimationForColoredICP(TransformationEstimation):
    """
    Class to estimate a transformation between two point clouds using color information
    """
    def __copy__(self) -> TransformationEstimationForColoredICP:
        ...
    def __deepcopy__(self, arg0: dict) -> TransformationEstimationForColoredICP:
        ...
    @typing.overload
    def __init__(self) -> None:
        """
        Default constructor
        """
    @typing.overload
    def __init__(self, arg0: TransformationEstimationForColoredICP) -> None:
        """
        Copy constructor
        """
    @typing.overload
    def __init__(self, lambda_geometric: float, kernel: robust_kernel.RobustKernel) -> None:
        ...
    @typing.overload
    def __init__(self, lambda_geometric: float) -> None:
        ...
    @typing.overload
    def __init__(self, kernel: robust_kernel.RobustKernel) -> None:
        ...
    def __repr__(self) -> str:
        ...
    @property
    def kernel(self) -> robust_kernel.RobustKernel:
        """
        Robust Kernel used in the Optimization
        """
    @kernel.setter
    def kernel(self, arg0: robust_kernel.RobustKernel) -> None:
        ...
    @property
    def lambda_geometric(self) -> float:
        """
        lambda_geometric
        """
    @lambda_geometric.setter
    def lambda_geometric(self, arg0: float) -> None:
        ...
class TransformationEstimationForDopplerICP(TransformationEstimation):
    """
    Class to estimate a transformation between two point clouds using color information
    """
    def __copy__(self) -> TransformationEstimationForDopplerICP:
        ...
    def __deepcopy__(self, arg0: dict) -> TransformationEstimationForDopplerICP:
        ...
    @typing.overload
    def __init__(self) -> None:
        """
        Default constructor
        """
    @typing.overload
    def __init__(self, arg0: TransformationEstimationForDopplerICP) -> None:
        """
        Copy constructor
        """
    @typing.overload
    def __init__(self, period: float, lambda_doppler: float, reject_dynamic_outliers: bool, doppler_outlier_threshold: float, outlier_rejection_min_iteration: int, geometric_robust_loss_min_iteration: int, doppler_robust_loss_min_iteration: int, goemetric_kernel: robust_kernel.RobustKernel, doppler_kernel: robust_kernel.RobustKernel, transform_vehicle_to_sensor: open3d.cuda.pybind.core.Tensor) -> None:
        ...
    @typing.overload
    def __init__(self, lambda_doppler: float) -> None:
        ...
    def __repr__(self) -> str:
        ...
    def compute_transformation(self, arg0: open3d.cuda.pybind.t.geometry.PointCloud, arg1: open3d.cuda.pybind.t.geometry.PointCloud, arg2: open3d.cuda.pybind.core.Tensor, arg3: open3d.cuda.pybind.core.Tensor, arg4: int) -> open3d.cuda.pybind.core.Tensor:
        """
        Compute transformation from source to target point cloud given correspondences
        """
    @property
    def doppler_kernel(self) -> robust_kernel.RobustKernel:
        """
        Robust Kernel used in the Doppler Error Optimization
        """
    @doppler_kernel.setter
    def doppler_kernel(self, arg0: robust_kernel.RobustKernel) -> None:
        ...
    @property
    def doppler_outlier_threshold(self) -> float:
        """
        Correspondences with Doppler error greater than this threshold are rejected from optimization.
        """
    @doppler_outlier_threshold.setter
    def doppler_outlier_threshold(self, arg0: float) -> None:
        ...
    @property
    def doppler_robust_loss_min_iteration(self) -> int:
        """
        Minimum iterations after which Robust Kernel is used for the Doppler error
        """
    @doppler_robust_loss_min_iteration.setter
    def doppler_robust_loss_min_iteration(self, arg0: int) -> None:
        ...
    @property
    def geometric_kernel(self) -> robust_kernel.RobustKernel:
        """
        Robust Kernel used in the Geometric Error Optimization
        """
    @geometric_kernel.setter
    def geometric_kernel(self, arg0: robust_kernel.RobustKernel) -> None:
        ...
    @property
    def geometric_robust_loss_min_iteration(self) -> int:
        """
        Minimum iterations after which Robust Kernel is used for the Geometric error
        """
    @geometric_robust_loss_min_iteration.setter
    def geometric_robust_loss_min_iteration(self, arg0: int) -> None:
        ...
    @property
    def lambda_doppler(self) -> float:
        """
        `λ ∈ [0, 1]` in the overall energy `(1−λ)EG + λED`. Refer the documentation of DopplerICP for more information.
        """
    @lambda_doppler.setter
    def lambda_doppler(self, arg0: float) -> None:
        ...
    @property
    def outlier_rejection_min_iteration(self) -> int:
        """
        Number of iterations of ICP after which outlier rejection is enabled.
        """
    @outlier_rejection_min_iteration.setter
    def outlier_rejection_min_iteration(self, arg0: int) -> None:
        ...
    @property
    def period(self) -> float:
        """
        Time period (in seconds) between the source and the target point clouds.
        """
    @period.setter
    def period(self, arg0: float) -> None:
        ...
    @property
    def reject_dynamic_outliers(self) -> bool:
        """
        Whether or not to reject dynamic point outlier correspondences.
        """
    @reject_dynamic_outliers.setter
    def reject_dynamic_outliers(self, arg0: bool) -> None:
        ...
    @property
    def transform_vehicle_to_sensor(self) -> open3d.cuda.pybind.core.Tensor:
        """
        The 4x4 extrinsic transformation matrix between the vehicle and the sensor frames.
        """
    @transform_vehicle_to_sensor.setter
    def transform_vehicle_to_sensor(self, arg0: open3d.cuda.pybind.core.Tensor) -> None:
        ...
class TransformationEstimationPointToPlane(TransformationEstimation):
    """
    Class to estimate a transformation for point to plane distance.
    """
    def __copy__(self) -> TransformationEstimationPointToPlane:
        ...
    def __deepcopy__(self, arg0: dict) -> TransformationEstimationPointToPlane:
        ...
    @typing.overload
    def __init__(self) -> None:
        """
        Default constructor
        """
    @typing.overload
    def __init__(self, arg0: TransformationEstimationPointToPlane) -> None:
        """
        Copy constructor
        """
    @typing.overload
    def __init__(self, kernel: robust_kernel.RobustKernel) -> None:
        ...
    def __repr__(self) -> str:
        ...
    @property
    def kernel(self) -> robust_kernel.RobustKernel:
        """
        Robust Kernel used in the Optimization
        """
    @kernel.setter
    def kernel(self, arg0: robust_kernel.RobustKernel) -> None:
        ...
class TransformationEstimationPointToPoint(TransformationEstimation):
    """
    Class to estimate a transformation for point to point distance.
    """
    def __copy__(self) -> TransformationEstimationPointToPoint:
        ...
    def __deepcopy__(self, arg0: dict) -> TransformationEstimationPointToPoint:
        ...
    @typing.overload
    def __init__(self, arg0: TransformationEstimationPointToPoint) -> None:
        """
        Copy constructor
        """
    @typing.overload
    def __init__(self) -> None:
        ...
    def __repr__(self) -> str:
        ...
def compute_fpfh_feature(input: open3d.cuda.pybind.t.geometry.PointCloud, max_nn: int | None = 100, radius: float | None = None) -> open3d.cuda.pybind.core.Tensor:
    """
    Function to compute FPFH feature for a point cloud.
    It uses KNN search (Not recommended to use on GPU) if only max_nn parameter
    is provided, Radius search (Not recommended to use on GPU) if only radius
    parameter is provided, and Hybrid search (Recommended) if both are provided.
    
    Args:
        input (open3d.cuda.pybind.t.geometry.PointCloud): The input point cloud with data type float32 or float64.
        max_nn (Optional[int], optional, default=100): [optional] Neighbor search max neighbors parameter.[Default = 100]
        radius (Optional[float], optional, default=None): [optional] Neighbor search radius parameter. [Recommended ~5x voxel size]
    
    Returns:
        open3d.cuda.pybind.core.Tensor
    """
def correspondences_from_features(source_features: open3d.cuda.pybind.core.Tensor, target_features: open3d.cuda.pybind.core.Tensor, mutual_filter: bool = False, mutual_consistency_ratio: float = 0.10000000149011612) -> open3d.cuda.pybind.core.Tensor:
    """
    Function to query nearest neighbors of source_features in target_features.
    
    Args:
        source_features (open3d.cuda.pybind.core.Tensor): The source features in shape (N, dim).
        target_features (open3d.cuda.pybind.core.Tensor): The target features in shape (M, dim).
        mutual_filter (bool, optional, default=False): filter correspondences and return the collection of (i, j) s.t. source_features[i] and target_features[j] are mutually the nearest neighbor.
        mutual_consistency_ratio (float, optional, default=0.10000000149011612): Threshold to decide whether the number of filtered correspondences is sufficient. Only used when mutual_filter is enabled.
    
    Returns:
        open3d.cuda.pybind.core.Tensor
    """
def evaluate_registration(*args, **kwargs) -> RegistrationResult:
    """
    Function for evaluating registration between point clouds
    
    Args:
        source (open3d.cuda.pybind.t.geometry.PointCloud): The source point cloud.
        target (open3d.cuda.pybind.t.geometry.PointCloud): The target point cloud.
        max_correspondence_distance (float): Maximum correspondence points-pair distance.
        transformation (open3d.cuda.pybind.core.Tensor, optional, default=[[1 0 0 0], [0 1 0 0], [0 0 1 0], [0 0 0 1]] Tensor[shape={4, 4}, stride={4, 1}, Float64): The 4x4 transformation matrix of type Float64 to transform ``source`` to ``target``
         ()
    
    Returns:
        open3d.cuda.pybind.t.pipelines.registration.RegistrationResult
    """
def get_information_matrix(source: open3d.cuda.pybind.t.geometry.PointCloud, target: open3d.cuda.pybind.t.geometry.PointCloud, max_correspondence_distance: float, transformation: open3d.cuda.pybind.core.Tensor) -> open3d.cuda.pybind.core.Tensor:
    """
    Function for computing information matrix from transformation matrix. Information matrix is tensor of shape {6, 6}, dtype Float64 on CPU device.
    
    Args:
        source (open3d.cuda.pybind.t.geometry.PointCloud): The source point cloud.
        target (open3d.cuda.pybind.t.geometry.PointCloud): The target point cloud.
        max_correspondence_distance (float): Maximum correspondence points-pair distance.
        transformation (open3d.cuda.pybind.core.Tensor): The 4x4 transformation matrix of type Float64 to transform ``source`` to ``target``
    
    Returns:
        open3d.cuda.pybind.core.Tensor
    """
def icp(*args, **kwargs) -> RegistrationResult:
    """
    Function for ICP registration
    
    Args:
        source (open3d.cuda.pybind.t.geometry.PointCloud): The source point cloud.
        target (open3d.cuda.pybind.t.geometry.PointCloud): The target point cloud.
        max_correspondence_distance (float): Maximum correspondence points-pair distance.
        init_source_to_target (open3d.cuda.pybind.core.Tensor, optional, default=[[1 0 0 0], [0 1 0 0], [0 0 1 0], [0 0 0 1]] Tensor[shape={4, 4}, stride={4, 1}, Float64): Initial transformation estimation
         ()
        estimation_method (open3d.cuda.pybind.t.pipelines.registration.TransformationEstimation, optional, default=TransformationEstimationPointToPoint): Estimation method. One of (``TransformationEstimationPointToPoint``, ``TransformationEstimationPointToPlane``, ``TransformationEstimationForColoredICP``, ``TransformationEstimationForGeneralizedICP``)
        criteria (open3d.cuda.pybind.t.pipelines.registration.ICPConvergenceCriteria, optional, default=ICPConvergenceCriteria[relative_fitness_=1.000000e-06, relative_rmse=1.000000e-06, max_iteration_=30].): Convergence criteria
        voxel_size (float, optional, default=-1.0): The input pointclouds will be down-sampled to this `voxel_size` scale. If `voxel_size` < 0, original scale will be used. However it is highly recommended to down-sample the point-cloud for performance. By default original scale of the point-cloud will be used.
        callback_after_iteration (Callable[[dict[str, open3d.cuda.pybind.core.Tensor]], None], optional, default=None): Optional lambda function, saves string to tensor map of attributes such as iteration_index, scale_index, scale_iteration_index, inlier_rmse, fitness, transformation, on CPU device, updated after each iteration.
    
    Returns:
        open3d.cuda.pybind.t.pipelines.registration.RegistrationResult
    """
def multi_scale_icp(*args, **kwargs) -> RegistrationResult:
    """
    Function for Multi-Scale ICP registration
    
    Args:
        source (open3d.cuda.pybind.t.geometry.PointCloud): The source point cloud.
        target (open3d.cuda.pybind.t.geometry.PointCloud): The target point cloud.
        voxel_sizes (open3d.cuda.pybind.utility.DoubleVector): o3d.utility.DoubleVector of voxel sizes in strictly decreasing order, for multi-scale icp.
        criteria_list (list[open3d.cuda.pybind.t.pipelines.registration.ICPConvergenceCriteria]): List of Convergence criteria for each scale of multi-scale icp.
        max_correspondence_distances (open3d.cuda.pybind.utility.DoubleVector): o3d.utility.DoubleVector of maximum correspondence points-pair distances for multi-scale icp.
        init_source_to_target (open3d.cuda.pybind.core.Tensor, optional, default=[[1 0 0 0], [0 1 0 0], [0 0 1 0], [0 0 0 1]] Tensor[shape={4, 4}, stride={4, 1}, Float64): Initial transformation estimation
         ()
        estimation_method (open3d.cuda.pybind.t.pipelines.registration.TransformationEstimation, optional, default=TransformationEstimationPointToPoint): Estimation method. One of (``TransformationEstimationPointToPoint``, ``TransformationEstimationPointToPlane``, ``TransformationEstimationForColoredICP``, ``TransformationEstimationForGeneralizedICP``)
        callback_after_iteration (Callable[[dict[str, open3d.cuda.pybind.core.Tensor]], None], optional, default=None): Optional lambda function, saves string to tensor map of attributes such as iteration_index, scale_index, scale_iteration_index, inlier_rmse, fitness, transformation, on CPU device, updated after each iteration.
    
    Returns:
        open3d.cuda.pybind.t.pipelines.registration.RegistrationResult
    """
