@echo off
REM Full Windows retail zip: Nuitka compile + downloads\AHA-win.zip
setlocal
cd /d "%~dp0\.."

call scripts\build_windows.bat
if errorlevel 1 exit /b 1

set STAGING=dist\_package_staging
set OUT=downloads\AHA-win.zip

if exist "%STAGING%" rmdir /s /q "%STAGING%"
mkdir "%STAGING%"
xcopy /E /I /Y dist\AHA "%STAGING%\AHA"
copy /Y INSTALL.md "%STAGING%\"

if exist "%OUT%" del /f "%OUT%"
powershell -NoProfile -Command "Compress-Archive -Path '%STAGING%\*' -DestinationPath '%OUT%' -Force"
rmdir /s /q "%STAGING%"

echo [OK] %OUT%
dir "%OUT%"
echo Upload to Supabase aha-releases and set AHA_DOWNLOAD_WIN_URL on Vercel.
endlocal
