@echo off
chcp 65001 >nul
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0gas_deploy_setup.ps1"
echo.
echo Press any key to close this window.
pause >nul
