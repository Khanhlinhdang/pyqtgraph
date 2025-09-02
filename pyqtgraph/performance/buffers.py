"""
Optimized data buffers for high-performance real-time applications.

This module provides efficient buffer implementations for streaming data,
particularly useful for trading applications that need to handle continuous
data feeds with minimal memory allocation overhead.
"""

import numpy as np
from typing import Optional, Union, Tuple, Any
from collections import deque
import threading


class RingBuffer:
    """
    High-performance ring buffer for continuous data streaming.
    
    Optimized for minimal memory allocations and fast append operations.
    Particularly useful for time-series data in trading applications.
    """
    
    def __init__(self, 
                 maxlen: int, 
                 dtype: np.dtype = np.float64,
                 dimensions: int = 1):
        """
        Initialize ring buffer.
        
        Parameters:
        -----------
        maxlen : int
            Maximum number of elements to store
        dtype : np.dtype
            Data type for the buffer
        dimensions : int
            Number of dimensions (1 for simple arrays, 2 for x,y pairs, etc.)
        """
        self.maxlen = maxlen
        self.dtype = dtype
        self.dimensions = dimensions
        
        if dimensions == 1:
            self._buffer = np.empty(maxlen, dtype=dtype)
        else:
            self._buffer = np.empty((maxlen, dimensions), dtype=dtype)
            
        self._head = 0
        self._size = 0
        self._lock = threading.RLock()
    
    def append(self, data: Union[float, np.ndarray]) -> None:
        """
        Append data to the buffer.
        
        Parameters:
        -----------
        data : float or np.ndarray
            Data to append. For multi-dimensional buffers, should be array-like
            with shape matching the dimensions.
        """
        with self._lock:
            self._buffer[self._head] = data
            self._head = (self._head + 1) % self.maxlen
            
            if self._size < self.maxlen:
                self._size += 1
    
    def extend(self, data: np.ndarray) -> None:
        """
        Extend buffer with multiple data points.
        
        Parameters:
        -----------
        data : np.ndarray
            Array of data to append
        """
        with self._lock:
            data = np.asarray(data, dtype=self.dtype)
            n = len(data)
            
            if n >= self.maxlen:
                # If data is larger than buffer, take only the last maxlen items
                self._buffer[:] = data[-self.maxlen:]
                self._head = 0
                self._size = self.maxlen
            else:
                # Add data chunk by chunk
                for i in range(n):
                    self._buffer[self._head] = data[i]
                    self._head = (self._head + 1) % self.maxlen
                    
                    if self._size < self.maxlen:
                        self._size += 1
    
    def get_data(self, copy: bool = True) -> np.ndarray:
        """
        Get current buffer data in correct order.
        
        Parameters:
        -----------
        copy : bool
            Whether to return a copy or a view (copy is safer for threading)
            
        Returns:
        --------
        np.ndarray
            Buffer data in chronological order
        """
        with self._lock:
            if self._size == 0:
                if self.dimensions == 1:
                    return np.array([], dtype=self.dtype)
                else:
                    return np.array([]).reshape((0, self.dimensions))
            
            if self._size < self.maxlen:
                # Buffer not full yet
                result = self._buffer[:self._size]
            else:
                # Buffer is full, need to reorder
                if self._head == 0:
                    result = self._buffer
                else:
                    result = np.concatenate([
                        self._buffer[self._head:],
                        self._buffer[:self._head]
                    ])
            
            return result.copy() if copy else result
    
    def get_latest(self, n: int) -> np.ndarray:
        """
        Get the latest n data points.
        
        Parameters:
        -----------
        n : int
            Number of latest points to retrieve
            
        Returns:
        --------
        np.ndarray
            Latest n data points
        """
        with self._lock:
            if n <= 0 or self._size == 0:
                if self.dimensions == 1:
                    return np.array([], dtype=self.dtype)
                else:
                    return np.array([]).reshape((0, self.dimensions))
            
            n = min(n, self._size)
            
            if self._size < self.maxlen:
                # Buffer not full
                start_idx = max(0, self._size - n)
                return self._buffer[start_idx:self._size].copy()
            else:
                # Buffer is full
                if n <= self._head:
                    return self._buffer[self._head - n:self._head].copy()
                else:
                    # Need to wrap around
                    tail_size = self._head
                    head_size = n - tail_size
                    return np.concatenate([
                        self._buffer[-head_size:],
                        self._buffer[:tail_size]
                    ])
    
    def clear(self) -> None:
        """Clear the buffer."""
        with self._lock:
            self._head = 0
            self._size = 0
    
    def __len__(self) -> int:
        """Return current buffer size."""
        return self._size
    
    @property
    def is_full(self) -> bool:
        """Check if buffer is full."""
        return self._size == self.maxlen


class StreamingBuffer:
    """
    Optimized buffer for streaming X,Y data pairs (e.g., time series plots).
    
    Maintains separate buffers for X and Y data with automatic downsampling
    for performance when dealing with large datasets.
    """
    
    def __init__(self,
                 maxlen: int,
                 x_dtype: np.dtype = np.float64,
                 y_dtype: np.dtype = np.float64,
                 downsample_threshold: Optional[int] = None,
                 downsample_factor: int = 2):
        """
        Initialize streaming buffer.
        
        Parameters:
        -----------
        maxlen : int
            Maximum number of data points
        x_dtype, y_dtype : np.dtype
            Data types for X and Y arrays
        downsample_threshold : int, optional
            If set, automatically downsample when buffer exceeds this size
        downsample_factor : int
            Factor by which to downsample (keep every Nth point)
        """
        self.maxlen = maxlen
        self.x_dtype = x_dtype
        self.y_dtype = y_dtype
        self.downsample_threshold = downsample_threshold or maxlen
        self.downsample_factor = downsample_factor
        
        self._x_buffer = RingBuffer(maxlen, x_dtype)
        self._y_buffer = RingBuffer(maxlen, y_dtype)
        self._lock = threading.RLock()
    
    def append(self, x: float, y: float) -> None:
        """
        Append X,Y data pair.
        
        Parameters:
        -----------
        x, y : float
            Data values to append
        """
        with self._lock:
            self._x_buffer.append(x)
            self._y_buffer.append(y)
            
            # Auto-downsample if threshold exceeded
            if (self.downsample_threshold is not None and 
                len(self._x_buffer) >= self.downsample_threshold):
                self._downsample()
    
    def extend(self, x_data: np.ndarray, y_data: np.ndarray) -> None:
        """
        Extend buffer with multiple X,Y pairs.
        
        Parameters:
        -----------
        x_data, y_data : np.ndarray
            Arrays of X and Y data
        """
        if len(x_data) != len(y_data):
            raise ValueError("X and Y data must have same length")
        
        with self._lock:
            self._x_buffer.extend(x_data)
            self._y_buffer.extend(y_data)
            
            # Auto-downsample if threshold exceeded
            if (self.downsample_threshold is not None and 
                len(self._x_buffer) >= self.downsample_threshold):
                self._downsample()
    
    def get_data(self, copy: bool = True) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get current buffer data.
        
        Parameters:
        -----------
        copy : bool
            Whether to return copies or views
            
        Returns:
        --------
        tuple
            (x_data, y_data) arrays
        """
        with self._lock:
            return (self._x_buffer.get_data(copy), 
                    self._y_buffer.get_data(copy))
    
    def get_latest(self, n: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get latest n data points.
        
        Parameters:
        -----------
        n : int
            Number of latest points to retrieve
            
        Returns:
        --------
        tuple
            (x_data, y_data) arrays
        """
        with self._lock:
            return (self._x_buffer.get_latest(n),
                    self._y_buffer.get_latest(n))
    
    def _downsample(self) -> None:
        """Internal method to downsample buffer data."""
        x_data = self._x_buffer.get_data(copy=False)
        y_data = self._y_buffer.get_data(copy=False)
        
        # Keep every nth point
        indices = np.arange(0, len(x_data), self.downsample_factor)
        downsampled_x = x_data[indices]
        downsampled_y = y_data[indices]
        
        # Clear buffers and reload with downsampled data
        self._x_buffer.clear()
        self._y_buffer.clear()
        self._x_buffer.extend(downsampled_x)
        self._y_buffer.extend(downsampled_y)
    
    def clear(self) -> None:
        """Clear both buffers."""
        with self._lock:
            self._x_buffer.clear()
            self._y_buffer.clear()
    
    def __len__(self) -> int:
        """Return current buffer size."""
        return len(self._x_buffer)
    
    @property
    def is_full(self) -> bool:
        """Check if buffer is full."""
        return self._x_buffer.is_full


class MultiSeriesBuffer:
    """
    Buffer for multiple data series (e.g., OHLC data, multiple indicators).
    
    Useful for trading applications that display multiple related data series.
    """
    
    def __init__(self,
                 maxlen: int,
                 series_names: list,
                 dtype: np.dtype = np.float64):
        """
        Initialize multi-series buffer.
        
        Parameters:
        -----------
        maxlen : int
            Maximum number of data points per series
        series_names : list
            Names of the data series (e.g., ['open', 'high', 'low', 'close'])
        dtype : np.dtype
            Data type for all series
        """
        self.maxlen = maxlen
        self.series_names = series_names
        self.dtype = dtype
        
        self._buffers = {
            name: RingBuffer(maxlen, dtype) 
            for name in series_names
        }
        self._lock = threading.RLock()
    
    def append(self, **data) -> None:
        """
        Append data to multiple series.
        
        Parameters:
        -----------
        **data
            Keyword arguments with series names as keys
        """
        with self._lock:
            for name, value in data.items():
                if name in self._buffers:
                    self._buffers[name].append(value)
    
    def extend(self, **data) -> None:
        """
        Extend multiple series with arrays of data.
        
        Parameters:
        -----------
        **data
            Keyword arguments with series names as keys, values are arrays
        """
        with self._lock:
            for name, values in data.items():
                if name in self._buffers:
                    self._buffers[name].extend(values)
    
    def get_series(self, name: str, copy: bool = True) -> np.ndarray:
        """
        Get data for a specific series.
        
        Parameters:
        -----------
        name : str
            Name of the series
        copy : bool
            Whether to return a copy
            
        Returns:
        --------
        np.ndarray
            Series data
        """
        with self._lock:
            if name not in self._buffers:
                raise KeyError(f"Unknown series: {name}")
            return self._buffers[name].get_data(copy)
    
    def get_all_series(self, copy: bool = True) -> dict:
        """
        Get all series data.
        
        Parameters:
        -----------
        copy : bool
            Whether to return copies
            
        Returns:
        --------
        dict
            Dictionary mapping series names to data arrays
        """
        with self._lock:
            return {
                name: buffer.get_data(copy) 
                for name, buffer in self._buffers.items()
            }
    
    def clear(self) -> None:
        """Clear all series buffers."""
        with self._lock:
            for buffer in self._buffers.values():
                buffer.clear()
    
    def __len__(self) -> int:
        """Return buffer size (assumes all series have same length)."""
        if self._buffers:
            return len(next(iter(self._buffers.values())))
        return 0