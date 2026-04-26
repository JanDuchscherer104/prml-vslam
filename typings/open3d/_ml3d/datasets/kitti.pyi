from __future__ import annotations
import argparse as argparse
from genericpath import exists
from genericpath import isfile
from glob import glob
import logging as logging
import numpy as np
import open3d._ml3d.datasets.base_dataset
from open3d._ml3d.datasets.base_dataset import BaseDataset
from open3d._ml3d.datasets.base_dataset import BaseDatasetSplit
import open3d._ml3d.datasets.utils.bev_box
from open3d._ml3d.datasets.utils.bev_box import BEVBox3D
from open3d._ml3d.datasets.utils.dataprocessing import DataProcessing
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

__all__: list[str] = [
    "BEVBox3D",
    "BaseDataset",
    "BaseDatasetSplit",
    "Config",
    "DATASET",
    "DataProcessing",
    "KITTI",
    "KITTISplit",
    "Object3d",
    "Path",
    "abspath",
    "argparse",
    "dirname",
    "exists",
    "glob",
    "isfile",
    "join",
    "log",
    "logging",
    "make_dir",
    "np",
    "os",
    "pickle",
    "split",
    "sys",
    "yaml",
]

class KITTI(open3d._ml3d.datasets.base_dataset.BaseDataset):
    """
    This class is used to create a dataset based on the KITTI dataset, and
        used in object detection, visualizer, training, or testing.

    """

    __abstractmethods__: typing.ClassVar[frozenset]
    _abc_impl: typing.ClassVar[_abc._abc_data]
    @staticmethod
    def _extend_matrix(mat): ...
    @staticmethod
    def get_label_to_names():
        """
        Returns a label to names dictionary object.

                Returns:
                    A dict where keys are label numbers and values are the corresponding
                    names.

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
    def __init__(
        self,
        dataset_path,
        name="KITTI",
        cache_dir="./logs/cache",
        use_cache=False,
        val_split=3712,
        test_result_folder="./test",
        **kwargs,
    ):
        """
        Initialize the function by passing the dataset and other details.

                Args:
                    dataset_path: The path to the dataset to use.
                    name: The name of the dataset (KITTI in this case).
                    cache_dir: The directory where the cache is stored.
                    use_cache: Indicates if the dataset should be cached.
                    val_split: The split value to get a set of images for training,
                    validation, for testing.
                    test_result_folder: Path to store test output.

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
    def is_tested(self):
        """
        Checks if a datum in the dataset has been tested.

                Args:
                    dataset: The current dataset to which the datum belongs to.
                    attr: The attribute that needs to be checked.

                Returns:
                    If the dataum attribute is tested, then return the path where the
                    attribute is stored; else, returns false.

        """
    def save_test_result(self, results, attrs):
        """
        Saves the output of a model.

                Args:
                    results: The output of a model for the datum associated with the
                    attribute passed.
                    attrs: The attributes that correspond to the outputs passed in
                    results.

        """

class KITTISplit:
    def __init__(self, dataset, split="train"): ...
    def __len__(self): ...
    def get_attr(self, idx): ...
    def get_data(self, idx): ...

class Object3d(open3d._ml3d.datasets.utils.bev_box.BEVBox3D):
    """
    The class stores details that are object-specific, such as bounding box
        coordinates, occulusion and so on.

    """
    def __init__(self, center, size, label, calib=None): ...
    def get_difficulty(self):
        """
        The method determines difficulty level of the object, such as Easy,
                Moderate, or Hard.

        """
    def to_str(self): ...

DATASET: open3d._ml3d.utils.registry.Registry
log: logging.Logger
