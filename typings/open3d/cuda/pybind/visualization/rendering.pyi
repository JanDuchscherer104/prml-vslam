from __future__ import annotations
import numpy
import open3d.cuda.pybind.camera
import open3d.cuda.pybind.geometry
import open3d.cuda.pybind.t.geometry
import typing

__all__: list[str] = [
    "Camera",
    "ColorGrading",
    "Gradient",
    "MaterialRecord",
    "OffscreenRenderer",
    "Open3DScene",
    "Renderer",
    "Scene",
    "TextureHandle",
    "TriangleMeshModel",
    "View",
]

class Camera:
    """
    Camera object
    """
    class FovType:
        """
        Enum class for Camera field of view types.

        Members:

          Vertical

          Horizontal
        """

        Horizontal: typing.ClassVar[Camera.FovType]
        Vertical: typing.ClassVar[Camera.FovType]
        __members__: typing.ClassVar[dict[str, Camera.FovType]]
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

    class Projection:
        """
        Enum class for Camera projection types.

        Members:

          Perspective

          Ortho
        """

        Ortho: typing.ClassVar[Camera.Projection]
        Perspective: typing.ClassVar[Camera.Projection]
        __members__: typing.ClassVar[dict[str, Camera.Projection]]
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

    Horizontal: typing.ClassVar[Camera.FovType]
    Ortho: typing.ClassVar[Camera.Projection]
    Perspective: typing.ClassVar[Camera.Projection]
    Vertical: typing.ClassVar[Camera.FovType]
    def copy_from(self, camera: Camera) -> None:
        """
        Copies the settings from the camera passed as the argument into this camera
        """
    def get_far(self) -> float:
        """
        Returns the distance from the camera to the far plane
        """
    def get_field_of_view(self) -> float:
        """
        Returns the field of view of camera, in degrees. Only valid if it was passed to set_projection().
        """
    def get_field_of_view_type(self) -> Camera.FovType:
        """
        Returns the field of view type. Only valid if it was passed to set_projection().
        """
    def get_model_matrix(self) -> numpy.ndarray:
        """
        Returns the model matrix of the camera
        """
    def get_near(self) -> float:
        """
        Returns the distance from the camera to the near plane
        """
    def get_projection_matrix(self) -> numpy.ndarray:
        """
        Returns the projection matrix of the camera
        """
    def get_view_matrix(self) -> numpy.ndarray:
        """
        Returns the view matrix of the camera
        """
    def look_at(self, center: numpy.ndarray, eye: numpy.ndarray, up: numpy.ndarray) -> None:
        """
        Sets the position and orientation of the camera:
        """
    @typing.overload
    def set_projection(
        self,
        field_of_view: float,
        aspect_ratio: float,
        near_plane: float,
        far_plane: float,
        field_of_view_type: Camera.FovType,
    ) -> None:
        """
        Sets a perspective projection.
        """
    @typing.overload
    def set_projection(
        self,
        projection_type: Camera.Projection,
        left: float,
        right: float,
        bottom: float,
        top: float,
        near: float,
        far: float,
    ) -> None:
        """
        Sets the camera projection via a viewing frustum.
        """
    @typing.overload
    def set_projection(
        self, intrinsics: numpy.ndarray, near_plane: float, far_plane: float, image_width: float, image_height: float
    ) -> None:
        """
        Sets the camera projection via intrinsics matrix.
        """
    def unproject(self, x: float, y: float, z: float, view_width: float, view_height: float) -> numpy.ndarray:
        """
        Takes the (x, y, z) location in the view, where x, y are the number of pixels from the upper left of the view, and z is the depth value. Returns the world coordinate (x', y', z').
        """

class ColorGrading:
    """
    Parameters to control color grading options
    """
    class Quality:
        """
        Quality level of color grading operations

        Members:

          LOW

          MEDIUM

          HIGH

          ULTRA
        """

        HIGH: typing.ClassVar[ColorGrading.Quality]
        LOW: typing.ClassVar[ColorGrading.Quality]
        MEDIUM: typing.ClassVar[ColorGrading.Quality]
        ULTRA: typing.ClassVar[ColorGrading.Quality]
        __members__: typing.ClassVar[dict[str, ColorGrading.Quality]]
        def __eq__(self, other: typing.Any) -> bool: ...
        def __getstate__(self) -> int: ...
        def __hash__(self) -> int: ...
        def __index__(self) -> int: ...
        def __init__(self, value: int) -> None: ...
        def __int__(self) -> int: ...
        def __ne__(self, other: typing.Any) -> bool: ...
        def __repr__(self) -> str: ...
        def __setstate__(self, state: int) -> None: ...
        def __str__(self) -> str: ...
        @property
        def name(self) -> str: ...
        @property
        def value(self) -> int: ...

    class ToneMapping:
        """
        Specifies the tone-mapping algorithm

        Members:

          LINEAR

          ACES_LEGACY

          ACES

          FILMIC

          UCHIMURA

          REINHARD

          DISPLAY_RANGE
        """

        ACES: typing.ClassVar[ColorGrading.ToneMapping]
        ACES_LEGACY: typing.ClassVar[ColorGrading.ToneMapping]
        DISPLAY_RANGE: typing.ClassVar[ColorGrading.ToneMapping]
        FILMIC: typing.ClassVar[ColorGrading.ToneMapping]
        LINEAR: typing.ClassVar[ColorGrading.ToneMapping]
        REINHARD: typing.ClassVar[ColorGrading.ToneMapping]
        UCHIMURA: typing.ClassVar[ColorGrading.ToneMapping]
        __members__: typing.ClassVar[dict[str, ColorGrading.ToneMapping]]
        def __eq__(self, other: typing.Any) -> bool: ...
        def __getstate__(self) -> int: ...
        def __hash__(self) -> int: ...
        def __index__(self) -> int: ...
        def __init__(self, value: int) -> None: ...
        def __int__(self) -> int: ...
        def __ne__(self, other: typing.Any) -> bool: ...
        def __repr__(self) -> str: ...
        def __setstate__(self, state: int) -> None: ...
        def __str__(self) -> str: ...
        @property
        def name(self) -> str: ...
        @property
        def value(self) -> int: ...

    def __init__(self, arg0: ColorGrading.Quality, arg1: ColorGrading.ToneMapping) -> None: ...
    @property
    def quality(self) -> ColorGrading.Quality:
        """
        Quality of color grading operations. High quality is more accurate but slower
        """
    @quality.setter
    def quality(self, arg1: ColorGrading.Quality) -> None: ...
    @property
    def temperature(self) -> float:
        """
        White balance color temperature
        """
    @temperature.setter
    def temperature(self, arg1: float) -> None: ...
    @property
    def tint(self) -> float:
        """
        Tint on the green/magenta axis. Ranges from -1.0 to 1.0.
        """
    @tint.setter
    def tint(self, arg1: float) -> None: ...
    @property
    def tone_mapping(self) -> ColorGrading.ToneMapping:
        """
        The tone mapping algorithm to apply. Must be one of Linear, AcesLegacy, Aces, Filmic, Uchimura, Rienhard, Display Range(for debug)
        """
    @tone_mapping.setter
    def tone_mapping(self, arg1: ColorGrading.ToneMapping) -> None: ...

class Gradient:
    """
    Manages a gradient for the unlitGradient shader.In gradient mode, the array of points specifies points along the gradient, from 0 to 1 (inclusive). These do need to be evenly spaced.Simple greyscale:    [ ( 0.0, black ),      ( 1.0, white ) ]Rainbow (note the gaps around green):    [ ( 0.000, blue ),      ( 0.125, cornflower blue ),      ( 0.250, cyan ),      ( 0.500, green ),      ( 0.750, yellow ),      ( 0.875, orange ),      ( 1.000, red ) ]The gradient will generate a largish texture, so it should be fairly smooth, but the boundaries may not be exactly as specified due to quantization imposed by the fixed size of the texture.  The points *must* be sorted from the smallest value to the largest. The values must be in the range [0, 1].
    """
    class Mode:
        """
        Members:

          GRADIENT

          LUT
        """

        GRADIENT: typing.ClassVar[Gradient.Mode]
        LUT: typing.ClassVar[Gradient.Mode]
        __members__: typing.ClassVar[dict[str, Gradient.Mode]]
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

    class Point:
        def __init__(self, arg0: float, arg1: numpy.ndarray) -> None: ...
        def __repr__(self) -> str: ...
        @property
        def color(self) -> numpy.ndarray:
            """
            [R, G, B, A]. Color values must be in [0.0, 1.0]
            """
        @color.setter
        def color(self, arg0: numpy.ndarray) -> None: ...
        @property
        def value(self) -> float:
            """
            Must be within 0.0 and 1.0
            """
        @value.setter
        def value(self, arg0: float) -> None: ...

    GRADIENT: typing.ClassVar[Gradient.Mode]
    LUT: typing.ClassVar[Gradient.Mode]
    mode: Gradient.Mode
    points: list[Gradient.Point]
    @typing.overload
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(self, arg0: list[Gradient.Point]) -> None: ...

class MaterialRecord:
    """
    Describes the real-world, physically based (PBR) material used to render a geometry
    """

    absorption_color: numpy.ndarray
    absorption_distance: float
    albedo_img: open3d.cuda.pybind.geometry.Image
    anisotropy_img: open3d.cuda.pybind.geometry.Image
    ao_img: open3d.cuda.pybind.geometry.Image
    ao_rough_metal_img: open3d.cuda.pybind.geometry.Image
    aspect_ratio: float
    base_anisotropy: float
    base_clearcoat: float
    base_clearcoat_roughness: float
    base_color: numpy.ndarray
    base_metallic: float
    base_reflectance: float
    base_roughness: float
    clearcoat_img: open3d.cuda.pybind.geometry.Image
    clearcoat_roughness_img: open3d.cuda.pybind.geometry.Image
    emissive_color: numpy.ndarray
    generic_imgs: dict[str, open3d.cuda.pybind.geometry.Image]
    generic_params: dict[str, numpy.ndarray]
    gradient: Gradient
    ground_plane_axis: float
    has_alpha: bool
    metallic_img: open3d.cuda.pybind.geometry.Image
    normal_img: open3d.cuda.pybind.geometry.Image
    point_size: float
    reflectance_img: open3d.cuda.pybind.geometry.Image
    roughness_img: open3d.cuda.pybind.geometry.Image
    sRGB_color: bool
    scalar_max: float
    scalar_min: float
    shader: str
    thickness: float
    transmission: float
    def __init__(self) -> None: ...
    @property
    def line_width(self) -> float:
        """
        Requires 'shader' to be 'unlitLine'
        """
    @line_width.setter
    def line_width(self, arg0: float) -> None: ...

class OffscreenRenderer:
    """
    Renderer instance that can be used for rendering to an image
    """
    def __init__(self, width: int, height: int, resource_path: str = "") -> None:
        """
        Takes width, height and optionally a resource_path.  If unspecified, resource_path will use the resource path from the installed Open3D library.
        """
    def render_to_depth_image(self, z_in_view_space: bool = False) -> open3d.cuda.pybind.geometry.Image:
        """
        Renders scene depth buffer to a float image, blocking until the image is returned. Pixels range from 0 (near plane) to 1 (far plane). If z_in_view_space is set to True then pixels are pre-transformed into view space (i.e., distance from camera).
        """
    def render_to_image(self) -> open3d.cuda.pybind.geometry.Image:
        """
        Renders scene to an image, blocking until the image is returned
        """
    @typing.overload
    def setup_camera(
        self,
        vertical_field_of_view: float,
        center: numpy.ndarray,
        eye: numpy.ndarray,
        up: numpy.ndarray,
        near_clip: float = -1.0,
        far_clip: float = -1.0,
    ) -> None:
        """
        Sets camera view using bounding box of current geometry if the near_clip and far_clip parameters are not set
        """
    @typing.overload
    def setup_camera(
        self, intrinsics: open3d.cuda.pybind.camera.PinholeCameraIntrinsic, extrinsic_matrix: numpy.ndarray
    ) -> None:
        """
        Sets the camera view using bounding box of current geometry
        """
    @typing.overload
    def setup_camera(
        self,
        intrinsic_matrix: numpy.ndarray,
        extrinsic_matrix: numpy.ndarray,
        intrinsic_width_px: int,
        intrinsic_height_px: int,
    ) -> None:
        """
        Sets the camera view using bounding box of current geometry
        """
    @property
    def scene(self) -> Open3DScene:
        """
        Returns the Open3DScene for this renderer. This scene is destroyed when the renderer is destroyed and should not be accessed after that point.
        """

class Open3DScene:
    """
    High-level scene for rending
    """
    class LightingProfile:
        """
        Enum for conveniently setting lighting

        Members:

          HARD_SHADOWS

          DARK_SHADOWS

          MED_SHADOWS

          SOFT_SHADOWS

          NO_SHADOWS
        """

        DARK_SHADOWS: typing.ClassVar[Open3DScene.LightingProfile]
        HARD_SHADOWS: typing.ClassVar[Open3DScene.LightingProfile]
        MED_SHADOWS: typing.ClassVar[Open3DScene.LightingProfile]
        NO_SHADOWS: typing.ClassVar[Open3DScene.LightingProfile]
        SOFT_SHADOWS: typing.ClassVar[Open3DScene.LightingProfile]
        __members__: typing.ClassVar[dict[str, Open3DScene.LightingProfile]]
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

    DARK_SHADOWS: typing.ClassVar[Open3DScene.LightingProfile]
    HARD_SHADOWS: typing.ClassVar[Open3DScene.LightingProfile]
    MED_SHADOWS: typing.ClassVar[Open3DScene.LightingProfile]
    NO_SHADOWS: typing.ClassVar[Open3DScene.LightingProfile]
    SOFT_SHADOWS: typing.ClassVar[Open3DScene.LightingProfile]
    def __init__(self, arg0: Renderer) -> None: ...
    @typing.overload
    def add_geometry(
        self,
        name: str,
        geometry: open3d.cuda.pybind.geometry.Geometry3D,
        material: MaterialRecord,
        add_downsampled_copy_for_fast_rendering: bool = True,
    ) -> None:
        """
        Adds a geometry with the specified name. Default visible is true.
        """
    @typing.overload
    def add_geometry(
        self,
        name: str,
        geometry: open3d.cuda.pybind.t.geometry.Geometry,
        material: MaterialRecord,
        add_downsampled_copy_for_fast_rendering: bool = True,
    ) -> None:
        """
        Adds a geometry with the specified name. Default visible is true.
        """
    def add_model(self, name: str, model: TriangleMeshModel) -> None:
        """
        Adds TriangleMeshModel to the scene.
        """
    def clear_geometry(self) -> None: ...
    def geometry_is_visible(self, name: str) -> bool:
        """
        Returns True if the geometry name is visible
        """
    def get_geometry_transform(self, name: str) -> numpy.ndarray:
        """
        Returns the pose of the geometry name in the scene
        """
    def has_geometry(self, name: str) -> bool:
        """
        Returns True if the geometry has been added to the scene, False otherwise
        """
    def modify_geometry_material(self, name: str, material: MaterialRecord) -> None:
        """
        Modifies the material of the specified geometry
        """
    def remove_geometry(self, name: str) -> None:
        """
        Removes the geometry with the given name
        """
    def set_background(self, color: numpy.ndarray, image: open3d.cuda.pybind.geometry.Image = None) -> None:
        """
        set_background([r, g, b, a], image=None). Sets the background color and (optionally) image of the scene.
        """
    def set_background_color(self, arg0: numpy.ndarray) -> None:
        """
        This function has been deprecated. Please use set_background() instead.
        """
    def set_geometry_transform(self, name: str, transform: numpy.ndarray) -> None:
        """
        sets the pose of the geometry name to transform
        """
    def set_lighting(self, profile: Open3DScene.LightingProfile, sun_dir: numpy.ndarray) -> None:
        """
        Sets a simple lighting model. The default value is set_lighting(Open3DScene.LightingProfile.MED_SHADOWS, (0.577, -0.577, -0.577))
        """
    def set_view_size(self, width: int, height: int) -> None:
        """
        Sets the view size. This should not be used except for rendering to an image
        """
    def show_axes(self, enable: bool) -> None:
        """
        Toggles display of xyz axes
        """
    def show_geometry(self, name: str, show: bool) -> None:
        """
        Shows or hides the geometry with the given name
        """
    def show_ground_plane(self, enable: bool, plane: Scene.GroundPlane) -> None:
        """
        Toggles display of ground plane
        """
    def show_skybox(self, enable: bool) -> None:
        """
        Toggles display of the skybox
        """
    def update_material(self, material: MaterialRecord) -> None:
        """
        Applies the passed material to all the geometries
        """
    @property
    def background_color(self) -> numpy.ndarray:
        """
        The background color (read-only)
        """
    @property
    def bounding_box(self) -> open3d.cuda.pybind.geometry.AxisAlignedBoundingBox:
        """
        The bounding box of all the items in the scene, visible and invisible
        """
    @property
    def camera(self) -> Camera:
        """
        The camera object (read-only)
        """
    @property
    def downsample_threshold(self) -> int:
        """
        Minimum number of points before downsampled point clouds are created and used when rendering speed is important
        """
    @downsample_threshold.setter
    def downsample_threshold(self, arg1: int) -> None: ...
    @property
    def scene(self) -> Scene:
        """
        The low-level rendering scene object (read-only)
        """
    @property
    def view(self) -> View:
        """
        The low level view associated with the scene
        """

class Renderer:
    """
    Renderer class that manages 3D resources. Get from gui.Window.
    """
    def add_texture(self, image: open3d.cuda.pybind.geometry.Image, is_sRGB: bool = False) -> TextureHandle:
        """
        Adds a texture. The first parameter is the image, the second parameter is optional and is True if the image is in the sRGB colorspace and False otherwise
        """
    def remove_texture(self, texture: TextureHandle) -> None:
        """
        Deletes the texture. This does not remove the texture from any existing materials or GUI widgets, and must be done prior to this call.
        """
    def set_clear_color(self, arg0: numpy.ndarray) -> None:
        """
        Sets the background color for the renderer, [r, g, b, a]. Applies to everything being rendered, so it essentially acts as the background color of the window
        """
    def update_texture(
        self, texture: TextureHandle, image: open3d.cuda.pybind.geometry.Image, is_sRGB: bool = False
    ) -> bool:
        """
        Updates the contents of the texture to be the new image, or returns False and does nothing if the image is a different size. It is more efficient to call update_texture() rather than removing and adding a new texture, especially when changes happen frequently, such as when implementing video. add_texture(geometry.Image, bool). The first parameter is the image, the second parameter is optional and is True if the image is in the sRGB colorspace and False otherwise
        """

class Scene:
    """
    Low-level rendering scene
    """
    class GroundPlane:
        """
        Plane on which to show ground plane: XZ, XY, or YZ

        Members:

          XZ

          XY

          YZ
        """

        XY: typing.ClassVar[Scene.GroundPlane]
        XZ: typing.ClassVar[Scene.GroundPlane]
        YZ: typing.ClassVar[Scene.GroundPlane]
        __members__: typing.ClassVar[dict[str, Scene.GroundPlane]]
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

    UPDATE_COLORS_FLAG: typing.ClassVar[int] = 4
    UPDATE_NORMALS_FLAG: typing.ClassVar[int] = 2
    UPDATE_POINTS_FLAG: typing.ClassVar[int] = 1
    UPDATE_UV0_FLAG: typing.ClassVar[int] = 8
    XY: typing.ClassVar[Scene.GroundPlane]
    XZ: typing.ClassVar[Scene.GroundPlane]
    YZ: typing.ClassVar[Scene.GroundPlane]
    def add_camera(self, name: str, camera: Camera) -> None:
        """
        Adds a camera to the scene
        """
    def add_directional_light(
        self, name: str, color: numpy.ndarray, direction: numpy.ndarray, intensity: float, cast_shadows: bool
    ) -> bool:
        """
        Adds a directional light to the scene
        """
    @typing.overload
    def add_geometry(
        self,
        name: str,
        geometry: open3d.cuda.pybind.geometry.Geometry3D,
        material: MaterialRecord,
        downsampled_name: str = "",
        downsample_threshold: int = 18446744073709551615,
    ) -> bool:
        """
        Adds a Geometry with a material to the scene
        """
    @typing.overload
    def add_geometry(
        self,
        name: str,
        geometry: open3d.cuda.pybind.t.geometry.Geometry,
        material: MaterialRecord,
        downsampled_name: str = "",
        downsample_threshold: int = 18446744073709551615,
    ) -> bool:
        """
        Adds a Geometry with a material to the scene
        """
    def add_point_light(
        self,
        name: str,
        color: numpy.ndarray,
        position: numpy.ndarray,
        intensity: float,
        falloff: float,
        cast_shadows: bool,
    ) -> bool:
        """
        Adds a point light to the scene.
        """
    def add_spot_light(
        self,
        name: str,
        color: numpy.ndarray,
        position: numpy.ndarray,
        direction: numpy.ndarray,
        intensity: float,
        falloff: float,
        inner_cone_angle: float,
        outer_cone_angle: float,
        cast_shadows: bool,
    ) -> bool:
        """
        Adds a spot light to the scene.
        """
    def enable_indirect_light(self, enable: bool) -> None:
        """
        Enables or disables indirect lighting
        """
    def enable_light_shadow(self, name: str, can_cast_shadows: bool) -> None:
        """
        Changes whether a point, spot, or directional light can cast shadows.
        """
    def enable_sun_light(self, enable: bool) -> None: ...
    def geometry_is_visible(self, name: str) -> bool:
        """
        Returns false if the geometry is hidden, True otherwise. Note: this is different from whether or not the geometry is in view.
        """
    def geometry_shadows(self, name: str, cast_shadows: bool, receive_shadows: bool) -> None:
        """
        Controls whether an object casts and/or receives shadows: geometry_shadows(name, cast_shadows, receieve_shadows)
        """
    def has_geometry(self, name: str) -> bool:
        """
        Returns True if a geometry with the provided name exists in the scene.
        """
    def remove_camera(self, name: str) -> None:
        """
        Removes the camera with the given name
        """
    def remove_geometry(self, name: str) -> None:
        """
        Removes the named geometry from the scene.
        """
    def remove_light(self, name: str) -> None:
        """
        Removes the named light from the scene.
        """
    def render_to_depth_image(self, arg0: typing.Callable[[open3d.cuda.pybind.geometry.Image], None]) -> None:
        """
        Renders the scene to a depth image. This can only be used in GUI app. To render without a window, use ``Application.render_to_depth_image``. Pixels range from 0.0 (near plane) to 1.0 (far plane)
        """
    def render_to_image(self, arg0: typing.Callable[[open3d.cuda.pybind.geometry.Image], None]) -> None:
        """
        Renders the scene to an image. This can only be used in a GUI app. To render without a window, use ``Application.render_to_image``.
        """
    def set_active_camera(self, name: str) -> None:
        """
        Sets the camera with the given name as the active camera for the scene
        """
    def set_geometry_culling(self, name: str, enable: bool) -> None:
        """
        Enable/disable view frustum culling on the named object. Culling is enabled by default.
        """
    def set_geometry_priority(self, name: str, priority: int) -> None:
        """
        Set sorting priority for named object. Objects with higher priority will be rendering on top of overlapping geometry with lower priority.
        """
    def set_indirect_light(self, name: str) -> bool:
        """
        Loads the indirect light. The name parameter is the name of the file to load
        """
    def set_indirect_light_intensity(self, intensity: float) -> None:
        """
        Sets the brightness of the indirect light
        """
    def set_sun_light(self, direction: numpy.ndarray, color: numpy.ndarray, intensity: float) -> None:
        """
        Sets the parameters of the sun light direction, color, intensity
        """
    def show_geometry(self, name: str, show: bool) -> None:
        """
        Show or hide the named geometry.
        """
    def update_geometry(
        self, name: str, point_cloud: open3d.cuda.pybind.t.geometry.PointCloud, update_flag: int
    ) -> None:
        """
        Updates the flagged arrays from the tgeometry.PointCloud. The flags should be ORed from Scene.UPDATE_POINTS_FLAG, Scene.UPDATE_NORMALS_FLAG, Scene.UPDATE_COLORS_FLAG, and Scene.UPDATE_UV0_FLAG
        """
    def update_light_color(self, name: str, color: numpy.ndarray) -> None:
        """
        Changes a point, spot, or directional light's color
        """
    def update_light_cone_angles(self, name: str, inner_cone_angle: float, outer_cone_angle: float) -> None:
        """
        Changes a spot light's inner and outer cone angles.
        """
    def update_light_direction(self, name: str, direction: numpy.ndarray) -> None:
        """
        Changes a spot or directional light's direction.
        """
    def update_light_falloff(self, name: str, falloff: float) -> None:
        """
        Changes a point or spot light's falloff.
        """
    def update_light_intensity(self, name: str, intensity: float) -> None:
        """
        Changes a point, spot or directional light's intensity.
        """
    def update_light_position(self, name: str, position: numpy.ndarray) -> None:
        """
        Changes a point or spot light's position.
        """

class TextureHandle:
    """
    Handle to a texture
    """

class TriangleMeshModel:
    """
    A list of geometry.TriangleMesh and Material that can describe a complex model with multiple meshes, such as might be stored in an FBX, OBJ, or GLTF file
    """
    class MeshInfo:
        """ """

        material_idx: int
        mesh: open3d.cuda.pybind.geometry.TriangleMesh
        mesh_name: str
        def __init__(self, arg0: open3d.cuda.pybind.geometry.TriangleMesh, arg1: str, arg2: int) -> None: ...

    materials: list[MaterialRecord]
    meshes: list[TriangleMeshModel.MeshInfo]
    def __init__(self) -> None: ...

class View:
    """
    Low-level view class
    """
    class ShadowType:
        """
        Available shadow mapping algorithm options

        Members:

          PCF

          VSM
        """

        PCF: typing.ClassVar[View.ShadowType]
        VSM: typing.ClassVar[View.ShadowType]
        __members__: typing.ClassVar[dict[str, View.ShadowType]]
        def __eq__(self, other: typing.Any) -> bool: ...
        def __getstate__(self) -> int: ...
        def __hash__(self) -> int: ...
        def __index__(self) -> int: ...
        def __init__(self, value: int) -> None: ...
        def __int__(self) -> int: ...
        def __ne__(self, other: typing.Any) -> bool: ...
        def __repr__(self) -> str: ...
        def __setstate__(self, state: int) -> None: ...
        def __str__(self) -> str: ...
        @property
        def name(self) -> str: ...
        @property
        def value(self) -> int: ...

    def get_camera(self) -> Camera:
        """
        Returns the Camera associated with this View.
        """
    def set_ambient_occlusion(self, enabled: bool, ssct_enabled: bool = False) -> None:
        """
        True to enable, False to disable ambient occlusion. Optionally, screen-space cone tracing may be enabled with ssct_enabled=True.
        """
    def set_antialiasing(self, enabled: bool, temporal: bool = False) -> None:
        """
        True to enable, False to disable anti-aliasing. Note that this only impacts anti-aliasing post-processing. MSAA is controlled separately by `set_sample_count`. Temporal anti-aliasing may be optionally enabled with temporal=True.
        """
    def set_color_grading(self, arg0: ColorGrading) -> None:
        """
        Sets the parameters to be used for the color grading algorithms
        """
    def set_post_processing(self, arg0: bool) -> None:
        """
        True to enable, False to disable post processing. Post processing effects include: color grading, ambient occlusion (and other screen space effects), and anti-aliasing.
        """
    def set_sample_count(self, arg0: int) -> None:
        """
        Sets the sample count for MSAA. Set to 1 to disable MSAA. Typical values are 2, 4 or 8. The maximum possible value depends on the underlying GPU and OpenGL driver.
        """
    def set_shadowing(self, enabled: bool, type: View.ShadowType = ...) -> None:
        """
        True to enable, false to enable all shadow mapping when rendering this View. When enabling shadow mapping you may also specify one of two shadow mapping algorithms: PCF (default) or VSM. Note: shadowing is enabled by default with PCF shadow mapping.
        """
