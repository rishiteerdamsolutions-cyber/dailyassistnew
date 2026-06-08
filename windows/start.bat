@echo off
setlocal enabledelayedexpansion
echo ==========================================
echo   AHA - Artificial Human Assistant
echo   Windows
echo ==========================================
echo.

cd /d "%~dp0"

python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in your PATH.
    echo         Download Python 3.10+ from https://www.python.org/downloads/
    echo         Check "Add Python to PATH" during install.
    pause
    exit /b 1
)

if not exist ".venv" (
    echo [INFO] Creating virtual environment...
    python -m venv .venv
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Could not create virtual environment.
        pause
        exit /b 1
    )
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip -q

echo [INFO] Installing dependencies (first run may take 1-2 minutes)...
pip install -q -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)
pip install -q -e .
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to install AHA package.
    pause
    exit /b 1
)

echo.
echo [INFO] Starting AHA...
echo [INFO] Keep this window open while you use the app.
echo.

python app_webview.py

echo.
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] AHA exited with an error.
) else (
    echo [INFO] AHA has been closed.
)
pause
