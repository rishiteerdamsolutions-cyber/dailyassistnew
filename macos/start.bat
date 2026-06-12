@echo off
echo ==========================================
echo Starting Biological Agent Companion App...
echo ==========================================

cd /d "%~dp0"

REM Check if Python is installed
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in your PATH. Please install Python 3.
    pause
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist ".venv" (
    echo [INFO] Creating virtual environment...
    python -m venv .venv
)

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Install requirements
echo [INFO] Installing dependencies...
pip install -r requirements.txt
pip install -e .

REM Start the server in the background
echo [INFO] Starting Backend Server...
start /B uvicorn server:app --port 8000

REM Wait 2 seconds for server to boot
timeout /t 2 /nobreak >nul

REM Open the sandbox in the default browser
echo [INFO] Opening Sandbox UI...
start sandbox.html

echo [INFO] System is running! Keep this window open. Close it to stop the server.
cmd /k
