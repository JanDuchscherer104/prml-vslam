"""
Functionality for running the open3d viewer.
"""
from __future__ import annotations
__all__: list[str] = ['run_viewer']
def run_viewer(args: list[str]) -> None:
    """
    Args:
        args (list[str]): List of arguments containing the path of the calling program (which should be in the same directory as the gui resources folder) and the optional path of the geometry to visualize.
    
    Returns:
        None
    """
