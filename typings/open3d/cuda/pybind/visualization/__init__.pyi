from __future__ import annotations
import numpy
import open3d.cuda.pybind.camera
import open3d.cuda.pybind.geometry
import open3d.cuda.pybind.t.geometry
import open3d.cuda.pybind.utility
import os
import typing
from . import app
from . import gui
from . import rendering
from . import webrtc_server
__all__: list[str] = ['Color', 'Default', 'Material', 'MeshColorOption', 'MeshShadeOption', 'Normal', 'O3DVisualizer', 'PickedPoint', 'PointColorOption', 'RenderOption', 'ScalarProperties', 'SelectedIndex', 'SelectionPolygonVolume', 'TextureMaps', 'VectorProperties', 'ViewControl', 'Visualizer', 'VisualizerWithEditing', 'VisualizerWithKeyCallback', 'VisualizerWithVertexSelection', 'XCoordinate', 'YCoordinate', 'ZCoordinate', 'app', 'draw_geometries', 'draw_geometries_with_animation_callback', 'draw_geometries_with_custom_animation', 'draw_geometries_with_editing', 'draw_geometries_with_key_callbacks', 'draw_geometries_with_vertex_selection', 'gui', 'read_selection_polygon_volume', 'rendering', 'webrtc_server']
class Material:
    """
    Properties (texture maps, scalar and vector) related to visualization. Materials are optionally set for 3D geometries such as TriangleMesh, LineSets, and PointClouds
    """
    material_name: str
    @typing.overload
    def __init__(self) -> None:
        ...
    @typing.overload
    def __init__(self, mat: Material) -> None:
        ...
    @typing.overload
    def __init__(self, material_name: str) -> None:
        ...
    @typing.overload
    def __init__(self, material_record: rendering.MaterialRecord) -> None:
        """
        Convert from MaterialRecord.
        """
    def __repr__(self) -> str:
        ...
    def is_valid(self) -> bool:
        """
        Returns false if material is an empty material
        """
    def set_default_properties(self) -> None:
        """
        Fills material with defaults for common PBR material properties used by Open3D
        """
    @property
    def scalar_properties(self) -> ScalarProperties:
        ...
    @property
    def texture_maps(self) -> TextureMaps:
        ...
    @property
    def vector_properties(self) -> VectorProperties:
        ...
class MeshColorOption:
    """
    Enum class for color for ``TriangleMesh``.
    """
    Color: typing.ClassVar[MeshColorOption]
    Default: typing.ClassVar[MeshColorOption]
    Normal: typing.ClassVar[MeshColorOption]
    XCoordinate: typing.ClassVar[MeshColorOption]
    YCoordinate: typing.ClassVar[MeshColorOption]
    ZCoordinate: typing.ClassVar[MeshColorOption]
    __members__: typing.ClassVar[dict[str, MeshColorOption]]
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
class MeshShadeOption:
    """
    Enum class for mesh shading for ``TriangleMesh``.
    """
    Color: typing.ClassVar[MeshShadeOption]
    Default: typing.ClassVar[MeshShadeOption]
    __members__: typing.ClassVar[dict[str, MeshShadeOption]]
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
class O3DVisualizer(gui.WindowBase):
    """
    Visualization object used by draw()
    """
    class DrawObject:
        """
        Information about an object that is drawn. Do not modify this, it can lead to unexpected results.
        """
        @property
        def geometry(self) -> typing.Any:
            """
            The geometry. Modifying this will not result in any visible change. Use remove_geometry() and then add_geometry()to change the geometry
            """
        @property
        def group(self) -> str:
            """
            The group that the object belongs to
            """
        @property
        def is_visible(self) -> bool:
            """
            True if the object is checked in the list. If the object's group is unchecked or an animation is playing, the object's visibility may not correspond with this value
            """
        @property
        def name(self) -> str:
            """
            The name of the object
            """
        @property
        def time(self) -> float:
            """
            The object's timestamp
            """
    class Shader:
        """
        Scene-level rendering options
        
        Members:
        
          STANDARD : Pixel colors from standard lighting model
        
          UNLIT : Normals will be ignored (useful for point clouds)
        
          NORMALS : Pixel colors correspond to surface normal
        
          DEPTH : Pixel colors correspond to depth buffer value
        """
        DEPTH: typing.ClassVar[O3DVisualizer.Shader]
        NORMALS: typing.ClassVar[O3DVisualizer.Shader]
        STANDARD: typing.ClassVar[O3DVisualizer.Shader]
        UNLIT: typing.ClassVar[O3DVisualizer.Shader]
        __members__: typing.ClassVar[dict[str, O3DVisualizer.Shader]]
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
    class TickResult:
        """
        Return value from animation tick callback
        
        Members:
        
          NO_CHANGE : Signals that no change happened and no redraw is required
        
          REDRAW : Signals that a redraw is required
        """
        NO_CHANGE: typing.ClassVar[O3DVisualizer.TickResult]
        REDRAW: typing.ClassVar[O3DVisualizer.TickResult]
        __members__: typing.ClassVar[dict[str, O3DVisualizer.TickResult]]
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
    DEPTH: typing.ClassVar[O3DVisualizer.Shader]
    NORMALS: typing.ClassVar[O3DVisualizer.Shader]
    STANDARD: typing.ClassVar[O3DVisualizer.Shader]
    UNLIT: typing.ClassVar[O3DVisualizer.Shader]
    def __init__(self, title: str = 'Open3D', width: int = 1024, height: int = 768) -> None:
        """
        Creates a O3DVisualizer object
        """
    def add_3d_label(self, pos: numpy.ndarray, text: str) -> None:
        """
        Displays text anchored at the 3D coordinate specified
        """
    def add_action(self, name: str, callback: typing.Callable[[O3DVisualizer], None]) -> None:
        """
        Adds a button to the custom actions section of the UI and a corresponding menu item in the "Actions" menu. The callback will be given one parameter, the O3DVisualizer instance, and does not return any value.
        """
    @typing.overload
    def add_geometry(self, name: str, geometry: open3d.cuda.pybind.geometry.Geometry3D, material: rendering.MaterialRecord = None, group: str = '', time: float = 0.0, is_visible: bool = True) -> None:
        """
        Adds a geometry. 'name' must be unique.
        """
    @typing.overload
    def add_geometry(self, name: str, geometry: open3d.cuda.pybind.t.geometry.Geometry, material: rendering.MaterialRecord = None, group: str = '', time: float = 0.0, is_visible: bool = True) -> None:
        """
        Adds a Tensor-based geometry. 'name' must be unique.
        """
    @typing.overload
    def add_geometry(self, name: str, model: rendering.TriangleMeshModel, material: rendering.MaterialRecord = None, group: str = '', time: float = 0.0, is_visible: bool = True) -> None:
        """
        Adds a TriangleMeshModel. 'name' must be unique. 'material' is ignored.
        """
    @typing.overload
    def add_geometry(self, d: dict) -> None:
        """
        Adds a geometry from a dictionary. The dictionary has the following elements:
        name: unique name of the object (required)
        geometry: the geometry or t.geometry object (required)
        material: a visualization.rendering.Material object (optional)
        group: a string declaring the group it is a member of (optional)
        time: a time value
        """
    def clear_3d_labels(self) -> None:
        """
        Clears all 3D text
        """
    def close(self) -> None:
        """
        Closes the window and destroys it, unless an on_close callback cancels the close.
        """
    def close_dialog(self) -> None:
        """
        Closes the current dialog
        """
    def enable_raw_mode(self, enable: bool) -> None:
        """
        Enables/disables raw mode for simplified lighting environment.
        """
    def export_current_image(self, path: str) -> None:
        """
        Exports a PNG or JPEG image of what is currently displayed to the given path.
        """
    def get_geometry(self, name: str) -> O3DVisualizer.DrawObject:
        """
        Returns the DrawObject corresponding to the name. This should be treated as read-only. Modify visibility with show_geometry(), and other values by removing the object and re-adding it with the new values
        """
    def get_geometry_material(self, name: str) -> rendering.MaterialRecord:
        """
        Returns the MaterialRecord corresponding to the name. The returned material is a copy, therefore modifying it directly will not change the visualization.
        """
    def get_selection_sets(self) -> list[dict[str, set[SelectedIndex]]]:
        """
        Returns the selection sets, as [{'obj_name', [SelectedIndex]}]
        """
    def modify_geometry_material(self, name: str, material: rendering.MaterialRecord) -> None:
        """
        Updates the named geometry to use the new provided material.
        """
    def post_redraw(self) -> None:
        """
        Tells the window to redraw
        """
    def remove_geometry(self, name: str) -> None:
        """
        Removes the geometry with the name.
        """
    def reset_camera_to_default(self) -> None:
        """
        Sets camera to default position
        """
    def set_background(self, bg_color: numpy.ndarray, bg_image: open3d.cuda.pybind.geometry.Image) -> None:
        """
        Sets the background color and, optionally, the background image. Passing None for the background image will clear any image already there.
        """
    def set_ibl(self, ibl_name: str) -> None:
        """
        Sets the IBL and its matching skybox. If ibl_name_ibl.ktx is found in the default resource directory then it is used. Otherwise, ibl_name is assumed to be a path to the ibl KTX file.
        """
    def set_ibl_intensity(self, intensity: float) -> None:
        """
        Sets the intensity of the current IBL
        """
    def set_on_animation_frame(self, callback: typing.Callable[[O3DVisualizer, float], None]) -> None:
        """
        Sets a callback that will be called every frame of the animation. The callback will be called as callback(o3dvis, current_time).
        """
    def set_on_animation_tick(self, callback: typing.Callable[[O3DVisualizer, float, float], O3DVisualizer.TickResult]) -> None:
        """
        Sets a callback that will be called every frame of the animation. The callback will be called as callback(o3dvis, time_since_last_tick, total_elapsed_since_animation_started). Note that this is a low-level callback. If you need to change the current timestamp being shown you will need to update the o3dvis.current_time property in the callback. The callback must return either O3DVisualizer.TickResult.IGNORE if no redraw is required or O3DVisualizer.TickResult.REDRAW if a redraw is required.
        """
    def set_on_close(self, callback: typing.Callable[[], bool]) -> None:
        """
        Sets a callback that will be called when the window is closed. The callback is given no arguments and should return True to continue closing the window or False to cancel the close
        """
    def set_panel_open(self, name: str, open: bool) -> None:
        """
        Expand/Collapse verts(panels) within the settings panel
        """
    @typing.overload
    def setup_camera(self, field_of_view: float, center: numpy.ndarray, eye: numpy.ndarray, up: numpy.ndarray) -> None:
        """
        Sets the camera view so that the camera is located at 'eye', pointing towards 'center', and oriented so that the up vector is 'up'
        """
    @typing.overload
    def setup_camera(self, intrinsic: open3d.cuda.pybind.camera.PinholeCameraIntrinsic, extrinsic_matrix: numpy.ndarray) -> None:
        """
        Sets the camera view
        """
    @typing.overload
    def setup_camera(self, intrinsic_matrix: numpy.ndarray, extrinsic_matrix: numpy.ndarray, intrinsic_width_px: int, intrinsic_height_px: int) -> None:
        """
        Sets the camera view
        """
    def show(self, vis: bool) -> None:
        """
        Shows or hides the window
        """
    def show_dialog(self, dlg: gui.Dialog) -> None:
        """
        Displays the dialog
        """
    def show_geometry(self, name: str, show: bool) -> None:
        """
        Checks or unchecks the named geometry in the list. Note that even if show_geometry(name, True) is called, the object may not actually be visible if its group is unchecked, or if an animation is in progress.
        """
    def show_menu(self, show: bool) -> None:
        """
        Shows or hides the menu in the window, except on macOS since the menubar is not in the window and all applications must have a menubar.
        """
    def show_message_box(self, title: str, message: str) -> None:
        """
        Displays a simple dialog with a title and message and okay button
        """
    def show_skybox(self, show: bool) -> None:
        """
        Show/Hide the skybox
        """
    def size_to_fit(self) -> None:
        """
        Sets the width and height of window to its preferred size
        """
    def start_rpc_interface(self, address: str, timeout: int) -> None:
        """
        Starts the RPC interface.
        address: str with the address to listen on.
        timeout: int timeout in milliseconds for sending the reply.
        """
    def stop_rpc_interface(self) -> None:
        """
        Stops the RPC interface.
        """
    def update_geometry(self, name: str, tpoint_cloud: open3d.cuda.pybind.t.geometry.Geometry, update_flags: int) -> None:
        """
        Updates the attributes of the named geometry specified by update_flags with tpoint_cloud. Note: Currently this function only works with T Geometry Point Clouds.
        """
    @property
    def animation_duration(self) -> float:
        """
        Gets/sets the duration (in seconds) of the animation. This is automatically computed to be the difference between the minimum and maximum time values, but this is useful if no time values have been specified (that is, all objects are at the default t=0)
        """
    @animation_duration.setter
    def animation_duration(self, arg1: float) -> None:
        ...
    @property
    def animation_frame_delay(self) -> float:
        """
        Gets/sets the length of time a frame is visible.
        """
    @animation_frame_delay.setter
    def animation_frame_delay(self, arg1: float) -> None:
        ...
    @property
    def animation_time_step(self) -> float:
        """
        Gets/sets the time step for animations. Default is 1.0 sec
        """
    @animation_time_step.setter
    def animation_time_step(self, arg1: float) -> None:
        ...
    @property
    def content_rect(self) -> gui.Rect:
        """
        Returns the frame in device pixels, relative  to the window, which is available for widgets (read-only)
        """
    @property
    def current_time(self) -> float:
        """
        Gets/sets the current time. If setting, only the objects belonging to the current time-step will be displayed
        """
    @current_time.setter
    def current_time(self, arg1: float) -> None:
        ...
    @property
    def ground_plane(self) -> rendering.Scene.GroundPlane:
        """
        Sets the plane for ground plane, XZ, XY, or YZ
        """
    @ground_plane.setter
    def ground_plane(self, arg1: rendering.Scene.GroundPlane) -> None:
        ...
    @property
    def is_animating(self) -> bool:
        """
        Gets/sets the status of the animation. Changing value will start or stop the animating.
        """
    @is_animating.setter
    def is_animating(self, arg1: bool) -> None:
        ...
    @property
    def is_visible(self) -> bool:
        """
        True if window is visible (read-only)
        """
    @property
    def line_width(self) -> int:
        """
        Gets/sets width of lines (in units of pixels)
        """
    @line_width.setter
    def line_width(self, arg1: int) -> None:
        ...
    @property
    def mouse_mode(self) -> gui.SceneWidget.Controls:
        """
        Gets/sets the control mode being used for the mouse
        """
    @mouse_mode.setter
    def mouse_mode(self, arg1: gui.SceneWidget.Controls) -> None:
        ...
    @property
    def os_frame(self) -> gui.Rect:
        """
        Window rect in OS coords, not device pixels
        """
    @os_frame.setter
    def os_frame(self, arg1: gui.Rect) -> None:
        ...
    @property
    def point_size(self) -> int:
        """
        Gets/sets size of points (in units of pixels)
        """
    @point_size.setter
    def point_size(self, arg1: int) -> None:
        ...
    @property
    def scaling(self) -> float:
        """
        Returns the scaling factor between OS pixels and device pixels (read-only)
        """
    @property
    def scene(self) -> rendering.Open3DScene:
        """
        Returns the rendering.Open3DScene object for low-level manipulation
        """
    @property
    def scene_shader(self) -> O3DVisualizer.Shader:
        """
        Gets/sets the shading model for the scene
        """
    @scene_shader.setter
    def scene_shader(self, arg1: O3DVisualizer.Shader) -> None:
        ...
    @property
    def show_axes(self) -> bool:
        """
        Gets/sets if axes are visible
        """
    @show_axes.setter
    def show_axes(self, arg1: bool) -> None:
        ...
    @property
    def show_ground(self) -> bool:
        """
        Gets/sets if ground plane is visible
        """
    @show_ground.setter
    def show_ground(self, arg1: bool) -> None:
        ...
    @property
    def show_settings(self) -> bool:
        """
        Gets/sets if settings panel is visible
        """
    @show_settings.setter
    def show_settings(self, arg1: bool) -> None:
        ...
    @property
    def size(self) -> gui.Size:
        """
        The size of the window in device pixels, including menubar (except on macOS)
        """
    @size.setter
    def size(self, arg1: gui.Size) -> None:
        ...
    @property
    def title(self) -> str:
        """
        Returns the title of the window
        """
    @title.setter
    def title(self, arg1: str) -> None:
        ...
    @property
    def uid(self) -> str:
        """
        Window's unique ID when WebRTCWindowSystem is use.Returns 'window_undefined' otherwise.
        """
class PickedPoint:
    coord: numpy.ndarray
    index: int
    def __init__(self) -> None:
        ...
class PointColorOption:
    """
    Enum class for point color for ``PointCloud``.
    """
    Color: typing.ClassVar[PointColorOption]
    Default: typing.ClassVar[PointColorOption]
    Normal: typing.ClassVar[PointColorOption]
    XCoordinate: typing.ClassVar[PointColorOption]
    YCoordinate: typing.ClassVar[PointColorOption]
    ZCoordinate: typing.ClassVar[PointColorOption]
    __members__: typing.ClassVar[dict[str, PointColorOption]]
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
class RenderOption:
    """
    Defines rendering options for visualizer.
    """
    def __init__(self) -> None:
        """
        Default constructor
        """
    def __repr__(self) -> str:
        ...
    def load_from_json(self, filename: os.PathLike) -> None:
        """
        Function to load RenderOption from a JSON file.
        
        Args:
            filename (os.PathLike): Path to file.
        
        Returns:
            None
        """
    def save_to_json(self, filename: os.PathLike) -> None:
        """
        Function to save RenderOption to a JSON file.
        
        Args:
            filename (os.PathLike): Path to file.
        
        Returns:
            None
        """
    @property
    def background_color(self) -> numpy.ndarray:
        """
        float numpy array of size ``(3,)``: Background RGB color.
        """
    @background_color.setter
    def background_color(self, arg0: numpy.ndarray) -> None:
        ...
    @property
    def light_on(self) -> bool:
        """
        bool: Whether to turn on Phong lighting.
        """
    @light_on.setter
    def light_on(self, arg0: bool) -> None:
        ...
    @property
    def line_width(self) -> float:
        """
        float: Line width for ``LineSet``.
        """
    @line_width.setter
    def line_width(self, arg0: float) -> None:
        ...
    @property
    def mesh_color_option(self) -> MeshColorOption:
        """
        ``MeshColorOption``: Color option for ``TriangleMesh``.
        """
    @mesh_color_option.setter
    def mesh_color_option(self, arg0: MeshColorOption) -> None:
        ...
    @property
    def mesh_shade_option(self) -> MeshShadeOption:
        """
        ``MeshShadeOption``: Mesh shading option for ``TriangleMesh``.
        """
    @mesh_shade_option.setter
    def mesh_shade_option(self, arg0: MeshShadeOption) -> None:
        ...
    @property
    def mesh_show_back_face(self) -> bool:
        """
        bool: Whether to show back faces for ``TriangleMesh``.
        """
    @mesh_show_back_face.setter
    def mesh_show_back_face(self, arg0: bool) -> None:
        ...
    @property
    def mesh_show_wireframe(self) -> bool:
        """
        bool: Whether to show wireframe for ``TriangleMesh``.
        """
    @mesh_show_wireframe.setter
    def mesh_show_wireframe(self, arg0: bool) -> None:
        ...
    @property
    def point_color_option(self) -> PointColorOption:
        """
        ``PointColorOption``: Point color option for ``PointCloud``.
        """
    @point_color_option.setter
    def point_color_option(self, arg0: PointColorOption) -> None:
        ...
    @property
    def point_show_normal(self) -> bool:
        """
        bool: Whether to show normal for ``PointCloud``.
        """
    @point_show_normal.setter
    def point_show_normal(self, arg0: bool) -> None:
        ...
    @property
    def point_size(self) -> float:
        """
        float: Point size for ``PointCloud``.
        """
    @point_size.setter
    def point_size(self, arg0: float) -> None:
        ...
    @property
    def show_coordinate_frame(self) -> bool:
        """
        bool: Whether to show coordinate frame.
        """
    @show_coordinate_frame.setter
    def show_coordinate_frame(self, arg0: bool) -> None:
        ...
class ScalarProperties:
    def __bool__(self) -> bool:
        """
        Check whether the map is nonempty
        """
    @typing.overload
    def __contains__(self, arg0: str) -> bool:
        ...
    @typing.overload
    def __contains__(self, arg0: typing.Any) -> bool:
        ...
    def __delitem__(self, arg0: str) -> None:
        ...
    def __getitem__(self, arg0: str) -> float:
        ...
    def __init__(self) -> None:
        ...
    def __iter__(self) -> typing.Iterator[str]:
        ...
    def __len__(self) -> int:
        ...
    def __repr__(self) -> str:
        """
        Return the canonical string representation of this map.
        """
    def __setitem__(self, arg0: str, arg1: float) -> None:
        ...
    def items(self) -> typing.ItemsView:
        ...
    def keys(self) -> typing.KeysView:
        ...
    def values(self) -> typing.ValuesView:
        ...
class SelectedIndex:
    """
    Information about a point or vertex that was selected
    """
    def __repr__(self) -> str:
        ...
    @property
    def index(self) -> int:
        """
        The index of this point in the point/vertex array
        """
    @property
    def order(self) -> int:
        """
        A monotonically increasing value that can be used to determine in what order the points were selected
        """
    @property
    def point(self) -> numpy.ndarray:
        """
        The (x, y, z) value of this point
        """
class SelectionPolygonVolume:
    """
    Select a polygon volume for cropping.
    """
    def __copy__(self) -> SelectionPolygonVolume:
        ...
    def __deepcopy__(self, arg0: dict) -> SelectionPolygonVolume:
        ...
    @typing.overload
    def __init__(self) -> None:
        """
        Default constructor
        """
    @typing.overload
    def __init__(self, arg0: SelectionPolygonVolume) -> None:
        """
        Copy constructor
        """
    def __repr__(self) -> str:
        ...
    def crop_in_polygon(self, input: open3d.cuda.pybind.geometry.PointCloud) -> list[int]:
        """
        Function to crop 3d point clouds.
        
        Args:
            input (open3d.cuda.pybind.geometry.PointCloud): The input point cloud xyz.
        
        Returns:
            list[int]
        """
    def crop_point_cloud(self, input: open3d.cuda.pybind.geometry.PointCloud) -> open3d.cuda.pybind.geometry.PointCloud:
        """
        Function to crop point cloud.
        
        Args:
            input (open3d.cuda.pybind.geometry.PointCloud): The input point cloud.
        
        Returns:
            open3d.cuda.pybind.geometry.PointCloud
        """
    def crop_triangle_mesh(self, input: open3d.cuda.pybind.geometry.TriangleMesh) -> open3d.cuda.pybind.geometry.TriangleMesh:
        """
        Function to crop crop triangle mesh.
        
        Args:
            input (open3d.cuda.pybind.geometry.TriangleMesh): The input triangle mesh.
        
        Returns:
            open3d.cuda.pybind.geometry.TriangleMesh
        """
    @property
    def axis_max(self) -> float:
        """
        float: Maximum axis value.
        """
    @axis_max.setter
    def axis_max(self, arg0: float) -> None:
        ...
    @property
    def axis_min(self) -> float:
        """
        float: Minimum axis value.
        """
    @axis_min.setter
    def axis_min(self, arg0: float) -> None:
        ...
    @property
    def bounding_polygon(self) -> open3d.cuda.pybind.utility.Vector3dVector:
        """
        ``(n, 3)`` float64 numpy array: Bounding polygon boundary.
        """
    @bounding_polygon.setter
    def bounding_polygon(self, arg0: open3d.cuda.pybind.utility.Vector3dVector) -> None:
        ...
    @property
    def orthogonal_axis(self) -> str:
        """
        string: one of ``{x, y, z}``.
        """
    @orthogonal_axis.setter
    def orthogonal_axis(self, arg0: str) -> None:
        ...
class TextureMaps:
    def __bool__(self) -> bool:
        """
        Check whether the map is nonempty
        """
    @typing.overload
    def __contains__(self, arg0: str) -> bool:
        ...
    @typing.overload
    def __contains__(self, arg0: typing.Any) -> bool:
        ...
    def __delitem__(self, arg0: str) -> None:
        ...
    def __getitem__(self, arg0: str) -> open3d.cuda.pybind.t.geometry.Image:
        ...
    def __init__(self) -> None:
        ...
    def __iter__(self) -> typing.Iterator[str]:
        ...
    def __len__(self) -> int:
        ...
    def __setitem__(self, arg0: str, arg1: open3d.cuda.pybind.t.geometry.Image) -> None:
        ...
    def items(self) -> typing.ItemsView:
        ...
    def keys(self) -> typing.KeysView:
        ...
    def values(self) -> typing.ValuesView:
        ...
class VectorProperties:
    def __bool__(self) -> bool:
        """
        Check whether the map is nonempty
        """
    @typing.overload
    def __contains__(self, arg0: str) -> bool:
        ...
    @typing.overload
    def __contains__(self, arg0: typing.Any) -> bool:
        ...
    def __delitem__(self, arg0: str) -> None:
        ...
    def __getitem__(self, arg0: str) -> numpy.ndarray:
        ...
    def __init__(self) -> None:
        ...
    def __iter__(self) -> typing.Iterator[str]:
        ...
    def __len__(self) -> int:
        ...
    def __repr__(self) -> str:
        """
        Return the canonical string representation of this map.
        """
    def __setitem__(self, arg0: str, arg1: numpy.ndarray) -> None:
        ...
    def items(self) -> typing.ItemsView:
        ...
    def keys(self) -> typing.KeysView:
        ...
    def values(self) -> typing.ValuesView:
        ...
class ViewControl:
    """
    View controller for visualizer.
    """
    def __init__(self) -> None:
        """
        Default constructor
        """
    def __repr__(self) -> str:
        ...
    def camera_local_rotate(self, x: float, y: float, xo: float = 0.0, yo: float = 0.0) -> None:
        """
        Function to process rotation of camera in a localcoordinate frame
        """
    def camera_local_translate(self, forward: float, right: float, up: float) -> None:
        """
        Function to process translation of camera
        """
    def change_field_of_view(self, step: float = 0.45) -> None:
        """
        Function to change field of view
        
        Args:
            step (float, optional, default=0.45): The step to change field of view.
        
        Returns:
            None
        """
    def convert_from_pinhole_camera_parameters(self, parameter: open3d.cuda.pybind.camera.PinholeCameraParameters, allow_arbitrary: bool = False) -> bool:
        """
        Args:
            parameter (open3d.cuda.pybind.camera.PinholeCameraParameters): The pinhole camera parameter to convert from.
            allow_arbitrary (bool, optional, default=False)
        
        Returns:
            bool
        """
    def convert_to_pinhole_camera_parameters(self) -> open3d.cuda.pybind.camera.PinholeCameraParameters:
        """
        Function to convert ViewControl to camera::PinholeCameraParameters
        
        Returns:
            open3d.cuda.pybind.camera.PinholeCameraParameters
        """
    def get_field_of_view(self) -> float:
        """
        Function to get field of view
        
        Returns:
            float
        """
    def reset_camera_local_rotate(self) -> None:
        """
        Resets the coordinate frame for local camera rotations
        """
    def rotate(self, x: float, y: float, xo: float = 0.0, yo: float = 0.0) -> None:
        """
        Function to process rotation
        
        Args:
            x (float): Distance the mouse cursor has moved in x-axis.
            y (float): Distance the mouse cursor has moved in y-axis.
            xo (float, optional, default=0.0): Original point coordinate of the mouse in x-axis.
            yo (float, optional, default=0.0): Original point coordinate of the mouse in y-axis.
        
        Returns:
            None
        """
    def scale(self, scale: float) -> None:
        """
        Function to process scaling
        
        Args:
            scale (float): Scale ratio.
        
        Returns:
            None
        """
    def set_constant_z_far(self, z_far: float) -> None:
        """
        Function to change the far z-plane of the visualizer to a constant value, i.e., independent of zoom and bounding box size.
        
        Args:
            z_far (float): The depth of the far z-plane of the visualizer.
        
        Returns:
            None
        """
    def set_constant_z_near(self, z_near: float) -> None:
        """
        Function to change the near z-plane of the visualizer to a constant value, i.e., independent of zoom and bounding box size.
        
        Args:
            z_near (float): The depth of the near z-plane of the visualizer.
        
        Returns:
            None
        """
    def set_front(self, front: numpy.ndarray) -> None:
        """
        Set the front vector of the visualizer
        """
    def set_lookat(self, lookat: numpy.ndarray) -> None:
        """
        Set the lookat vector of the visualizer
        """
    def set_up(self, up: numpy.ndarray) -> None:
        """
        Set the up vector of the visualizer
        """
    def set_zoom(self, zoom: float) -> None:
        """
        Set the zoom of the visualizer
        """
    def translate(self, x: float, y: float, xo: float = 0.0, yo: float = 0.0) -> None:
        """
        Function to process translation
        
        Args:
            x (float): Distance the mouse cursor has moved in x-axis.
            y (float): Distance the mouse cursor has moved in y-axis.
            xo (float, optional, default=0.0): Original point coordinate of the mouse in x-axis.
            yo (float, optional, default=0.0): Original point coordinate of the mouse in y-axis.
        
        Returns:
            None
        """
    def unset_constant_z_far(self) -> None:
        """
        Function to remove a previously set constant z far value, i.e., far z-plane of the visualizer is dynamically set dependent on zoom and bounding box size.
        
        Returns:
            None
        """
    def unset_constant_z_near(self) -> None:
        """
        Function to remove a previously set constant z near value, i.e., near z-plane of the visualizer is dynamically set dependent on zoom and bounding box size.
        
        Returns:
            None
        """
class Visualizer:
    """
    The main Visualizer class.
    """
    def __init__(self) -> None:
        """
        Default constructor
        """
    def __repr__(self) -> str:
        ...
    def add_geometry(self, geometry: open3d.cuda.pybind.geometry.Geometry, reset_bounding_box: bool = True) -> bool:
        """
        Function to add geometry to the scene and create corresponding shaders
        
        Args:
            geometry (open3d.cuda.pybind.geometry.Geometry): The ``Geometry`` object.
            reset_bounding_box (bool, optional, default=True): Set to ``False`` to keep current viewpoint
        
        Returns:
            bool
        """
    def capture_depth_float_buffer(self, do_render: bool = False) -> open3d.cuda.pybind.geometry.Image:
        """
        Function to capture depth in a float buffer
        
        Args:
            do_render (bool, optional, default=False): Set to ``True`` to do render.
        
        Returns:
            open3d.cuda.pybind.geometry.Image
        """
    def capture_depth_image(self, filename: os.PathLike, do_render: bool = False, depth_scale: float = 1000.0) -> None:
        """
        Function to capture and save a depth image
        
        Args:
            filename (os.PathLike): Path to file.
            do_render (bool, optional, default=False): Set to ``True`` to do render.
            depth_scale (float, optional, default=1000.0): Scale depth value when capturing the depth image.
        
        Returns:
            None
        """
    def capture_depth_point_cloud(self, filename: os.PathLike, do_render: bool = False, convert_to_world_coordinate: bool = False) -> None:
        """
        Function to capture and save local point cloud
        
        Args:
            filename (os.PathLike): Path to file.
            do_render (bool, optional, default=False): Set to ``True`` to do render.
            convert_to_world_coordinate (bool, optional, default=False): Set to ``True`` to convert to world coordinates
        
        Returns:
            None
        """
    def capture_screen_float_buffer(self, do_render: bool = False) -> open3d.cuda.pybind.geometry.Image:
        """
        Function to capture screen and store RGB in a float buffer
        
        Args:
            do_render (bool, optional, default=False): Set to ``True`` to do render.
        
        Returns:
            open3d.cuda.pybind.geometry.Image
        """
    def capture_screen_image(self, filename: os.PathLike, do_render: bool = False) -> None:
        """
        Function to capture and save a screen image
        
        Args:
            filename (os.PathLike): Path to file.
            do_render (bool, optional, default=False): Set to ``True`` to do render.
        
        Returns:
            None
        """
    def clear_geometries(self) -> bool:
        """
        Function to clear geometries from the visualizer
        """
    def close(self) -> None:
        """
        Function to notify the window to be closed
        
        Returns:
            None
        """
    def create_window(self, window_name: str = 'Open3D', width: int = 1920, height: int = 1080, left: int = 50, top: int = 50, visible: bool = True) -> bool:
        """
        Function to create a window and initialize GLFW
        
        Args:
            window_name (str, optional, default='Open3D'): Window title name.
            width (int, optional, default=1920): Width of the window.
            height (int, optional, default=1080): Height of window.
            left (int, optional, default=50): Left margin of the window to the screen.
            top (int, optional, default=50): Top margin of the window to the screen.
            visible (bool, optional, default=True): Whether the window is visible.
        
        Returns:
            bool
        """
    def destroy_window(self) -> None:
        """
        Function to destroy a window. This function MUST be called from the main thread.
        
        Returns:
            None
        """
    def get_render_option(self) -> RenderOption:
        """
        Function to retrieve the associated ``RenderOption``
        
        Returns:
            open3d.cuda.pybind.visualization.RenderOption
        """
    def get_view_control(self) -> ViewControl:
        """
        Function to retrieve the associated ``ViewControl``
        
        Returns:
            open3d.cuda.pybind.visualization.ViewControl
        """
    def get_view_status(self) -> str:
        """
        Get the current view status as a json string of ViewTrajectory.
        """
    def get_window_name(self) -> str:
        """
        Returns:
            str
        """
    def is_full_screen(self) -> bool:
        """
        Function to query whether in fullscreen mode
        
        Returns:
            bool
        """
    def poll_events(self) -> bool:
        """
        Function to poll events
        
        Returns:
            bool
        """
    def register_animation_callback(self, callback_func: typing.Callable[[Visualizer], bool]) -> None:
        """
        Function to register a callback function for animation. The callback function returns if UpdateGeometry() needs to be run.
        
        Args:
            callback_func (Callable[[open3d.cuda.pybind.visualization.Visualizer], bool]): The call back function.
        
        Returns:
            None
        """
    def remove_geometry(self, geometry: open3d.cuda.pybind.geometry.Geometry, reset_bounding_box: bool = True) -> bool:
        """
        Function to remove geometry
        
        Args:
            geometry (open3d.cuda.pybind.geometry.Geometry): The ``Geometry`` object.
            reset_bounding_box (bool, optional, default=True): Set to ``False`` to keep current viewpoint
        
        Returns:
            bool
        """
    def reset_view_point(self, reset_bounding_box: bool = False) -> None:
        """
        Function to reset view point
        
        Args:
            reset_bounding_box (bool, optional, default=False): Set to ``False`` to keep current viewpoint
        
        Returns:
            None
        """
    def run(self) -> None:
        """
        Function to activate the window. This function will block the current thread until the window is closed.
        
        Returns:
            None
        """
    def set_full_screen(self, fullscreen: bool) -> None:
        """
        Function to change between fullscreen and windowed
        
        Args:
            fullscreen (bool)
        
        Returns:
            None
        """
    def set_view_status(self, view_status_str: str) -> None:
        """
        Set the current view status from a json string of ViewTrajectory.
        """
    def toggle_full_screen(self) -> None:
        """
        Function to toggle between fullscreen and windowed
        
        Returns:
            None
        """
    def update_geometry(self, geometry: open3d.cuda.pybind.geometry.Geometry) -> bool:
        """
        Function to update geometry. This function must be called when geometry has been changed. Otherwise the behavior of Visualizer is undefined.
        
        Args:
            geometry (open3d.cuda.pybind.geometry.Geometry): The ``Geometry`` object.
        
        Returns:
            bool
        """
    def update_renderer(self) -> None:
        """
        Function to inform render needed to be updated
        
        Returns:
            None
        """
class VisualizerWithEditing(Visualizer):
    """
    Visualizer with editing capabilities.
    """
    @typing.overload
    def __init__(self) -> None:
        """
        Default constructor
        """
    @typing.overload
    def __init__(self, voxel_size: float, use_dialog: bool, directory: str) -> None:
        ...
    def __repr__(self) -> str:
        ...
    def get_cropped_geometry(self) -> open3d.cuda.pybind.geometry.Geometry:
        """
        Function to get cropped geometry
        """
    def get_picked_points(self) -> list[int]:
        """
        Function to get picked points
        """
class VisualizerWithKeyCallback(Visualizer):
    """
    Visualizer with custom key callback capabilities.
    """
    def __init__(self) -> None:
        """
        Default constructor
        """
    def __repr__(self) -> str:
        ...
    def register_key_action_callback(self, key: int, callback_func: typing.Callable[[Visualizer, int, int], bool]) -> None:
        """
        Function to register a callback function for a key action event. The callback function takes `Visualizer`, `action` and `mods` as input and returns a boolean indicating if `UpdateGeometry()` needs to be run.  The `action` can be one of `GLFW_RELEASE` (0), `GLFW_PRESS` (1) or `GLFW_REPEAT` (2), see `GLFW input interface <https://www.glfw.org/docs/latest/group__input.html>`__. The `mods` specifies the modifier key, see `GLFW modifier key <https://www.glfw.org/docs/latest/group__mods.html>`__
        """
    def register_key_callback(self, key: int, callback_func: typing.Callable[[Visualizer], bool]) -> None:
        """
        Function to register a callback function for a key press event
        """
    def register_mouse_button_callback(self, callback_func: typing.Callable[[Visualizer, int, int, int], bool]) -> None:
        """
        Function to register a callback function for a mouse button event. The callback function takes `Visualizer`, `button`, `action` and `mods` as input and returns a boolean indicating `UpdateGeometry()` needs to be run. The `action` can be one of GLFW_RELEASE (0), GLFW_PRESS (1) or GLFW_REPEAT (2), see `GLFW input interface <https://www.glfw.org/docs/latest/group__input.html>`__.  The `mods` specifies the modifier key, see `GLFW modifier key <https://www.glfw.org/docs/latest/group__mods.html>`__.
        """
    def register_mouse_move_callback(self, callback_func: typing.Callable[[Visualizer, float, float], bool]) -> None:
        """
        Function to register a callback function for a mouse move event. The callback function takes Visualizer, x and y mouse position inside the window as input and returns a boolean indicating if UpdateGeometry() needs to be run. `GLFW mouse position <https://www.glfw.org/docs/latest/input_guide.html#input_mouse>`__ for more details.
        """
    def register_mouse_scroll_callback(self, callback_func: typing.Callable[[Visualizer, float, float], bool]) -> None:
        """
        Function to register a callback function for a mouse scroll event. The callback function takes Visualizer, x and y mouse scroll offset as input and returns a boolean indicating if UpdateGeometry() needs to be run. `GLFW mouse scrolling <https://www.glfw.org/docs/latest/input_guide.html#scrolling>`__ for more details.
        """
class VisualizerWithVertexSelection(Visualizer):
    """
    Visualizer with vertex selection capabilities.
    """
    @typing.overload
    def __init__(self) -> None:
        """
        Default constructor
        """
    @typing.overload
    def __init__(self) -> None:
        ...
    def __repr__(self) -> str:
        ...
    def add_picked_points(self, indices: open3d.cuda.pybind.utility.IntVector) -> None:
        """
        Function to add picked points
        """
    def clear_picked_points(self) -> None:
        """
        Function to clear picked points
        """
    def get_picked_points(self) -> list[PickedPoint]:
        """
        Function to get picked points
        """
    def pick_points(self, x: float, y: float, w: float, h: float) -> open3d.cuda.pybind.utility.IntVector:
        """
        Function to pick points
        """
    def register_selection_changed_callback(self, f: typing.Callable[[], None]) -> None:
        """
        Registers a function to be called when selection changes
        """
    def register_selection_moved_callback(self, f: typing.Callable[[], None]) -> None:
        """
        Registers a function to be called after selection moves
        """
    def register_selection_moving_callback(self, f: typing.Callable[[], None]) -> None:
        """
        Registers a function to be called while selection moves. Geometry's vertex values can be changed, but do not changethe number of vertices.
        """
    def remove_picked_points(self, indices: open3d.cuda.pybind.utility.IntVector) -> None:
        """
        Function to remove picked points
        """
def draw_geometries(geometry_list: list[open3d.cuda.pybind.geometry.Geometry], window_name: str = 'Open3D', width: int = 1920, height: int = 1080, left: int = 50, top: int = 50, point_show_normal: bool = False, mesh_show_wireframe: bool = False, mesh_show_back_face: bool = False, lookat: numpy.ndarray | None = None, up: numpy.ndarray | None = None, front: numpy.ndarray | None = None, zoom: float | None = None) -> None:
    """
    Function to draw a list of geometry::Geometry objects
    
    Args:
        geometry_list (list[open3d.cuda.pybind.geometry.Geometry]): List of geometries to be visualized.
        window_name (str, optional, default='Open3D'): The displayed title of the visualization window.
        width (int, optional, default=1920): The width of the visualization window.
        height (int, optional, default=1080): The height of the visualization window.
        left (int, optional, default=50): The left margin of the visualization window.
        top (int, optional, default=50): The top margin of the visualization window.
        point_show_normal (bool, optional, default=False): Visualize point normals if set to true.
        mesh_show_wireframe (bool, optional, default=False): Visualize mesh wireframe if set to true.
        mesh_show_back_face (bool, optional, default=False): Visualize also the back face of the mesh triangles.
        lookat (Optional[numpy.ndarray[numpy.float64[3, 1]]], optional, default=None): The lookat vector of the camera.
        up (Optional[numpy.ndarray[numpy.float64[3, 1]]], optional, default=None): The up vector of the camera.
        front (Optional[numpy.ndarray[numpy.float64[3, 1]]], optional, default=None): The front vector of the camera.
        zoom (Optional[float], optional, default=None): The zoom of the camera.
    
    Returns:
        None
    """
def draw_geometries_with_animation_callback(geometry_list: list[open3d.cuda.pybind.geometry.Geometry], callback_function: typing.Callable[[Visualizer], bool], window_name: str = 'Open3D', width: int = 1920, height: int = 1080, left: int = 50, top: int = 50) -> None:
    """
    Function to draw a list of geometry::Geometry objects with a customized animation callback function
    
    Args:
        geometry_list (list[open3d.cuda.pybind.geometry.Geometry]): List of geometries to be visualized.
        callback_function (Callable[[open3d.cuda.pybind.visualization.Visualizer], bool]): Call back function to be triggered at a key press event.
        window_name (str, optional, default='Open3D'): The displayed title of the visualization window.
        width (int, optional, default=1920): The width of the visualization window.
        height (int, optional, default=1080): The height of the visualization window.
        left (int, optional, default=50): The left margin of the visualization window.
        top (int, optional, default=50): The top margin of the visualization window.
    
    Returns:
        None
    """
def draw_geometries_with_custom_animation(geometry_list: list[open3d.cuda.pybind.geometry.Geometry], window_name: str = 'Open3D', width: int = 1920, height: int = 1080, left: int = 50, top: int = 50, optional_view_trajectory_json_file: os.PathLike = '') -> None:
    """
    Function to draw a list of geometry::Geometry objects with a GUI that supports animation
    
    Args:
        geometry_list (list[open3d.cuda.pybind.geometry.Geometry]): List of geometries to be visualized.
        window_name (str, optional, default='Open3D'): The displayed title of the visualization window.
        width (int, optional, default=1920): The width of the visualization window.
        height (int, optional, default=1080): The height of the visualization window.
        left (int, optional, default=50): The left margin of the visualization window.
        top (int, optional, default=50): The top margin of the visualization window.
        optional_view_trajectory_json_file (os.PathLike, optional, default=''): Camera trajectory json file path for custom animation.
    
    Returns:
        None
    """
def draw_geometries_with_editing(geometry_list: list[open3d.cuda.pybind.geometry.Geometry], window_name: str = 'Open3D', width: int = 1920, height: int = 1080, left: int = 50, top: int = 50) -> None:
    """
    Function to draw a list of geometry::Geometry providing user interaction
    
    Args:
        geometry_list (list[open3d.cuda.pybind.geometry.Geometry]): List of geometries to be visualized.
        window_name (str, optional, default='Open3D'): The displayed title of the visualization window.
        width (int, optional, default=1920): The width of the visualization window.
        height (int, optional, default=1080): The height of the visualization window.
        left (int, optional, default=50): The left margin of the visualization window.
        top (int, optional, default=50): The top margin of the visualization window.
    
    Returns:
        None
    """
def draw_geometries_with_key_callbacks(geometry_list: list[open3d.cuda.pybind.geometry.Geometry], key_to_callback: dict[int, typing.Callable[[Visualizer], bool]], window_name: str = 'Open3D', width: int = 1920, height: int = 1080, left: int = 50, top: int = 50) -> None:
    """
    Function to draw a list of geometry::Geometry objects with a customized key-callback mapping
    
    Args:
        geometry_list (list[open3d.cuda.pybind.geometry.Geometry]): List of geometries to be visualized.
        key_to_callback (dict[int, Callable[[open3d.cuda.pybind.visualization.Visualizer], bool]]): Map of key to call back functions.
        window_name (str, optional, default='Open3D'): The displayed title of the visualization window.
        width (int, optional, default=1920): The width of the visualization window.
        height (int, optional, default=1080): The height of the visualization window.
        left (int, optional, default=50): The left margin of the visualization window.
        top (int, optional, default=50): The top margin of the visualization window.
    
    Returns:
        None
    """
def draw_geometries_with_vertex_selection(geometry_list: list[open3d.cuda.pybind.geometry.Geometry], window_name: str = 'Open3D', width: int = 1920, height: int = 1080, left: int = 50, top: int = 50) -> None:
    """
    Function to draw a list of geometry::Geometry providing ability for user to select points
    
    Args:
        geometry_list (list[open3d.cuda.pybind.geometry.Geometry]): List of geometries to be visualized.
        window_name (str, optional, default='Open3D'): The displayed title of the visualization window.
        width (int, optional, default=1920): The width of the visualization window.
        height (int, optional, default=1080): The height of the visualization window.
        left (int, optional, default=50): The left margin of the visualization window.
        top (int, optional, default=50): The top margin of the visualization window.
    
    Returns:
        None
    """
def read_selection_polygon_volume(filename: os.PathLike) -> SelectionPolygonVolume:
    """
    Function to read SelectionPolygonVolume from file
    
    Args:
        filename (os.PathLike): The file path.
    
    Returns:
        open3d.cuda.pybind.visualization.SelectionPolygonVolume
    """
Color: MeshColorOption
Default: MeshColorOption
Normal: MeshColorOption
XCoordinate: MeshColorOption
YCoordinate: MeshColorOption
ZCoordinate: MeshColorOption
