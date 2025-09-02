# PyQtGraph Performance Optimization Guide for TradingView-like Applications

## Hướng dẫn tối ưu hóa hiệu năng PyQtGraph cho ứng dụng giao dịch tương tự TradingView

Tài liệu này cung cấp các phương pháp và kỹ thuật tối ưu hóa để xây dựng ứng dụng biểu đồ thời gian thực hiệu suất cao với PyQtGraph.

### 1. Cấu hình tối ưu hóa cơ bản

#### 1.1 Sử dụng OpenGL Acceleration
```python
import pyqtgraph as pg
from pyqtgraph.performance import TradingViewConfig

# Áp dụng cấu hình tối ưu cho trading
config = TradingViewConfig(
    enable_opengl=True,          # Bật gia tốc OpenGL
    mouse_rate_limit=120,        # Giới hạn tỷ lệ chuột 120Hz
    enable_antialiasing=False,   # Tắt antialiasing để tăng tốc
    enable_numba=True           # Bật Numba để tăng tốc tính toán
)
config.apply()
```

#### 1.2 Các preset cấu hình có sẵn
```python
from pyqtgraph.performance import apply_trading_config, apply_high_frequency_config

# Cho ứng dụng trading thông thường
apply_trading_config()

# Cho dữ liệu tần số cực cao
apply_high_frequency_config()
```

### 2. Quản lý dữ liệu streaming hiệu quả

#### 2.1 Sử dụng Ring Buffer cho dữ liệu thời gian thực
```python
from pyqtgraph.performance import RingBuffer, StreamingBuffer

# Buffer vòng tròn cho dữ liệu đơn chiều
price_buffer = RingBuffer(maxlen=10000, dtype=np.float64)

# Buffer cho dữ liệu X,Y (thời gian, giá)
xy_buffer = StreamingBuffer(maxlen=10000)

# Thêm dữ liệu mới
price_buffer.append(new_price)
xy_buffer.append(timestamp, price)

# Lấy dữ liệu gần nhất
recent_data = price_buffer.get_latest(1000)
x_data, y_data = xy_buffer.get_latest(1000)
```

#### 2.2 Buffer đa chuỗi cho OHLC và chỉ báo kỹ thuật
```python
from pyqtgraph.performance import MultiSeriesBuffer

# Buffer cho dữ liệu OHLC
ohlc_buffer = MultiSeriesBuffer(
    maxlen=10000,
    series_names=['open', 'high', 'low', 'close', 'volume']
)

# Thêm dữ liệu OHLC
ohlc_buffer.append(
    open=100.5,
    high=101.2, 
    low=99.8,
    close=100.9,
    volume=50000
)

# Lấy dữ liệu cho từng chuỗi
close_prices = ohlc_buffer.get_series('close')
all_data = ohlc_buffer.get_all_series()
```

### 3. Tối ưu hóa tín hiệu và cập nhật

#### 3.1 Signal Proxy cho tần số cao
```python
from pyqtgraph.performance import BatchedSignalProxy, RateLimitedSignalProxy

# Gộp nhiều tín hiệu thành batch để xử lý hiệu quả
batched_proxy = BatchedSignalProxy(
    signal=data_source.new_data,
    batch_size=10,                # Gộp 10 tín hiệu
    max_delay=0.1,               # Tối đa 100ms delay
    slot=update_chart_batch
)

# Giới hạn tỷ lệ cập nhật nhưng giữ giá trị mới nhất
rate_limited_proxy = RateLimitedSignalProxy(
    signal=price_updates,
    rate_limit=60,               # Tối đa 60 cập nhật/giây
    slot=update_price_display
)
```

#### 3.2 Adaptive Signal Proxy tự động điều chỉnh
```python
from pyqtgraph.performance import AdaptiveSignalProxy

# Tự động thay đổi chiến lược dựa trên tần số
adaptive_proxy = AdaptiveSignalProxy(
    signal=market_data.tick_received,
    low_freq_threshold=10,       # < 10Hz: cập nhật ngay lập tức
    high_freq_threshold=100,     # > 100Hz: sử dụng batching
    slot=handle_market_update
)
```

### 4. Threading để cập nhật không chặn

#### 4.1 Data Stream Thread
```python
from pyqtgraph.performance import DataStreamThread

def get_market_data():
    """Hàm lấy dữ liệu thị trường từ API hoặc feed"""
    return api_client.get_latest_tick()

# Thread xử lý dữ liệu nền
data_thread = DataStreamThread(
    data_source=get_market_data,
    update_interval=0.01,        # 100Hz polling
    buffer_size=1000
)

# Kết nối tín hiệu
data_thread.dataReceived.connect(process_new_data)
data_thread.start()
```

#### 4.2 Non-blocking Plot Updater
```python
from pyqtgraph.performance import NonBlockingUpdater

# Quản lý cập nhật plot không chặn GUI
updater = NonBlockingUpdater(max_updates_per_frame=10)

# Đăng ký plot items
updater.register_plot_item('price_chart', price_curve)
updater.register_plot_item('volume_chart', volume_bars)

# Queue cập nhật từ background thread
updater.queue_data_update('price_chart', x_data, y_data, priority=1)
```

#### 4.3 High-level Real-time Manager
```python
from pyqtgraph.performance import RealTimeDataManager

# Manager tổng hợp cho dữ liệu real-time
data_manager = RealTimeDataManager()

# Thêm data stream
data_manager.add_data_stream(
    stream_id='prices',
    data_source=get_market_data,
    plot_targets=['main_chart', 'mini_chart'],
    data_processor=process_tick_data,
    update_interval=0.02         # 50Hz
)

# Đăng ký plots
data_manager.register_plot('main_chart', main_price_curve)
data_manager.start_stream('prices')
```

### 5. Giám sát và đo lường hiệu năng

#### 5.1 Performance Monitor
```python
from pyqtgraph.performance import PerformanceMonitor

# Monitor hiệu năng tổng thể
perf_monitor = PerformanceMonitor()

# Đo thời gian các thao tác
with perf_monitor.timer('data_processing'):
    process_market_data(raw_data)

# Đếm events
perf_monitor.increment_counter('data_points_received')

# Tracking FPS
perf_monitor.tick_frame()  # Gọi mỗi frame

# Lấy thống kê
stats = perf_monitor.get_all_stats()
print(f"FPS: {stats['fps']['fps']:.1f}")
```

#### 5.2 FPS Counter riêng lẻ
```python
from pyqtgraph.performance import FPSCounter

fps_counter = FPSCounter(window_size=60)

# Trong paint event hoặc animation loop
def paintEvent(self, event):
    fps_counter.tick()
    # ... code vẽ ...
    
    current_fps = fps_counter.get_fps()
    frame_time = fps_counter.get_frame_time_ms()
```

### 6. Tối ưu hóa cài đặt plot

#### 6.1 Cài đặt ViewBox tối ưu
```python
# Tối ưu hóa ViewBox cho hiệu suất
plot_item.setClipToView(True)           # Chỉ vẽ phần nhìn thấy
plot_item.setDownsampling(mode='peak')   # Downsampling tự động
plot_item.setAutoDownsample(True)       # Bật auto-downsampling

# Giới hạn range để tăng hiệu suất
plot_item.setLimits(xMin=0, xMax=86400)  # 24 giờ
plot_item.setRange(xRange=[-3600, 0])    # Hiển thị 1 giờ gần nhất
```

#### 6.2 Tối ưu hóa PlotDataItem
```python
# Sử dụng pen tối ưu
fast_pen = pg.mkPen(color='w', width=1, cosmetic=True)

# Tạo curve với cài đặt tối ưu
price_curve = plot_item.plot(
    pen=fast_pen,
    connect='finite',       # Chỉ nối các điểm hữu hạn
    skipFiniteCheck=True,   # Bỏ qua kiểm tra finite
    antialias=False        # Tắt antialiasing
)

# Cập nhật dữ liệu hiệu quả
price_curve.setData(x_data, y_data, connect='all')
```

### 7. Ví dụ ứng dụng hoàn chỉnh

```python
import sys
import numpy as np
import pyqtgraph as pg
from pyqtgraph.performance import *

class TradingChart(pg.GraphicsLayoutWidget):
    def __init__(self):
        super().__init__()
        
        # Áp dụng cấu hình tối ưu
        apply_trading_config(enable_opengl=True, mouse_rate_limit=120)
        
        # Khởi tạo monitoring
        self.perf_monitor = PerformanceMonitor()
        
        # Tạo plots
        self.setup_plots()
        
        # Thiết lập data streaming
        self.setup_data_streaming()
    
    def setup_plots(self):
        """Thiết lập các plot với cài đặt tối ưu"""
        # Main price chart
        self.price_plot = self.addPlot(title="Price Chart")
        self.price_plot.setClipToView(True)
        self.price_plot.setDownsampling(mode='peak')
        
        # Price curve
        self.price_curve = self.price_plot.plot(
            pen=pg.mkPen('w', width=1),
            connect='finite'
        )
        
        # Volume chart  
        self.nextRow()
        self.volume_plot = self.addPlot(title="Volume")
        self.volume_bars = pg.BarGraphItem(x=[], height=[], width=1)
        self.volume_plot.addItem(self.volume_bars)
    
    def setup_data_streaming(self):
        """Thiết lập streaming dữ liệu real-time"""
        # Data buffers
        self.price_buffer = StreamingBuffer(maxlen=10000)
        self.volume_buffer = RingBuffer(maxlen=10000)
        
        # Real-time data manager
        self.data_manager = RealTimeDataManager()
        self.data_manager.register_plot('price', self.price_curve)
        
        # Add market data stream
        self.data_manager.add_data_stream(
            stream_id='market',
            data_source=self.get_market_data,
            plot_targets=['price'],
            update_interval=0.02  # 50Hz
        )
        
        self.data_manager.start_stream('market')
    
    def get_market_data(self):
        """Simulator dữ liệu thị trường"""
        timestamp = time.time()
        price = 100 + 10 * np.sin(timestamp * 0.1) + np.random.normal(0, 0.5)
        volume = np.random.randint(1000, 5000)
        
        return {'timestamp': timestamp, 'price': price, 'volume': volume}

# Chạy ứng dụng
if __name__ == '__main__':
    app = pg.mkQApp()
    chart = TradingChart()
    chart.show()
    app.exec()
```

### 8. Checklist tối ưu hóa

#### Performance Settings
- ✅ Bật OpenGL acceleration (`useOpenGL=True`)
- ✅ Tắt antialiasing (`antialias=False`)  
- ✅ Giới hạn mouse rate (`mouseRateLimit=120`)
- ✅ Bật Numba compilation (`useNumba=True`)
- ✅ Sử dụng segmented line mode (`segmentedLineMode='on'`)

#### Plot Optimization  
- ✅ Enable clipping to view (`setClipToView(True)`)
- ✅ Enable downsampling (`setDownsampling(mode='peak')`)
- ✅ Set appropriate plot limits
- ✅ Use cosmetic pens (`cosmetic=True`)
- ✅ Optimize connect mode (`connect='finite'`)

#### Data Management
- ✅ Sử dụng ring buffers cho dữ liệu streaming
- ✅ Batch multiple updates together
- ✅ Rate limit high-frequency signals
- ✅ Process data in background threads
- ✅ Queue updates for main thread

#### Memory Management
- ✅ Limit buffer sizes to reasonable values
- ✅ Clear old data regularly
- ✅ Use appropriate data types (float32 vs float64)
- ✅ Avoid memory leaks in signal connections

### 9. Benchmark và Testing

```python
# Test hiệu năng với data khác nhau
def benchmark_performance():
    configs = [
        {'name': 'Basic', 'opengl': False, 'antialias': True},
        {'name': 'Optimized', 'opengl': True, 'antialias': False},
    ]
    
    for config in configs:
        pg.setConfigOption('useOpenGL', config['opengl'])
        pg.setConfigOption('antialias', config['antialias'])
        
        # Đo FPS với 10000 điểm dữ liệu
        fps = measure_fps_with_data_points(10000)
        print(f"{config['name']}: {fps:.1f} FPS")
```

### 10. Xử lý sự cố thường gặp

#### 10.1 FPS thấp
- Kiểm tra OpenGL có được bật không
- Giảm số lượng điểm dữ liệu hiển thị
- Bật downsampling và clipping
- Tắt antialiasing
- Sử dụng cosmetic pens

#### 10.2 Lag khi có nhiều updates
- Sử dụng signal proxy để batch updates
- Giới hạn update rate
- Xử lý data trong background thread
- Queue updates thay vì cập nhật trực tiếp

#### 10.3 Memory usage cao
- Giới hạn kích thước buffer
- Clear data cũ định kỳ
- Sử dụng data type thích hợp
- Kiểm tra memory leaks

### Kết luận

Với các kỹ thuật tối ưu hóa này, bạn có thể xây dựng ứng dụng biểu đồ trading real-time hiệu suất cao tương tự TradingView. Các tính năng chính bao gồm:

1. **Cấu hình tối ưu**: OpenGL, rate limiting, Numba acceleration
2. **Data streaming hiệu quả**: Ring buffers, streaming buffers
3. **Signal processing thông minh**: Batching, rate limiting, adaptive proxies
4. **Threading không chặn**: Background data processing, queued updates
5. **Performance monitoring**: FPS tracking, timing measurements
6. **Plot optimization**: Clipping, downsampling, efficient rendering

Áp dụng các kỹ thuật này sẽ giúp ứng dụng của bạn đạt được hiệu suất cao nhất có thể với PyQtGraph.