@echo off
rem One-click EA report (2026-11-21): trades from GAS + backtest of the same period -> HTML with charts (opens in the browser).
rem Options: --days 90 (only the last 90 days)  --no-bt (skip the backtest, faster)
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
py -m mt5_ea.live.report %*
echo.
echo Press any key to close this window.
pause >nul
