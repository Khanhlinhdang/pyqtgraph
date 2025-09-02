#!/usr/bin/env python3
"""
Performance optimization test script.

Tests that the performance optimization utilities are working correctly
without requiring a GUI environment.
"""

import sys
import numpy as np
import time

def test_performance_imports():
    """Test that performance modules can be imported."""
    print("Testing performance module imports...")
    
    try:
        # Test direct imports
        from pyqtgraph.performance import (
            PerformanceConfig, TradingViewConfig, 
            RingBuffer, StreamingBuffer,
            PerformanceMonitor, FPSCounter
        )
        print("✓ Performance modules imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def test_ring_buffer():
    """Test ring buffer functionality."""
    print("\nTesting RingBuffer...")
    
    try:
        from pyqtgraph.performance import RingBuffer
        
        # Test basic functionality
        buffer = RingBuffer(maxlen=100, dtype=np.float64)
        
        # Add some data
        for i in range(150):  # More than max length
            buffer.append(float(i))
        
        # Get data
        data = buffer.get_data()
        
        # Should have only last 100 items
        assert len(data) == 100
        assert data[0] == 50.0  # First item should be 50 (items 0-49 were dropped)
        assert data[-1] == 149.0  # Last item should be 149
        
        # Test latest items
        latest = buffer.get_latest(10)
        assert len(latest) == 10
        assert latest[-1] == 149.0
        
        print("✓ RingBuffer tests passed")
        return True
    except Exception as e:
        print(f"✗ RingBuffer test failed: {e}")
        return False

def test_streaming_buffer():
    """Test streaming buffer functionality.""" 
    print("\nTesting StreamingBuffer...")
    
    try:
        from pyqtgraph.performance import StreamingBuffer
        
        buffer = StreamingBuffer(maxlen=100)
        
        # Add X,Y data
        for i in range(50):
            buffer.append(float(i), float(i * 2))
        
        # Get data
        x_data, y_data = buffer.get_data()
        
        assert len(x_data) == 50
        assert len(y_data) == 50
        assert x_data[0] == 0.0
        assert y_data[0] == 0.0
        assert x_data[-1] == 49.0
        assert y_data[-1] == 98.0
        
        print("✓ StreamingBuffer tests passed")
        return True
    except Exception as e:
        print(f"✗ StreamingBuffer test failed: {e}")
        return False

def test_performance_monitor():
    """Test performance monitoring."""
    print("\nTesting PerformanceMonitor...")
    
    try:
        from pyqtgraph.performance import PerformanceMonitor
        
        monitor = PerformanceMonitor()
        
        # Test timing
        with monitor.timer('test_operation'):
            time.sleep(0.01)  # 10ms operation
        
        # Test counter
        monitor.increment_counter('test_counter', 5)
        
        # Get stats
        stats = monitor.get_all_stats()
        
        assert 'timings' in stats
        assert 'counters' in stats
        assert 'test_operation' in stats['timings']
        assert stats['counters']['test_counter'] == 5
        
        timing_stats = monitor.get_timing_stats('test_operation')
        assert timing_stats['count'] == 1
        assert timing_stats['avg_ms'] >= 10  # Should be at least 10ms
        
        print("✓ PerformanceMonitor tests passed")
        return True
    except Exception as e:
        print(f"✗ PerformanceMonitor test failed: {e}")
        return False

def test_configuration():
    """Test configuration classes."""
    print("\nTesting Configuration classes...")
    
    try:
        from pyqtgraph.performance import TradingViewConfig, HighFrequencyConfig
        
        # Test TradingView config
        trading_config = TradingViewConfig(enable_opengl=True, mouse_rate_limit=120)
        config_dict = trading_config.get_config()
        
        assert config_dict['useOpenGL'] == True
        assert config_dict['mouseRateLimit'] == 120
        assert config_dict['antialias'] == False  # Should be disabled for performance
        
        # Test high frequency config
        hf_config = HighFrequencyConfig()
        hf_dict = hf_config.get_config()
        
        assert hf_dict['useOpenGL'] == True
        assert hf_dict['useCupy'] == True
        assert hf_dict['mouseRateLimit'] == 60  # Lower for max performance
        
        print("✓ Configuration tests passed")
        return True
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False

def test_fps_counter():
    """Test FPS counter."""
    print("\nTesting FPSCounter...")
    
    try:
        from pyqtgraph.performance import FPSCounter
        
        counter = FPSCounter(window_size=10)
        
        # Simulate some frames at ~50 FPS
        frame_interval = 1.0 / 50  # 50 FPS = 20ms per frame
        
        for i in range(15):
            counter.tick()
            time.sleep(frame_interval)
        
        # Get stats
        fps = counter.get_fps()
        frame_time = counter.get_frame_time_ms()
        stats = counter.get_statistics()
        
        # Should be approximately 50 FPS (allowing some tolerance)
        assert 40 < fps < 60, f"FPS {fps} not in expected range"
        assert 15 < frame_time < 30, f"Frame time {frame_time}ms not in expected range"
        assert 'fps' in stats
        assert 'avg_frame_time_ms' in stats
        
        print(f"✓ FPSCounter tests passed (measured {fps:.1f} FPS)")
        return True
    except Exception as e:
        print(f"✗ FPSCounter test failed: {e}")
        return False

def benchmark_ring_buffer():
    """Benchmark ring buffer performance."""
    print("\nBenchmarking RingBuffer performance...")
    
    try:
        from pyqtgraph.performance import RingBuffer
        
        # Test with large buffer and many operations
        buffer = RingBuffer(maxlen=10000, dtype=np.float64)
        
        # Benchmark append operations
        start_time = time.perf_counter()
        for i in range(50000):
            buffer.append(float(i))
        append_time = time.perf_counter() - start_time
        
        # Benchmark data retrieval
        start_time = time.perf_counter()
        for i in range(1000):
            data = buffer.get_latest(1000)
        retrieval_time = time.perf_counter() - start_time
        
        append_rate = 50000 / append_time
        retrieval_rate = 1000 / retrieval_time
        
        print(f"✓ RingBuffer performance:")
        print(f"  - Append rate: {append_rate:.0f} ops/sec")
        print(f"  - Retrieval rate: {retrieval_rate:.0f} ops/sec")
        
        return True
    except Exception as e:
        print(f"✗ RingBuffer benchmark failed: {e}")
        return False

def main():
    """Run all tests."""
    print("=== PyQtGraph Performance Optimization Tests ===\n")
    
    tests = [
        test_performance_imports,
        test_ring_buffer,
        test_streaming_buffer, 
        test_performance_monitor,
        test_configuration,
        test_fps_counter,
        benchmark_ring_buffer
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
            failed += 1
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total: {passed + failed}")
    
    if failed == 0:
        print("\n🎉 All tests passed! Performance optimizations are working correctly.")
        return 0
    else:
        print(f"\n❌ {failed} test(s) failed. Please check the implementation.")
        return 1

if __name__ == '__main__':
    sys.exit(main())