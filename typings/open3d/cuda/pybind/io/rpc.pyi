from __future__ import annotations
import open3d.cuda.pybind.camera
import open3d.cuda.pybind.geometry
import open3d.cuda.pybind.t.geometry
import typing

__all__: list[str] = [
    "BufferConnection",
    "Connection",
    "data_buffer_to_meta_geometry",
    "destroy_zmq_context",
    "set_active_camera",
    "set_legacy_camera",
    "set_mesh_data",
    "set_point_cloud",
    "set_time",
    "set_triangle_mesh",
]

class BufferConnection(_ConnectionBase):
    """

    A connection writing to a memory buffer.
    """
    def __init__(self) -> None: ...
    def get_buffer(self) -> bytes:
        """
        Returns a copy of the buffer.
        """

class Connection(_ConnectionBase):
    """

    The default connection class which uses a ZeroMQ socket.
    """
    def __init__(
        self, address: str = "tcp://127.0.0.1:51454", connect_timeout: int = 5000, timeout: int = 10000
    ) -> None:
        """
        Creates a connection object
        """

class _ConnectionBase:
    pass

class _DummyReceiver:
    """
    Dummy receiver for the server side receiving requests from a client.
    """
    def __init__(self, address: str = "tcp://127.0.0.1:51454", timeout: int = 10000) -> None:
        """
        Creates the receiver object which can be used for testing connections.
        """
    def start(self) -> None:
        """
        Starts the receiver mainloop in a new thread.
        """
    def stop(self) -> None:
        """
        Stops the receiver mainloop and joins the thread. This function blocks until the mainloop is done with processing messages that have already been received.
        """

def data_buffer_to_meta_geometry(data: str) -> tuple[str, float, open3d.cuda.pybind.t.geometry.Geometry]:
    """
    This function returns the geometry, the path and the time stored in a
    SetMeshData message. data must contain the Request header message followed
    by the SetMeshData message. The function returns None for the geometry if not
    successful.
    """

def destroy_zmq_context() -> None:
    """
    Destroys the ZMQ context.
    """

def set_active_camera(path: str, connection: _ConnectionBase = None) -> bool:
    """
    Sets the object with the specified path as the active camera.

    Args:
        path (str): A path descriptor, e.g., 'mygroup/camera'.
        connection (open3d.cuda.pybind.io.rpc._ConnectionBase, optional, default=None): A Connection object. Use None to automatically create the connection.

    Returns:
        bool
    """

def set_legacy_camera(
    camera: open3d.cuda.pybind.camera.PinholeCameraParameters,
    path: str = "",
    time: int = 0,
    layer: str = "",
    connection: _ConnectionBase = None,
) -> bool:
    """
    Sends a PinholeCameraParameters object.

    Args:
        camera (open3d.cuda.pybind.camera.PinholeCameraParameters)
        path (str, optional, default=''): A path descriptor, e.g., 'mygroup/camera'.
        time (int, optional, default=0): The time associated with this data.
        layer (str, optional, default=''): The layer associated with this data.
        connection (open3d.cuda.pybind.io.rpc._ConnectionBase, optional, default=None): A Connection object. Use None to automatically create the connection.

    Returns:
        bool
    """

def set_mesh_data(*args, **kwargs) -> bool:
    """
    Sends a set_mesh_data message.

    Args:
        path (str, optional, default=''): A path descriptor, e.g., 'mygroup/points'.
        time (int, optional, default=0): The time associated with this data.
        layer (str, optional, default=''): The layer associated with this data.
        vertices (open3d.cuda.pybind.core.Tensor, optional, default=0-element Tensor Tensor[shape={0}, stride={1}, Float32): Tensor defining the vertices.
         ()
        vertex_attributes (dict[str, open3d.cuda.pybind.core.Tensor], optional, default={}): dict of Tensors with vertex attributes.
        faces (open3d.cuda.pybind.core.Tensor, optional, default=0-element Tensor Tensor[shape={0}, stride={1}, Int32): Tensor defining the faces with vertex indices.
         ()
        face_attributes (dict[str, open3d.cuda.pybind.core.Tensor], optional, default={}): dict of Tensors with face attributes.
        lines (open3d.cuda.pybind.core.Tensor, optional, default=0-element Tensor Tensor[shape={0}, stride={1}, Int32): Tensor defining lines with vertex indices.
         ()
        line_attributes (dict[str, open3d.cuda.pybind.core.Tensor], optional, default={}): dict of Tensors with line attributes.
        material (str, optional, default=''): Basic Material for geometry drawing.  Must be non-empty if any material attributes or texture maps are provided.
        material_scalar_attributes (dict[str, float], optional, default={}): dict of material scalar attributes for geometry drawing (e.g. ``point_size``, ``line_width`` or ``base_reflectance``).
        material_vector_attributes (dict[str, Annotated[list[float], FixedSize(4)]], optional, default={}): dict of material Vector4f attributes for geometry drawing (e.g. ``base_color`` or ``absorption_color``)
        texture_maps (dict[str, open3d.cuda.pybind.t.geometry.Image], optional, default={}): dict of Images with textures.
        o3d_type (str, optional, default=''): The type of the geometry. This is one of
            ``PointCloud``, ``LineSet``, ``TriangleMesh``.  This argument should be
            specified for partial data that has no primary key data, e.g., a
            triangle mesh without vertices but with other attribute tensors.
        connection (open3d.cuda.pybind.io.rpc._ConnectionBase, optional, default=None): A Connection object. Use None to automatically create the connection.

    Returns:
        bool
    """

def set_point_cloud(
    pcd: open3d.cuda.pybind.geometry.PointCloud,
    path: str = "",
    time: int = 0,
    layer: str = "",
    connection: _ConnectionBase = None,
) -> bool:
    """
    Sends a point cloud message to a viewer.

    Args:
        pcd (open3d.cuda.pybind.geometry.PointCloud): Point cloud object.
        path (str, optional, default=''): A path descriptor, e.g., 'mygroup/points'.
        time (int, optional, default=0): The time associated with this data.
        layer (str, optional, default=''): The layer associated with this data.
        connection (open3d.cuda.pybind.io.rpc._ConnectionBase, optional, default=None): A Connection object. Use None to automatically create the connection.

    Returns:
        bool
    """

def set_time(time: int, connection: _ConnectionBase = None) -> bool:
    """
    Sets the time in the external visualizer.

    Args:
        time (int): The time value to set.
        connection (open3d.cuda.pybind.io.rpc._ConnectionBase, optional, default=None): A Connection object. Use None to automatically create the connection.

    Returns:
        bool
    """

@typing.overload
def set_triangle_mesh(
    mesh: open3d.cuda.pybind.geometry.TriangleMesh,
    path: str = "",
    time: int = 0,
    layer: str = "",
    connection: _ConnectionBase = None,
) -> bool:
    """
    Sends a triangle mesh to a viewer.
    Args:
        mesh (o3d.geometry.TriangleMesh): The triangle mesh.
        path (str): The path in the scene graph.
        time (int): The time associated with the data.
        layer (str): A layer name that can be used by receivers that support layers.
        connection (o3d.io.rpc.Connection): A connection object that will be used for sending the data.

    Returns:
        Returns True if the data was successfully received.
    """

@typing.overload
def set_triangle_mesh(
    mesh: open3d.cuda.pybind.t.geometry.TriangleMesh,
    path: str = "",
    time: int = 0,
    layer: str = "",
    connection: _ConnectionBase = None,
) -> bool:
    """
    Sends a triangle mesh to a viewer.
    Args:
        mesh (o3d.t.geometry.TriangleMesh): The triangle mesh.
        path (str): The path in the scene graph.
        time (int): The time associated with the data.
        layer (str): A layer name that can be used by receivers that support layers.
        connection (o3d.io.rpc.Connection): A connection object that will be used for sending the data.

    Returns:
        Returns True if the data was successfully received.
    """
