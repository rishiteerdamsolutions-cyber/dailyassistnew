@echo off
REM Stage Tesseract + tessdata for Nuitka Windows retail builds.
setlocal
cd /d "%~dp0\.."

set DEST=vendor\tesseract
set SRC=C:\Program Files\Tesseract-OCR

if not exist "%SRC%\tesseract.exe" (
  echo ERROR: Install Tesseract for Windows first:
  echo   https://github.com/UB-Mannheim/tesseract/wiki
  echo Expected: %SRC%\tesseract.exe
  exit /b 1
)

if exist "%DEST%" rmdir /s /q "%DEST%"
mkdir "%DEST%"
mkdir "%DEST%\tessdata"

copy /Y "%SRC%\tesseract.exe" "%DEST%\"
xcopy /E /I /Y "%SRC%\tessdata\eng.traineddata" "%DEST%\tessdata\" >nul 2>&1
if not exist "%DEST%\tessdata\eng.traineddata" (
  xcopy /E /I /Y "%SRC%\tessdata" "%DEST%\tessdata\"
)

REM Common runtime DLLs next to tesseract.exe
for %%F in (libtesseract-5.dll libleptonica-*.dll libarchive-*.dll) do (
  if exist "%SRC%\%%F" copy /Y "%SRC%\%%F" "%DEST%\" >nul 2>&1
)

echo [OK] Staged Tesseract: %DEST%\tesseract.exe
endlocal
