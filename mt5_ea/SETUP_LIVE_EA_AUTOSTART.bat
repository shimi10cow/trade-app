@echo off
rem Start the demo EA automatically at Windows logon (run once). To turn it off: add -Remove after -Kind demo below and run again.
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_live_ea_autostart.ps1" -Kind demo
pause
