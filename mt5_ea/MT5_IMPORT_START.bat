@echo off
cd /d "%~dp0"
echo Starting read-only MT5 import worker...
py mt5_import_worker.py
pause
