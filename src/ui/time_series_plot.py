import pyqtgraph as pg
import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QScrollBar, QStackedWidget, QPushButton, QHBoxLayout, QLabel, QMenu
from PyQt6.QtCore import Qt, pyqtSignal, QEvent
from src.data.eeg_model import EEGDataModel

class TimeSeriesPlot(QWidget):
    channels_loaded = pyqtSignal(list)
    effective_downsample_changed = pyqtSignal(int)
    load_file_clicked = pyqtSignal()
    load_folder_clicked = pyqtSignal()
    load_dummy_clicked = pyqtSignal()
    load_recent_file_clicked = pyqtSignal(str)
    load_recent_folder_clicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        
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
        
        self.is_experimental = False
        self.data_loaded = False
        
        # Stacked widget to switch between placeholder and graph
        self.stack = QStackedWidget()
        self.layout().addWidget(self.stack)
        
        # --- Placeholder Widget with Load Buttons ---
        self.placeholder_widget = QWidget()
        placeholder_layout = QVBoxLayout(self.placeholder_widget)
        placeholder_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        placeholder_label = QLabel("No data loaded")
        placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #666;")
        placeholder_layout.addWidget(placeholder_label)
        
        btn_layout = QHBoxLayout()
        
        self.btn_load_file = QPushButton("Load EDF File")
        self.btn_load_file.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        """)
        self.btn_load_file.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_load_file.clicked.connect(self.load_file_clicked.emit)
        
        self.btn_load_folder = QPushButton("Load Folder")
        self.btn_load_folder.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        """)
        self.btn_load_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_load_folder.clicked.connect(self.load_folder_clicked.emit)
        
        self.btn_load_dummy = QPushButton("Load Dummy Data")
        self.btn_load_dummy.setStyleSheet("""
            QPushButton {
                background-color: #666;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #555;
            }
            QPushButton:pressed {
                background-color: #444;
            }
        """)
        self.btn_load_dummy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_load_dummy.clicked.connect(self.load_dummy_clicked.emit)
        
        btn_layout.addWidget(self.btn_load_file)
        btn_layout.addWidget(self.btn_load_folder)
        btn_layout.addWidget(self.btn_load_dummy)
        placeholder_layout.addLayout(btn_layout)
        
        # Separator line
        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: #ddd;")
        placeholder_layout.addSpacing(12)
        placeholder_layout.addWidget(separator)
        placeholder_layout.addSpacing(8)
        
        # Recent label
        recent_label = QLabel("Recent")
        recent_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        recent_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #999; text-transform: uppercase; letter-spacing: 1px;")
        placeholder_layout.addWidget(recent_label)
        placeholder_layout.addSpacing(4)
        
        # Recent files dropdown
        self.btn_recent_files = QPushButton("Recent Files ▼")
        self.btn_recent_files.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #0078d4;
                border: 1px solid #0078d4;
                border-radius: 4px;
                padding: 5px 14px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #0078d4;
                color: white;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        """)
        self.btn_recent_files.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_recent_files.setVisible(False)
        self.recent_files_menu = QMenu(self.btn_recent_files)
        self.btn_recent_files.setMenu(self.recent_files_menu)
        placeholder_layout.addWidget(self.btn_recent_files, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Recent folders dropdown
        self.btn_recent_folders = QPushButton("Recent Folders ▼")
        self.btn_recent_folders.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #0078d4;
                border: 1px solid #0078d4;
                border-radius: 4px;
                padding: 5px 14px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #0078d4;
                color: white;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        """)
        self.btn_recent_folders.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_recent_folders.setVisible(False)
        self.recent_folders_menu = QMenu(self.btn_recent_folders)
        self.btn_recent_folders.setMenu(self.recent_folders_menu)
        placeholder_layout.addWidget(self.btn_recent_folders, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # --- Graph Widget ---
        self.graph_widget = QWidget()
        graph_layout = QVBoxLayout(self.graph_widget)
        graph_layout.setContentsMargins(0, 0, 0, 0)
        graph_layout.setSpacing(0)
        
        self.graphics_layout = pg.GraphicsLayoutWidget()
        self.graphics_layout.setBackground('w')
        graph_layout.addWidget(self.graphics_layout)
        
        self.plot_item = self.graphics_layout.addPlot()
        self.plot_item.setLabel('bottom', 'Time', units='s')
        self.plot_item.setLabel('left', 'Chs')
        self.plot_item.showGrid(x=True, y=True)
        self.plot_item.enableAutoRange(x=False, y=False)
        
        vb = self.plot_item.getViewBox()
        vb.setMouseEnabled(x=False, y=False)
        vb.enableAutoRange(x=False, y=False)
        vb.setDefaultPadding(0)
        self.graphics_layout.viewport().installEventFilter(self)
        
        self.scrollbar = QScrollBar(Qt.Orientation.Horizontal)
        self.scrollbar.setStyleSheet("""
            QScrollBar:horizontal {
                border: 1px solid #dcdcdc;
                background: #f0f0f0;
                height: 16px;
                margin: 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:horizontal {
                background: #999999;
                min-width: 40px;
                border-radius: 4px;
                margin: 2px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #777777;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
                background: none;
            }
        """)
        graph_layout.addWidget(self.scrollbar)
        
        self.stack.addWidget(self.placeholder_widget)
        self.stack.addWidget(self.graph_widget)
        self.stack.setCurrentWidget(self.placeholder_widget)
        
        self.curves = []
        self.window_lines = []
        
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
        self._update_window_lines()

    def unlock_view(self):
        self.locked_duration = None
        self.scroll_step = None
        self._update_scrollbar()
        self._clear_window_lines()

    def set_experimental_mode(self, enabled: bool):
        self.is_experimental = enabled
        if enabled:
            self.graphics_layout.setBackground('#0a0a1a')
            self.plot_item.getAxis('bottom').setPen(pg.mkPen('#ff00ff', width=2))
            self.plot_item.getAxis('left').setPen(pg.mkPen('#00ffff', width=2))
            self.plot_item.getAxis('bottom').setTextPen('#ffff00')
            self.plot_item.getAxis('left').setTextPen('#00ff00')
            self.plot_item.showGrid(x=True, y=True, alpha=30)
            if hasattr(self, 'curves'):
                for curve, _, _ in self.curves:
                    curve.setPen(pg.mkPen(color='#00ffff', width=2))
            self.placeholder_widget.setStyleSheet("""
                QWidget {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0a0a0a, stop:0.5 #1a0a2e, stop:1 #0a1a2e);
                }
                QLabel {
                    color: #00ffff;
                    font-family: monospace;
                    font-weight: bold;
                    font-size: 20px;
                }
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ff00ff, stop:1 #00ffff);
                    color: #000000;
                    border: 2px solid #ffff00;
                    border-radius: 8px;
                    padding: 10px 20px;
                    font-size: 14px;
                    font-weight: bold;
                    font-family: monospace;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ffff00, stop:1 #ff00ff);
                    border: 2px solid #ffffff;
                }
                QPushButton:pressed {
                    background: #00ff00;
                    border: 2px solid #ff0000;
                }
            """)
            self.btn_recent_files.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #00ffff;
                    border: 1px solid #ff00ff;
                    border-radius: 4px;
                    padding: 5px 14px;
                    font-size: 11px;
                    font-weight: bold;
                    font-family: monospace;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ff00ff, stop:1 #00ffff);
                    color: #000000;
                    border: 1px solid #ffff00;
                }
            """)
            self.btn_recent_folders.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #00ffff;
                    border: 1px solid #ff00ff;
                    border-radius: 4px;
                    padding: 5px 14px;
                    font-size: 11px;
                    font-weight: bold;
                    font-family: monospace;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ff00ff, stop:1 #00ffff);
                    color: #000000;
                    border: 1px solid #ffff00;
                }
            """)
        else:
            self.graphics_layout.setBackground('w')
            self.plot_item.getAxis('bottom').setPen(pg.mkPen('k', width=1))
            self.plot_item.getAxis('left').setPen(pg.mkPen('k', width=1))
            self.plot_item.getAxis('bottom').setTextPen('k')
            self.plot_item.getAxis('left').setTextPen('k')
            self.plot_item.showGrid(x=True, y=True, alpha=128)
            if hasattr(self, 'curves'):
                for curve, _, _ in self.curves:
                    curve.setPen(pg.mkPen(color='k', width=1))
            self.placeholder_widget.setStyleSheet("")
            self.btn_recent_files.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #0078d4;
                    border: 1px solid #0078d4;
                    border-radius: 4px;
                    padding: 5px 14px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #0078d4;
                    color: white;
                }
                QPushButton:pressed {
                    background-color: #005a9e;
                }
            """)
            self.btn_recent_folders.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #0078d4;
                    border: 1px solid #0078d4;
                    border-radius: 4px;
                    padding: 5px 14px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #0078d4;
                    color: white;
                }
                QPushButton:pressed {
                    background-color: #005a9e;
                }
            """)

    def _update_window_lines(self):
        if self.locked_duration is None or self.scroll_step is None:
            self._clear_window_lines()
            return

        num_windows = int(round(self.locked_duration / self.scroll_step))
        while len(self.window_lines) < num_windows + 1:
            line = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen(color='r', style=Qt.PenStyle.DashLine, width=2))
            self.plot_item.addItem(line)
            self.window_lines.append(line)
            
        start = self.current_x_range[0]
        for i, line in enumerate(self.window_lines):
            if i <= num_windows:
                line.setValue(start + i * self.scroll_step)
                line.setVisible(True)
            else:
                line.setVisible(False)

    def _clear_window_lines(self):
        for line in self.window_lines:
            line.setVisible(False)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Wheel and obj is self.graphics_layout.viewport():
            if self.total_duration <= 0:
                return True

            pixel_delta = event.pixelDelta()
            angle_delta = event.angleDelta()

            if not pixel_delta.isNull():
                dx = pixel_delta.x()
                dy = pixel_delta.y()

                if abs(dx) > abs(dy):
                    pixels_per_second = self.width() / self.visible_duration
                    pan_seconds = dx / pixels_per_second
                    new_start = self.current_x_range[0] + pan_seconds
                else:
                    pixels_per_second = self.width() / self.visible_duration
                    pan_seconds = dy / pixels_per_second * 2
                    new_start = self.current_x_range[0] + pan_seconds

                new_start = max(0, min(new_start, self.total_duration - self.visible_duration))
                self.scrollbar.setValue(int(new_start * 1000))
            else:
                dy = angle_delta.y()
                if dy != 0:
                    pan_amount = self.visible_duration * 0.15
                    if dy > 0:
                        new_start = self.current_x_range[0] - pan_amount
                    else:
                        new_start = self.current_x_range[0] + pan_amount

                    new_start = max(0, min(new_start, self.total_duration - self.visible_duration))
                    self.scrollbar.setValue(int(new_start * 1000))

            event.accept()
            return True

        return super().eventFilter(obj, event)

    def _apply_zoom(self, factor: float):
        """Applies zoom centered on the current view."""
        if self.total_duration <= 0 or self.locked_duration is not None:
            return
            
        center = (self.current_x_range[0] + self.current_x_range[1]) / 2
        new_duration = self.visible_duration * factor
        new_duration = max(0.1, min(new_duration, self.total_duration))
        
        start = max(0, center - new_duration / 2)
        end = min(self.total_duration, start + new_duration)
        start = max(0, end - new_duration)
        
        self.plot_item.setXRange(start, end, padding=0)

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
        
        start_time = max(0, min(start_time, self.total_duration))
        end_time = max(start_time + 0.01, min(end_time, self.total_duration))
        
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
        self.visible_duration = max(0.1, x_range[1] - x_range[0])
        self._update_scrollbar()
        if self.locked_duration is not None:
            self._update_window_lines()

    def _update_scrollbar(self):
        self._scrollbar_blocking = True
        
        safe_start = max(0.0, min(self.current_x_range[0], self.total_duration))
        safe_duration = max(0.1, min(self.visible_duration, self.total_duration))
        
        scrollbar_value = int(min(safe_start * 1000, 2147483647))
        page_step = int(min(safe_duration * 1000, 2147483647))
        max_val = int(max(0, min((self.total_duration - safe_duration) * 1000, 2147483647)))
        
        if self.scroll_step and self.locked_duration is not None:
            single_step = int(min(self.scroll_step * 1000, 2147483647))
        else:
            single_step = max(1, page_step // 10)
            
        self.scrollbar.blockSignals(True)
        self.scrollbar.setMaximum(max_val)
        self.scrollbar.setValue(scrollbar_value)
        self.scrollbar.setPageStep(page_step)
        self.scrollbar.setSingleStep(single_step)
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

        self.data_loaded = True
        self.stack.setCurrentWidget(self.graph_widget)

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
        if self.data_model is None:
            self.clear_curves()
            return

        n_vis = len(self.visible_channels_indices)
        
        # Reuse existing curves to avoid heavy removeItem/addItem calls
        while len(self.curves) > n_vis:
            curve, _, _ = self.curves.pop()
            self.plot_item.removeItem(curve)
        
        while len(self.curves) < n_vis:
            curve = self.plot_item.plot(pen=pg.mkPen(color='#00ffff' if self.is_experimental else 'k', width=2 if self.is_experimental else 1))
            self.curves.append([curve, 0, 0])

        yticks = []
        for i, ch_idx in enumerate(self.visible_channels_indices):
            y_offset = (n_vis - 1 - i) * self.offset_step
            ch_name = self.data_model.channel_names[ch_idx]
            yticks.append((y_offset, ch_name))
            
            # Update the stored offset and channel index
            self.curves[i][1] = y_offset
            self.curves[i][2] = ch_idx

        self.plot_item.getAxis('left').setTicks([yticks])
        if self.is_experimental:
            self.plot_item.getAxis('left').setTextPen('#00ff00')
        
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
            
            if self.samples_per_pixel > 1:
                # Peak (Min-Max) downsampling to preserve spikes and envelope
                n_chunks = n_points // self.samples_per_pixel
                if n_chunks > 0:
                    trimmed_len = n_chunks * self.samples_per_pixel
                    reshaped = channel_data[:trimmed_len].reshape(n_chunks, self.samples_per_pixel)
                    
                    mins = np.min(reshaped, axis=1)
                    maxs = np.max(reshaped, axis=1)
                    
                    # Interleave mins and maxs to create the envelope
                    downsampled = np.empty(n_chunks * 2, dtype=channel_data.dtype)
                    downsampled[0::2] = mins
                    downsampled[1::2] = maxs
                    
                    decimated_times = np.empty(n_chunks * 2, dtype=visible_times.dtype)
                    chunk_times = visible_times[:trimmed_len:self.samples_per_pixel]
                    decimated_times[0::2] = chunk_times
                    # Offset max times slightly within the chunk duration
                    decimated_times[1::2] = chunk_times + (self.samples_per_pixel / self.data_model.sfreq) * 0.5
                    
                    curve.setData(decimated_times, downsampled + y_offset)
                else:
                    curve.setData(visible_times, channel_data + y_offset)
            else:
                curve.setData(visible_times, channel_data + y_offset)
        
        n_vis = len(self.visible_channels_indices)
        self.plot_item.setYRange(-self.offset_step, n_vis * self.offset_step, padding=0)
