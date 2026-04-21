from __future__ import annotations
import argparse as argparse
from genericpath import exists
from genericpath import isfile
from glob import glob
import logging as logging
import numpy as np
import open3d._ml3d.datasets.base_dataset
from open3d._ml3d.datasets.base_dataset import BaseDataset
import open3d._ml3d.datasets.utils.bev_box
from open3d._ml3d.datasets.utils.bev_box import BEVBox3D
from open3d._ml3d.utils.config import Config
from open3d._ml3d.utils.dataset_helper import make_dir
import open3d._ml3d.utils.registry
import os as os
from pathlib import Path
import pickle as pickle
from posixpath import abspath
from posixpath import dirname
from posixpath import join
from posixpath import split
import sys as sys
import typing
import yaml as yaml
__all__: list[str] = ['BEVBox3D', 'BaseDataset', 'Config', 'DATASET', 'Object3d', 'Path', 'Waymo', 'WaymoSplit', 'abspath', 'argparse', 'dirname', 'exists', 'glob', 'isfile', 'join', 'log', 'logging', 'make_dir', 'np', 'os', 'pickle', 'split', 'sys', 'yaml']
class Object3d(open3d._ml3d.datasets.utils.bev_box.BEVBox3D):
    def __init__(self, center, size, label, calib):
        ...
    def get_difficulty(self):
        """
        The method determines difficulty level of the object, such as Easy,
                Moderate, or Hard.
                
        """
    def to_kitti_format(self):
        """
        This method transforms the class to kitti format.
        """
    def to_str(self):
        ...
class Waymo(open3d._ml3d.datasets.base_dataset.BaseDataset):
    """
    This class is used to create a dataset based on the Waymo 3D dataset, and
        used in object detection, visualizer, training, or testing.
    
        The Waymo 3D dataset is best suited for autonomous driving applications.
        
    """
    __abstractmethods__: typing.ClassVar[frozenset]
    _abc_impl: typing.ClassVar[_abc._abc_data]
    @staticmethod
    def _extend_matrix(mat):
        ...
    @staticmethod
    def get_label_to_names():
        """
        Returns a label to names dictionary object.
        
                Returns:
                    A dict where keys are label numbers and
                    values are the corresponding names.
                
        """
    @staticmethod
    def is_tested(attr):
        """
        Checks if a datum in the dataset has been tested.
        
                Args:
                    attr: The attribute that needs to be checked.
        
                Returns:
                    If the datum attribute is tested, then return the path where the
                        attribute is stored; else, returns false.
                
        """
    @staticmethod
    def read_calib(path):
        """
        Reads calibiration for the dataset. You can use them to compare
                modeled results to observed results.
        
                Returns:
                    The camera and the camera image used in calibration.
                
        """
    @staticmethod
    def read_label(path, calib):
        """
        Reads labels of bounding boxes.
        
                Args:
                    path: The path to the label file.
                    calib: Calibration as returned by read_calib().
        
                Returns:
                    The data objects with bounding boxes information.
                
        """
    @staticmethod
    def read_lidar(path):
        """
        Reads lidar data from the path provided.
        
                Returns:
                    pc: pointcloud data with shape [N, 6], where
                        the format is xyzRGB.
                
        """
    @staticmethod
    def save_test_result(results, attr):
        """
        Saves the output of a model.
        
                Args:
                    results: The output of a model for the datum associated with the attribute passed.
                    attr: The attributes that correspond to the outputs passed in results.
                
        """
    def __init__(self, dataset_path, name = 'Waymo', cache_dir = './logs/cache', use_cache = False, **kwargs):
        """
        Initialize the function by passing the dataset and other details.
        
                Args:
                    dataset_path: The path to the dataset to use.
                    name: The name of the dataset (Waymo in this case).
                    cache_dir: The directory where the cache is stored.
                    use_cache: Indicates if the dataset should be cached.
        
                Returns:
                    class: The corresponding class.
                
        """
    def get_split(self, split):
        """
        Returns a dataset split.
        
                Args:
                    split: A string identifying the dataset split that is usually one of
                    'training', 'test', 'validation', or 'all'.
        
                Returns:
                    A dataset split object providing the requested subset of the data.
                
        """
    def get_split_list(self, split):
        """
        Returns the list of data splits available.
        
                Args:
                    split: A string identifying the dataset split that is usually one of
                    'training', 'test', 'validation', or 'all'.
        
                Returns:
                    A dataset split object providing the requested subset of the data.
        
                Raises:
                    ValueError: Indicates that the split name passed is incorrect. The
                    split name should be one of 'training', 'test', 'validation', or
                    'all'.
                
        """
class WaymoSplit:
    def __init__(self, dataset, split = 'train'):
        ...
    def __len__(self):
        ...
    def get_attr(self, idx):
        ...
    def get_data(self, idx):
        ...
DATASET: open3d._ml3d.utils.registry.Registry
log: logging.Logger
