import pyqtgraph as pg
import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QScrollBar
from PyQt6.QtCore import Qt, pyqtSignal
from src.data.eeg_model import EEGDataModel

class TimeSeriesPlot(QWidget):
    channels_loaded = pyqtSignal(list)
    effective_downsample_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        
        self.data_model = None
        self.raw_data = None
        self.times = None
        self.n_channels = 0
        self.offset_step = 0
        self.total_duration = 0
        self.visible_channels_indices = []
        
        self.current_x_range = (0, 10)
        self.samples_per_pixel = 1
        self.downsample_override = 0
        self.visible_duration = 10
        
        self.locked_duration = None
        self.scroll_step = None
        
        self.graphics_layout = pg.GraphicsLayoutWidget()
        self.graphics_layout.setBackground('w')
        self.layout().addWidget(self.graphics_layout)
        
        self.plot_item = self.graphics_layout.addPlot()
        self.plot_item.setLabel('bottom', 'Time', units='s')
        self.plot_item.setLabel('left', 'Channels')
        self.plot_item.showGrid(x=True, y=True)
        
        self.plot_item.setMouseEnabled(x=False, y=False)
        self.plot_item.setMenuEnabled(False)
        
        self.curves = []
        
        self.scrollbar = QScrollBar(Qt.Orientation.Horizontal)
        self.layout().addWidget(self.scrollbar)
        
        self.scrollbar.valueChanged.connect(self.on_scrollbar_changed)
        
        self.sigXRangeChanged = self.plot_item.sigXRangeChanged
        self.plot_item.sigXRangeChanged.connect(self.on_x_range_changed)
        
        self._scrollbar_blocking = False

    def set_locked_view(self, duration: float, step: float):
        self.locked_duration = duration
        self.scroll_step = step
        self.visible_duration = duration
        start = self.current_x_range[0]
        end = min(self.total_duration, start + duration)
        self.plot_item.setXRange(start, end, padding=0)
        self.current_x_range = (start, end)
        self._update_scrollbar()

    def unlock_view(self):
        self.locked_duration = None
        self.scroll_step = None
        self._update_scrollbar()

    def wheelEvent(self, event):
        """Overrides mouse wheel to zoom with a fixed start point or scroll if locked."""
        delta = event.angleDelta().y()
        
        if self.locked_duration is not None:
            # Scroll instead of zoom
            step = int(self.scroll_step * 1000) if self.scroll_step else int(self.visible_duration * 100)
            if delta > 0:
                self.scrollbar.setValue(self.scrollbar.value() - step)
            else:
                self.scrollbar.setValue(self.scrollbar.value() + step)
            event.accept()
            return
            
        if delta > 0:
            self.zoom_fixed_start(0.9)
        else:
            self.zoom_fixed_start(1.1)
        event.accept()

    def on_scrollbar_changed(self, value):
        if self._scrollbar_blocking:
            return
        
        start_time = value / 1000.0
        
        if self.locked_duration is not None:
            end_time = start_time + self.locked_duration
        else:
            end_time = start_time + self.visible_duration
            if end_time > self.total_duration:
                end_time = self.total_duration
                start_time = max(0, end_time - self.visible_duration)
        
        self.plot_item.setXRange(start_time, end_time, padding=0)
        self.current_x_range = (start_time, end_time)
        self.update_visible_data()

    def on_x_range_changed(self, _, x_range):
        if self.locked_duration is not None:
            if abs((x_range[1] - x_range[0]) - self.locked_duration) > 0.01:
                self.plot_item.sigXRangeChanged.disconnect(self.on_x_range_changed)
                end = x_range[0] + self.locked_duration
                self.plot_item.setXRange(x_range[0], end, padding=0)
                self.plot_item.sigXRangeChanged.connect(self.on_x_range_changed)
                x_range = (x_range[0], end)

        self.current_x_range = x_range
        self.visible_duration = x_range[1] - x_range[0]
        self._update_scrollbar()

    def _update_scrollbar(self):
        self._scrollbar_blocking = True
        scrollbar_value = int(self.current_x_range[0] * 1000)
        page_step = int(self.visible_duration * 1000)
        
        if self.scroll_step and self.locked_duration is not None:
            self.scrollbar.setSingleStep(int(self.scroll_step * 1000))
        else:
            self.scrollbar.setSingleStep(max(1, page_step // 10))
            
        self.scrollbar.blockSignals(True)
        self.scrollbar.setMaximum(int(max(0, self.total_duration - self.visible_duration) * 1000))
        self.scrollbar.setValue(scrollbar_value)
        self.scrollbar.setPageStep(page_step)
        self.scrollbar.blockSignals(False)
        
        self._scrollbar_blocking = False
        self.update_visible_data()

    def zoom_fixed_start(self, factor: float):
        if self.locked_duration is not None:
            return # Block zooming if locked

        start = self.current_x_range[0]
        new_duration = self.visible_duration * factor
        new_duration = max(0.1, min(new_duration, self.total_duration))
        end = min(self.total_duration, start + new_duration)
        
        self.plot_item.setXRange(start, end, padding=0)

    def set_visible_channels(self, indices: list):
        self.visible_channels_indices = sorted(indices)
        self.refresh_plot_layout()

    def plot_data(self, model: EEGDataModel):
        print(f"TimeSeriesPlot: Loading new model {model.filename}")
        self.data_model = model
        self.raw_data, self.times = model.get_data()
        
        if self.raw_data is None:
            print("TimeSeriesPlot: No data found.")
            return

        self.n_channels = self.raw_data.shape[0]
        self.total_duration = self.times[-1] if len(self.times) > 0 else 0
        self.visible_channels_indices = list(range(self.n_channels))
        
        data_std = np.std(self.raw_data) if self.raw_data.size > 0 else 1.0
        self.offset_step = (data_std if data_std > 0 else 1.0) * 5
        
        self.refresh_plot_layout()
        
        if self.locked_duration is None:
            initial_duration = min(10, self.total_duration)
        else:
            initial_duration = self.locked_duration
            
        self.plot_item.setXRange(0, initial_duration, padding=0)
        self.current_x_range = (0, initial_duration)
        self.visible_duration = initial_duration
        self._update_scrollbar()

        self.channels_loaded.emit(self.data_model.channel_names)
        print("TimeSeriesPlot: plot_data completed.")

    def refresh_data_only(self):
        if self.data_model:
            print("TimeSeriesPlot: Refreshing data only...")
            self.raw_data, self.times = self.data_model.get_data()
            self.update_visible_data()

    def refresh_plot_layout(self):
        self.clear_curves()
        if not self.visible_channels_indices or self.data_model is None:
            return

        yticks = []
        n_vis = len(self.visible_channels_indices)
        for i, ch_idx in enumerate(self.visible_channels_indices):
            y_offset = (n_vis - 1 - i) * self.offset_step
            ch_name = self.data_model.channel_names[ch_idx]
            yticks.append((y_offset, ch_name))
            
            curve = self.plot_item.plot(pen=pg.mkPen(color='k', width=1))
            self.curves.append((curve, y_offset, ch_idx))

        self.plot_item.getAxis('left').setTicks([yticks])
        
        y_min = -self.offset_step
        y_max = n_vis * self.offset_step
        self.plot_item.setLimits(yMin=y_min, yMax=y_max)
        self.plot_item.setYRange(y_min, y_max, padding=0)
        self.update_visible_data()

    def clear_curves(self):
        for curve, _, _ in self.curves:
            self.plot_item.removeItem(curve)
        self.curves.clear()

    def set_downsampling(self, val: int):
        self.downsample_override = val
        self.update_visible_data()

    def update_visible_data(self):
        if not self.isVisible() or self.raw_data is None or self.times is None or not self.curves:
            return
            
        x_min, x_max = self.current_x_range
        x_min = max(0, x_min)
        x_max = min(self.times[-1], x_max)
        
        if x_min >= x_max:
            return
        
        mask = (self.times >= x_min) & (self.times <= x_max)
        visible_times = self.times[mask]
        n_points = len(visible_times)
        
        if n_points == 0:
            return
        
        if self.downsample_override > 0:
            self.samples_per_pixel = self.downsample_override
        else:
            view_width = int(max(100, self.plot_item.width()))
            self.samples_per_pixel = int(max(1, n_points // view_width))
            
        self.effective_downsample_changed.emit(self.samples_per_pixel)
        
        for curve, y_offset, ch_idx in self.curves:
            channel_data = self.raw_data[ch_idx, mask]
            
            if self.samples_per_pixel > 2:
                n_chunks = int(n_points // self.samples_per_pixel)
                if n_chunks > 0:
                    trimmed_len = int(n_chunks * self.samples_per_pixel)
                    reshaped = channel_data[:trimmed_len].reshape(n_chunks, self.samples_per_pixel)
                    downsampled = np.mean(reshaped, axis=1)
                    decimated_times = visible_times[:trimmed_len:self.samples_per_pixel]
                    if len(decimated_times) == len(downsampled):
                        curve.setData(decimated_times, downsampled + y_offset)
                    else:
                        curve.setData(visible_times, channel_data + y_offset)
                else:
                    curve.setData(visible_times, channel_data + y_offset)
            else:
                curve.setData(visible_times, channel_data + y_offset)
