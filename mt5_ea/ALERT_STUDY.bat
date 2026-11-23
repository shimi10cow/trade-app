@echo off
rem 2026-11-22: compare the current alert (touch the H4 line, M15 turn) and the new one (within 2.5 ATR, M15 trendline break). Read only.
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
py -m mt5_ea.live.alert_study %*
echo.
echo Press any key to close this window.
pause >nul
