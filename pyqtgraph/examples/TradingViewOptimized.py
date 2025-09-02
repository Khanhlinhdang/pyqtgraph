#!/usr/bin/env python3
"""
TradingView-like Real-time Chart Example

This example demonstrates how to use PyQtGraph's performance optimization
features to create a high-performance trading chart similar to TradingView.

Features demonstrated:
- Real-time data streaming
- Multiple technical indicators
- Optimized rendering with OpenGL
- High-frequency data handling
- Performance monitoring
"""

import sys
import time
import numpy as np
from typing import Optional

# Import PyQtGraph and performance optimizations
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets, QtGui
from pyqtgraph.performance import (
    TradingViewConfig, PerformanceMonitor, RealTimeDataManager,
    StreamingBuffer, RateLimitedSignalProxy
)


class MarketDataSimulator:
    """
    Simulates real-time market data for demonstration.
    
    Generates realistic price data with trends, volatility, and noise
    similar to actual market data.
    """
    
    def __init__(self, initial_price: float = 100.0, volatility: float = 0.02):
        self.price = initial_price
        self.volatility = volatility
        self.time = 0
        self.trend = 0.0001  # Small upward trend
        
        # Generate some historical data
        self.history_length = 1000
        self.prices = []
        self.timestamps = []
        
        for i in range(self.history_length):
            self.timestamps.append(i)
            self.prices.append(self._generate_next_price())
    
    def _generate_next_price(self) -> float:
        """Generate next price point."""
        # Random walk with trend and volatility
        change = (
            np.random.normal(0, self.volatility) +  # Random component
            self.trend +                             # Trend component
            0.001 * np.sin(self.time * 0.01)       # Cyclical component
        )
        
        self.price *= (1 + change)
        self.time += 1
        
        return self.price
    
    def get_next_tick(self) -> Optional[dict]:
        """Get next market tick."""
        timestamp = time.time()
        price = self._generate_next_price()
        
        # Store in history
        self.timestamps.append(timestamp)
        self.prices.append(price)
        
        # Keep only recent history
        if len(self.prices) > self.history_length:
            self.timestamps.pop(0)
            self.prices.pop(0)
        
        return {
            'timestamp': timestamp,
            'price': price,
            'volume': np.random.randint(100, 1000)
        }
    
    def get_historical_data(self) -> tuple:
        """Get historical price data."""
        return np.array(self.timestamps), np.array(self.prices)


class TechnicalIndicators:
    """
    Calculates common technical indicators for trading charts.
    """
    
    @staticmethod
    def sma(prices: np.ndarray, period: int) -> np.ndarray:
        """Simple Moving Average."""
        if len(prices) < period:
            return np.array([])
        
        return np.convolve(prices, np.ones(period) / period, mode='valid')
    
    @staticmethod
    def ema(prices: np.ndarray, period: int) -> np.ndarray:
        """Exponential Moving Average."""
        if len(prices) == 0:
            return np.array([])
        
        alpha = 2.0 / (period + 1)
        ema_values = [prices[0]]
        
        for price in prices[1:]:
            ema_values.append(alpha * price + (1 - alpha) * ema_values[-1])
        
        return np.array(ema_values)
    
    @staticmethod
    def rsi(prices: np.ndarray, period: int = 14) -> np.ndarray:
        """Relative Strength Index."""
        if len(prices) < period + 1:
            return np.array([])
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gains = np.convolve(gains, np.ones(period) / period, mode='valid')
        avg_losses = np.convolve(losses, np.ones(period) / period, mode='valid')
        
        rs = avg_gains / (avg_losses + 1e-10)  # Avoid division by zero
        rsi = 100 - (100 / (1 + rs))
        
        return rsi


class HighPerformanceTradingChart(QtWidgets.QMainWindow):
    """
    High-performance trading chart widget optimized for real-time updates.
    
    Demonstrates best practices for TradingView-like applications using
    PyQtGraph's performance optimization features.
    """
    
    def __init__(self):
        super().__init__()
        
        # Apply optimized configuration for trading
        self.config = TradingViewConfig(
            enable_opengl=True,
            mouse_rate_limit=120,
            enable_antialiasing=False,
            enable_numba=True
        )
        self.config.apply()
        
        # Initialize performance monitoring
        self.performance_monitor = PerformanceMonitor()
        
        # Initialize data components
        self.market_data = MarketDataSimulator()
        self.indicators = TechnicalIndicators()
        
        # Data buffers for efficient streaming
        self.price_buffer = StreamingBuffer(maxlen=10000)
        self.sma_buffer = StreamingBuffer(maxlen=10000)
        self.ema_buffer = StreamingBuffer(maxlen=10000)
        self.rsi_buffer = StreamingBuffer(maxlen=10000)
        
        # Setup UI
        self._setup_ui()
        
        # Setup real-time data management
        self._setup_data_streaming()
        
        # Start the simulation
        self._start_simulation()
    
    def _setup_ui(self):
        """Setup the user interface."""
        self.setWindowTitle("High-Performance Trading Chart - PyQtGraph")
        self.setGeometry(100, 100, 1200, 800)
        
        # Central widget with graphics layout
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QtWidgets.QVBoxLayout(central_widget)
        
        # Create graphics layout widget
        self.graphics_widget = pg.GraphicsLayoutWidget()
        layout.addWidget(self.graphics_widget)
        
        # Main price chart
        self.price_plot = self.graphics_widget.addPlot(
            title="Price Chart (Optimized for Real-time)",
            labels={'left': 'Price ($)', 'bottom': 'Time'}
        )
        
        # Enable auto-range and clipping for performance
        self.price_plot.enableAutoRange(axis='y')
        self.price_plot.setClipToView(True)
        self.price_plot.setDownsampling(mode='peak')
        
        # Add plots to next row
        self.graphics_widget.nextRow()
        
        # RSI indicator
        self.rsi_plot = self.graphics_widget.addPlot(
            title="RSI (14)",
            labels={'left': 'RSI', 'bottom': 'Time'}
        )
        self.rsi_plot.setClipToView(True)
        self.rsi_plot.setDownsampling(mode='peak')
        self.rsi_plot.setYRange(0, 100)
        
        # Add horizontal lines for RSI levels
        self.rsi_plot.addLine(y=70, pen=pg.mkPen('r', style=QtCore.Qt.DashLine))
        self.rsi_plot.addLine(y=30, pen=pg.mkPen('g', style=QtCore.Qt.DashLine))
        
        # Create plot curves
        self.price_curve = self.price_plot.plot(
            pen=pg.mkPen('w', width=1),
            name="Price"
        )
        
        self.sma_curve = self.price_plot.plot(
            pen=pg.mkPen('y', width=1),
            name="SMA(20)"
        )
        
        self.ema_curve = self.price_plot.plot(
            pen=pg.mkPen('c', width=1),
            name="EMA(20)"
        )
        
        self.rsi_curve = self.rsi_plot.plot(
            pen=pg.mkPen('m', width=1),
            name="RSI"
        )
        
        # Add legend
        self.price_plot.addLegend()
        
        # Status bar for performance info
        self.status_bar = self.statusBar()
        self.performance_label = QtWidgets.QLabel("Performance: Initializing...")
        self.status_bar.addWidget(self.performance_label)
        
        # Performance monitoring timer
        self.perf_timer = QtCore.QTimer()
        self.perf_timer.timeout.connect(self._update_performance_display)
        self.perf_timer.start(1000)  # Update every second
    
    def _setup_data_streaming(self):
        """Setup real-time data streaming."""
        # Create real-time data manager
        self.data_manager = RealTimeDataManager(max_updates_per_frame=15)
        
        # Register plot items
        self.data_manager.register_plot('price', self.price_curve)
        self.data_manager.register_plot('sma', self.sma_curve)
        self.data_manager.register_plot('ema', self.ema_curve)
        self.data_manager.register_plot('rsi', self.rsi_curve)
        
        # Add data stream for market data
        self.data_manager.add_data_stream(
            stream_id='market_data',
            data_source=self._get_market_data,
            plot_targets=['price'],
            data_processor=self._process_market_data,
            update_interval=0.05,  # 20Hz updates
            buffer_size=1000
        )
        
        # Rate-limited signal for indicator updates
        self.indicator_timer = QtCore.QTimer()
        self.indicator_timer.timeout.connect(self._update_indicators)
        self.indicator_timer.start(100)  # Update indicators at 10Hz
    
    def _get_market_data(self):
        """Get next market data point."""
        return self.market_data.get_next_tick()
    
    def _process_market_data(self, data):
        """Process raw market data for plotting."""
        if data is None:
            return None
        
        # Add to price buffer
        timestamp = data['timestamp']
        price = data['price']
        self.price_buffer.append(timestamp, price)
        
        # Get recent data for plotting
        x_data, y_data = self.price_buffer.get_latest(1000)
        
        # Record performance metrics
        self.performance_monitor.increment_counter('data_points')
        
        with self.performance_monitor.timer('data_processing'):
            return {'x': x_data, 'y': y_data}
    
    def _update_indicators(self):
        """Update technical indicators."""
        with self.performance_monitor.timer('indicator_calculation'):
            try:
                # Get current price data
                x_data, y_data = self.price_buffer.get_data()
                
                if len(y_data) < 20:
                    return  # Need minimum data for indicators
                
                # Calculate indicators
                sma_values = self.indicators.sma(y_data, 20)
                ema_values = self.indicators.ema(y_data, 20)
                rsi_values = self.indicators.rsi(y_data, 14)
                
                # Update SMA
                if len(sma_values) > 0:
                    sma_x = x_data[-len(sma_values):]
                    self.sma_buffer.clear()
                    self.sma_buffer.extend(sma_x, sma_values)
                    self.data_manager.updater.queue_data_update(
                        'sma', sma_x, sma_values, priority=1
                    )
                
                # Update EMA
                if len(ema_values) > 0:
                    ema_x = x_data[-len(ema_values):]
                    self.ema_buffer.clear()
                    self.ema_buffer.extend(ema_x, ema_values)
                    self.data_manager.updater.queue_data_update(
                        'ema', ema_x, ema_values, priority=1
                    )
                
                # Update RSI
                if len(rsi_values) > 0:
                    rsi_x = x_data[-len(rsi_values):]
                    self.rsi_buffer.clear()
                    self.rsi_buffer.extend(rsi_x, rsi_values)
                    self.data_manager.updater.queue_data_update(
                        'rsi', rsi_x, rsi_values, priority=1
                    )
                
                self.performance_monitor.increment_counter('indicator_updates')
                
            except Exception as e:
                print(f"Error updating indicators: {e}")
    
    def _start_simulation(self):
        """Start the market data simulation."""
        # Load historical data
        hist_x, hist_y = self.market_data.get_historical_data()
        self.price_buffer.extend(hist_x, hist_y)
        
        # Initial plot of historical data
        self.data_manager.updater.queue_data_update('price', hist_x, hist_y)
        
        # Start the data stream
        self.data_manager.start_stream('market_data')
        
        # Update indicators with historical data
        self._update_indicators()
    
    def _update_performance_display(self):
        """Update performance display in status bar."""
        self.performance_monitor.tick_frame()
        stats = self.performance_monitor.get_all_stats()
        
        fps = stats['fps']['fps']
        data_points = stats['counters'].get('data_points', 0)
        indicator_updates = stats['counters'].get('indicator_updates', 0)
        
        perf_text = (f"FPS: {fps:.1f} | "
                    f"Data Points: {data_points} | "
                    f"Indicator Updates: {indicator_updates}")
        
        self.performance_label.setText(perf_text)
    
    def closeEvent(self, event):
        """Clean up when closing."""
        self.data_manager.cleanup()
        event.accept()


def main():
    """Main application entry point."""
    # Create QApplication
    app = pg.mkQApp("Trading Chart Example")
    
    # Create and show the trading chart
    chart = HighPerformanceTradingChart()
    chart.show()
    
    # Show performance monitor window
    perf_widget = chart.performance_monitor.get_realtime_widget()
    if hasattr(chart.performance_monitor, 'get_realtime_widget'):
        # Would show performance widget if implemented
        pass
    
    # Print optimization tips
    print("=== PyQtGraph Trading Chart Optimization Example ===")
    print("Optimizations applied:")
    print("- OpenGL acceleration enabled")
    print("- Anti-aliasing disabled for performance")  
    print("- Mouse rate limiting (120Hz)")
    print("- Data clipping to view enabled")
    print("- Automatic downsampling enabled")
    print("- High-frequency data streaming (20Hz)")
    print("- Rate-limited indicator updates (10Hz)")
    print("- Thread-safe data buffers")
    print("- Performance monitoring active")
    print("\nPress Ctrl+C to exit")
    
    # Run the application
    if sys.flags.interactive != 1 or not hasattr(QtCore, 'PYQT_VERSION'):
        app.exec()


if __name__ == '__main__':
    main()