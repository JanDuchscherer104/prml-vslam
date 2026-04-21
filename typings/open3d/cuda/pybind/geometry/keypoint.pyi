"""
Keypoint Detectors.
"""
from __future__ import annotations
import open3d.cuda.pybind.geometry
__all__: list[str] = ['compute_iss_keypoints']
def compute_iss_keypoints(input: open3d.cuda.pybind.geometry.PointCloud, salient_radius: float = 0.0, non_max_radius: float = 0.0, gamma_21: float = 0.975, gamma_32: float = 0.975, min_neighbors: int = 5) -> open3d.cuda.pybind.geometry.PointCloud:
    """
    Function that computes the ISS keypoints from an input point cloud. This implements the keypoint detection modules proposed in Yu Zhong, 'Intrinsic Shape Signatures: A Shape Descriptor for 3D Object Recognition', 2009.
    
    Args:
        input (open3d.cuda.pybind.geometry.PointCloud): The Input point cloud.
        salient_radius (float, optional, default=0.0): The radius of the spherical neighborhood used to detect keypoints.
        non_max_radius (float, optional, default=0.0): The non maxima suppression radius
        gamma_21 (float, optional, default=0.975): The upper bound on the ratio between the second and the first eigenvalue returned by the EVD
        gamma_32 (float, optional, default=0.975): The upper bound on the ratio between the third and the second eigenvalue returned by the EVD
        min_neighbors (int, optional, default=5): Minimum number of neighbors that has to be found to consider a keypoint
    
    Returns:
        open3d.cuda.pybind.geometry.PointCloud
    """
