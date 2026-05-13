# EEGAnalyser

A (vibe coded) Python-based application for visualizing and analyzing EEG data from EDF files.

Why? EDFBrowser was not working on macos.

## Features
- EDF file loading and visualization.
- Multi-channel time-series plotting with downsampling for performance.
- Spectral analysis (PSD and Spectrogram).
- Annotation management and export.

## Installation
1. Create a virtual environment:
   ```bash
   python -m venv venv
   ```
2. Activate the virtual environment:
   - macOS/Linux: `source venv/bin/activate`
   - Windows: `venv\Scripts\activate`
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application
Use the provided `run.sh` script or run directly:
```bash
python main.py
```

## Troubleshooting
If the application fails to load or display data:
1. Check the console output for error messages.
2. Ensure your EDF files are valid.
3. If the UI is blank, try disabling OpenGL in `main.py`.
