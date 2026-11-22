@echo off
rem 2026-11-22: first time only. Gets every pair's history into MT5 (3 years of W1 = 3 years of M1, 400 days of M15) with no time limit,
rem so that the normal button (PAIR_ENV.bat, 60 s / 300 s limits) is quick afterwards. Also sends the arrows and the stars. Read only, no orders.
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
echo 初回だけ：全部の通貨の履歴を MT5 に取り込みます（時間の制限なし。長いと数十分）。注文はしません。
py -m mt5_ea.live.pair_env --timeout 0 --w1-timeout 0 %*
echo.
echo Press any key to close this window.
pause >nul
