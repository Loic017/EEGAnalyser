from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox, 
    QDialogButtonBox, QFormLayout, QListWidget, QListWidgetItem, 
    QPushButton, QComboBox, QCheckBox
)
from PyQt6.QtCore import Qt

EXPERIMENTAL_DIALOG_STYLE = """
    QDialog {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0a0a0a, stop:0.5 #1a0a2e, stop:1 #0a1a2e);
    }
    QLabel {
        color: #00ffff;
        font-family: monospace;
        font-weight: bold;
    }
    QDoubleSpinBox, QSpinBox, QComboBox {
        background-color: #0a0a1a;
        color: #ffff00;
        border: 2px solid #ff00ff;
        border-radius: 8px;
        padding: 6px 10px;
        font-family: monospace;
        font-weight: bold;
    }
    QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus {
        border: 2px solid #00ffff;
    }
    QCheckBox {
        color: #00ffff;
        font-family: monospace;
        font-weight: bold;
        spacing: 8px;
    }
    QCheckBox::indicator {
        width: 20px;
        height: 20px;
        border-radius: 10px;
        border: 2px solid #ff00ff;
        background-color: #0a0a1a;
    }
    QCheckBox::indicator:checked {
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
    QPushButton:pressed {
        background: #00ff00;
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
        padding: 10px;
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
    QDialogButtonBox {
        dialogbuttonbox-buttons-have-icons: false;
    }
"""

DEFAULT_DIALOG_STYLE = """
    QDialog {
        background-color: #ffffff;
    }
    QLabel {
        color: #333333;
    }
    QDoubleSpinBox, QSpinBox, QComboBox {
        background-color: #ffffff;
        color: #333333;
        border: 1px solid #cccccc;
        border-radius: 4px;
        padding: 4px 8px;
    }
    QCheckBox {
        color: #333333;
        spacing: 6px;
    }
    QPushButton {
        background-color: #f0f0f0;
        color: #333333;
        border: 1px solid #cccccc;
        border-radius: 4px;
        padding: 6px 12px;
    }
    QPushButton:hover {
        background-color: #e0e0e0;
    }
    QListWidget {
        background-color: #ffffff;
        color: #333333;
        border: 1px solid #cccccc;
        border-radius: 4px;
    }
    QListWidget::item {
        padding: 6px;
        border-bottom: 1px solid #eeeeee;
    }
    QListWidget::item:hover {
        background-color: #f5f5f5;
    }
    QListWidget::item:selected {
        background-color: #0078d4;
        color: #ffffff;
    }
    QScrollBar:vertical {
        border: none;
        background: #f0f0f0;
        width: 10px;
        margin: 0px;
    }
    QScrollBar::handle:vertical {
        background: #cccccc;
        min-height: 20px;
        border-radius: 5px;
        margin: 2px;
    }
    QScrollBar::handle:vertical:hover {
        background: #aaaaaa;
    }
"""

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

        self._apply_style(parent)

    def _apply_style(self, parent):
        if parent and hasattr(parent, 'experimental_appearance') and parent.experimental_appearance:
            self.setStyleSheet(EXPERIMENTAL_DIALOG_STYLE)
        else:
            self.setStyleSheet(DEFAULT_DIALOG_STYLE)

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

        self._apply_style(parent)

    def _apply_style(self, parent):
        if parent and hasattr(parent, 'experimental_appearance') and parent.experimental_appearance:
            self.setStyleSheet(EXPERIMENTAL_DIALOG_STYLE)
        else:
            self.setStyleSheet(DEFAULT_DIALOG_STYLE)

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

        self._apply_style(parent)

    def _apply_style(self, parent):
        if parent and hasattr(parent, 'experimental_appearance') and parent.experimental_appearance:
            self.setStyleSheet(EXPERIMENTAL_DIALOG_STYLE)
        else:
            self.setStyleSheet(DEFAULT_DIALOG_STYLE)

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

        self._apply_style(parent)

    def _apply_style(self, parent):
        if parent and hasattr(parent, 'experimental_appearance') and parent.experimental_appearance:
            self.setStyleSheet(EXPERIMENTAL_DIALOG_STYLE)
        else:
            self.setStyleSheet(DEFAULT_DIALOG_STYLE)

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

        self._apply_style(parent)

    def _apply_style(self, parent):
        if parent and hasattr(parent, 'experimental_appearance') and parent.experimental_appearance:
            self.setStyleSheet(EXPERIMENTAL_DIALOG_STYLE)
        else:
            self.setStyleSheet(DEFAULT_DIALOG_STYLE)

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

        self._apply_style(parent)

    def _apply_style(self, parent):
        if parent and hasattr(parent, 'experimental_appearance') and parent.experimental_appearance:
            self.setStyleSheet(EXPERIMENTAL_DIALOG_STYLE)
        else:
            self.setStyleSheet(DEFAULT_DIALOG_STYLE)

    def remove_selected(self):
        current_item = self.list_widget.currentItem()
        if current_item:
            index = current_item.data(Qt.ItemDataRole.UserRole)
            self.removed_indices.append(index)
            self.list_widget.takeItem(self.list_widget.row(current_item))
            self.accept()
