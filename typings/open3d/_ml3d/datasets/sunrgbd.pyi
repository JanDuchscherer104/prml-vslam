from __future__ import annotations
import logging as logging
import numpy as np
import open3d._ml3d.datasets.base_dataset
from open3d._ml3d.datasets.base_dataset import BaseDataset
import open3d._ml3d.datasets.utils.bev_box
from open3d._ml3d.datasets.utils.bev_box import BEVBox3D
import open3d._ml3d.utils.registry
import os as os
from pathlib import Path
import pickle as pickle
from posixpath import join
import typing
__all__: list[str] = ['BEVBox3D', 'BaseDataset', 'DATASET', 'Object3d', 'Path', 'SunRGBD', 'SunRGBDSplit', 'join', 'log', 'logging', 'np', 'os', 'pickle']
class Object3d(open3d._ml3d.datasets.utils.bev_box.BEVBox3D):
    """
    Stores object specific details like bbox coordinates.
    """
    def __init__(self, name, center, size, yaw, box2d):
        ...
class SunRGBD(open3d._ml3d.datasets.base_dataset.BaseDataset):
    """
    SunRGBD 3D dataset for Object Detection, used in visualizer, training, or
        test.
        
    """
    __abstractmethods__: typing.ClassVar[frozenset]
    _abc_impl: typing.ClassVar[_abc._abc_data]
    @staticmethod
    def read_lidar(path):
        ...
    def __init__(self, dataset_path, name = 'SunRGBD', cache_dir = './logs/cache', use_cache = False, **kwargs):
        """
        Initialize the dataset by passing the dataset and other details.
        
                Args:
                    dataset_path (str): The path to the dataset to use.
                    name (str): The name of the dataset (SunRGBD in this case).
                    cache_dir (str): The directory where the cache is stored.
                    use_cache (bool): Indicates if the dataset should be cached.
                
        """
    def get_label_to_names(self):
        ...
    def get_split(self, split):
        ...
    def get_split_list(self, split):
        ...
    def is_tested(self):
        ...
    def read_label(self, path):
        ...
    def save_test_result(self):
        ...
class SunRGBDSplit:
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
