"""
Color map optimization pipeline
"""
from __future__ import annotations
import open3d.cuda.pybind.camera
import open3d.cuda.pybind.geometry
__all__: list[str] = ['NonRigidOptimizerOption', 'RigidOptimizerOption', 'run_non_rigid_optimizer', 'run_rigid_optimizer']
class NonRigidOptimizerOption:
    """
    Non Rigid optimizer option class.
    """
    def __init__(self, number_of_vertical_anchors: int = 16, non_rigid_anchor_point_weight: float = 0.316, maximum_iteration: int = 0, maximum_allowable_depth: float = 2.5, depth_threshold_for_visibility_check: float = 0.03, depth_threshold_for_discontinuity_check: float = 0.1, half_dilation_kernel_size_for_discontinuity_map: int = 3, image_boundary_margin: int = 10, invisible_vertex_color_knn: int = 3, debug_output_dir: str = '') -> None:
        """
        Args:
            number_of_vertical_anchors (int, optional, default=16): int: (Default ``16``) Number of vertical anchor points for image wrapping field. The number of horizontal anchor points is computed automatically based on the number of vertical anchor points. This option is only used when non-rigid optimization is enabled.
            non_rigid_anchor_point_weight (float, optional, default=0.316): float: (Default ``0.316``) Additional regularization terms added to non-rigid regularization. A higher value results gives more conservative updates. If the residual error does not stably decrease, it is mainly because images are being bended abruptly. In this case, consider making iteration more conservative by increasing the value. This option is only used when non-rigid optimization is enabled.
            maximum_iteration (int, optional, default=0): int: (Default ``300``) Number of iterations for optimization steps.
            maximum_allowable_depth (float, optional, default=2.5): float: (Default ``2.5``) Parameter to check the visibility of a point. Points with depth larger than ``maximum_allowable_depth`` in a RGB-D will be marked as invisible for the camera producing that RGB-D image. Select a proper value to include necessary points while ignoring unwanted points such as the background.
            depth_threshold_for_visibility_check (float, optional, default=0.03): float: (Default ``0.03``) Parameter for point visibility check. When the difference of a point's depth value in the RGB-D image and the point's depth value in the 3D mesh is greater than ``depth_threshold_for_visibility_check``, the point is marked as invisible to the camera producing the RGB-D image.
            depth_threshold_for_discontinuity_check (float, optional, default=0.1): float: (Default ``0.1``) Parameter to check the visibility of a point. It's often desirable to ignore points where there is an abrupt change in depth value. First the depth gradient image is computed, points are considered to be invisible if the depth gradient magnitude is larger than ``depth_threshold_for_discontinuity_check``.
            half_dilation_kernel_size_for_discontinuity_map (int, optional, default=3): int: (Default ``3``) Parameter to check the visibility of a point. Related to ``depth_threshold_for_discontinuity_check``, when boundary points are detected, dilation is performed to ignore points near the object boundary. ``half_dilation_kernel_size_for_discontinuity_map`` specifies the half-kernel size for the dilation applied on the visibility mask image.
            image_boundary_margin (int, optional, default=10): int: (Default ``10``) If a projected 3D point onto a 2D image lies in the image border within ``image_boundary_margin``, the 3D point is considered invisible from the camera producing the image. This parameter is not used for visibility check, but used when computing the final color assignment after color map optimization.
            invisible_vertex_color_knn (int, optional, default=3): int: (Default ``3``) If a vertex is invisible from all images, we assign the averaged color of the k nearest visible vertices to fill the invisible vertex. Set to ``0`` to disable this feature and all invisible vertices will be black.
            debug_output_dir (str, optional, default=''): If specified, the intermediate results will be stored in in the debug output dir. Existing files will be overwritten if the names are the same.
        """
class RigidOptimizerOption:
    """
    Rigid optimizer option class.
    """
    def __init__(self, maximum_iteration: int = 0, maximum_allowable_depth: float = 2.5, depth_threshold_for_visibility_check: float = 0.03, depth_threshold_for_discontinuity_check: float = 0.1, half_dilation_kernel_size_for_discontinuity_map: int = 3, image_boundary_margin: int = 10, invisible_vertex_color_knn: int = 3, debug_output_dir: str = '') -> None:
        """
        Args:
            maximum_iteration (int, optional, default=0): int: (Default ``300``) Number of iterations for optimization steps.
            maximum_allowable_depth (float, optional, default=2.5): float: (Default ``2.5``) Parameter to check the visibility of a point. Points with depth larger than ``maximum_allowable_depth`` in a RGB-D will be marked as invisible for the camera producing that RGB-D image. Select a proper value to include necessary points while ignoring unwanted points such as the background.
            depth_threshold_for_visibility_check (float, optional, default=0.03): float: (Default ``0.03``) Parameter for point visibility check. When the difference of a point's depth value in the RGB-D image and the point's depth value in the 3D mesh is greater than ``depth_threshold_for_visibility_check``, the point is marked as invisible to the camera producing the RGB-D image.
            depth_threshold_for_discontinuity_check (float, optional, default=0.1): float: (Default ``0.1``) Parameter to check the visibility of a point. It's often desirable to ignore points where there is an abrupt change in depth value. First the depth gradient image is computed, points are considered to be invisible if the depth gradient magnitude is larger than ``depth_threshold_for_discontinuity_check``.
            half_dilation_kernel_size_for_discontinuity_map (int, optional, default=3): int: (Default ``3``) Parameter to check the visibility of a point. Related to ``depth_threshold_for_discontinuity_check``, when boundary points are detected, dilation is performed to ignore points near the object boundary. ``half_dilation_kernel_size_for_discontinuity_map`` specifies the half-kernel size for the dilation applied on the visibility mask image.
            image_boundary_margin (int, optional, default=10): int: (Default ``10``) If a projected 3D point onto a 2D image lies in the image border within ``image_boundary_margin``, the 3D point is considered invisible from the camera producing the image. This parameter is not used for visibility check, but used when computing the final color assignment after color map optimization.
            invisible_vertex_color_knn (int, optional, default=3): int: (Default ``3``) If a vertex is invisible from all images, we assign the averaged color of the k nearest visible vertices to fill the invisible vertex. Set to ``0`` to disable this feature and all invisible vertices will be black.
            debug_output_dir (str, optional, default=''): If specified, the intermediate results will be stored in in the debug output dir. Existing files will be overwritten if the names are the same.
        """
def run_non_rigid_optimizer(arg0: open3d.cuda.pybind.geometry.TriangleMesh, arg1: list[open3d.cuda.pybind.geometry.RGBDImage], arg2: open3d.cuda.pybind.camera.PinholeCameraTrajectory, arg3: NonRigidOptimizerOption) -> tuple[open3d.cuda.pybind.geometry.TriangleMesh, open3d.cuda.pybind.camera.PinholeCameraTrajectory]:
    """
    Run non-rigid optimization.
    """
def run_rigid_optimizer(arg0: open3d.cuda.pybind.geometry.TriangleMesh, arg1: list[open3d.cuda.pybind.geometry.RGBDImage], arg2: open3d.cuda.pybind.camera.PinholeCameraTrajectory, arg3: RigidOptimizerOption) -> tuple[open3d.cuda.pybind.geometry.TriangleMesh, open3d.cuda.pybind.camera.PinholeCameraTrajectory]:
    """
    Run rigid optimization.
    """
