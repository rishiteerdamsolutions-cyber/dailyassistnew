@echo off
setlocal enabledelayedexpansion
echo ==========================================
echo   AHA - Artificial Human Assistant
echo ==========================================
echo.

cd /d "%~dp0"

REM Check Python 3.9+
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in your PATH.
    echo         Download Python from https://www.python.org/downloads/
    echo         Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist ".venv" (
    echo [INFO] Creating virtual environment...
    python -m venv .venv
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Could not create virtual environment.
        pause
        exit /b 1
    )
)

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Install/update dependencies
echo [INFO] Installing dependencies (first run may take a minute)...
pip install --quiet -r requirements.txt
pip install --quiet -e .
pip install --quiet pywebview

echo.
echo [INFO] Starting AHA companion...
echo [INFO] A window will open shortly. Keep this terminal open.
echo.

REM Launch the companion app (pywebview opens its own window)
python app_webview.py

echo.
echo [INFO] AHA has been closed.
pause
