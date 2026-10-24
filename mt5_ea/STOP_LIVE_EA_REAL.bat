@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop_live_ea.ps1" -Kind live
timeout /t 3 /nobreak >nul
