$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$login=[Environment]::GetEnvironmentVariable("EA_LIVE_LOGIN","User")
$server=[Environment]::GetEnvironmentVariable("EA_LIVE_SERVER","User")
if (-not $login -or -not $server) { throw "LIVE account lock is not configured." }
$env:EA_LIVE_LOGIN=$login
$env:EA_LIVE_SERVER=$server
$telegramToken=[Environment]::GetEnvironmentVariable("EA_TELEGRAM_BOT_TOKEN","User")
$telegramChat=[Environment]::GetEnvironmentVariable("EA_TELEGRAM_CHAT_ID","User")
if ($telegramToken) { $env:EA_TELEGRAM_BOT_TOKEN=$telegramToken }
if ($telegramChat) { $env:EA_TELEGRAM_CHAT_ID=$telegramChat }
if (-not $telegramToken -or -not $telegramChat) { Write-Warning "Telegram is not configured; trading can continue but notifications are unavailable." }
$env:EA_LIVE_ARMED="false"
$env:EA_DRY_RUN="true"
$env:EA_PAIRS=""  # Monitor every pair configured in the app/EA_Settings
$env:EA_POLL_SEC="2"
$env:EA_MAGIC="560001"
$env:EA_LIVE_REQUIRE_REAL="true"

$running = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
  $_.Name -match '^(python|pythonw)\.exe$' -and $_.CommandLine -match 'main\.py'
}
if ($running) {
  Write-Host "EA is already running. PID: $($running.ProcessId -join ', ')" -ForegroundColor Yellow
  exit 0
}

Write-Host "Hybrid EA - one-shot final check + LIVE start" -ForegroundColor Cyan
py .\preflight.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
py .\telegram_test.py
if ($LASTEXITCODE -ne 0) { Write-Warning "Telegram check failed; LIVE safety checks will continue." }
py .\live_safety_test.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# The script arms LIVE only after every no-order check has passed.
$env:EA_DRY_RUN="false"
$env:EA_LIVE_ARMED="true"
Write-Host "All checks passed. Starting LIVE runner." -ForegroundColor Green
py .\main.py
