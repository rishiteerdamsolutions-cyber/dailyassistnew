#!/bin/bash
echo "Starting AHA Companion Thin Client..."
echo "Please ensure you have python3 installed."

# Create venv if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
echo "Installing dependencies..."
# Pin pyobjc-core<12.0 to fix a known compilation issue on Python 3.9 Mac
pip install "pyobjc-core<12.0"
pip install websockets mss pyautogui pillow

echo "Launching agent. When prompted, macOS will ask for Accessibility and Screen Recording permissions for this Terminal."
python3 client.py
