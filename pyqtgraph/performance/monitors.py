"""
Performance monitoring and profiling tools for PyQtGraph applications.

This module provides utilities to monitor rendering performance, FPS,
and identify bottlenecks in real-time graphics applications.
"""

import time
import threading
from collections import deque
from typing import Dict, List, Optional, Callable, Any
import statistics

from ..Qt import QtCore, QtWidgets


class FPSCounter:
    """
    High-performance FPS counter for monitoring rendering performance.
    
    Tracks frames per second and provides statistics for performance
    optimization in real-time applications.
    """
    
    def __init__(self, window_size: int = 60):
        """
        Initialize FPS counter.
        
        Parameters:
        -----------
        window_size : int
            Number of frames to keep for statistics calculation
        """
        self.window_size = window_size
        self._frame_times = deque(maxlen=window_size)
        self._last_frame_time = None
        self._lock = threading.RLock()
    
    def tick(self) -> None:
        """Register a new frame."""
        current_time = time.perf_counter()
        
        with self._lock:
            if self._last_frame_time is not None:
                frame_time = current_time - self._last_frame_time
                self._frame_times.append(frame_time)
            
            self._last_frame_time = current_time
    
    def get_fps(self) -> float:
        """Get current FPS."""
        with self._lock:
            if len(self._frame_times) == 0:
                return 0.0
            
            avg_frame_time = sum(self._frame_times) / len(self._frame_times)
            return 1.0 / avg_frame_time if avg_frame_time > 0 else 0.0
    
    def get_frame_time_ms(self) -> float:
        """Get average frame time in milliseconds."""
        with self._lock:
            if len(self._frame_times) == 0:
                return 0.0
            
            return (sum(self._frame_times) / len(self._frame_times)) * 1000
    
    def get_statistics(self) -> Dict[str, float]:
        """Get detailed frame time statistics."""
        with self._lock:
            if len(self._frame_times) == 0:
                return {
                    'fps': 0.0,
                    'avg_frame_time_ms': 0.0,
                    'min_frame_time_ms': 0.0,
                    'max_frame_time_ms': 0.0,
                    'std_frame_time_ms': 0.0
                }
            
            frame_times_ms = [ft * 1000 for ft in self._frame_times]
            
            return {
                'fps': self.get_fps(),
                'avg_frame_time_ms': statistics.mean(frame_times_ms),
                'min_frame_time_ms': min(frame_times_ms),
                'max_frame_time_ms': max(frame_times_ms),
                'std_frame_time_ms': statistics.stdev(frame_times_ms) if len(frame_times_ms) > 1 else 0.0
            }
    
    def reset(self) -> None:
        """Reset the counter."""
        with self._lock:
            self._frame_times.clear()
            self._last_frame_time = None


class PerformanceTimer:
    """
    Context manager for timing specific operations.
    """
    
    def __init__(self, name: str, monitor: 'PerformanceMonitor' = None):
        self.name = name
        self.monitor = monitor
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        duration = self.end_time - self.start_time
        
        if self.monitor:
            self.monitor.record_timing(self.name, duration)
    
    @property
    def duration(self) -> Optional[float]:
        """Get the measured duration in seconds."""
        if self.start_time is not None and self.end_time is not None:
            return self.end_time - self.start_time
        return None


class PerformanceMonitor:
    """
    Comprehensive performance monitoring for PyQtGraph applications.
    
    Tracks various performance metrics including rendering times,
    update frequencies, and resource usage.
    """
    
    def __init__(self, max_samples: int = 1000):
        """
        Initialize performance monitor.
        
        Parameters:
        -----------
        max_samples : int
            Maximum number of samples to keep for each metric
        """
        self.max_samples = max_samples
        self._timings: Dict[str, deque] = {}
        self._counters: Dict[str, int] = {}
        self._fps_counter = FPSCounter()
        self._lock = threading.RLock()
        
        # Start time for relative measurements
        self._start_time = time.perf_counter()
    
    def record_timing(self, name: str, duration: float) -> None:
        """
        Record a timing measurement.
        
        Parameters:
        -----------
        name : str
            Name of the operation being timed
        duration : float
            Duration in seconds
        """
        with self._lock:
            if name not in self._timings:
                self._timings[name] = deque(maxlen=self.max_samples)
            
            self._timings[name].append(duration)
    
    def increment_counter(self, name: str, amount: int = 1) -> None:
        """
        Increment a counter metric.
        
        Parameters:
        -----------
        name : str
            Name of the counter
        amount : int
            Amount to increment by
        """
        with self._lock:
            if name not in self._counters:
                self._counters[name] = 0
            self._counters[name] += amount
    
    def timer(self, name: str) -> PerformanceTimer:
        """
        Create a timer context manager.
        
        Parameters:
        -----------
        name : str
            Name for the timing measurement
            
        Returns:
        --------
        PerformanceTimer
            Context manager for timing
        """
        return PerformanceTimer(name, self)
    
    def tick_frame(self) -> None:
        """Register a frame for FPS tracking."""
        self._fps_counter.tick()
    
    def get_timing_stats(self, name: str) -> Optional[Dict[str, float]]:
        """
        Get statistics for a timing measurement.
        
        Parameters:
        -----------
        name : str
            Name of the timing measurement
            
        Returns:
        --------
        dict or None
            Statistics dictionary or None if no data
        """
        with self._lock:
            if name not in self._timings or len(self._timings[name]) == 0:
                return None
            
            timings = list(self._timings[name])
            timings_ms = [t * 1000 for t in timings]
            
            return {
                'count': len(timings),
                'avg_ms': statistics.mean(timings_ms),
                'min_ms': min(timings_ms),
                'max_ms': max(timings_ms),
                'std_ms': statistics.stdev(timings_ms) if len(timings_ms) > 1 else 0.0,
                'total_ms': sum(timings_ms)
            }
    
    def get_counter_value(self, name: str) -> int:
        """Get current value of a counter."""
        with self._lock:
            return self._counters.get(name, 0)
    
    def get_fps_stats(self) -> Dict[str, float]:
        """Get FPS statistics."""
        return self._fps_counter.get_statistics()
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get all performance statistics."""
        with self._lock:
            stats = {
                'fps': self.get_fps_stats(),
                'timings': {},
                'counters': dict(self._counters),
                'uptime_seconds': time.perf_counter() - self._start_time
            }
            
            for name in self._timings:
                timing_stats = self.get_timing_stats(name)
                if timing_stats:
                    stats['timings'][name] = timing_stats
            
            return stats
    
    def reset(self) -> None:
        """Reset all performance metrics."""
        with self._lock:
            self._timings.clear()
            self._counters.clear()
            self._fps_counter.reset()
            self._start_time = time.perf_counter()
    
    def print_report(self) -> None:
        """Print a performance report to console."""
        stats = self.get_all_stats()
        
        print("=== Performance Report ===")
        print(f"Uptime: {stats['uptime_seconds']:.1f} seconds")
        print()
        
        # FPS stats
        fps_stats = stats['fps']
        print(f"FPS: {fps_stats['fps']:.1f}")
        print(f"Frame time: {fps_stats['avg_frame_time_ms']:.2f}ms (avg), "
              f"{fps_stats['min_frame_time_ms']:.2f}ms (min), "
              f"{fps_stats['max_frame_time_ms']:.2f}ms (max)")
        print()
        
        # Timing stats
        if stats['timings']:
            print("Timing Statistics:")
            for name, timing in stats['timings'].items():
                print(f"  {name}: {timing['avg_ms']:.2f}ms (avg), "
                      f"{timing['min_ms']:.2f}ms (min), "
                      f"{timing['max_ms']:.2f}ms (max), "
                      f"{timing['count']} samples")
            print()
        
        # Counters
        if stats['counters']:
            print("Counters:")
            for name, value in stats['counters'].items():
                print(f"  {name}: {value}")
            print()


class RealTimePerformanceWidget(QtWidgets.QWidget):
    """
    Widget for displaying real-time performance metrics.
    
    Shows FPS, frame times, and other performance data in a compact display.
    """
    
    def __init__(self, monitor: PerformanceMonitor, parent=None):
        super().__init__(parent)
        self.monitor = monitor
        
        self.setFixedSize(200, 100)
        self.setWindowTitle("Performance Monitor")
        
        # Update timer
        self._update_timer = QtCore.QTimer()
        self._update_timer.timeout.connect(self.update_display)
        self._update_timer.start(500)  # Update every 500ms
    
    def paintEvent(self, event):
        """Paint the performance display."""
        from ..Qt import QtGui
        
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), QtGui.QColor(0, 0, 0, 180))
        
        painter.setPen(QtGui.QColor(255, 255, 255))
        
        stats = self.monitor.get_all_stats()
        fps_stats = stats['fps']
        
        y = 20
        painter.drawText(10, y, f"FPS: {fps_stats['fps']:.1f}")
        
        y += 20
        painter.drawText(10, y, f"Frame: {fps_stats['avg_frame_time_ms']:.1f}ms")
        
        y += 20
        if stats['counters']:
            updates = stats['counters'].get('updates', 0)
            painter.drawText(10, y, f"Updates: {updates}")
    
    def update_display(self):
        """Update the display."""
        self.update()


class ProfiledPlotWidget:
    """
    Mixin class that adds performance monitoring to plot widgets.
    
    Can be mixed with existing plot widget classes to add automatic
    performance tracking.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._performance_monitor = PerformanceMonitor()
        self._auto_profiling = True
    
    def get_performance_monitor(self) -> PerformanceMonitor:
        """Get the performance monitor instance."""
        return self._performance_monitor
    
    def enable_auto_profiling(self, enabled: bool = True) -> None:
        """Enable or disable automatic profiling."""
        self._auto_profiling = enabled
    
    def show_performance_widget(self) -> RealTimePerformanceWidget:
        """Show a real-time performance monitoring widget."""
        widget = RealTimePerformanceWidget(self._performance_monitor)
        widget.show()
        return widget
    
    def paintEvent(self, event):
        """Override paintEvent to add timing."""
        if self._auto_profiling:
            with self._performance_monitor.timer('paint_event'):
                super().paintEvent(event)
            self._performance_monitor.tick_frame()
        else:
            super().paintEvent(event)


def create_performance_dashboard(monitors: Dict[str, PerformanceMonitor]) -> QtWidgets.QWidget:
    """
    Create a performance dashboard showing multiple monitors.
    
    Parameters:
    -----------
    monitors : dict
        Dictionary mapping names to PerformanceMonitor instances
        
    Returns:
    --------
    QtWidgets.QWidget
        Dashboard widget
    """
    dashboard = QtWidgets.QWidget()
    dashboard.setWindowTitle("Performance Dashboard")
    layout = QtWidgets.QVBoxLayout(dashboard)
    
    for name, monitor in monitors.items():
        group = QtWidgets.QGroupBox(name)
        group_layout = QtWidgets.QVBoxLayout(group)
        
        perf_widget = RealTimePerformanceWidget(monitor)
        group_layout.addWidget(perf_widget)
        
        layout.addWidget(group)
    
    return dashboard