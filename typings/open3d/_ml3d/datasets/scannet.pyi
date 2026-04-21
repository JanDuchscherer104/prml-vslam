from __future__ import annotations
import logging as logging
import numpy as np
import open3d._ml3d.datasets.base_dataset
from open3d._ml3d.datasets.base_dataset import BaseDataset
from open3d._ml3d.datasets.base_dataset import BaseDatasetSplit
import open3d._ml3d.datasets.utils.bev_box
from open3d._ml3d.datasets.utils.bev_box import BEVBox3D
from open3d._ml3d.utils.dataset_helper import make_dir
import open3d._ml3d.utils.registry
import os as os
from pathlib import Path
from posixpath import join
import typing
__all__: list[str] = ['BEVBox3D', 'BaseDataset', 'BaseDatasetSplit', 'DATASET', 'Object3d', 'Path', 'Scannet', 'ScannetSplit', 'join', 'log', 'logging', 'make_dir', 'np', 'os']
class Object3d(open3d._ml3d.datasets.utils.bev_box.BEVBox3D):
    """
    Stores object specific details like bbox coordinates.
    """
    def __init__(self, name, center, size, yaw):
        ...
class Scannet(open3d._ml3d.datasets.base_dataset.BaseDataset):
    """
    Scannet 3D dataset for Object Detection, used in visualizer, training, or
        test.
        
    """
    __abstractmethods__: typing.ClassVar[frozenset]
    _abc_impl: typing.ClassVar[_abc._abc_data]
    @staticmethod
    def read_lidar(path):
        ...
    def __init__(self, dataset_path, name = 'Scannet', cache_dir = './logs/cache', use_cache = False, **kwargs):
        """
        Initialize the dataset by passing the dataset and other details.
        
                Args:
                    dataset_path (str): The path to the dataset to use.
                    name (str): The name of the dataset (Scannet in this case).
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
    def read_label(self, scene):
        ...
    def save_test_result(self, results, attr):
        ...
class ScannetSplit(open3d._ml3d.datasets.base_dataset.BaseDatasetSplit):
    __abstractmethods__: typing.ClassVar[frozenset]
    _abc_impl: typing.ClassVar[_abc._abc_data]
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
