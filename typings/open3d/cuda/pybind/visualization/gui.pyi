from __future__ import annotations
import numpy
import open3d.cuda.pybind.camera
import open3d.cuda.pybind.geometry
import open3d.cuda.pybind.t.geometry
import open3d.cuda.pybind.visualization.rendering
import typing

__all__: list[str] = [
    "A",
    "ALT",
    "AMPERSAND",
    "ASTERISK",
    "AT",
    "Application",
    "B",
    "BACKSLASH",
    "BACKSPACE",
    "BACKTICK",
    "BUTTON4",
    "BUTTON5",
    "Button",
    "C",
    "CAPS_LOCK",
    "CARET",
    "COLON",
    "COMMA",
    "CTRL",
    "CheckableTextTreeCell",
    "Checkbox",
    "CollapsableVert",
    "Color",
    "ColorEdit",
    "ColormapTreeCell",
    "Combobox",
    "D",
    "DELETE",
    "DOLLAR_SIGN",
    "DOUBLE_QUOTE",
    "DOWN",
    "Dialog",
    "E",
    "EIGHT",
    "END",
    "ENTER",
    "EQUALS",
    "ESCAPE",
    "EXCLAMATION_MARK",
    "F",
    "F1",
    "F10",
    "F11",
    "F12",
    "F2",
    "F3",
    "F4",
    "F5",
    "F6",
    "F7",
    "F8",
    "F9",
    "FIVE",
    "FOUR",
    "FileDialog",
    "FontDescription",
    "FontStyle",
    "G",
    "GREATER_THAN",
    "H",
    "HASH",
    "HOME",
    "Horiz",
    "I",
    "INSERT",
    "ImageWidget",
    "J",
    "K",
    "KeyEvent",
    "KeyModifier",
    "KeyName",
    "L",
    "LEFT",
    "LEFT_BRACE",
    "LEFT_BRACKET",
    "LEFT_CONTROL",
    "LEFT_PAREN",
    "LEFT_SHIFT",
    "LESS_THAN",
    "LUTTreeCell",
    "Label",
    "Label3D",
    "Layout1D",
    "LayoutContext",
    "ListView",
    "M",
    "META",
    "MIDDLE",
    "MINUS",
    "Margins",
    "Menu",
    "MouseButton",
    "MouseEvent",
    "N",
    "NINE",
    "NONE",
    "NumberEdit",
    "O",
    "ONE",
    "P",
    "PAGE_DOWN",
    "PAGE_UP",
    "PERCENT",
    "PERIOD",
    "PIPE",
    "PLUS",
    "ProgressBar",
    "Q",
    "QUESTION_MARK",
    "QUOTE",
    "R",
    "RIGHT",
    "RIGHT_BRACE",
    "RIGHT_BRACKET",
    "RIGHT_CONTROL",
    "RIGHT_PAREN",
    "RIGHT_SHIFT",
    "RadioButton",
    "Rect",
    "S",
    "SEMICOLON",
    "SEVEN",
    "SHIFT",
    "SIX",
    "SLASH",
    "SPACE",
    "SceneWidget",
    "ScrollableVert",
    "Size",
    "Slider",
    "StackedWidget",
    "T",
    "TAB",
    "THREE",
    "TILDE",
    "TWO",
    "TabControl",
    "TextEdit",
    "Theme",
    "ToggleSwitch",
    "TreeView",
    "U",
    "UIImage",
    "UNDERSCORE",
    "UNKNOWN",
    "UP",
    "V",
    "VGrid",
    "VectorEdit",
    "Vert",
    "W",
    "Widget",
    "WidgetProxy",
    "WidgetStack",
    "Window",
    "WindowBase",
    "X",
    "Y",
    "Z",
    "ZERO",
]

class Application:
    """
    Global application singleton. This owns the menubar, windows, and event loop
    """

    DEFAULT_FONT_ID: typing.ClassVar[int] = 0
    instance: typing.ClassVar[Application]
    def __repr__(self) -> str: ...
    def add_font(self, arg0: FontDescription) -> int:
        """
        Adds a font. Must be called after initialize() and before a window is created. Returns the font id, which can be used to change the font in widgets such as Label which support custom fonts.
        """
    def add_window(self, arg0: WindowBase) -> None:
        """
        Adds a window to the application. This is only necessary when creating an object that is a Window directly, rather than with create_window
        """
    def create_window(
        self, title: str = "", width: int = -1, height: int = -1, x: int = -1, y: int = -1, flags: int = 0
    ) -> Window:
        """
        Creates a window and adds it to the application. To programmatically destroy the window do window.close().Usage: create_window(title, width, height, x, y, flags). x, y, and flags are optional.
        """
    @typing.overload
    def initialize(self) -> None:
        """
        Initializes the application, using the resources included in the wheel. One of the `initialize` functions _must_ be called prior to using anything in the gui module
        """
    @typing.overload
    def initialize(self, arg0: str) -> None:
        """
        Initializes the application with location of the resources provided by the caller. One of the `initialize` functions _must_ be called prior to using anything in the gui module
        """
    def post_to_main_thread(self, arg0: WindowBase, arg1: typing.Callable[[], None]) -> None:
        """
        Runs the provided function on the main thread. This can be used to execute UI-related code at a safe point in time. If the UI changes, you will need to manually request a redraw of the window with w.post_redraw()
        """
    def quit(self) -> None:
        """
        Closes all the windows, exiting as a result
        """
    def render_to_image(
        self, arg0: open3d.cuda.pybind.visualization.rendering.Open3DScene, arg1: int, arg2: int
    ) -> open3d.cuda.pybind.geometry.Image:
        """
        Renders a scene to an image and returns the image. If you are rendering without a visible window you should use open3d.visualization.rendering.RenderToImage instead
        """
    def run(self) -> None:
        """
        Runs the event loop. After this finishes, all windows and widgets should be considered uninitialized, even if they are still held by Python variables. Using them is unsafe, even if run() is called again.
        """
    def run_in_thread(self, arg0: typing.Callable[[], None]) -> None:
        """
        Runs function in a separate thread. Do not call GUI functions on this thread, call post_to_main_thread() if this thread needs to change the GUI.
        """
    def run_one_tick(self) -> bool:
        """
        Runs the event loop once, returns True if the app is still running, or False if all the windows have closed or quit() has been called.
        """
    def set_font(self, arg0: int, arg1: FontDescription) -> None:
        """
        Changes the contents of an existing font, for instance, the default font.
        """
    @property
    def menubar(self) -> Menu:
        """
        The Menu for the application (initially None)
        """
    @menubar.setter
    def menubar(self, arg1: Menu) -> None: ...
    @property
    def now(self) -> float:
        """
        Returns current time in seconds
        """
    @property
    def resource_path(self) -> str:
        """
        Returns a string with the path to the resources directory
        """

class Button(Widget):
    """
    Button
    """
    def __init__(self, arg0: str) -> None:
        """
        Creates a button with the given text
        """
    def __repr__(self) -> str: ...
    def set_on_clicked(self, arg0: typing.Callable[[], None]) -> None:
        """
        Calls passed function when button is pressed
        """
    @property
    def horizontal_padding_em(self) -> float:
        """
        Horizontal padding in em units
        """
    @horizontal_padding_em.setter
    def horizontal_padding_em(self, arg1: typing.Any) -> None: ...
    @property
    def is_on(self) -> bool:
        """
        True if the button is toggleable and in the on state
        """
    @is_on.setter
    def is_on(self, arg1: bool) -> None: ...
    @property
    def text(self) -> str:
        """
        Gets/sets the button text.
        """
    @text.setter
    def text(self, arg1: str) -> None: ...
    @property
    def toggleable(self) -> bool:
        """
        True if button is toggleable, False if a push button
        """
    @toggleable.setter
    def toggleable(self, arg1: bool) -> None: ...
    @property
    def vertical_padding_em(self) -> float:
        """
        Vertical padding in em units
        """
    @vertical_padding_em.setter
    def vertical_padding_em(self, arg1: typing.Any) -> None: ...

class CheckableTextTreeCell(Widget):
    """
    TreeView cell with a checkbox and text
    """
    def __init__(self, arg0: str, arg1: bool, arg2: typing.Callable[[bool], None]) -> None:
        """
        Creates a TreeView cell with a checkbox and text. CheckableTextTreeCell(text, is_checked, on_toggled): on_toggled takes a boolean and returns None
        """
    @property
    def checkbox(self) -> Checkbox:
        """
        Returns the checkbox widget (property is read-only)
        """
    @property
    def label(self) -> Label:
        """
        Returns the label widget (property is read-only)
        """

class Checkbox(Widget):
    """
    Checkbox
    """
    def __init__(self, arg0: str) -> None:
        """
        Creates a checkbox with the given text
        """
    def __repr__(self) -> str: ...
    def set_on_checked(self, arg0: typing.Callable[[bool], None]) -> None:
        """
        Calls passed function when checkbox changes state
        """
    @property
    def checked(self) -> bool:
        """
        True if checked, False otherwise
        """
    @checked.setter
    def checked(self, arg1: bool) -> None: ...

class CollapsableVert(Vert):
    """
    Vertical layout with title, whose contents are collapsable
    """
    @typing.overload
    def __init__(self, text: str, spacing: int = 0, margins: Margins = ...) -> None:
        """
        Creates a layout that arranges widgets vertically, top to bottom, making their width equal to the layout's width. First argument is the heading text, the second is the spacing between widgets, and the third is the margins. Both the spacing and the margins default to 0.
        """
    @typing.overload
    def __init__(self, text: str, spacing: float = 0.0, margins: Margins = ...) -> None:
        """
        Creates a layout that arranges widgets vertically, top to bottom, making their width equal to the layout's width. First argument is the heading text, the second is the spacing between widgets, and the third is the margins. Both the spacing and the margins default to 0.
        """
    def get_is_open(self) -> bool:
        """
        Check if widget is open.
        """
    def get_text(self) -> str:
        """
        Gets the text for the CollapsableVert
        """
    def set_is_open(self, is_open: bool) -> None:
        """
        Sets to collapsed (False) or open (True). Requires a call to Window.SetNeedsLayout() afterwards, unless calling before window is visible
        """
    def set_text(self, text: str) -> None:
        """
        Sets the text for the CollapsableVert
        """
    @property
    def font_id(self) -> int:
        """
        Set the font using the FontId returned from Application.add_font()
        """
    @font_id.setter
    def font_id(self, arg1: int) -> None: ...

class Color:
    """
    Stores color for gui classes
    """
    def __init__(self, r: float = 1.0, g: float = 1.0, b: float = 1.0, a: float = 1.0) -> None: ...
    def set_color(self, r: float, g: float, b: float, a: float = 1.0) -> None:
        """
        Sets red, green, blue, and alpha channels, (range: [0.0, 1.0])
        """
    @property
    def alpha(self) -> float:
        """
        Returns alpha channel in the range [0.0, 1.0] (read-only)
        """
    @property
    def blue(self) -> float:
        """
        Returns blue channel in the range [0.0, 1.0] (read-only)
        """
    @property
    def green(self) -> float:
        """
        Returns green channel in the range [0.0, 1.0] (read-only)
        """
    @property
    def red(self) -> float:
        """
        Returns red channel in the range [0.0, 1.0] (read-only)
        """

class ColorEdit(Widget):
    """
    Color picker
    """
    def __init__(self) -> None: ...
    def __repr__(self) -> str: ...
    def set_on_value_changed(self, arg0: typing.Callable[[Color], None]) -> None:
        """
        Calls f(Color) when color changes by user input
        """
    @property
    def color_value(self) -> Color:
        """
        Color value (gui.Color)
        """
    @color_value.setter
    def color_value(self, arg1: Color) -> None: ...

class ColormapTreeCell(Widget):
    """
    TreeView cell with a number edit and color edit
    """
    def __init__(
        self, arg0: float, arg1: Color, arg2: typing.Callable[[float], None], arg3: typing.Callable[[Color], None]
    ) -> None:
        """
        Creates a TreeView cell with a number and a color edit. ColormapTreeCell(value, color, on_value_changed, on_color_changed): on_value_changed takes a double and returns None; on_color_changed takes a gui.Color and returns None
        """
    @property
    def color_edit(self) -> ColorEdit:
        """
        Returns the ColorEdit widget (property is read-only)
        """
    @property
    def number_edit(self) -> NumberEdit:
        """
        Returns the NumberEdit widget (property is read-only)
        """

class Combobox(Widget):
    """
    Exclusive selection from a pull-down menu
    """
    def __init__(self) -> None:
        """
        Creates an empty combobox. Use add_item() to add items
        """
    def add_item(self, arg0: str) -> int:
        """
        Adds an item to the end
        """
    @typing.overload
    def change_item(self, arg0: int, arg1: str) -> None:
        """
        Changes the text of the item at index: change_item(index, newtext)
        """
    @typing.overload
    def change_item(self, arg0: str, arg1: str) -> None:
        """
        Changes the text of the matching item: change_item(text, newtext)
        """
    def clear_items(self) -> None:
        """
        Removes all items
        """
    def get_item(self, index: int) -> str:
        """
        Returns the item at the given index. Index must be valid.
        """
    @typing.overload
    def remove_item(self, arg0: str) -> None:
        """
        Removes the first item of the given text
        """
    @typing.overload
    def remove_item(self, arg0: int) -> None:
        """
        Removes the item at the index
        """
    def set_on_selection_changed(self, arg0: typing.Callable[[str, int], None]) -> None:
        """
        Calls f(str, int) when user selects item from combobox. Arguments are the selected text and selected index, respectively
        """
    @property
    def number_of_items(self) -> int:
        """
        The number of items (read-only)
        """
    @property
    def selected_index(self) -> int:
        """
        The index of the currently selected item
        """
    @selected_index.setter
    def selected_index(self, arg1: int) -> None: ...
    @property
    def selected_text(self) -> str:
        """
        The index of the currently selected item
        """
    @selected_text.setter
    def selected_text(self, arg1: str) -> bool: ...

class Dialog(Widget):
    """
    Dialog
    """
    def __init__(self, arg0: str) -> None:
        """
        Creates a dialog with the given title
        """

class FileDialog(Dialog):
    """
    File picker dialog
    """
    class Mode:
        """
        Enum class for FileDialog modes.
        """

        OPEN: typing.ClassVar[FileDialog.Mode]
        OPEN_DIR: typing.ClassVar[FileDialog.Mode]
        SAVE: typing.ClassVar[FileDialog.Mode]
        __members__: typing.ClassVar[dict[str, FileDialog.Mode]]
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

    OPEN: typing.ClassVar[FileDialog.Mode]
    OPEN_DIR: typing.ClassVar[FileDialog.Mode]
    SAVE: typing.ClassVar[FileDialog.Mode]
    def __init__(self, arg0: FileDialog.Mode, arg1: str, arg2: Theme) -> None:
        """
        Creates either an open or save file dialog. The first parameter is either FileDialog.OPEN or FileDialog.SAVE. The second is the title of the dialog, and the third is the theme, which is used internally by the dialog for layout. The theme should normally be retrieved from window.theme.
        """
    def add_filter(self, arg0: str, arg1: str) -> None:
        """
        Adds a selectable file-type filter: add_filter('.stl', 'Stereolithography mesh'
        """
    def set_on_cancel(self, arg0: typing.Callable[[], None]) -> None:
        """
        Cancel callback; required
        """
    def set_on_done(self, arg0: typing.Callable[[str], None]) -> None:
        """
        Done callback; required
        """
    def set_path(self, arg0: str) -> None:
        """
        Sets the initial path path of the dialog
        """

class FontDescription:
    """
    Class to describe a custom font
    """

    MONOSPACE: typing.ClassVar[str] = "monospace"
    SANS_SERIF: typing.ClassVar[str] = "sans-serif"
    def __init__(self, typeface: str = "sans-serif", style: FontStyle = ..., point_size: int = 0) -> None:
        """
        Creates a FontDescription. 'typeface' is a path to a TrueType (.ttf), TrueType Collection (.ttc), or OpenType (.otf) file, or it is the name of the font, in which case the system font paths will be searched to find the font file. This typeface will be used for roman characters (Extended Latin, that is, European languages
        """
    def add_typeface_for_code_points(self, arg0: str, arg1: list[int]) -> None:
        """
        Adds specific code points from the typeface. This is useful for selectively adding glyphs, for example, from an icon font.
        """
    def add_typeface_for_language(self, arg0: str, arg1: str) -> None:
        """
        Adds code points outside Extended Latin from the specified typeface. Supported languages are:
           'ja' (Japanese)
           'ko' (Korean)
           'th' (Thai)
           'vi' (Vietnamese)
           'zh' (Chinese, 2500 most common characters, 50 MB per window)
           'zh_all' (Chinese, all characters, ~200 MB per window)
        All other languages will be assumed to be Cyrillic. Note that generally fonts do not have CJK glyphs unless they are specifically a CJK font, although operating systems generally use a CJK font for you. We do not have the information necessary to do this, so you will need to provide a font that has the glyphs you need. In particular, common fonts like 'Arial', 'Helvetica', and SANS_SERIF do not contain CJK glyphs.
        """

class FontStyle:
    """
    Font style

    Members:

      NORMAL

      BOLD

      ITALIC

      BOLD_ITALIC
    """

    BOLD: typing.ClassVar[FontStyle]
    BOLD_ITALIC: typing.ClassVar[FontStyle]
    ITALIC: typing.ClassVar[FontStyle]
    NORMAL: typing.ClassVar[FontStyle]
    __members__: typing.ClassVar[dict[str, FontStyle]]
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

class Horiz(Layout1D):
    """
    Horizontal layout
    """
    @typing.overload
    def __init__(self, spacing: int = 0, margins: Margins = ...) -> None:
        """
        Creates a layout that arranges widgets horizontally, left to right, making their height equal to the layout's height (which will generally be the largest height of the items). First argument is the spacing between widgets, the second is the margins. Both default to 0.
        """
    @typing.overload
    def __init__(self, spacing: float = 0.0, margins: Margins = ...) -> None:
        """
        Creates a layout that arranges widgets horizontally, left to right, making their height equal to the layout's height (which will generally be the largest height of the items). First argument is the spacing between widgets, the second is the margins. Both default to 0.
        """
    @property
    def preferred_height(self) -> int:
        """
        Sets the preferred height of the layout
        """
    @preferred_height.setter
    def preferred_height(self, arg1: int) -> None: ...

class ImageWidget(Widget):
    """
    Displays a bitmap
    """
    @typing.overload
    def __init__(self) -> None:
        """
        Creates an ImageWidget with no image
        """
    @typing.overload
    def __init__(self, arg0: str) -> None:
        """
        Creates an ImageWidget from the image at the specified path
        """
    @typing.overload
    def __init__(self, arg0: open3d.cuda.pybind.geometry.Image) -> None:
        """
        Creates an ImageWidget from the provided image
        """
    @typing.overload
    def __init__(self, arg0: open3d.cuda.pybind.t.geometry.Image) -> None:
        """
        Creates an ImageWidget from the provided tgeometry image
        """
    def __repr__(self) -> str: ...
    def set_on_key(self, arg0: typing.Callable[[KeyEvent], int]) -> None:
        """
        Sets a callback for key events. This callback is passed a KeyEvent object. The callback must return EventCallbackResult.IGNORED, EventCallbackResult.HANDLED, or EventCallackResult.CONSUMED.
        """
    def set_on_mouse(self, arg0: typing.Callable[[MouseEvent], int]) -> None:
        """
        Sets a callback for mouse events. This callback is passed a MouseEvent object. The callback must return EventCallbackResult.IGNORED, EventCallbackResult.HANDLED, or EventCallbackResult.CONSUMED.
        """
    @typing.overload
    def update_image(self, arg0: open3d.cuda.pybind.geometry.Image) -> None:
        """
        Mostly a convenience function for ui_image.update_image(). If 'image' is the same size as the current image, will update the texture with the contents of 'image'. This is the fastest path for setting an image, and is recommended if you are displaying video. If 'image' is a different size, it will allocate a new texture, which is essentially the same as creating a new UIImage and calling SetUIImage(). This is the slow path, and may eventually exhaust internal texture resources.
        """
    @typing.overload
    def update_image(self, arg0: open3d.cuda.pybind.t.geometry.Image) -> None:
        """
        Mostly a convenience function for ui_image.update_image(). If 'image' is the same size as the current image, will update the texture with the contents of 'image'. This is the fastest path for setting an image, and is recommended if you are displaying video. If 'image' is a different size, it will allocate a new texture, which is essentially the same as creating a new UIImage and calling SetUIImage(). This is the slow path, and may eventually exhaust internal texture resources.
        """
    @property
    def ui_image(self) -> UIImage:
        """
        Replaces the texture with a new texture. This is not a fast path, and is not recommended for video as you will exhaust internal texture resources.
        """
    @ui_image.setter
    def ui_image(self, arg1: UIImage) -> None: ...

class KeyEvent:
    """
    Object that stores key events
    """
    class Type:
        """
        Members:

          DOWN

          UP
        """

        DOWN: typing.ClassVar[KeyEvent.Type]
        UP: typing.ClassVar[KeyEvent.Type]
        __members__: typing.ClassVar[dict[str, KeyEvent.Type]]
        def __and__(self, other: typing.Any) -> typing.Any: ...
        def __eq__(self, other: typing.Any) -> bool: ...
        def __ge__(self, other: typing.Any) -> bool: ...
        def __getstate__(self) -> int: ...
        def __gt__(self, other: typing.Any) -> bool: ...
        def __hash__(self) -> int: ...
        def __index__(self) -> int: ...
        def __init__(self, value: int) -> None: ...
        def __int__(self) -> int: ...
        def __invert__(self) -> typing.Any: ...
        def __le__(self, other: typing.Any) -> bool: ...
        def __lt__(self, other: typing.Any) -> bool: ...
        def __ne__(self, other: typing.Any) -> bool: ...
        def __or__(self, other: typing.Any) -> typing.Any: ...
        def __rand__(self, other: typing.Any) -> typing.Any: ...
        def __repr__(self) -> str: ...
        def __ror__(self, other: typing.Any) -> typing.Any: ...
        def __rxor__(self, other: typing.Any) -> typing.Any: ...
        def __setstate__(self, state: int) -> None: ...
        def __str__(self) -> str: ...
        def __xor__(self, other: typing.Any) -> typing.Any: ...
        @property
        def name(self) -> str: ...
        @property
        def value(self) -> int: ...

    DOWN: typing.ClassVar[KeyEvent.Type]
    UP: typing.ClassVar[KeyEvent.Type]
    @property
    def is_repeat(self) -> bool:
        """
        True if this key down event comes from a key repeat
        """
    @is_repeat.setter
    def is_repeat(self, arg0: bool) -> None: ...
    @property
    def key(self) -> int:
        """
        This is the actual key that was pressed, not the character generated by the key. This event is not suitable for text entry
        """
    @key.setter
    def key(self, arg0: int) -> None: ...
    @property
    def type(self) -> KeyEvent.Type:
        """
        Key event type
        """
    @type.setter
    def type(self, arg0: KeyEvent.Type) -> None: ...

class KeyModifier:
    """
    Key modifier identifiers

    Members:

      NONE

      SHIFT

      CTRL

      ALT

      META
    """

    ALT: typing.ClassVar[KeyModifier]
    CTRL: typing.ClassVar[KeyModifier]
    META: typing.ClassVar[KeyModifier]
    NONE: typing.ClassVar[KeyModifier]
    SHIFT: typing.ClassVar[KeyModifier]
    __members__: typing.ClassVar[dict[str, KeyModifier]]
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

class KeyName:
    """
    Names of keys. Used by KeyEvent.key

    Members:

      NONE

      BACKSPACE

      TAB

      ENTER

      ESCAPE

      SPACE

      EXCLAMATION_MARK

      DOUBLE_QUOTE

      HASH

      DOLLAR_SIGN

      PERCENT

      AMPERSAND

      QUOTE

      LEFT_PAREN

      RIGHT_PAREN

      ASTERISK

      PLUS

      COMMA

      MINUS

      PERIOD

      SLASH

      ZERO

      ONE

      TWO

      THREE

      FOUR

      FIVE

      SIX

      SEVEN

      EIGHT

      NINE

      COLON

      SEMICOLON

      LESS_THAN

      EQUALS

      GREATER_THAN

      QUESTION_MARK

      AT

      LEFT_BRACKET

      BACKSLASH

      RIGHT_BRACKET

      CARET

      UNDERSCORE

      BACKTICK

      A

      B

      C

      D

      E

      F

      G

      H

      I

      J

      K

      L

      M

      N

      O

      P

      Q

      R

      S

      T

      U

      V

      W

      X

      Y

      Z

      LEFT_BRACE

      PIPE

      RIGHT_BRACE

      TILDE

      DELETE

      LEFT_SHIFT

      RIGHT_SHIFT

      LEFT_CONTROL

      RIGHT_CONTROL

      ALT

      META

      CAPS_LOCK

      LEFT

      RIGHT

      UP

      DOWN

      INSERT

      HOME

      END

      PAGE_UP

      PAGE_DOWN

      F1

      F2

      F3

      F4

      F5

      F6

      F7

      F8

      F9

      F10

      F11

      F12

      UNKNOWN
    """

    A: typing.ClassVar[KeyName]
    ALT: typing.ClassVar[KeyName]
    AMPERSAND: typing.ClassVar[KeyName]
    ASTERISK: typing.ClassVar[KeyName]
    AT: typing.ClassVar[KeyName]
    B: typing.ClassVar[KeyName]
    BACKSLASH: typing.ClassVar[KeyName]
    BACKSPACE: typing.ClassVar[KeyName]
    BACKTICK: typing.ClassVar[KeyName]
    C: typing.ClassVar[KeyName]
    CAPS_LOCK: typing.ClassVar[KeyName]
    CARET: typing.ClassVar[KeyName]
    COLON: typing.ClassVar[KeyName]
    COMMA: typing.ClassVar[KeyName]
    D: typing.ClassVar[KeyName]
    DELETE: typing.ClassVar[KeyName]
    DOLLAR_SIGN: typing.ClassVar[KeyName]
    DOUBLE_QUOTE: typing.ClassVar[KeyName]
    DOWN: typing.ClassVar[KeyName]
    E: typing.ClassVar[KeyName]
    EIGHT: typing.ClassVar[KeyName]
    END: typing.ClassVar[KeyName]
    ENTER: typing.ClassVar[KeyName]
    EQUALS: typing.ClassVar[KeyName]
    ESCAPE: typing.ClassVar[KeyName]
    EXCLAMATION_MARK: typing.ClassVar[KeyName]
    F: typing.ClassVar[KeyName]
    F1: typing.ClassVar[KeyName]
    F10: typing.ClassVar[KeyName]
    F11: typing.ClassVar[KeyName]
    F12: typing.ClassVar[KeyName]
    F2: typing.ClassVar[KeyName]
    F3: typing.ClassVar[KeyName]
    F4: typing.ClassVar[KeyName]
    F5: typing.ClassVar[KeyName]
    F6: typing.ClassVar[KeyName]
    F7: typing.ClassVar[KeyName]
    F8: typing.ClassVar[KeyName]
    F9: typing.ClassVar[KeyName]
    FIVE: typing.ClassVar[KeyName]
    FOUR: typing.ClassVar[KeyName]
    G: typing.ClassVar[KeyName]
    GREATER_THAN: typing.ClassVar[KeyName]
    H: typing.ClassVar[KeyName]
    HASH: typing.ClassVar[KeyName]
    HOME: typing.ClassVar[KeyName]
    I: typing.ClassVar[KeyName]
    INSERT: typing.ClassVar[KeyName]
    J: typing.ClassVar[KeyName]
    K: typing.ClassVar[KeyName]
    L: typing.ClassVar[KeyName]
    LEFT: typing.ClassVar[KeyName]
    LEFT_BRACE: typing.ClassVar[KeyName]
    LEFT_BRACKET: typing.ClassVar[KeyName]
    LEFT_CONTROL: typing.ClassVar[KeyName]
    LEFT_PAREN: typing.ClassVar[KeyName]
    LEFT_SHIFT: typing.ClassVar[KeyName]
    LESS_THAN: typing.ClassVar[KeyName]
    M: typing.ClassVar[KeyName]
    META: typing.ClassVar[KeyName]
    MINUS: typing.ClassVar[KeyName]
    N: typing.ClassVar[KeyName]
    NINE: typing.ClassVar[KeyName]
    NONE: typing.ClassVar[KeyName]
    O: typing.ClassVar[KeyName]
    ONE: typing.ClassVar[KeyName]
    P: typing.ClassVar[KeyName]
    PAGE_DOWN: typing.ClassVar[KeyName]
    PAGE_UP: typing.ClassVar[KeyName]
    PERCENT: typing.ClassVar[KeyName]
    PERIOD: typing.ClassVar[KeyName]
    PIPE: typing.ClassVar[KeyName]
    PLUS: typing.ClassVar[KeyName]
    Q: typing.ClassVar[KeyName]
    QUESTION_MARK: typing.ClassVar[KeyName]
    QUOTE: typing.ClassVar[KeyName]
    R: typing.ClassVar[KeyName]
    RIGHT: typing.ClassVar[KeyName]
    RIGHT_BRACE: typing.ClassVar[KeyName]
    RIGHT_BRACKET: typing.ClassVar[KeyName]
    RIGHT_CONTROL: typing.ClassVar[KeyName]
    RIGHT_PAREN: typing.ClassVar[KeyName]
    RIGHT_SHIFT: typing.ClassVar[KeyName]
    S: typing.ClassVar[KeyName]
    SEMICOLON: typing.ClassVar[KeyName]
    SEVEN: typing.ClassVar[KeyName]
    SIX: typing.ClassVar[KeyName]
    SLASH: typing.ClassVar[KeyName]
    SPACE: typing.ClassVar[KeyName]
    T: typing.ClassVar[KeyName]
    TAB: typing.ClassVar[KeyName]
    THREE: typing.ClassVar[KeyName]
    TILDE: typing.ClassVar[KeyName]
    TWO: typing.ClassVar[KeyName]
    U: typing.ClassVar[KeyName]
    UNDERSCORE: typing.ClassVar[KeyName]
    UNKNOWN: typing.ClassVar[KeyName]
    UP: typing.ClassVar[KeyName]
    V: typing.ClassVar[KeyName]
    W: typing.ClassVar[KeyName]
    X: typing.ClassVar[KeyName]
    Y: typing.ClassVar[KeyName]
    Z: typing.ClassVar[KeyName]
    ZERO: typing.ClassVar[KeyName]
    __members__: typing.ClassVar[dict[str, KeyName]]
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

class LUTTreeCell(Widget):
    """
    TreeView cell with checkbox, text, and color edit
    """
    def __init__(
        self,
        arg0: str,
        arg1: bool,
        arg2: Color,
        arg3: typing.Callable[[bool], None],
        arg4: typing.Callable[[Color], None],
    ) -> None:
        """
        Creates a TreeView cell with a checkbox, text, and a color editor. LUTTreeCell(text, is_checked, color, on_enabled, on_color): on_enabled is called when the checkbox toggles, and takes a boolean and returns None; on_color is called when the user changes the color and it takes a gui.Color and returns None.
        """
    @property
    def checkbox(self) -> Checkbox:
        """
        Returns the checkbox widget (property is read-only)
        """
    @property
    def color_edit(self) -> ColorEdit:
        """
        Returns the ColorEdit widget (property is read-only)
        """
    @property
    def label(self) -> Label:
        """
        Returns the label widget (property is read-only)
        """

class Label(Widget):
    """
    Displays text
    """
    def __init__(self, arg0: str) -> None:
        """
        Creates a Label with the given text
        """
    def __repr__(self) -> str: ...
    @property
    def font_id(self) -> int:
        """
        Set the font using the FontId returned from Application.add_font()
        """
    @font_id.setter
    def font_id(self, arg1: int) -> None: ...
    @property
    def text(self) -> str:
        """
        The text of the label. Newlines will be treated as line breaks
        """
    @text.setter
    def text(self, arg1: str) -> None: ...
    @property
    def text_color(self) -> Color:
        """
        The color of the text (gui.Color)
        """
    @text_color.setter
    def text_color(self, arg1: Color) -> None: ...

class Label3D:
    """
    Displays text in a 3D scene
    """
    def __init__(self, arg0: str, arg1: numpy.ndarray) -> None:
        """
        Create a 3D Label with given text and position
        """
    @property
    def color(self) -> Color:
        """
        The color of the text (gui.Color)
        """
    @color.setter
    def color(self, arg1: Color) -> None: ...
    @property
    def position(self) -> numpy.ndarray:
        """
        The position of the text in 3D coordinates
        """
    @position.setter
    def position(self, arg1: numpy.ndarray) -> None: ...
    @property
    def scale(self) -> float:
        """
        The scale of the 3D label. When set to 1.0 (the default) text will be rendered at its native font size. Larger and smaller values of scale will enlarge or shrink the rendered text. Note: large values of scale may result in blurry text as the underlying font is not resized.
        """
    @scale.setter
    def scale(self, arg1: float) -> None: ...
    @property
    def text(self) -> str:
        """
        The text to display with this label.
        """
    @text.setter
    def text(self, arg1: str) -> None: ...

class Layout1D(Widget):
    """
    Layout base class
    """
    @typing.overload
    def add_fixed(self, arg0: int) -> None:
        """
        Adds a fixed amount of empty space to the layout
        """
    @typing.overload
    def add_fixed(self, arg0: float) -> None:
        """
        Adds a fixed amount of empty space to the layout
        """
    def add_stretch(self) -> None:
        """
        Adds empty space to the layout that will take up as much extra space as there is available in the layout
        """

class LayoutContext:
    """
    Context passed to Window's on_layout callback
    """
    @property
    def theme(self) -> Theme: ...

class ListView(Widget):
    """
    Displays a list of text
    """
    def __init__(self) -> None:
        """
        Creates an empty list
        """
    def __repr__(self) -> str: ...
    def set_items(self, arg0: list[str]) -> None:
        """
        Sets the list to display the list of items provided
        """
    def set_max_visible_items(self, arg0: int) -> None:
        """
        Limit the max visible items shown to user. Set to negative number will make list extends vertically as much as possible, otherwise the list will at least show 3 items and at most show num items.
        """
    def set_on_selection_changed(self, arg0: typing.Callable[[str, bool], None]) -> None:
        """
        Calls f(new_val, is_double_click) when user changes selection
        """
    @property
    def selected_index(self) -> int:
        """
        The index of the currently selected item
        """
    @selected_index.setter
    def selected_index(self, arg1: int) -> None: ...
    @property
    def selected_value(self) -> str:
        """
        The text of the currently selected item
        """

class Margins:
    """
    Margins for layouts
    """

    bottom: int
    left: int
    right: int
    top: int
    @typing.overload
    def __init__(self, left: int = 0, top: int = 0, right: int = 0, bottom: int = 0) -> None:
        """
        Creates margins. Arguments are left, top, right, bottom. Use the em-size (window.theme.font_size) rather than pixels for more consistency across platforms and monitors. Margins are the spacing from the edge of the widget's frame to its content area. They act similar to the 'padding' property in CSS
        """
    @typing.overload
    def __init__(self, left: float = 0.0, top: float = 0.0, right: float = 0.0, bottom: float = 0.0) -> None:
        """
        Creates margins. Arguments are left, top, right, bottom. Use the em-size (window.theme.font_size) rather than pixels for more consistency across platforms and monitors. Margins are the spacing from the edge of the widget's frame to its content area. They act similar to the 'padding' property in CSS
        """
    def __repr__(self) -> str: ...
    def get_horiz(self) -> int: ...
    def get_vert(self) -> int: ...

class Menu:
    """
    A menu, possibly a menu tree
    """
    def __init__(self) -> None: ...
    def add_item(self, arg0: str, arg1: int) -> None:
        """
        Adds a menu item with id to the menu
        """
    def add_menu(self, arg0: str, arg1: Menu) -> None:
        """
        Adds a submenu to the menu
        """
    def add_separator(self) -> None:
        """
        Adds a separator to the menu
        """
    def is_checked(self, arg0: int) -> bool:
        """
        Returns True if menu item is checked
        """
    def set_checked(self, arg0: int, arg1: bool) -> None:
        """
        Sets menu item (un)checked
        """
    def set_enabled(self, arg0: int, arg1: bool) -> None:
        """
        Sets menu item enabled or disabled
        """

class MouseButton:
    """
    Mouse button identifiers

    Members:

      NONE

      LEFT

      MIDDLE

      RIGHT

      BUTTON4

      BUTTON5
    """

    BUTTON4: typing.ClassVar[MouseButton]
    BUTTON5: typing.ClassVar[MouseButton]
    LEFT: typing.ClassVar[MouseButton]
    MIDDLE: typing.ClassVar[MouseButton]
    NONE: typing.ClassVar[MouseButton]
    RIGHT: typing.ClassVar[MouseButton]
    __members__: typing.ClassVar[dict[str, MouseButton]]
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

class MouseEvent:
    """
    Object that stores mouse events
    """
    class Type:
        """
        Members:

          MOVE

          BUTTON_DOWN

          DRAG

          BUTTON_UP

          WHEEL
        """

        BUTTON_DOWN: typing.ClassVar[MouseEvent.Type]
        BUTTON_UP: typing.ClassVar[MouseEvent.Type]
        DRAG: typing.ClassVar[MouseEvent.Type]
        MOVE: typing.ClassVar[MouseEvent.Type]
        WHEEL: typing.ClassVar[MouseEvent.Type]
        __members__: typing.ClassVar[dict[str, MouseEvent.Type]]
        def __and__(self, other: typing.Any) -> typing.Any: ...
        def __eq__(self, other: typing.Any) -> bool: ...
        def __ge__(self, other: typing.Any) -> bool: ...
        def __getstate__(self) -> int: ...
        def __gt__(self, other: typing.Any) -> bool: ...
        def __hash__(self) -> int: ...
        def __index__(self) -> int: ...
        def __init__(self, value: int) -> None: ...
        def __int__(self) -> int: ...
        def __invert__(self) -> typing.Any: ...
        def __le__(self, other: typing.Any) -> bool: ...
        def __lt__(self, other: typing.Any) -> bool: ...
        def __ne__(self, other: typing.Any) -> bool: ...
        def __or__(self, other: typing.Any) -> typing.Any: ...
        def __rand__(self, other: typing.Any) -> typing.Any: ...
        def __repr__(self) -> str: ...
        def __ror__(self, other: typing.Any) -> typing.Any: ...
        def __rxor__(self, other: typing.Any) -> typing.Any: ...
        def __setstate__(self, state: int) -> None: ...
        def __str__(self) -> str: ...
        def __xor__(self, other: typing.Any) -> typing.Any: ...
        @property
        def name(self) -> str: ...
        @property
        def value(self) -> int: ...

    BUTTON_DOWN: typing.ClassVar[MouseEvent.Type]
    BUTTON_UP: typing.ClassVar[MouseEvent.Type]
    DRAG: typing.ClassVar[MouseEvent.Type]
    MOVE: typing.ClassVar[MouseEvent.Type]
    WHEEL: typing.ClassVar[MouseEvent.Type]
    def is_button_down(self, arg0: MouseButton) -> bool:
        """
        Convenience function to more easily deterimine if a mouse button is pressed
        """
    def is_modifier_down(self, arg0: KeyModifier) -> bool:
        """
        Convenience function to more easily deterimine if a modifier key is down
        """
    @property
    def buttons(self) -> int:
        """
        ORed mouse buttons
        """
    @buttons.setter
    def buttons(self, arg1: int) -> None: ...
    @property
    def modifiers(self) -> int:
        """
        ORed mouse modifiers
        """
    @modifiers.setter
    def modifiers(self, arg0: int) -> None: ...
    @property
    def type(self) -> MouseEvent.Type:
        """
        Mouse event type
        """
    @type.setter
    def type(self, arg0: MouseEvent.Type) -> None: ...
    @property
    def wheel_dx(self) -> int:
        """
        Mouse wheel horizontal motion
        """
    @wheel_dx.setter
    def wheel_dx(self, arg1: int) -> None: ...
    @property
    def wheel_dy(self) -> int:
        """
        Mouse wheel vertical motion
        """
    @wheel_dy.setter
    def wheel_dy(self, arg1: int) -> None: ...
    @property
    def wheel_is_trackpad(self) -> bool:
        """
        Is mouse wheel event from a trackpad
        """
    @wheel_is_trackpad.setter
    def wheel_is_trackpad(self, arg1: bool) -> None: ...
    @property
    def x(self) -> int:
        """
        x coordinate  of the mouse event
        """
    @x.setter
    def x(self, arg0: int) -> None: ...
    @property
    def y(self) -> int:
        """
        y coordinate of the mouse event
        """
    @y.setter
    def y(self, arg0: int) -> None: ...

class NumberEdit(Widget):
    """
    Allows the user to enter a number.
    """
    class Type:
        """
        Enum class for NumberEdit types.
        """

        DOUBLE: typing.ClassVar[NumberEdit.Type]
        INT: typing.ClassVar[NumberEdit.Type]
        __members__: typing.ClassVar[dict[str, NumberEdit.Type]]
        def __and__(self, other: typing.Any) -> typing.Any: ...
        def __eq__(self, other: typing.Any) -> bool: ...
        def __ge__(self, other: typing.Any) -> bool: ...
        def __getstate__(self) -> int: ...
        def __gt__(self, other: typing.Any) -> bool: ...
        def __hash__(self) -> int: ...
        def __index__(self) -> int: ...
        def __init__(self, value: int) -> None: ...
        def __int__(self) -> int: ...
        def __invert__(self) -> typing.Any: ...
        def __le__(self, other: typing.Any) -> bool: ...
        def __lt__(self, other: typing.Any) -> bool: ...
        def __ne__(self, other: typing.Any) -> bool: ...
        def __or__(self, other: typing.Any) -> typing.Any: ...
        def __rand__(self, other: typing.Any) -> typing.Any: ...
        def __repr__(self) -> str: ...
        def __ror__(self, other: typing.Any) -> typing.Any: ...
        def __rxor__(self, other: typing.Any) -> typing.Any: ...
        def __setstate__(self, state: int) -> None: ...
        def __str__(self) -> str: ...
        def __xor__(self, other: typing.Any) -> typing.Any: ...
        @property
        def name(self) -> str: ...
        @property
        def value(self) -> int: ...

    DOUBLE: typing.ClassVar[NumberEdit.Type]
    INT: typing.ClassVar[NumberEdit.Type]
    def __init__(self, arg0: NumberEdit.Type) -> None:
        """
        Creates a NumberEdit that is either integers (INT) or floating point (DOUBLE). The initial value is 0 and the limits are +/- max integer (roughly).
        """
    def __repr__(self) -> str: ...
    def set_limits(self, arg0: float, arg1: float) -> None:
        """
        Sets the minimum and maximum values for the number
        """
    def set_on_value_changed(self, arg0: typing.Callable[[float], None]) -> None:
        """
        Sets f(new_value) which is called with a Float when user changes widget's value
        """
    @typing.overload
    def set_preferred_width(self, arg0: int) -> None:
        """
        Sets the preferred width of the NumberEdit
        """
    @typing.overload
    def set_preferred_width(self, arg0: float) -> None:
        """
        Sets the preferred width of the NumberEdit
        """
    def set_value(self, arg0: float) -> None:
        """
        Sets value
        """
    @property
    def decimal_precision(self) -> int:
        """
        Number of fractional digits shown
        """
    @decimal_precision.setter
    def decimal_precision(self, arg1: int) -> None: ...
    @property
    def double_value(self) -> float:
        """
        Current value (double)
        """
    @double_value.setter
    def double_value(self, arg1: float) -> None: ...
    @property
    def int_value(self) -> int:
        """
        Current value (int)
        """
    @int_value.setter
    def int_value(self, arg1: int) -> None: ...
    @property
    def maximum_value(self) -> float:
        """
        The maximum value number can contain (read-only, use set_limits() to set)
        """
    @property
    def minimum_value(self) -> float:
        """
        The minimum value number can contain (read-only, use set_limits() to set)
        """

class ProgressBar(Widget):
    """
    Displays a progress bar
    """
    def __init__(self) -> None: ...
    def __repr__(self) -> str: ...
    @property
    def value(self) -> float:
        """
        The value of the progress bar, ranges from 0.0 to 1.0
        """
    @value.setter
    def value(self, arg1: float) -> None: ...

class RadioButton(Widget):
    """
    Exclusive selection from radio button list
    """
    class Type:
        """
        Enum class for RadioButton types.
        """

        HORIZ: typing.ClassVar[RadioButton.Type]
        VERT: typing.ClassVar[RadioButton.Type]
        __members__: typing.ClassVar[dict[str, RadioButton.Type]]
        def __and__(self, other: typing.Any) -> typing.Any: ...
        def __eq__(self, other: typing.Any) -> bool: ...
        def __ge__(self, other: typing.Any) -> bool: ...
        def __getstate__(self) -> int: ...
        def __gt__(self, other: typing.Any) -> bool: ...
        def __hash__(self) -> int: ...
        def __index__(self) -> int: ...
        def __init__(self, value: int) -> None: ...
        def __int__(self) -> int: ...
        def __invert__(self) -> typing.Any: ...
        def __le__(self, other: typing.Any) -> bool: ...
        def __lt__(self, other: typing.Any) -> bool: ...
        def __ne__(self, other: typing.Any) -> bool: ...
        def __or__(self, other: typing.Any) -> typing.Any: ...
        def __rand__(self, other: typing.Any) -> typing.Any: ...
        def __repr__(self) -> str: ...
        def __ror__(self, other: typing.Any) -> typing.Any: ...
        def __rxor__(self, other: typing.Any) -> typing.Any: ...
        def __setstate__(self, state: int) -> None: ...
        def __str__(self) -> str: ...
        def __xor__(self, other: typing.Any) -> typing.Any: ...
        @property
        def name(self) -> str: ...
        @property
        def value(self) -> int: ...

    HORIZ: typing.ClassVar[RadioButton.Type]
    VERT: typing.ClassVar[RadioButton.Type]
    def __init__(self, arg0: RadioButton.Type) -> None:
        """
        Creates an empty radio buttons. Use set_items() to add items
        """
    def set_items(self, arg0: list[str]) -> None:
        """
        Set radio items, each item is a radio button.
        """
    def set_on_selection_changed(self, arg0: typing.Callable[[int], None]) -> None:
        """
        Calls f(new_idx) when user changes selection
        """
    @property
    def selected_index(self) -> int:
        """
        The index of the currently selected item
        """
    @selected_index.setter
    def selected_index(self, arg1: int) -> None: ...
    @property
    def selected_value(self) -> str:
        """
        The text of the currently selected item
        """

class Rect:
    """
    Represents a widget frame
    """

    height: int
    width: int
    x: int
    y: int
    @typing.overload
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(self, arg0: int, arg1: int, arg2: int, arg3: int) -> None: ...
    @typing.overload
    def __init__(self, arg0: float, arg1: float, arg2: float, arg3: float) -> None: ...
    def __repr__(self) -> str: ...
    def get_bottom(self) -> int: ...
    def get_left(self) -> int: ...
    def get_right(self) -> int: ...
    def get_top(self) -> int: ...

class SceneWidget(Widget):
    """
    Displays 3D content
    """
    class Controls:
        """
        Enum class describing mouse interaction.
        """

        FLY: typing.ClassVar[SceneWidget.Controls]
        PICK_POINTS: typing.ClassVar[SceneWidget.Controls]
        ROTATE_CAMERA: typing.ClassVar[SceneWidget.Controls]
        ROTATE_CAMERA_SPHERE: typing.ClassVar[SceneWidget.Controls]
        ROTATE_IBL: typing.ClassVar[SceneWidget.Controls]
        ROTATE_MODEL: typing.ClassVar[SceneWidget.Controls]
        ROTATE_SUN: typing.ClassVar[SceneWidget.Controls]
        __members__: typing.ClassVar[dict[str, SceneWidget.Controls]]
        def __and__(self, other: typing.Any) -> typing.Any: ...
        def __eq__(self, other: typing.Any) -> bool: ...
        def __ge__(self, other: typing.Any) -> bool: ...
        def __getstate__(self) -> int: ...
        def __gt__(self, other: typing.Any) -> bool: ...
        def __hash__(self) -> int: ...
        def __index__(self) -> int: ...
        def __init__(self, value: int) -> None: ...
        def __int__(self) -> int: ...
        def __invert__(self) -> typing.Any: ...
        def __le__(self, other: typing.Any) -> bool: ...
        def __lt__(self, other: typing.Any) -> bool: ...
        def __ne__(self, other: typing.Any) -> bool: ...
        def __or__(self, other: typing.Any) -> typing.Any: ...
        def __rand__(self, other: typing.Any) -> typing.Any: ...
        def __repr__(self) -> str: ...
        def __ror__(self, other: typing.Any) -> typing.Any: ...
        def __rxor__(self, other: typing.Any) -> typing.Any: ...
        def __setstate__(self, state: int) -> None: ...
        def __str__(self) -> str: ...
        def __xor__(self, other: typing.Any) -> typing.Any: ...
        @property
        def name(self) -> str: ...
        @property
        def value(self) -> int: ...

    FLY: typing.ClassVar[SceneWidget.Controls]
    PICK_POINTS: typing.ClassVar[SceneWidget.Controls]
    ROTATE_CAMERA: typing.ClassVar[SceneWidget.Controls]
    ROTATE_CAMERA_SPHERE: typing.ClassVar[SceneWidget.Controls]
    ROTATE_IBL: typing.ClassVar[SceneWidget.Controls]
    ROTATE_MODEL: typing.ClassVar[SceneWidget.Controls]
    ROTATE_SUN: typing.ClassVar[SceneWidget.Controls]
    def __init__(self) -> None:
        """
        Creates an empty SceneWidget. Assign a Scene with the 'scene' property
        """
    def add_3d_label(self, arg0: numpy.ndarray, arg1: str) -> Label3D:
        """
        Add a 3D text label to the scene. The label will be anchored at the specified 3D point.
        """
    def enable_scene_caching(self, arg0: bool) -> None:
        """
        Enable/Disable caching of scene content when the view or model is not changing. Scene caching can help improve UI responsiveness for large models and point clouds
        """
    def force_redraw(self) -> None:
        """
        Ensures scene redraws even when scene caching is enabled.
        """
    def look_at(self, arg0: numpy.ndarray, arg1: numpy.ndarray, arg2: numpy.ndarray) -> None:
        """
        look_at(center, eye, up): sets the camera view so that the camera is located at 'eye', pointing towards 'center', and oriented so that the up vector is 'up'
        """
    def remove_3d_label(self, arg0: Label3D) -> None:
        """
        Removes the 3D text label from the scene
        """
    def set_on_key(self, arg0: typing.Callable[[KeyEvent], int]) -> None:
        """
        Sets a callback for key events. This callback is passed a KeyEvent object. The callback must return EventCallbackResult.IGNORED, EventCallbackResult.HANDLED, or EventCallbackResult.CONSUMED.
        """
    def set_on_mouse(self, arg0: typing.Callable[[MouseEvent], int]) -> None:
        """
        Sets a callback for mouse events. This callback is passed a MouseEvent object. The callback must return EventCallbackResult.IGNORED, EventCallbackResult.HANDLED, or EventCallbackResult.CONSUMED.
        """
    def set_on_sun_direction_changed(self, arg0: typing.Callable[[numpy.ndarray], None]) -> None:
        """
        Callback when user changes sun direction (only called in ROTATE_SUN control mode). Called with one argument, the [i, j, k] vector of the new sun direction
        """
    def set_view_controls(self, arg0: SceneWidget.Controls) -> None:
        """
        Sets mouse interaction, e.g. ROTATE_OBJ
        """
    @typing.overload
    def setup_camera(
        self, arg0: float, arg1: open3d.cuda.pybind.geometry.AxisAlignedBoundingBox, arg2: numpy.ndarray
    ) -> None:
        """
        Configure the camera: setup_camera(field_of_view, model_bounds, center_of_rotation)
        """
    @typing.overload
    def setup_camera(
        self,
        arg0: open3d.cuda.pybind.camera.PinholeCameraIntrinsic,
        arg1: numpy.ndarray,
        arg2: open3d.cuda.pybind.geometry.AxisAlignedBoundingBox,
    ) -> None:
        """
        setup_camera(intrinsics, extrinsic_matrix, model_bounds): sets the camera view
        """
    @typing.overload
    def setup_camera(
        self,
        arg0: numpy.ndarray,
        arg1: numpy.ndarray,
        arg2: int,
        arg3: int,
        arg4: open3d.cuda.pybind.geometry.AxisAlignedBoundingBox,
    ) -> None:
        """
        setup_camera(intrinsic_matrix, extrinsic_matrix, intrinsic_width_px, intrinsic_height_px, model_bounds): sets the camera view
        """
    @property
    def center_of_rotation(self) -> numpy.ndarray:
        """
        Current center of rotation (for ROTATE_CAMERA and ROTATE_CAMERA_SPHERE)
        """
    @center_of_rotation.setter
    def center_of_rotation(self, arg1: numpy.ndarray) -> None: ...
    @property
    def scene(self) -> open3d.cuda.pybind.visualization.rendering.Open3DScene:
        """
        The rendering.Open3DScene that the SceneWidget renders
        """
    @scene.setter
    def scene(self, arg1: open3d.cuda.pybind.visualization.rendering.Open3DScene) -> None: ...

class ScrollableVert(Vert):
    """
    Scrollable vertical layout
    """
    @typing.overload
    def __init__(self, spacing: int = 0, margins: Margins = ...) -> None:
        """
        Creates a layout that arranges widgets vertically, top to bottom, making their width equal to the layout's width. First argument is the spacing between widgets, the second is the margins. Both default to 0.
        """
    @typing.overload
    def __init__(self, spacing: float = 0.0, margins: Margins = ...) -> None:
        """
        Creates a layout that arranges widgets vertically, top to bottom, making their width equal to the layout's width. First argument is the spacing between widgets, the second is the margins. Both default to 0.
        """

class Size:
    """
    Size object
    """

    height: int
    width: int
    @typing.overload
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(self, arg0: int, arg1: int) -> None: ...
    @typing.overload
    def __init__(self, arg0: float, arg1: float) -> None: ...
    def __repr__(self) -> str: ...

class Slider(Widget):
    """
    A slider widget for visually selecting numbers
    """
    class Type:
        """
        Enum class for Slider types.
        """

        DOUBLE: typing.ClassVar[Slider.Type]
        INT: typing.ClassVar[Slider.Type]
        __members__: typing.ClassVar[dict[str, Slider.Type]]
        def __and__(self, other: typing.Any) -> typing.Any: ...
        def __eq__(self, other: typing.Any) -> bool: ...
        def __ge__(self, other: typing.Any) -> bool: ...
        def __getstate__(self) -> int: ...
        def __gt__(self, other: typing.Any) -> bool: ...
        def __hash__(self) -> int: ...
        def __index__(self) -> int: ...
        def __init__(self, value: int) -> None: ...
        def __int__(self) -> int: ...
        def __invert__(self) -> typing.Any: ...
        def __le__(self, other: typing.Any) -> bool: ...
        def __lt__(self, other: typing.Any) -> bool: ...
        def __ne__(self, other: typing.Any) -> bool: ...
        def __or__(self, other: typing.Any) -> typing.Any: ...
        def __rand__(self, other: typing.Any) -> typing.Any: ...
        def __repr__(self) -> str: ...
        def __ror__(self, other: typing.Any) -> typing.Any: ...
        def __rxor__(self, other: typing.Any) -> typing.Any: ...
        def __setstate__(self, state: int) -> None: ...
        def __str__(self) -> str: ...
        def __xor__(self, other: typing.Any) -> typing.Any: ...
        @property
        def name(self) -> str: ...
        @property
        def value(self) -> int: ...

    DOUBLE: typing.ClassVar[Slider.Type]
    INT: typing.ClassVar[Slider.Type]
    def __init__(self, arg0: Slider.Type) -> None:
        """
        Creates a NumberEdit that is either integers (INT) or floating point (DOUBLE). The initial value is 0 and the limits are +/- infinity.
        """
    def __repr__(self) -> str: ...
    def set_limits(self, arg0: float, arg1: float) -> None:
        """
        Sets the minimum and maximum values for the slider
        """
    def set_on_value_changed(self, arg0: typing.Callable[[float], None]) -> None:
        """
        Sets f(new_value) which is called with a Float when user changes widget's value
        """
    @property
    def double_value(self) -> float:
        """
        Slider value (double)
        """
    @double_value.setter
    def double_value(self, arg1: float) -> None: ...
    @property
    def get_maximum_value(self) -> float:
        """
        The maximum value number can contain (read-only, use set_limits() to set)
        """
    @property
    def get_minimum_value(self) -> float:
        """
        The minimum value number can contain (read-only, use set_limits() to set)
        """
    @property
    def int_value(self) -> int:
        """
        Slider value (int)
        """
    @int_value.setter
    def int_value(self, arg1: int) -> None: ...

class StackedWidget(Widget):
    """
    Like a TabControl but without the tabs
    """
    def __init__(self) -> None: ...
    @property
    def selected_index(self) -> int:
        """
        Selects the index of the child to display
        """
    @selected_index.setter
    def selected_index(self, arg1: int) -> None: ...

class TabControl(Widget):
    """
    Tab control
    """
    def __init__(self) -> None: ...
    def add_tab(self, arg0: str, arg1: Widget) -> None:
        """
        Adds a tab. The first parameter is the title of the tab, and the second parameter is a widget--normally this is a layout.
        """
    def set_on_selected_tab_changed(self, arg0: typing.Callable[[int], None]) -> None:
        """
        Calls the provided callback function with the index of the currently selected tab whenever the user clicks on a different tab
        """
    @property
    def selected_tab_index(self) -> int:
        """
        The index of the currently selected item
        """
    @selected_tab_index.setter
    def selected_tab_index(self, arg1: int) -> None: ...

class TextEdit(Widget):
    """
    Allows the user to enter or modify text
    """
    def __init__(self) -> None:
        """
        Creates a TextEdit widget with an initial value of an empty string.
        """
    def __repr__(self) -> str: ...
    def set_on_text_changed(self, arg0: typing.Callable[[str], None]) -> None:
        """
        Sets f(new_text) which is called whenever the the user makes a change to the text
        """
    def set_on_value_changed(self, arg0: typing.Callable[[str], None]) -> None:
        """
        Sets f(new_text) which is called with the new text when the user completes text editing
        """
    @property
    def placeholder_text(self) -> str:
        """
        The placeholder text displayed when text value is empty
        """
    @placeholder_text.setter
    def placeholder_text(self, arg1: str) -> None: ...
    @property
    def text_value(self) -> str:
        """
        The value of text
        """
    @text_value.setter
    def text_value(self, arg1: str) -> None: ...

class Theme:
    """
    Theme parameters such as colors used for drawing widgets (read-only)
    """
    @property
    def default_layout_spacing(self) -> int:
        """
        Good value for the spacing parameter in layouts (read-only)
        """
    @property
    def default_margin(self) -> int:
        """
        Good default value for margins, useful for layouts (read-only)
        """
    @property
    def font_size(self) -> int:
        """
        Font size (which is also the conventional size of the em unit) (read-only)
        """

class ToggleSwitch(Widget):
    """
    ToggleSwitch
    """
    def __init__(self, arg0: str) -> None:
        """
        Creates a toggle switch with the given text
        """
    def __repr__(self) -> str: ...
    def set_on_clicked(self, arg0: typing.Callable[[bool], None]) -> None:
        """
        Sets f(is_on) which is called when the switch changes state.
        """
    @property
    def is_on(self) -> bool:
        """
        True if is one, False otherwise
        """
    @is_on.setter
    def is_on(self, arg1: bool) -> None: ...

class TreeView(Widget):
    """
    Hierarchical list
    """
    def __init__(self) -> None:
        """
        Creates an empty TreeView widget
        """
    def __repr__(self) -> str: ...
    def add_item(self, arg0: int, arg1: Widget) -> int:
        """
        Adds a child item to the parent. add_item(parent, widget)
        """
    def add_text_item(self, arg0: int, arg1: str) -> int:
        """
        Adds a child item to the parent. add_text_item(parent, text)
        """
    def clear(self) -> None:
        """
        Removes all items
        """
    def get_item(self, item_id: int) -> Widget:
        """
        Returns the widget associated with the provided Item ID. For example, to manipulate the widget of the currently selected item you would use the ItemID of the selected_item property with get_item to get the widget.
        """
    def get_root_item(self) -> int:
        """
        Returns the root item. This item is invisible, so its child are the top-level items
        """
    def remove_item(self, arg0: int) -> None:
        """
        Removes an item and all its children (if any)
        """
    def set_on_selection_changed(self, arg0: typing.Callable[[int], None]) -> None:
        """
        Sets f(new_item_id) which is called when the user changes the selection.
        """
    @property
    def can_select_items_with_children(self) -> bool:
        """
        If set to False, clicking anywhere on an item with will toggle the item open or closed; the item cannot be selected. If set to True, items with children can be selected, and to toggle open/closed requires clicking the arrow or double-clicking the item
        """
    @can_select_items_with_children.setter
    def can_select_items_with_children(self, arg1: bool) -> None: ...
    @property
    def selected_item(self) -> int:
        """
        The currently selected item
        """
    @selected_item.setter
    def selected_item(self, arg1: int) -> None: ...

class UIImage:
    """
    A bitmap suitable for displaying with ImageWidget
    """
    class Scaling:
        """
        Members:

          NONE

          ANY

          ASPECT
        """

        ANY: typing.ClassVar[UIImage.Scaling]
        ASPECT: typing.ClassVar[UIImage.Scaling]
        NONE: typing.ClassVar[UIImage.Scaling]
        __members__: typing.ClassVar[dict[str, UIImage.Scaling]]
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

    @typing.overload
    def __init__(self, arg0: str) -> None:
        """
        Creates a UIImage from the image at the specified path
        """
    @typing.overload
    def __init__(self, arg0: open3d.cuda.pybind.geometry.Image) -> None:
        """
        Creates a UIImage from the provided image
        """
    def __repr__(self) -> str: ...
    @property
    def scaling(self) -> UIImage.Scaling:
        """
        Sets how the image is scaled:
        gui.UIImage.Scaling.NONE: no scaling
        gui.UIImage.Scaling.ANY: scaled to fit
        gui.UIImage.Scaling.ASPECT: scaled to fit but keeping the image's aspect ratio
        """
    @scaling.setter
    def scaling(self, arg1: UIImage.Scaling) -> None: ...

class VGrid(Widget):
    """
    Grid layout
    """
    @typing.overload
    def __init__(self, cols: int, spacing: int = 0, margins: Margins = ...) -> None:
        """
        Creates a layout that orders its children in a grid, left to right, top to bottom, according to the number of columns. The first argument is the number of columns, the second is the spacing between items (both vertically and horizontally), and third is the margins. Both spacing and margins default to zero.
        """
    @typing.overload
    def __init__(self, cols: int, spacing: float = 0.0, margins: Margins = ...) -> None:
        """
        Creates a layout that orders its children in a grid, left to right, top to bottom, according to the number of columns. The first argument is the number of columns, the second is the spacing between items (both vertically and horizontally), and third is the margins. Both spacing and margins default to zero.
        """
    @property
    def margins(self) -> Margins:
        """
        Returns the margins
        """
    @property
    def preferred_width(self) -> int:
        """
        Sets the preferred width of the layout
        """
    @preferred_width.setter
    def preferred_width(self, arg1: int) -> None: ...
    @property
    def spacing(self) -> int:
        """
        Returns the spacing between rows and columns
        """

class VectorEdit(Widget):
    """
    Allows the user to edit a 3-space vector
    """
    def __init__(self) -> None: ...
    def __repr__(self) -> str: ...
    def set_on_value_changed(self, arg0: typing.Callable[[numpy.ndarray], None]) -> None:
        """
        Sets f([x, y, z]) which is called whenever the user changes the value of a component
        """
    @property
    def vector_value(self) -> numpy.ndarray:
        """
        Returns value [x, y, z]
        """
    @vector_value.setter
    def vector_value(self, arg1: numpy.ndarray) -> None: ...

class Vert(Layout1D):
    """
    Vertical layout
    """
    @typing.overload
    def __init__(self, spacing: int = 0, margins: Margins = ...) -> None:
        """
        Creates a layout that arranges widgets vertically, top to bottom, making their width equal to the layout's width. First argument is the spacing between widgets, the second is the margins. Both default to 0.
        """
    @typing.overload
    def __init__(self, spacing: float = 0.0, margins: Margins = ...) -> None:
        """
        Creates a layout that arranges widgets vertically, top to bottom, making their width equal to the layout's width. First argument is the spacing between widgets, the second is the margins. Both default to 0.
        """
    @property
    def preferred_width(self) -> int:
        """
        Sets the preferred width of the layout
        """
    @preferred_width.setter
    def preferred_width(self, arg1: int) -> None: ...

class Widget:
    """
    Base widget class
    """
    class Constraints:
        """
        Constraints object for Widget.calc_preferred_size()
        """

        height: int
        width: int
        def __init__(self) -> None: ...

    class EventCallbackResult:
        """
        Returned by event handlers

        Members:

          IGNORED : Event handler ignored the event, widget will handle event normally

          HANDLED : Event handler handled the event, but widget will still handle the event normally. This is useful when you are augmenting base functionality

          CONSUMED : Event handler consumed the event, event handling stops, widget will not handle the event. This is useful when you are replacing functionality
        """

        CONSUMED: typing.ClassVar[Widget.EventCallbackResult]
        HANDLED: typing.ClassVar[Widget.EventCallbackResult]
        IGNORED: typing.ClassVar[Widget.EventCallbackResult]
        __members__: typing.ClassVar[dict[str, Widget.EventCallbackResult]]
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

    CONSUMED: typing.ClassVar[Widget.EventCallbackResult]
    HANDLED: typing.ClassVar[Widget.EventCallbackResult]
    IGNORED: typing.ClassVar[Widget.EventCallbackResult]
    def __init__(self) -> None: ...
    def __repr__(self) -> str: ...
    def add_child(self, arg0: Widget) -> None:
        """
        Adds a child widget
        """
    def calc_preferred_size(self, arg0: LayoutContext, arg1: Widget.Constraints) -> Size:
        """
        Returns the preferred size of the widget. This is intended to be called only during layout, although it will also work during drawing. Calling it at other times will not work, as it requires some internal setup in order to function properly
        """
    def get_children(self) -> list[Widget]:
        """
        Returns the array of children. Do not modify.
        """
    @property
    def background_color(self) -> Color:
        """
        Background color of the widget
        """
    @background_color.setter
    def background_color(self, arg1: Color) -> None: ...
    @property
    def enabled(self) -> bool:
        """
        True if widget is enabled, False if disabled
        """
    @enabled.setter
    def enabled(self, arg1: bool) -> None: ...
    @property
    def frame(self) -> Rect:
        """
        The widget's frame. Setting this value will be overridden if the frame is within a layout.
        """
    @frame.setter
    def frame(self, arg1: Rect) -> None: ...
    @property
    def tooltip(self) -> str:
        """
        Widget's tooltip that is displayed on mouseover
        """
    @tooltip.setter
    def tooltip(self, arg1: str) -> None: ...
    @property
    def visible(self) -> bool:
        """
        True if widget is visible, False otherwise
        """
    @visible.setter
    def visible(self, arg1: bool) -> None: ...

class WidgetProxy(Widget):
    """
    Widget container to delegate any widget dynamically. Widget can not be managed dynamically. Although it is allowed to add more child widgets, it's impossible to replace some child with new on or remove children. WidgetProxy is designed to solve this problem. When WidgetProxy is created, it's invisible and disabled, so it won't be drawn or layout, seeming like it does not exist. When a widget is set by  set_widget, all  Widget's APIs will be conducted to that child widget. It looks like WidgetProxy is that widget. At any time, a new widget could be set, to replace the old one. and the old widget will be destroyed. Due to the content changing after a new widget is set or cleared, a relayout of Window might be called after set_widget. The delegated widget could be retrieved by  get_widget in case  you need to access it directly, like get check status of a CheckBox. API other than  set_widget and get_widget has completely same functions as Widget.
    """
    def __init__(self) -> None:
        """
        Creates a widget proxy
        """
    def __repr__(self) -> str: ...
    def get_widget(self) -> Widget:
        """
        Retrieve current delegated widget.return instance of current delegated widget set by set_widget. An empty pointer will be returned if there is none.
        """
    def set_widget(self, arg0: Widget) -> None:
        """
        set a new widget to be delegated by this one. After set_widget, the previously delegated widget , will be abandon all calls to Widget's API will be  conducted to widget. Before any set_widget call,  this widget is invisible and disabled, seems it  does not exist because it won't be drawn or in a layout.
        """

class WidgetStack(WidgetProxy):
    """
    A widget stack saves all widgets pushed into by push_widget and always shows the top one. The WidgetStack is a subclass of WidgetProxy, in otherwords, the topmost widget will delegate itself to WidgetStack. pop_widget will remove the topmost widget and callback set by set_on_top taking the new topmost widget will be called. The WidgetStack disappears in GUI if there is no widget in stack.
    """
    def __init__(self) -> None:
        """
        Creates a widget stack. The widget stack without anywidget will not be shown in GUI until set_widget iscalled to push a widget.
        """
    def __repr__(self) -> str: ...
    def pop_widget(self) -> Widget:
        """
        pop the topmost widget in the stack. The new topmost widgetof stack will be the widget on the show in GUI.
        """
    def push_widget(self, arg0: Widget) -> None:
        """
        push a new widget onto the WidgetStack's stack, hiding whatever widget was there before and making the new widget visible.
        """
    def set_on_top(self, arg0: typing.Callable[[Widget], None]) -> None:
        """
        Callable[[widget] -> None], called while a widget becomes the topmost of stack after some widget is poppedout. It won't be called if a widget is pushed into stackby set_widget.
        """

class Window(WindowBase):
    """
    Application window. Create with Application.instance.create_window().
    """
    def __repr__(self) -> str: ...
    def add_child(self, arg0: Widget) -> None:
        """
        Adds a widget to the window
        """
    def close(self) -> None:
        """
        Closes the window and destroys it, unless an on_close callback cancels the close.
        """
    def close_dialog(self) -> None:
        """
        Closes the current dialog
        """
    def post_redraw(self) -> None:
        """
        Sends a redraw message to the OS message queue
        """
    def set_focus_widget(self, arg0: Widget) -> None:
        """
        Makes specified widget have text focus
        """
    def set_needs_layout(self) -> None:
        """
        Flags window to re-layout
        """
    def set_on_close(self, arg0: typing.Callable[[], bool]) -> None:
        """
        Sets a callback that will be called when the window is closed. The callback is given no arguments and should return True to continue closing the window or False to cancel the close
        """
    def set_on_key(self, arg0: typing.Callable[[KeyEvent], bool]) -> None:
        """
        Sets a callback for key events. This callback is passed a KeyEvent object. The callback must return True to stop more dispatching or False to dispatchto focused widget
        """
    def set_on_layout(self, arg0: typing.Callable[[LayoutContext], None]) -> None:
        """
        Sets a callback function that manually sets the frames of children of the window. Callback function will be called with one argument: gui.LayoutContext
        """
    def set_on_menu_item_activated(self, arg0: int, arg1: typing.Callable[[], None]) -> None:
        """
        Sets callback function for menu item:  callback()
        """
    def set_on_tick_event(self, arg0: typing.Callable[[], bool]) -> None:
        """
        Sets callback for tick event. Callback takes no arguments and must return True if a redraw is needed (that is, if any widget has changed in any fashion) or False if nothing has changed
        """
    def show(self, arg0: bool) -> None:
        """
        Shows or hides the window
        """
    def show_dialog(self, arg0: Dialog) -> None:
        """
        Displays the dialog
        """
    def show_menu(self, arg0: bool) -> None:
        """
        show_menu(show): shows or hides the menu in the window, except on macOS since the menubar is not in the window and all applications must have a menubar.
        """
    def show_message_box(self, arg0: str, arg1: str) -> None:
        """
        Displays a simple dialog with a title and message and okay button
        """
    def size_to_fit(self) -> None:
        """
        Sets the width and height of window to its preferred size
        """
    @property
    def content_rect(self) -> Rect:
        """
        Returns the frame in device pixels, relative  to the window, which is available for widgets (read-only)
        """
    @property
    def is_active_window(self) -> bool:
        """
        True if the window is currently the active window (read-only)
        """
    @property
    def is_visible(self) -> bool:
        """
        True if window is visible (read-only)
        """
    @property
    def os_frame(self) -> Rect:
        """
        Window rect in OS coords, not device pixels
        """
    @os_frame.setter
    def os_frame(self, arg1: Rect) -> None: ...
    @property
    def renderer(self) -> open3d.cuda.pybind.visualization.rendering.Renderer:
        """
        Gets the rendering.Renderer object for the Window
        """
    @property
    def scaling(self) -> float:
        """
        Returns the scaling factor between OS pixels and device pixels (read-only)
        """
    @property
    def size(self) -> Size:
        """
        The size of the window in device pixels, including menubar (except on macOS)
        """
    @size.setter
    def size(self, arg1: Size) -> None: ...
    @property
    def theme(self) -> Theme:
        """
        Get's window's theme info
        """
    @property
    def title(self) -> str:
        """
        Returns the title of the window
        """
    @title.setter
    def title(self, arg1: str) -> None: ...

class WindowBase:
    """
    Application window
    """

A: KeyName
ALT: KeyName
AMPERSAND: KeyName
ASTERISK: KeyName
AT: KeyName
B: KeyName
BACKSLASH: KeyName
BACKSPACE: KeyName
BACKTICK: KeyName
BUTTON4: MouseButton
BUTTON5: MouseButton
C: KeyName
CAPS_LOCK: KeyName
CARET: KeyName
COLON: KeyName
COMMA: KeyName
CTRL: KeyModifier
D: KeyName
DELETE: KeyName
DOLLAR_SIGN: KeyName
DOUBLE_QUOTE: KeyName
DOWN: KeyName
E: KeyName
EIGHT: KeyName
END: KeyName
ENTER: KeyName
EQUALS: KeyName
ESCAPE: KeyName
EXCLAMATION_MARK: KeyName
F: KeyName
F1: KeyName
F10: KeyName
F11: KeyName
F12: KeyName
F2: KeyName
F3: KeyName
F4: KeyName
F5: KeyName
F6: KeyName
F7: KeyName
F8: KeyName
F9: KeyName
FIVE: KeyName
FOUR: KeyName
G: KeyName
GREATER_THAN: KeyName
H: KeyName
HASH: KeyName
HOME: KeyName
I: KeyName
INSERT: KeyName
J: KeyName
K: KeyName
L: KeyName
LEFT: KeyName
LEFT_BRACE: KeyName
LEFT_BRACKET: KeyName
LEFT_CONTROL: KeyName
LEFT_PAREN: KeyName
LEFT_SHIFT: KeyName
LESS_THAN: KeyName
M: KeyName
META: KeyName
MIDDLE: MouseButton
MINUS: KeyName
N: KeyName
NINE: KeyName
NONE: KeyName
O: KeyName
ONE: KeyName
P: KeyName
PAGE_DOWN: KeyName
PAGE_UP: KeyName
PERCENT: KeyName
PERIOD: KeyName
PIPE: KeyName
PLUS: KeyName
Q: KeyName
QUESTION_MARK: KeyName
QUOTE: KeyName
R: KeyName
RIGHT: KeyName
RIGHT_BRACE: KeyName
RIGHT_BRACKET: KeyName
RIGHT_CONTROL: KeyName
RIGHT_PAREN: KeyName
RIGHT_SHIFT: KeyName
S: KeyName
SEMICOLON: KeyName
SEVEN: KeyName
SHIFT: KeyModifier
SIX: KeyName
SLASH: KeyName
SPACE: KeyName
T: KeyName
TAB: KeyName
THREE: KeyName
TILDE: KeyName
TWO: KeyName
U: KeyName
UNDERSCORE: KeyName
UNKNOWN: KeyName
UP: KeyName
V: KeyName
W: KeyName
X: KeyName
Y: KeyName
Z: KeyName
ZERO: KeyName
