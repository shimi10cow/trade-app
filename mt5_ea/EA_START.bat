@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Normal -File "%~dp0start_live.ps1"
if errorlevel 1 (
  echo.
  echo EA failed to start. Check the message above.
  pause
)
