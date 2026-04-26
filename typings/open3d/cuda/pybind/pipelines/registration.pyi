"""
Registration pipeline.
"""

from __future__ import annotations
import numpy
import open3d.cuda.pybind.geometry
import open3d.cuda.pybind.utility
import typing

__all__: list[str] = [
    "CauchyLoss",
    "CorrespondenceChecker",
    "CorrespondenceCheckerBasedOnDistance",
    "CorrespondenceCheckerBasedOnEdgeLength",
    "CorrespondenceCheckerBasedOnNormal",
    "FastGlobalRegistrationOption",
    "Feature",
    "GMLoss",
    "GlobalOptimizationConvergenceCriteria",
    "GlobalOptimizationGaussNewton",
    "GlobalOptimizationLevenbergMarquardt",
    "GlobalOptimizationMethod",
    "GlobalOptimizationOption",
    "HuberLoss",
    "ICPConvergenceCriteria",
    "L1Loss",
    "L2Loss",
    "PoseGraph",
    "PoseGraphEdge",
    "PoseGraphEdgeVector",
    "PoseGraphNode",
    "PoseGraphNodeVector",
    "RANSACConvergenceCriteria",
    "RegistrationResult",
    "RobustKernel",
    "TransformationEstimation",
    "TransformationEstimationForColoredICP",
    "TransformationEstimationForGeneralizedICP",
    "TransformationEstimationPointToPlane",
    "TransformationEstimationPointToPoint",
    "TukeyLoss",
    "compute_fpfh_feature",
    "correspondences_from_features",
    "evaluate_registration",
    "get_information_matrix_from_point_clouds",
    "global_optimization",
    "m",
    "n",
    "registration_colored_icp",
    "registration_fgr_based_on_correspondence",
    "registration_fgr_based_on_feature_matching",
    "registration_generalized_icp",
    "registration_icp",
    "registration_ransac_based_on_correspondence",
    "registration_ransac_based_on_feature_matching",
]

class CauchyLoss(RobustKernel):
    """

    The loss :math:`\\rho(r)` for a given residual ``r`` is:

    .. math::
      \\begin{equation}
        \\rho(r)=
        \\frac{k^2}{2} \\log\\left(1 + \\left(\\frac{r}{k}\\right)^2\\right)
      \\end{equation}

    The weight :math:`w(r)` for a given residual ``r`` is given by:

    .. math::
      \\begin{equation}
        w(r)=
        \\frac{1}{1 + \\left(\\frac{r}{k}\\right)^2}
      \\end{equation}
    """
    def __copy__(self) -> CauchyLoss: ...
    def __deepcopy__(self, arg0: dict) -> CauchyLoss: ...
    @typing.overload
    def __init__(self, arg0: CauchyLoss) -> None:
        """
        Copy constructor
        """
    @typing.overload
    def __init__(self, k: float) -> None: ...
    def __repr__(self) -> str: ...
    @property
    def k(self) -> float:
        """
        Parameter of the loss.
        """
    @k.setter
    def k(self, arg0: float) -> None: ...

class CorrespondenceChecker:
    """
    Base class that checks if two (small) point clouds can be aligned. This class is used in feature based matching algorithms (such as RANSAC and FastGlobalRegistration) to prune out outlier correspondences. The virtual function Check() must be implemented in subclasses.
    """
    def Check(
        self,
        source: open3d.cuda.pybind.geometry.PointCloud,
        target: open3d.cuda.pybind.geometry.PointCloud,
        corres: open3d.cuda.pybind.utility.Vector2iVector,
        transformation: numpy.ndarray,
    ) -> bool:
        """
        Function to check if two points can be aligned. The two input point clouds must have exact the same number of points.

        Args:
            source (open3d.cuda.pybind.geometry.PointCloud): Source point cloud.
            target (open3d.cuda.pybind.geometry.PointCloud): Target point cloud.
            corres (open3d.cuda.pybind.utility.Vector2iVector): Correspondence set between source and target point cloud.
            transformation (numpy.ndarray[numpy.float64[4, 4]]): The estimated transformation (inplace).

        Returns:
            bool
        """
    @property
    def require_pointcloud_alignment_(self) -> bool:
        """
        Some checkers do not require point clouds to be aligned, e.g., the edge length checker. Some checkers do, e.g., the distance checker.
        """
    @require_pointcloud_alignment_.setter
    def require_pointcloud_alignment_(self, arg0: bool) -> None: ...

class CorrespondenceCheckerBasedOnDistance(CorrespondenceChecker):
    """
    Class to check if aligned point clouds are close (less than specified threshold).
    """
    def __copy__(self) -> CorrespondenceCheckerBasedOnDistance: ...
    def __deepcopy__(self, arg0: dict) -> CorrespondenceCheckerBasedOnDistance: ...
    @typing.overload
    def __init__(self, arg0: CorrespondenceCheckerBasedOnDistance) -> None:
        """
        Copy constructor
        """
    @typing.overload
    def __init__(self, distance_threshold: float) -> None: ...
    def __repr__(self) -> str: ...
    @property
    def distance_threshold(self) -> float:
        """
        Distance threshold for the check.
        """
    @distance_threshold.setter
    def distance_threshold(self, arg0: float) -> None: ...

class CorrespondenceCheckerBasedOnEdgeLength(CorrespondenceChecker):
    """
    Check if two point clouds build the polygons with similar edge lengths. That is, checks if the lengths of any two arbitrary edges (line formed by two vertices) individually drawn within the source point cloud and within the target point cloud with correspondences are similar. The only parameter similarity_threshold is a number between 0 (loose) and 1 (strict)
    """
    def __copy__(self) -> CorrespondenceCheckerBasedOnEdgeLength: ...
    def __deepcopy__(self, arg0: dict) -> CorrespondenceCheckerBasedOnEdgeLength: ...
    @typing.overload
    def __init__(self, arg0: CorrespondenceCheckerBasedOnEdgeLength) -> None:
        """
        Copy constructor
        """
    @typing.overload
    def __init__(self, similarity_threshold: float = 0.9) -> None: ...
    def __repr__(self) -> str: ...
    @property
    def similarity_threshold(self) -> float:
        """
        float value between 0 (loose) and 1 (strict): For the
        check to be true,

        :math:`||\\text{edge}_{\\text{source}}|| > \\text{similarity_threshold} \\times ||\\text{edge}_{\\text{target}}||` and

        :math:`||\\text{edge}_{\\text{target}}|| > \\text{similarity_threshold} \\times ||\\text{edge}_{\\text{source}}||`

        must hold true for all edges.
        """
    @similarity_threshold.setter
    def similarity_threshold(self, arg0: float) -> None: ...

class CorrespondenceCheckerBasedOnNormal(CorrespondenceChecker):
    """
    Class to check if two aligned point clouds have similar normals. It considers vertex normal affinity of any correspondences. It computes dot product of two normal vectors. It takes radian value for the threshold.
    """
    def __copy__(self) -> CorrespondenceCheckerBasedOnNormal: ...
    def __deepcopy__(self, arg0: dict) -> CorrespondenceCheckerBasedOnNormal: ...
    @typing.overload
    def __init__(self, arg0: CorrespondenceCheckerBasedOnNormal) -> None:
        """
        Copy constructor
        """
    @typing.overload
    def __init__(self, normal_angle_threshold: float) -> None: ...
    def __repr__(self) -> str: ...
    @property
    def normal_angle_threshold(self) -> float:
        """
        Radian value for angle threshold.
        """
    @normal_angle_threshold.setter
    def normal_angle_threshold(self, arg0: float) -> None: ...

class FastGlobalRegistrationOption:
    """
    Options for FastGlobalRegistration.
    """
    def __copy__(self) -> FastGlobalRegistrationOption: ...
    def __deepcopy__(self, arg0: dict) -> FastGlobalRegistrationOption: ...
    @typing.overload
    def __init__(self, arg0: FastGlobalRegistrationOption) -> None:
        """
        Copy constructor
        """
    @typing.overload
    def __init__(
        self,
        division_factor: float = 1.4,
        use_absolute_scale: bool = False,
        decrease_mu: bool = False,
        maximum_correspondence_distance: float = 0.025,
        iteration_number: int = 64,
        tuple_scale: float = 0.95,
        maximum_tuple_count: int = 1000,
        tuple_test: bool = True,
    ) -> None: ...
    def __repr__(self) -> str: ...
    @property
    def decrease_mu(self) -> bool:
        """
        bool: Set to ``True`` to decrease scale mu by ``division_factor`` for graduated non-convexity.
        """
    @decrease_mu.setter
    def decrease_mu(self, arg0: bool) -> None: ...
    @property
    def division_factor(self) -> float:
        """
        float: Division factor used for graduated non-convexity.
        """
    @division_factor.setter
    def division_factor(self, arg0: float) -> None: ...
    @property
    def iteration_number(self) -> int:
        """
        int: Maximum number of iterations.
        """
    @iteration_number.setter
    def iteration_number(self, arg0: int) -> None: ...
    @property
    def maximum_correspondence_distance(self) -> float:
        """
        float: Maximum correspondence distance.
        """
    @maximum_correspondence_distance.setter
    def maximum_correspondence_distance(self, arg0: float) -> None: ...
    @property
    def maximum_tuple_count(self) -> int:
        """
        float: Maximum tuple numbers.
        """
    @maximum_tuple_count.setter
    def maximum_tuple_count(self, arg0: int) -> None: ...
    @property
    def tuple_scale(self) -> float:
        """
        float: Similarity measure used for tuples of feature points.
        """
    @tuple_scale.setter
    def tuple_scale(self, arg0: float) -> None: ...
    @property
    def tuple_test(self) -> bool:
        """
        bool: Set to `true` to perform geometric compatibility tests on initial set of correspondences.
        """
    @tuple_test.setter
    def tuple_test(self, arg0: bool) -> None: ...
    @property
    def use_absolute_scale(self) -> bool:
        """
        bool: Measure distance in absolute scale (1) or in scale relative to the diameter of the model (0).
        """
    @use_absolute_scale.setter
    def use_absolute_scale(self, arg0: bool) -> None: ...

class Feature:
    """
    Class to store featrues for registration.
    """
    def __copy__(self) -> Feature: ...
    def __deepcopy__(self, arg0: dict) -> Feature: ...
    @typing.overload
    def __init__(self) -> None:
        """
        Default constructor
        """
    @typing.overload
    def __init__(self, arg0: Feature) -> None:
        """
        Copy constructor
        """
    def __repr__(self) -> str: ...
    def dimension(self) -> int:
        """
        Returns feature dimensions per point.

        Returns:
            int
        """
    def num(self) -> int:
        """
        Returns number of points.

        Returns:
            int
        """
    def resize(self, dim: int, n: int) -> None:
        """
        Resize feature data buffer to ``dim x n``.

        Args:
            dim (int): Feature dimension per point.
            n (int): Number of points.

        Returns:
            None
        """
    def select_by_index(self, indices: list[int], invert: bool = False) -> Feature:
        """
        Function to select features from input Feature group into output Feature group.

        Args:
            indices (list[int]): Indices of features to be selected.
            invert (bool, optional, default=False): Set to ``True`` to invert the selection of indices.

        Returns:
            open3d.cuda.pybind.pipelines.registration.Feature
        """
    @property
    def data(self) -> numpy.ndarray:
        """
        ``dim x n`` float64 numpy array: Data buffer storing features.
        """
    @data.setter
    def data(self, arg0: numpy.ndarray) -> None: ...

class GMLoss(RobustKernel):
    """

    The loss :math:`\\rho(r)` for a given residual ``r`` is:

    .. math::
      \\begin{equation}
        \\rho(r)=
        \\frac{r^2/ 2}{k + r^2}
      \\end{equation}

    The weight :math:`w(r)` for a given residual ``r`` is given by:

    .. math::
      \\begin{equation}
        w(r)=
        \\frac{k}{\\left(k + r^2\\right)^2}
      \\end{equation}
    """
    def __copy__(self) -> GMLoss: ...
    def __deepcopy__(self, arg0: dict) -> GMLoss: ...
    @typing.overload
    def __init__(self, arg0: GMLoss) -> None:
        """
        Copy constructor
        """
    @typing.overload
    def __init__(self, k: float) -> None: ...
    def __repr__(self) -> str: ...
    @property
    def k(self) -> float:
        """
        Parameter of the loss.
        """
    @k.setter
    def k(self, arg0: float) -> None: ...

class GlobalOptimizationConvergenceCriteria:
    """
    Convergence criteria of GlobalOptimization.
    """
    def __copy__(self) -> GlobalOptimizationConvergenceCriteria: ...
    def __deepcopy__(self, arg0: dict) -> GlobalOptimizationConvergenceCriteria: ...
    @typing.overload
    def __init__(self) -> None:
        """
        Default constructor
        """
    @typing.overload
    def __init__(self, arg0: GlobalOptimizationConvergenceCriteria) -> None:
        """
        Copy constructor
        """
    def __repr__(self) -> str: ...
    @property
    def lower_scale_factor(self) -> float:
        """
        float: Lower scale factor value.
        """
    @lower_scale_factor.setter
    def lower_scale_factor(self, arg0: float) -> None: ...
    @property
    def max_iteration(self) -> int:
        """
        int: Maximum iteration number for iterative optimization module.
        """
    @max_iteration.setter
    def max_iteration(self, arg0: int) -> None: ...
    @property
    def max_iteration_lm(self) -> int:
        """
        int: Maximum iteration number for Levenberg Marquardt method. max_iteration_lm is used for additional Levenberg-Marquardt inner loop that automatically changes steepest gradient gain.
        """
    @max_iteration_lm.setter
    def max_iteration_lm(self, arg0: int) -> None: ...
    @property
    def min_relative_increment(self) -> float:
        """
        float: Minimum relative increments.
        """
    @min_relative_increment.setter
    def min_relative_increment(self, arg0: float) -> None: ...
    @property
    def min_relative_residual_increment(self) -> float:
        """
        float: Minimum relative residual increments.
        """
    @min_relative_residual_increment.setter
    def min_relative_residual_increment(self, arg0: float) -> None: ...
    @property
    def min_residual(self) -> float:
        """
        float: Minimum residual value.
        """
    @min_residual.setter
    def min_residual(self, arg0: float) -> None: ...
    @property
    def min_right_term(self) -> float:
        """
        float: Minimum right term value.
        """
    @min_right_term.setter
    def min_right_term(self, arg0: float) -> None: ...
    @property
    def upper_scale_factor(self) -> float:
        """
        float: Upper scale factor value. Scaling factors are used for levenberg marquardt algorithm these are scaling factors that increase/decrease lambda used in H_LM = H + lambda * I
        """
    @upper_scale_factor.setter
    def upper_scale_factor(self, arg0: float) -> None: ...

class GlobalOptimizationGaussNewton(GlobalOptimizationMethod):
    """
    Global optimization with Gauss-Newton algorithm.
    """
    def __copy__(self) -> GlobalOptimizationGaussNewton: ...
    def __deepcopy__(self, arg0: dict) -> GlobalOptimizationGaussNewton: ...
    @typing.overload
    def __init__(self) -> None:
        """
        Default constructor
        """
    @typing.overload
    def __init__(self, arg0: GlobalOptimizationGaussNewton) -> None:
        """
        Copy constructor
        """
    def __repr__(self) -> str: ...

class GlobalOptimizationLevenbergMarquardt(GlobalOptimizationMethod):
    """
    Global optimization with Levenberg-Marquardt algorithm. Recommended over the Gauss-Newton method since the LM has better convergence characteristics.
    """
    def __copy__(self) -> GlobalOptimizationLevenbergMarquardt: ...
    def __deepcopy__(self, arg0: dict) -> GlobalOptimizationLevenbergMarquardt: ...
    @typing.overload
    def __init__(self) -> None:
        """
        Default constructor
        """
    @typing.overload
    def __init__(self, arg0: GlobalOptimizationLevenbergMarquardt) -> None:
        """
        Copy constructor
        """
    def __repr__(self) -> str: ...

class GlobalOptimizationMethod:
    """
    Base class for global optimization method.
    """
    def OptimizePoseGraph(
        self, pose_graph: PoseGraph, criteria: GlobalOptimizationConvergenceCriteria, option: GlobalOptimizationOption
    ) -> None:
        """
        Run pose graph optimization.

        Args:
            pose_graph (open3d.cuda.pybind.pipelines.registration.PoseGraph): The pose graph to be optimized (in-place).
            criteria (open3d.cuda.pybind.pipelines.registration.GlobalOptimizationConvergenceCriteria): Convergence criteria.
            option (open3d.cuda.pybind.pipelines.registration.GlobalOptimizationOption): Global optimization options.

        Returns:
            None
        """

class GlobalOptimizationOption:
    """
    Option for GlobalOptimization.
    """
    def __copy__(self) -> GlobalOptimizationOption: ...
    def __deepcopy__(self, arg0: dict) -> GlobalOptimizationOption: ...
    @typing.overload
    def __init__(self) -> None:
        """
        Default constructor
        """
    @typing.overload
    def __init__(self, arg0: GlobalOptimizationOption) -> None:
        """
        Copy constructor
        """
    @typing.overload
    def __init__(
        self,
        max_correspondence_distance: float = 0.03,
        edge_prune_threshold: float = 0.25,
        preference_loop_closure: float = 1.0,
        reference_node: int = -1,
    ) -> None: ...
    def __repr__(self) -> str: ...
    @property
    def edge_prune_threshold(self) -> float:
        """
        float: According to [Choi et al 2015], line_process weight < edge_prune_threshold (0.25) is pruned.
        """
    @edge_prune_threshold.setter
    def edge_prune_threshold(self, arg0: float) -> None: ...
    @property
    def max_correspondence_distance(self) -> float:
        """
        float: Identifies which distance value is used for finding neighboring points when making information matrix. According to [Choi et al 2015], this distance is used for determining $mu, a line process weight.
        """
    @max_correspondence_distance.setter
    def max_correspondence_distance(self, arg0: float) -> None: ...
    @property
    def preference_loop_closure(self) -> float:
        """
        float: Balancing parameter to decide which one is more reliable: odometry vs loop-closure. [0,1] -> try to unchange odometry edges, [1) -> try to utilize loop-closure. Recommendation: 0.1 for RGBD Odometry, 2.0 for fragment registration.
        """
    @preference_loop_closure.setter
    def preference_loop_closure(self, arg0: float) -> None: ...
    @property
    def reference_node(self) -> int:
        """
        int: The pose of this node is unchanged after optimization.
        """
    @reference_node.setter
    def reference_node(self, arg0: int) -> None: ...

class HuberLoss(RobustKernel):
    """
    
    The loss :math:`\\rho(r)` for a given residual ``r`` is:
    
    .. math::
      \\begin{equation}
        \\rho(r)=
        \\begin{cases}
          \\frac{r^{2}}{2}, & |r| \\leq k.\\\\
          k(|r|-k / 2), & \\text{otherwise}.
        \\end{cases}
      \\end{equation}
    
    The weight :math:`w(r)` for a given residual ``r`` is given by:
    
    .. math::
      \\begin{equation}
        w(r)=
        \\begin{cases}
          1,              & |r| \\leq k.       \\\\
          \\frac{k}{|r|} , & \\text{otherwise}.
        \\end{cases}
      \\end{equation}
    """
    def __copy__(self) -> HuberLoss: ...
    def __deepcopy__(self, arg0: dict) -> HuberLoss: ...
    @typing.overload
    def __init__(self, arg0: HuberLoss) -> None:
        """
        Copy constructor
        """
    @typing.overload
    def __init__(self, k: float) -> None: ...
    def __repr__(self) -> str: ...
    @property
    def k(self) -> float:
        """
        Parameter of the loss
        """
    @k.setter
    def k(self, arg0: float) -> None: ...

class ICPConvergenceCriteria:
    """
    Class that defines the convergence criteria of ICP. ICP algorithm stops if the relative change of fitness and rmse hit ``relative_fitness`` and ``relative_rmse`` individually, or the iteration number exceeds ``max_iteration``.
    """
    def __copy__(self) -> ICPConvergenceCriteria: ...
    def __deepcopy__(self, arg0: dict) -> ICPConvergenceCriteria: ...
    @typing.overload
    def __init__(self, arg0: ICPConvergenceCriteria) -> None:
        """
        Copy constructor
        """
    @typing.overload
    def __init__(
        self, relative_fitness: float = 1e-06, relative_rmse: float = 1e-06, max_iteration: int = 30
    ) -> None: ...
    def __repr__(self) -> str: ...
    @property
    def max_iteration(self) -> int:
        """
        Maximum iteration before iteration stops.
        """
    @max_iteration.setter
    def max_iteration(self, arg0: int) -> None: ...
    @property
    def relative_fitness(self) -> float:
        """
        If relative change (difference) of fitness score is lower than ``relative_fitness``, the iteration stops.
        """
    @relative_fitness.setter
    def relative_fitness(self, arg0: float) -> None: ...
    @property
    def relative_rmse(self) -> float:
        """
        If relative change (difference) of inliner RMSE score is lower than ``relative_rmse``, the iteration stops.
        """
    @relative_rmse.setter
    def relative_rmse(self, arg0: float) -> None: ...

class L1Loss(RobustKernel):
    """

    The loss :math:`\\rho(r)` for a given residual ``r`` is given by:

    .. math:: \\rho(r) = |r|

    The weight :math:`w(r)` for a given residual ``r`` is given by:

    .. math:: w(r) = \\frac{1}{|r|}
    """
    def __copy__(self) -> L1Loss: ...
    def __deepcopy__(self, arg0: dict) -> L1Loss: ...
    @typing.overload
    def __init__(self) -> None:
        """
        Default constructor
        """
    @typing.overload
    def __init__(self, arg0: L1Loss) -> None:
        """
        Copy constructor
        """
    def __repr__(self) -> str: ...

class L2Loss(RobustKernel):
    """

    The loss :math:`\\rho(r)` for a given residual ``r`` is given by:

    .. math:: \\rho(r) = \\frac{r^2}{2}

    The weight :math:`w(r)` for a given residual ``r`` is given by:

    .. math:: w(r) = 1
    """
    def __copy__(self) -> L2Loss: ...
    def __deepcopy__(self, arg0: dict) -> L2Loss: ...
    @typing.overload
    def __init__(self) -> None:
        """
        Default constructor
        """
    @typing.overload
    def __init__(self, arg0: L2Loss) -> None:
        """
        Copy constructor
        """
    def __repr__(self) -> str: ...

class PoseGraph:
    """
    Data structure defining the pose graph.
    """
    def __copy__(self) -> PoseGraph: ...
    def __deepcopy__(self, arg0: dict) -> PoseGraph: ...
    @typing.overload
    def __init__(self) -> None:
        """
        Default constructor
        """
    @typing.overload
    def __init__(self, arg0: PoseGraph) -> None:
        """
        Copy constructor
        """
    def __repr__(self) -> str: ...
    @property
    def edges(self) -> PoseGraphEdgeVector:
        """
        ``List(PoseGraphEdge)``: List of ``PoseGraphEdge``.
        """
    @edges.setter
    def edges(self, arg0: PoseGraphEdgeVector) -> None: ...
    @property
    def nodes(self) -> PoseGraphNodeVector:
        """
        ``List(PoseGraphNode)``: List of ``PoseGraphNode``.
        """
    @nodes.setter
    def nodes(self, arg0: PoseGraphNodeVector) -> None: ...

class PoseGraphEdge:
    """
    Edge of ``PoseGraph``.
    """
    def __copy__(self) -> PoseGraphEdge: ...
    def __deepcopy__(self, arg0: dict) -> PoseGraphEdge: ...
    @typing.overload
    def __init__(self) -> None:
        """
        Default constructor
        """
    @typing.overload
    def __init__(self, arg0: PoseGraphEdge) -> None:
        """
        Copy constructor
        """
    @typing.overload
    def __init__(
        self,
        source_node_id: int = -1,
        target_node_id: int = -1,
        transformation: numpy.ndarray = ...,
        information: numpy.ndarray = ...,
        uncertain: bool = False,
        confidence: float = 1.0,
    ) -> None: ...
    def __repr__(self) -> str: ...
    @property
    def confidence(self) -> float:
        """
        float from 0 to 1: Confidence value of the edge. if uncertain is true, it has confidence bounded in [0,1].   1 means reliable, and 0 means unreliable edge. This correspondence to line process value in [Choi et al 2015] See core/registration/globaloptimization.h for more details.
        """
    @confidence.setter
    def confidence(self, arg0: float) -> None: ...
    @property
    def information(self) -> numpy.ndarray:
        """
        ``6 x 6`` float64 numpy array: Information matrix.
        """
    @information.setter
    def information(self, arg0: numpy.ndarray) -> None: ...
    @property
    def source_node_id(self) -> int:
        """
        int: Source ``PoseGraphNode`` id.
        """
    @source_node_id.setter
    def source_node_id(self, arg0: int) -> None: ...
    @property
    def target_node_id(self) -> int:
        """
        int: Target ``PoseGraphNode`` id.
        """
    @target_node_id.setter
    def target_node_id(self, arg0: int) -> None: ...
    @property
    def transformation(self) -> numpy.ndarray:
        """
        ``4 x 4`` float64 numpy array: Transformation matrix.
        """
    @transformation.setter
    def transformation(self, arg0: numpy.ndarray) -> None: ...
    @property
    def uncertain(self) -> bool:
        """
        bool: Whether the edge is uncertain. Odometry edge has uncertain == false, loop closure edges has uncertain == true
        """
    @uncertain.setter
    def uncertain(self, arg0: bool) -> None: ...

class PoseGraphEdgeVector:
    """
    Vector of PoseGraphEdge
    """
    def __bool__(self) -> bool:
        """
        Check whether the list is nonempty
        """
    @typing.overload
    def __delitem__(self, arg0: int) -> None:
        """
        Delete the list elements at index ``i``
        """
    @typing.overload
    def __delitem__(self, arg0: slice) -> None:
        """
        Delete list elements using a slice object
        """
    @typing.overload
    def __getitem__(self, s: slice) -> PoseGraphEdgeVector:
        """
        Retrieve list elements using a slice object
        """
    @typing.overload
    def __getitem__(self, arg0: int) -> PoseGraphEdge: ...
    @typing.overload
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(self, arg0: PoseGraphEdgeVector) -> None:
        """
        Copy constructor
        """
    @typing.overload
    def __init__(self, arg0: typing.Iterable) -> None: ...
    def __iter__(self) -> typing.Iterator[PoseGraphEdge]: ...
    def __len__(self) -> int: ...
    @typing.overload
    def __setitem__(self, arg0: int, arg1: PoseGraphEdge) -> None: ...
    @typing.overload
    def __setitem__(self, arg0: slice, arg1: PoseGraphEdgeVector) -> None:
        """
        Assign list elements using a slice object
        """
    def append(self, x: PoseGraphEdge) -> None:
        """
        Add an item to the end of the list
        """
    def clear(self) -> None:
        """
        Clear the contents
        """
    @typing.overload
    def extend(self, L: PoseGraphEdgeVector) -> None:
        """
        Extend the list by appending all the items in the given list
        """
    @typing.overload
    def extend(self, L: typing.Iterable) -> None:
        """
        Extend the list by appending all the items in the given list
        """
    def insert(self, i: int, x: PoseGraphEdge) -> None:
        """
        Insert an item at a given position.
        """
    @typing.overload
    def pop(self) -> PoseGraphEdge:
        """
        Remove and return the last item
        """
    @typing.overload
    def pop(self, i: int) -> PoseGraphEdge:
        """
        Remove and return the item at index ``i``
        """

class PoseGraphNode:
    """
    Node of ``PoseGraph``.
    """

    pose: numpy.ndarray
    def __copy__(self) -> PoseGraphNode: ...
    def __deepcopy__(self, arg0: dict) -> PoseGraphNode: ...
    @typing.overload
    def __init__(self) -> None:
        """
        Default constructor
        """
    @typing.overload
    def __init__(self, arg0: PoseGraphNode) -> None:
        """
        Copy constructor
        """
    @typing.overload
    def __init__(self, pose: numpy.ndarray) -> None: ...
    def __repr__(self) -> str: ...

class PoseGraphNodeVector:
    """
    Vector of PoseGraphNode
    """
    def __bool__(self) -> bool:
        """
        Check whether the list is nonempty
        """
    @typing.overload
    def __delitem__(self, arg0: int) -> None:
        """
        Delete the list elements at index ``i``
        """
    @typing.overload
    def __delitem__(self, arg0: slice) -> None:
        """
        Delete list elements using a slice object
        """
    @typing.overload
    def __getitem__(self, s: slice) -> PoseGraphNodeVector:
        """
        Retrieve list elements using a slice object
        """
    @typing.overload
    def __getitem__(self, arg0: int) -> PoseGraphNode: ...
    @typing.overload
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(self, arg0: PoseGraphNodeVector) -> None:
        """
        Copy constructor
        """
    @typing.overload
    def __init__(self, arg0: typing.Iterable) -> None: ...
    def __iter__(self) -> typing.Iterator[PoseGraphNode]: ...
    def __len__(self) -> int: ...
    @typing.overload
    def __setitem__(self, arg0: int, arg1: PoseGraphNode) -> None: ...
    @typing.overload
    def __setitem__(self, arg0: slice, arg1: PoseGraphNodeVector) -> None:
        """
        Assign list elements using a slice object
        """
    def append(self, x: PoseGraphNode) -> None:
        """
        Add an item to the end of the list
        """
    def clear(self) -> None:
        """
        Clear the contents
        """
    @typing.overload
    def extend(self, L: PoseGraphNodeVector) -> None:
        """
        Extend the list by appending all the items in the given list
        """
    @typing.overload
    def extend(self, L: typing.Iterable) -> None:
        """
        Extend the list by appending all the items in the given list
        """
    def insert(self, i: int, x: PoseGraphNode) -> None:
        """
        Insert an item at a given position.
        """
    @typing.overload
    def pop(self) -> PoseGraphNode:
        """
        Remove and return the last item
        """
    @typing.overload
    def pop(self, i: int) -> PoseGraphNode:
        """
        Remove and return the item at index ``i``
        """

class RANSACConvergenceCriteria:
    """
    Class that defines the convergence criteria of RANSAC. RANSAC algorithm stops if the iteration number hits ``max_iteration``, or the fitness measured during validation suggests that the algorithm can be terminated early with some ``confidence``. Early termination takes place when the number of iterations reaches ``k = log(1 - confidence)/log(1 - fitness^{ransac_n})``, where ``ransac_n`` is the number of points used during a ransac iteration. Use confidence=1.0 to avoid early termination.
    """
    def __copy__(self) -> RANSACConvergenceCriteria: ...
    def __deepcopy__(self, arg0: dict) -> RANSACConvergenceCriteria: ...
    @typing.overload
    def __init__(self, arg0: RANSACConvergenceCriteria) -> None:
        """
        Copy constructor
        """
    @typing.overload
    def __init__(self, max_iteration: int = 100000, confidence: float = 0.999) -> None: ...
    def __repr__(self) -> str: ...
    @property
    def confidence(self) -> float:
        """
        Desired probability of success. Used for estimating early termination. Use 1.0 to avoid early termination.
        """
    @confidence.setter
    def confidence(self, arg0: float) -> None: ...
    @property
    def max_iteration(self) -> int:
        """
        Maximum iteration before iteration stops.
        """
    @max_iteration.setter
    def max_iteration(self, arg0: int) -> None: ...

class RegistrationResult:
    """
    Class that contains the registration results.
    """
    def __copy__(self) -> RegistrationResult: ...
    def __deepcopy__(self, arg0: dict) -> RegistrationResult: ...
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
    def __repr__(self) -> str: ...
    @property
    def correspondence_set(self) -> open3d.cuda.pybind.utility.Vector2iVector:
        """
        ``n x 2`` int numpy array: Correspondence set between source and target point cloud.
        """
    @correspondence_set.setter
    def correspondence_set(self, arg0: open3d.cuda.pybind.utility.Vector2iVector) -> None: ...
    @property
    def fitness(self) -> float:
        """
        float: The overlapping area (# of inlier correspondences / # of points in source). Higher is better.
        """
    @fitness.setter
    def fitness(self, arg0: float) -> None: ...
    @property
    def inlier_rmse(self) -> float:
        """
        float: RMSE of all inlier correspondences. Lower is better.
        """
    @inlier_rmse.setter
    def inlier_rmse(self, arg0: float) -> None: ...
    @property
    def transformation(self) -> numpy.ndarray:
        """
        ``4 x 4`` float64 numpy array: The estimated transformation matrix.
        """
    @transformation.setter
    def transformation(self, arg0: numpy.ndarray) -> None: ...

class RobustKernel:
    """
    
    Base class that models a robust kernel for outlier rejection. The virtual
    function ``weight()`` must be implemented in derived classes.
    
    The main idea of a robust loss is to downweight large residuals that are
    assumed to be caused from outliers such that their influence on the solution
    is reduced. This is achieved by optimizing:
    
    .. math::
      \\def\\argmin{\\mathop{\\rm argmin}}
      \\begin{equation}
        x^{*} = \\argmin_{x} \\sum_{i=1}^{N} \\rho({r_i(x)})
      \\end{equation}
      :label: robust_loss
    
    where :math:`\\rho(r)` is also called the robust loss or kernel and
    :math:`r_i(x)` is the residual.
    
    Several robust kernels have been proposed to deal with different kinds of
    outliers such as Huber, Cauchy, and others.
    
    The optimization problem in :eq:`robust_loss` can be solved using the
    iteratively reweighted least squares (IRLS) approach, which solves a sequence
    of weighted least squares problems. We can see the relation between the least
    squares optimization in stanad non-linear least squares and robust loss
    optimization by comparing the respective gradients which go to zero at the
    optimum (illustrated only for the :math:`i^\\mathrm{th}` residual):
    
    .. math::
      \\begin{eqnarray}
        \\frac{1}{2}\\frac{\\partial (w_i r^2_i(x))}{\\partial{x}}
        &=&
        w_i r_i(x) \\frac{\\partial r_i(x)}{\\partial{x}} \\\\
        \\label{eq:gradient_ls}
        \\frac{\\partial(\\rho(r_i(x)))}{\\partial{x}}
        &=&
        \\rho'(r_i(x)) \\frac{\\partial r_i(x)}{\\partial{x}}.
      \\end{eqnarray}
    
    By setting the weight :math:`w_i= \\frac{1}{r_i(x)}\\rho'(r_i(x))`, we
    can solve the robust loss optimization problem by using the existing techniques
    for weighted least-squares. This scheme allows standard solvers using
    Gauss-Newton and Levenberg-Marquardt algorithms to optimize for robust losses
    and is the one implemented in Open3D.
    
    Then we minimize the objective function using Gauss-Newton and determine
    increments by iteratively solving:
    
    .. math::
      \\newcommand{\\mat}[1]{\\mathbf{#1}}
      \\newcommand{\\veca}[1]{\\vec{#1}}
      \\renewcommand{\\vec}[1]{\\mathbf{#1}}
      \\begin{align}
       \\left(\\mat{J}^\\top \\mat{W} \\mat{J}\\right)^{-1}\\mat{J}^\\top\\mat{W}\\vec{r},
      \\end{align}
    
    where :math:`\\mat{W} \\in \\mathbb{R}^{n\\times n}` is a diagonal matrix containing
    weights :math:`w_i` for each residual :math:`r_i`
    
    The different loss functions will only impact in the weight for each residual
    during the optimization step.
    Therefore, the only impact of the choice on the kernel is through its first
    order derivate.
    
    The kernels implemented so far, and the notation has been inspired by the
    publication: **"Analysis of Robust Functions for Registration Algorithms"**, by
    Philippe Babin et al.
    
    For more information please also see: **"Adaptive Robust Kernels for
    Non-Linear Least Squares Problems"**, by Nived Chebrolu et al.
    """
    def weight(self, residual: float) -> float:
        """
        Obtain the weight for the given residual according to the robust kernel model.

        Args:
            residual (float): value obtained during the optimization problem

        Returns:
            float
        """

class TransformationEstimation:
    """
    Base class that estimates a transformation between two point clouds. The virtual function ComputeTransformation() must be implemented in subclasses.
    """
    def compute_rmse(
        self,
        source: open3d.cuda.pybind.geometry.PointCloud,
        target: open3d.cuda.pybind.geometry.PointCloud,
        corres: open3d.cuda.pybind.utility.Vector2iVector,
    ) -> float:
        """
        Compute RMSE between source and target points cloud given correspondences.

        Args:
            source (open3d.cuda.pybind.geometry.PointCloud): Source point cloud.
            target (open3d.cuda.pybind.geometry.PointCloud): Target point cloud.
            corres (open3d.cuda.pybind.utility.Vector2iVector): Correspondence set between source and target point cloud.

        Returns:
            float
        """
    def compute_transformation(
        self,
        source: open3d.cuda.pybind.geometry.PointCloud,
        target: open3d.cuda.pybind.geometry.PointCloud,
        corres: open3d.cuda.pybind.utility.Vector2iVector,
    ) -> numpy.ndarray:
        """
        Compute transformation from source to target point cloud given correspondences.

        Args:
            source (open3d.cuda.pybind.geometry.PointCloud): Source point cloud.
            target (open3d.cuda.pybind.geometry.PointCloud): Target point cloud.
            corres (open3d.cuda.pybind.utility.Vector2iVector): Correspondence set between source and target point cloud.

        Returns:
            numpy.ndarray[numpy.float64[4, 4]]
        """

class TransformationEstimationForColoredICP(TransformationEstimation):
    """
    Class to estimate a transformation between two point clouds using color information
    """
    def __copy__(self) -> TransformationEstimationForColoredICP: ...
    def __deepcopy__(self, arg0: dict) -> TransformationEstimationForColoredICP: ...
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
    def __init__(self, lambda_geometric: float, kernel: RobustKernel) -> None: ...
    @typing.overload
    def __init__(self, lambda_geometric: float) -> None: ...
    @typing.overload
    def __init__(self, kernel: RobustKernel) -> None: ...
    def __repr__(self) -> str: ...
    @property
    def kernel(self) -> RobustKernel:
        """
        Robust Kernel used in the Optimization
        """
    @kernel.setter
    def kernel(self, arg0: RobustKernel) -> None: ...
    @property
    def lambda_geometric(self) -> float:
        """
        lambda_geometric
        """
    @lambda_geometric.setter
    def lambda_geometric(self, arg0: float) -> None: ...

class TransformationEstimationForGeneralizedICP(TransformationEstimation):
    """
    Class to estimate a transformation for Generalized ICP.
    """
    def __copy__(self) -> TransformationEstimationForGeneralizedICP: ...
    def __deepcopy__(self, arg0: dict) -> TransformationEstimationForGeneralizedICP: ...
    @typing.overload
    def __init__(self) -> None:
        """
        Default constructor
        """
    @typing.overload
    def __init__(self, arg0: TransformationEstimationForGeneralizedICP) -> None:
        """
        Copy constructor
        """
    @typing.overload
    def __init__(self, epsilon: float, kernel: RobustKernel) -> None: ...
    @typing.overload
    def __init__(self, epsilon: float) -> None: ...
    @typing.overload
    def __init__(self, kernel: RobustKernel) -> None: ...
    def __repr__(self) -> str: ...
    @property
    def epsilon(self) -> float:
        """
        epsilon
        """
    @epsilon.setter
    def epsilon(self, arg0: float) -> None: ...
    @property
    def kernel(self) -> RobustKernel:
        """
        Robust Kernel used in the Optimization
        """
    @kernel.setter
    def kernel(self, arg0: RobustKernel) -> None: ...

class TransformationEstimationPointToPlane(TransformationEstimation):
    """
    Class to estimate a transformation for point to plane distance.
    """
    def __copy__(self) -> TransformationEstimationPointToPlane: ...
    def __deepcopy__(self, arg0: dict) -> TransformationEstimationPointToPlane: ...
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
    def __init__(self, kernel: RobustKernel) -> None: ...
    def __repr__(self) -> str: ...
    @property
    def kernel(self) -> RobustKernel:
        """
        Robust Kernel used in the Optimization
        """
    @kernel.setter
    def kernel(self, arg0: RobustKernel) -> None: ...

class TransformationEstimationPointToPoint(TransformationEstimation):
    """
    Class to estimate a transformation for point to point distance.
    """
    def __copy__(self) -> TransformationEstimationPointToPoint: ...
    def __deepcopy__(self, arg0: dict) -> TransformationEstimationPointToPoint: ...
    @typing.overload
    def __init__(self, arg0: TransformationEstimationPointToPoint) -> None:
        """
        Copy constructor
        """
    @typing.overload
    def __init__(self, with_scaling: bool = False) -> None: ...
    def __repr__(self) -> str: ...
    @property
    def with_scaling(self) -> bool:
        """
        Set to ``True`` to estimate scaling, ``False`` to force
        scaling to be ``1``.

        The homogeneous transformation is given by

        :math:`T = \\begin{bmatrix} c\\mathbf{R} & \\mathbf{t} \\\\ \\mathbf{0} & 1 \\end{bmatrix}`

        Sets :math:`c = 1` if ``with_scaling`` is ``False``.
        """
    @with_scaling.setter
    def with_scaling(self, arg0: bool) -> None: ...

class TukeyLoss(RobustKernel):
    """
    
    The loss :math:`\\rho(r)` for a given residual ``r`` is:
    
    .. math::
      \\begin{equation}
        \\rho(r)=
        \\begin{cases}
          \\frac{k^2\\left[1-\\left(1-\\left(\\frac{e}{k}\\right)^2\\right)^3\\right]}{2}, & |r| \\leq k.       \\\\
          \\frac{k^2}{2},                                                           & \\text{otherwise}.
        \\end{cases}
      \\end{equation}
    
    The weight :math:`w(r)` for a given residual ``r`` is given by:
    
    .. math::
      \\begin{equation}
        w(r)=
        \\begin{cases}
          \\left(1 - \\left(\\frac{r}{k}\\right)^2\\right)^2, & |r| \\leq k.       \\\\
          0 ,                                            & \\text{otherwise}.
        \\end{cases}
      \\end{equation}
    """
    def __copy__(self) -> TukeyLoss: ...
    def __deepcopy__(self, arg0: dict) -> TukeyLoss: ...
    @typing.overload
    def __init__(self, arg0: TukeyLoss) -> None:
        """
        Copy constructor
        """
    @typing.overload
    def __init__(self, k: float) -> None: ...
    def __repr__(self) -> str: ...
    @property
    def k(self) -> float:
        """
        ``k`` Is a running constant for the loss.
        """
    @k.setter
    def k(self, arg0: float) -> None: ...

def compute_fpfh_feature(
    input: open3d.cuda.pybind.geometry.PointCloud, search_param: open3d.cuda.pybind.geometry.KDTreeSearchParam
) -> Feature:
    """
    Function to compute FPFH feature for a point cloud

    Args:
        input (open3d.cuda.pybind.geometry.PointCloud): The Input point cloud.
        search_param (open3d.cuda.pybind.geometry.KDTreeSearchParam): KDTree KNN search parameter.

    Returns:
        open3d.cuda.pybind.pipelines.registration.Feature
    """

def correspondences_from_features(
    source_features: Feature,
    target_features: Feature,
    mutual_filter: bool = False,
    mutual_consistency_ratio: float = 0.10000000149011612,
) -> open3d.cuda.pybind.utility.Vector2iVector:
    """
    Function to find nearest neighbor correspondences from features

    Args:
        source_features (open3d.cuda.pybind.pipelines.registration.Feature): The source features stored in (dim, N).
        target_features (open3d.cuda.pybind.pipelines.registration.Feature): The target features stored in (dim, M).
        mutual_filter (bool, optional, default=False): filter correspondences and return the collection of (i, j) s.t. source_features[i] and target_features[j] are mutually the nearest neighbor.
        mutual_consistency_ratio (float, optional, default=0.10000000149011612): Threshold to decide whether the number of filtered correspondences is sufficient. Only used when mutual_filter is enabled.

    Returns:
        open3d.cuda.pybind.utility.Vector2iVector
    """

def evaluate_registration(
    source: open3d.cuda.pybind.geometry.PointCloud,
    target: open3d.cuda.pybind.geometry.PointCloud,
    max_correspondence_distance: float,
    transformation: numpy.ndarray = ...,
) -> RegistrationResult:
    """
    Function for evaluating registration between point clouds

    Args:
        source (open3d.cuda.pybind.geometry.PointCloud): The source point cloud.
        target (open3d.cuda.pybind.geometry.PointCloud): The target point cloud.
        max_correspondence_distance (float): Maximum correspondence points-pair distance.
        transformation (numpy.ndarray[numpy.float64[4, 4]], optional, default=array([[1., 0., 0., 0.], [0., 1., 0., 0.], [0., 0., 1., 0.], [0., 0., 0., 1.]])): The 4x4 transformation matrix to transform ``source`` to ``target``

    Returns:
        open3d.cuda.pybind.pipelines.registration.RegistrationResult
    """

def get_information_matrix_from_point_clouds(
    source: open3d.cuda.pybind.geometry.PointCloud,
    target: open3d.cuda.pybind.geometry.PointCloud,
    max_correspondence_distance: float,
    transformation: numpy.ndarray,
) -> numpy.ndarray:
    """
    Function for computing information matrix from transformation matrix

    Args:
        source (open3d.cuda.pybind.geometry.PointCloud): The source point cloud.
        target (open3d.cuda.pybind.geometry.PointCloud): The target point cloud.
        max_correspondence_distance (float): Maximum correspondence points-pair distance.
        transformation (numpy.ndarray[numpy.float64[4, 4]]): The 4x4 transformation matrix to transform ``source`` to ``target``

    Returns:
        numpy.ndarray[numpy.float64[6, 6]]
    """

def global_optimization(
    pose_graph: PoseGraph,
    method: GlobalOptimizationMethod,
    criteria: GlobalOptimizationConvergenceCriteria,
    option: GlobalOptimizationOption,
) -> None:
    """
    Function to optimize PoseGraph

    Args:
        pose_graph (open3d.cuda.pybind.pipelines.registration.PoseGraph): The pose_graph to be optimized (in-place).
        method (open3d.cuda.pybind.pipelines.registration.GlobalOptimizationMethod): Global optimization method. Either ``GlobalOptimizationGaussNewton()`` or ``GlobalOptimizationLevenbergMarquardt()``.
        criteria (open3d.cuda.pybind.pipelines.registration.GlobalOptimizationConvergenceCriteria): Global optimization convergence criteria.
        option (open3d.cuda.pybind.pipelines.registration.GlobalOptimizationOption): Global optimization option.

    Returns:
        None
    """

def registration_colored_icp(
    source: open3d.cuda.pybind.geometry.PointCloud,
    target: open3d.cuda.pybind.geometry.PointCloud,
    max_correspondence_distance: float,
    init: numpy.ndarray = ...,
    estimation_method: TransformationEstimationForColoredICP = ...,
    criteria: ICPConvergenceCriteria = ...,
) -> RegistrationResult:
    """
    Function for Colored ICP registration

    Args:
        source (open3d.cuda.pybind.geometry.PointCloud): The source point cloud.
        target (open3d.cuda.pybind.geometry.PointCloud): The target point cloud.
        max_correspondence_distance (float): Maximum correspondence points-pair distance.
        init (numpy.ndarray[numpy.float64[4, 4]], optional, default=array([[1., 0., 0., 0.], [0., 1., 0., 0.], [0., 0., 1., 0.], [0., 0., 0., 1.]])): Initial transformation estimation
        estimation_method (open3d.cuda.pybind.pipelines.registration.TransformationEstimationForColoredICP, optional, default=TransformationEstimationForColoredICP(lambda_geometric=0.968)): Estimation method. One of (``TransformationEstimationPointToPoint``, ``TransformationEstimationPointToPlane``, ``TransformationEstimationForGeneralizedICP``, ``TransformationEstimationForColoredICP``)
        criteria (open3d.cuda.pybind.pipelines.registration.ICPConvergenceCriteria, optional, default=ICPConvergenceCriteria(relative_fitness=1.000000e-06, relative_rmse=1.000000e-06, max_iteration=30)): Convergence criteria

    Returns:
        open3d.cuda.pybind.pipelines.registration.RegistrationResult
    """

def registration_fgr_based_on_correspondence(
    source: open3d.cuda.pybind.geometry.PointCloud,
    target: open3d.cuda.pybind.geometry.PointCloud,
    corres: open3d.cuda.pybind.utility.Vector2iVector,
    option: FastGlobalRegistrationOption = ...,
) -> RegistrationResult:
    """
    Function for fast global registration based on a set of correspondences

    Args:
        source (open3d.cuda.pybind.geometry.PointCloud): The source point cloud.
        target (open3d.cuda.pybind.geometry.PointCloud): The target point cloud.
        corres (open3d.cuda.pybind.utility.Vector2iVector): o3d.utility.Vector2iVector that stores indices of corresponding point or feature arrays.
        option (open3d.cuda.pybind.pipelines.registration.FastGlobalRegistrationOption, optional, default=FastGlobalRegistrationOption( division_factor=1.4, use_absolute_scale=false, decrease_mu=true, maximum_correspondence_distance=0.025, iteration_number=64, tuple_scale=0.95, maximum_tuple_count=1000, tuple_test=true, )): Registration option

    Returns:
        open3d.cuda.pybind.pipelines.registration.RegistrationResult
    """

def registration_fgr_based_on_feature_matching(
    source: open3d.cuda.pybind.geometry.PointCloud,
    target: open3d.cuda.pybind.geometry.PointCloud,
    source_feature: Feature,
    target_feature: Feature,
    option: FastGlobalRegistrationOption = ...,
) -> RegistrationResult:
    """
    Function for fast global registration based on feature matching

    Args:
        source (open3d.cuda.pybind.geometry.PointCloud): The source point cloud.
        target (open3d.cuda.pybind.geometry.PointCloud): The target point cloud.
        source_feature (open3d.cuda.pybind.pipelines.registration.Feature): Source point cloud feature.
        target_feature (open3d.cuda.pybind.pipelines.registration.Feature): Target point cloud feature.
        option (open3d.cuda.pybind.pipelines.registration.FastGlobalRegistrationOption, optional, default=FastGlobalRegistrationOption( division_factor=1.4, use_absolute_scale=false, decrease_mu=true, maximum_correspondence_distance=0.025, iteration_number=64, tuple_scale=0.95, maximum_tuple_count=1000, tuple_test=true, )): Registration option

    Returns:
        open3d.cuda.pybind.pipelines.registration.RegistrationResult
    """

def registration_generalized_icp(
    source: open3d.cuda.pybind.geometry.PointCloud,
    target: open3d.cuda.pybind.geometry.PointCloud,
    max_correspondence_distance: float,
    init: numpy.ndarray = ...,
    estimation_method: TransformationEstimationForGeneralizedICP = ...,
    criteria: ICPConvergenceCriteria = ...,
) -> RegistrationResult:
    """
    Function for Generalized ICP registration

    Args:
        source (open3d.cuda.pybind.geometry.PointCloud): The source point cloud.
        target (open3d.cuda.pybind.geometry.PointCloud): The target point cloud.
        max_correspondence_distance (float): Maximum correspondence points-pair distance.
        init (numpy.ndarray[numpy.float64[4, 4]], optional, default=array([[1., 0., 0., 0.], [0., 1., 0., 0.], [0., 0., 1., 0.], [0., 0., 0., 1.]])): Initial transformation estimation
        estimation_method (open3d.cuda.pybind.pipelines.registration.TransformationEstimationForGeneralizedICP, optional, default=TransformationEstimationForGeneralizedICP(epsilon=0.001)): Estimation method. One of (``TransformationEstimationPointToPoint``, ``TransformationEstimationPointToPlane``, ``TransformationEstimationForGeneralizedICP``, ``TransformationEstimationForColoredICP``)
        criteria (open3d.cuda.pybind.pipelines.registration.ICPConvergenceCriteria, optional, default=ICPConvergenceCriteria(relative_fitness=1.000000e-06, relative_rmse=1.000000e-06, max_iteration=30)): Convergence criteria

    Returns:
        open3d.cuda.pybind.pipelines.registration.RegistrationResult
    """

def registration_icp(
    source: open3d.cuda.pybind.geometry.PointCloud,
    target: open3d.cuda.pybind.geometry.PointCloud,
    max_correspondence_distance: float,
    init: numpy.ndarray = ...,
    estimation_method: TransformationEstimation = ...,
    criteria: ICPConvergenceCriteria = ...,
) -> RegistrationResult:
    """
    Function for ICP registration

    Args:
        source (open3d.cuda.pybind.geometry.PointCloud): The source point cloud.
        target (open3d.cuda.pybind.geometry.PointCloud): The target point cloud.
        max_correspondence_distance (float): Maximum correspondence points-pair distance.
        init (numpy.ndarray[numpy.float64[4, 4]], optional, default=array([[1., 0., 0., 0.], [0., 1., 0., 0.], [0., 0., 1., 0.], [0., 0., 0., 1.]])): Initial transformation estimation
        estimation_method (open3d.cuda.pybind.pipelines.registration.TransformationEstimation, optional, default=TransformationEstimationPointToPoint(with_scaling=False)): Estimation method. One of (``TransformationEstimationPointToPoint``, ``TransformationEstimationPointToPlane``, ``TransformationEstimationForGeneralizedICP``, ``TransformationEstimationForColoredICP``)
        criteria (open3d.cuda.pybind.pipelines.registration.ICPConvergenceCriteria, optional, default=ICPConvergenceCriteria(relative_fitness=1.000000e-06, relative_rmse=1.000000e-06, max_iteration=30)): Convergence criteria

    Returns:
        open3d.cuda.pybind.pipelines.registration.RegistrationResult
    """

def registration_ransac_based_on_correspondence(
    source: open3d.cuda.pybind.geometry.PointCloud,
    target: open3d.cuda.pybind.geometry.PointCloud,
    corres: open3d.cuda.pybind.utility.Vector2iVector,
    max_correspondence_distance: float,
    estimation_method: TransformationEstimation = ...,
    ransac_n: int = 3,
    checkers: list[CorrespondenceChecker] = [],
    criteria: RANSACConvergenceCriteria = ...,
) -> RegistrationResult:
    """
    Function for global RANSAC registration based on a set of correspondences

    Args:
        source (open3d.cuda.pybind.geometry.PointCloud): The source point cloud.
        target (open3d.cuda.pybind.geometry.PointCloud): The target point cloud.
        corres (open3d.cuda.pybind.utility.Vector2iVector): o3d.utility.Vector2iVector that stores indices of corresponding point or feature arrays.
        max_correspondence_distance (float): Maximum correspondence points-pair distance.
        estimation_method (open3d.cuda.pybind.pipelines.registration.TransformationEstimation, optional, default=TransformationEstimationPointToPoint(with_scaling=False)): Estimation method. One of (``TransformationEstimationPointToPoint``, ``TransformationEstimationPointToPlane``, ``TransformationEstimationForGeneralizedICP``, ``TransformationEstimationForColoredICP``)
        ransac_n (int, optional, default=3): Fit ransac with ``ransac_n`` correspondences
        checkers (list[open3d.cuda.pybind.pipelines.registration.CorrespondenceChecker], optional, default=[]): Vector of Checker class to check if two point clouds can be aligned. One of (``CorrespondenceCheckerBasedOnEdgeLength``, ``CorrespondenceCheckerBasedOnDistance``, ``CorrespondenceCheckerBasedOnNormal``)
        criteria (open3d.cuda.pybind.pipelines.registration.RANSACConvergenceCriteria, optional, default=RANSACConvergenceCriteria(max_iteration=100000, confidence=9.990000e-01)): Convergence criteria

    Returns:
        open3d.cuda.pybind.pipelines.registration.RegistrationResult
    """

def registration_ransac_based_on_feature_matching(
    source: open3d.cuda.pybind.geometry.PointCloud,
    target: open3d.cuda.pybind.geometry.PointCloud,
    source_feature: Feature,
    target_feature: Feature,
    mutual_filter: bool,
    max_correspondence_distance: float,
    estimation_method: TransformationEstimation = ...,
    ransac_n: int = 3,
    checkers: list[CorrespondenceChecker] = [],
    criteria: RANSACConvergenceCriteria = ...,
) -> RegistrationResult:
    """
    Function for global RANSAC registration based on feature matching

    Args:
        source (open3d.cuda.pybind.geometry.PointCloud): The source point cloud.
        target (open3d.cuda.pybind.geometry.PointCloud): The target point cloud.
        source_feature (open3d.cuda.pybind.pipelines.registration.Feature): Source point cloud feature.
        target_feature (open3d.cuda.pybind.pipelines.registration.Feature): Target point cloud feature.
        mutual_filter (bool): Enables mutual filter such that the correspondence of the source point's correspondence is itself.
        max_correspondence_distance (float): Maximum correspondence points-pair distance.
        estimation_method (open3d.cuda.pybind.pipelines.registration.TransformationEstimation, optional, default=TransformationEstimationPointToPoint(with_scaling=False)): Estimation method. One of (``TransformationEstimationPointToPoint``, ``TransformationEstimationPointToPlane``, ``TransformationEstimationForGeneralizedICP``, ``TransformationEstimationForColoredICP``)
        ransac_n (int, optional, default=3): Fit ransac with ``ransac_n`` correspondences
        checkers (list[open3d.cuda.pybind.pipelines.registration.CorrespondenceChecker], optional, default=[]): Vector of Checker class to check if two point clouds can be aligned. One of (``CorrespondenceCheckerBasedOnEdgeLength``, ``CorrespondenceCheckerBasedOnDistance``, ``CorrespondenceCheckerBasedOnNormal``)
        criteria (open3d.cuda.pybind.pipelines.registration.RANSACConvergenceCriteria, optional, default=RANSACConvergenceCriteria(max_iteration=100000, confidence=9.990000e-01)): Convergence criteria

    Returns:
        open3d.cuda.pybind.pipelines.registration.RegistrationResult
    """

m: typing.TypeVar
n: typing.TypeVar
