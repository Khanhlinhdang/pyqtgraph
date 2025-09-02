"""
PyQtGraph Performance Optimization Package

This package provides optimization utilities for high-performance real-time 
graphics applications, specifically designed for trading-like applications 
that require smooth, continuous updates at high frequencies.

Key Features:
- OpenGL acceleration configurations
- Data buffering and streaming optimizations  
- Signal rate limiting and batching
- GPU acceleration helpers
- Threading utilities for real-time data
- Performance monitoring tools
"""

from .config import PerformanceConfig, TradingViewConfig
from .buffers import RingBuffer, StreamingBuffer
from .signals import BatchedSignalProxy, RateLimitedSignalProxy  
from .monitors import PerformanceMonitor, FPSCounter
from .threading import DataStreamThread, NonBlockingUpdater

__all__ = [
    'PerformanceConfig',
    'TradingViewConfig', 
    'RingBuffer',
    'StreamingBuffer',
    'BatchedSignalProxy',
    'RateLimitedSignalProxy',
    'PerformanceMonitor',
    'FPSCounter',
    'DataStreamThread',
    'NonBlockingUpdater'
]