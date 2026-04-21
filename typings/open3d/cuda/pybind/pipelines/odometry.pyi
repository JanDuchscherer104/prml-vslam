"""
Odometry pipeline.
"""
from __future__ import annotations
import numpy
import open3d.cuda.pybind.camera
import open3d.cuda.pybind.geometry
import open3d.cuda.pybind.utility
import typing
__all__: list[str] = ['OdometryOption', 'RGBDOdometryJacobian', 'RGBDOdometryJacobianFromColorTerm', 'RGBDOdometryJacobianFromHybridTerm', 'compute_correspondence', 'compute_rgbd_odometry']
class OdometryOption:
    """
    Class that defines Odometry options.
    """
    def __init__(self, iteration_number_per_pyramid_level: open3d.cuda.pybind.utility.IntVector = ..., depth_diff_max: float = 0.03, depth_min: float = 0.0, depth_max: float = 4.0) -> None:
        ...
    def __repr__(self) -> str:
        ...
    @property
    def depth_diff_max(self) -> float:
        """
        Maximum depth difference to be considered as correspondence. In depth image domain, if two aligned pixels have a depth difference less than specified value, they are considered as a correspondence. Larger value induce more aggressive search, but it is prone to unstable result.
        """
    @depth_diff_max.setter
    def depth_diff_max(self, arg0: float) -> None:
        ...
    @property
    def depth_max(self) -> float:
        """
        Pixels that has larger than specified depth values are ignored.
        """
    @depth_max.setter
    def depth_max(self, arg0: float) -> None:
        ...
    @property
    def depth_min(self) -> float:
        """
        Pixels that has smaller than specified depth values are ignored.
        """
    @depth_min.setter
    def depth_min(self, arg0: float) -> None:
        ...
    @property
    def iteration_number_per_pyramid_level(self) -> open3d.cuda.pybind.utility.IntVector:
        """
        List(int): Iteration number per image pyramid level, typically larger image in the pyramid have lower iteration number to reduce computation time.
        """
    @iteration_number_per_pyramid_level.setter
    def iteration_number_per_pyramid_level(self, arg0: open3d.cuda.pybind.utility.IntVector) -> None:
        ...
class RGBDOdometryJacobian:
    """
    Base class that computes Jacobian from two RGB-D images.
    """
    @staticmethod
    def compute_jacobian_and_residual(*args, **kwargs) -> None:
        ...
class RGBDOdometryJacobianFromColorTerm(RGBDOdometryJacobian):
    """
    Class to Compute Jacobian using color term.
    
    Energy: :math:`(I_p-I_q)^2.`
    
    Reference:
    
    F. Steinbrucker, J. Sturm, and D. Cremers.
    
    Real-time visual odometry from dense RGB-D images.
    
    In ICCV Workshops, 2011.
    """
    def __copy__(self) -> RGBDOdometryJacobianFromColorTerm:
        ...
    def __deepcopy__(self, arg0: dict) -> RGBDOdometryJacobianFromColorTerm:
        ...
    @typing.overload
    def __init__(self) -> None:
        """
        Default constructor
        """
    @typing.overload
    def __init__(self, arg0: RGBDOdometryJacobianFromColorTerm) -> None:
        """
        Copy constructor
        """
    def __repr__(self) -> str:
        ...
class RGBDOdometryJacobianFromHybridTerm(RGBDOdometryJacobian):
    """
    Class to compute Jacobian using hybrid term
    
    Energy: :math:`(I_p-I_q)^2 + \\lambda(D_p-D_q')^2`
    
    Reference:
    
    J. Park, Q.-Y. Zhou, and V. Koltun
    
    Anonymous submission.
    """
    def __copy__(self) -> RGBDOdometryJacobianFromHybridTerm:
        ...
    def __deepcopy__(self, arg0: dict) -> RGBDOdometryJacobianFromHybridTerm:
        ...
    @typing.overload
    def __init__(self) -> None:
        """
        Default constructor
        """
    @typing.overload
    def __init__(self, arg0: RGBDOdometryJacobianFromHybridTerm) -> None:
        """
        Copy constructor
        """
    def __repr__(self) -> str:
        ...
def compute_correspondence(intrinsic_matrix: numpy.ndarray, extrinsic: numpy.ndarray, depth_s: open3d.cuda.pybind.geometry.Image, depth_t: open3d.cuda.pybind.geometry.Image, option: OdometryOption = ...) -> open3d.cuda.pybind.utility.Vector4iVector:
    """
    Function to estimate point to point correspondences from two depth images. A vector of u_s, v_s, u_t, v_t which maps the 2d coordinates of source to target.
    
    Args:
        intrinsic_matrix (numpy.ndarray[numpy.float64[3, 3]]): Camera intrinsic parameters.
        extrinsic (numpy.ndarray[numpy.float64[4, 4]]): Estimation of transform from source to target.
        depth_s (open3d.cuda.pybind.geometry.Image): Source depth image.
        depth_t (open3d.cuda.pybind.geometry.Image): Target depth image.
        option (open3d.cuda.pybind.pipelines.odometry.OdometryOption, optional, default=OdometryOption( iteration_number_per_pyramid_level=[ 20, 10, 5, ] , depth_diff_max=0.03, depth_min=0, depth_max=4, )): Odometry hyper parameters.
    
    Returns:
        open3d.cuda.pybind.utility.Vector4iVector
    """
def compute_rgbd_odometry(rgbd_source: open3d.cuda.pybind.geometry.RGBDImage, rgbd_target: open3d.cuda.pybind.geometry.RGBDImage, pinhole_camera_intrinsic: open3d.cuda.pybind.camera.PinholeCameraIntrinsic = ..., odo_init: numpy.ndarray = ..., jacobian: RGBDOdometryJacobian = ..., option: OdometryOption = ...) -> tuple[bool, numpy.ndarray, numpy.ndarray]:
    """
    Function to estimate 6D rigid motion from two RGBD image pairs. Output: (is_success, 4x4 motion matrix, 6x6 information matrix).
    
    Args:
        rgbd_source (open3d.cuda.pybind.geometry.RGBDImage): Source RGBD image.
        rgbd_target (open3d.cuda.pybind.geometry.RGBDImage): Target RGBD image.
        pinhole_camera_intrinsic (open3d.cuda.pybind.camera.PinholeCameraIntrinsic, optional, default=PinholeCameraIntrinsic(width=-1, height=-1, )): Camera intrinsic parameters
        odo_init (numpy.ndarray[numpy.float64[4, 4]], optional, default=array([[1., 0., 0., 0.], [0., 1., 0., 0.], [0., 0., 1., 0.], [0., 0., 0., 1.]])): Initial 4x4 motion matrix estimation.
        jacobian (open3d.cuda.pybind.pipelines.odometry.RGBDOdometryJacobian, optional, default=RGBDOdometryJacobianFromHybridTerm): The odometry Jacobian method to use. Can be ``RGBDOdometryJacobianFromHybridTerm()`` or ``RGBDOdometryJacobianFromColorTerm().``
        option (open3d.cuda.pybind.pipelines.odometry.OdometryOption, optional, default=OdometryOption( iteration_number_per_pyramid_level=[ 20, 10, 5, ] , depth_diff_max=0.03, depth_min=0, depth_max=4, )): Odometry hyper parameters.
    
    Returns:
        tuple[bool, numpy.ndarray[numpy.float64[4, 4]], numpy.ndarray[numpy.float64[6, 6]]]
    """
