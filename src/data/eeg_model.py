import mne
import numpy as np
from typing import Optional, Tuple, List

class EEGDataModel:
    def __init__(self):
        self.raw: Optional[mne.io.Raw] = None
        self.original_raw: Optional[mne.io.Raw] = None
        self.filename: str = ""
        self.channel_names: List[str] = []
        self.sfreq: float = 0.0
        self.applied_filters: List[dict] = []

    def load_edf(self, filepath: str) -> bool:
        print(f"EEGDataModel: Attempting to load {filepath}")
        try:
            # For EDF, mne.io.read_raw_edf is the standard. 
            # We use preload=True to keep data in memory for fast access in this prototype.
            self.original_raw = mne.io.read_raw_edf(filepath, preload=True, verbose='error')
            self.raw = self.original_raw.copy()
            self.filename = filepath
            self.channel_names = self.raw.ch_names
            self.sfreq = self.raw.info['sfreq']
            self.applied_filters = []
            print(f"EEGDataModel: Successfully loaded {len(self.channel_names)} channels at {self.sfreq} Hz")
            return True
        except Exception as e:
            print(f"EEGDataModel ERROR: Failed to load EDF: {e}")
            import traceback
            traceback.print_exc()
            return False

    def apply_filter(self, filter_type: str, params: dict):
        """Adds a filter to the list and re-applies all filters."""
        self.applied_filters.append({"type": filter_type, "params": params})
        self._reapply_filters()

    def remove_filter(self, index: int):
        """Removes a filter by index and re-applies remaining filters."""
        if 0 <= index < len(self.applied_filters):
            self.applied_filters.pop(index)
            self._reapply_filters()

    def _reapply_filters(self):
        """Internal method to reset data and apply all filters in sequence."""
        if self.original_raw is None:
            return
            
        print("EEGDataModel: Re-applying all filters...")
        self.raw = self.original_raw.copy()
        
        for filt in self.applied_filters:
            f_type = filt["type"]
            params = filt["params"]
            
            try:
                if f_type == "notch":
                    self.raw.notch_filter(freqs=params["freqs"], verbose='error')
                elif f_type == "bandpass":
                    self.raw.filter(l_freq=params["l_freq"], h_freq=params["h_freq"], verbose='error')
                elif f_type == "lowpass":
                    self.raw.filter(l_freq=None, h_freq=params["h_freq"], verbose='error')
                elif f_type == "highpass":
                    self.raw.filter(l_freq=params["l_freq"], h_freq=None, verbose='error')
            except Exception as e:
                print(f"EEGDataModel ERROR: Failed to apply filter {f_type}: {e}")

    def get_data(self) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """Returns (data_array, times_array)"""
        if self.raw:
            try:
                print("EEGDataModel: Fetching all data...")
                data, times = self.raw.get_data(return_times=True)
                print(f"EEGDataModel: Data fetched. Shape: {data.shape}")
                return data, times
            except Exception as e:
                print(f"EEGDataModel ERROR: get_data failed: {e}")
        return None, None

    def get_channel_data(self, ch_index: int) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        if self.raw:
            data, times = self.raw[ch_index, :]
            return data[0], times
        return None, None