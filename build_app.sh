#!/bin/bash
# Script to build the standalone macOS application using PyInstaller

# Exit immediately if a command exits with a non-zero status
set -e

# Check if the virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Please ensure it was created during setup."
    exit 1
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Ensuring PyInstaller is installed..."
pip install pyinstaller --quiet

echo "Cleaning up previous builds..."
rm -rf build/ dist/ EEGAnalyser.spec EEGAnalyser.app

echo "Building standalone macOS application..."
# --windowed: Do not provide a console window for standard i/o.
# --noupx: Do not use UPX even if available (improves macOS compatibility)
# --name: The name to assign to the bundled app and executable
# --collect-all mne: Ensures lazy_loader and other data files are included
pyinstaller --windowed --noupx --collect-all mne --name "EEGAnalyser" main.py

echo "Moving app to project root..."
mv dist/EEGAnalyser.app ./EEGAnalyser.app

echo "Cleaning up build artifacts..."
rm -rf build/ dist/ EEGAnalyser.spec

echo "=========================================================="
echo "Build complete! "
echo "You can find EEGAnalyser.app in the current directory."
echo "You can run it directly or move it to your Applications folder."
echo "=========================================================="