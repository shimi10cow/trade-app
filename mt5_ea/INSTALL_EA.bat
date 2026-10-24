@echo off
rem One-time install of the self-updating EA into %USERPROFILE%\TradeEA (2026-10-24).
rem After this, start the EA only with %USERPROFILE%\TradeEA\RUN_EA_DEMO.bat (it updates itself from GitHub main).
setlocal
set "T=%USERPROFILE%\TradeEA"
if not exist "%T%" mkdir "%T%"
copy /Y "%~dp0live\updater.py" "%T%\updater.py" >nul
(
echo @echo off
echo cd /d "%%~dp0"
echo :loop
echo py "%%~dp0updater.py" "%%~dp0."
echo powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%%~dp0app\mt5_ea\start_live_ea.ps1" -Kind demo
echo if %%ERRORLEVEL%%==3 goto loop
echo echo EA stopped ^(code %%ERRORLEVEL%%^).
echo pause
) > "%T%\RUN_EA_DEMO.bat"
(
echo @echo off
echo cd /d "%%~dp0"
echo :loop
echo py "%%~dp0updater.py" "%%~dp0."
echo powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%%~dp0app\mt5_ea\start_live_ea.ps1" -Kind live
echo if %%ERRORLEVEL%%==3 goto loop
echo echo EA stopped ^(code %%ERRORLEVEL%%^).
echo pause
) > "%T%\RUN_EA_REAL.bat"
(
echo @echo off
echo cd /d "%%~dp0app"
echo py -m mt5_ea.live.check_symbols
echo pause
) > "%T%\CHECK_SYMBOLS.bat"
py "%T%\updater.py" "%T%"
echo.
echo Installed to %T%
echo From now on start the EA with: %T%\RUN_EA_DEMO.bat
explorer "%T%"
pause
