@echo off
rem 2026-11-23: how well the stars and the alerts catch the trader's marks, and how often they come (read only)
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
py -m mt5_ea.live.alert_study %*
echo.
echo Press any key to close this window.
pause >nul
