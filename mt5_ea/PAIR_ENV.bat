@echo off
rem Pair tab trend arrows (2026-11-21): MT5 Dow direction M1/W1/D1/H4/H1 for every pair -> the app (Pairs). Read only, no orders.
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
py -m mt5_ea.live.pair_env %*
echo.
echo Press any key to close this window.
pause >nul
