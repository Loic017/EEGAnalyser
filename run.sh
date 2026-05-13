#!/bin/bash
# Simple script to activate the virtual environment and run the application

# Check if the virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Please ensure it was created during setup."
    exit 1
fi

echo "Activating virtual environment and launching EEGAnalyser..."
source venv/bin/activate
python main.py
