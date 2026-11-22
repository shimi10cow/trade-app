@echo off
rem 2026-11-22: alerts answer check - which Telegram alerts and stars would have come over the last 2 weeks (read only, no orders)
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
py -m mt5_ea.live.alert_replay %*
echo.
echo Press any key to close this window.
pause >nul
