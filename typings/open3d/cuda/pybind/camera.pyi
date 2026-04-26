from __future__ import annotations
import numpy
import typing

__all__: list[str] = [
    "Kinect2ColorCameraDefault",
    "Kinect2DepthCameraDefault",
    "PinholeCameraIntrinsic",
    "PinholeCameraIntrinsicParameters",
    "PinholeCameraParameters",
    "PinholeCameraTrajectory",
    "PrimeSenseDefault",
]

class PinholeCameraIntrinsic:
    """
    PinholeCameraIntrinsic class stores intrinsic camera matrix, and image height and width.
    """
    def __copy__(self) -> PinholeCameraIntrinsic: ...
    def __deepcopy__(self, arg0: dict) -> PinholeCameraIntrinsic: ...
    @typing.overload
    def __init__(self) -> None:
        """
        Default constructor
        """
    @typing.overload
    def __init__(self, arg0: PinholeCameraIntrinsic) -> None:
        """
            Copy constructor

        Args:
            arg0 (open3d.cuda.pybind.camera.PinholeCameraIntrinsic)
        """
    @typing.overload
    def __init__(self, width: int, height: int, intrinsic_matrix: numpy.ndarray) -> None:
        """
        Args:
            width (int)
            height (int)
            intrinsic_matrix (numpy.ndarray[numpy.float64[3, 3]])
        """
    @typing.overload
    def __init__(self, width: int, height: int, fx: float, fy: float, cx: float, cy: float) -> None:
        """
        Args:
            width (int)
            height (int)
            fx (float)
            fy (float)
            cx (float)
            cy (float)
        """
    @typing.overload
    def __init__(self, param: PinholeCameraIntrinsicParameters) -> None:
        """
        Args:
            param (open3d.cuda.pybind.camera.PinholeCameraIntrinsicParameters)
        """
    def __repr__(self) -> str: ...
    def get_focal_length(self) -> tuple[float, float]:
        """
        Returns the focal length in a tuple of X-axis and Y-axisfocal lengths.

        Returns:
            tuple[float, float]
        """
    def get_principal_point(self) -> tuple[float, float]:
        """
        Returns the principle point in a tuple of X-axis and.Y-axis principle points

        Returns:
            tuple[float, float]
        """
    def get_skew(self) -> float:
        """
        Returns the skew.

        Returns:
            float
        """
    def is_valid(self) -> bool:
        """
        Returns True iff both the width and height are greater than 0.

        Returns:
            bool
        """
    def set_intrinsics(self, width: int, height: int, fx: float, fy: float, cx: float, cy: float) -> None:
        """
        Set camera intrinsic parameters.

        Args:
            width (int): Width of the image.
            height (int): Height of the image.
            fx (float): X-axis focal length
            fy (float): Y-axis focal length.
            cx (float): X-axis principle point.
            cy (float): Y-axis principle point.

        Returns:
            None
        """
    @property
    def height(self) -> int:
        """
        int: Height of the image.
        """
    @height.setter
    def height(self, arg0: int) -> None: ...
    @property
    def intrinsic_matrix(self) -> numpy.ndarray:
        """
        3x3 numpy array: Intrinsic camera matrix ``[[fx, 0, cx], [0, fy, cy], [0, 0, 1]]``
        """
    @intrinsic_matrix.setter
    def intrinsic_matrix(self, arg0: numpy.ndarray) -> None: ...
    @property
    def width(self) -> int:
        """
        int: Width of the image.
        """
    @width.setter
    def width(self, arg0: int) -> None: ...

class PinholeCameraIntrinsicParameters:
    """
    Enum class that contains default camera intrinsic parameters for different sensors.
    """

    Kinect2ColorCameraDefault: typing.ClassVar[PinholeCameraIntrinsicParameters]
    Kinect2DepthCameraDefault: typing.ClassVar[PinholeCameraIntrinsicParameters]
    PrimeSenseDefault: typing.ClassVar[PinholeCameraIntrinsicParameters]
    __members__: typing.ClassVar[dict[str, PinholeCameraIntrinsicParameters]]
    def __eq__(self, other: typing.Any) -> bool: ...
    def __ge__(self, other: typing.Any) -> bool: ...
    def __getstate__(self) -> int: ...
    def __gt__(self, other: typing.Any) -> bool: ...
    def __hash__(self) -> int: ...
    def __index__(self) -> int: ...
    def __init__(self, value: int) -> None: ...
    def __int__(self) -> int: ...
    def __le__(self, other: typing.Any) -> bool: ...
    def __lt__(self, other: typing.Any) -> bool: ...
    def __ne__(self, other: typing.Any) -> bool: ...
    def __repr__(self) -> str: ...
    def __setstate__(self, state: int) -> None: ...
    def __str__(self) -> str: ...
    @property
    def name(self) -> str: ...
    @property
    def value(self) -> int: ...

class PinholeCameraParameters:
    """
    Contains both intrinsic and extrinsic pinhole camera parameters.
    """
    def __copy__(self) -> PinholeCameraParameters: ...
    def __deepcopy__(self, arg0: dict) -> PinholeCameraParameters: ...
    @typing.overload
    def __init__(self) -> None:
        """
        Default constructor
        """
    @typing.overload
    def __init__(self, arg0: PinholeCameraParameters) -> None:
        """
        Copy constructor
        """
    def __repr__(self) -> str: ...
    @property
    def extrinsic(self) -> numpy.ndarray:
        """
        4x4 numpy array: Camera extrinsic parameters.
        """
    @extrinsic.setter
    def extrinsic(self, arg0: numpy.ndarray) -> None: ...
    @property
    def intrinsic(self) -> PinholeCameraIntrinsic:
        """
        ``open3d.camera.PinholeCameraIntrinsic``: PinholeCameraIntrinsic object.
        """
    @intrinsic.setter
    def intrinsic(self, arg0: PinholeCameraIntrinsic) -> None: ...

class PinholeCameraTrajectory:
    """
    Contains a list of ``PinholeCameraParameters``, useful to storing trajectories.
    """
    def __copy__(self) -> PinholeCameraTrajectory: ...
    def __deepcopy__(self, arg0: dict) -> PinholeCameraTrajectory: ...
    @typing.overload
    def __init__(self) -> None:
        """
        Default constructor
        """
    @typing.overload
    def __init__(self, arg0: PinholeCameraTrajectory) -> None:
        """
        Copy constructor
        """
    def __repr__(self) -> str: ...
    @property
    def parameters(self) -> list[PinholeCameraParameters]:
        """
        ``List(open3d.camera.PinholeCameraParameters)``: List of PinholeCameraParameters objects.
        """
    @parameters.setter
    def parameters(self, arg0: list[PinholeCameraParameters]) -> None: ...

Kinect2ColorCameraDefault: PinholeCameraIntrinsicParameters
Kinect2DepthCameraDefault: PinholeCameraIntrinsicParameters
PrimeSenseDefault: PinholeCameraIntrinsicParameters
