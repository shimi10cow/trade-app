@echo off
setlocal
cd /d "%~dp0"

powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Normal -File "%~dp0start_live.ps1"
set "EA_EXIT=%ERRORLEVEL%"

echo.
if not "%EA_EXIT%"=="0" (
  echo EA failed to start. Check the message above.
) else (
  echo EA runner exited or EA is already running.
)
echo.
echo Press any key to close this window.
pause >nul
exit /b %EA_EXIT%
