from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox, 
    QDialogButtonBox, QFormLayout, QListWidget, QListWidgetItem, 
    QPushButton, QComboBox, QCheckBox
)
from PyQt6.QtCore import Qt

class ResolutionSettingsDialog(QDialog):
    def __init__(self, parent=None, is_auto=True, current_factor=1):
        super().__init__(parent)
        self.setWindowTitle("Resolution Settings")
        layout = QVBoxLayout(self)
        
        self.chk_auto = QCheckBox("Auto Resolution (Adjust for window size)")
        self.chk_auto.setChecked(is_auto)
        
        form = QFormLayout()
        self.combo_factor = QComboBox()
        self.factors_map = {
            "1x (Max Detail)": 1,
            "2x": 2,
            "4x": 4,
            "8x": 8,
            "16x": 16,
            "32x": 32,
            "64x": 64,
            "128x": 128,
            "256x": 256,
            "512x (Low Detail)": 512
        }
        for k in self.factors_map.keys():
            self.combo_factor.addItem(k)
        
        # Find nearest factor to current_factor
        current_idx = 0
        best_diff = float('inf')
        for idx, (k, v) in enumerate(self.factors_map.items()):
            diff = abs(v - current_factor)
            if diff < best_diff:
                best_diff = diff
                current_idx = idx
        
        self.combo_factor.setCurrentIndex(current_idx)
        self.combo_factor.setEnabled(not is_auto)
        self.chk_auto.stateChanged.connect(self.on_auto_changed)
        
        form.addRow("Manual Decimation:", self.combo_factor)
        
        layout.addWidget(self.chk_auto)
        layout.addLayout(form)
        
        lbl_hint = QLabel("<i>Note: High decimation factors speed up rendering for long files.</i>")
        lbl_hint.setWordWrap(True)
        layout.addWidget(lbl_hint)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def on_auto_changed(self, state):
        self.combo_factor.setEnabled(state != Qt.CheckState.Checked.value)

    def get_values(self):
        selected_text = self.combo_factor.currentText()
        return {
            "is_auto": self.chk_auto.isChecked(),
            "factor": self.factors_map[selected_text]
        }

class NotchFilterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Notch Filter Settings")
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.spin_freq = QDoubleSpinBox()
        self.spin_freq.setRange(0.1, 500.0)
        self.spin_freq.setValue(50.0)
        self.spin_freq.setSuffix(" Hz")
        
        form.addRow("Frequency:", self.spin_freq)
        layout.addLayout(form)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_values(self):
        return {"freqs": self.spin_freq.value()}

class BandpassFilterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Band-pass Filter Settings")
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.spin_low = QDoubleSpinBox()
        self.spin_low.setRange(0.1, 500.0)
        self.spin_low.setValue(1.0)
        self.spin_low.setSuffix(" Hz")
        
        self.spin_high = QDoubleSpinBox()
        self.spin_high.setRange(0.1, 500.0)
        self.spin_high.setValue(40.0)
        self.spin_high.setSuffix(" Hz")
        
        form.addRow("Low Cutoff:", self.spin_low)
        form.addRow("High Cutoff:", self.spin_high)
        layout.addLayout(form)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_values(self):
        return {"l_freq": self.spin_low.value(), "h_freq": self.spin_high.value()}

class LowpassFilterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Low-pass Filter Settings")
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.spin_high = QDoubleSpinBox()
        self.spin_high.setRange(0.1, 500.0)
        self.spin_high.setValue(40.0)
        self.spin_high.setSuffix(" Hz")
        
        form.addRow("High Cutoff:", self.spin_high)
        layout.addLayout(form)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_values(self):
        return {"h_freq": self.spin_high.value()}

class HighpassFilterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("High-pass Filter Settings")
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.spin_low = QDoubleSpinBox()
        self.spin_low.setRange(0.1, 500.0)
        self.spin_low.setValue(1.0)
        self.spin_low.setSuffix(" Hz")
        
        form.addRow("Low Cutoff:", self.spin_low)
        layout.addLayout(form)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_values(self):
        return {"l_freq": self.spin_low.value()}

class ViewFiltersDialog(QDialog):
    def __init__(self, applied_filters, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Applied Filters")
        self.resize(300, 400)
        layout = QVBoxLayout(self)
        
        self.list_widget = QListWidget()
        for i, filt in enumerate(applied_filters):
            f_type = filt["type"]
            params = filt["params"]
            text = f"{f_type.capitalize()}: "
            if f_type == "notch":
                text += f"{params['freqs']} Hz"
            elif f_type == "bandpass":
                text += f"{params['l_freq']} - {params['h_freq']} Hz"
            elif f_type == "lowpass":
                text += f"< {params['h_freq']} Hz"
            elif f_type == "highpass":
                text += f"> {params['l_freq']} Hz"
            
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, i)
            self.list_widget.addItem(item)
            
        layout.addWidget(self.list_widget)
        
        self.btn_remove = QPushButton("Remove Selected Filter")
        self.btn_remove.clicked.connect(self.remove_selected)
        layout.addWidget(self.btn_remove)
        
        self.removed_indices = []
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def remove_selected(self):
        current_item = self.list_widget.currentItem()
        if current_item:
            index = current_item.data(Qt.ItemDataRole.UserRole)
            self.removed_indices.append(index)
            # Remove from list widget immediately
            self.list_widget.takeItem(self.list_widget.row(current_item))
            # Since we can remove multiple, we need to be careful with indices.
            # Actually, better to just remove one and close or handle it properly.
            # If we remove multiple, the indices in self.applied_filters shift.
            # A simpler way is to signal the parent to remove and then refresh.
            self.accept() # Close and signal removal
