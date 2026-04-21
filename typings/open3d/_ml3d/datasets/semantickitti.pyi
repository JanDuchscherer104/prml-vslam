from __future__ import annotations
import argparse as argparse
from genericpath import exists
from genericpath import isfile
import logging as logging
import numpy as np
import open3d._ml3d.datasets.base_dataset
from open3d._ml3d.datasets.base_dataset import BaseDataset
from open3d._ml3d.datasets.base_dataset import BaseDatasetSplit
from open3d._ml3d.datasets.utils.dataprocessing import DataProcessing
from open3d._ml3d.utils.dataset_helper import make_dir
import open3d._ml3d.utils.registry
import os as os
import pickle as pickle
from posixpath import abspath
from posixpath import dirname
from posixpath import join
from posixpath import split
from sklearn.neighbors._kd_tree import KDTree
import sys as sys
import typing
import yaml as yaml
__all__: list[str] = ['BaseDataset', 'BaseDatasetSplit', 'DATASET', 'DataProcessing', 'KDTree', 'SemanticKITTI', 'SemanticKITTISplit', 'abspath', 'argparse', 'dirname', 'exists', 'isfile', 'join', 'log', 'logging', 'make_dir', 'np', 'os', 'pickle', 'split', 'sys', 'yaml']
class SemanticKITTI(open3d._ml3d.datasets.base_dataset.BaseDataset):
    """
    This class is used to create a dataset based on the SemanticKitti
        dataset, and used in visualizer, training, or testing.
    
        The dataset is best for semantic scene understanding.
        
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
    def __init__(self, dataset_path, name = 'SemanticKITTI', cache_dir = './logs/cache', use_cache = False, class_weights = [55437630, 320797, 541736, 2578735, 3274484, 552662, 184064, 78858, 240942562, 17294618, 170599734, 6369672, 230413074, 101130274, 476491114, 9833174, 129609852, 4506626, 1168181], ignored_label_inds = [0], test_result_folder = './test', test_split = ['11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21'], training_split = ['00', '01', '02', '03', '04', '05', '06', '07', '09', '10'], validation_split = ['08'], all_split = ['00', '01', '02', '03', '04', '05', '06', '07', '09', '08', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21'], **kwargs):
        """
        Initialize the function by passing the dataset and other details.
        
                Args:
                    dataset_path: The path to the dataset to use.
                    name: The name of the dataset (Semantic3D in this case).
                    cache_dir: The directory where the cache is stored.
                    use_cache: Indicates if the dataset should be cached.
                    class_weights: The class weights to use in the dataset.
                    ignored_label_inds: A list of labels that should be ignored in the dataset.
                    test_result_folder: The folder where the test results should be stored.
        
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
        Returns a dataset split.
        
                Args:
                    split: A string identifying the dataset split that is usually one of
                    'training', 'test', 'validation', or 'all'.
        
                Returns:
                    A dataset split object providing the requested subset of the data.
        
                Raises:
                    ValueError: Indicates that the split name passed is incorrect. The split name should be one of
                    'training', 'test', 'validation', or 'all'.
                
        """
    def is_tested(self, attr):
        """
        Checks if a datum in the dataset has been tested.
        
                Args:
                    attr: The attribute that needs to be checked.
        
                Returns:
                    If the datum attribute is tested, then return the path where the
                        attribute is stored; else, returns false.
                
        """
    def save_test_result(self, results, attr):
        """
        Saves the output of a model.
        
                Args:
                    results: The output of a model for the datum associated with the attribute passed.
                    attr: The attributes that correspond to the outputs passed in results.
                
        """
    def save_test_result_kpconv(self, results, inputs):
        ...
class SemanticKITTISplit(open3d._ml3d.datasets.base_dataset.BaseDatasetSplit):
    __abstractmethods__: typing.ClassVar[frozenset]
    _abc_impl: typing.ClassVar[_abc._abc_data]
    def __init__(self, dataset, split = 'training'):
        ...
    def __len__(self):
        ...
    def get_attr(self, idx):
        ...
    def get_data(self, idx):
        ...
DATASET: open3d._ml3d.utils.registry.Registry
log: logging.Logger
