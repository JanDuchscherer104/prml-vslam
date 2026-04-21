"""
Tensor-based geometry defining module.
"""
from __future__ import annotations
import numpy
import open3d.cuda.pybind.core
import open3d.cuda.pybind.geometry
import open3d.cuda.pybind.visualization
import open3d.cuda.pybind.visualization.rendering
import typing
__all__: list[str] = ['AxisAlignedBoundingBox', 'ChamferDistance', 'Cubic', 'DrawableGeometry', 'FScore', 'Geometry', 'HausdorffDistance', 'Image', 'InterpType', 'Lanczos', 'LineSet', 'Linear', 'Metric', 'MetricParameters', 'Nearest', 'OrientedBoundingBox', 'PointCloud', 'RGBDImage', 'RaycastingScene', 'Super', 'TensorMap', 'TriangleMesh', 'VectorMetric', 'VoxelBlockGrid']
class AxisAlignedBoundingBox(Geometry, DrawableGeometry):
    """
    A bounding box that is aligned along the coordinate axes and
    has the properties:
    
    - (``min_bound``, ``max_bound``): Lower and upper bounds of the bounding box for all axes. These are tensors with shape (3,) and a common data type and device. The data type can only be ``open3d.core.float32`` (default) or ``open3d.core.float64``. The device of the tensor determines the device of the box.
    - ``color``: Color of the bounding box is a tensor with shape (3,) and a data type ``open3d.core.float32`` (default) or ``open3d.core.float64``. Values can only be in the range [0.0, 1.0].
    """
    @staticmethod
    def create_from_points(points: open3d.cuda.pybind.core.Tensor) -> AxisAlignedBoundingBox:
        """
        Creates the axis-aligned box that encloses the set of points.
        
        Args:
            points (open3d.cuda.pybind.core.Tensor): A list of points with data type of float32 or float64 (N x 3 tensor).
        
        Returns:
            open3d.cuda.pybind.t.geometry.AxisAlignedBoundingBox
        """
    @staticmethod
    def from_legacy(box: open3d.cuda.pybind.geometry.AxisAlignedBoundingBox, dtype: open3d.cuda.pybind.core.Dtype = ..., device: open3d.cuda.pybind.core.Device = ...) -> AxisAlignedBoundingBox:
        """
        Create an AxisAlignedBoundingBox from a legacy Open3D axis-aligned box.
        """
    def __add__(self, arg0: AxisAlignedBoundingBox) -> AxisAlignedBoundingBox:
        """
        Add operation for axis-aligned bounding box.
        The device of ohter box must be the same as the device of the current box.
        """
    def __copy__(self) -> AxisAlignedBoundingBox:
        ...
    def __deepcopy__(self, arg0: dict) -> AxisAlignedBoundingBox:
        ...
    @typing.overload
    def __init__(self, device: open3d.cuda.pybind.core.Device = ...) -> None:
        """
        Construct an empty axis-aligned box on the provided device.
        """
    @typing.overload
    def __init__(self, min_bound: open3d.cuda.pybind.core.Tensor, max_bound: open3d.cuda.pybind.core.Tensor) -> None:
        """
        Construct an axis-aligned box from min/max bound.
        The axis-aligned box will be created on the device of the given bound
        tensor, which must be on the same device and have the same data type.
        """
    @typing.overload
    def __init__(self, arg0: AxisAlignedBoundingBox) -> None:
        """
        Copy constructor
        """
    def __repr__(self) -> str:
        ...
    def clone(self) -> AxisAlignedBoundingBox:
        """
        Returns copy of the axis-aligned box on the same device.
        """
    def cpu(self) -> AxisAlignedBoundingBox:
        """
        Transfer the axis-aligned box to CPU. If the axis-aligned box is already on CPU, no copy will be performed.
        """
    def cuda(self, device_id: int = 0) -> AxisAlignedBoundingBox:
        """
        Transfer the axis-aligned box to a CUDA device. If the axis-aligned box is already on the specified CUDA device, no copy will be performed.
        """
    def get_box_points(self) -> open3d.cuda.pybind.core.Tensor:
        """
        Returns the eight points that define the bounding box. The Return tensor has shape {8, 3} and data type of float32.
        """
    def get_center(self) -> open3d.cuda.pybind.core.Tensor:
        """
        Returns the center for box coordinates.
        """
    def get_extent(self) -> open3d.cuda.pybind.core.Tensor:
        """
        Get the extent/length of the bounding box in x, y, and z dimension.
        """
    def get_half_extent(self) -> open3d.cuda.pybind.core.Tensor:
        """
        Returns the half extent of the bounding box.
        """
    def get_max_extent(self) -> float:
        """
        Returns the maximum extent, i.e. the maximum of X, Y and Z axis's extents.
        """
    def get_oriented_bounding_box(self) -> OrientedBoundingBox:
        """
        Convert to an oriented box.
        """
    def get_point_indices_within_bounding_box(self, points: open3d.cuda.pybind.core.Tensor) -> open3d.cuda.pybind.core.Tensor:
        """
        Indices to points that are within the bounding box.
        
        Args:
            points (open3d.cuda.pybind.core.Tensor): Tensor with {N, 3} shape, and type float32 or float64.
        
        Returns:
            open3d.cuda.pybind.core.Tensor
        """
    def scale(self, scale: float, center: open3d.cuda.pybind.core.Tensor | None = None) -> AxisAlignedBoundingBox:
        """
        Scale the axis-aligned
        box.
        If \\f$mi\\f$ is the min_bound and \\f$ma\\f$ is the max_bound of the axis aligned
        bounding box, and \\f$s\\f$ and \\f$c\\f$ are the provided scaling factor and
        center respectively, then the new min_bound and max_bound are given by
        \\f$mi = c + s (mi - c)\\f$ and \\f$ma = c + s (ma - c)\\f$.
        The scaling center will be the box center if it is not specified.
        
        Args:
            scale (float): The scale parameter.
            center (Optional[open3d.cuda.pybind.core.Tensor], optional, default=None): Center used for the scaling operation. Tensor with {3,} shape, and type float32 or float64
        
        Returns:
            open3d.cuda.pybind.t.geometry.AxisAlignedBoundingBox
        """
    def set_color(self, color: open3d.cuda.pybind.core.Tensor) -> None:
        """
        Set the color of the axis-aligned box.
        
        Args:
            color (open3d.cuda.pybind.core.Tensor): Tensor with {3,} shape, and type float32 or float64, with values in range [0.0, 1.0].
        
        Returns:
            None
        """
    def set_max_bound(self, max_bound: open3d.cuda.pybind.core.Tensor) -> None:
        """
        Set the upper bound of the axis-aligned box.
        
        Args:
            max_bound (open3d.cuda.pybind.core.Tensor): Tensor with {3,} shape, and type float32 or float64.
        
        Returns:
            None
        """
    def set_min_bound(self, min_bound: open3d.cuda.pybind.core.Tensor) -> None:
        """
        Set the lower bound of the axis-aligned box.
        
        Args:
            min_bound (open3d.cuda.pybind.core.Tensor): Tensor with {3,} shape, and type float32 or float64.
        
        Returns:
            None
        """
    def to(self, device: open3d.cuda.pybind.core.Device, copy: bool = False) -> AxisAlignedBoundingBox:
        """
        Transfer the axis-aligned box to a specified device.
        """
    def to_legacy(self) -> open3d.cuda.pybind.geometry.AxisAlignedBoundingBox:
        """
        Convert to a legacy Open3D axis-aligned box.
        """
    def translate(self, translation: open3d.cuda.pybind.core.Tensor, relative: bool = True) -> AxisAlignedBoundingBox:
        """
        Translate the
        axis-aligned box by the given translation. If relative is true, the translation
        is applied to the current min and max bound. If relative is false, the
        translation is applied to make the box's center at the given translation.
        
        Args:
            translation (open3d.cuda.pybind.core.Tensor): Translation tensor of shape (3,), type float32 or float64, device same as the box.
            relative (bool, optional, default=True): Whether to perform relative translation.
        
        Returns:
            open3d.cuda.pybind.t.geometry.AxisAlignedBoundingBox
        """
    def volume(self) -> float:
        """
        Returns the volume of the bounding box.
        """
    @property
    def color(self) -> open3d.cuda.pybind.core.Tensor:
        """
        Returns the color for box.
        """
    @property
    def dtype(self) -> open3d.cuda.pybind.core.Dtype:
        """
        Returns the data type attribute of this AxisAlignedBoundingBox.
        """
    @property
    def max_bound(self) -> open3d.cuda.pybind.core.Tensor:
        """
        Returns the max bound for box coordinates.
        """
    @property
    def min_bound(self) -> open3d.cuda.pybind.core.Tensor:
        """
        Returns the min bound for box coordinates.
        """
class DrawableGeometry:
    """
    Base class for geometry types which can be visualized.
    """
    material: open3d.cuda.pybind.visualization.Material
    def has_valid_material(self) -> bool:
        """
        Returns true if the geometry's material is valid.
        """
class Geometry:
    """
    The base geometry class.
    """
    def clear(self) -> Geometry:
        """
        Clear all elements in the geometry.
        
        Returns:
            open3d.cuda.pybind.t.geometry.Geometry
        """
    def is_empty(self) -> bool:
        """
        Returns ``True`` iff the geometry is empty.
        
        Returns:
            bool
        """
    @property
    def device(self) -> open3d.cuda.pybind.core.Device:
        """
        Returns the device of the geometry.
        """
    @property
    def is_cpu(self) -> bool:
        """
        Returns true if the geometry is on CPU.
        """
    @property
    def is_cuda(self) -> bool:
        """
        Returns true if the geometry is on CUDA.
        """
class Image(Geometry):
    """
    The Image class stores image with customizable rols, cols, channels, dtype and device.
    """
    @staticmethod
    def from_legacy(image_legacy: open3d.cuda.pybind.geometry.Image, device: open3d.cuda.pybind.core.Device = ...) -> Image:
        """
        Create a Image from a legacy Open3D Image.
        """
    def __copy__(self) -> Image:
        ...
    def __deepcopy__(self, arg0: dict) -> Image:
        ...
    def __getstate__(self) -> tuple:
        ...
    @typing.overload
    def __init__(self, rows: int = 0, cols: int = 0, channels: int = 1, dtype: open3d.cuda.pybind.core.Dtype = ..., device: open3d.cuda.pybind.core.Device = ...) -> None:
        """
        Row-major storage is used, similar to OpenCV. Use (row, col, channel) indexing order for image creation and accessing. In general, (r, c, ch) are the preferred variable names for consistency, and avoid using width, height, u, v, x, y for coordinates.
        """
    @typing.overload
    def __init__(self, tensor: open3d.cuda.pybind.core.Tensor) -> None:
        """
        Construct from a tensor. The tensor won't be copied and memory will be shared.
        """
    @typing.overload
    def __init__(self, arg0: Image) -> None:
        """
        Copy constructor
        """
    def __repr__(self) -> str:
        ...
    def __setstate__(self, arg0: tuple) -> None:
        ...
    def as_tensor(self) -> open3d.cuda.pybind.core.Tensor:
        ...
    def clear(self) -> Image:
        """
        Clear stored data.
        
        Returns:
            open3d.cuda.pybind.t.geometry.Image
        """
    def clip_transform(self, scale: float, min_value: float, max_value: float, clip_fill: float = 0.0) -> Image:
        """
        Preprocess a image of shape (rows, cols, channels=1), typically used for a depth image. UInt16 and Float32 Dtypes supported. Each pixel will be transformed by
        x = x / scale
        x = x < min_value ? clip_fill : x
        x = x > max_value ? clip_fill : x
        Use INF, NAN or 0.0 (default) for clip_fill
        """
    def clone(self) -> Image:
        """
        Returns a copy of the Image on the same device.
        """
    def colorize_depth(self, scale: float, min_value: float, max_value: float) -> Image:
        """
        Colorize an input depth image (with Dtype UInt16 or Float32). The image values are divided by scale, then clamped within (min_value, max_value) and finally converted to a 3 channel UInt8 RGB image using the Turbo colormap as a lookup table.
        """
    def cpu(self) -> Image:
        """
        Transfer the image to CPU. If the image is already on CPU, no copy will be performed.
        """
    def create_normal_map(self, invalid_fill: float = 0.0) -> Image:
        """
        Create a normal map of shape (rows, cols, channels=3) in Float32 from a vertex map of shape (rows, cols, channels=1) in Float32 using cross product of V(r, c+1)-V(r, c) and V(r+1, c)-V(r, c). The input vertex map is expected to be the output of create_vertex_map. You may need to start with a filtered depth  image (e.g. with filter_bilateral) to obtain good results.
        """
    def create_vertex_map(self, intrinsics: open3d.cuda.pybind.core.Tensor, invalid_fill: float = 0.0) -> Image:
        """
        Create a vertex map of shape (rows, cols, channels=3) in Float32 from an image of shape (rows, cols, channels=1) in Float32 using unprojection. The input depth is expected to be the output of clip_transform.
        """
    def cuda(self, device_id: int = 0) -> Image:
        """
        Transfer the image to a CUDA device. If the image is already on the specified CUDA device, no copy will be performed.
        """
    def dilate(self, kernel_size: int = 3) -> Image:
        """
        Return a new image after performing morphological dilation. Supported datatypes are UInt8, UInt16 and Float32 with {1, 3, 4} channels. An 8-connected neighborhood is used to create the dilation mask.
        """
    def filter(self, kernel: open3d.cuda.pybind.core.Tensor) -> Image:
        """
        Return a new image after filtering with the given kernel.
        """
    def filter_bilateral(self, kernel_size: int = 3, value_sigma: float = 20.0, dist_sigma: float = 10.0) -> Image:
        """
        Return a new image after bilateral filtering.Note: CPU (IPP) and CUDA (NPP) versions are inconsistent: CPU uses a round kernel (radius = floor(kernel_size / 2)), while CUDA uses a square kernel (width = kernel_size). Make sure to tune parameters accordingly.
        """
    def filter_gaussian(self, kernel_size: int = 3, sigma: float = 1.0) -> Image:
        """
        Return a new image after Gaussian filtering. Possible kernel_size: odd numbers >= 3 are supported.
        """
    def filter_sobel(self, kernel_size: int = 3) -> tuple[Image, Image]:
        """
        Return a pair of new gradient images (dx, dy) after Sobel filtering. Possible kernel_size: 3 and 5.
        """
    def get_max_bound(self) -> open3d.cuda.pybind.core.Tensor:
        """
        Compute max 2D coordinates for the data ({rows, cols}).
        
        Returns:
            open3d.cuda.pybind.core.Tensor
        """
    def get_min_bound(self) -> open3d.cuda.pybind.core.Tensor:
        """
        Compute min 2D coordinates for the data (always {0, 0}).
        
        Returns:
            open3d.cuda.pybind.core.Tensor
        """
    def is_empty(self) -> bool:
        """
        Is any data stored?
        
        Returns:
            bool
        """
    def linear_transform(self, scale: float = 1.0, offset: float = 0.0) -> Image:
        """
        Function to linearly transform pixel intensities in place: image = scale * image + offset.
        
        Args:
            scale (float, optional, default=1.0): First multiply image pixel values with this factor. This should be positive for unsigned dtypes.
            offset (float, optional, default=0.0): Then add this factor to all image pixel values.
        
        Returns:
            open3d.cuda.pybind.t.geometry.Image
        """
    def pyrdown(self) -> Image:
        """
        Return a new downsampled image with pyramid downsampling formed by a chained Gaussian filter (kernel_size = 5, sigma = 1.0) and a resize (ratio = 0.5) operation.
        """
    def resize(self, sampling_rate: float = 0.5, interp_type: InterpType = ...) -> Image:
        """
        Return a new image after resizing with specified interpolation type. Downsample if sampling rate is < 1. Upsample if sampling rate > 1. Aspect ratio is always kept.
        """
    def rgb_to_gray(self) -> Image:
        """
        Converts a 3-channel RGB image to a new 1-channel Grayscale image by I = 0.299 * R + 0.587 * G + 0.114 * B.
        """
    @typing.overload
    def to(self, device: open3d.cuda.pybind.core.Device, copy: bool = False) -> Image:
        """
            Transfer the Image to a specified device.  A new image is always created if copy is true, else it is avoided when the original image is already on the target device.
        
        Args:
            device (open3d.cuda.pybind.core.Device)
            copy (bool, optional, default=False): If true, a new tensor is always created; if false, the copy is avoided when the original tensor already has the targeted dtype.
        
        Returns:
            open3d.cuda.pybind.t.geometry.Image
        """
    @typing.overload
    def to(self, dtype: open3d.cuda.pybind.core.Dtype, copy: bool = False, scale: float | None = None, offset: float = 0.0) -> Image:
        """
            Returns an Image with the specified Dtype.
        
        Args:
            dtype (open3d.cuda.pybind.core.Dtype): The targeted dtype to convert to.
            copy (bool, optional, default=False): If true, a new tensor is always created; if false, the copy is avoided when the original tensor already has the targeted dtype.
            scale (Optional[float], optional, default=None): Optional scale value. This is 1./255 for UInt8 -> Float{32,64}, 1./65535 for UInt16 -> Float{32,64} and 1 otherwise
            offset (float, optional, default=0.0): Optional shift value. Default 0.
        
        Returns:
            open3d.cuda.pybind.t.geometry.Image
        """
    def to_legacy(self) -> open3d.cuda.pybind.geometry.Image:
        """
        Convert to legacy Image type.
        
        Returns:
            open3d.cuda.pybind.geometry.Image
        """
    @property
    def channels(self) -> int:
        """
        Get the number of channels of the image.
        """
    @property
    def columns(self) -> int:
        """
        Get the number of columns of the image.
        """
    @property
    def device(self) -> open3d.cuda.pybind.core.Device:
        """
        Get the device of the image.
        """
    @property
    def dtype(self) -> open3d.cuda.pybind.core.Dtype:
        """
        Get dtype of the image
        """
    @property
    def rows(self) -> int:
        """
        Get the number of rows of the image.
        """
class InterpType:
    """
    Interpolation type.
    
    Members:
    
      Nearest
    
      Linear
    
      Cubic
    
      Lanczos
    
      Super
    """
    Cubic: typing.ClassVar[InterpType]
    Lanczos: typing.ClassVar[InterpType]
    Linear: typing.ClassVar[InterpType]
    Nearest: typing.ClassVar[InterpType]
    Super: typing.ClassVar[InterpType]
    __members__: typing.ClassVar[dict[str, InterpType]]
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
class LineSet(Geometry, DrawableGeometry):
    """
    
    A LineSet contains points and lines joining them and optionally attributes on
    the points and lines.  The ``LineSet`` class stores the attribute data in
    key-value maps, where the key is the attribute name and value is a Tensor
    containing the attribute data.  There are two maps: one each for ``point``
    and ``line``.
    
    The attributes of the line set have different levels::
    
        import open3d as o3d
    
        dtype_f = o3d.core.float32
        dtype_i = o3d.core.int32
    
        # Create an empty line set
        # Use lineset.point to access the point attributes
        # Use lineset.line to access the line attributes
        lineset = o3d.t.geometry.LineSet()
    
        # Default attribute: point.positions, line.indices
        # These attributes is created by default and are required by all line
        # sets. The shape must be (N, 3) and (N, 2) respectively. The device of
        # "positions" determines the device of the line set.
        lineset.point.positions = o3d.core.Tensor([[0, 0, 0],
                                                      [0, 0, 1],
                                                      [0, 1, 0],
                                                      [0, 1, 1]], dtype_f, device)
        lineset.line.indices = o3d.core.Tensor([[0, 1],
                                                   [1, 2],
                                                   [2, 3],
                                                   [3, 0]], dtype_i, device)
    
        # Common attributes: line.colors
        # Common attributes are used in built-in line set operations. The
        # spellings must be correct. For example, if "color" is used instead of
        # "color", some internal operations that expects "colors" will not work.
        # "colors" must have shape (N, 3) and must be on the same device as the
        # line set.
        lineset.line.colors = o3d.core.Tensor([[0.0, 0.0, 0.0],
                                                  [0.1, 0.1, 0.1],
                                                  [0.2, 0.2, 0.2],
                                                  [0.3, 0.3, 0.3]], dtype_f, device)
    
        # User-defined attributes
        # You can also attach custom attributes. The value tensor must be on the
        # same device as the line set. The are no restrictions on the shape or
        # dtype, e.g.,
        lineset.point.labels = o3d.core.Tensor(...)
        lineset.line.features = o3d.core.Tensor(...)
    """
    @staticmethod
    def create_camera_visualization(view_width_px: int, view_height_px: int, intrinsic: open3d.cuda.pybind.core.Tensor, extrinsic: open3d.cuda.pybind.core.Tensor, scale: float = 1.0, color: open3d.cuda.pybind.core.Tensor = ...) -> LineSet:
        """
        Factory function to create a LineSet from intrinsic and extrinsic
        matrices. Camera reference frame is shown with XYZ axes in RGB.
        
        Args:
            view_width_px (int): The width of the view, in pixels.
            view_height_px (int): The height of the view, in pixels.
            intrinsic (open3d.core.Tensor): The intrinsic matrix {3,3} shape.
            extrinsic (open3d.core.Tensor): The extrinsic matrix {4,4} shape.
            scale (float): camera scale
            color (open3d.core.Tensor): color with float32 and shape {3}. Default is blue.
        
        Example:
        
            Draw a purple camera frame with XYZ axes in RGB::
        
                import open3d.core as o3c
                from open3d.t.geometry import LineSet
                from open3d.visualization import draw
                K = o3c.Tensor([[512, 0, 512], [0, 512, 512], [0, 0, 1]], dtype=o3c.float32)
                T = o3c.Tensor.eye(4, dtype=o3c.float32)
                ls = LineSet.create_camera_visualization(1024, 1024, K, T, 1, [0.8, 0.2, 0.8])
                draw([ls])
        """
    @staticmethod
    def from_legacy(lineset_legacy: open3d.cuda.pybind.geometry.LineSet, float_dtype: open3d.cuda.pybind.core.Dtype = ..., int_dtype: open3d.cuda.pybind.core.Dtype = ..., device: open3d.cuda.pybind.core.Device = ...) -> LineSet:
        """
        Create a LineSet from a legacy Open3D LineSet.
        
        Args:
            lineset_legacy (open3d.cuda.pybind.geometry.LineSet): Legacy Open3D LineSet.
            float_dtype (open3d.cuda.pybind.core.Dtype, optional, default=Float32): Float32 or Float64, used to store floating point values, e.g. points, normals, colors.
            int_dtype (open3d.cuda.pybind.core.Dtype, optional, default=Int64): Int32 or Int64, used to store index values, e.g. line indices.
            device (open3d.cuda.pybind.core.Device, optional, default=CPU:0): The device where the resulting LineSet resides.
        
        Returns:
            open3d.cuda.pybind.t.geometry.LineSet
        """
    def __copy__(self) -> LineSet:
        ...
    def __deepcopy__(self, arg0: dict) -> LineSet:
        ...
    def __getstate__(self) -> tuple:
        ...
    @typing.overload
    def __init__(self, device: open3d.cuda.pybind.core.Device = ...) -> None:
        """
        Construct an empty LineSet on the provided device.
        """
    @typing.overload
    def __init__(self, point_positions: open3d.cuda.pybind.core.Tensor, line_indices: open3d.cuda.pybind.core.Tensor) -> None:
        """
        Construct a LineSet from point_positions and line_indices.
        
        The input tensors will be directly used as the underlying storage of the line
        set (no memory copy).  The resulting ``LineSet`` will have the same ``dtype``
        and ``device`` as the tensor. The device for ``point_positions`` must be consistent with
        ``line_indices``.
        """
    @typing.overload
    def __init__(self, arg0: LineSet) -> None:
        """
        Copy constructor
        """
    def __repr__(self) -> str:
        ...
    def __setstate__(self, arg0: tuple) -> None:
        ...
    def clone(self) -> LineSet:
        """
        Returns copy of the line set on the same device.
        """
    def cpu(self) -> LineSet:
        """
        Transfer the line set to CPU. If the line set is already on CPU, no copy will be performed.
        """
    def cuda(self, device_id: int = 0) -> LineSet:
        """
        Transfer the line set to a CUDA device. If the line set is already on the specified CUDA device, no copy will be performed.
        """
    def extrude_linear(self, vector: open3d.cuda.pybind.core.Tensor, scale: float = 1.0, capping: bool = True) -> TriangleMesh:
        """
        Sweeps the line set along a direction vector.
        
        Args:
            vector (open3d.core.Tensor): The direction vector.
            scale (float): Scalar factor which essentially scales the direction vector.
        
        Returns:
            A triangle mesh with the result of the sweep operation.
        
        
        Example:
            This code generates an L-shaped mesh::
        
                import open3d as o3d
        
                lines = o3d.t.geometry.LineSet([[1.0,0.0,0.0],[0,0,0],[0,0,1]], [[0,1],[1,2]])
                mesh = lines.extrude_linear([0,1,0])
                o3d.visualization.draw([{'name': 'L', 'geometry': mesh}])
        """
    def extrude_rotation(self, angle: float, axis: open3d.cuda.pybind.core.Tensor, resolution: int = 16, translation: float = 0.0, capping: bool = True) -> TriangleMesh:
        """
        Sweeps the line set rotationally about an axis.
        
        Args:
            angle (float): The rotation angle in degree.
            axis (open3d.core.Tensor): The rotation axis.
            resolution (int): The resolution defines the number of intermediate sweeps
                about the rotation axis.
            translation (float): The translation along the rotation axis.
        
        Returns:
            A triangle mesh with the result of the sweep operation.
        
        
        Example:
            This code generates a spring from a single line::
        
                import open3d as o3d
        
                line = o3d.t.geometry.LineSet([[0.7,0,0],[1,0,0]], [[0,1]])
                spring = line.extrude_rotation(3*360, [0,1,0], resolution=3*16, translation=2)
                o3d.visualization.draw([{'name': 'spring', 'geometry': spring}])
        """
    def get_axis_aligned_bounding_box(self) -> AxisAlignedBoundingBox:
        """
        Create an axis-aligned bounding box from point attribute 'positions'.
        """
    def get_center(self) -> open3d.cuda.pybind.core.Tensor:
        """
        Returns the center for point coordinates.
        """
    def get_max_bound(self) -> open3d.cuda.pybind.core.Tensor:
        """
        Returns the max bound for point coordinates.
        """
    def get_min_bound(self) -> open3d.cuda.pybind.core.Tensor:
        """
        Returns the min bound for point coordinates.
        """
    def get_oriented_bounding_box(self) -> OrientedBoundingBox:
        """
        Create an oriented bounding box from point attribute 'positions'.
        """
    def paint_uniform_color(self, color: open3d.cuda.pybind.core.Tensor) -> LineSet:
        """
        Assigns unifom color to all the lines of the LineSet. Floating color values are clipped between 00 and 1.0. Input `color` should be a (3,) shape tensor.
        """
    def rotate(self, R: open3d.cuda.pybind.core.Tensor, center: open3d.cuda.pybind.core.Tensor) -> LineSet:
        """
        Rotate points and lines. Custom attributes (e.g. point normals) are not rotated.
        
        Args:
            R (open3d.cuda.pybind.core.Tensor): Rotation [Tensor of shape (3,3)].
            center (open3d.cuda.pybind.core.Tensor): Center [Tensor of shape (3,)] about which the LineSet is to be rotated. Should be on the same device as the LineSet.
        
        Returns:
            open3d.cuda.pybind.t.geometry.LineSet
        """
    def scale(self, scale: float, center: open3d.cuda.pybind.core.Tensor) -> LineSet:
        """
        Scale points and lines. Custom attributes are not scaled.
        
        Args:
            scale (float): Scale magnitude.
            center (open3d.cuda.pybind.core.Tensor): Center [Tensor of shape (3,)] about which the LineSet is to be scaled. Should be on the same device as the LineSet.
        
        Returns:
            open3d.cuda.pybind.t.geometry.LineSet
        """
    def to(self, device: open3d.cuda.pybind.core.Device, copy: bool = False) -> LineSet:
        """
        Transfer the line set to a specified device.
        """
    def to_legacy(self) -> open3d.cuda.pybind.geometry.LineSet:
        """
        Convert to a legacy Open3D LineSet.
        """
    def transform(self, transformation: open3d.cuda.pybind.core.Tensor) -> LineSet:
        """
        Transforms the points and lines. Custom attributes (e.g. point normals) are not
        transformed. Extracts R, t from the transformation as:
        
        .. math::
            T_{(4,4)} = \\begin{bmatrix} R_{(3,3)} & t_{(3,1)} \\\\
                                    O_{(1,3)} & s_{(1,1)} \\end{bmatrix}
        
        It assumes :math:`s = 1` (no scaling) and :math:`O = [0,0,0]` and applies the
        transformation as :math:`P = R(P) + t`
        
        Args:
            transformation (open3d.cuda.pybind.core.Tensor): Transformation [Tensor of shape (4,4)].  Should be on the same device as the LineSet
        
        Returns:
            open3d.cuda.pybind.t.geometry.LineSet
        """
    def translate(self, translation: open3d.cuda.pybind.core.Tensor, relative: bool = True) -> LineSet:
        """
        Translates points and lines of the LineSet.
        
        Args:
            translation (open3d.cuda.pybind.core.Tensor): Translation tensor of dimension (3,). Should be on the same device as the LineSet
            relative (bool, optional, default=True): If true (default) translates relative to center of LineSet.
        
        Returns:
            open3d.cuda.pybind.t.geometry.LineSet
        """
    @property
    def line(self) -> TensorMap:
        """
        Dictionary containing line attributes. The primary key ``indices`` contains indices of points defining the lines.
        """
    @property
    def point(self) -> TensorMap:
        """
        Dictionary containing point attributes. The primary key ``positions`` contains point positions.
        """
class Metric:
    """
    Enum for metrics for comparing point clouds and triangle meshes.
    
    Members:
    
      ChamferDistance : Chamfer Distance
    
      HausdorffDistance : Hausdorff Distance
    
      FScore : F-Score
    """
    ChamferDistance: typing.ClassVar[Metric]
    FScore: typing.ClassVar[Metric]
    HausdorffDistance: typing.ClassVar[Metric]
    __members__: typing.ClassVar[dict[str, Metric]]
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
class MetricParameters:
    """
    Holder for various parameters required by metrics.
    """
    def __init__(self, fscore_radius: list[float] = [0.009999999776482582], n_sampled_points: int = 1000) -> None:
        ...
    def __repr__(self) -> str:
        ...
    @property
    def fscore_radius(self) -> list[float]:
        """
        Radius for computing the F-Score. A match between a point and its nearest neighbor is sucessful if it is within this radius.
        """
    @fscore_radius.setter
    def fscore_radius(self, arg1: list[float]) -> None:
        ...
    @property
    def n_sampled_points(self) -> int:
        """
        Points are sampled uniformly from the surface of triangle meshes before distance computation. This specifies the number of points sampled. No sampling is done for point clouds.
        """
    @n_sampled_points.setter
    def n_sampled_points(self, arg0: int) -> None:
        ...
class OrientedBoundingBox(Geometry, DrawableGeometry):
    """
    A bounding box oriented along an arbitrary frame of reference
    with the properties:
    
    - (``center``, ``rotation``, ``extent``): The oriented bounding box is defined by its center position (shape (3,)), rotation maxtrix (shape (3,3)) and extent (shape (3,)).  Each of these tensors must have the same data type and device. The data type can only be ``open3d.core.float32`` (default) or ``open3d.core.float64``. The device of the tensor determines the device of the box.
    - ``color``: Color of the bounding box is a tensor with shape (3,) and a data type ``open3d.core.float32`` (default) or ``open3d.core.float64``. Values can only be in the range [0.0, 1.0].
    """
    @staticmethod
    def create_from_axis_aligned_bounding_box(aabb: AxisAlignedBoundingBox) -> OrientedBoundingBox:
        """
        Create an OrientedBoundingBox from a legacy Open3D oriented box.
        
        Args:
            aabb (open3d.cuda.pybind.t.geometry.AxisAlignedBoundingBox): AxisAlignedBoundingBox object from which OrientedBoundingBox is created.
        
        Returns:
            open3d.cuda.pybind.t.geometry.OrientedBoundingBox
        """
    @staticmethod
    def create_from_points(points: open3d.cuda.pybind.core.Tensor, robust: bool = False) -> OrientedBoundingBox:
        """
        Creates an oriented bounding box using a PCA.
        Note that this is only an approximation to the minimum oriented bounding box
        that could be computed for example with O'Rourke's algorithm
        (cf. http://cs.smith.edu/~jorourke/Papers/MinVolBox.pdf, https://www.geometrictools.com/Documentation/MinimumVolumeBox.pdf)
        This is a wrapper for a CPU implementation.
        
        Args:
            points (open3d.cuda.pybind.core.Tensor): A list of points with data type of float32 or float64 (N x 3 tensor, where N must be larger than 3).
            robust (bool, optional, default=False): If set to true uses a more robust method which works in degenerate cases but introduces noise to the points coordinates.
        
        Returns:
            open3d.cuda.pybind.t.geometry.OrientedBoundingBox
        """
    @staticmethod
    def from_legacy(box: open3d.cuda.pybind.geometry.OrientedBoundingBox, dtype: open3d.cuda.pybind.core.Dtype = ..., device: open3d.cuda.pybind.core.Device = ...) -> OrientedBoundingBox:
        """
        Create an oriented bounding box from the AxisAlignedBoundingBox.
        """
    def __copy__(self) -> OrientedBoundingBox:
        ...
    def __deepcopy__(self, arg0: dict) -> OrientedBoundingBox:
        ...
    @typing.overload
    def __init__(self, device: open3d.cuda.pybind.core.Device = ...) -> None:
        """
        Construct an empty OrientedBoundingBox on the provided device.
        """
    @typing.overload
    def __init__(self, center: open3d.cuda.pybind.core.Tensor, rotation: open3d.cuda.pybind.core.Tensor, extent: open3d.cuda.pybind.core.Tensor) -> None:
        """
        Construct an OrientedBoundingBox from center, rotation and extent.
        The OrientedBoundingBox will be created on the device of the given tensors, which
        must be on the same device and have the same data type.
        """
    @typing.overload
    def __init__(self, arg0: OrientedBoundingBox) -> None:
        """
        Copy constructor
        """
    def __repr__(self) -> str:
        ...
    def clone(self) -> OrientedBoundingBox:
        """
        Returns copy of the oriented box on the same device.
        """
    def cpu(self) -> OrientedBoundingBox:
        """
        Transfer the oriented box to CPU. If the oriented box is already on CPU, no copy will be performed.
        """
    def cuda(self, device_id: int = 0) -> OrientedBoundingBox:
        """
        Transfer the oriented box to a CUDA device. If the oriented box is already on the specified CUDA device, no copy will be performed.
        """
    def get_axis_aligned_bounding_box(self) -> AxisAlignedBoundingBox:
        """
         Returns an oriented bounding box from the AxisAlignedBoundingBox.
        """
    def get_box_points(self) -> open3d.cuda.pybind.core.Tensor:
        """
        Returns the eight points that define the bounding box. The Return tensor has shape {8, 3} and data type same as the box.
        """
    def get_max_bound(self) -> open3d.cuda.pybind.core.Tensor:
        """
        Returns the max bound for box.
        """
    def get_min_bound(self) -> open3d.cuda.pybind.core.Tensor:
        """
        Returns the min bound for box.
        """
    def get_point_indices_within_bounding_box(self, points: open3d.cuda.pybind.core.Tensor) -> open3d.cuda.pybind.core.Tensor:
        """
        Indices to points that are within the bounding box.
        
        Args:
            points (open3d.cuda.pybind.core.Tensor): Tensor with {N, 3} shape, and type float32 or float64.
        
        Returns:
            open3d.cuda.pybind.core.Tensor
        """
    def rotate(self, rotation: open3d.cuda.pybind.core.Tensor, center: open3d.cuda.pybind.core.Tensor | None = None) -> OrientedBoundingBox:
        """
        Rotate the oriented box by the given rotation matrix. If the
        rotation matrix is not orthogonal, the rotation will no be applied.
        The rotation center will be the box center if it is not specified.
        
        Args:
            rotation (open3d.cuda.pybind.core.Tensor): Rotation matrix of shape {3, 3}, type float32 or float64, device same as the box.
            center (Optional[open3d.cuda.pybind.core.Tensor], optional, default=None): Center of the rotation, default is null, which means use center of the box as rotation center.
        
        Returns:
            open3d.cuda.pybind.t.geometry.OrientedBoundingBox
        """
    def scale(self, scale: float, center: open3d.cuda.pybind.core.Tensor | None = None) -> OrientedBoundingBox:
        """
        Scale the axis-aligned
        box.
        If \\f$mi\\f$ is the min_bound and \\f$ma\\f$ is the max_bound of the axis aligned
        bounding box, and \\f$s\\f$ and \\f$c\\f$ are the provided scaling factor and
        center respectively, then the new min_bound and max_bound are given by
        \\f$mi = c + s (mi - c)\\f$ and \\f$ma = c + s (ma - c)\\f$.
        The scaling center will be the box center if it is not specified.
        
        Args:
            scale (float): The scale parameter.
            center (Optional[open3d.cuda.pybind.core.Tensor], optional, default=None): Center used for the scaling operation. Tensor with {3,} shape, and type float32 or float64
        
        Returns:
            open3d.cuda.pybind.t.geometry.OrientedBoundingBox
        """
    def set_center(self, center: open3d.cuda.pybind.core.Tensor) -> None:
        """
        Set the center of the box.
        
        Args:
            center (open3d.cuda.pybind.core.Tensor): Tensor with {3,} shape, and type float32 or float64.
        
        Returns:
            None
        """
    def set_color(self, color: open3d.cuda.pybind.core.Tensor) -> None:
        """
        Set the color of the oriented box.
        
        Args:
            color (open3d.cuda.pybind.core.Tensor): Tensor with {3,} shape, and type float32 or float64, with values in range [0.0, 1.0].
        
        Returns:
            None
        """
    def set_extent(self, extent: open3d.cuda.pybind.core.Tensor) -> None:
        """
        Set the extent of the box.
        
        Args:
            extent (open3d.cuda.pybind.core.Tensor): Tensor with {3,} shape, and type float32 or float64.
        
        Returns:
            None
        """
    def set_rotation(self, rotation: open3d.cuda.pybind.core.Tensor) -> None:
        """
        Set the rotation matrix of the box.
        
        Args:
            rotation (open3d.cuda.pybind.core.Tensor): Tensor with {3, 3} shape, and type float32 or float64.
        
        Returns:
            None
        """
    def to(self, device: open3d.cuda.pybind.core.Device, copy: bool = False) -> OrientedBoundingBox:
        """
        Transfer the oriented box to a specified device.
        """
    def to_legacy(self) -> open3d.cuda.pybind.geometry.OrientedBoundingBox:
        """
        Convert to a legacy Open3D oriented box.
        """
    def transform(self, transformation: open3d.cuda.pybind.core.Tensor) -> OrientedBoundingBox:
        """
        Transform the oriented box by the given transformation matrix.
        """
    def translate(self, translation: open3d.cuda.pybind.core.Tensor, relative: bool = True) -> OrientedBoundingBox:
        """
        Translate the
        oriented box by the given translation. If relative is true, the translation is
        added to the center of the box. If false, the center will be assigned to the
        translation.
        
        Args:
            translation (open3d.cuda.pybind.core.Tensor): Translation tensor of shape {3,}, type float32 or float64, device same as the box.
            relative (bool, optional, default=True): Whether to perform relative translation.
        
        Returns:
            open3d.cuda.pybind.t.geometry.OrientedBoundingBox
        """
    def volume(self) -> float:
        """
        Returns the volume of the bounding box.
        """
    @property
    def center(self) -> open3d.cuda.pybind.core.Tensor:
        """
        Returns the center for box.
        """
    @property
    def color(self) -> open3d.cuda.pybind.core.Tensor:
        """
        Returns the color for box.
        """
    @property
    def dtype(self) -> open3d.cuda.pybind.core.Dtype:
        """
        Returns the data type attribute of this OrientedBoundingBox.
        """
    @property
    def extent(self) -> open3d.cuda.pybind.core.Tensor:
        """
        Returns the extent for box coordinates.
        """
    @property
    def rotation(self) -> open3d.cuda.pybind.core.Tensor:
        """
        Returns the rotation for box.
        """
class PointCloud(Geometry, DrawableGeometry):
    """
    
    A point cloud contains a list of 3D points. The point cloud class stores the
    attribute data in key-value maps, where the key is a string representing the
    attribute name and the value is a Tensor containing the attribute data.
    
    The attributes of the point cloud have different levels::
    
        import open3d as o3d
    
        device = o3d.core.Device("CPU:0")
        dtype = o3d.core.float32
    
        # Create an empty point cloud
        # Use pcd.point to access the points' attributes
        pcd = o3d.t.geometry.PointCloud(device)
    
        # Default attribute: "positions".
        # This attribute is created by default and is required by all point clouds.
        # The shape must be (N, 3). The device of "positions" determines the device
        # of the point cloud.
        pcd.point.positions = o3d.core.Tensor([[0, 0, 0],
                                               [1, 1, 1],
                                               [2, 2, 2]], dtype, device)
    
        # Common attributes: "normals", "colors".
        # Common attributes are used in built-in point cloud operations. The
        # spellings must be correct. For example, if "normal" is used instead of
        # "normals", some internal operations that expects "normals" will not work.
        # "normals" and "colors" must have shape (N, 3) and must be on the same
        # device as the point cloud.
        pcd.point.normals = o3d.core.Tensor([[0, 0, 1],
                                             [0, 1, 0],
                                             [1, 0, 0]], dtype, device)
        pcd.point.colors = o3d.core.Tensor([[0.0, 0.0, 0.0],
                                            [0.1, 0.1, 0.1],
                                            [0.2, 0.2, 0.2]], dtype, device)
    
        # User-defined attributes.
        # You can also attach custom attributes. The value tensor must be on the
        # same device as the point cloud. The are no restrictions on the shape and
        # dtype, e.g.,
        pcd.point.intensities = o3d.core.Tensor([0.3, 0.1, 0.4], dtype, device)
        pcd.point.labels = o3d.core.Tensor([3, 1, 4], o3d.core.int32, device)
    """
    @staticmethod
    def create_from_depth_image(*args, **kwargs) -> PointCloud:
        """
        Factory function to create a pointcloud (with only 'points') from a depth image and a camera model.
        
         Given depth value d at (u, v) image coordinate, the corresponding 3d point is:
        
         z = d / depth_scale
        
         x = (u - cx) * z / fx
        
         y = (v - cy) * z / fy
        
        Args:
            depth (open3d.cuda.pybind.t.geometry.Image): The input depth image should be a uint16_t image.
            intrinsics (open3d.cuda.pybind.core.Tensor): Intrinsic parameters of the camera.
            extrinsics (open3d.cuda.pybind.core.Tensor, optional, default=[[1 0 0 0], [0 1 0 0], [0 0 1 0], [0 0 0 1]] Tensor[shape={4, 4}, stride={4, 1}, Float32): Extrinsic parameters of the camera.
             ()
            depth_scale (float, optional, default=1000.0): The depth is scaled by 1 / depth_scale.
            depth_max (float, optional, default=3.0): Truncated at depth_max distance.
            stride (int, optional, default=1): Sampling factor to support coarse point cloud extraction. Unless normals are requested, there is no low pass filtering, so aliasing is possible for stride>1.
            with_normals (bool, optional, default=False): Also compute normals for the point cloud. If True, the point cloud will only contain points with valid normals. If normals are requested, the depth map is first filtered to ensure smooth normals.
        
        Returns:
            open3d.cuda.pybind.t.geometry.PointCloud
        """
    @staticmethod
    def create_from_rgbd_image(*args, **kwargs) -> PointCloud:
        """
        Factory function to create a pointcloud (with properties {'points', 'colors'}) from an RGBD image and a camera model.
        
        Given depth value d at (u, v) image coordinate, the corresponding 3d point is:
        
         z = d / depth_scale
        
         x = (u - cx) * z / fx
        
         y = (v - cy) * z / fy
        
        Args:
            rgbd_image (open3d.cuda.pybind.t.geometry.RGBDImage): The input RGBD image should have a uint16_t depth image and  RGB image with any DType and the same size.
            intrinsics (open3d.cuda.pybind.core.Tensor): Intrinsic parameters of the camera.
            extrinsics (open3d.cuda.pybind.core.Tensor, optional, default=[[1 0 0 0], [0 1 0 0], [0 0 1 0], [0 0 0 1]] Tensor[shape={4, 4}, stride={4, 1}, Float32): Extrinsic parameters of the camera.
             ()
            depth_scale (float, optional, default=1000.0): The depth is scaled by 1 / depth_scale.
            depth_max (float, optional, default=3.0): Truncated at depth_max distance.
            stride (int, optional, default=1): Sampling factor to support coarse point cloud extraction. Unless normals are requested, there is no low pass filtering, so aliasing is possible for stride>1.
            with_normals (bool, optional, default=False): Also compute normals for the point cloud. If True, the point cloud will only contain points with valid normals. If normals are requested, the depth map is first filtered to ensure smooth normals.
        
        Returns:
            open3d.cuda.pybind.t.geometry.PointCloud
        """
    @staticmethod
    def from_legacy(pcd_legacy: open3d.cuda.pybind.geometry.PointCloud, dtype: open3d.cuda.pybind.core.Dtype = ..., device: open3d.cuda.pybind.core.Device = ...) -> PointCloud:
        """
        Create a PointCloud from a legacy Open3D PointCloud.
        """
    @staticmethod
    def orient_normals_to_align_with_direction(*args, **kwargs) -> None:
        """
        Function to orient the normals of a point cloud.
        
        Args:
            orientation_reference (open3d.cuda.pybind.core.Tensor, optional, default=[0 0 1] Tensor[shape={3}, stride={1}, Float32): Normals are oriented with respect to orientation_reference.
             ()
        
        Returns:
            None
        """
    @staticmethod
    def orient_normals_towards_camera_location(*args, **kwargs) -> None:
        """
        Function to orient the normals of a point cloud.
        
        Args:
            camera_location (open3d.cuda.pybind.core.Tensor, optional, default=[0 0 0] Tensor[shape={3}, stride={1}, Float32): Normals are oriented with towards the camera_location.
             ()
        
        Returns:
            None
        """
    def __add__(self, arg0: PointCloud) -> PointCloud:
        ...
    def __copy__(self) -> PointCloud:
        ...
    def __deepcopy__(self, arg0: dict) -> PointCloud:
        ...
    def __getstate__(self) -> tuple:
        ...
    @typing.overload
    def __init__(self, device: open3d.cuda.pybind.core.Device = ...) -> None:
        """
        Construct an empty pointcloud on the provided ``device`` (default: 'CPU:0').
        """
    @typing.overload
    def __init__(self, positions: open3d.cuda.pybind.core.Tensor) -> None:
        ...
    @typing.overload
    def __init__(self, map_keys_to_tensors: dict[str, open3d.cuda.pybind.core.Tensor]) -> None:
        ...
    @typing.overload
    def __init__(self, arg0: PointCloud) -> None:
        """
        Copy constructor
        """
    def __repr__(self) -> str:
        ...
    def __setstate__(self, arg0: tuple) -> None:
        ...
    def append(self, arg0: PointCloud) -> PointCloud:
        ...
    def clone(self) -> PointCloud:
        """
        Returns a copy of the point cloud on the same device.
        """
    def cluster_dbscan(self, eps: float, min_points: int, print_progress: bool = False) -> open3d.cuda.pybind.core.Tensor:
        """
        Cluster PointCloud using the DBSCAN algorithm  Ester et al.,'A
        Density-Based Algorithm for Discovering Clusters in Large Spatial Databases
        with Noise', 1996. This is a wrapper for a CPU implementation and a copy of the
        point cloud data and resulting labels will be made.
        
        Args:
            eps: Density parameter that is used to find neighbouring points.
        
            min_points: Minimum number of points to form a cluster.
        
        print_progress (default False): If 'True' the progress is visualized in the console.
        
        Return:
            A Tensor list of point labels on the same device as the point cloud, -1
            indicates noise according to the algorithm.
        
        Example:
        
            We use Redwood dataset for demonstration::
        
                import matplotlib.pyplot as plt
        
                sample_ply_data = o3d.data.PLYPointCloud()
                pcd = o3d.t.io.read_point_cloud(sample_ply_data.path)
                labels = pcd.cluster_dbscan(eps=0.02, min_points=10, print_progress=True)
        
                max_label = labels.max().item()
                colors = plt.get_cmap("tab20")(
                        labels.numpy() / (max_label if max_label > 0 else 1))
                colors = o3d.core.Tensor(colors[:, :3], o3d.core.float32)
                colors[labels < 0] = 0
                pcd.point.colors = colors
                o3d.visualization.draw([pcd])
        """
    def compute_boundary_points(self, radius: float, max_nn: int = 30, angle_threshold: float = 90.0) -> tuple[PointCloud, open3d.cuda.pybind.core.Tensor]:
        """
        Compute the boundary points of a point cloud.
        The implementation is inspired by the PCL implementation. Reference:
        https://pointclouds.org/documentation/classpcl_1_1_boundary_estimation.html
        
        Args:
            radius: Neighbor search radius parameter.
            max_nn (default 30): Maximum number of neighbors to search.
            angle_threshold (default 90.0): Angle threshold to decide if a point is on the boundary.
        
        Return:
            Tensor of boundary points and its boolean mask tensor.
        
        Example:
            We will load the DemoCropPointCloud dataset, compute its boundary points::
        
                ply_point_cloud = o3d.data.DemoCropPointCloud()
                pcd = o3d.t.io.read_point_cloud(ply_point_cloud.point_cloud_path)
                boundaries, mask = pcd.compute_boundary_points(radius, max_nn)
                boundaries.paint_uniform_color([1.0, 0.0, 0.0])
                o3d.visualization.draw([pcd, boundaries])
        """
    def compute_convex_hull(self, joggle_inputs: bool = False) -> TriangleMesh:
        """
        Compute the convex hull of a triangle mesh using qhull. This runs on the CPU.
        
        Args:
            joggle_inputs (default False): Handle precision problems by randomly perturbing the input data. Set to True if perturbing the input is acceptable but you need convex simplicial output. If False, neighboring facets may be merged in case of precision problems. See `QHull docs <http://www.qhull.org/html/qh-impre.htm#joggle>`__ for more details.
        
        Return:
            TriangleMesh representing the convexh hull. This contains an
            extra vertex property `point_indices` that contains the index of the
            corresponding vertex in the original mesh.
        
        Example:
            We will load the Eagle dataset, compute and display it's convex hull::
        
                eagle = o3d.data.EaglePointCloud()
                pcd = o3d.t.io.read_point_cloud(eagle.path)
                hull = pcd.compute_convex_hull()
                o3d.visualization.draw([{'name': 'eagle', 'geometry': pcd}, {'name': 'convex hull', 'geometry': hull}])
        """
    def compute_metrics(self, pcd2: PointCloud, metrics: list[Metric], params: MetricParameters) -> open3d.cuda.pybind.core.Tensor:
        """
        Compute various metrics between two point clouds. 
                    
        Currently, Chamfer distance, Hausdorff distance and F-Score `[Knapitsch2017] <../tutorial/reference.html#Knapitsch2017>`_ are supported. 
        The Chamfer distance is the sum of the mean distance to the nearest neighbor 
        from the points of the first point cloud to the second point cloud. The F-Score
        at a fixed threshold radius is the harmonic mean of the Precision and Recall. 
        Recall is the percentage of surface points from the first point cloud that have 
        the second point cloud points within the threshold radius, while Precision is 
        the percentage of points from the second point cloud that have the first point 
        cloud points within the threhold radius.
        
        .. math::
            :nowrap:
        
            \\begin{align}
                \\text{Chamfer Distance: } d_{CD}(X,Y) &= \\frac{1}{|X|}\\sum_{i \\in X} || x_i - n(x_i, Y) || + \\frac{1}{|Y|}\\sum_{i \\in Y} || y_i - n(y_i, X) ||\\\\
                \\text{Hausdorff distance: } d_H(X,Y) &= \\max \\left\\{ \\max_{i \\in X} || x_i - n(x_i, Y) ||, \\max_{i \\in Y} || y_i - n(y_i, X) || \\right\\}\\\\
                \\text{Precision: } P(X,Y|d) &= \\frac{100}{|X|} \\sum_{i \\in X} || x_i - n(x_i, Y) || < d \\\\
                \\text{Recall: } R(X,Y|d) &= \\frac{100}{|Y|} \\sum_{i \\in Y} || y_i - n(y_i, X) || < d \\\\
                \\text{F-Score: } F(X,Y|d) &= \\frac{2 P(X,Y|d) R(X,Y|d)}{P(X,Y|d) + R(X,Y|d)} \\\\
            \\end{align}
        
        Args:
            pcd2 (t.geometry.PointCloud): Other point cloud to compare with.
            metrics (Sequence[t.geometry.Metric]): List of Metric s to compute. Multiple metrics can be computed at once for efficiency.
            params (t.geometry.MetricParameters): This holds parameters required by different metrics.
        
        Returns:
            Tensor containing the requested metrics.
        
        Example::
        
            from open3d.t.geometry import TriangleMesh, PointCloud, Metric, MetricParameters
            # box is a cube with one vertex at the origin and a side length 1
            pos = TriangleMesh.create_box().vertex.positions
            pcd1 = PointCloud(pos.clone())
            pcd2 = PointCloud(pos * 1.1)
        
            # (1, 3, 3, 1) vertices are shifted by (0, 0.1, 0.1*sqrt(2), 0.1*sqrt(3))
            # respectively
            metric_params = MetricParameters(
                fscore_radius=o3d.utility.FloatVector((0.01, 0.11, 0.15, 0.18)))
            metrics = pcd1.compute_metrics(
                pcd2, (Metric.ChamferDistance, Metric.HausdorffDistance, Metric.FScore),
                metric_params)
        
            print(metrics)
            np.testing.assert_allclose(
                metrics.cpu().numpy(),
                (0.22436734, np.sqrt(3) / 10, 100. / 8, 400. / 8, 700. / 8, 100.),
                rtol=1e-6)
        """
    def cpu(self) -> PointCloud:
        """
        Transfer the point cloud to CPU. If the point cloud is already on CPU, no copy will be performed.
        """
    @typing.overload
    def crop(self, aabb: AxisAlignedBoundingBox, invert: bool = False) -> PointCloud:
        """
            Function to crop pointcloud into output pointcloud.
        
        Args:
            aabb (open3d.cuda.pybind.t.geometry.AxisAlignedBoundingBox): AxisAlignedBoundingBox to crop points.
            invert (bool, optional, default=False): Crop the points outside of the bounding box or inside of the bounding box.
        
        Returns:
            open3d.cuda.pybind.t.geometry.PointCloud
        
        Args:
            aabb (open3d.cuda.pybind.t.geometry.AxisAlignedBoundingBox)
            invert (bool, optional, default=False): Crop the points outside of the bounding box or inside of the bounding box.
        
        Returns:
            open3d.cuda.pybind.t.geometry.PointCloud
        """
    @typing.overload
    def crop(self, obb: OrientedBoundingBox, invert: bool = False) -> PointCloud:
        """
            Function to crop pointcloud into output pointcloud.
        
        Args:
            obb (open3d.cuda.pybind.t.geometry.OrientedBoundingBox)
            invert (bool, optional, default=False): Crop the points outside of the bounding box or inside of the bounding box.
        
        Returns:
            open3d.cuda.pybind.t.geometry.PointCloud
        
        Args:
            obb (open3d.cuda.pybind.t.geometry.OrientedBoundingBox): OrientedBoundingBox to crop points.
            invert (bool, optional, default=False): Crop the points outside of the bounding box or inside of the bounding box.
        
        Returns:
            open3d.cuda.pybind.t.geometry.PointCloud
        """
    def cuda(self, device_id: int = 0) -> PointCloud:
        """
        Transfer the point cloud to a CUDA device. If the point cloud is already on the specified CUDA device, no copy will be performed.
        """
    def estimate_color_gradients(self, max_nn: int | None = 30, radius: float | None = None) -> None:
        """
        Function to estimate point color gradients. It uses KNN search (Not recommended to use on GPU) if only max_nn parameter is provided, Radius search (Not recommended to use on GPU) if only radius is provided and Hybrid Search (Recommended) if radius parameter is also provided.
        """
    def estimate_normals(self, max_nn: int | None = 30, radius: float | None = None) -> None:
        """
        Function to estimate point normals. If the point cloud normals exist, the estimated normals are oriented with respect to the same. It uses KNN search (Not recommended to use on GPU) if only max_nn parameter is provided, Radius search (Not recommended to use on GPU) if only radius is provided and Hybrid Search (Recommended) if radius parameter is also provided.
        
        Args:
            max_nn (Optional[int], optional, default=30): Neighbor search max neighbors parameter [default = 30].
            radius (Optional[float], optional, default=None): neighbors search radius parameter to use HybridSearch. [Recommended ~1.4x voxel size].
        
        Returns:
            None
        """
    def extrude_linear(self, vector: open3d.cuda.pybind.core.Tensor, scale: float = 1.0, capping: bool = True) -> LineSet:
        """
        Sweeps the point cloud along a direction vector.
        
        Args:
        
            vector (open3d.core.Tensor): The direction vector.
        
            scale (float): Scalar factor which essentially scales the direction vector.
        
        Returns:
            A line set with the result of the sweep operation.
        
        
        Example:
        
            This code generates a set of straight lines from a point cloud::
        
                import open3d as o3d
                import numpy as np
                pcd = o3d.t.geometry.PointCloud(np.random.rand(10,3))
                lines = pcd.extrude_linear([0,1,0])
                o3d.visualization.draw([{'name': 'lines', 'geometry': lines}])
        """
    def extrude_rotation(self, angle: float, axis: open3d.cuda.pybind.core.Tensor, resolution: int = 16, translation: float = 0.0, capping: bool = True) -> LineSet:
        """
        Sweeps the point set rotationally about an axis.
        
        Args:
            angle (float): The rotation angle in degree.
        
            axis (open3d.core.Tensor): The rotation axis.
        
            resolution (int): The resolution defines the number of intermediate sweeps
                about the rotation axis.
        
            translation (float): The translation along the rotation axis.
        
        Returns:
            A line set with the result of the sweep operation.
        
        
        Example:
        
            This code generates a number of helices from a point cloud::
        
                import open3d as o3d
                import numpy as np
                pcd = o3d.t.geometry.PointCloud(np.random.rand(10,3))
                helices = pcd.extrude_rotation(3*360, [0,1,0], resolution=3*16, translation=2)
                o3d.visualization.draw([{'name': 'helices', 'geometry': helices}])
        """
    def farthest_point_down_sample(self, num_samples: int, start_index: int = 0) -> PointCloud:
        """
        Index to start downsampling from. Valid index is a non-negative number less than number of points in the input pointcloud.
        
        Args:
            num_samples (int): Number of points to be sampled.
            start_index (int, optional, default=0): Index of point to start downsampling from.
        
        Returns:
            open3d.cuda.pybind.t.geometry.PointCloud
        """
    def get_axis_aligned_bounding_box(self) -> AxisAlignedBoundingBox:
        """
        Create an axis-aligned bounding box from attribute 'positions'.
        """
    def get_center(self) -> open3d.cuda.pybind.core.Tensor:
        """
        Returns the center for point coordinates.
        """
    def get_max_bound(self) -> open3d.cuda.pybind.core.Tensor:
        """
        Returns the max bound for point coordinates.
        """
    def get_min_bound(self) -> open3d.cuda.pybind.core.Tensor:
        """
        Returns the min bound for point coordinates.
        """
    def get_oriented_bounding_box(self) -> OrientedBoundingBox:
        """
        Create an oriented bounding box from attribute 'positions'.
        """
    def hidden_point_removal(self, camera_location: open3d.cuda.pybind.core.Tensor, radius: float) -> tuple[TriangleMesh, open3d.cuda.pybind.core.Tensor]:
        """
        Removes hidden points from a point cloud and returns a mesh of
        the remaining points. Based on Katz et al. 'Direct Visibility of Point Sets',
        2007. Additional information about the choice of radius for noisy point clouds
        can be found in Mehra et. al. 'Visibility of Noisy Point Cloud Data', 2010.
        This is a wrapper for a CPU implementation and a copy of the point cloud data
        and resulting visible triangle mesh and indiecs will be made.
        
        Args:
            camera_location: All points not visible from that location will be removed.
        
            radius: The radius of the spherical projection.
        
        Return:
            Tuple of visible triangle mesh and indices of visible points on the same
            device as the point cloud.
        
        Example:
        
            We use armadillo mesh to compute the visible points from given camera::
        
                # Convert mesh to a point cloud and estimate dimensions.
                armadillo_data = o3d.data.ArmadilloMesh()
                pcd = o3d.io.read_triangle_mesh(
                armadillo_data.path).sample_points_poisson_disk(5000)
        
                diameter = np.linalg.norm(
                        np.asarray(pcd.get_max_bound()) - np.asarray(pcd.get_min_bound()))
        
                # Define parameters used for hidden_point_removal.
                camera = o3d.core.Tensor([0, 0, diameter], o3d.core.float32)
                radius = diameter * 100
        
                # Get all points that are visible from given view point.
                pcd = o3d.t.geometry.PointCloud.from_legacy(pcd)
                _, pt_map = pcd.hidden_point_removal(camera, radius)
                pcd = pcd.select_by_index(pt_map)
                o3d.visualization.draw([pcd], point_size=5)
        """
    def normalize_normals(self) -> PointCloud:
        """
        Normalize point normals to length 1.
        """
    def orient_normals_consistent_tangent_plane(self, k: int, lambda_penalty: float = 0.0, cos_alpha_tol: float = 1.0) -> None:
        """
        Function to consistently orient the normals of a point cloud based on tangent planes.
        
        The algorithm is described in Hoppe et al., "Surface Reconstruction from Unorganized Points", 1992.
        Additional information about the choice of lambda_penalty and cos_alpha_tol for complex
        point clouds can be found in Piazza, Valentini, Varetti, "Mesh Reconstruction from Point Cloud", 2023
        (https://eugeniovaretti.github.io/meshreco/Piazza_Valentini_Varetti_MeshReconstructionFromPointCloud_2023.pdf).
        
        Args:
            k (int): Number of neighbors to use for tangent plane estimation.
            lambda_penalty (float): A non-negative real parameter that influences the distance
                metric used to identify the true neighbors of a point in complex
                geometries. It penalizes the distance between a point and the tangent
                plane defined by the reference point and its normal vector, helping to
                mitigate misclassification issues encountered with traditional
                Euclidean distance metrics.
            cos_alpha_tol (float): Cosine threshold angle used to determine the
                inclusion boundary of neighbors based on the direction of the normal
                vector.
        
        Example:
            We use Bunny point cloud to compute its normals and orient them consistently.
            The initial reconstruction adheres to Hoppe's algorithm (raw), whereas the
            second reconstruction utilises the lambda_penalty and cos_alpha_tol parameters.
            Due to the high density of the Bunny point cloud available in Open3D a larger
            value of the parameter k is employed to test the algorithm.  Usually you do
            not have at disposal such a refined point clouds, thus you cannot find a
            proper choice of k: refer to
            https://eugeniovaretti.github.io/meshreco for these cases.::
        
                import open3d as o3d
                import numpy as np
                # Load point cloud
                data = o3d.data.BunnyMesh()
        
                # Case 1, Hoppe (raw):
                pcd = o3d.io.read_point_cloud(data.path)
        
                # Compute normals and orient them consistently, using k=100 neighbours
                pcd.estimate_normals()
                pcd.orient_normals_consistent_tangent_plane(100)
        
                # Create mesh from point cloud using Poisson Algorithm
                poisson_mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(pcd, depth=8, width=0, scale=1.1, linear_fit=False)[0]
                poisson_mesh.paint_uniform_color(np.array([[0.5],[0.5],[0.5]]))
                poisson_mesh.compute_vertex_normals()
                o3d.visualization.draw_geometries([poisson_mesh])
        
                # Case 2, reconstruction using lambda_penalty and cos_alpha_tol parameters:
                pcd_robust = o3d.io.read_point_cloud(data.path)
        
                # Compute normals and orient them consistently, using k=100 neighbours
                pcd_robust.estimate_normals()
                pcd_robust.orient_normals_consistent_tangent_plane(100, 10, 0.5)
        
                # Create mesh from point cloud using Poisson Algorithm
                poisson_mesh_robust = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(pcd_robust, depth=8, width=0, scale=1.1, linear_fit=False)[0]
                poisson_mesh_robust.paint_uniform_color(np.array([[0.5],[0.5],[0.5]]))
                poisson_mesh_robust.compute_vertex_normals()
        
                o3d.visualization.draw_geometries([poisson_mesh_robust]) 
        """
    def paint_uniform_color(self, color: open3d.cuda.pybind.core.Tensor) -> PointCloud:
        """
        Assigns uniform color to the point cloud.
        
        Args:
            color (open3d.cuda.pybind.core.Tensor): Color of the pointcloud. Floating color values are clipped between 0.0 and 1.0.
        
        Returns:
            open3d.cuda.pybind.t.geometry.PointCloud
        """
    def pca_partition(self, max_points: int) -> int:
        """
        Partition the point cloud by recursively doing PCA.
        
        This function creates a new point attribute with the name "partition_ids" storing
        the partition id for each point.
        
        Args:
            max_points (int): The maximum allowed number of points in a partition.
        
        
        Example:
        
            This code computes parititions a point cloud such that each partition
            contains at most 20 points::
        
                import open3d as o3d
                import numpy as np
                pcd = o3d.t.geometry.PointCloud(np.random.rand(100,3))
                num_partitions = pcd.pca_partition(max_points=20)
        
                # print the partition ids and the number of points for each of them.
                print(np.unique(pcd.point.partition_ids.numpy(), return_counts=True))
        """
    def project_to_depth_image(self, width: int, height: int, intrinsics: open3d.cuda.pybind.core.Tensor, extrinsics: open3d.cuda.pybind.core.Tensor = ..., depth_scale: float = 1000.0, depth_max: float = 3.0) -> Image:
        """
        Project a point cloud to a depth image.
        """
    def project_to_rgbd_image(self, width: int, height: int, intrinsics: open3d.cuda.pybind.core.Tensor, extrinsics: open3d.cuda.pybind.core.Tensor = ..., depth_scale: float = 1000.0, depth_max: float = 3.0) -> RGBDImage:
        """
        Project a colored point cloud to a RGBD image.
        """
    def random_down_sample(self, sampling_ratio: float) -> PointCloud:
        """
        Downsample a pointcloud by selecting random index point and its attributes.
        
        Args:
            sampling_ratio (float): Sampling ratio, the ratio of sample to total number of points in the pointcloud.
        
        Returns:
            open3d.cuda.pybind.t.geometry.PointCloud
        """
    def remove_duplicated_points(self) -> tuple[PointCloud, open3d.cuda.pybind.core.Tensor]:
        """
        Remove duplicated points and there associated attributes.
        """
    def remove_non_finite_points(self, remove_nan: bool = True, remove_infinite: bool = True) -> tuple[PointCloud, open3d.cuda.pybind.core.Tensor]:
        """
        Remove all points from the point cloud that have a nan entry, or
        infinite value. It also removes the corresponding attributes.
        
        Args:
            remove_nan: Remove NaN values from the PointCloud.
            remove_infinite: Remove infinite values from the PointCloud.
        
        Return:
            Tuple of filtered point cloud and boolean mask tensor for selected values
            w.r.t. input point cloud.
        """
    def remove_radius_outliers(self, nb_points: int, search_radius: float) -> tuple[PointCloud, open3d.cuda.pybind.core.Tensor]:
        """
        Remove points that have less than nb_points neighbors in a
        sphere of a given search radius.
        
        Args:
            nb_points: Number of neighbor points required within the radius.
            search_radius: Radius of the sphere.
        
        Return:
            Tuple of filtered point cloud and boolean mask tensor for selected values
            w.r.t. input point cloud.
        
        Args:
            nb_points (int): Number of neighbor points required within the radius.
            search_radius (float): Radius of the sphere.
        
        Returns:
            tuple[open3d.cuda.pybind.t.geometry.PointCloud, open3d.cuda.pybind.core.Tensor]
        """
    def remove_statistical_outliers(self, nb_neighbors: int, std_ratio: float) -> tuple[PointCloud, open3d.cuda.pybind.core.Tensor]:
        """
        Remove points that are further away from their \\p nb_neighbor
        neighbors in average. This function is not recommended to use on GPU.
        
        Args:
            nb_neighbors: Number of neighbors around the target point.
            std_ratio: Standard deviation ratio.
        
        Return:
            Tuple of filtered point cloud and boolean mask tensor for selected values
            w.r.t. input point cloud.
        """
    def rotate(self, R: open3d.cuda.pybind.core.Tensor, center: open3d.cuda.pybind.core.Tensor) -> PointCloud:
        """
        Rotate points and normals (if exist).
        """
    def scale(self, scale: float, center: open3d.cuda.pybind.core.Tensor) -> PointCloud:
        """
        Scale points.
        """
    def segment_plane(self, distance_threshold: float = 0.01, ransac_n: int = 3, num_iterations: int = 100, probability: float = 0.999) -> tuple[open3d.cuda.pybind.core.Tensor, open3d.cuda.pybind.core.Tensor]:
        """
        Segments a plane in the point cloud using the RANSAC algorithm.
        This is a wrapper for a CPU implementation and a copy of the point cloud data and
        resulting plane model and inlier indiecs will be made.
        
        Args:
            distance_threshold (default 0.01): Max distance a point can be from the plane model, and still be considered an inlier.
        
            ransac_n (default 3): Number of initial points to be considered inliers in each iteration.
            num_iterations (default 100): Maximum number of iterations.
        
            probability (default 0.999): Expected probability of finding the optimal plane.
        
        Return:
            Tuple of the plane model `ax + by + cz + d = 0` and the indices of
            the plane inliers on the same device as the point cloud.
        
        Example:
        
            We use Redwood dataset to compute its plane model and inliers::
        
                sample_pcd_data = o3d.data.PCDPointCloud()
                pcd = o3d.t.io.read_point_cloud(sample_pcd_data.path)
                plane_model, inliers = pcd.segment_plane(distance_threshold=0.01,
                                                         ransac_n=3,
                                                         num_iterations=1000)
                inlier_cloud = pcd.select_by_index(inliers)
                inlier_cloud = inlier_cloud.paint_uniform_color([1.0, 0, 0])
                outlier_cloud = pcd.select_by_index(inliers, invert=True)
                o3d.visualization.draw([inlier_cloud, outlier_cloud])
        """
    def select_by_index(self, indices: open3d.cuda.pybind.core.Tensor, invert: bool = False, remove_duplicates: bool = False) -> PointCloud:
        """
        Select points from input pointcloud, based on indices into output point cloud.
        
        Args:
            indices (open3d.cuda.pybind.core.Tensor): Int64 indexing tensor of shape {n,} containing index value that is to be selected.
            invert (bool, optional, default=False): Set to `True` to invert the selection of indices, and also ignore the duplicated indices.
            remove_duplicates (bool, optional, default=False): Set to `True` to remove the duplicated indices.
        
        Returns:
            open3d.cuda.pybind.t.geometry.PointCloud
        """
    def select_by_mask(self, boolean_mask: open3d.cuda.pybind.core.Tensor, invert: bool = False) -> PointCloud:
        """
        Select points from input pointcloud, based on boolean mask indices into output point cloud.
        
        Args:
            boolean_mask (open3d.cuda.pybind.core.Tensor): Boolean indexing tensor of shape {n,} containing true value for the indices that is to be selected..
            invert (bool, optional, default=False): Set to `True` to invert the selection of indices.
        
        Returns:
            open3d.cuda.pybind.t.geometry.PointCloud
        """
    def to(self, device: open3d.cuda.pybind.core.Device, copy: bool = False) -> PointCloud:
        """
        Transfer the point cloud to a specified device.
        """
    def to_legacy(self) -> open3d.cuda.pybind.geometry.PointCloud:
        """
        Convert to a legacy Open3D PointCloud.
        """
    def transform(self, transformation: open3d.cuda.pybind.core.Tensor) -> PointCloud:
        """
        Transforms the points and normals (if exist).
        """
    def translate(self, translation: open3d.cuda.pybind.core.Tensor, relative: bool = True) -> PointCloud:
        """
        Translates points.
        """
    def uniform_down_sample(self, every_k_points: int) -> PointCloud:
        """
        Downsamples a point cloud by selecting every kth index point and its attributes.
        
        Args:
            every_k_points (int): Sample rate, the selected point indices are [0, k, 2k, …].
        
        Returns:
            open3d.cuda.pybind.t.geometry.PointCloud
        """
    def voxel_down_sample(self, voxel_size: float, reduction: str = 'mean') -> PointCloud:
        """
        Downsamples a point cloud with a specified voxel size.
        
        Args:
            voxel_size (float): The size of the voxel used to downsample the point cloud.
        
            reduction (str): The approach to pool point properties in a voxel. Can only be "mean" at current.
        
        Return:
            A downsampled point cloud with point properties reduced in each voxel.
        
        Example:
        
            We will load the Eagle dataset, downsample it, and show the result::
        
                eagle = o3d.data.EaglePointCloud()
                pcd = o3d.t.io.read_point_cloud(eagle.path)
                pcd_down = pcd.voxel_down_sample(voxel_size=0.05)
                o3d.visualization.draw([{'name': 'pcd', 'geometry': pcd}, {'name': 'pcd_down', 'geometry': pcd_down}])
        
        Args:
            voxel_size (float): Voxel size. A positive number.
            reduction (str, optional, default='mean')
        
        Returns:
            open3d.cuda.pybind.t.geometry.PointCloud
        """
    @property
    def point(self) -> TensorMap:
        """
        Point's attributes: positions, colors, normals, etc.
        """
class RGBDImage(Geometry):
    """
    RGBDImage is a pair of color and depth images. For most processing, the image pair should be aligned (same viewpoint and  resolution).
    """
    def __getstate__(self) -> tuple:
        ...
    @typing.overload
    def __init__(self) -> None:
        """
            Construct an empty RGBDImage.
        """
    @typing.overload
    def __init__(self, color: Image, depth: Image, aligned: bool = True) -> None:
        """
            Parameterized constructor
        
        Args:
            color (open3d.cuda.pybind.t.geometry.Image): The color image.
            depth (open3d.cuda.pybind.t.geometry.Image): The depth image.
            aligned (bool, optional, default=True): Are the two images aligned (same viewpoint and resolution)?
        """
    def __repr__(self) -> str:
        ...
    def __setstate__(self, arg0: tuple) -> None:
        ...
    def are_aligned(self) -> bool:
        """
        Are the depth and color images aligned (same viewpoint and resolution)?
        """
    def clear(self) -> RGBDImage:
        """
        Clear stored data.
        
        Returns:
            open3d.cuda.pybind.t.geometry.RGBDImage
        """
    def clone(self) -> RGBDImage:
        """
        Returns a copy of the RGBDImage on the same device.
        """
    def cpu(self) -> RGBDImage:
        """
        Transfer the RGBD image to CPU. If the RGBD image is already on CPU, no copy will be performed.
        """
    def cuda(self, device_id: int = 0) -> RGBDImage:
        """
        Transfer the RGBD image to a CUDA device. If the RGBD image is already on the specified CUDA device, no copy will be performed.
        """
    def get_max_bound(self) -> open3d.cuda.pybind.core.Tensor:
        """
        Compute max 2D coordinates for the data.
        
        Returns:
            open3d.cuda.pybind.core.Tensor
        """
    def get_min_bound(self) -> open3d.cuda.pybind.core.Tensor:
        """
        Compute min 2D coordinates for the data (always {0, 0}).
        
        Returns:
            open3d.cuda.pybind.core.Tensor
        """
    def is_empty(self) -> bool:
        """
        Is any data stored?
        
        Returns:
            bool
        """
    def to(self, device: open3d.cuda.pybind.core.Device, copy: bool = False) -> RGBDImage:
        """
        Transfer the RGBDImage to a specified device.
        """
    def to_legacy(self) -> open3d.cuda.pybind.geometry.RGBDImage:
        """
        Convert to legacy RGBDImage type.
        
        Returns:
            open3d.cuda.pybind.geometry.RGBDImage
        """
    @property
    def aligned_(self) -> bool:
        """
        Are the depth and color images aligned (same viewpoint and resolution)?
        """
    @aligned_.setter
    def aligned_(self, arg0: bool) -> None:
        ...
    @property
    def color(self) -> Image:
        """
        The color image.
        """
    @color.setter
    def color(self, arg0: Image) -> None:
        ...
    @property
    def depth(self) -> Image:
        """
        The depth image.
        """
    @depth.setter
    def depth(self, arg0: Image) -> None:
        ...
class RaycastingScene:
    """
    
    A scene class with basic ray casting and closest point queries.
    
    The RaycastingScene allows to compute ray intersections with triangle meshes
    or compute the closest point on the surface of a mesh with respect to one
    or more query points.
    It builds an internal acceleration structure to speed up those queries.
    
    This class supports the CPU device and SYCL GPU device.
    
    The following shows how to create a scene and compute ray intersections::
    
        import open3d as o3d
        import matplotlib.pyplot as plt
    
        cube = o3d.t.geometry.TriangleMesh.from_legacy(
                                            o3d.geometry.TriangleMesh.create_box())
    
        # Create scene and add the cube mesh
        scene = o3d.t.geometry.RaycastingScene()
        scene.add_triangles(cube)
    
        # Rays are 6D vectors with origin and ray direction.
        # Here we use a helper function to create rays for a pinhole camera.
        rays = scene.create_rays_pinhole(fov_deg=60,
                                         center=[0.5,0.5,0.5],
                                         eye=[-1,-1,-1],
                                         up=[0,0,1],
                                         width_px=320,
                                         height_px=240)
    
        # Compute the ray intersections.
        ans = scene.cast_rays(rays)
    
        # Visualize the hit distance (depth)
        plt.imshow(ans['t_hit'].numpy())
    
    """
    INVALID_ID: typing.ClassVar[int] = 4294967295
    @staticmethod
    @typing.overload
    def create_rays_pinhole(intrinsic_matrix: open3d.cuda.pybind.core.Tensor, extrinsic_matrix: open3d.cuda.pybind.core.Tensor, width_px: int, height_px: int) -> open3d.cuda.pybind.core.Tensor:
        """
        Creates rays for the given camera parameters.
        
        Args:
            intrinsic_matrix (open3d.core.Tensor): The upper triangular intrinsic matrix
                with shape {3,3}.
            extrinsic_matrix (open3d.core.Tensor): The 4x4 world to camera SE(3)
                transformation matrix.
            width_px (int): The width of the image in pixels.
            height_px (int): The height of the image in pixels.
        
        Returns:
            A tensor of shape {height_px, width_px, 6} with the rays.
        """
    @staticmethod
    @typing.overload
    def create_rays_pinhole(fov_deg: float, center: open3d.cuda.pybind.core.Tensor, eye: open3d.cuda.pybind.core.Tensor, up: open3d.cuda.pybind.core.Tensor, width_px: int, height_px: int) -> open3d.cuda.pybind.core.Tensor:
        """
        Creates rays for the given camera parameters.
        
        Args:
            fov_deg (float): The horizontal field of view in degree.
            center (open3d.core.Tensor): The point the camera is looking at with shape
                {3}.
            eye (open3d.core.Tensor): The position of the camera with shape {3}.
            up (open3d.core.Tensor): The up-vector with shape {3}.
            width_px (int): The width of the image in pixels.
            height_px (int): The height of the image in pixels.
        
        Returns:
            A tensor of shape {height_px, width_px, 6} with the rays.
        """
    def __init__(self, nthreads: int = 0, device: open3d.cuda.pybind.core.Device = ...) -> None:
        """
        Create a RaycastingScene.
        
        Args:
            nthreads (int): The number of threads to use for building the scene. Set to 0 for automatic.
            device (open3d.core.Device): The device to use. Currently CPU and SYCL devices are supported.
        """
    @typing.overload
    def add_triangles(self, vertex_positions: open3d.cuda.pybind.core.Tensor, triangle_indices: open3d.cuda.pybind.core.Tensor) -> int:
        """
        Add a triangle mesh to the scene.
        
        Args:
            vertices (open3d.core.Tensor): Vertices as Tensor of dim {N,3} and dtype
                Float32.
            triangles (open3d.core.Tensor): Triangles as Tensor of dim {M,3} and dtype
                UInt32.
        
        Returns:
            The geometry ID of the added mesh.
        """
    @typing.overload
    def add_triangles(self, mesh: TriangleMesh) -> int:
        """
        Add a triangle mesh to the scene.
        
        Args:
            mesh (open3d.t.geometry.TriangleMesh): A triangle mesh.
        
        Returns:
            The geometry ID of the added mesh.
        """
    def cast_rays(self, rays: open3d.cuda.pybind.core.Tensor, nthreads: int = 0) -> dict[str, open3d.cuda.pybind.core.Tensor]:
        """
        Computes the first intersection of the rays with the scene.
        
        Args:
            rays (open3d.core.Tensor): A tensor with >=2 dims, shape {.., 6}, and Dtype
                Float32 describing the rays.
                {..} can be any number of dimensions, e.g., to organize rays for
                creating an image the shape can be {height, width, 6}. The last
                dimension must be 6 and has the format [ox, oy, oz, dx, dy, dz]
                with [ox,oy,oz] as the origin and [dx,dy,dz] as the direction. It is
                not necessary to normalize the direction but the returned hit distance
                uses the length of the direction vector as unit.
        
            nthreads (int): The number of threads to use. Set to 0 for automatic.
        
        Returns:
            A dictionary which contains the following keys
        
            t_hit
                A tensor with the distance to the first hit. The shape is {..}. If there
                is no intersection the hit distance is *inf*.
        
            geometry_ids
                A tensor with the geometry IDs. The shape is {..}. If there
                is no intersection the ID is *INVALID_ID*.
        
            primitive_ids
                A tensor with the primitive IDs, which corresponds to the triangle
                index. The shape is {..}.  If there is no intersection the ID is
                *INVALID_ID*.
        
            primitive_uvs
                A tensor with the barycentric coordinates of the hit points within the
                hit triangles. The shape is {.., 2}.
        
            primitive_normals
                A tensor with the normals of the hit triangles. The shape is {.., 3}.
        """
    def compute_closest_points(self, query_points: open3d.cuda.pybind.core.Tensor, nthreads: int = 0) -> dict[str, open3d.cuda.pybind.core.Tensor]:
        """
        Computes the closest points on the surfaces of the scene.
        
        Args:
            query_points (open3d.core.Tensor): A tensor with >=2 dims, shape {.., 3},
                and Dtype Float32 describing the query points.
                {..} can be any number of dimensions, e.g., to organize the query_point
                to create a 3D grid the shape can be {depth, height, width, 3}.
                The last dimension must be 3 and has the format [x, y, z].
        
            nthreads (int): The number of threads to use. Set to 0 for automatic.
        
        Returns:
            The returned dictionary contains
        
            points
                A tensor with the closest surface points. The shape is {..}.
        
            geometry_ids
                A tensor with the geometry IDs. The shape is {..}.
        
            primitive_ids
                A tensor with the primitive IDs, which corresponds to the triangle
                index. The shape is {..}.
        
            primitive_uvs
                A tensor with the barycentric coordinates of the closest points within
                the triangles. The shape is {.., 2}.
        
            primitive_normals
                A tensor with the normals of the closest triangle . The shape is
                {.., 3}.
        """
    def compute_distance(self, query_points: open3d.cuda.pybind.core.Tensor, nthreads: int = 0) -> open3d.cuda.pybind.core.Tensor:
        """
        Computes the distance to the surface of the scene.
        
        Args:
            query_points (open3d.core.Tensor): A tensor with >=2 dims, shape {.., 3},
                and Dtype Float32 describing the query points.
                {..} can be any number of dimensions, e.g., to organize the
                query points to create a 3D grid the shape can be
                {depth, height, width, 3}.
                The last dimension must be 3 and has the format [x, y, z].
        
            nthreads (int): The number of threads to use. Set to 0 for automatic.
        
        Returns:
            A tensor with the distances to the surface. The shape is {..}.
        """
    def compute_occupancy(self, query_points: open3d.cuda.pybind.core.Tensor, nthreads: int = 0, nsamples: int = 1) -> open3d.cuda.pybind.core.Tensor:
        """
        Computes the occupancy at the query point positions.
        
        This function computes whether the query points are inside or outside.
        The function assumes that all meshes are watertight and that there are
        no intersections between meshes, i.e., inside and outside must be well
        defined. The function determines if a point is inside by counting the
        intersections of a rays starting at the query points.
        
        Args:
            query_points (open3d.core.Tensor): A tensor with >=2 dims, shape {.., 3},
                and Dtype Float32 describing the query points.
                {..} can be any number of dimensions, e.g., to organize the
                query points to create a 3D grid the shape can be
                {depth, height, width, 3}.
                The last dimension must be 3 and has the format [x, y, z].
        
            nthreads (int): The number of threads to use. Set to 0 for automatic.
        
            nsamples (int): The number of rays used for determining the inside.
                This must be an odd number. The default is 1. Use a higher value if you
                notice errors in the occupancy values. Errors can occur when rays hit
                exactly an edge or vertex in the scene.
        
        Returns:
            A tensor with the occupancy values. The shape is {..}. Values are either 0
            or 1. A point is occupied or inside if the value is 1.
        """
    def compute_signed_distance(self, query_points: open3d.cuda.pybind.core.Tensor, nthreads: int = 0, nsamples: int = 1) -> open3d.cuda.pybind.core.Tensor:
        """
        Computes the signed distance to the surface of the scene.
        
        This function computes the signed distance to the meshes in the scene.
        The function assumes that all meshes are watertight and that there are
        no intersections between meshes, i.e., inside and outside must be well
        defined. The function determines the sign of the distance by counting
        the intersections of a rays starting at the query points.
        
        Args:
            query_points (open3d.core.Tensor): A tensor with >=2 dims, shape {.., 3},
                and Dtype Float32 describing the query_points.
                {..} can be any number of dimensions, e.g., to organize the
                query points to create a 3D grid the shape can be
                {depth, height, width, 3}.
                The last dimension must be 3 and has the format [x, y, z].
        
            nthreads (int): The number of threads to use. Set to 0 for automatic.
        
            nsamples (int): The number of rays used for determining the inside.
                This must be an odd number. The default is 1. Use a higher value if you
                notice sign flipping, which can occur when rays hit exactly an edge or
                vertex in the scene.
        
        Returns:
            A tensor with the signed distances to the surface. The shape is {..}.
            Negative distances mean a point is inside a closed surface.
        """
    def count_intersections(self, rays: open3d.cuda.pybind.core.Tensor, nthreads: int = 0) -> open3d.cuda.pybind.core.Tensor:
        """
        Computes the number of intersection of the rays with the scene.
        
        Args:
            rays (open3d.core.Tensor): A tensor with >=2 dims, shape {.., 6}, and Dtype
                Float32 describing the rays.
                {..} can be any number of dimensions, e.g., to organize rays for
                creating an image the shape can be {height, width, 6}.
                The last dimension must be 6 and has the format [ox, oy, oz, dx, dy, dz]
                with [ox,oy,oz] as the origin and [dx,dy,dz] as the direction. It is not
                necessary to normalize the direction.
        
            nthreads (int): The number of threads to use. Set to 0 for automatic.
        
        Returns:
            A tensor with the number of intersections. The shape is {..}.
        """
    def list_intersections(self, rays: open3d.cuda.pybind.core.Tensor, nthreads: int = 0) -> dict[str, open3d.cuda.pybind.core.Tensor]:
        """
        Lists the intersections of the rays with the scene::
        
            import open3d as o3d
            import numpy as np
        
            # Create scene and add the monkey model.
            scene = o3d.t.geometry.RaycastingScene()
            d = o3d.data.MonkeyModel()
            mesh = o3d.t.io.read_triangle_mesh(d.path)
            mesh_id = scene.add_triangles(mesh)
        
            # Create a grid of rays covering the bounding box
            bb_min = mesh.vertex['positions'].min(dim=0).numpy()
            bb_max = mesh.vertex['positions'].max(dim=0).numpy()
            x,y = np.linspace(bb_min, bb_max, num=10)[:,:2].T
            xv, yv = np.meshgrid(x,y)
            orig = np.stack([xv, yv, np.full_like(xv, bb_min[2]-1)], axis=-1).reshape(-1,3)
            dest = orig + np.full(orig.shape, (0,0,2+bb_max[2]-bb_min[2]),dtype=np.float32)
            rays = np.concatenate([orig, dest-orig], axis=-1).astype(np.float32)
        
            # Compute the ray intersections.
            lx = scene.list_intersections(rays)
            lx = {k:v.numpy() for k,v in lx.items()}
        
            # Calculate intersection coordinates using the primitive uvs and the mesh
            v = mesh.vertex['positions'].numpy()
            t = mesh.triangle['indices'].numpy()
            tidx = lx['primitive_ids']
            uv = lx['primitive_uvs']
            w = 1 - np.sum(uv, axis=1)
            c = \\
            v[t[tidx, 1].flatten(), :] * uv[:, 0][:, None] + \\
            v[t[tidx, 2].flatten(), :] * uv[:, 1][:, None] + \\
            v[t[tidx, 0].flatten(), :] * w[:, None]
        
            # Calculate intersection coordinates using ray_ids
            c = rays[lx['ray_ids']][:,:3] + rays[lx['ray_ids']][:,3:]*lx['t_hit'][...,None]
        
            # Visualize the rays and intersections.
            lines = o3d.t.geometry.LineSet()
            lines.point.positions = np.hstack([orig,dest]).reshape(-1,3)
            lines.line.indices = np.arange(lines.point.positions.shape[0]).reshape(-1,2)
            lines.line.colors = np.full((lines.line.indices.shape[0],3), (1,0,0))
            x = o3d.t.geometry.PointCloud(positions=c)
            o3d.visualization.draw([mesh, lines, x], point_size=8)
        
        
        Args:
            rays (open3d.core.Tensor): A tensor with >=2 dims, shape {.., 6}, and Dtype
                Float32 describing the rays; {..} can be any number of dimensions.
                The last dimension must be 6 and has the format [ox, oy, oz, dx, dy, dz]
                with [ox,oy,oz] as the origin and [dx,dy,dz] as the direction. It is not
                necessary to normalize the direction although it should be normalised if
                t_hit is to be calculated in coordinate units.
        
            nthreads (int): The number of threads to use. Set to 0 for automatic.
        
        Returns:
            The returned dictionary contains
        
            ray_splits
                A tensor with ray intersection splits. Can be used to iterate over all intersections for each ray. The shape is {num_rays + 1}.
        
            ray_ids
                A tensor with ray IDs. The shape is {num_intersections}.
        
            t_hit
                A tensor with the distance to the hit. The shape is {num_intersections}.
        
            geometry_ids
                A tensor with the geometry IDs. The shape is {num_intersections}.
        
            primitive_ids
                A tensor with the primitive IDs, which corresponds to the triangle
                index. The shape is {num_intersections}.
        
            primitive_uvs
                A tensor with the barycentric coordinates of the intersection points within
                the triangles. The shape is {num_intersections, 2}.
        
        
        An example of using ray_splits::
        
            ray_splits: [0, 2, 3, 6, 6, 8] # note that the length of this is num_rays+1
            t_hit: [t1, t2, t3, t4, t5, t6, t7, t8]
        
            for ray_id, (start, end) in enumerate(zip(ray_splits[:-1], ray_splits[1:])):
                for i,t in enumerate(t_hit[start:end]):
                    print(f'ray {ray_id}, intersection {i} at {t}')
        """
    def test_occlusions(self, rays: open3d.cuda.pybind.core.Tensor, tnear: float = 0.0, tfar: float = ..., nthreads: int = 0) -> open3d.cuda.pybind.core.Tensor:
        """
        Checks if the rays have any intersection with the scene.
        
        Args:
            rays (open3d.core.Tensor): A tensor with >=2 dims, shape {.., 6}, and Dtype
                Float32 describing the rays.
                {..} can be any number of dimensions, e.g., to organize rays for
                creating an image the shape can be {height, width, 6}.
                The last dimension must be 6 and has the format [ox, oy, oz, dx, dy, dz]
                with [ox,oy,oz] as the origin and [dx,dy,dz] as the direction. It is not
                necessary to normalize the direction.
        
            tnear (float): The tnear offset for the rays. The default is 0.
        
            tfar (float): The tfar value for the ray. The default is infinity.
        
            nthreads (int): The number of threads to use. Set to 0 for automatic.
        
        Returns:
            A boolean tensor which indicates if the ray is occluded by the scene (true)
            or not (false).
        """
class TensorMap:
    """
    Map of String to Tensor with a primary key.
    """
    def __bool__(self) -> bool:
        """
        Check whether the map is nonempty
        """
    def __contains__(self, arg0: str) -> bool:
        ...
    def __delattr__(self, arg0: str) -> int:
        ...
    def __delitem__(self, arg0: str) -> int:
        ...
    def __getattr__(self, arg0: str) -> open3d.cuda.pybind.core.Tensor:
        ...
    def __getitem__(self, arg0: str) -> open3d.cuda.pybind.core.Tensor:
        ...
    def __getstate__(self) -> tuple:
        ...
    @typing.overload
    def __init__(self) -> None:
        ...
    @typing.overload
    def __init__(self, primary_key: str) -> None:
        ...
    @typing.overload
    def __init__(self, primary_key: str, map_keys_to_tensors: dict[str, open3d.cuda.pybind.core.Tensor]) -> None:
        ...
    def __iter__(self) -> typing.Iterator[str]:
        ...
    def __len__(self) -> int:
        ...
    def __repr__(self) -> str:
        ...
    def __setattr__(self, arg0: str, arg1: open3d.cuda.pybind.core.Tensor) -> None:
        ...
    @typing.overload
    def __setitem__(self, arg0: str, arg1: open3d.cuda.pybind.core.Tensor) -> None:
        ...
    @typing.overload
    def __setitem__(self, arg0: str, arg1: open3d.cuda.pybind.core.Tensor) -> None:
        ...
    def __setstate__(self, arg0: tuple) -> None:
        ...
    def __str__(self) -> str:
        ...
    def assert_size_synchronized(self) -> None:
        ...
    def erase(self, arg0: str) -> int:
        ...
    def is_size_synchronized(self) -> bool:
        ...
    def items(self) -> typing.Iterator[tuple[str, open3d.cuda.pybind.core.Tensor]]:
        ...
    @property
    def primary_key(self) -> str:
        ...
class TriangleMesh(Geometry, DrawableGeometry):
    """
    
    A triangle mesh contains vertices and triangles. The triangle mesh class stores
    the attribute data in key-value maps. There are two maps: the vertex attributes
    map, and the triangle attribute map.
    
    The attributes of the triangle mesh have different levels::
    
        import open3d as o3d
    
        device = o3d.core.Device("CPU:0")
        dtype_f = o3d.core.float32
        dtype_i = o3d.core.int32
    
        # Create an empty triangle mesh
        # Use mesh.vertex to access the vertices' attributes
        # Use mesh.triangle to access the triangles' attributes
        mesh = o3d.t.geometry.TriangleMesh(device)
    
        # Default attribute: vertex.positions, triangle.indices
        # These attributes is created by default and is required by all triangle
        # meshes. The shape of both must be (N, 3). The device of "positions"
        # determines the device of the triangle mesh.
        mesh.vertex.positions = o3d.core.Tensor([[0, 0, 0],
                                                    [0, 0, 1],
                                                    [0, 1, 0],
                                                    [0, 1, 1]], dtype_f, device)
        mesh.triangle.indices = o3d.core.Tensor([[0, 1, 2],
                                                    [0, 2, 3]]], dtype_i, device)
    
        # Common attributes: vertex.colors  , vertex.normals
        #                    triangle.colors, triangle.normals
        # Common attributes are used in built-in triangle mesh operations. The
        # spellings must be correct. For example, if "normal" is used instead of
        # "normals", some internal operations that expects "normals" will not work.
        # "normals" and "colors" must have shape (N, 3) and must be on the same
        # device as the triangle mesh.
        mesh.vertex.normals = o3d.core.Tensor([[0, 0, 1],
                                                  [0, 1, 0],
                                                  [1, 0, 0],
                                                  [1, 1, 1]], dtype_f, device)
        mesh.vertex.colors = o3d.core.Tensor([[0.0, 0.0, 0.0],
                                                 [0.1, 0.1, 0.1],
                                                 [0.2, 0.2, 0.2],
                                                 [0.3, 0.3, 0.3]], dtype_f, device)
        mesh.triangle.normals = o3d.core.Tensor(...)
        mesh.triangle.colors = o3d.core.Tensor(...)
    
        # User-defined attributes
        # You can also attach custom attributes. The value tensor must be on the
        # same device as the triangle mesh. The are no restrictions on the shape and
        # dtype, e.g.,
        pcd.vertex.labels = o3d.core.Tensor(...)
        pcd.triangle.features = o3d.core.Tensor(...)
    """
    @staticmethod
    def create_arrow(cylinder_radius: float = 1.0, cone_radius: float = 1.5, cylinder_height: float = 5.0, cone_height: float = 4.0, resolution: int = 20, cylinder_split: int = 4, cone_split: int = 1, float_dtype: open3d.cuda.pybind.core.Dtype = ..., int_dtype: open3d.cuda.pybind.core.Dtype = ..., device: open3d.cuda.pybind.core.Device = ...) -> TriangleMesh:
        """
        Create a arrow mesh.
        
        Args:
            cylinder_radius (float, optional, default=1.0): The radius of the cylinder.
            cone_radius (float, optional, default=1.5): The radius of the cone.
            cylinder_height (float, optional, default=5.0): The height of the cylinder. The cylinder is from (0, 0, 0) to (0, 0, cylinder_height)
            cone_height (float, optional, default=4.0): The height of the cone. The axis of the cone will be from (0, 0, cylinder_height) to (0, 0, cylinder_height + cone_height)
            resolution (int, optional, default=20): The cone will be split into ``resolution`` segments.
            cylinder_split (int, optional, default=4): The ``cylinder_height`` will be split into ``cylinder_split`` segments.
            cone_split (int, optional, default=1): The ``cone_height`` will be split into ``cone_split`` segments.
            float_dtype (open3d.cuda.pybind.core.Dtype, optional, default=Float32): Float_dtype, Float32 or Float64.
            int_dtype (open3d.cuda.pybind.core.Dtype, optional, default=Int64): Int_dtype, Int32 or Int64.
            device (open3d.cuda.pybind.core.Device, optional, default=CPU:0): Device of the create octahedron.
        
        Returns:
            open3d.cuda.pybind.t.geometry.TriangleMesh
        """
    @staticmethod
    def create_box(height: float = 1.0, depth: float = 1.0, float_dtype: open3d.cuda.pybind.core.Dtype = ..., int_dtype: open3d.cuda.pybind.core.Dtype = ..., device: open3d.cuda.pybind.core.Device = ...) -> TriangleMesh:
        """
        Args:
            height (float, optional, default=1.0): y-directional length.
            depth (float, optional, default=1.0): z-directional length.
            float_dtype (open3d.cuda.pybind.core.Dtype, optional, default=Float32): Float_dtype, Float32 or Float64.
            int_dtype (open3d.cuda.pybind.core.Dtype, optional, default=Int64): Int_dtype, Int32 or Int64.
            device (open3d.cuda.pybind.core.Device, optional, default=CPU:0): Device of the create mesh.
        
        Returns:
            open3d.cuda.pybind.t.geometry.TriangleMesh
        """
    @staticmethod
    def create_cone(radius: float = 1.0, height: float = 2.0, resolution: int = 20, split: int = 1, float_dtype: open3d.cuda.pybind.core.Dtype = ..., int_dtype: open3d.cuda.pybind.core.Dtype = ..., device: open3d.cuda.pybind.core.Device = ...) -> TriangleMesh:
        """
        Create a cone mesh.
        
        Args:
            radius (float, optional, default=1.0): The radius of the cone.
            height (float, optional, default=2.0): The height of the cone. The axis of the cone will be from (0, 0, 0) to (0, 0, height).
            resolution (int, optional, default=20): The circle will be split into ``resolution`` segments
            split (int, optional, default=1): The ``height`` will be split into ``split`` segments.
            float_dtype (open3d.cuda.pybind.core.Dtype, optional, default=Float32): Float_dtype, Float32 or Float64.
            int_dtype (open3d.cuda.pybind.core.Dtype, optional, default=Int64): Int_dtype, Int32 or Int64.
            device (open3d.cuda.pybind.core.Device, optional, default=CPU:0): Device of the create octahedron.
        
        Returns:
            open3d.cuda.pybind.t.geometry.TriangleMesh
        """
    @staticmethod
    def create_coordinate_frame(size: float = 1.0, origin: numpy.ndarray = ..., float_dtype: open3d.cuda.pybind.core.Dtype = ..., int_dtype: open3d.cuda.pybind.core.Dtype = ..., device: open3d.cuda.pybind.core.Device = ...) -> TriangleMesh:
        """
        Create a coordinate frame mesh.
        
        Args:
            size (float, optional, default=1.0): The size of the coordinate frame.
            origin (numpy.ndarray[numpy.float64[3, 1]], optional, default=array([0., 0., 0.])): The origin of the coordinate frame.
            float_dtype (open3d.cuda.pybind.core.Dtype, optional, default=Float32): Float_dtype, Float32 or Float64.
            int_dtype (open3d.cuda.pybind.core.Dtype, optional, default=Int64): Int_dtype, Int32 or Int64.
            device (open3d.cuda.pybind.core.Device, optional, default=CPU:0): Device of the create octahedron.
        
        Returns:
            open3d.cuda.pybind.t.geometry.TriangleMesh
        """
    @staticmethod
    def create_cylinder(radius: float = 1.0, height: float = 2.0, resolution: int = 20, split: int = 4, float_dtype: open3d.cuda.pybind.core.Dtype = ..., int_dtype: open3d.cuda.pybind.core.Dtype = ..., device: open3d.cuda.pybind.core.Device = ...) -> TriangleMesh:
        """
        Create a cylinder mesh.
        
        Args:
            radius (float, optional, default=1.0): The radius of the cylinder.
            height (float, optional, default=2.0): The height of the cylinder.The axis of the cylinder will be from (0, 0, -height/2) to (0, 0, height/2).
            resolution (int, optional, default=20):  The circle will be split into ``resolution`` segments
            split (int, optional, default=4): The ``height`` will be split into ``split`` segments.
            float_dtype (open3d.cuda.pybind.core.Dtype, optional, default=Float32): Float_dtype, Float32 or Float64.
            int_dtype (open3d.cuda.pybind.core.Dtype, optional, default=Int64): Int_dtype, Int32 or Int64.
            device (open3d.cuda.pybind.core.Device, optional, default=CPU:0): Device of the create octahedron.
        
        Returns:
            open3d.cuda.pybind.t.geometry.TriangleMesh
        """
    @staticmethod
    def create_icosahedron(radius: float = 1.0, float_dtype: open3d.cuda.pybind.core.Dtype = ..., int_dtype: open3d.cuda.pybind.core.Dtype = ..., device: open3d.cuda.pybind.core.Device = ...) -> TriangleMesh:
        """
        Create a icosahedron mesh centered at (0, 0, 0).
        
        Args:
            radius (float, optional, default=1.0): Distance from centroid to mesh vetices.
            float_dtype (open3d.cuda.pybind.core.Dtype, optional, default=Float32): Float_dtype, Float32 or Float64.
            int_dtype (open3d.cuda.pybind.core.Dtype, optional, default=Int64): Int_dtype, Int32 or Int64.
            device (open3d.cuda.pybind.core.Device, optional, default=CPU:0): Device of the create octahedron.
        
        Returns:
            open3d.cuda.pybind.t.geometry.TriangleMesh
        """
    @staticmethod
    def create_isosurfaces(volume: open3d.cuda.pybind.core.Tensor, contour_values: list[float] = [0.0], device: open3d.cuda.pybind.core.Device = ...) -> TriangleMesh:
        """
        Create a mesh from a 3D scalar field (volume) by computing the
        isosurface.
        
        This method uses the Flying Edges dual contouring method that computes the
        isosurface similar to Marching Cubes. The center of the first voxel of the
        volume is at the origin (0,0,0). The center of the voxel at index [z,y,x]
        will be at (x,y,z).
        
        Args:
            volume (open3d.core.Tensor): 3D tensor with the volume.
            contour_values (list): A list of contour values at which isosurfaces will
                be generated. The default value is 0.
            device (o3d.core.Device): The device for the returned mesh.
        
        Returns:
            A TriangleMesh with the extracted isosurfaces.
        
        
        This example shows how to create a sphere from a volume::
        
            import open3d as o3d
            import numpy as np
        
            grid_coords = np.stack(np.meshgrid(*3*[np.linspace(-1,1,num=64)], indexing='ij'), axis=-1)
            vol = 0.5 - np.linalg.norm(grid_coords, axis=-1)
            mesh = o3d.t.geometry.TriangleMesh.create_isosurfaces(vol)
            o3d.visualization.draw(mesh)
        
        
        This example shows how to convert a mesh to a signed distance field (SDF) and back to a mesh::
        
            import open3d as o3d
            import numpy as np
        
            mesh1 = o3d.t.geometry.TriangleMesh.create_torus()
            grid_coords = np.stack(np.meshgrid(*3*[np.linspace(-2,2,num=64, dtype=np.float32)], indexing='ij'), axis=-1)
        
            scene = o3d.t.geometry.RaycastingScene()
            scene.add_triangles(mesh1)
            sdf = scene.compute_signed_distance(grid_coords)
            mesh2 = o3d.t.geometry.TriangleMesh.create_isosurfaces(sdf)
        
            # Flip the triangle orientation for SDFs with negative values as "inside" and positive values as "outside"
            mesh2.triangle.indices = mesh2.triangle.indices[:,[2,1,0]]
        
            o3d.visualization.draw(mesh2)
        """
    @staticmethod
    def create_mobius(length_split: int = 70, width_split: int = 15, twists: int = 1, raidus: float = 1, flatness: float = 1, width: float = 1, scale: float = 1, float_dtype: open3d.cuda.pybind.core.Dtype = ..., int_dtype: open3d.cuda.pybind.core.Dtype = ..., device: open3d.cuda.pybind.core.Device = ...) -> TriangleMesh:
        """
        Create a Mobius strip.
        
        Args:
            length_split (int, optional, default=70): The number of segments along the Mobius strip.
            width_split (int, optional, default=15): The number of segments along the width of the Mobius strip.
            twists (int, optional, default=1): Number of twists of the Mobius strip.
            raidus (float, optional, default=1)
            flatness (float, optional, default=1): Controls the flatness/height of the Mobius strip.
            width (float, optional, default=1): Width of the Mobius strip.
            scale (float, optional, default=1): Scale the complete Mobius strip.
            float_dtype (open3d.cuda.pybind.core.Dtype, optional, default=Float32): Float_dtype, Float32 or Float64.
            int_dtype (open3d.cuda.pybind.core.Dtype, optional, default=Int64): Int_dtype, Int32 or Int64.
            device (open3d.cuda.pybind.core.Device, optional, default=CPU:0): Device of the create octahedron.
        
        Returns:
            open3d.cuda.pybind.t.geometry.TriangleMesh
        """
    @staticmethod
    def create_octahedron(radius: float = 1.0, float_dtype: open3d.cuda.pybind.core.Dtype = ..., int_dtype: open3d.cuda.pybind.core.Dtype = ..., device: open3d.cuda.pybind.core.Device = ...) -> TriangleMesh:
        """
        Create a octahedron mesh centered at (0, 0, 0).
        
        Args:
            radius (float, optional, default=1.0): Distance from centroid to mesh vetices.
            float_dtype (open3d.cuda.pybind.core.Dtype, optional, default=Float32): Float_dtype, Float32 or Float64.
            int_dtype (open3d.cuda.pybind.core.Dtype, optional, default=Int64): Int_dtype, Int32 or Int64.
            device (open3d.cuda.pybind.core.Device, optional, default=CPU:0): Device of the create octahedron.
        
        Returns:
            open3d.cuda.pybind.t.geometry.TriangleMesh
        """
    @staticmethod
    def create_sphere(radius: float = 1.0, resolution: int = 20, float_dtype: open3d.cuda.pybind.core.Dtype = ..., int_dtype: open3d.cuda.pybind.core.Dtype = ..., device: open3d.cuda.pybind.core.Device = ...) -> TriangleMesh:
        """
        Create a sphere mesh centered at (0, 0, 0).
        
        Args:
            radius (float, optional, default=1.0): The radius of the sphere.
            resolution (int, optional, default=20): The resolution of the sphere.
            float_dtype (open3d.cuda.pybind.core.Dtype, optional, default=Float32): Float_dtype, Float32 or Float64.
            int_dtype (open3d.cuda.pybind.core.Dtype, optional, default=Int64): Int_dtype, Int32 or Int64.
            device (open3d.cuda.pybind.core.Device, optional, default=CPU:0): Device of the create sphere.
        
        Returns:
            open3d.cuda.pybind.t.geometry.TriangleMesh
        """
    @staticmethod
    def create_tetrahedron(radius: float = 1.0, float_dtype: open3d.cuda.pybind.core.Dtype = ..., int_dtype: open3d.cuda.pybind.core.Dtype = ..., device: open3d.cuda.pybind.core.Device = ...) -> TriangleMesh:
        """
        Create a tetrahedron mesh centered at (0, 0, 0).
        
        Args:
            radius (float, optional, default=1.0): Distance from centroid to mesh vetices.
            float_dtype (open3d.cuda.pybind.core.Dtype, optional, default=Float32): Float_dtype, Float32 or Float64.
            int_dtype (open3d.cuda.pybind.core.Dtype, optional, default=Int64): Int_dtype, Int32 or Int64.
            device (open3d.cuda.pybind.core.Device, optional, default=CPU:0): Device of the create tetrahedron.
        
        Returns:
            open3d.cuda.pybind.t.geometry.TriangleMesh
        """
    @staticmethod
    def create_text(text: str, depth: float = 0.0, float_dtype: open3d.cuda.pybind.core.Dtype = ..., int_dtype: open3d.cuda.pybind.core.Dtype = ..., device: open3d.cuda.pybind.core.Device = ...) -> TriangleMesh:
        """
        Create a triangle mesh from a text string.
        
        Args:
            text (str): The text for generating the mesh. ASCII characters 32-126 are
                supported (includes alphanumeric characters and punctuation). In
                addition the line feed '\\n' is supported to start a new line.
            depth (float): The depth of the generated mesh. If depth is 0 then a flat mesh will be generated.
            float_dtype (o3d.core.Dtype): Float type for the vertices. Either Float32 or Float64.
            int_dtype (o3d.core.Dtype): Int type for the triangle indices. Either Int32 or Int64.
            device (o3d.core.Device): The device for the returned mesh.
        
        Returns:
            Text as triangle mesh.
        
        Example:
            This shows how to simplifify the Stanford Bunny mesh::
        
                import open3d as o3d
        
                mesh = o3d.t.geometry.TriangleMesh.create_text('Open3D', depth=1)
                o3d.visualization.draw([{'name': 'text', 'geometry': mesh}])
        """
    @staticmethod
    def create_torus(torus_radius: float = 1.0, tube_radius: float = 0.5, radial_resolution: int = 30, tubular_resolution: int = 20, float_dtype: open3d.cuda.pybind.core.Dtype = ..., int_dtype: open3d.cuda.pybind.core.Dtype = ..., device: open3d.cuda.pybind.core.Device = ...) -> TriangleMesh:
        """
        Create a torus mesh.
        
        Args:
            torus_radius (float, optional, default=1.0): The radius from the center of the torus to the center of the tube.
            tube_radius (float, optional, default=0.5): The radius of the torus tube.
            radial_resolution (int, optional, default=30): The number of segments along the radial direction.
            tubular_resolution (int, optional, default=20): The number of segments along the tubular direction.
            float_dtype (open3d.cuda.pybind.core.Dtype, optional, default=Float32): Float_dtype, Float32 or Float64.
            int_dtype (open3d.cuda.pybind.core.Dtype, optional, default=Int64): Int_dtype, Int32 or Int64.
            device (open3d.cuda.pybind.core.Device, optional, default=CPU:0): Device of the create octahedron.
        
        Returns:
            open3d.cuda.pybind.t.geometry.TriangleMesh
        """
    @staticmethod
    def from_legacy(mesh_legacy: open3d.cuda.pybind.geometry.TriangleMesh, vertex_dtype: open3d.cuda.pybind.core.Dtype = ..., triangle_dtype: open3d.cuda.pybind.core.Dtype = ..., device: open3d.cuda.pybind.core.Device = ...) -> TriangleMesh:
        """
        Create a TriangleMesh from a legacy Open3D TriangleMesh.
        """
    @staticmethod
    def from_triangle_mesh_model(model: open3d.cuda.pybind.visualization.rendering.TriangleMeshModel, vertex_dtype: open3d.cuda.pybind.core.Dtype = ..., triangle_dtype: open3d.cuda.pybind.core.Dtype = ..., device: open3d.cuda.pybind.core.Device = ...) -> dict[str, TriangleMesh]:
        """
        Convert a TriangleMeshModel (e.g. as read from a file with
        `open3d.io.read_triangle_mesh_model()`) to a dictionary of mesh names to
        triangle meshes with the specified vertex and triangle dtypes and moved to the
        specified device. Only a single material per mesh is supported. Materials common
        to multiple meshes will be duplicated. Textures (as t.geometry.Image) will use
        shared storage on the CPU (GPU resident images for textures is not yet supported).
        
        Returns:
            Dictionary of names to triangle meshes.
        
        Example:
            Converting the FlightHelmetModel to a dictionary of triangle meshes::
        
                flight_helmet = o3d.data.FlightHelmetModel()
                model = o3d.io.read_triangle_model(flight_helmet.path)
                mesh_dict = o3d.t.geometry.TriangleMesh.from_triangle_mesh_model(model)
                o3d.visualization.draw(list({"name": name, "geometry": tmesh} for
                    (name, tmesh) in mesh_dict.items()))
        """
    def __copy__(self) -> TriangleMesh:
        ...
    def __deepcopy__(self, arg0: dict) -> TriangleMesh:
        ...
    def __getstate__(self) -> tuple:
        ...
    @typing.overload
    def __init__(self, device: open3d.cuda.pybind.core.Device = ...) -> None:
        """
        Construct an empty trianglemesh on the provided ``device`` (default: 'CPU:0').
        """
    @typing.overload
    def __init__(self, vertex_positions: open3d.cuda.pybind.core.Tensor, triangle_indices: open3d.cuda.pybind.core.Tensor) -> None:
        ...
    @typing.overload
    def __init__(self, arg0: TriangleMesh) -> None:
        """
        Copy constructor
        """
    def __repr__(self) -> str:
        ...
    def __setstate__(self, arg0: tuple) -> None:
        ...
    def bake_triangle_attr_textures(self, size: int, triangle_attr: set[str], margin: float = 2.0, fill: float = 0.0, update_material: bool = True) -> dict[str, open3d.cuda.pybind.core.Tensor]:
        """
        Bake triangle attributes into textures.
        
        This function assumes a triangle attribute with name 'texture_uvs'.
        
        This function always uses the CPU device.
        
        Args:
            size (int): The width and height of the texture in pixels. Only square
                textures are supported.
        
            triangle_attr (set): The vertex attributes for which textures should be
                generated.
        
            margin (float): The margin in pixels. The recommended value is 2. The margin
                are additional pixels around the UV islands to avoid discontinuities.
        
            fill (float): The value used for filling texels outside the UV islands.
        
            update_material (bool): If true updates the material of the mesh.
                Baking a vertex attribute with the name 'albedo' will become the albedo
                texture in the material. Existing textures in the material will be
                overwritten.
        
        Returns:
            A dictionary of tensors that store the baked textures.
        
        Example:
            We generate a texture visualizing the index of the triangle to which the
            texel belongs to::
        
                import open3d as o3d
                from matplotlib import pyplot as plt
        
                box = o3d.geometry.TriangleMesh.create_box(create_uv_map=True)
                box = o3d.t.geometry.TriangleMesh.from_legacy(box)
                # Creates a triangle attribute 'albedo' which is the triangle index
                # multiplied by (255//12).
                box.triangle['albedo'] = (255//12)*np.arange(box.triangle.indices.shape[0], dtype=np.uint8)
        
                # Initialize material and bake the 'albedo' triangle attribute to a
                # texture. The texture will be automatically added to the material of
                # the object.
                box.material.set_default_properties()
                texture_tensors = box.bake_triangle_attr_textures(128, {'albedo'})
        
                # Shows the textured cube.
                o3d.visualization.draw([box])
        
                # Plot the tensor with the texture.
                plt.imshow(texture_tensors['albedo'].numpy())
        """
    def bake_vertex_attr_textures(self, size: int, vertex_attr: set[str], margin: float = 2.0, fill: float = 0.0, update_material: bool = True) -> dict[str, open3d.cuda.pybind.core.Tensor]:
        """
        Bake vertex attributes into textures.
        
        This function assumes a triangle attribute with name 'texture_uvs'.
        Only float type attributes can be baked to textures.
        
        This function always uses the CPU device.
        
        Args:
            size (int): The width and height of the texture in pixels. Only square
                textures are supported.
        
            vertex_attr (set): The vertex attributes for which textures should be
                generated.
        
            margin (float): The margin in pixels. The recommended value is 2. The margin
                are additional pixels around the UV islands to avoid discontinuities.
        
            fill (float): The value used for filling texels outside the UV islands.
        
            update_material (bool): If true updates the material of the mesh.
                Baking a vertex attribute with the name 'albedo' will become the albedo
                texture in the material. Existing textures in the material will be
                overwritten.
        
        Returns:
            A dictionary of tensors that store the baked textures.
        
        Example:
            We generate a texture storing the xyz coordinates for each texel::
        
                import open3d as o3d
                from matplotlib import pyplot as plt
        
                box = o3d.geometry.TriangleMesh.create_box(create_uv_map=True)
                box = o3d.t.geometry.TriangleMesh.from_legacy(box)
                box.vertex['albedo'] = box.vertex.positions
        
                # Initialize material and bake the 'albedo' vertex attribute to a
                # texture. The texture will be automatically added to the material of
                # the object.
                box.material.set_default_properties()
                texture_tensors = box.bake_vertex_attr_textures(128, {'albedo'})
        
                # Shows the textured cube.
                o3d.visualization.draw([box])
        
                # Plot the tensor with the texture.
                plt.imshow(texture_tensors['albedo'].numpy())
        """
    def boolean_difference(self, mesh: TriangleMesh, tolerance: float = 1e-06) -> TriangleMesh:
        """
        Computes the mesh that encompasses the volume after subtracting the volume of the second operand.
        Both meshes should be manifold.
        
        This function always uses the CPU device.
        
        Args:
            mesh (open3d.t.geometry.TriangleMesh): This is the second operand for the
                boolean operation.
        
            tolerance (float): Threshold which determines when point distances are
                considered to be 0.
        
        Returns:
            The mesh describing the difference volume.
        
        Example:
            This subtracts the sphere from the cube volume::
        
                box = o3d.geometry.TriangleMesh.create_box()
                box = o3d.t.geometry.TriangleMesh.from_legacy(box)
                sphere = o3d.geometry.TriangleMesh.create_sphere(0.8)
                sphere = o3d.t.geometry.TriangleMesh.from_legacy(sphere)
        
                ans = box.boolean_difference(sphere)
        
                o3d.visualization.draw([{'name': 'difference', 'geometry': ans}])
        """
    def boolean_intersection(self, mesh: TriangleMesh, tolerance: float = 1e-06) -> TriangleMesh:
        """
        Computes the mesh that encompasses the intersection of the volumes of two meshes.
        Both meshes should be manifold.
        
        This function always uses the CPU device.
        
        Args:
            mesh (open3d.t.geometry.TriangleMesh): This is the second operand for the
                boolean operation.
        
            tolerance (float): Threshold which determines when point distances are
                considered to be 0.
        
        Returns:
            The mesh describing the intersection volume.
        
        Example:
            This copmutes the intersection of a sphere and a cube::
        
                box = o3d.geometry.TriangleMesh.create_box()
                box = o3d.t.geometry.TriangleMesh.from_legacy(box)
                sphere = o3d.geometry.TriangleMesh.create_sphere(0.8)
                sphere = o3d.t.geometry.TriangleMesh.from_legacy(sphere)
        
                ans = box.boolean_intersection(sphere)
        
                o3d.visualization.draw([{'name': 'intersection', 'geometry': ans}])
        """
    def boolean_union(self, mesh: TriangleMesh, tolerance: float = 1e-06) -> TriangleMesh:
        """
        Computes the mesh that encompasses the union of the volumes of two meshes.
        Both meshes should be manifold.
        
        This function always uses the CPU device.
        
        Args:
            mesh (open3d.t.geometry.TriangleMesh): This is the second operand for the
                boolean operation.
        
            tolerance (float): Threshold which determines when point distances are
                considered to be 0.
        
        Returns:
            The mesh describing the union volume.
        
        Example:
            This copmutes the union of a sphere and a cube::
        
                box = o3d.geometry.TriangleMesh.create_box()
                box = o3d.t.geometry.TriangleMesh.from_legacy(box)
                sphere = o3d.geometry.TriangleMesh.create_sphere(0.8)
                sphere = o3d.t.geometry.TriangleMesh.from_legacy(sphere)
        
                ans = box.boolean_union(sphere)
        
                o3d.visualization.draw([{'name': 'union', 'geometry': ans}])
        """
    def clip_plane(self, point: open3d.cuda.pybind.core.Tensor, normal: open3d.cuda.pybind.core.Tensor) -> TriangleMesh:
        """
        Returns a new triangle mesh clipped with the plane.
        
        This method clips the triangle mesh with the specified plane.
        Parts of the mesh on the positive side of the plane will be kept and triangles
        intersected by the plane will be cut.
        
        Args:
            point (open3d.core.Tensor): A point on the plane.
        
            normal (open3d.core.Tensor): The normal of the plane. The normal points to
                the positive side of the plane for which the geometry will be kept.
        
        Returns:
            New triangle mesh clipped with the plane.
        
        
        This example shows how to create a hemisphere from a sphere::
        
            import open3d as o3d
        
            sphere = o3d.t.geometry.TriangleMesh.from_legacy(o3d.geometry.TriangleMesh.create_sphere())
            hemisphere = sphere.clip_plane(point=[0,0,0], normal=[1,0,0])
        
            o3d.visualization.draw(hemisphere)
        """
    def clone(self) -> TriangleMesh:
        """
        Returns copy of the triangle mesh on the same device.
        """
    def compute_convex_hull(self, joggle_inputs: bool = False) -> TriangleMesh:
        """
        Compute the convex hull of a point cloud using qhull. This runs on the CPU.
        
        Args:
            joggle_inputs (bool with default False): Handle precision problems by
                randomly perturbing the input data. Set to True if perturbing the input
                iis acceptable but you need convex simplicial output. If False,
                neighboring facets may be merged in case of precision problems. See
                `QHull docs <http://www.qhull.org/html/qh-impre.htm#joggle`__ for more
                details.
        
        Returns:
            TriangleMesh representing the convexh hull. This contains an
            extra vertex property "point_indices" that contains the index of the
            corresponding vertex in the original mesh.
        
        Example:
            We will load the Stanford Bunny dataset, compute and display it's convex hull::
        
                bunny = o3d.data.BunnyMesh()
                mesh = o3d.t.geometry.TriangleMesh.from_legacy(o3d.io.read_triangle_mesh(bunny.path))
                hull = mesh.compute_convex_hull()
                o3d.visualization.draw([{'name': 'bunny', 'geometry': mesh}, {'name': 'convex hull', 'geometry': hull}])
        """
    def compute_metrics(self, mesh2: TriangleMesh, metrics: list[Metric], params: MetricParameters) -> open3d.cuda.pybind.core.Tensor:
        """
        Compute various metrics between two triangle meshes. 
                    
        This uses ray casting for distance computations between a sampled point cloud 
        and a triangle mesh.  Currently, Chamfer distance, Hausdorff distance  and 
        F-Score `[Knapitsch2017] <../tutorial/reference.html#Knapitsch2017>`_ are supported. 
        The Chamfer distance is the sum of the mean distance to the nearest neighbor from
        the sampled surface points of the first mesh to the second mesh and vice versa. 
        The F-Score at the fixed threshold radius is the harmonic mean of the Precision 
        and Recall. Recall is the percentage of surface points from the first mesh that 
        have the second mesh within the threshold radius, while Precision is the 
        percentage of sampled points from the second mesh that have the first mesh 
        surface within the threhold radius.
        
        .. math::
            :nowrap:
        
            \\begin{align}
                \\text{Chamfer Distance: } d_{CD}(X,Y) &= \\frac{1}{|X|}\\sum_{i \\in X} || x_i - n(x_i, Y) || + \\frac{1}{|Y|}\\sum_{i \\in Y} || y_i - n(y_i, X) ||\\\\
                \\text{Hausdorff distance: } d_H(X,Y) &= \\max \\left\\{ \\max_{i \\in X} || x_i - n(x_i, Y) ||, \\max_{i \\in Y} || y_i - n(y_i, X) || \\right\\}\\\\
                \\text{Precision: } P(X,Y|d) &= \\frac{100}{|X|} \\sum_{i \\in X} || x_i - n(x_i, Y) || < d \\\\
                \\text{Recall: } R(X,Y|d) &= \\frac{100}{|Y|} \\sum_{i \\in Y} || y_i - n(y_i, X) || < d \\\\
                \\text{F-Score: } F(X,Y|d) &= \\frac{2 P(X,Y|d) R(X,Y|d)}{P(X,Y|d) + R(X,Y|d)} \\\\
            \\end{align}
        
        As a side effect, the triangle areas are saved in the "areas" attribute.
        
        Args:
            mesh2 (t.geometry.TriangleMesh): Other triangle mesh to compare with.
            metrics (Sequence[t.geometry.Metric]): List of Metrics to compute. Multiple metrics can be computed at once for efficiency.
            params (t.geometry.MetricParameters): This holds parameters required by different metrics.
        
        Returns:
            Tensor containing the requested metrics.
        
        Example::
        
            from open3d.t.geometry import TriangleMesh, Metric, MetricParameters
            # box is a cube with one vertex at the origin and a side length 1
            box1 = TriangleMesh.create_box()
            box2 = TriangleMesh.create_box()
            box2.vertex.positions *= 1.1
        
            # 3 faces of the cube are the same, and 3 are shifted up by 0.1
            metric_params = MetricParameters(fscore_radius=o3d.utility.FloatVector(
                (0.05, 0.15)), n_sampled_points=100000)
            metrics = box1.compute_metrics(
                box2, (Metric.ChamferDistance, Metric.HausdorffDistance, Metric.FScore),
                metric_params)
        
            print(metrics)
            np.testing.assert_allclose(metrics.cpu().numpy(), (0.1, 0.17, 50, 100),
                                       rtol=0.05)
        """
    def compute_triangle_areas(self) -> TriangleMesh:
        """
        Compute triangle areas and save it as \\"areas\\" triangle attribute.
        
        Returns:
            The mesh.
        
        Example:
        
            This code computes the overall surface area of a box::
        
                import open3d as o3d
                box = o3d.t.geometry.TriangleMesh.create_box()
                surface_area = box.compute_triangle_areas().triangle.areas.sum()
        """
    def compute_triangle_normals(self, normalized: bool = True) -> TriangleMesh:
        """
        Function to compute triangle normals, usually called before rendering.
        """
    def compute_uvatlas(self, size: int = 512, gutter: float = 1.0, max_stretch: float = 0.1666666716337204, parallel_partitions: int = 1, nthreads: int = 0) -> tuple[float, int, int]:
        """
        Creates an UV atlas and adds it as triangle attr 'texture_uvs' to the mesh.
        
        Input meshes must be manifold for this method to work.
        The algorithm is based on:
        Zhou et al, "Iso-charts: Stretch-driven Mesh Parameterization using Spectral Analysis", Eurographics Symposium on Geometry Processing (2004)
        Sander et al. "Signal-Specialized Parametrization" Europgraphics 2002
        This function always uses the CPU device.
        
        Args:
            size (int): The target size of the texture (size x size). The uv coordinates
                will still be in the range [0..1] but parameters like gutter use pixels
                as units.
            gutter (float): This is the space around the uv islands in pixels.
            max_stretch (float): The maximum amount of stretching allowed. The parameter
                range is [0..1] with 0 meaning no stretch allowed.
        
            parallel_partitions (int): The approximate number of partitions created
                before computing the UV atlas for parallelizing the computation.
                Parallelization can be enabled with values > 1. Note that
                parallelization increases the number of UV islands and can lead to results
                with lower quality.
        
            nthreads (int): The number of threads used when parallel_partitions
                is > 1. Set to 0 for automatic number of thread detection.
        
        Returns:
            This function creates a face attribute "texture_uvs" and returns a tuple
            with (max stretch, num_charts, num_partitions) storing the
            actual amount of stretch, the number of created charts, and the number of
            parallel partitions created.
        
        Example:
            This code creates a uv map for the Stanford Bunny mesh::
        
                import open3d as o3d
                bunny = o3d.data.BunnyMesh()
                mesh = o3d.t.geometry.TriangleMesh.from_legacy(o3d.io.read_triangle_mesh(bunny.path))
                mesh.compute_uvatlas()
        
                # Add a wood texture and visualize
                texture_data = o3d.data.WoodTexture()
                mesh.material.material_name = 'defaultLit'
                mesh.material.texture_maps['albedo'] = o3d.t.io.read_image(texture_data.albedo_texture_path)
                o3d.visualization.draw(mesh)
        """
    def compute_vertex_normals(self, normalized: bool = True) -> TriangleMesh:
        """
        Function to compute vertex normals, usually called before rendering.
        """
    def cpu(self) -> TriangleMesh:
        """
        Transfer the triangle mesh to CPU. If the triangle mesh is already on CPU, no copy will be performed.
        """
    def cuda(self, device_id: int = 0) -> TriangleMesh:
        """
        Transfer the triangle mesh to a CUDA device. If the triangle mesh is already on the specified CUDA device, no copy will be performed.
        """
    def extrude_linear(self, vector: open3d.cuda.pybind.core.Tensor, scale: float = 1.0, capping: bool = True) -> TriangleMesh:
        """
        Sweeps the line set along a direction vector.
        Args:
            vector (open3d.core.Tensor): The direction vector.
            scale (float): Scalar factor which essentially scales the direction vector.
        
        Returns:
            A triangle mesh with the result of the sweep operation.
        
        Example:
            This code generates a wedge from a triangle::
        
                import open3d as o3d
                triangle = o3d.t.geometry.TriangleMesh([[1.0,1.0,0.0], [0,1,0], [1,0,0]], [[0,1,2]])
                wedge = triangle.extrude_linear([0,0,1])
                o3d.visualization.draw([{'name': 'wedge', 'geometry': wedge}])
        """
    def extrude_rotation(self, angle: float, axis: open3d.cuda.pybind.core.Tensor, resolution: int = 16, translation: float = 0.0, capping: bool = True) -> TriangleMesh:
        """
        Sweeps the triangle mesh rotationally about an axis.
        Args:
            angle (float): The rotation angle in degree.
            axis (open3d.core.Tensor): The rotation axis.
            resolution (int): The resolution defines the number of intermediate sweeps
                about the rotation axis.
            translation (float): The translation along the rotation axis.
        
        Returns:
            A triangle mesh with the result of the sweep operation.
        
        Example:
            This code generates a spring with a triangle cross-section::
        
                import open3d as o3d
        
                mesh = o3d.t.geometry.TriangleMesh([[1,1,0], [0.7,1,0], [1,0.7,0]], [[0,1,2]])
                spring = mesh.extrude_rotation(3*360, [0,1,0], resolution=3*16, translation=2)
                o3d.visualization.draw([{'name': 'spring', 'geometry': spring}])
        """
    def fill_holes(self, hole_size: float = 1000000.0) -> TriangleMesh:
        """
        Fill holes by triangulating boundary edges.
        
        This function always uses the CPU device.
        
        Args:
            hole_size (float): This is the approximate threshold for filling holes.
                The value describes the maximum radius of holes to be filled.
        
        Returns:
            New mesh after filling holes.
        
        Example:
            Fill holes at the bottom of the Stanford Bunny mesh::
        
                bunny = o3d.data.BunnyMesh()
                mesh = o3d.t.geometry.TriangleMesh.from_legacy(o3d.io.read_triangle_mesh(bunny.path))
                filled = mesh.fill_holes()
                o3d.visualization.draw([{'name': 'filled', 'geometry': ans}])
        """
    def get_axis_aligned_bounding_box(self) -> AxisAlignedBoundingBox:
        """
        Create an axis-aligned bounding box from vertex attribute 'positions'.
        """
    def get_center(self) -> open3d.cuda.pybind.core.Tensor:
        """
        Returns the center for point coordinates.
        """
    def get_max_bound(self) -> open3d.cuda.pybind.core.Tensor:
        """
        Returns the max bound for point coordinates.
        """
    def get_min_bound(self) -> open3d.cuda.pybind.core.Tensor:
        """
        Returns the min bound for point coordinates.
        """
    def get_non_manifold_edges(self, allow_boundary_edges: bool = True) -> open3d.cuda.pybind.core.Tensor:
        """
        Returns the list consisting of non-manifold edges.
        """
    def get_oriented_bounding_box(self) -> OrientedBoundingBox:
        """
        Create an oriented bounding box from vertex attribute 'positions'.
        """
    def get_surface_area(self) -> float:
        """
        Computes the surface area of the mesh, i.e., the sum of the individual triangle surfaces.
        
        Example:
            This computes the surface area of the Stanford Bunny::
                bunny = o3d.data.BunnyMesh()
                mesh = o3d.t.io.read_triangle_mesh(bunny.path)
                print('The surface area is', mesh.get_surface_area())
        
        Returns:
            A scalar describing the surface area of the mesh.
        """
    def normalize_normals(self) -> TriangleMesh:
        """
        Normalize both triangle normals and vertex normals to length 1.
        """
    def pca_partition(self, max_faces: int) -> int:
        """
        Partition the mesh by recursively doing PCA.
        
        This function creates a new face attribute with the name "partition_ids" storing
        the partition id for each face.
        
        Args:
            max_faces (int): The maximum allowed number of faces in a partition.
        
        
        Example:
        
            This code partitions a mesh such that each partition contains at most 20k
            faces::
        
                import open3d as o3d
                import numpy as np
                bunny = o3d.data.BunnyMesh()
                mesh = o3d.t.geometry.TriangleMesh.from_legacy(o3d.io.read_triangle_mesh(bunny.path))
                num_partitions = mesh.pca_partition(max_faces=20000)
        
                # print the partition ids and the number of faces for each of them.
                print(np.unique(mesh.triangle.partition_ids.numpy(), return_counts=True))
        """
    def project_images_to_albedo(self, images: list[Image], intrinsic_matrices: list[open3d.cuda.pybind.core.Tensor], extrinsic_matrices: list[open3d.cuda.pybind.core.Tensor], tex_size: int = 1024, update_material: bool = True) -> Image:
        """
        Create an albedo for the triangle mesh using calibrated images. The triangle
        mesh must have texture coordinates ("texture_uvs" triangle attribute). This works
        by back projecting the images onto the texture surface. Overlapping images are
        blended together in the resulting albedo. For best results, use images captured
        with exposure and white balance lock to reduce the chance of seams in the output
        texture.
        
        This function is only supported on the CPU.
        
        Args:
            images (List[open3d.t.geometry.Image]): List of images.
            intrinsic_matrices (List[open3d.core.Tensor]): List of (3,3) intrinsic matrices describing
                the pinhole camera.
            extrinsic_matrices (List[open3d.core.Tensor]): List of (4,4) extrinsic matrices describing
                the position and orientation of the camera.
            tex_size (int): Output albedo texture size. This is a square image, so
                only one side is needed.
            update_material (bool): Whether to update the material of the triangle
                mesh, possibly overwriting an existing albedo texture.
        
        Returns:
            Image with albedo texture.
        """
    def remove_non_manifold_edges(self) -> TriangleMesh:
        """
        Function that removes all non-manifold edges, by
        successively deleting  triangles with the smallest surface
        area adjacent to the non-manifold edge until the number of
        adjacent triangles to the edge is `<= 2`.
        
        Returns:
            The mesh.
        """
    def remove_unreferenced_vertices(self) -> TriangleMesh:
        """
        Removes unreferenced vertices from the mesh in-place.
        """
    def rotate(self, R: open3d.cuda.pybind.core.Tensor, center: open3d.cuda.pybind.core.Tensor) -> TriangleMesh:
        """
        Rotate points and normals (if exist).
        """
    def sample_points_uniformly(self, number_of_points: int, use_triangle_normal: bool = False) -> PointCloud:
        """
        Sample points uniformly from the triangle mesh surface and return as a PointCloud. Normals and colors are interpolated from the triangle mesh. If texture_uvs and albedo are present, these are used to estimate the sampled point color, otherwise vertex colors are used, if present. During sampling, triangle areas are computed and saved in the "areas" attribute.
        
        Args:
            number_of_points (int): The number of points to sample.
            use_triangle_normal (bool): If true, use the triangle normal as the normal of the sampled point. By default, the vertex normals are interpolated instead.
        
        Returns:
            Sampled point cloud, with colors and normals, if available.
        
        Example::
        
            mesh = o3d.t.geometry.TriangleMesh.create_box()
            mesh.vertex.colors = mesh.vertex.positions.clone()
            pcd = mesh.sample_points_uniformly(100000)
            o3d.visualization.draw([mesh, pcd], point_size=5, show_ui=True, show_skybox=False)
        """
    def scale(self, scale: float, center: open3d.cuda.pybind.core.Tensor) -> TriangleMesh:
        """
        Scale points.
        """
    def select_by_index(self, indices: open3d.cuda.pybind.core.Tensor, copy_attributes: bool = True) -> TriangleMesh:
        """
        Returns a new mesh with the vertices selected according to the indices list.
        If an item from the indices list exceeds the max vertex number of the mesh
        or has a negative value, it is ignored.
        
        Args:
            indices (open3d.core.Tensor): An integer list of indices. Duplicates are
            allowed, but ignored. Signed and unsigned integral types are accepted.
            copy_attributes (bool): Indicates if vertex attributes (other than
            positions) and triangle attributes (other than indices) should be copied to
            the returned mesh.
        
        Returns:
            A new mesh with the selected vertices and faces built from these vertices.
            If the original mesh is empty, return an empty mesh.
        
        Example:
        
            This code selects the top face of a box, which has indices [2, 3, 6, 7]::
        
                import open3d as o3d
                import numpy as np
                box = o3d.t.geometry.TriangleMesh.create_box()
                top_face = box.select_by_index([2, 3, 6, 7])
        """
    def select_faces_by_mask(self, mask: open3d.cuda.pybind.core.Tensor) -> TriangleMesh:
        """
        Returns a new mesh with the faces selected by a boolean mask.
        
        Args:
            mask (open3d.core.Tensor): A boolean mask with the shape (N) with N as the
                number of faces in the mesh.
        
        Returns:
            A new mesh with the selected faces. If the original mesh is empty, return an empty mesh.
        
        Example:
        
            This code partitions the mesh using PCA and then visualized the individual
            parts::
        
                import open3d as o3d
                import numpy as np
                bunny = o3d.data.BunnyMesh()
                mesh = o3d.t.geometry.TriangleMesh.from_legacy(o3d.io.read_triangle_mesh(bunny.path))
                num_partitions = mesh.pca_partition(max_faces=20000)
        
                parts = []
                for i in range(num_partitions):
                    mask = mesh.triangle.partition_ids == i
                    part = mesh.select_faces_by_mask(mask)
                    part.vertex.colors = np.tile(np.random.rand(3), (part.vertex.positions.shape[0],1))
                    parts.append(part)
        
                o3d.visualization.draw(parts)
        """
    def simplify_quadric_decimation(self, target_reduction: float, preserve_volume: bool = True) -> TriangleMesh:
        """
        Function to simplify mesh using Quadric Error Metric Decimation by Garland and Heckbert.
        
        This function always uses the CPU device.
        
        Args:
            target_reduction (float): The factor of triangles to delete, i.e., setting
                this to 0.9 will return a mesh with about 10% of the original triangle
                count. It is not guaranteed that the target reduction factor will be
                reached.
        
            preserve_volume (bool): If set to True this enables volume preservation
                which reduces the error in triangle normal direction.
        
        Returns:
            Simplified TriangleMesh.
        
        Example:
            This shows how to simplifify the Stanford Bunny mesh::
        
                bunny = o3d.data.BunnyMesh()
                mesh = o3d.t.geometry.TriangleMesh.from_legacy(o3d.io.read_triangle_mesh(bunny.path))
                simplified = mesh.simplify_quadric_decimation(0.99)
                o3d.visualization.draw([{'name': 'bunny', 'geometry': simplified}])
        """
    def slice_plane(self, point: open3d.cuda.pybind.core.Tensor, normal: open3d.cuda.pybind.core.Tensor, contour_values: list[float] = [0.0]) -> LineSet:
        """
        Returns a line set with the contour slices defined by the plane and values.
        
        This method generates slices as LineSet from the mesh at specific contour
        values with respect to a plane.
        
        Args:
            point (open3d.core.Tensor): A point on the plane.
            normal (open3d.core.Tensor): The normal of the plane.
            contour_values (list): A list of contour values at which slices will be
                generated. The value describes the signed distance to the plane.
        
        Returns:
            LineSet with the extracted contours.
        
        
        This example shows how to create a hemisphere from a sphere::
        
            import open3d as o3d
            import numpy as np
        
            bunny = o3d.data.BunnyMesh()
            mesh = o3d.t.geometry.TriangleMesh.from_legacy(o3d.io.read_triangle_mesh(bunny.path))
            contours = mesh.slice_plane([0,0,0], [0,1,0], np.linspace(0,0.2))
            o3d.visualization.draw([{'name': 'bunny', 'geometry': contours}])
        """
    def to(self, device: open3d.cuda.pybind.core.Device, copy: bool = False) -> TriangleMesh:
        """
        Transfer the triangle mesh to a specified device.
        """
    def to_legacy(self) -> open3d.cuda.pybind.geometry.TriangleMesh:
        """
        Convert to a legacy Open3D TriangleMesh.
        """
    def to_mitsuba(self, name, bsdf = None):
        """
        Convert Open3D TriangleMesh to Mitsuba Mesh.
        
            Converts an Open3D TriangleMesh to a Mitsuba Mesh which can be used directly
            in a Mitsbua scene. The TriangleMesh's material will be converted to a
            Mitsuba Principled BSDF and assigned to the Mitsuba Mesh. Optionally, the
            user may provide a Mitsuba BSDF to be used instead of converting the Open3D
            material.
        
            Args:
                name (str): Name for the Mitsuba Mesh. Used by Mitsuba as an identifier
        
                bsdf (default None): If a Mitsuba BSDF is supplied it will be used as
                the BSDF for the converted mesh. Otherwise, the TriangleMesh's material
                will be converted to Mitsuba Principled BSDF.
        
            Returns:
                A Mitsuba Mesh (with associated BSDF) ready for use in a Mitsuba scene.
            
        """
    def transform(self, transformation: open3d.cuda.pybind.core.Tensor) -> TriangleMesh:
        """
        Transforms the points and normals (if exist).
        """
    def translate(self, translation: open3d.cuda.pybind.core.Tensor, relative: bool = True) -> TriangleMesh:
        """
        Translates points.
        """
    @property
    def triangle(self) -> TensorMap:
        ...
    @property
    def vertex(self) -> TensorMap:
        ...
class VectorMetric:
    __hash__: typing.ClassVar[None] = None
    def __bool__(self: list[Metric]) -> bool:
        """
        Check whether the list is nonempty
        """
    def __contains__(self: list[Metric], x: Metric) -> bool:
        """
        Return true the container contains ``x``
        """
    @typing.overload
    def __delitem__(self: list[Metric], arg0: int) -> None:
        """
        Delete the list elements at index ``i``
        """
    @typing.overload
    def __delitem__(self: list[Metric], arg0: slice) -> None:
        """
        Delete list elements using a slice object
        """
    def __eq__(self: list[Metric], arg0: list[Metric]) -> bool:
        ...
    @typing.overload
    def __getitem__(self: list[Metric], s: slice) -> list[Metric]:
        """
        Retrieve list elements using a slice object
        """
    @typing.overload
    def __getitem__(self: list[Metric], arg0: int) -> Metric:
        ...
    @typing.overload
    def __init__(self) -> None:
        ...
    @typing.overload
    def __init__(self, arg0: list[Metric]) -> None:
        """
        Copy constructor
        """
    @typing.overload
    def __init__(self, arg0: typing.Iterable) -> None:
        ...
    def __iter__(self: list[Metric]) -> typing.Iterator[Metric]:
        ...
    def __len__(self: list[Metric]) -> int:
        ...
    def __ne__(self: list[Metric], arg0: list[Metric]) -> bool:
        ...
    @typing.overload
    def __setitem__(self: list[Metric], arg0: int, arg1: Metric) -> None:
        ...
    @typing.overload
    def __setitem__(self: list[Metric], arg0: slice, arg1: list[Metric]) -> None:
        """
        Assign list elements using a slice object
        """
    def append(self: list[Metric], x: Metric) -> None:
        """
        Add an item to the end of the list
        """
    def clear(self: list[Metric]) -> None:
        """
        Clear the contents
        """
    def count(self: list[Metric], x: Metric) -> int:
        """
        Return the number of times ``x`` appears in the list
        """
    @typing.overload
    def extend(self: list[Metric], L: list[Metric]) -> None:
        """
        Extend the list by appending all the items in the given list
        """
    @typing.overload
    def extend(self: list[Metric], L: typing.Iterable) -> None:
        """
        Extend the list by appending all the items in the given list
        """
    def insert(self: list[Metric], i: int, x: Metric) -> None:
        """
        Insert an item at a given position.
        """
    @typing.overload
    def pop(self: list[Metric]) -> Metric:
        """
        Remove and return the last item
        """
    @typing.overload
    def pop(self: list[Metric], i: int) -> Metric:
        """
        Remove and return the item at index ``i``
        """
    def remove(self: list[Metric], x: Metric) -> None:
        """
        Remove the first item from the list whose value is x. It is an error if there is no such item.
        """
class VoxelBlockGrid:
    """
    A voxel block grid is a sparse grid of voxel blocks. Each voxel block is a dense 3D array, preserving local data distribution. If the block_resolution is set to 1, then the VoxelBlockGrid degenerates to a sparse voxel grid.
    """
    @staticmethod
    def load(file_name: str) -> VoxelBlockGrid:
        """
        Load a voxel block grid from a npz file.
        """
    def __init__(self, attr_names: list[str], attr_dtypes: list[open3d.cuda.pybind.core.Dtype], attr_channels: list[open3d.cuda.pybind.core.SizeVector], voxel_size: float = 0.0058, block_resolution: int = 16, block_count: int = 10000, device: open3d.cuda.pybind.core.Device = ...) -> None:
        ...
    def attribute(self, attribute_name: str) -> open3d.cuda.pybind.core.Tensor:
        """
        Get the attribute tensor to be indexed with voxel_indices.
        """
    @typing.overload
    def compute_unique_block_coordinates(self, depth: Image, intrinsic: open3d.cuda.pybind.core.Tensor, extrinsic: open3d.cuda.pybind.core.Tensor, depth_scale: float = 1000.0, depth_max: float = 3.0, trunc_voxel_multiplier: float = 8.0) -> open3d.cuda.pybind.core.Tensor:
        """
        Get a (3, M) active block coordinates from a depth image, with potential duplicates removed.Note: these coordinates are not activated in the internal sparse voxel block. They need to be inserted in the hash map.
        """
    @typing.overload
    def compute_unique_block_coordinates(self, pcd: PointCloud, trunc_voxel_multiplier: float = 8.0) -> open3d.cuda.pybind.core.Tensor:
        """
        Obtain active block coordinates from a point cloud.
        """
    def cpu(self) -> VoxelBlockGrid:
        """
        Transfer the voxel block grid to CPU. If the voxel block grid is already on CPU, no copy will be performed.
        """
    def cuda(self, device_id: int = 0) -> VoxelBlockGrid:
        """
        Transfer the voxel block grid to a CUDA device. If the voxel block grid is already on the specified CUDA device, no copy will be performed.
        """
    def extract_point_cloud(self, weight_threshold: float = 3.0, estimated_point_number: int = -1) -> PointCloud:
        """
        Specific operation for TSDF volumes.Extract point cloud at isosurface points.
        """
    def extract_triangle_mesh(self, weight_threshold: float = 3.0, estimated_vertex_number: int = -1) -> TriangleMesh:
        """
        Specific operation for TSDF volumes.Extract triangle mesh at isosurface points.
        """
    def hashmap(self) -> open3d.cuda.pybind.core.HashMap:
        """
        Get the underlying hash map from 3d block coordinates to block voxel grids.
        """
    @typing.overload
    def integrate(self, block_coords: open3d.cuda.pybind.core.Tensor, depth: Image, color: Image, depth_intrinsic: open3d.cuda.pybind.core.Tensor, color_intrinsic: open3d.cuda.pybind.core.Tensor, extrinsic: open3d.cuda.pybind.core.Tensor, depth_scale: float = 1000.0, depth_max: float = 3.0, trunc_voxel_multiplier: float = 8.0) -> None:
        """
        Specific operation for TSDF volumes.Integrate an RGB-D frame in the selected block coordinates using pinhole camera model.
        """
    @typing.overload
    def integrate(self, block_coords: open3d.cuda.pybind.core.Tensor, depth: Image, color: Image, intrinsic: open3d.cuda.pybind.core.Tensor, extrinsic: open3d.cuda.pybind.core.Tensor, depth_scale: float = 1000.0, depth_max: float = 3.0, trunc_voxel_multiplier: float = 8.0) -> None:
        """
        Specific operation for TSDF volumes.Integrate an RGB-D frame in the selected block coordinates using pinhole camera model.
        """
    @typing.overload
    def integrate(self, block_coords: open3d.cuda.pybind.core.Tensor, depth: Image, intrinsic: open3d.cuda.pybind.core.Tensor, extrinsic: open3d.cuda.pybind.core.Tensor, depth_scale: float = 1000.0, depth_max: float = 3.0, trunc_voxel_multiplier: float = 8.0) -> None:
        """
        Specific operation for TSDF volumes.Similar to RGB-D integration, but only applied to depth images.
        """
    def ray_cast(self, block_coords: open3d.cuda.pybind.core.Tensor, intrinsic: open3d.cuda.pybind.core.Tensor, extrinsic: open3d.cuda.pybind.core.Tensor, width: int, height: int, render_attributes: list[str] = ['depth', 'color'], depth_scale: float = 1000.0, depth_min: float = 0.10000000149011612, depth_max: float = 3.0, weight_threshold: float = 3.0, trunc_voxel_multiplier: float = 8.0, range_map_down_factor: int = 8) -> TensorMap:
        """
        Specific operation for TSDF volumes.Perform volumetric ray casting in the selected block coordinates.The block coordinates in the frustum can be taken fromcompute_unique_block_coordinatesAll the block coordinates can be taken from hashmap().key_tensor()
        """
    def save(self, file_name: str) -> None:
        """
        Save the voxel block grid to a npz file.
        """
    def to(self, device: open3d.cuda.pybind.core.Device, copy: bool = False) -> VoxelBlockGrid:
        """
        Transfer the voxel block grid to a specified device.
        """
    def voxel_coordinates(self, voxel_indices: open3d.cuda.pybind.core.Tensor) -> open3d.cuda.pybind.core.Tensor:
        """
        Get a (3, hashmap.Size() * resolution^3) coordinate tensor of activevoxels per block, used for geometry transformation jointly with   indices from voxel_indices.                                       Example:                                                          For a voxel block grid with (2, 2, 2) block resolution,           if the active block coordinates are {(-1, 3, 2), (0, 2, 4)},      the returned result will be a (3, 2 x 8) tensor given by:         {                                                                 key_tensor[voxel_indices[0]] * block_resolution_ + voxel_indices[1] key_tensor[voxel_indices[0]] * block_resolution_ + voxel_indices[2] key_tensor[voxel_indices[0]] * block_resolution_ + voxel_indices[3] }                                                                 Note: the coordinates are VOXEL COORDINATES in Int64. To access metriccoordinates, multiply by voxel size.
        """
    @typing.overload
    def voxel_coordinates_and_flattened_indices(self, buf_indices: open3d.cuda.pybind.core.Tensor) -> tuple[open3d.cuda.pybind.core.Tensor, open3d.cuda.pybind.core.Tensor]:
        """
        Get a (buf_indices.shape[0] * resolution^3, 3), Float32 voxel coordinate tensor,and a (buf_indices.shape[0] * resolution^3, 1), Int64 voxel index tensor.
        """
    @typing.overload
    def voxel_coordinates_and_flattened_indices(self) -> tuple[open3d.cuda.pybind.core.Tensor, open3d.cuda.pybind.core.Tensor]:
        """
        Get a (hashmap.size() * resolution^3, 3), Float32 voxel coordinate tensor,and a (hashmap.size() * resolution^3, 1), Int64 voxel index tensor.
        """
    @typing.overload
    def voxel_indices(self, arg0: open3d.cuda.pybind.core.Tensor) -> open3d.cuda.pybind.core.Tensor:
        """
        Get a (4, N), Int64 index tensor for input buffer indices, used for advanced indexing.   Returned index tensor can access selected value bufferin the order of  (buf_index, index_voxel_x, index_voxel_y, index_voxel_z).       Example:                                                        For a voxel block grid with (2, 2, 2) block resolution,         if the active block coordinates are at buffer index {(2, 4)} given by active_indices() from the underlying hash map,         the returned result will be a (4, 2 x 8) tensor:                {                                                               (2, 0, 0, 0), (2, 1, 0, 0), (2, 0, 1, 0), (2, 1, 1, 0),         (2, 0, 0, 1), (2, 1, 0, 1), (2, 0, 1, 1), (2, 1, 1, 1),         (4, 0, 0, 0), (4, 1, 0, 0), (4, 0, 1, 0), (4, 1, 1, 0),         (4, 0, 0, 1), (4, 1, 0, 1), (4, 0, 1, 1), (4, 1, 1, 1),         }Note: the slicing order is z-y-x.
        """
    @typing.overload
    def voxel_indices(self) -> open3d.cuda.pybind.core.Tensor:
        """
        Get a (4, N) Int64 idnex tensor for all the active voxels stored in the hash map, used for advanced indexing.
        """
ChamferDistance: Metric
Cubic: InterpType
FScore: Metric
HausdorffDistance: Metric
Lanczos: InterpType
Linear: InterpType
Nearest: InterpType
Super: InterpType
