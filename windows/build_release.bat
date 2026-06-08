@echo off
REM Build AHA for release — Windows .exe folder (run from this windows\ folder).
setlocal
cd /d "%~dp0"

echo Building AHA for Windows release...

python --version >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python 3.10+ required on PATH.
  pause
  exit /b 1
)

if not exist .venv python -m venv .venv
call .venv\Scripts\activate.bat
pip install -q -r requirements.txt -e .
pip install -q nuitka ordered-set zstandard 2>nul

python -c "import nuitka" 2>nul
if errorlevel 1 (
  echo ERROR: pip install nuitka
  pause
  exit /b 1
)

python -m nuitka ^
  --standalone ^
  --windows-console-mode=disable ^
  --output-dir=dist ^
  --include-data-dir=web=web ^
  --include-data-dir=VISIONBUTTONS=VISIONBUTTONS ^
  --include-package=aha ^
  --include-package=bol ^
  --assume-yes-for-downloads ^
  app_webview.py

echo [OK] dist\app_webview.dist\ — zip this folder for customers
pause
endlocal
