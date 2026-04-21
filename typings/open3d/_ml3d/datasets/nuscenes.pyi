from __future__ import annotations
import logging as logging
import numpy as np
import open3d as o3d
import open3d._ml3d.datasets.base_dataset
from open3d._ml3d.datasets.base_dataset import BaseDataset
from open3d._ml3d.datasets.utils.bev_box import BEVBox3D
import open3d._ml3d.utils.registry
import os as os
from pathlib import Path
import pickle as pickle
from posixpath import join
from scipy.spatial.transform._rotation import Rotation as R
import typing
__all__: list[str] = ['BEVBox3D', 'BaseDataset', 'DATASET', 'NuSceneSplit', 'NuScenes', 'Path', 'R', 'join', 'log', 'logging', 'np', 'o3d', 'os', 'pickle']
class NuSceneSplit:
    def __init__(self, dataset, split = 'train'):
        ...
    def __len__(self):
        ...
    def get_attr(self, idx):
        ...
    def get_data(self, idx):
        ...
class NuScenes(open3d._ml3d.datasets.base_dataset.BaseDataset):
    """
    This class is used to create a dataset based on the NuScenes 3D dataset,
        and used in object detection, visualizer, training, or testing.
    
        The NuScenes 3D dataset is best suited for autonomous driving applications.
        
    """
    __abstractmethods__: typing.ClassVar[frozenset]
    _abc_impl: typing.ClassVar[_abc._abc_data]
    @staticmethod
    def get_label_to_names():
        """
        Returns a label to names dictionary object.
        
                Returns:
                    A dict where keys are label numbers and
                    values are the corresponding names.
                
        """
    @staticmethod
    def is_tested():
        """
        Checks if a datum in the dataset has been tested.
        
                Args:
                    dataset: The current dataset to which the datum belongs to.
                                attr: The attribute that needs to be checked.
        
                Returns:
                    If the dataum attribute is tested, then return the path where the
                        attribute is stored; else, returns false.
                
        """
    @staticmethod
    def read_label(info, calib):
        """
        Reads labels of bound boxes.
        
                Returns:
                    The data objects with bound boxes information.
                
        """
    @staticmethod
    def read_lidar(path):
        """
        Reads lidar data from the path provided.
        
                Returns:
                    A data object with lidar information.
                
        """
    @staticmethod
    def save_test_result():
        """
        Saves the output of a model.
        
                Args:
                    results: The output of a model for the datum associated with the
                        attribute passed.
                    attr: The attributes that correspond to the outputs passed in
                        results.
                
        """
    def __init__(self, dataset_path, info_path = None, name = 'NuScenes', cache_dir = './logs/cache', use_cache = False, **kwargs):
        """
        Initialize the function by passing the dataset and other details.
        
                Args:
                    dataset_path: The path to the dataset to use.
                    info_path: The path to the file that includes information about the
                        dataset. This is default to dataset path if nothing is provided.
                    name: The name of the dataset (NuScenes in this case).
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
    def read_cams(self, cam_dict):
        """
        Reads image data from the cam dict provided.
        
                Args:
                    cam_dict (Dict): Mapping from camera names to dict with image
                        information ('data_path', 'sensor2lidar_translation',
                        'sensor2lidar_rotation', 'cam_intrinsic').
        
                Returns:
                    A dict with keys as camera names and value as images.
                
        """
DATASET: open3d._ml3d.utils.registry.Registry
log: logging.Logger
