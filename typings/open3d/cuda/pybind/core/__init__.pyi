from __future__ import annotations
import typing
from typing import Any as capsule
from . import cuda
from . import kernel
from . import nns
from . import sycl
__all__: list[str] = ['Blob', 'Device', 'Dtype', 'DynamicSizeVector', 'HashMap', 'HashSet', 'Scalar', 'SizeVector', 'Tensor', 'addmm', 'append', 'bool', 'bool8', 'capsule', 'concatenate', 'cuda', 'det', 'float32', 'float64', 'int16', 'int32', 'int64', 'int8', 'inv', 'kernel', 'lstsq', 'lu', 'lu_ipiv', 'matmul', 'maximum', 'minimum', 'nns', 'solve', 'svd', 'sycl', 'sycl_demo', 'tril', 'triu', 'triul', 'uint16', 'uint32', 'uint64', 'uint8', 'undefined']
class Blob:
    pass
class Device:
    """
    Device context specifying device type and device id.
    """
    class DeviceType:
        """
        Members:
        
          CPU
        
          CUDA
        """
        CPU: typing.ClassVar[Device.DeviceType]
        CUDA: typing.ClassVar[Device.DeviceType]
        __members__: typing.ClassVar[dict[str, Device.DeviceType]]
        def __eq__(self, other: typing.Any) -> bool:
            ...
        def __getstate__(self) -> int:
            ...
        def __hash__(self) -> int:
            ...
        def __index__(self) -> int:
            ...
        def __init__(self, value: int) -> None:
            ...
        def __int__(self) -> int:
            ...
        def __ne__(self, other: typing.Any) -> bool:
            ...
        def __repr__(self) -> str:
            ...
        def __setstate__(self, state: int) -> None:
            ...
        def __str__(self) -> str:
            ...
        @property
        def name(self) -> str:
            ...
        @property
        def value(self) -> int:
            ...
    CPU: typing.ClassVar[Device.DeviceType]
    CUDA: typing.ClassVar[Device.DeviceType]
    __hash__: typing.ClassVar[None] = None
    def __ene__(self, arg0: Device) -> bool:
        ...
    def __eq__(self, arg0: Device) -> bool:
        ...
    def __getstate__(self) -> tuple:
        ...
    @typing.overload
    def __init__(self) -> None:
        ...
    @typing.overload
    def __init__(self, arg0: Device.DeviceType, arg1: int) -> None:
        ...
    @typing.overload
    def __init__(self, arg0: str, arg1: int) -> None:
        ...
    @typing.overload
    def __init__(self, arg0: str) -> None:
        ...
    def __repr__(self) -> str:
        ...
    def __setstate__(self, arg0: tuple) -> None:
        ...
    def __str__(self) -> str:
        ...
    def get_id(self) -> int:
        ...
    def get_type(self) -> Device.DeviceType:
        ...
class Dtype:
    """
    Open3D data types.
    """
    class DtypeCode:
        """
        Members:
        
          Undefined
        
          Bool
        
          Int
        
          UInt
        
          Float
        
          Object
        """
        Bool: typing.ClassVar[Dtype.DtypeCode]
        Float: typing.ClassVar[Dtype.DtypeCode]
        Int: typing.ClassVar[Dtype.DtypeCode]
        Object: typing.ClassVar[Dtype.DtypeCode]
        UInt: typing.ClassVar[Dtype.DtypeCode]
        Undefined: typing.ClassVar[Dtype.DtypeCode]
        __members__: typing.ClassVar[dict[str, Dtype.DtypeCode]]
        def __eq__(self, other: typing.Any) -> bool:
            ...
        def __getstate__(self) -> int:
            ...
        def __hash__(self) -> int:
            ...
        def __index__(self) -> int:
            ...
        def __init__(self, value: int) -> None:
            ...
        def __int__(self) -> int:
            ...
        def __ne__(self, other: typing.Any) -> bool:
            ...
        def __repr__(self) -> str:
            ...
        def __setstate__(self, state: int) -> None:
            ...
        def __str__(self) -> str:
            ...
        @property
        def name(self) -> str:
            ...
        @property
        def value(self) -> int:
            ...
    Bool: typing.ClassVar[Dtype]
    Float32: typing.ClassVar[Dtype]
    Float64: typing.ClassVar[Dtype]
    Int16: typing.ClassVar[Dtype]
    Int32: typing.ClassVar[Dtype]
    Int64: typing.ClassVar[Dtype]
    Int8: typing.ClassVar[Dtype]
    UInt16: typing.ClassVar[Dtype]
    UInt32: typing.ClassVar[Dtype]
    UInt64: typing.ClassVar[Dtype]
    UInt8: typing.ClassVar[Dtype]
    Undefined: typing.ClassVar[Dtype]
    def __ene__(self, arg0: Dtype) -> bool:
        ...
    def __eq__(self, arg0: Dtype) -> bool:
        ...
    def __hash__(self) -> int:
        ...
    def __init__(self, arg0: Dtype.DtypeCode, arg1: int, arg2: str) -> None:
        ...
    def __repr__(self) -> str:
        ...
    def __str__(self) -> str:
        ...
    def byte_code(self) -> Dtype.DtypeCode:
        ...
    def byte_size(self) -> int:
        ...
class DynamicSizeVector:
    """
    A vector of integers for specifying shape, strides, etc. Some elements can be None.
    """
    __hash__: typing.ClassVar[None] = None
    def __bool__(self) -> bool:
        """
        Check whether the list is nonempty
        """
    def __contains__(self, x: int | None) -> bool:
        """
        Return true the container contains ``x``
        """
    @typing.overload
    def __delitem__(self, arg0: int) -> None:
        """
        Delete the list elements at index ``i``
        """
    @typing.overload
    def __delitem__(self, arg0: slice) -> None:
        """
        Delete list elements using a slice object
        """
    def __eq__(self, arg0: DynamicSizeVector) -> bool:
        ...
    @typing.overload
    def __getitem__(self, s: slice) -> DynamicSizeVector:
        """
        Retrieve list elements using a slice object
        """
    @typing.overload
    def __getitem__(self, arg0: int) -> int | None:
        ...
    @typing.overload
    def __init__(self) -> None:
        ...
    @typing.overload
    def __init__(self, arg0: DynamicSizeVector) -> None:
        """
        Copy constructor
        """
    @typing.overload
    def __init__(self, arg0: typing.Iterable) -> None:
        ...
    def __iter__(self) -> typing.Iterator[int | None]:
        ...
    def __len__(self) -> int:
        ...
    def __ne__(self, arg0: DynamicSizeVector) -> bool:
        ...
    def __repr__(self) -> str:
        ...
    @typing.overload
    def __setitem__(self, arg0: int, arg1: int | None) -> None:
        ...
    @typing.overload
    def __setitem__(self, arg0: slice, arg1: DynamicSizeVector) -> None:
        """
        Assign list elements using a slice object
        """
    def append(self, x: int | None) -> None:
        """
        Add an item to the end of the list
        """
    def clear(self) -> None:
        """
        Clear the contents
        """
    def count(self, x: int | None) -> int:
        """
        Return the number of times ``x`` appears in the list
        """
    @typing.overload
    def extend(self, L: DynamicSizeVector) -> None:
        """
        Extend the list by appending all the items in the given list
        """
    @typing.overload
    def extend(self, L: typing.Iterable) -> None:
        """
        Extend the list by appending all the items in the given list
        """
    def insert(self, i: int, x: int | None) -> None:
        """
        Insert an item at a given position.
        """
    @typing.overload
    def pop(self) -> int | None:
        """
        Remove and return the last item
        """
    @typing.overload
    def pop(self, i: int) -> int | None:
        """
        Remove and return the item at index ``i``
        """
    def remove(self, x: int | None) -> None:
        """
        Remove the first item from the list whose value is x. It is an error if there is no such item.
        """
class HashMap:
    """
    A HashMap is an unordered map from key to value wrapped by Tensors.
    """
    @staticmethod
    def load(file_name: str) -> HashMap:
        """
        Load a hash map from a .npz file.
        
        Args:
            file_name (str): File name of the corresponding .npz file.
        
        Returns:
            open3d.cuda.pybind.core.HashMap
        """
    @typing.overload
    def __init__(self, init_capacity: int, key_dtype: Dtype, key_element_shape: SizeVector, value_dtype: Dtype, value_element_shape: SizeVector, device: Device = ...) -> None:
        """
        Args:
            init_capacity (int): Initial capacity of a hash container.
            key_dtype (open3d.cuda.pybind.core.Dtype): Data type for the input key tensor.
            key_element_shape (open3d.cuda.pybind.core.SizeVector): Element shape for the input key tensor. E.g. (3) for 3D coordinate keys.
            value_dtype (open3d.cuda.pybind.core.Dtype): Data type for the input value tensor.
            value_element_shape (open3d.cuda.pybind.core.SizeVector): Element shape for the input value tensor. E.g. (1) for mapped index.
            device (open3d.cuda.pybind.core.Device, optional, default=CPU:0): Compute device to store and operate on the hash container.
        """
    @typing.overload
    def __init__(self, init_capacity: int, key_dtype: Dtype, key_element_shape: SizeVector, value_dtypes: list[Dtype], value_element_shapes: list[SizeVector], device: Device = ...) -> None:
        """
        Args:
            init_capacity (int): Initial capacity of a hash container.
            key_dtype (open3d.cuda.pybind.core.Dtype): Data type for the input key tensor.
            key_element_shape (open3d.cuda.pybind.core.SizeVector): Element shape for the input key tensor. E.g. (3) for 3D coordinate keys.
            value_dtypes (list[open3d.cuda.pybind.core.Dtype]): List of data type for the input value tensors.
            value_element_shapes (list[open3d.cuda.pybind.core.SizeVector]): List of element shapes for the input value tensors. E.g. ((8,8,8,1), (8,8,8,3)) for mapped weights and RGB colors stored in 8^3 element arrays.
            device (open3d.cuda.pybind.core.Device, optional, default=CPU:0): Compute device to store and operate on the hash container.
        """
    def activate(self, keys: Tensor) -> tuple:
        """
        Activate an array of keys stored in Tensors without copying values.
        
        Args:
            keys (open3d.cuda.pybind.core.Tensor): Input keys stored in a tensor of shape (N, key_element_shape).
        
        Returns:
            tuple
        """
    def active_buf_indices(self) -> Tensor:
        """
        Get the buffer indices corresponding to active entries in the hash map.
        """
    def capacity(self) -> int:
        """
        Get the capacity of the hash map.
        """
    def clone(self) -> HashMap:
        """
        Clone the hash map, including the data structure and the data buffers.
        """
    def cpu(self) -> HashMap:
        """
        Transfer the hash map to CPU. If the hash map is already on CPU, no copy will be performed.
        """
    def cuda(self, device_id: int = 0) -> HashMap:
        """
        Transfer the hash map to a CUDA device. If the hash map is already on the specified CUDA device, no copy will be performed.
        
        Args:
            device_id (int, optional, default=0): Target CUDA device ID.
        
        Returns:
            open3d.cuda.pybind.core.HashMap
        """
    def erase(self, keys: Tensor) -> Tensor:
        """
        Erase an array of keys stored in Tensors.
        
        Args:
            keys (open3d.cuda.pybind.core.Tensor): Input keys stored in a tensor of shape (N, key_element_shape).
        
        Returns:
            open3d.cuda.pybind.core.Tensor
        """
    def find(self, keys: Tensor) -> tuple:
        """
        Find an array of keys stored in Tensors.
        
        Args:
            keys (open3d.cuda.pybind.core.Tensor): Input keys stored in a tensor of shape (N, key_element_shape).
        
        Returns:
            tuple
        """
    @typing.overload
    def insert(self, keys: Tensor, values: Tensor) -> tuple:
        """
            Insert an array of keys and an array of values stored in Tensors.
        
        Args:
            keys (open3d.cuda.pybind.core.Tensor): Input keys stored in a tensor of shape (N, key_element_shape).
            values (open3d.cuda.pybind.core.Tensor): Input values stored in a tensor of shape (N, value_element_shape).
        
        Returns:
            tuple
        """
    @typing.overload
    def insert(self, keys: Tensor, list_values: list[Tensor]) -> tuple:
        """
            Insert an array of keys and a list of value arrays stored in Tensors.
        
        Args:
            keys (open3d.cuda.pybind.core.Tensor): Input keys stored in a tensor of shape (N, key_element_shape).
            list_values (list[open3d.cuda.pybind.core.Tensor]): List of input values stored in tensors of corresponding shapes.
        
        Returns:
            tuple
        """
    def key_tensor(self) -> Tensor:
        """
        Get the key tensor stored in the buffer.
        """
    def reserve(self, capacity: int) -> None:
        """
        Reserve the hash map given the capacity.
        
        Args:
            capacity (int): New capacity for rehashing.
        
        Returns:
            None
        """
    def save(self, file_name: str) -> None:
        """
        Save the hash map into a .npz file.
        
        Args:
            file_name (str): File name of the corresponding .npz file.
        
        Returns:
            None
        """
    def size(self) -> int:
        """
        Get the size of the hash map.
        """
    def to(self, device: Device, copy: bool = False) -> HashMap:
        """
        Convert the hash map to a selected device.
        
        Args:
            device (open3d.cuda.pybind.core.Device): Compute device to store and operate on the hash container.
            copy (bool, optional, default=False): If true, a new tensor is always created; if false, the copy is avoided when the original tensor already has the targeted dtype.
        
        Returns:
            open3d.cuda.pybind.core.HashMap
        """
    @typing.overload
    def value_tensor(self) -> Tensor:
        """
            Get the value tensor stored at index 0.
        
        Returns:
            open3d.cuda.pybind.core.Tensor
        """
    @typing.overload
    def value_tensor(self, value_buffer_id: int) -> Tensor:
        """
            Get the value tensor stored at index i
        
        Args:
            value_buffer_id (int)
        
        Returns:
            open3d.cuda.pybind.core.Tensor
        """
    def value_tensors(self) -> list[Tensor]:
        """
        Get the list of value tensors stored in the buffer.
        """
    @property
    def device(self) -> Device:
        ...
    @property
    def is_cpu(self) -> bool:
        ...
    @property
    def is_cuda(self) -> bool:
        ...
class HashSet:
    """
    A HashSet is an unordered set of keys wrapped by Tensors.
    """
    @staticmethod
    def load(file_name: str) -> HashSet:
        """
        Load a hash set from a .npz file.
        
        Args:
            file_name (str): File name of the corresponding .npz file.
        
        Returns:
            open3d.cuda.pybind.core.HashSet
        """
    def __init__(self, init_capacity: int, key_dtype: Dtype, key_element_shape: SizeVector, device: Device = ...) -> None:
        """
        Args:
            init_capacity (int): Initial capacity of a hash container.
            key_dtype (open3d.cuda.pybind.core.Dtype): Data type for the input key tensor.
            key_element_shape (open3d.cuda.pybind.core.SizeVector): Element shape for the input key tensor. E.g. (3) for 3D coordinate keys.
            device (open3d.cuda.pybind.core.Device, optional, default=CPU:0): Compute device to store and operate on the hash container.
        """
    def active_buf_indices(self) -> Tensor:
        """
        Get the buffer indices corresponding to active entries in the hash set.
        """
    def capacity(self) -> int:
        """
        Get the capacity of the hash set.
        """
    def clone(self) -> HashSet:
        """
        Clone the hash set, including the data structure and the data buffers.
        """
    def cpu(self) -> HashSet:
        """
        Transfer the hash set to CPU. If the hash set is already on CPU, no copy will be performed.
        """
    def cuda(self, device_id: int = 0) -> HashSet:
        """
        Transfer the hash set to a CUDA device. If the hash set is already on the specified CUDA device, no copy will be performed.
        
        Args:
            device_id (int, optional, default=0): Target CUDA device ID.
        
        Returns:
            open3d.cuda.pybind.core.HashSet
        """
    def erase(self, keys: Tensor) -> Tensor:
        """
        Erase an array of keys stored in Tensors.
        
        Args:
            keys (open3d.cuda.pybind.core.Tensor): Input keys stored in a tensor of shape (N, key_element_shape).
        
        Returns:
            open3d.cuda.pybind.core.Tensor
        """
    def find(self, keys: Tensor) -> tuple:
        """
        Find an array of keys stored in Tensors.
        
        Args:
            keys (open3d.cuda.pybind.core.Tensor): Input keys stored in a tensor of shape (N, key_element_shape).
        
        Returns:
            tuple
        """
    def insert(self, keys: Tensor) -> tuple:
        """
        Insert an array of keys stored in Tensors.
        
        Args:
            keys (open3d.cuda.pybind.core.Tensor): Input keys stored in a tensor of shape (N, key_element_shape).
        
        Returns:
            tuple
        """
    def key_tensor(self) -> Tensor:
        """
        Get the key tensor stored in the buffer.
        """
    def reserve(self, capacity: int) -> None:
        """
        Reserve the hash set given the capacity.
        
        Args:
            capacity (int): New capacity for rehashing.
        
        Returns:
            None
        """
    def save(self, file_name: str) -> None:
        """
        Save the hash set into a .npz file.
        
        Args:
            file_name (str): File name of the corresponding .npz file.
        
        Returns:
            None
        """
    def size(self) -> int:
        """
        Get the size of the hash set.
        """
    def to(self, device: Device, copy: bool = False) -> HashSet:
        """
        Convert the hash set to a selected device.
        
        Args:
            device (open3d.cuda.pybind.core.Device): Compute device to store and operate on the hash container.
            copy (bool, optional, default=False): If true, a new tensor is always created; if false, the copy is avoided when the original tensor already has the targeted dtype.
        
        Returns:
            open3d.cuda.pybind.core.HashSet
        """
    @property
    def device(self) -> Device:
        ...
    @property
    def is_cpu(self) -> bool:
        ...
    @property
    def is_cuda(self) -> bool:
        ...
class Scalar:
    """
    A Scalar can store one of {double, int64, bool}.
    """
    @typing.overload
    def __init__(self, arg0: float) -> None:
        ...
    @typing.overload
    def __init__(self, arg0: float) -> None:
        ...
    @typing.overload
    def __init__(self, arg0: int) -> None:
        ...
    @typing.overload
    def __init__(self, arg0: int) -> None:
        ...
    @typing.overload
    def __init__(self, arg0: int) -> None:
        ...
    @typing.overload
    def __init__(self, arg0: int) -> None:
        ...
    @typing.overload
    def __init__(self, arg0: int) -> None:
        ...
    @typing.overload
    def __init__(self, arg0: int) -> None:
        ...
    @typing.overload
    def __init__(self, arg0: int) -> None:
        ...
    @typing.overload
    def __init__(self, arg0: int) -> None:
        ...
    @typing.overload
    def __init__(self, arg0: bool) -> None:
        ...
class SizeVector:
    """
    A vector of integers for specifying shape, strides, etc.
    """
    __hash__: typing.ClassVar[None] = None
    def __bool__(self) -> bool:
        """
        Check whether the list is nonempty
        """
    def __contains__(self, x: int) -> bool:
        """
        Return true the container contains ``x``
        """
    @typing.overload
    def __delitem__(self, arg0: int) -> None:
        """
        Delete the list elements at index ``i``
        """
    @typing.overload
    def __delitem__(self, arg0: slice) -> None:
        """
        Delete list elements using a slice object
        """
    def __eq__(self, arg0: SizeVector) -> bool:
        ...
    @typing.overload
    def __getitem__(self, s: slice) -> SizeVector:
        """
        Retrieve list elements using a slice object
        """
    @typing.overload
    def __getitem__(self, arg0: int) -> int:
        ...
    @typing.overload
    def __init__(self) -> None:
        ...
    @typing.overload
    def __init__(self, arg0: SizeVector) -> None:
        """
        Copy constructor
        """
    @typing.overload
    def __init__(self, arg0: typing.Iterable) -> None:
        ...
    @typing.overload
    def __init__(self, arg0: int) -> None:
        ...
    def __iter__(self) -> typing.Iterator[int]:
        ...
    def __len__(self) -> int:
        ...
    def __ne__(self, arg0: SizeVector) -> bool:
        ...
    def __repr__(self) -> str:
        """
        Return the canonical string representation of this list.
        """
    @typing.overload
    def __setitem__(self, arg0: int, arg1: int) -> None:
        ...
    @typing.overload
    def __setitem__(self, arg0: slice, arg1: SizeVector) -> None:
        """
        Assign list elements using a slice object
        """
    def append(self, x: int) -> None:
        """
        Add an item to the end of the list
        """
    def clear(self) -> None:
        """
        Clear the contents
        """
    def count(self, x: int) -> int:
        """
        Return the number of times ``x`` appears in the list
        """
    @typing.overload
    def extend(self, L: SizeVector) -> None:
        """
        Extend the list by appending all the items in the given list
        """
    @typing.overload
    def extend(self, L: typing.Iterable) -> None:
        """
        Extend the list by appending all the items in the given list
        """
    def insert(self, i: int, x: int) -> None:
        """
        Insert an item at a given position.
        """
    @typing.overload
    def pop(self) -> int:
        """
        Remove and return the last item
        """
    @typing.overload
    def pop(self, i: int) -> int:
        """
        Remove and return the item at index ``i``
        """
    def remove(self, x: int) -> None:
        """
        Remove the first item from the list whose value is x. It is an error if there is no such item.
        """
class Tensor:
    """
    A Tensor is a view of a data Blob with shape, stride, data_ptr.
    """
    __hash__: typing.ClassVar[None] = None
    @staticmethod
    @typing.overload
    def arange(stop: int, /, *, dtype: Dtype | None = None, device: Device | None = None) -> Tensor:
        """
        Create a 1D tensor with evenly spaced values in the given interval.
        """
    @staticmethod
    @typing.overload
    def arange(start: int, stop: int, step: int | None = None, dtype: Dtype | None = None, *, device: Device | None = None) -> Tensor:
        """
        Create a 1D tensor with evenly spaced values in the given interval.
        """
    @staticmethod
    @typing.overload
    def arange(stop: float, /, *, dtype: Dtype | None = None, device: Device | None = None) -> Tensor:
        """
        Create a 1D tensor with evenly spaced values in the given interval.
        """
    @staticmethod
    @typing.overload
    def arange(start: float, stop: float, step: float | None = None, dtype: Dtype | None = None, *, device: Device | None = None) -> Tensor:
        """
        Create a 1D tensor with evenly spaced values in the given interval.
        """
    @staticmethod
    def diag(arg0: Tensor) -> Tensor:
        ...
    @staticmethod
    def empty(shape: SizeVector, dtype: Dtype | None = None, device: Device | None = None) -> Tensor:
        """
        Create Tensor with a given shape.
        
        Args:
            shape (open3d.cuda.pybind.core.SizeVector): List of Tensor dimensions.
            dtype (Optional[open3d.cuda.pybind.core.Dtype], optional, default=None): Data type for the Tensor.
            device (Optional[open3d.cuda.pybind.core.Device], optional, default=None): Compute device to store and operate on the Tensor.
        
        Returns:
            open3d.cuda.pybind.core.Tensor
        """
    @staticmethod
    def eye(n: int, dtype: Dtype | None = None, device: Device | None = None) -> Tensor:
        """
        Create an identity matrix of size n x n.
        """
    @staticmethod
    def from_dlpack(arg0: capsule) -> Tensor:
        ...
    @staticmethod
    def from_numpy(arg0: numpy.ndarray) -> Tensor:
        ...
    @staticmethod
    @typing.overload
    def full(shape: SizeVector, fill_value: float, dtype: Dtype | None = None, device: Device | None = None) -> Tensor:
        """
        Args:
            shape (open3d.cuda.pybind.core.SizeVector): List of Tensor dimensions.
            fill_value (float): Scalar value to initialize all elements with.
            dtype (Optional[open3d.cuda.pybind.core.Dtype], optional, default=None): Data type for the Tensor.
            device (Optional[open3d.cuda.pybind.core.Device], optional, default=None): Compute device to store and operate on the Tensor.
        
        Returns:
            open3d.cuda.pybind.core.Tensor
        """
    @staticmethod
    @typing.overload
    def full(shape: SizeVector, fill_value: float, dtype: Dtype | None = None, device: Device | None = None) -> Tensor:
        """
        Args:
            shape (open3d.cuda.pybind.core.SizeVector): List of Tensor dimensions.
            fill_value (float): Scalar value to initialize all elements with.
            dtype (Optional[open3d.cuda.pybind.core.Dtype], optional, default=None): Data type for the Tensor.
            device (Optional[open3d.cuda.pybind.core.Device], optional, default=None): Compute device to store and operate on the Tensor.
        
        Returns:
            open3d.cuda.pybind.core.Tensor
        """
    @staticmethod
    @typing.overload
    def full(shape: SizeVector, fill_value: int, dtype: Dtype | None = None, device: Device | None = None) -> Tensor:
        """
        Args:
            shape (open3d.cuda.pybind.core.SizeVector): List of Tensor dimensions.
            fill_value (int): Scalar value to initialize all elements with.
            dtype (Optional[open3d.cuda.pybind.core.Dtype], optional, default=None): Data type for the Tensor.
            device (Optional[open3d.cuda.pybind.core.Device], optional, default=None): Compute device to store and operate on the Tensor.
        
        Returns:
            open3d.cuda.pybind.core.Tensor
        """
    @staticmethod
    @typing.overload
    def full(shape: SizeVector, fill_value: int, dtype: Dtype | None = None, device: Device | None = None) -> Tensor:
        """
        Args:
            shape (open3d.cuda.pybind.core.SizeVector): List of Tensor dimensions.
            fill_value (int): Scalar value to initialize all elements with.
            dtype (Optional[open3d.cuda.pybind.core.Dtype], optional, default=None): Data type for the Tensor.
            device (Optional[open3d.cuda.pybind.core.Device], optional, default=None): Compute device to store and operate on the Tensor.
        
        Returns:
            open3d.cuda.pybind.core.Tensor
        """
    @staticmethod
    @typing.overload
    def full(shape: SizeVector, fill_value: int, dtype: Dtype | None = None, device: Device | None = None) -> Tensor:
        """
        Args:
            shape (open3d.cuda.pybind.core.SizeVector): List of Tensor dimensions.
            fill_value (int): Scalar value to initialize all elements with.
            dtype (Optional[open3d.cuda.pybind.core.Dtype], optional, default=None): Data type for the Tensor.
            device (Optional[open3d.cuda.pybind.core.Device], optional, default=None): Compute device to store and operate on the Tensor.
        
        Returns:
            open3d.cuda.pybind.core.Tensor
        """
    @staticmethod
    @typing.overload
    def full(shape: SizeVector, fill_value: int, dtype: Dtype | None = None, device: Device | None = None) -> Tensor:
        """
        Args:
            shape (open3d.cuda.pybind.core.SizeVector): List of Tensor dimensions.
            fill_value (int): Scalar value to initialize all elements with.
            dtype (Optional[open3d.cuda.pybind.core.Dtype], optional, default=None): Data type for the Tensor.
            device (Optional[open3d.cuda.pybind.core.Device], optional, default=None): Compute device to store and operate on the Tensor.
        
        Returns:
            open3d.cuda.pybind.core.Tensor
        """
    @staticmethod
    @typing.overload
    def full(shape: SizeVector, fill_value: int, dtype: Dtype | None = None, device: Device | None = None) -> Tensor:
        """
        Args:
            shape (open3d.cuda.pybind.core.SizeVector): List of Tensor dimensions.
            fill_value (int): Scalar value to initialize all elements with.
            dtype (Optional[open3d.cuda.pybind.core.Dtype], optional, default=None): Data type for the Tensor.
            device (Optional[open3d.cuda.pybind.core.Device], optional, default=None): Compute device to store and operate on the Tensor.
        
        Returns:
            open3d.cuda.pybind.core.Tensor
        """
    @staticmethod
    @typing.overload
    def full(shape: SizeVector, fill_value: int, dtype: Dtype | None = None, device: Device | None = None) -> Tensor:
        """
        Args:
            shape (open3d.cuda.pybind.core.SizeVector): List of Tensor dimensions.
            fill_value (int): Scalar value to initialize all elements with.
            dtype (Optional[open3d.cuda.pybind.core.Dtype], optional, default=None): Data type for the Tensor.
            device (Optional[open3d.cuda.pybind.core.Device], optional, default=None): Compute device to store and operate on the Tensor.
        
        Returns:
            open3d.cuda.pybind.core.Tensor
        """
    @staticmethod
    @typing.overload
    def full(shape: SizeVector, fill_value: int, dtype: Dtype | None = None, device: Device | None = None) -> Tensor:
        """
        Args:
            shape (open3d.cuda.pybind.core.SizeVector): List of Tensor dimensions.
            fill_value (int): Scalar value to initialize all elements with.
            dtype (Optional[open3d.cuda.pybind.core.Dtype], optional, default=None): Data type for the Tensor.
            device (Optional[open3d.cuda.pybind.core.Device], optional, default=None): Compute device to store and operate on the Tensor.
        
        Returns:
            open3d.cuda.pybind.core.Tensor
        """
    @staticmethod
    @typing.overload
    def full(shape: SizeVector, fill_value: int, dtype: Dtype | None = None, device: Device | None = None) -> Tensor:
        """
        Args:
            shape (open3d.cuda.pybind.core.SizeVector): List of Tensor dimensions.
            fill_value (int): Scalar value to initialize all elements with.
            dtype (Optional[open3d.cuda.pybind.core.Dtype], optional, default=None): Data type for the Tensor.
            device (Optional[open3d.cuda.pybind.core.Device], optional, default=None): Compute device to store and operate on the Tensor.
        
        Returns:
            open3d.cuda.pybind.core.Tensor
        """
    @staticmethod
    @typing.overload
    def full(shape: SizeVector, fill_value: bool, dtype: Dtype | None = None, device: Device | None = None) -> Tensor:
        """
        Args:
            shape (open3d.cuda.pybind.core.SizeVector): List of Tensor dimensions.
            fill_value (bool): Scalar value to initialize all elements with.
            dtype (Optional[open3d.cuda.pybind.core.Dtype], optional, default=None): Data type for the Tensor.
            device (Optional[open3d.cuda.pybind.core.Device], optional, default=None): Compute device to store and operate on the Tensor.
        
        Returns:
            open3d.cuda.pybind.core.Tensor
        """
    @staticmethod
    def load(file_name: str) -> Tensor:
        """
        Load tensor from Numpy's npy format.
        """
    @staticmethod
    def ones(shape: SizeVector, dtype: Dtype | None = None, device: Device | None = None) -> Tensor:
        """
        Create Tensor with a given shape.
        
        Args:
            shape (open3d.cuda.pybind.core.SizeVector): List of Tensor dimensions.
            dtype (Optional[open3d.cuda.pybind.core.Dtype], optional, default=None): Data type for the Tensor.
            device (Optional[open3d.cuda.pybind.core.Device], optional, default=None): Compute device to store and operate on the Tensor.
        
        Returns:
            open3d.cuda.pybind.core.Tensor
        """
    @staticmethod
    @typing.overload
    def to(*args, **kwargs) -> Tensor:
        """
        Args:
            dtype (open3d.cuda.pybind.core.Dtype): Data type for the Tensor.
            copy (bool, optional, default=False): If true, a new tensor is always created; if false, the copy is avoided when the original tensor already has the targeted dtype.
        
        Returns:
            open3d.cuda.pybind.core.Tensor
        """
    @staticmethod
    def zeros(shape: SizeVector, dtype: Dtype | None = None, device: Device | None = None) -> Tensor:
        """
        Create Tensor with a given shape.
        
        Args:
            shape (open3d.cuda.pybind.core.SizeVector): List of Tensor dimensions.
            dtype (Optional[open3d.cuda.pybind.core.Dtype], optional, default=None): Data type for the Tensor.
            device (Optional[open3d.cuda.pybind.core.Device], optional, default=None): Compute device to store and operate on the Tensor.
        
        Returns:
            open3d.cuda.pybind.core.Tensor
        """
    def T(self) -> Tensor:
        """
        Transpose <=2-D tensor by swapping dimension 0 and 1.0-D and 1-D Tensor remains the same.
        """
    @typing.overload
    def __add__(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def __add__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __add__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __add__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __add__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __add__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __add__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __add__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __add__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __add__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __add__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __add__(self, arg0: bool) -> Tensor:
        ...
    @typing.overload
    def __and__(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def __and__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __and__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __and__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __and__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __and__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __and__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __and__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __and__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __and__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __and__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __and__(self, arg0: bool) -> Tensor:
        ...
    def __bool__(self) -> bool:
        ...
    @typing.overload
    def __div__(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def __div__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __div__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __div__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __div__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __div__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __div__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __div__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __div__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __div__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __div__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __div__(self, arg0: bool) -> Tensor:
        ...
    @typing.overload
    def __eq__(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def __eq__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __eq__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __eq__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __eq__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __eq__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __eq__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __eq__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __eq__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __eq__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __eq__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __eq__(self, arg0: bool) -> Tensor:
        ...
    @typing.overload
    def __floordiv__(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def __floordiv__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __floordiv__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __floordiv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __floordiv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __floordiv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __floordiv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __floordiv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __floordiv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __floordiv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __floordiv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __floordiv__(self, arg0: bool) -> Tensor:
        ...
    @typing.overload
    def __ge__(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def __ge__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __ge__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __ge__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ge__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ge__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ge__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ge__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ge__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ge__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ge__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ge__(self, arg0: bool) -> Tensor:
        ...
    @typing.overload
    def __getitem__(self, arg0: bool) -> Tensor:
        ...
    @typing.overload
    def __getitem__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __getitem__(self, arg0: slice) -> Tensor:
        ...
    @typing.overload
    def __getitem__(self, arg0: numpy.ndarray) -> Tensor:
        ...
    @typing.overload
    def __getitem__(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def __getitem__(self, arg0: list) -> Tensor:
        ...
    @typing.overload
    def __getitem__(self, arg0: tuple) -> Tensor:
        ...
    def __getstate__(self) -> tuple:
        ...
    @typing.overload
    def __gt__(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def __gt__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __gt__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __gt__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __gt__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __gt__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __gt__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __gt__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __gt__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __gt__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __gt__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __gt__(self, arg0: bool) -> Tensor:
        ...
    @typing.overload
    def __iadd__(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def __iadd__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __iadd__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __iadd__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __iadd__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __iadd__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __iadd__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __iadd__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __iadd__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __iadd__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __iadd__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __iadd__(self, arg0: bool) -> Tensor:
        ...
    @typing.overload
    def __iand__(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def __iand__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __iand__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __iand__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __iand__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __iand__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __iand__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __iand__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __iand__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __iand__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __iand__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __iand__(self, arg0: bool) -> Tensor:
        ...
    @typing.overload
    def __idiv__(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def __idiv__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __idiv__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __idiv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __idiv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __idiv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __idiv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __idiv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __idiv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __idiv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __idiv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __idiv__(self, arg0: bool) -> Tensor:
        ...
    @typing.overload
    def __ifloordiv__(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def __ifloordiv__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __ifloordiv__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __ifloordiv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ifloordiv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ifloordiv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ifloordiv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ifloordiv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ifloordiv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ifloordiv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ifloordiv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ifloordiv__(self, arg0: bool) -> Tensor:
        ...
    @typing.overload
    def __imul__(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def __imul__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __imul__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __imul__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __imul__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __imul__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __imul__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __imul__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __imul__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __imul__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __imul__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __imul__(self, arg0: bool) -> Tensor:
        ...
    @typing.overload
    def __init__(self, np_array: numpy.ndarray, dtype: Dtype | None = None, device: Device | None = None) -> None:
        """
            Initialize Tensor from a Numpy array.
        
        Args:
            np_array (numpy.ndarray)
            dtype (Optional[open3d.cuda.pybind.core.Dtype], optional, default=None): Data type for the Tensor.
            device (Optional[open3d.cuda.pybind.core.Device], optional, default=None): Compute device to store and operate on the Tensor.
        """
    @typing.overload
    def __init__(self, scalar_value: bool, dtype: Dtype | None = None, device: Device | None = None) -> None:
        """
        Args:
            scalar_value (bool): Initial value for the single element tensor.
            dtype (Optional[open3d.cuda.pybind.core.Dtype], optional, default=None): Data type for the Tensor.
            device (Optional[open3d.cuda.pybind.core.Device], optional, default=None): Compute device to store and operate on the Tensor.
        """
    @typing.overload
    def __init__(self, scalar_value: int, dtype: Dtype | None = None, device: Device | None = None) -> None:
        """
        Args:
            scalar_value (int): Initial value for the single element tensor.
            dtype (Optional[open3d.cuda.pybind.core.Dtype], optional, default=None): Data type for the Tensor.
            device (Optional[open3d.cuda.pybind.core.Device], optional, default=None): Compute device to store and operate on the Tensor.
        """
    @typing.overload
    def __init__(self, scalar_value: float, dtype: Dtype | None = None, device: Device | None = None) -> None:
        """
        Args:
            scalar_value (float): Initial value for the single element tensor.
            dtype (Optional[open3d.cuda.pybind.core.Dtype], optional, default=None): Data type for the Tensor.
            device (Optional[open3d.cuda.pybind.core.Device], optional, default=None): Compute device to store and operate on the Tensor.
        """
    @typing.overload
    def __init__(self, shape: list, dtype: Dtype | None = None, device: Device | None = None) -> None:
        """
            Initialize Tensor from a nested list.
        
        Args:
            shape (list): List of Tensor dimensions.
            dtype (Optional[open3d.cuda.pybind.core.Dtype], optional, default=None): Data type for the Tensor.
            device (Optional[open3d.cuda.pybind.core.Device], optional, default=None): Compute device to store and operate on the Tensor.
        """
    @typing.overload
    def __init__(self, shape: tuple, dtype: Dtype | None = None, device: Device | None = None) -> None:
        """
            Initialize Tensor from a nested tuple.
        
        Args:
            shape (tuple): List of Tensor dimensions.
            dtype (Optional[open3d.cuda.pybind.core.Dtype], optional, default=None): Data type for the Tensor.
            device (Optional[open3d.cuda.pybind.core.Device], optional, default=None): Compute device to store and operate on the Tensor.
        """
    @typing.overload
    def __ior__(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def __ior__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __ior__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __ior__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ior__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ior__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ior__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ior__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ior__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ior__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ior__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ior__(self, arg0: bool) -> Tensor:
        ...
    @typing.overload
    def __isub__(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def __isub__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __isub__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __isub__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __isub__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __isub__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __isub__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __isub__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __isub__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __isub__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __isub__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __isub__(self, arg0: bool) -> Tensor:
        ...
    def __iter__(self) -> typing.Iterator[Tensor]:
        ...
    @typing.overload
    def __itruediv__(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def __itruediv__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __itruediv__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __itruediv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __itruediv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __itruediv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __itruediv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __itruediv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __itruediv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __itruediv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __itruediv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __itruediv__(self, arg0: bool) -> Tensor:
        ...
    @typing.overload
    def __ixor__(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def __ixor__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __ixor__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __ixor__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ixor__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ixor__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ixor__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ixor__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ixor__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ixor__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ixor__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ixor__(self, arg0: bool) -> Tensor:
        ...
    @typing.overload
    def __le__(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def __le__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __le__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __le__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __le__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __le__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __le__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __le__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __le__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __le__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __le__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __le__(self, arg0: bool) -> Tensor:
        ...
    def __len__(self) -> int:
        ...
    @typing.overload
    def __lt__(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def __lt__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __lt__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __lt__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __lt__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __lt__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __lt__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __lt__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __lt__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __lt__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __lt__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __lt__(self, arg0: bool) -> Tensor:
        ...
    def __matmul__(self, arg0: Tensor) -> Tensor:
        """
        Computes matrix multiplication of a 2D tensor with another tensor of compatible shape.
        """
    @typing.overload
    def __mul__(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def __mul__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __mul__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __mul__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __mul__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __mul__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __mul__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __mul__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __mul__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __mul__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __mul__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __mul__(self, arg0: bool) -> Tensor:
        ...
    @typing.overload
    def __ne__(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def __ne__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __ne__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __ne__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ne__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ne__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ne__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ne__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ne__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ne__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ne__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ne__(self, arg0: bool) -> Tensor:
        ...
    def __neg__(self) -> Tensor:
        ...
    @typing.overload
    def __or__(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def __or__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __or__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __or__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __or__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __or__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __or__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __or__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __or__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __or__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __or__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __or__(self, arg0: bool) -> Tensor:
        ...
    @typing.overload
    def __radd__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __radd__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __radd__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __radd__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __radd__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __radd__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __radd__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __radd__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __radd__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __radd__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __radd__(self, arg0: bool) -> Tensor:
        ...
    @typing.overload
    def __rand__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __rand__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __rand__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rand__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rand__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rand__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rand__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rand__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rand__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rand__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rand__(self, arg0: bool) -> Tensor:
        ...
    @typing.overload
    def __rdiv__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __rdiv__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __rdiv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rdiv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rdiv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rdiv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rdiv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rdiv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rdiv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rdiv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rdiv__(self, arg0: bool) -> Tensor:
        ...
    def __repr__(self) -> str:
        ...
    @typing.overload
    def __rfloordiv__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __rfloordiv__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __rfloordiv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rfloordiv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rfloordiv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rfloordiv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rfloordiv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rfloordiv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rfloordiv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rfloordiv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rfloordiv__(self, arg0: bool) -> Tensor:
        ...
    @typing.overload
    def __rmul__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __rmul__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __rmul__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rmul__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rmul__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rmul__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rmul__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rmul__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rmul__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rmul__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rmul__(self, arg0: bool) -> Tensor:
        ...
    @typing.overload
    def __ror__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __ror__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __ror__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ror__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ror__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ror__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ror__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ror__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ror__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ror__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __ror__(self, arg0: bool) -> Tensor:
        ...
    @typing.overload
    def __rsub__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __rsub__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __rsub__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rsub__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rsub__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rsub__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rsub__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rsub__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rsub__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rsub__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rsub__(self, arg0: bool) -> Tensor:
        ...
    @typing.overload
    def __rtruediv__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __rtruediv__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __rtruediv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rtruediv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rtruediv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rtruediv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rtruediv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rtruediv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rtruediv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rtruediv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rtruediv__(self, arg0: bool) -> Tensor:
        ...
    @typing.overload
    def __rxor__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __rxor__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __rxor__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rxor__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rxor__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rxor__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rxor__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rxor__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rxor__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rxor__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __rxor__(self, arg0: bool) -> Tensor:
        ...
    @typing.overload
    def __setitem__(self, arg0: bool, arg1: typing.Any) -> Tensor:
        ...
    @typing.overload
    def __setitem__(self, arg0: int, arg1: typing.Any) -> Tensor:
        ...
    @typing.overload
    def __setitem__(self, arg0: slice, arg1: typing.Any) -> Tensor:
        ...
    @typing.overload
    def __setitem__(self, arg0: numpy.ndarray, arg1: typing.Any) -> Tensor:
        ...
    @typing.overload
    def __setitem__(self, arg0: Tensor, arg1: typing.Any) -> Tensor:
        ...
    @typing.overload
    def __setitem__(self, arg0: list, arg1: typing.Any) -> Tensor:
        ...
    @typing.overload
    def __setitem__(self, arg0: tuple, arg1: typing.Any) -> Tensor:
        ...
    def __setstate__(self, arg0: tuple) -> None:
        ...
    def __str__(self) -> str:
        ...
    @typing.overload
    def __sub__(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def __sub__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __sub__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __sub__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __sub__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __sub__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __sub__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __sub__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __sub__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __sub__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __sub__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __sub__(self, arg0: bool) -> Tensor:
        ...
    @typing.overload
    def __truediv__(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def __truediv__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __truediv__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __truediv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __truediv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __truediv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __truediv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __truediv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __truediv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __truediv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __truediv__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __truediv__(self, arg0: bool) -> Tensor:
        ...
    @typing.overload
    def __xor__(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def __xor__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __xor__(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def __xor__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __xor__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __xor__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __xor__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __xor__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __xor__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __xor__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __xor__(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def __xor__(self, arg0: bool) -> Tensor:
        ...
    def abs(self) -> Tensor:
        ...
    def abs_(self) -> Tensor:
        ...
    @typing.overload
    def add(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def add(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def add(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def add(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def add(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def add(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def add(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def add(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def add(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def add(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def add(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def add(self, arg0: bool) -> Tensor:
        ...
    @typing.overload
    def add_(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def add_(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def add_(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def add_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def add_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def add_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def add_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def add_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def add_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def add_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def add_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def add_(self, arg0: bool) -> Tensor:
        ...
    def all(self, dim: SizeVector | None = None, keepdim: bool = False) -> Tensor:
        """
        Returns true if all elements in the tensor are true. Only works for boolean tensors.
        """
    def allclose(self, other: Tensor, rtol: float = 1e-05, atol: float = 1e-08) -> bool:
        """
        Returns true if the two tensors are element-wise equal within a tolerance.
        
        - If the ``device`` is not the same: throws exception.
        - If the ``dtype`` is not the same: throws exception.
        - If the ``shape`` is not the same: returns false.
        - Returns true if: ``abs(self - other) <= (atol + rtol * abs(other)``).
        
        The equation is not symmetrical, i.e. ``a.allclose(b)`` might not be the same
        as ``b.allclose(a)``. Also see `Numpy's documentation <https://numpy.org/doc/stable/reference/generated/numpy.allclose.html>`__.
        
        TODO:
        	Support nan.
        
        Args:
            other (open3d.cuda.pybind.core.Tensor): The other tensor to compare with.
            rtol (float, optional, default=1e-05): Relative tolerance.
            atol (float, optional, default=1e-08): Absolute tolerance.
        
        Returns:
            bool
        """
    def any(self, dim: SizeVector | None = None, keepdim: bool = False) -> Tensor:
        """
        Returns true if any elements in the tensor are true. Only works for boolean tensors.
        """
    def append(self, values: Tensor, axis: int | None = None) -> Tensor:
        """
        Appends the `values` tensor, along the given axis and returns
        a copy of the original tensor. Both the tensors must have same data-type
        device, and number of dimensions. All dimensions must be the same, except the
        dimension along the axis the tensors are to be appended.
        
        This is the similar to NumPy's semantics:
        - https://numpy.org/doc/stable/reference/generated/numpy.append.html
        
        Returns:
            A copy of the tensor with `values` appended to axis. Note that append
            does not occur in-place: a new array is allocated and filled. If axis
            is None, out is a flattened tensor.
        
        Example:
            >>> a = o3d.core.Tensor([[0, 1], [2, 3]])
            >>> b = o3d.core.Tensor([[4, 5]])
            >>> a.append(b, axis = 0)
            [[0 1],
             [2 3],
             [4 5]]
            Tensor[shape={3, 2}, stride={2, 1}, Int64, CPU:0, 0x55555abc6b00]
        
            >>> a.append(b)
            [0 1 2 3 4 5]
            Tensor[shape={6}, stride={1}, Int64, CPU:0, 0x55555abc6b70]
        """
    def argmax(self, dim: SizeVector | None = None) -> Tensor:
        ...
    def argmin(self, dim: SizeVector | None = None) -> Tensor:
        ...
    def ceil(self) -> Tensor:
        ...
    @typing.overload
    def clip(self, arg0: float, arg1: float) -> Tensor:
        ...
    @typing.overload
    def clip(self, arg0: float, arg1: float) -> Tensor:
        ...
    @typing.overload
    def clip(self, arg0: int, arg1: int) -> Tensor:
        ...
    @typing.overload
    def clip(self, arg0: int, arg1: int) -> Tensor:
        ...
    @typing.overload
    def clip(self, arg0: int, arg1: int) -> Tensor:
        ...
    @typing.overload
    def clip(self, arg0: int, arg1: int) -> Tensor:
        ...
    @typing.overload
    def clip(self, arg0: int, arg1: int) -> Tensor:
        ...
    @typing.overload
    def clip(self, arg0: int, arg1: int) -> Tensor:
        ...
    @typing.overload
    def clip(self, arg0: int, arg1: int) -> Tensor:
        ...
    @typing.overload
    def clip(self, arg0: int, arg1: int) -> Tensor:
        ...
    @typing.overload
    def clip(self, arg0: bool, arg1: bool) -> Tensor:
        ...
    @typing.overload
    def clip_(self, arg0: float, arg1: float) -> Tensor:
        ...
    @typing.overload
    def clip_(self, arg0: float, arg1: float) -> Tensor:
        ...
    @typing.overload
    def clip_(self, arg0: int, arg1: int) -> Tensor:
        ...
    @typing.overload
    def clip_(self, arg0: int, arg1: int) -> Tensor:
        ...
    @typing.overload
    def clip_(self, arg0: int, arg1: int) -> Tensor:
        ...
    @typing.overload
    def clip_(self, arg0: int, arg1: int) -> Tensor:
        ...
    @typing.overload
    def clip_(self, arg0: int, arg1: int) -> Tensor:
        ...
    @typing.overload
    def clip_(self, arg0: int, arg1: int) -> Tensor:
        ...
    @typing.overload
    def clip_(self, arg0: int, arg1: int) -> Tensor:
        ...
    @typing.overload
    def clip_(self, arg0: int, arg1: int) -> Tensor:
        ...
    @typing.overload
    def clip_(self, arg0: bool, arg1: bool) -> Tensor:
        ...
    def clone(self) -> Tensor:
        """
        Copy Tensor to the same device.
        """
    def contiguous(self) -> Tensor:
        """
        Returns a contiguous tensor containing the same data in the same device.  If the tensor is already contiguous, the same underlying memory will be used.
        """
    def cos(self) -> Tensor:
        ...
    def cos_(self) -> Tensor:
        ...
    def cpu(self) -> Tensor:
        """
        Transfer the tensor to CPU. If the tensor is already on CPU, no copy will be performed.
        """
    def cuda(self, device_id: int = 0) -> Tensor:
        """
        Transfer the tensor to a CUDA device. If the tensor is already on the specified CUDA device, no copy will be performed.
        """
    def det(self) -> float:
        """
        Compute the determinant of a 2D square tensor.
        """
    @typing.overload
    def div(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def div(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def div(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def div(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def div(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def div(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def div(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def div(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def div(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def div(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def div(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def div(self, arg0: bool) -> Tensor:
        ...
    @typing.overload
    def div_(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def div_(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def div_(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def div_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def div_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def div_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def div_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def div_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def div_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def div_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def div_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def div_(self, arg0: bool) -> Tensor:
        ...
    @typing.overload
    def eq(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def eq(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def eq(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def eq(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def eq(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def eq(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def eq(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def eq(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def eq(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def eq(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def eq(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def eq(self, arg0: bool) -> Tensor:
        ...
    @typing.overload
    def eq_(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def eq_(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def eq_(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def eq_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def eq_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def eq_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def eq_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def eq_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def eq_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def eq_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def eq_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def eq_(self, arg0: bool) -> Tensor:
        ...
    def exp(self) -> Tensor:
        ...
    def exp_(self) -> Tensor:
        ...
    def flatten(self, start_dim: int = 0, end_dim: int = -1) -> Tensor:
        """
        Flattens input by reshaping it into a one-dimensional tensor. If
        start_dim or end_dim are passed, only dimensions starting with start_dim
        and ending with end_dim are flattened. The order of elements in input is
        unchanged.
        
        Unlike NumPy’s flatten, which always copies input’s data, this function
        may return the original object, a view, or copy. If no dimensions are
        flattened, then the original object input is returned. Otherwise, if
        input can be viewed as the flattened shape, then that view is returned.
        Finally, only if the input cannot be viewed as the flattened shape is
        input’s data copied.
        
        Ref:
        - https://pytorch.org/docs/stable/tensors.html
        - aten/src/ATen/native/TensorShape.cpp
        - aten/src/ATen/TensorUtils.cpp
        
        Args:
            start_dim (int, optional, default=0): The first dimension to flatten (inclusive).
            end_dim (int, optional, default=-1): The last dimension to flatten, starting from start_dim (inclusive).
        
        Returns:
            open3d.cuda.pybind.core.Tensor
        """
    def floor(self) -> Tensor:
        ...
    @typing.overload
    def ge(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def ge(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def ge(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def ge(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def ge(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def ge(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def ge(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def ge(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def ge(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def ge(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def ge(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def ge(self, arg0: bool) -> Tensor:
        ...
    @typing.overload
    def ge_(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def ge_(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def ge_(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def ge_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def ge_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def ge_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def ge_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def ge_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def ge_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def ge_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def ge_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def ge_(self, arg0: bool) -> Tensor:
        ...
    @typing.overload
    def gt(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def gt(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def gt(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def gt(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def gt(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def gt(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def gt(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def gt(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def gt(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def gt(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def gt(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def gt(self, arg0: bool) -> Tensor:
        ...
    @typing.overload
    def gt_(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def gt_(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def gt_(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def gt_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def gt_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def gt_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def gt_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def gt_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def gt_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def gt_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def gt_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def gt_(self, arg0: bool) -> Tensor:
        ...
    def inv(self) -> Tensor:
        """
        Computes the matrix inverse of the square matrix self with LU factorization and returns the result.
        """
    def is_contiguous(self) -> bool:
        """
        Returns True if the underlying memory buffer is contiguous.
        """
    def isclose(self, other: Tensor, rtol: float = 1e-05, atol: float = 1e-08) -> Tensor:
        """
        Element-wise version of ``tensor.allclose``.
        
        - If the ``device`` is not the same: throws exception.
        - If the ``dtype`` is not the same: throws exception.
        - If the ``shape`` is not the same: throws exception.
        - For each element in the returned tensor:
          ``abs(self - other) <= (atol + rtol * abs(other))``.
        
        The equation is not symmetrical, i.e. a.is_close(b) might not be the same
        as b.is_close(a). Also see `Numpy's documentation <https://numpy.org/doc/stable/reference/generated/numpy.isclose.html>`__.
        
        TODO:
            Support nan.
        
        Returns:
            A boolean tensor indicating where the tensor is close.
        
        Args:
            other (open3d.cuda.pybind.core.Tensor): The other tensor to compare with.
            rtol (float, optional, default=1e-05): Relative tolerance.
            atol (float, optional, default=1e-08): Absolute tolerance.
        
        Returns:
            open3d.cuda.pybind.core.Tensor
        """
    def isfinite(self) -> Tensor:
        ...
    def isinf(self) -> Tensor:
        ...
    def isnan(self) -> Tensor:
        ...
    def issame(self, arg0: Tensor) -> bool:
        """
        Returns true iff the tensor is the other tensor. This means that, the two tensors have the same underlying memory, device, dtype, shape, strides and etc.
        """
    def item(self) -> typing.Any:
        """
        Helper function to return the scalar value of a scalar tensor. The tensor must be 0 - dimensional (i.e. have an empty shape).
        """
    @typing.overload
    def le(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def le(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def le(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def le(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def le(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def le(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def le(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def le(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def le(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def le(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def le(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def le(self, arg0: bool) -> Tensor:
        ...
    @typing.overload
    def le_(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def le_(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def le_(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def le_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def le_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def le_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def le_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def le_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def le_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def le_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def le_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def le_(self, arg0: bool) -> Tensor:
        ...
    @typing.overload
    def logical_and(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def logical_and(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def logical_and(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def logical_and(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_and(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_and(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_and(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_and(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_and(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_and(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_and(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_and(self, arg0: bool) -> Tensor:
        ...
    @typing.overload
    def logical_and_(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def logical_and_(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def logical_and_(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def logical_and_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_and_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_and_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_and_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_and_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_and_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_and_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_and_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_and_(self, arg0: bool) -> Tensor:
        ...
    def logical_not(self) -> Tensor:
        ...
    def logical_not_(self) -> Tensor:
        ...
    @typing.overload
    def logical_or(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def logical_or(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def logical_or(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def logical_or(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_or(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_or(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_or(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_or(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_or(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_or(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_or(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_or(self, arg0: bool) -> Tensor:
        ...
    @typing.overload
    def logical_or_(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def logical_or_(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def logical_or_(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def logical_or_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_or_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_or_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_or_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_or_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_or_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_or_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_or_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_or_(self, arg0: bool) -> Tensor:
        ...
    @typing.overload
    def logical_xor(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def logical_xor(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def logical_xor(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def logical_xor(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_xor(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_xor(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_xor(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_xor(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_xor(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_xor(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_xor(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_xor(self, arg0: bool) -> Tensor:
        ...
    @typing.overload
    def logical_xor_(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def logical_xor_(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def logical_xor_(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def logical_xor_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_xor_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_xor_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_xor_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_xor_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_xor_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_xor_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_xor_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def logical_xor_(self, arg0: bool) -> Tensor:
        ...
    def lstsq(self, B: Tensor) -> Tensor:
        """
        Solves the linear system AX = B with QR decomposition and returns X. A is a (m, n) matrix with m >= n.
        """
    @typing.overload
    def lt(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def lt(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def lt(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def lt(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def lt(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def lt(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def lt(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def lt(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def lt(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def lt(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def lt(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def lt(self, arg0: bool) -> Tensor:
        ...
    @typing.overload
    def lt_(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def lt_(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def lt_(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def lt_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def lt_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def lt_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def lt_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def lt_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def lt_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def lt_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def lt_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def lt_(self, arg0: bool) -> Tensor:
        ...
    def lu(self, permute_l: bool = False) -> tuple[Tensor, Tensor, Tensor]:
        """
        Computes LU factorisation of the 2D square tensor, using A = P * L * U;
        where P is the permutation matrix, L is the lower-triangular matrix with
        diagonal elements as 1.0 and U is the upper-triangular matrix, and returns
        tuple (P, L, U).
        
        Returns:
            Tuple (P, L, U).
        
        Args:
            permute_l (bool, optional, default=False): If True, returns L as P * L.
        
        Returns:
            tuple[open3d.cuda.pybind.core.Tensor, open3d.cuda.pybind.core.Tensor, open3d.cuda.pybind.core.Tensor]
        """
    def lu_ipiv(self) -> tuple[Tensor, Tensor]:
        """
        Computes LU factorisation of the 2D square tensor, using A = P * L * U;
        where P is the permutation matrix, L is the lower-triangular matrix with
        diagonal elements as 1.0 and U is the upper-triangular matrix, and returns
        tuple `output` tensor of shape {n,n} and `ipiv` tensor of shape {n}, where
        {n,n} is the shape of input tensor.
        
        Returns:
            ipiv: ipiv is a 1D integer pivot indices tensor. It contains the pivot
                indices, indicating row i of the matrix was interchanged with row
                ipiv[i]
            output: It has L as lower triangular values and U as upper triangle
                values including the main diagonal (diagonal elements of L to be
                taken as unity).
        
        Example:
            >>> ipiv, output = a.lu_ipiv()
        """
    def matmul(self, arg0: Tensor) -> Tensor:
        """
        Computes matrix multiplication of a 2D tensor with another tensor of compatible shape.
        """
    def max(self, dim: SizeVector | None = None, keepdim: bool = False) -> Tensor:
        ...
    def mean(self, dim: SizeVector | None = None, keepdim: bool = False) -> Tensor:
        ...
    def min(self, dim: SizeVector | None = None, keepdim: bool = False) -> Tensor:
        ...
    @typing.overload
    def mul(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def mul(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def mul(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def mul(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def mul(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def mul(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def mul(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def mul(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def mul(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def mul(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def mul(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def mul(self, arg0: bool) -> Tensor:
        ...
    @typing.overload
    def mul_(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def mul_(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def mul_(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def mul_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def mul_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def mul_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def mul_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def mul_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def mul_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def mul_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def mul_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def mul_(self, arg0: bool) -> Tensor:
        ...
    @typing.overload
    def ne(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def ne(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def ne(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def ne(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def ne(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def ne(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def ne(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def ne(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def ne(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def ne(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def ne(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def ne(self, arg0: bool) -> Tensor:
        ...
    @typing.overload
    def ne_(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def ne_(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def ne_(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def ne_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def ne_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def ne_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def ne_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def ne_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def ne_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def ne_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def ne_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def ne_(self, arg0: bool) -> Tensor:
        ...
    def neg(self) -> Tensor:
        ...
    def neg_(self) -> Tensor:
        ...
    def nonzero(self, as_tuple: bool = False) -> typing.Any:
        """
        Find the indices of the elements that are non-zero.
        
        Args:
            as_tuple (bool, optional, default=False): If ``as_tuple`` is True, returns an int64 tensor of shape {num_dims, num_non_zeros}, where the i-th row contains the indices of the non-zero elements in i-th dimension of the original tensor. If ``as_tuple`` is False, Returns a vector of int64 Tensors, each containing the indices of the non-zero elements in each dimension.
        
        Returns:
            object
        """
    def num_elements(self) -> int:
        ...
    def numpy(self) -> numpy.ndarray:
        ...
    def prod(self, dim: SizeVector | None = None, keepdim: bool = False) -> Tensor:
        ...
    def reshape(self, dst_shape: SizeVector) -> Tensor:
        """
        Returns a tensor with the same data and number of elements as input, but
        with the specified shape. When possible, the returned tensor will be a view of
        input. Otherwise, it will be a copy.
        
        Contiguous inputs and inputs with compatible strides can be reshaped
        without copying, but you should not depend on the copying vs. viewing
        behavior.
        
        Ref:
        - https://pytorch.org/docs/stable/tensors.html
        - aten/src/ATen/native/TensorShape.cpp
        - aten/src/ATen/TensorUtils.cpp
        
        Args:
            dst_shape (open3d.cuda.pybind.core.SizeVector): Compatible destination shape with the same number of elements.
        
        Returns:
            open3d.cuda.pybind.core.Tensor
        """
    def round(self) -> Tensor:
        ...
    def save(self, file_name: str) -> None:
        """
        Save tensor to Numpy's npy format.
        """
    def sin(self) -> Tensor:
        ...
    def sin_(self) -> Tensor:
        ...
    def solve(self, B: Tensor) -> Tensor:
        """
        Solves the linear system AX = B with LU decomposition and returns X.  A must be a square matrix.
        """
    def sqrt(self) -> Tensor:
        ...
    def sqrt_(self) -> Tensor:
        ...
    @typing.overload
    def sub(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def sub(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def sub(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def sub(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def sub(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def sub(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def sub(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def sub(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def sub(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def sub(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def sub(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def sub(self, arg0: bool) -> Tensor:
        ...
    @typing.overload
    def sub_(self, arg0: Tensor) -> Tensor:
        ...
    @typing.overload
    def sub_(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def sub_(self, arg0: float) -> Tensor:
        ...
    @typing.overload
    def sub_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def sub_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def sub_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def sub_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def sub_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def sub_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def sub_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def sub_(self, arg0: int) -> Tensor:
        ...
    @typing.overload
    def sub_(self, arg0: bool) -> Tensor:
        ...
    def sum(self, dim: SizeVector | None = None, keepdim: bool = False) -> Tensor:
        ...
    def svd(self) -> tuple[Tensor, Tensor, Tensor]:
        """
        Computes the matrix SVD decomposition :math:`A = U S V^T` and returns the result.  Note :math:`V^T` (V transpose) is returned instead of :math:`V`.
        """
    @typing.overload
    def to(self, dtype: Dtype, copy: bool = False) -> Tensor:
        """
            Returns a tensor with the specified ``dtype``.
        
        Args:
            dtype (open3d.cuda.pybind.core.Dtype): Data type for the Tensor.
            copy (bool, optional, default=False): If true, a new tensor is always created; if false, the copy is avoided when the original tensor already has the targeted dtype.
        
        Returns:
            open3d.cuda.pybind.core.Tensor
        """
    @typing.overload
    def to(self, device: Device, copy: bool = False) -> Tensor:
        """
            Returns a tensor with the specified ``device``.
        
        Args:
            device (open3d.cuda.pybind.core.Device): Compute device to store and operate on the Tensor.
            copy (bool, optional, default=False): If true, a new tensor is always created; if false, the copy is avoided when the original tensor already has the targeted dtype.
        
        Returns:
            open3d.cuda.pybind.core.Tensor
        """
    def to_dlpack(self) -> capsule:
        ...
    def tril(self, diagonal: int = 0) -> Tensor:
        """
        Returns the lower triangular matrix of the 2D tensor, above the given diagonal index. [The value of diagonal = col - row, therefore 0 is the main diagonal (row = col), and it shifts towards right for positive values (for diagonal = 1, col - row = 1), and towards left for negative values. The value of the diagonal parameter must be between [-m, n] where {m, n} is the shape of input tensor.
        
        Args:
            diagonal (int, optional, default=0): Value of [col - row], below which the elements are to be taken for lower triangular matrix.
        
        Returns:
            open3d.cuda.pybind.core.Tensor
        """
    def triu(self, diagonal: int = 0) -> Tensor:
        """
        Returns the upper triangular matrix of the 2D tensor, above the given diagonal index. [The value of diagonal = col - row, therefore 0 is the main diagonal (row = col), and it shifts towards right for positive values (for diagonal = 1, col - row = 1), and towards left for negative values. The value of the diagonal parameter must be between [-m, n] for a {m,n} shaped tensor.
        
        Args:
            diagonal (int, optional, default=0): Value of [col - row], above which the elements are to be taken for upper triangular matrix.
        
        Returns:
            open3d.cuda.pybind.core.Tensor
        """
    def triul(self, diagonal: int = 0) -> tuple[Tensor, Tensor]:
        """
        Returns the tuple of upper and lower triangular matrix of the 2D tensor, above and below the given diagonal index.  The diagonal elements of lower triangular matrix are taken to be unity.  [The value of diagonal = col - row, therefore 0 is the main diagonal (row = col), and it shifts towards right for positive values (for diagonal = 1, col - row = 1), and towards left for negative values.  The value of the diagonal parameter must be between [-m, n] where {m, n} is the shape of input tensor.
        
        Args:
            diagonal (int, optional, default=0): Value of [col - row], above and below which the elements are to be taken for upper (diag. included) and lower triangular matrix.
        
        Returns:
            tuple[open3d.cuda.pybind.core.Tensor, open3d.cuda.pybind.core.Tensor]
        """
    def trunc(self) -> Tensor:
        ...
    @property
    def blob(self) -> Blob:
        ...
    @property
    def device(self) -> Device:
        ...
    @property
    def dtype(self) -> Dtype:
        ...
    @property
    def is_cpu(self) -> bool:
        ...
    @property
    def is_cuda(self) -> bool:
        ...
    @property
    def ndim(self) -> int:
        ...
    @property
    def shape(self) -> SizeVector:
        ...
    @property
    def strides(self) -> SizeVector:
        ...
def addmm(input: Tensor, A: Tensor, B: Tensor, alpha: float, beta: float) -> Tensor:
    """
    Function to perform addmm of two 2D tensors with compatible shapes. Specifically this function returns output = alpha * A @ B + beta * input.
    """
def append(self: Tensor, values: Tensor, axis: int | None = None) -> Tensor:
    """
    Appends the `values` tensor to the `self` tensor, along the
    given axis and returns a new tensor. Both the tensors must have same data-type
    device, and number of dimensions. All dimensions must be the same, except the
    dimension along the axis the tensors are to be appended.
    
    This is the same as NumPy's semantics:
    - https://numpy.org/doc/stable/reference/generated/numpy.append.html
    
    Returns:
        A copy of the `self` tensor with `values` appended to axis. Note that
        append does not occur in-place: a new array is allocated and filled.
        If axis is null, out is a flattened tensor.
    
    Example:
        >>> o3d.core.append([[0, 1], [2, 3]], [[4, 5]], axis = 0)
        [[0 1],
         [2 3],
         [4 5]]
        Tensor[shape={3, 2}, stride={2, 1}, Int64, CPU:0, 0x55555abc6b00]
    
        >>> o3d.core.append([[0, 1], [2, 3]], [[4, 5]])
        [0 1 2 3 4 5]
        Tensor[shape={6}, stride={1}, Int64, CPU:0, 0x55555abc6b70]
    """
def concatenate(tensors: list[Tensor], axis: int | None = 0) -> Tensor:
    """
    Concatenates the list of tensors in their order, along the given
    axis into a new tensor. All the tensors must have same data-type, device, and
    number of dimensions. All dimensions must be the same, except the dimension
    along the axis the tensors are to be concatenated.
    Using Concatenate for a single tensor, the tensor is split along its first
    dimension (length), and concatenated along the axis.
    
    This is the same as NumPy's semantics:
    - https://numpy.org/doc/stable/reference/generated/numpy.concatenate.html
    
    Returns:
         A new tensor with the values of list of tensors concatenated in order,
         along the given axis.
    
    Example:
        >>> a = o3d.core.Tensor([[0, 1], [2, 3]])
        >>> b = o3d.core.Tensor([[4, 5]])
        >>> c = o3d.core.Tensor([[6, 7])
        >>> o3d.core.concatenate((a, b, c), 0)
        [[0 1],
         [2 3],
         [4 5],
         [6 7],
         [8 9]]
        Tensor[shape={5, 2}, stride={2, 1}, Int64, CPU:0, 0x55b454b09390]
    """
def det(A: Tensor) -> float:
    """
    Function to compute determinant of a 2D square tensor.
    """
def inv(A: Tensor) -> Tensor:
    """
    Function to inverse a square 2D tensor.
    """
def lstsq(A: Tensor, B: Tensor) -> Tensor:
    """
    Function to solve X for a linear system AX = B where A is a full rank matrix.
    """
def lu(A: Tensor, permute_l: bool = False) -> tuple:
    """
    Function to compute LU factorisation of a square 2D tensor.
    """
def lu_ipiv(A: Tensor) -> tuple:
    """
    Function to compute LU factorisation of a square 2D tensor.
    """
def matmul(A: Tensor, B: Tensor) -> Tensor:
    """
    Function to perform matrix multiplication of two 2D tensors with compatible shapes.
    """
def maximum(input: Tensor, other: Tensor) -> Tensor:
    """
    Computes the element-wise maximum of input and other. The tensors
    must have same data type and device.
    If input.GetShape() != other.GetShape(), then they will be broadcasted to a
    common shape (which becomes the shape of the output).
    """
def minimum(input: Tensor, other: Tensor) -> Tensor:
    """
    Computes the element-wise minimum of input and other. The tensors
    must have same data type and device.
    If input.GetShape() != other.GetShape(), then they will be broadcasted to a
    common shape (which becomes the shape of the output).
    """
def solve(A: Tensor, B: Tensor) -> Tensor:
    """
    Function to solve X for a linear system AX = B where A is a square matrix
    """
def svd(A: Tensor) -> tuple:
    """
    Function to decompose A with A = U S VT.
    """
def sycl_demo() -> int:
    ...
def tril(A: Tensor, diagonal: int = 0) -> Tensor:
    """
    Function to get lower triangular matrix, below diagonal
    """
def triu(A: Tensor, diagonal: int = 0) -> Tensor:
    """
    Function to get upper triangular matrix, above diagonal
    """
def triul(A: Tensor, diagonal: int = 0) -> tuple:
    """
    Function to get both upper and lower triangular matrix
    """
bool: Dtype
bool8: Dtype
float32: Dtype
float64: Dtype
int16: Dtype
int32: Dtype
int64: Dtype
int8: Dtype
uint16: Dtype
uint32: Dtype
uint64: Dtype
uint8: Dtype
undefined: Dtype
