from PyQt6.QtWidgets import (
    QInputDialog, QMessageBox, QFileDialog, QDialog, 
    QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QDoubleSpinBox, 
    QDialogButtonBox, QLabel, QScrollArea, QWidget, QPushButton
)
import pyqtgraph as pg
import pandas as pd
import hashlib
from typing import List, Dict

class AnnotationDialog(QDialog):
    def __init__(self, parent=None, max_time=1000.0, manager=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Annotations")
        self.manager = manager
        self.setMinimumWidth(450)
        
        layout = QVBoxLayout(self)
        
        # --- List of Existing Annotations ---
        if self.manager and self.manager.annotations:
            layout.addWidget(QLabel("<b>Current Annotations:</b>"))
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setMaximumHeight(200)
            scroll_content = QWidget()
            scroll_layout = QVBoxLayout(scroll_content)
            
            # Create a copy of the list to iterate safely
            for ann in list(self.manager.annotations):
                row = QHBoxLayout()
                rgn = ann['region_item'].getRegion()
                text = f"<b>{ann['label']}</b>: {rgn[0]:.3f}s - {rgn[1]:.3f}s"
                row.addWidget(QLabel(text))
                
                btn_del = QPushButton("X")
                btn_del.setFixedWidth(30)
                btn_del.setStyleSheet("color: red; font-weight: bold;")
                # Use a closure to capture the specific annotation dictionary
                btn_del.clicked.connect(lambda checked, a=ann: self.delete_clicked(a))
                row.addWidget(btn_del)
                scroll_layout.addLayout(row)
            
            scroll_layout.addStretch()
            scroll.setWidget(scroll_content)
            layout.addWidget(scroll)
            
            line = QWidget()
            line.setFixedHeight(2)
            line.setStyleSheet("background-color: #ddd;")
            layout.addWidget(line)

        # --- Add New Annotation ---
        layout.addWidget(QLabel("<b>Add New Annotation:</b>"))
        form = QFormLayout()
        
        self.label_edit = QLineEdit()
        self.start_spin = QDoubleSpinBox()
        self.start_spin.setRange(0, max_time)
        self.start_spin.setDecimals(3)
        self.start_spin.setSuffix(" s")
        
        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setRange(0, max_time)
        self.duration_spin.setDecimals(3)
        self.duration_spin.setSuffix(" s")

        self.end_spin = QDoubleSpinBox()
        self.end_spin.setRange(0, max_time)
        self.end_spin.setDecimals(3)
        self.end_spin.setSuffix(" s")
        self.end_spin.setValue(min(max_time, 10.0))
        
        # Connect sync logic
        self.start_spin.valueChanged.connect(self._sync_end_from_start_duration)
        self.duration_spin.valueChanged.connect(self._sync_end_from_start_duration)
        self.end_spin.valueChanged.connect(self._sync_duration_from_start_end)

        form.addRow("Label:", self.label_edit)
        form.addRow("Start Time:", self.start_spin)
        form.addRow("Duration:", self.duration_spin)
        form.addRow("End Time:", self.end_spin)
        
        layout.addLayout(form)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _sync_end_from_start_duration(self):
        if self.end_spin.signalsBlocked():
            return
        self.end_spin.blockSignals(True)
        self.end_spin.setValue(self.start_spin.value() + self.duration_spin.value())
        self.end_spin.blockSignals(False)

    def _sync_duration_from_start_end(self):
        if self.duration_spin.signalsBlocked():
            return
        self.duration_spin.blockSignals(True)
        self.duration_spin.setValue(max(0, self.end_spin.value() - self.start_spin.value()))
        self.duration_spin.blockSignals(False)

    def delete_clicked(self, ann_dict):
        reply = QMessageBox.question(self, "Confirm Delete", 
                                   f"Remove annotation '{ann_dict['label']}'?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if self.manager:
                self.manager.remove_annotation(ann_dict)
                self.accept() # Close and reopen to refresh or just finish
                self.manager.add_annotation_region() # Re-open for convenience

    def validate_and_accept(self):
        label = self.label_edit.text().strip()
        start = self.start_spin.value()
        end = self.end_spin.value()

        if not label:
            QMessageBox.warning(self, "Input Error", "Please enter a label.")
            return
        if start >= end:
            QMessageBox.warning(self, "Input Error", "Start time must be less than end time.")
            return

        # Check for overlap if not allowed
        if self.manager and self.manager.parent_window and not getattr(self.manager.parent_window, 'allow_overlap', True):
            for ann in self.manager.annotations:
                # Get current region boundaries
                r_start, r_end = ann['region_item'].getRegion()
                # If new annotation overlaps with any existing one
                if start < r_end and end > r_start:
                    QMessageBox.warning(self, "Overlap Error", 
                                       f"Annotation overlaps with existing '{ann['label']}'\n"
                                       f"({r_start:.3f}s - {r_end:.3f}s).\n\n"
                                       "Enable 'Allow Overlapping Annotations' in Settings to override.")
                    return

        self.accept()

    def get_data(self):
        return {
            'label': self.label_edit.text().strip(),
            'start': self.start_spin.value(),
            'end': self.end_spin.value()
        }

class HoverableLinearRegionItem(pg.LinearRegionItem):
    """A LinearRegionItem that emits signals when hovered."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptHoverEvents(True)
        self.hovered = False
        self.on_hover_change = None # Callback function

    def hoverEvent(self, ev):
        if ev.isEnter():
            self.hovered = True
            if self.on_hover_change:
                self.on_hover_change(True)
        elif ev.isExit():
            self.hovered = False
            if self.on_hover_change:
                self.on_hover_change(False)

class ViewAnnotationsDialog(QDialog):
    def __init__(self, parent=None, manager=None):
        super().__init__(parent)
        self.setWindowTitle("View Annotations")
        self.manager = manager
        self.resize(500, 400)
        
        layout = QVBoxLayout(self)
        
        if not self.manager or not self.manager.annotations:
            layout.addWidget(QLabel("No annotations available."))
        else:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll_content = QWidget()
            self.scroll_layout = QVBoxLayout(scroll_content)
            
            self.refresh_list()
            
            scroll.setWidget(scroll_content)
            layout.addWidget(scroll)
            
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def refresh_list(self):
        # Clear existing
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

        for ann in self.manager.annotations:
            row = QHBoxLayout()
            rgn = ann['region_item'].getRegion()
            text = f"<b>{ann['label']}</b><br/>{rgn[0]:.2f}s - {rgn[1]:.2f}s (Dur: {rgn[1]-rgn[0]:.2f}s)"
            lbl = QLabel(text)
            row.addWidget(lbl)
            
            btn_goto = QPushButton("Go To")
            btn_goto.setFixedWidth(60)
            btn_goto.clicked.connect(lambda checked, a=ann: self.goto_annotation(a))
            row.addWidget(btn_goto)

            btn_del = QPushButton("Delete")
            btn_del.setFixedWidth(60)
            btn_del.setStyleSheet("color: red;")
            btn_del.clicked.connect(lambda checked, a=ann: self.delete_annotation(a))
            row.addWidget(btn_del)
            
            self.scroll_layout.addLayout(row)
        
        self.scroll_layout.addStretch()

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def goto_annotation(self, ann):
        if self.manager and self.manager.plot_widget:
            rgn = ann['region_item'].getRegion()
            # Center the view on the annotation
            duration = rgn[1] - rgn[0]
            # If duration is very small, show a bit more padding
            view_width = max(duration * 2, 5.0) 
            center = (rgn[0] + rgn[1]) / 2
            start = max(0, center - view_width / 2)
            end = start + view_width
            self.manager.plot_widget.plot_item.setXRange(start, end, padding=0)

    def delete_annotation(self, ann):
        reply = QMessageBox.question(self, "Confirm Delete", 
                                   f"Remove annotation '{ann['label']}'?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.manager.remove_annotation(ann)
            if not self.manager.annotations:
                self.accept()
            else:
                self.refresh_list()

class AnnotationManager:
    def __init__(self, plot_widget: 'TimeSeriesPlot', parent_window=None):
        self.plot_widget = plot_widget
        self.parent_window = parent_window
        self.annotations: List[Dict] = []

    def view_annotations(self):
        if not self.annotations:
            QMessageBox.information(self.parent_window, "Annotations", "No annotations found.")
            return
        
        dialog = ViewAnnotationsDialog(self.parent_window, manager=self)
        dialog.exec()

    def clear_annotations(self):
        for ann in list(self.annotations):
            self.remove_annotation(ann)
        self.annotations.clear()

    def remove_annotation(self, ann_dict):
        if ann_dict in self.annotations:
            self.plot_widget.plot_item.removeItem(ann_dict['region_item'])
            self.plot_widget.plot_item.removeItem(ann_dict['text_item'])
            self.annotations.remove(ann_dict)

    def add_annotation_region(self):
        try:
            if self.plot_widget.data_model is None or self.plot_widget.data_model.raw is None:
                parent = self.parent_window if self.parent_window else self.plot_widget
                QMessageBox.information(parent, "Info", "Please load an EDF file first.")
                return

            max_time = self.plot_widget.total_duration
            dialog = AnnotationDialog(self.parent_window, max_time=max_time, manager=self)
            
            # Pre-fill with current view range for convenience
            current_range = self.plot_widget.current_x_range
            dialog.start_spin.setValue(max(0, current_range[0]))
            dialog.end_spin.setValue(min(max_time, current_range[1]))
            # Ensure duration is synced (though signals should have handled it)
            dialog._sync_duration_from_start_end()
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                data = dialog.get_data()
                if data['label']: # Only create if we have data (not from delete accept)
                    self._create_annotation(data['label'], data['start'], data['end'])
                
        except Exception as e:
            parent = self.parent_window if self.parent_window else self.plot_widget
            QMessageBox.critical(parent, "Error", f"Failed to add annotation: {e}")
            print(f"Annotation error: {e}")

    def _get_color_for_label(self, label):
        """Returns a (R, G, B) tuple for the given label."""
        mapping = {
            "1": (0, 0, 255),      # Blue
            "2": (255, 0, 0),      # Red
            "3": (0, 255, 0),      # Green
            "4": (255, 165, 0),    # Orange
        }
        
        label_str = str(label).strip()
        if label_str in mapping:
            return mapping[label_str]
        
        # Consistent random color based on hash
        hash_val = int(hashlib.md5(label_str.encode()).hexdigest(), 16)
        r = (hash_val & 0xFF0000) >> 16
        g = (hash_val & 0x00FF00) >> 8
        b = (hash_val & 0x0000FF)
        
        return (r, g, b)

    def _create_annotation(self, label, start, end):
        plot_item = self.plot_widget.plot_item
        view_box = plot_item.getViewBox()
        
        color = self._get_color_for_label(label)
        brush_color = (*color, 60) # RGB + Alpha
        
        region = HoverableLinearRegionItem([start, end], brush=brush_color, movable=False)
        region.setToolTip(f"Label: {label}\nStart: {start:.3f}s\nEnd: {end:.3f}s")
        plot_item.addItem(region)
        
        text_item = pg.TextItem(text=label, anchor=(0.5, 0), color=color)
        text_item.setToolTip(f"Annotation Label: {label}")
        text_item.setVisible(False) # Hidden by default, shown on hover
        plot_item.addItem(text_item)
        
        def update_text_pos():
            rgn = region.getRegion()
            y_range = view_box.viewRange()[1]
            # Ensure text is slightly above the plot area
            text_item.setPos((rgn[0] + rgn[1])/2, y_range[1])
            
        def on_hover(is_hovered):
            text_item.setVisible(is_hovered)
            if is_hovered:
                update_text_pos()

        region.on_hover_change = on_hover
        
        # We still connect to sigRegionChanged in case we ever re-enable dragging,
        # but also call it once now.
        region.sigRegionChanged.connect(update_text_pos)
        update_text_pos()
        
        self.annotations.append({
            'label': label,
            'region_item': region,
            'text_item': text_item
        })

    def load_labels_from_json(self, filepath: str):
        """Loads annotations from a JSON file."""
        import json
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Support both a single object and a list of objects
            if isinstance(data, dict):
                items = [data]
            elif isinstance(data, list):
                items = data
            else:
                print(f"AnnotationManager: Invalid JSON format in {filepath}")
                return

            count = 0
            for item in items:
                label = item.get('label', 'Unknown')
                # Convert milliseconds to seconds
                start_ms = item.get('start', 0)
                end_ms = item.get('end', 0)
                
                start_s = start_ms / 1000.0
                end_s = end_ms / 1000.0
                
                if end_s > start_s:
                    self._create_annotation(label, start_s, end_s)
                    count += 1
            
            print(f"AnnotationManager: Loaded {count} annotations from {filepath}")
        except Exception as e:
            print(f"AnnotationManager ERROR: Failed to load labels from {filepath}: {e}")

    def export_annotations(self, parent_window):
        if not self.annotations:
            QMessageBox.information(parent_window, "Info", "No annotations to export.")
            return

        filepath, _ = QFileDialog.getSaveFileName(parent_window, "Export Annotations", "", "CSV Files (*.csv)")
        if filepath:
            data = []
            for ann in self.annotations:
                rgn = ann['region_item'].getRegion()
                data.append({
                    'label': ann['label'],
                    'start_time': rgn[0],
                    'end_time': rgn[1]
                })
            df = pd.DataFrame(data)
            try:
                df.to_csv(filepath, index=False)
                QMessageBox.information(parent_window, "Success", f"Annotations exported to {filepath}")
            except Exception as e:
                QMessageBox.critical(parent_window, "Error", f"Failed to export annotations: {e}")