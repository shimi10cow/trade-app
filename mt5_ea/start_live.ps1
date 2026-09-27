$ErrorActionPreference = "Stop"
$login=[Environment]::GetEnvironmentVariable("EA_LIVE_LOGIN","User")
$server=[Environment]::GetEnvironmentVariable("EA_LIVE_SERVER","User")
if (-not $login -or -not $server) { throw "Run configure_live_lock.ps1 first." }
$env:EA_LIVE_LOGIN=$login
$env:EA_LIVE_SERVER=$server
$env:EA_LIVE_ARMED="true"
$env:EA_DRY_RUN="false"
$env:EA_PAIRS="EURUSD,USDJPY,EURJPY,AUDJPY,XAUUSD"
$env:EA_POLL_SEC="2"
$env:EA_MAGIC="560001"
Write-Host "Hybrid EA LIVE launcher" -ForegroundColor Yellow
Write-Host "Account/server lock + runtime safety gates are active." -ForegroundColor Yellow
py .\main.py
