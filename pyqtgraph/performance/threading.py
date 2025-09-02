"""
Threading utilities for non-blocking real-time data updates.

This module provides thread-safe utilities for updating PyQtGraph plots
from background data threads without blocking the main GUI thread.
"""

import threading
import queue
import time
from typing import Callable, Any, Optional, Dict, List
from dataclasses import dataclass
from enum import Enum

from ..Qt import QtCore


class UpdateType(Enum):
    """Types of plot updates."""
    SET_DATA = "set_data"
    APPEND_DATA = "append_data"
    CLEAR_DATA = "clear_data"
    UPDATE_RANGE = "update_range"
    CUSTOM = "custom"


@dataclass
class PlotUpdate:
    """Represents a plot update operation."""
    update_type: UpdateType
    target_id: str
    data: Any
    timestamp: float
    priority: int = 0  # Higher priority updates are processed first


class DataStreamThread(QtCore.QThread):
    """
    Thread for handling continuous data streams.
    
    Receives data from external sources and queues updates for the main
    GUI thread in a thread-safe manner.
    """
    
    # Signals for communicating with main thread
    dataReceived = QtCore.Signal(object)  # Raw data received
    updateReady = QtCore.Signal(object)   # Processed update ready
    
    def __init__(self, 
                 data_source: Callable[[], Any],
                 update_interval: float = 0.01,  # 100Hz default
                 buffer_size: int = 1000,
                 parent=None):
        """
        Initialize data stream thread.
        
        Parameters:
        -----------
        data_source : callable
            Function that returns new data or None if no data available
        update_interval : float
            Time between data polls in seconds
        buffer_size : int
            Maximum size of internal data buffer
        parent : QObject, optional
            Parent object
        """
        super().__init__(parent)
        
        self.data_source = data_source
        self.update_interval = update_interval
        self.buffer_size = buffer_size
        
        self._running = False
        self._paused = False
        self._data_buffer = queue.Queue(maxsize=buffer_size)
        self._stats = {
            'samples_received': 0,
            'samples_dropped': 0,
            'last_update_time': 0
        }
    
    def run(self):
        """Main thread loop."""
        self._running = True
        
        while self._running:
            if not self._paused:
                try:
                    # Get new data
                    data = self.data_source()
                    
                    if data is not None:
                        current_time = time.perf_counter()
                        
                        # Try to add to buffer
                        try:
                            self._data_buffer.put_nowait(data)
                            self._stats['samples_received'] += 1
                            self._stats['last_update_time'] = current_time
                            
                            # Emit signal for raw data
                            self.dataReceived.emit(data)
                            
                        except queue.Full:
                            # Buffer is full, drop oldest data
                            try:
                                self._data_buffer.get_nowait()
                                self._data_buffer.put_nowait(data)
                                self._stats['samples_dropped'] += 1
                            except queue.Empty:
                                pass
                
                except Exception as e:
                    print(f"Error in data stream thread: {e}")
            
            # Sleep for update interval
            self.msleep(int(self.update_interval * 1000))
    
    def stop(self):
        """Stop the thread."""
        self._running = False
        self.wait()
    
    def pause(self):
        """Pause data collection."""
        self._paused = True
    
    def resume(self):
        """Resume data collection."""
        self._paused = False
    
    def get_data(self, max_items: int = None) -> List[Any]:
        """
        Get buffered data items.
        
        Parameters:
        -----------
        max_items : int, optional
            Maximum number of items to retrieve
            
        Returns:
        --------
        list
            List of data items
        """
        items = []
        count = 0
        
        while (not self._data_buffer.empty() and 
               (max_items is None or count < max_items)):
            try:
                items.append(self._data_buffer.get_nowait())
                count += 1
            except queue.Empty:
                break
        
        return items
    
    def get_stats(self) -> Dict[str, Any]:
        """Get thread statistics."""
        return self._stats.copy()
    
    def clear_buffer(self):
        """Clear the data buffer."""
        while not self._data_buffer.empty():
            try:
                self._data_buffer.get_nowait()
            except queue.Empty:
                break


class NonBlockingUpdater(QtCore.QObject):
    """
    Manager for non-blocking plot updates from background threads.
    
    Coordinates updates to multiple plot items while maintaining smooth
    GUI responsiveness.
    """
    
    def __init__(self, max_updates_per_frame: int = 10, parent=None):
        """
        Initialize updater.
        
        Parameters:
        -----------
        max_updates_per_frame : int
            Maximum number of updates to process per timer interval
        parent : QObject, optional
            Parent object
        """
        super().__init__(parent)
        
        self.max_updates_per_frame = max_updates_per_frame
        
        self._update_queue = queue.PriorityQueue()
        self._plot_items = {}  # target_id -> plot_item mapping
        self._update_callbacks = {}  # target_id -> callback mapping
        
        # Timer for processing updates
        self._update_timer = QtCore.QTimer()
        self._update_timer.timeout.connect(self._process_updates)
        self._update_timer.start(16)  # ~60 FPS
        
        self._stats = {
            'updates_processed': 0,
            'updates_queued': 0,
            'queue_size': 0
        }
    
    def register_plot_item(self, 
                          target_id: str, 
                          plot_item: Any,
                          update_callback: Optional[Callable] = None):
        """
        Register a plot item for updates.
        
        Parameters:
        -----------
        target_id : str
            Unique identifier for the plot item
        plot_item : object
            Plot item to update (e.g., PlotDataItem, PlotCurveItem)
        update_callback : callable, optional
            Custom update function, if None will use default setData
        """
        self._plot_items[target_id] = plot_item
        if update_callback:
            self._update_callbacks[target_id] = update_callback
    
    def unregister_plot_item(self, target_id: str):
        """Unregister a plot item."""
        self._plot_items.pop(target_id, None)
        self._update_callbacks.pop(target_id, None)
    
    def queue_update(self, update: PlotUpdate):
        """
        Queue an update for processing.
        
        Parameters:
        -----------
        update : PlotUpdate
            Update to queue
        """
        # Use negative priority for max-heap behavior (higher priority first)
        priority = -update.priority
        self._update_queue.put((priority, update.timestamp, update))
        self._stats['updates_queued'] += 1
    
    def queue_data_update(self,
                         target_id: str,
                         x_data: Any = None,
                         y_data: Any = None,
                         priority: int = 0):
        """
        Queue a data update for a plot item.
        
        Parameters:
        -----------
        target_id : str
            Target plot item identifier
        x_data, y_data : array-like
            Data to update
        priority : int
            Update priority (higher = more urgent)
        """
        update = PlotUpdate(
            update_type=UpdateType.SET_DATA,
            target_id=target_id,
            data={'x': x_data, 'y': y_data},
            timestamp=time.perf_counter(),
            priority=priority
        )
        self.queue_update(update)
    
    def queue_append_update(self,
                           target_id: str,
                           x_value: Any = None,
                           y_value: Any = None,
                           priority: int = 0):
        """
        Queue an append update for a plot item.
        
        Parameters:
        -----------
        target_id : str
            Target plot item identifier
        x_value, y_value : scalar
            Values to append
        priority : int
            Update priority
        """
        update = PlotUpdate(
            update_type=UpdateType.APPEND_DATA,
            target_id=target_id,
            data={'x': x_value, 'y': y_value},
            timestamp=time.perf_counter(),
            priority=priority
        )
        self.queue_update(update)
    
    def queue_custom_update(self,
                           target_id: str,
                           callback: Callable,
                           args: tuple = (),
                           kwargs: dict = None,
                           priority: int = 0):
        """
        Queue a custom update function.
        
        Parameters:
        -----------
        target_id : str
            Target plot item identifier
        callback : callable
            Function to call for the update
        args : tuple
            Arguments for the callback
        kwargs : dict
            Keyword arguments for the callback
        priority : int
            Update priority
        """
        update = PlotUpdate(
            update_type=UpdateType.CUSTOM,
            target_id=target_id,
            data={'callback': callback, 'args': args, 'kwargs': kwargs or {}},
            timestamp=time.perf_counter(),
            priority=priority
        )
        self.queue_update(update)
    
    def _process_updates(self):
        """Process queued updates."""
        processed = 0
        
        while (processed < self.max_updates_per_frame and 
               not self._update_queue.empty()):
            try:
                priority, timestamp, update = self._update_queue.get_nowait()
                self._process_single_update(update)
                processed += 1
                self._stats['updates_processed'] += 1
                
            except queue.Empty:
                break
            except Exception as e:
                print(f"Error processing update: {e}")
        
        self._stats['queue_size'] = self._update_queue.qsize()
    
    def _process_single_update(self, update: PlotUpdate):
        """Process a single update."""
        target_id = update.target_id
        
        if target_id not in self._plot_items:
            return  # Plot item not registered
        
        plot_item = self._plot_items[target_id]
        
        try:
            if update.update_type == UpdateType.SET_DATA:
                if target_id in self._update_callbacks:
                    self._update_callbacks[target_id](plot_item, update.data)
                else:
                    # Default setData behavior
                    x_data = update.data.get('x')
                    y_data = update.data.get('y')
                    if x_data is not None and y_data is not None:
                        plot_item.setData(x_data, y_data)
                    elif y_data is not None:
                        plot_item.setData(y_data)
            
            elif update.update_type == UpdateType.APPEND_DATA:
                # Handle append (would need custom implementation per plot type)
                if hasattr(plot_item, 'appendData'):
                    x_val = update.data.get('x')
                    y_val = update.data.get('y')
                    if x_val is not None and y_val is not None:
                        plot_item.appendData(x_val, y_val)
            
            elif update.update_type == UpdateType.CLEAR_DATA:
                if hasattr(plot_item, 'clear'):
                    plot_item.clear()
                else:
                    plot_item.setData([], [])
            
            elif update.update_type == UpdateType.CUSTOM:
                callback = update.data['callback']
                args = update.data['args']
                kwargs = update.data['kwargs']
                callback(plot_item, *args, **kwargs)
        
        except Exception as e:
            print(f"Error executing update for {target_id}: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get updater statistics."""
        return self._stats.copy()
    
    def clear_queue(self):
        """Clear the update queue."""
        while not self._update_queue.empty():
            try:
                self._update_queue.get_nowait()
            except queue.Empty:
                break


class RealTimeDataManager:
    """
    High-level manager for coordinating real-time data streams and plot updates.
    
    Combines DataStreamThread and NonBlockingUpdater for easy setup of
    real-time data visualization.
    """
    
    def __init__(self, max_updates_per_frame: int = 10):
        """
        Initialize real-time data manager.
        
        Parameters:
        -----------
        max_updates_per_frame : int
            Maximum plot updates per frame
        """
        self.updater = NonBlockingUpdater(max_updates_per_frame)
        self._data_threads = {}
        self._data_processors = {}
    
    def add_data_stream(self,
                       stream_id: str,
                       data_source: Callable[[], Any],
                       plot_targets: List[str],
                       data_processor: Optional[Callable] = None,
                       update_interval: float = 0.01,
                       buffer_size: int = 1000):
        """
        Add a data stream.
        
        Parameters:
        -----------
        stream_id : str
            Unique identifier for the stream
        data_source : callable
            Function that returns new data
        plot_targets : list
            List of plot target IDs to update
        data_processor : callable, optional
            Function to process raw data before plotting
        update_interval : float
            Data polling interval
        buffer_size : int
            Buffer size for the stream
        """
        # Create data thread
        thread = DataStreamThread(
            data_source=data_source,
            update_interval=update_interval,
            buffer_size=buffer_size
        )
        
        # Connect data processing
        if data_processor:
            self._data_processors[stream_id] = data_processor
        
        def process_data(data):
            processed_data = data
            if stream_id in self._data_processors:
                processed_data = self._data_processors[stream_id](data)
            
            # Update all target plots
            for target_id in plot_targets:
                if isinstance(processed_data, dict):
                    self.updater.queue_data_update(
                        target_id=target_id,
                        x_data=processed_data.get('x'),
                        y_data=processed_data.get('y')
                    )
                elif isinstance(processed_data, (list, tuple)) and len(processed_data) == 2:
                    self.updater.queue_data_update(
                        target_id=target_id,
                        x_data=processed_data[0],
                        y_data=processed_data[1]
                    )
        
        thread.dataReceived.connect(process_data)
        self._data_threads[stream_id] = thread
    
    def start_stream(self, stream_id: str):
        """Start a data stream."""
        if stream_id in self._data_threads:
            self._data_threads[stream_id].start()
    
    def stop_stream(self, stream_id: str):
        """Stop a data stream."""
        if stream_id in self._data_threads:
            self._data_threads[stream_id].stop()
    
    def register_plot(self, target_id: str, plot_item: Any, update_callback: Optional[Callable] = None):
        """Register a plot item for updates."""
        self.updater.register_plot_item(target_id, plot_item, update_callback)
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all components."""
        stats = {
            'updater': self.updater.get_stats(),
            'streams': {}
        }
        
        for stream_id, thread in self._data_threads.items():
            stats['streams'][stream_id] = thread.get_stats()
        
        return stats
    
    def cleanup(self):
        """Clean up all resources."""
        for thread in self._data_threads.values():
            thread.stop()
        self._data_threads.clear()
        self._data_processors.clear()