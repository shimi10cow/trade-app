$ErrorActionPreference = "Stop"
$login=[Environment]::GetEnvironmentVariable("EA_LIVE_LOGIN","User")
$server=[Environment]::GetEnvironmentVariable("EA_LIVE_SERVER","User")
if (-not $login -or -not $server) { throw "LIVE account lock is not configured." }
$env:EA_LIVE_LOGIN=$login
$env:EA_LIVE_SERVER=$server
$telegramToken=[Environment]::GetEnvironmentVariable("EA_TELEGRAM_BOT_TOKEN","User")
$telegramChat=[Environment]::GetEnvironmentVariable("EA_TELEGRAM_CHAT_ID","User")
if (-not $telegramToken -or -not $telegramChat) { throw "Telegram is not configured. Run configure_telegram.ps1 first." }
$env:EA_TELEGRAM_BOT_TOKEN=$telegramToken
$env:EA_TELEGRAM_CHAT_ID=$telegramChat
$env:EA_LIVE_ARMED="false"
$env:EA_DRY_RUN="true"
$env:EA_LIVE_REQUIRE_REAL="true"
Write-Host "Hybrid EA - FINAL PRE-LIVE CHECK (NO ORDERS)" -ForegroundColor Cyan
py .\preflight.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
py .\telegram_test.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
py .\live_safety_test.py
