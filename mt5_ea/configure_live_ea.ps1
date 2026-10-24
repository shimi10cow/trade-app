# One-time setup for the new live EA (2026-10-24). Saves the settings as user environment variables.
$ErrorActionPreference = "Stop"
$url = Read-Host "GAS URL (the app's /exec address)"
$key = Read-Host "EA_KEY (shown by eaSetupKeys() in the Apps Script log)"
$demo = Read-Host "Demo EA account number"
$demoPath = Read-Host "Demo MT5 terminal64.exe path (Enter = default terminal)"
$live = Read-Host "Live EA account number (Enter = not yet)"
$livePath = Read-Host "Live MT5 terminal64.exe path (Enter = not yet)"
[Environment]::SetEnvironmentVariable("EA_GAS_URL",$url,"User")
[Environment]::SetEnvironmentVariable("EA_GAS_KEY",$key,"User")
[Environment]::SetEnvironmentVariable("EA_DEMO_LOGIN",$demo,"User")
[Environment]::SetEnvironmentVariable("EA_DEMO_MT5_PATH",$demoPath,"User")
[Environment]::SetEnvironmentVariable("EA_REAL_LOGIN",$live,"User")
[Environment]::SetEnvironmentVariable("EA_REAL_MT5_PATH",$livePath,"User")
Write-Host "Saved. Start with START_LIVE_EA_DEMO.bat (and START_LIVE_EA_REAL.bat when the live account is ready)."
