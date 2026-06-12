@echo off
echo Starting AHA Companion Thin Client...
echo Please ensure you have Python installed and added to PATH.

IF NOT EXIST venv (
    echo Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate.bat
echo Installing dependencies...
pip install websockets mss pyautogui pillow

echo Launching agent...
python client.py
pause
