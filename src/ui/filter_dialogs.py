from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox, 
    QDialogButtonBox, QFormLayout, QListWidget, QListWidgetItem, 
    QPushButton
)
from PyQt6.QtCore import Qt

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
