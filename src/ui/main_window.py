import os
import json
from PyQt6.QtWidgets import (
    QMainWindow, QSplitter, QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QMessageBox, QCheckBox, QComboBox, QSpinBox, QDoubleSpinBox, QLabel, QFormLayout,
    QMenuBar, QMenu, QToolBar, QListWidget, QListWidgetItem, QDialog, QDialogButtonBox, QLineEdit
)
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtCore import Qt, QTimer
import pyqtgraph as pg

from .spectral_panel import SpectralViewWidget
from .time_series_plot import TimeSeriesPlot
from .annotation_manager import AnnotationManager
from src.data.eeg_model import EEGDataModel
from .filter_dialogs import (
    NotchFilterDialog, BandpassFilterDialog, LowpassFilterDialog, 
    HighpassFilterDialog, ViewFiltersDialog, ResolutionSettingsDialog
)

class FeatureSettingsDialog(QDialog):
    def __init__(self, parent=None, channels=[], sfreq=None, duration=None, n_channels=None):
        super().__init__(parent)
        self.setWindowTitle("Feature Extract Settings")
        self.setMinimumWidth(480)
        layout = QVBoxLayout(self)

        if sfreq:
            nyquist = sfreq / 2
            rec_nperseg = int(sfreq * 2)
            rec_noverlap = rec_nperseg // 2
            rec_window = min(max(1, int(duration / 16) * 2), 10) if duration else 2
        else:
            nyquist = rec_nperseg = rec_noverlap = rec_window = None

        info_text = f"Signal: {n_channels or '?'} ch  |  {sfreq or '?'} Hz  |  {duration or '?'} s"
        if nyquist:
            info_text += f"  |  Nyquist: {nyquist:.0f} Hz"
        info_label = QLabel(info_text)
        info_label.setStyleSheet("font-size: 11px; color: #666; padding: 4px 0;")
        layout.addWidget(info_label)

        form = QFormLayout()

        self.cmb_mode = QComboBox()
        self.cmb_mode.addItems(["PSD", "Spectrogram", "Topomap"])

        self.cmb_band = QComboBox()
        self.cmb_band.addItems(["Delta (1-4 Hz)", "Theta (4-8 Hz)", "Alpha (8-12 Hz)", "Beta (12-30 Hz)", "Gamma (30-45 Hz)"])
        self.cmb_band.setEnabled(False)
        self.cmb_mode.currentTextChanged.connect(lambda t: self.cmb_band.setEnabled(t == "Topomap"))

        self.spin_window = QSpinBox()
        self.spin_window.setRange(1, 60)
        self.spin_window.setSuffix(" s")
        if rec_window:
            self.spin_window.setToolTip(f"Recommended: {rec_window} s")

        self.list_target_ch = QListWidget()
        for ch in channels:
            item = QListWidgetItem(ch)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.list_target_ch.addItem(item)
        self.list_target_ch.setMaximumHeight(120)

        self.spin_nperseg = QSpinBox()
        self.spin_nperseg.setRange(0, 10000)
        self.spin_nperseg.setSpecialValueText("Auto")
        if rec_nperseg:
            self.spin_nperseg.setToolTip(f"Segment length in samples. Recommended: {rec_nperseg} ({rec_nperseg/sfreq:.1f}s @ {sfreq} Hz). Auto = {rec_nperseg}.")
        else:
            self.spin_nperseg.setToolTip("Segment length (nperseg). 0 for Auto.")

        self.spin_noverlap = QSpinBox()
        self.spin_noverlap.setRange(0, 10000)
        self.spin_noverlap.setSpecialValueText("Auto")
        if rec_noverlap:
            self.spin_noverlap.setToolTip(f"Overlap length in samples. Recommended: {rec_noverlap} (50% of nperseg). Auto = {rec_noverlap}.")
        else:
            self.spin_noverlap.setToolTip("Overlap length (noverlap). 0 for Auto.")

        self.cmb_window = QComboBox()
        self.cmb_window.addItems(["hann", "hamming", "boxcar", "blackman", "bartlett"])
        self.cmb_window.setToolTip("Window function for FFT. 'hann' is recommended for most EEG analysis.")

        self.cmb_scaling = QComboBox()
        self.cmb_scaling.addItems(["density", "spectrum"])
        self.cmb_scaling.setToolTip("'density' gives power spectral density (µV²/Hz). 'spectrum' gives power spectrum (µV²). Recommended: density.")

        self.cmb_interp = QComboBox()
        self.cmb_interp.addItems(["cubic", "linear", "nearest"])
        self.cmb_interp.setEnabled(False)
        self.cmb_mode.currentTextChanged.connect(lambda t: self.cmb_interp.setEnabled(t == "Topomap"))

        form.addRow("Extraction Mode:", self.cmb_mode)
        form.addRow("Topomap Band:", self.cmb_band)
        form.addRow("Topomap Interp:", self.cmb_interp)
        form.addRow("Analysis Window:", self.spin_window)
        form.addRow("Target Channels:", self.list_target_ch)
        form.addRow("Nperseg (Samples):", self.spin_nperseg)
        form.addRow("Noverlap (Samples):", self.spin_noverlap)
        form.addRow("Window Function:", self.cmb_window)
        form.addRow("Scaling:", self.cmb_scaling)

        layout.addLayout(form)

        if rec_nperseg:
            hint = QLabel(f"💡 When set to Auto, nperseg={rec_nperseg} ({rec_nperseg/sfreq:.1f}s) and noverlap={rec_noverlap} ({rec_noverlap/sfreq:.1f}s) at {sfreq} Hz")
            hint.setStyleSheet("font-size: 10px; color: #999; padding: 2px 0;")
            layout.addWidget(hint)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if parent and hasattr(parent, 'experimental_appearance') and parent.experimental_appearance:
            self.setStyleSheet("""
                QDialog {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0a0a0a, stop:0.5 #1a0a2e, stop:1 #0a1a2e);
                }
                QLabel {
                    color: #00ffff;
                    font-family: monospace;
                    font-weight: bold;
                }
                QSpinBox, QComboBox {
                    background-color: #0a0a1a;
                    color: #ffff00;
                    border: 2px solid #ff00ff;
                    border-radius: 8px;
                    padding: 6px 10px;
                    font-family: monospace;
                    font-weight: bold;
                }
                QSpinBox:focus, QComboBox:focus {
                    border: 2px solid #00ffff;
                }
                QListWidget {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(10,10,26,0.9), stop:1 rgba(26,0,51,0.9));
                    color: #00ffff;
                    border: 2px solid #ff00ff;
                    border-radius: 8px;
                    font-family: monospace;
                    font-weight: bold;
                }
                QListWidget::item {
                    padding: 8px;
                    border-bottom: 2px solid rgba(255,0,255,0.3);
                    color: #00ffff;
                }
                QListWidget::item:hover {
                    background: rgba(255,0,255,0.3);
                    color: #ffff00;
                }
                QListWidget::item:selected {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ff00ff, stop:1 #00ffff);
                    color: #000000;
                }
                QListWidget::indicator {
                    width: 20px;
                    height: 20px;
                    border-radius: 10px;
                    border: 2px solid #ff00ff;
                    background-color: #0a0a1a;
                }
                QListWidget::indicator:checked {
                    background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, stop:0 #ffff00, stop:0.5 #ff00ff, stop:1 #00ffff);
                    border: 2px solid #ffff00;
                }
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff00ff, stop:1 #00ffff);
                    color: #000000;
                    border: 2px solid #ffff00;
                    border-radius: 8px;
                    padding: 8px 16px;
                    font-weight: bold;
                    font-family: monospace;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ffff00, stop:1 #ff00ff);
                }
                QScrollBar:vertical {
                    border: 2px solid #ff00ff;
                    background: #0a0a1a;
                    width: 12px;
                    margin: 0px;
                    border-radius: 6px;
                }
                QScrollBar::handle:vertical {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ff00ff, stop:0.5 #00ffff, stop:1 #ffff00);
                    min-height: 20px;
                    border-radius: 6px;
                    margin: 2px;
                }
            """)

    def set_values(self, mode, window, target_ch, nperseg, noverlap, band="Alpha (8-12 Hz)", window_func="hann", scaling="density", interp="cubic"):
        self.cmb_mode.setCurrentText(mode.capitalize() if mode != "psd" else "PSD")
        self.cmb_band.setCurrentText(band)
        self.cmb_band.setEnabled(self.cmb_mode.currentText() == "Topomap")
        self.cmb_interp.setCurrentText(interp)
        self.cmb_interp.setEnabled(self.cmb_mode.currentText() == "Topomap")
        self.spin_window.setValue(window)
        
        target_list = target_ch if isinstance(target_ch, list) else ([target_ch] if target_ch else [])
        for i in range(self.list_target_ch.count()):
            item = self.list_target_ch.item(i)
            if item.text() in target_list:
                item.setCheckState(Qt.CheckState.Checked)
            else:
                item.setCheckState(Qt.CheckState.Unchecked)
                
        self.spin_nperseg.setValue(nperseg)
        self.spin_noverlap.setValue(noverlap)
        self.cmb_window.setCurrentText(window_func)
        self.cmb_scaling.setCurrentText(scaling)

    def get_values(self):
        checked_channels = []
        for i in range(self.list_target_ch.count()):
            item = self.list_target_ch.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                checked_channels.append(item.text())
                
        return {
            "mode": self.cmb_mode.currentText().lower(),
            "band": self.cmb_band.currentText(),
            "interp": self.cmb_interp.currentText(),
            "window": self.spin_window.value(),
            "target_ch": checked_channels,
            "nperseg": self.spin_nperseg.value(),
            "noverlap": self.spin_noverlap.value(),
            "window_func": self.cmb_window.currentText(),
            "scaling": self.cmb_scaling.currentText()
        }

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EEGAnalyser")
        self.resize(1200, 800)
        
        self.data_model = EEGDataModel()
        
        # Internal state
        self.extract_mode = "psd"
        self.extract_band = "Alpha (8-12 Hz)"
        self.extract_window = 2
        self.extract_target_ch = []
        self.extract_nperseg = 0
        self.extract_noverlap = 0
        self.extract_window_func = "hann"
        self.extract_scaling = "density"
        self.extract_interp = "cubic"
        self.allow_overlap = False
        self.auto_load_labels = True
        self.experimental_appearance = False
        self.current_folder = ""
        self.recent_files = []
        self.recent_folders = []
        
        # Load recents from a simple local file
        self.load_recents()

        # Main splitter (vertical)
        self.main_splitter = QSplitter(Qt.Orientation.Vertical)
        self.main_splitter.setStyleSheet("QSplitter::handle { background-color: rgba(0,0,0,0.1); }")
        self.setCentralWidget(self.main_splitter)

        # Top Panel: Feature Extraction View
        self.extract_panel = SpectralViewWidget()
        self.extract_panel.setVisible(False)
        self.main_splitter.addWidget(self.extract_panel)

        # Bottom Panel: Time-Series View
        self.time_series_plot = TimeSeriesPlot()
        self.main_splitter.addWidget(self.time_series_plot)

        # Connect load buttons in the time series plot placeholder
        self.time_series_plot.load_file_clicked.connect(self.load_file_dialog)
        self.time_series_plot.load_folder_clicked.connect(self.open_folder_dialog)
        self.time_series_plot.load_dummy_clicked.connect(self.load_dummy_data)

        # Set initial sizes
        self.main_splitter.setSizes([0, 800])

        # Small Expand Button (appears when dock is hidden)
        self.btn_expand_sidebar = QPushButton("▶", self)
        self.btn_expand_sidebar.setFixedSize(20, 40)
        self.btn_expand_sidebar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_expand_sidebar.setToolTip("Expand Chs Sidebar")
        self.btn_expand_sidebar.setStyleSheet("""
            QPushButton {
                background-color: rgba(220, 220, 220, 0.5);
                border: 1px solid #ccc;
                border-left: none;
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
                color: #555;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #555;
                background-color: rgba(220, 220, 220, 0.7);
            }
        """)
        self.btn_expand_sidebar.setVisible(False)
        self.btn_expand_sidebar.clicked.connect(lambda: self.channel_dock.show())
        self.btn_expand_sidebar.move(0, 300)

        # Channel Selection Dock
        self.setup_channel_dock() 

        # Annotation Manager
        self.annotation_manager = AnnotationManager(self.time_series_plot, parent_window=self)

        # UI Components
        self.setup_menu_bar()
        self.setup_tool_bar()
        self.update_recent_menus()
        
        self.spectral_timer = QTimer()
        self.spectral_timer.setSingleShot(True)
        self.spectral_timer.timeout.connect(self.update_spectral_view)
        self.last_x_range = None

        # Debounce channel selection updates
        self.channel_selection_timer = QTimer()
        self.channel_selection_timer.setSingleShot(True)
        self.channel_selection_timer.timeout.connect(self.apply_channel_selection)

        # Connect signals
        self.time_series_plot.sigXRangeChanged.connect(self.on_x_range_changed)
        self.time_series_plot.channels_loaded.connect(self.populate_channel_list)

    def load_recents(self):
        try:
            path = os.path.expanduser("~/.eeganalyser_recents.json")
            if os.path.exists(path):
                with open(path, 'r') as f:
                    data = json.load(f)
                    self.recent_files = data.get("files", [])
                    self.recent_folders = data.get("folders", [])
                    
                    # Load feature settings
                    self.extract_mode = data.get("extract_mode", "psd")
                    self.extract_band = data.get("extract_band", "Alpha (8-12 Hz)")
                    self.extract_window = data.get("extract_window", 2)
                    self.extract_target_ch = data.get("extract_target_ch", [])
                    self.extract_nperseg = data.get("extract_nperseg", 0)
                    self.extract_noverlap = data.get("extract_noverlap", 0)
                    self.extract_window_func = data.get("extract_window_func", "hann")
                    self.extract_scaling = data.get("extract_scaling", "density")
                    self.extract_interp = data.get("extract_interp", "cubic")
                    
                    self.allow_overlap = data.get("allow_overlap", False)
                    self.auto_load_labels = data.get("auto_load_labels", True)
                    self.experimental_appearance = data.get("experimental_appearance", False)
                    
                    self.extract_panel.set_mode(self.extract_mode)
        except:
            pass

    def save_recents(self):
        try:
            path = os.path.expanduser("~/.eeganalyser_recents.json")
            with open(path, 'w') as f:
                json.dump({
                    "files": self.recent_files, 
                    "folders": self.recent_folders,
                    "extract_mode": self.extract_mode,
                    "extract_band": self.extract_band,
                    "extract_window": self.extract_window,
                    "extract_target_ch": self.extract_target_ch,
                    "extract_nperseg": self.extract_nperseg,
                    "extract_noverlap": self.extract_noverlap,
                    "extract_window_func": self.extract_window_func,
                    "extract_scaling": self.extract_scaling,
                    "extract_interp": self.extract_interp,
                    "allow_overlap": self.allow_overlap,
                    "auto_load_labels": self.auto_load_labels,
                    "experimental_appearance": self.experimental_appearance
                }, f)
        except:
            pass

    def closeEvent(self, event):
        self.save_recents()
        super().closeEvent(event)

    def update_recents(self, file_path=None, folder_path=None):
        if file_path:
            if file_path in self.recent_files:
                self.recent_files.remove(file_path)
            self.recent_files.insert(0, file_path)
            self.recent_files = self.recent_files[:10]
        if folder_path:
            if folder_path in self.recent_folders:
                self.recent_folders.remove(folder_path)
            self.recent_folders.insert(0, folder_path)
            self.recent_folders = self.recent_folders[:10]
        self.save_recents()
        self.update_recent_menus()

    def update_recent_menus(self):
        self.recent_files_menu.clear()
        for f in self.recent_files:
            action = QAction(os.path.basename(f), self)
            action.setData(f)
            action.triggered.connect(lambda ch, path=f: self.load_edf(path))
            self.recent_files_menu.addAction(action)

        self.recent_folders_menu.clear()
        for d in self.recent_folders:
            action = QAction(d, self)
            action.setData(d)
            action.triggered.connect(lambda ch, path=d: self.open_folder(path))
            self.recent_folders_menu.addAction(action)

        self.time_series_plot.recent_files_menu.clear()
        for f in self.recent_files:
            action = QAction(os.path.basename(f), self)
            action.setData(f)
            action.triggered.connect(lambda ch, path=f: self.load_edf(path))
            self.time_series_plot.recent_files_menu.addAction(action)
        self.time_series_plot.btn_recent_files.setVisible(len(self.recent_files) > 0)

        self.time_series_plot.recent_folders_menu.clear()
        for d in self.recent_folders:
            action = QAction(d, self)
            action.setData(d)
            action.triggered.connect(lambda ch, path=d: self.open_folder(path))
            self.time_series_plot.recent_folders_menu.addAction(action)
        self.time_series_plot.btn_recent_folders.setVisible(len(self.recent_folders) > 0)

    def setup_channel_dock(self):
        self.channel_dock = QDockWidget(self)
        self.channel_dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self.channel_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.channel_dock.setMinimumWidth(100)
        self.channel_dock.setMaximumWidth(160)

        # Custom Title Bar
        title_bar = QWidget()
        title_bar.setObjectName("channelDockTitle")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(8, 4, 4, 4)
        title_layout.setSpacing(4)

        lbl_title = QLabel("Channels")
        lbl_title.setObjectName("channelDockTitleLabel")
        title_layout.addWidget(lbl_title)
        title_layout.addStretch()

        btn_collapse = QPushButton("◀")
        btn_collapse.setFixedSize(22, 22)
        btn_collapse.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_collapse.setToolTip("Collapse Sidebar")
        btn_collapse.setObjectName("channelDockCollapseBtn")
        btn_collapse.clicked.connect(lambda: self.channel_dock.hide())
        title_layout.addWidget(btn_collapse)

        self.channel_dock.setTitleBarWidget(title_bar)

        dock_container = QWidget()
        dock_container.setObjectName("channelDockContainer")
        main_dock_layout = QVBoxLayout(dock_container)
        main_dock_layout.setContentsMargins(4, 4, 4, 4)
        main_dock_layout.setSpacing(4)

        # Search box
        self.channel_search = QLineEdit()
        self.channel_search.setObjectName("channelSearch")
        self.channel_search.setPlaceholderText("Search channels...")
        self.channel_search.textChanged.connect(self.filter_channel_list)
        main_dock_layout.addWidget(self.channel_search)

        self.channel_list = QListWidget()
        self.channel_list.setObjectName("channelList")
        self.channel_list.setSpacing(2)
        self.channel_list.itemChanged.connect(self.on_channel_selection_changed)
        main_dock_layout.addWidget(self.channel_list)

        btn_container = QWidget()
        btn_container.setObjectName("channelBtnContainer")
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 2, 0, 2)
        btn_layout.setSpacing(4)

        btn_all = QPushButton("All")
        btn_all.setObjectName("channelBtnAll")
        btn_all.clicked.connect(self.select_all_channels)

        btn_none = QPushButton("None")
        btn_none.setObjectName("channelBtnNone")
        btn_none.clicked.connect(self.clear_all_channels)

        btn_layout.addWidget(btn_all)
        btn_layout.addWidget(btn_none)
        main_dock_layout.addWidget(btn_container)
        self.channel_dock.setWidget(dock_container)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.channel_dock)

        self.resizeDocks([self.channel_dock], [100], Qt.Orientation.Horizontal)
        self.apply_appearance()

    def filter_channel_list(self, text):
        text = text.lower()
        for i in range(self.channel_list.count()):
            item = self.channel_list.item(i)
            item.setHidden(text not in item.text().lower())

    def apply_appearance(self):
        if self.experimental_appearance:
            self._apply_experimental_styles()
        else:
            self._apply_default_styles()

    def _apply_default_styles(self):
        self.setStyleSheet("")
        
        title_bar = self.channel_dock.titleBarWidget()
        if title_bar:
            title_bar.setStyleSheet("background-color: #333333; border-bottom: 1px solid #444444;")
            lbl = title_bar.findChild(QLabel)
            if lbl:
                lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #ffffff;")
            btn = title_bar.findChild(QPushButton)
            if btn:
                btn.setStyleSheet("""
                    QPushButton { 
                        border: none; 
                        background: transparent; 
                        font-size: 12px; 
                        color: #ffffff; 
                        margin: 0; 
                        padding: 0;
                    } 
                    QPushButton:hover { 
                        color: #cccccc;
                    }
                """)

        dock_container = self.channel_dock.widget()
        if dock_container:
            dock_container.setStyleSheet("background-color: #333333;")

        self.channel_search.setStyleSheet("""
            QLineEdit {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px 8px;
                font-size: 11px;
            }
            QLineEdit:focus {
                border: 1px solid #0078d4;
            }
            QLineEdit::placeholder {
                color: #888888;
            }
        """)

        self.channel_list.setStyleSheet("""
            QListWidget {
                border: none;
                background-color: #333333;
                outline: none;
            }
            QListWidget::item {
                padding: 6px 8px;
                border-bottom: 1px solid #444444;
                color: #ffffff;
            }
            QListWidget::item:hover {
                background-color: #444444;
            }
            QListWidget::item:selected {
                background-color: #555555;
                color: #ffffff;
            }
            QListWidget::indicator {
                width: 16px;
                height: 16px;
                border-radius: 3px;
                border: 1px solid #888;
                background-color: white;
            }
            QListWidget::indicator:unchecked:hover {
                border: 1px solid #ffffff;
            }
            QListWidget::indicator:checked {
                background-color: #0078d4;
                border: 1px solid #0078d4;
            }
            QScrollBar:vertical {
                border: none;
                background: #2b2b2b;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #555555;
                min-height: 20px;
                border-radius: 5px;
                margin: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background: #666666;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
                background: none;
            }
        """)

        btn_style = """
            QPushButton {
                background-color: #444444;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 4px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #555555;
            }
            QPushButton:pressed {
                background-color: #222222;
            }
        """
        for btn in self.channel_dock.widget().findChildren(QPushButton):
            if btn.objectName() not in ["channelDockCollapseBtn"]:
                btn.setStyleSheet(btn_style)

        self.btn_expand_sidebar.setStyleSheet("""
            QPushButton {
                background-color: rgba(220, 220, 220, 0.5);
                border: 1px solid #ccc;
                border-left: none;
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
                color: #555;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #555;
                background-color: rgba(220, 220, 220, 0.7);
            }
        """)

        if hasattr(self, 'toolbar'):
            for btn in self.toolbar.findChildren(QPushButton):
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #f0f0f0;
                        color: #333333;
                        border: 1px solid #cccccc;
                        border-radius: 4px;
                        padding: 4px 8px;
                        font-size: 11px;
                    }
                    QPushButton:hover {
                        background-color: #e0e0e0;
                    }
                    QPushButton:pressed {
                        background-color: #d0d0d0;
                    }
                """)

    def _apply_experimental_styles(self):
        # EXPERIMENTAL: NEON CYBERPUNK CHAOS MODE
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0a0a0a, stop:0.5 #1a0a2e, stop:1 #0a1a2e);
            }
            QMenuBar {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff00ff, stop:0.5 #00ffff, stop:1 #ffff00);
                color: #000000;
                border-bottom: 3px solid #ff00ff;
                padding: 4px;
                font-weight: bold;
            }
            QMenuBar::item:selected {
                background: #ffff00;
                color: #ff00ff;
                border-radius: 4px;
            }
            QMenu {
                background-color: #0a0a1a;
                color: #00ff00;
                border: 2px solid #ff00ff;
                font-family: monospace;
            }
            QMenu::item:selected {
                background: #ff00ff;
                color: #000000;
            }
            QToolBar {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1a0033, stop:0.5 #330066, stop:1 #003366);
                border-bottom: 3px solid #00ffff;
                padding: 6px;
                spacing: 8px;
            }
            QToolBar QComboBox, QToolBar QSpinBox, QToolBar QCheckBox {
                color: #ffff00;
                font-weight: bold;
            }
            QSplitter::handle {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff00ff, stop:0.5 #00ffff, stop:1 #ffff00);
                height: 4px;
            }
            QScrollBar:horizontal {
                border: 2px solid #ff00ff;
                background: #0a0a1a;
                height: 16px;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff00ff, stop:1 #00ffff);
                min-width: 50px;
                border-radius: 8px;
                margin: 2px;
            }
            QScrollBar::handle:horizontal:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ffff00, stop:1 #ff00ff);
            }
        """)

        title_bar = self.channel_dock.titleBarWidget()
        if title_bar:
            title_bar.setStyleSheet("""
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff0000, stop:0.33 #00ff00, stop:0.66 #0000ff, stop:1 #ff00ff);
                border-bottom: 3px solid #ffff00;
            """)
            lbl = title_bar.findChild(QLabel)
            if lbl:
                lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff; letter-spacing: 3px; text-transform: uppercase; font-family: monospace;")
            btn = title_bar.findChild(QPushButton)
            if btn:
                btn.setStyleSheet("""
                    QPushButton { 
                        border: 2px solid #ffff00; 
                        background: #ff00ff; 
                        font-size: 14px; 
                        color: #000000; 
                        border-radius: 10px;
                        margin: 2px; 
                        padding: 2px;
                        font-weight: bold;
                    } 
                    QPushButton:hover { 
                        background: #00ffff;
                        border: 2px solid #ff0000;
                    }
                """)

        dock_container = self.channel_dock.widget()
        if dock_container:
            dock_container.setStyleSheet("""
                background: qconicalgradient(cx:0.5, cy:0.5, angle:45, stop:0 #1a0033, stop:0.25 #003366, stop:0.5 #006600, stop:0.75 #660066, stop:1 #1a0033);
                border-right: 3px solid #00ffff;
            """)

        self.channel_search.setStyleSheet("""
            QLineEdit {
                background-color: #0a0a1a;
                color: #00ff00;
                border: 2px solid #ff00ff;
                border-radius: 12px;
                padding: 8px 12px;
                font-size: 12px;
                font-family: monospace;
                font-weight: bold;
            }
            QLineEdit:focus {
                border: 2px solid #00ffff;
                background-color: #1a0033;
                color: #ffff00;
            }
            QLineEdit::placeholder {
                color: #ff00ff;
                font-style: italic;
            }
        """)

        self.channel_list.setStyleSheet("""
            QListWidget {
                border: none;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(10,10,26,0.9), stop:1 rgba(26,0,51,0.9));
                outline: none;
                font-size: 12px;
                font-family: monospace;
            }
            QListWidget::item {
                padding: 10px 12px;
                border: none;
                border-bottom: 2px solid rgba(255, 0, 255, 0.3);
                color: #00ffff;
                border-radius: 6px;
                margin: 2px 4px;
                font-weight: bold;
            }
            QListWidget::item:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(255,0,255,0.4), stop:1 rgba(0,255,255,0.4));
                color: #ffff00;
            }
            QListWidget::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ff00ff, stop:1 #00ffff);
                color: #000000;
                border: 2px solid #ffff00;
            }
            QListWidget::indicator {
                width: 20px;
                height: 20px;
                border-radius: 10px;
                border: 3px solid #ff00ff;
                background-color: #0a0a1a;
            }
            QListWidget::indicator:unchecked:hover {
                border: 3px solid #00ffff;
                background: #1a0033;
            }
            QListWidget::indicator:checked {
                background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, stop:0 #ffff00, stop:0.5 #ff00ff, stop:1 #00ffff);
                border: 3px solid #ffff00;
            }
            QScrollBar:vertical {
                border: 2px solid #ff00ff;
                background: #0a0a1a;
                width: 12px;
                margin: 0px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ff00ff, stop:0.5 #00ffff, stop:1 #ffff00);
                min-height: 20px;
                border-radius: 6px;
                margin: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffff00, stop:0.5 #ff00ff, stop:1 #00ffff);
            }
        """)

        for btn in self.channel_dock.widget().findChildren(QPushButton):
            if btn.objectName() == "channelBtnAll" or btn.objectName() == "channelBtnNone":
                btn.setStyleSheet("""
                    QPushButton {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff0000, stop:0.5 #00ff00, stop:1 #0000ff);
                        color: #ffffff;
                        border: 2px solid #ffff00;
                        border-radius: 10px;
                        padding: 8px 14px;
                        font-size: 12px;
                        font-weight: bold;
                        font-family: monospace;
                    }
                    QPushButton:hover {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ffff00, stop:0.5 #ff00ff, stop:1 #00ffff);
                        border: 2px solid #ffffff;
                    }
                    QPushButton:pressed {
                        background: #ff00ff;
                        border: 2px solid #000000;
                    }
                """)
            elif btn.objectName() not in ["channelDockCollapseBtn"]:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #1a0033;
                        color: #00ffff;
                        border: 2px solid #ff00ff;
                        border-radius: 6px;
                        padding: 6px;
                        font-size: 11px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #ff00ff;
                        color: #000000;
                    }
                """)

        # Style toolbar buttons - NEON CHAOS
        if hasattr(self, 'toolbar'):
            for btn in self.toolbar.findChildren(QPushButton):
                btn.setStyleSheet("""
                    QPushButton {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ff00ff, stop:1 #00ffff);
                        color: #000000;
                        border: 2px solid #ffff00;
                        border-radius: 8px;
                        padding: 6px 12px;
                        font-size: 11px;
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

        # Style expand sidebar button
        self.btn_expand_sidebar.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ff00ff, stop:0.5 #00ffff, stop:1 #ffff00);
                border: 2px solid #ff00ff;
                border-left: none;
                border-top-right-radius: 10px;
                border-bottom-right-radius: 10px;
                color: #000000;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffff00, stop:0.5 #ff00ff, stop:1 #00ffff);
                border: 2px solid #00ffff;
            }
        """)

    def populate_channel_list(self, names):
        self.channel_list.blockSignals(True)
        self.channel_list.clear()
        for name in names:
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.channel_list.addItem(item)
        self.channel_list.blockSignals(False)
        if names:
            self.extract_target_ch = names[0]

    def on_channel_selection_changed(self, item=None):
        # Use a short timer to debounce multiple rapid changes (spam clicking)
        self.channel_selection_timer.stop()
        self.channel_selection_timer.start(50)  # 50ms delay for responsiveness

    def apply_channel_selection(self):
        indices = []
        for i in range(self.channel_list.count()):
            if self.channel_list.item(i).checkState() == Qt.CheckState.Checked:
                indices.append(i)
        self.time_series_plot.set_visible_channels(indices)

    def select_all_channels(self):
        self.channel_list.blockSignals(True)
        for i in range(self.channel_list.count()):
            self.channel_list.item(i).setCheckState(Qt.CheckState.Checked)
        self.channel_list.blockSignals(False)
        self.on_channel_selection_changed()

    def clear_all_channels(self):
        self.channel_list.blockSignals(True)
        for i in range(self.channel_list.count()):
            self.channel_list.item(i).setCheckState(Qt.CheckState.Unchecked)
        self.channel_list.blockSignals(False)
        self.on_channel_selection_changed()

    def setup_menu_bar(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")
        
        load_action = QAction("&Load EDF File", self)
        load_action.triggered.connect(self.load_file_dialog)
        file_menu.addAction(load_action)
        
        self.recent_files_menu = file_menu.addMenu("Open Recent File")
        
        file_menu.addSeparator()
        
        folder_action = QAction("Open &Folder", self)
        folder_action.triggered.connect(self.open_folder_dialog)
        file_menu.addAction(folder_action)
        
        self.recent_folders_menu = file_menu.addMenu("Open Recent Folder")
        
        file_menu.addSeparator()

        dummy_action = QAction("Load &Dummy Data", self)
        dummy_action.triggered.connect(self.load_dummy_data)
        file_menu.addAction(dummy_action)

        file_menu.addSeparator()

        export_action = QAction("&Export Annotations CSV", self)
        export_action.triggered.connect(lambda: self.annotation_manager.export_annotations(self))
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        close_action = QAction("&Close", self)
        close_action.setShortcut("Cmd+W")
        close_action.triggered.connect(self.close_file)
        file_menu.addAction(close_action)
        
        view_menu = menubar.addMenu("&View")
        self.extract_action = QAction("Enable &Feature Extraction", self)
        self.extract_action.setCheckable(True)
        self.extract_action.triggered.connect(self.toggle_extract_view)
        view_menu.addAction(self.extract_action)
        
        settings_action = QAction("Feature Extract &Settings", self)
        settings_action.triggered.connect(self.open_extract_settings)
        view_menu.addAction(settings_action)

        res_settings_action = QAction("&Resolution Settings", self)
        res_settings_action.triggered.connect(self.open_resolution_settings)
        view_menu.addAction(res_settings_action)

        self.show_res_toolbar_action = QAction("Show &Resolution in Toolbar", self)
        self.show_res_toolbar_action.setCheckable(True)
        self.show_res_toolbar_action.setChecked(False)
        self.show_res_toolbar_action.triggered.connect(self.toggle_res_toolbar)
        view_menu.addAction(self.show_res_toolbar_action)

        view_menu.addSeparator()
        dock_action = self.channel_dock.toggleViewAction()
        view_menu.addAction(dock_action)
        
        filter_menu = menubar.addMenu("&Filter")
        notch_action = QAction("&Notch Filter", self)
        notch_action.triggered.connect(self.open_notch_filter)
        filter_menu.addAction(notch_action)
        
        bp_action = QAction("&Band-pass Filter", self)
        bp_action.triggered.connect(self.open_bandpass_filter)
        filter_menu.addAction(bp_action)
        
        lp_action = QAction("&Low-pass Filter", self)
        lp_action.triggered.connect(self.open_lowpass_filter)
        filter_menu.addAction(lp_action)
        
        hp_action = QAction("&High-pass Filter", self)
        hp_action.triggered.connect(self.open_highpass_filter)
        filter_menu.addAction(hp_action)
        
        filter_menu.addSeparator()
        view_filters_action = QAction("&View Applied Filters", self)
        view_filters_action.triggered.connect(self.open_view_filters)
        filter_menu.addAction(view_filters_action)

        ann_menu = menubar.addMenu("&Annotations")
        add_ann_action = QAction("&Add Annotation Region", self)
        add_ann_action.triggered.connect(self.annotation_manager.add_annotation_region)
        ann_menu.addAction(add_ann_action)

        view_ann_action = QAction("&View Annotations", self)
        view_ann_action.triggered.connect(self.annotation_manager.view_annotations)
        ann_menu.addAction(view_ann_action)

        settings_menu = menubar.addMenu("&Settings")
        overlap_action = QAction("Allow Overlapping Annotations", self)
        overlap_action.setCheckable(True)
        overlap_action.setChecked(self.allow_overlap)
        overlap_action.triggered.connect(self.toggle_overlap)
        settings_menu.addAction(overlap_action)

        auto_load_action = QAction("Auto-load Label JSON", self)
        auto_load_action.setCheckable(True)
        auto_load_action.setChecked(self.auto_load_labels)
        auto_load_action.triggered.connect(self.toggle_auto_load_labels)
        settings_menu.addAction(auto_load_action)

        settings_menu.addSeparator()

        self.experimental_action = QAction("Experimental Appearance", self)
        self.experimental_action.setCheckable(True)
        self.experimental_action.setChecked(self.experimental_appearance)
        self.experimental_action.triggered.connect(self.toggle_experimental_appearance)
        settings_menu.addAction(self.experimental_action)
        
        self.update_recent_menus()

    def toggle_overlap(self, checked):
        self.allow_overlap = checked

    def toggle_auto_load_labels(self, checked):
        self.auto_load_labels = checked

    def toggle_experimental_appearance(self, checked):
        self.experimental_appearance = checked
        self.experimental_action.setChecked(checked)
        self.time_series_plot.set_experimental_mode(checked)
        self.extract_panel.set_experimental_mode(checked)
        self.apply_appearance()

    def load_dummy_data(self):
        """Generates and loads dummy EEG data and labels for testing."""
        import tempfile
        import mne
        import numpy as np
        
        # Create a temporary directory that persists for the session
        temp_dir = tempfile.gettempdir()
        edf_path = os.path.join(temp_dir, "dummy_test_data.edf")
        label_path = os.path.join(temp_dir, "dummy_test_data_labels.json")
        
        try:
            # Generate dummy EDF
            sfreq = 256
            n_channels = 4
            duration = 30
            n_samples = sfreq * duration
            data = np.random.randn(n_channels, n_samples) * 1e-6
            
            ch_names = [f'EEG {i}' for i in range(n_channels)]
            ch_types = ['eeg'] * n_channels
            info = mne.create_info(ch_names=ch_names, sfreq=sfreq, ch_types=ch_types)
            raw = mne.io.RawArray(data, info)
            
            # Export to EDF (requires edfio)
            mne.export.export_raw(edf_path, raw, fmt='edf', overwrite=True)
            
            # Generate dummy labels
            labels = [
                {"label": "Seizure", "start": 5000, "end": 10000},
                {"label": "Alpha Wave", "start": 15000, "end": 20000},
                {"label": "Artifact", "start": 25000, "end": 28000}
            ]
            with open(label_path, 'w') as f:
                json.dump(labels, f, indent=4)
                
            print(f"MainWindow: Generated dummy data at {edf_path}")
            
            # Load the file normally but without updating recents (we'll manually call load_edf logic)
            # We want to use the same logic but avoid update_recents
            self._load_edf_internal(edf_path, record_recent=False)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate dummy data: {e}")

    def setup_tool_bar(self):
        self.toolbar = QToolBar("Controls")
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)

        self.toolbar.addSeparator()

        self.toolbar.addWidget(QLabel(" Zoom: "))
        btn_zoom_in = QPushButton("Zoom In (+)")
        btn_zoom_in.clicked.connect(lambda: self.time_series_plot.zoom_fixed_start(0.5))
        self.toolbar.addWidget(btn_zoom_in)

        btn_zoom_out = QPushButton("Zoom Out (-)")
        btn_zoom_out.clicked.connect(lambda: self.time_series_plot.zoom_fixed_start(2.0))
        self.toolbar.addWidget(btn_zoom_out)

        self.toolbar.addSeparator()

        btn_add_ann = QPushButton("Add Annotation")
        btn_add_ann.clicked.connect(self.annotation_manager.add_annotation_region)
        self.toolbar.addWidget(btn_add_ann)

        self.toolbar.addSeparator()

        # Resolution info in toolbar
        self.lbl_ds_info = QLabel(" (Res: Auto)")
        self.toolbar.addWidget(self.lbl_ds_info)
        self.time_series_plot.effective_downsample_changed.connect(
            lambda ds: self.lbl_ds_info.setText(f" (1px = {ds} samples)")
        )

        # Advanced resolution controls (initially hidden)
        self.lbl_res_advanced = QLabel(" Res: ")
        self.combo_res_advanced = QComboBox()
        self.factors_map = {
            "1x": 1, "2x": 2, "4x": 4, "8x": 8, "16x": 16, 
            "32x": 32, "64x": 64, "128x": 128, "256x": 256, "512x": 512
        }
        for k in self.factors_map.keys():
            self.combo_res_advanced.addItem(k)
        self.combo_res_advanced.currentIndexChanged.connect(self.handle_advanced_res_change)
        
        self.chk_auto_advanced = QCheckBox("Auto")
        self.chk_auto_advanced.setChecked(True)
        self.chk_auto_advanced.stateChanged.connect(self.handle_advanced_auto_toggle)

        self.adv_res_widgets = [
            self.toolbar.addWidget(self.lbl_res_advanced),
            self.toolbar.addWidget(self.chk_auto_advanced),
            self.toolbar.addWidget(self.combo_res_advanced)
        ]
        for w in self.adv_res_widgets:
            w.setVisible(False)

        # Internal state for resolution
        self.is_auto_res = True
        self.manual_res_factor = 1
        
        self.toolbar.addSeparator()
        
        # Folder Navigator Button
        self.btn_folder_nav = QPushButton("Navigator")
        self.btn_folder_nav.setEnabled(False)
        self.btn_folder_nav.setVisible(False)
        self.nav_menu = QMenu(self)
        self.btn_folder_nav.setMenu(self.nav_menu)
        self.toolbar.addWidget(self.btn_folder_nav)

        self.toolbar.addSeparator()
        btn_copy = QPushButton("Copy Snippet")
        btn_copy.setToolTip("Copy the current view to clipboard")
        btn_copy.clicked.connect(self.copy_to_clipboard)
        self.toolbar.addWidget(btn_copy)

    def copy_to_clipboard(self):
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QImage

        # Save original stylesheets to restore them later
        old_extract_style = self.extract_panel.styleSheet()
        old_ts_style = self.time_series_plot.styleSheet()
        old_splitter_style = self.main_splitter.styleSheet()

        # Apply white background ONLY for the capture
        self.extract_panel.setStyleSheet("background-color: white;")
        self.time_series_plot.setStyleSheet("background-color: white;")
        self.main_splitter.setStyleSheet("QSplitter { background-color: white; } QSplitter::handle { background-color: white; }")

        # Temporarily hide the scrollbar and expand button to keep the snippet clean
        self.time_series_plot.scrollbar.hide()
        self.btn_expand_sidebar.hide()
        
        # Force a layout update so the plot expands into the scrollbar's space
        QApplication.processEvents()
        
        # We grab the main splitter which contains both the spectral panel and the time series plot
        pixmap = self.main_splitter.grab()
        
        # Convert to QImage for more reliable clipboard behavior
        image = pixmap.toImage()
        
        # Restore original styles immediately after grab
        self.extract_panel.setStyleSheet(old_extract_style)
        self.time_series_plot.setStyleSheet(old_ts_style)
        self.main_splitter.setStyleSheet(old_splitter_style)

        # Restore scrollbar and expand button (if it should be visible)
        self.time_series_plot.scrollbar.show()
        if not self.channel_dock.isVisible():
            self.btn_expand_sidebar.show()
        
        clipboard = QApplication.clipboard()
        clipboard.setImage(image)
        
        # Briefly change the window title or show a status message if we had one
        original_title = self.windowTitle()
        self.setWindowTitle(original_title + " (Snippet Copied!)")
        QTimer.singleShot(1500, lambda: self.setWindowTitle(original_title))

    def open_resolution_settings(self):
        dialog = ResolutionSettingsDialog(self, is_auto=self.is_auto_res, current_factor=self.manual_res_factor)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            vals = dialog.get_values()
            self.apply_resolution_settings(vals["is_auto"], vals["factor"])

    def apply_resolution_settings(self, is_auto, factor):
        self.is_auto_res = is_auto
        self.manual_res_factor = factor
        
        # Update toolbar widgets if they are visible
        self.chk_auto_advanced.blockSignals(True)
        self.chk_auto_advanced.setChecked(is_auto)
        self.chk_auto_advanced.blockSignals(False)
        
        self.combo_res_advanced.blockSignals(True)
        # Find index for factor
        for i in range(self.combo_res_advanced.count()):
            text = self.combo_res_advanced.itemText(i)
            if self.factors_map.get(text) == factor:
                self.combo_res_advanced.setCurrentIndex(i)
                break
        self.combo_res_advanced.setEnabled(not is_auto)
        self.combo_res_advanced.blockSignals(False)

        if self.is_auto_res:
            self.time_series_plot.set_downsampling(0)
        else:
            self.time_series_plot.set_downsampling(self.manual_res_factor)

    def toggle_res_toolbar(self, checked):
        for w in self.adv_res_widgets:
            w.setVisible(checked)
        if checked:
            self.lbl_ds_info.setVisible(False)
        else:
            self.lbl_ds_info.setVisible(True)

    def handle_advanced_res_change(self, index):
        text = self.combo_res_advanced.currentText()
        factor = self.factors_map.get(text, 1)
        self.apply_resolution_settings(self.chk_auto_advanced.isChecked(), factor)

    def handle_advanced_auto_toggle(self, state):
        is_auto = (state == Qt.CheckState.Checked.value)
        self.apply_resolution_settings(is_auto, self.manual_res_factor)

    def open_extract_settings(self):
        sfreq = self.data_model.sfreq if self.data_model.raw else None
        duration = self.data_model.raw.times[-1] if self.data_model.raw is not None and hasattr(self.data_model.raw, 'times') and self.data_model.raw.times is not None else None
        n_channels = len(self.data_model.channel_names) if self.data_model.channel_names else None
        dialog = FeatureSettingsDialog(self, channels=self.data_model.channel_names,
                                       sfreq=sfreq, duration=duration, n_channels=n_channels)
        dialog.set_values(self.extract_mode, self.extract_window, self.extract_target_ch, 
                         self.extract_nperseg, self.extract_noverlap, 
                         band=self.extract_band, 
                         window_func=self.extract_window_func, 
                         scaling=self.extract_scaling,
                         interp=self.extract_interp)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            vals = dialog.get_values()
            self.extract_mode = vals["mode"]
            self.extract_band = vals["band"]
            self.extract_interp = vals["interp"]
            self.extract_window = vals["window"]
            self.extract_target_ch = vals["target_ch"]
            self.extract_nperseg = vals["nperseg"]
            self.extract_noverlap = vals["noverlap"]
            self.extract_window_func = vals["window_func"]
            self.extract_scaling = vals["scaling"]
            self.extract_panel.set_mode(self.extract_mode)
            if self.extract_action.isChecked():
                self.time_series_plot.set_locked_view(self.extract_window * 4, self.extract_window)
                self.update_spectral_view()
            self.save_recents()

    def open_notch_filter(self):
        if not self.data_model.raw: return
        dialog = NotchFilterDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.data_model.apply_filter("notch", dialog.get_values())
            self.refresh_after_filtering()

    def open_bandpass_filter(self):
        if not self.data_model.raw: return
        dialog = BandpassFilterDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.data_model.apply_filter("bandpass", dialog.get_values())
            self.refresh_after_filtering()

    def open_lowpass_filter(self):
        if not self.data_model.raw: return
        dialog = LowpassFilterDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.data_model.apply_filter("lowpass", dialog.get_values())
            self.refresh_after_filtering()

    def open_highpass_filter(self):
        if not self.data_model.raw: return
        dialog = HighpassFilterDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.data_model.apply_filter("highpass", dialog.get_values())
            self.refresh_after_filtering()

    def open_view_filters(self):
        if not self.data_model.raw: return
        dialog = ViewFiltersDialog(self.data_model.applied_filters, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            for idx in reversed(dialog.removed_indices):
                self.data_model.remove_filter(idx)
            self.refresh_after_filtering()

    def refresh_after_filtering(self):
        self.time_series_plot.refresh_data_only()
        if self.extract_action.isChecked():
            self.update_spectral_view()

    def load_file_dialog(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Open EDF File", "", "EDF Files (*.edf)")
        if filepath:
            self.load_edf(filepath)

    def load_edf(self, filepath):
        self._load_edf_internal(filepath, record_recent=True)

    def _load_edf_internal(self, filepath, record_recent=True):
        print(f"MainWindow: Loading {filepath}")
        
        # Disable navigator if we are loading a specific file and it's not from the current folder
        if self.current_folder and not filepath.startswith(self.current_folder):
            self.btn_folder_nav.setEnabled(False)
            self.btn_folder_nav.setVisible(False)
        elif not self.current_folder:
            self.btn_folder_nav.setEnabled(False)
            self.btn_folder_nav.setVisible(False)

        if self.data_model.load_edf(filepath):
            self.update_recents(file_path=filepath)
            self.annotation_manager.clear_annotations()
            
            # Check for label file: <original_name>_labels.json
            if self.auto_load_labels:
                base_path, _ = os.path.splitext(filepath)
                label_path = base_path + "_labels.json"
                if os.path.exists(label_path):
                    print(f"MainWindow: Found label file {label_path}")
                    self.annotation_manager.load_labels_from_json(label_path)

            self.setWindowTitle(f"EEGAnalyser - {filepath}")
            
            # Set a default target channel for extraction if none selected
            if not self.extract_target_ch and self.data_model.channel_names:
                self.extract_target_ch = self.data_model.channel_names[0]

            self.extract_panel.set_data_loaded(True)
            self.time_series_plot.plot_data(self.data_model)
            if self.extract_action.isChecked():
                self.time_series_plot.set_locked_view(self.extract_window * 4, self.extract_window)
                self.update_spectral_view()
            self.update()
        else:
            QMessageBox.critical(self, "Error", f"Failed to load EDF file: {filepath}")

    def close_file(self):
        self.data_model = EEGDataModel()
        self.current_folder = ""
        self.btn_folder_nav.setEnabled(False)
        self.btn_folder_nav.setVisible(False)
        self.annotation_manager.clear_annotations()
        self.time_series_plot.clear_curves()
        self.time_series_plot.data_loaded = False
        self.time_series_plot.stack.setCurrentWidget(self.time_series_plot.placeholder_widget)
        self.time_series_plot.raw_data = None
        self.time_series_plot.times = None
        self.time_series_plot.total_duration = 0
        self.extract_panel.set_data_loaded(False)
        self.extract_panel.setVisible(False)
        self.extract_action.setChecked(False)
        self.main_splitter.setSizes([0, 800])
        self.channel_list.clear()
        self.setWindowTitle("EEGAnalyser")
        self.time_series_plot.update()

    def open_folder_dialog(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if dir_path:
            self.open_folder(dir_path)

    def open_folder(self, dir_path):
        self.current_folder = dir_path
        self.update_recents(folder_path=dir_path)
        self.btn_folder_nav.setEnabled(True)
        self.btn_folder_nav.setVisible(True)
        self.refresh_navigator_menu()
        
        # Load first EDF if available
        for root, dirs, files in os.walk(dir_path):
            for f in files:
                if f.lower().endswith(".edf"):
                    self.load_edf(os.path.join(root, f))
                    return

    def refresh_navigator_menu(self):
        self.nav_menu.clear()
        if not self.current_folder:
            return

        # Simple recursive file tree in menu
        self._build_nav_menu(self.current_folder, self.nav_menu)

    def _build_nav_menu(self, path, parent_menu):
        try:
            items = sorted(os.listdir(path))
            for item in items:
                full_path = os.path.join(path, item)
                if os.path.isdir(full_path):
                    # Check if there are any EDFs inside before adding sub-menu
                    has_edfs = False
                    for r, d, f in os.walk(full_path):
                        if any(fname.lower().endswith(".edf") for fname in f):
                            has_edfs = True
                            break
                    if has_edfs:
                        sub_menu = parent_menu.addMenu(item)
                        self._build_nav_menu(full_path, sub_menu)
                elif item.lower().endswith(".edf"):
                    action = QAction(item, self)
                    action.triggered.connect(lambda ch, p=full_path: self.load_edf(p))
                    parent_menu.addAction(action)
        except Exception as e:
            print(f"Error building nav menu: {e}")

    def toggle_extract_view(self, checked):
        self.extract_panel.setVisible(checked)
        if checked:
            self.main_splitter.setSizes([300, 500])
            self.time_series_plot.set_locked_view(self.extract_window * 4, self.extract_window)
            # Delay update slightly to let layout settle and avoid QPainter errors
            QTimer.singleShot(200, self.update_spectral_view)
        else:
            self.main_splitter.setSizes([0, 800])
            self.time_series_plot.unlock_view()

    def on_x_range_changed(self, _, x_range):
        if self.extract_action.isChecked() and self.data_model.raw is not None:
            self.last_x_range = x_range
            self.spectral_timer.start(250)

    def update_spectral_view(self):
        if not self.extract_action.isChecked() or not self.extract_panel.isVisible():
            return
            
        if self.last_x_range is None or self.data_model.raw is None:
            return
            
        x_range = self.last_x_range
        tmin = max(0.0, x_range[0])
        # Fetch exactly 4 windows of data
        tmax = tmin + (self.extract_window * 4)
        tmax = min(tmax, self.data_model.raw.times[-1])
        
        if tmin >= tmax: return
            
        sfreq = self.data_model.sfreq
        
        try:
            # Use target channels if selected, otherwise all channels
            picks = None
            if self.extract_mode == "topomap":
                # For topomap we usually want all channels to interpolate correctly
                picks = None 
            elif self.extract_target_ch:
                if isinstance(self.extract_target_ch, list) and len(self.extract_target_ch) > 0:
                    picks = [self.data_model.channel_names.index(ch) for ch in self.extract_target_ch if ch in self.data_model.channel_names]
                elif isinstance(self.extract_target_ch, str) and self.extract_target_ch:
                    picks = [self.data_model.channel_names.index(self.extract_target_ch)]
            
            data, _ = self.data_model.raw.get_data(picks=picks, tmin=tmin, tmax=tmax, return_times=True)
            
            # Average across channels if multiple are explicitly selected (only for PSD/Spectrogram)
            if self.extract_mode != "topomap" and data is not None and data.shape[0] > 1 and self.extract_target_ch and isinstance(self.extract_target_ch, list) and len(self.extract_target_ch) > 1:
                import numpy as np
                data = np.mean(data, axis=0, keepdims=True)
                current_ch_names = ["Average"]
            else:
                current_ch_names = self.data_model.channel_names if picks is None else [self.data_model.channel_names[i] for i in picks]

            self.extract_panel.update_features(data, sfreq, self.extract_window, self.extract_mode, 
                                             nperseg_override=self.extract_nperseg, 
                                             noverlap_override=self.extract_noverlap,
                                             band_str=self.extract_band,
                                             ch_names=current_ch_names,
                                             window_func=self.extract_window_func,
                                             scaling=self.extract_scaling,
                                             interp=self.extract_interp)
        except Exception as e:
            print(f"Error updating extract view: {e}")
