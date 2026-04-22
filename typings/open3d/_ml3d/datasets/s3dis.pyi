from __future__ import annotations
from genericpath import exists
from genericpath import isdir
import glob as glob
import logging as logging
import numpy as np
import open3d._ml3d.datasets.base_dataset
from open3d._ml3d.datasets.base_dataset import BaseDataset
from open3d._ml3d.datasets.base_dataset import BaseDatasetSplit
import open3d._ml3d.datasets.utils.bev_box
from open3d._ml3d.datasets.utils.bev_box import BEVBox3D
from open3d._ml3d.datasets.utils.dataprocessing import DataProcessing
from open3d._ml3d.datasets.utils.operations import get_min_bbox
from open3d._ml3d.utils.dataset_helper import make_dir
import open3d._ml3d.utils.registry
import os as os
import pandas as pd
from pathlib import Path
import pickle as pickle
from posixpath import abspath
from posixpath import dirname
from posixpath import join
from sklearn.neighbors._kd_tree import KDTree
from tqdm.std import tqdm
import typing

__all__: list[str] = [
    "BEVBox3D",
    "BaseDataset",
    "BaseDatasetSplit",
    "DATASET",
    "DataProcessing",
    "KDTree",
    "Object3d",
    "Path",
    "S3DIS",
    "S3DISSplit",
    "abspath",
    "dirname",
    "exists",
    "get_min_bbox",
    "glob",
    "isdir",
    "join",
    "log",
    "logging",
    "make_dir",
    "np",
    "os",
    "pd",
    "pickle",
    "tqdm",
]

class Object3d(open3d._ml3d.datasets.utils.bev_box.BEVBox3D):
    """
    Stores object specific details like bbox coordinates.
    """
    def __init__(self, name, center, size, yaw): ...

class S3DIS(open3d._ml3d.datasets.base_dataset.BaseDataset):
    """
    This class is used to create a dataset based on the S3DIS (Stanford
        Large-Scale 3D Indoor Spaces) dataset, and used in visualizer, training, or
        testing.

        The S3DIS dataset is best used to train models for building indoors.

    """

    __abstractmethods__: typing.ClassVar[frozenset]
    _abc_impl: typing.ClassVar[_abc._abc_data]
    @staticmethod
    def create_ply_files(dataset_path, class_names): ...
    @staticmethod
    def get_label_to_names():
        """
        Returns a label to names dictionary object.

                Returns:
                    A dict where keys are label numbers and
                    values are the corresponding names.

        """
    @staticmethod
    def read_bboxes(bboxes, ignored_objects): ...
    def __init__(
        self,
        dataset_path,
        name="S3DIS",
        task="segmentation",
        cache_dir="./logs/cache",
        use_cache=False,
        class_weights=[
            3370714,
            2856755,
            4919229,
            318158,
            375640,
            478001,
            974733,
            650464,
            791496,
            88727,
            1284130,
            229758,
            2272837,
        ],
        num_points=40960,
        test_area_idx=3,
        ignored_label_inds=list(),
        ignored_objects=["wall", "floor", "ceiling", "beam", "column", "clutter"],
        test_result_folder="./test",
        **kwargs,
    ):
        """
        Initialize the function by passing the dataset and other details.

                Args:
                    dataset_path: The path to the dataset to use.
                    name: The name of the dataset (S3DIS in this case).
                    task: One of {segmentation, detection} for semantic segmentation and object detection.
                    cache_dir: The directory where the cache is stored.
                    use_cache: Indicates if the dataset should be cached.
                    class_weights: The class weights to use in the dataset.
                    num_points: The maximum number of points to use when splitting the dataset.
                    test_area_idx: The area to use for testing. The valid values are 1 through 6.
                    ignored_label_inds: A list of labels that should be ignored in the dataset.
                    ignored_objects: Ignored objects
                    test_result_folder: The folder where the test results should be stored.

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
    def get_split_list(self, split): ...
    def is_tested(self, attr): ...
    def save_test_result(self, results, attr): ...

class S3DISSplit(open3d._ml3d.datasets.base_dataset.BaseDatasetSplit):
    """
    This class is used to create a split for S3DIS dataset.

        Initialize the class.

        Args:
            dataset: The dataset to split.
            split: A string identifying the dataset split that is usually one of
                'training', 'test', 'validation', or 'all'.
            **kwargs: The configuration of the model as keyword arguments.

        Returns:
            A dataset split object providing the requested subset of the data.

    """

    __abstractmethods__: typing.ClassVar[frozenset]
    _abc_impl: typing.ClassVar[_abc._abc_data]
    def __init__(self, dataset, split="training"): ...
    def __len__(self): ...
    def get_attr(self, idx): ...
    def get_data(self, idx): ...

DATASET: open3d._ml3d.utils.registry.Registry
log: logging.Logger
