@echo off
cd /d "%~dp0"
echo This starts the EA on the REAL account (real money).
choice /C YN /M "Start the REAL-account EA"
if errorlevel 2 exit /b 0
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_live_ea.ps1" -Kind live
pause
