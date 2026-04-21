from __future__ import annotations
from genericpath import exists
import hashlib as hashlib
import numpy as np
from os import makedirs
from posix import listdir
from posixpath import join
from posixpath import splitext
__all__: list[str] = ['Cache', 'exists', 'get_hash', 'hashlib', 'join', 'listdir', 'make_dir', 'makedirs', 'np', 'splitext']
class Cache:
    """
    Cache converter for preprocessed data.
    """
    def __call__(self, unique_id: str, *data):
        """
        Call the converter. If the cache exists, load and return the cache,
                otherwise run the preprocess function and store the cache.
        
                Args:
                    unique_id: A unique key of this data.
                    data: Input to the preprocess function.
        
                Returns:
                    class: Preprocessed (cache) data.
                
        """
    def __init__(self, func: typing.Callable, cache_dir: str, cache_key: str):
        """
        Initialize.
        
                Args:
                    func: preprocess function of a model.
                    cache_dir: directory to store the cache.
                    cache_key: key of this cache
                Returns:
                    class: The corresponding class.
                
        """
    def _read(self, fpath):
        ...
    def _write(self, x, fpath):
        ...
def get_hash(x: str):
    """
    Generate a hash from a string.
    """
def make_dir(folder_name):
    """
    Create a directory.
    
        If already exists, do nothing
        
    """
