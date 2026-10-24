@echo off
cd /d "%~dp0.."
py -m mt5_ea.live.check_symbols
pause
