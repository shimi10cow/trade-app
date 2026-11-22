@echo off
rem Monthly Dow, once (2026-11-22): 16 years of MN1 from MT5 into TradeEA_data\monthly. Downloads old M1 history (~6 GB); delete the old .hcc files afterwards.
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
py -m mt5_ea.live.pair_env --seed-monthly %*
echo.
echo Press any key to close this window.
pause >nul
