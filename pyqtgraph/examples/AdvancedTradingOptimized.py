#!/usr/bin/env python3
"""
Advanced TradingView Performance Optimizations

This example demonstrates advanced optimization techniques specifically
for trading applications including:
- OHLC candlestick charts with high-frequency updates
- Multiple technical indicators 
- Real-time order book visualization
- Volume profile analysis
- Multi-timeframe support
"""

import sys
import time
import numpy as np
from collections import deque
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets, QtGui

# Import our performance optimizations
try:
    from pyqtgraph.performance import *
except ImportError:
    print("Performance module not found. Running with basic PyQtGraph.")
    
    # Fallback implementations
    class TradingViewConfig:
        def __init__(self, **kwargs): pass
        def apply(self): pass
    
    class PerformanceMonitor:
        def __init__(self): pass
        def timer(self, name): return self
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def increment_counter(self, name, amount=1): pass
        def tick_frame(self): pass
        def get_all_stats(self): return {'fps': {'fps': 0}, 'counters': {}}


class TimeFrame(Enum):
    """Trading timeframes."""
    TICK = "tick"
    M1 = "1m" 
    M5 = "5m"
    M15 = "15m"
    H1 = "1h"
    D1 = "1d"


@dataclass
class OHLCV:
    """OHLC + Volume data structure."""
    timestamp: float
    open: float
    high: float  
    low: float
    close: float
    volume: int


@dataclass
class OrderBookLevel:
    """Order book level data."""
    price: float
    size: int
    side: str  # 'bid' or 'ask'


class AdvancedMarketSimulator:
    """
    Advanced market data simulator with realistic OHLC, order book,
    and multi-timeframe data generation.
    """
    
    def __init__(self, symbol: str = "BTCUSD", initial_price: float = 50000):
        self.symbol = symbol
        self.price = initial_price
        self.volume_profile = {}
        
        # OHLC data for different timeframes
        self.ohlc_data: Dict[TimeFrame, List[OHLCV]] = {tf: [] for tf in TimeFrame}
        
        # Current tick data
        self.current_tick_price = initial_price
        self.tick_count = 0
        
        # Order book simulation
        self.order_book_bids = []
        self.order_book_asks = []
        
        # Generate some historical data
        self._generate_historical_data()
    
    def _generate_historical_data(self):
        """Generate historical OHLC data for different timeframes."""
        # Generate 1000 minutes of M1 data
        base_time = time.time() - 1000 * 60
        
        for i in range(1000):
            timestamp = base_time + i * 60
            
            # Generate M1 OHLC
            open_price = self.price
            
            # Random walk for the minute
            high_price = open_price * (1 + np.random.exponential(0.001))
            low_price = open_price * (1 - np.random.exponential(0.001))
            close_price = open_price + np.random.normal(0, open_price * 0.002)
            volume = np.random.randint(50, 500)
            
            self.price = close_price
            
            ohlcv = OHLCV(timestamp, open_price, high_price, low_price, close_price, volume)
            self.ohlc_data[TimeFrame.M1].append(ohlcv)
        
        # Aggregate to higher timeframes
        self._aggregate_timeframes()
    
    def _aggregate_timeframes(self):
        """Aggregate M1 data to higher timeframes."""
        m1_data = self.ohlc_data[TimeFrame.M1]
        
        # 5-minute aggregation
        for i in range(0, len(m1_data), 5):
            chunk = m1_data[i:i+5]
            if chunk:
                agg = self._aggregate_ohlcv_chunk(chunk)
                self.ohlc_data[TimeFrame.M5].append(agg)
        
        # 15-minute aggregation  
        m5_data = self.ohlc_data[TimeFrame.M5]
        for i in range(0, len(m5_data), 3):
            chunk = m5_data[i:i+3]
            if chunk:
                agg = self._aggregate_ohlcv_chunk(chunk)
                self.ohlc_data[TimeFrame.M15].append(agg)
    
    def _aggregate_ohlcv_chunk(self, chunk: List[OHLCV]) -> OHLCV:
        """Aggregate a chunk of OHLCV data."""
        if not chunk:
            return None
        
        return OHLCV(
            timestamp=chunk[0].timestamp,
            open=chunk[0].open,
            high=max(bar.high for bar in chunk),
            low=min(bar.low for bar in chunk), 
            close=chunk[-1].close,
            volume=sum(bar.volume for bar in chunk)
        )
    
    def get_next_tick(self) -> dict:
        """Generate next price tick."""
        # Realistic price movement
        volatility = 0.001
        trend = 0.0001 if np.random.random() > 0.5 else -0.0001
        
        price_change = np.random.normal(trend, volatility)
        self.current_tick_price *= (1 + price_change)
        
        volume = np.random.randint(1, 50)
        self.tick_count += 1
        
        return {
            'timestamp': time.time(),
            'price': self.current_tick_price,
            'volume': volume,
            'tick_id': self.tick_count
        }
    
    def get_order_book_update(self) -> List[OrderBookLevel]:
        """Generate order book update."""
        levels = []
        mid_price = self.current_tick_price
        
        # Generate bid levels
        for i in range(5):
            price = mid_price * (1 - (i + 1) * 0.0001)
            size = np.random.randint(10, 1000)
            levels.append(OrderBookLevel(price, size, 'bid'))
        
        # Generate ask levels
        for i in range(5):
            price = mid_price * (1 + (i + 1) * 0.0001)
            size = np.random.randint(10, 1000)
            levels.append(OrderBookLevel(price, size, 'ask'))
        
        return levels
    
    def get_ohlc_data(self, timeframe: TimeFrame, limit: int = 100) -> List[OHLCV]:
        """Get OHLC data for a specific timeframe."""
        data = self.ohlc_data.get(timeframe, [])
        return data[-limit:] if data else []


class CandlestickChartItem(pg.GraphicsObject):
    """
    Optimized candlestick chart item for high-performance OHLC visualization.
    
    Uses efficient drawing techniques and caching for smooth real-time updates.
    """
    
    def __init__(self):
        super().__init__()
        self.data = []
        self.picture = None
        self.width = 0.8
        
    def setData(self, ohlc_data: List[OHLCV]):
        """Set OHLC data and trigger redraw."""
        self.data = ohlc_data
        self.picture = None  # Clear cache
        self.informViewBoundsChanged()
        self.update()
    
    def generatePicture(self):
        """Generate the picture for efficient drawing."""
        self.picture = QtGui.QPicture()
        painter = QtGui.QPainter(self.picture)
        
        if not self.data:
            painter.end()
            return
        
        # Set up pens for bull/bear candles
        bull_pen = pg.mkPen(color='g', width=1)
        bear_pen = pg.mkPen(color='r', width=1)
        bull_brush = pg.mkBrush('g')
        bear_brush = pg.mkBrush('r')
        
        for i, candle in enumerate(self.data):
            x = i
            
            # Determine if bullish or bearish
            is_bull = candle.close >= candle.open
            pen = bull_pen if is_bull else bear_pen
            brush = bull_brush if is_bull else bear_brush
            
            painter.setPen(pen)
            
            # Draw high-low line
            painter.drawLine(QtCore.QPointF(x, candle.low), QtCore.QPointF(x, candle.high))
            
            # Draw body rectangle
            body_height = abs(candle.close - candle.open)
            if body_height > 0:
                body_top = max(candle.open, candle.close)
                body_rect = QtCore.QRectF(x - self.width/2, body_top - body_height, 
                                        self.width, body_height)
                
                painter.fillRect(body_rect, brush)
                painter.drawRect(body_rect)
        
        painter.end()
    
    def paint(self, painter, option, widget):
        """Paint the candlestick chart."""
        if self.picture is None:
            self.generatePicture()
        
        self.picture.play(painter)
    
    def boundingRect(self):
        """Return bounding rectangle."""
        if not self.data:
            return QtCore.QRectF()
        
        min_price = min(min(c.low for c in self.data), min(c.high for c in self.data))
        max_price = max(max(c.low for c in self.data), max(c.high for c in self.data))
        
        return QtCore.QRectF(0, min_price, len(self.data), max_price - min_price)


class OrderBookVisualization(pg.GraphicsObject):
    """
    Optimized order book visualization with depth chart.
    """
    
    def __init__(self):
        super().__init__()
        self.bids = []
        self.asks = []
        self.picture = None
        self.max_depth = 10
    
    def setData(self, order_book_levels: List[OrderBookLevel]):
        """Update order book data."""
        self.bids = [level for level in order_book_levels if level.side == 'bid']
        self.asks = [level for level in order_book_levels if level.side == 'ask']
        
        # Sort bids (highest first) and asks (lowest first)
        self.bids.sort(key=lambda x: x.price, reverse=True)
        self.asks.sort(key=lambda x: x.price)
        
        self.picture = None
        self.update()
    
    def generatePicture(self):
        """Generate order book picture."""
        self.picture = QtGui.QPicture()
        painter = QtGui.QPainter(self.picture)
        
        if not self.bids and not self.asks:
            painter.end()
            return
        
        # Draw bid side (green)
        bid_brush = pg.mkBrush(color=(0, 255, 0, 100))
        cumulative_size = 0
        
        for level in self.bids:
            cumulative_size += level.size
            rect = QtCore.QRectF(0, level.price, cumulative_size/100, 0.1)
            painter.fillRect(rect, bid_brush)
        
        # Draw ask side (red)  
        ask_brush = pg.mkBrush(color=(255, 0, 0, 100))
        cumulative_size = 0
        
        for level in self.asks:
            cumulative_size += level.size
            rect = QtCore.QRectF(0, level.price, cumulative_size/100, 0.1)
            painter.fillRect(rect, ask_brush)
        
        painter.end()
    
    def paint(self, painter, option, widget):
        """Paint the order book."""
        if self.picture is None:
            self.generatePicture()
        
        self.picture.play(painter)
    
    def boundingRect(self):
        """Return bounding rectangle."""
        if not self.bids and not self.asks:
            return QtCore.QRectF()
        
        all_levels = self.bids + self.asks
        min_price = min(level.price for level in all_levels)
        max_price = max(level.price for level in all_levels)
        max_size = max(level.size for level in all_levels)
        
        return QtCore.QRectF(0, min_price, max_size/100, max_price - min_price)


class AdvancedTradingInterface(QtWidgets.QMainWindow):
    """
    Advanced trading interface with multiple optimized charts and real-time data.
    """
    
    def __init__(self):
        super().__init__()
        
        # Apply high-performance configuration
        self.config = TradingViewConfig(
            enable_opengl=True,
            mouse_rate_limit=120,
            enable_antialiasing=False,
            enable_numba=True
        )
        self.config.apply()
        
        # Performance monitoring
        self.perf_monitor = PerformanceMonitor()
        
        # Market data simulator
        self.market_sim = AdvancedMarketSimulator()
        self.current_timeframe = TimeFrame.M1
        
        # Setup UI
        self._setup_ui()
        self._setup_charts()
        self._setup_data_feeds()
        
        # Start real-time updates
        self._start_real_time_updates()
    
    def _setup_ui(self):
        """Setup the user interface."""
        self.setWindowTitle("Advanced Trading Interface - PyQtGraph Optimized")
        self.setGeometry(100, 100, 1600, 1000)
        
        # Central widget
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QtWidgets.QHBoxLayout(central_widget)
        
        # Left panel for charts
        chart_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        main_layout.addWidget(chart_splitter, stretch=3)
        
        # Graphics layout for charts
        self.graphics_widget = pg.GraphicsLayoutWidget()
        chart_splitter.addWidget(self.graphics_widget)
        
        # Right panel for order book and controls
        right_panel = QtWidgets.QWidget()
        right_panel.setMaximumWidth(300)
        main_layout.addWidget(right_panel)
        
        right_layout = QtWidgets.QVBoxLayout(right_panel)
        
        # Timeframe selection
        tf_group = QtWidgets.QGroupBox("Timeframe")
        tf_layout = QtWidgets.QHBoxLayout(tf_group)
        
        self.tf_buttons = {}
        for tf in [TimeFrame.M1, TimeFrame.M5, TimeFrame.M15]:
            btn = QtWidgets.QPushButton(tf.value)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, t=tf: self._change_timeframe(t))
            tf_layout.addWidget(btn)
            self.tf_buttons[tf] = btn
        
        self.tf_buttons[TimeFrame.M1].setChecked(True)
        right_layout.addWidget(tf_group)
        
        # Performance display
        perf_group = QtWidgets.QGroupBox("Performance")
        perf_layout = QtWidgets.QVBoxLayout(perf_group)
        
        self.fps_label = QtWidgets.QLabel("FPS: --")
        self.updates_label = QtWidgets.QLabel("Updates: --")
        self.memory_label = QtWidgets.QLabel("Memory: --")
        
        perf_layout.addWidget(self.fps_label)
        perf_layout.addWidget(self.updates_label)
        perf_layout.addWidget(self.memory_label)
        
        right_layout.addWidget(perf_group)
        
        # Order book widget  
        ob_group = QtWidgets.QGroupBox("Order Book")
        ob_layout = QtWidgets.QVBoxLayout(ob_group)
        
        self.order_book_widget = pg.GraphicsLayoutWidget()
        self.order_book_widget.setMaximumHeight(300)
        ob_layout.addWidget(self.order_book_widget)
        
        right_layout.addWidget(ob_group)
        
        # Spacer
        right_layout.addStretch()
        
        # Status bar
        self.status_bar = self.statusBar()
        self.status_label = QtWidgets.QLabel("Ready")
        self.status_bar.addWidget(self.status_label)
    
    def _setup_charts(self):
        """Setup the trading charts."""
        # Main price chart with candlesticks
        self.price_plot = self.graphics_widget.addPlot(
            title=f"Price Chart - {self.current_timeframe.value.upper()}",
            labels={'left': 'Price ($)', 'bottom': 'Time'}
        )
        
        # Optimize plot settings
        self.price_plot.setClipToView(True)
        self.price_plot.setDownsampling(mode='peak')
        self.price_plot.enableAutoRange(axis='y')
        
        # Add candlestick chart
        self.candlestick_item = CandlestickChartItem()
        self.price_plot.addItem(self.candlestick_item)
        
        # Volume overlay
        self.volume_plot = self.graphics_widget.addPlot(
            title="Volume",
            labels={'left': 'Volume', 'bottom': 'Time'}
        )
        self.volume_plot.setClipToView(True)
        
        # Technical indicators
        self.graphics_widget.nextRow()
        
        # RSI
        self.rsi_plot = self.graphics_widget.addPlot(
            title="RSI (14)",
            labels={'left': 'RSI', 'bottom': 'Time'}
        )
        self.rsi_plot.setClipToView(True)
        self.rsi_plot.setYRange(0, 100)
        
        # Add RSI levels
        self.rsi_plot.addLine(y=70, pen=pg.mkPen('r', style=QtCore.Qt.DashLine))
        self.rsi_plot.addLine(y=30, pen=pg.mkPen('g', style=QtCore.Qt.DashLine))
        
        self.rsi_curve = self.rsi_plot.plot(pen=pg.mkPen('y', width=1))
        
        # MACD
        self.macd_plot = self.graphics_widget.addPlot(
            title="MACD",
            labels={'left': 'MACD', 'bottom': 'Time'}
        )
        self.macd_plot.setClipToView(True)
        
        self.macd_line = self.macd_plot.plot(pen=pg.mkPen('b', width=1), name='MACD')
        self.signal_line = self.macd_plot.plot(pen=pg.mkPen('r', width=1), name='Signal')
        
        # Order book chart
        self.ob_plot = self.order_book_widget.addPlot(
            title="Order Book Depth",
            labels={'left': 'Price', 'bottom': 'Cumulative Size'}
        )
        
        self.order_book_viz = OrderBookVisualization()
        self.ob_plot.addItem(self.order_book_viz)
    
    def _setup_data_feeds(self):
        """Setup real-time data feeds."""
        # Tick data timer
        self.tick_timer = QtCore.QTimer()
        self.tick_timer.timeout.connect(self._update_tick_data)
        
        # OHLC update timer
        self.ohlc_timer = QtCore.QTimer()
        self.ohlc_timer.timeout.connect(self._update_ohlc_data)
        
        # Order book timer
        self.ob_timer = QtCore.QTimer()
        self.ob_timer.timeout.connect(self._update_order_book)
        
        # Performance monitoring timer
        self.perf_timer = QtCore.QTimer()
        self.perf_timer.timeout.connect(self._update_performance_display)
        self.perf_timer.start(1000)  # 1 second
    
    def _start_real_time_updates(self):
        """Start all real-time data updates."""
        self.tick_timer.start(50)    # 20Hz tick updates
        self.ohlc_timer.start(1000)  # 1Hz OHLC updates  
        self.ob_timer.start(200)     # 5Hz order book updates
        
        # Load initial data
        self._load_initial_data()
    
    def _load_initial_data(self):
        """Load initial historical data."""
        ohlc_data = self.market_sim.get_ohlc_data(self.current_timeframe, 100)
        
        if ohlc_data:
            with self.perf_monitor.timer('initial_data_load'):
                self.candlestick_item.setData(ohlc_data)
                self._update_technical_indicators(ohlc_data)
    
    def _update_tick_data(self):
        """Update with new tick data."""
        with self.perf_monitor.timer('tick_update'):
            tick = self.market_sim.get_next_tick()
            
            # Update current price display
            self.status_label.setText(f"Price: ${tick['price']:.2f}")
            
            self.perf_monitor.increment_counter('ticks_processed')
    
    def _update_ohlc_data(self):
        """Update OHLC candlestick data."""
        with self.perf_monitor.timer('ohlc_update'):
            ohlc_data = self.market_sim.get_ohlc_data(self.current_timeframe, 100)
            
            if ohlc_data:
                self.candlestick_item.setData(ohlc_data)
                self._update_technical_indicators(ohlc_data)
                
            self.perf_monitor.increment_counter('ohlc_updates')
    
    def _update_order_book(self):
        """Update order book visualization."""
        with self.perf_monitor.timer('order_book_update'):
            ob_levels = self.market_sim.get_order_book_update()
            self.order_book_viz.setData(ob_levels)
            
            self.perf_monitor.increment_counter('order_book_updates')
    
    def _update_technical_indicators(self, ohlc_data: List[OHLCV]):
        """Update technical indicator charts."""
        if len(ohlc_data) < 20:
            return
        
        with self.perf_monitor.timer('indicator_calculation'):
            # Extract prices
            closes = np.array([candle.close for candle in ohlc_data])
            
            # Calculate RSI
            if len(closes) >= 15:
                rsi_values = self._calculate_rsi(closes, 14)
                if len(rsi_values) > 0:
                    x_data = np.arange(len(ohlc_data) - len(rsi_values), len(ohlc_data))
                    self.rsi_curve.setData(x_data, rsi_values)
            
            # Calculate MACD
            if len(closes) >= 26:
                macd_line, signal_line = self._calculate_macd(closes)
                if len(macd_line) > 0:
                    x_data = np.arange(len(ohlc_data) - len(macd_line), len(ohlc_data))
                    self.macd_line.setData(x_data, macd_line)
                    self.signal_line.setData(x_data, signal_line)
    
    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> np.ndarray:
        """Calculate RSI indicator."""
        if len(prices) < period + 1:
            return np.array([])
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gains = np.convolve(gains, np.ones(period) / period, mode='valid')
        avg_losses = np.convolve(losses, np.ones(period) / period, mode='valid')
        
        rs = avg_gains / (avg_losses + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_macd(self, prices: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[np.ndarray, np.ndarray]:
        """Calculate MACD indicator."""
        if len(prices) < slow:
            return np.array([]), np.array([])
        
        # Calculate EMAs
        ema_fast = self._calculate_ema(prices, fast)
        ema_slow = self._calculate_ema(prices, slow)
        
        # MACD line
        macd_line = ema_fast[-len(ema_slow):] - ema_slow
        
        # Signal line
        signal_line = self._calculate_ema(macd_line, signal)
        
        return macd_line[-len(signal_line):], signal_line
    
    def _calculate_ema(self, prices: np.ndarray, period: int) -> np.ndarray:
        """Calculate Exponential Moving Average."""
        if len(prices) == 0:
            return np.array([])
        
        alpha = 2.0 / (period + 1)
        ema_values = [prices[0]]
        
        for price in prices[1:]:
            ema_values.append(alpha * price + (1 - alpha) * ema_values[-1])
        
        return np.array(ema_values)
    
    def _change_timeframe(self, timeframe: TimeFrame):
        """Change the chart timeframe."""
        self.current_timeframe = timeframe
        
        # Update button states
        for tf, btn in self.tf_buttons.items():
            btn.setChecked(tf == timeframe)
        
        # Update chart title
        self.price_plot.setTitle(f"Price Chart - {timeframe.value.upper()}")
        
        # Reload data for new timeframe
        self._load_initial_data()
    
    def _update_performance_display(self):
        """Update performance metrics display."""
        self.perf_monitor.tick_frame()
        stats = self.perf_monitor.get_all_stats()
        
        fps = stats['fps']['fps']
        counters = stats['counters']
        
        self.fps_label.setText(f"FPS: {fps:.1f}")
        self.updates_label.setText(f"Updates: {counters.get('ohlc_updates', 0)}")
        
        # Memory usage (simplified)
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        self.memory_label.setText(f"Memory: {memory_mb:.1f} MB")
    
    def closeEvent(self, event):
        """Clean up when closing."""
        self.tick_timer.stop()
        self.ohlc_timer.stop()
        self.ob_timer.stop()
        self.perf_timer.stop()
        event.accept()


def main():
    """Main application entry point."""
    app = pg.mkQApp("Advanced Trading Interface")
    
    # Create the main interface
    interface = AdvancedTradingInterface()
    interface.show()
    
    print("=== Advanced Trading Interface ===")
    print("Features:")
    print("- Real-time OHLC candlestick charts")
    print("- Technical indicators (RSI, MACD)")
    print("- Order book depth visualization")
    print("- Multi-timeframe support")
    print("- Performance monitoring")
    print("- OpenGL acceleration")
    print()
    print("Performance optimizations:")
    print("- Optimized candlestick rendering")
    print("- Efficient data structures")
    print("- Rate-limited updates")
    print("- Clipping and downsampling")
    print("- Memory management")
    
    if sys.flags.interactive != 1:
        app.exec()


if __name__ == '__main__':
    main()