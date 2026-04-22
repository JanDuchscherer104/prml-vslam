from __future__ import annotations
import abc
from abc import ABC
from abc import abstractmethod
from genericpath import exists
import logging as logging
import numpy as np
from open3d._ml3d.utils.builder import get_module
from open3d._ml3d.utils.config import Config
from posixpath import abspath
from posixpath import dirname
from posixpath import join
import typing
import yaml as yaml

__all__: list[str] = [
    "ABC",
    "BaseDataset",
    "BaseDatasetSplit",
    "Config",
    "abspath",
    "abstractmethod",
    "dirname",
    "exists",
    "get_module",
    "join",
    "log",
    "logging",
    "np",
    "yaml",
]

class BaseDataset(abc.ABC):
    """
    The base dataset class that is used by all other datasets.

        All datasets must inherit from this class and implement the functions in order to be
        compatible with pipelines.

        Args:
            **kwargs: The configuration of the model as keyword arguments.

        Attributes:
            cfg: The configuration file as Config object that stores the keyword
                arguments that were passed to the constructor.
            name: The name of the dataset.

        **Example:**
            This example shows a custom dataset that inherit from the base_dataset class:

                from .base_dataset import BaseDataset

                class MyDataset(BaseDataset):
                def __init__(self,
                     dataset_path,
                     name='CustomDataset',
                     cache_dir='./logs/cache',
                     use_cache=False,
                     num_points=65536,
                     class_weights=[],
                     test_result_folder='./test',
                     val_files=['Custom.ply'],
                     **kwargs):

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
    def __init__(self, **kwargs):
        """
        Initialize the class by passing the dataset path.
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
    def is_tested(self, attr):
        """
        Checks whether a datum has been tested.

                Args:
                    attr: The attributes associated with the datum.

                Returns:
                    This returns True if the test result has been stored for the datum with the
                    specified attribute; else returns False.

        """
    def save_test_result(self, results, attr):
        """
        Saves the output of a model.

                Args:
                    results: The output of a model for the datum associated with the attribute passed.
                    attr: The attributes that correspond to the outputs passed in results.

        """

class BaseDatasetSplit(abc.ABC):
    """
    The base class for dataset splits.

        This class provides access to the data of a specified subset or split of a dataset.

        Args:
            dataset: The dataset object associated to this split.
            split: A string identifying the dataset split, usually one of
                'training', 'test', 'validation', or 'all'.

        Attributes:
            cfg: Shortcut to the config of the dataset object.
            dataset: The dataset object associated to this split.
            split: A string identifying the dataset split, usually one of
                'training', 'test', 'validation', or 'all'.

    """

    __abstractmethods__: typing.ClassVar[frozenset]
    _abc_impl: typing.ClassVar[_abc._abc_data]
    def __init__(self, dataset, split="training"): ...
    def __len__(self):
        """
        Returns the number of samples in the split.
        """
    def get_attr(self, idx):
        """
        Returns the attributes for the given index.
        """
    def get_data(self, idx):
        """
        Returns the data for the given index.
        """

log: logging.Logger
