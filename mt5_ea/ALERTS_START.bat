@echo off
rem Discretionary alerts (2026-11-21): Telegram + app list when price comes back to an H4 gateway / fortress. Read only, no orders.
chcp 65001 >nul
title 裁量の通知（この窓を閉じると止まる・注文はしない）
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
:loop
py -m mt5_ea.live.alerts
if %ERRORLEVEL%==3 (timeout /t 5 >nul & exit /b 0)
echo Stopped. Restarting in 30 seconds (close this window to stop)...
timeout /t 30 >nul
goto loop
