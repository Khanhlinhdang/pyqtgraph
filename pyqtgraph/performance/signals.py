"""
Enhanced signal processing for high-frequency data updates.

This module provides optimized signal proxies that can handle high-frequency
updates efficiently through batching and rate limiting, essential for 
trading applications with real-time data feeds.
"""

import time
import weakref
from typing import Any, Callable, Optional, List
from collections import deque
import threading

from ..Qt import QtCore
from ..SignalProxy import SignalProxy
from ..ThreadsafeTimer import ThreadsafeTimer


class BatchedSignalProxy(QtCore.QObject):
    """
    Signal proxy that batches multiple rapid signals into fewer, batched emissions.
    
    Particularly useful for high-frequency data updates where processing
    individual signals would be too expensive.
    """
    
    sigBatchReady = QtCore.Signal(object)  # Emits list of batched arguments
    
    def __init__(self,
                 signal,
                 batch_size: int = 10,
                 max_delay: float = 0.1,
                 slot: Optional[Callable] = None,
                 thread_safe: bool = True):
        """
        Initialize batched signal proxy.
        
        Parameters:
        -----------
        signal
            Source signal to batch
        batch_size : int
            Maximum number of signals to batch together
        max_delay : float
            Maximum time (seconds) to wait before emitting incomplete batch
        slot : callable, optional
            Function to connect to batch emissions
        thread_safe : bool
            Whether to use thread-safe operations
        """
        super().__init__()
        
        self.batch_size = batch_size
        self.max_delay = max_delay
        self.thread_safe = thread_safe
        
        self._batch = []
        self._lock = threading.RLock() if thread_safe else None
        
        Timer = ThreadsafeTimer if thread_safe else QtCore.QTimer
        self._timer = Timer()
        self._timer.timeout.connect(self._emit_batch)
        self._timer.setSingleShot(True)
        
        self._signal = signal
        self._signal.connect(self._on_signal)
        
        if slot is not None:
            self.sigBatchReady.connect(slot)
            self._slot = weakref.ref(slot)
        else:
            self._slot = None
    
    def _on_signal(self, *args):
        """Handle incoming signal."""
        if self._lock:
            with self._lock:
                self._add_to_batch(args)
        else:
            self._add_to_batch(args)
    
    def _add_to_batch(self, args):
        """Add signal arguments to current batch."""
        self._batch.append(args)
        
        if len(self._batch) >= self.batch_size:
            self._emit_batch()
        elif len(self._batch) == 1:
            # Start timer for first item in batch
            self._timer.start(int(self.max_delay * 1000))
    
    def _emit_batch(self):
        """Emit the current batch."""
        if not self._batch:
            return
        
        self._timer.stop()
        batch_copy = list(self._batch)
        self._batch.clear()
        
        self.sigBatchReady.emit(batch_copy)
    
    def flush(self):
        """Force emission of current batch."""
        if self._lock:
            with self._lock:
                self._emit_batch()
        else:
            self._emit_batch()


class RateLimitedSignalProxy(QtCore.QObject):
    """
    Signal proxy that limits emission rate while preserving the latest value.
    
    Unlike the standard SignalProxy, this ensures the most recent value
    is always emitted, making it ideal for real-time data displays.
    """
    
    sigRateLimited = QtCore.Signal(object)
    
    def __init__(self,
                 signal,
                 rate_limit: float,
                 slot: Optional[Callable] = None,
                 thread_safe: bool = True):
        """
        Initialize rate-limited signal proxy.
        
        Parameters:
        -----------
        signal
            Source signal to rate-limit
        rate_limit : float
            Maximum emission rate in Hz (signals per second)
        slot : callable, optional
            Function to connect to rate-limited emissions
        thread_safe : bool
            Whether to use thread-safe operations
        """
        super().__init__()
        
        self.rate_limit = rate_limit
        self.min_interval = 1.0 / rate_limit if rate_limit > 0 else 0
        self.thread_safe = thread_safe
        
        self._latest_args = None
        self._last_emission_time = 0
        self._pending = False
        self._lock = threading.RLock() if thread_safe else None
        
        Timer = ThreadsafeTimer if thread_safe else QtCore.QTimer
        self._timer = Timer()
        self._timer.timeout.connect(self._emit_latest)
        self._timer.setSingleShot(True)
        
        self._signal = signal
        self._signal.connect(self._on_signal)
        
        if slot is not None:
            self.sigRateLimited.connect(slot)
            self._slot = weakref.ref(slot)
        else:
            self._slot = None
    
    def _on_signal(self, *args):
        """Handle incoming signal."""
        if self._lock:
            with self._lock:
                self._update_latest(args)
        else:
            self._update_latest(args)
    
    def _update_latest(self, args):
        """Update the latest arguments and manage emission timing."""
        self._latest_args = args
        current_time = time.perf_counter()
        
        if current_time - self._last_emission_time >= self.min_interval:
            # Can emit immediately
            self._emit_now()
        elif not self._pending:
            # Schedule emission for later
            delay = self.min_interval - (current_time - self._last_emission_time)
            self._timer.start(int(delay * 1000))
            self._pending = True
    
    def _emit_now(self):
        """Emit the latest args immediately."""
        if self._latest_args is not None:
            self._timer.stop()
            self._pending = False
            self._last_emission_time = time.perf_counter()
            args = self._latest_args
            self._latest_args = None
            self.sigRateLimited.emit(args)
    
    def _emit_latest(self):
        """Timer callback to emit latest args."""
        if self._lock:
            with self._lock:
                self._emit_now()
        else:
            self._emit_now()
    
    def flush(self):
        """Force emission of latest value."""
        if self._lock:
            with self._lock:
                self._emit_now()
        else:
            self._emit_now()


class AdaptiveSignalProxy(QtCore.QObject):
    """
    Signal proxy that adaptively adjusts its behavior based on signal frequency.
    
    Automatically switches between immediate emission, rate limiting, and
    batching based on the incoming signal frequency.
    """
    
    sigAdaptive = QtCore.Signal(object)
    
    def __init__(self,
                 signal,
                 low_freq_threshold: float = 10,    # Hz
                 high_freq_threshold: float = 100,  # Hz
                 batch_size: int = 5,
                 slot: Optional[Callable] = None,
                 thread_safe: bool = True):
        """
        Initialize adaptive signal proxy.
        
        Parameters:
        -----------
        signal
            Source signal
        low_freq_threshold : float
            Below this frequency, emit immediately
        high_freq_threshold : float
            Above this frequency, use batching
        batch_size : int
            Batch size for high-frequency mode
        slot : callable, optional
            Function to connect to emissions
        thread_safe : bool
            Whether to use thread-safe operations
        """
        super().__init__()
        
        self.low_freq_threshold = low_freq_threshold
        self.high_freq_threshold = high_freq_threshold
        self.batch_size = batch_size
        self.thread_safe = thread_safe
        
        self._signal_times = deque(maxlen=20)  # Track recent signal times
        self._current_frequency = 0
        self._mode = 'immediate'  # 'immediate', 'rate_limited', 'batched'
        self._lock = threading.RLock() if thread_safe else None
        
        # Current proxy handling the signal
        self._current_proxy = None
        
        self._signal = signal
        self._signal.connect(self._on_signal)
        
        if slot is not None:
            self.sigAdaptive.connect(slot)
            self._slot = weakref.ref(slot)
        else:
            self._slot = None
    
    def _on_signal(self, *args):
        """Handle incoming signal and adapt behavior."""
        current_time = time.perf_counter()
        
        if self._lock:
            with self._lock:
                self._update_frequency(current_time)
                self._adapt_behavior()
                self._forward_signal(args)
        else:
            self._update_frequency(current_time)
            self._adapt_behavior()
            self._forward_signal(args)
    
    def _update_frequency(self, current_time):
        """Update current signal frequency estimate."""
        self._signal_times.append(current_time)
        
        if len(self._signal_times) >= 2:
            time_span = self._signal_times[-1] - self._signal_times[0]
            if time_span > 0:
                self._current_frequency = (len(self._signal_times) - 1) / time_span
    
    def _adapt_behavior(self):
        """Adapt proxy behavior based on current frequency."""
        if self._current_frequency < self.low_freq_threshold:
            target_mode = 'immediate'
        elif self._current_frequency < self.high_freq_threshold:
            target_mode = 'rate_limited'
        else:
            target_mode = 'batched'
        
        if target_mode != self._mode:
            self._switch_mode(target_mode)
    
    def _switch_mode(self, new_mode):
        """Switch to a new operating mode."""
        # Clean up current proxy
        if self._current_proxy is not None:
            if hasattr(self._current_proxy, 'flush'):
                self._current_proxy.flush()
            self._current_proxy = None
        
        self._mode = new_mode
        
        if new_mode == 'rate_limited':
            rate_limit = (self.low_freq_threshold + self.high_freq_threshold) / 2
            self._current_proxy = RateLimitedSignalProxy(
                self._signal,
                rate_limit=rate_limit,
                slot=lambda args: self.sigAdaptive.emit(args),
                thread_safe=self.thread_safe
            )
        elif new_mode == 'batched':
            self._current_proxy = BatchedSignalProxy(
                self._signal,
                batch_size=self.batch_size,
                max_delay=0.05,  # 50ms max delay
                slot=lambda batch: self.sigAdaptive.emit(batch),
                thread_safe=self.thread_safe
            )
        # For 'immediate' mode, _current_proxy remains None
    
    def _forward_signal(self, args):
        """Forward signal based on current mode."""
        if self._mode == 'immediate':
            self.sigAdaptive.emit(args)
        # For other modes, the proxy handles it
    
    def get_current_frequency(self) -> float:
        """Get the current estimated signal frequency."""
        return self._current_frequency
    
    def get_current_mode(self) -> str:
        """Get the current operating mode."""
        return self._mode


class HighFrequencySignalManager:
    """
    Manager for coordinating multiple high-frequency signals efficiently.
    
    Provides centralized management of signal proxies with shared timing
    and batching strategies for optimal performance.
    """
    
    def __init__(self, thread_safe: bool = True):
        self.thread_safe = thread_safe
        self._proxies = {}
        self._lock = threading.RLock() if thread_safe else None
        
        # Shared timer for coordinated updates
        Timer = ThreadsafeTimer if thread_safe else QtCore.QTimer
        self._update_timer = Timer()
        self._update_timer.timeout.connect(self._coordinated_update)
        self._update_timer.start(16)  # ~60 FPS
        
    def add_signal(self,
                   name: str,
                   signal,
                   proxy_type: str = 'adaptive',
                   slot: Optional[Callable] = None,
                   **proxy_kwargs):
        """
        Add a signal to be managed.
        
        Parameters:
        -----------
        name : str
            Unique name for this signal
        signal
            The signal to manage
        proxy_type : str
            Type of proxy ('adaptive', 'batched', 'rate_limited')
        slot : callable, optional
            Function to connect to processed signal
        **proxy_kwargs
            Additional arguments for the proxy constructor
        """
        if self._lock:
            with self._lock:
                self._add_signal_internal(name, signal, proxy_type, slot, **proxy_kwargs)
        else:
            self._add_signal_internal(name, signal, proxy_type, slot, **proxy_kwargs)
    
    def _add_signal_internal(self, name, signal, proxy_type, slot, **proxy_kwargs):
        """Internal method to add signal."""
        if proxy_type == 'adaptive':
            proxy = AdaptiveSignalProxy(signal, slot=slot, thread_safe=self.thread_safe, **proxy_kwargs)
        elif proxy_type == 'batched':
            proxy = BatchedSignalProxy(signal, slot=slot, thread_safe=self.thread_safe, **proxy_kwargs)
        elif proxy_type == 'rate_limited':
            proxy = RateLimitedSignalProxy(signal, slot=slot, thread_safe=self.thread_safe, **proxy_kwargs)
        else:
            raise ValueError(f"Unknown proxy type: {proxy_type}")
        
        self._proxies[name] = proxy
    
    def remove_signal(self, name: str):
        """Remove a managed signal."""
        if self._lock:
            with self._lock:
                if name in self._proxies:
                    proxy = self._proxies.pop(name)
                    if hasattr(proxy, 'flush'):
                        proxy.flush()
        else:
            if name in self._proxies:
                proxy = self._proxies.pop(name)
                if hasattr(proxy, 'flush'):
                    proxy.flush()
    
    def _coordinated_update(self):
        """Coordinated update for all managed signals."""
        if self._lock:
            with self._lock:
                for proxy in self._proxies.values():
                    if hasattr(proxy, 'flush'):
                        proxy.flush()
        else:
            for proxy in self._proxies.values():
                if hasattr(proxy, 'flush'):
                    proxy.flush()
    
    def get_proxy_stats(self) -> dict:
        """Get statistics for all managed proxies."""
        stats = {}
        for name, proxy in self._proxies.items():
            if hasattr(proxy, 'get_current_frequency'):
                stats[name] = {
                    'frequency': proxy.get_current_frequency(),
                    'mode': proxy.get_current_mode()
                }
            else:
                stats[name] = {'type': type(proxy).__name__}
        return stats