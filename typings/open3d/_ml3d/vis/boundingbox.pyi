from PIL import Image
from PIL import ImageDraw
from __future__ import annotations
import numpy as np
import open3d as o3d
import typing
__all__: list[str] = ['BoundingBox3D', 'Image', 'ImageDraw', 'np', 'o3d']
class BoundingBox3D:
    """
    Class that defines an axially-oriented bounding box.
    """
    next_id: typing.ClassVar[int] = 1
    @staticmethod
    def create_lines(boxes, lut = None, out_format = 'lineset'):
        """
        Creates a LineSet that can be used to render the boxes.
        
                Args:
                    boxes: the list of bounding boxes
                    lut: a ml3d.vis.LabelLUT that is used to look up the color based on
                        the label_class argument of the BoundingBox3D constructor. If
                        not provided, a color of 50% grey will be used. (optional)
                    out_format (str): Output format. Can be "lineset" (default) for the
                        Open3D lineset or "dict" for a dictionary of lineset properties.
        
                Returns:
                    For out_format == "lineset": open3d.geometry.LineSet
                    For out_format == "dict": Dictionary of lineset properties
                        ("vertex_positions", "line_indices", "line_colors", "bbox_labels",
                        "bbox_confidences").
                
        """
    @staticmethod
    def plot_rect3d_on_img(img, num_rects, rect_corners, line_indices, color = None, thickness = 1):
        """
        Plot the boundary lines of 3D rectangular on 2D images.
        
                Args:
                    img (numpy.array): The numpy array of image.
                    num_rects (int): Number of 3D rectangulars.
                    rect_corners (numpy.array): Coordinates of the corners of 3D
                        rectangulars. Should be in the shape of [num_rect, 8, 2] or
                        [num_rect, 14, 2] if counting arrows.
                    line_indices (numpy.array): indicates connectivity of lines between
                        rect_corners.  Should be in the shape of [num_rect, 12, 2] or
                        [num_rect, 17, 2] if counting arrows.
                    color (tuple[int]): The color to draw bboxes. Default: (1.0, 1.0,
                        1.0), i.e. white.
                    thickness (int, optional): The thickness of bboxes. Default: 1.
                
        """
    @staticmethod
    def project_to_img(boxes, img, lidar2img_rt = ..., lut = None):
        """
        Returns image with projected 3D bboxes
        
                Args:
                    boxes: the list of bounding boxes
                    img: an RGB image
                    lidar2img_rt: 4x4 transformation from lidar frame to image plane
                    lut: a ml3d.vis.LabelLUT that is used to look up the color based on
                        the label_class argument of the BoundingBox3D constructor. If
                        not provided, a color of 50% grey will be used. (optional)
                
        """
    def __init__(self, center, front, up, left, size, label_class, confidence, meta = None, show_class = False, show_confidence = False, show_meta = None, identifier = None, arrow_length = 1.0):
        """
        Creates a bounding box.
        
                Front, up, left define the axis of the box and must be normalized and
                mutually orthogonal.
        
                Args:
                    center: (x, y, z) that defines the center of the box.
                    front: normalized (i, j, k) that defines the front direction of the
                        box.
                    up: normalized (i, j, k) that defines the up direction of the box.
                    left: normalized (i, j, k) that defines the left direction of the
                        box.
                    size: (width, height, depth) that defines the size of the box, as
                        measured from edge to edge.
                    label_class: integer specifying the classification label. If an LUT
                        is specified in create_lines() this will be used to determine
                        the color of the box.
                    confidence: confidence level of the box.
                    meta: a user-defined string (optional).
                    show_class: displays the class label in text near the box
                        (optional).
                    show_confidence: displays the confidence value in text near the box
                        (optional).
                    show_meta: displays the meta string in text near the box (optional).
                    identifier: a unique integer that defines the id for the box
                        (optional, will be generated if not provided).
                    arrow_length: the length of the arrow in the front_direct. Set to
                        zero to disable the arrow (optional).
                
        """
    def __repr__(self):
        ...
