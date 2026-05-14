from PyQt6.QtWidgets import QWidget, QVBoxLayout, QStackedWidget
import pyqtgraph as pg
import scipy.signal
import scipy.interpolate
import numpy as np
import mne

class SpectralViewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        self.stack = QStackedWidget()
        self.layout.addWidget(self.stack)
        
        # --- PSD View ---
        self.psd_widget = pg.GraphicsLayoutWidget()
        self.psd_widget.setBackground('w')
        
        # --- Spectrogram View ---
        self.spec_widget = pg.GraphicsLayoutWidget()
        self.spec_widget.setBackground('w')

        # --- Topomap View ---
        self.topo_widget = pg.GraphicsLayoutWidget()
        self.topo_widget.setBackground('w')
        
        self.psd_plots = []
        self.spec_plots = []
        self.spec_images = []
        self.topo_plots = []
        self.topo_images = []
        
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

            # Topomap
            tp = self.topo_widget.addPlot(title=f"Window {i+1}")
            timg = pg.ImageItem()
            tp.addItem(timg)
            tp.setAspectLocked(True)
            tp.invertY(False)
            tp.hideAxis('bottom')
            tp.hideAxis('left')
            timg.setLookupTable(pg.colormap.get('viridis').getLookupTable())
            self.topo_plots.append(tp)
            self.topo_images.append(timg)
            
        self.stack.addWidget(self.psd_widget)
        self.stack.addWidget(self.spec_widget)
        self.stack.addWidget(self.topo_widget)
        
        self.current_mode = 'psd'
        self.set_mode('psd')

    def set_mode(self, mode: str):
        self.current_mode = mode.lower()
        if self.current_mode == 'psd':
            self.stack.setCurrentWidget(self.psd_widget)
        elif self.current_mode == 'spectrogram':
            self.stack.setCurrentWidget(self.spec_widget)
        elif self.current_mode == 'topomap':
            self.stack.setCurrentWidget(self.topo_widget)

    def _clear_plot(self, idx: int, mode: str):
        if mode == 'psd':
            if self.psd_plots[idx][0].vb.width() > 0:
                self.psd_plots[idx][1].clear()
        elif mode == 'spectrogram':
            if self.spec_plots[idx].vb.width() > 0:
                self.spec_images[idx].clear()
        elif mode == 'topomap':
            if self.topo_plots[idx].vb.width() > 0:
                self.topo_images[idx].clear()

    def update_features(self, data: np.ndarray, sfreq: float, window_size_sec: float, mode: str, 
                        nperseg_override: int = 0, noverlap_override: int = 0, 
                        band_str: str = "Alpha (8-12 Hz)", ch_names: list = []):
        if not self.isVisible() or data.size == 0 or sfreq == 0:
            return
            
        # VERY IMPORTANT: Only update the widget that is actually visible in the stack.
        active_widget = self.stack.currentWidget()
        if mode == 'psd' and active_widget != self.psd_widget:
            return
        if mode == 'spectrogram' and active_widget != self.spec_widget:
            return
        if mode == 'topomap' and active_widget != self.topo_widget:
            return
            
        n_samples_per_window = int(window_size_sec * sfreq)
        
        # Prepare band for topomap if needed
        band_range = (8, 12)
        if mode == 'topomap':
            import re
            match = re.search(r"(\d+)-(\d+)", band_str)
            if match:
                band_range = (int(match.group(1)), int(match.group(2)))
            
            # Get channel positions
            pos = self._get_ch_pos(ch_names)
            if pos is None:
                for i in range(4): self._clear_plot(i, mode)
                return

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
                    chunk_to_use = chunk[0]
                    nperseg = nperseg_override if nperseg_override > 0 else min(int(window_size_sec * sfreq), chunk_to_use.shape[0])
                    nperseg = min(nperseg, chunk_to_use.shape[0])
                    if nperseg < 2:
                        self._clear_plot(i, mode)
                        continue
                        
                    freqs, psd = scipy.signal.welch(chunk_to_use, fs=sfreq, nperseg=nperseg)
                    if freqs.size > 1 and psd.size > 1:
                        psd_db = np.nan_to_num(10 * np.log10(psd + 1e-20), posinf=0.0, neginf=0.0)
                        if self.psd_plots[i][0].vb.width() > 0 and self.psd_plots[i][0].vb.height() > 0:
                            self.psd_plots[i][1].setData(freqs, psd_db)
                            self.psd_plots[i][0].autoRange()
                        else:
                            self._clear_plot(i, mode)
                    else:
                        self._clear_plot(i, mode)

                elif mode == 'spectrogram':
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
                    w = t[-1] - t[0] if len(t) > 1 else 0.0
                    h = f[-1] - f[0] if len(f) > 1 else 0.0
                    if w > 0 and h > 0 and self.spec_plots[i].vb.width() > 0:
                        self.spec_images[i].setImage(Sxx_log.T, autoLevels=True)
                        self.spec_images[i].setRect(pg.QtCore.QRectF(t[0], f[0], w, h))
                        self.spec_plots[i].autoRange()
                    else:
                        self._clear_plot(i, mode)

                elif mode == 'topomap':
                    # Calculate band power for all channels
                    nperseg = nperseg_override if nperseg_override > 0 else min(int(sfreq), chunk.shape[1])
                    f, psd = scipy.signal.welch(chunk, fs=sfreq, nperseg=nperseg, axis=1)
                    
                    idx_band = np.logical_and(f >= band_range[0], f <= band_range[1])
                    if not np.any(idx_band):
                        self._clear_plot(i, mode)
                        continue
                        
                    band_power = np.mean(psd[:, idx_band], axis=1)
                    # Convert to dB for better visualization range
                    band_power_db = 10 * np.log10(band_power + 1e-20)
                    
                    # Interpolate
                    grid_x, grid_y = np.mgrid[-0.6:0.6:100j, -0.6:0.6:100j]
                    # Project 3D pos to 2D
                    points = pos[:, :2]
                    values = band_power_db
                    
                    # RBF or GridData interpolation
                    zi = scipy.interpolate.griddata(points, values, (grid_x, grid_y), method='cubic')
                    
                    # Mask to circle
                    mask = np.sqrt(grid_x**2 + grid_y**2) > 0.5
                    zi[mask] = np.nan
                    
                    if self.topo_plots[i].vb.width() > 0:
                        # pyqtgraph ImageItem expects (width, height)
                        self.topo_images[i].setImage(zi, autoLevels=True)
                        self.topo_images[i].setRect(pg.QtCore.QRectF(-0.6, -0.6, 1.2, 1.2))
                        self.topo_plots[i].autoRange()
                    else:
                        self._clear_plot(i, mode)

            except Exception as e:
                print(f"SpectralView ERROR (Window {i+1}): {e}")
                self._clear_plot(i, mode)

    def _get_ch_pos(self, ch_names):
        try:
            # Try to get standard montage
            montage = mne.channels.make_standard_montage('standard_1020')
            # Filter and reorder to match our ch_names
            # MNE might have slightly different naming (e.g., 'FP1' vs 'Fp1')
            ch_names_upper = [c.upper() for c in ch_names]
            montage_names_upper = [c.upper() for c in montage.ch_names]
            
            pos = []
            valid_indices = []
            for i, name in enumerate(ch_names_upper):
                if name in montage_names_upper:
                    m_idx = montage_names_upper.index(name)
                    # Get 3D position
                    p = montage.dig[m_idx + 3]['r'] # First 3 are cardinal points usually
                    pos.append(p)
                    valid_indices.append(i)
                else:
                    # Fallback for common misspellings or 'EEG Fp1' etc
                    found = False
                    for m_idx, m_name in enumerate(montage_names_upper):
                        if m_name in name or name in m_name:
                            p = montage.dig[m_idx + 3]['r']
                            pos.append(p)
                            valid_indices.append(i)
                            found = True
                            break
                    if not found:
                        pass # Cannot find position for this channel

            if len(pos) < 3:
                return None
                
            pos = np.array(pos)
            # Simple projection to 2D
            return pos
        except Exception as e:
            print(f"Error getting channel positions: {e}")
            return None
