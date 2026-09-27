$ErrorActionPreference = "Stop"
$login=[Environment]::GetEnvironmentVariable("EA_LIVE_LOGIN","User")
$server=[Environment]::GetEnvironmentVariable("EA_LIVE_SERVER","User")
if (-not $login -or -not $server) { throw "LIVE account lock is not configured." }
$env:EA_LIVE_LOGIN=$login
$env:EA_LIVE_SERVER=$server
$telegramToken=[Environment]::GetEnvironmentVariable("EA_TELEGRAM_BOT_TOKEN","User")
$telegramChat=[Environment]::GetEnvironmentVariable("EA_TELEGRAM_CHAT_ID","User")
if ($telegramToken) { $env:EA_TELEGRAM_BOT_TOKEN=$telegramToken }
if ($telegramChat) { $env:EA_TELEGRAM_CHAT_ID=$telegramChat }
$env:EA_LIVE_ARMED="false"
$env:EA_DRY_RUN="true"
$env:EA_PAIRS="EURUSD,USDJPY,EURJPY,AUDJPY,XAUUSD"
$env:EA_POLL_SEC="2"
$env:EA_MAGIC="560001"
$env:EA_LIVE_REQUIRE_REAL="true"

Write-Host "Hybrid EA - one-shot final check + LIVE start" -ForegroundColor Cyan
py .\preflight.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
py .\live_safety_test.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# The script arms LIVE only after every no-order check has passed.
$env:EA_DRY_RUN="false"
$env:EA_LIVE_ARMED="true"
Write-Host "All checks passed. Starting LIVE runner." -ForegroundColor Green
py .\main.py
