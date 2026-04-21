from __future__ import annotations
__all__: list[str] = ['Colormap']
class Colormap:
    """
    This class is used to create a color map for visualization of points.
    """
    class Point:
        """
        Initialize the class.
        
                Args:
                    value: The scalar value index of the point.
                    color: The color associated with the value.
                
        """
        def __init__(self, value, color):
            ...
        def __repr__(self):
            """
            Represent the color and value in the colormap.
            """
    @staticmethod
    def make_greyscale():
        """
        Generate a greyscale colormap.
        """
    @staticmethod
    def make_rainbow():
        """
        Generate the rainbow color array.
        """
    def __init__(self, points):
        ...
    def calc_color_array(self, values, range_min, range_max):
        """
        Generate the color array based on the minimum and maximum range passed.
        
                Args:
                    values: The index of values.
                    range_min: The minimum value in the range.
                    range_max: The maximum value in the range.
        
                Returns:
                    An array of color index based on the range passed.
                
        """
    def calc_u_array(self, values, range_min, range_max):
        """
        Generate the basic array based on the minimum and maximum range passed.
        """
