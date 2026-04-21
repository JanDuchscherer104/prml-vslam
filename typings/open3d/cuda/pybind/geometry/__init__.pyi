from __future__ import annotations
import numpy
import open3d.cuda.pybind.camera
import open3d.cuda.pybind.pipelines.registration
import open3d.cuda.pybind.utility
import typing
import typing_extensions
from . import keypoint
__all__: list[str] = ['All', 'Average', 'AxisAlignedBoundingBox', 'Color', 'DeformAsRigidAsPossibleEnergy', 'FilterScope', 'Gaussian3', 'Gaussian5', 'Gaussian7', 'Geometry', 'Geometry2D', 'Geometry3D', 'HalfEdge', 'HalfEdgeTriangleMesh', 'Image', 'ImageFilterType', 'KDTreeFlann', 'KDTreeSearchParam', 'KDTreeSearchParamHybrid', 'KDTreeSearchParamKNN', 'KDTreeSearchParamRadius', 'LineSet', 'MeshBase', 'Normal', 'Octree', 'OctreeColorLeafNode', 'OctreeInternalNode', 'OctreeInternalPointNode', 'OctreeLeafNode', 'OctreeNode', 'OctreeNodeInfo', 'OctreePointColorLeafNode', 'OrientedBoundingBox', 'PointCloud', 'Quadric', 'RGBDImage', 'SimplificationContraction', 'Smoothed', 'Sobel3dx', 'Sobel3dy', 'Spokes', 'TetraMesh', 'TriangleMesh', 'Vertex', 'Voxel', 'VoxelGrid', 'get_rotation_matrix_from_axis_angle', 'get_rotation_matrix_from_quaternion', 'get_rotation_matrix_from_xyz', 'get_rotation_matrix_from_xzy', 'get_rotation_matrix_from_yxz', 'get_rotation_matrix_from_yzx', 'get_rotation_matrix_from_zxy', 'get_rotation_matrix_from_zyx', 'keypoint', 'm', 'n']
class AxisAlignedBoundingBox(Geometry3D):
    """
    Class that defines an axis_aligned box that can be computed from 3D geometries, The axis aligned bounding box uses the coordinate axes for bounding box generation.
    """
    @staticmethod
    def create_from_points(points: open3d.cuda.pybind.utility.Vector3dVector) -> AxisAlignedBoundingBox:
        """
        Creates the bounding box that encloses the set of points.
        
        Args:
            points (open3d.cuda.pybind.utility.Vector3dVector): A list of points.
        
        Returns:
            open3d.cuda.pybind.geometry.AxisAlignedBoundingBox
        """
    def __copy__(self) -> AxisAlignedBoundingBox:
        ...
    def __deepcopy__(self, arg0: dict) -> AxisAlignedBoundingBox:
        ...
    def __iadd__(self, arg0: AxisAlignedBoundingBox) -> AxisAlignedBoundingBox:
        ...
    @typing.overload
    def __init__(self) -> None:
        """
        Default constructor
        """
    @typing.overload
    def __init__(self, arg0: AxisAlignedBoundingBox) -> None:
        """
        Copy constructor
        """
    @typing.overload
    def __init__(self, min_bound: numpy.ndarray, max_bound: numpy.ndarray) -> None:
        """
        Create an AxisAlignedBoundingBox from min bounds and max bounds in x, y and z
        """
    def __repr__(self) -> str:
        ...
    def get_box_points(self) -> open3d.cuda.pybind.utility.Vector3dVector:
        """
        Returns the eight points that define the bounding box.
        
        Returns:
            open3d.cuda.pybind.utility.Vector3dVector
        """
    def get_extent(self) -> numpy.ndarray:
        """
        Get the extent/length of the bounding box in x, y, and z dimension.
        
        Returns:
            numpy.ndarray[numpy.float64[3, 1]]
        """
    def get_half_extent(self) -> numpy.ndarray:
        """
        Returns the half extent of the bounding box.
        
        Returns:
            numpy.ndarray[numpy.float64[3, 1]]
        """
    def get_max_extent(self) -> float:
        """
        Returns the maximum extent, i.e. the maximum of X, Y and Z axis
        
        Returns:
            float
        """
    def get_point_indices_within_bounding_box(self, points: open3d.cuda.pybind.utility.Vector3dVector) -> list[int]:
        """
        Return indices to points that are within the bounding box.
        
        Args:
            points (open3d.cuda.pybind.utility.Vector3dVector): A list of points.
        
        Returns:
            list[int]
        """
    def get_print_info(self) -> str:
        """
        Returns the 3D dimensions of the bounding box in string format.
        
        Returns:
            str
        """
    def volume(self) -> float:
        """
        Returns the volume of the bounding box.
        
        Returns:
            float
        """
    @property
    def color(self) -> numpy.ndarray:
        """
        ``float64`` array of shape ``(3, )``
        """
    @color.setter
    def color(self, arg0: numpy.ndarray) -> None:
        ...
    @property
    def max_bound(self) -> numpy.ndarray:
        """
        ``float64`` array of shape ``(3, )``
        """
    @max_bound.setter
    def max_bound(self, arg0: numpy.ndarray) -> None:
        ...
    @property
    def min_bound(self) -> numpy.ndarray:
        """
        ``float64`` array of shape ``(3, )``
        """
    @min_bound.setter
    def min_bound(self, arg0: numpy.ndarray) -> None:
        ...
class DeformAsRigidAsPossibleEnergy:
    """
    Members:
    
      Spokes : is the original energy as formulated in orkine and Alexa, "As-Rigid-As-Possible Surface Modeling", 2007.
    
      Smoothed : adds a rotation smoothing term to the rotations.
    """
    Smoothed: typing.ClassVar[DeformAsRigidAsPossibleEnergy]
    Spokes: typing.ClassVar[DeformAsRigidAsPossibleEnergy]
    __members__: typing.ClassVar[dict[str, DeformAsRigidAsPossibleEnergy]]
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
class FilterScope:
    """
    Members:
    
      All : All properties (color, normal, vertex position) are filtered.
    
      Color : Only the color values are filtered.
    
      Normal : Only the normal values are filtered.
    
      Vertex : Only the vertex positions are filtered.
    """
    All: typing.ClassVar[FilterScope]
    Color: typing.ClassVar[FilterScope]
    Normal: typing.ClassVar[FilterScope]
    Vertex: typing.ClassVar[FilterScope]
    __members__: typing.ClassVar[dict[str, FilterScope]]
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
class Geometry:
    """
    The base geometry class.
    """
    class Type:
        """
        Enum class for Geometry types.
        """
        HalfEdgeTriangleMesh: typing.ClassVar[Geometry.Type]
        Image: typing.ClassVar[Geometry.Type]
        LineSet: typing.ClassVar[Geometry.Type]
        PointCloud: typing.ClassVar[Geometry.Type]
        RGBDImage: typing.ClassVar[Geometry.Type]
        TetraMesh: typing.ClassVar[Geometry.Type]
        TriangleMesh: typing.ClassVar[Geometry.Type]
        Unspecified: typing.ClassVar[Geometry.Type]
        VoxelGrid: typing.ClassVar[Geometry.Type]
        __members__: typing.ClassVar[dict[str, Geometry.Type]]
        def __eq__(self, other: typing.Any) -> bool:
            ...
        def __ge__(self, other: typing.Any) -> bool:
            ...
        def __getstate__(self) -> int:
            ...
        def __gt__(self, other: typing.Any) -> bool:
            ...
        def __hash__(self) -> int:
            ...
        def __index__(self) -> int:
            ...
        def __init__(self, value: int) -> None:
            ...
        def __int__(self) -> int:
            ...
        def __le__(self, other: typing.Any) -> bool:
            ...
        def __lt__(self, other: typing.Any) -> bool:
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
    HalfEdgeTriangleMesh: typing.ClassVar[Geometry.Type]
    Image: typing.ClassVar[Geometry.Type]
    LineSet: typing.ClassVar[Geometry.Type]
    PointCloud: typing.ClassVar[Geometry.Type]
    RGBDImage: typing.ClassVar[Geometry.Type]
    TetraMesh: typing.ClassVar[Geometry.Type]
    TriangleMesh: typing.ClassVar[Geometry.Type]
    Unspecified: typing.ClassVar[Geometry.Type]
    VoxelGrid: typing.ClassVar[Geometry.Type]
    def clear(self) -> Geometry:
        """
        Clear all elements in the geometry.
        
        Returns:
            open3d.cuda.pybind.geometry.Geometry
        """
    def dimension(self) -> int:
        """
        Returns whether the geometry is 2D or 3D.
        
        Returns:
            int
        """
    def get_geometry_type(self) -> Geometry.Type:
        """
        Returns one of registered geometry types.
        
        Returns:
            open3d.cuda.pybind.geometry.Geometry.Type
        """
    def is_empty(self) -> bool:
        """
        Returns ``True`` iff the geometry is empty.
        
        Returns:
            bool
        """
class Geometry2D(Geometry):
    """
    The base geometry class for 2D geometries.
    """
    def get_max_bound(self) -> numpy.ndarray:
        """
        Returns max bounds for geometry coordinates.
        
        Returns:
            numpy.ndarray[numpy.float64[2, 1]]
        """
    def get_min_bound(self) -> numpy.ndarray:
        """
        Returns min bounds for geometry coordinates.
        
        Returns:
            numpy.ndarray[numpy.float64[2, 1]]
        """
class Geometry3D(Geometry):
    """
    The base geometry class for 3D geometries.
    """
    @staticmethod
    def get_rotation_matrix_from_axis_angle(rotation: numpy.ndarray) -> numpy.ndarray:
        ...
    @staticmethod
    def get_rotation_matrix_from_quaternion(rotation: numpy.ndarray) -> numpy.ndarray:
        ...
    @staticmethod
    def get_rotation_matrix_from_xyz(rotation: numpy.ndarray) -> numpy.ndarray:
        ...
    @staticmethod
    def get_rotation_matrix_from_xzy(rotation: numpy.ndarray) -> numpy.ndarray:
        ...
    @staticmethod
    def get_rotation_matrix_from_yxz(rotation: numpy.ndarray) -> numpy.ndarray:
        ...
    @staticmethod
    def get_rotation_matrix_from_yzx(rotation: numpy.ndarray) -> numpy.ndarray:
        ...
    @staticmethod
    def get_rotation_matrix_from_zxy(rotation: numpy.ndarray) -> numpy.ndarray:
        ...
    @staticmethod
    def get_rotation_matrix_from_zyx(rotation: numpy.ndarray) -> numpy.ndarray:
        ...
    def get_axis_aligned_bounding_box(self) -> AxisAlignedBoundingBox:
        """
        Returns an axis-aligned bounding box of the geometry.
        
        Returns:
            open3d.cuda.pybind.geometry.AxisAlignedBoundingBox
        """
    def get_center(self) -> numpy.ndarray:
        """
        Returns the center of the geometry coordinates.
        
        Returns:
            numpy.ndarray[numpy.float64[3, 1]]
        """
    def get_max_bound(self) -> numpy.ndarray:
        """
        Returns max bounds for geometry coordinates.
        
        Returns:
            numpy.ndarray[numpy.float64[3, 1]]
        """
    def get_min_bound(self) -> numpy.ndarray:
        """
        Returns min bounds for geometry coordinates.
        
        Returns:
            numpy.ndarray[numpy.float64[3, 1]]
        """
    def get_minimal_oriented_bounding_box(self, robust: bool = False) -> OrientedBoundingBox:
        """
        Returns the minimal oriented bounding box for the geometry.
        
        Creates the oriented bounding box with the smallest volume.
        The algorithm makes use of the fact that at least one edge of
        the convex hull must be collinear with an edge of the minimum
        bounding box: for each triangle in the convex hull, calculate
        the minimal axis aligned box in the frame of that triangle.
        at the end, return the box with the smallest volume
        
        Args:
             robust (bool): If set to true uses a more robust method which works in
                  degenerate cases but introduces noise to the points coordinates.
        
        Returns:
             open3d.geometry.OrientedBoundingBox: The oriented bounding box. The
             bounding box is oriented such that its volume is minimized.
        """
    def get_oriented_bounding_box(self, robust: bool = False) -> OrientedBoundingBox:
        """
        Returns the oriented bounding box for the geometry.
        
        Computes the oriented bounding box based on the PCA of the convex hull.
        The returned bounding box is an approximation to the minimal bounding box.
        
        Args:
             robust (bool): If set to true uses a more robust method which works in
                  degenerate cases but introduces noise to the points coordinates.
        
        Returns:
             open3d.geometry.OrientedBoundingBox: The oriented bounding box. The
             bounding box is oriented such that the axes are ordered with respect to
             the principal components.
        """
    @typing.overload
    def rotate(self, R: numpy.ndarray) -> Geometry3D:
        """
            Apply rotation to the geometry coordinates and normals.
        
        Args:
            R (numpy.ndarray[numpy.float64[3, 3]]): The rotation matrix
        
        Returns:
            open3d.cuda.pybind.geometry.Geometry3D
        """
    @typing.overload
    def rotate(self, R: numpy.ndarray, center: numpy.ndarray) -> Geometry3D:
        """
            Apply rotation to the geometry coordinates and normals.
        
        Args:
            R (numpy.ndarray[numpy.float64[3, 3]]): The rotation matrix
            center (numpy.ndarray[numpy.float64[3, 1]]): Rotation center used for transformation.
        
        Returns:
            open3d.cuda.pybind.geometry.Geometry3D
        """
    @typing.overload
    def scale(self, scale: float, center: numpy.ndarray) -> Geometry3D:
        """
            Apply scaling to the geometry coordinates.
        
        Args:
            scale (float): The scale parameter that is multiplied to the points/vertices of the geometry.
            center (numpy.ndarray[numpy.float64[3, 1]]): Scale center used for transformation.
        
        Returns:
            open3d.cuda.pybind.geometry.Geometry3D
        """
    @typing.overload
    def scale(self, scale: float, center: numpy.ndarray) -> Geometry3D:
        """
            Apply scaling to the geometry coordinates.
        
        Args:
            scale (float): The scale parameter that is multiplied to the points/vertices of the geometry.
            center (numpy.ndarray[numpy.float64[3, 1]]): Scale center used for transformation.
        
        Returns:
            open3d.cuda.pybind.geometry.Geometry3D
        """
    def transform(self, arg0: numpy.ndarray) -> Geometry3D:
        """
        Apply transformation (4x4 matrix) to the geometry coordinates.
        
        Args:
            arg0 (numpy.ndarray[numpy.float64[4, 4]])
        
        Returns:
            open3d.cuda.pybind.geometry.Geometry3D
        """
    def translate(self, translation: numpy.ndarray, relative: bool = True) -> Geometry3D:
        """
        Apply translation to the geometry coordinates.
        
        Args:
            translation (numpy.ndarray[numpy.float64[3, 1]]): A 3D vector to transform the geometry
            relative (bool, optional, default=True): If true, the translation vector is directly added to the geometry coordinates. Otherwise, the center is moved to the translation vector.
        
        Returns:
            open3d.cuda.pybind.geometry.Geometry3D
        """
class HalfEdge:
    """
    HalfEdge class contains vertex, triangle info about a half edge, as well as relations of next and twin half edge.
    """
    def __copy__(self) -> HalfEdge:
        ...
    def __deepcopy__(self, arg0: dict) -> HalfEdge:
        ...
    @typing.overload
    def __init__(self) -> None:
        """
        Default constructor
        """
    @typing.overload
    def __init__(self, arg0: HalfEdge) -> None:
        """
        Copy constructor
        """
    def __repr__(self) -> str:
        ...
    def is_boundary(self) -> bool:
        """
        Returns ``True`` iff the half edge is the boundary (has not twin, i.e. twin index == -1).
        """
    @property
    def next(self) -> int:
        """
        int: Index of the next HalfEdge in the same triangle.
        """
    @next.setter
    def next(self, arg0: int) -> None:
        ...
    @property
    def triangle_index(self) -> int:
        """
        int: Index of the triangle containing this half edge
        """
    @triangle_index.setter
    def triangle_index(self, arg0: int) -> None:
        ...
    @property
    def twin(self) -> int:
        """
        int: Index of the twin HalfEdge
        """
    @twin.setter
    def twin(self, arg0: int) -> None:
        ...
    @property
    def vertex_indices(self) -> numpy.ndarray:
        """
        List(int) of length 2: Index of the ordered vertices forming this half edge
        """
    @vertex_indices.setter
    def vertex_indices(self, arg0: numpy.ndarray) -> None:
        ...
class HalfEdgeTriangleMesh(MeshBase):
    """
    HalfEdgeTriangleMesh inherits TriangleMesh class with the addition of HalfEdge data structure for each half edge in the mesh as well as related functions.
    """
    @staticmethod
    def boundary_vertices_from_vertex(*args, **kwargs) -> open3d.cuda.pybind.utility.IntVector:
        """
        Returns:
            open3d.cuda.pybind.utility.IntVector
        """
    @staticmethod
    def create_from_triangle_mesh(mesh: TriangleMesh) -> HalfEdgeTriangleMesh:
        """
        Convert HalfEdgeTriangleMesh from TriangleMesh. Throws exception if the input mesh is not manifolds
        
        Args:
            mesh (open3d.cuda.pybind.geometry.TriangleMesh): The input TriangleMesh
        
        Returns:
            open3d.cuda.pybind.geometry.HalfEdgeTriangleMesh
        """
    def __copy__(self) -> HalfEdgeTriangleMesh:
        ...
    def __deepcopy__(self, arg0: dict) -> HalfEdgeTriangleMesh:
        ...
    @typing.overload
    def __init__(self) -> None:
        """
        Default constructor
        """
    @typing.overload
    def __init__(self, arg0: HalfEdgeTriangleMesh) -> None:
        """
        Copy constructor
        """
    def __repr__(self) -> str:
        ...
    def boundary_half_edges_from_vertex(self, vertex_index: int) -> open3d.cuda.pybind.utility.IntVector:
        """
        Query manifold boundary half edges from a starting vertex. If query vertex is not on boundary, empty vector will be returned.
        
        Args:
            vertex_index (int)
        
        Returns:
            open3d.cuda.pybind.utility.IntVector
        """
    def get_boundaries(self) -> list[open3d.cuda.pybind.utility.IntVector]:
        """
        Returns a vector of boundaries. A boundary is a vector of vertices.
        
        Returns:
            list[open3d.cuda.pybind.utility.IntVector]
        """
    def has_half_edges(self) -> bool:
        """
        Returns ``True`` if half-edges have already been computed.
        
        Returns:
            bool
        """
    @property
    def half_edges(self) -> list[HalfEdge]:
        """
        List of HalfEdge in the mesh
        """
    @half_edges.setter
    def half_edges(self, arg0: list[HalfEdge]) -> None:
        ...
    @property
    def ordered_half_edge_from_vertex(self) -> list[open3d.cuda.pybind.utility.IntVector]:
        """
        Counter-clockwise ordered half-edges started from each vertex
        """
    @ordered_half_edge_from_vertex.setter
    def ordered_half_edge_from_vertex(self, arg0: list[open3d.cuda.pybind.utility.IntVector]) -> None:
        ...
    @property
    def triangle_normals(self) -> open3d.cuda.pybind.utility.Vector3dVector:
        """
        ``float64`` array of shape ``(num_triangles, 3)``, use ``numpy.asarray()`` to access data: Triangle normals.
        """
    @triangle_normals.setter
    def triangle_normals(self, arg0: open3d.cuda.pybind.utility.Vector3dVector) -> None:
        ...
    @property
    def triangles(self) -> open3d.cuda.pybind.utility.Vector3iVector:
        """
        ``int`` array of shape ``(num_triangles, 3)``, use ``numpy.asarray()`` to access data: List of triangles denoted by the index of points forming the triangle.
        """
    @triangles.setter
    def triangles(self, arg0: open3d.cuda.pybind.utility.Vector3iVector) -> None:
        ...
class Image(Geometry2D):
    """
    The image class stores image with customizable width, height, num of channels and bytes per channel.
    """
    @staticmethod
    def filter_pyramid(image_pyramid: list[Image], filter_type: ImageFilterType) -> list[Image]:
        """
        Function to filter ImagePyramid
        
        Args:
            image_pyramid (list[open3d.cuda.pybind.geometry.Image]): The ImagePyramid object
            filter_type (open3d.cuda.pybind.geometry.ImageFilterType): The filter type to be applied.
        
        Returns:
            list[open3d.cuda.pybind.geometry.Image]
        """
    def __copy__(self) -> Image:
        ...
    def __deepcopy__(self, arg0: dict) -> Image:
        ...
    @typing.overload
    def __init__(self) -> None:
        """
        Default constructor
        """
    @typing.overload
    def __init__(self, arg0: Image) -> None:
        """
        Copy constructor
        """
    @typing.overload
    def __init__(self, arg0: typing_extensions.Buffer) -> None:
        ...
    def __repr__(self) -> str:
        ...
    def create_pyramid(self, num_of_levels: int, with_gaussian_filter: bool) -> list[Image]:
        """
        Function to create ImagePyramid
        
        Args:
            num_of_levels (int)
            with_gaussian_filter (bool): When ``True``, image in the pyramid will first be filtered by a 3x3 Gaussian kernel before downsampling.
        
        Returns:
            list[open3d.cuda.pybind.geometry.Image]
        """
    def filter(self, filter_type: ImageFilterType) -> Image:
        """
        Function to filter Image
        
        Args:
            filter_type (open3d.cuda.pybind.geometry.ImageFilterType): The filter type to be applied.
        
        Returns:
            open3d.cuda.pybind.geometry.Image
        """
    def flip_horizontal(self) -> Image:
        """
        Function to flip image horizontally (from left to right)
        """
    def flip_vertical(self) -> Image:
        """
        Function to flip image vertically (upside down)
        """
class ImageFilterType:
    """
    Enum class for Image filter types.
    """
    Gaussian3: typing.ClassVar[ImageFilterType]
    Gaussian5: typing.ClassVar[ImageFilterType]
    Gaussian7: typing.ClassVar[ImageFilterType]
    Sobel3dx: typing.ClassVar[ImageFilterType]
    Sobel3dy: typing.ClassVar[ImageFilterType]
    __members__: typing.ClassVar[dict[str, ImageFilterType]]
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
class KDTreeFlann:
    """
    KDTree with FLANN for nearest neighbor search.
    """
    @typing.overload
    def __init__(self) -> None:
        ...
    @typing.overload
    def __init__(self, data: numpy.ndarray) -> None:
        ...
    @typing.overload
    def __init__(self, geometry: Geometry) -> None:
        ...
    @typing.overload
    def __init__(self, feature: open3d.cuda.pybind.pipelines.registration.Feature) -> None:
        ...
    def search_hybrid_vector_3d(self, query: numpy.ndarray, radius: float, max_nn: int) -> tuple[int, open3d.cuda.pybind.utility.IntVector, open3d.cuda.pybind.utility.DoubleVector]:
        """
        Args:
            query (numpy.ndarray[numpy.float64[3, 1]]): The input query point.
            radius (float): Search radius.
            max_nn (int): At maximum, ``max_nn`` neighbors will be searched.
        
        Returns:
            tuple[int, open3d.cuda.pybind.utility.IntVector, open3d.cuda.pybind.utility.DoubleVector]
        """
    def search_hybrid_vector_xd(self, query: numpy.ndarray, radius: float, max_nn: int) -> tuple[int, open3d.cuda.pybind.utility.IntVector, open3d.cuda.pybind.utility.DoubleVector]:
        """
        Args:
            query (numpy.ndarray[numpy.float64[m, 1]]): The input query point.
            radius (float): Search radius.
            max_nn (int): At maximum, ``max_nn`` neighbors will be searched.
        
        Returns:
            tuple[int, open3d.cuda.pybind.utility.IntVector, open3d.cuda.pybind.utility.DoubleVector]
        """
    def search_knn_vector_3d(self, query: numpy.ndarray, knn: int) -> tuple[int, open3d.cuda.pybind.utility.IntVector, open3d.cuda.pybind.utility.DoubleVector]:
        """
        Args:
            query (numpy.ndarray[numpy.float64[3, 1]]): The input query point.
            knn (int): ``knn`` neighbors will be searched.
        
        Returns:
            tuple[int, open3d.cuda.pybind.utility.IntVector, open3d.cuda.pybind.utility.DoubleVector]
        """
    def search_knn_vector_xd(self, query: numpy.ndarray, knn: int) -> tuple[int, open3d.cuda.pybind.utility.IntVector, open3d.cuda.pybind.utility.DoubleVector]:
        """
        Args:
            query (numpy.ndarray[numpy.float64[m, 1]]): The input query point.
            knn (int): ``knn`` neighbors will be searched.
        
        Returns:
            tuple[int, open3d.cuda.pybind.utility.IntVector, open3d.cuda.pybind.utility.DoubleVector]
        """
    def search_radius_vector_3d(self, query: numpy.ndarray, radius: float) -> tuple[int, open3d.cuda.pybind.utility.IntVector, open3d.cuda.pybind.utility.DoubleVector]:
        """
        Args:
            query (numpy.ndarray[numpy.float64[3, 1]]): The input query point.
            radius (float): Search radius.
        
        Returns:
            tuple[int, open3d.cuda.pybind.utility.IntVector, open3d.cuda.pybind.utility.DoubleVector]
        """
    def search_radius_vector_xd(self, query: numpy.ndarray, radius: float) -> tuple[int, open3d.cuda.pybind.utility.IntVector, open3d.cuda.pybind.utility.DoubleVector]:
        """
        Args:
            query (numpy.ndarray[numpy.float64[m, 1]]): The input query point.
            radius (float): Search radius.
        
        Returns:
            tuple[int, open3d.cuda.pybind.utility.IntVector, open3d.cuda.pybind.utility.DoubleVector]
        """
    def search_vector_3d(self, query: numpy.ndarray, search_param: KDTreeSearchParam) -> tuple[int, open3d.cuda.pybind.utility.IntVector, open3d.cuda.pybind.utility.DoubleVector]:
        """
        Args:
            query (numpy.ndarray[numpy.float64[3, 1]]): The input query point.
            search_param (open3d.cuda.pybind.geometry.KDTreeSearchParam)
        
        Returns:
            tuple[int, open3d.cuda.pybind.utility.IntVector, open3d.cuda.pybind.utility.DoubleVector]
        """
    def search_vector_xd(self, query: numpy.ndarray, search_param: KDTreeSearchParam) -> tuple[int, open3d.cuda.pybind.utility.IntVector, open3d.cuda.pybind.utility.DoubleVector]:
        """
        Args:
            query (numpy.ndarray[numpy.float64[m, 1]]): The input query point.
            search_param (open3d.cuda.pybind.geometry.KDTreeSearchParam)
        
        Returns:
            tuple[int, open3d.cuda.pybind.utility.IntVector, open3d.cuda.pybind.utility.DoubleVector]
        """
    def set_feature(self, feature: open3d.cuda.pybind.pipelines.registration.Feature) -> bool:
        """
        Sets the data for the KDTree from the feature data.
        
        Args:
            feature (open3d.cuda.pybind.pipelines.registration.Feature): Feature data.
        
        Returns:
            bool
        """
    def set_geometry(self, geometry: Geometry) -> bool:
        """
        Sets the data for the KDTree from geometry.
        
        Args:
            geometry (open3d.cuda.pybind.geometry.Geometry)
        
        Returns:
            bool
        """
    def set_matrix_data(self, data: numpy.ndarray) -> bool:
        """
        Sets the data for the KDTree from a matrix.
        
        Args:
            data (numpy.ndarray[numpy.float64[m, n]]): Matrix data.
        
        Returns:
            bool
        """
class KDTreeSearchParam:
    """
    Base class for KDTree search parameters.
    """
    class Type:
        """
        Enum class for Geometry types.
        """
        HybridSearch: typing.ClassVar[KDTreeSearchParam.Type]
        KNNSearch: typing.ClassVar[KDTreeSearchParam.Type]
        RadiusSearch: typing.ClassVar[KDTreeSearchParam.Type]
        __members__: typing.ClassVar[dict[str, KDTreeSearchParam.Type]]
        def __eq__(self, other: typing.Any) -> bool:
            ...
        def __ge__(self, other: typing.Any) -> bool:
            ...
        def __getstate__(self) -> int:
            ...
        def __gt__(self, other: typing.Any) -> bool:
            ...
        def __hash__(self) -> int:
            ...
        def __index__(self) -> int:
            ...
        def __init__(self, value: int) -> None:
            ...
        def __int__(self) -> int:
            ...
        def __le__(self, other: typing.Any) -> bool:
            ...
        def __lt__(self, other: typing.Any) -> bool:
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
    HybridSearch: typing.ClassVar[KDTreeSearchParam.Type]
    KNNSearch: typing.ClassVar[KDTreeSearchParam.Type]
    RadiusSearch: typing.ClassVar[KDTreeSearchParam.Type]
    def get_search_type(self) -> KDTreeSearchParam.Type:
        """
        Get the search type (KNN, Radius, Hybrid) for the search parameter.
        
        Returns:
            open3d.cuda.pybind.geometry.KDTreeSearchParam.Type
        """
class KDTreeSearchParamHybrid(KDTreeSearchParam):
    """
    KDTree search parameters for hybrid KNN and radius search.
    """
    def __init__(self, radius: float, max_nn: int) -> None:
        ...
    def __repr__(self) -> str:
        ...
    @property
    def max_nn(self) -> int:
        """
        At maximum, ``max_nn`` neighbors will be searched.
        """
    @max_nn.setter
    def max_nn(self, arg0: int) -> None:
        ...
    @property
    def radius(self) -> float:
        """
        Search radius.
        """
    @radius.setter
    def radius(self, arg0: float) -> None:
        ...
class KDTreeSearchParamKNN(KDTreeSearchParam):
    """
    KDTree search parameters for pure KNN search.
    """
    def __init__(self, knn: int = 30) -> None:
        ...
    def __repr__(self) -> str:
        ...
    @property
    def knn(self) -> int:
        """
        Number of the neighbors that will be searched.
        """
    @knn.setter
    def knn(self, arg0: int) -> None:
        ...
class KDTreeSearchParamRadius(KDTreeSearchParam):
    """
    KDTree search parameters for pure radius search.
    """
    def __init__(self, radius: float) -> None:
        ...
    def __repr__(self) -> str:
        ...
    @property
    def radius(self) -> float:
        """
        Search radius.
        """
    @radius.setter
    def radius(self, arg0: float) -> None:
        ...
class LineSet(Geometry3D):
    """
    LineSet define a sets of lines in 3D. A typical application is to display the point cloud correspondence pairs.
    """
    @staticmethod
    @typing.overload
    def create_camera_visualization(view_width_px: int, view_height_px: int, intrinsic: numpy.ndarray, extrinsic: numpy.ndarray, scale: float = 1.0) -> LineSet:
        """
        Factory function to create a LineSet from intrinsic and extrinsic camera matrices
        """
    @staticmethod
    @typing.overload
    def create_camera_visualization(intrinsic: open3d.cuda.pybind.camera.PinholeCameraIntrinsic, extrinsic: numpy.ndarray, scale: float = 1.0) -> LineSet:
        """
        Factory function to create a LineSet from intrinsic and extrinsic camera matrices
        """
    @staticmethod
    def create_from_axis_aligned_bounding_box(box: AxisAlignedBoundingBox) -> LineSet:
        """
        Factory function to create a LineSet from an AxisAlignedBoundingBox.
        
        Args:
            box (open3d.cuda.pybind.geometry.AxisAlignedBoundingBox): The input bounding box.
        
        Returns:
            open3d.cuda.pybind.geometry.LineSet
        """
    @staticmethod
    def create_from_oriented_bounding_box(box: OrientedBoundingBox) -> LineSet:
        """
        Factory function to create a LineSet from an OrientedBoundingBox.
        
        Args:
            box (open3d.cuda.pybind.geometry.OrientedBoundingBox): The input bounding box.
        
        Returns:
            open3d.cuda.pybind.geometry.LineSet
        """
    @staticmethod
    def create_from_point_cloud_correspondences(cloud0: PointCloud, cloud1: PointCloud, correspondences: list[tuple[int, int]]) -> LineSet:
        """
        Factory function to create a LineSet from two pointclouds and a correspondence set.
        
        Args:
            cloud0 (open3d.cuda.pybind.geometry.PointCloud): First point cloud.
            cloud1 (open3d.cuda.pybind.geometry.PointCloud): Second point cloud.
            correspondences (list[tuple[int, int]]): Set of correspondences.
        
        Returns:
            open3d.cuda.pybind.geometry.LineSet
        """
    @staticmethod
    def create_from_tetra_mesh(mesh: TetraMesh) -> LineSet:
        """
        Factory function to create a LineSet from edges of a tetra mesh.
        
        Args:
            mesh (open3d.cuda.pybind.geometry.TetraMesh): The input tetra mesh.
        
        Returns:
            open3d.cuda.pybind.geometry.LineSet
        """
    @staticmethod
    def create_from_triangle_mesh(mesh: TriangleMesh) -> LineSet:
        """
        Factory function to create a LineSet from edges of a triangle mesh.
        
        Args:
            mesh (open3d.cuda.pybind.geometry.TriangleMesh): The input triangle mesh.
        
        Returns:
            open3d.cuda.pybind.geometry.LineSet
        """
    def __add__(self, arg0: LineSet) -> LineSet:
        ...
    def __copy__(self) -> LineSet:
        ...
    def __deepcopy__(self, arg0: dict) -> LineSet:
        ...
    def __iadd__(self, arg0: LineSet) -> LineSet:
        ...
    @typing.overload
    def __init__(self) -> None:
        """
        Default constructor
        """
    @typing.overload
    def __init__(self, arg0: LineSet) -> None:
        """
        Copy constructor
        """
    @typing.overload
    def __init__(self, points: open3d.cuda.pybind.utility.Vector3dVector, lines: open3d.cuda.pybind.utility.Vector2iVector) -> None:
        """
        Create a LineSet from given points and line indices
        """
    def __repr__(self) -> str:
        ...
    def get_line_coordinate(self, line_index: int) -> tuple[numpy.ndarray, numpy.ndarray]:
        """
        Args:
            line_index (int): Index of the line.
        
        Returns:
            tuple[numpy.ndarray[numpy.float64[3, 1]], numpy.ndarray[numpy.float64[3, 1]]]
        """
    def has_colors(self) -> bool:
        """
        Returns ``True`` if the object's lines contain colors.
        
        Returns:
            bool
        """
    def has_lines(self) -> bool:
        """
        Returns ``True`` if the object contains lines.
        
        Returns:
            bool
        """
    def has_points(self) -> bool:
        """
        Returns ``True`` if the object contains points.
        
        Returns:
            bool
        """
    def paint_uniform_color(self, color: numpy.ndarray) -> LineSet:
        """
        Assigns each line in the line set the same color.
        
        Args:
            color (numpy.ndarray[numpy.float64[3, 1]]): Color for the LineSet.
        
        Returns:
            open3d.cuda.pybind.geometry.LineSet
        """
    @property
    def colors(self) -> open3d.cuda.pybind.utility.Vector3dVector:
        """
        ``float64`` array of shape ``(num_lines, 3)``, range ``[0, 1]`` , use ``numpy.asarray()`` to access data: RGB colors of lines.
        """
    @colors.setter
    def colors(self, arg0: open3d.cuda.pybind.utility.Vector3dVector) -> None:
        ...
    @property
    def lines(self) -> open3d.cuda.pybind.utility.Vector2iVector:
        """
        ``int`` array of shape ``(num_lines, 2)``, use ``numpy.asarray()`` to access data: Lines denoted by the index of points forming the line.
        """
    @lines.setter
    def lines(self, arg0: open3d.cuda.pybind.utility.Vector2iVector) -> None:
        ...
    @property
    def points(self) -> open3d.cuda.pybind.utility.Vector3dVector:
        """
        ``float64`` array of shape ``(num_points, 3)``, use ``numpy.asarray()`` to access data: Points coordinates.
        """
    @points.setter
    def points(self, arg0: open3d.cuda.pybind.utility.Vector3dVector) -> None:
        ...
class MeshBase(Geometry3D):
    """
    MeshBase class. Triangle mesh contains vertices. Optionally, the mesh may also contain vertex normals and vertex colors.
    """
    def __add__(self, arg0: MeshBase) -> MeshBase:
        ...
    def __copy__(self) -> MeshBase:
        ...
    def __deepcopy__(self, arg0: dict) -> MeshBase:
        ...
    def __iadd__(self, arg0: MeshBase) -> MeshBase:
        ...
    @typing.overload
    def __init__(self) -> None:
        """
        Default constructor
        """
    @typing.overload
    def __init__(self, arg0: MeshBase) -> None:
        """
        Copy constructor
        """
    def __repr__(self) -> str:
        ...
    def compute_convex_hull(self) -> tuple[TriangleMesh, list[int]]:
        """
        Computes the convex hull of the triangle mesh.
        
        Returns:
            tuple[open3d.cuda.pybind.geometry.TriangleMesh, list[int]]
        """
    def has_vertex_colors(self) -> bool:
        """
        Returns ``True`` if the mesh contains vertex colors.
        
        Returns:
            bool
        """
    def has_vertex_normals(self) -> bool:
        """
        Returns ``True`` if the mesh contains vertex normals.
        
        Returns:
            bool
        """
    def has_vertices(self) -> bool:
        """
        Returns ``True`` if the mesh contains vertices.
        
        Returns:
            bool
        """
    def normalize_normals(self) -> MeshBase:
        """
        Normalize vertex normals to length 1.
        
        Returns:
            open3d.cuda.pybind.geometry.MeshBase
        """
    def paint_uniform_color(self, color: numpy.ndarray) -> MeshBase:
        """
        Assigns each vertex in the MeshBase the same color.
        
        Args:
            color (numpy.ndarray[numpy.float64[3, 1]]): RGB colors of vertices.
        
        Returns:
            open3d.cuda.pybind.geometry.MeshBase
        """
    @property
    def vertex_colors(self) -> open3d.cuda.pybind.utility.Vector3dVector:
        """
        ``float64`` array of shape ``(num_vertices, 3)``, range ``[0, 1]`` , use ``numpy.asarray()`` to access data: RGB colors of vertices.
        """
    @vertex_colors.setter
    def vertex_colors(self, arg0: open3d.cuda.pybind.utility.Vector3dVector) -> None:
        ...
    @property
    def vertex_normals(self) -> open3d.cuda.pybind.utility.Vector3dVector:
        """
        ``float64`` array of shape ``(num_vertices, 3)``, use ``numpy.asarray()`` to access data: Vertex normals.
        """
    @vertex_normals.setter
    def vertex_normals(self, arg0: open3d.cuda.pybind.utility.Vector3dVector) -> None:
        ...
    @property
    def vertices(self) -> open3d.cuda.pybind.utility.Vector3dVector:
        """
        ``float64`` array of shape ``(num_vertices, 3)``, use ``numpy.asarray()`` to access data: Vertex coordinates.
        """
    @vertices.setter
    def vertices(self, arg0: open3d.cuda.pybind.utility.Vector3dVector) -> None:
        ...
class Octree(Geometry3D):
    """
    Octree datastructure.
    """
    @staticmethod
    def create_from_voxel_grid(*args, **kwargs) -> None:
        """
        Returns:
            None
        """
    @staticmethod
    def is_point_in_bound(point: numpy.ndarray, origin: numpy.ndarray, size: float) -> bool:
        """
        Return true if point within bound, that is, origin<= point < origin + size
        
        Args:
            point (numpy.ndarray[numpy.float64[3, 1]]): Coordinates of the point.
            origin (numpy.ndarray[numpy.float64[3, 1]]): Origin coordinates.
            size (float): Size of the Octree.
        
        Returns:
            bool
        """
    def __copy__(self) -> Octree:
        ...
    def __deepcopy__(self, arg0: dict) -> Octree:
        ...
    @typing.overload
    def __init__(self) -> None:
        """
            Default constructor
        """
    @typing.overload
    def __init__(self, arg0: Octree) -> None:
        """
            Copy constructor
        
        Args:
            arg0 (open3d.cuda.pybind.geometry.Octree)
        """
    @typing.overload
    def __init__(self, max_depth: int) -> None:
        """
        Args:
            max_depth (int)
        """
    @typing.overload
    def __init__(self, max_depth: int, origin: numpy.ndarray, size: float) -> None:
        """
        Args:
            max_depth (int)
            origin (numpy.ndarray[numpy.float64[3, 1]])
            size (float)
        """
    def __repr__(self) -> str:
        ...
    def convert_from_point_cloud(self, point_cloud: PointCloud, size_expand: float = 0.01) -> None:
        """
        Convert octree from point cloud.
        
        Args:
            point_cloud (open3d.cuda.pybind.geometry.PointCloud): Input point cloud.
            size_expand (float, optional, default=0.01): A small expansion size such that the octree is slightly bigger than the original point cloud bounds to accommodate all points.
        
        Returns:
            None
        """
    def insert_point(self, point: numpy.ndarray, f_init: typing.Callable[[], OctreeLeafNode], f_update: typing.Callable[[OctreeLeafNode], None], fi_init: typing.Callable[[], OctreeInternalNode] = None, fi_update: typing.Callable[[OctreeInternalNode], None] = None) -> None:
        """
        Insert a point to the octree.
        
        Args:
            point (numpy.ndarray[numpy.float64[3, 1]]): Coordinates of the point.
            f_init (Callable[[], open3d.cuda.pybind.geometry.OctreeLeafNode])
            f_update (Callable[[open3d.cuda.pybind.geometry.OctreeLeafNode], None])
            fi_init (Callable[[], open3d.cuda.pybind.geometry.OctreeInternalNode], optional, default=None)
            fi_update (Callable[[open3d.cuda.pybind.geometry.OctreeInternalNode], None], optional, default=None)
        
        Returns:
            None
        """
    def locate_leaf_node(self, point: numpy.ndarray) -> tuple[OctreeLeafNode, OctreeNodeInfo]:
        """
        Returns leaf OctreeNode and OctreeNodeInfo where the querypoint should reside.
        
        Args:
            point (numpy.ndarray[numpy.float64[3, 1]]): Coordinates of the point.
        
        Returns:
            tuple[open3d.cuda.pybind.geometry.OctreeLeafNode, open3d.cuda.pybind.geometry.OctreeNodeInfo]
        """
    def to_voxel_grid(self) -> VoxelGrid:
        """
        Convert to VoxelGrid.
        
        Returns:
            open3d.cuda.pybind.geometry.VoxelGrid
        """
    def traverse(self, f: typing.Callable[[OctreeNode, OctreeNodeInfo], bool]) -> None:
        """
        DFS traversal of the octree from the root, with a callback function f being called for each node.
        """
    @property
    def max_depth(self) -> int:
        """
        int: Maximum depth of the octree. The depth is defined as the distance from the deepest leaf node to root. A tree with only the root node has depth 0.
        """
    @max_depth.setter
    def max_depth(self, arg0: int) -> None:
        ...
    @property
    def origin(self) -> numpy.ndarray:
        """
        (3, 1) float numpy array: Global min bound (include). A point is within bound iff origin <= point < origin + size.
        """
    @origin.setter
    def origin(self, arg0: numpy.ndarray) -> None:
        ...
    @property
    def root_node(self) -> OctreeNode:
        """
        OctreeNode: The root octree node.
        """
    @root_node.setter
    def root_node(self, arg0: OctreeNode) -> None:
        ...
    @property
    def size(self) -> float:
        """
        float: Outer bounding box edge size for the whole octree. A point is within bound iff origin <= point < origin + size.
        """
    @size.setter
    def size(self, arg0: float) -> None:
        ...
class OctreeColorLeafNode(OctreeLeafNode):
    """
    OctreeColorLeafNode class is an OctreeLeafNode containing color.
    """
    @staticmethod
    def get_init_function() -> typing.Callable[[], OctreeLeafNode]:
        """
        Get lambda function for initializing OctreeLeafNode. When the init function is called, an empty OctreeColorLeafNode is created.
        """
    @staticmethod
    def get_update_function(color: numpy.ndarray) -> typing.Callable[[OctreeLeafNode], None]:
        """
        Get lambda function for updating OctreeLeafNode. When called, the update function updates the corresponding node with the input color.
        """
    def __copy__(self) -> OctreeColorLeafNode:
        ...
    def __deepcopy__(self, arg0: dict) -> OctreeColorLeafNode:
        ...
    @typing.overload
    def __init__(self) -> None:
        """
        Default constructor
        """
    @typing.overload
    def __init__(self, arg0: OctreeColorLeafNode) -> None:
        """
        Copy constructor
        """
    def __repr__(self) -> str:
        ...
    @property
    def color(self) -> numpy.ndarray:
        """
        (3, 1) float numpy array: Color of the node.
        """
    @color.setter
    def color(self, arg0: numpy.ndarray) -> None:
        ...
class OctreeInternalNode(OctreeNode):
    """
    OctreeInternalNode class, containing OctreeNode children.
    """
    @staticmethod
    def get_init_function() -> typing.Callable[[], OctreeInternalNode]:
        """
        Get lambda function for initializing OctreeInternalNode. When the init function is called, an empty OctreeInternalNode is created.
        """
    @staticmethod
    def get_update_function() -> typing.Callable[[OctreeInternalNode], None]:
        """
        Get lambda function for updating OctreeInternalNode. This update function does nothing.
        """
    def __copy__(self) -> OctreeInternalNode:
        ...
    def __deepcopy__(self, arg0: dict) -> OctreeInternalNode:
        ...
    @typing.overload
    def __init__(self) -> None:
        """
            Default constructor
        """
    @typing.overload
    def __init__(self, arg0: OctreeInternalNode) -> None:
        """
            Copy constructor
        
        Args:
            arg0 (open3d.cuda.pybind.geometry.OctreeInternalNode)
        """
    def __repr__(self) -> str:
        ...
    @property
    def children(self) -> list[OctreeNode]:
        """
        List of children Nodes.
        """
    @children.setter
    def children(self, arg0: list[OctreeNode]) -> None:
        ...
class OctreeInternalPointNode(OctreeInternalNode):
    """
    OctreeInternalPointNode class is an OctreeInternalNode with a list of point indices (from point cloud) belonging to children of this node.
    """
    @staticmethod
    def get_init_function() -> typing.Callable[[], OctreeInternalNode]:
        """
        Get lambda function for initializing OctreeInternalPointNode. When the init function is called, an empty OctreeInternalPointNode is created.
        """
    @staticmethod
    def get_update_function(arg0: int) -> typing.Callable[[OctreeInternalNode], None]:
        """
        Get lambda function for updating OctreeInternalPointNode. When called, the update function adds the input point index to the corresponding node's list of indices of children points.
        """
    def __copy__(self) -> OctreeInternalPointNode:
        ...
    def __deepcopy__(self, arg0: dict) -> OctreeInternalPointNode:
        ...
    @typing.overload
    def __init__(self) -> None:
        """
            Default constructor
        """
    @typing.overload
    def __init__(self, arg0: OctreeInternalPointNode) -> None:
        """
            Copy constructor
        
        Args:
            arg0 (open3d.cuda.pybind.geometry.OctreeInternalPointNode)
        """
    def __repr__(self) -> str:
        ...
    @property
    def children(self) -> list[OctreeNode]:
        """
        List of children Nodes.
        """
    @children.setter
    def children(self, arg0: list[OctreeNode]) -> None:
        ...
    @property
    def indices(self) -> list[int]:
        """
        List of point cloud point indices contained in children nodes.
        """
    @indices.setter
    def indices(self, arg0: list[int]) -> None:
        ...
class OctreeLeafNode(OctreeNode):
    """
    OctreeLeafNode base class.
    """
    __hash__: typing.ClassVar[None] = None
    def __eq__(self, other: OctreeLeafNode) -> bool:
        """
        Check equality of OctreeLeafNode.
        """
    def __repr__(self) -> str:
        ...
    def clone(self) -> OctreeLeafNode:
        """
        Clone this OctreeLeafNode.
        """
class OctreeNode:
    """
    The base class for octree node.
    """
    def __repr__(self) -> str:
        ...
class OctreeNodeInfo:
    """
    OctreeNode's information. OctreeNodeInfo is computed on the fly, not stored with the Node.
    """
    def __init__(self, origin: numpy.ndarray, size: float, depth: int, child_index: int) -> None:
        """
        Args:
            origin (numpy.ndarray[numpy.float64[3, 1]])
            size (float)
            depth (int)
            child_index (int)
        """
    def __repr__(self) -> str:
        ...
    @property
    def child_index(self) -> int:
        """
        int: Node's child index of itself. For non-root nodes, child_index is 0~7; root node's child_index is -1.
        """
    @child_index.setter
    def child_index(self, arg0: int) -> None:
        ...
    @property
    def depth(self) -> int:
        """
        int: Depth of the node to the root. The root is of depth 0.
        """
    @depth.setter
    def depth(self, arg0: int) -> None:
        ...
    @property
    def origin(self) -> numpy.ndarray:
        """
        (3, 1) float numpy array: Origin coordinate of the node.
        """
    @origin.setter
    def origin(self, arg0: numpy.ndarray) -> None:
        ...
    @property
    def size(self) -> float:
        """
        float: Size of the node.
        """
    @size.setter
    def size(self, arg0: float) -> None:
        ...
class OctreePointColorLeafNode(OctreeLeafNode):
    """
    OctreePointColorLeafNode class is an OctreeLeafNode containing color.
    """
    @staticmethod
    def get_init_function() -> typing.Callable[[], OctreeLeafNode]:
        """
        Get lambda function for initializing OctreeLeafNode. When the init function is called, an empty OctreePointColorLeafNode is created.
        """
    @staticmethod
    def get_update_function(idx: int, color: numpy.ndarray) -> typing.Callable[[OctreeLeafNode], None]:
        """
        Get lambda function for updating OctreeLeafNode. When called, the update function updates the corresponding node with the new point index and the input color.
        """
    def __copy__(self) -> OctreePointColorLeafNode:
        ...
    def __deepcopy__(self, arg0: dict) -> OctreePointColorLeafNode:
        ...
    @typing.overload
    def __init__(self) -> None:
        """
        Default constructor
        """
    @typing.overload
    def __init__(self, arg0: OctreePointColorLeafNode) -> None:
        """
        Copy constructor
        """
    def __repr__(self) -> str:
        ...
    @property
    def color(self) -> numpy.ndarray:
        """
        (3, 1) float numpy array: Color of the node.
        """
    @color.setter
    def color(self, arg0: numpy.ndarray) -> None:
        ...
    @property
    def indices(self) -> list[int]:
        """
        List of point cloud point indices contained in this leaf node.
        """
    @indices.setter
    def indices(self, arg0: list[int]) -> None:
        ...
class OrientedBoundingBox(Geometry3D):
    """
    Class that defines an oriented box that can be computed from 3D geometries.
    """
    @staticmethod
    def create_from_axis_aligned_bounding_box(aabox: AxisAlignedBoundingBox) -> OrientedBoundingBox:
        """
        Returns an oriented bounding box from the AxisAlignedBoundingBox.
        
        Args:
            aabox (open3d.cuda.pybind.geometry.AxisAlignedBoundingBox): AxisAlignedBoundingBox object from which OrientedBoundingBox is created.
        
        Returns:
            open3d.cuda.pybind.geometry.OrientedBoundingBox
        """
    @staticmethod
    def create_from_points(points: open3d.cuda.pybind.utility.Vector3dVector, robust: bool = False) -> OrientedBoundingBox:
        """
        Creates the oriented bounding box that encloses the set of points.
        
        Computes the oriented bounding box based on the PCA of the convex hull.
        The returned bounding box is an approximation to the minimal bounding box.
        
        Args:
             points (open3d.utility.Vector3dVector): Input points.
             robust (bool): If set to true uses a more robust method which works in
                  degenerate cases but introduces noise to the points coordinates.
        
        Returns:
             open3d.geometry.OrientedBoundingBox: The oriented bounding box. The
             bounding box is oriented such that the axes are ordered with respect to
             the principal components.
        """
    @staticmethod
    def create_from_points_minimal(points: open3d.cuda.pybind.utility.Vector3dVector, robust: bool = False) -> OrientedBoundingBox:
        """
        Creates the oriented bounding box with the smallest volume.
        
        The algorithm makes use of the fact that at least one edge of
        the convex hull must be collinear with an edge of the minimum
        bounding box: for each triangle in the convex hull, calculate
        the minimal axis aligned box in the frame of that triangle.
        at the end, return the box with the smallest volume
        
        Args:
             points (open3d.utility.Vector3dVector): Input points.
             robust (bool): If set to true uses a more robust method which works in
                  degenerate cases but introduces noise to the points coordinates.
        
        Returns:
             open3d.geometry.OrientedBoundingBox: The oriented bounding box. The
             bounding box is oriented such that its volume is minimized.
        """
    def __copy__(self) -> OrientedBoundingBox:
        ...
    def __deepcopy__(self, arg0: dict) -> OrientedBoundingBox:
        ...
    @typing.overload
    def __init__(self) -> None:
        """
        Default constructor
        """
    @typing.overload
    def __init__(self, arg0: OrientedBoundingBox) -> None:
        """
        Copy constructor
        """
    @typing.overload
    def __init__(self, center: numpy.ndarray, R: numpy.ndarray, extent: numpy.ndarray) -> None:
        """
        Create OrientedBoudingBox from center, rotation R and extent in x, y and z direction
        """
    def __repr__(self) -> str:
        ...
    def get_box_points(self) -> open3d.cuda.pybind.utility.Vector3dVector:
        """
        Returns the eight points that define the bounding box.
        
        Returns:
            open3d.cuda.pybind.utility.Vector3dVector
        """
    def get_point_indices_within_bounding_box(self, points: open3d.cuda.pybind.utility.Vector3dVector) -> list[int]:
        """
        Return indices to points that are within the bounding box.
        
        Args:
            points (open3d.cuda.pybind.utility.Vector3dVector): A list of points.
        
        Returns:
            list[int]
        """
    def volume(self) -> float:
        """
        Returns the volume of the bounding box.
        
        Returns:
            float
        """
    @property
    def R(self) -> numpy.ndarray:
        """
        ``float64`` array of shape ``(3,3 )``
        """
    @R.setter
    def R(self, arg0: numpy.ndarray) -> None:
        ...
    @property
    def center(self) -> numpy.ndarray:
        """
        ``float64`` array of shape ``(3, )``
        """
    @center.setter
    def center(self, arg0: numpy.ndarray) -> None:
        ...
    @property
    def color(self) -> numpy.ndarray:
        """
        ``float64`` array of shape ``(3, )``
        """
    @color.setter
    def color(self, arg0: numpy.ndarray) -> None:
        ...
    @property
    def extent(self) -> numpy.ndarray:
        """
        ``float64`` array of shape ``(3, )``
        """
    @extent.setter
    def extent(self, arg0: numpy.ndarray) -> None:
        ...
class PointCloud(Geometry3D):
    """
    PointCloud class. A point cloud consists of point coordinates, and optionally point colors and point normals.
    """
    @staticmethod
    def create_from_depth_image(depth: Image, intrinsic: open3d.cuda.pybind.camera.PinholeCameraIntrinsic, extrinsic: numpy.ndarray = ..., depth_scale: float = 1000.0, depth_trunc: float = 1000.0, stride: int = 1, project_valid_depth_only: bool = True) -> PointCloud:
        """
        Factory function to create a pointcloud from a depth image and a
        camera. Given depth value d at (u, v) image coordinate, the corresponding 3d point is:
        
            - z = d / depth_scale
            - x = (u - cx) * z / fx
            - y = (v - cy) * z / fy
        
        Args:
            depth (open3d.cuda.pybind.geometry.Image): The input depth image can be either a float image, or a uint16_t image.
            intrinsic (open3d.cuda.pybind.camera.PinholeCameraIntrinsic): Intrinsic parameters of the camera.
            extrinsic (numpy.ndarray[numpy.float64[4, 4]], optional, default=array([[1., 0., 0., 0.], [0., 1., 0., 0.], [0., 0., 1., 0.], [0., 0., 0., 1.]]))
            depth_scale (float, optional, default=1000.0): The depth is scaled by 1 / depth_scale.
            depth_trunc (float, optional, default=1000.0): Truncated at depth_trunc distance.
            stride (int, optional, default=1): Sampling factor to support coarse point cloud extraction.
            project_valid_depth_only (bool, optional, default=True)
        
        Returns:
            open3d.cuda.pybind.geometry.PointCloud
        """
    @staticmethod
    def create_from_rgbd_image(image: RGBDImage, intrinsic: open3d.cuda.pybind.camera.PinholeCameraIntrinsic, extrinsic: numpy.ndarray = ..., project_valid_depth_only: bool = True) -> PointCloud:
        """
        Factory function to create a pointcloud from an RGB-D image and a camera. Given depth value d at (u, v) image coordinate, the corresponding 3d point is:
        
            - z = d / depth_scale
            - x = (u - cx) * z / fx
            - y = (v - cy) * z / fy
        
        Args:
            image (open3d.cuda.pybind.geometry.RGBDImage): The input image.
            intrinsic (open3d.cuda.pybind.camera.PinholeCameraIntrinsic): Intrinsic parameters of the camera.
            extrinsic (numpy.ndarray[numpy.float64[4, 4]], optional, default=array([[1., 0., 0., 0.], [0., 1., 0., 0.], [0., 0., 1., 0.], [0., 0., 0., 1.]]))
            project_valid_depth_only (bool, optional, default=True)
        
        Returns:
            open3d.cuda.pybind.geometry.PointCloud
        """
    @staticmethod
    def estimate_point_covariances(input: PointCloud, search_param: KDTreeSearchParam = ...) -> open3d.cuda.pybind.utility.Matrix3dVector:
        """
        Static function to compute the covariance matrix for each point in the given point cloud, doesn't change the input
        
        Args:
            input (open3d.cuda.pybind.geometry.PointCloud): The input point cloud.
            search_param (open3d.cuda.pybind.geometry.KDTreeSearchParam, optional, default=KDTreeSearchParamKNN(knn=30)): The KDTree search parameters for neighborhood search.
        
        Returns:
            open3d.cuda.pybind.utility.Matrix3dVector
        """
    def __add__(self, arg0: PointCloud) -> PointCloud:
        ...
    def __copy__(self) -> PointCloud:
        ...
    def __deepcopy__(self, arg0: dict) -> PointCloud:
        ...
    def __iadd__(self, arg0: PointCloud) -> PointCloud:
        ...
    @typing.overload
    def __init__(self) -> None:
        """
        Default constructor
        """
    @typing.overload
    def __init__(self, arg0: PointCloud) -> None:
        """
        Copy constructor
        """
    @typing.overload
    def __init__(self, points: open3d.cuda.pybind.utility.Vector3dVector) -> None:
        """
        Create a PointCloud from points
        """
    def __repr__(self) -> str:
        ...
    def cluster_dbscan(self, eps: float, min_points: int, print_progress: bool = False) -> open3d.cuda.pybind.utility.IntVector:
        """
        Cluster PointCloud using the DBSCAN algorithm  Ester et al., 'A Density-Based Algorithm for Discovering Clusters in Large Spatial Databases with Noise', 1996. Returns a list of point labels, -1 indicates noise according to the algorithm.
        
        Args:
            eps (float): Density parameter that is used to find neighbouring points.
            min_points (int): Minimum number of points to form a cluster.
            print_progress (bool, optional, default=False): If true the progress is visualized in the console.
        
        Returns:
            open3d.cuda.pybind.utility.IntVector
        """
    def compute_convex_hull(self, joggle_inputs: bool = False) -> tuple[TriangleMesh, list[int]]:
        """
        Computes the convex hull of the point cloud.
        
        Args:
             joggle_inputs (bool): If True allows the algorithm to add random noise to
                  the points to work around degenerate inputs. This adds the 'QJ'
                  option to the qhull command.
        
        Returns:
             tuple(open3d.geometry.TriangleMesh, list): The triangle mesh of the convex
             hull and the list of point indices that are part of the convex hull.
        """
    def compute_mahalanobis_distance(self) -> open3d.cuda.pybind.utility.DoubleVector:
        """
        Function to compute the Mahalanobis distance for points in a point cloud. See: https://en.wikipedia.org/wiki/Mahalanobis_distance.
        
        Returns:
            open3d.cuda.pybind.utility.DoubleVector
        """
    def compute_mean_and_covariance(self) -> tuple[numpy.ndarray, numpy.ndarray]:
        """
        Function to compute the mean and covariance matrix of a point cloud.
        
        Returns:
            tuple[numpy.ndarray[numpy.float64[3, 1]], numpy.ndarray[numpy.float64[3, 3]]]
        """
    def compute_nearest_neighbor_distance(self) -> open3d.cuda.pybind.utility.DoubleVector:
        """
        Function to compute the distance from a point to its nearest neighbor in the point cloud
        
        Returns:
            open3d.cuda.pybind.utility.DoubleVector
        """
    def compute_point_cloud_distance(self, target: PointCloud) -> open3d.cuda.pybind.utility.DoubleVector:
        """
        For each point in the source point cloud, compute the distance to the target point cloud.
        
        Args:
            target (open3d.cuda.pybind.geometry.PointCloud): The target point cloud.
        
        Returns:
            open3d.cuda.pybind.utility.DoubleVector
        """
    @typing.overload
    def crop(self, bounding_box: AxisAlignedBoundingBox, invert: bool = False) -> PointCloud:
        """
            Function to crop input pointcloud into output pointcloud
        
        Args:
            bounding_box (open3d.cuda.pybind.geometry.AxisAlignedBoundingBox): AxisAlignedBoundingBox to crop points
            invert (bool, optional, default=False): optional boolean to invert cropping
        
        Returns:
            open3d.cuda.pybind.geometry.PointCloud
        """
    @typing.overload
    def crop(self, bounding_box: OrientedBoundingBox, invert: bool = False) -> PointCloud:
        """
            Function to crop input pointcloud into output pointcloud
        
        Args:
            bounding_box (open3d.cuda.pybind.geometry.OrientedBoundingBox): AxisAlignedBoundingBox to crop points
            invert (bool, optional, default=False): optional boolean to invert cropping
        
        Returns:
            open3d.cuda.pybind.geometry.PointCloud
        """
    def detect_planar_patches(self, normal_variance_threshold_deg: float = 60, coplanarity_deg: float = 75, outlier_ratio: float = 0.75, min_plane_edge_length: float = 0.0, min_num_points: int = 0, search_param: KDTreeSearchParam = ...) -> list[OrientedBoundingBox]:
        """
        Detects planar patches in the point cloud using a robust statistics-based approach.
        
        Returns:
             A list of detected planar patches, represented as
             OrientedBoundingBox objects, with the third column (z) of R indicating
             the planar patch normal vector. The extent in the z direction is
             non-zero so that the OrientedBoundingBox contains the points that
             contribute to the plane detection.
        
        Args:
            normal_variance_threshold_deg (float, optional, default=60)
            coplanarity_deg (float, optional, default=75)
            outlier_ratio (float, optional, default=0.75): Maximum allowable ratio of outliers associated to a plane.
            min_plane_edge_length (float, optional, default=0.0): Minimum edge length of plane's long edge before being rejected.
            min_num_points (int, optional, default=0): Minimum number of points allowable for fitting planes.
            search_param (open3d.cuda.pybind.geometry.KDTreeSearchParam, optional, default=KDTreeSearchParamKNN(knn=30)): The KDTree search parameters for neighborhood search.
        
        Returns:
            list[open3d.cuda.pybind.geometry.OrientedBoundingBox]
        """
    def estimate_covariances(self, search_param: KDTreeSearchParam = ...) -> None:
        """
        Function to compute the covariance matrix for each point in the point cloud
        
        Args:
            search_param (open3d.cuda.pybind.geometry.KDTreeSearchParam, optional, default=KDTreeSearchParamKNN(knn=30)): The KDTree search parameters for neighborhood search.
        
        Returns:
            None
        """
    def estimate_normals(self, search_param: KDTreeSearchParam = ..., fast_normal_computation: bool = True) -> None:
        """
        Function to compute the normals of a point cloud. Normals are oriented with respect to the input point cloud if normals exist
        
        Args:
            search_param (open3d.cuda.pybind.geometry.KDTreeSearchParam, optional, default=KDTreeSearchParamKNN(knn=30)): The KDTree search parameters for neighborhood search.
            fast_normal_computation (bool, optional, default=True): If true, the normal estimation uses a non-iterative method to extract the eigenvector from the covariance matrix. This is faster, but is not as numerical stable.
        
        Returns:
            None
        """
    def farthest_point_down_sample(self, num_samples: int, start_index: int = 0) -> PointCloud:
        """
        Index to start downsampling from. Valid index is a non-negative number less than number of points in the input pointcloud.
        """
    def has_colors(self) -> bool:
        """
        Returns ``True`` if the point cloud contains point colors.
        
        Returns:
            bool
        """
    def has_covariances(self) -> bool:
        """
        Returns ``True`` if the point cloud contains covariances.
        """
    def has_normals(self) -> bool:
        """
        Returns ``True`` if the point cloud contains point normals.
        
        Returns:
            bool
        """
    def has_points(self) -> bool:
        """
        Returns ``True`` if the point cloud contains points.
        
        Returns:
            bool
        """
    def hidden_point_removal(self, camera_location: numpy.ndarray, radius: float) -> tuple[TriangleMesh, list[int]]:
        """
        Removes hidden points from a point cloud and returns a mesh of the remaining points. Based on Katz et al. 'Direct Visibility of Point Sets', 2007. Additional information about the choice of radius for noisy point clouds can be found in Mehra et. al. 'Visibility of Noisy Point Cloud Data', 2010.
        
        Args:
            camera_location (numpy.ndarray[numpy.float64[3, 1]]): All points not visible from that location will be removed
            radius (float): The radius of the sperical projection
        
        Returns:
            tuple[open3d.cuda.pybind.geometry.TriangleMesh, list[int]]
        """
    def normalize_normals(self) -> PointCloud:
        """
        Normalize point normals to length 1.
        
        Returns:
            open3d.cuda.pybind.geometry.PointCloud
        """
    def orient_normals_consistent_tangent_plane(self, k: int, lambda_penalty: float = 0.0, cos_alpha_tol: float = 1.0) -> None:
        """
        Function to orient the normals with respect to consistent tangent planes
        
        Args:
            k (int): Number of k nearest neighbors used in constructing the Riemannian graph used to propagate normal orientation.
            lambda_penalty (float, optional, default=0.0)
            cos_alpha_tol (float, optional, default=1.0)
        
        Returns:
            None
        """
    def orient_normals_to_align_with_direction(self, orientation_reference: numpy.ndarray = ...) -> None:
        """
        Function to orient the normals of a point cloud
        
        Args:
            orientation_reference (numpy.ndarray[numpy.float64[3, 1]], optional, default=array([0., 0., 1.])): Normals are oriented with respect to orientation_reference.
        
        Returns:
            None
        """
    def orient_normals_towards_camera_location(self, camera_location: numpy.ndarray = ...) -> None:
        """
        Function to orient the normals of a point cloud
        
        Args:
            camera_location (numpy.ndarray[numpy.float64[3, 1]], optional, default=array([0., 0., 0.])): Normals are oriented with towards the camera_location.
        
        Returns:
            None
        """
    def paint_uniform_color(self, color: numpy.ndarray) -> PointCloud:
        """
        Assigns each point in the PointCloud the same color.
        
        Args:
            color (numpy.ndarray[numpy.float64[3, 1]]): RGB color for the PointCloud.
        
        Returns:
            open3d.cuda.pybind.geometry.PointCloud
        """
    def random_down_sample(self, sampling_ratio: float) -> PointCloud:
        """
        Function to downsample input pointcloud into output pointcloud randomly. The sample is generated by randomly sampling the indexes from the point cloud.
        
        Args:
            sampling_ratio (float): Sampling ratio, the ratio of number of selected points to total number of points[0-1]
        
        Returns:
            open3d.cuda.pybind.geometry.PointCloud
        """
    def remove_duplicated_points(self) -> PointCloud:
        """
        Removes duplicated points, i.e., points that have identical coordinates. It also removes the corresponding attributes associated with the non-finite point such as normals, covariances and color entries. It doesn't re-computes these attributes after removing duplicated points.
        
        Returns:
            open3d.cuda.pybind.geometry.PointCloud
        """
    def remove_non_finite_points(self, remove_nan: bool = True, remove_infinite: bool = True) -> PointCloud:
        """
        Removes all points from the point cloud that have a nan entry, or infinite entries. It also removes the corresponding attributes associated with the non-finite point such as normals, covariances and color entries. It doesn't re-computes these attributes after removing non-finite points.
        
        Args:
            remove_nan (bool, optional, default=True): Remove NaN values from the PointCloud
            remove_infinite (bool, optional, default=True): Remove infinite values from the PointCloud
        
        Returns:
            open3d.cuda.pybind.geometry.PointCloud
        """
    def remove_radius_outlier(self, nb_points: int, radius: float, print_progress: bool = False) -> tuple[PointCloud, list[int]]:
        """
        Removes points that have neighbors less than nb_points in a sphere of a given radius
        
        Args:
            nb_points (int): Number of points within the radius.
            radius (float): Radius of the sphere.
            print_progress (bool, optional, default=False): Set to True to print progress bar.
        
        Returns:
            tuple[open3d.cuda.pybind.geometry.PointCloud, list[int]]
        """
    def remove_statistical_outlier(self, nb_neighbors: int, std_ratio: float, print_progress: bool = False) -> tuple[PointCloud, list[int]]:
        """
        Removes points that are further away from their neighbors in average.
        
        Args:
            nb_neighbors (int): Number of neighbors around the target point.
            std_ratio (float): Standard deviation ratio.
            print_progress (bool, optional, default=False): Set to True to print progress bar.
        
        Returns:
            tuple[open3d.cuda.pybind.geometry.PointCloud, list[int]]
        """
    def segment_plane(self, distance_threshold: float, ransac_n: int, num_iterations: int, probability: float = 0.99999999) -> tuple[numpy.ndarray, list[int]]:
        """
        Segments a plane in the point cloud using the RANSAC algorithm.
        
        Args:
            distance_threshold (float): Max distance a point can be from the plane model, and still be considered an inlier.
            ransac_n (int): Number of initial points to be considered inliers in each iteration.
            num_iterations (int): Number of iterations.
            probability (float, optional, default=0.99999999): Expected probability of finding the optimal plane.
        
        Returns:
            tuple[numpy.ndarray[numpy.float64[4, 1]], list[int]]
        """
    def select_by_index(self, indices: list[int], invert: bool = False) -> PointCloud:
        """
        Function to select points from input pointcloud into output pointcloud.
        
        Args:
            indices (list[int]): Indices of points to be selected.
            invert (bool, optional, default=False): Set to ``True`` to invert the selection of indices.
        
        Returns:
            open3d.cuda.pybind.geometry.PointCloud
        """
    def uniform_down_sample(self, every_k_points: int) -> PointCloud:
        """
        Function to downsample input pointcloud into output pointcloud uniformly. The sample is performed in the order of the points with the 0-th point always chosen, not at random.
        
        Args:
            every_k_points (int): Sample rate, the selected point indices are [0, k, 2k, ...]
        
        Returns:
            open3d.cuda.pybind.geometry.PointCloud
        """
    def voxel_down_sample(self, voxel_size: float) -> PointCloud:
        """
        Function to downsample input pointcloud into output pointcloud with a voxel. Normals and colors are averaged if they exist.
        
        Args:
            voxel_size (float): Voxel size to downsample into.
        
        Returns:
            open3d.cuda.pybind.geometry.PointCloud
        """
    def voxel_down_sample_and_trace(self, voxel_size: float, min_bound: numpy.ndarray, max_bound: numpy.ndarray, approximate_class: bool = False) -> tuple[PointCloud, numpy.ndarray, list[open3d.cuda.pybind.utility.IntVector]]:
        """
        Function to downsample using PointCloud::VoxelDownSample. Also records point cloud index before downsampling
        
        Args:
            voxel_size (float): Voxel size to downsample into.
            min_bound (numpy.ndarray[numpy.float64[3, 1]]): Minimum coordinate of voxel boundaries
            max_bound (numpy.ndarray[numpy.float64[3, 1]]): Maximum coordinate of voxel boundaries
            approximate_class (bool, optional, default=False)
        
        Returns:
            tuple[open3d.cuda.pybind.geometry.PointCloud, numpy.ndarray[numpy.int32[m, n]], list[open3d.cuda.pybind.utility.IntVector]]
        """
    @property
    def colors(self) -> open3d.cuda.pybind.utility.Vector3dVector:
        """
        ``float64`` array of shape ``(num_points, 3)``, range ``[0, 1]`` , use ``numpy.asarray()`` to access data: RGB colors of points.
        """
    @colors.setter
    def colors(self, arg0: open3d.cuda.pybind.utility.Vector3dVector) -> None:
        ...
    @property
    def covariances(self) -> open3d.cuda.pybind.utility.Matrix3dVector:
        """
        ``float64`` array of shape ``(num_points, 3, 3)``, use ``numpy.asarray()`` to access data: Points covariances.
        """
    @covariances.setter
    def covariances(self, arg0: open3d.cuda.pybind.utility.Matrix3dVector) -> None:
        ...
    @property
    def normals(self) -> open3d.cuda.pybind.utility.Vector3dVector:
        """
        ``float64`` array of shape ``(num_points, 3)``, use ``numpy.asarray()`` to access data: Points normals.
        """
    @normals.setter
    def normals(self, arg0: open3d.cuda.pybind.utility.Vector3dVector) -> None:
        ...
    @property
    def points(self) -> open3d.cuda.pybind.utility.Vector3dVector:
        """
        ``float64`` array of shape ``(num_points, 3)``, use ``numpy.asarray()`` to access data: Points coordinates.
        """
    @points.setter
    def points(self, arg0: open3d.cuda.pybind.utility.Vector3dVector) -> None:
        ...
class RGBDImage(Geometry2D):
    """
    RGBDImage is for a pair of registered color and depth images, viewed from the same view, of the same resolution. If you have other format, convert it first.
    """
    @staticmethod
    def create_from_color_and_depth(color: Image, depth: Image, depth_scale: float = 1000.0, depth_trunc: float = 3.0, convert_rgb_to_intensity: bool = True) -> RGBDImage:
        """
        Function to make RGBDImage from color and depth image
        
        Args:
            color (open3d.cuda.pybind.geometry.Image): The color image.
            depth (open3d.cuda.pybind.geometry.Image): The depth image.
            depth_scale (float, optional, default=1000.0): The ratio to scale depth values. The depth values will first be scaled and then truncated.
            depth_trunc (float, optional, default=3.0): Depth values larger than ``depth_trunc`` gets truncated to 0. The depth values will first be scaled and then truncated.
            convert_rgb_to_intensity (bool, optional, default=True): Whether to convert RGB image to intensity image.
        
        Returns:
            open3d.cuda.pybind.geometry.RGBDImage
        """
    @staticmethod
    def create_from_nyu_format(color: Image, depth: Image, convert_rgb_to_intensity: bool = True) -> RGBDImage:
        """
        Function to make RGBDImage (for NYU format)
        
        Args:
            color (open3d.cuda.pybind.geometry.Image): The color image.
            depth (open3d.cuda.pybind.geometry.Image): The depth image.
            convert_rgb_to_intensity (bool, optional, default=True): Whether to convert RGB image to intensity image.
        
        Returns:
            open3d.cuda.pybind.geometry.RGBDImage
        """
    @staticmethod
    def create_from_redwood_format(color: Image, depth: Image, convert_rgb_to_intensity: bool = True) -> RGBDImage:
        """
        Function to make RGBDImage (for Redwood format)
        
        Args:
            color (open3d.cuda.pybind.geometry.Image): The color image.
            depth (open3d.cuda.pybind.geometry.Image): The depth image.
            convert_rgb_to_intensity (bool, optional, default=True): Whether to convert RGB image to intensity image.
        
        Returns:
            open3d.cuda.pybind.geometry.RGBDImage
        """
    @staticmethod
    def create_from_sun_format(color: Image, depth: Image, convert_rgb_to_intensity: bool = True) -> RGBDImage:
        """
        Function to make RGBDImage (for SUN format)
        
        Args:
            color (open3d.cuda.pybind.geometry.Image): The color image.
            depth (open3d.cuda.pybind.geometry.Image): The depth image.
            convert_rgb_to_intensity (bool, optional, default=True): Whether to convert RGB image to intensity image.
        
        Returns:
            open3d.cuda.pybind.geometry.RGBDImage
        """
    @staticmethod
    def create_from_tum_format(color: Image, depth: Image, convert_rgb_to_intensity: bool = True) -> RGBDImage:
        """
        Function to make RGBDImage (for TUM format)
        
        Args:
            color (open3d.cuda.pybind.geometry.Image): The color image.
            depth (open3d.cuda.pybind.geometry.Image): The depth image.
            convert_rgb_to_intensity (bool, optional, default=True): Whether to convert RGB image to intensity image.
        
        Returns:
            open3d.cuda.pybind.geometry.RGBDImage
        """
    def __init__(self) -> None:
        """
        Default constructor
        """
    def __repr__(self) -> str:
        ...
    @property
    def color(self) -> Image:
        """
        open3d.geometry.Image: The color image.
        """
    @color.setter
    def color(self, arg0: Image) -> None:
        ...
    @property
    def depth(self) -> Image:
        """
        open3d.geometry.Image: The depth image.
        """
    @depth.setter
    def depth(self, arg0: Image) -> None:
        ...
class SimplificationContraction:
    """
    Members:
    
      Average : The vertex positions are computed by the averaging.
    
      Quadric : The vertex positions are computed by minimizing the distance to the adjacent triangle planes.
    """
    Average: typing.ClassVar[SimplificationContraction]
    Quadric: typing.ClassVar[SimplificationContraction]
    __members__: typing.ClassVar[dict[str, SimplificationContraction]]
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
class TetraMesh(MeshBase):
    """
    TetraMesh class. Tetra mesh contains vertices and tetrahedra represented by the indices to the vertices.
    """
    @staticmethod
    def create_from_point_cloud(point_cloud: PointCloud) -> tuple[TetraMesh, list[int]]:
        """
        Function to create a tetrahedral mesh from a point cloud.
        
        Args:
            point_cloud (open3d.cuda.pybind.geometry.PointCloud): A PointCloud.
        
        Returns:
            tuple[open3d.cuda.pybind.geometry.TetraMesh, list[int]]
        """
    def __add__(self, arg0: TetraMesh) -> TetraMesh:
        ...
    def __copy__(self) -> TetraMesh:
        ...
    def __deepcopy__(self, arg0: dict) -> TetraMesh:
        ...
    def __iadd__(self, arg0: TetraMesh) -> TetraMesh:
        ...
    @typing.overload
    def __init__(self) -> None:
        """
        Default constructor
        """
    @typing.overload
    def __init__(self, arg0: TetraMesh) -> None:
        """
        Copy constructor
        """
    @typing.overload
    def __init__(self, vertices: open3d.cuda.pybind.utility.Vector3dVector, tetras: open3d.cuda.pybind.utility.Vector4iVector) -> None:
        """
        Create a tetrahedra mesh from vertices and tetra indices
        """
    def __repr__(self) -> str:
        ...
    def extract_triangle_mesh(self, values: open3d.cuda.pybind.utility.DoubleVector, level: float) -> TriangleMesh:
        """
        Function that generates a triangle mesh of the specified iso-surface.
        
        Args:
            values (open3d.cuda.pybind.utility.DoubleVector): Vector with a scalar value for each vertex in the tetra mesh
            level (float): A scalar which defines the level-set to extract
        
        Returns:
            open3d.cuda.pybind.geometry.TriangleMesh
        """
    def has_tetras(self) -> bool:
        """
        Returns ``True`` if the mesh contains tetras.
        
        Returns:
            bool
        """
    def has_vertices(self) -> bool:
        """
        Returns ``True`` if the mesh contains vertices.
        
        Returns:
            bool
        """
    def remove_degenerate_tetras(self) -> TetraMesh:
        """
        Function that removes degenerate tetras, i.e., tetras that references a single vertex multiple times in a single tetra. They are usually the product of removing duplicated vertices.
        
        Returns:
            open3d.cuda.pybind.geometry.TetraMesh
        """
    def remove_duplicated_tetras(self) -> TetraMesh:
        """
        Function that removes duplicated tetras, i.e., removes tetras that reference the same four vertices, independent of their order.
        
        Returns:
            open3d.cuda.pybind.geometry.TetraMesh
        """
    def remove_duplicated_vertices(self) -> TetraMesh:
        """
        Function that removes duplicated vertices, i.e., vertices that have identical coordinates.
        
        Returns:
            open3d.cuda.pybind.geometry.TetraMesh
        """
    def remove_unreferenced_vertices(self) -> TetraMesh:
        """
        This function removes vertices from the tetra mesh that are not referenced in any tetra of the mesh.
        
        Returns:
            open3d.cuda.pybind.geometry.TetraMesh
        """
    @property
    def tetras(self) -> open3d.cuda.pybind.utility.Vector4iVector:
        """
        ``int64`` array of shape ``(num_tetras, 4)``, use ``numpy.asarray()`` to access data: List of tetras denoted by the index of points forming the tetra.
        """
    @tetras.setter
    def tetras(self, arg0: open3d.cuda.pybind.utility.Vector4iVector) -> None:
        ...
    @property
    def vertices(self) -> open3d.cuda.pybind.utility.Vector3dVector:
        """
        ``float64`` array of shape ``(num_vertices, 3)``, use ``numpy.asarray()`` to access data: Vertex coordinates.
        """
    @vertices.setter
    def vertices(self, arg0: open3d.cuda.pybind.utility.Vector3dVector) -> None:
        ...
class TriangleMesh(MeshBase):
    """
    TriangleMesh class. Triangle mesh contains vertices and triangles represented by the indices to the vertices. Optionally, the mesh may also contain triangle normals, vertex normals and vertex colors.
    """
    @staticmethod
    def create_arrow(cylinder_radius: float = 1.0, cone_radius: float = 1.5, cylinder_height: float = 5.0, cone_height: float = 4.0, resolution: int = 20, cylinder_split: int = 4, cone_split: int = 1) -> TriangleMesh:
        """
        Factory function to create an arrow mesh
        
        Args:
            cylinder_radius (float, optional, default=1.0): The radius of the cylinder.
            cone_radius (float, optional, default=1.5): The radius of the cone.
            cylinder_height (float, optional, default=5.0): The height of the cylinder. The cylinder is from (0, 0, 0) to (0, 0, cylinder_height)
            cone_height (float, optional, default=4.0): The height of the cone. The axis of the cone will be from (0, 0, cylinder_height) to (0, 0, cylinder_height + cone_height)
            resolution (int, optional, default=20): The cone will be split into ``resolution`` segments.
            cylinder_split (int, optional, default=4): The ``cylinder_height`` will be split into ``cylinder_split`` segments.
            cone_split (int, optional, default=1): The ``cone_height`` will be split into ``cone_split`` segments.
        
        Returns:
            open3d.cuda.pybind.geometry.TriangleMesh
        """
    @staticmethod
    def create_box(width: float = 1.0, height: float = 1.0, depth: float = 1.0, create_uv_map: bool = False, map_texture_to_each_face: bool = False) -> TriangleMesh:
        """
        Factory function to create a box. The left bottom corner on the front will be placed at (0, 0, 0), and default UV map, maps the entire texture to each face.
        
        Args:
            width (float, optional, default=1.0): x-directional length.
            height (float, optional, default=1.0): y-directional length.
            depth (float, optional, default=1.0): z-directional length.
            create_uv_map (bool, optional, default=False): Add default uv map to the mesh.
            map_texture_to_each_face (bool, optional, default=False): Map entire texture to each face.
        
        Returns:
            open3d.cuda.pybind.geometry.TriangleMesh
        """
    @staticmethod
    def create_cone(radius: float = 1.0, height: float = 2.0, resolution: int = 20, split: int = 1, create_uv_map: bool = False) -> TriangleMesh:
        """
        Factory function to create a cone mesh.
        
        Args:
            radius (float, optional, default=1.0): The radius of the cone.
            height (float, optional, default=2.0): The height of the cone. The axis of the cone will be from (0, 0, 0) to (0, 0, height).
            resolution (int, optional, default=20): The circle will be split into ``resolution`` segments
            split (int, optional, default=1): The ``height`` will be split into ``split`` segments.
            create_uv_map (bool, optional, default=False): Add default uv map to the mesh.
        
        Returns:
            open3d.cuda.pybind.geometry.TriangleMesh
        """
    @staticmethod
    def create_coordinate_frame(size: float = 1.0, origin: numpy.ndarray = ...) -> TriangleMesh:
        """
        Factory function to create a coordinate frame mesh. The coordinate frame will be centered at ``origin``. The x, y, z axis will be rendered as red, green, and blue arrows respectively.
        
        Args:
            size (float, optional, default=1.0): The size of the coordinate frame.
            origin (numpy.ndarray[numpy.float64[3, 1]], optional, default=array([0., 0., 0.])): The origin of the coordinate frame.
        
        Returns:
            open3d.cuda.pybind.geometry.TriangleMesh
        """
    @staticmethod
    def create_cylinder(radius: float = 1.0, height: float = 2.0, resolution: int = 20, split: int = 4, create_uv_map: bool = False) -> TriangleMesh:
        """
        Factory function to create a cylinder mesh.
        
        Args:
            radius (float, optional, default=1.0): The radius of the cylinder.
            height (float, optional, default=2.0): The height of the cylinder. The axis of the cylinder will be from (0, 0, -height/2) to (0, 0, height/2).
            resolution (int, optional, default=20):  The circle will be split into ``resolution`` segments
            split (int, optional, default=4): The ``height`` will be split into ``split`` segments.
            create_uv_map (bool, optional, default=False): Add default uv map to the mesh.
        
        Returns:
            open3d.cuda.pybind.geometry.TriangleMesh
        """
    @staticmethod
    def create_from_oriented_bounding_box(obox: OrientedBoundingBox, scale: numpy.ndarray = ..., create_uv_map: bool = False) -> TriangleMesh:
        """
        Factory function to create a solid oriented bounding box.
        
        Args:
            obox (open3d.cuda.pybind.geometry.OrientedBoundingBox): OrientedBoundingBox object to create mesh of.
            scale (numpy.ndarray[numpy.float64[3, 1]], optional, default=array([1., 1., 1.])): scale factor along each direction of OrientedBoundingBox
            create_uv_map (bool, optional, default=False): Add default uv map to the mesh.
        
        Returns:
            open3d.cuda.pybind.geometry.TriangleMesh
        """
    @staticmethod
    @typing.overload
    def create_from_point_cloud_alpha_shape(pcd: PointCloud, alpha: float) -> TriangleMesh:
        """
            Alpha shapes are a generalization of the convex hull. With decreasing alpha value the shape schrinks and creates cavities. See Edelsbrunner and Muecke, "Three-Dimensional Alpha Shapes", 1994.
        
        Args:
            pcd (open3d.cuda.pybind.geometry.PointCloud): PointCloud from which the TriangleMesh surface is reconstructed.
            alpha (float): Parameter to control the shape. A very big value will give a shape close to the convex hull.
        
        Returns:
            open3d.cuda.pybind.geometry.TriangleMesh
        """
    @staticmethod
    @typing.overload
    def create_from_point_cloud_alpha_shape(pcd: PointCloud, alpha: float, tetra_mesh: TetraMesh, pt_map: list[int]) -> TriangleMesh:
        """
            Alpha shapes are a generalization of the convex hull. With decreasing alpha value the shape shrinks and creates cavities. See Edelsbrunner and Muecke, "Three-Dimensional Alpha Shapes", 1994.
        
        Args:
            pcd (open3d.cuda.pybind.geometry.PointCloud): PointCloud from which the TriangleMesh surface is reconstructed.
            alpha (float): Parameter to control the shape. A very big value will give a shape close to the convex hull.
            tetra_mesh (open3d.cuda.pybind.geometry.TetraMesh): If not None, than uses this to construct the alpha shape. Otherwise, TetraMesh is computed from pcd.
            pt_map (list[int]): Optional map from tetra_mesh vertex indices to pcd points.
        
        Returns:
            open3d.cuda.pybind.geometry.TriangleMesh
        """
    @staticmethod
    def create_from_point_cloud_ball_pivoting(pcd: PointCloud, radii: open3d.cuda.pybind.utility.DoubleVector) -> TriangleMesh:
        """
        Function that computes a triangle mesh from a oriented PointCloud. This implements the Ball Pivoting algorithm proposed in F. Bernardini et al., "The ball-pivoting algorithm for surface reconstruction", 1999. The implementation is also based on the algorithms outlined in Digne, "An Analysis and Implementation of a Parallel Ball Pivoting Algorithm", 2014. The surface reconstruction is done by rolling a ball with a given radius over the point cloud, whenever the ball touches three points a triangle is created.
        
        Args:
            pcd (open3d.cuda.pybind.geometry.PointCloud): PointCloud from which the TriangleMesh surface is reconstructed. Has to contain normals.
            radii (open3d.cuda.pybind.utility.DoubleVector): The radii of the ball that are used for the surface reconstruction.
        
        Returns:
            open3d.cuda.pybind.geometry.TriangleMesh
        """
    @staticmethod
    def create_from_point_cloud_poisson(pcd: PointCloud, depth: int = 8, width: float = 0, scale: float = 1.1, linear_fit: bool = False, n_threads: int = -1) -> tuple[TriangleMesh, open3d.cuda.pybind.utility.DoubleVector]:
        """
        Function that computes a triangle mesh from a oriented PointCloud pcd. This implements the Screened Poisson Reconstruction proposed in Kazhdan and Hoppe, "Screened Poisson Surface Reconstruction", 2013. This function uses the original implementation by Kazhdan. See https://github.com/mkazhdan/PoissonRecon
        
        Args:
            pcd (open3d.cuda.pybind.geometry.PointCloud): PointCloud from which the TriangleMesh surface is reconstructed. Has to contain normals.
            depth (int, optional, default=8): Maximum depth of the tree that will be used for surface reconstruction. Running at depth d corresponds to solving on a grid whose resolution is no larger than 2^d x 2^d x 2^d. Note that since the reconstructor adapts the octree to the sampling density, the specified reconstruction depth is only an upper bound.
            width (float, optional, default=0): Specifies the target width of the finest level octree cells. This parameter is ignored if depth is specified
            scale (float, optional, default=1.1): Specifies the ratio between the diameter of the cube used for reconstruction and the diameter of the samples' bounding cube.
            linear_fit (bool, optional, default=False): If true, the reconstructor will use linear interpolation to estimate the positions of iso-vertices.
            n_threads (int, optional, default=-1): Number of threads used for reconstruction. Set to -1 to automatically determine it.
        
        Returns:
            tuple[open3d.cuda.pybind.geometry.TriangleMesh, open3d.cuda.pybind.utility.DoubleVector]
        """
    @staticmethod
    def create_icosahedron(radius: float = 1.0, create_uv_map: bool = False) -> TriangleMesh:
        """
        Factory function to create a icosahedron. The centroid of the mesh will be placed at (0, 0, 0) and the vertices have a distance of radius to the center.
        
        Args:
            radius (float, optional, default=1.0): Distance from centroid to mesh vetices.
            create_uv_map (bool, optional, default=False): Add default uv map to the mesh.
        
        Returns:
            open3d.cuda.pybind.geometry.TriangleMesh
        """
    @staticmethod
    def create_mobius(length_split: int = 70, width_split: int = 15, twists: int = 1, raidus: float = 1, flatness: float = 1, width: float = 1, scale: float = 1) -> TriangleMesh:
        """
        Factory function to create a Mobius strip.
        
        Args:
            length_split (int, optional, default=70): The number of segments along the Mobius strip.
            width_split (int, optional, default=15): The number of segments along the width of the Mobius strip.
            twists (int, optional, default=1): Number of twists of the Mobius strip.
            raidus (float, optional, default=1)
            flatness (float, optional, default=1): Controls the flatness/height of the Mobius strip.
            width (float, optional, default=1): Width of the Mobius strip.
            scale (float, optional, default=1): Scale the complete Mobius strip.
        
        Returns:
            open3d.cuda.pybind.geometry.TriangleMesh
        """
    @staticmethod
    def create_octahedron(radius: float = 1.0, create_uv_map: bool = False) -> TriangleMesh:
        """
        Factory function to create a octahedron. The centroid of the mesh will be placed at (0, 0, 0) and the vertices have a distance of radius to the center.
        
        Args:
            radius (float, optional, default=1.0): Distance from centroid to mesh vetices.
            create_uv_map (bool, optional, default=False): Add default uv map to the mesh.
        
        Returns:
            open3d.cuda.pybind.geometry.TriangleMesh
        """
    @staticmethod
    def create_sphere(radius: float = 1.0, resolution: int = 20, create_uv_map: bool = False) -> TriangleMesh:
        """
        Factory function to create a sphere mesh centered at (0, 0, 0).
        
        Args:
            radius (float, optional, default=1.0): The radius of the sphere.
            resolution (int, optional, default=20): The resolution of the sphere. The longitues will be split into ``resolution`` segments (i.e. there are ``resolution + 1`` latitude lines including the north and south pole). The latitudes will be split into ```2 * resolution`` segments (i.e. there are ``2 * resolution`` longitude lines.)
            create_uv_map (bool, optional, default=False): Add default uv map to the mesh.
        
        Returns:
            open3d.cuda.pybind.geometry.TriangleMesh
        """
    @staticmethod
    def create_tetrahedron(radius: float = 1.0, create_uv_map: bool = False) -> TriangleMesh:
        """
        Factory function to create a tetrahedron. The centroid of the mesh will be placed at (0, 0, 0) and the vertices have a distance of radius to the center.
        
        Args:
            radius (float, optional, default=1.0): Distance from centroid to mesh vetices.
            create_uv_map (bool, optional, default=False): Add default uv map to the mesh.
        
        Returns:
            open3d.cuda.pybind.geometry.TriangleMesh
        """
    @staticmethod
    def create_torus(torus_radius: float = 1.0, tube_radius: float = 0.5, radial_resolution: int = 30, tubular_resolution: int = 20) -> TriangleMesh:
        """
        Factory function to create a torus mesh.
        
        Args:
            torus_radius (float, optional, default=1.0): The radius from the center of the torus to the center of the tube.
            tube_radius (float, optional, default=0.5): The radius of the torus tube.
            radial_resolution (int, optional, default=30): The number of segments along the radial direction.
            tubular_resolution (int, optional, default=20): The number of segments along the tubular direction.
        
        Returns:
            open3d.cuda.pybind.geometry.TriangleMesh
        """
    def __add__(self, arg0: TriangleMesh) -> TriangleMesh:
        ...
    def __copy__(self) -> TriangleMesh:
        ...
    def __deepcopy__(self, arg0: dict) -> TriangleMesh:
        ...
    def __iadd__(self, arg0: TriangleMesh) -> TriangleMesh:
        ...
    @typing.overload
    def __init__(self) -> None:
        """
        Default constructor
        """
    @typing.overload
    def __init__(self, arg0: TriangleMesh) -> None:
        """
        Copy constructor
        """
    @typing.overload
    def __init__(self, vertices: open3d.cuda.pybind.utility.Vector3dVector, triangles: open3d.cuda.pybind.utility.Vector3iVector) -> None:
        """
        Create a triangle mesh from vertices and triangle indices
        """
    def __repr__(self) -> str:
        ...
    def cluster_connected_triangles(self) -> tuple[open3d.cuda.pybind.utility.IntVector, list[int], open3d.cuda.pybind.utility.DoubleVector]:
        """
        Function that clusters connected triangles, i.e., triangles that are connected via edges are assigned the same cluster index. This function returns an array that contains the cluster index per triangle, a second array contains the number of triangles per cluster, and a third vector contains the surface area per cluster.
        
        Returns:
            tuple[open3d.cuda.pybind.utility.IntVector, list[int], open3d.cuda.pybind.utility.DoubleVector]
        """
    def compute_adjacency_list(self) -> TriangleMesh:
        """
        Function to compute adjacency list, call before adjacency list is needed
        
        Returns:
            open3d.cuda.pybind.geometry.TriangleMesh
        """
    def compute_convex_hull(self) -> tuple[TriangleMesh, list[int]]:
        """
        Computes the convex hull of the triangle mesh.
        
        Returns:
            tuple[open3d.cuda.pybind.geometry.TriangleMesh, list[int]]
        """
    def compute_triangle_normals(self, normalized: bool = True) -> TriangleMesh:
        """
        Function to compute triangle normals, usually called before rendering
        
        Args:
            normalized (bool, optional, default=True)
        
        Returns:
            open3d.cuda.pybind.geometry.TriangleMesh
        """
    def compute_vertex_normals(self, normalized: bool = True) -> TriangleMesh:
        """
        Function to compute vertex normals, usually called before rendering
        
        Args:
            normalized (bool, optional, default=True)
        
        Returns:
            open3d.cuda.pybind.geometry.TriangleMesh
        """
    @typing.overload
    def crop(self, bounding_box: AxisAlignedBoundingBox) -> TriangleMesh:
        """
            Function to crop input TriangleMesh into output TriangleMesh
        
        Args:
            bounding_box (open3d.cuda.pybind.geometry.AxisAlignedBoundingBox): AxisAlignedBoundingBox to crop points
        
        Returns:
            open3d.cuda.pybind.geometry.TriangleMesh
        """
    @typing.overload
    def crop(self, bounding_box: OrientedBoundingBox) -> TriangleMesh:
        """
            Function to crop input TriangleMesh into output TriangleMesh
        
        Args:
            bounding_box (open3d.cuda.pybind.geometry.OrientedBoundingBox): AxisAlignedBoundingBox to crop points
        
        Returns:
            open3d.cuda.pybind.geometry.TriangleMesh
        """
    def deform_as_rigid_as_possible(self, constraint_vertex_indices: open3d.cuda.pybind.utility.IntVector, constraint_vertex_positions: open3d.cuda.pybind.utility.Vector3dVector, max_iter: int, energy: DeformAsRigidAsPossibleEnergy = ..., smoothed_alpha: float = 0.01) -> TriangleMesh:
        """
        This function deforms the mesh using the method by Sorkine and Alexa, 'As-Rigid-As-Possible Surface Modeling', 2007
        
        Args:
            constraint_vertex_indices (open3d.cuda.pybind.utility.IntVector): Indices of the triangle vertices that should be constrained by the vertex positions in constraint_vertex_positions.
            constraint_vertex_positions (open3d.cuda.pybind.utility.Vector3dVector): Vertex positions used for the constraints.
            max_iter (int): Maximum number of iterations to minimize energy functional.
            energy (open3d.cuda.pybind.geometry.DeformAsRigidAsPossibleEnergy, optional, default=DeformAsRigidAsPossibleEnergy.Spokes): Energy model that is minimized in the deformation process
            smoothed_alpha (float, optional, default=0.01): trade-off parameter for the smoothed energy functional for the regularization term.
        
        Returns:
            open3d.cuda.pybind.geometry.TriangleMesh
        """
    def euler_poincare_characteristic(self) -> int:
        """
        Function that computes the Euler-Poincaré characteristic, i.e., V + F - E, where V is the number of vertices, F is the number of triangles, and E is the number of edges.
        
        Returns:
            int
        """
    def filter_sharpen(self, number_of_iterations: int = 1, strength: float = 1, filter_scope: FilterScope = ...) -> TriangleMesh:
        """
        Function to sharpen triangle mesh. The output value (:math:`v_o`) is the input value (:math:`v_i`) plus strength times the input value minus he sum of he adjacent values. :math:`v_o = v_i x strength (v_i * |N| - \\sum_{n \\in N} v_n)`
        
        Args:
            number_of_iterations (int, optional, default=1):  Number of repetitions of this operation
            strength (float, optional, default=1): Filter parameter.
            filter_scope (open3d.cuda.pybind.geometry.FilterScope, optional, default=FilterScope.All)
        
        Returns:
            open3d.cuda.pybind.geometry.TriangleMesh
        """
    def filter_smooth_laplacian(self, number_of_iterations: int = 1, lambda_filter: float = 0.5, filter_scope: FilterScope = ...) -> TriangleMesh:
        """
        Function to smooth triangle mesh using Laplacian. :math:`v_o = v_i \\cdot \\lambda (sum_{n \\in N} w_n v_n - v_i)`, with :math:`v_i` being the input value, :math:`v_o` the output value, :math:`N` is the  set of adjacent neighbours, :math:`w_n` is the weighting of the neighbour based on the inverse distance (closer neighbours have higher weight), and lambda_filter is the smoothing parameter.
        
        Args:
            number_of_iterations (int, optional, default=1):  Number of repetitions of this operation
            lambda_filter (float, optional, default=0.5): Filter parameter.
            filter_scope (open3d.cuda.pybind.geometry.FilterScope, optional, default=FilterScope.All)
        
        Returns:
            open3d.cuda.pybind.geometry.TriangleMesh
        """
    def filter_smooth_simple(self, number_of_iterations: int = 1, filter_scope: FilterScope = ...) -> TriangleMesh:
        """
        Function to smooth triangle mesh with simple neighbour average. :math:`v_o = \\frac{v_i + \\sum_{n \\in N} v_n)}{|N| + 1}`, with :math:`v_i` being the input value, :math:`v_o` the output value, and :math:`N` is the set of adjacent neighbours.
        
        Args:
            number_of_iterations (int, optional, default=1):  Number of repetitions of this operation
            filter_scope (open3d.cuda.pybind.geometry.FilterScope, optional, default=FilterScope.All)
        
        Returns:
            open3d.cuda.pybind.geometry.TriangleMesh
        """
    def filter_smooth_taubin(self, number_of_iterations: int = 1, lambda_filter: float = 0.5, mu: float = -0.53, filter_scope: FilterScope = ...) -> TriangleMesh:
        """
        Function to smooth triangle mesh using method of Taubin, "Curve and Surface Smoothing Without Shrinkage", 1995. Applies in each iteration two times filter_smooth_laplacian, first with filter parameter lambda_filter and second with filter parameter mu as smoothing parameter. This method avoids shrinkage of the triangle mesh.
        
        Args:
            number_of_iterations (int, optional, default=1):  Number of repetitions of this operation
            lambda_filter (float, optional, default=0.5): Filter parameter.
            mu (float, optional, default=-0.53): Filter parameter.
            filter_scope (open3d.cuda.pybind.geometry.FilterScope, optional, default=FilterScope.All)
        
        Returns:
            open3d.cuda.pybind.geometry.TriangleMesh
        """
    def get_non_manifold_edges(self, allow_boundary_edges: bool = True) -> open3d.cuda.pybind.utility.Vector2iVector:
        """
        Get list of non-manifold edges.
        
        Args:
            allow_boundary_edges (bool, optional, default=True): If true, than non-manifold edges are defined as edges with more than two adjacent triangles, otherwise each edge that is not adjacent to two triangles is defined as non-manifold.
        
        Returns:
            open3d.cuda.pybind.utility.Vector2iVector
        """
    def get_non_manifold_vertices(self) -> open3d.cuda.pybind.utility.IntVector:
        """
        Returns a list of indices to non-manifold vertices.
        
        Returns:
            open3d.cuda.pybind.utility.IntVector
        """
    def get_self_intersecting_triangles(self) -> open3d.cuda.pybind.utility.Vector2iVector:
        """
        Returns a list of indices to triangles that intersect the mesh.
        
        Returns:
            open3d.cuda.pybind.utility.Vector2iVector
        """
    def get_surface_area(self) -> float:
        """
        Function that computes the surface area of the mesh, i.e. the sum of the individual triangle surfaces.
        """
    def get_volume(self) -> float:
        """
        Function that computes the volume of the mesh, under the condition that it is watertight and orientable.
        """
    def has_adjacency_list(self) -> bool:
        """
        Returns ``True`` if the mesh contains adjacency normals.
        
        Returns:
            bool
        """
    def has_textures(self) -> bool:
        """
        Returns ``True`` if the mesh contains a texture image.
        
        Returns:
            bool
        """
    def has_triangle_material_ids(self) -> bool:
        """
        Returns ``True`` if the mesh contains material ids.
        
        Returns:
            bool
        """
    def has_triangle_normals(self) -> bool:
        """
        Returns ``True`` if the mesh contains triangle normals.
        
        Returns:
            bool
        """
    def has_triangle_uvs(self) -> bool:
        """
        Returns ``True`` if the mesh contains uv coordinates.
        
        Returns:
            bool
        """
    def has_triangles(self) -> bool:
        """
        Returns ``True`` if the mesh contains triangles.
        
        Returns:
            bool
        """
    def has_vertex_colors(self) -> bool:
        """
        Returns ``True`` if the mesh contains vertex colors.
        
        Returns:
            bool
        """
    def has_vertex_normals(self) -> bool:
        """
        Returns ``True`` if the mesh contains vertex normals.
        
        Returns:
            bool
        """
    def has_vertices(self) -> bool:
        """
        Returns ``True`` if the mesh contains vertices.
        
        Returns:
            bool
        """
    def is_edge_manifold(self, allow_boundary_edges: bool = True) -> bool:
        """
        Tests if the triangle mesh is edge manifold.
        
        Args:
            allow_boundary_edges (bool, optional, default=True): If true, than non-manifold edges are defined as edges with more than two adjacent triangles, otherwise each edge that is not adjacent to two triangles is defined as non-manifold.
        
        Returns:
            bool
        """
    def is_intersecting(self, arg0: TriangleMesh) -> bool:
        """
        Tests if the triangle mesh is intersecting the other triangle mesh.
        
        Args:
            arg0 (open3d.cuda.pybind.geometry.TriangleMesh)
        
        Returns:
            bool
        """
    def is_orientable(self) -> bool:
        """
        Tests if the triangle mesh is orientable.
        
        Returns:
            bool
        """
    def is_self_intersecting(self) -> bool:
        """
        Tests if the triangle mesh is self-intersecting.
        
        Returns:
            bool
        """
    def is_vertex_manifold(self) -> bool:
        """
        Tests if all vertices of the triangle mesh are manifold.
        
        Returns:
            bool
        """
    def is_watertight(self) -> bool:
        """
        Tests if the triangle mesh is watertight.
        
        Returns:
            bool
        """
    def merge_close_vertices(self, eps: float) -> TriangleMesh:
        """
        Function that will merge close by vertices to a single one. The vertex position, normal and color will be the average of the vertices. The parameter eps defines the maximum distance of close by vertices.  This function might help to close triangle soups.
        
        Args:
            eps (float): Parameter that defines the distance between close vertices.
        
        Returns:
            open3d.cuda.pybind.geometry.TriangleMesh
        """
    def normalize_normals(self) -> TriangleMesh:
        """
        Normalize both triangle normals and vertex normals to length 1.
        
        Returns:
            open3d.cuda.pybind.geometry.TriangleMesh
        """
    def orient_triangles(self) -> bool:
        """
        If the mesh is orientable this function orients all triangles such that all normals point towards the same direction.
        
        Returns:
            bool
        """
    def paint_uniform_color(self, arg0: numpy.ndarray) -> MeshBase:
        """
        Assigns each vertex in the TriangleMesh the same color.
        
        Args:
            arg0 (numpy.ndarray[numpy.float64[3, 1]])
        
        Returns:
            open3d.cuda.pybind.geometry.MeshBase
        """
    def remove_degenerate_triangles(self) -> TriangleMesh:
        """
        Function that removes degenerate triangles, i.e., triangles that references a single vertex multiple times in a single triangle. They are usually the product of removing duplicated vertices.
        
        Returns:
            open3d.cuda.pybind.geometry.TriangleMesh
        """
    def remove_duplicated_triangles(self) -> TriangleMesh:
        """
        Function that removes duplicated triangles, i.e., removes triangles that reference the same three vertices and have the same orientation.
        
        Returns:
            open3d.cuda.pybind.geometry.TriangleMesh
        """
    def remove_duplicated_vertices(self) -> TriangleMesh:
        """
        Function that removes duplicated vertices, i.e., vertices that have identical coordinates.
        
        Returns:
            open3d.cuda.pybind.geometry.TriangleMesh
        """
    def remove_non_manifold_edges(self) -> TriangleMesh:
        """
        Function that removes all non-manifold edges, by successively deleting  triangles with the smallest surface area adjacent to the non-manifold edge until the number of adjacent triangles to the edge is `<= 2`.
        
        Returns:
            open3d.cuda.pybind.geometry.TriangleMesh
        """
    def remove_triangles_by_index(self, triangle_indices: list[int]) -> None:
        """
        This function removes the triangles with index in triangle_indices.  Call remove_unreferenced_vertices to clean up vertices afterwards.
        
        Args:
            triangle_indices (list[int]): 1D array of triangle indices that should be removed from the TriangleMesh.
        
        Returns:
            None
        """
    def remove_triangles_by_mask(self, triangle_mask: list[bool]) -> None:
        """
        This function removes the triangles where triangle_mask is set to true.  Call remove_unreferenced_vertices to clean up vertices afterwards.
        
        Args:
            triangle_mask (list[bool]): 1D bool array, True values indicate triangles that should be removed.
        
        Returns:
            None
        """
    def remove_unreferenced_vertices(self) -> TriangleMesh:
        """
        This function removes vertices from the triangle mesh that are not referenced in any triangle of the mesh.
        
        Returns:
            open3d.cuda.pybind.geometry.TriangleMesh
        """
    def remove_vertices_by_index(self, vertex_indices: list[int]) -> None:
        """
        This function removes the vertices with index in vertex_indices. Note that also all triangles associated with the vertices are removed.
        
        Args:
            vertex_indices (list[int]): 1D array of vertex indices that should be removed from the TriangleMesh.
        
        Returns:
            None
        """
    def remove_vertices_by_mask(self, vertex_mask: list[bool]) -> None:
        """
        This function removes the vertices that are masked in vertex_mask. Note that also all triangles associated with the vertices are removed.
        
        Args:
            vertex_mask (list[bool]): 1D bool array, True values indicate vertices that should be removed.
        
        Returns:
            None
        """
    def sample_points_poisson_disk(self, number_of_points: int, init_factor: float = 5, pcl: PointCloud = None, use_triangle_normal: bool = False) -> PointCloud:
        """
        Function to sample points from the mesh, where each point has approximately the same distance to the neighbouring points (blue noise). Method is based on Yuksel, "Sample Elimination for Generating Poisson Disk Sample Sets", EUROGRAPHICS, 2015.
        
        Args:
            number_of_points (int): Number of points that should be sampled.
            init_factor (float, optional, default=5): Factor for the initial uniformly sampled PointCloud. This init PointCloud is used for sample elimination.
            pcl (open3d.cuda.pybind.geometry.PointCloud, optional, default=None): Initial PointCloud that is used for sample elimination. If this parameter is provided the init_factor is ignored.
            use_triangle_normal (bool, optional, default=False): If True assigns the triangle normals instead of the interpolated vertex normals to the returned points. The triangle normals will be computed and added to the mesh if necessary.
        
        Returns:
            open3d.cuda.pybind.geometry.PointCloud
        """
    def sample_points_uniformly(self, number_of_points: int = 100, use_triangle_normal: bool = False) -> PointCloud:
        """
        Function to uniformly sample points from the mesh.
        
        Args:
            number_of_points (int, optional, default=100): Number of points that should be uniformly sampled.
            use_triangle_normal (bool, optional, default=False): If True assigns the triangle normals instead of the interpolated vertex normals to the returned points. The triangle normals will be computed and added to the mesh if necessary.
        
        Returns:
            open3d.cuda.pybind.geometry.PointCloud
        """
    def select_by_index(self, indices: list[int], cleanup: bool = True) -> TriangleMesh:
        """
        Function to select mesh from input triangle mesh into output triangle mesh. ``input``: The input triangle mesh. ``indices``: Indices of vertices to be selected.
        
        Args:
            indices (list[int]): Indices of vertices to be selected.
            cleanup (bool, optional, default=True): If true calls number of mesh cleanup functions to remove unreferenced vertices and degenerate triangles
        
        Returns:
            open3d.cuda.pybind.geometry.TriangleMesh
        """
    def simplify_quadric_decimation(self, target_number_of_triangles: int, maximum_error: float = ..., boundary_weight: float = 1.0) -> TriangleMesh:
        """
        Function to simplify mesh using Quadric Error Metric Decimation by Garland and Heckbert
        
        Args:
            target_number_of_triangles (int): The number of triangles that the simplified mesh should have. It is not guaranteed that this number will be reached.
            maximum_error (float, optional, default=inf): The maximum error where a vertex is allowed to be merged
            boundary_weight (float, optional, default=1.0): A weight applied to edge vertices used to preserve boundaries
        
        Returns:
            open3d.cuda.pybind.geometry.TriangleMesh
        """
    def simplify_vertex_clustering(self, voxel_size: float, contraction: SimplificationContraction = ...) -> TriangleMesh:
        """
        Function to simplify mesh using vertex clustering.
        
        Args:
            voxel_size (float): The size of the voxel within vertices are pooled.
            contraction (open3d.cuda.pybind.geometry.SimplificationContraction, optional, default=SimplificationContraction.Average): Method to aggregate vertex information. Average computes a simple average, Quadric minimizes the distance to the adjacent planes.
        
        Returns:
            open3d.cuda.pybind.geometry.TriangleMesh
        """
    def subdivide_loop(self, number_of_iterations: int = 1) -> TriangleMesh:
        """
        Function subdivide mesh using Loop's algorithm. Loop, "Smooth subdivision surfaces based on triangles", 1987.
        
        Args:
            number_of_iterations (int, optional, default=1): Number of iterations. A single iteration splits each triangle into four triangles.
        
        Returns:
            open3d.cuda.pybind.geometry.TriangleMesh
        """
    def subdivide_midpoint(self, number_of_iterations: int = 1) -> TriangleMesh:
        """
        Function subdivide mesh using midpoint algorithm.
        
        Args:
            number_of_iterations (int, optional, default=1): Number of iterations. A single iteration splits each triangle into four triangles that cover the same surface.
        
        Returns:
            open3d.cuda.pybind.geometry.TriangleMesh
        """
    @property
    def adjacency_list(self) -> list[set[int]]:
        """
        List of Sets: The set ``adjacency_list[i]`` contains the indices of adjacent vertices of vertex i.
        """
    @adjacency_list.setter
    def adjacency_list(self, arg0: list[set[int]]) -> None:
        ...
    @property
    def textures(self) -> list[Image]:
        """
        open3d.geometry.Image: The texture images.
        """
    @textures.setter
    def textures(self, arg0: list[Image]) -> None:
        ...
    @property
    def triangle_material_ids(self) -> open3d.cuda.pybind.utility.IntVector:
        """
        `int` array of shape ``(num_trianges, 1)``, use ``numpy.asarray()`` to access data: material index associated with each triangle
        """
    @triangle_material_ids.setter
    def triangle_material_ids(self, arg0: open3d.cuda.pybind.utility.IntVector) -> None:
        ...
    @property
    def triangle_normals(self) -> open3d.cuda.pybind.utility.Vector3dVector:
        """
        ``float64`` array of shape ``(num_triangles, 3)``, use ``numpy.asarray()`` to access data: Triangle normals.
        """
    @triangle_normals.setter
    def triangle_normals(self, arg0: open3d.cuda.pybind.utility.Vector3dVector) -> None:
        ...
    @property
    def triangle_uvs(self) -> open3d.cuda.pybind.utility.Vector2dVector:
        """
        ``float64`` array of shape ``(3 * num_triangles, 2)``, use ``numpy.asarray()`` to access data: List of uvs denoted by the index of points forming the triangle.
        """
    @triangle_uvs.setter
    def triangle_uvs(self, arg0: open3d.cuda.pybind.utility.Vector2dVector) -> None:
        ...
    @property
    def triangles(self) -> open3d.cuda.pybind.utility.Vector3iVector:
        """
        ``int`` array of shape ``(num_triangles, 3)``, use ``numpy.asarray()`` to access data: List of triangles denoted by the index of points forming the triangle.
        """
    @triangles.setter
    def triangles(self, arg0: open3d.cuda.pybind.utility.Vector3iVector) -> None:
        ...
    @property
    def vertex_colors(self) -> open3d.cuda.pybind.utility.Vector3dVector:
        """
        ``float64`` array of shape ``(num_vertices, 3)``, range ``[0, 1]`` , use ``numpy.asarray()`` to access data: RGB colors of vertices.
        """
    @vertex_colors.setter
    def vertex_colors(self, arg0: open3d.cuda.pybind.utility.Vector3dVector) -> None:
        ...
    @property
    def vertex_normals(self) -> open3d.cuda.pybind.utility.Vector3dVector:
        """
        ``float64`` array of shape ``(num_vertices, 3)``, use ``numpy.asarray()`` to access data: Vertex normals.
        """
    @vertex_normals.setter
    def vertex_normals(self, arg0: open3d.cuda.pybind.utility.Vector3dVector) -> None:
        ...
    @property
    def vertices(self) -> open3d.cuda.pybind.utility.Vector3dVector:
        """
        ``float64`` array of shape ``(num_vertices, 3)``, use ``numpy.asarray()`` to access data: Vertex coordinates.
        """
    @vertices.setter
    def vertices(self, arg0: open3d.cuda.pybind.utility.Vector3dVector) -> None:
        ...
class Voxel:
    """
    Base Voxel class, containing grid id and color
    """
    def __copy__(self) -> Voxel:
        ...
    def __deepcopy__(self, arg0: dict) -> Voxel:
        ...
    @typing.overload
    def __init__(self) -> None:
        """
        Default constructor
        """
    @typing.overload
    def __init__(self, arg0: Voxel) -> None:
        """
        Copy constructor
        """
    @typing.overload
    def __init__(self, grid_index: numpy.ndarray) -> None:
        ...
    @typing.overload
    def __init__(self, grid_index: numpy.ndarray, color: numpy.ndarray) -> None:
        ...
    def __repr__(self) -> str:
        ...
    @property
    def color(self) -> numpy.ndarray:
        """
        Float64 numpy array of shape (3,): Color of the voxel.
        """
    @color.setter
    def color(self, arg0: numpy.ndarray) -> None:
        ...
    @property
    def grid_index(self) -> numpy.ndarray:
        """
        Int numpy array of shape (3,): Grid coordinate index of the voxel.
        """
    @grid_index.setter
    def grid_index(self, arg0: numpy.ndarray) -> None:
        ...
class VoxelGrid(Geometry3D):
    """
    VoxelGrid is a collection of voxels which are aligned in grid.
    """
    class VoxelPoolingMode:
        """
        Mode of determining color for each voxel.
        
        Members:
        
          AVG
        
          MIN
        
          MAX
        
          SUM
        """
        AVG: typing.ClassVar[VoxelGrid.VoxelPoolingMode]
        MAX: typing.ClassVar[VoxelGrid.VoxelPoolingMode]
        MIN: typing.ClassVar[VoxelGrid.VoxelPoolingMode]
        SUM: typing.ClassVar[VoxelGrid.VoxelPoolingMode]
        __members__: typing.ClassVar[dict[str, VoxelGrid.VoxelPoolingMode]]
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
    @staticmethod
    def create_dense(origin: numpy.ndarray, color: numpy.ndarray, voxel_size: float, width: float, height: float, depth: float) -> VoxelGrid:
        """
        Creates a voxel grid where every voxel is set (hence dense). This is a useful starting point for voxel carving
        
        Args:
            origin (numpy.ndarray[numpy.float64[3, 1]]): Coordinate center of the VoxelGrid
            color (numpy.ndarray[numpy.float64[3, 1]]): Voxel color for all voxels if the VoxelGrid.
            voxel_size (float): Voxel size of of the VoxelGrid construction.
            width (float): Spatial width extend of the VoxelGrid.
            height (float): Spatial height extend of the VoxelGrid.
            depth (float): Spatial depth extend of the VoxelGrid.
        
        Returns:
            open3d.cuda.pybind.geometry.VoxelGrid
        """
    @staticmethod
    def create_from_point_cloud(input: PointCloud, voxel_size: float, pooling_mode: VoxelGrid.VoxelPoolingMode = ...) -> VoxelGrid:
        """
        Creates a VoxelGrid from a given PointCloud. The color value of a given  voxel is determined by the VoxelPoolingMode, e.g. by default the average color value of the points that fall into it (if the PointCloud has colors). The bounds of the created VoxelGrid are computed from the PointCloud.
        
        Args:
            input (open3d.cuda.pybind.geometry.PointCloud): The input PointCloud
            voxel_size (float): Voxel size of of the VoxelGrid construction.
            pooling_mode (open3d.cuda.pybind.geometry.VoxelGrid.VoxelPoolingMode, optional, default=<VoxelPoolingMode.AVG: 0>): VoxelPoolingMode for determining voxel color.
        
        Returns:
            open3d.cuda.pybind.geometry.VoxelGrid
        """
    @staticmethod
    def create_from_point_cloud_within_bounds(input: PointCloud, voxel_size: float, min_bound: numpy.ndarray, max_bound: numpy.ndarray, pooling_mode: VoxelGrid.VoxelPoolingMode = ...) -> VoxelGrid:
        """
        Creates a VoxelGrid from a given PointCloud. The color value of a given voxel is determined by the VoxelPoolingMode, e.g. by default the average color value of the points that fall into it (if the PointCloud has colors). The bounds of the created VoxelGrid are defined by the given parameters.
        
        Args:
            input (open3d.cuda.pybind.geometry.PointCloud): The input PointCloud
            voxel_size (float): Voxel size of of the VoxelGrid construction.
            min_bound (numpy.ndarray[numpy.float64[3, 1]]): Minimum boundary point for the VoxelGrid to create.
            max_bound (numpy.ndarray[numpy.float64[3, 1]]): Maximum boundary point for the VoxelGrid to create.
            pooling_mode (open3d.cuda.pybind.geometry.VoxelGrid.VoxelPoolingMode, optional, default=<VoxelPoolingMode.AVG: 0>): VoxelPoolingMode that determines how to compute the voxel color.
        
        Returns:
            open3d.cuda.pybind.geometry.VoxelGrid
        """
    @staticmethod
    def create_from_triangle_mesh(input: TriangleMesh, voxel_size: float) -> VoxelGrid:
        """
        Creates a VoxelGrid from a given TriangleMesh. No color information is converted. The bounds of the created VoxelGrid are computed from the  TriangleMesh.
        
        Args:
            input (open3d.cuda.pybind.geometry.TriangleMesh): The input TriangleMesh
            voxel_size (float): Voxel size of of the VoxelGrid construction.
        
        Returns:
            open3d.cuda.pybind.geometry.VoxelGrid
        """
    @staticmethod
    def create_from_triangle_mesh_within_bounds(input: TriangleMesh, voxel_size: float, min_bound: numpy.ndarray, max_bound: numpy.ndarray) -> VoxelGrid:
        """
        Creates a VoxelGrid from a given TriangleMesh. No color information is converted. The bounds of the created VoxelGrid are defined by the given parameters
        
        Args:
            input (open3d.cuda.pybind.geometry.TriangleMesh): The input TriangleMesh
            voxel_size (float): Voxel size of of the VoxelGrid construction.
            min_bound (numpy.ndarray[numpy.float64[3, 1]]): Minimum boundary point for the VoxelGrid to create.
            max_bound (numpy.ndarray[numpy.float64[3, 1]]): Maximum boundary point for the VoxelGrid to create.
        
        Returns:
            open3d.cuda.pybind.geometry.VoxelGrid
        """
    def __add__(self, arg0: VoxelGrid) -> VoxelGrid:
        ...
    def __copy__(self) -> VoxelGrid:
        ...
    def __deepcopy__(self, arg0: dict) -> VoxelGrid:
        ...
    def __iadd__(self, arg0: VoxelGrid) -> VoxelGrid:
        ...
    @typing.overload
    def __init__(self) -> None:
        """
        Default constructor
        """
    @typing.overload
    def __init__(self, arg0: VoxelGrid) -> None:
        """
        Copy constructor
        """
    def __repr__(self) -> str:
        ...
    def add_voxel(self, voxel: Voxel) -> None:
        """
        Add a new voxel into the VoxelGrid.
        
        Args:
            voxel (open3d.cuda.pybind.geometry.Voxel)
        
        Returns:
            None
        """
    def carve_depth_map(self, depth_map: Image, camera_params: open3d.cuda.pybind.camera.PinholeCameraParameters, keep_voxels_outside_image: bool = False) -> VoxelGrid:
        """
        Remove all voxels from the VoxelGrid where none of the boundary points of the voxel projects to depth value that is smaller, or equal than the projected depth of the boundary point. If keep_voxels_outside_image is true then voxels are only carved if all boundary points project to a valid image location.
        
        Args:
            depth_map (open3d.cuda.pybind.geometry.Image): Depth map (Image) used for VoxelGrid carving.
            camera_params (open3d.cuda.pybind.camera.PinholeCameraParameters)
            keep_voxels_outside_image (bool, optional, default=False): retain voxels that don't project to pixels in the image
        
        Returns:
            open3d.cuda.pybind.geometry.VoxelGrid
        """
    def carve_silhouette(self, silhouette_mask: Image, camera_params: open3d.cuda.pybind.camera.PinholeCameraParameters, keep_voxels_outside_image: bool = False) -> VoxelGrid:
        """
        Remove all voxels from the VoxelGrid where none of the boundary points of the voxel projects to a valid mask pixel (pixel value > 0). If keep_voxels_outside_image is true then voxels are only carved if all boundary points project to a valid image location.
        
        Args:
            silhouette_mask (open3d.cuda.pybind.geometry.Image): Silhouette mask (Image) used for VoxelGrid carving.
            camera_params (open3d.cuda.pybind.camera.PinholeCameraParameters)
            keep_voxels_outside_image (bool, optional, default=False): retain voxels that don't project to pixels in the image
        
        Returns:
            open3d.cuda.pybind.geometry.VoxelGrid
        """
    def check_if_included(self, queries: open3d.cuda.pybind.utility.Vector3dVector) -> list[bool]:
        """
        Element-wise check if a query in the list is included in the VoxelGrid. Queries are double precision and are mapped to the closest voxel.
        
        Args:
            queries (open3d.cuda.pybind.utility.Vector3dVector)
        
        Returns:
            list[bool]
        """
    def create_from_octree(self, octree: Octree) -> None:
        """
        Convert from Octree.
        
        Args:
            octree (open3d.cuda.pybind.geometry.Octree): geometry.Octree: The source octree.
        
        Returns:
            None
        """
    def get_voxel(self, point: numpy.ndarray) -> numpy.ndarray:
        """
        Returns voxel index given query point.
        
        Args:
            point (numpy.ndarray[numpy.float64[3, 1]]): The query point.
        
        Returns:
            numpy.ndarray[numpy.int32[3, 1]]
        """
    def get_voxel_bounding_points(self, index: numpy.ndarray) -> open3d.cuda.pybind.utility.Vector3dVector:
        """
        Returns the 8 bounding points of a voxel given its grid index.
        
        Args:
            index (numpy.ndarray[numpy.int32[3, 1]]): The grid index of the query voxel.
        
        Returns:
            open3d.cuda.pybind.utility.Vector3dVector
        """
    def get_voxel_center_coordinate(self, idx: numpy.ndarray) -> numpy.ndarray:
        """
        Returns the center coordinate of a voxel given its grid index.
        
        Args:
            idx (numpy.ndarray[numpy.int32[3, 1]]): The grid index of the query voxel.
        
        Returns:
            numpy.ndarray[numpy.float64[3, 1]]
        """
    def get_voxels(self) -> list[Voxel]:
        """
        Returns List of ``Voxel``: Voxels contained in voxel grid. Changes to the voxels returned from this methodare not reflected in the voxel grid.
        """
    def has_colors(self) -> bool:
        """
        Returns ``True`` if the voxel grid contains voxel colors.
        
        Returns:
            bool
        """
    def has_voxels(self) -> bool:
        """
        Returns ``True`` if the voxel grid contains voxels.
        
        Returns:
            bool
        """
    def remove_voxel(self, idx: numpy.ndarray) -> None:
        """
        Remove a voxel given index.
        
        Args:
            idx (numpy.ndarray[numpy.int32[3, 1]]): The grid index of the target voxel.
        
        Returns:
            None
        """
    def to_octree(self, max_depth: int) -> Octree:
        """
        Convert to Octree.
        
        Args:
            max_depth (int): int: Maximum depth of the octree.
        
        Returns:
            open3d.cuda.pybind.geometry.Octree
        """
    @property
    def origin(self) -> numpy.ndarray:
        """
        ``float64`` vector of length 3: Coordinate of the origin point.
        """
    @origin.setter
    def origin(self, arg0: numpy.ndarray) -> None:
        ...
    @property
    def voxel_size(self) -> float:
        """
        ``float64`` Size of the voxel.
        """
    @voxel_size.setter
    def voxel_size(self, arg0: float) -> None:
        ...
def get_rotation_matrix_from_axis_angle(rotation: numpy.ndarray) -> numpy.ndarray:
    ...
def get_rotation_matrix_from_quaternion(rotation: numpy.ndarray) -> numpy.ndarray:
    ...
def get_rotation_matrix_from_xyz(rotation: numpy.ndarray) -> numpy.ndarray:
    ...
def get_rotation_matrix_from_xzy(rotation: numpy.ndarray) -> numpy.ndarray:
    ...
def get_rotation_matrix_from_yxz(rotation: numpy.ndarray) -> numpy.ndarray:
    ...
def get_rotation_matrix_from_yzx(rotation: numpy.ndarray) -> numpy.ndarray:
    ...
def get_rotation_matrix_from_zxy(rotation: numpy.ndarray) -> numpy.ndarray:
    ...
def get_rotation_matrix_from_zyx(rotation: numpy.ndarray) -> numpy.ndarray:
    ...
All: FilterScope
Average: SimplificationContraction
Color: FilterScope
Gaussian3: ImageFilterType
Gaussian5: ImageFilterType
Gaussian7: ImageFilterType
Normal: FilterScope
Quadric: SimplificationContraction
Smoothed: DeformAsRigidAsPossibleEnergy
Sobel3dx: ImageFilterType
Sobel3dy: ImageFilterType
Spokes: DeformAsRigidAsPossibleEnergy
Vertex: FilterScope
m: typing.TypeVar
n: typing.TypeVar
