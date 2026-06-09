@echo off
REM Nuitka retail compile for Windows — dist\AHA\AHA.exe
REM Requires Python 3.10+ on PATH (python.org installer, not legacy 3.9).

setlocal
cd /d "%~dp0\.."

set PY=
where python3.12 >nul 2>&1 && set PY=python3.12
if not defined PY where python3.11 >nul 2>&1 && set PY=python3.11
if not defined PY where python3.10 >nul 2>&1 && set PY=python3.10
if not defined PY (
  echo ERROR: Python 3.10+ required. Install from https://www.python.org/downloads/
  exit /b 1
)

echo [INFO] Using %PY%
if not exist .venv python -m venv .venv
call .venv\Scripts\activate.bat

pip install -q -U pip
pip install -q -r requirements.txt -e .
pip install -q -r requirements-build.txt

echo [INFO] Staging Tesseract for customer machines...
call scripts\stage_tesseract_win.bat
if errorlevel 1 exit /b 1

echo [INFO] Compiling AHA.exe with Nuitka...
%PY% -m nuitka ^
  --standalone ^
  --windows-console-mode=disable ^
  --company-name=dailyassist.xyz ^
  --product-name=AHA ^
  --file-version=1.0.0 ^
  --output-dir=dist ^
  --output-filename=AHA ^
  --include-data-dir=web=web ^
  --include-data-dir=VISIONBUTTONS=VISIONBUTTONS ^
  --include-data-dir=vendor\tesseract=tesseract ^
  --include-data-files=INSTALL.md=INSTALL.md ^
  --include-package=aha ^
  --include-package=bol ^
  --include-package=server ^
  --include-package=cv2 ^
  --include-package=PIL ^
  --include-package=numpy ^
  --include-package=pytesseract ^
  --include-package=pyautogui ^
  --include-package=mss ^
  --include-package=psutil ^
  --include-package=uvicorn ^
  --include-package=fastapi ^
  --include-package=multipart ^
  --include-package=starlette ^
  --include-package=pydantic ^
  --include-package=pydantic_settings ^
  --include-package=firebase_admin ^
  --include-package=supabase ^
  --include-package=razorpay ^
  --include-package=google.generativeai ^
  --include-package=engineio ^
  --include-package=socketio ^
  --include-package=httpx ^
  --include-package=anyio ^
  --include-package-data=webview ^
  --include-package-data=cv2 ^
  --nofollow-import-to=webview.platforms.android ^
  --nofollow-import-to=webview.platforms.cocoa ^
  --nofollow-import-to=webview.platforms.qt ^
  --nofollow-import-to=webview.platforms.edgehtml ^
  --nofollow-import-to=webview.platforms.mshtml ^
  --nofollow-import-to=webview.platforms.cef ^
  --nofollow-import-to=tests ^
  --nofollow-import-to=pytest ^
  --assume-yes-for-downloads ^
  app_webview.py

if not exist dist\AHA.dist\AHA.exe (
  if exist dist\app_webview.dist\app_webview.exe (
    rmdir /s /q dist\AHA 2>nul
    move dist\app_webview.dist dist\AHA
    ren dist\AHA\app_webview.exe AHA.exe
  ) else (
    echo ERROR: Nuitka did not produce AHA.exe
    dir dist
    exit /b 1
  )
) else (
  rmdir /s /q dist\AHA 2>nul
  move dist\AHA.dist dist\AHA
)

echo [OK] dist\AHA\AHA.exe
endlocal
