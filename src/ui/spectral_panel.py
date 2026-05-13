from PyQt6.QtWidgets import QWidget, QVBoxLayout, QStackedWidget
import pyqtgraph as pg
import scipy.signal
import numpy as np

class SpectralViewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.stack = QStackedWidget()
        self.layout.addWidget(self.stack)
        
        # --- PSD View ---
        self.psd_widget = pg.GraphicsLayoutWidget()
        self.psd_widget.setBackground('w')
        
        # --- Spectrogram View ---
        self.spec_widget = pg.GraphicsLayoutWidget()
        self.spec_widget.setBackground('w')
        
        self.psd_plots = []
        self.spec_plots = []
        self.spec_images = []
        
        colormap = pg.colormap.get('viridis')
        
        for i in range(4):
            # PSD
            p = self.psd_widget.addPlot(title=f"Window {i+1}")
            curve = p.plot(pen=pg.mkPen('b', width=1.5))
            p.setLabel('bottom', "Freq", units='Hz')
            p.setLabel('left', "Power", units='dB')
            p.showGrid(x=True, y=True)
            self.psd_plots.append((p, curve))
            
            # Spectrogram
            sp = self.spec_widget.addPlot(title=f"Window {i+1}")
            img = pg.ImageItem()
            sp.addItem(img)
            sp.setLabel('bottom', "Time", units='s')
            sp.setLabel('left', "Freq", units='Hz')
            img.setLookupTable(colormap.getLookupTable())
            self.spec_plots.append(sp)
            self.spec_images.append(img)
            
        self.stack.addWidget(self.psd_widget)
        self.stack.addWidget(self.spec_widget)
        
        self.current_mode = 'psd'
        self.set_mode('psd')

    def set_mode(self, mode: str):
        self.current_mode = mode.lower()
        if self.current_mode == 'psd':
            self.stack.setCurrentWidget(self.psd_widget)
        elif self.current_mode == 'spectrogram':
            self.stack.setCurrentWidget(self.spec_widget)

    def _clear_plot(self, idx: int, mode: str):
        if mode == 'psd':
            if self.psd_plots[idx][0].vb.width() > 0:
                self.psd_plots[idx][1].clear()
        else:
            if self.spec_plots[idx].vb.width() > 0:
                self.spec_images[idx].clear()

    def update_features(self, data: np.ndarray, sfreq: float, window_size_sec: float, mode: str, nperseg_override: int = 0, noverlap_override: int = 0):
        if not self.isVisible() or data.size == 0 or sfreq == 0:
            return
            
        # VERY IMPORTANT: Only update the widget that is actually visible in the stack.
        # Updating hidden GraphicsLayoutWidgets can trigger QPainter errors during layout/autoRange.
        active_widget = self.stack.currentWidget()
        if mode == 'psd' and active_widget != self.psd_widget:
            return
        if mode == 'spectrogram' and active_widget != self.spec_widget:
            return
            
        n_samples_per_window = int(window_size_sec * sfreq)
        
        for i in range(4):
            start_idx = i * n_samples_per_window
            end_idx = start_idx + n_samples_per_window
            if start_idx >= data.shape[1]:
                self._clear_plot(i, mode)
                continue
                
            chunk = data[:, start_idx:min(end_idx, data.shape[1])]
            if chunk.shape[1] < 2:
                self._clear_plot(i, mode)
                continue
                
            try:
                if mode == 'psd':
                    # Match spectrogram logic: use first channel for analysis
                    chunk_to_use = chunk[0]
                    nperseg = nperseg_override if nperseg_override > 0 else min(int(window_size_sec * sfreq), chunk_to_use.shape[0])
                    nperseg = min(nperseg, chunk_to_use.shape[0])
                    if nperseg < 2:
                        self._clear_plot(i, mode)
                        continue
                        
                    freqs, psd = scipy.signal.welch(chunk_to_use, fs=sfreq, nperseg=nperseg)
                    if freqs.size > 1 and psd.size > 1:
                        # Convert to dB and ensure no NaNs/Infs
                        psd_db = np.nan_to_num(10 * np.log10(psd + 1e-20), posinf=0.0, neginf=0.0)
                        
                        # Only update and auto-range if the view has a valid size to avoid QPainter issues
                        if self.psd_plots[i][0].vb.width() > 0 and self.psd_plots[i][0].vb.height() > 0:
                            self.psd_plots[i][1].setData(freqs, psd_db)
                            self.psd_plots[i][0].autoRange()
                        else:
                            self._clear_plot(i, mode)
                    else:
                        self._clear_plot(i, mode)
                elif mode == 'spectrogram':
                    # Nperseg needs to be small enough for the window to yield multiple time bins
                    chunk_to_use = chunk[0]
                    nperseg = nperseg_override if nperseg_override > 0 else max(2, min(int(sfreq * 0.25), chunk_to_use.shape[0]))
                    nperseg = min(nperseg, chunk_to_use.shape[0])
                    noverlap = noverlap_override if noverlap_override > 0 else nperseg // 2
                    noverlap = min(noverlap, nperseg - 1)
                    
                    if chunk_to_use.shape[0] < nperseg:
                        self._clear_plot(i, mode)
                        continue
                        
                    f, t, Sxx = scipy.signal.spectrogram(chunk_to_use, fs=sfreq, nperseg=nperseg, noverlap=noverlap)
                    if Sxx.size == 0:
                        self._clear_plot(i, mode)
                        continue
                        
                    Sxx_log = np.nan_to_num(10 * np.log10(Sxx + 1e-10), posinf=0.0, neginf=0.0)
                    
                    # Ensure positive dimensions and valid view before updating/auto-ranging
                    w = t[-1] - t[0] if len(t) > 1 else 0.0
                    h = f[-1] - f[0] if len(f) > 1 else 0.0
                    if w > 0 and h > 0 and self.spec_plots[i].vb.width() > 0:
                        self.spec_images[i].setImage(Sxx_log.T, autoLevels=True)
                        self.spec_images[i].setRect(pg.QtCore.QRectF(t[0], f[0], w, h))
                        self.spec_plots[i].autoRange()
                    else:
                        self._clear_plot(i, mode)
            except Exception as e:
                print(f"SpectralView ERROR (Window {i+1}): {e}")
                self._clear_plot(i, mode)
