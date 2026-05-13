import os
import json
from PyQt6.QtWidgets import (
    QMainWindow, QSplitter, QDockWidget, QWidget, QVBoxLayout,
    QPushButton, QFileDialog, QMessageBox, QCheckBox, QComboBox, QSpinBox, QDoubleSpinBox, QLabel, QFormLayout,
    QMenuBar, QMenu, QToolBar, QListWidget, QListWidgetItem, QDialog, QDialogButtonBox
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
    HighpassFilterDialog, ViewFiltersDialog
)

class FeatureSettingsDialog(QDialog):
    def __init__(self, parent=None, channels=[]):
        super().__init__(parent)
        self.setWindowTitle("Feature Extract Settings")
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.cmb_mode = QComboBox()
        self.cmb_mode.addItems(["PSD", "Spectrogram"])
        
        self.spin_window = QSpinBox()
        self.spin_window.setRange(1, 60)
        self.spin_window.setSuffix(" s")
        
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
        self.spin_nperseg.setToolTip("Segment length (nperseg). 0 for Auto.")

        self.spin_noverlap = QSpinBox()
        self.spin_noverlap.setRange(0, 10000)
        self.spin_noverlap.setSpecialValueText("Auto")
        self.spin_noverlap.setToolTip("Overlap length (noverlap). 0 for Auto.")
        
        form.addRow("Extraction Mode:", self.cmb_mode)
        form.addRow("Analysis Window:", self.spin_window)
        form.addRow("Target Channels:", self.list_target_ch)
        form.addRow("Nperseg (Samples):", self.spin_nperseg)
        form.addRow("Noverlap (Samples):", self.spin_noverlap)
        
        layout.addLayout(form)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def set_values(self, mode, window, target_ch, nperseg, noverlap):
        self.cmb_mode.setCurrentText(mode.upper())
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

    def get_values(self):
        checked_channels = []
        for i in range(self.list_target_ch.count()):
            item = self.list_target_ch.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                checked_channels.append(item.text())
                
        return {
            "mode": self.cmb_mode.currentText().lower(),
            "window": self.spin_window.value(),
            "target_ch": checked_channels,
            "nperseg": self.spin_nperseg.value(),
            "noverlap": self.spin_noverlap.value()
        }

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EEGAnalyser")
        self.resize(1200, 800)
        
        self.data_model = EEGDataModel()
        
        # Internal state
        self.extract_mode = "psd"
        self.extract_window = 2
        self.extract_target_ch = []
        self.extract_nperseg = 0
        self.extract_noverlap = 0
        self.allow_overlap = False
        self.current_folder = ""
        self.recent_files = []
        self.recent_folders = []
        
        # Load recents from a simple local file
        self.load_recents()

        # Main splitter (vertical)
        self.main_splitter = QSplitter(Qt.Orientation.Vertical)
        self.setCentralWidget(self.main_splitter)

        # Top Panel: Feature Extraction View
        self.extract_panel = SpectralViewWidget()
        self.extract_panel.setVisible(False)
        self.main_splitter.addWidget(self.extract_panel)

        # Bottom Panel: Time-Series View
        self.time_series_plot = TimeSeriesPlot()
        self.main_splitter.addWidget(self.time_series_plot)

        # Set initial sizes
        self.main_splitter.setSizes([0, 800])

        # Channel Selection Dock
        self.setup_channel_dock()

        # Annotation Manager
        self.annotation_manager = AnnotationManager(self.time_series_plot, parent_window=self)

        # UI Components
        self.setup_menu_bar()
        self.setup_tool_bar()
        
        self.spectral_timer = QTimer()
        self.spectral_timer.setSingleShot(True)
        self.spectral_timer.timeout.connect(self.update_spectral_view)
        self.last_x_range = None

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
        except:
            pass

    def save_recents(self):
        try:
            path = os.path.expanduser("~/.eeganalyser_recents.json")
            with open(path, 'w') as f:
                json.dump({"files": self.recent_files, "folders": self.recent_folders}, f)
        except:
            pass

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

    def setup_channel_dock(self):
        self.channel_dock = QDockWidget("Channels", self)
        self.channel_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        # Make it thinner and fixed-ish
        self.channel_dock.setMinimumWidth(80)
        self.channel_dock.setMaximumWidth(140)
        
        dock_container = QWidget()
        main_dock_layout = QVBoxLayout(dock_container)
        main_dock_layout.setContentsMargins(2, 2, 2, 2)
        main_dock_layout.setSpacing(2)
        
        self.channel_list = QListWidget()
        # Modern borderless style with better item spacing
        self.channel_list.setStyleSheet("""
            QListWidget { 
                border: none; 
                background: transparent;
            }
            QListWidget::item {
                padding: 4px;
                border-bottom: 1px solid #f0f0f0;
            }
            QListWidget::item:selected {
                background: #e0e0e0;
                color: black;
            }
        """)
        self.channel_list.itemChanged.connect(self.on_channel_selection_changed)
        main_dock_layout.addWidget(self.channel_list)
        
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(1)
        btn_all = QPushButton("All")
        btn_all.setFixedHeight(22)
        btn_all.clicked.connect(self.select_all_channels)
        btn_none = QPushButton("None")
        btn_none.setFixedHeight(22)
        btn_none.clicked.connect(self.clear_all_channels)
        btn_layout.addWidget(btn_all)
        btn_layout.addWidget(btn_none)
        main_dock_layout.addLayout(btn_layout)
        
        self.channel_dock.setWidget(dock_container)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.channel_dock)

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

        export_action = QAction("&Export Annotations CSV", self)
        export_action.triggered.connect(lambda: self.annotation_manager.export_annotations(self))
        file_menu.addAction(export_action)
        
        view_menu = menubar.addMenu("&View")
        self.extract_action = QAction("Enable &Feature Extraction", self)
        self.extract_action.setCheckable(True)
        self.extract_action.triggered.connect(self.toggle_extract_view)
        view_menu.addAction(self.extract_action)
        
        settings_action = QAction("Feature Extract &Settings", self)
        settings_action.triggered.connect(self.open_extract_settings)
        view_menu.addAction(settings_action)

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

        settings_menu = menubar.addMenu("&Settings")
        overlap_action = QAction("Allow Overlapping Annotations", self)
        overlap_action.setCheckable(True)
        overlap_action.setChecked(self.allow_overlap)
        overlap_action.triggered.connect(self.toggle_overlap)
        settings_menu.addAction(overlap_action)
        
        self.update_recent_menus()

    def toggle_overlap(self, checked):
        self.allow_overlap = checked

    def setup_tool_bar(self):
        self.toolbar = QToolBar("Controls")
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)
        
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
        lbl_ds = QLabel(" Resolution: ")
        lbl_ds.setToolTip("0.0 = Auto. 1.0 = Full detail. 0.1 = 10% detail.")
        self.toolbar.addWidget(lbl_ds)
        
        self.spin_downsample = QDoubleSpinBox()
        self.spin_downsample.setRange(0.0, 1.0)
        self.spin_downsample.setSingleStep(0.1)
        self.spin_downsample.setValue(0.0)
        self.spin_downsample.setSpecialValueText("Auto")
        self.spin_downsample.setToolTip("Ratio of data to display (0.0 to 1.0).")
        self.spin_downsample.valueChanged.connect(self.handle_resolution_change)
        self.toolbar.addWidget(self.spin_downsample)
        
        self.lbl_ds_info = QLabel(" (Auto)")
        self.toolbar.addWidget(self.lbl_ds_info)
        self.time_series_plot.effective_downsample_changed.connect(
            lambda ds: self.lbl_ds_info.setText(f" (1px = {ds} samples)")
        )
        
        self.toolbar.addSeparator()
        
        # Folder Navigator Button
        self.btn_folder_nav = QPushButton("Navigator")
        self.btn_folder_nav.setEnabled(False)
        self.nav_menu = QMenu(self)
        self.btn_folder_nav.setMenu(self.nav_menu)
        self.toolbar.addWidget(self.btn_folder_nav)

    def handle_resolution_change(self, value):
        if value <= 0.0:
            self.time_series_plot.set_downsampling(0)
        else:
            factor = max(1, int(1.0 / value))
            self.time_series_plot.set_downsampling(factor)

    def open_extract_settings(self):
        dialog = FeatureSettingsDialog(self, channels=self.data_model.channel_names)
        dialog.set_values(self.extract_mode, self.extract_window, self.extract_target_ch, self.extract_nperseg, self.extract_noverlap)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            vals = dialog.get_values()
            self.extract_mode = vals["mode"]
            self.extract_window = vals["window"]
            self.extract_target_ch = vals["target_ch"]
            self.extract_nperseg = vals["nperseg"]
            self.extract_noverlap = vals["noverlap"]
            self.extract_panel.set_mode(self.extract_mode)
            if self.extract_action.isChecked():
                self.time_series_plot.set_locked_view(self.extract_window * 4, self.extract_window)
                self.update_spectral_view()

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
        print(f"MainWindow: Loading {filepath}")
        if self.data_model.load_edf(filepath):
            self.update_recents(file_path=filepath)
            self.annotation_manager.clear_annotations()
            self.setWindowTitle(f"EEGAnalyser - {filepath}")
            
            # Set a default target channel for extraction if none selected
            if not self.extract_target_ch and self.data_model.channel_names:
                self.extract_target_ch = self.data_model.channel_names[0]

            self.time_series_plot.plot_data(self.data_model)
            if self.extract_action.isChecked():
                self.time_series_plot.set_locked_view(self.extract_window * 4, self.extract_window)
                self.update_spectral_view()
            self.update()
        else:
            QMessageBox.critical(self, "Error", f"Failed to load EDF file: {filepath}")

    def open_folder_dialog(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if dir_path:
            self.open_folder(dir_path)

    def open_folder(self, dir_path):
        self.current_folder = dir_path
        self.update_recents(folder_path=dir_path)
        self.btn_folder_nav.setEnabled(True)
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
            if self.extract_target_ch:
                if isinstance(self.extract_target_ch, list) and len(self.extract_target_ch) > 0:
                    picks = [self.data_model.channel_names.index(ch) for ch in self.extract_target_ch if ch in self.data_model.channel_names]
                elif isinstance(self.extract_target_ch, str) and self.extract_target_ch:
                    picks = [self.data_model.channel_names.index(self.extract_target_ch)]
            
            data, _ = self.data_model.raw.get_data(picks=picks, tmin=tmin, tmax=tmax, return_times=True)
            
            # Average across channels if multiple are explicitly selected
            if data is not None and data.shape[0] > 1 and self.extract_target_ch and isinstance(self.extract_target_ch, list) and len(self.extract_target_ch) > 1:
                import numpy as np
                data = np.mean(data, axis=0, keepdims=True)

            self.extract_panel.update_features(data, sfreq, self.extract_window, self.extract_mode, 
                                             nperseg_override=self.extract_nperseg, 
                                             noverlap_override=self.extract_noverlap)
        except Exception as e:
            print(f"Error updating extract view: {e}")
